# Deferred BoundName Investigation: Current Architecture Analysis

This document provides a verified analysis of Pyrefly's current architecture
for name binding and partial type inference, intended to help engineers
investigating the deferred `BoundName` proposal. All code locations and
behaviors have been verified against the actual codebase.


## Original Proposal


### The Problem(s)

This doc is about a change to the bindings-phase architecture motivated by [this issue](https://github.com/facebook/pyrefly/issues/842) \- at the moment, inside of a loop Pyrefly disables partial type inference.

#### Partial type inference is disabled in loops

The challenge here is that even in cases where a loop doesn’t reassign a name, Pyrefly doesn’t have a way to know that at the outset of the AST traversal. Consider this code:

```
x = []
for i in range(5):
    x.append(i)
```

we create a speculative `LoopPhi` key at the top of the loop for `x`, and the `x.append(i)` evaluates against that binding. We later correctly note that `x` was not reassigned, so we create a `Binding::Forward` for the `LoopPhi`.

Now, partial-type inference knows how to look through `Forward` bindings. But because `BoundName` bindings (which are what look up a name in the current scope) are created eagerly, at the point where we actually create the lookup of `x` we don’t know yet that it will be a `Forward`. As a result, the read of `x` is ignored by partial type inference.

I consider this an extremely serious problem because one of Pyrefly’s key marketing points is partial type inference, but a pretty large proportion of actual uses of partial types involve containers populated in loops.

#### Determinism

In addition, there’s currently a known problem demonstrated here:

```
x = []
x.append(1) if len(x) == 0 else w := x.append("foo")
```

The problem here is that the `x.append(1) if len(x) == 0 else w := x.append("foo")` is the first use of `x`, but it is a compound binding:

* It wraps a narrow binding due to `len(x) == 0`  
* It additionally wraps a `NameAssign` binding for `w`

The challenge is that we now trade off cycles vs determinism:

* It’s known that compound bindings need to all use the same version of `x`; Jia fixed a bug in September where we tried to treat a narrow in a compound binding as *not* part of the first use, and this triggers a cycle where the `len(x) == 0` narrow tries to use the type of `x` *after* partial type inference, but we’re actually in the process of evaluating the partial type inference so we get `Unknown`  
* But if we allow `w` to use the raw type `list[@_]` of `x` and there’s any way for `w` to “escape” down the graph without us evaluating the entire statement, then it will be possible for an export that depends on `w` to trigger the `x.append(“foo”)` before the `x.append(1)`. This is clearly nondeterministic.

It’s unclear exactly how serious this problem is \- walrus operators are the only case where I’m sure we can leak an operation that nondeterministically pins a partial type, and walrus isn’t especially common. But if we care about determinism, we do need to close this gap.

### A proposed solution

Instead of directly inserting `Key::BoundName(location) => Binding::Forward(...)` bindings in the AST traversal using the `CurrentIdx` to handle partial type inference, let’s consider deferring the work by saving a record of the bindings we *will* need.

We can store this as a map where we store the actual bound name plus all the idxs passed as `CurrentIdx` in a lookup:

```
enum Use {
  Idx(Idx<Key>),
  Other,
}
struct Uses(Use);
struct BoundNames(SmallMap<(TextRange, Idx<Key>), Uses>);
```

The `Use::Other` is there to handle the possibility that some `Key.*` type that isn’t a `Key` depends on a name; I’m not sure if this happens today but architecturally it could occur, and we probably want to disable first-use inference if it does.

We can then create all of the `Key::BoundName(location) => Binding::Forward(...)` pairs at the very end of binding, when the entire module has already been traversed.

This approach is designed to allow us to solve both the determinism and loop problem:

* First, we can easily either disable first-use inference entirely in cases like compound bindings where there are determinism issues.  
  * In addition, we may be able to later massage the handling to eliminate the problem \- for example, if a walrus occurs inside a compound binding that is also a first-use, we could potentially create an extra binding in order to force all reads from the walrus-defined binding to pass through the outer binding in the binding graph.  
  * That might not be necessary in V0, my instinct would be to initially just disable partial type pinning when the first use location has multiple uses. but this map gives us the data needed for more clever approaches.  
* It solves the loop problem, because by the time we actually create the `BoundName` pairs we will know when a `LoopPhi` key is actually just a `Forward` and we’ll be able to look “through” the `Forward` to identify that we are looking at a first use of a potential partial type

### Conclusion (to the original proposal)

I think that this change is probably relatively noncontroversial, but I wanted to document it ahead of 2026 planning because it’s a major plumbing change that I think might take at least a week or two, and given the importance of partial type inference in loops I think it needs to happen before our V1 release of Pyrefly.


## Key Data Structures

### The `Key` Enum (`binding/binding.rs:376-448`)

`Key` identifies a binding site in the code. Relevant variants:

| Variant | Purpose |
|---------|---------|
| `Key::Definition(ShortIdentifier)` | A name assignment site (`x = ...`) |
| `Key::BoundName(ShortIdentifier)` | A name usage/lookup site (`... x ...`) |
| `Key::CompletedPartialType(ShortIdentifier)` | The "pinned" version of a name assignment |
| `Key::PartialTypeWithUpstreamsCompleted(ShortIdentifier)` | Handles first-use chains |
| `Key::Phi(Name, TextRange)` | A merge point for control flow |

### The `Binding` Enum (`binding/binding.rs:1270-1450`)

`Binding` describes how to compute a type for a `Key`. Relevant variants:

| Variant | Purpose |
|---------|---------|
| `Binding::Forward(Idx<Key>)` | Delegate to another binding |
| `Binding::Phi(JoinStyle, SmallSet<Idx<Key>>)` | Union of branch types |
| `Binding::LoopPhi(Idx<Key>, SmallSet<Idx<Key>>)` | Loop-aware phi with a prior value |
| `Binding::CompletedPartialType(Idx<Key>, FirstUse)` | Pins placeholder types after first use |
| `Binding::NameAssign{...}` | A variable assignment |

### The `Usage` Enum (`binding/expr.rs:72-108`)

Tracks the context in which a name lookup occurs:

```rust
pub enum Usage {
    /// Normal usage - can potentially pin placeholder types
    CurrentIdx(Idx<Key>, SmallSet<Idx<Key>>),
    /// Narrowing context - does not pin (nondeterminism risk)
    Narrowing(Option<Idx<Key>>),
    /// Type annotation context - does not pin
    StaticTypeInformation,
}
```

The `SmallSet<Idx<Key>>` in `CurrentIdx` tracks all first-use sites
encountered during expression evaluation. This exists for tracking when an
expression contains multiple first-uses.

### The `FirstUse` Enum (`binding/binding.rs:1260-1267`)

Tracks whether a `CompletedPartialType` has been pinned:

```rust
pub enum FirstUse {
    /// Not yet determined if there's a first use
    Undetermined,
    /// This binding cannot pin (e.g., used in narrowing context first)
    DoesNotPin,
    /// Pinned by the binding at this idx
    UsedBy(Idx<Key>),
}
```

## The Name Binding Flow

### 1. Name Lookup: `ensure_name_impl` (`binding/expr.rs:302-378`)

When encountering a name in an expression (e.g., `x` in `x.append(1)`):

```rust
fn ensure_name_impl(&mut self, name: &Identifier, usage: &mut Usage, ...) -> Idx<Key> {
    let key = Key::BoundName(ShortIdentifier::new(name));  // Line 308
    // ...
    let lookup_result = self.lookup_name(Hashed::new(&name.id), usage);  // Line 325
    match lookup_result {
        NameLookupResult::Found { idx: value, initialized } => {
            // ...error handling for uninitialized...
            self.insert_binding(key, Binding::Forward(value))  // Line 344
        }
        // ...not found handling...
    }
}
```

**Key observation**: The `BoundName` binding is inserted **immediately** with
`Binding::Forward(value)`, where `value` comes from `lookup_name`. This is the
"eager binding" that the proposal aims to defer.

### 2. Name Resolution: `lookup_name` (`binding/bindings.rs:864-896`)

Resolves a name in the current scope and handles first-use detection:

```rust
pub fn lookup_name(&mut self, name: Hashed<&Name>, usage: &mut Usage) -> NameLookupResult {
    match self.scopes.look_up_name_for_read(name) {
        NameReadInfo::Flow { idx, initialized } => {
            let (idx, first_use) = self.detect_first_use(idx, usage);  // Line 870
            if let Some(used_idx) = first_use {
                self.record_first_use(used_idx, usage);  // Line 872
            }
            // ...mark parameter/import/variable used...
            NameLookupResult::Found { idx, initialized }
        }
        // ...other cases...
    }
}
```

**Key observation**: First-use detection happens inside `lookup_name`, before
the `BoundName` is created. This couples first-use handling with immediate
binding creation.

### 3. First-Use Detection: `detect_first_use` (`binding/bindings.rs:913-952`)

Checks if the current lookup is the first use of a partial type:

```rust
fn detect_first_use(&self, flow_idx: Idx<Key>, usage: &mut Usage) -> (Idx<Key>, Option<Idx<Key>>) {
    match self.table.types.1.get(flow_idx) {
        Some(Binding::CompletedPartialType(unpinned_idx, FirstUse::Undetermined)) => {
            match usage {
                Usage::StaticTypeInformation | Usage::Narrowing(_) => {
                    (flow_idx, Some(flow_idx))  // Will set DoesNotPin
                }
                Usage::CurrentIdx(..) => {
                    (*unpinned_idx, Some(flow_idx))  // Return unpinned for inference
                }
            }
        }
        Some(Binding::CompletedPartialType(unpinned_idx, FirstUse::UsedBy(usage_idx))) => {
            // Handle secondary reads in the same first-use context
            // ...
        }
        _ => (flow_idx, None),  // Line 951 - LoopPhi falls through here!
    }
}
```

**Critical observation**: This function only recognizes `Binding::CompletedPartialType`.
A `Key::Phi` that has not yet been filled in (or a `Binding::LoopPhi`) will
fall through to the default case `(flow_idx, None)`, disabling first-use inference.

## Loop Handling

### 4. Loop Setup: `setup_loop` (`binding/scope.rs:2548-2555`)

Before traversing a loop body, speculative phi keys are reserved:

```rust
pub fn setup_loop(&mut self, range: TextRange, loop_header_targets: &SmallSet<Name>) {
    let base = mem::take(&mut self.scopes.current_mut().flow);
    // Speculatively insert phi keys for possible reassignments
    self.scopes.current_mut().flow =
        self.insert_phi_keys(base.clone(), range, loop_header_targets);
    self.scopes.current_mut().loops.push(Loop::new(base));
}
```

### 5. Phi Key Reservation: `insert_phi_keys` (`binding/scope.rs:2512-2540`)

For each name in the current flow, a `Key::Phi` is **reserved** using
`idx_for_promise`, but no binding is inserted yet:

```rust
fn insert_phi_keys(&mut self, mut flow: Flow, range: TextRange, exclude_names: &SmallSet<Name>) -> Flow {
    for (name, info) in flow.info.iter_mut() {
        if exclude_names.contains(name) { continue; }
        // Reserve a phi idx - binding will be inserted at merge time
        let phi_idx = self.idx_for_promise(Key::Phi(name.clone(), range));  // Line 2523
        match &mut info.value {
            Some(value) => { value.idx = phi_idx; }
            None => {
                info.value = Some(FlowValue {
                    idx: phi_idx,
                    style: FlowStyle::LoopRecursion,
                });
                info.narrow = None;
            }
        }
    }
    flow
}
```

**Important**: At this point, the `phi_idx` has no binding yet. Any name
lookup inside the loop will get this `phi_idx` from the flow, but
`self.table.types.1.get(phi_idx)` will return `None`.

### 6. Loop Merge: `merge_idxs` (`binding/scope.rs:2273-2296`)

After traversing the loop body, the reserved phi keys are filled in:

```rust
fn merge_idxs(
    &mut self,
    branch_idxs: SmallSet<Idx<Key>>,
    phi_idx: Idx<Key>,
    loop_prior: Option<Idx<Key>>,
    join_style: JoinStyle<Idx<Key>>,
) -> Idx<Key> {
    if branch_idxs.len() == 1 {
        // Name was NOT reassigned - just forward to the one idx
        let idx = *branch_idxs.first().unwrap();
        self.insert_binding_idx(phi_idx, Binding::Forward(idx));  // Line 2287
        idx
    } else if let Some(loop_prior) = loop_prior {
        // Name WAS reassigned in the loop - create LoopPhi
        self.insert_binding_idx(phi_idx, Binding::LoopPhi(loop_prior, branch_idxs));  // Line 2290
        phi_idx
    } else {
        self.insert_binding_idx(phi_idx, Binding::Phi(join_style, branch_idxs));
        phi_idx
    }
}
```

**Key insight**: If a name was NOT reassigned in the loop, the phi becomes a
simple `Binding::Forward`. But this resolution happens **after** the loop body
has been fully traversed - by which point all `BoundName` bindings inside the
loop already point to the unfilled `phi_idx`.

## The Problem in Detail

Consider this code:
```python
x = []
for i in range(5):
    x.append(i)
```

The flow is:
1. **Line 1**: `x = []` creates:
   - `Key::Definition(x)` → `Binding::NameAssign{...}` (produces `list[@_]`)
   - `Key::CompletedPartialType(x)` → `Binding::CompletedPartialType(def_idx, FirstUse::Undetermined)`
   - The flow maps `x` → `pinned_idx`

2. **Loop setup**: `setup_loop` is called:
   - A `Key::Phi(x, loop_range)` is reserved via `idx_for_promise`
   - The flow is updated: `x` → `phi_idx` (NO BINDING YET)

3. **Line 3**: `x.append(i)` is traversed:
   - `ensure_name_impl("x")` is called
   - `lookup_name` looks up `x` in the flow, gets `phi_idx`
   - `detect_first_use(phi_idx, ...)` is called
   - `self.table.types.1.get(phi_idx)` returns `None` (no binding yet!)
   - Falls through to `(flow_idx, None)` - **first-use detection fails**
   - `ensure_name_impl` inserts: `Key::BoundName(x)` → `Binding::Forward(phi_idx)`

4. **Loop teardown**: `merge_idxs` is called:
   - `x` was not reassigned, so `branch_idxs.len() == 1`
   - Phi becomes `Binding::Forward(pinned_idx)` (the CompletedPartialType)
   - **Too late!** The `BoundName` already points to `phi_idx`, not through it

5. **Solving**: When solving `BoundName(x)`:
   - It forwards to `phi_idx`
   - `phi_idx` forwards to `pinned_idx` (the CompletedPartialType)
   - But `FirstUse` is still `Undetermined` because `detect_first_use` never saw it
   - The placeholder type is forced to `Any` instead of being inferred from `append(i)`

## Partial Type Creation

### 7. Name Assignment: `bind_single_name_assign` (`binding/target.rs:432-499`)

When assigning to a simple name (like `x = []`):

```rust
pub fn bind_single_name_assign(&mut self, name: &Identifier, mut value: Box<Expr>, ...) {
    let identifier = ShortIdentifier::new(name);
    let mut user = self.declare_current_idx(Key::Definition(identifier));
    let pinned_idx = self.idx_for_promise(Key::CompletedPartialType(identifier));  // Line 440
    // ...process the value expression...

    // Insert the raw NameAssign binding
    let def_idx = self.insert_binding_idx(def_idx, binding);  // Line 480

    // Handle upstream first-uses if any
    let unpinned_idx = if first_used_by.is_empty() {
        def_idx
    } else {
        self.insert_binding(
            Key::PartialTypeWithUpstreamsCompleted(identifier),
            Binding::PartialTypeWithUpstreamsCompleted(def_idx, first_used_by...),
        )
    };

    // Insert the pinning binding
    self.insert_binding_idx(
        pinned_idx,
        Binding::CompletedPartialType(unpinned_idx, FirstUse::Undetermined),  // Line 496
    );
}
```

This creates the layered structure:
- `Key::Definition` → `Binding::NameAssign` (may have placeholder `Var`s)
- `Key::CompletedPartialType` → `Binding::CompletedPartialType(def, FirstUse::Undetermined)`

The `CompletedPartialType` is what goes into the scope's flow and is what
normal name lookups will find.

## Existing Deferred Patterns

The codebase already uses `idx_for_promise` for deferred binding in several
places:

| Location | Key Type | When Filled |
|----------|----------|-------------|
| `scope.rs:2496` | `Key::Phi` | At branch merge |
| `scope.rs:2523` | `Key::Phi` | At loop merge |
| `target.rs:440` | `Key::CompletedPartialType` | Same function, after processing value |

This pattern - reserving an `Idx<Key>` and filling in the binding later - is
well-established and architecturally consistent.

## Verified Architecture Facts

1. **Eager `BoundName` creation is confirmed**: Line 344 of `expr.rs` inserts
   `Binding::Forward(value)` immediately, where `value` comes from `lookup_name`.

2. **First-use detection only recognizes `CompletedPartialType`**: Line 918 of
   `bindings.rs` explicitly matches on this binding type; everything else falls
   through.

3. **Phi keys are reserved before loop body traversal**: Line 2523 of
   `scope.rs` calls `idx_for_promise` but does not insert a binding.

4. **Phi bindings are filled in after loop body traversal**: Line 2287 and
   2290 of `scope.rs` insert the actual binding in `merge_idxs`.

5. **The timing mismatch is the root cause**: `BoundName` bindings are created
   during loop body traversal (step 3 above), but phi bindings aren't filled
   in until after (step 4). This prevents `detect_first_use` from looking
   through the phi to find the `CompletedPartialType`.

## Implications for the Proposed Solution

The proposed solution to defer `BoundName` creation until after AST traversal
is architecturally sound because:

1. It follows the existing `idx_for_promise` pattern
2. By finalization time, all phi bindings have been filled in
3. Walking through `Forward` chains will correctly find `CompletedPartialType`
4. First-use detection can then work correctly

The key implementation considerations are:
- Store the result of `lookup_name` (the target idx) at traversal time
- Don't replay `lookup_name` at finalization (scope state has changed)
- Process deferred bindings in `TextRange` order for determinism
- Handle compound bindings (multiple uses at same location) conservatively

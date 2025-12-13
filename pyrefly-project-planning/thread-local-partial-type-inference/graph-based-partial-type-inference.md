# Graph-Based Partial Type Inference in Pyrefly

This document details the implementation of partial type inference in Pyrefly.
This system enables the type checker to infer types for variables initialized
with incomplete information (e.g., `x = []`) by "trapping" the partial types
within the binding graph and pinning them based on their first deterministic
usage.

## 1. The Problem

Consider:

```python
x = []
x.append(1)
```

At `x = []`, the element type is unknown. A naive approach would immediately
assign `list[Any]`. Instead, Pyrefly defers this decision, creating a **partial
type** (`list[@0]` where `@0` is a placeholder), and then uses the first
downstream use (`x.append(1)`) to infer `list[int]`.

The challenge is that Pyrefly uses a graph-based solver that processes bindings
in topological order. Without careful design, partial types could either:

1. Escape into the binding graph before being pinned, causing nondeterminism
2. Get pinned too early, before constraints from usage can inform the type

## 2. Core Architecture: The "Trap" Pattern

Pyrefly "traps" partial types by splitting each name assignment into multiple
binding graph nodes, creating a controlled pathway for partial types to flow
through.

### 2.1 Key Types (`lib/binding/binding.rs`)

**`Key` enum:**

- `Key::Definition(ShortIdentifier)`: The raw assignment result, may contain
  unpinned `Type::Var`s
- `Key::CompletedPartialType(ShortIdentifier)`: The "public" binding exposed to
  scopes; responsible for pinning
- `Key::PartialTypeWithUpstreamsCompleted(ShortIdentifier)`: Intermediate
  binding when an assignment is also a first use of another partial type

**`FirstUse` enum:**

```rust
pub enum FirstUse {
    Undetermined,       // No first use seen yet
    DoesNotPin,         // First use in non-pinning context (static type info)
    UsedBy(Idx<Key>),   // This binding is the first use
}
```

**`Binding` variants:**

- `Binding::NameAssign { .. }`: Raw computation, can produce partial `Var`s
- `Binding::CompletedPartialType(Idx<Key>, FirstUse)`: Wraps raw definition,
  forces first use before pinning
- `Binding::PartialTypeWithUpstreamsCompleted(Idx<Key>, Box<[Idx<Key>]>)`:
  Forces upstream pins before evaluating raw definition

### 2.2 Variable Types (`lib/solver/solver.rs`)

```rust
enum Variable {
    PartialContained,                 // Empty containers: [], {}, set()
    PartialQuantified(Box<Quantified>), // Unsolved type params in generic calls
    Quantified(Box<Quantified>),      // Type params during instantiation
    Recursive,                        // General recursion
    LoopRecursive(Type, LoopBound),   // Loop-recursive with prior bound
    Unwrap,                           // Extracting inner types (e.g., T from Awaitable[T])
    Parameter,                        // Function/lambda parameter types
    Answer(Type),                     // Solved variable
}
```

**Key distinction:** `PartialQuantified` behaves like `PartialContained` but
retains access to its default type, which is used if pinning doesn't resolve it
otherwise.

## 3. Binding Graph Construction

### 3.1 The Three Binding Nodes

For a statement `x = []`, the `bind_single_name_assign` function (in
`lib/binding/target.rs`) creates the following structure:

1. **`Key::Definition(x)` -> `Binding::NameAssign`**
   - **Role:** The "Raw" definition.
   - **Content:** Evaluates `[]` to `list[@0]`, where `@0` is a
     `Variable::PartialContained`.
   - **Pinning:** **SKIPPED**. This is one of the few bindings where
     `pin_all_placeholder_types` is explicitly bypassed in the solver. This
     allows the partial variable `@0` to "leak" out, but only to specific
     consumers.

2. **`Key::PartialTypeWithUpstreamsCompleted(x)` ->
   `Binding::PartialTypeWithUpstreamsCompleted`** (Optional)
   - **Role:** The "Chain" link.
   - **Usage:** Created *only* if the assignment `x = ...` is itself the first
     use of *another* partial variable (e.g., `x = [], y`).
   - **Logic:** Forces the *pinned* (public) version of upstream dependencies
     before evaluating the "Raw" definition. This prevents upstream partial
     variables from leaking into `x`, while still allowing `x` to have its own
     partial variables.
   - **Pinning:** **SKIPPED**. Like `NameAssign`, this exposes the raw partial
     type of `x`.

3. **`Key::CompletedPartialType(x)` -> `Binding::CompletedPartialType`**
   - **Role:** The "Public" face / The "Pin".
   - **Usage:** This is what names in the scope map to.
   - **State:** Stores a `FirstUse` state (`Undetermined`, `DoesNotPin`, or
     `UsedBy(idx)`).
   - **Logic:** When solved, it *first* forces the evaluation of the recorded
     `FirstUse` binding (triggering side effects/constraints), *then* evaluates
     the Raw definition.
   - **Pinning:** **PERFORMED**. After evaluation, `pin_all_placeholder_types`
     is called. Any partial variable that wasn't solved by the first use is
     forced to its default (usually `Any`).

### 3.2 Binding Graph Visualization

```
                                 ┌─────────────────────────────────┐
                                 │       Scope sees this           │
                                 └─────────────────────────────────┘
                                                 │
                                                 ▼
                         ┌───────────────────────────────────────────┐
                         │ Key::CompletedPartialType(x)               │
                         │ Binding::CompletedPartialType(             │
                         │     unpinned_idx, FirstUse::Undetermined)  │
                         └───────────────────────────────────────────┘
                                                 │
                                                 ▼
                         ┌───────────────────────────────────────────┐
                         │ Key::Definition(x)                         │
                         │ Binding::NameAssign { ... }                │
                         │ Type: list[@0] where @0 is PartialContained│
                         └───────────────────────────────────────────┘
```

**When the assignment is also a first use** (e.g., `y = [], x` where `x = []`
was prior):

```
                         ┌───────────────────────────────────────────┐
                         │ Key::CompletedPartialType(y)               │
                         │ Binding::CompletedPartialType(             │
                         │     upstreams_idx, FirstUse::Undetermined) │
                         └───────────────────────────────────────────┘
                                                 │
                                                 ▼
                         ┌───────────────────────────────────────────┐
                         │ Key::PartialTypeWithUpstreamsCompleted(y)  │
                         │ Binding::PartialTypeWithUpstreamsCompleted(│
                         │     def_idx, [x's CompletedPartialType])   │
                         └───────────────────────────────────────────┘
                                                 │
                                                 ▼
                         ┌───────────────────────────────────────────┐
                         │ Key::Definition(y)                         │
                         │ Binding::NameAssign { ... }                │
                         └───────────────────────────────────────────┘
```

### 3.3 The `CurrentIdx` Struct (`lib/binding/bindings.rs`)

```rust
pub struct CurrentIdx(Usage);

impl CurrentIdx {
    pub fn decompose(self) -> (SmallSet<Idx<Key>>, Idx<Key>) {
        match self.0 {
            Usage::CurrentIdx(idx, first_used_by) => (first_used_by, idx),
            _ => unreachable!(),
        }
    }
}
```

The `first_used_by` set accumulates during expression binding. When a name
lookup records a first use (via `record_first_use`), it inserts the
`CompletedPartialType` index into this set. At the end of
`bind_single_name_assign`, if the set is non-empty, the intermediate
`PartialTypeWithUpstreamsCompleted` binding is created.

**Key insight:** The `first_used_by` set is populated via `user.decompose()`
which extracts the accumulated `SmallSet<Idx<Key>>` from `Usage::CurrentIdx`.
This set contains `CompletedPartialType` indices (NOT raw `Definition` indices),
so forcing them triggers the full pinning machinery.

## 4. First-Use Detection and Recording

### 4.1 `Usage` enum (`lib/binding/expr.rs`)

```rust
pub enum Usage {
    CurrentIdx(Idx<Key>, SmallSet<Idx<Key>>),  // Normal binding context
    Narrowing(Option<Idx<Key>>),                // Narrowing context (if, boolean ops)
    StaticTypeInformation,                      // Type annotations, casts
}
```

**Important behavioral difference:**

- `CurrentIdx`: First use can pin; returns unpinned types to first-use binding
- `Narrowing` / `StaticTypeInformation`: First use does NOT pin; returns pinned
  types immediately, marks `FirstUse::DoesNotPin`

**Note on usage propagation:** The `Usage` is now passed through uniformly to
sub-expressions, including those in narrowing contexts (if tests, boolean
operators, comprehension filters, etc.). This allows first-use tracking to work
in these sub-expressions when the outer context is `CurrentIdx`.

### 4.2 `lookup_name` (`lib/binding/bindings.rs`)

```rust
pub fn lookup_name(&mut self, name: Hashed<&Name>, usage: &mut Usage) -> NameLookupResult {
    match self.scopes.look_up_name_for_read(name) {
        NameReadInfo::Flow { idx, initialized } => {
            let (idx, first_use) = self.detect_first_use(idx, usage);
            if let Some(used_idx) = first_use {
                self.record_first_use(used_idx, usage);
            }
            // ...
        }
        // ...
    }
}
```

### 4.3 `detect_first_use` (`lib/binding/bindings.rs`)

**This is the core of the "trap" mechanism.** The logic:

1. If binding is `CompletedPartialType` with `FirstUse::Undetermined`:
   - `Usage::CurrentIdx`: Return `(unpinned_idx, Some(flow_idx))` — expose raw
     binding, record first use
   - `Usage::Narrowing`/`StaticTypeInformation`: Return
     `(flow_idx, Some(flow_idx))` — use pinned, mark `DoesNotPin`

2. If `FirstUse::UsedBy(usage_idx)` is already set:
   - If currently inside that same first-use binding: return
     `(unpinned_idx, None)` — continue exposing raw binding for consistency
   - Otherwise: return `(flow_idx, None)` — use pinned, already recorded

3. Other bindings: return `(flow_idx, None)` — no special handling

**Code detail:**

```rust
FirstUse::UsedBy(usage_idx) => {
    // Detect secondary reads of the same name from a first use
    let currently_in_first_use =
        usage.current_idx().is_some_and(|idx| &idx == usage_idx);
    if currently_in_first_use {
        (*unpinned_idx, None)  // Continue exposing raw binding
    } else {
        (flow_idx, None)       // Use pinned binding
    }
}
```

### 4.4 `record_first_use` (`lib/binding/bindings.rs`)

```rust
fn record_first_use(&mut self, used: Idx<Key>, usage: &mut Usage) {
    match self.table.types.1.get_mut(used) {
        Some(Binding::CompletedPartialType(.., first_use @ FirstUse::Undetermined)) => {
            *first_use = match usage {
                Usage::CurrentIdx(use_idx, first_uses_of) => {
                    first_uses_of.insert(used);  // Track for upstream handling
                    FirstUse::UsedBy(*use_idx)
                }
                Usage::StaticTypeInformation | Usage::Narrowing(_) => FirstUse::DoesNotPin,
            };
        }
        // ...
    }
}
```

**Key insight:** The `first_uses_of.insert(used)` call is how the information
flows back to `bind_single_name_assign` for creating
`PartialTypeWithUpstreamsCompleted`.

## 5. Solver Handling

### 5.1 The Pinning Boundary (`lib/alt/solve.rs`)

```rust
pub fn solve_binding(&self, binding: &Binding, errors: &ErrorCollector) -> Arc<TypeInfo> {
    if let Binding::Forward(fwd) = binding {
        return self.get_idx(*fwd);
    }
    let mut type_info = self.binding_to_type_info(binding, errors);
    type_info.visit_mut(&mut |ty| {
        if !matches!(
            binding,
            Binding::NameAssign { .. } | Binding::PartialTypeWithUpstreamsCompleted(..)
        ) {
            self.pin_all_placeholder_types(ty);
        }
        self.expand_vars_mut(ty);
    });
    Arc::new(type_info)
}
```

**This is perhaps the most important detail:** Pinning is SKIPPED for exactly
two binding types:

1. `Binding::NameAssign` — so the raw partial types can flow to the
   `CompletedPartialType`
2. `Binding::PartialTypeWithUpstreamsCompleted` — so the raw partial types
   (after upstream pinning) can flow to the `CompletedPartialType`

All other bindings (including `Binding::Narrow`, `Binding::Expr`, etc.) have
their placeholder types pinned automatically. This is the key safety mechanism
that prevents partial types from leaking into the broader binding graph.

### 5.2 Solving `CompletedPartialType` (`lib/alt/solve.rs`)

```rust
Binding::CompletedPartialType(unpinned_idx, first_use) => {
    // Calculate the first use for its side-effects (it might pin `Var`s)
    match first_use {
        FirstUse::UsedBy(idx) => {
            self.get_idx(*idx);  // Force evaluation of first-use binding
        }
        FirstUse::Undetermined | FirstUse::DoesNotPin => {}
    }
    self.get_idx(*unpinned_idx).arc_clone().into_ty()
}
```

**Important:** After forcing the first-use binding, we evaluate the raw
definition. Since `CompletedPartialType` is NOT in the exception list, its
result goes through `pin_all_placeholder_types`, ensuring any remaining unsolved
`Var`s are defaulted to `Any`.

### 5.3 Solving `PartialTypeWithUpstreamsCompleted` (`lib/alt/solve.rs`)

```rust
Binding::PartialTypeWithUpstreamsCompleted(raw_idx, first_used_by) => {
    // Force all of the upstream `Pin`s for which was the first use
    for idx in first_used_by {
        self.get_idx(*idx);  // Force upstream CompletedPartialTypes
    }
    self.get_idx(*raw_idx).arc_clone().into_ty()
}
```

Since this binding IS in the exception list, its result is NOT pinned — the
partial types from the current assignment can still flow through to the
enclosing `CompletedPartialType`, where they'll be pinned after first-use
evaluation.

### 5.4 `pin_placeholder_type` (`lib/solver/solver.rs`)

```rust
pub fn pin_placeholder_type(&self, var: Var) {
    let variables = self.variables.lock();
    let mut variable = variables.get_mut(var);
    match &mut *variable {
        Variable::LoopRecursive(..) | Variable::Recursive | Variable::Answer(..) => {
            // Already answered or recursive - nothing to do
        }
        Variable::Quantified(q) => {
            *variable = Variable::Answer(q.as_gradual_type());
        }
        Variable::PartialQuantified(q) => {
            *variable = Variable::Answer(default(q));  // Uses default or Any
        }
        Variable::PartialContained | Variable::Unwrap => {
            *variable = Variable::Answer(Type::any_implicit());
        }
        Variable::Parameter => {
            unreachable!("Unexpected Variable::Parameter")
        }
    }
}
```

### 5.5 Constraint-Based Resolution (`lib/solver/solver.rs`)

When a `PartialContained` variable appears in a constraint (e.g., from
`list[@0].append(int)`):

```rust
Variable::PartialContained => {
    let t1_p = t1.clone().promote_literals(self.type_order.stdlib());
    drop(v2_ref);
    variables.update(*v2, Variable::Answer(t1_p));
    Ok(())
}
```

The variable is immediately solved to the constrained type (with literal
promotion).

## 6. Partial Type Creation (`lib/alt/expr.rs`)

Partial types are created for empty containers when `infer_with_first_use` is
enabled:

**Empty list:**

```rust
self.solver().fresh_partial_contained(self.uniques).to_type()
```

**Empty set:** Same pattern

**Empty dict:** For both key and value types

The `fresh_partial_contained` function (`lib/solver/solver.rs`) creates a new
`Var` backed by `Variable::PartialContained`.

## 7. Complete Execution Flow

For `x = []; x.append(1)`:

**Binding Phase:**

1. `bind_single_name_assign("x", [])` called
2. Creates `Key::Definition(x)` -> `Binding::NameAssign` producing `list[@0]`
3. Creates `Key::CompletedPartialType(x)` ->
   `Binding::CompletedPartialType(def_idx, FirstUse::Undetermined)`
4. Scope maps `x` -> `CompletedPartialType` index

5. Processing `x.append(1)`:
   - `lookup_name("x")` called with `Usage::CurrentIdx(append_idx, {})`
   - `detect_first_use` sees `FirstUse::Undetermined`, returns
     `(def_idx, Some(pin_idx))`
   - `record_first_use` sets `FirstUse::UsedBy(append_idx)`
   - Expression binding proceeds with raw `list[@0]`

**Solve Phase:**

1. Solver requests `CompletedPartialType(x)`
2. Sees `FirstUse::UsedBy(append_idx)`, forces `append_idx` binding
3. During `append_idx` evaluation:
   - Looks up `x`, gets raw `list[@0]` (since we're inside first use)
   - Evaluates `list[@0].append(1)`
   - Constraint solving matches `@0` against `int`
   - `Variable::PartialContained` -> `Variable::Answer(int)`
4. Returns to `CompletedPartialType`, evaluates `def_idx`
5. Result is `list[int]` (since `@0` is now solved)
6. `pin_all_placeholder_types` runs (no-op since everything solved)

## 8. Limitations and Edge Cases

### 8.1 Multiple Binding Escape Paths

When the same name lookup feeds multiple bindings (e.g., narrowing creates
duplicate expressions), the "trapping" mechanism may fail to catch all escape
paths. The `Pin` binding might not intercept all uses of the raw `Var`.

### 8.2 Leakage Prevention

The `PartialTypeWithUpstreamsCompleted` binding is essential for statements like
`y = [], x`. It ensures that `x` is pinned *before* `y`'s raw value is computed,
preventing `x`'s partial variables from becoming part of `y`'s type (which would
create complex, hard-to-track dependencies).

### 8.3 StaticTypeInformation Context

When `Usage::StaticTypeInformation` is used (for type annotations, casts, etc.),
first-use tracking is disabled and `FirstUse::DoesNotPin` is recorded. This
ensures that static type contexts don't accidentally pin partial types.

## 9. Key Invariants

1. **Only `NameAssign` and `PartialTypeWithUpstreamsCompleted` can produce
   unpinned partial types** — all other bindings have `pin_all_placeholder_types`
   applied

2. **`PartialTypeWithUpstreamsCompleted` forces upstream `CompletedPartialType`
   indices** — NOT raw `Definition` indices; this ensures the full pinning
   machinery runs

3. **`CompletedPartialType` forces first-use binding BEFORE evaluating raw
   definition** — this ensures constraint-based pinning happens first

4. **The `first_uses_of` set in `Usage::CurrentIdx` accumulates
   `CompletedPartialType` indices** — enabling proper upstream tracking

5. **Pinning is idempotent** — already-solved `Variable::Answer` types are
   unaffected by `pin_placeholder_type`

6. **`Usage` propagates uniformly through sub-expressions** — including those in
   narrowing contexts (if tests, boolean operators, comprehension filters),
   enabling first-use tracking in these locations when the outer context is
   `CurrentIdx`

## 10. Summary

Pyrefly's partial type inference relies on a specific cooperation between:

1. **Binding Construction:** Creating a hidden "Raw" node and a public "Pin"
   node.
2. **Lookup Logic:** Exposing the Raw node *only* to the first valid consumer.
3. **Solver Logic:** Enforcing `First Use -> Raw -> Pin` ordering and
   selectively applying `pin_all_placeholder_types`.
4. **Usage Propagation:** Passing `Usage` uniformly through all sub-expressions,
   allowing first-use tracking to work in narrowing contexts.

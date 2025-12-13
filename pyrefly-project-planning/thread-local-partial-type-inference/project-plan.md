# Thread-Local Partial Type Inference: Final Implementation Plan

This document is a consolidation of three junior engineer
proposals for refactoring Pyrefly's partial type inference system.


It describes re-wiring the current approach to partial type inference
(which is separately discussed in ./graph-based-partial-type-inference.md)
in terms of thread local storage (the implementation of which is described
in ./thread-local-answers-solver-storage.md).

## 1. Executive Summary

### 1.1 Current State

Pyrefly uses a "trap" pattern with **2-3 binding nodes per name assignment** to
prevent partial types (e.g., `list[@0]` from `x = []`) from escaping before
being pinned by their first downstream use.

**Current binding structure:**

1. `Key::Definition` → `Binding::NameAssign` (raw, unpinned)
2. `Key::PartialTypeWithUpstreamsCompleted` → `Binding::PartialTypeWithUpstreamsCompleted`
   (optional, when assignment uses other partial types)
3. `Key::CompletedPartialType` → `Binding::CompletedPartialType` (public face,
   stores `FirstUse` state)

**Key files and line numbers (verified):**

- `FirstUse` enum: `lib/binding/binding.rs:1258-1267`
- `Binding::NameAssign`: `lib/binding/binding.rs:1359-1365`
- `Binding::CompletedPartialType`: `lib/binding/binding.rs:1399-1425`
- `Binding::PartialTypeWithUpstreamsCompleted`: `lib/binding/binding.rs:1426-1443`
- `bind_single_name_assign`: `lib/binding/target.rs:432-499`
- `detect_first_use`: `lib/binding/bindings.rs:972-1012`
- `record_first_use`: `lib/binding/bindings.rs:1015-1030`
- Pinning bypass in `solve_binding`: `lib/alt/solve.rs:1500-1505`
- `PreliminaryAnswers`: `lib/alt/answers_solver.rs:377-473`

### 1.2 Proposed State

Replace the multi-node graph structure with:

1. **Single `NameAssign` binding** with embedded `first_use: Option<Idx<Key>>` field
2. **Thread-local storage** (`PreliminaryAnswers`) for raw results containing
   partial `Var`s
3. **Eager first-use chaining** during solving to trigger constraint resolution
4. **Batch pinning and commit** when chain ends

**Benefits:**

- Reduces binding complexity: 1 node instead of 2-3 per assignment
- Explicit control flow instead of implicit graph ordering
- Reuses existing `PreliminaryAnswers` infrastructure (currently marked dead code)
- Easier debugging and reasoning

## 2. Architecture Overview

### 2.1 Current Flow (Trapping)

```
Scope looks up "x"
        │
        ▼
CompletedPartialType(x) ──forces──▶ FirstUse binding
        │                                  │
        │                            (constrains Var)
        ▼                                  │
PartialTypeWithUpstreamsCompleted(x)       │ (optional)
        │                                  │
        ▼                                  │
Definition(x) ◀────────────────────────────┘
        │
        ▼
list[@0] ──pin──▶ list[int] or list[Any]
```

### 2.2 Proposed Flow (Thread-Local Eager)

```
Solve NameAssign(x)
        │
        ▼
Compute raw type: list[@0]
        │
        ▼
Has partial Vars? ──no──▶ Return immediately (fast path)
        │
       yes
        │
        ▼
Store in thread-local preliminary answers
        │
        ▼
Has first_use? ──no──▶ Force vars, commit to global
        │
       yes
        │
        ▼
get_idx(first_use_idx) ──recurses if also partial──▶ ...
        │
        ▼
Chain ends → Force all partial Vars → Commit to global
```

## 3. Detailed Implementation

### 3.1 Binding Phase Changes

#### 3.1.1 Modify `Binding::NameAssign`

**File:** `lib/binding/binding.rs:1359-1365`

```rust
// Current:
NameAssign {
    name: Name,
    annotation: Option<(AnnotationStyle, Idx<KeyAnnotation>)>,
    expr: Box<Expr>,
    legacy_tparams: Option<Box<[Idx<KeyLegacyTypeParam>]>>,
    is_in_function_scope: bool,
}

// Proposed:
NameAssign {
    name: Name,
    annotation: Option<(AnnotationStyle, Idx<KeyAnnotation>)>,
    expr: Box<Expr>,
    legacy_tparams: Option<Box<[Idx<KeyLegacyTypeParam>]>>,
    is_in_function_scope: bool,
    first_use: Option<Idx<Key>>,  // NEW: initially None
}
```

**Note:** No `Cell` or `RefCell` is needed. During the binding phase,
`BindingsBuilder` has `&mut self` and can call `table.types.1.get_mut(idx)` to
get a mutable reference—this is exactly how the current `record_first_use`
mutates `CompletedPartialType` bindings.

#### 3.1.2 Simplify `bind_single_name_assign`

**File:** `lib/binding/target.rs:432-499`

```rust
pub fn bind_single_name_assign(
    &mut self,
    name: &Identifier,
    mut value: Box<Expr>,
    direct_ann: Option<(&Expr, Idx<KeyAnnotation>)>,
) -> Option<Idx<KeyAnnotation>> {
    let identifier = ShortIdentifier::new(name);

    // Create CurrentIdx for the Definition directly
    let mut user = self.declare_current_idx(Key::Definition(identifier));

    // ... existing type alias detection and ensure_expr logic (unchanged) ...

    let style = if self.scopes.in_class_body() {
        FlowStyle::ClassField { initial_value: Some((*value).clone()) }
    } else {
        self.scopes.register_variable(name);
        FlowStyle::Other
    };

    // NEW: Scope maps directly to Definition key (not CompletedPartialType)
    let (_, def_idx) = user.decompose();
    let canonical_ann = self.bind_name(&name.id, def_idx, style);

    let ann = match direct_ann {
        Some((_, idx)) => Some((AnnotationStyle::Direct, idx)),
        None => canonical_ann.map(|idx| (AnnotationStyle::Forwarded, idx)),
    };

    let binding = Binding::NameAssign {
        name: name.id.clone(),
        annotation: ann,
        expr: value,
        legacy_tparams: tparams,
        is_in_function_scope: self.scopes.in_function_scope(),
        first_use: None,  // NEW: initialized as None
    };

    self.insert_binding_idx(def_idx, binding);

    // REMOVED: CompletedPartialType and PartialTypeWithUpstreamsCompleted creation

    canonical_ann
}
```

#### 3.1.3 Simplify First-Use Recording

**File:** `lib/binding/bindings.rs`

Replace `detect_first_use` (lines 972-1012) and `record_first_use` (lines 1015-1030)
with a simpler function:

```rust
pub fn lookup_name(&mut self, name: Hashed<&Name>, usage: &mut Usage) -> NameLookupResult {
    match self.scopes.look_up_name_for_read(name) {
        NameReadInfo::Flow { idx, initialized } => {
            // NEW: Record first-use directly if applicable
            self.maybe_record_first_use(idx, usage);
            self.scopes.mark_parameter_used(name.key());
            self.scopes.mark_import_used(name.key());
            self.scopes.mark_variable_used(name.key());
            NameLookupResult::Found { idx, initialized }
        }
        // ... other cases unchanged
    }
}

/// Simplified first-use recording. Replaces detect_first_use + record_first_use.
fn maybe_record_first_use(&mut self, target_idx: Idx<Key>, usage: &Usage) {
    // Only record for CurrentIdx usage (not Narrowing or StaticTypeInformation)
    let Usage::CurrentIdx(use_idx, _) = usage else {
        return;
    };

    // Only NameAssign bindings can have first uses
    let Some(Binding::NameAssign { first_use, .. }) = self.table.types.1.get_mut(target_idx)
    else {
        return;
    };

    // Only record if first_use is currently None
    if first_use.is_none() {
        *first_use = Some(*use_idx);
    }
}
```

**Key difference from current code:** The current `detect_first_use` returns
different indices depending on context (sometimes unpinned, sometimes pinned).
With the new design, we always return the same `Definition` index; the solver
handles thread-local vs global distinction.

#### 3.1.4 Simplify `Usage` Enum (Phase 2)

**File:** `lib/binding/expr.rs:73-90`

The `first_uses_of` set in `Usage::CurrentIdx` was used to create
`PartialTypeWithUpstreamsCompleted`. With thread-local storage, this tracking
becomes unnecessary—upstream dependencies are handled implicitly through
`get_idx` calls.

```rust
// Current (line 75):
CurrentIdx(Idx<Key>, SmallSet<Idx<Key>>),  // idx + first_uses_of set

// Proposed (after verifying no other uses):
CurrentIdx(Idx<Key>),  // Just the current binding index
```

**Caveat:** Before removing `first_uses_of`, verify it's not used for other
purposes. Search for all callers of `user.decompose()` in the codebase.

### 3.2 Solver Phase Changes

#### 3.2.1 The Critical Challenge: Passing Binding Index to Solver

The `Solve` trait (`lib/alt/traits.rs:81-89`) currently does NOT pass the
binding index to the `solve` method:

```rust
pub trait Solve<Ans: LookupAnswer>: Keyed {
    fn solve(
        answers: &AnswersSolver<Ans>,
        binding: &Self::Value,
        errors: &ErrorCollector,
    ) -> Arc<Self::Answer>;
    // ...
}
```

However, `calculate_and_record_answer` (`lib/alt/answers_solver.rs:682-697`)
has access to `idx`:

```rust
fn calculate_and_record_answer<K: Solve<Ans>>(
    &self,
    current: CalcId,
    idx: Idx<K>,  // <-- Available here
    calculation: &Calculation<Arc<K::Answer>, Var>,
) -> Arc<K::Answer> {
    let binding = self.bindings().get(idx);
    let answer = calculation
        .record_value(K::solve(self, binding, self.base_errors), |var, answer| {
            // ...
        });
    // ...
}
```

**Recommended approach:** Modify the `Solve` trait to accept `idx`:

```rust
pub trait Solve<Ans: LookupAnswer>: Keyed {
    fn solve(
        answers: &AnswersSolver<Ans>,
        idx: Idx<Self>,  // NEW parameter
        binding: &Self::Value,
        errors: &ErrorCollector,
    ) -> Arc<Self::Answer>;
    // ...
}
```

This requires updating all ~20+ implementations of `Solve`. Most implementations
will simply ignore the new `idx` parameter. Only `impl Solve for Key` will use
it, passing it to `solve_binding`.

#### 3.2.2 Modify `solve_binding`

**File:** `lib/alt/solve.rs:1493-1509`

```rust
// Current signature:
pub fn solve_binding(&self, binding: &Binding, errors: &ErrorCollector) -> Arc<TypeInfo>

// Proposed signature:
pub fn solve_binding(
    &self,
    idx: Idx<Key>,  // NEW
    binding: &Binding,
    errors: &ErrorCollector,
) -> Arc<TypeInfo> {
    // Special case for forward
    if let Binding::Forward(fwd) = binding {
        return self.get_idx(*fwd);
    }

    // Special handling for NameAssign
    if let Binding::NameAssign { first_use, .. } = binding {
        return self.solve_name_assign(idx, binding, *first_use, errors);
    }

    // All other bindings: compute and pin uniformly
    let mut type_info = self.binding_to_type_info(binding, errors);
    type_info.visit_mut(&mut |ty| {
        self.pin_all_placeholder_types(ty);
        self.expand_vars_mut(ty);
    });
    Arc::new(type_info)
}
```

**Note:** Remove the selective pinning bypass. All bindings now get pinned
uniformly except `NameAssign`, which handles its own pinning via thread-local
storage.

#### 3.2.3 New `solve_name_assign` Method

**File:** `lib/alt/solve.rs` (new method)

```rust
fn solve_name_assign(
    &self,
    idx: Idx<Key>,
    binding: &Binding,
    first_use: Option<Idx<Key>>,
    errors: &ErrorCollector,
) -> Arc<TypeInfo> {
    // Step 1: Compute raw type (may contain partial Vars)
    let mut raw_type_info = self.binding_to_type_info(binding, errors);

    // Step 2: Check if we have partial Vars (fast path)
    if !self.has_partial_vars(&raw_type_info) {
        raw_type_info.visit_mut(&mut |ty| {
            self.pin_all_placeholder_types(ty);
            self.expand_vars_mut(ty);
        });
        return Arc::new(raw_type_info);
    }

    // Step 3: Store raw result in thread-local storage
    self.thread_state.preliminary_answers.record_answer(
        self.module(),
        idx,
        Arc::new(raw_type_info.clone()),
    );

    // Step 4: Chase first-use chain (this triggers constraint solving)
    if let Some(first_use_idx) = first_use {
        self.get_idx(first_use_idx);
    }

    // Step 5: Force remaining partial Vars and commit to global
    self.force_and_commit_preliminary();

    // Step 6: Re-read the (now pinned) result and return
    let mut final_type_info = raw_type_info;
    final_type_info.visit_mut(&mut |ty| {
        self.expand_vars_mut(ty);  // Vars should now be Answer(...)
    });
    Arc::new(final_type_info)
}
```

#### 3.2.4 Helper Methods

**File:** `lib/alt/solve.rs` (new methods)

```rust
impl<'a, Ans: LookupAnswer> AnswersSolver<'a, Ans> {
    /// Check if a TypeInfo contains any partial (unsolved) Vars.
    fn has_partial_vars(&self, type_info: &TypeInfo) -> bool {
        let mut has_partial = false;
        type_info.visit(&mut |ty| {
            if let Type::Var(var) = ty {
                let variables = self.solver().variables.lock();
                if matches!(
                    *variables.get(*var),
                    Variable::PartialContained | Variable::PartialQuantified(_)
                ) {
                    has_partial = true;
                }
            }
        });
        has_partial
    }

    /// Force all partial Vars in preliminary storage to their defaults.
    fn force_partial_vars_in_preliminary(&self) {
        let preliminary = self.thread_state.preliminary_answers.0.borrow();
        if let Some(ref map) = *preliminary {
            let mut vars_to_pin = Vec::new();
            for (_module, table) in map.iter() {
                // Collect all Vars from all TypeInfo answers
                if let Some(key_table) = table.get::<Key>() {
                    for (_idx, entry) in key_table.iter() {
                        if let Either::Left(answer) = entry {
                            answer.visit(&mut |ty| {
                                if let Type::Var(var) = ty {
                                    vars_to_pin.push(*var);
                                }
                            });
                        }
                    }
                }
            }
            drop(preliminary);  // Release borrow before pinning
            for var in vars_to_pin {
                self.solver().pin_placeholder_type(var);
            }
        }
    }

    /// Commit all preliminary answers to global storage.
    fn commit_preliminary_to_global(&self) {
        let preliminary = self.thread_state
            .preliminary_answers
            .0
            .borrow_mut()
            .take()
            .unwrap_or_default();

        for (module_info, table) in preliminary {
            if let Some(key_table) = table.get::<Key>() {
                for (idx, entry) in key_table.iter() {
                    if let Either::Left(answer) = entry {
                        // Expand vars (should now all be Answer(...))
                        let mut final_answer = (*answer).clone();
                        final_answer.visit_mut(&mut |ty| {
                            self.expand_vars_mut(ty);
                        });
                        // Write to global answers
                        // Note: May need transaction API depending on exact Answers interface
                        self.current.set_idx(idx, Arc::new(final_answer));
                    }
                }
            }
        }
    }

    /// Combined force + commit operation.
    fn force_and_commit_preliminary(&self) {
        self.force_partial_vars_in_preliminary();
        self.commit_preliminary_to_global();
    }
}
```

#### 3.2.5 Integration with `get_preliminary`

The existing `get_idx` method (`lib/alt/answers_solver.rs:612-676`) already
checks `get_preliminary` at line 619:

```rust
pub fn get_idx<K: Solve<Ans>>(&self, idx: Idx<K>) -> Arc<K::Answer> {
    // ...
    if let Some(result) = self.get_preliminary(idx) {
        return result;
    }
    // ...
}
```

This ensures that when `x.append(1)` looks up `x`, it sees the raw `list[@0]`
from thread-local storage, allowing constraint solving to pin `@0` to `int`.

### 3.3 Components to Remove

#### 3.3.1 Key Variants

**File:** `lib/binding/binding.rs`

Remove:
- `Key::CompletedPartialType(ShortIdentifier)` (lines 388-390)
- `Key::PartialTypeWithUpstreamsCompleted(ShortIdentifier)` (lines 393-394)

Update related `impl` blocks:
- `Ranged` impl (lines 457-458)
- `DisplayWith<ModuleInfo>` impl

#### 3.3.2 Binding Variants

**File:** `lib/binding/binding.rs`

Remove:
- `Binding::CompletedPartialType(Idx<Key>, FirstUse)` (lines 1399-1425)
- `Binding::PartialTypeWithUpstreamsCompleted(Idx<Key>, Box<[Idx<Key>]>)` (lines 1426-1443)

#### 3.3.3 `FirstUse` Enum

**File:** `lib/binding/binding.rs:1257-1267`

Remove the entire `FirstUse` enum.

#### 3.3.4 Functions to Remove/Simplify

**File:** `lib/binding/bindings.rs`
- Remove `detect_first_use` (lines 972-1012)
- Remove `record_first_use` (lines 1015-1030)

**File:** `lib/alt/solve.rs`
- Remove `Binding::CompletedPartialType` match arm (lines 2656-2665)
- Remove `Binding::PartialTypeWithUpstreamsCompleted` match arm (lines 2666-2673)

## 4. Edge Cases

### 4.1 No First Use

```python
x = []  # No usage of x
# Result: x is list[Any]
```

**Flow:**
1. `solve_name_assign` computes `list[@0]`, stores in preliminary
2. `first_use` is `None`, skip chasing
3. `force_partial_vars_in_preliminary()` pins `@0` → `Any`
4. Commits `list[Any]`

### 4.2 Static Type / Narrowing Context

```python
x = []
if x:  # Narrowing context
    pass
# x is list[Any]
```

**Flow:**
1. Lookup uses `Usage::Narrowing(_)`
2. `maybe_record_first_use` skips for non-`CurrentIdx`
3. `first_use` remains `None`
4. Pins to `Any`

### 4.3 Chained Partial Types

```python
x = []
y = [x]      # y's assignment is first use of x
y[0].append(1)
```

**Flow during solving:**
1. Solver hits `x`. Computes `list[@0]`. Stores in preliminary.
2. `x` chases `y`. Calls `get_idx(y)`.
3. Solver hits `y`.
4. `y` looks up `x`. `get_idx(x)` sees `list[@0]` in preliminary.
5. `y` computes `list[list[@0]]` (sharing same `@0`!). Stores in preliminary.
6. `y` chases `append`. Calls `get_idx(append)`.
7. `append` looks up `y`. Sees `list[list[@0]]`. Constrains `@0` to `int`.
8. `y` finishes chasing. Calls `force_and_commit_preliminary`.
9. `force_and_commit` pins both `x` (`list[int]`) and `y` (`list[list[int]]`).
10. `x` finishes—preliminary already committed.

**Result:** `x: list[int]`, `y: list[list[int]]`. Correct.

### 4.4 Multiple Reads in First Use

```python
x = []
y = x + x  # Both reads of x get the same raw list[@0]
y.append(1)
```

**Flow:**
1. First `x` lookup: sets `x.first_use = Some(y_idx)`
2. Second `x` lookup: `first_use` already set, no change
3. Both lookups call `get_idx(x)` → hit `get_preliminary` → consistent `list[@0]`

### 4.5 Cross-Module First-Uses

```python
# module_a.py
x = []

# module_b.py
from module_a import x
x.append(1)
```

Thread-local storage is keyed by `ModuleInfo`, so chains work across modules.
`commit_preliminary_to_global` writes each answer to the appropriate module's
`Answers`.

## 5. Implementation Plan

### Phase 1: Infrastructure (Non-Breaking)

**Goal:** Add new fields/methods without changing behavior.

1. Add `first_use: Option<Idx<Key>>` to `Binding::NameAssign`
   - Initialize to `None` in all construction sites
   - This is a no-op—the field exists but isn't used yet

2. Add helper methods to `AnswersSolver`:
   - `has_partial_vars`
   - `force_partial_vars_in_preliminary`
   - `commit_preliminary_to_global`
   - `force_and_commit_preliminary`

3. Remove `#[expect(dead_code)]` from `PreliminaryAnswers` methods

4. Implement `maybe_record_first_use` in `BindingsBuilder`
   - Initially call it alongside existing `detect_first_use` logic

5. Verify compilation: All tests pass (no behavior changes)

### Phase 2: Wire Up First-Use Recording

**Goal:** Make binding phase populate `first_use` field.

1. Modify `lookup_name` to call `maybe_record_first_use`
2. Add debug logging to verify correct first-use detection
3. Run tests, verify logging shows correct patterns

### Phase 3: Modify Solve Trait (Feature-Flagged)

**Goal:** Enable passing index to solver.

1. Modify `Solve` trait to accept `idx: Idx<Self>` parameter
2. Update all ~20+ implementations (most will ignore the new parameter)
3. Modify `calculate_and_record_answer` to pass `idx` to `K::solve`
4. Modify `solve_binding` to accept `idx`
5. Add feature flag for new solver path:
   ```rust
   #[cfg(feature = "thread_local_partial")]
   ```

### Phase 4: Enable New Solver Path

**Goal:** Switch to thread-local solver behavior.

1. Implement `solve_name_assign` with thread-local storage
2. Modify `get_idx` integration with preliminary storage
3. Run all tests with flag enabled, fix any regressions
4. Remove feature flag once stable

### Phase 5: Remove Old Infrastructure

**Goal:** Delete obsolete code.

1. Update `bind_single_name_assign` to create only one binding
2. Update scope mapping to use `Key::Definition` directly
3. Remove `Key::CompletedPartialType` and `Key::PartialTypeWithUpstreamsCompleted`
4. Remove corresponding `Binding` variants
5. Remove `FirstUse` enum
6. Remove `detect_first_use` and `record_first_use`
7. Simplify `Usage` enum (remove `first_uses_of` set) after verifying no other uses

### Phase 6: Testing and Validation

1. Run existing partial type inference tests
2. Add new tests for:
   - No first use → defaults to `Any`
   - Cross-module first-use
   - Chained first-uses
   - Multiple reads in first-use expression
   - Narrowing/static contexts don't record first-use
3. Validate no regressions in conformance tests
4. Performance benchmarking: measure memory and time impact

## 6. Key Invariants

1. **Partial `Var`s stay thread-local:** Raw results with partial `Var`s are
   stored only in `PreliminaryAnswers`, never directly in global `Answers`.

2. **Force before commit:** All partial `Var`s are forced (pinned) before
   committing to global storage.

3. **First-use chasing is bounded:** The chain terminates when we hit a binding
   with no `first_use` set, or when the first-use binding doesn't produce
   partial types.

4. **Lookup sees preliminary:** `get_preliminary` ensures that lookups during
   first-use resolution see the raw (unpinned) types, allowing constraint
   solving to work.

5. **Mutation is controlled:** The `first_use` field on `NameAssign` is mutated
   during binding phase only, before solving begins.

6. **Shared `Var` objects:** Chained partial types share the same underlying
   `Var` objects, so solving one affects all.

## 7. Risks and Mitigations

### 7.1 Performance

**Risk:** Thread-local storage lookups may add overhead.

**Mitigation:**
- `PreliminaryAnswers` uses `Option` wrapper for fast path when empty
- Most bindings don't have partial types, so fast path dominates
- Benchmark before/after on real codebases

### 7.2 Error Handling

**Risk:** Preliminary storage may not be committed on errors.

**Mitigation:** Use RAII guard pattern:
```rust
let _guard = scopeguard::guard((), |_| {
    self.force_and_commit_preliminary();
});
```

### 7.3 Incremental Re-checking

**Risk:** Fewer binding nodes may affect incremental caching.

**Mitigation:** Verify cache invalidation behavior is unchanged. The mapping
from source location to binding should be simpler, potentially improving
incrementality.

### 7.4 Debug Tooling

**Risk:** Thread-local storage is less visible in debug output.

**Mitigation:** Add tracing for thread-local storage operations.

## 8. Success Criteria

- [ ] All existing partial type inference tests pass
- [ ] No regressions in conformance tests
- [ ] Performance within 5% of current implementation
- [ ] Reduced code size (fewer binding types, simpler logic)
- [ ] Improved maintainability (team consensus)

# Deferred BoundName Implementation Plan

## Overview

This document provides a step-by-step implementation plan for deferring `BoundName` binding creation in Pyrefly. This change enables partial type inference to work correctly in loops where variables are not reassigned.

**Goal**: Enable code like this to correctly infer `x: list[int]`:
```python
x = []
for i in range(5):
    x.append(i)  # Currently fails to infer; should work after this change
```

**Root Cause**: `BoundName` bindings are created **during** loop body traversal, but loop phi bindings aren't filled in **until after** the loop. When we look up `x` inside the loop, `detect_first_use` sees an empty phi node and fails to recognize the first-use opportunity.

**Solution**: Separate the scope lookup (which must happen during traversal) from binding creation and first-use detection (which should happen after all phi nodes are populated).

---

## Phase 1: Data Structures

### Step 1.1: Define `DeferredBoundName` struct

**Location**: `pyrefly/lib/binding/bindings.rs` (add near line 180, before `BindingsBuilder`)

```rust
/// Information needed to create a BoundName binding after AST traversal.
///
/// During traversal, we record the lookup result without creating the binding.
/// After traversal (when all phi nodes are populated), we process these to
/// create the actual bindings and correctly detect first-use opportunities.
#[derive(Debug)]
struct DeferredBoundName {
    /// The reserved Idx for the Key::BoundName we will create
    bound_name_idx: Idx<Key>,
    /// The flow key that the lookup resolved to (may be a phi that forwards elsewhere)
    flow_target_idx: Idx<Key>,
    /// The current binding idx at the time of lookup (for first-use tracking)
    current_binding_idx: Option<Idx<Key>>,
    /// Whether this lookup was in a narrowing context (does not pin)
    is_narrowing: bool,
    /// Whether this lookup was in a static type context (does not pin)
    is_static_type: bool,
}
```

**Why this structure**:
- We store the essential information from `Usage` rather than `Usage` itself (which doesn't derive `Clone`)
- The `flow_target_idx` is what `lookup_name` returned - we'll follow this chain at finalization
- We need the usage context to correctly handle first-use detection later

### Step 1.2: Add field to `BindingsBuilder`

**Location**: `pyrefly/lib/binding/bindings.rs`, in the `BindingsBuilder` struct (around line 184-200)

Add this field:
```rust
pub struct BindingsBuilder<'a> {
    // ... existing fields ...

    /// BoundName lookups deferred until after AST traversal
    deferred_bound_names: Vec<DeferredBoundName>,

    // ... rest of fields ...
}
```

Update initialization in `Bindings::new()` (around line 388):
```rust
let mut builder = BindingsBuilder {
    // ... existing field initializations ...
    deferred_bound_names: Vec::new(),
    // ...
};
```

---

## Phase 2: Refactor `lookup_name` to Support Deferred First-Use

The key insight is that we need to split `lookup_name` into two parts:
1. **Scope lookup + marking used** (must happen during traversal)
2. **First-use detection** (should happen after traversal)

### Step 2.1: Create `lookup_name_without_first_use`

**Location**: `pyrefly/lib/binding/bindings.rs` (around line 864-896)

Add a new method that performs lookup without first-use detection:

```rust
/// Look up a name in scope, marking it as used, but without first-use detection.
///
/// This is used for deferred BoundName creation where first-use detection
/// happens after AST traversal when all phi nodes are populated.
fn lookup_name_without_first_use(&mut self, name: Hashed<&Name>) -> NameLookupResult {
    match self.scopes.look_up_name_for_read(name) {
        NameReadInfo::Flow { idx, initialized } => {
            // Mark as used (this must happen during traversal for unused-variable detection)
            self.scopes.mark_parameter_used(name.key());
            self.scopes.mark_import_used(name.key());
            self.scopes.mark_variable_used(name.key());
            NameLookupResult::Found { idx, initialized }
        }
        NameReadInfo::Anywhere { key, initialized } => {
            self.scopes.mark_parameter_used(name.key());
            self.scopes.mark_import_used(name.key());
            self.scopes.mark_variable_used(name.key());
            NameLookupResult::Found {
                idx: self.table.types.0.insert(key),
                initialized,
            }
        }
        NameReadInfo::NotFound => NameLookupResult::NotFound,
    }
}
```

**Why**: The existing `lookup_name` calls `detect_first_use` and `record_first_use`. We need a version that skips this for deferred bindings.

---

## Phase 3: Modify `ensure_name_impl` to Defer Binding Creation

**Location**: `pyrefly/lib/binding/expr.rs` (lines 302-378)

### Step 3.1: Update `ensure_name_impl` for normal flow lookups

The current code (simplified):
```rust
fn ensure_name_impl(&mut self, name: &Identifier, usage: &mut Usage, ...) -> Idx<Key> {
    let key = Key::BoundName(ShortIdentifier::new(name));
    // ... empty name check ...
    let lookup_result = self.lookup_name(Hashed::new(&name.id), usage);
    match lookup_result {
        NameLookupResult::Found { idx: value, .. } => {
            self.insert_binding(key, Binding::Forward(value))  // EAGER - change this
        }
        NameLookupResult::NotFound => { /* error handling */ }
    }
}
```

**New approach**:
```rust
fn ensure_name_impl(&mut self, name: &Identifier, usage: &mut Usage, ...) -> Idx<Key> {
    let key = Key::BoundName(ShortIdentifier::new(name));

    if name.is_empty() {
        // Error recovery case - keep immediate binding
        return self.insert_binding_overwrite(key, Binding::Type(Type::any_error()));
    }

    let used_in_static_type = matches!(usage, Usage::StaticTypeInformation);
    let is_narrowing = matches!(usage, Usage::Narrowing(_));

    // Handle legacy type parameter lookups (keep synchronous for now)
    if used_in_static_type && let Some((tparams_collector, tparam_id)) = tparams_lookup {
        let lookup_result = self.intercept_lookup(tparams_collector, tparam_id);
        return match lookup_result {
            NameLookupResult::Found { idx: value, initialized } => {
                // Check uninitialized error
                // ...existing error handling...
                self.insert_binding(key, Binding::Forward(value))
            }
            NameLookupResult::NotFound => {
                // ...existing not-found handling...
            }
        };
    }

    // Normal case: defer the binding creation
    let lookup_result = self.lookup_name_without_first_use(Hashed::new(&name.id));

    match lookup_result {
        NameLookupResult::Found { idx: flow_target_idx, initialized } => {
            // Check uninitialized error (still needs to happen during traversal)
            if !used_in_static_type
                && !self.module_info.path().is_interface()
                && let Some(error_message) = initialized.as_error_message(&name.id)
            {
                self.error(name.range, ErrorInfo::Kind(ErrorKind::UnboundName), error_message);
            }

            // Reserve an idx for the BoundName without creating the binding
            let bound_name_idx = self.idx_for_promise(key);

            // Record for deferred processing
            self.deferred_bound_names.push(DeferredBoundName {
                bound_name_idx,
                flow_target_idx,
                current_binding_idx: usage.current_idx(),
                is_narrowing,
                is_static_type: used_in_static_type,
            });

            bound_name_idx
        }
        NameLookupResult::NotFound => {
            // Error case - create binding immediately (no deferral needed)
            // ...existing not-found handling...
        }
    }
}
```

**Key changes**:
1. Use `idx_for_promise` to reserve an index without creating the binding
2. Store the lookup result in `deferred_bound_names`
3. Return the reserved index (callers don't need to change)
4. Keep `LegacyTParamCollector` handling synchronous to avoid complexity
5. Keep error cases (`NotFound`) synchronous since they don't benefit from deferral

---

## Phase 4: Process Deferred Bindings After Traversal

### Step 4.1: Add `process_deferred_bound_names` method

**Location**: `pyrefly/lib/binding/bindings.rs`

Add this method to `BindingsBuilder`:

```rust
/// Process all deferred BoundName bindings after AST traversal.
///
/// At this point, all phi nodes are populated, so we can correctly
/// follow Forward chains and detect first-use opportunities.
fn process_deferred_bound_names(&mut self) {
    // Take the deferred bindings to avoid borrow issues
    let deferred = std::mem::take(&mut self.deferred_bound_names);

    for binding in deferred {
        self.finalize_bound_name(binding);
    }
}

/// Finalize a single deferred BoundName binding.
fn finalize_bound_name(&mut self, deferred: DeferredBoundName) {
    // Follow Forward chains to find the actual binding
    let (final_idx, partial_type_idx) = self.follow_to_partial_type(deferred.flow_target_idx);

    // Determine if this is a first-use opportunity
    let should_record_first_use = partial_type_idx.is_some()
        && !deferred.is_narrowing
        && !deferred.is_static_type;

    if let Some(pt_idx) = partial_type_idx {
        if should_record_first_use {
            // This is a first-use! Update the CompletedPartialType
            self.mark_first_use(pt_idx, deferred.bound_name_idx);
        } else if deferred.is_narrowing || deferred.is_static_type {
            // Non-pinning context: mark as DoesNotPin
            self.mark_does_not_pin(pt_idx);
        }
    }

    // Create the actual binding
    self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(final_idx));
}

/// Follow Forward chains to find a CompletedPartialType with Undetermined first-use.
/// Returns (idx_to_forward_to, Some(partial_type_idx)) if found, or (original_idx, None).
fn follow_to_partial_type(&self, start_idx: Idx<Key>) -> (Idx<Key>, Option<Idx<Key>>) {
    let mut current = start_idx;
    let mut seen = SmallSet::new();

    loop {
        if seen.contains(&current) {
            // Cycle detected - bail out
            return (start_idx, None);
        }
        seen.insert(current);

        match self.table.types.1.get(current) {
            Some(Binding::Forward(target)) => {
                current = *target;
            }
            Some(Binding::CompletedPartialType(unpinned_idx, FirstUse::Undetermined)) => {
                // Found it! Return the unpinned idx for inference
                return (*unpinned_idx, Some(current));
            }
            Some(Binding::CompletedPartialType(_, FirstUse::UsedBy(_))) => {
                // Already pinned by something else
                return (current, None);
            }
            Some(Binding::CompletedPartialType(_, FirstUse::DoesNotPin)) => {
                // Already marked as non-pinning
                return (current, None);
            }
            _ => {
                // Not a forward, not a partial type - done
                return (current, None);
            }
        }
    }
}

/// Mark a CompletedPartialType as used by a specific binding.
fn mark_first_use(&mut self, partial_type_idx: Idx<Key>, user_idx: Idx<Key>) {
    if let Some(Binding::CompletedPartialType(_, first_use)) =
        self.table.types.1.get_mut(partial_type_idx)
    {
        *first_use = FirstUse::UsedBy(user_idx);
    }
}

/// Mark a CompletedPartialType as DoesNotPin.
fn mark_does_not_pin(&mut self, partial_type_idx: Idx<Key>) {
    if let Some(Binding::CompletedPartialType(_, first_use)) =
        self.table.types.1.get_mut(partial_type_idx)
    {
        if matches!(first_use, FirstUse::Undetermined) {
            *first_use = FirstUse::DoesNotPin;
        }
    }
}
```

### Step 4.2: Call `process_deferred_bound_names` in `Bindings::new`

**Location**: `pyrefly/lib/binding/bindings.rs`, in `Bindings::new()` (around line 413)

Add the call after AST traversal but before export processing:

```rust
pub fn new(...) -> Self {
    let mut builder = BindingsBuilder { /* ... */ };
    builder.init_static_scope(&x.body, true);
    // ... builtins injection ...
    builder.stmts(x.body, &NestingContext::toplevel());
    assert_eq!(builder.scopes.loop_depth(), 0);

    // NEW: Process deferred BoundName bindings now that all phis are populated
    builder.process_deferred_bound_names();

    // ... rest of the function (export validation, etc.) ...
}
```

**Why this location**: At this point:
- All statements have been traversed (`stmts` is complete)
- All loop phis have been filled in (verified by the `loop_depth() == 0` assertion)
- The scope trace hasn't been finalized yet, which is fine

---

## Phase 5: Handle Multiple First-Uses (Compound Bindings)

The original proposal mentions a determinism concern with compound bindings like:
```python
x = []
x.append(1) if len(x) == 0 else (w := x.append("foo"))
```

For V0, we take a conservative approach: if the same `CompletedPartialType` could be pinned by multiple bindings, disable first-use inference.

### Step 5.1: Track potential first-uses before committing

Update `finalize_bound_name` to check for already-pinned state:

```rust
fn finalize_bound_name(&mut self, deferred: DeferredBoundName) {
    let (final_idx, partial_type_idx) = self.follow_to_partial_type(deferred.flow_target_idx);

    if let Some(pt_idx) = partial_type_idx {
        if deferred.is_narrowing || deferred.is_static_type {
            // Non-pinning context
            self.mark_does_not_pin(pt_idx);
            // Forward to the pinned version (not unpinned)
            self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(pt_idx));
            return;
        }

        // Check if already used by something else
        if let Some(Binding::CompletedPartialType(unpinned, first_use)) =
            self.table.types.1.get(pt_idx)
        {
            match first_use {
                FirstUse::Undetermined => {
                    // We're the first! Claim it.
                    self.mark_first_use(pt_idx, deferred.bound_name_idx);
                    self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(*unpinned));
                    return;
                }
                FirstUse::UsedBy(other_idx) => {
                    // Already pinned - check if same binding context
                    let same_context = deferred.current_binding_idx == Some(*other_idx);
                    if same_context {
                        // Secondary read in same first-use context - use unpinned
                        self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(*unpinned));
                    } else {
                        // Different binding - use pinned version
                        self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(pt_idx));
                    }
                    return;
                }
                FirstUse::DoesNotPin => {
                    // Forward to pinned version
                    self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(pt_idx));
                    return;
                }
            }
        }
    }

    // Default: forward to whatever we found
    self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(final_idx));
}
```

---

## Phase 6: Testing

### Step 6.1: Write a failing test first

**Location**: Find the appropriate test file in `pyrefly/lib/test/`

Add this test BEFORE making changes to verify the current behavior:

```rust
#[test]
fn test_partial_type_inference_in_loop() {
    // This test should FAIL before the fix and PASS after
    let code = r#"
x = []
for i in range(5):
    x.append(i)
reveal_type(x)  # Should be list[int]
"#;
    // Assert that x is inferred as list[int], not list[Unknown]
}
```

### Step 6.2: Additional test cases

```rust
#[test]
fn test_partial_type_no_reassignment_in_loop() {
    // x is read in loop but not reassigned - should work
    let code = r#"
x = []
for i in range(5):
    x.append(i)
    y = len(x)  # x is used but not reassigned
"#;
}

#[test]
fn test_partial_type_with_reassignment_in_loop() {
    // x IS reassigned in loop - inference should still work before loop
    let code = r#"
x = []
x.append(1)  # First use BEFORE the loop
for i in range(5):
    x = [i]  # Reassignment
"#;
}

#[test]
fn test_partial_type_nested_loops() {
    let code = r#"
x = []
for i in range(5):
    for j in range(3):
        x.append(i + j)
reveal_type(x)  # Should be list[int]
"#;
}
```

### Step 6.3: Run tests incrementally

```bash
# After each phase:
buck test pyrefly:pyrefly_library -- test_partial_type

# Before submitting:
./test.py
```

---

## Implementation Checklist

- [ ] **Phase 1**: Add `DeferredBoundName` struct and `deferred_bound_names` field to `BindingsBuilder`
- [ ] **Phase 2**: Add `lookup_name_without_first_use` method
- [ ] **Phase 3**: Update `ensure_name_impl` to defer binding creation
- [ ] **Phase 4**: Implement `process_deferred_bound_names` and related helper methods
- [ ] **Phase 4**: Call `process_deferred_bound_names` in `Bindings::new`
- [ ] **Phase 5**: Handle already-pinned cases correctly
- [ ] **Phase 6**: Write and verify tests
- [ ] Run `arc autocargo` if you modified any Buck files
- [ ] Run `./test.py` to verify all tests pass

---

## Edge Cases and Risks

### LegacyTParamCollector

The `LegacyTParamCollector` logic in `ensure_name_impl` intercepts lookups in static type contexts. For simplicity, we keep this path synchronous (not deferred). This is safe because:
- Static type contexts already don't pin partial types
- The lookup path is different (`intercept_lookup` → `lookup_legacy_tparam`)

### Error Cases

When a name is not found (`NameLookupResult::NotFound`), we create the binding immediately with an error. This is fine because:
- Error bindings don't participate in first-use inference
- We still need to report the error during traversal

### Cycle Detection

The `follow_to_partial_type` function includes cycle detection. This shouldn't be necessary in well-formed code, but protects against bugs.

### Processing Order

We process deferred bindings in insertion order (the order lookups occurred during traversal). This preserves determinism since AST traversal is deterministic.

---

## Architecture Notes

### Why Not Clone `Usage`?

The `Usage` enum contains `SmallSet<Idx<Key>>` which is clonable, but the enum itself doesn't derive `Clone`. Rather than adding `Clone`, we extract the essential information:
- `current_idx()` → stored as `Option<Idx<Key>>`
- Is it narrowing? → stored as `bool`
- Is it static type? → stored as `bool`

This is cleaner and makes the deferred state explicit.

### Why Defer All Flow Lookups?

We could try to detect at traversal time whether a lookup goes through a phi and only defer those. However:
1. This adds complexity to the lookup path
2. The overhead of deferral is minimal (one Vec push per lookup)
3. Consistent handling is easier to reason about

### Future Improvements

1. **Smarter compound binding handling**: The current V0 approach is conservative. We could track which bindings might compete and only disable inference when there's actual ambiguity.

2. **Cross-function first-use**: Currently first-use is module-local. Future work could extend this.

---

## Debugging Tips

### Bindings Not Created

If tests fail after Phase 4 because bindings don't exist:
- Check that `process_deferred_bound_names` is being called
- Add debug prints in `finalize_bound_name` to see what's being processed

### First-Use Not Detected

If loop tests still fail:
- Print the binding chain for the phi node - is it actually a `Forward`?
- Check that `follow_to_partial_type` is correctly following the chain
- Verify the `FirstUse` enum is being updated

### Cycle Panics

If you see cycle-related panics:
- The `SmallSet` in `follow_to_partial_type` should catch cycles
- Check if you're accidentally creating circular forwards

---

## Questions for Review / Answers from tech lead

Before starting implementation:

1. Is keeping `LegacyTParamCollector` synchronous the right tradeoff?
   Answer: I think so, making it asynchronous seems difficult and I believe that it just produces
           `Forward` bindings in the case where a name is *not* a legacy tparam, so it should work
           okay. The issue is tricky, but a couple junior engineers looked into it and agreed that
           it will probably work.
2. Should we process in insertion order or TextRange order? (Plan uses insertion order for simplicity)
   Answer: let's use insertion order initially, but also mark a TODO to consider revisiting this
           because it's possible that text range order would be more predictable. They will be the
           same in most cases, and it's more important to make the overall architecture change
           work first before fine-tuning.
3. Do we need to handle any other binding types besides `Key::BoundName`?
   Answer: I don't think so - to my knowledge all reads of a name wind up becoming `Key::BoundName`,
           even when they are in a static type context. If there are any others, the existing logic
           probably isn't handling it anyway, so fixing the problem is most likely out-of-scope
           for this project.

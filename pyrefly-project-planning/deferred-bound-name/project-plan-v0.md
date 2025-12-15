# Deferred BoundName Implementation Plan

**Prerequisite**: This plan is based on the codebase with D88413287 (`adfe44adfc`) applied, which simplifies usage tracking by removing `Usage::narrowing_from()`. The simplified `Usage` flow makes the deferred binding implementation cleaner.

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

## Implementation Notes

This section documents how the plan was actually implemented.

**Phases 0-2**: Implemented as separate commits.
- Phase 0: Added 4 failing test cases to `delayed_inference.rs` with `bug = "..."` tags
- Phase 1: Added `DeferredBoundName`, `UsageContext` structs and `deferred_bound_names` field
- Phase 2: Added `lookup_name_without_first_use` method

**Phases 3-5**: Implemented together in a single commit. These phases are interdependent:
- Phase 3 (defer binding creation) breaks all tests until Phase 4 is also implemented
- Phase 4's `finalize_bound_name` needed Phase 5's logic to handle secondary reads correctly

Key implementation details that differed from the original plan:
1. `follow_to_partial_type` returns full partial type info `(default_idx, Option<(pt_idx, unpinned_idx, FirstUse)>)` rather than just `(idx, Option<pt_idx>)`. This allows `finalize_bound_name` to handle all `FirstUse` states.
2. The `FirstUse::UsedBy(other_idx)` case from Phase 5 was essential for handling secondary reads of the same name in the same binding context (e.g., `g(x, x)`).
3. A `defer_bound_name` helper method was added to `BindingsBuilder` to encapsulate the deferral logic.

**Future cleanup**: Once the implementation is stable, `lookup_name_without_first_use` can be renamed to `lookup_name` and the original `lookup_name`, `detect_first_use`, and `record_first_use` can be removed.

---

## Phase 0: Write Failing Tests First

Before making any code changes, write tests that demonstrate the current broken behavior.
This validates your understanding and gives you a clear success criterion.

### Step 0.1: Find existing partial type tests

Look for existing tests related to partial types to understand the test patterns:
```bash
# Find test files
ls pyrefly/lib/test/

# Search for existing partial type tests
grep -r "partial" pyrefly/lib/test/ --include="*.md" --include="*.rs"
grep -r "list\[@" pyrefly/lib/test/ --include="*.md" --include="*.rs"
```

Pyrefly uses markdown-based end-to-end tests in addition to Rust unit tests.
Check `pyrefly/lib/test/` for the appropriate location.

### Step 0.2: Write the failing test

Add a test that should FAIL before the fix and PASS after:

```python
# Test: partial type inference in loop (currently broken)
x = []
for i in range(5):
    x.append(i)
reveal_type(x)  # Expected: list[int], Currently: list[Unknown] or similar
```

Run to confirm it fails:
```bash
buck test pyrefly:pyrefly_library -- <test_name>
```

---

## Phase 1: Data Structures

### Step 1.1: Define `DeferredBoundName` struct

**Location**: `pyrefly/lib/binding/bindings.rs` (add near line 185, before `BindingsBuilder` which starts at line 189)

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
    /// The result of the name lookup (may be a phi that forwards elsewhere)
    lookup_result_idx: Idx<Key>,
    /// Information about the usage context where the lookup occurred
    used_in: UsageContext,
}

/// Information about the usage context where a name lookup occurred.
///
/// This captures the relevant properties of `Usage` needed for deferred
/// first-use detection.
#[derive(Debug)]
struct UsageContext {
    /// The current binding idx at the time of lookup (for first-use tracking)
    current_binding_idx: Option<Idx<Key>>,
    /// Whether this lookup can pin a partial type's first use.
    /// True for normal usage (Usage::CurrentIdx), false for narrowing or static type contexts.
    may_pin_partial_type: bool,
}
```

**Why this structure**:
- We store the essential information from `Usage` rather than `Usage` itself (which doesn't derive `Clone`)
- The `lookup_result_idx` is what `lookup_name` returned - we'll follow this chain at finalization
- `UsageContext` groups together the properties of where the lookup occurred

### Step 1.2: Add field to `BindingsBuilder`

**Location**: `pyrefly/lib/binding/bindings.rs`, in the `BindingsBuilder` struct (lines 189-207)

Add this field:
```rust
pub struct BindingsBuilder<'a> {
    // ... existing fields ...

    /// BoundName lookups deferred until after AST traversal
    deferred_bound_names: Vec<DeferredBoundName>,

    // ... rest of fields ...
}
```

Update initialization in `Bindings::new()` (around line 400, look for the `BindingsBuilder` initialization):
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

**Location**: `pyrefly/lib/binding/bindings.rs` (add near `lookup_name` which is at lines 954-986)

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

**Why**: The existing `lookup_name` (lines 954-986) calls `detect_first_use` (lines 1003-1043) and `record_first_use`. We need a version that skips this for deferred bindings.

**Future cleanup**: Once all callers are migrated to deferred binding creation and the original `lookup_name` is no longer needed, rename `lookup_name_without_first_use` to `lookup_name` and remove the old function along with `detect_first_use` and `record_first_use`.

---

## Phase 3: Modify `ensure_name_impl` to Defer Binding Creation

**Location**: `pyrefly/lib/binding/expr.rs` (lines 294-370)

**Important**: The `Usage` enum is defined at lines 72-100 in this same file. After D88413287, the `Usage` enum is simplified:
- `CurrentIdx(Idx<Key>, SmallSet<Idx<Key>>)` - Normal usage for creating bindings
- `Narrowing(Option<Idx<Key>>)` - Usage in narrowing contexts (doesn't pin)
- `StaticTypeInformation` - Static type contexts (doesn't pin)

The `narrowing_from()` method was removed - usage now flows through unchanged. The `current_idx()` method returns `Option<Idx<Key>>` for all variants.

### Step 3.1: Update `ensure_name_impl` for normal flow lookups

The current code (lines 312-336):
```rust
let used_in_static_type = matches!(usage, Usage::StaticTypeInformation);
let lookup_result =
    if used_in_static_type && let Some((tparams_collector, tparam_id)) = tparams_lookup {
        self.intercept_lookup(tparams_collector, tparam_id)
    } else {
        self.lookup_name(Hashed::new(&name.id), usage)
    };
match lookup_result {
    NameLookupResult::Found { idx: value, initialized: is_initialized } => {
        if !used_in_static_type
            && !self.module_info.path().is_interface()
            && let Some(error_message) = is_initialized.as_error_message(&name.id)
        {
            self.error(...);
        }
        self.insert_binding(key, Binding::Forward(value))  // EAGER - change this
    }
    NameLookupResult::NotFound => { /* error handling */ }
}
```

**New approach** - keep existing structure, just change the lookup and binding creation:
```rust
let used_in_static_type = matches!(usage, Usage::StaticTypeInformation);
let may_pin_partial_type = matches!(usage, Usage::CurrentIdx(_, _));

let lookup_result =
    if used_in_static_type && let Some((tparams_collector, tparam_id)) = tparams_lookup {
        self.intercept_lookup(tparams_collector, tparam_id)  // Keep synchronous
    } else {
        self.lookup_name_without_first_use(Hashed::new(&name.id))  // NEW: no first-use detection
    };

match lookup_result {
    NameLookupResult::Found { idx: lookup_result_idx, initialized: is_initialized } => {
        // Uninitialized local errors still reported during traversal
        if !used_in_static_type
            && !self.module_info.path().is_interface()
            && let Some(error_message) = is_initialized.as_error_message(&name.id)
        {
            self.error(name.range, ErrorInfo::Kind(ErrorKind::UnboundName), error_message);
        }

        // For LegacyTParamCollector path (static type context), create binding immediately
        // since it doesn't participate in partial type pinning anyway
        if used_in_static_type {
            return self.insert_binding(key, Binding::Forward(lookup_result_idx));
        }

        // Normal case: defer the binding creation
        self.defer_bound_name(
            key,
            lookup_result_idx,
            usage.current_idx(),
            may_pin_partial_type,
        )
    }
    NameLookupResult::NotFound => {
        // Error case - create binding immediately (no deferral needed)
        // ...existing not-found handling unchanged...
    }
}
```

### Step 3.2: Add `defer_bound_name` helper method

**Location**: `pyrefly/lib/binding/bindings.rs`

```rust
/// Defer creation of a BoundName binding until after AST traversal.
///
/// This reserves an index for the binding and stores the lookup result
/// along with usage context. The actual binding is created later by
/// `process_deferred_bound_names` when all phi nodes are populated.
pub fn defer_bound_name(
    &mut self,
    key: Key,
    lookup_result_idx: Idx<Key>,
    current_binding_idx: Option<Idx<Key>>,
    may_pin_partial_type: bool,
) -> Idx<Key> {
    let bound_name_idx = self.idx_for_promise(key);
    self.deferred_bound_names.push(DeferredBoundName {
        bound_name_idx,
        lookup_result_idx,
        used_in: UsageContext {
            current_binding_idx,
            may_pin_partial_type,
        },
    });
    bound_name_idx
}
```

**Key changes**:
1. Change `lookup_name` to `lookup_name_without_first_use` in the else branch
2. Keep the existing `if/else` structure for lookup - don't restructure the control flow
3. In the `Found` branch, check `used_in_static_type` to decide immediate vs deferred binding
4. Use `idx_for_promise` to reserve an index for deferred bindings
5. Store the lookup result in `deferred_bound_names`
6. Return the reserved index (callers don't need to change)
7. Keep error cases (`NotFound`) synchronous since they don't benefit from deferral

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
///
/// This handles all the first-use logic that was previously done eagerly
/// in `lookup_name`. Now that phi nodes are populated, we can correctly
/// follow Forward chains and detect first-use opportunities.
fn finalize_bound_name(&mut self, deferred: DeferredBoundName) {
    // Follow Forward chains to find any partial type
    let (default_idx, partial_type_info) =
        self.follow_to_partial_type(deferred.lookup_result_idx);

    if let Some((pt_idx, unpinned_idx, first_use)) = partial_type_info {
        if !deferred.used_in.may_pin_partial_type {
            // Non-pinning context
            self.mark_does_not_pin(pt_idx);
            // Forward to the pinned version (not unpinned)
            self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(pt_idx));
            return;
        }

        // Handle based on current first-use state
        match first_use {
            FirstUse::Undetermined => {
                // We're the first! Claim it.
                if let Some(current_idx) = deferred.used_in.current_binding_idx {
                    self.mark_first_use(pt_idx, current_idx);
                }
                self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(unpinned_idx));
                return;
            }
            FirstUse::UsedBy(other_idx) => {
                // Already pinned - check if same binding context
                let same_context = deferred.used_in.current_binding_idx == Some(other_idx);
                if same_context {
                    // Secondary read in same first-use context - use unpinned
                    self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(unpinned_idx));
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

    // Default: forward to whatever we found
    self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(default_idx));
}

/// Follow Forward chains to find a CompletedPartialType.
/// Returns (idx_to_forward_to, Some((partial_type_idx, unpinned_idx, first_use_state)))
/// if a CompletedPartialType is found, or (original_idx, None) otherwise.
fn follow_to_partial_type(
    &self,
    start_idx: Idx<Key>,
) -> (Idx<Key>, Option<(Idx<Key>, Idx<Key>, FirstUse)>) {
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
            Some(Binding::CompletedPartialType(unpinned_idx, first_use)) => {
                // Return all the info about this partial type
                return (*unpinned_idx, Some((current, *unpinned_idx, first_use.clone())));
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

**Location**: `pyrefly/lib/binding/bindings.rs`, in `Bindings::new()` (lines 414-510)

The key locations within `Bindings::new()`:
- Line 454: `builder.stmts(x.body, &NestingContext::toplevel())` - AST traversal
- Line 455: `assert_eq!(builder.scopes.loop_depth(), 0)` - loop depth check
- Line 468: `builder.scopes.finish()` - scope finalization

Add the call after the loop_depth assertion (line 455), before the `__all__` validation:

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

**Note**: This logic is integrated into the `finalize_bound_name` function shown in Phase 4.

The original proposal mentions a determinism concern with compound bindings like:
```python
x = []
x.append(1) if len(x) == 0 else (w := x.append("foo"))
```

The key insight is handling the `FirstUse::UsedBy(other_idx)` case - when a partial type has already been claimed by a previous binding, we need to check if we're in the same binding context (a "secondary read") or a different one.

### Secondary Read Detection

In `finalize_bound_name`, the `FirstUse::UsedBy(other_idx)` case handles this:

```rust
FirstUse::UsedBy(other_idx) => {
    // Already pinned - check if same binding context
    let same_context = deferred.used_in.current_binding_idx == Some(other_idx);
    if same_context {
        // Secondary read in same first-use context - use unpinned
        self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(unpinned_idx));
    } else {
        // Different binding - use pinned version
        self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(pt_idx));
    }
    return;
}
```

This is essential for tests like `test_first_use_reads_name_twice` where expressions like `g(x, x)` have multiple reads of the same name. The second read should forward to the unpinned type, not the pinned one.

---

## Phase 6: Testing

**Note**: This phase should actually be done FIRST (see Phase 0). The tests here are for reference.

### Step 6.1: Test file locations

Pyrefly uses multiple test formats:
- Markdown-based end-to-end tests in `pyrefly/lib/test/`
- Rust unit tests within the source files
- Conformance tests in `conformance/`

For this feature, look for existing partial type tests:
```bash
# Find partial type related tests
grep -r "partial" pyrefly/lib/test/ --include="*.md"
grep -r "@_" pyrefly/lib/test/ --include="*.md"
```

### Step 6.2: Test cases to add

These test cases can be added as markdown tests or Rust tests depending on the test infrastructure:

**Core case - partial type in loop (the main bug)**:
```python
x = []
for i in range(5):
    x.append(i)
reveal_type(x)  # Expected: list[int]
```

**Secondary read in loop**:
```python
x = []
for i in range(5):
    x.append(i)
    y = len(x)  # x is used but not reassigned
reveal_type(x)  # Expected: list[int]
```

**First use before loop, reassignment in loop**:
```python
x = []
x.append(1)  # First use BEFORE the loop
for i in range(5):
    x = [i]  # Reassignment
reveal_type(x)  # Expected: list[int] (pinned before loop)
```

**Nested loops**:
```python
x = []
for i in range(5):
    for j in range(3):
        x.append(i + j)
reveal_type(x)  # Expected: list[int]
```

**While loop**:
```python
x = []
i = 0
while i < 5:
    x.append(i)
    i += 1
reveal_type(x)  # Expected: list[int]
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

- [x] **Phase 0**: Write failing tests first to confirm broken behavior
- [x] **Phase 1**: Add `DeferredBoundName` struct and `deferred_bound_names` field to `BindingsBuilder`
- [x] **Phase 2**: Add `lookup_name_without_first_use` method
- [x] **Phase 3**: Update `ensure_name_impl` to defer binding creation (includes `defer_bound_name` helper)
- [x] **Phase 4**: Implement `process_deferred_bound_names` and related helper methods
- [x] **Phase 4**: Call `process_deferred_bound_names` in `Bindings::new` (after line 455, before `__all__` validation)
- [x] **Phase 5**: Handle already-pinned cases correctly (integrated into `finalize_bound_name`)
- [x] **Phase 6**: Verify tests now pass (all 3118 tests pass)
- [ ] Run `arc autocargo` if you modified any Buck files
- [ ] Run `./test.py` to verify all tests pass
- [ ] Future cleanup: Remove old `lookup_name`, `detect_first_use`, `record_first_use`

---

## Verified Code Locations (as of December 2024, after D88413287 and Phase 1)

These locations were verified against the codebase with D88413287 applied and Phase 1 complete:

| Item | File | Lines | Notes |
|------|------|-------|-------|
| `DeferredBoundName` struct | `binding/bindings.rs` | 189-202 | ✅ Phase 1 complete |
| `UsageContext` struct | `binding/bindings.rs` | 204-215 | ✅ Phase 1 complete |
| `BindingsBuilder` struct | `binding/bindings.rs` | 217-237 | ✅ `deferred_bound_names` field added |
| `Bindings::new()` | `binding/bindings.rs` | 414-510 | Main constructor |
| AST traversal call | `binding/bindings.rs` | 454 | `builder.stmts(x.body, ...)` |
| loop_depth assertion | `binding/bindings.rs` | 455 | Insert `process_deferred_bound_names` after this |
| Scope finalization | `binding/bindings.rs` | 468 | `builder.scopes.finish()` |
| `lookup_name` | `binding/bindings.rs` | 954-986 | Add `lookup_name_without_first_use` nearby |
| `detect_first_use` | `binding/bindings.rs` | 1003-1043 | Reference for first-use logic |
| `record_first_use` | `binding/bindings.rs` | 1046-1061 | Reference for recording first-use |
| `idx_for_promise` | `binding/bindings.rs` | 653-660 | Existing pattern to follow |
| `ensure_name_impl` | `binding/expr.rs` | 294-370 | Main function to modify |
| `Usage` enum | `binding/expr.rs` | 72-100 | Simplified in D88413287 |
| `setup_loop` | `binding/scope.rs` | 2676 | Loop phi creation |
| `insert_phi_keys` | `binding/scope.rs` | 2640 | How phis are reserved |
| `merge_idxs` | `binding/scope.rs` | 2401 | How phis are filled in |

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

**TODO**: Consider revisiting whether TextRange order would be more predictable. In most cases insertion order and TextRange order will be the same, but there may be edge cases where they differ (e.g., complex expressions with multiple name lookups). The architectural change should work first before fine-tuning the ordering.

---

## Architecture Notes

### Why Not Clone `Usage`?

The `Usage` enum contains `SmallSet<Idx<Key>>` which is clonable, but the enum itself doesn't derive `Clone`. Rather than adding `Clone`, we extract the essential information into `UsageContext`:
- `current_idx()` → stored as `current_binding_idx: Option<Idx<Key>>`
- Can it pin? → stored as `may_pin_partial_type: bool`

Grouping these in `UsageContext` makes it clear they both describe properties of the usage context where the lookup occurred.

**Note on D88413287 simplification**: The `narrowing_from()` method was removed. The `Usage` now flows through expressions unchanged - narrowing contexts just pass the same usage through. This simplifies our implementation because:
1. We don't need to track complex narrowing inheritance
2. The `may_pin_partial_type` flag is simply `matches!(usage, Usage::CurrentIdx(_, _))`
3. The `current_idx()` method works uniformly across all variants

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

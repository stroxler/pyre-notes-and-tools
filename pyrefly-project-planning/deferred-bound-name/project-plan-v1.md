# Deferred BoundName Implementation Plan (v1)

**Context**: This plan updates v0 to work with the current codebase state where `Usage::narrowing_from()` is present. The previous plan was based on D88413287 which removed that method, but that change was reverted. We now need a more complex approach to handle narrowing contexts properly.

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

## Terminology: The Partial Type Binding Chain

When a name is assigned with a partial type (like `x = []`), three bindings are created in a chain:

```
Key::Definition(x) → Binding::NameAssign { ... }
                          ↑
Key::PartialTypeWithUpstreamsCompleted(x) → Binding::PartialTypeWithUpstreamsCompleted(def_idx, first_uses)
                          ↑
Key::CompletedPartialType(x) → Binding::CompletedPartialType(unpinned_idx, FirstUse)
```

**The three layers:**

1. **`Key::Definition` / `Binding::NameAssign`** ("raw definition")
   - The actual assignment binding that may contain placeholder type variables
   - This is the `def_idx` that gets stored inside `PartialTypeWithUpstreamsCompleted`

2. **`Key::PartialTypeWithUpstreamsCompleted` / `Binding::PartialTypeWithUpstreamsCompleted(def_idx, first_uses)`** ("unpinned")
   - Wraps the raw definition
   - `first_uses: Box<[Idx<Key>]>` lists the upstream `CompletedPartialType` indices that this binding is a first-use of
   - When solved, it forces all upstream pins before computing its own type
   - This is the `unpinned_idx` that gets stored inside `CompletedPartialType`
   - **We mutate this binding** to add entries to `first_uses` when we discover first-use relationships

3. **`Key::CompletedPartialType` / `Binding::CompletedPartialType(unpinned_idx, FirstUse)`** ("pinned")
   - Wraps the unpinned version
   - `FirstUse` enum tracks whether someone has claimed first-use rights: `Undetermined`, `UsedBy(idx)`, or `DoesNotPin`
   - This is what phi nodes forward to, and what scopes bind names to
   - **We mutate this binding** to set `FirstUse::UsedBy(idx)` or `FirstUse::DoesNotPin`

**How first-use works:**
- When binding Y reads partial-type X for the first time, we:
  1. Mark X's `CompletedPartialType` as `FirstUse::UsedBy(Y)` (mutate the pinned version)
  2. Add X's `CompletedPartialType` idx to Y's `PartialTypeWithUpstreamsCompleted.first_uses` (mutate the unpinned version)
  3. Forward Y's `BoundName` to X's `PartialTypeWithUpstreamsCompleted` (unpinned) so Y sees the raw placeholder types

---

## Key Differences from v0

The v0 plan assumed `Usage::narrowing_from()` was removed, which simplified the implementation. With that method present, we face a new challenge:

1. **`Usage` is mutable**: The `CurrentIdx(Idx<Key>, SmallSet<Idx<Key>>)` variant contains a `first_uses_of` set that gets mutated during traversal via `record_first_use`.

2. **Narrowing contexts need special handling**: When `Usage::narrowing_from(usage)` is called, it creates `Narrowing(Some(idx))` which preserves the current binding idx. This is needed so that secondary reads in narrowing contexts can be detected.

3. **Cannot store `Usage` in deferred data structure**: Since `Usage` is mutated during traversal (its `first_uses_of` set accumulates data), we can't simply store it for later.

### Solution Approach

The solution involves four key changes:

**(a)** Rename the existing `Usage` to `LegacyUsage`, then create a new `Usage` data structure that mirrors the old `Usage` but doesn't have a `first_uses_of` map. Add a helper to convert `LegacyUsage` to `Usage`.

**(b)** Modify `target.rs` so that we *always* create `PartialTypeWithUpstreamsCompleted` binding, even when `first_uses_of` is empty. When empty, it behaves like a `Forward` binding.

**(c)** In the deferred-name-lookup data structures, store `Usage` instead of just the idx. This is how we'll properly handle `Usage::Narrowing` lookups.

**(d)** When implementing bound name creation in the finalization pass:
   - Accumulate first-use information in a separate `first_use_of_map: HashMap<Idx<Key>, Vec<Idx<Key>>>` variable
   - After the first pass, do a second pass that scans the binding table for `PartialTypeWithUpstreamsCompleted` bindings and mutates them to include any `first_uses_of` that were recorded

---

## Phase 0: Write Failing Tests First

Before making any code changes, write tests that demonstrate the current broken behavior.
This validates your understanding and gives you a clear success criterion.

### Step 0.1: Find existing partial type tests

Look for existing tests related to partial types to understand the test patterns:
```bash
# Find test files
ls lib/test/

# Search for existing partial type tests
grep -r "partial" lib/test/ --include="*.md" --include="*.rs"
grep -r "list\[@" lib/test/ --include="*.md" --include="*.rs"
```

### Step 0.2: Write the failing test

Add tests that should FAIL before the fix and PASS after. Add them to a test file with `bug = "..."` tags:

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

### Step 1.1: Rename existing `Usage` to `LegacyUsage` and define new `Usage` enum

**Location**: `lib/binding/expr.rs` (around line 72)

First, rename the existing `Usage` enum to `LegacyUsage`:

```rust
/// Legacy usage context for name lookups (to be removed after migration).
///
/// This enum tracks the mutable `first_uses_of` set which is mutated during
/// traversal. It will be replaced by the immutable `Usage` enum once the
/// deferred binding approach is fully implemented.
#[derive(Debug)]
pub enum LegacyUsage {
    /// Normal usage context that may pin partial types.
    CurrentIdx(Idx<Key>, SmallSet<Idx<Key>>),
    /// Narrowing context.
    Narrowing(Option<Idx<Key>>),
    /// Static type context.
    StaticTypeInformation,
}

// Keep existing methods on LegacyUsage (renamed from Usage)
impl LegacyUsage {
    // ... existing methods like narrowing_from, current_idx, etc. ...
}
```

Then, define the new immutable `Usage` enum:

```rust
/// Usage context for deferred name lookups.
///
/// Unlike `LegacyUsage`, this doesn't carry a mutable `first_uses_of` set.
/// It captures the essential information needed for deferred first-use detection.
#[derive(Debug, Clone)]
pub enum Usage {
    /// Normal usage context that may pin partial types.
    /// The idx is the current binding being computed.
    CurrentIdx(Idx<Key>),
    /// Narrowing context that should not pin partial types.
    /// The idx (if present) is used for secondary-read detection.
    Narrowing(Option<Idx<Key>>),
    /// Static type context that should not pin partial types.
    StaticTypeInformation,
}

impl Usage {
    /// Create a Usage from a LegacyUsage reference.
    pub fn from_legacy(usage: &LegacyUsage) -> Self {
        match usage {
            LegacyUsage::CurrentIdx(idx, _) => Usage::CurrentIdx(*idx),
            LegacyUsage::Narrowing(idx) => Usage::Narrowing(*idx),
            LegacyUsage::StaticTypeInformation => Usage::StaticTypeInformation,
        }
    }

    /// Get the current binding idx, if any.
    pub fn current_idx(&self) -> Option<Idx<Key>> {
        match self {
            Usage::CurrentIdx(idx) => Some(*idx),
            Usage::Narrowing(idx) => *idx,
            Usage::StaticTypeInformation => None,
        }
    }

    /// Whether this usage context may pin partial types.
    pub fn may_pin_partial_type(&self) -> bool {
        matches!(self, Usage::CurrentIdx(_))
    }
}
```

### Step 1.2: Define `DeferredBoundName` struct

**Location**: `lib/binding/bindings.rs` (add near line 185, before `BindingsBuilder`)

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
    usage: Usage,
}
```

### Step 1.3: Add field to `BindingsBuilder`

**Location**: `lib/binding/bindings.rs`, in the `BindingsBuilder` struct

Add this field:
```rust
pub struct BindingsBuilder<'a> {
    // ... existing fields ...

    /// BoundName lookups deferred until after AST traversal
    deferred_bound_names: Vec<DeferredBoundName>,

    // ... rest of fields ...
}
```

Update initialization in `Bindings::new()`:
```rust
let mut builder = BindingsBuilder {
    // ... existing field initializations ...
    deferred_bound_names: Vec::new(),
    // ...
};
```

---

## Phase 2: Always Create PartialTypeWithUpstreamsCompleted

### Step 2.1: Modify `bind_single_name_assign` in `target.rs`

**Location**: `lib/binding/target.rs`, in `bind_single_name_assign` (around line 452)

Currently, the code conditionally creates `PartialTypeWithUpstreamsCompleted`:
```rust
// Current code (lines 502-512)
let unpinned_idx = if first_use_of.is_empty() {
    def_idx
} else {
    self.insert_binding(
        Key::PartialTypeWithUpstreamsCompleted(identifier),
        Binding::PartialTypeWithUpstreamsCompleted(
            def_idx,
            first_use_of.into_iter().collect(),
        ),
    )
};
```

**Change to always create the binding** (empty list behaves like Forward):
```rust
// New code: always create PartialTypeWithUpstreamsCompleted
// When first_use_of is empty, it behaves like a Forward to def_idx
let unpinned_idx = self.insert_binding(
    Key::PartialTypeWithUpstreamsCompleted(identifier),
    Binding::PartialTypeWithUpstreamsCompleted(
        def_idx,
        first_use_of.into_iter().collect(),
    ),
);
```

### Step 2.2: Update solve.rs if needed

**Location**: `lib/alt/solve.rs`

Verify that `Binding::PartialTypeWithUpstreamsCompleted` with an empty list works correctly. The current code:
```rust
Binding::PartialTypeWithUpstreamsCompleted(raw_idx, first_used_by) => {
    // Force all of the upstream `Pin`s for which was the first use.
    for idx in first_used_by {
        self.get_idx(*idx);
    }
    // ...
}
```

This should work fine with an empty list (the loop just does nothing).

### Step 2.3: Update `get_original_binding` in `bindings.rs`

**Location**: `lib/binding/bindings.rs`, in `get_original_binding` method

The narrowing logic uses `get_original_binding` to follow through wrapper bindings to find the original definition. Since we now always create `PartialTypeWithUpstreamsCompleted`, we need to add it to the list of bindings that should be followed through.

Find the pattern match in `get_original_binding` that looks like:
```rust
while let Some(
    Binding::Forward(fwd_idx)
    | Binding::CompletedPartialType(fwd_idx, _)
    | Binding::Phi(JoinStyle::NarrowOf(fwd_idx), _),
) = original_binding
```

**Add `PartialTypeWithUpstreamsCompleted`** to the pattern:
```rust
while let Some(
    Binding::Forward(fwd_idx)
    | Binding::CompletedPartialType(fwd_idx, _)
    | Binding::PartialTypeWithUpstreamsCompleted(fwd_idx, _)
    | Binding::Phi(JoinStyle::NarrowOf(fwd_idx), _),
) = original_binding
```

### Step 2.4: Update TypeInfo computation in `solve.rs`

**Location**: `lib/alt/solve.rs`, in the TypeInfo computation section

When computing TypeInfo (which preserves facets like dict literal key completions), we need to handle `PartialTypeWithUpstreamsCompleted` specially to preserve the facet information from the wrapped binding.

Add a new match arm to handle `PartialTypeWithUpstreamsCompleted`:
```rust
Binding::PartialTypeWithUpstreamsCompleted(raw_idx, first_used_by) => {
    // Force all of the upstream `Pin`s for which this was the first use.
    for idx in first_used_by {
        self.get_idx(*idx);
    }
    // Recursively get the TypeInfo from the raw binding to preserve facets
    self.get_type_info(*raw_idx)
}
```

### Step 2.5: Update captured variable detection in `captured_variable.rs`

**Location**: `lib/report/pysa/captured_variable.rs`

The captured variable detection logic traces through bindings to find definitions. Since we now always create `PartialTypeWithUpstreamsCompleted`, we need to update two methods:

1. **In `get_definition_from_usage`**: Add `Binding::CompletedPartialType` and `Binding::PartialTypeWithUpstreamsCompleted` to the match pattern that follows through wrapper bindings.

2. **In `get_definition_from_idx`**: Add `Binding::PartialTypeWithUpstreamsCompleted` to the existing `CompletedPartialType` pattern.

---

## Phase 3: Refactor `lookup_name` to Support Deferred First-Use

### Step 3.1: Rename existing `lookup_name` to `legacy_lookup_name` and create new `lookup_name`

**Location**: `lib/binding/bindings.rs` (near the existing `lookup_name`)

First, rename the existing `lookup_name` method to `legacy_lookup_name`:

```rust
/// Legacy name lookup that performs eager first-use detection.
///
/// This method is deprecated and will be removed after migration to
/// deferred binding creation. Use `lookup_name` instead.
fn legacy_lookup_name(&mut self, name: Hashed<&Name>, usage: &mut LegacyUsage) -> NameLookupResult {
    // ... existing lookup_name implementation unchanged ...
}
```

Then, create the new `lookup_name` method:

```rust
/// Look up a name in scope, marking it as used, but without first-use detection.
///
/// This is the primary lookup method for deferred BoundName creation.
/// First-use detection happens later in `process_deferred_bound_names`
/// when all phi nodes are populated.
fn lookup_name(&mut self, name: Hashed<&Name>) -> NameLookupResult {
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

### Step 3.2: Add `defer_bound_name` helper

**Location**: `lib/binding/bindings.rs`

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
    legacy_usage: &LegacyUsage,
) -> Idx<Key> {
    let bound_name_idx = self.idx_for_promise(key);
    self.deferred_bound_names.push(DeferredBoundName {
        bound_name_idx,
        lookup_result_idx,
        usage: Usage::from_legacy(legacy_usage),
    });
    bound_name_idx
}
```

---

## Phase 4: Modify `ensure_name_impl` to Defer Binding Creation

**Location**: `lib/binding/expr.rs` (around line 294)

**Note**: During this transitional phase, `ensure_name_impl` still receives `&mut LegacyUsage` as its parameter. We pass this to `defer_bound_name` which converts it to the new `Usage`.

### Step 4.1: Update `ensure_name_impl` for flow lookups

Change the normal case from creating bindings immediately to deferring them:

```rust
let used_in_static_type = matches!(usage, LegacyUsage::StaticTypeInformation);

let lookup_result =
    if used_in_static_type && let Some((tparams_collector, tparam_id)) = tparams_lookup {
        self.intercept_lookup(tparams_collector, tparam_id)  // Keep synchronous
    } else {
        self.lookup_name(Hashed::new(&name.id))  // NEW: no first-use detection
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
        self.defer_bound_name(key, lookup_result_idx, usage)
    }
    NameLookupResult::NotFound => {
        // Error case - create binding immediately (no deferral needed)
        // ...existing not-found handling unchanged...
    }
}
```

---

## Phase 5: Process Deferred Bindings After Traversal

### Step 5.1: Add `process_deferred_bound_names` method

**Location**: `lib/binding/bindings.rs`

**Note**: `bindings.rs` currently uses `starlark_map::small_map::SmallMap` and does not import `std::collections::HashMap`. You will need to add `use std::collections::HashMap;` at the top of the file. `HashMap` is appropriate here since the index can be large.

```rust
/// Process all deferred BoundName bindings after AST traversal.
///
/// At this point, all phi nodes are populated, so we can correctly
/// follow Forward chains and detect first-use opportunities.
fn process_deferred_bound_names(&mut self) {
    // Take the deferred bindings to avoid borrow issues
    let deferred = std::mem::take(&mut self.deferred_bound_names);

    // Build an index from Definition idx -> PartialTypeWithUpstreamsCompleted idx
    // This avoids linear scans when looking up which binding to update.
    // The current_idx in Usage is always a Key::Definition, so we need this
    // mapping to find the associated PartialTypeWithUpstreamsCompleted.
    let def_to_upstreams: HashMap<Idx<Key>, Idx<Key>> = self.build_definition_to_upstreams_index();

    // Accumulate first-uses to avoid O(n²) Box reallocations.
    // Key: PartialTypeWithUpstreamsCompleted idx to update
    // Value: CompletedPartialType idxs to add to its first_uses list
    let mut first_uses_to_add: HashMap<Idx<Key>, Vec<Idx<Key>>> = HashMap::new();

    // Process each deferred binding
    for binding in deferred {
        self.finalize_bound_name(binding, &def_to_upstreams, &mut first_uses_to_add);
    }

    // Bulk update all PartialTypeWithUpstreamsCompleted bindings
    for (upstreams_idx, new_first_uses) in first_uses_to_add {
        self.extend_first_uses_of_partial_type(upstreams_idx, new_first_uses);
    }
}

/// Build an index from Key::Definition idx to Key::PartialTypeWithUpstreamsCompleted idx.
///
/// This is used to efficiently look up which PartialTypeWithUpstreamsCompleted binding
/// needs to be updated when we discover that a Definition is a first-use of some
/// upstream partial type.
fn build_definition_to_upstreams_index(&self) -> HashMap<Idx<Key>, Idx<Key>> {
    let mut index = HashMap::new();
    for (idx, binding) in self.table.types.1.iter_enumerated() {
        if let Binding::PartialTypeWithUpstreamsCompleted(def_idx, _) = binding {
            index.insert(*def_idx, idx);
        }
    }
    index
}

/// Extend the first_uses list of a PartialTypeWithUpstreamsCompleted binding.
///
/// This is called once per binding at the end of process_deferred_bound_names,
/// avoiding O(n²) reallocations from repeated single-element appends.
fn extend_first_uses_of_partial_type(
    &mut self,
    partial_type_idx: Idx<Key>,
    additional_first_uses: Vec<Idx<Key>>,
) {
    if additional_first_uses.is_empty() {
        return;
    }
    if let Some(Binding::PartialTypeWithUpstreamsCompleted(_, first_uses)) =
        self.table.types.1.get_mut(partial_type_idx)
    {
        // Convert Box<[Idx<Key>]> to Vec, extend, convert back (done once per binding)
        let mut vec: Vec<_> = std::mem::take(first_uses).into_vec();
        vec.extend(additional_first_uses);
        *first_uses = vec.into_boxed_slice();
    }
}
```

### Step 5.2: Add `finalize_bound_name` method

```rust
/// Finalize a single deferred BoundName binding.
///
/// This handles all the first-use logic that was previously done eagerly
/// in `lookup_name`. Now that phi nodes are populated, we can correctly
/// follow Forward chains and detect first-use opportunities.
///
/// Key insight for narrowing contexts:
/// - Narrowing does NOT claim first-use (marks DoesNotPin when Undetermined)
/// - But if the upstream is already UsedBy(enclosing_idx) matching the narrowing's
///   enclosing binding, this is a "secondary read" and forwards to unpinned
/// - This preserves the existing secondary-read logic from detect_first_use
fn finalize_bound_name(
    &mut self,
    deferred: DeferredBoundName,
    def_to_upstreams: &HashMap<Idx<Key>, Idx<Key>>,
    first_uses_to_add: &mut HashMap<Idx<Key>, Vec<Idx<Key>>>,
) {
    // Follow Forward chains to find any partial type
    let (default_idx, partial_type_info) =
        self.follow_to_partial_type(deferred.lookup_result_idx);

    if let Some((pinned_idx, unpinned_idx, first_use)) = partial_type_info {
        // pinned_idx = the upstream's CompletedPartialType (pinned version)
        // unpinned_idx = the upstream's PartialTypeWithUpstreamsCompleted or Definition

        // Check if this is a narrowing context
        let is_narrowing = matches!(deferred.usage, Usage::Narrowing(_));

        if matches!(deferred.usage, Usage::StaticTypeInformation) {
            // Static type context: doesn't pin, forwards to pinned version
            self.mark_does_not_pin(pinned_idx);
            self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(pinned_idx));
            return;
        }

        if is_narrowing {
            // Narrowing context: does not pin partial types.
            // However, if the enclosing binding already claimed first-use, this is a
            // "secondary read" and should forward to unpinned (to see placeholder types).
            //
            // This mirrors the existing secondary-read logic in detect_first_use:
            // if we're in the same first-use context, we forward to unpinned.
            if let Usage::Narrowing(Some(enclosing_idx)) = deferred.usage {
                match first_use {
                    FirstUse::Undetermined => {
                        // Narrowing doesn't claim first-use; mark as DoesNotPin
                        self.mark_does_not_pin(pinned_idx);
                        // Forward to pinned version (consistent with current behavior)
                        self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(pinned_idx));
                    }
                    FirstUse::UsedBy(other_idx) => {
                        // Check if this is a secondary read in the same first-use context
                        if enclosing_idx == other_idx {
                            // Same context - forward to unpinned (secondary read semantics)
                            self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(unpinned_idx));
                        } else {
                            // Different context - forward to pinned
                            self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(pinned_idx));
                        }
                    }
                    FirstUse::DoesNotPin => {
                        // Already marked as not pinning - forward to pinned
                        self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(pinned_idx));
                    }
                }
            } else {
                // Narrowing(None) - no enclosing binding
                // Mark as does-not-pin if still undetermined
                if matches!(first_use, FirstUse::Undetermined) {
                    self.mark_does_not_pin(pinned_idx);
                }
                // Always forward to pinned (no secondary-read possible without enclosing idx)
                self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(pinned_idx));
            }
            return;
        }

        // Normal CurrentIdx context: may pin partial types
        match first_use {
            FirstUse::Undetermined => {
                // We're the first! Claim it.
                if let Some(current_idx) = deferred.usage.current_idx() {
                    self.mark_first_use(pinned_idx, current_idx);
                    // Record that the current binding's PartialTypeWithUpstreamsCompleted
                    // needs to include pinned_idx in its first_uses list
                    if let Some(&current_upstreams_idx) = def_to_upstreams.get(&current_idx) {
                        first_uses_to_add
                            .entry(current_upstreams_idx)
                            .or_default()
                            .push(pinned_idx);
                    }
                }
                self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(unpinned_idx));
                return;
            }
            FirstUse::UsedBy(other_idx) => {
                // Already pinned - check if same binding context
                let same_context = deferred.usage.current_idx() == Some(other_idx);
                if same_context {
                    // Secondary read in same first-use context - use unpinned
                    self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(unpinned_idx));
                } else {
                    // Different binding - use pinned version
                    self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(pinned_idx));
                }
                return;
            }
            FirstUse::DoesNotPin => {
                // Forward to pinned version
                self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(pinned_idx));
                return;
            }
        }
    }

    // Default: forward to whatever we found
    self.insert_binding_idx(deferred.bound_name_idx, Binding::Forward(default_idx));
}
```

### Step 5.3: Add helper methods

```rust
/// Follow Forward chains to find a CompletedPartialType.
/// Returns (idx_to_forward_to, Some((pinned_idx, unpinned_idx, first_use_state)))
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
                return (current, Some((current, *unpinned_idx, first_use.clone())));
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

### Step 5.4: Call `process_deferred_bound_names` in `Bindings::new`

**Location**: `lib/binding/bindings.rs`, in `Bindings::new()`

Add the call after the loop_depth assertion, before the `__all__` validation:

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

---

## Phase 6: Testing

### Step 6.1: Test cases to verify

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

**Narrowing context in loop**:
```python
x = []
for i in range(5):
    if x:  # Narrowing context - should not pin
        pass
    x.append(i)
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

### Step 6.2: Run tests incrementally

```bash
# After each phase:
buck test pyrefly:pyrefly_library -- test_partial_type

# Before submitting:
./test.py
```

---

## Phase 7: Cleanup - Remove LegacyUsage

After the deferred binding approach is fully working and tested, remove the legacy code:

### Step 7.1: Delete `LegacyUsage` and related methods

**Location**: `lib/binding/expr.rs`

1. Delete the `LegacyUsage` enum entirely
2. Delete `LegacyUsage::narrowing_from()` method
3. Delete any other `LegacyUsage`-specific methods

### Step 7.2: Delete old first-use detection code

**Location**: `lib/binding/bindings.rs`

1. Delete `detect_first_use` method
2. Delete `record_first_use` method
3. Delete `legacy_lookup_name` method (the one that did eager first-use detection)

### Step 7.3: Update callers to use `Usage` directly

**Location**: `lib/binding/expr.rs` and other files

1. Change all function signatures from `&mut LegacyUsage` to `&Usage` (now immutable!)
2. Update callers to construct `Usage` directly instead of `LegacyUsage`
3. Remove `Usage::from_legacy()` since it's no longer needed
4. The `narrowing_from` logic can be moved to `Usage::narrowing()` constructor

### Step 7.4: Simplify `bind_single_name_assign`

**Location**: `lib/binding/target.rs`

The `first_use_of` parameter can be removed since we always create `PartialTypeWithUpstreamsCompleted` with an empty list initially, and populate it during `process_deferred_bound_names`.

---

## Implementation Checklist

- [ ] **Phase 0**: Write failing tests first to confirm broken behavior
- [ ] **Phase 1**: Rename `Usage` to `LegacyUsage`, define new `Usage` enum, add `DeferredBoundName` struct, and `deferred_bound_names` field
- [ ] **Phase 2**: Modify `bind_single_name_assign` to always create `PartialTypeWithUpstreamsCompleted`
- [ ] **Phase 2**: Verify `Binding::PartialTypeWithUpstreamsCompleted` with empty list works in `solve.rs`
- [ ] **Phase 2**: Update `get_original_binding` to follow through `PartialTypeWithUpstreamsCompleted`
- [ ] **Phase 2**: Update TypeInfo computation in `solve.rs` to preserve facets through the wrapper
- [ ] **Phase 2**: Update captured variable detection in `captured_variable.rs`
- [ ] **Phase 3**: Rename `lookup_name` to `legacy_lookup_name`, add new `lookup_name` method
- [ ] **Phase 3**: Add `defer_bound_name` helper method
- [ ] **Phase 4**: Update `ensure_name_impl` to defer binding creation
- [ ] **Phase 5**: Implement `process_deferred_bound_names` with `build_definition_to_upstreams_index` and `extend_first_uses_of_partial_type`
- [ ] **Phase 5**: Implement `finalize_bound_name` and helper methods
- [ ] **Phase 5**: Call `process_deferred_bound_names` in `Bindings::new`
- [ ] **Phase 6**: Verify tests now pass
- [ ] Run `arc autocargo` if you modified any Buck files
- [ ] Run `./test.py` to verify all tests pass
- [ ] **Phase 7**: Delete `LegacyUsage` enum and related methods
- [ ] **Phase 7**: Delete `detect_first_use`, `record_first_use`, and `legacy_lookup_name`
- [ ] **Phase 7**: Update callers to use `Usage` directly (now immutable)
- [ ] **Phase 7**: Simplify `bind_single_name_assign` to remove `first_use_of` parameter

---

## Edge Cases and Risks

### Narrowing Contexts

Narrowing contexts (e.g., `if x:`) use the current semantics:

1. **`Narrowing(Some(enclosing_idx))` with `Undetermined`**: Mark `DoesNotPin`, forward to pinned
2. **`Narrowing(Some(enclosing_idx))` with `UsedBy(enclosing_idx)`**: Secondary read in same context → forward to unpinned
3. **`Narrowing(Some(enclosing_idx))` with `UsedBy(other_idx)`**: Different context → forward to pinned
4. **`Narrowing(None)`**: Mark `DoesNotPin` if undetermined, forward to pinned

This is consistent with the existing secondary-read logic in `detect_first_use` (lines 1002-1016 of `bindings.rs`), which checks if we're in the same first-use context and forwards to unpinned for secondary reads.

### When def_to_upstreams.get() Might Not Find a Match

The code uses `if let Some(&idx) = def_to_upstreams.get(&current_idx)` to look up the `PartialTypeWithUpstreamsCompleted` for a binding. This lookup may fail (return `None`) in the following cases:

1. **Non-name-assignment bindings**: The `current_idx` might be for a binding that isn't a name assignment, such as:
   - Attribute assignments (`x.y = ...`)
   - Subscript assignments (`x[i] = ...`)
   - Anonymous bindings (`Key::Anon`)

   These bindings don't have an associated `PartialTypeWithUpstreamsCompleted` because they don't participate in partial type inference.

2. **Bindings from other scopes**: If the current binding is in a nested scope (e.g., a lambda or comprehension), its Definition idx may not have a corresponding `PartialTypeWithUpstreamsCompleted` in the current module's index.

**This is expected and safe**: When the lookup fails, we simply don't add to `first_uses_to_add`. The first-use will still be recorded in the `CompletedPartialType`'s `FirstUse::UsedBy(idx)` - the only thing we skip is adding to the `PartialTypeWithUpstreamsCompleted.first_uses` list, which is only meaningful for name assignments with partial types.

### Processing Structure

The deferred binding processing has two phases:
1. **Build index**: A single O(n) scan to build `def_to_upstreams` mapping Definition idx → PartialTypeWithUpstreamsCompleted idx
2. **Process deferred bindings**: For each deferred binding, create the BoundName and directly mutate the relevant PartialTypeWithUpstreamsCompleted (via O(1) index lookup)

### Performance

The `build_definition_to_upstreams_index` method does a single linear scan of all bindings at the start of `process_deferred_bound_names`. This is O(n) where n is the number of bindings, and it's done once. After that, all lookups from `def_to_upstreams` are O(1) hash map lookups.

This is much better than the original approach of doing a linear scan for each deferred binding, which would be O(n*m) where m is the number of deferred bindings.

### Processing Order

We process deferred bindings in insertion order (the order lookups occurred during traversal). This preserves determinism since AST traversal is deterministic.

---

## Architecture Notes

### Why Rename Usage to LegacyUsage?

The old `Usage` enum contains `SmallSet<Idx<Key>>` in its `CurrentIdx` variant which gets mutated during traversal. Rather than trying to make this work with deferral, we:

1. Rename the old `Usage` to `LegacyUsage` (temporary, for the transition)
2. Create a new immutable `Usage` enum that captures just the essential information (which idx, what context)
3. After Phase 7 cleanup, only the new `Usage` remains

The new `Usage` variants:
- `CurrentIdx(idx)` → can pin, has a current binding idx, forwards to unpinned on first use
- `Narrowing(Some(idx))` → cannot pin itself; marks `DoesNotPin` if undetermined; but if already `UsedBy(idx)` (same enclosing), forwards to unpinned (secondary read)
- `Narrowing(None)` → cannot pin; marks `DoesNotPin` if undetermined; forwards to pinned
- `StaticTypeInformation` → cannot pin, forwards to pinned version

### Why Always Create PartialTypeWithUpstreamsCompleted?

Previously, this binding was only created when `first_uses_of` was non-empty. However, with deferred processing, we don't know at binding creation time whether there will be first-uses. By always creating it (even with an empty list), we have a stable location to update when we discover first-uses during `finalize_bound_name`.

### Why Build the Index Upfront?

The `current_idx` from `Usage::CurrentIdx` is always a `Key::Definition` (the raw binding idx), not a `PartialTypeWithUpstreamsCompleted`. To find the associated `PartialTypeWithUpstreamsCompleted` that needs updating, we'd need to scan all bindings. By building `def_to_upstreams` once at the start (O(n)), we get O(1) lookups for each deferred binding instead of O(n) per binding.

---

## Debugging Tips

### Bindings Not Created

If tests fail because bindings don't exist:
- Check that `process_deferred_bound_names` is being called
- Add debug prints in `finalize_bound_name` to see what's being processed

### First-Use Not Detected

If loop tests still fail:
- Print the binding chain for the phi node - is it actually a `Forward`?
- Check that `follow_to_partial_type` is correctly following the chain
- Verify the `FirstUse` enum is being updated via `mark_first_use`
- Check that `extend_first_uses_of_partial_type` is being called to update `PartialTypeWithUpstreamsCompleted`
- Verify `def_to_upstreams` contains the expected mapping

### Cycle Panics

If you see cycle-related issues:
- The `SmallSet` in `follow_to_partial_type` should catch cycles
- Check if you're accidentally creating circular forwards

---

## Questions for Review / Answers from Tech Lead

1. Is the two-pass approach acceptable, or is there a simpler way?
   **Answer**: The two-pass complexity is acceptable.

2. Should we maintain an index for looking up PartialTypeWithUpstreamsCompleted from Definition idx?
   **Answer**: Yes - the `current_idx` from `Usage::CurrentIdx` is always a `Key::Definition` (the raw binding idx), never a `PartialTypeWithUpstreamsCompleted`. So every lookup would require a linear scan. The solution is to build a `def_to_upstreams: HashMap<Idx<Key>, Idx<Key>>` index upfront via `build_definition_to_upstreams_index()`, which does a single O(n) scan and then provides O(1) lookups.

3. Are there any edge cases with `Usage::narrowing_from()` that need special handling?
   **Answer**: Yes - narrowing requires special handling. The semantics are:
   - Narrowing does NOT claim first-use (always marks `DoesNotPin` when `Undetermined`)
   - If the upstream is already `UsedBy(enclosing_idx)` where `enclosing_idx` matches the narrowing's enclosing binding, this is a "secondary read" and should forward to unpinned
   - Otherwise, forward to pinned

   This is consistent with the existing secondary-read logic in `detect_first_use` (lines 1002-1016 of `bindings.rs`).

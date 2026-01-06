# Transactional Var Pinning: Design Notes

This document provides a design for eliminating nondeterminism in Pyrefly's type inference
by isolating cycle resolution to individual threads.

**Companion documents:**
- `worked-example.md` - Detailed trace of A → B → A cycle showing exact call sequence
- `review-feedback.md` - Corrections and clarifications based on code review

---

## Problem Statement

Pyrefly has nondeterminism issues stemming from `Type::Var` values leaking to global storage
before they're fully resolved. When answers are computed using unresolved `Var` placeholders,
the results may differ from what you'd get with the final resolved types.

**Root cause:** Non-idempotent computation. Computing with placeholders produces different
results (and errors) than computing with final types.

---

## High-Level Approach

### The Three-Value Model

For each cycle with break_at idx B, there are three types:

1. **T_B0** (placeholder): `Any` or `Variable::Recursive`, stored when cycle detected
2. **T_B1** (tentative final): Result of first traversal using T_B0, **committed to global**
3. **T_B2** (stability check): Result of second traversal using T_B1, **diagnostic only**

### The Core Invariant

**Pass N for the cycle uses Pass N-1 result for break_at**

This ensures all bindings in the cycle observe a consistent value for break_at: the Pass N-1
result. This is why T_B1 (not T_B2) is committed—D, E, F were all computed using T_B1, so
using T_B2 would create inconsistency between break_at's type and its dependencies' types.

### Two-Pass Protocol

**Pass 1 (Tentative Computation):**
- Store T_B0 in `Cycle.preliminary_answers`
- Call `K::solve(break_at)` → computes T_B1
  - Dependencies call `get_idx()` → see T_B0 for recursion
  - Other bindings D, E, F... computed and stored in `preliminary_answers`
- Commit T_B1 to global `Calculation`
- Clear `preliminary_answers`

**Pass 2 (Canonical Computation):**
- Call `K::solve(break_at)` → computes T_B2
  - Dependencies call `get_idx()` → see T_B1 from global
  - Other bindings D, E, F... recompute using T_B1
  - Write D, E, F to global `Calculation`
- Compare T_B2 to T_B1
  - If different: warn "unstable cycle resolution"
  - Keep T_B1 (discard T_B2)

**Result:** All bindings in the cycle are based on T_B1 (consistent).

---

## Architecture

### Component 1: PreliminaryAnswers (Per-Cycle)

**Location:** `pyrefly/lib/alt/answers_solver.rs`

**Structure:**
```rust
pub struct Cycle {
    break_at: CalcId,
    recursion_stack: Vec<CalcId>,
    unwind_stack: Vec<CalcId>,
    unwound: Vec<CalcId>,
    detected_at: CalcId,
    preliminary_answers: PreliminaryAnswers,  // NEW: Per-cycle storage!
}

struct PreliminaryAnswers(RefCell<Option<SmallMap<ModuleInfo, SparseAnswerTable>>>);
```

**Why the `Option` wrapper?**

The `Option` serves two purposes:
1. **Lazy initialization**: Most computations aren't in cycles, so `None` short-circuits lookups
   without allocating the map.
2. **Clear semantics**: After pass 1, `clear()` sets it to `None`, making it explicit that
   preliminary storage is inactive.

**Key design decisions:**

1. **Per-cycle ownership**: Each `Cycle` owns its `PreliminaryAnswers`. When cycle pops,
   storage is automatically cleaned up.

2. **Natural lifecycle**:
   - Cycle created → PreliminaryAnswers created
   - Pass 1 completes → PreliminaryAnswers cleared
   - Cycle pops → PreliminaryAnswers destroyed

3. **Nested cycle support**: Lookup checks innermost cycle first, then outer cycles, then
   global:
   ```rust
   fn get_preliminary<K>(&self, idx: Idx<K>) -> Option<Arc<K::Answer>> {
       for cycle in self.cycles().iter().rev() {  // Innermost to outermost
           if let Some(answer) = cycle.preliminary_answers.get_idx(self.module(), idx) {
               return Some(answer);
           }
       }
       None  // Fall through to global
   }
   ```

4. **Cross-module aware**: Uses `(ModuleInfo, Idx<K>)` keys. Works for cross-module cycles
   because `ThreadState` (which holds the `Cycles` stack) is already threaded across
   module boundaries.

**Terminology note:**
- **CalcId** = `(Bindings, AnyIdx)` - used for cycle detection in CalcStack (type-erased)
- **PreliminaryAnswers key** = `(ModuleInfo, Idx<K>)` - used for storage (typed)
- `Bindings` contains a reference to `ModuleInfo`, allowing conversion between representations

### Component 2: Store-Then-Solve Pattern

**The pattern for cycle breaking:**

```rust
// Store placeholder
cycle.preliminary_answers.record(idx, placeholder);

// Solve using that placeholder
let binding = self.bindings().get(idx);
let result = K::solve(self, binding, errors);  // Direct solve, NOT get_idx!
```

**Why this works:**
- `K::solve(binding)` computes the binding's dependencies via `get_idx(D)`, `get_idx(E)`, etc.
- Dependencies' `get_idx()` calls can return the placeholder (breaks recursion)
- Calling `K::solve()` directly bypasses the cache check that `get_idx()` would perform

**Key clarification:** Calling `K::solve()` directly on break_at bypasses `get_idx()`'s cache
check for B. B's dependencies still use `get_idx()`, which triggers fresh computation because
`preliminary_answers` was cleared, making them "not found."

**Used in:**
- Pass 1: Store T_B0, solve → T_B1
- Pass 2: Store T_B1 in global, solve → T_B2
- Fixpoint: Store T_Bi, solve → T_B(i+1)

### Component 3: No Explicit Participant Tracking

**An alternative approach** would track all bindings in the cycle: `Vec<(ModuleInfo, AnyIdx)>`.

**This design avoids that:** Recomputation happens **implicitly via dependency graph**.

When we call `K::solve(break_at)` in pass 2:
- B computes and calls `get_idx(D)`
- D not in global or preliminary → recomputes
- D calls `get_idx(E)` → E recomputes
- All dependencies naturally recompute

**No iteration needed.** No type erasure problem. The Rust call stack drives recomputation.

---

## Detailed Protocol

### Cycle Detection

```rust
// In get_idx(), check for cycle
match self.stack().current_cycle(current_id) {
    None => {
        // No cycle, proceed normally
    }
    Some(cycle_detection) => {
        // Cycle detected! Inform Cycles struct
        let state = self.cycles().on_cycle_detected(cycle_detection);

        match state {
            CycleState::Continue => {
                // We're part of a cycle but not the break point
                // Keep recursing (will hit BreakHere at minimal idx)
            }
            CycleState::BreakHere => {
                // WE are the break_at (minimal idx)
                // Create and store placeholder NOW
                let t_b0 = create_placeholder();  // Any or Variable::Recursive
                self.cycles().current().preliminary_answers.record(
                    self.module(),
                    idx_b,
                    t_b0.clone()
                );
                // Return placeholder to caller
                return promote_to_answer(t_b0);
            }
        }
    }
}
```

**Key clarification:** The placeholder is created and stored when we reach `BreakHere` (the
minimal idx in the cycle), not at the first detection point.

**See worked-example.md** for a detailed trace showing exactly when BreakHere triggers.

### Pass 1: Tentative Computation

```rust
// After creating placeholder, we're still in K::solve(B)
// Continue computation...
let t_b1 = /* B's computation completes, using T_B0 for recursion */

// Write T_B1 to global
calculation(B).record_value(t_b1);

// Clear preliminary answers
self.cycles().current().preliminary_answers.clear();

// At this point:
//   B → T_B1 (global)
//   D, E, F → nothing (were in preliminary, now cleared)
```

**Why clearing enables pass 2 recomputation:**

Clearing removes D, E, F from thread-local storage. When pass 2 calls `get_idx(D)`:
1. Check preliminary_answers → None (cleared)
2. Check global Calculation(D) → NotCalculated
3. Call `K::solve(D)` and write to global

Without clearing, D would be found in preliminary_answers, preventing recomputation.

### Pass 2: Canonical Computation

```rust
// Explicitly recompute B to get official answers for D, E, F
let binding_b = self.bindings().get(idx_b);
let t_b2 = K::solve(self, binding_b, errors);  // Direct solve, bypasses get_idx

// During K::solve(B):
//   B's computation calls self.get_idx(idx_d)
//   get_idx(D) flow:
//     1. Check preliminary_answers → None (cleared)
//     2. Check global Calculation(D) → NotCalculated
//     3. Call K::solve(D) and write result to global
//   D's computation calls self.get_idx(idx_b)
//   get_idx(B) flow:
//     1. Check preliminary_answers → None
//     2. Check global Calculation(B) → Calculated(T_B1)
//     3. Return T_B1
//   D completes → written to global
//   E, F follow same pattern...
//   B completes → t_b2

// Stability check
if t_b2 != t_b1 {
    emit_warning("Cycle resolution unstable at {:?}", idx_b);
}

// Keep T_B1 (already in global), discard T_B2
```

### Cycle Cleanup

```rust
// Pop cycle from stack
self.cycles().pop();

// PreliminaryAnswers automatically destroyed (owned by Cycle)
```

---

## Nested Cycles

**Scenario:**
```
C1: A → B (break at A)
  While computing B, detect:
  C2: B → D (break at B)
    While computing D, detect:
    C3: D → F (break at D)
```

**Cycles stack:**
```rust
[C1, C2, C3]  // C3 is innermost
```

**C3 Resolution:**
- Store T_D0 in C3.preliminary_answers
- Solve D → T_D1 (may use T_B0 from C2, T_A0 from C1)
- Write T_D1 to global
- Clear C3.preliminary_answers
- Solve D → T_D2, write F, compare
- Pop C3

**C2 Resolution (resumes):**
- B's computation continues (D now in global)
- Complete B → T_B1
- Write T_B1 to global
- Clear C2.preliminary_answers
- Solve B → T_B2, write D, E, compare
- Pop C2

**C1 Resolution (resumes):**
- A's computation continues (B now in global)
- Complete A → T_A1
- Write T_A1 to global
- Clear C1.preliminary_answers
- Solve A → T_A2, write B, C, compare
- Pop C1

**Precision loss:** If D depends on A (outer cycle), D's final type contains T_A0
(placeholder) which eventually becomes `Any`. This is acceptable: we solve one cycle at a
time, accepting precision loss for complex nested scenarios.

**Concrete example:**

```python
# Outer cycle C1
def a(x):
    return b(x)

def b(x):
    # Inner cycle C2 detected here
    return d(x)

def d(x):
    return b(x).upper()  # Also references a(x) from outer cycle
```

**C2 resolution (inner, break at b):**
- T_B0 = `Any` (placeholder)
- D computes: `b(x).upper()` with T_B0 → `Any.upper()` → error or `Any`
- D also calls `a(x)` → returns T_A0 from C1 (also `Any`)
- T_D1 = `Any` (committed during C2)

**C1 resolution (outer, break at a):**
- T_A1 might resolve to `str` based on usage elsewhere
- But D already committed with type `Any` (from C2)

**Result:** D's type is `Any` instead of the more precise `str -> str`.

**User-visible effect:**
```python
result = d("hello")
result.lower()  # Error: "lower not found on Any"
# Should work if d's type was str → str
```

**This is acceptable:** Deep nested cycles are rare. Users can add type annotations.

---

## How This Design Avoids Potential Pitfalls

### Pitfall #1: Complex Transaction Lifecycle
**Risk:** Explicit transaction `begin()` and `end()` calls are error-prone.
**Solution:** No explicit transaction! Cycle creation/destruction is the lifecycle. Begin = push
Cycle, end = pop Cycle. The existing `Cycle` struct naturally owns the transaction state.

### Pitfall #2: Tracking Cycle Participants
**Risk:** Tracking which bindings participate in a cycle requires invasive changes to
`record_value()` and introduces type erasure problems.
**Solution:** No participant tracking needed. Recomputation is lazy via dependency graph.
When we call `K::solve(break_at)` in pass 2, all dependencies naturally recompute.

### Pitfall #3: Cross-Module Recomputation
**Risk:** `AnswersSolver` is per-module—how to recompute bindings in other modules?
**Solution:** `K::solve(break_at)` naturally calls `get_idx()` for dependencies. Each
dependency recomputes in its own module's context as part of the dependency chain.
No special cross-module coordinator needed.

### Pitfall #4: Type Erasure with AnyIdx
**Risk:** Can't call `K::solve()` on type-erased `AnyIdx`, which would be needed if we
iterated over cycle participants.
**Solution:** No need to iterate type-erased participants. Only call `K::solve()` on
break_at, which has a known type. The call graph handles the rest.

### Pitfall #5: Heterogeneous Storage
**Risk:** Rust's type system makes it hard to store heterogeneous `Idx<K>` for iteration.
**Solution:** Don't store them for iteration. Only store in `PreliminaryAnswers` which uses
the `table!` macro for heterogeneous storage, same as global `Answers`. No new patterns needed.

### Pitfall #6: Error Collector Complexity
**Risk:** Tentative error suppression requires threading "tentative mode" through the entire
call chain.
**Solution:** Addressed in Phase 2 with a simpler approach: errors are stored exactly once
per binding—when the final `Calculation` result is recorded during pass 2. Pass 1 errors
are simply discarded. See "Implementation Phases" section.

### Pitfall #7: Invasive Protocol Changes
**Risk:** Cycle isolation could require rearchitecting the `Calculation` proposal/record
protocol.
**Solution:** Minimal changes. Only add:
  - PreliminaryAnswers to `Cycle` struct
  - Lookup precedence (preliminary before global)
  - Pass 2 solve call after pass 1

---

## Implementation Plan

The stages below map to the three implementation phases:
- **Stages 1-4**: Phase 1 (Isolation & Computation Order)
- **Stage 5**: Phase 2 (Error Determinism)
- **Stage 6**: Phase 3 (Simplification)

### Stage 1: Port PreliminaryAnswers Infrastructure

**Goal:** Get the basic storage working.

**Tasks:**
1. Port `SparseIndexMap` from uncommitted stack (commit 844f311)
2. Port `PreliminaryAnswers` struct (commit e74dd662)
3. Add `preliminary_answers: PreliminaryAnswers` to `Cycle` struct
4. Implement lookup cascade (check preliminary before global) in `get_idx()`
5. Add tests verifying preliminary lookups work

**Deliverable:** Infrastructure exists but isn't used yet (no cycle breaking changes).

**Success criteria:**
- Code compiles
- Tests pass
- No regressions

### Stage 2: Single-Cycle Prototype (2-3 weeks)

**Goal:** Get two-pass protocol working for single (non-nested) cycles.

**Tasks:**
1. Modify cycle detection to store placeholder in `Cycle.preliminary_answers`
2. After pass 1, write T_B1 to global, clear `preliminary_answers`
3. Implement pass 2: call `K::solve(break_at)` for stability check
4. Add warning if T_B1 != T_B2
5. Add tests with single-module, single-cycle scenarios

**Key challenge:** Figure out the exact sequence of calls for pass 2. Need to ensure:
- B is in global with T_B1
- D, E, F are NOT in global (were cleared)
- `K::solve(B)` actually recomputes (doesn't just return T_B1)

**Deliverable:** Single cycles are deterministic.

**Success criteria:**
- Tests with cycles show same results across runs
- Telemetry shows acceptable overhead (<10% slowdown)
- No deadlocks or correctness bugs

### Stage 3: Nested Cycles (2-3 weeks)

**Goal:** Handle nested cycles correctly.

**Tasks:**
1. Verify lookup cascade works for nested preliminary_answers
2. Add tests with nested cycles (C2 inside C1)
3. Add tests with cross-module cycles
4. Verify precision loss is acceptable (document examples)

**Deliverable:** Nested cycles are deterministic.

**Success criteria:**
- Tests with nested cycles show same results across runs
- No panics or infinite loops
- Precision loss is documented and acceptable

### Stage 4: Production Hardening (2-3 weeks)

**Goal:** Make it production-ready.

**Tasks:**
1. Add telemetry:
   - Cycle frequency and depth distribution
   - Instability warnings (how often T_B1 != T_B2)
   - Performance overhead
2. Handle edge cases:
   - Recursion limits during pass 2
   - Panics in `K::solve()`
   - Very large cycles (performance cliffs)
3. Documentation and code review
4. A/B testing on internal codebase

**Deliverable:** Ready to ship.

**Success criteria:**
- No known correctness bugs
- Performance acceptable (<20% slowdown in worst case)
- Telemetry shows nondeterminism is eliminated

### Stage 5: Error Determinism (Phase 2)

**Goal:** Store errors exactly once per binding.

**Tasks:**
1. Modify error collection to buffer errors during pass 1
2. Discard pass 1 errors after pass 1 completes
3. Record errors during pass 2 alongside `record_value()`
4. Verify errors reference T_B1, not T_B0

**Success criteria:**
- Error messages don't reference placeholder types
- Each binding's errors stored exactly once
- No duplicate or conflicting errors

### Stage 6: Simplification (Phase 3)

**Goal:** Simplify placeholder mechanism.

**Tasks:**
1. Evaluate whether `Variable::Recursive` is still needed
2. Evaluate whether `Variable::LoopRecursive` is still needed
3. If possible, replace `Recursive` with simple `Any` placeholder
4. If possible, replace `LoopRecursive` with loop prior as placeholder
5. Remove unused complexity from solver
6. Verify no regression in type quality

**Success criteria:**
- Simpler code (fewer Variable variants)
- Same or better type inference
- Determinism maintained

---

## Future Work: Fixpoint Iteration

The two-pass protocol can be extended to a fixpoint approach:

```rust
let mut t_prev = create_placeholder();
cycle.preliminary_answers.record(idx, t_prev);

let binding = self.bindings().get(idx);
let errors = &self.error_collector;

for iteration in 1..=MAX_ITERATIONS {
    let t_curr = K::solve(self, binding, errors);

    if t_curr == t_prev {
        // Converged!
        global.record_value(idx, t_curr);
        break;
    }

    // Store for next iteration
    cycle.preliminary_answers.record(idx, t_curr);  // Overwrite
    t_prev = t_curr;
}

if !converged {
    warn!("Cycle did not converge in {MAX_ITERATIONS} iterations");
    global.record_value(idx, t_prev);  // Best effort
}

// Pass N+1: Official computation for rest of cycle
cycle.preliminary_answers.clear();
K::solve(self, binding, errors);  // Writes all dependencies to global
```

**Differences from two-pass:**
- Iterations store results in `preliminary_answers` (not global)
- Final converged result commits to global
- Last pass (N+1) computes official answers for dependencies

**Benefits:**
- Better precision (more iterations to refine types)
- Explicit convergence detection

**Costs:**
- More computation (N iterations instead of 2)
- Complexity (need to define equality, MAX_ITERATIONS)

**Recommendation:** Ship two-pass first, add fixpoint later based on telemetry showing
instability warnings are frequent.

---

## Implementation Phases

The implementation is divided into three phases, each building on the previous:

### Phase 1: Isolation & Computation Order

**Goal:** Get cycle isolation and the two-pass protocol working correctly.

**Focus:**
- Implement PreliminaryAnswers and per-cycle storage
- Establish correct computation order (pass 1 with placeholder, pass 2 with T_B1)
- Ensure answers are only visible to the resolving thread during cycle resolution
- Keep `Variable::Recursive` as-is for placeholders

**Error handling:** Deferred entirely. Errors may still reference unsolved Vars—that's
acceptable for this phase. The goal is to prove the isolation and computation order work.

**Success criteria:**
- Cycle answers are deterministic across runs
- No Var leakage to other threads during resolution
- Pass 2 correctly recomputes dependencies

### Phase 2: Error Determinism

**Goal:** Ensure errors are stored exactly once per binding, when the final result is recorded.

**Focus:**
- Errors from pass 1 (tentative computation) are discarded
- Errors from pass 2 (canonical computation) are kept and stored with the `Calculation`
- Each binding's errors are recorded exactly once: when `record_value()` commits to global

**Key insight:** By only storing errors during pass 2, we ensure errors are based on T_B1
(the committed type), not T_B0 (the placeholder). This makes errors more meaningful.

**Note:** This doesn't guarantee errors are completely Var-free. In edge cases (especially
with nested cycles referencing outer placeholders), some Vars may still appear. But the
architecture makes Var-free errors the common case.

**Success criteria:**
- Errors reference resolved types, not placeholders
- Each binding's errors stored exactly once
- Error messages are meaningful and actionable

### Phase 3: Simplification

**Goal:** Simplify the placeholder mechanism now that isolation and error handling are solid.

**Focus:**
- Revisit `Variable::Recursive` and evaluate if it's still needed
- Revisit `Variable::LoopRecursive` similarly (use loop prior as placeholder instead)
- Goal: Replace with simpler placeholders (e.g., `Any` for recursive, loop prior for loops)
- Remove complexity that was only necessary for the old non-isolated approach

**Rationale:** With phases 1 and 2 working, the placeholder's job is simpler. It just needs
to break recursion during pass 1. We don't need sophisticated recursive type handling if
we're always recomputing in pass 2 with the real type.

**Success criteria:**
- Simpler codebase (fewer Variable variants or simpler handling)
- No regression in type inference quality
- Maintained determinism guarantees

---

## Open Questions

### Q1: Verify Pass 2 Recomputation Mechanism

Pass 2 calls `K::solve(B)` directly (not `get_idx(B)`). This should work because:

1. `K::solve(B)` computes B's dependencies via `get_idx(D)`, `get_idx(E)`, etc.
2. D, E, F are NOT in global (preliminary was cleared)
3. `get_idx(D)` sees NotCalculated → calls `K::solve(D)` → writes to global
4. Fresh computation triggered for all dependencies

**No special forcing mechanism needed.** The cleared preliminary_answers naturally causes
recomputation.

**To verify in Stage 2:** Add telemetry to confirm dependencies are recomputed (not cached).
Check that the number of solve calls matches expectations.

### Q2: What About LoopRecursive?

`Variable::LoopRecursive` is used for loop Phi nodes. Does it need the same two-pass
treatment as `Variable::Recursive`?

**Answer:** Yes, `LoopRecursive` variables are only created when we encounter a cycle, so
they are relevant to this design.

**Phases 1 and 2:** Leave `LoopRecursive` handling as-is, same as `Recursive`. The two-pass
protocol applies equally—we're just isolating and recomputing, regardless of the placeholder
type.

**Phase 3:** As part of simplification, we'll likely remove `Variable::LoopRecursive` entirely
and use a simple placeholder. The key difference from `Recursive`: instead of using `Any` as
the placeholder (T_B0), we use the **loop prior** as the initial guess. This preserves the
loop's type refinement behavior while eliminating the `LoopRecursive` variant.

### Q3: Control Flow Divergence in Pass 2

What if T_B1 changes control flow vs T_B0, causing pass 2 to discover different cycles?

**Example:**
```python
def b(x):
    if isinstance(x, SomeClass):
        return d(x)  # Cycle C2
    else:
        return e(x)  # Different cycle C3
```

**Pass 1:** T_B0 = `Any`, takes `else` branch → C3
**Pass 2:** T_B1 = `SomeClass`, takes `if` branch → C2

**Answer:** This is fine. Pass 2 uses the same cycle detection protocol as pass 1:
- C2 is detected during pass 2
- Nested cycle protocol applies (store placeholder, solve, commit)
- C2 completes before B's pass 2 finishes
- Final result: B's dependencies based on C2 (from pass 2), not C3 (from pass 1)

**Key insight:** The pass 2 result determines the official results for B's dependencies. If
pass 2 discovers different cycles, those cycles' results are final. This is still consistent:
all of C2's bindings see the same value for B (T_B1 from pass 2's context).

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pass 2 recomputation mechanism is tricky | Medium | High | Prototype in Stage 2, design carefully |
| Performance overhead is unacceptable | Low | High | Telemetry in Stage 2, optimize if needed |
| Nested cycles have edge cases | Medium | Medium | Extensive testing in Stage 3 |
| Error buffering adds complexity (Phase 2) | Medium | Medium | Keep simple: discard pass 1 errors entirely |
| Variable::Recursive removal breaks edge cases (Phase 3) | Low | Medium | Keep as fallback if simplification fails |
| Rust borrow checker issues with Cycle ownership | Low | Medium | Refactor if needed |

**Overall risk:** **Medium**. The design is straightforward, but pass 2 mechanics need
careful implementation.

**Estimated probability of success:** **80%**.

---

## Design Strengths

**Simplicity:**
- No explicit transaction state management
- No explicit participant tracking
- No cross-module coordinator
- No type-preserving closures

**Correctness:**
- Lazy recomputation via dependency graph (can't miss participants)
- Per-cycle storage (automatic cleanup on pop)
- Store-then-solve pattern (clear recursion breaking)

**Performance:**
- Only 2 full traversals per cycle
- No overhead when not in cycles (common case)

**Implementation:**
- Builds on existing `Cycle` infrastructure
- Minimal changes to `get_idx()` logic
- No new global state

---

## Conclusion

This design achieves cycle determinism through:
1. Moving PreliminaryAnswers to per-cycle ownership
2. Using lazy dependency-driven recomputation
3. Establishing the pass-N-uses-pass-N-1 invariant

**Next step:** Implement Stage 1 (port infrastructure).

**Expected outcome:** Eliminates nondeterminism in cycle resolution, making Pyrefly's type
inference predictable and deterministic.

# Transactional Var Pinning: Design Notes v2

This document provides a refined design for eliminating nondeterminism in Pyrefly's type
inference, incorporating insights from the v1 prototype attempt and subsequent design
discussions.

**Companion documents:**
- `v2-worked-example.md` - Detailed trace of A → B → A cycle showing exact call sequence
- `v2-review-feedback.md` - Corrections and clarifications based on code review

---

## Changes from v1

**Major simplifications:**
- PreliminaryAnswers lives in `Cycle` struct (not top-level ThreadState)
- No explicit participant tracking needed
- No eager recomputation iteration needed
- Store-then-solve pattern for cycle breaking
- Two-pass protocol with clear invariant: pass N uses pass N-1 result for break_at

**Key insight from v1:** The uncommitted stack already solved cross-module storage by
putting PreliminaryAnswers in ThreadState. The remaining challenge was recomputation,
which v2 solves via lazy dependency-driven recomputation instead of eager iteration.

---

## Problem Statement (unchanged from v0)

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

**v1 tried to track:** `Vec<(ModuleInfo, AnyIdx)>` of all bindings in cycle.

**v2 realizes:** Don't need it! Recomputation happens **implicitly via dependency graph**.

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

**See v2-worked-example.md** for a detailed trace showing exactly when BreakHere triggers.

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

## How This Eliminates v1 Stuck Points

### Stuck Point #1: Transaction Lifecycle Triggers
**v1 problem:** When to call `transaction.begin()` and `end()`?
**v2 solution:** No transaction! Cycle creation/destruction is the lifecycle. Begin = push
Cycle, end = pop Cycle.

### Stuck Point #2: Participant Tracking Without Idx
**v1 problem:** `record_value()` doesn't have `Idx` for tracking participants.
**v2 solution:** No participant tracking needed. Recomputation is lazy via dependency graph.

### Stuck Point #3: Cross-Module Recomputation
**v1 problem:** `AnswersSolver` is per-module, how to recompute cross-module?
**v2 solution:** `K::solve(break_at)` naturally calls `get_idx()` for dependencies. Each
dependency recomputes in its own module's context as part of the dependency chain.

### Stuck Point #4: Type Erasure (AnyIdx)
**v1 problem:** Can't call `K::solve()` on type-erased `AnyIdx`.
**v2 solution:** No need to iterate type-erased participants. Only call `K::solve()` on
break_at, which has a known type.

### Stuck Point #5: Rust Type System Limits
**v1 problem:** Hard to store heterogeneous `Idx<K>` for iteration.
**v2 solution:** Don't store them. Only store in `PreliminaryAnswers` which uses the `table!`
macro for heterogeneous storage, same as global `Answers`.

### Stuck Point #6: Error Collector Architecture
**v1 problem:** Need tentative error suppression.
**v2 solution:** **Defer to future work.** Ship without error determinism first. Errors
during pass 1 may be imprecise (reference placeholders), but they're deterministic because
each thread resolves cycles independently.

### Stuck Point #7: Cycle Protocol Integration
**v1 problem:** Existing logic tightly coupled to global `Calculation`.
**v2 solution:** Minimal changes. Only add:
  - PreliminaryAnswers to `Cycle` struct
  - Lookup precedence (preliminary before global)
  - Pass 2 solve call after pass 1

---

## Implementation Plan

### Stage 1: Port PreliminaryAnswers Infrastructure (1 week)

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

**Total timeline:** 7-10 weeks (1.5-2.5 months)

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

## Error Handling (Deferred)

**v1 proposed:** Suppress type errors during pass 1, only emit during pass 2.

**v2 defers this:** Error determinism is orthogonal to cycle determinism. Ship without error
suppression first.

**Current behavior:** Errors emitted during pass 1 may reference placeholders (T_B0). This
produces deterministic but potentially confusing errors.

**Future work:** Add error suppression via:
1. `ErrorCollector.set_tentative(true)` during pass 1
2. Classify errors as fatal (recursion limit) vs suppressible (type mismatch)
3. Only emit errors during pass 2 (canonical computation)

**Estimated effort:** 1-2 weeks after core cycle determinism is working.

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

**Hypothesis:** Loops are intra-binding (not cross-binding), so they don't form cycles in
the binding graph. `LoopRecursive` might not need changes.

**Needs investigation** in Stage 2.

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
| Error handling is too invasive | Low | Low | Defer to future work |
| Rust borrow checker issues with Cycle ownership | Low | Medium | Refactor if needed |

**Overall risk:** **Medium**. The design is much simpler than v1, but pass 2 mechanics need
careful implementation.

**Estimated probability of success:** **80%** (much higher than v1's 40%).

---

## Why v2 is Better Than v1

**Simplicity:**
- No transaction state management
- No explicit participant tracking
- No cross-module coordinator
- No type-preserving closures

**Correctness:**
- Lazy recomputation via dependency graph (can't miss participants)
- Per-cycle storage (automatic cleanup on pop)
- Store-then-solve pattern (clear recursion breaking)

**Performance:**
- Only 2 full traversals per cycle (not 3)
- No overhead when not in cycles (common case)

**Implementation:**
- Builds on existing `Cycle` infrastructure
- Minimal changes to `get_idx()` logic
- No new global state

---

## Conclusion

The v2 design solves all the stuck points from v1 by:
1. Moving PreliminaryAnswers to per-cycle ownership
2. Using lazy dependency-driven recomputation
3. Establishing the pass-N-uses-pass-N-1 invariant

**Next step:** Implement Stage 1 (port infrastructure).

**Estimated timeline:** 7-10 weeks for production-ready implementation.

**Expected outcome:** Eliminates nondeterminism in cycle resolution, making Pyrefly's type
inference predictable and deterministic.

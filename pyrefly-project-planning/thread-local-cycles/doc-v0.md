# Transactional Var Pinning: Design Notes v0

## Motivation

Pyrefly has nondeterminism issues stemming from `Type::Var` values leaking to
global storage before they're fully resolved. This affects two areas:

### 1. Partial Type Inference

When a variable is initialized with incomplete type information (e.g., `x = []`),
Pyrefly creates a `Variable::PartialContained` placeholder that should be
"pinned" to a concrete type based on first use (e.g., `x.append(1)` pins the
element type to `int`).

The current implementation uses a "trap" pattern with multiple binding nodes
(`CompletedPartialType`, `PartialTypeWithUpstreamsCompleted`) to isolate partial
types until they're pinned. This works but adds complexity.

### 2. Cycle Handling

When bindings form a cycle (A depends on B, B depends on A), Pyrefly creates
`Variable::Recursive` placeholders to break the cycle. These placeholders can
be constrained during cycle resolution, but:
- If cycles aren't thread-isolated, different threads may race to constrain the
  same Var, causing nondeterminism
- Even with thread isolation, the final type depends on cycle traversal order,
  which isn't predictable to users or developers

### The Unified Problem

Both cases involve the same underlying issue: **intermediate answers containing
unresolved `Var`s leak to global storage**, where they can be seen by other
threads or influence computation in order-dependent ways.

## The Core Problem: Non-Idempotent Computation

When answers are computed using unresolved `Var` placeholders, the results may
differ from what you'd get with the final resolved types. Example:

```python
def f(x: T) -> T: ...
y = f([])  # During cycle: f(list[@0]) -> list[@0]
           # After resolution: f(list[int]) -> list[int]
```

If `y`'s answer is computed with `list[@0]` and written to global storage,
another thread computing `y` with the resolved `list[int]` would get a different
result. This causes nondeterminism.

The same applies to **errors**: computation with `list[@0]` might produce no
error (Vars are compatible with anything) or a vague error about type variables,
while computation with `list[int]` produces concrete, actionable errors. This
can lead to nondeterminism even in cases where the `Var` is always pinned to the same
type, because depending on race conditions a binding might sometimes only be computed
once (getting the `Var`) or sometimes be computed twice (with once case getting the
final answer), producing different type errors that are not deduplicated.

**Key insight**: We can't just batch writes to global storage. We need to:
1. Treat computations with unresolved `Var`s as *tentative*
2. Discard tentative answers after `Var` resolution
3. Recompute affected bindings with final types
4. Only then commit to global storage

## Scope Considerations

### Partial Type First-Use Chains
- First-use chains are intra-module only (first use must be in same module as
  the partial assignment)
- Chains are typically short (1-2 bindings)

### Cycles
- Can be cross-module
- Can be arbitrarily long and arbitrarily nested
- Empirically, large cycles and deeply nested cycles are rare
- Recomputation cost is proportional to cycle size, so rare large cycles are
  acceptable

## High-Level Approach: Transactional Preliminary Answers

### Phase 1: Tentative Computation
When we enter a context that creates `Var`s (partial assignment, cycle):
- Start a "transaction" (if not already in one)
- All answers computed during this phase go to thread-local `PreliminaryAnswers`
- These answers may contain unresolved `Var`s
- The primary purpose is **constraint discovery**, not final answers

### Phase 2: Var Resolution
When the outermost transaction scope completes:
- Pin all remaining partial `Var`s to their defaults (e.g., `Any`)
- Recursive `Var`s should already be resolved by cycle unwinding

### Phase 3: Recomputation
- Discard all tentative answers from Phase 1
- Recompute each affected binding using the now-resolved types
- This produces the canonical, deterministic answers

### Phase 4: Commit
- Write all recomputed answers to global storage atomically
- Other threads now see consistent, `Var`-free answers

## Transaction Mechanics

### When to Start a Transaction
- When solving a binding that produces partial `Var`s in the result
- When cycle detection creates a `Variable::Recursive` placeholder
- Nested starts increment a depth counter (don't create new transaction)

### When to Commit
- When the outermost transaction scope exits
- For partial types: when the binding producing partial Vars completes
- For cycles: when `Cycles::on_calculation_finished` indicates cycle resolution

### What Gets Tracked
- All `Idx<Key>` that have answers written during the transaction
- The module info for each (for cross-module cycles)
- Possibly: which `Var`s each answer depends on (for selective recomputation)

## Why Thread-Local Var Resolution Isn't Sufficient

An alternative idea was considered: keep `Var` solutions thread-local during a
transaction, then merge on commit. This would mean answers could be written to
global storage immediately (computed with the thread's view of Var solutions).

However, this doesn't eliminate the need for:

1. **PreliminaryAnswers**: We still need somewhere to store intermediate answers
   during cycle traversal. When solving a cycle, we need to look up partially-
   computed answers for bindings we've already visited. Thread-local Var storage
   doesn't provide this.

2. **Recomputation**: Even if Vars were thread-local, the answers computed with
   `Type::Var` placeholders are still inferior to those computed with resolved
   types. This is especially true for **errors** (see "Non-Idempotent Computation"
   above).

Thread-local Var resolution might help with constraint conflict races (two
threads constraining the same Var differently), but it's orthogonal to the
core problem of non-idempotent computation.

## Two Distinct Mechanisms

### 1. PreliminaryAnswers: Graph Traversal During Cycles

**Purpose**: Store intermediate answers so cycle traversal can look up bindings
that are currently being computed.

**Behavior**:
- Thread-local storage keyed by `(ModuleInfo, Idx<Key>)`
- `get_idx` checks preliminary before global
- Enables recursive lookups during cycle resolution

**Note**: `PreliminaryAnswers` does not exist on trunk. It was implemented in an
uncommitted stack (ending in commit 93fe16001d) as an extension to `ThreadState`.
The implementation provides the infrastructure described here, but the stack was
not landed due to nondeterminism issues that this document aims to address.

To inspect the implementation:
```bash
sl show 93fe16001d  # View the commit
sl cat -r 93fe16001d pyrefly/lib/alt/answers_solver.rs  # View the file at that commit
```
The commits are also available as drafts on Phabricator.

### 2. Transactional Commit: Isolation from Global Storage

**Purpose**: Prevent other threads from seeing answers computed with unresolved
`Var`s.

**Behavior**:
- All answers during a transaction go to PreliminaryAnswers (never global)
- On commit: discard tentative answers, recompute with resolved types, write to
  global
- Errors from tentative phase are also discarded

**Key insight**: The tentative phase is purely for:
- Constraint discovery (pinning Vars)
- Enabling graph traversal (via PreliminaryAnswers lookups)

The actual answers and errors from this phase are **throwaway work**.

## Transaction Lifecycle

```
1. BEGIN TRANSACTION (on first Var-producing computation)
   - Set transaction depth = 1
   - PreliminaryAnswers becomes the write target

2. TENTATIVE PHASE (constraint discovery)
   - Compute answers, write to PreliminaryAnswers
   - Answers may contain Var placeholders
   - Errors are collected but marked as tentative
   - Lookups check PreliminaryAnswers first (enables cycle traversal)

3. VAR RESOLUTION
   - When outermost scope completes, pin remaining Vars
   - All Vars in the transaction are now Answer(concrete_type)

4. RECOMPUTATION PHASE
   - Clear PreliminaryAnswers
   - Re-solve all bindings that were part of the transaction
   - Now using resolved types, producing canonical answers and errors
   - Write results back to PreliminaryAnswers

5. COMMIT
   - Move all PreliminaryAnswers entries to global storage
   - Clear PreliminaryAnswers
   - Transaction depth = 0
```

### What Gets Recomputed?

We need to track which `Idx<Key>` were solved during the tentative phase:

```rust
struct TransactionState {
    depth: usize,
    participants: Vec<(ModuleInfo, Idx<Key>)>,  // Bindings to recompute
}
```

On recomputation, we iterate `participants` and re-solve each binding.

### Error Handling

Errors should be **buffered per-computation and committed atomically with the
answer**. This applies to all bindings, not just those in cycles:

1. Every binding computation collects errors into a temporary buffer
2. When `record_value` succeeds (this thread wins the race), transfer errors
   to permanent storage
3. When `record_value` loses (another thread already wrote), discard the
   temp errors along with the discarded answer

This ensures:
- Errors always correspond to the stored answer (same computation)
- No duplicate errors from racing threads, even without deduplication
- Deduplication becomes a safety net, not the primary mechanism

For cycles specifically, the tentative phase uses a throwaway error collector
entirely (those errors are discarded regardless of who wins). Only the
recomputation phase collects errors that may be committed.

**Important distinction**: Only *type errors* (subset failures, missing
attributes, etc.) should be suppressed during tentative phase. *Fatal errors*
(recursion depth limits, internal logical inconsistencies) should still
propagate immediately. This prevents the system from spinning on a doomed
calculation during the tentative phase.

### State Hygiene (RAII)

The `PreliminaryAnswers` cleanup (clearing the map) must happen in an RAII guard
or equivalent. If the tentative phase panics or returns early, we must guarantee
that thread-local storage doesn't leak tentative answers into subsequent
unrelated calculations on the same thread.

```rust
// Example pattern
let _guard = scopeguard::guard((), |_| {
    self.thread_state.preliminary_answers.clear();
});
```

## Refined Cycle Resolution Protocol

This section details a proposed approach to cycle resolution that avoids the
current issues with `Var::Recursive` and shared global state.

### Current Approach (Problems)

1. Duplicate idx detected → pick minimal idx to break cycle
2. Create `Var::Recursive` placeholder stored in global `Calculation`
3. Resume computation with many duplicate stack frames
4. Use `Calculation` to communicate preliminary results across threads
5. Threads can race to constrain the shared `Var` → nondeterminism

### Proposed Approach

**CYCLE DETECTED** (duplicate idx found in `CalcStack`):

```
1. Determine minimal idx to break cycle (existing logic)

2. Create placeholder (Type::Any) for minimal idx
   → Store in thread-local PreliminaryAnswers (NOT global Calculation)
   → Keep global Calculation in Calculating state (no placeholder stored)

3. Set ThreadState.in_cycle = true
   - All answers → PreliminaryAnswers
   - All errors → throwaway collector
```

**FIRST PASS** (constraint discovery / tentative computation):

```
4. Compute minimal idx
   - Goes around the cycle using placeholder for the minimal idx
   - Other bindings in cycle see placeholder via PreliminaryAnswers
   - Tentative answers stored in PreliminaryAnswers

5. Capture final type for minimal idx (call it T1)

6. Clear all PreliminaryAnswers for cycle participants
   - Only keep T1 for the minimal idx

7. Set ThreadState.in_cycle = false
```

**SECOND PASS** (canonical computation):

```
8. Try to record_value(T1) for minimal idx in global Calculation
   - If we WIN: proceed to step 9
   - If we LOSE (another thread beat us): use their answer, discard our work

9. Restart computation of minimal idx (if we won)
   - Now minimal idx has real answer in global storage
   - Other cycle participants look it up → no cycle detected
   - Each binding computes its final answer, stored to global
   - Errors collected in temp buffer

10. Transfer temp errors to real ErrorCollector

11. (Optional) Compare second-pass answer to T1
    - If different: emit diagnostic about unstable cycle resolution
    - Use T1 for consistency (it's already recorded)
```

### Key Properties

1. **No global placeholder**: `Var::Recursive` is not stored in `Calculation`.
   The placeholder lives only in thread-local `PreliminaryAnswers`.

2. **Thread isolation**: Each thread resolves cycles independently. Racing
   threads don't share Var constraints.

3. **First-writer-wins**: The first thread to `record_value` for the minimal
   idx wins. Other threads discard their work.

4. **Cycle "breaks" on second pass**: Once minimal idx has a real answer in
   global storage, the cycle no longer exists from the perspective of other
   bindings—they just see a computed value.

5. **Consistent errors**: Errors are buffered and only committed by the
   winning thread, ensuring they match the stored answer.

### Concurrency Model: Optimistic Fine-Grained

This approach uses **optimistic locking** at a fine granularity:

1. **No actual locks**: Threads are allowed to race and duplicate work. There
   is no blocking; threads proceed independently and only one writes final
   results. This eliminates deadlock risk.

2. **Fine-grained scope**: The "conflict domain" is per-cycle, not per-module
   or global. This means:
   - Other bindings in the same module proceed in parallel
   - Disjoint cycles in the same module proceed in parallel
   - Only threads working on the *same* cycle may duplicate work

3. **Bounded waste**: The worst case is two threads doing the same cycle work.
   Since cycles are typically small, the wasted work is bounded. And the
   winning thread's result is correct and deterministic.

4. **No coordination overhead**: Threads don't need to communicate during cycle
   resolution. They only "coordinate" at the moment of `record_value`, which is
   already an atomic operation.

### Interaction with Existing Infrastructure

- **`Calculation.propose_calculation()`**: Still returns `CycleDetected` when
  same thread hits same idx. But we don't call `record_cycle` to store a
  placeholder globally.

- **`Calculation.record_cycle()`**: Becomes dead code. The recursive placeholder
  is no longer stored in global `Calculation`; it lives in thread-local
  `PreliminaryAnswers` instead.

- **`Status::Calculating`**: Currently stores `Box<(Option<R>, SmallSet<ThreadId>)>`
  where `Option<R>` is the recursive placeholder. With `record_cycle` removed,
  this can simplify to just `Box<SmallSet<ThreadId>>`.

- **`Cycles` struct**: Still tracks cycle detection and determines minimal idx.
  The change is what we do *after* detection.

- **`CalcStack`**: Still tracks the current computation path for cycle
  detection.

- **`PreliminaryAnswers`**: Becomes the exclusive home for tentative answers
  during cycle resolution. `get_idx` checks it before global storage.

## Opportunity: Eliminate Recursive Variable Variants

With transactional preliminary answers, we may be able to eliminate
`Variable::Recursive` and `Variable::LoopRecursive` entirely.

### `Variable::LoopRecursive` → Preliminary Answer with Loop Prior

**Current behavior**:
```rust
Variable::LoopRecursive(prior_type, loop_bound)
```
- Created during loop analysis (e.g., `x = 1; while cond: x = f(x)`)
- Lookups see the Var, which expands to the prior type
- Fixed-point detection uses the `LoopBound`

**Proposed behavior**:
- Store `prior_type` directly as the preliminary answer (no Var)
- Lookups during tentative phase see `prior_type`
- Fixed-point detection happens in loop-solving logic, not in Variable
- On recompute: store the final widened type

**Benefits**:
- No Var indirection
- Same semantics (lookups see prior, final answer is widened)
- Simpler mental model

**Potential edge cases**:
- False negatives: if current logic sometimes propagates constraints through
  `LoopRecursive` Vars in ways that affect the final type, we might lose that.
  But this seems unlikely - loop widening is structural, not constraint-based.

### `Variable::Recursive` → Preliminary Answer with `Any`

**Current behavior**:
```rust
Variable::Recursive
```
- Created when cycle is detected in binding graph
- Acts as a placeholder that can unify with other types
- **Can be constrained** by generic calls or other type operations
- This constraint-based pinning is **ordering-dependent**

**Proposed behavior**:
- Store `Type::Any` as the preliminary answer (no Var)
- Lookups during tentative phase see `Any` (compatible with everything)
- On recompute: actual type is available, no `Any` in final answer
- **Deliberate behavior change**: constraints during cycle resolution no longer
  affect the final type

**Why this is better**:

The current constraint-based pinning of `Var(Recursive)` has two problems:

1. **Nondeterminism** (if cycles aren't thread-isolated): If multiple threads
   race to resolve the same cycle, they may constrain Vars differently depending
   on timing. Transaction isolation fixes this.

2. **Unpredictability** (even with thread isolation): The pinning depends on
   cycle traversal order, which isn't obvious to users or developers. Cycles
   aren't always apparent in code, and the order bindings are evaluated isn't
   something humans can easily predict.

These are distinct issues:
- **Nondeterminism** = different runs produce different results
- **Unpredictability** = results depend on opaque implementation details

Transaction isolation solves (1). Replacing `Recursive` with `Any` solves (2)
by making the rule simple: **binding types come from definitions, not from
constraint side effects during cycle resolution**.

With the new approach:
- Cycles are about mutual recursion in *definitions*
- If you want usage to influence type, that's partial type inference (first-use)
- The separation is cleaner and more principled
- Users can reason about types without understanding cycle traversal order

**Potential behavior changes**:

Some code that currently relies on constraint-based pinning during cycles would
behave differently. For example:

```python
def f(x): return g(x)
def g(x): return f(x).method()  # Currently might pin x via .method()
```

With the new approach, `x` would not be pinned by the `.method()` call during
cycle resolution. This is arguably more correct - the cycle should be resolved
based on the function signatures, not ordering-dependent method calls.

### Simplified Variable Enum

If this works, `Variable` becomes:

```rust
enum Variable {
    // Partial type inference (need pinning)
    PartialContained,
    PartialQuantified(Box<Quantified>),

    // Type parameters (instantiation)
    Quantified(Box<Quantified>),
    Parameter,

    // Extraction
    Unwrap,

    // Solved
    Answer(Type),
}
```

The cycle-related variants (`Recursive`, `LoopRecursive`) are gone. Cycle
handling is purely a matter of transaction + preliminary answers.

## Downstream Simplification: Partial Type Binding Structure

Once transactional preliminary answers are in place, the current "trap" pattern
for partial types can be simplified.

### Current Structure (2-3 binding nodes per partial assignment)

For `x = []`:

1. `Key::Definition(x)` → `Binding::NameAssign` — raw computation, produces
   `list[@0]` with unpinned Var
2. `Key::PartialTypeWithUpstreamsCompleted(x)` → forces upstream partial types
   to be pinned before evaluating this one (optional, only when assignment uses
   other partial types)
3. `Key::CompletedPartialType(x)` → the "public" binding that scopes see; forces
   first-use evaluation before returning the pinned type

This structure isolates partial types through the graph topology.

### Simplified Structure (1 binding node)

With transactional preliminary answers providing isolation, this can become:

1. `Key::Definition(x)` → `Binding::NameAssign` with an embedded
   `first_use: Option<Idx<Key>>` field

The solver, when handling this binding:
1. Computes the raw type
2. If it contains partial Vars, starts a transaction (if not already in one)
3. Stores the raw type in PreliminaryAnswers
4. Chases the first-use chain if present
5. On transaction commit: recomputes with pinned types, writes to global

**Benefits**:
- Fewer binding nodes (simpler graph)
- Explicit control flow in the solver rather than implicit graph ordering
- Easier debugging and reasoning

This simplification is a downstream benefit of the transactional approach, not
a prerequisite.

## Implementation Risks

### Global Lock Duration

The global `Calculation` entry for a binding must remain in the `Calculating`
state for the entire duration of the transaction (tentative phase + resolution +
recomputation). This blocks other threads from reading that binding.

**Risk**: If the implementation releases the `Calculating` status early (e.g.,
between tentative and recompute phases), other threads might race to read
invalid/intermediate state, reintroducing nondeterminism.

**Mitigation**: The transaction commit must be atomic from the perspective of
other threads. The `Calculating` → `Calculated` transition should only happen
after the final (recomputed) answer is written. This likely means:
- Keep the `Calculation` in `Calculating` state throughout
- Write the recomputed answer directly to the `Calculation`
- Only then transition to `Calculated`

#### Cross-Module Lock Contention

If a transaction spans modules A → B → A, and another thread needs a binding
from B that's *not* part of the cycle, does that thread block on the entire
transaction? This could cause severe throughput degradation.

**Needs resolution**: The lock protocol at the `Calculation` level may need a
separate `CalculatingInTransaction` state that distinguishes tentative from
final answers, or finer-grained locking.

#### Interaction with `ProposalResult::CycleBroken`

Currently at `answers_solver.rs:510-516`, when `CycleBroken(r)` is returned,
another thread has already written a placeholder. With transactional writes,
who owns the placeholder? If thread 1 starts a transaction and thread 2 races
to write a placeholder, thread 2's placeholder could become globally visible
before thread 1's transaction commits.

**Needs resolution**: Define the ownership and visibility semantics for
placeholders when transactions and cycle-breaking interact.

### Performance (Double Solve)

Recomputing every binding in a transaction means paying ~2x cost for those
bindings. The document assumes cycles are small, but:

**Risk**: Large generated files or deep recursive dependency chains (common in
some frameworks) could hit performance cliffs.

**Mitigation options**:
1. Track which bindings actually depend on unstable `Var`s and only recompute
   those (selective recomputation)
2. Accept the cost for now, measure in practice, optimize if needed
3. Consider caching constraint-discovery work that doesn't need to be redone

Option 1 is more complex but could be important if large cycles are more common
than expected.

**Telemetry to add**: Transaction size distribution, recomputation time vs
original solve time, percentage of type-checking time spent in transactions.

## Open Questions

### 1. Nested Transaction Model

If a first-use chain is inside a cycle, do we have nested transactions? Or one
big transaction that covers both?

**Sub-questions**:
- The `Cycles` struct is a stack (`Vec<Cycle>`), suggesting nesting is already
  supported at the cycle level. But `TransactionState` as described has only a
  `depth: usize`, not a stack of participant sets.
- If we have a single flat participant list and we commit the outer transaction,
  we'd recompute everything including first-use bindings that were already
  correct.

**Decision needed**: Either formalize that transactions are flat (single depth
counter, one participant list) with an explanation of why that's sufficient, or
design a proper transaction stack.

### 2. PreliminaryAnswers Lookup Semantics

The document describes `(ModuleInfo, Idx<Key>)` as the key structure. But:

- Is this sufficient, or do we need to distinguish different transaction scopes?
- What if a nested cycle creates a different preliminary answer for the same key?
- "Check preliminary before global": What happens if a key has a preliminary
  answer from an outer transaction and we're in an inner transaction that needs
  to override it?

**Decision needed**: Formalize the lookup order with examples, especially for
nested cycles.

### 3. Participant Tracking: Read vs Write Semantics

The `TransactionState::participants` vec tracks bindings *solved* (written)
during the tentative phase. But what about:

- **Transitive dependencies**: If binding A is solved (goes into participants),
  and A's answer uses binding B (already globally computed), but B's type
  contains a Var that gets constrained during A's solve—B won't be in
  participants but its cached answer is now stale.
- **Generic instantiation**: When `f[T](x)` is called and T gets pinned during
  the tentative phase, does the call site binding get added to participants?
  The current `Quantified`/`PartialQuantified` handling suggests Vars can be
  pinned implicitly.

**Decision needed**: Clarify whether participants should include all bindings
that were *read* (not just written) during tentative phase, or add an invariant
explaining why write-tracking is sufficient.

### 4. Error Classification

The distinction between "type errors" (suppress) and "fatal errors" (propagate)
needs more precision:

- What is a "type error" vs "fatal error"? The `ErrorCollector` doesn't
  currently have this distinction. Is this a classification of `Error` enum
  variants, or a flag on the collector?
- **Partially-constrained errors**: If we suppress an error during tentative
  phase and then the Var gets pinned to a compatible type, we've correctly
  avoided a false positive. But if we suppress an error and recomputation
  produces the same error, we've done wasted work. Should we cache error
  positions?

**Decision needed**: Define the error classification explicitly and consider
whether a "tentative error buffer with deduplication" is more appropriate than
full suppression.

### 5. LoopRecursive Semantics Preservation

The proposal to store `prior_type` directly as a preliminary answer is
reasonable, but:

- When a `LoopRecursive` var is forced, it transitions to `LoopBound::Prior`,
  which is a special state that affects subsequent lookups.
- The `LoopBound` enum also tracks `UpperBounds(Vec<Type>)`, which accumulates
  constraints during recursion.

**Decision needed**: Work through a concrete loop example (e.g.,
`x = None; while cond: x = f(x)`) with both old and new approaches to verify
semantics are preserved.

### 6. Validate Recursive Hypothesis

Audit current uses of `Variable::Recursive` to confirm that removing
constraint-based pinning produces acceptable behavior changes.

**Specific concerns**:
- The pattern `def f(x): return g(x); def g(x): return f(x).method()` currently
  might work if `.method()` constrains x. This isn't just a behavior change—it's
  a different mental model (constraint-based vs definition-based).
- Compatibility with PEP 695 and future Python typing features: If typing
  evolves to expect constraint propagation through cycles, this design decision
  would be load-bearing.

### 7. Cross-Module Participant Tracking

Participants may span modules. The current `ThreadState` is per-thread and
travels across module boundaries. But `PreliminaryAnswers` needs module-aware
keys. The design mentions `(ModuleInfo, Idx<Key>)` but doesn't confirm the
implementation handles cross-module recomputation correctly.

## Resolved Questions

1. **Cycle integration**: The transaction scope must strictly enclose cycle
   resolution. The "Transaction Commit" point should align with the outermost
   `on_calculation_finished` that returns the stack depth to where the
   transaction started. If `CycleState::BreakAt` triggers a cycle unwind, the
   transaction must not commit until that unwind is complete and recursion has
   backed out to the transaction start point.

2. **Selective vs. Full Recomputation**: Implement full recomputation first.
   Tracking granular dependencies on specific Vars is complex and prone to
   "under-recomputing" bugs (missing a dependency). Given that cycles are
   empirically small, the complexity cost of selective recomputation likely
   outweighs the performance benefit for v0. Add telemetry to log transaction
   sizes; only optimize if data proves it necessary.

## Risk Summary

| Risk | Severity | Mitigation |
|------|----------|------------|
| Lock contention in cross-module scenarios | High | Prototype and benchmark |
| Behavior changes from removing constraint-based cycle resolution | Medium | Audit existing behavior first |
| Incomplete participant tracking (read vs write) | Medium | Formalize semantics |
| Nested transaction ambiguity | Medium | Decide on flat vs stacked model |
| LoopRecursive semantics preservation | Medium | Work through concrete examples |

## Recommended Next Steps

Before starting implementation, address the architectural decisions that are
expensive to change later:

### 1. Formalize the Lock Protocol

Specify the exact sequence of operations (lock acquisition, state transitions,
cleanup) as pseudocode or a state machine diagram. Address:
- Cross-module lock contention
- Interaction with `CycleBroken` placeholder ownership
- The `Calculating` vs `CalculatingInTransaction` distinction (if needed)

### 2. Decide on Transaction Nesting Model

Either:
- Formalize that transactions are flat (single depth counter, one participant
  list) with an explanation of why that's sufficient
- Or design a proper transaction stack with per-level participant sets

### 3. Write Detailed Worked Examples

Pick specific cases and trace through old and new behavior step-by-step:
- **Mutual recursion**: `def f(x): return g(x); def g(x): return f(x).method()`
  — what's in PreliminaryAnswers at each step, when do Vars get pinned, what
  errors are produced?
- **Loop recursion**: `x = None; while cond: x = f(x)` — verify `LoopRecursive`
  semantics are preserved
- **Nested cycle**: A first-use chain inside a cycle — how do participants and
  commits interact?

### 4. Audit `Variable::Recursive` Usage

Search for all places that match on or create `Recursive` and document expected
behavior changes. Create a list of code patterns that will behave differently.

### 5. Add Conformance Tests First

Before implementing, add tests that capture current behavior for edge cases:
- Nested cycles
- Cross-module cycles
- First-use inside cycles
- `LoopRecursive` fixed-point behavior

These become regression tests to verify the new implementation matches expected
behavior (or documents intentional changes).

### 6. Prototype PreliminaryAnswers in Isolation

Before adding transactional commits, implement just the thread-local answer
storage and verify cycle handling still works. This validates the basic
infrastructure before adding transaction complexity.

---

*Working document capturing design discussion and review feedback.*

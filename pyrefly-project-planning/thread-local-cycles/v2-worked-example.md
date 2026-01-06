# Worked Example: Simple Cycle (A → B → A)

This document shows the exact call sequence for the simplest possible cycle, demonstrating
how the two-pass protocol works in detail.

---

## Python Code

```python
def a() -> ???:
    return b()

def b() -> ???:
    return a()
```

**Goal:** Infer types for `a` and `b`.

**Challenge:** Circular dependency. We need `a`'s type to compute `b`, and `b`'s type to compute `a`.

---

## Initial State

```
Global Calculation:
  a: NotCalculated
  b: NotCalculated

ThreadState.cycles: []  # Empty stack
ThreadState.stack: []   # Empty calc stack
```

---

## Pass 1: Tentative Computation

### Step 1: Start computing `a`

```rust
// User calls get_idx(a)
self.stack().push(CalcId(bindings, idx_a));

// Check for cycle
match self.stack().current_cycle(CalcId(bindings, idx_a)) {
    None => {
        // No cycle yet, proceed
    }
}

// Propose calculation
calculation(a).propose_calculation() → Calculatable

// Mark as Calculating
Calculation(a): Calculating(None, {thread_id})
```

**State:**
```
Global Calculation:
  a: Calculating
  b: NotCalculated

ThreadState.stack: [CalcId(bindings, idx_a)]
ThreadState.cycles: []
```

### Step 2: `a()` calls `get_idx(b)`

```rust
// In K::solve(a), we call self.get_idx(idx_b)
self.stack().push(CalcId(bindings, idx_b));

// Check for cycle
match self.stack().current_cycle(CalcId(bindings, idx_b)) {
    None => {
        // No cycle yet (a and b are different), proceed
    }
}

// Propose calculation
calculation(b).propose_calculation() → Calculatable

// Mark as Calculating
Calculation(b): Calculating(None, {thread_id})
```

**State:**
```
Global Calculation:
  a: Calculating
  b: Calculating

ThreadState.stack: [CalcId(bindings, idx_a), CalcId(bindings, idx_b)]
ThreadState.cycles: []
```

### Step 3: `b()` calls `get_idx(a)` → **CYCLE DETECTED!**

```rust
// In K::solve(b), we call self.get_idx(idx_a)
self.stack().push(CalcId(bindings, idx_a));  // Duplicate!

// Check for cycle
match self.stack().current_cycle(CalcId(bindings, idx_a)) {
    Some(cycle_info) => {
        // CYCLE DETECTED: a is in stack at position 0
        // Stack: [a, b, a]
        //         ^     ^ duplicate!

        // Cycle participants: [a, b]
        // Minimal idx: a (assume a < b in ordering)
    }
}

// Inform Cycles struct
let state = self.cycles().on_cycle_detected(cycle_info);
```

### Step 4: Determine break point

```rust
// In Cycles::on_cycle_detected()
// Create new Cycle with break_at = a (minimal idx)
let cycle = Cycle {
    break_at: CalcId(bindings, idx_a),
    recursion_stack: vec![CalcId(bindings, idx_b)],  // Frames to recurse through
    unwind_stack: vec![],  // Will populate during recursion
    unwound: vec![],
    detected_at: CalcId(bindings, idx_a),
    preliminary_answers: PreliminaryAnswers::new(),
};
self.cycles.push(cycle);

// Check: are we at break_at?
if current_id == break_at {
    return CycleState::BreakHere;
} else {
    return CycleState::Continue;
}
// current_id = a, break_at = a → BreakHere!
```

**State:**
```
Global Calculation:
  a: Calculating
  b: Calculating

ThreadState.stack: [CalcId(bindings, idx_a), CalcId(bindings, idx_b), CalcId(bindings, idx_a)]
ThreadState.cycles: [Cycle { break_at: a, ... }]
```

### Step 5: Create placeholder for `a`

```rust
// We got CycleState::BreakHere for a
let t_a0 = create_placeholder();  // Variable::Recursive or Type::Any

// Store in cycle's preliminary_answers
self.cycles().current().preliminary_answers.record(
    self.module(),
    idx_a,
    t_a0.clone()
);

// Return placeholder to caller (b)
return Arc::new(promote_to_answer(t_a0));
```

**State:**
```
Global Calculation:
  a: Calculating
  b: Calculating

Cycle C1:
  preliminary_answers:
    a → T_A0 (Any)

ThreadState.stack: [CalcId(bindings, idx_a), CalcId(bindings, idx_b), CalcId(bindings, idx_a)]
```

**Result:** `b()` receives `T_A0 = Any`

### Step 6: `b()` completes

```rust
// Back in K::solve(b), we have the result from a: T_A0
// b's computation: return a()  →  return Any
let t_b1 = Type::Any;  // Result of b's computation

// Record in preliminary_answers (we're in a cycle)
self.cycles().current().preliminary_answers.record(
    self.module(),
    idx_b,
    t_b1.clone()
);

// Call on_calculation_finished
self.cycles().on_calculation_finished(&CalcId(bindings, idx_b));
// Updates unwind_stack, but cycle is still active

// Pop from stack
self.stack().pop();  // Remove second a
self.stack().pop();  // Remove b

// Return to a's computation
return Arc::new(t_b1);
```

**State:**
```
Global Calculation:
  a: Calculating
  b: Calculating

Cycle C1:
  preliminary_answers:
    a → T_A0 (Any)
    b → T_B1 (Any)

ThreadState.stack: [CalcId(bindings, idx_a)]
```

**Result:** `a()` receives `T_B1 = Any`

### Step 7: `a()` completes (pass 1 result)

```rust
// Back in K::solve(a), we have the result from b: T_B1
// a's computation: return b()  →  return Any
let t_a1 = Type::Any;  // Result of a's computation

// This is the break_at, so T_A1 becomes the official answer
// Write to GLOBAL Calculation (not preliminary)
calculation(a).record_value(Arc::new(t_a1.clone()));

// Transition to Calculated
Calculation(a): Calculated(T_A1)

// on_calculation_finished
self.cycles().on_calculation_finished(&CalcId(bindings, idx_a));
// Cycle C1 completes unwinding

// Pop from stack
self.stack().pop();  // Remove first a

// Cycle C1 is complete (unwind_stack empty)
```

**State:**
```
Global Calculation:
  a: Calculated(Any)  ← Written!
  b: Calculating       ← Still in progress

Cycle C1:
  preliminary_answers:
    a → T_A0 (Any)  ← Old placeholder
    b → T_B1 (Any)  ← Tentative answer

ThreadState.stack: []
```

### Step 8: Clear preliminary answers

```rust
// Before starting pass 2, clear the cycle's preliminary storage
self.cycles().current().preliminary_answers.clear();
```

**State:**
```
Global Calculation:
  a: Calculated(Any)
  b: Calculating

Cycle C1:
  preliminary_answers: {}  ← Cleared!

ThreadState.stack: []
```

---

## Pass 2: Canonical Computation

### Step 9: Recompute `a` (stability check)

```rust
// Call K::solve directly (not get_idx!)
let binding_a = self.bindings().get(idx_a);
let errors = &self.error_collector;
let t_a2 = K::solve(self, binding_a, errors);
```

### Step 10: `a()` calls `get_idx(b)` (pass 2)

```rust
// In K::solve(a), we call self.get_idx(idx_b)
self.stack().push(CalcId(bindings, idx_b));

// Check preliminary_answers
if let Some(answer) = self.get_preliminary(idx_b) {
    return answer;
}
// → None (cleared in step 8)

// Check global Calculation(b)
calculation(b).propose_calculation() → ???
```

**Wait, what's b's status?**

Looking back: b was set to `Calculating` in step 2, but we never called `record_value` on it!
Only `a` was written to global in step 7.

So `Calculation(b)` is still `Calculating`. But we're the same thread, so:

```rust
calculation(b).propose_calculation() → Calculatable  // Same thread can proceed
```

Actually, let me reconsider. In the actual implementation, when we write to preliminary_answers
for non-break_at bindings (like b), do we also record_value to global?

**Re-reading the protocol:** No! Only break_at gets written to global after pass 1. Other
bindings (b) stay in `Calculating` state.

So:
```rust
// b is Calculating with our thread_id
// We can proceed (no deadlock)
calculation(b).propose_calculation() → Calculatable

// Compute b fresh (not in preliminary, not in global)
let binding_b = self.bindings().get(idx_b);
let t_b2 = K::solve(self, binding_b, errors);
```

### Step 11: `b()` calls `get_idx(a)` (pass 2)

```rust
// In K::solve(b), we call self.get_idx(idx_a)
self.stack().push(CalcId(bindings, idx_a));

// Check preliminary_answers
if let Some(answer) = self.get_preliminary(idx_a) {
    return answer;
}
// → None (cleared)

// Check global Calculation(a)
calculation(a).get() → Calculated(T_A1)

// Return T_A1 from global
return Arc::new(T_A1);  // Any
```

**Result:** `b()` receives `T_A1 = Any` from global (not placeholder!)

### Step 12: `b()` completes (pass 2)

```rust
// b's computation: return a()  →  return Any
let t_b2 = Type::Any;

// Write to global Calculation (official answer for b)
calculation(b).record_value(Arc::new(t_b2.clone()));

// Transition to Calculated
Calculation(b): Calculated(T_B2)

// Pop from stack
self.stack().pop();  // Remove b

// Return to a's pass-2 computation
return Arc::new(t_b2);
```

**State:**
```
Global Calculation:
  a: Calculated(Any)  ← From pass 1
  b: Calculated(Any)  ← From pass 2

Cycle C1: still active
ThreadState.stack: [CalcId(bindings, idx_a)]  ← From pass 2 solve
```

### Step 13: `a()` completes (pass 2 result)

```rust
// Back in pass-2 K::solve(a), we have the result from b: T_B2
// a's computation: return b()  →  return Any
let t_a2 = Type::Any;

// Compare with T_A1
if t_a2 != t_a1 {
    emit_warning("Cycle resolution unstable at {:?}", idx_a);
}
// T_A2 = Any, T_A1 = Any → Equal, no warning

// Discard T_A2, keep T_A1 (already in global)

// Pop from stack
self.stack().pop();  // Remove a from pass-2 solve
```

**State:**
```
Global Calculation:
  a: Calculated(Any)  ← Final
  b: Calculated(Any)  ← Final

Cycle C1: can now be popped
ThreadState.stack: []
```

### Step 14: Cleanup

```rust
// Pop cycle from stack
self.cycles().pop();

// Cycle C1 destroyed, preliminary_answers freed
```

**Final State:**
```
Global Calculation:
  a: Calculated(Any)
  b: Calculated(Any)

ThreadState.cycles: []
ThreadState.stack: []
```

---

## Summary

**Pass 1 (Tentative):**
- Detected cycle when b → a
- Created placeholder T_A0 = Any for a (break_at)
- Computed b using T_A0 → T_B1 = Any (stored in preliminary)
- Computed a using T_B1 → T_A1 = Any (written to global)
- Cleared preliminary_answers

**Pass 2 (Canonical):**
- Recomputed a using direct solve
- a calls get_idx(b) → b not in preliminary or global → recomputes
- b calls get_idx(a) → returns T_A1 from global
- b completes → T_B2 = Any (written to global)
- a completes → T_A2 = Any
- Compared T_A2 vs T_A1 → equal, no warning

**Key Observations:**

1. **break_at (a) committed after pass 1**, ensuring consistency
2. **Other bindings (b) committed during pass 2**, based on pass-1 result for break_at
3. **Clearing preliminary_answers** is what triggers recomputation in pass 2
4. **Direct solve** on break_at bypasses cache, while dependencies use normal get_idx
5. **Stability check** catches cases where the type would keep changing

---

## What if Types Were More Interesting?

Let's modify the example:

```python
def a() -> ???:
    return b().upper()  # Calls .upper() on b's result

def b() -> ???:
    return a()
```

**Pass 1:**
- T_A0 = Any (placeholder for a)
- b computes: `a() → Any`, so T_B1 = Any
- a computes: `b().upper() → Any.upper()` → AttributeError on Any? Or Any?
  - Depends on how we handle attribute access on Any
  - Let's say we get Any → T_A1 = Any

**Pass 2:**
- a recomputes: `b().upper()` where b returns T_B2
- b recomputes using T_A1 = Any → T_B2 = Any
- a completes: `Any.upper() → Any` → T_A2 = Any
- Equal, no warning

**Still no precision!** Without external constraints (type annotations, usage elsewhere),
the cycle stays as Any.

**With annotation:**

```python
def a() -> str:
    return b().upper()

def b() -> ???:
    return a()
```

**Pass 1:**
- T_A0 = Any (placeholder, ignores annotation temporarily)
- b computes: `a() → Any`, so T_B1 = Any
- a computes: `b().upper() → Any`, but annotation says str → T_A1 = str

**Pass 2:**
- b recomputes using T_A1 = str → T_B2 = str
- a recomputes: `b().upper() → str.upper() → str` → T_A2 = str
- Equal to T_A1, no warning

**Result:** a = str, b = str

This shows how annotations can "seed" the cycle with information that propagates.

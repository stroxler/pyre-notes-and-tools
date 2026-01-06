# Implementation Plan: Match Statement Exhaustiveness Checking in Pyrefly

## Objective

Enable comprehensive exhaustiveness checking for Python `match` statements in Pyrefly, allowing the type checker to:

1. Detect when a `match` statement covers all possible cases for a subject type
2. Recognize that code following an exhaustive match (where all branches terminate) is unreachable
3. Narrow types in downstream cases based on patterns from prior cases
4. Provide clear, actionable error messages showing which cases are missing

## Current State

Pyrefly has **partial** exhaustiveness support with a critical gap:

### What Works

1. **Type-Based Exhaustiveness Errors** (`alt/narrow.rs`):
   - `check_match_exhaustiveness()` detects non-exhaustive matches
   - Only fires for enums and unions of literals
   - Reports `NonExhaustiveMatch` error with missing cases

2. **Syntactic Irrefutability Detection** (`binding/pattern.rs`):
   - `Pattern::is_wildcard()` and `Pattern::is_irrefutable()` detect `_` or `case x:`
   - Used for control flow at binding time

3. **Negative Narrowing** (`binding/pattern.rs`):
   - `negated_prev_ops` accumulates negated patterns for downstream cases
   - Type narrows correctly through match branches

### The Gap

```
              BINDING TIME                         SOLVING TIME
                   |                                    |
                   v                                    v
  function_last_expressions() ──────────────────> check_match_exhaustiveness()
  (determines implicit return)                    (determines type exhaustiveness)

  Uses: pattern.is_wildcard(),                    Uses: narrowing, type algebra
        pattern.is_irrefutable()

  NO TYPE INFORMATION HERE                        HAS TYPE INFORMATION
```

The `function_last_expressions` logic in `lib/binding/function.rs` only checks for syntactic wildcards:

```rust
Stmt::Match(x) => {
    let mut exhaustive = false;
    for case in x.cases.iter() {
        f(sys_info, &case.body, res)?;
        if case.pattern.is_wildcard() || case.pattern.is_irrefutable() {
            exhaustive = true;  // Only syntactic check!
            break;
        }
    }
    if !exhaustive {
        return None;  // May fall through
    }
}
```

This means type-based exhaustiveness (solved later) doesn't inform return type validation.

### Verification Test (Confirmed Failing)

```python
from enum import Enum

class Color(Enum):
    RED = 1
    BLUE = 2

def f(c: Color) -> str:
    match c:
        case Color.RED: return "red"
        case Color.BLUE: return "blue"
    # CURRENT: Warns about missing return
    # DESIRED: No warning (match is exhaustive)
```

---

## Implementation Phases

### Phase 1: Expand Type Coverage for Exhaustiveness Checking

**Goal:** Make exhaustiveness checking work for general union types, not just enums and literals.

**Changes to `lib/alt/narrow.rs`:**

1. Replace the restrictive predicate:
   ```rust
   // Before: is_enum_class_or_literal_union
   // After: should_check_exhaustiveness
   fn should_check_exhaustiveness(&self, ty: &Type) -> bool {
       match ty {
           Type::Union(variants) => {
               variants.iter().all(|v| self.is_exhaustible_variant(v))
           }
           Type::Literal(_) => true,
           Type::ClassType(cls) if self.is_enum_class(cls) => true,
           Type::ClassType(cls) if self.is_builtin_bool(cls) => true,
           Type::None => true,
           _ => false
       }
   }

   fn is_exhaustible_variant(&self, ty: &Type) -> bool {
       match ty {
           Type::Literal(_) => true,
           Type::None => true,
           Type::ClassType(cls) if self.is_builtin_bool(cls) => true,
           Type::ClassType(cls) => self.is_final_class(cls) || self.is_enum_class(cls),
           _ => false
       }
   }
   ```

   Note: `bool` should be checked via `is_builtin_bool(cls)` or recognized as `Literal[True] | Literal[False]`, depending on how Pyrefly represents it.

2. The existing narrowing logic handles exhaustiveness computation—when all union variants are eliminated, the remaining type becomes `Never`.

**Test Cases:**
```python
# Should detect exhaustiveness (for error reporting, not yet control flow)
def exhaustive_union(x: int | str) -> None:
    match x:
        case int():
            pass
        case str():
            pass
    # No NonExhaustiveMatch error

# Should detect non-exhaustiveness
def non_exhaustive_union(x: int | str | None):
    match x:  # E: Match is not exhaustive (missing: None)
        case int():
            pass
        case str():
            pass
```

---

### Phase 2: Connect Exhaustiveness to Return Analysis

**Goal:** Make type-based exhaustiveness inform implicit return analysis.

This is the critical architectural change. Two options:

#### Option A: Late-Binding Approach (Recommended)

1. In `function_last_expressions` (`lib/binding/function.rs`), when encountering a match without syntactic wildcards, mark it as "potentially exhaustive" instead of immediately returning `None`:
   ```rust
   Stmt::Match(x) => {
       let mut syntactic_exhaustive = false;
       for case in x.cases.iter() {
           f(sys_info, &case.body, res)?;
           if case.pattern.is_wildcard() || case.pattern.is_irrefutable() {
               syntactic_exhaustive = true;
               break;
           }
       }
       if !syntactic_exhaustive {
           // NEW: Instead of returning None, mark for later resolution
           res.push(LastExpression::PendingMatchExhaustiveness {
               match_id: x.id,
               subject_name: extract_subject_name(&x.subject),
           });
       }
   }
   ```

2. Add a new `ReturnTypeKind` variant or similar mechanism:
   ```rust
   enum ReturnTypeKind {
       // ... existing variants ...
       PendingMatchExhaustiveness(MatchId),
   }
   ```

3. In solving (`lib/alt/`), when analyzing return types:
   - Check if the function has `PendingMatchExhaustiveness` markers
   - Consult the solved exhaustiveness (is remaining type `Never`?)
   - If exhaustive AND all branches terminate, treat as no implicit return path

#### Option B: Two-Pass Approach

1. At binding time, always generate an implicit return key for functions with match statements that lack syntactic wildcards

2. At solving time, determine if the implicit return path is reachable:
   - If the match is type-exhaustive and all branches return/raise, the implicit return type is `Never`
   - If implicit return type is `Never`, suppress "missing return" errors

3. This requires the implicit return mechanism to understand match-internal control flow better

**Recommendation:** Option A is more explicit and easier to reason about. Option B is more elegant but requires deeper changes to how implicit returns work.

**Test Cases (should pass after this phase):**
```python
from enum import Enum

class Color(Enum):
    RED = 1
    BLUE = 2

def describe(color: Color) -> str:
    match color:
        case Color.RED:
            return "It's red"
        case Color.BLUE:
            return "It's blue"
    # Should NOT warn about missing return

def describe_partial(color: Color) -> str:  # E: Missing return
    match color:
        case Color.RED:
            return "It's red"
        # Missing BLUE case
```

---

### Phase 3: Improve Error Reporting

**Goal:** Show users exactly which cases are missing from a non-exhaustive match.

**Changes to `lib/alt/narrow.rs`:**

1. Add a helper to format the remaining (uncovered) type for diagnostics:
   ```rust
   fn format_missing_cases(&self, remaining_ty: &Type) -> String {
       match remaining_ty {
           Type::Union(variants) => {
               variants.iter()
                   .map(|v| self.format_type_for_error(v))
                   .collect::<Vec<_>>()
                   .join(", ")
           }
           Type::Literal(values) => {
               values.iter()
                   .map(|v| format!("{:?}", v))
                   .collect::<Vec<_>>()
                   .join(", ")
           }
           ty => self.format_type_for_error(ty)
       }
   }
   ```

2. Update error emission:
   ```
   // Before: "Match on `<type>` is not exhaustive"
   // After: "Match on `int | str | None` is not exhaustive. Missing cases: None"
   ```

3. For enum types, list missing variant names (e.g., `Color.BLUE, Color.GREEN`).

---

### Phase 4: Sequence Pattern Exhaustiveness

**Goal:** Check exhaustiveness for tuple patterns with known lengths.

**Implementation Strategy:**

1. Detect fixed-length tuple types and track length constraints:
   ```rust
   fn get_tuple_length(&self, ty: &Type) -> Option<usize> {
       match ty {
           Type::Tuple(TupleType::Concrete(elements)) => Some(elements.len()),
           _ => None
       }
   }
   ```

2. For sequence patterns, generate length-based narrow operations:
   - `case [x]:` → matches length 1
   - `case [x, y]:` → matches length 2
   - `case [x, *rest]:` → matches length >= 1

3. Check if all required lengths are covered:
   ```python
   def process_pair(p: tuple[int, int]) -> int:
       match p:
           case (x, y):
               return x + y
       # OK: exhaustive for 2-tuple
   ```

**Limitation:** Variable-length tuples (`tuple[int, ...]`) cannot be checked for exhaustiveness.

---

### Phase 5: Class Pattern Improvements

**Goal:** Improve exhaustiveness checking for class patterns with sub-patterns.

**Current Issue:** When a class pattern has sub-patterns (e.g., `case C(x=1):`), a `Placeholder` narrow op is inserted which prevents exact negation.

**Proposed Approach:**

For class patterns where inner patterns are exhaustive:
```python
@dataclass
class Toggle:
    enabled: bool

def check_toggle(t: Toggle) -> str:
    match t:
        case Toggle(enabled=True):
            return "on"
        case Toggle(enabled=False):
            return "off"
    # Should be exhaustive!
```

This requires tracking whether attribute patterns form an exhaustive set—more complex analysis that can be deferred.

---

### Phase 6: OR Pattern Handling

**Goal:** Ensure OR patterns are properly considered for exhaustiveness.

**Semantics (from CPython docs):**
- OR pattern is irrefutable if ANY subpattern is irrefutable
- All subpatterns must bind the same names

**Test Cases:**
```python
def or_pattern_exhaustive(x: int | str):
    match x:
        case int() | str():
            pass
    # OK: exhaustive via OR pattern
```

---

## Guard Handling

Guards are correctly handled by the current implementation:

- A guard (`if condition`) can cause a pattern match to fail even if the pattern succeeds
- Cases with guards never contribute to exhaustiveness guarantees
- This aligns with CPython semantics

```python
def guarded_not_exhaustive(x: Literal['A', 'B']):
    match x:  # E: Not exhaustive (guard may fail)
        case 'A' if some_condition():
            pass
        case 'B':
            pass
```

**Important edge case:** A guarded case followed by an unguarded case for the same value IS exhaustive:
```python
def describe(color: Color) -> str:
    match color:
        case Color.RED if some_condition():
            return "conditionally red"
        case Color.RED:  # Catches remaining RED cases
            return "red"
        case Color.BLUE:
            return "blue"
    # Should NOT warn - all cases covered
```

---

## Key Implementation Files

| File | Changes |
|------|---------|
| `lib/alt/narrow.rs` | Expand `check_match_exhaustiveness`, improve error messages |
| `lib/binding/function.rs` | Mark matches as "potentially exhaustive", add `PendingMatchExhaustiveness` |
| `lib/binding/pattern.rs` | May need updates for sequence length tracking |
| `lib/test/pattern_match.rs` | Add comprehensive test cases |

---

## Testing Strategy

### Category 1: Return Type Validation with Exhaustive Matches
```python
# Test 1.1: Basic exhaustive enum
def f(c: Color) -> str:
    match c:
        case Color.RED: return "red"
        case Color.BLUE: return "blue"
    # Should NOT warn

# Test 1.2: Exhaustive literal union
def f(s: Literal["a", "b"]) -> str:
    match s:
        case "a": return "A"
        case "b": return "B"
    # Should NOT warn

# Test 1.3: Exhaustive bool
def f(b: bool) -> str:
    match b:
        case True: return "yes"
        case False: return "no"
    # Should NOT warn
```

### Category 2: Mixed Returns and Raises
```python
# Test 2.1: All branches return or raise
def f(s: Status) -> int:
    match s:
        case Status.OK: return 0
        case Status.ERROR: raise ValueError()
        case Status.UNKNOWN: return -1
    # Should NOT warn

# Test 2.2: Some branches fall through (should warn)
def f(s: Status) -> int:  # E: Missing return
    match s:
        case Status.OK: return 0
        case Status.ERROR: print("error")  # Falls through!
```

### Category 3: Class Pattern Exhaustiveness
```python
# Test 3.1: Union covered by class patterns
def f(x: int | str) -> str:
    match x:
        case int(): return "int"
        case str(): return "str"
    # Should NOT warn

# Test 3.2: Partial coverage (should warn)
def f(x: int | str | bytes) -> str:  # E: Missing return
    match x:
        case int(): return "int"
        case str(): return "str"
```

### Category 4: Guards
```python
# Test 4.1: Guard prevents exhaustiveness
def f(c: Color) -> str:  # E: Missing return
    match c:
        case Color.RED if cond(): return "red"
        case Color.BLUE: return "blue"

# Test 4.2: Guarded + unguarded for same value
def f(c: Color) -> str:
    match c:
        case Color.RED if cond(): return "conditional"
        case Color.RED: return "red"
        case Color.BLUE: return "blue"
    # Should NOT warn
```

### Non-Goals (Should Still Warn)
```python
# NG1: Abstract base class
def f(a: Animal) -> str:  # E: Missing return (open hierarchy)
    match a:
        case Dog(): return "woof"
        case Cat(): return "meow"

# NG2: Open type (object, Any)
def f(x: object) -> str:  # E: Missing return
    match x:
        case int(): return "int"
        case str(): return "str"
```

---

## Known Limitations

1. **Open Class Hierarchies:** Cannot check exhaustiveness for non-sealed classes
2. **Value Patterns:** Runtime values (e.g., `case SOME_CONSTANT:`) cannot be statically verified
3. **Variable-Length Sequences:** `tuple[int, ...]` and `list[int]` have unbounded lengths
4. **Mapping Patterns:** Generally not exhaustive-checkable

---

## Open Questions

1. **Should we warn about redundant cases?** (e.g., `case _:` followed by another case)
2. **How to handle `Enum` with `_missing_` hook?** (custom handling for unknown values)
3. **TypedDict discriminated unions?** (e.g., `case {"type": "a"}:` for tagged unions)

---

## Summary

The core challenge is bridging the gap between:
- **Binding time** (when `function_last_expressions` runs, no type info)
- **Solving time** (when exhaustiveness is computed with full type info)

The implementation requires:
1. **Phase 1:** Expand type coverage for exhaustiveness checking
2. **Phase 2:** Connect type-based exhaustiveness to return analysis (the critical architectural change)
3. **Phase 3:** Improve error messages
4. **Phases 4-6:** Advanced patterns (sequence, class, OR)

The recommended approach (Option A) marks matches as "potentially exhaustive" at binding time and resolves them at solving time, keeping the architecture clean while enabling the feature.

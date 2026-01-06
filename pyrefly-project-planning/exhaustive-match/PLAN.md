# Exhaustive Match in Pyrefly: Implementation Plan

## Executive Summary

This document plans an effort to make Pyrefly understand exhaustiveness of match
statements at the type level, enabling:

1. Detection of non-exhaustive matches with clear error messages
2. Recognition that exhaustive matches where all branches return don't need implicit returns
3. Correct type narrowing after exhaustive matches (subject becomes `Never`)

## Current State Analysis

### What Pyrefly Already Has

Pyrefly has significant infrastructure for match statement analysis, including recent
additions (December 2025 - January 2026) that provide the foundation for this work.

**Pattern Binding & Narrowing** (`lib/binding/pattern.rs`):
- Each pattern type generates narrowing operations (`Eq`, `Is`, `LenEq`, `IsInstance`, etc.)
- `negated_prev_ops` accumulates negated patterns for downstream case narrowing
- `bind_pattern()` traverses patterns recursively, creating narrow ops

**Control Flow Tracking** (`lib/binding/scope.rs`):
- `Flow` struct tracks `has_terminated` and `is_definitely_unreachable` flags
- Branch merging correctly propagates termination when all branches terminate
- `finish_exhaustive_fork()` vs `finish_non_exhaustive_fork()` handle control flow differently

**Type-Based Exhaustiveness Checking** (`lib/alt/narrow.rs`):
- `check_match_exhaustiveness()` uses narrowing to detect non-exhaustive matches
- Reports `NonExhaustiveMatch` warning with missing cases for enums/literals
- Core logic: if remaining type after all narrows is `Never`, match is exhaustive

**Implicit Return Analysis** (`lib/binding/function.rs`):
- `function_last_expressions()` determines if a function can fall through
- Used to validate return type annotations and infer return types

### Recent Commits (Foundation for This Work)

**D89431015** (Jan 2, 2026) - "Report Non-Exhaustive match Statements":
- Added `BindingExpect::MatchExhaustiveness` binding that captures narrowing data
- Added `check_match_exhaustiveness()` in `lib/alt/narrow.rs:1218-1282`
- Only activates for enums and literal unions (`is_enum_class_or_literal_union`)
- Emits `NonExhaustiveMatch` **warning** when cases are missing

**D89670207** (Dec 22, 2025) - "Detect when previous patterns were exhaustive":
- Fixed class patterns without arguments (e.g., `case int():`) to not use `Placeholder`
- This allows `assert_never(x)` in wildcard cases to work correctly
- Pattern without arguments is now treated as a pure isinstance check

### Current Limitations

1. **Limited Type Coverage**: `check_match_exhaustiveness` only activates for enums and
   literal unions (guarded by `is_enum_class_or_literal_union`)

2. **Exhaustiveness Warning Disconnected from Return Analysis**: The `BindingExpect::MatchExhaustiveness`
   binding only emits warnings; it does NOT inform `ReturnImplicit` handling

3. **Syntactic-Only Control Flow**: `function_last_expressions` only considers syntactic
   exhaustiveness (wildcards, capture patterns), not type-based exhaustiveness

4. **Class Pattern Placeholder**: Class patterns **with arguments** still use `Placeholder`
   narrow ops which prevent exact negation (patterns without arguments were fixed in D89670207)

5. **No Sequence Pattern Exhaustiveness**: Tuple length/structure matching not checked

### The Core Problem: Binding vs Solving Time

There's a fundamental disconnect between when control flow is analyzed and when
type information is available:

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

The `function_last_expressions` logic in `lib/binding/function.rs:848-860` only
checks for syntactic wildcards:

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

This means type-based exhaustiveness (computed at solving time) doesn't inform
return type validation (determined at binding time).

### Confirmed Gap

The following test **currently fails** (warns about missing return when it shouldn't):

```python
from enum import Enum

class Color(Enum):
    RED = 1
    BLUE = 2

def describe(c: Color) -> str:
    match c:
        case Color.RED: return "red"
        case Color.BLUE: return "blue"
    # CURRENT: Warns about missing return
    # DESIRED: No warning (match is exhaustive)
```

---

## Implementation Phases

### Phase 1: Expand Type Coverage for Exhaustiveness Checking

**Goal:** Make exhaustiveness checking work for more types beyond enums and literal unions.

**Changes to `lib/alt/narrow.rs`:**

Replace the restrictive `is_enum_class_or_literal_union` predicate:

```rust
/// Determines if a type should be checked for match exhaustiveness.
/// We check exhaustiveness when:
/// 1. The type has a finite, known set of possible values
/// 2. We can reliably narrow away each case
fn should_check_exhaustiveness(&self, ty: &Type) -> bool {
    match ty {
        // Enums have a fixed set of members
        Type::ClassType(cls) if self.is_non_flag_enum(cls) => true,

        // Literal types have explicit values
        Type::Literal(_) => true,

        // None is a singleton
        Type::None => true,

        // Unions are exhaustible if all members are
        Type::Union(union) => {
            union.members.iter().all(|m| self.is_exhaustible_type(m))
        }

        _ => false,
    }
}

/// Determines if a type can be exhaustively matched as part of a union.
fn is_exhaustible_type(&self, ty: &Type) -> bool {
    match ty {
        Type::Literal(_) => true,
        Type::None => true,
        Type::ClassType(cls) => {
            // Enums are exhaustible
            self.is_non_flag_enum(cls) ||
            // Final classes can't have subclasses
            self.is_final_class(cls.class_object()) ||
            // bool is Literal[True] | Literal[False] effectively
            cls.is_builtin("bool")
        }
        _ => false,
    }
}
```

**The existing narrowing logic handles the rest**: When all union variants are eliminated
by pattern matching, the remaining type becomes `Never`, indicating exhaustiveness.

**Test Cases:**
```python
# Union of classes
def exhaustive_union(x: int | str) -> int:
    match x:
        case int(): return 1
        case str(): return 2
    # Should not warn (after Phase 2)

# Bool as effectively Literal[True, False]
def exhaustive_bool(x: bool) -> str:
    match x:
        case True: return "yes"
        case False: return "no"
    # Should not warn

# Missing case should error
def non_exhaustive(x: int | str | None):
    match x:  # E: Match is not exhaustive (missing: None)
        case int(): pass
        case str(): pass
```

---

### Phase 2: Connect Exhaustiveness to Return Analysis

**Goal:** Make type-based exhaustiveness inform implicit return analysis.

**The Key Challenge:**

The existing `BindingExpect::MatchExhaustiveness` binding already computes whether a match
is exhaustive at solving time (by checking if `remaining_ty.is_never()`). However, this
information is currently used only to emit warnings - it doesn't affect `ReturnImplicit`.

The challenge is that `ReturnImplicit` is also resolved at solving time, but it has no
connection to the `MatchExhaustiveness` binding. We need to bridge this gap.

**Recommended Approach: Extend ReturnImplicit with Match References**

Rather than trying to make the solver "smarter" at solving time without any binding-time
changes, we extend the binding phase to track which match statements might provide
type-based exhaustiveness for return analysis.

**Step 1: Add a new `LastStmt` variant** (`lib/binding/binding.rs`):

```rust
#[derive(Clone, Dupe, Copy, Debug)]
pub enum LastStmt {
    /// The last statement is an expression
    Expr,
    /// The last statement is a `with`, with the following context
    With(IsAsync),
    /// The last statement is a match that may be type-exhaustive
    /// The Idx points to the MatchExhaustiveness binding (if one was created)
    Match(Option<Idx<KeyExpect>>),
}
```

**Step 2: Update `function_last_expressions`** (`lib/binding/function.rs`):

Instead of returning `None` for non-syntactically-exhaustive matches, return a
`LastStmt::Match` with a reference to the match statement's range (which can be
used to look up the `MatchExhaustiveness` binding):

```rust
Stmt::Match(x) => {
    let mut exhaustive = false;
    for case in x.cases.iter() {
        f(sys_info, &case.body, res)?;
        if case.pattern.is_wildcard() || case.pattern.is_irrefutable() {
            exhaustive = true;
            break;
        }
    }
    if !exhaustive {
        // Instead of returning None, record that this match might be
        // type-exhaustive. We'll resolve this at solving time.
        res.push((LastStmt::Match(x.range), /* placeholder expr */));
    }
}
```

**Note:** This requires some refactoring since `function_last_expressions` currently
returns expressions, not statement ranges. The design needs to accommodate match
statements that don't have an associated expression.

**Step 3: Update `ReturnImplicit` solving** (`lib/alt/solve.rs`):

When solving `ReturnImplicit`, check if any `LastStmt::Match` entries are type-exhaustive:

```rust
Binding::ReturnImplicit(x) => {
    // ... existing logic ...

    // For Match entries, check if they're actually exhaustive
    let all_paths_terminate = x.last_exprs.as_ref().is_some_and(|xs| {
        xs.iter().all(|(last, k)| {
            match last {
                LastStmt::Expr => self.get_idx(*k).ty().is_never(),
                LastStmt::With(kind) => { /* existing logic */ },
                LastStmt::Match(match_range) => {
                    // Look up the MatchExhaustiveness binding for this range
                    // and check if it computed Never as the remaining type
                    self.is_match_type_exhaustive(*match_range)
                }
            }
        })
    });

    if all_paths_terminate {
        Type::never()
    } else {
        Type::None
    }
}
```

**Step 4: Add helper to check match exhaustiveness** (`lib/alt/narrow.rs` or `solve.rs`):

```rust
/// Check if a match statement at the given range was determined to be type-exhaustive.
/// This looks up the MatchExhaustiveness binding and checks if remaining type is Never.
fn is_match_type_exhaustive(&self, match_range: TextRange) -> bool {
    // Find the MatchExhaustiveness binding for this match statement
    // Reuse the same narrowing logic from check_match_exhaustiveness
    // but return bool instead of emitting errors
    // ...
}
```

**Why This Approach:**

1. **Leverages existing infrastructure**: Uses the `MatchExhaustiveness` binding and
   narrowing logic that already exists
2. **Clean separation**: Binding phase identifies "potentially exhaustive" matches,
   solving phase resolves them
3. **Minimal invasiveness**: Main changes are to `LastStmt` enum and `ReturnImplicit` handling
4. **Consistent with existing patterns**: Similar to how `With` is handled (context manager
   exit type checked at solving time)

**Alternative Approach: Post-Solve Error Suppression**

If the above proves too invasive, a simpler fallback:

1. Keep binding analysis unchanged
2. When emitting "missing return" errors, check if the function ends with a match
3. If so, check if that match was type-exhaustive
4. Suppress the error if exhaustive

This is simpler but less principled - it works around the architecture rather than
integrating cleanly. It also means the return type would still be `None` instead of
the correct union of branch return types.

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

### Phase 3: Improve Error Messages

**Goal:** Show users exactly which cases are missing from a non-exhaustive match.

**Current State:** Already partially implemented - `format_missing_literal_cases`
exists but only handles literals.

**Changes to `lib/alt/narrow.rs`:**

Extend `format_missing_literal_cases` to handle more types:

```rust
fn format_missing_cases(&self, remaining_ty: &Type) -> Option<String> {
    fn collect_cases(solver: &Self, ty: &Type, acc: &mut Vec<String>) -> bool {
        match ty {
            Type::Literal(lit) => {
                acc.push(format!("{}", lit));
                true
            }
            Type::None => {
                acc.push("None".to_string());
                true
            }
            Type::ClassType(cls) if solver.is_non_flag_enum(cls) => {
                // For enum class (not literal), show the class name
                acc.push(format!("{}", cls.name()));
                true
            }
            Type::Union(union) => {
                union.members.iter().all(|m| collect_cases(solver, m, acc))
            }
            _ => false,
        }
    }

    let mut cases = Vec::new();
    if collect_cases(self, remaining_ty, &mut cases) {
        Some(cases.join(", "))
    } else {
        None
    }
}
```

**Improved Error Format:**
```
Before: "Match on `Color` is not exhaustive"
After:  "Match on `Color` is not exhaustive. Missing cases: Color.BLUE, Color.GREEN"
```

---

### Phase 4: Sequence Pattern Exhaustiveness

**Goal:** Check exhaustiveness for tuple patterns with known lengths.

**Implementation:**

1. Detect fixed-length tuple types:
```rust
fn get_tuple_length(&self, ty: &Type) -> Option<usize> {
    match ty {
        Type::Tuple(Tuple::Concrete(elements)) => Some(elements.len()),
        Type::ClassType(cls) if let Some(Tuple::Concrete(elements)) = self.as_tuple(cls) => {
            Some(elements.len())
        }
        _ => None,
    }
}
```

2. For sequence patterns, verify length coverage:
   - `case [x]:` → matches length 1
   - `case [x, y]:` → matches length 2
   - `case [x, *rest]:` → matches length >= 1

**Test Cases:**
```python
def process_pair(p: tuple[int, int]) -> int:
    match p:
        case (x, y):
            return x + y
    # OK: exhaustive for 2-tuple

def incomplete_tuple(p: tuple[int, int]):
    match p:  # E: Not exhaustive
        case (x,):  # Never matches 2-tuple!
            pass
```

**Limitation:** Variable-length tuples (`tuple[int, ...]`) cannot be checked.

---

### Phase 5: Class Pattern Improvements

**Goal:** Improve exhaustiveness for class patterns with sub-patterns.

**Current State:** Class patterns **without arguments** (e.g., `case int():`) were fixed
in D89670207 (Dec 22, 2025) to not use `Placeholder`. These now work correctly for
exhaustiveness checking and `assert_never()` patterns.

**Remaining Issue:** Class patterns **with arguments** (e.g., `case Toggle(enabled=True):`)
still insert `Placeholder` narrow ops (see `lib/binding/pattern.rs:239-246`), preventing
exact negation.

**Proposed Approach:**

For class patterns where inner patterns form an exhaustive set, avoid placeholder:

```python
@dataclass
class Toggle:
    enabled: bool

def check_toggle(t: Toggle) -> str:
    match t:
        case Toggle(enabled=True): return "on"
        case Toggle(enabled=False): return "off"
    # Should be exhaustive - bool attribute fully covered
```

**Implementation Complexity:** This requires:
1. Tracking attribute coverage across patterns
2. Determining when attribute patterns are exhaustive
3. Combining class + attribute exhaustiveness

**Recommendation:** Defer to later phase; focus on Phases 1-3 first.

---

### Phase 6: OR Pattern Handling

**Goal:** Properly account for OR patterns in exhaustiveness.

**Semantics (from CPython docs):**
- OR pattern succeeds if ANY subpattern succeeds
- OR pattern is irrefutable if ANY subpattern is irrefutable
- Coverage = union of subpattern coverage

**Current State:** Likely already handled via `NarrowOps::or_all()` in pattern.rs.

**Verification:**
```python
def or_pattern_exhaustive(x: int | str):
    match x:
        case int() | str():
            pass
    # Should recognize this covers int | str

def or_with_wildcard(x: int | str):
    match x:
        case int() | _:  # _ makes this irrefutable
            pass
    # Should recognize as syntactically exhaustive
```

---

### Phase 7: Redundant Case Detection

**Goal:** Warn when a match case is unreachable because prior cases already cover it.

**New Error Code:** `RedundantCase` (to be added to `pyrefly_config/src/error_kind.rs`)

The error should have default severity `Warn` (consistent with `NonExhaustiveMatch`).

**Cases to Detect:**

1. **Duplicate literal/value patterns:**
   ```python
   match x:
       case Color.RED: ...
       case Color.RED: ...  # W: Redundant case (already matched above)
   ```

2. **Wildcard before other cases:**
   ```python
   match x:
       case _: ...
       case Color.RED: ...  # W: Redundant case (wildcard above catches all)
   ```

3. **Irrefutable pattern before other cases:**
   ```python
   match x:
       case y: ...  # Captures all
       case Color.RED: ...  # W: Redundant case
   ```

4. **Subsumed class patterns:**
   ```python
   match x:
       case int(): ...
       case int(): ...  # W: Redundant case
   ```

**Implementation:**

At binding time, after processing each case, check if the narrowed subject type is
already `Never`. If so, subsequent cases are redundant:

```rust
// In stmt_match, after bind_pattern for each case:
if !exhaustive {
    // Check if this case made the remaining type Never
    // If so, mark remaining cases as redundant
}
```

Alternatively, implement at solving time by checking if each case's pattern
could match any remaining values after prior case narrowing.

**Note:** This integrates naturally with exhaustiveness checking - a match is
exhaustive when remaining type is `Never`, and any subsequent case is redundant.

---

## Guard Handling

Guards are already handled correctly:

- A guard (`if condition`) can cause pattern match to fail even if pattern succeeds
- Cases with guards never guarantee exhaustiveness
- The `Placeholder` narrow op is added for guarded patterns (pattern.rs:240-245)

```python
def guarded_not_exhaustive(x: Literal['A', 'B']):
    match x:  # E: Not exhaustive (guard may fail)
        case 'A' if some_condition():
            pass
        case 'B':
            pass
```

**Important edge case:** A guarded case followed by an unguarded case for the same
value IS exhaustive:

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

## Implementation Order

| Phase | Priority | Effort | Dependencies |
|-------|----------|--------|--------------|
| 1: Expand Type Coverage | P0 | Medium | None |
| 2: Control Flow Integration | P0 | Medium-Large | Phase 1 |
| 3: Error Messages | P1 | Small | Phase 1 |
| 4: Sequence Patterns | P2 | Medium | Phase 1 |
| 5: Class Pattern Improvements | P3 | Large | Phases 1-4 |
| 6: OR Pattern Verification | P2 | Small | Phase 1 |
| 7: Redundant Case Detection | P1 | Medium | Phases 1-2 |

**Minimum Viable Feature:** Phases 1, 2, 3

---

## Key Files

| File | Changes |
|------|---------|
| `lib/binding/binding.rs` | Add `LastStmt::Match` variant (Phase 2) |
| `lib/binding/function.rs` | Update `function_last_expressions` to track potentially-exhaustive matches (Phase 2) |
| `lib/alt/narrow.rs` | Expand `is_enum_class_or_literal_union` predicate (Phase 1), improve error messages (Phase 3), add `is_match_type_exhaustive` helper (Phase 2) |
| `lib/alt/solve.rs` | Modify `ReturnImplicit` handling to check match exhaustiveness (Phase 2) |
| `lib/binding/pattern.rs` | Sequence length tracking (Phase 4), redundant case detection (Phase 7) |
| `lib/test/pattern_match.rs` | Comprehensive test cases |
| `crates/pyrefly_config/src/error_kind.rs` | Add `RedundantCase` error kind (Phase 7) |

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

# Test 4.2: Guarded + unguarded for same value (IS exhaustive)
def f(c: Color) -> str:
    match c:
        case Color.RED if cond(): return "conditional"
        case Color.RED: return "red"  # Catches remaining RED
        case Color.BLUE: return "blue"
    # Should NOT warn
```

### Category 5: Redundant Cases
```python
# Test 5.1: Duplicate pattern
match x:
    case Color.RED: ...
    case Color.RED: ...  # W: Redundant case

# Test 5.2: Wildcard before other cases
match x:
    case _: ...
    case Color.RED: ...  # W: Redundant case

# Test 5.3: Capture pattern before other cases
match x:
    case y: ...  # Captures all
    case Color.RED: ...  # W: Redundant case

# Test 5.4: Not redundant - guard allows fallthrough
match x:
    case Color.RED if cond(): ...
    case Color.RED: ...  # NOT redundant - guard may fail
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

1. **Open Class Hierarchies:** Cannot check exhaustiveness for non-final, non-sealed
   classes (unknown subclasses may exist)

2. **Value Patterns:** Runtime values (`case SOME_CONSTANT:`) cannot be statically
   verified for exhaustiveness

3. **Variable-Length Sequences:** `tuple[int, ...]` and `list[int]` have unbounded
   possible lengths

4. **Mapping Patterns:** Dicts are inherently partial; exhaustiveness not checkable

5. **Abstract Classes:** Matching on ABC cannot be exhaustive

6. **Enum `_missing_` hook:** Enums that use `_missing_` to dynamically create
   members at runtime are treated as exhaustive when all declared members are
   matched. This is intentional - see "Resolved Design Decisions" for rationale.

---

## Future Work

1. **TypedDict Discriminated Unions (Fast Follow):** Support exhaustiveness checking
   for `case {"type": "a"}:` style patterns on TypedDict unions. This is a common
   pattern for tagged unions in Python and would be valuable, but can be implemented
   after the core exhaustiveness feature.

2. **IDE Integration:** Code actions for adding missing cases

3. **@sealed/@final Support:** Honor these decorators for exhaustiveness analysis
   on class hierarchies

---

## Resolved Design Decisions

1. **Redundant case detection:** Yes, we will warn on redundant cases using a new
   `RedundantCase` error code (see Phase 7).

2. **Enum with `_missing_` hook:** We treat enums with `_missing_` the same as
   regular enums for exhaustiveness checking. Rationale:

   - `_missing_` is a constructor-time mechanism (`Color(value)`) that allows
     creating enum values from data. It's not intended to affect pattern matching
     on already-typed enum values.
   - The static type `Color` represents the declared members. If `_missing_`
     dynamically creates new members at runtime, that's outside the type system's
     scope.
   - Most `_missing_` usage is for returning a default member or raising better
     errors, not for creating dynamic members.
   - Relying on `_missing_` to handle unmatched cases in a match statement is
     not a reasonable pattern - if you need a fallback, use a wildcard case.
   - Consistent with mypy and pyright behavior.

3. **TypedDict discriminated unions:** Tracked as a fast-follow (see Future Work).

---

## References

- CPython match statement documentation (see `match-semantics.rst`)
- PEP 634: Structural Pattern Matching: Specification
- PEP 636: Structural Pattern Matching: Tutorial
- Pyrefly source files referenced throughout

---

## Revision History

**January 5, 2026** - Updated based on code review:
- Added "Recent Commits" section documenting D89431015 (MatchExhaustiveness binding)
  and D89670207 (class pattern without arguments fix)
- Clarified that class patterns without arguments already work correctly
- Rewrote Phase 2 with a concrete implementation approach using `LastStmt::Match`
- Updated Key Files table with specific changes per phase
- Noted that the current exhaustiveness warning is disconnected from return analysis

# Type-Aware If Branch Termination

## Problem Statement

The Pyrefly type checker is currently lacking a feature.

We understand control flow of code that has branching control flow with termination that is
determinable via syntax, for example
```python
def f(x: str | bytes | bool) -> str | bytes:
    if isinstance(x, str):
        pass
    elif isinstance(x, bytes):
        pass
    else:
        raise Exception("oops")
    return x  # ok
```
which happens because in scope.rs the `Flow` data structure tracks a `terminated` flag
for whether we've seen a flow-terminating statement (like a `return` or a `raise`) in this branch.


But the `Never` / `NoReturn` type in Python (which are semantically the same, it has
two names to signal slightly different developer intent) means that we are also
supposed to understand termination at the control-flow level:
```python
def raises() -> NoReturn: ...
def f(x: str | bytes | bool) -> str | bytes:
    if isinstance(x, str):
        pass
    elif isinstance(x, bytes):
        pass
    else:
        raises()  # Pyrefly is supposed to know this flow terminates
    return x  # should be ok
```

Now, given Pyrefly's current architecture we don't think it would be easy to track
*all* function calls for marking a flow as terminated, because it's important to the
way we create bindings that they be small.

But we actually should be able to do this much more easily: in almost all real code
(including the example above), a call returning `Never` or `NoReturn` that is supposed
to terminate control flow is going to be:
- A function call that is a top-level `StmtExpr`, not a function call inside some
  other statement like an assignment or buried inside of a larger expression
- The final statement in the branch (nothing else follows it)


That should mean that we can handle it like this:
- As we traverse a flow, track whether the final statement is a `StmtExpr` by storing
  an optional `Idx<Key>` pointing to a `Binding::StmtExpr`. This should be set when we
  see a `StmtExpr` and cleared when we see any other statement type, so that it only
  has a value if the branch ends with a `StmtExpr`.
- Then, extend the `Phi` binding to allow each branch to contain such an
  optional key that we can look up later at solve time
- In the `Phi` solving stage, check the `StmtExpr` keys if they are present
  - If every branch terminates (every branch has a trailing `StmtExpr` that resolves
    to `Never`), just merge the flow as usual (ignore termination), which is consistent
    with how we already deal with syntax-level termination at binding time
  - Otherwise, exclude terminated branches from the merge. A branch is "live" (not
    terminated) if it either has no trailing `StmtExpr` key, or it has one but the
    type is anything other than `Never` / `NoReturn`

Note that this is more complex but very similar to how we handle the implications
of `Never` / `NoReturn` in function return type inference, so it may be possible
to cross-reference that for more details.


## Design Decisions

These decisions were made by the tech lead to scope the initial implementation:

1. **Comprehensions and nested scopes**: Treat as never terminating flow. We only expect top-level function calls to be used in practice.

2. **`SpecialExport::PytestNoReturn`**: Leave in place for now, but mark with a `TODO(stroxler)` noting it may be redundant. Minimize changes in the initial implementation.

3. **Loops**: Ignore `NoReturn` termination in loops for now. It's possible they end in a `NoReturn` but that would be surprising—wait for a bug report.


---

## Implementation Plan

### Step 0: Create a Failing Test

**File**: `pyrefly/lib/test/flow_branching.rs`

Add test cases near other NoReturn tests:

```rust
testcase!(
    test_noreturn_branch_termination,
    r#"
from typing import NoReturn, assert_type

def raises() -> NoReturn:
    raise Exception()

def f(x: str | bytes | bool) -> str | bytes:
    if isinstance(x, str):
        pass
    elif isinstance(x, bytes):
        pass
    else:
        raises()
    return x  # Should be ok - x is str | bytes here

def g(x: str | None) -> str:
    if x is None:
        raises()
    return x  # Should be ok - x is str here

def h(x: int | str) -> None:
    if isinstance(x, int):
        y = x + 1
    else:
        raises()
    assert_type(y, int)  # y should be int, not str | int
"#,
);
```

Run the test to confirm it fails:
```bash
buck test pyrefly:pyrefly_library -- test_noreturn_branch_termination
```

---

### Step 1: Extend the `Flow` struct

**File**: `pyrefly/lib/binding/scope.rs` (around line 432)

**Current code:**
```rust
#[derive(Default, Clone, Debug)]
pub struct Flow {
    info: SmallMap<Name, FlowInfo>,
    has_terminated: bool,
}
```

**Change to:**
```rust
#[derive(Default, Clone, Debug)]
pub struct Flow {
    info: SmallMap<Name, FlowInfo>,
    has_terminated: bool,
    /// The key for the last `Binding::StmtExpr` in this flow, if any.
    /// Used to check for type-based termination (NoReturn/Never) at solve time.
    last_stmt_expr: Option<Idx<Key>>,
}
```

---

### Step 2: Update `last_stmt_expr` when processing statement expressions

**File**: `pyrefly/lib/binding/stmt.rs` (around line 971)

**Current code:**
```rust
Stmt::Expr(mut x) => {
    let mut current = self.declare_current_idx(Key::StmtExpr(x.value.range()));
    self.ensure_expr(&mut x.value, current.usage());
    let special_export = if let Expr::Call(ExprCall { func, .. }) = &*x.value {
        self.as_special_export(func)
    } else {
        None
    };
    self.insert_binding_current(current, Binding::StmtExpr(*x.value, special_export));
    if special_export == Some(SpecialExport::PytestNoReturn) {
        self.scopes.mark_flow_termination();
    }
}
```

**Change to:**
```rust
Stmt::Expr(mut x) => {
    let mut current = self.declare_current_idx(Key::StmtExpr(x.value.range()));
    self.ensure_expr(&mut x.value, current.usage());
    let special_export = if let Expr::Call(ExprCall { func, .. }) = &*x.value {
        self.as_special_export(func)
    } else {
        None
    };
    let key = self.insert_binding_current(current, Binding::StmtExpr(*x.value, special_export));
    // Track this StmtExpr as the trailing statement for type-based termination
    self.scopes.set_last_stmt_expr(Some(key));
    // TODO(stroxler): PytestNoReturn may now be redundant given type-based termination
    if special_export == Some(SpecialExport::PytestNoReturn) {
        self.scopes.mark_flow_termination();
    }
}
```

**Note**: `insert_binding_current` returns `Idx<Key>`, so we can capture it directly.

---

### Step 2b: Clear `last_stmt_expr` for non-StmtExpr statements

**File**: `pyrefly/lib/binding/stmt.rs`

For the `last_stmt_expr` to correctly represent "the branch ends with a StmtExpr", we must clear it whenever we process a non-`StmtExpr` statement. Add this call at the start of handling for other statement types that don't already terminate flow:

```rust
// Clear last_stmt_expr since this is not a trailing StmtExpr
self.scopes.set_last_stmt_expr(None);
```

The key statement types that need this are:
- `Stmt::Assign`
- `Stmt::AugAssign`
- `Stmt::AnnAssign`
- `Stmt::Pass`
- `Stmt::Delete`
- `Stmt::Global`
- `Stmt::Nonlocal`
- `Stmt::Import`
- `Stmt::ImportFrom`
- `Stmt::Assert` (unless it's `assert False` which terminates)
- `Stmt::TypeAlias`

Statement types that involve control flow (`If`, `For`, `While`, `Try`, `With`, `Match`) handle their own branching and merging, so the `last_stmt_expr` will be set appropriately by their internal statement processing.

Statement types that terminate flow (`Return`, `Raise`, `Break`, `Continue`) don't need to clear `last_stmt_expr` because terminated branches are already filtered at binding time.

**Recommended approach**: Add a helper that clears `last_stmt_expr` and call it at the top of each relevant match arm, or refactor to clear at the start of `stmt()` and only set it in the `Stmt::Expr` case.

---

### Step 3: Add helper methods for `last_stmt_expr`

**File**: `pyrefly/lib/binding/scope.rs`

Add these methods to the `Scopes` impl block (near `mark_flow_termination` around line 1730):

```rust
/// Set or clear the last statement expression key for the current flow.
/// This is used for type-based termination checking at solve time.
/// Should be set to Some(key) for StmtExpr, and None for other statements.
pub fn set_last_stmt_expr(&mut self, key: Option<Idx<Key>>) {
    self.current_mut().flow.last_stmt_expr = key;
}
```

---

### Step 4: Clear `last_stmt_expr` when starting a new branch

**File**: `pyrefly/lib/binding/scope.rs` (around line 2632, in `start_branch`)

**Current code:**
```rust
pub fn start_branch(&mut self) {
    let scope = self.scopes.current_mut();
    let fork = scope.forks.last_mut().unwrap();
    fork.branch_started = true;
    scope.flow = fork.base.clone();
}
```

**Change to:**
```rust
pub fn start_branch(&mut self) {
    let scope = self.scopes.current_mut();
    let fork = scope.forks.last_mut().unwrap();
    fork.branch_started = true;
    scope.flow = fork.base.clone();
    // Clear last_stmt_expr so this branch tracks only its own terminal statement
    scope.flow.last_stmt_expr = None;
}
```

**Rationale**: When we clone a `Flow` for a new branch, the clone inherits the base flow's `last_stmt_expr`. We clear it so each branch tracks only its own terminal statement.

---

### Step 5: Extend `Binding::Phi` to store termination keys

**File**: `pyrefly/lib/binding/binding.rs` (around line 1342)

**Current code:**
```rust
/// A phi node, representing the union of several alternative keys.
Phi(JoinStyle<Idx<Key>>, SmallSet<Idx<Key>>),
```

**Change to:**
```rust
/// A phi node, representing the union of several alternative keys.
/// The optional third element contains termination info for type-based filtering:
/// - If None, no type-based termination checking is needed
/// - If Some, contains PhiTerminationInfo for solve-time filtering
Phi(
    JoinStyle<Idx<Key>>,
    SmallSet<Idx<Key>>,
    Option<Box<PhiTerminationInfo>>,
),
```

Add a helper struct (in the same file):

```rust
/// Information for type-based termination filtering at solve time.
#[derive(Clone, Debug)]
pub struct PhiTerminationInfo {
    /// One entry per branch in merge order.
    /// Maps to the branch's last_stmt_expr key if it exists.
    pub branch_termination_keys: Vec<Option<Idx<Key>>>,
    /// Maps each value key to the indices of branches that produced it.
    pub value_to_branches: SmallMap<Idx<Key>, SmallVec<[usize; 2]>>,
}
```

**Rationale for the structure**: The `SmallSet<Idx<Key>>` contains *unique* value keys after deduplication. Multiple branches may produce the same value (e.g., `x = 1` in both `if` and `else`). We need to track which branches produced each value so we can determine if at least one producing branch is live.

---

### Step 6: Update all Phi construction sites

Search for `Binding::Phi(` in the codebase and update each site.

**File**: `pyrefly/lib/binding/bindings.rs` (line 499)

**Current:**
```rust
Binding::Phi(JoinStyle::SimpleMerge, SmallSet::new())
```

**Change to:**
```rust
Binding::Phi(JoinStyle::SimpleMerge, SmallSet::new(), None)
```

**File**: `pyrefly/lib/binding/scope.rs` (in `merge_idxs` around line 2293)

This is the main construction site. Updated in Step 8.

---

### Step 7: Thread termination info through the merge pipeline

**File**: `pyrefly/lib/binding/scope.rs`

In `merge_flow` (around line 2465), after partitioning branches but before merging:

```rust
// After partitioning, extract termination keys from the flows we're using
let termination_keys: Vec<Option<Idx<Key>>> = flows
    .iter()
    .map(|flow| flow.last_stmt_expr)
    .collect();

// Only create termination info if at least one branch has a last_stmt_expr
let has_termination_info = termination_keys.iter().any(|k| k.is_some());
```

Then pass this information through `merged_flow_info` to `merge_idxs`.

**Key insight**: The `termination_keys` vector is the same for all names being merged at this point (it comes from the Flow, not the per-name FlowInfo). Every name that gets a Phi in this merge needs access to the same termination keys.

---

### Step 8: Update `merge_idxs` to include termination info

**File**: `pyrefly/lib/binding/scope.rs` (around line 2273)

**New signature:**
```rust
fn merge_idxs(
    &mut self,
    branch_idxs: SmallSet<Idx<Key>>,
    phi_idx: Idx<Key>,
    loop_prior: Option<Idx<Key>>,
    join_style: JoinStyle<Idx<Key>>,
    termination_keys: Option<&[Option<Idx<Key>>]>,
    branch_value_keys: Option<&[Idx<Key>]>,  // The value key from each branch, in order
) -> Idx<Key>
```

Build `PhiTerminationInfo` if needed:

```rust
let termination_info = match (termination_keys, branch_value_keys) {
    (Some(term_keys), Some(value_keys)) if term_keys.iter().any(|k| k.is_some()) => {
        let mut value_to_branches: SmallMap<Idx<Key>, SmallVec<[usize; 2]>> = SmallMap::new();
        for (i, value_key) in value_keys.iter().enumerate() {
            value_to_branches
                .entry(*value_key)
                .or_default()
                .push(i);
        }
        Some(Box::new(PhiTerminationInfo {
            branch_termination_keys: term_keys.to_vec(),
            value_to_branches,
        }))
    }
    _ => None,
};

self.insert_binding_idx(
    phi_idx,
    Binding::Phi(join_style, branch_idxs, termination_info)
);
```

---

### Step 9: Implement solve-time filtering

**File**: `pyrefly/lib/alt/solve.rs` (around line 2120)

**Change the Phi handling:**

```rust
Binding::Phi(join_style, ks, termination_info) => {
    if ks.len() == 1 {
        self.get_idx(*ks.first().unwrap()).arc_clone()
    } else {
        // Determine which value keys to include based on termination analysis
        let live_keys: SmallSet<Idx<Key>> = match termination_info.as_ref() {
            None => ks.clone(),
            Some(info) => {
                // First, determine which branches are live
                let live_branches: SmallSet<usize> = info.branch_termination_keys
                    .iter()
                    .enumerate()
                    .filter_map(|(i, term_key)| {
                        match term_key {
                            None => Some(i), // No terminal expr, branch is live
                            Some(k) => {
                                let term_type = self.get_idx(*k);
                                if term_type.ty().is_never() {
                                    None // Branch terminated by Never
                                } else {
                                    Some(i) // Branch is live
                                }
                            }
                        }
                    })
                    .collect();

                // If all branches terminated, include all (consistent with binding-time)
                if live_branches.is_empty() {
                    ks.clone()
                } else {
                    // Include value keys that have at least one live branch
                    ks.iter()
                        .filter(|k| {
                            info.value_to_branches
                                .get(k)
                                .map_or(true, |branches| {
                                    branches.iter().any(|b| live_branches.contains(b))
                                })
                        })
                        .copied()
                        .collect()
                }
            }
        };

        let type_infos = live_keys
            .iter()
            .filter_map(|k| {
                let t: Arc<TypeInfo> = self.get_idx(*k);
                if matches!(t.ty(), Type::Overload(_)) || !t.ty().is_overload() {
                    Some(t.arc_clone())
                } else {
                    None
                }
            })
            .collect::<Vec<_>>();

        TypeInfo::join(
            type_infos,
            &|ts| self.unions(ts),
            &|got, want| self.is_subset_eq(got, want),
            join_style.map(|idx| self.get_idx(*idx)),
        )
    }
}
```

---

### Step 10: Run tests and iterate

Run the new test:
```bash
buck test pyrefly:pyrefly_library -- test_noreturn_branch_termination
```

Run the full test suite for regressions:
```bash
buck test pyrefly:pyrefly_library
```

---

## Key Concepts and Code Pointers

### 1. Understanding Flow and Branching

- **`Flow` struct** (scope.rs:432): Represents the type state at a point in program execution
- **`has_terminated`**: Set to `true` when syntactic termination is detected (return, raise, assert False)
- **Cloning flows**: When we enter a branch (if/else), we clone the base flow. Each branch evolves independently.
- **Merging flows**: After branches rejoin, we merge their states using Phi bindings

**Key function**: `merge_flow` (scope.rs:2441) - This is where branches are combined

### 2. Understanding Phi Bindings

A Phi (φ) binding represents "the value of variable X could be any of these alternatives, depending on which branch was taken."

- **Creation**: `merge_idxs` (scope.rs:2273) creates the actual `Binding::Phi`
- **Solving**: `binding_to_type_info` for `Binding::Phi` (solve.rs:2120) joins the types

**Example**:
```python
if cond:
    x = 1
else:
    x = "hello"
# After merge: x has Phi({key_for_1, key_for_hello})
# Solved type: int | str
```

### 3. Understanding StmtExpr

`Binding::StmtExpr` (binding.rs:1275) is created for expression statements—statements that are just an expression with no assignment:

```python
print("hello")      # This is a StmtExpr
x = foo()           # This is NOT a StmtExpr (it's an assignment)
foo(); bar()        # The foo() and bar() are each StmtExpr
```

The key insight: if the *final* statement in a branch is a `StmtExpr` calling a function that returns `Never`, then that branch terminates. This is why we must clear `last_stmt_expr` when processing non-`StmtExpr` statements—otherwise we'd incorrectly consider a branch terminated even when there's code after the `NoReturn` call:

```python
if cond:
    raises()  # StmtExpr returning Never
    x = 1     # Assignment after - branch is NOT terminated!
```

### 4. The ReturnImplicit Pattern (Template to Follow)

Look at solve.rs:3131-3165 for the `Binding::ReturnImplicit` handling. This is the template:

```rust
} else if x.last_exprs.as_ref().is_some_and(|xs| {
    xs.iter().all(|(last, k)| {
        let e = self.get_idx(*k);
        match last {
            LastStmt::Expr => e.ty().is_never(),
            // ...
        }
    })
}) {
    Type::never()
} else {
    Type::None
}
```

Key points:
- Store keys at binding time
- Resolve types at solve time using `self.get_idx(k)`
- Check `is_never()` to detect termination

### 5. Fork/Branch/Merge Lifecycle

```
start_fork(range)       // Save base flow, prepare for branches
  start_branch()        // Clone base flow for first branch
    ... statements ...
  finish_branch()       // Save this branch's flow
  start_branch()        // Clone base flow for second branch
    ... statements ...
  finish_branch()       // Save this branch's flow
finish_fork()           // Merge all branch flows using Phi bindings
```

**Key files**:
- `start_fork`, `start_branch`, `finish_branch`: scope.rs:2618-2671
- Branch merging: scope.rs:2673-2740

### 6. The Key Invariant

A branch's `last_stmt_expr` is only meaningful if `!has_terminated` (syntactically). If `has_terminated` is true, that branch is already filtered out at binding time, so its `last_stmt_expr` is never consulted at solve time.

### 7. Index Alignment Challenge

The `termination_keys` vector has one entry per *branch*, but the Phi's `SmallSet<Idx<Key>>` contains *unique* value keys after deduplication. These are not 1:1.

**Solution**: The `PhiTerminationInfo` struct maps each value key back to the branch indices that produced it. A value is included if at least one of its producing branches is live.

### 8. Testing Patterns

Tests in `pyrefly/lib/test/` use the `testcase!` macro:

```rust
testcase!(
    test_name,
    r#"
# Python code here
# E: Expected error message (on same line or line above)
"#,
);
```

To test narrowing, use `assert_type`:
```python
from typing import assert_type
assert_type(x, str)  # Fails if x is not exactly `str`
```

### 9. Useful Types and Functions

- `Type::never()` (pyrefly_types/src/types.rs): Creates a `Never` type
- `is_never()` (pyrefly_types/src/types.rs): Checks if a type is `Never`
- `self.get_idx(key)`: Resolves a key to `Arc<TypeInfo>` at solve time
- `SmallSet<T>`, `SmallMap<K, V>`: Space-efficient small collections from `starlark_map`
- `Idx<Key>`: Index into the bindings table

### 10. Debugging Tips

If your implementation isn't working:

1. Add debug prints in `merge_flow` to see what branches are being merged
2. Check if `last_stmt_expr` is being set correctly by printing it in `finish_branch`
3. In solve.rs, print the termination keys and their resolved types
4. Use `cargo test -- --nocapture` to see print output (for cargo) or check test output with buck

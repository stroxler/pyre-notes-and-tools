# Thread-Local Answers Solver Storage

This document describes the thread-local storage API added to the answers solver
for storing "preliminary" answers that are only visible within the current thread.

## Motivation

When solving cycles in the type graph, Pyrefly needs to store intermediate results
that should not be visible to other threads. This is necessary to:

1. **Avoid data races**: Pinning `Var`s with constraint solving needs to happen
   in isolation to prevent races between threads.
2. **Support cycle breaking**: During cycle resolution, we need to store
   placeholder values and intermediate results before committing them globally.

## Architecture Overview

The implementation consists of several components:

### `SparseIndexMap<K, V>` (graph/sparse_index_map.rs)

A lightweight map from `Idx<K>` to `V` that doesn't pre-allocate storage for
all indices in a module. Unlike `IndexMap` (which reserves space for every
binding in a module), `SparseIndexMap` uses a `SmallMap` internally, making it
efficient for storing small subsets of bindings.

Key operations:
- `new()` - Create an empty map
- `get(key: Idx<K>) -> Option<&V>` - Look up a value
- `insert(key: Idx<K>, value: V) -> Option<V>` - Insert and return previous value
- `iter()` - Iterate over (index, value) pairs

### `SparseAnswerTable` (alt/answers_solver.rs)

A table type that holds `SparseAnswerEntry<K>` for each binding kind `K`:

```rust
pub type SparseAnswerEntry<K> = SparseIndexMap<K, Either<Arc<<K as Keyed>::Answer>, Var>>;
```

The `Either` type represents:
- `Left(Arc<Answer>)` - A computed answer
- `Right(Var)` - A cyclic placeholder (a `Var` that will be resolved later)

### `PreliminaryAnswers` (alt/answers_solver.rs)

The core thread-local storage struct:

```rust
struct PreliminaryAnswers(RefCell<Option<SmallMap<ModuleInfo, SparseAnswerTable>>>);
```

This structure:
- Uses `RefCell` for interior mutability (safe because it's thread-local)
- Wraps in `Option` to short-circuit lookups when no preliminary answers exist
- Maps by `ModuleInfo` because cycles can cross module boundaries

#### API

**Reading:**

```rust
fn get_idx<K>(&self, module_info: &ModuleInfo, idx: Idx<K>) -> Option<Either<Arc<K::Answer>, Var>>
```

Look up a preliminary answer for a binding in a specific module.

**Recording (low-level):**

```rust
fn record<K>(
    &self,
    module_info: &ModuleInfo,
    idx: Idx<K>,
    result: Either<Arc<K::Answer>, Var>,
) -> Option<Var>
```

Record a result (either an answer or a cyclic placeholder). Returns any
previously-recorded cyclic `Var` placeholder if one existed.

**Recording cyclic placeholders:**

```rust
fn record_cyclic<K>(&self, module_info: &ModuleInfo, idx: Idx<K>, var: Var)
```

Record a cyclic placeholder. Panics if a placeholder was already recorded
for this binding.

**Recording answers:**

```rust
fn record_answer<K>(
    &self,
    module_info: &ModuleInfo,
    idx: Idx<K>,
    answer: Arc<K::Answer>,
) -> Option<Var>
```

Record a final answer. Returns any previously-recorded cyclic placeholder
so the caller can finalize the `Var`-to-answer mapping.

**Bulk retrieval:**

```rust
fn reset_and_get_all(&mut self) -> SmallMap<ModuleInfo, SparseAnswerTable>
```

Get all preliminary answers and reset the storage to `None`. Used when a
cycle completes to move answers into the global `Answers` storage.

### `ThreadState` (alt/answers_solver.rs)

Thread-local state passed through the solver:

```rust
pub struct ThreadState {
    cycles: Cycles,
    stack: CalcStack,
    preliminary_answers: PreliminaryAnswers,
    debug: RefCell<bool>,
}
```

The `preliminary_answers` field stores per-thread preliminary results.

### Integration with `AnswersSolver`

The `AnswersSolver::get_idx` method checks preliminary answers before
looking in the global `Answers`:

```rust
fn get_preliminary<K: Solve<Ans>>(&self, idx: Idx<K>) -> Option<Arc<K::Answer>> {
    self.thread_state
        .preliminary_answers
        .get_idx(self.module(), idx)
        .map(|result| match result {
            Either::Left(answer) => answer,
            Either::Right(var) => Arc::new(K::promote_recursive(var)),
        })
}

pub fn get_idx<K: Solve<Ans>>(&self, idx: Idx<K>) -> Arc<K::Answer> {
    // Check preliminary answers first
    if let Some(result) = self.get_preliminary(idx) {
        return result;
    }
    // ... proceed with normal calculation
}
```

### Global Answer Setting

To commit preliminary answers to global storage, `Answers::set_idx` allows
directly setting an answer:

```rust
pub fn set_idx<K: Keyed>(&self, k: Idx<K>, answer: Arc<K::Answer>) {
    self.table
        .get::<K>()
        .get(k)
        .map(|calculation| calculation.record_value(answer, |_r, value| value));
}
```

And `TransactionHandle::record_answer` provides a higher-level API that handles
the state machine (checking whether we're in the answers or solutions phase):

```rust
fn record_answer<K: Solve<...> + Exported>(
    &self,
    module_data: ArcId<ModuleDataMut>,
    idx: Idx<K>,
    answer: Arc<K::Answer>,
) {
    let lock = module_data.state.read();
    if lock.steps.solutions.is_some() {
        // Already finalized, nothing to do
    } else if let Some(bindings_and_answers) = &lock.steps.answers {
        bindings_and_answers.1.set_idx(idx, answer);
    } else {
        unreachable!("...");
    }
}
```

## Data Flow

1. When a cycle is detected during solving, the solver can store placeholder
   `Var`s in `preliminary_answers`
2. As the cycle unwinds, computed answers replace the placeholders
3. The preliminary answers are visible only to the current thread's solver
4. When the cycle fully resolves, `reset_and_get_all()` retrieves all answers
5. The answers are then committed globally via `Answers::set_idx`

## Current Status

The APIs are built but marked with `#[expect(dead_code)]`. They provide the
infrastructure for isolating `Var` pinning to prevent data races during
cycle resolution.

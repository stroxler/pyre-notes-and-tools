# JAX Examples for Pyrefly Array Shape Support

This repository contains two corpuses of JAX examples designed to drive the
development of numpy/jax stubs for Pyrefly's tensor shape tracking system.

## Structure

### `progressive/` — Progressive API demos (~50 files)

A ladder of small, focused examples that each introduce a few new JAX/numpy
operations. These are meant to be committed incrementally, with each commit
driving stub development for the operations it introduces.

The examples progress from basic tensor creation through advanced patterns
used in real neural networks. Each file is self-contained and exercises
specific operations that need stub support.

See [progressive/README.md](progressive/README.md) for the full ladder.

### `models/` — Real-world model annotations (~25-30 files)

Copies of well-known open-source JAX model implementations, annotated with
jaxtyping shape annotations. These prove out the flow of adding annotations
to existing, idiomatic JAX code.

Models are drawn from official repositories (Flax examples, dm-haiku,
vision_transformer, etc.) covering vision, NLP, RL, and generative domains.

See [models/README.md](models/README.md) for the source catalog and status.

## Relationship to Pyrefly torch examples

The existing torch examples in `pyrefly/tensor-shapes/examples/torch/` cover
29 models. This JAX corpus mirrors that coverage where possible, using
real open-source JAX implementations rather than torch-to-jax conversions.

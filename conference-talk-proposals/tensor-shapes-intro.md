# Static Tensor Shape Checking for PyTorch with Pyrefly

## Abstract (~150 words)

Shape errors are the most common source of bugs in PyTorch models, yet they
remain invisible until runtime. We present tensor shape types in Pyrefly — a
practical static checker that tracks tensor shapes through entire models,
showing developers the shape of every intermediate tensor as an inline type hint
and catching mismatches before execution.

Our approach extends Python's type system with symbolic integer arithmetic
(e.g., `Tensor[B, D // NHead, T]`), a shape transform DSL for specifying how
each PyTorch operator transforms shapes, and the `Dim[X]` type that bridges
runtime values to type-level symbols. The system requires no constraint solver —
just normalization-based equality.

We demonstrate the system on 28 real-world models spanning LLMs, vision, audio,
recommenders, and RL, achieving end-to-end shape coverage with ~30 annotations
per model. We discuss coverage limits, syntax ergonomics, and how AI assistants
can automatically port existing models to use shape annotations.

## Outline

### The Problem (3-5 min)

Tensor shapes can be hard to track: every op makes non-trivial transformations.
Mistakes can be frustrating - crashes that don't happen right away, or only in
some situations.

Today, ML developers often use shapes in comments, develop in a notebook using
test data, or use print debugging.

We would like to do better: provide a way to statically understand shapes for
quick, automatic feedback that is easy to verify with a type checker and we
can see directly in our editor.

### Demo (7-10 min)

Show how tensor shape types work in a transformer model:
- How inline shape hints appear in real time and can help us trace the code
- How the type checker can give humans and agents immediate feedback about errors

### The Design (8-10 min)

How do we make this actually work?

We add symbolic integer type parameters to the type system:
- Type variables like `N` and `M` can be combined with concrete integers
  to be passed as type parameters (e.g. `N // M`, `N * M + 1`).
- Equality works by normalization - there is no constraint solver, to keep this
  simple and fast.

We add two new generic types:
- `Tensor[B, C, H, W]` describes a shape, and is variadic in the rank of a tensor
- `m: Dim[M]` allows us to state that an integer argument `m` should be treated
  as a symbolic integer. This lets us model things like `def arange[N](n: Dim[N]) -> Tensor[n]`

We provide a shape-transform DSL to describe shape transformations in a simple
subset of ordinary Python code.
- This is a key innovation - it avoids the need for a type-level algebra of all
  shape operations.
- The approach was inspired by the symbolic tensors used inside the Pytorch compiler's
  tracing jit.

Finally, we provide some special support for `nn.Module` which allows us to
model improtant modules like `nn.Linear[In, Out]` and `nn.Conv2d[InC, OutC, K, S, P, D]`.


### Evaluation: 28 Real Models (5-7 min)

In order to validate the basic approach and build out a minimal viable set of
stubs for Pytorch, we annotated 28 real open-source models (21 from TorchBench
and 7 others) with shape types.

Architecture families covered:
- LLMs (LLaMA, NanoGPT, Mixtral),
- Vision (ResNet, DenseNet, SAM, Squeezenet)
- Audio (Demucs, Tacotron2)
- Recommenders (DLRM)
- RL (Soft Actor-Critic, DrQ)

What we learned:
- These models averaged about 450 lines of code
- It took about 30 annotations per model
- What we learned: typical models can mostly be covered by static shapes
  - We usually encountered 1-2 places per model where we had to fall back to a
    gradual `Tensor` or use a `# type: ignore`, the rest were well-typed.
  - Heterogeneous lists and divisbility constraints were the biggest causes
    of us losing track of the shapes.

### AI-Assisted Porting (3-5 min)

We used Claude for porting all 28 models. In the process, we built a skill with
a structured flow for auditing the ops, adding annotations, and validating with
`assert_type`.

The skill is designed to be usable in a loop, usually 1-2 iterations is enough
to annotate a model. Often AI is initially pessimistic about static types
and later discovers that they work better than expected.

### Syntax & Adoption (3-5 min)

Our current syntax will work out of the box with `from __future__ import annotations`
using PEP-695-style scoped type parameters; these will not work at runtime since
the built in `TypeVar` type does not support arithmetic. This is something we hope
to change with a PEP, but we'll need adoption first to make a case for changing
CPython.

We also provide our own `TypeVar` in a `shape_extensions` module that will work at
runtime using legacy syntax.

Finally, we support desugaring jaxtyping-style annotations, to support jaxtyping
users out-of-the-box wherever functions are annotated.

## Key Features

Pyrefly's approach to tensor shape types features a number of key innovations, compared to
previous attempts like Pyre, that we believe make it viable for production codebases:
- We have a lightweight syntax in which symbolic dimensions are ordinary type variables
- Our DSL for writing shape transforms that is directly inspired by the pytorch compiler
- Support for jaxtyping as an alternative syntax

We have used shapes in 28 open-source models ranging from computer vision to transformer
architectures. This helped us improve our approach, and gives us confidence that it can
work for real codebases.

## Speaker Bios

Avik Chaudhuri is a software engineer on Meta's Python team, working on both
Pyrefly and triton. He is a former member of the Pytorch compiler team, and
was the initial lead developer for Flow, Meta's javascript type checker.

Steven Troxler is a software engineer on Meta's Python team, working on Pyrefly
— Meta's open-source Python type checker. He is the author of PEP 698 adding an
`@override` decorator to Python, and has hosted the PyCon Typing Summit for
the past 3 years.


## Resources

- Pyrefly website: https://pyrefly.org
- Tensor shapes docs: https://pyrefly.org/en/docs/tensor-shapes/
- 28 example models: github.com/[pyrefly repo]/test/tensor_shapes/models/
- Short talk targeted at typing experts at the PyCon typing summit: https://www.youtube.com/watch?v=HE5EyQW_7eY

## Tailoring Notes

**For PyTorch Conference** (most technical): Emphasize the DSL architecture,
*connection to torch.compile's symbolic shapes, and path to hosting stubs in
*PyTorch. Use "Core PyTorch" track.

**For PyBay** (Python audience): Lead with the type system innovation angle —
*"teaching Python to count." Emphasize syntax ergonomics, the typing community
*conversation, and that these ideas generalize beyond ML.

**For ODSC** (practitioners): Lead with the pain point ("never debug `mat1 and
*mat2 shapes cannot be multiplied` again"). Emphasize the inline hints developer
*experience, AI-assisted porting, and getting started in 5 minutes.



Proposal is at https://github.com/stroxler/pyre-notes-and-tools/blob/main/conference-talk-proposals/tensor-shapes-intro.md, this copy made for collaborative commenting / editing


# Static Tensor Shape Checking for PyTorch with Pyrefly


## Audience

This talk is for PyTorch developers who:
- Have been frustrated by shape errors that only surface at runtime
- Are curious about how static analysis can improve the model development experience
- Want to understand how Pyrefly tensor shape checking works and try it on their own models

Familiarity with PyTorch and basic Python type hints is helpful but not required.


## Abstract (~150 words)

Shape errors are the most common source of bugs in a PyTorch model. An
empirical study found that tensor shape faults account for 45% of failures in
deep learning programs [1]. Normally the problems cannot be found until runtime.

This talk introduces tensor shape types in Pyrefly, Meta’s new python type checker.
This static analysis, inspired by the shape tracking in the pytorch compiler, can show
shapes of tensors in a model as inline type hints and catch shape mismatches
immediately.

Under the hood, the system extends Python's type system with symbolic integer
arithmetic (e.g., `Tensor[B, D // NHead, T]`), a shape transform DSL for
specifying how each PyTorch operator transforms shapes, and the `Dim[X]` type
that bridges runtime values to type-level symbols — no constraint solver needed.

We'll walk through results from real-world models spanning LLMs, vision,
audio, recommenders, and RL, and show how AI assistants can automatically port
existing models to use shape annotations with ~30 annotations per model.


## What attendees will learn

- How to read and write tensor shape annotations in Pyrefly
- What kinds of shape errors static checking can catch, and where it hits limits
- How shape transforms are defined, and the connection to torch.compile symbolic shapes
- How to try shape checking on your own models, including AI-assisted porting


## Why this matters now

**Shape errors are the #1 bug class in deep learning.** Empirical research
has found that tensor shape faults account for 45% of failures in deep learning
programs [1], and 65.82% of crashing shape faults only manifest at execution
time, not during model construction [2]. Despite this, the most common
mitigations remain ad-hoc: shape comments, notebook-based testing, and print
debugging.

**torch.compile makes shape understanding critical.** Shape mismatches are
one of the most common causes of torch.compile recompilations. Each
recompilation is slow and memory-intensive, and after 8 recompilations per
function the compiler falls back to eager mode entirely. Static shape
checking can help developers identify which dimensions are truly static vs.
dynamic, enabling more effective use of torch.compile's `dynamic` settings and
avoiding accidental recompilation in production serving.

**The community is already reaching for solutions.** jaxtyping has over 5
million monthly PyPI downloads for runtime shape checking. einops (9.5k GitHub
stars, ICLR 2022) was built specifically to address shape readability: as its
author puts it, shape "comments don't prevent mistakes, [are] not tested, and
without code review tend to be outdated." PyTorch's own named tensors feature,
motivated by similar concerns, has remained experimental for over 5 years.
Static shape types build on this momentum with a complementary approach:
catching errors before execution rather than at runtime.

**Static checks solve problems existing tools do not** While jaxtyping can
undeniably be useful, actually  getting feedback requires a runtime type
checker, which simply checks actual shapes on the data given. This runtime
check has a few gaps compared to static analysis:
- It requires running the code, versus near-instant feedback from type checks
- It only looks at sample dimensions, which can hide bugs that only surface
  in production if the sample data happens to have some dimensions that are
  always equal.
- It can interfere with graph analysis on `torch.compile`


## Outline

### The Problem (3-5 min)

Tensor shapes can be hard to track: every op makes non-trivial transformations.
Mistakes can be frustrating - crashes that don't happen right away, or only in
some situations. A study found that shape faults account for 45% of failures in
deep learning programs [1].

Shape errors aren't just a debugging problem — they're also a torch.compile
problem. Shape mismatches trigger recompilations, which can cause performance
and memory problems in production.

Today, ML developers often use shapes in comments, develop in a notebook using
test data, or use print debugging. What if you could statically understand
shapes for quick, automatic feedback that you can verify with a type checker
and see directly in your editor?

Related tools like jaxtyping have been useful but only check at runtime, which
limits the expressiveness and gives a slower feedback loop. Moreover, they can
interfere with torch.compile. Checking statically avoids this - there’s no
runtime cost, the symbolic dimensions can express intent better (especially
when dimensions might happen to be equal on simple examples but not always in
production) and the feedback after an edit is nearly-instant.

### Demo (7-10 min)

Walk through tensor shape types in a transformer model:
- See how inline shape hints appear in real time and help you trace the code
- See how the type checker gives humans and agents immediate feedback about errors

### The Design (8-10 min)

How does this actually work?

The system adds symbolic integer type parameters to Python's type system:
- Type variables like `N` and `M` can be combined with concrete integers
  to be passed as type parameters (e.g. `N // M`, `N * M + 1`).
- Equality works by normalization - there is no constraint solver, to keep this
  simple and fast.

Two new generic types make this ergonomic:
- `Tensor[B, C, H, W]` describes a shape, and is variadic in the rank of a tensor
- `m: Dim[M]` allows us to state that an integer argument `m` should be treated
  as a symbolic integer. This lets us model things like `def arange[N](n: Dim[N]) -> Tensor[n]`

A shape-transform DSL describes how each op transforms shapes, written in a simple
subset of ordinary Python code.
- This is a key innovation - it avoids the need for a type-level algebra of all
  shape operations.
- The approach was inspired by the symbolic tensors used inside the PyTorch
  compiler's tracing jit.

There is also special support for `nn.Module` which allows modeling
important modules like `nn.Linear[In, Out]` and `nn.Conv2d[InC, OutC, K, S, P, D]`.

### Evaluation against Real Models (5-7 min)

To validate the approach and build out a minimal viable set of stubs for
PyTorch, we annotated 28 real open-source models (21 from TorchBench and 7
others) with shape types.

Architecture families covered:
- LLMs (LLaMA, NanoGPT, Mixtral),
- Vision (ResNet, DenseNet, SAM, Squeezenet)
- Audio (Demucs, Tacotron2)
- Recommenders (DLRM)
- RL (Soft Actor-Critic, DrQ)

What we learned:
- These models averaged about 450 lines of code
- It took about 30 annotations per model
- Typical models can mostly be covered by static shapes
  - We usually encountered 1-2 places per model where we had to fall back to a
    gradual `Tensor` or use a `# type: ignore`, the rest were well-typed.
  - Heterogeneous lists and divisbility constraints were the biggest causes
    of us losing track of the shapes.
- We also built and tested support for jaxtyping-style annotations, so
  projects already using jaxtyping can get shape checking out of the box.

### AI-Assisted Porting (3-5 min)

We used Claude for porting all 28 models. In the process, we built a skill with
a structured flow for auditing the ops, adding annotations, and validating with
`assert_type`.

The skill is designed to be usable in a loop, usually 1-2 iterations is enough
to annotate a model. Often AI is initially pessimistic about static types
and later discovers that they work better than expected.


## References

- [1] Chen et al., "An Empirical Study on Tensor Shape Faults in Deep Learning
  Systems," 2021. https://arxiv.org/abs/2106.02887
- [2] Xiao et al., "Tensfa: Detecting and Repairing Tensor Shape Faults in
  Deep Learning Systems," ISSRE 2021.


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


## Bottom matter (NOT FOR TALK PROPOSAL)

Some more sections of material that might help us tailor talk proposals
*after* Pytorch conference, particularly once we've hopefully expanded
support beyond just torch.

### Tailoring Notes

**For PyBay** (Python audience): Lead with the type system innovation angle —
*"teaching Python to count." Emphasize syntax ergonomics, the typing community
*conversation, and that these ideas generalize beyond ML.

**For ODSC** (practitioners): Lead with the pain point ("never debug `mat1 and
*mat2 shapes cannot be multiplied` again"). Emphasize the inline hints developer
*experience, AI-assisted porting, and getting started in 5 minutes.

### Further Discussion of Shape Errors

#### Shape errors as a barrier for PyTorch beginners

Multiple independent PyTorch teaching resources converge on shape errors as
the #1 stumbling block for learners. None cite rigorous survey data, but the
consistency across sources is notable:

- Zero to Mastery's PyTorch course lists shape errors as #1 of the three
  most common PyTorch errors (alongside device and dtype errors), framing
  them as something that "happens to every programmer."
  https://www.learnpytorch.io/pytorch_most_common_errors/

- HeyTensor calls shape errors "the most common category of PyTorch
  RuntimeErrors" and notes the mat1/mat2 mismatch is "the single most
  common PyTorch shape error." Key pedagogical insight: errors often arise
  not from the layer that throws the error but from upstream operations, and
  "the wording can be cryptic if you do not know what to look for."
  https://heytensor.com/blog/pytorch-shape-errors-explained.html

- apxml.com's PyTorch course calls them "Perhaps the most common runtime
  error in PyTorch" and frames them as inevitable growing pains.
  https://apxml.com/courses/getting-started-with-pytorch/chapter-8-monitoring-debugging-models/common-pytorch-pitfalls

The recommended debugging strategy across these resources — printing shapes
at every intermediate step — is exactly the workflow that Pyrefly's inline
shape hints replace. This could be a compelling angle when approaching ML
educators about adopting shape types as a teaching tool.

#### JAX ecosystem: a natural fit for static shape types

JAX's jit compilation requires static shapes — "it requires all arrays to
have static shapes" — and shape changes trigger recompilation, just like
torch.compile. JAX code already needs static shape reasoning; a static
shape checker can verify that reasoning is correct.
https://docs.jax.dev/en/latest/notebooks/thinking_in_jax.html

JAX is also where the shape-checking community has been most active.
jaxtyping originated in the JAX ecosystem (from the author of Equinox and
Diffrax), and JAX itself offers a `JAX_NUMPY_RANK_PROMOTION=raise` setting
to disable silent broadcasting — evidence the JAX team considers accidental
broadcasting dangerous enough to provide an opt-out.
https://docs.jax.dev/en/latest/tracing.html

JAX's functional programming model (immutable arrays, pure functions,
composable transformations like jit/grad/vmap) also means JAX code tends
to be more straight-line than PyTorch, with fewer dynamic control flow
patterns. This makes it likely that shape types would achieve higher
coverage on typical JAX codebases than on PyTorch.

#### NumPy: silent broadcasting as a shape-checking motivation

NumPy has roughly 960 million monthly PyPI downloads — orders of magnitude
larger than PyTorch or JAX — and is used across scientific computing,
statistics, and data processing well beyond ML. 51% of Python developers
work in data exploration/processing, with NumPy and pandas as the most
common tools (JetBrains Python Developer Survey 2025).
https://pypistats.org/packages/numpy
https://blog.jetbrains.com/pycharm/2025/08/the-state-of-python-2025/

The most compelling shape-checking angle for NumPy is not crash-inducing
errors but *silent broadcasting bugs*. As one NumPy tutorial puts it:
"Worse than errors: operations that succeed but produce wrong results."
The classic trap is `(n,)` vs `(n,1)` vs `(1,n)` — all three broadcast
against a matrix successfully but produce semantically different results.
A function expecting element-wise multiplication can silently produce an
outer product if a vector is accidentally reshaped to a column vector.
https://sungchullee.github.io/python_book_writing/ch09/broadcasting/failures_debugging/

A blog post on using jaxtyping with NumPy describes how shape annotations
can catch these bugs: annotating a function with the expected shape
prevents a `(3,1)` array from being passed where a `(3,)` is expected.
The `#` modifier in jaxtyping makes broadcasting opt-in per dimension,
forcing developers to declare intent explicitly.
https://geeksilas.bearblog.dev/jaxtyping-enhancing-type-safety-and-catching-silent-bugs-in-pytorch-numpy-and-beyond-with-einops/




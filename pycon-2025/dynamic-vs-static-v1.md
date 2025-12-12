# Title

**Mind the gap! When Python’s dynamic patterns fight static types**

# Duration

30 Minutes

# Audience

This talk is for Python developers who:
- Have tried adding types to existing code and struggled
- Want to understand common Python idioms that are difficult to type
- Are curious about tradeoffs with static typing, and how to use it judiciously

Being experienced with Python and familiar with simple type ints (for
example `def foo(x: int) -> str: ...`) is helpful but you don't need to be
an expert.


# Abstract

Have you ever tried to add types to an existing Python library or application and hit a wall or wondered why it can be so hard? This talk is for you!

Static typing is a powerful lever for working with code. It provides verifiable documentation, can find bugs quickly and enable fearless (well let's be honest, somewhat less scary) refactors, and allows us to leverage powerful tools like modern IDEs to understand and navigate code.

But often developers and even type thoerists approach the problem of turning untyped code into statically typed code as though it were merely a problem of adding annotations. This is often not the case, and it can be helpful to understand why.

Python was concieved as a dynamically typed language, and much of it's rich library ecosystem was written without types. And many of the powerful patterns that make dynamically typed Python useful are difficult to statically type for
example
- Pervasive use of duck typing
- Use of metaprogramming and classes with highly dynamic behavior
- Reliance of flow-sensitive type information that type checkers cannot track
- Using heterogenious containers in ways that the type system can't model

We'll explore some of these patterns, why they are hard to type and might not be worth typing, and some advice for how to get the most out of the type system without trying to force inherently dynamic code to be statically typed.

We'll also look at the many ways Python's type system has evolved to support more dynamic use cases over the years, and a few possible future directions.

## Does the proposal need more pizzaz?

The v0 doc includes a few sections I've skipped for now:
- "Why this talk matters now"
- "What attendees will learn"
- "Additional notes", including differentiation

Need to figure out if / where these kinds of blurbs should be included in the final proposal.

## Details

## Types and their value (5 minutes)

A lightning introduction to static type syntax, gradual typing and the `Any` type

A very short discussion of the evolution of types in the library ecosystem
- Increasing adoption of types by widely-used libraries like numpy
- New libraries like pydantic, typer, and httpx that are type-centric

A very short discussion of the role of types in tooling
- Types at the center of IDE functionality in OOP languages (method resolution)
- Types as a way to increase the leverage of AI agents with fast feedback

## Dynamic Pattern 1: Duck Typing (5 minutes)

Introduction to duck typing and how the runtime is duck-typed
- Relationship to nominal typing and to inheritance

Discussion of duck-typing as a programming pattern
- Enables using libraries in unexpected ways (a familiar example: Python unit testing has always relied heavily on duck typing; this is part of how a mock works)

- That can be powerful for rapid iteration, but also has downsides - it's easy to couple to library internals

Duck typing and the static type system
- The initial static type system had no support
- PEP 544 added support but there's a gap:
  - Protcols require explicit declaration, so even if they work it's no longer just adding annotations to code
  - You can't declare duck-type compatibility with existing classes

Examples in the wild
- cupy and cuDF duck type numpy and pandas classes with GPU-accellerated versions
- FakeTensor in torch dynamo duck types Tensor, not permitted

## Dynamic Pattern 2: Heterogeneous Collections (5 minutes)

Idiomatic dynamically-typed Python makes wide use of built-in-data structures
- Common for data ingestion, consuming json APIs or configuration
- DataFrames, which are only partially typed - type checkers don't understand the column types
- Can be a core part of an implementation (example - maybe a tiny interpreter, or minikanren?)

Statically typed python doesn't support code that relies on heterogenious containers well
- Typed dicts can help with dicts, but not sets or lists
- Big unions are hard to work with, and even if you narrow types the narrows may not carry
- Mutable containers are invariant, and often existing logic uses them covariantly
  - You can sometimes get around this by using Sequence or Mapping, but not always

One approach that often helps, not only with typing but with application architecture, is defining a validation barrier
  - Libraries like Pydantic can help with this

## Dynamic Pattern 3: Flow-dependent Logic and Dynamic Classes (5 minutes)

It's common for dynamic code to use narrows (which static type checkers do support in simple cases) in ways that exceed type checker limitations, for example:
- narrowing multiple variables together and reusing the condition later
- relying on invariants that aren't written down as part of the type reasoning

Class construction is another common place for highly dynamic logic
- Dynamically-typed python just sets attributes on classes and instances freely; often an attribute might or might not be set and the runtime just throws an error on bad lookups
- Some type checkers support inferring types not declared in the body (especially if set in constructors), but there are limits both to inference and safety and tradeoffs between them
- It's possible to create some really cool magic using custom metaclasses or class decorators.
  - This is sometimes used, for example to define methods automatically based on class attributes.
  - With the exception of dataclass-like libraries, static type checkers won't understand.


## Bridging the gap (10 minutes)

### Converting Dynamic Code

For fast-changing and business-critical code where safety and great tooling support is essential, it may be worth substatially rewriting the code to get types.

Be on the lookout for easy wins:
- Situations where refactoring to use simple types like `dataclasses` can make things clearer and play well with the type system
- Containers that should be typed using covariant types (e.g. `Sequence` instead of `list`)
- Protocols that just need to be defined and used

For duck-typing, a hack that can work is to add a method that casts your duck type into
the type you'd like to pretend it is.

### Living with Dynamic Code

Often it might not be worth adding types to existing code.

If you have stable code that is battle-tested, has good unit tests, and doesn't change often, the benefits of types may not matter much and the cost of trying to make changes could be too high.

If your code is inherently very dynamic - like data analyses making heavy use of dataframes, it can be wise to embrace `Any` where it is needed. You may still see big benefits from IDE features from even partial type information.

In a bigger application, it can be very helpful to focus on providing types at boundaries between systems, and often data validation with libraries like Pydantic or runtime type checkers like beartype and typeguard can help.


### Expanding Python's type system

Dynamic code is sometimes just code that the existing type system doesn't understand yet.

Python's type system has already expanded to close many gaps:
- PEP 544 (Protocols): enabled structural typing
- PEP 612 (ParamSpec): dramatically improved decorator typing
- PEP 647/724 (TypeGuard/TypeIs): better custom narrowing
- PEP 673 (Self): recursive type annotations
- PEP 681 (Data Class Transforms): greatly improved support for libraries like attrs and pydantic

The type system can evolve to handle dynamic patterns!

Are there opportunities to close more gaps?
- Better narrowing across multiple variables
- More expressive ParamSpec (add/remove specific kwargs)
- DataFrame typing improvements:
  - Index types by TypedDict for column access?
  - Abstract operations relating columns to types?
- Explicit duck-type declarations?
The typing community is active and open to proposals


# Additional Notes

## Why this talk matters now

- Survey data divide: 91% of typing-aware developers use types, but many developers avoid typing entirely
- Divide in the community: many Python developers advocate types strongly or dislike them, often the gap is less clear than it could be
- Ecosystem changes: many libraries (e.g. numpy, django) are in the midst of trying to adopt types and may face these challenges

## What Attendees will learn

- Historical context on how Python was used before static types
- An understanding of common challenges trying to add types to code whose semantics don't fit
- Approaches for dealing with code that is difficult to statically type
- Perspective on how the Python type system sometimes evolves to handle a wider range of existing patterns

## Differentiation from existing talks

Typical typing talks are either "how to use types" (focusing on adding types assuming code is already possible to statically type) or "why types are good" (advocacy). This talk is "when types don't fit" (semantics) and options for what to do, filling a gap for developers facing real migration challenges.
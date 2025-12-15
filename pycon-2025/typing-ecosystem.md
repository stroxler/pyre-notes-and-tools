# Title

**The case for Python type hints: Updated for 2026**

# Duration

30 Minutes

# Audience

This talk is for:

- New Python users trying to decide whether it is worth learning to use type
  annotations from the start
- Anyone frequently starting new applications and needing to decide when or if
  to use types
- Experienced developers who have tried types before and decided the benefits
  didn't outweigh the costs

Experience with software development will be helpful, but this talk is mostly
conceptual and about changes to Python's library and tooling ecosystem, so no
particular expertise with Python typing is needed.

# Abstract

For years, the conventional wisdom around Python type hints was that they are
valuable for large, long-lived applications but they may not be worth using for
scripts, smaller projects, or beginners. What if that advice is outdated?

This talk explores how changes in the Python ecosystem have drastically changed
the tradeoffs on using types in the past 2-3 years, both lowering costs and
increasing benefits:

- Better typed libraries, better type inference, and faster type checkers have
  all made it easier to add types
- The emergence of type-centric libraries and the integration of type checkers
  into IDE tooling have made types more useful than ever

With AI-assisted programming, this trend shows signs of accelerating even more
because

- AI can make it much easier to write type hints on both new and existing code
- Type information and type checking can be a big help to AI, reducing
  hallucinations and providing very fast iteration

## What attendees will learn

- Changes in Python tooling that make types easier to add and more useful for
  hacking
- Changes in the Python library ecosystem to use types better, and sometimes get
  functionality for free from types
- How AI development may rapidly accelerate these trends
  - Further bringing down the costs of adding and using types
  - Greatly increasing the importance of types for validating generated code and
    limiting hallucinations

# Details

## Introduction: Why Types Feel Different now (5 minutes)

Conventional wisdom in Python has been that types are mainly useful in large,
long-lived codebases but not scripts, and aren't suitable for beginners. Types
came with many downsides:

- Many Python programs can't easily be statically typed (this is still true!)
- Writing out types took time, annotating codebases after the fact was very
  difficult
- Often third-party libraries lacked types, so even with annotations you might
  not get much safety
- Type checkers were often slow to run, the feedback loop was not nearly as good
  as, for example, Java with an IDE like IntelliJ.

Recent improvements to the tooling around Python typing and library ecosystem
have shifted the tradeoff. Typing might still not be right for you, but it's
worth understanding some of these shifts.

## Shift 1: Faster and IDE-native Type Checkers (5 minutes)

In the past, type checking usually required running a cli tool.

- Early type checkers like mypy and pyre prioritized correctness and fast batch
  processing, but often felt separate from the editing experience.
- TypeScript showed the industry how valuable an IDE-focused approach could be,
  even if it meant trading off some soundness for developer experience.
- Pyright brought this philosophy to Python, adopting a similar architecture to
  mainstream the idea of lazy, incremental, and responsive typing.
- The latest generation of type checkers (`Pyrefly`, `ty`, and `zuban`) are
  trying to get the benefits of both approaches: the correctness of the early
  tools with the speed and DX of the new wave.

Type inference has gotten more powerful as well: many type checkers can now
infer return types or empty container types, which reduces the need for
annotations.

With these fast and IDE native type checkers, you get much more than catching
bugs. Python code is frequently object-oriented, so only a type analysis can
easily track the identities of things across attribute access. This means types
are key to getting:

- Autocompletion and signature help
- Go-to-definition
- Automated refactors (e.g. rename a class attribute)

To me, this is one of the most important shifts. I remember when I first worked
in Java as a longtime Pythonista in 2015, I mostly hated it but the ability to
explore library APIs with autocomplete felt magical. Now we can have that in
Python!

## Shift 2: Libraries Built Around Types (5 minutes)

The Python library ecosystem used to be a major barrier to using types - even if
you annotated code, often you'd have a type of `Any` as soon as you talked to a
third party library (or worse yet, it would be a C extension with no stubs so
you'd have to go write stubs yourself).

Over the years many library maintainers have added types because they find types
are a feature or help with maintainability. And typeshed maintains stubs for
many of the other libraries; these get better over time:

- SQLAlchemy 2.0 rewrote with types in mind in 2023
- NumPy's 2025 type coverage jump: 33% → 88% in months
- From survey data: in 2025 91% of typing-aware developers use types "always" or
  "often"
  - Resistance is dropping too: the number of respondents citing coworker
    pushback as a barrier dropped by ~30% from 2024 to 2025.

In addition, many new libraries are type-first by design, and often the types
can actually save you a lot of time and work:

- Pydantic lets you write a class with type hints and get validation and
  serialization for free
  - In traditional python, validation could take many lines of code and be hard
    to maintain or read
- FastAPI uses type hints (and Pydantic) to get request validation, API schemas,
  and documentation automatically from type hints
- SQLModel is a type-powered library for integrating with relational databases
  - It fuses SQLAlchemy and Pydantic to bring validation and DB integration
    together
- Hydra is a configuration engine (originally built with ML applications in
  mind) that can integrate with Pydantic to type configurations
  - It's been estimated that over half of outages are caused by configuration
    errors
- Typer generates CLI interfaces from type hints
  - Compared to older CLI interfaces this can be more concise and much easier to
    document
  - This is a great example of why type hints may now be worth using even in
    small scripts

## Shift 3: AI Supercharges Typing (10 minutes)

With AI, you may no longer need to write types by hand:

- If AI is writing code, we can teach it how to use types from the start
- And AI can also help with one of the most vexing problems: migrating untyped
  code to have type annotations
  - Earlier ML approaches like TypeWriter showed promise
  - Recent experiments using LLMs have shown great promise

More importantly, types are a very valuable tool for using AI to work with code

- Types provide structured context about code at generation time
  - Code graphs like Glean and CodeQL can help AI explore large codebases or
    dependency trees in a structured way, and with more types they can index
    better
  - LSP-MCP integrations can allow AI to query information (like what is this
    type, where is it defined, what completions are available) just like an IDE
- And types are a valuable tool for validating the results
  - Type checking is very fast, can provide a much tighter inner iteration cycle
    for an AI agent than running tests
    - Academic research suggests up to an 80% reduction in mistakes where
      generated code tries to use undefined symbols
    - The very specific errors, which include line numbers, seem to accelerate
      AI's ability to course-correct from feedback
  - Types can also help with one of the biggest concerns with AI coding:
    security
    - Some security features can be encoded directly into library types (for
      example, PEP 675 allows libraries to prevent user-controlled data from
      flowing into SQL queries or shell calls to avoid injection attacks)
    - The presence of types can enable downstream static analysis - for example
      Meta relies heavily on the Pysa taint analyzer for security, but it needs
      types in order to resolve method calls

One other thing to consider

- Types serve as a kind of documentation of code that can be both
  programmatically verified and programmatically used to provide tools like IDE
  features.
  - This is part of why, in the early days, typing was most used by large
    companies
  - It's true that types add "line noise" -- a metadata cost that can make code
    harder for humans to scan.
  - But as we rely more on AI to summarize and navigate code, the tradeoff
    shifts: machine-readable metadata becomes more valuable than purely human-
    readable aesthetics.
- Traditionally, individual developers and small teams didn't need this as much
  - Often the codebases were small enough to hold in our heads
  - The benefits of dynamic typing (which is powerful!) often outweighed the
    benefits of static typing
- But with the advent of widespread vibe coding, this may change
  - Even individual developers may now be facing codebases they didn't write by
    hand and don't understand as fully

## Conclusion (5 minutes)

Python typing has made tremendous strides in usability and adoption in the last
few years.

Especially with the growth in vibe coding, now is a great time to revisit
assumptions about when types are useful.

Now's an exciting time to explore the future of Python, and how types might or
might not play a role. We have many open problems:

- Learning how best to integrate type information and code indexes with AI
- Understanding how to teach AI to use types wisely
- Continuing to improve the type system so that more of the dynamic features we
  love in Python can be understood programmatically

# Additional Notes

## Why this talk matters now

This talk covers recent rapid shifts in the tooling and library ecosystem that
are actively underway

- New type checkers like Pyrefly, ty, and zuban
- A steady increase in type availability in key packages like NumPy and
  SQLAlchemy
- AI development shows signs of rapidly accelerating the changes already making
  types easier to use and more valuable

I'd like to note that this github blog came out _as I was writing_ this
proposal:

- https://github.blog/news-insights/octoverse/the-new-identity-of-a-developer-what-changes-and-what-doesnt-in-the-ai-era/
  - Search for "Octoverse" in the "Ecosystem Signals" (sorry I can't figure out
    how to link a section header)
- They note that TypeScript development is up sharply, overtaking Python and
  JavaScript in 2025
- They explicitly hypothesize that the role of types in handling AI may be a
  driving factor

## Differentiation from existing talks

Most typing talks focus on how to use type hints or on how type hints can help
catch bugs. This talk focuses on broad ecosystem changes happening that are
changing the tradeoffs around using type hints in ways developers may not be
tracking.

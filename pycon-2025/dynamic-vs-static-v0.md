# Draft Proposal for a Talk on Dynamic Typing vs Static Typing in Python

### Title
**Two Pythons: When Static Typing Doesn't Fit (And How to Bridge the Gap)**

### Duration
30 minutes

### Level
Intermediate

### Category
Core Python / Language Design

### Abstract

Python's power comes from its dynamic nature—duck typing, runtime attribute manipulation, heterogeneous collections, and metaprogramming patterns that make code concise and flexible. But when you add type hints, you're essentially writing in a different language with different constraints and capabilities.

This talk explores the fundamental tension between dynamic and statically-typed Python. We'll examine common dynamic patterns that type checkers struggle with or reject entirely: DataFrames with column-dependent types, duck typing without explicit protocols, heterogeneous containers, and dynamic class construction. You'll learn when these patterns are worth preserving, how to type them when possible, and strategies for creating clean boundaries between typed and untyped code.

We'll also trace the evolution of Python's type system—from PEP 544 (Protocols) enabling duck typing support to PEP 646 (Variadic Generics) tackling heterogeneous sequences—showing how formerly impossible-to-type patterns became possible. Finally, we'll explore potential future directions and how the typing community approaches these challenges.

### Audience

This talk is for Python developers who:
- Have tried adding types to existing dynamic code and hit walls
- Want to understand *why* some Python patterns are hard to type
- Work with libraries that rely heavily on dynamic features (ORMs, DataFrame libraries, decorator-heavy frameworks)
- Are curious about the tradeoffs between dynamic flexibility and static safety
- Want to make informed decisions about when to use types and when to stay dynamic

Basic familiarity with type hints is helpful (`def foo(x: int) -> str:`), but you don't need to be a typing expert. We'll focus on conceptual understanding rather than advanced syntax.

### Detailed Outline

**Introduction: One Language, Two Paradigms** (3 minutes)
- Python is dynamically typed by design—this is a feature, not a limitation
- Type hints create a "second language" with different semantics
- Quick example: duck typing that works at runtime but fails type checking
- This talk: understand the gap, learn when to bridge it and when not to

**Theme 1: Duck Typing and the Protocol Gap** (5 minutes)

*The Classic Pattern* (2 min)
- Historical duck typing: "If it walks like a duck..." (Real Python example)
- Power: extend behaviors without inheritance, create flexible interfaces
- Example: file-like objects, context managers, iterables
- Why this was considered a core Python strength

*The Static Typing Challenge* (3 min)
- Type checkers originally couldn't handle duck typing at all
- PEP 544 (2017) introduced Protocols for structural typing
- But: Protocols require explicit definition, can't be applied retroactively
- Example: testing code that needs a "file-like" object without importing the real class
- Protocol checking is expensive, error messages are poor
- Remaining gap: can't declare duck-type compatibility for existing classes

**Theme 2: Heterogeneous Collections** (5 minutes)

*The Dynamic Python Way* (2 min)
- Lists/tuples/dicts mixing types: `["Alice", 42, 3.14, None, {...}]`
- Common in data processing, serialization, configuration
- Example: minikanren (logic programming) relies heavily on this
- Clean, natural Python—but how do you type it?

*Typing Solutions and Their Costs* (3 min)
- `tuple[str, int, float, None, dict[str, str]]` - precise but inflexible
- `list[object]` or `list[Any]` - loses all safety
- TypedDict for structured dicts, but doesn't help with positional data
- PEP 646 (TypeVarTuple): enables variadic generics, helps some cases
- The tradeoff: precision vs ergonomics
- Sometimes better to restructure (use proper classes) or stay untyped

**Theme 3: DataFrames and Control-Flow Dependent Types** (6 minutes)

*The DataFrame Problem* (3 min)
- Most-used data structure in Python, extremely hard to type
- Column types and names determined at runtime, vary by control flow
- Historical state: basic stubs, but dtype/column info was lost
- PyCon 2025 talk on static-frame: now technically possible with TypeVarTuple/Unpack
- But: types are verbose, can't access columns by name (yet)
- Example comparison: pandas vs static-frame typing ergonomics

*The Deeper Issue: Dependent Types* (3 min)
- Real problem: types depend on runtime values
- Theoretical solution: dependent types (Agda, Idris) let types reference values
- Unlikely to come to Python—too big a complexity jump
- Practical implications: some patterns will always be hard to type
- Narrowing limitations: isinstance checks with and/or, coupled conditions
- Workarounds: TypeGuard/TypeIs, but require extra boilerplate

**Theme 4: Dynamic Attributes and Metaclass Magic** (5 minutes)

*Dynamic Attribute Patterns* (3 min)
- Lazy initialization: `self.x = None` → `self.x = 42`
- Setup methods: attributes created outside `__init__`
- Monkey patching: attributes added from outside the class
- Example progression showing what type checkers can/can't handle
- Modern type checkers handle lazy init better, but setup/monkey-patching remain hard

*Metaclass Challenges* (2 min)
- Django/SQLAlchemy ORM pattern: class attributes become instance attributes
- Dynamic class creation with `type()`
- Type checkers work with static definitions, but here structure is runtime data
- Migration strategies: type stubs, modern typed ORMs (SQLModel), or accept untyped sections
- Sometimes worth avoiding if typing is a priority

**Bridging the Gap: Strategies for Mixed Codebases** (4 minutes)

*Typing at Boundaries* (2 min)
- Dropbox's experience with 4M lines: focus on module boundaries
- Keep dynamic internals, typed interfaces
- Pattern: untyped implementation wrapped in typed API
- Gradual typing: start where value is highest

*Runtime Validation as a Bridge* (2 min)
- beartype/typeguard: guard typed code from dynamic callers
- Pydantic: validate at deserialization boundaries (JSON, config, APIs)
- Pattern: validate untrusted data entering typed sections
- Complementary to static typing, not a replacement

**The Evolution of the Type System** (4 minutes)

*Gaps That Were Closed* (2 min)
- PEP 544 (Protocols): enabled structural typing
- PEP 612 (ParamSpec): dramatically improved decorator typing
- PEP 647/724 (TypeGuard/TypeIs): better custom narrowing
- PEP 673 (Self): recursive type annotations
- Shows the type system *can* evolve to handle dynamic patterns

*Current Gaps and Future Possibilities* (2 min)
- Better narrowing across multiple variables
- More expressive ParamSpec (add/remove specific kwargs)
- DataFrame typing improvements:
  - Index types by TypedDict for column access?
  - Abstract operations relating columns to types?
- Explicit duck-type declarations for testing?
- The typing community is active and open to proposals

**Conclusion: Choosing Your Python** (3 minutes)
- Static and dynamic Python can coexist—use each where appropriate
- When dynamic is worth preserving:
  - Metaprogramming that would be too constrained by types
  - DataFrames and complex runtime-dependent structures
  - Internal code with excellent test coverage
- When to invest in typing:
  - Public APIs and library boundaries
  - Configuration and data validation
  - Code using type-first libraries
  - (Brief reference: for more on why typing is increasingly valuable, see companion talk "Python Type Hints in 2025: The Case for a Second Look")
- The key: informed decisions based on your constraints, not dogma
- Get involved: typing community welcomes diverse perspectives

### Why This Talk Matters Now

The Python typing community has made tremendous progress, but there's still tension:

1. **Survey data shows divide**: 91% of typing-aware developers use types, but many developers avoid typing entirely
2. **Library migration challenges**: NumPy (33%→88% in 2025), pandas, Django still working on typing
3. **Framework conflicts**: Some popular libraries (ORMs, test frameworks) rely on patterns that resist typing
4. **Design philosophy**: Not everyone agrees Python should become more static-typed

This talk doesn't advocate for one side—it helps developers navigate the real tradeoffs and make informed choices for their specific contexts.

### What Attendees Will Learn

1. **Why** certain Python patterns are fundamentally hard to type (not just "type checker limitations")
2. **Concrete examples** of dynamic patterns: duck typing, heterogeneous collections, DataFrames, metaclasses
3. **Historical evolution** of typing features that closed former gaps (Protocols, ParamSpec, TypeVarTuple)
4. **Practical strategies** for mixed typed/untyped codebases (boundaries, runtime validation)
5. **When to preserve dynamic code** vs when to refactor for typing
6. **Future possibilities** for improving type system expressiveness

### Additional Notes

**Research foundation:**
- Real Python's duck typing guide and typing guides
- PEP deep dives: 544 (Protocols), 612 (ParamSpec), 646 (TypeVarTuple), 692 (TypedDict kwargs)
- Dropbox's 4M line typing journey case study
- PyCon 2025 talk on DataFrame typing with static-frame
- Active discussions from discuss.python.org typing forum
- Type checker issue trackers (mypy, pyright, pyrefly) for current limitations

**Talk style:**
- Balanced: celebrates both dynamic and static Python
- Pragmatic: focus on real-world decisions, not theory
- Code-heavy: concrete examples throughout
- Forward-looking: evolution shows progress is possible

**Differentiation:**
Most typing talks are either "how to use types" (syntax focus) or "why types are good" (advocacy). This talk is "when types don't fit" and "what to do about it"—filling a gap for developers facing real migration challenges.

**Connection to companion talk:**
This talk establishes *when* typing is hard or inappropriate. The companion talk ("Python Type Hints in 2025: The Case for a Second Look") focuses on *why* typing might be worth more investment than before in cases where it does fit. Each talk stands alone, but together they provide a complete picture of the Python typing landscape in 2025.

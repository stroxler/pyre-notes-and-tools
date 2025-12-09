# PyCon Proposal

## Introduction

I'd like to create a proposal for a talk about how dynamically typed Python and statically
typed Python are languages with different semantics, and it is not always feasible to simply
add types to dynamic code.

Examples of this include
- cases where the types are really control-flow dependent in ways the type
  system can't cope with well (for example, Pandas dataframes are this way, typically
  the different colums have specific types but it's not practical to write them down
  and trying to write statically typed code is too difficult)
- the pervasive use of duck-typing in pre-static-typing Python code to have a class
  that doesn't inherit mimic the behavior of some other class; this does not work without
  introducing protocols in statically-typed Python, and in many cases if the
  code you're using is third-party you cannot even change that code to use protocols
- static typing tends to be pretty impractical for dealing with heterogeneous collections.
  A fun example of code that relies heavily on this is minikanren, the small logic
  programming engine inspired by lisp.
- code at system boundaries - for example pulling in raw json data as lists / dicts of
  primitives. Often it's better to use untyped Python collections and/or convert them to
  well-typed code at some later point in the program. For this particular use case,
  libraries to validate types at runtime like Pydantic can be very helpful; often Pydantic
  in particular can push the types all the way out to data injestion (e.g. with FastAPI)
  although that may be hard to do in existing codebases.


The talk should focus on not only interesting examples, but on:
- Understanding when a design change or using different libraries can help with
  migrating existing dynamic code to types. Pydantic is a particularly important library
  in this context; in some contexts heavy use of TypedDict can also help.
- Exploring the tradeoffs of adopting vs not adopting types in different settings, as
  well as ways to get the most out of types in mostly untyped code.
- Understanding aspects of the type system that might be contributing to this.
  - In the past, there have been many type system gaps that led to dynamic code that we
    were later able to close with new features, for example
    - decorator libraries were improved greatly by PEP 612 ParamSpec and Concatenate
    - many user-defined functions for narrowing types were supported when we added
      TypeGuard and TypeIs to the type system
    - the TypedDict specification has evolved over the years - for example adding
      Required / NotRequired - to support more use cases
  - Existing gaps that I know of often come from:
    - The reliance on nominal types rather than structural types, which diverges from
      dynamic Python's widespread use of duck typing. This probably cannot be changed,
      but is worth pointing out.
    - Use cases where dependent types (which we probably will not add to Python, but
      there are languages like Agda and Idris that use them) would be needed to reasonably
      express control-flow-dependent types
    - A special case of flow-dependent types: situations where narrows on multiple variables
      are tightly coupled, or the narrowing conditions are resused in other ways that type
      checkers may not understand. For example this Pyrefly issue is relevant:
      - https://github.com/facebook/pyrefly/issues/997

## A few examples in code

Here is a starter set of examples that one of my teammates put together which
might be helpful...

Theme 1: dynamic attribute manipulation
Example: getattr / setattr

Example: dynamic attribute creation outside class (“monkey-patching”)
```python
class Foo:
    def bar(self) -> int:
	return self.bar  # <- Should this be a type error?

...

f = Foo()
if some_condition:
    f.bar = 42
```

Example: dynamic attribute creation within class
```python
class C:
    def __init__(self, x: int) -> None:
        self.x = x

    def do_something(self, y: str) -> None:
        self.y = y

...

c = C(42)
do_something_else(c)
print(c.y)  # <- Should this be a type error?
```

Example: dynamic attribute creation outside of __init__ (often in a func called setup(), or __enter__()
```python
class C:
    def __init__(self) -> None:
        setup()

    def setup(self) -> None:
        self.x = 42

    def use_x(self) -> None:
        print(self.x)  # <- Should this be a type error?

    def use_y(self) -> None:
        print(self.y)  # <- Should this be a type error?

...

class D(C):
    def setup(self) -> None:
        self.y = "abc"
```

Example: lazy attr initialization

```python
class C:
    def __init__(self) -> None:
        self.x = None

    def setup(self) -> None:
        self.x = 42

def test(c: C) -> int:
    return c.x  # <- Should this be a type error?
```

Theme 2: Container dynamism
Example: heterogeneous container usage

```python
row = ["Alice", 42, 3.14, None, {"city": "Menlo Park"}]
process_name(row[0])  # <- Should this be a type error?
process_city(row[4])  # <- Should this be a type error?
```

Example: list/dict argument splats

```python
def f(x: int, y: str) -> None: ...
def get_args_for_f() -> list: ...
y = get_args_for_f()
f(*y)  # <- Should this be a type error?

def g(*, x: int, y: int) -> None: ...
def wraps_g(args: dict[str, int]) -> None:
    g(**args)  # <- Should this be a type error?
```

Theme 3: Import dynamism
```python
import a
import b

print(a.c.x)  # <- Should this be a type error?


import a.b as c
import a

print(a.b)  # <- Should this be a type error?
```

Theme 4: Dynamic or customized class creation

Example: dynamic classes
```python
def create_record_class(name: str, fields: List[str]) -> Type:
    def __init__(self, **kwargs):
        for field in fields:
            setattr(self, field, kwargs.get(field))
    NewClass = type(name, (object,), {
        '__init__': __init__,
        'fields': tuple(fields)
    })
    return NewClass

MyRecord = create_record_class("MyRecord", read_names_from_disk())
def test(record: MyRecord) -> None:
    print(record.age)  # <-Should this be a type error?
```

Example: Custom metaclass
```python
class ModelBase(type):
    def __new__(mcs, name, bases, attrs):
        ... # metaclass magic

class User(metaclass=ModelBase):
    # These are NOT attributes on the instance yet; they are markers.
    name = CharField(max_length=100)
    age = IntegerField()

user_instance = User(name="Alice")

# The 'name' attribute we access here is a dynamic property created 
# by the metaclass, not the CharField object.
print(user_instance.name)
```

### Theme N: Uncategorized

Example:
```python
def clean_strings(collection):
    # Create a new container of the SAME type as the input
    container_type = type(collection)
    cleaned_data = (s.strip() for s in collection)
    return container_type(cleaned_data)

users_list = [" alice ", "bob"]
users_set = {" alice ", "bob"}

clean_list = clean_strings(users_list) # Returns ['alice', 'bob'] (List)
clean_set = clean_strings(users_set)   # Returns {'alice', 'bob'} (Set)
```



## Research Stage Description

I'd like to do some research to understand more about this topic.

What prior work is available that I should look at?
  - What blogs have already been written that are relevant to the limitations of
    typed python or patterns in dynamically typed code that are difficult to migrate?
  - Could we compile a list of past typing features that fixed gaps in our ability
    to model dynamic code? What currently open PEPs are out right now?
  - Are there interesting issues tracked on major github repositories? For example:
    - facebook/pyrefly
    - astral/ruff (the ty type checker)
    - python/mypy
    - python/typeshed
    - microsoft/pyright
  - What are the most interesting dicussions in the typing channel of
    discuss.python.org at https://discuss.python.org/c/typing/32
  - What libraries are interesting for people trying to use some types in codebases
    that have a lot of dynamic logic? Offhand, I know of:
    - serialization libraries like Pydantic that can enforce assumptions at
      deserialization time
    - runtime type checkers like beartype and typeguard that can help with making
      a clear boundary between dynamic code and statically typed code (in particular
      it can "guard" statically typed code that's being called from dynamic code)



## Research Stage Results

### Key Blog Posts & Articles

1. **[A Strategic Guide to Gradual Typing in Python](https://medium.com/@tihomir.manushev/a-strategic-guide-to-gradual-typing-in-python-49ac85f6dbdd)** (Dec 2025)
   - Comprehensive guide on adopting typing incrementally in existing codebases
   - Discusses practical strategies for migration and when to use typing vs when to stay dynamic

2. **[7 Gradual Typing Wins in Python](https://medium.com/@sparknp1/7-gradual-typing-wins-in-python-494fe14be587)** (Oct 2025)
   - Practical, low-friction typing improvements that provide value without full migration
   - Highlights specific patterns where typing provides the most benefit

3. **[From Scripts to Scale | A Software Engineer's Deep Dive into Python, mypy, and the Rise of Static Typing](https://www.simplethread.com/from-scripts-to-scale/)**
   - Explores the evolution from untyped Python scripts to large-scale typed codebases
   - Discusses real-world challenges and solutions in typing adoption

4. **[Beyond Inheritance: Mastering Static Duck Typing with Python Protocols](https://medium.com/@tihomir.manushev/beyond-inheritance-mastering-static-duck-typing-with-python-protocols-4fa574ea2f66)** (Dec 2025)
   - Deep dive into how Protocols enable structural typing in static Python
   - Shows the gap between nominal typing defaults and Python's duck typing traditions

5. **[Our journey to type checking 4 million lines of Python](https://dropbox.tech/application/our-journey-to-type-checking-4-million-lines-of-python)** (Dropbox)
   - Seminal case study on large-scale typing migration
   - Documents real challenges faced when adding types to existing dynamic code

6. **[Duck Typing in Python: Writing Flexible and Decoupled Code](https://realpython.com/duck-typing-python/)** (Real Python)
   - Explains traditional duck typing patterns in dynamic Python
   - Useful for understanding what gets lost in the transition to static typing

7. **[Python Type Checking (Guide)](https://realpython.com/python-type-checking/)** (Real Python)
   - Comprehensive guide including debugging techniques like `reveal_type` and `assert_type`
   - Covers common limitations and workarounds

8. **[Python 3.12 Preview: Static Typing Improvements](https://realpython.com/python312-typing/)** (Real Python)
   - Overview of recent typing system improvements
   - Shows evolution of the type system to handle previously problematic patterns

9. **[Monkey Patching in Python: A Double-Edged Sword](https://medium.com/@akhilvp/monkey-patching-in-python-a-double-edged-sword-83e35402c4bd)**
   - Explains monkey patching patterns that are nearly impossible to type check
   - Relevant to your examples of dynamic attribute manipulation

10. **[Python type hints: how to use @overload](https://adamj.eu/tech/2021/05/29/python-type-hints-how-to-use-overload/)** (Adam Johnson)
    - Explains function overloading as a solution to some typing challenges
    - Relevant for cases where different argument combinations have different return types

### Important PEPs (Type System Evolution)

11. **[PEP 544 – Protocols: Structural subtyping (static duck typing)](https://peps.python.org/pep-0544/)**
    - Introduced Protocols to enable structural typing
    - Addresses the nominal vs duck typing gap

12. **[PEP 612 – Parameter Specification Variables](https://peps.python.org/pep-0612/)**
    - Introduced ParamSpec and Concatenate for better decorator typing
    - Solved a major gap in typing higher-order functions

13. **[PEP 647 – User-Defined Type Guards](https://peps.python.org/pep-0647/)**
    - Enabled user-defined narrowing functions via TypeGuard
    - Addresses custom type narrowing patterns

14. **[PEP 724 – Stricter Type Guards](https://peps.python.org/pep-0724/)**
    - Introduced TypeIs for more precise narrowing than TypeGuard
    - Fixes narrowing limitations in negative branches

15. **[PEP 673 – Self Type](https://peps.python.org/pep-0673/)**
    - Added Self type for better typing of methods that return instances
    - Solved recursive type annotation problems

16. **[PEP 646 – Variadic Generics](https://peps.python.org/pep-0646/)**
    - Introduced TypeVarTuple for heterogeneous sequences
    - Relevant to your heterogeneous container examples

17. **[PEP 692 – Using TypedDict for more precise **kwargs typing](https://peps.python.org/pep-0692/)**
    - Improved typing of keyword arguments using TypedDict with Unpack
    - Addresses the dict splat examples in your notes

18. **[PEP 696 – Type Defaults for Type Parameters](https://peps.python.org/pep-0696/)**
    - Added default values for type parameters
    - Reduces verbosity in generic code

### Discuss.Python.org Threads

19. **[Improve support for infinite and recursive types](https://discuss.python.org/t/improve-support-for-infinite-and-recursive-types/105231)**
    - Discusses fundamental limitations with recursive type structures
    - Relevant to dependent types discussion

20. **[Allow adding specific, named keyword arguments to ParamSpec](https://discuss.python.org/t/allow-adding-specific-named-keyword-arguments-to-paramspec-possibly-in-scope-of-comprehensive-improvements-to-paramspec-expressiveness/105202)**
    - Highlights remaining gaps in ParamSpec expressiveness
    - Shows ongoing evolution needs

21. **[PEP 747: TypeExpr: Type Hint for a Type Expression](https://discuss.python.org/t/pep-747-typeexpr-type-hint-for-a-type-expression/55984)**
    - Addresses gap in typing higher-order type operations
    - Relevant to dynamic class creation examples

22. **[A more useful and less divisive future for typing?](https://discuss.python.org/t/a-more-useful-and-less-divisive-future-for-typing/34225)**
    - Philosophical discussion about typing's direction
    - Discusses tension between static and dynamic Python communities

23. **[Typing Stability & Evolution](https://discuss.python.org/t/typing-stability-evolution/34424)**
    - Discusses balance between innovation and stability in type system
    - Relevant to understanding why some features take time to add

### GitHub Issues (Type Checker Limitations)

24. **[Mypy #20363: Type narrowing with isinstance does not work with `and` and `or`](https://github.com/python/mypy/issues/20363)**
    - Shows limitations in combining narrowing conditions
    - Relevant to your Pyrefly issue #997 mention

25. **[Mypy #20359: TypeIs narrowing of union type in a generic is not working](https://github.com/python/mypy/issues/20359)**
    - Demonstrates challenges with narrowing in generic contexts
    - Shows current type system limitations

26. **[Pyrefly #1783: False positive invalid-argument in isinstance of runtime protocol using Self](https://github.com/facebook/pyrefly/issues/1783)**
    - Protocol checking challenges with Self types
    - Example of dependent type scenarios

27. **[Pyrefly #1784: str is assignable to Sequence and Container but not to Collection](https://github.com/facebook/pyrefly/issues/1784)**
    - Protocol subtyping inconsistencies
    - Shows structural typing edge cases

### Libraries & Tools

28. **[Pydantic](https://docs.pydantic.dev/latest/concepts/serialization/)**
    - Runtime validation library that bridges dynamic/static typing
    - Essential for data boundaries (your JSON example)

29. **[beartype](https://pypi.org/project/beartype/)**
    - O(1) runtime type checking in pure Python
    - Enables guarding static code from dynamic callers

30. **[typeguard](https://pypi.org/project/pytest-mypy-testing/)**
    - Runtime type checking decorator library
    - Alternative to beartype with different performance characteristics

31. **[attrs](https://www.revsys.com/tidbits/dataclasses-and-attrs-when-and-why/)** and dataclasses
    - Class definition libraries that work well with typing
    - Relevant to the metaclass/dynamic class creation discussion

32. **[msgspec](https://www.libhunt.com/l/python/topic/serialization)**, marshmallow, cattrs
    - Serialization libraries with varying typing support
    - Useful for boundary typing strategies

### Additional Resources

33. **[Python typing specification](https://typing.python.org/en/latest/spec/)**
    - Official typing specification
    - Reference for understanding type system semantics

34. **[Overloads — typing documentation](https://typing.python.org/en/latest/spec/overload.html)**
    - Detailed spec on function overloading
    - Relevant to typing functions with complex signatures

35. **[PyCon 2025: Elastic Generics: Flexible Static Typing with TypeVarTuple and Unpack](https://us.pycon.org/2025/schedule/presentation/83/)**
    - Upcoming PyCon talk on variadic generics
    - Directly relevant to heterogeneous container typing


## Subtopics


# Introduction

Now that we've had a look at research, let's think about a list of potential topics for the talk.

# Starter topics (Steven)

- Duck typing in Python:
  - What it is, how it was historically used.
    - Historically this was considered a core part of Python and treated as a
      good thing, the [RealPython article](https://realpython.com/duck-typing-python/) is a
      great example of how Pythonistas classically approached it.
    - It has a lot of advantages, it gave Python similar abilities to what traits in Rust and
      type classes in Haskell give - a way of extending library behaviors over new types; in
      fact it was even more powerful in some ways since libraries didn't even have to expose
      the interface (which could be useful but also creates maintainability problems).
    - Statically typed Python originally didn't support this; with PEP 544 we have Protocols,
      but unlike duck typing, it requires libraries to be aware that downstream code will want
      to extend behavior. Protocol checks are also typically pretty expensive and error messages
      are poor.
    - Possible extensions of the type system: we could use decorators to make
      Protocol implementations explicit and also bypass mismatch errors (which is
      not type safe but can be useful). We could potentially even allow declaring
      a duck-typing subtype relationship for classes that are not Protocols. Maybe
      I could come up with an example where this would help with unit testing?

- Dataframes
  - Historically it was impossible to type the DataFrame API very explicitly;
    we can and do have types that help document the basic functions, but the
    dtypes get lost and the column names aren't understood.
  - With TypeVarTuple and Unpack, it's now possible to type deataframes (see
    last year's PyCon talk
    [abstract](https://us.pycon.org/2025/schedule/presentation/83/); the video
    is on Youtube) and the (static-frame library)[https://github.com/static-frame/static-frame]
  - But in practice I think this is likely still impractical:
    - The types are pretty verbose
    - You still cannot currently access columns by name
  - I think this is a great example of the power of dynamic typing; this is one of the
    most used types in Python, and it's really hard to statically type.
  - Possible extensions of the type system:
    - I think in principle, if the columns index were literals and a type checker
      understood indexing then the static frame library could be made to understand
      access by name.
    - Alternatively, if we could index types using a typed dict and express access
      operations abstractly it might be possible to treat the columns as keys of a
      Typed Dict

# Additional possible topics (Claude)

- **Control-flow dependent types and the limits of narrowing:**
  - Dynamic Python allows types to change based on runtime conditions that type checkers can't always track
  - Your Pyrefly #997 issue: when narrowing conditions on multiple variables are coupled, or when narrowing logic is reused in ways type checkers don't understand
  - Example: `isinstance` checks combined with `and`/`or` that confuse narrowing (from Mypy #20363)
  - The theoretical limit: dependent types (as in Agda/Idris) would solve this, but are unlikely to come to Python
  - Practical workarounds: TypeGuard/TypeIs functions can help, but require extra boilerplate
  - Migration strategy: Sometimes it's better to keep these sections untyped or use cast() at boundaries

- **Heterogeneous collections and the typing tax:**
  - Dynamic Python freely mixes types in lists/tuples/dicts, but static typing makes this painful
  - Your example: `row = ["Alice", 42, 3.14, None, {"city": "Menlo Park"}]` - how do you type this?
  - Solutions and their tradeoffs:
    - `tuple[str, int, float, None, dict[str, str]]` - precise but inflexible and verbose
    - `list[object]` or `list[Any]` - loses all type safety
    - TypedDict for dict structures, but can't help with positional heterogeneous data
    - TypeVarTuple (PEP 646) helps for some cases but has limitations
  - Real-world impact: Libraries like minikanren that rely heavily on heterogeneous collections become very difficult to type
  - Design consideration: Sometimes worth restructuring to use homogeneous collections or proper classes

- **Dynamic attribute manipulation - the monkey patching problem:**
  - Your code examples show this well: `setattr`, `getattr`, and attributes created outside `__init__`
  - Three patterns with different typing implications:
    1. Lazy initialization (`self.x = None` then `self.x = 42`) - Type checkers now handle this better with Optional narrowing
    2. Attributes added outside `__init__` (in `setup()` or `__enter__()`) - Type checkers generally can't track this
    3. Monkey patching from outside the class - fundamentally incompatible with static typing
  - PEP 544 Protocols help a bit but only if you control the library code
  - Migration strategy: Use dataclasses/attrs, make attributes explicit, or keep dynamic sections untyped
  - Runtime checking: beartype/typeguard can help protect boundaries between typed and untyped code

- **System boundaries and untyped data:**
  - At boundaries (JSON APIs, config files, databases), you get raw dicts/lists/primitives
  - Typing these as `dict[str, Any]` loses safety; converting immediately to typed structures is verbose
  - Pydantic's game-changing contribution:
    - Runtime validation + type coercion at deserialization time
    - Pushes types to the boundary (FastAPI is a great example)
    - But: requires buy-in, may be hard to retrofit to existing codebases
  - Alternative: TypedDict for read-only boundary data, but no runtime validation
  - Design choice: Where do you convert from untyped to typed? Earlier is safer but more work
  - Sometimes better to delay typing until data is validated/normalized

- **Dynamic class creation and metaclass magic:**
  - Your examples: `type()` for dynamic classes, metaclasses (Django ORM style)
  - These patterns are nearly impossible to type check accurately
  - The fundamental issue: type checkers work with static class definitions, but here the class structure is runtime data
  - ORM implications: Django/SQLAlchemy models where class attributes become instance attributes
  - PEP 747 (TypeExpr) might help with higher-order type operations, but won't solve the general problem
  - Migration strategies:
    - Use typed ORM alternatives (Pydantic models, modern SQLAlchemy 2.0)
    - Add type stubs for generated code
    - Accept that these sections remain untyped
  - When to avoid: If typing is a priority, avoid dynamic class creation patterns

- **The decorator typing evolution:**
  - Decorators were a major pain point before PEP 612
  - Example: How do you type a decorator that preserves the signature of the wrapped function?
  - Pre-PEP 612: Essentially impossible, or required tons of overloads
  - PEP 612 ParamSpec + Concatenate: Game changer for decorator typing
  - Remaining gaps: Adding/removing specific kwargs (see discuss.python.org thread)
  - Shows the type system CAN evolve to handle dynamic patterns, but it takes time
  - Lesson: Some patterns that seem impossible to type now may become possible later

- **Argument unpacking and the splat operators:**
  - Your examples: `f(*args)` and `g(**kwargs)` with dynamic lists/dicts
  - Type checkers struggle with these because the signature is determined at runtime
  - Solutions:
    - `*args: int` works for homogeneous cases
    - PEP 692 (TypedDict with Unpack) helps with `**kwargs`
    - But `get_args_for_f() -> list` returning `[42, "hello"]` to splat into `f(x: int, y: str)` is still hard
  - Tuple unpacking is better: `tuple[int, str]` can be splatted, but must be exact length
  - Migration: Convert to explicit arguments, use TypedDict for kwargs, or accept reduced type safety

- **Import and module-level dynamism:**
  - Your examples show dynamic attribute access across imports
  - `import a.b as c; print(a.b)` - should this work? Type checkers vary
  - Runtime import hooks and `__getattr__` at module level
  - Type stubs can help but require maintenance
  - Migration: Make imports explicit, avoid dynamic module manipulation

- **When NOT to add types - the pragmatic view:**
  - Not all code benefits equally from typing
  - Scripts and prototypes: typing overhead may not be worth it
  - Code that's fundamentally dynamic: better to keep untyped than fight the type system
  - Boundary between typed/untyped: runtime checking (beartype/typeguard/Pydantic) can protect typed code
  - Gradual typing wins: Start with function signatures in core logic, leave the edges untyped
  - The Dropbox case study shows you don't need 100% coverage to get value

- **The type system gap analysis - what could help?:**
  - Patterns that WERE gaps but are now solved:
    - Decorators (ParamSpec), type guards (TypeGuard/TypeIs), Self types, variadic generics
  - Current gaps that might be solvable:
    - More expressive ParamSpec (adding/removing specific kwargs)
    - Better narrowing across multiple variables
    - Intersection types (Python only has Union, not intersection)
  - Fundamental limitations (unlikely to change):
    - Nominal by default (vs structural) - though Protocols help
    - No dependent types (types that depend on values)
    - No full theorem proving for control flow
  - This shows typing is evolving but will always have limits

- **Typing as a design constraint - embracing the restriction:**
  - Statically typed Python isn't just "Python + types", it's a different design aesthetic
  - Sometimes the "restrictive" nature leads to better design:
    - Explicit is better than implicit (The Zen of Python)
    - Dataclasses/attrs encourage thinking about data structure upfront
    - Pydantic encourages validation at boundaries
  - But: Don't force typing where it doesn't fit
  - The key insight: Dynamic and static Python can coexist, use each where appropriate


## Ergonomics of Python typing

### Steven's prompt

I was inspired by the subsection above proposing that for "Scripts and prototypes: typing overhead may not be worth it"
to explore another pair of topics:

(1) What are the benefits of typing for short-term developer ergonomics?
  - A lot of talks and research focus on huge codebases, maintainability, and
    large-scale refactors. But a lot of those talks (especially from Dropbox and Meta)
    come from an age of relatively slow, batch-oriented type checkers like mypy and
    Pyre
  - With Pyright and also the new generation of type checkers like Pyrefly, ty, and zuban
    the type checker is now tightly integrated with IDE tooling (and even prior to that,
    some IDE engines like Pycharm would use annotations)
  - As a result, you can now get a lot of language server capabilities powered by types
    - e.g. completion, signature help, go-to-definition, automated refactoring of methods and attributes
    - I'm especially interested in completion and signature help, because I remember as a Python
      dev before types doing some java; I mostly didn't like it, but I remember that "completion-based
      exploration" of library APIs felt like the one superpower of Java. Now we can have this in Python!
  - It might be the case that for a tiny project or script, the tradeoffs around typing depend
    on what libraries you are using - if the libraries have good types, then using them in your
    project could help you work much faster.

(2) How might AI-assisted programming change the tradeoffs around typing?
  - Most obviously, writing out type annotations (particularly on parameters; some type checkers can
    infer return types but none of the common ones infer parameters) can be time-consuming, but for
    an AI typing isn't a bottleneck.
    - So AI can help add types to code as you write, lowering the cost of using types
    - It's more challenging to add types to existing code, but AI may be able to help here too,
      going much further than earlier ML-based experiments such as Meta's `TypeWriter` project
      - I believe that https://github.com/kimasplund/mcp-pyrefly was one related experiment
  - In addition, if the AI is able to *consume* the results of a very fast incremental re-check,
    then it can potentially iterate much faster without having to execute code. Is there any research
    (or if not, then just blogs) on how the presence of types affects vibe-coding efficincy?


## Investigation results

### Topic 1: Short-term Developer Ergonomics Benefits of Typing

#### The Evolution of Python Type Checkers and IDE Integration

The landscape has changed dramatically from the early days of mypy and Pyre. The key shift is from **batch-oriented type checking** (running mypy in CI or manually) to **IDE-integrated, incremental type checking** with millisecond-level feedback:

- **[Pyright](https://pydevtools.com/handbook/reference/pyright/)** is designed specifically for IDE integration, providing real-time feedback
- **Pylance** (Microsoft's VS Code extension wrapping Pyright) was specifically built for "[fast, feature-rich language support](https://devblogs.microsoft.com/python/announcing-pylance-fast-feature-rich-language-support-for-python-in-visual-studio-code/)"
- **Pyrefly** (Meta's new type checker) explicitly targets "[IDE-friendly typing for Python](https://talkpython.fm/episodes/show/523/pyrefly-fast-ide-friendly-typing-for-python)"
- The comparison between [Pyright and older tools like Jedi](https://www.libhunt.com/compare-pyright-vs-jedi-language-server) shows dramatically better autocomplete and navigation when types are present

This means typing now provides **immediate, as-you-type benefits** rather than just catching bugs in CI later.

#### IDE Superpowers Enabled by Types

When libraries have good type information, modern IDEs provide:

1. **Autocomplete/IntelliSense that enables API exploration**
   - You mentioned the "Java superpower" of completion-based exploration - Python now has this too with typed libraries
   - You can discover methods and their signatures without constantly checking documentation
   - This is especially valuable when learning new libraries or working with complex APIs

2. **Signature help**
   - As you type function calls, you get inline documentation of parameters
   - No need to jump to docs to remember parameter order or names

3. **Go-to-definition and find-all-references**
   - Type information makes navigation much more accurate
   - Refactoring becomes safer and easier

4. **Real-time error detection**
   - Catch mistakes immediately rather than at runtime
   - Reduces the "run-debug-fix" cycle

#### The "Well-Typed Libraries" Effect

A key insight: **The value of types in a small script may depend more on the libraries you're using than on the script size itself.**

- If you're using well-typed libraries (FastAPI, Pydantic, modern SQLAlchemy, httpx, etc.), adding types to your code gives you:
  - Excellent autocomplete for library APIs
  - Immediate feedback when you misuse library functions
  - Ability to explore APIs through your editor

- If you're using poorly-typed or untyped libraries, you lose most of these benefits
  - The type checker can't help you with library usage
  - Autocomplete falls back to Jedi-style runtime inspection (less reliable)
  - You still need to constantly check documentation

This suggests a **nuanced view of "scripts don't need types"**:
- A script using pandas, requests, and numpy (historically poorly typed): types might not help much
- A script using FastAPI, Pydantic, and httpx (well typed): types could make you much more productive

#### Cross-Language Comparisons

**TypeScript's adoption story** is heavily based on ergonomics, not just catching bugs:
- [Developer surveys](https://medium.com/@brianaldybramasta/why-are-so-many-developers-switching-to-typescript-heres-why-51f018c58d0b) consistently cite "better autocomplete and refactoring" as a top reason for adoption
- [TypeScript benefits](https://www.netguru.com/blog/typescript-benefits) frequently emphasize IntelliSense and developer experience
- The [Airbnb TypeScript migration](https://medium.com/airbnb-engineering/ts-migrate-a-tool-for-migrating-to-typescript-at-scale-cd23bfeb5cc) at scale was partly motivated by improved developer tooling

**Ruby's Sorbet** (Stripe's gradual type checker):
- [Stripe's case study](https://stripe.com/blog/sorbet-stripes-type-checker-for-ruby) emphasizes editor integration and autocomplete improvements
- The [gradual typing talks](https://sorbet.org/docs/talks/curry-on-2019) discuss how types enable better IDE tooling
- [Developer experience improvements](https://blog.appsignal.com/2024/09/18/rubys-hidden-gems-sorbet.html) are cited alongside bug detection

**Typed Racket** has academic research on gradual typing but less focus on IDE ergonomics (it's more research-oriented)

#### Relevant Research and Case Studies

1. **[Understanding the Language Server Protocol (LSP)](https://medium.com/@rhithick_m/understanding-the-language-server-protocol-lsp-how-it-transformed-developer-productivity-6a41d7a40cd0)**: How LSP transformed developer productivity by enabling type-aware tooling across editors

2. **[From Scripts to Scale](https://www.simplethread.com/from-scripts-to-scale/)**: Discusses how typing becomes valuable even in smaller codebases when integrated with modern tooling

3. **[Dagster's "Using Type Hinting in Python Projects"](https://dagster.io/blog/python-type-hinting)**: Real-world perspective on how types improve the development experience

4. **[Comparing Pyright vs Python-LSP-Server performance](https://blog.kodezi.com/pyright-vs-python-lsp-server-key-features-and-performance-insights/)**: Shows the dramatic performance improvements that make real-time type checking viable

5. **[Adding Type Hints to Python at Scale](https://dagster.io/blog/adding-python-types)**: Dagster's experience with types and developer productivity

#### Open Questions and Gaps

- **Limited empirical data**: Most evidence is anecdotal or from case studies, not controlled experiments
  - Hard to quantify "how much faster" development is with types
  - Self-selection bias: companies that adopt types may already have different practices

- **Library ecosystem maturity**:
  - Typeshed and type stubs have improved dramatically, but coverage is still uneven
  - Some popular libraries (pandas, numpy) are getting better but historically were hard to type
  - The experience varies wildly depending on your dependencies

- **Learning curve**:
  - There's an upfront cost to learning type syntax
  - Advanced typing (Generics, Protocols, TypeVars) can be confusing
  - Not clear when the productivity benefits outweigh this learning cost

#### Potential Talk Angles

1. **"The hidden cost of untyped libraries"**: Show side-by-side comparison of working with well-typed vs poorly-typed libraries

2. **"Completion-driven development is back"**: How Python reclaimed the "Java superpower" of API exploration through autocomplete

3. **"Type checkers evolved: From batch to real-time"**: Compare the experience of mypy in CI vs Pyright in your editor

4. **"When types help your scripts"**: Counter the "types are only for big projects" narrative by showing how library types matter

5. **"The virtuous cycle"**: Well-typed libraries make typing your code more valuable, which incentivizes better library types

### Topic 2: How AI-Assisted Programming Changes the Typing Tradeoffs

#### The Cost-Benefit Equation is Shifting

Historically, one of the main arguments against typing in Python was the **annotation burden**:
- Writing type annotations takes time and mental effort
- Type checkers can't infer parameter types (though they can often infer returns)
- Adding types to existing code requires significant manual work

AI coding assistants fundamentally change this calculus:
- **LLMs can generate type annotations at near-zero cost** as you write code
- **Automated type annotation is becoming viable** at scale using LLMs
- AI assistants can help add types to existing code much faster than humans alone

#### Research on LLM-Powered Type Annotation

1. **[Automated Type Annotation in Python Using Large Language Models](https://arxiv.org/abs/2508.00422v1)** (2025)
   - Recent research directly addressing LLM-based type annotation for Python
   - Shows promise for automating the annotation process
   - Builds on earlier work like Meta's TypeWriter but with modern LLMs

2. Meta's **TypeWriter** project (pre-LLM era)
   - Used machine learning to suggest type annotations
   - Limited compared to modern LLM capabilities
   - Modern LLMs like GPT-4/Claude are much more capable at this task

3. **[A Comparative Study of Code Generation using ChatGPT 3.5 across 10 Programming Languages](https://arxiv.org/abs/2308.04477)**
   - Shows variation in LLM performance across different languages
   - Typed languages may provide better context for code generation
   - Suggests type information helps LLMs generate more correct code

#### AI Workflow Integration with Type Checking

**The "Vibe Coding" Phenomenon and Its Risks:**
- [Vibe coding](https://www.vktr.com/ai-technology/vibe-coding-explained-use-cases-risks-and-developer-guidance/) refers to rapidly iterating with AI without careful verification
- [Security researchers warn](https://www.databricks.com/blog/passing-security-vibe-check-dangers-vibe-coding) this creates vulnerabilities
- [Studies show](https://arxiv.org/html/2512.03262) AI-generated code has significant security weaknesses
- **Type checking can be a first-line defense** against AI mistakes

**Emerging AI + Type Checker Workflows:**

1. **Real-time verification during AI generation**
   - Modern IDEs (Cursor, Windsurf, Copilot in VS Code) integrate both AI and type checkers
   - As AI generates code, type checker provides immediate feedback
   - This creates a [feedback loop](https://github.blog/ai-and-ml/github-copilot/from-idea-to-pr-a-guide-to-github-copilots-agentic-workflows/) that improves code quality
   - [AI coding workflows](https://medium.com/@muhammadwaniai/cursor-vs-windsurf-vs-cline-i-coded-for-30-days-with-each-ai-ide-eee31ffa860f) now commonly include type checking as a verification step

2. **Agentic workflows with verification**
   - [GitHub Copilot's agentic features](https://github.blog/ai-and-ml/github-copilot/from-idea-to-pr-a-guide-to-github-copilots-agentic-workflows/) can iterate on code based on type errors
   - [Test-driven development with AI agents](https://www.flowhunt.io/blog/test-driven-development-with-ai-agents/) often includes type checking
   - The AI can see type errors and fix them automatically

3. **Static analysis as guardrails**
   - [AI-assisted static analysis](https://www.parasoft.com/blog/transform-code-quality-with-ai-driven-static-analysis/) helps verify AI-generated code
   - Type checking is one of the fastest forms of static analysis
   - Provides nearly instant feedback compared to running tests

#### Do Types Help LLMs Generate Better Code?

**Limited Direct Evidence:**
- No major empirical studies specifically on "typed vs untyped context for LLM code generation"
- Anecdotal evidence suggests types help, but hard to quantify

**Theoretical Arguments:**

1. **Types as Context:**
   - Type annotations provide machine-readable specification
   - LLMs can use type signatures to understand intent
   - Similar to how humans use types to understand APIs

2. **Types Reduce Ambiguity:**
   - In dynamically typed code, functions can accept/return many different types
   - Type signatures narrow the solution space
   - May reduce [LLM hallucinations](https://www.getzep.com/ai-agents/reducing-llm-hallucinations/) by providing constraints

3. **Types Enable Better Verification:**
   - Even if types don't help generation, they help **verification**
   - Type errors catch AI mistakes faster than running code
   - Creates a tighter feedback loop for iterative AI coding

**Comparison to TypeScript:**
- TypeScript is consistently one of the [top languages in developer surveys](https://medium.com/@brianaldybramasta/why-are-so-many-developers-switching-to-typescript-heres-why-51f018c58d0b)
- Anecdotally, many developers report better AI code quality in TypeScript vs JavaScript
- But this could be correlation not causation (TypeScript codebases may be different in many ways)

#### Empirical Studies on AI Code Quality

1. **[GitHub's Research on Copilot Code Quality](https://visualstudiomagazine.com/Articles/2024/11/22/Article_0GitHub-Copilot-Research-Claims-Code-Quality-Gains-in-Addition-to-Productivity.aspx)** (2024)
   - Claims code quality improvements beyond just productivity
   - Doesn't specifically measure typed vs untyped
   - But suggests AI can produce maintainable code with right workflows

2. **[Security Weaknesses of Copilot-Generated Code](https://arxiv.org/html/2310.02059v4)**
   - Empirical study showing security issues in AI-generated code
   - Highlights need for verification mechanisms
   - Type checking could catch some classes of errors

3. **[An Empirical Evaluation of GitHub Copilot's Code Suggestions](https://ieeexplore.ieee.org/document/9796235)**
   - Studies correctness and usefulness of suggestions
   - Context quality matters for suggestion quality
   - Type information is high-quality context

#### Open Questions and Research Gaps

1. **Does type context improve LLM code generation?**
   - Need controlled studies comparing typed vs untyped contexts
   - Does providing type signatures in prompts lead to better code?
   - How much does the LLM's training data distribution matter?

2. **Optimal AI + type checker workflow?**
   - Should AI see type errors and auto-fix them?
   - Or should humans review type errors before AI iterates?
   - What's the right balance of automation vs human oversight?

3. **Cost-benefit of AI-added types?**
   - If AI adds types automatically, are they useful?
   - Do auto-generated types help humans or just placate the type checker?
   - Quality vs coverage tradeoff for automated annotations

4. **Long-term effects on codebase quality?**
   - Does AI + types lead to more maintainable code?
   - Or do developers rely too much on AI and lose understanding?
   - Impact on onboarding new developers to AI-generated typed code

#### Potential Talk Angles

1. **"Types as AI guardrails"**: How type checking protects against vibe coding risks
   - Show examples of AI mistakes caught by type checker
   - Demonstrate the feedback loop: AI generates → type checker validates → AI fixes

2. **"The annotation barrier is gone"**: AI makes the cost of typing near-zero
   - Live demo: have AI add types to untyped code
   - Compare effort before and after AI assistants

3. **"Verification velocity"**: Type checking as the fastest way to verify AI code
   - Compare: type check (milliseconds) vs tests (seconds) vs manual review (minutes)
   - Argue for "type-first verification" in AI workflows

4. **"The context paradox"**: Types help AI, but AI helps add types
   - Well-typed codebases → better AI suggestions → easier to maintain types
   - Another virtuous cycle

5. **"From TypeWriter to GPT-4"**: Evolution of automated type annotation
   - History: manual → ML (TypeWriter) → LLM (GPT-4/Claude)
   - What this means for typing adoption going forward

#### Interesting Cross-References

- **Connection to Topic 1**: AI lowers the cost of types, while IDE integration increases the benefit
  - Together they fundamentally change the typing ROI calculation
  - What was "not worth it for scripts" may now be "worth it everywhere"

- **Link to gradual typing**: AI + types enables a new gradual typing workflow
  - Start untyped, have AI add types incrementally as needed
  - Type checker guides where types would be most valuable
  - More pragmatic than "all or nothing" typing strategies
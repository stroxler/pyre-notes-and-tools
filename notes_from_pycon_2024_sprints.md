# Notes from discussion on May 20, 2024 at PyCon sprints

## MyPy Notes (Shantanu)

build.py is the entrypoint
 - handles module-level logic including figuring out SCCs
   ... note: it is eager; making it lazy would be a huge help for some codebases
 - modulefinder.py is the module tracker
   - it builds a module-level dependency graph
   - find_sources.py has some related logic, especially related to trees and
     packages including namespace packages
   - .. there does exist some finer-grained logic (options.py -> fine_grained_incremental)

fastparse produce nodes

semanal = populates extra info on nodes; sort of like UGE (esp classSummary) + a few other things like type aliases (maybe?)
          ... has some magic to defer logic
          ... has a fixpoint flavor with multiple passes

typeanal = does work similar to semanal but deals specifically with type annotation contexts
          ... has the same deferral mechanisms


checker = the core type checker at a high level
- binder is most of the control flow
  - Unlike in pyright, this is inside the checker
- checkexpr does a lot of the work
  - checkmember is a lot of the AttributeResolution layer logic, and ~half of the "net" checkexpr logic

- solve + constraints has a lot of the "interesting" stuff:
  - bidirectional inference
  - the constraint solving
... Shantanu says this is nice code, which is good news for me since this is the stuff I most
need to learn for Pyre. I should probably look at it in a great deal of detail.
  - type_state is global state, it has things like global options
  - "type context" is the thing that stores contextual info for the bidirectional solver;
    often it's an implicit idea rather than an actual code artifact; `Context` is just
    an AST node and is *not* the "type context"

- applytype and exapandtype are related to type variable handling

- testing dsl:
  - look for `.test` modules, it's an extended Python syntax which is pretty cool
  - it has fixtures, with a simple typeshed similar to Pyre.py
    - some tests do run against the full typeshed, but not most; it is slow

misc
  - PartialType is how mypy handles things like empty containers
    - note: type errors on usage don't happen on usage, they get lifted to the definition
      as needs-annotation... this is a nice behavior! More of this in Pyre might help.
  - plugins... not that interesting to me now but someday it would be good to look at
  - there's an uninitialized local, done as a separate analysis as in Pyre. Consensus
    was that it actually would be nice to do it in the type check, possibly by having
    an actual unbound type (pyanalyze does this and Jelle says it's nice)
  - `if 2 in arg_pass_nums` of `checkexpr.py` is related to lambdas somehow
  - Shantanu: the way Pyright infers function types (as generic types!) is *extremely*
    friendly for scripting use cases. My opinion: Pyre having a mode to do this would
    be extremely helpful for AI use cases that aren't super typing-forward.
  - erasetype.py: ?? Probably related to generics in some way
  - Shantanu: mypy's overload logic is complicated... `check_overload_call`
    - the ambiguous handling (under elif any_causes_overload_ambiguity) is "super sketchy"
    - Carl: intersection types might help with doing this better
  - Mypy intersection logic is maybe involving synthesizing typeinfos
    - in checker.py there's an `intersect_instances` function, logic is there
  - TypeOfAny is nice, it tracks things about the orgin of an Any type (I want to do this
    in Pyre, like if we have an Any from a not-found import don't forget the thing's name)


### Stuff Steven could work on

let's try to tackle the new dataclasses test
 - check for carljm's commits on typing for the spec + test
 - the mypy logic is in a plugin, see `dataclasses.py`
 - existing final handling is at `if sym.type is None and node.is_final and node.is_inferred:` (~652)
 - for normal attributes, you set `is_final` on `nodes.Var` to mark as final, so we'll need
   ways to special case this; search for places where we set `is_final = True` to understand where 
   this is getting set. Basically we probably want to delete the existing handling and then
   make it do something more like what the normal non-dataclasses code does.

Look at #9618 as well, this is probably a pretty straightforward change to `checker.py`
Look at `check_method_override`

In general take a few tasks marked good-second-issue.

Resources if I wanted to tackle the `__new__` bugs:
   - docs on `__new__`: https://docs.python.org/3/reference/datamodel.html#basic-customization
   - blogpost with a more consumable description: https://santoshk.dev/posts/2022/__init__-vs-__new__-and-when-to-use-them/
   - couple of examples where mypy has arguably-bad semantics
     - ex A: https://gist.github.com/mypy-play/b40fec12cb83d7683c6832320aecc4d8
     - ex B: https://gist.github.com/mypy-play/46b45241159045b55d7dfd9d871280f1
     - another bug report: https://github.com/python/mypy/issues/17251
     - a narrower bug report about enums specifically:  https://github.com/python/mypy/issues/16806
     - another bug report related to generics: https://github.com/python/mypy/issues/15935
       gist: https://gist.github.com/mypy-play/8e3a4d537d6054de128e1ff4765c7a0c
   - Shantanu described what's going on, a class is actually represented as a FunctionLike (basically
     a Callable) representing its constructor, which is a kind of strange representation and is likely
     at the heart of what's going on, because we actually extract the return value of this type to figure
     out "what is" the type, and that's not a very good choice!

The match issue might also be interesting:
 - https://github.com/python/mypy/commit/3579c6149b74bee4717fb5fcac9e4351d36fe1b5

### Particularly valuable stuff for Steven to read:

Jukka has started working on 695:

https://github.com/python/mypy/commit/5fb8d6262f2ade83234e46334eb3fb8a4bbaedc0
https://github.com/python/mypy/commit/3b97e6e60b561b18ef23bfd98a4296b23f60a10a

But also of course I could start reading *any* PR, and ideally commenting
if I see anything.


## Typeshed notes (Alex)

The most desirable place for stub packages is actually typeshed, ideally Pyre would
contribute here! I should talk with Maggie about it.

I should probably also learn some mypy-related stuff, e.g. `stubtest`.

In parallel with this we definitely want infra for pulling the stub packages down
when we import them internally, which is kind of the dual of us upstreaming patches!

To see the testing infra, look in `https://github.com/python/typeshed/tree/main/.github/workflows`

## PyAnalyze (Jelle)

Started in 2015 before any type checkers were mature; it actually started as something
closer to a linter (am I calling undefined functions? Is my arity right) and only gradually
added typing support. It still has limited typing logic; for example it can understand generics
when typing non-generic code, but it cannot handle type checking the bodies of generic
functions; this works ok for quora because very little *application* code is generic.

One of the big reasons it still exists is that Quora uses nonstandard (or no-longer standard)
things like roughly-old-style yield-based async (asynq) and some wierd class attribute magic that
pyanalyze can handle but not other type checkers.

It also has better support for dynamicism, which works better on some kinds of codebases
(note: this may be a little like the spy prototype). For a classic example, pyanalyze handles
dataclasses with almost zero special casing!

It actually operates on both the module *and* the AST (so it imports a module but also
parses it and uses both in type checking). The dynamic part is largely inspect.signature
oriented. Another interesting thing is that c libraries work somewhat out of the box.
- the ast visitor is important for lots of things, including discovering nested
  functions and nested (lazy) imports

It does handle stubs with some special casing in the module finding logic.

... it's maybe worth reading this code actually, because it relies more explicitly
on runtime behavior that a static checker ought to understand anyway.


It has two passes, most type checking is on the 2nd pass (I imagine the first pass
is probably scope building?)

The main ast walk is `name_check_visitor.py`. The trickiest bit might(?) be
`stacked_scopes.py`. It deals with nested Python scopes and probably has some
bugs, especially on class scopes.

`implementation.py` is a lot of the attributeResolution-style logic, and it
supports a plugin-like functionality that can be pulled directly out of the
user code. There's logic in Quora's internal `db.py` that does type-provider-like
logic type get database schemas.

Note that https://pyanalyze.readthedocs.io/en/latest/type_evaluation.html was
an almost-proposal at one point, we could revisit this.

## Ruff notes (Alex + Carl)

You can track the type checker development by looking for PRs tagged various
variations of "red knot" e.g. "redknot", "red-knot", "red knot", etc.

This search gets most of them I think:
https://github.com/astral-sh/ruff/pulls?page=1&q=is%3Apr+knot

## PyCharm notes ()

PyCharm's type inference pre-dates PEP 484, it is now complicated to unify with
PEP 484, but is also super useful.

Several fancy types of inference PyCharm can do.
 - it infers protocol types  on untyped functions
 - it will also attempt inference based on (same-modue) callsites; this is
   especially handy for example in 
 - it goes even further and can sometimes determine all classes that actually
   fulfill a protocol (for example if you use a couple of string methods, it's
   likely to realize pretty quickly that you have either a `str` or `bytes` object)
   - this is the same trick I described wanting to do in `pyre infer` last
     Typing Summit... use a reverse index to infer types off method/attribute names
   - PyCharm users hate the "indexing" state; the main thing PyCharm is doing
     here is building the indices used for this kind of inference
   - it currently only uses that type inference for autocomplete, not autogenerating
     annotations but this could be done.

Another thing PyCharm has is "binary skeletons", which are obtained by inspecting
the runtime; part of the reason this exists is PyCharm predates typeshed, so it
needed a way to find standard library information.
 - it doesn't get type info, but it does get signature info so it's like a
   weak stub (with some extra goodies, e.g. docstrings!)
 - these days, PyCharm will prefer stubs if you have them, but it can fall back
   to the binary skeletons. This remains super useful on less-often-used
   packages with C code since PyCharm can figure out some basic info.
   - It maybe still uses these for docstrings? Not sure.
 - In addition to the untyped binary skeletons, PyCharm will (or did in the past
   at least) also use a rulebook to extract type info from a bunch of the common
   docstring formats
   - see https://github.com/JetBrains/python-skeletons
   - (note: basic pycharm is open source, see
      https://github.com/JetBrains/intellij-community/tree/master/python)

Some of this non-standard stuff, e.g. docstring-based types, still works on
user code. You can try using `:type` and `:rtype` in docstrings to see this
in action. There was at least for a while some effort to support extended syntax
here, e.g. PEP 677 callable types.

### Implementation (Mikhail Golubev)

There are two layers to the PyCharm trees
 - AST: a normal AST
 - StubTree: a high-level AST representation that just knows about the
   interface (this is, I think, very similar to Flow's `Signature` types, and
   a bit like [parts of] Pyre's symbol table and what we want eventually)
   - indices contain only the stub trees
   - this tries to conform to an IntelliJ standard called
     "Psi = program structured interface"

As much of PyCharm as possible tries to rely only on these indices
  - as a result, all of the fancy inference is limited to same-file,
    there's rarely (never?) cross-module inference using function bodies.
  - this is good for performance, but the delta when functions get moved
    can be very confusing for users.
    - What's even more confusing is that on autocomplete PyCharm actually
      *will* go use the function body to infer.
    - Why does PyCharm do this? The general philosophy is that:
      - PyCharm won't try to infer stuff off of other module's
        function bodies for background stuff like producing diagnostics,
        this can get too expensive
      - Bug for user-triggered actions like autocomplete, it's willing
        to do more work and actually use the AST of another module
      - ... this is good for users since autocomplete is so useful, but
        it is also very confusing to users since it's one IDE getting
        different levels of type info for different editor features.

The StubTree is build using *only* local information. How does this work
when a signature depends on other modules (e.g. imported types)?  Similarly
to Flow, the StubTree represents the annotations + scope info but it is
lazy about actually resolving the meanings of annotations; you can figure
that out in the type check stage once you have the index with all
the `StubTree` instances.

PyCharm doesn't have much dependency tracking, so cache invalidations can
be pretty expensive. They are investigating coarse-grained dependency
tracking.

PyCharm also has limited constraint solving logic and sometimes has
problems with generic types; they are planning to work on this with some help
from the Kotlin team.

There's a test DSL a little like MyPy's for some of this logic, although
more elaborate given that there are IDE features; PyCharm has a headless
mode that helps with integration tests. Hopefully we'll be able to get it
running in the conformance tests soonish!
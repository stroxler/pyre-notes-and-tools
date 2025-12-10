# Front matter - dumping the most likely content from `./brainstorming.md`

## References

### High level references

- The direct references
  - Call for proposals: https://us.pycon.org/2026/speaking/talks/
  - Guidelines: https://us.pycon.org/2026/speaking/guidelines/
- Some sources of examples
  - [A repository of some PyCon US proposals](https://github.com/akaptur/pycon-proposals) including some accepted / rejected ones
  - [Another collection of proposals (see links)](https://rhodesmill.org/brandon/2013/example-pycon-proposals/)
  - [PyCon Indea 2023 proposals - this page links to all the full proposals](https://in.pycon.org/cfp/pycon-india-2023/proposals/)
- Additional information
  [How I review a PyCon talk proposal](https://doughellmann.com/posts/how-i-review-a-pycon-talk-proposal/) by Doug Hellmann, who's been on the committee

- For future reference
  [75 ideas for talks, from 2022](https://www.thursdaybram.com/pycon-2022-talk-proposals-and-75-talk-ideas-you-can-use) ... obviously
  not what I would talk about per se, but rereading these might really get me in the frame of mind to come up with ideas in future years!

### Some example proposals (useful to see format and level of detail)

- https://gist.github.com/robintw/e4a8445d0ce1538928cb4dd5233f8614
- https://rhodesmill.org/brandon/2013/example-pycon-proposals/webfaction.txt
- https://github.com/akaptur/pycon-proposals/blob/master/accepted/python-2-to-3-pycon-2018.md
- https://github.com/akaptur/pycon-proposals/blob/master/accepted/write-excellent-programming-blog-ajdavis-2016.txt
- https://github.com/akaptur/pycon-proposals/blob/master/accepted/important_decisions_kaptur_2014.md
- https://github.com/akaptur/pycon-proposals/blob/master/accepted/build-a-better-hat-rack-glasnt-2016.md
- https://in.pycon.org/cfp/pycon-india-2023/proposals/music-making-with-python-and-foxdot~dwpp8/
- https://in.pycon.org/cfp/pycon-india-2023/proposals/lpython-novel-fast-retargetable-python-compiler~bYEp2/


Actually https://in.pycon.org/cfp/pycon-india-2023/proposals/ai-engineering-in-python-system-design-101~elY5g/ is not only
interesting as an example proposal, but it's also talking about RAG.


### The references I think I'm most likely to include

Everything mentioned in ./research-round2 might be fair game, and there may be some
valuable material in ./brainstorming.md not reflected here.

Docs, papers and dicussions:
- [Duck Typing in Python: Writing Flexible and Decoupled Code](https://realpython.com/duck-typing-python/)
- [PEP 544](https://peps.python.org/pep-0544/) - support for duck typing, one of the most important type system extensions
- [Dropbox's journey to gradually adopting types](https://dropbox.tech/application/our-journey-to-type-checking-4-million-lines-of-python)
- [Typing Stability & Evolution](https://discuss.python.org/t/typing-stability-evolution/34424)
- [PyCon 2025: Elastic Generics: Flexible Static Typing with TypeVarTuple and Unpack](https://us.pycon.org/2025/schedule/presentation/83/) about static-frame
  - [The talk on youtube](https://www.youtube.com/watch?v=fmczXlnQ3cs)
  - [The static-frame library](https://github.com/static-frame/static-frame) referenced in the talk above
- [Pyright and older tools like Jedi](https://www.libhunt.com/compare-pyright-vs-jedi-language-server) 
- [AI and security vulnerabilities](https://arxiv.org/html/2310.02059v4) - cross reference this with safe typed library work from Meta.
- [Copiolot and leetcode analysis](https://ieeexplore.ieee.org/document/9796235) provides limited, indirect evidence that static types *may* be useful
- [TypeWriter](https://arxiv.org/abs/1912.03768), a pre-LLM experiment in ML for typing
- [Newer research](https://arxiv.org/abs/2508.00422) on using LLMs to do the same
- [An experiment](https://github.com/kimasplund/mcp-pyrefly) using a Pyrefly MCP to do the same
- [A talk from Jane Street](https://www.youtube.com/watch?v=0ML7ZLMdcl4) that includes type checking (OCaml) as part of reinforcement learning for a post-trained model

Libraries
- [Pydantic](https://docs.pydantic.dev/latest/concepts/serialization/)
- [beartype](https://pypi.org/project/beartype/)
- [typeguard](https://pypi.org/project/pytest-mypy-testing/)

## Initial outline for a possible (single) talk

- Python is dynamically typed
  - Not all code patterns can be understood by a type checker by just adding a few annotations
    - Dynamic class attributes (often requires annotations in the class body)
    - Basic duck typing (requires defining protocols)
    - Limitations in analysis of invariant containers (it's almost always lists that cause issues)
  - Some code patterns aren't practical to statically type
    - Dataframes are partially typed - with static-frame you can in theory type them now but the ergonomics are poor
    - Highly dynamic code, for example decorators that use introspection, some metaprogramming examples
- We should be wise about where to use types. But tradeoffs are changing
  - It's okay for some code to be dynamic
    - If what you are doing is hard to type (dataframes), types may not help much
    - Highly dynamic logic can often be untyped and well-tested, but wrapped in a typed interface
    - Having some types can help, focusing on module boundaries can help (Dropbox's experience is relevant)
    - Runtime checkers and type-aware validations at the boundary can also help
  - That said, the tradeoff is changing: the value is going up and the costs going down
    - Types power IDE functionality, so they don't just help you catch bugs but also develop (pyright vs jedi)
      - Pyright vs jedi, ideally find some research or at least link to Microsoft's rationale on pyright/pylance
      - The newer generation of type checkers are all IDE native
    - The library ecosystem is changing, often types actually make applications easier to write
      - The overall library ecosystem is increasingly typed (need to add some research to trends, past pain points)
      - Dataclass libraries make it concise to structure code around types, Pydantic adds powerful validation
      - FastAPI can automate parts of building webservers, 
    - With newer tools and AI development, the cost of types may be going down
      - Better type inference (e.g. return type inference, empty container inference) can reduce the need for annotations
      - Writing out annotations took time, but when AI is developing we don't have to type them out
      - AI may also be able to add annotations post-hoc
        - Early research like TypeWriter showed promise using ML to add types, there's active work with LLMs
        - An idea to explore: customizing agents to add types to code just written (e.g. claude commands)
  - The value of types may also increase even faster with AI
    - Some research suggests types can be a big help to the AI: faster feedback especially for hallucinations
      - Newer and faster type checkers are also relevant here - quicker cycle times
      - Open question as far as I know: MCP may also be able to give AI some ability to leverage IDE-like functionality
        - Is there any active research on this topic?
        - What about leveraging out-of-band tools like Glean as part of an MCP?
    - Security is a big concern, and types can play a role in security
      - Example: motivations behind PEP 675; any research I can find on using types for 'security-safe' libraries
      - Example: Meta relies heavily on Pysa static analysis which needs types (proveded by Pyrefly)
- Close with a few possibilities for increasing statically-typed Python support for dynamic types
  - Note the history of this
    - Duck typing wasn't supported originally, but PEP 544 added support
    - PEP 612 greatly improved support for decorators
    - Many more like this, several currently under discussion!
  - A few new ideas:
    - Decorators for adhoc duck typing, to plug gaps in protocol usability (a testing example would be neat)
    - A couple of ideas for data frames:
      - Given the existing tuple-oriented `static-frame` approach, use an abstract operation to relate columns to ops
      - Alternatively, allow indexing a type by a typed dict to get dynamic attribute / subscript resolution
        - This might be more aligned with typical "table" interfaces and less Pandas-specific
  - Call to action: the Python typing community is open and welcoming, we'd love to have you get involved!


## Initial outline for a possible pair of talks

One concern is that the talk above is a little too wide-ranging and unfocused (looking at it, just the
outline without much detail is about as long as many proposals are, which suggests that it's too much
material to do justice to in one talk given both time constraints and the need for a focused talk
to engage the audience).

With that in mind, here's an alternative pair of sketches for two related but mostly separate talks:

- One proposal would focus on why typing might be worth more investment given a
  rapidly evolving ecosystem of libraries and tools. Most of the content above actually
  fits better here:
  - Introduction to python, static vs dynamic typing
    - Dynamic python can do more things... here the entire other talk content is
      relevant, but condensed down to just a slide or two
    - Past advice has often been to type only large applications or long-lived
      applications, but that's tricky (do you know if your app will live long
      or your script will grow over time)
    - More over, the past views on tradeoffs may not reflect the current state
      of tools (types are no longer just a bug-catching tool, they aid development);
      that's what the rest of the talk will be on
  - The body of the talk, covering:
    - The non-AI material
      - Changes that make adopting typing easier: faster type checkers, better
        type inference, better availability of types across the library ecosystem
      - Changes that make typing more valuable: type-centric libraries like
        pydantic, httpx, typer, etc; IDE-native type checkers and the impact of
        types on IDE usefulness; and so forth
    - The AI material
      - How AI might reduce the cost of types: you don't have to write them out
        by hand, AI is good at boilerplate; experiments in using AI to annotate code
      - How types might be vastly more useful in the presence of AI
        - Context for code generation: MCPs for LSP-like info, the use of code indexes
          like Glean and CodeQL that can consume types, etc.
        - The effectivess of types and a fast feedback loop for improving output
          quality of models
        - Typing for security: LiteralStr and related examples, type-informed static analysis
      

- One proposal would be focused on static vs dynamic typing in Python:
  - Common dynamic typing patterns such as
    - Embedded dsls with heavy use of metaprogramming
    - Heterogenious containers, including dataframes and raw json data ingestion
    - Heavily control-flow-dependent type information
    - The use of invariant containers, given limits in the type system
  - Advice on how to deal with dynamic python
    - Why typing has benefits
      - This is where the overlap would be: the entire content of the other talk
        would be relevant here, but condensed to just a slide or two
    - Typing at the boundary between typed/untyped code
      - Some experience research (e.g. from dropbox) using gradual typing in
        mixed static / dynamic codebases
  - The path forward
    - Some history of formerly dynamic patterns that were brought into the language, e.g.
      - Protocols for (limited) duck-typing support - PEP 544
      - Better support for complex decorators - PEP 612
      - Dataclass transforms
      - Various improvements to TypedDict over time
    - Some ideas of what we could do going forward
      - Decorators for declaring duck typing in cases where Protocols don't work?
      - We could explore ways of improving support for table data (dataframes)
      - New ways of improving invariant container typing (e.g. an "owned" list that
        has no other pointers to it could be treated covariantly)


This is an open question: it's possible that the more focused talks lack enough
material to be compelling on their own, we should not assume that two talks are better.

# Draft Proposal (as a single talk covering everything)

### Title
**The Shifting Tradeoffs of Python Type Hints: Why Now Is Different**

### Duration
30 minutes

### Level
Intermediate

### Category
Core Python / Best Practices

### Abstract

Python is dynamically typed, and that's a feature, not a bug. But the landscape around when and how to use type hints is changing rapidly. This talk explores how recent advances in tooling, libraries, and AI-assisted development are reshaping the cost-benefit analysis of static typing in Python—and what that means for your code.

We'll examine why some code patterns remain better left untyped, explore the growing ecosystem of type-first libraries that actually save you work (not just catch bugs), and investigate how types are becoming increasingly valuable in the age of AI-assisted development. Along the way, we'll look at the ongoing evolution of Python's type system to better support dynamic patterns, and discuss practical strategies for deciding where types help most in your projects.

### Audience

This talk is designed for Python developers with some familiarity with type hints who want to make informed decisions about where and how to use them. You should understand basic type annotation syntax (`def foo(x: int) -> str:`), but deep type system expertise is not required.

The talk will be valuable if you:
- Have used type hints but wonder whether they're worth the effort
- Are curious about modern libraries like Pydantic, FastAPI, or Typer
- Work with AI coding assistants and want to understand how types affect code generation
- Want to understand the practical tradeoffs of typing in real projects

### Detailed Outline

**Introduction: Python's Dynamic Nature** (3 minutes)
- Python's dynamic typing is a strength, not a weakness
- Not all code patterns are practical to type:
  - Dynamic class attributes, duck typing without protocols
  - Highly dynamic frameworks (some decorators, metaprogramming)
  - Partially-typed domains (DataFrames with static-frame are technically possible but ergonomically challenging)
- The key question: when do types help, and when do they hinder?

**The Traditional Value Proposition** (4 minutes)
- Types at module boundaries (Dropbox's experience with 4M lines)
- Runtime checkers (beartype, typeguard) for validation
- Early bug detection vs. development friction
- Brief example: where types traditionally made sense

**How the Tradeoffs Are Changing: Value Going Up** (10 minutes)

*Types Power Modern IDEs* (3 min)
- Pyright/Pylance vs older tools (Jedi, Rope)
- Type-aware autocomplete, navigation, and refactoring
- Real-time feedback: Pyrefly's 1.8M lines/second enables keystroke-level checking
- Quick example: jump-to-definition accuracy with/without types

*The Type-First Library Ecosystem* (4 min)
- Libraries where types save work, not just catch bugs:
  - **Pydantic**: Validation and serialization from type definitions
  - **FastAPI**: Auto-generate API schemas, documentation, validation
  - **Typer**: CLI interfaces from type hints
  - **SQLModel**: Database schemas + type checking from one definition
  - **Pydantic Settings**: Configuration management with type safety
- Real-world impact: Configuration errors cause ~70% of production outages; typed config catches these at startup
- NumPy's 2025 typing push (33% → 88% type-completeness): ecosystem is maturing

*Types and AI Development* (3 min)
- AI code generation benefits from types as context (LSP-MCP integrations)
- Types enable fast validation feedback loops
- Academic research: 80% reduction in API/undefined symbol errors with compiler feedback
- Faster iteration: type errors in seconds vs waiting for test runs
- Security: Meta's Pysa relies on types for static security analysis

**How the Tradeoffs Are Changing: Costs Going Down** (5 minutes)
- Better type inference (return types, container types) reduces annotation burden
- AI can write type annotations as it generates code (or add them afterward)
- Tools like TypeWriter and modern LLM approaches for post-hoc typing
- Example: using AI to annotate existing code

**Supporting Dynamic Patterns in Static Types** (5 minutes)
- History of type system evolution:
  - PEP 544 (Protocols) enabled structural typing/duck typing
  - PEP 612 improved decorator typing
  - Ongoing work to expand type system capabilities
- Current limitations and potential solutions:
  - Testing with protocols (possible decorator patterns)
  - DataFrame typing approaches (static-frame, alternative table interfaces)
- The typing community is open and active

**Practical Recommendations & Call to Action** (3 minutes)
- When to prioritize types:
  - Public APIs and library boundaries
  - Code working with type-first libraries (Pydantic, FastAPI)
  - Projects using AI-assisted development
  - Configuration and data validation
- When to skip types:
  - Highly dynamic internal code with good test coverage
  - One-off scripts and exploratory work
  - Code that's hard to type (can be wrapped in typed interfaces)
- Gradual typing is your friend: start where value is highest
- Get involved: the Python typing community welcomes contributions and ideas

### Why This Talk Matters Now

The Python typing landscape has fundamentally changed in the past 2-3 years:
- Major libraries (NumPy, SQLAlchemy 2.0) have embraced types
- Type-first libraries (FastAPI, Pydantic) have achieved widespread adoption (65% of survey respondents use Pydantic)
- AI-assisted development is becoming mainstream, and types affect AI code quality
- New type checkers (Pyrefly, 2024) prioritize IDE experience over just CI/CD

This isn't about convincing everyone to type everything—it's about understanding how the equation has shifted so you can make informed decisions about where types help *your* projects.

### What Attendees Will Learn

1. How to identify code patterns that benefit most from typing
2. Modern libraries and tools that make types a productivity multiplier, not just a safety feature
3. How types interact with AI-assisted development workflows
4. Practical strategies for gradual adoption in existing projects
5. The ongoing evolution of Python's type system and how to engage with it

### Additional Notes

This talk draws on:
- Recent academic research (2024-2025) on AI code generation and static analysis
- Meta and Quansight's 2025 typing improvement initiatives for scientific Python
- Real-world adoption data from the 2024 Python typing survey (91% of respondents use types "always" or "often")
- Practical experience from major Python projects (Dropbox's 4M line migration, Instagram/Meta's tooling evolution)

The talk balances theoretical understanding with practical advice, using concrete examples throughout. All research citations will be available in shared slides.


# Draft proposal for a talk just on the changing ecosystem and tradeoffs for typing in 2025

### Title
**Python Type Hints in 2025: The Case for a Second Look**

### Duration
30 minutes

### Level
Intermediate

### Category
Core Python / Best Practices

### Abstract

For years, the conventional wisdom around Python type hints has been clear: they're valuable for large, long-lived applications, but optional for scripts and smaller projects. But what if that advice is outdated?

This talk explores how the Python typing ecosystem has fundamentally transformed in the past 2-3 years. We'll examine three major shifts: how modern libraries use types to save you work (not just catch bugs), how type-aware tooling has revolutionized the IDE experience, and how AI-assisted development changes the equation entirely. Whether you've been skeptical about types or just haven't revisited the topic recently, you'll leave with a fresh perspective on when and why types might be worth your investment.

You'll discover type-first libraries that generate APIs and CLIs from annotations, understand why modern type checkers make IDEs dramatically more useful, and see research showing how types create faster feedback loops for AI code generation. This isn't about typing everything—it's about recognizing that the tradeoffs have shifted, and making informed decisions based on today's tools, not yesterday's constraints.

### Audience

This talk is for Python developers who:
- Have basic familiarity with type hints but haven't used them extensively
- Are curious whether types are "worth it" for their projects
- Want to understand what's changed in the typing ecosystem recently
- Work with modern Python libraries or AI coding assistants
- Are looking for practical guidance on where to invest typing effort

You should understand basic type annotation syntax (`def foo(x: int) -> str:`), but no advanced typing knowledge is required. The talk assumes you're comfortable with Python but may not have kept up with recent typing developments.

### Detailed Outline

**Introduction: The Old Wisdom** (3 minutes)
- Traditional advice: types for big projects, skip them for scripts
- The problem: how do you know if your script will grow? When is "big enough"?
- A key insight: the tradeoffs we base decisions on may be outdated
- Brief acknowledgment: Python's dynamic typing enables patterns types can't express
  - But we won't focus on when types don't work—we'll focus on when they now work better than before
- This talk: what's changed, and what it means for your code today

**Shift 1: Types That Save You Work** (8 minutes)

*The Type-First Library Revolution* (5 min)
- **Pydantic**: Write a class with type hints, get validation + serialization free
  - Example: data validation that would take dozens of lines in traditional Python
  - Real impact: configuration errors cause ~70% of production outages; Pydantic Settings catches these at startup
- **FastAPI**: Type hints generate API schemas, documentation, request validation automatically
  - Example: A typed function becomes a documented, validated API endpoint
  - Why it matters: Pydantic usage rivals Mypy in surveys (65% vs 66%)
- **Typer**: CLI interfaces generated from type hints
  - Example: argparse boilerplate vs type-driven approach
  - Pattern: less code, better documentation, automatic validation
- **SQLModel**: One definition for database schema + type checking
  - Single source of truth for data models

*The Ecosystem Is Maturing* (3 min)
- NumPy's 2025 type-completeness jump: 33% → 88% in months
- SQLAlchemy 2.0 rewrote with types in mind (2023)
- httpx vs requests: modern libraries are type-first by design
- Survey data: 91% of typing-aware developers use types "always" or "often"
- The shift: newer libraries treat types as a feature multiplier, not just a safety net

**Shift 2: Types Power Your IDE** (7 minutes)

*From Jedi to Pyright: A Generation Gap* (4 min)
- Old tools (Jedi, Rope): dynamic analysis, runtime introspection
  - Struggled with complex patterns, slow on large codebases
- New tools (Pyright/Pylance, Pyrefly): static type analysis
  - Pyright: built for VS Code, type-first architecture
  - Pyrefly (Meta, 2024): 1.8M lines/second, "IDE-first" design
- What changes with types:
  - **Autocomplete**: knows what's available on typed objects
  - **Navigation**: jump-to-definition works reliably
  - **Real-time feedback**: errors as you type, not on save/compile
  - **Refactoring**: rename, extract function with confidence
- Quick demo comparison: navigating typed vs untyped code

*Why This Matters* (3 min)
- TypeScript study: better code quality and understandability metrics
  - Not just about bugs—about maintainability
- IDE experience affects daily productivity
  - Less context switching (doc searches)
  - Faster navigation
  - Earlier error detection
- Meta's investment: Pyre → Pyright → Pyrefly shows IDE value
- The subtle point: types help you *write* code, not just check it

**Shift 3: Types and AI Development** (9 minutes)

*AI Can Write Your Types* (3 min)
- The old cost: typing out annotations by hand
- The new reality: AI handles boilerplate naturally
- Research directions:
  - TypeWriter (pre-LLM ML approach) showed promise
  - Modern LLMs are better at structural, repetitive code
  - Example: using AI to annotate existing code
- The paradox: AI might reduce the cost of typing just as types become more valuable

*Types Help AI Generate Better Code* (4 min)
- Types provide structured context for code generation
  - LSP-MCP integrations: AI can query type information like an IDE
  - Code graphs (Glean, CodeQL) consume types for semantic understanding
- Types enable fast validation feedback loops
  - Academic research: 80% reduction in API/undefined symbol errors with compiler feedback
  - Type checkers run in seconds (vs waiting for test runs)
  - More specific error messages → higher fix rates (87% vs 34% in research)
- Security benefits: Meta's Pysa static analysis needs types
  - PEP 675 (LiteralString) enables security-safe libraries
  - AI-generated code + security analysis = practical defense

*The Emerging Pattern* (2 min)
- Best AI coding practices now include validation loops
- Type checking ranks highest for feedback effectiveness
  - Fast, precise, structural + semantic, no execution needed
- Context engineering: types are machine-readable documentation
- The future: type-aware code generation (AI checks types during generation, not after)

**Practical Recommendations** (3 minutes)
- When types deliver highest value today:
  - Any project using Pydantic, FastAPI, Typer, SQLModel (types unlock features)
  - Configuration and data validation (prevent production errors)
  - AI-assisted development (faster feedback, better context)
  - Public APIs and library code (IDE experience for users)
- When to still skip types:
  - True one-off scripts (but: can you be sure they'll stay one-off?)
  - Exploratory prototypes in early stages
  - Highly dynamic code (can be wrapped in typed interfaces)
- The gradual typing advantage: start where value is highest, expand incrementally
- You don't need 100% coverage—focus on boundaries and pain points

**Conclusion: Making the Decision** (2 minutes)
- The 2020 advice: "types for big projects" assumed types mainly catch bugs
- The 2025 reality: types unlock library features, improve IDE experience, help AI assist you
- The question isn't "is my project big enough?" but "which of these benefits matter to me?"
- Not prescriptive: evaluate based on your actual tools and workflow
- The landscape keeps evolving—worth revisiting periodically

### Why This Talk Matters Now

The timing is critical because multiple trends converged in 2024-2025:

1. **Library ecosystem maturity**: NumPy, SQLAlchemy 2.0, and the type-first library generation (FastAPI, Pydantic, etc.) reached production-ready status
2. **Tooling revolution**: Pyrefly (2024), Pyright's IDE dominance, and 10x+ speed improvements make types nearly frictionless
3. **AI mainstream adoption**: GitHub Copilot, Claude Code, Cursor are now standard tools, and types affect their effectiveness
4. **Research validation**: 2024-2025 academic papers quantified benefits that were previously anecdotal

Someone who evaluated types in 2020 made decisions based on different tools, libraries, and workflows. This talk updates that evaluation with current data.

### What Attendees Will Learn

1. **Concrete examples** of libraries where types save work, not just add safety (Pydantic, FastAPI, Typer, SQLModel)
2. **How type-aware tooling changes the IDE experience** and why that matters for daily productivity
3. **The relationship between types and AI development**, backed by recent research
4. **A framework for deciding where to invest typing effort** based on 2025 tools and ecosystem
5. **Practical adoption strategies** for gradually adding types where they deliver the most value

### Additional Notes

**Research foundation:**
- 2024-2025 academic research on AI code generation, static analysis feedback loops, and code quality
- Meta and Quansight's 2025 typing improvement initiatives (NumPy case study)
- 2024 Python typing survey data (750 respondents, 91% adoption among typing-aware developers)
- Real-world adoption stories (Dropbox's 4M line journey, Meta's Pyre→Pyrefly evolution)

**Talk style:**
- Balanced perspective: not advocating "type everything," but updating the cost-benefit analysis
- Concrete examples throughout (library comparisons, IDE demos, research data)
- Forward-looking but practical: focuses on tools and libraries available today

**Differentiation from existing talks:**
Most typing talks focus on *how* to use types (syntax, advanced features) or *why* types catch bugs. This talk focuses on *when* types are worth it in 2025, given ecosystem changes most developers may not be tracking.

# Draft proposal for a talk on just dynamic typing vs static typing in python

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
  - (Brief reference to the benefits covered in the other talk)
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

**Connection to second talk:**
This talk establishes *when* typing is hard or inappropriate. The second talk ("Python Type Hints in 2025") focuses on *why* typing might be worth more investment than before in the cases where it does fit. Together they provide a complete picture of the typing landscape.

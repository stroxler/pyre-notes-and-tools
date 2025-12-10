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


## The references I think I'm most likely to include

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


More stuff
- [This blog on llm hallucinations](https://www.getzep.com/ai-agents/reducing-llm-hallucinations/) discusses
  RAG = Retrieval-Augmented Generation as a method for improving LLM output. Need to research this more:
  - how widely used is it in MCP today? How widely used for coding (the examples in the blog are mostly
    not coding-specific) What are some examples?
  - this is a corporate blog plugging a particular product - is there any more
    independent research on the topic? Primary sources? I'm particularly interested in applications
    to AI coding

## A sketch of a possible talk arc

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


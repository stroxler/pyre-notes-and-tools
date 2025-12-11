# Title

**Python Types for Flow and Profit: The Case For Adopting Types in 2026**

# Duration

30 Minutes

# Audience

This talk is for:
- New Python users trying to decide whether it is worth learning to use type annotations from the start
- Anyone frequently starting new applications and needing to decide when or if to use types
- Experienced developers who have tried types before and decided the benefits didn't outweigh the costs

Experience with software development will be helpful, but this talk is mostly conceptual and about changes to Python's library and tooling ecosystem, so no particular expertise with Python typing is needed.

# Abstract

For years, the conventional wisdom around Python type hints was that they are valuable for large, long-lived applications but they may not be worth using for scripts, smaller projects, or beginners. What if that advice is outdated?

This talk explores how changes in the Python ecosystem have drastically changed the tradeoffs on using types in the past 2-3 years, both lowering costs and increasing benefits:
- Better typed libraries, better type inference, and faster type checkers have all made it easier to add types
- The emergence of type-centric libraries and the integration of type checkers into IDE tooling have made types more useful than ever

With AI-assisted programming, this trend shows signs accellerating even more because
- AI can make it much easier to write type hints on both new and existing code
- Type information and type checking can be a big help to AI, reducing hallucinations and providing very fast iteration

## Does the proposal need more pizzaz?

The v0 doc includes a few sections I've skipped for now:
- "Why this talk matters now"
- "What attendees will learn"
- "Additional notes", including differentiation

Need to figure out if / where these kinds of blurbs should be included in the final proposal.

# Detailed Outline

... TODO; I think I mostly like the v0 outline here, although I wonder if IDEs should go first, in which case we'd get
something along the lines of

- Intro: past experience, conventional wisdom, the drawbacks of typing (5 minutes)
- Shift 1: Type checkers are faster and more useful than ever (5 minutes)
- Shift 2: Types save you work  (5 minutes)
- Shift 3: Types and AI (10 minutes)
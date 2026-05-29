# On the overall architecture of Static Python and how to onboard

  Pipeline
  source.py -> AST -> declaration pass -> type binding pass -> Static Python bytecode -> interpreter/JIT runtime support.

  The important files are:

  - Docs/StaticPython/README.md: best high-level explanation of the feature and the LOAD_FIELD example.
  - Docs/StaticPython/tutorial.md: user-facing semantics: primitives, CheckedList, CheckedDict, cast, dynamic_return, etc.
  - PythonLib/cinderx/compiler/static/compiler.py:513: compiler orchestration. It builds module declarations, runs lexical scope analysis, then binds types.
  - PythonLib/cinderx/compiler/static/declaration_visitor.py:44: first pass over AST. Builds ModuleTable, static classes, functions, imports, annotations.
  - PythonLib/cinderx/compiler/static/type_binder.py:73: expression/local type flow, narrowing, assignment checks, and node type metadata.
  - PythonLib/cinderx/compiler/static/types.py:86: the Static Python semantic universe. This is the big file: Value, Class, primitive instances, functions, slots, call binding, emit hooks.
  - PythonLib/cinderx/compiler/static/__init__.py:151: StaticCodeGenBase, which turns typed AST decisions into static bytecodes.
  - PythonLib/cinderx/compiler/opcode_static.py:8: Static Python bytecode dialect: LOAD_FIELD, STORE_FIELD, CAST, INVOKE_FUNCTION, PRIMITIVE_BINARY_OP, etc.
  - StaticPython/classloader.c:87: runtime descriptor resolution, vtables, method/field slot lookup.
  - Jit/hir/preload.cpp:390: JIT preloads static descriptors into concrete field offsets/invoke targets.
  - Jit/hir/builder.cpp:4239: lowers static bytecodes like LOAD_FIELD into HIR.

  Where Pyrefly fits today
  The experimental integration is small and intentionally rough:

  - PythonLib/cinderx/compiler/static/pyrefly_compiler.py:17 subclasses the strict compiler and swaps in PyreflyTypeBinder.
  - PythonLib/cinderx/compiler/static/pyrefly_info.py:53 loads Pyrefly JSON, maps source locations to type entries, and resolves qnames back into CinderX Value/Class objects.
  - PythonLib/cinderx/compiler/static/pyrefly_type_binder.py:24 overrides expression typing: it mostly visits children, asks Pyrefly for a type, then calls set_type(node, declared_type).
  - PythonLib/cinderx/compiler/__main__.py:32 has --pyrefly, which runs pyrefly check --report-cinderx, installs the Pyrefly loader, then compiles with Pyrefly type data.

  The core risk is exactly what you called out: Static Python’s optimizer assumes some type facts are safe because they come from annotations plus runtime checks, static class layouts, strict
  modules, checked containers, or casts. Pyrefly facts are not the same kind of proof. A real integration probably needs an explicit trust model, not just “replace binder output with Pyrefly
  output.”

  A useful design framing: split facts into at least two classes.

  - Runtime-backed facts: safe to use for LOAD_FIELD, primitive unboxing, direct invoke, slot offsets, etc. These either come from static declarations or are enforced by emitted CAST/argument
    checks/container checks.
  - Speculative/checker facts: useful for choosing where to insert checks or for warnings, but not enough to emit unchecked layout-sensitive bytecode.

  Good onboarding path

  1. Read the Static Python README and tutorial.
  2. Trace one tiny example: class with self.x: int, function reading c.x. Look for how Slot.emit_load_from_slot() emits LOAD_FIELD.
  3. Read Compiler._bind(), then DeclarationVisitor.visitClassDef(), then TypeBinder.visitName/visitAttribute/visitCall.
  4. Skim types.py around Class, Function, Slot, CInstance, and call emitters. Don’t try to absorb all of it linearly.
  5. Read JIT guide sections on bytecode -> HIR, then inspect emitLoadField() and emitInvokeFunction() in builder.cpp.

  For your compiler-design goal, CinderX is a useful case study because it has multiple IR levels: Python AST, Static Python bytecode as a typed bytecode dialect, HIR with its own type lattice,
  then LIR. The most relevant IR-design lesson here is that each level has different invariants: AST binding reasons about Python semantics, static bytecode encodes runtime-checkable
  specialization decisions, and HIR reasons about machine-level lowering, deopt, refcounts, and concrete object layouts.


# On the jit vs static python

  - Static Python compiler: PythonLib/cinderx/compiler/static/*
    This is the main thing to study. It turns annotations/type knowledge into specialized bytecode and metadata.
  - Static Python runtime support: StaticPython/*, plus interpreter opcode implementations under Interpreter/<version>/cinder-bytecodes.c
    This is where static bytecodes, slot/vtable/type-descriptor machinery, checked containers, primitives, and runtime casts actually mean something.
  - Cinder JIT: Jit/*
    Mostly a consumer of Static Python bytecodes and metadata. Important later for performance, but not the center of “can Pyrefly type info safely drive Static Python?”

  For your Pyrefly angle, I’d focus on these questions before diving into JIT:

  1. What facts does Static Python currently derive itself?
     Look at DeclarationVisitor, ModuleTable, TypeBinder, and types.py.
  2. Which facts are trusted only because runtime checks are emitted?
     Look for CAST, function argument checks, return checks, CheckedList/CheckedDict, and static class slot layout.
  3. Which emitted bytecodes become unsafe if the type fact is merely checker-inferred?
     Especially LOAD_FIELD, STORE_FIELD, INVOKE_FUNCTION, INVOKE_METHOD, primitive PRIMITIVE_UNBOX, and direct typed container operations.
  4. Where should Pyrefly facts be treated as hints versus proofs?
     The current PyreflyTypeBinder largely sets node types directly. That is probably the conceptual pressure point.

  So the shortest useful path is: compiler.py -> declaration_visitor.py -> type_binder.py -> selected parts of types.py -> opcode_static.py -> StaticPython/classloader.c and Interpreter/
  <version>/cinder-bytecodes.c.

  The JIT can stay as “downstream optimizer that benefits if the bytecode contract is sound,” not the thing you need to understand first.

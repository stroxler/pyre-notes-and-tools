# Research: Gaps Between Runtime Duck Typing and PEP 544 Protocols

This document summarizes research on limitations of Python's Protocol-based static
duck typing compared to traditional runtime duck typing.

## Key Limitations

### 1. Protocol Intersection is Missing

One of the most discussed gaps is that you can't compose multiple Protocols on-the-fly.
In runtime duck typing, you just use the methods you need. In the type system, if you
need an object with both `read()` and `write()`, you have to define a new Protocol subclass.

**Key discussions:**
- [Protocol-only intersections](https://discuss.python.org/t/protocol-only-intersections/79911) on discuss.python.org
- [A case for type intersection: duck typing file-like arguments](https://discuss.python.org/t/a-case-for-type-intersection-duck-typing-file-like-arguments-with-an-ad-hoc-set-of-small-protocols/47964)

**Third-party workaround:**
- [typing-protocol-intersection](https://pypi.org/project/typing-protocol-intersection/) on PyPI

### 2. Cannot Declare Existing Classes Implement a Protocol

With runtime duck typing, if a class has the right methods, it just works. But in the
static type system, you can't retroactively declare that a third-party class implements
your Protocol without modifying it or using stubs.

**Key limitation from typing spec:**
> "You cannot easily declare retroactively that an existing class implements a protocol"

- [typing.python.org Protocol spec](https://typing.python.org/en/latest/spec/protocol.html)
- [Protocols (structural subtyping) - Issue #11](https://github.com/python/typing/issues/11) on python/typing

### 3. Attribute Implementation Flexibility Rejected

Python attributes can be implemented as instance variables, class variables, `@property`,
`@cached_property`, or descriptors - they all behave the same at runtime. But type
checkers reject some implementations as incompatible.

**Key discussion:**
- [Need a way to type-hint attributes that is compatible with duck-typing](https://discuss.python.org/t/need-a-way-to-type-hint-attributes-that-is-compatible-with-duck-typing/41137) on discuss.python.org

The core problem: A function expecting `foo: Foo` rejects implementations using
`@property` or custom descriptors, even though they behave identically at runtime.
Type checkers reject valid duck-typing implementations based on implementation details
rather than runtime behavior.

### 4. Optional Protocol Members Not Supported

Runtime code commonly uses `hasattr()` or `getattr()` with default to check for optional
methods. PEP 544 explicitly doesn't support optional members.

**Key resources:**
- [Optional class and protocol fields and methods - Issue #601](https://github.com/python/typing/issues/601) on python/typing
- [Discussion: Optional class and protocol fields and methods](https://discuss.python.org/t/discussion-optional-class-and-protocol-fields-and-methods/79254)

**From PEP 544:**
> "The specification deliberately excludes optional protocol members"

The catch-22:
- Include optional methods: Type checker incorrectly assumes they always exist
- Exclude optional methods: Type checker rejects valid code that uses runtime checks

### 5. Default Implementations Don't Work with Structural Subtyping

From the typing spec:
> "The default implementations cannot be used if the assignable-to relationship is
> implicit and only structural."

This means:
- Explicit `Protocol` inheritance gives you free default methods
- Implicit/structural matching forces you to reimplement everything yourself
- You cannot leverage protocol code unless you modify your class's inheritance hierarchy

### 6. Runtime Checking is Limited

`isinstance()` and `issubclass()` fail for Protocol types by default. Even with
`@runtime_checkable`, instance checks are "not 100% reliable statically" according
to the typing spec.

**From PEP 544:**
> "There is no intent to provide sophisticated runtime instance and class checks
> against protocol classes"

### 7. Protocol Boilerplate vs Duck Typing Simplicity

Standard Protocol definitions require verbose boilerplate, particularly for read-only
attributes. Defining read-only protocols traditionally demands repetitive `@property`
decorators.

**Third-party workaround:**
- [quacks](https://pypi.org/project/quacks/) - provides mypy-compatible extensions
  to reduce Protocol verbosity, especially for read-only attributes

### 8. ABCMeta Duck Typing Inconsistency

Python's standard library maintains two implementations of ABCMeta helpers (C version
and pure Python fallback) that behave inconsistently regarding duck typing support.
The C implementation uses stricter type checking that breaks transparent object proxies.

**Bug report:**
- [ABCMeta.__subclasscheck__() doesn't support duck typing](https://bugs.python.org/issue44847)

## Implications for Your Talk

These limitations highlight the core tension you're discussing:

1. **Library authors must anticipate duck-typing use cases** - If they don't define
   Protocols, consumers can't easily express structural compatibility

2. **Consumers can't easily "opt in" to duck typing** - You can't declare that an
   existing class satisfies a Protocol without modifying it

3. **Test mocks are a pain point** - MagicMock and similar test doubles work at
   runtime but cause type errors

4. **File-like objects are a canonical example** - The proliferation of small protocols
   (SupportsRead, SupportsWrite, etc.) and the desire for intersection types shows
   how the type system struggles with Python's historically flexible file-like duck typing

## Sources

### GitHub Issues
- [Protocols (a.k.a. structural subtyping) - Issue #11](https://github.com/python/typing/issues/11)
- [Optional class and protocol fields - Issue #601](https://github.com/python/typing/issues/601)
- [ABCMeta duck typing bug](https://bugs.python.org/issue44847)

### discuss.python.org
- [Protocol-only intersections](https://discuss.python.org/t/protocol-only-intersections/79911)
- [A case for type intersection: file-like arguments](https://discuss.python.org/t/a-case-for-type-intersection-duck-typing-file-like-arguments-with-an-ad-hoc-set-of-small-protocols/47964)
- [Need a way to type-hint attributes compatible with duck-typing](https://discuss.python.org/t/need-a-way-to-type-hint-attributes-that-is-compatible-with-duck-typing/41137)
- [Discussion: Optional class and protocol fields](https://discuss.python.org/t/discussion-optional-class-and-protocol-fields-and-methods/79254)
- [Mypy vs pyright in practice](https://discuss.python.org/t/mypy-vs-pyright-in-practice/75984)

### Official Documentation
- [PEP 544 – Protocols: Structural subtyping](https://peps.python.org/pep-0544/)
- [typing spec - Protocol](https://typing.python.org/en/latest/spec/protocol.html)

### Third-Party Libraries
- [typing-protocol-intersection on PyPI](https://pypi.org/project/typing-protocol-intersection/)
- [quacks on PyPI](https://pypi.org/project/quacks/)

### Blog Posts
- [Python type hints: duck typing with Protocol - Adam Johnson](https://adamj.eu/tech/2021/05/18/python-type-hints-duck-typing-with-protocol/)
- [Stop Using datetime.now! - Haki Benita](https://hakibenita.com/python-dependency-injection) - excellent example of duck-typed fake services

---

## Ad-hoc Duck-Typed Test Fixtures

This section covers examples of using duck typing to create simple test fixtures without
relying on mock libraries - a pattern that works at runtime but can conflict with static
type checking.

### Best Example: Fake Service for Dependency Injection

From Haki Benita's article on dependency injection, this shows creating a duck-typed
fake service for testing:

```python
class FakeIpLookupService:
    def __init__(self, results: Iterable[Optional[str]]):
        self.results = iter(results)

    def get_country_from_ip(self, ip: str) -> Optional[str]:
        return next(self.results)
```

The fake implements just the methods needed, returning predetermined values. At runtime
this works perfectly via duck typing. With static types, you'd need to either:
- Inherit from a Protocol (changing your code structure)
- Use explicit type: ignore comments
- Hope the library author defined a Protocol you can use

Source: [Stop Using datetime.now!](https://hakibenita.com/python-dependency-injection)

### Classic Example: StringIO as File-Like Object

The canonical example of duck-typed test fixtures:

```python
def test_get_layout_from_file(self):
    layout = StringIO.StringIO()
    layout.write(LAYOUT)
    layout.seek(0)
    self.assertEqual(
        test_get_layout_from_file(layout),
        {'foo': 'bar'}
    )
```

`StringIO` duck-types the file interface - it has `.write()`, `.read()`, `.seek()` etc.
Functions expecting file-like objects accept it without modification.

Source: [GitHub gist example](https://gist.github.com/adamtheturtle/e788776f0625fb05ca31)

### Library Example: pyfakefs

The `pyfakefs` library is an elaborate example of duck typing for testing. It creates
an in-memory file system that duck-types Python's entire file system interface:

> "The software under test requires no modification to work with pyfakefs"

This works because the fake objects respond to the same method calls as real file
objects - pure duck typing in action.

Source: [pyfakefs on GitHub](https://github.com/pytest-dev/pyfakefs)

### Why This Matters for the Talk

These examples illustrate the tension:

1. **Runtime flexibility**: You can create a simple class with just the methods you need
2. **Static typing friction**: Type checkers may reject these unless the library author
   anticipated your use case and defined appropriate Protocols
3. **The "permission" problem**: With Protocols, you need the library author to have
   defined the right abstractions; with runtime duck typing, you just use what works

---

## Scientific Computing: Duck-Typing Arrays and Tensors

This is where duck typing really shines in Python's ecosystem. NumPy, PyTorch, and
the scientific Python stack have embraced duck typing as a core design principle,
and these examples powerfully illustrate the gap with static typing.

### PyTorch FakeTensor: Duck-Typing for Symbolic Tracing

PyTorch's `FakeTensor` is a tensor that holds metadata (shape, dtype, device) but
**no actual data**. It duck-types real tensors for symbolic tracing in `torch.compile`.

From the documentation:
> "Fake tensors are used by the compiler to execute the code quickly and without
> allocating memory, while recording the operations and the tensor shapes involved."

**How it works:**
- FakeTensor responds to tensor operations like a real tensor
- Operations return new FakeTensors with computed metadata
- The compiler traces the computation graph without executing it

**The typing challenge:** A `FakeTensor` needs to pass wherever `Tensor` is expected
during tracing, but it's fundamentally not a Tensor (no data!). How would you type this?

```python
# During tracing, this might receive a FakeTensor
def my_layer(x: torch.Tensor) -> torch.Tensor:
    return x.reshape(-1) + 1
```

The function works fine with FakeTensor at runtime, but the type annotation says `Tensor`.

**Sources:**
- [PyTorch FakeTensor documentation](https://docs.pytorch.org/docs/stable/torch.compiler_fake_tensor.html)
- [How PyTorch handles dynamic tensor shapes](https://furiosa.ai/blog/how-pytorch-handles-dynamic-tensor-shapes)

### NumPy's Formal Duck Array Protocols

NumPy has **official Enhancement Proposals** explicitly about duck typing arrays.

#### NEP 22: The Philosophy

Defines "duck arrays" as objects that "quack like" NumPy arrays:

> "A 'duck array' is a Python object that 'quacks like' an ndarray in that it has
> the same or similar Python API, but doesn't share the C-level implementation."

Key principles:
- Focus on objects that implement ndarray's Python API
- Use protocols (`__array_ufunc__`) rather than ABCs
- Let real-world usage drive what's actually needed

Source: [NEP 22 - Duck typing for NumPy arrays](https://numpy.org/neps/nep-0022-ndarray-duck-typing-overview.html)

#### NEP 30: The `__duckarray__` Protocol

Proposes letting array-like objects opt out of coercion to ndarray:

```python
def duckarray(array_like):
    if hasattr(array_like, '__duckarray__'):
        return array_like.__duckarray__()
    return np.asarray(array_like)
```

**The problem it solves:** When you pass a Dask array or CuPy array through numpy
code that calls `np.asarray()`, it gets force-converted to a numpy array, losing
all the benefits (lazy evaluation, GPU acceleration, etc.).

Source: [NEP 30 - Duck array protocol](https://numpy.org/neps/nep-0030-duck-array-protocol.html)

### NumPy Array Protocol Methods

NumPy provides explicit hooks for duck-typing arrays:

```python
class MyArray:
    def __array__(self, dtype=None, copy=None):
        """Convert to numpy array when needed"""
        return np.asarray(self.data, dtype=dtype)

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        """Intercept numpy ufuncs like np.add, np.sin, etc."""
        args = tuple(x.data if isinstance(x, MyArray) else x for x in inputs)
        result = ufunc(*args, **kwargs)
        return MyArray(result)

    def __array_function__(self, func, types, args, kwargs):
        """Intercept numpy function calls like np.concatenate"""
        if func not in HANDLED_FUNCTIONS:
            return NotImplemented
        return HANDLED_FUNCTIONS[func](*args, **kwargs)
```

**From the NumPy docs:**
> "Duck-typing via these protocols is preferred over subclassing" for Dask, CuPy,
> sparse arrays, etc.

Source: [NumPy array classes documentation](https://numpy.org/devdocs/reference/arrays.classes.html)

### xarray's Permissive Duck Typing

xarray explicitly documents its philosophy:

> "A library like xarray that is capable of using multiple different types of arrays
> does not have to explicitly check that each one it encounters is permitted (e.g.
> `if dask`, `if numpy`, `if sparse` etc.). Instead xarray can take the more permissive
> approach of simply treating the wrapped array as valid, attempting to call the
> relevant methods and only raising an error if a problem occurs."

This enables seamless interoperability with Dask, Sparse, CuPy, and Pint without
requiring xarray modifications for each array type.

Source: [xarray duck arrays documentation](https://docs.xarray.dev/en/latest/user-guide/duckarrays.html)

### CuPy: Drop-in NumPy Replacement via Duck Typing

CuPy explicitly markets itself as duck-typing numpy:

> "CuPy acts as a drop-in replacement to run existing NumPy/SciPy code on NVIDIA
> CUDA or AMD ROCm platforms."

Just change `import numpy as np` to `import cupy as cp` - same API, GPU execution.

CuPy arrays respond to the same methods as numpy arrays. If your code does:
```python
result = arr.reshape(-1).sum()
```
It works identically whether `arr` is numpy or cupy.

Source: [CuPy GitHub](https://github.com/cupy/cupy)

### The Static Typing Challenge

These examples reveal a spectrum of duck-typing approaches in scientific Python:

| Approach | Example | Static Typing Support |
|----------|---------|----------------------|
| Drop-in replacement | CuPy | Limited - no shared Protocol |
| Protocol hooks | `__array_ufunc__` | Not expressible in type system |
| Symbolic stand-in | FakeTensor | Type says `Tensor`, reality is different |

**Key questions for your talk:**

1. How do you type a function that accepts "anything array-like"?
   - `numpy.typing.ArrayLike` exists but is limited
   - No `TensorLike` Protocol in PyTorch's typing

2. How do you type code that works with CuPy OR NumPy interchangeably?
   - They don't share a common Protocol
   - Runtime duck typing "just works"

3. How do you type tracing/JIT code where FakeTensor substitutes for Tensor?
   - The type annotation lies during tracing
   - But the code works correctly

### Sources for Scientific Computing Section

- [PyTorch FakeTensor docs](https://docs.pytorch.org/docs/stable/torch.compiler_fake_tensor.html)
- [How PyTorch handles dynamic tensor shapes](https://furiosa.ai/blog/how-pytorch-handles-dynamic-tensor-shapes)
- [NEP 22 - Duck typing overview](https://numpy.org/neps/nep-0022-ndarray-duck-typing-overview.html)
- [NEP 30 - Duck array protocol](https://numpy.org/neps/nep-0030-duck-array-protocol.html)
- [NumPy array classes](https://numpy.org/devdocs/reference/arrays.classes.html)
- [xarray duck arrays](https://docs.xarray.dev/en/latest/user-guide/duckarrays.html)
- [CuPy GitHub](https://github.com/cupy/cupy)

---

## DataFrame Libraries: Duck-Typing for Data Scientists

The DataFrame ecosystem has embraced duck typing even more aggressively than the
array ecosystem. These examples are particularly relevant for data science audiences.

### cuDF pandas: Proxy-Based GPU Acceleration (Best Example!)

RAPIDS cuDF provides a "proxy module" that intercepts pandas and accelerates it on
GPU with **zero code changes**. This is perhaps the most dramatic example of duck
typing in the Python data ecosystem.

**How it works:**
- When you load `cudf.pandas`, it substitutes a proxy module for pandas
- The proxy contains "proxy types and proxy functions"
- Operations attempt GPU execution first, automatically fall back to CPU
- Even works **inside third-party libraries** that use pandas!

```python
# Just add this, then use pandas normally
%load_ext cudf.pandas
import pandas as pd  # This is now proxied to cuDF!

df = pd.read_csv("huge_file.csv")  # Runs on GPU
df.groupby("col").mean()  # Runs on GPU
```

**Special handling for method chains:**
> "The system special cases chained method calls like `.groupby().rolling().apply()`
> that can fail at any level of the chain and rewinds and replays the chain minimally
> to deliver the correct result."

**The typing challenge:** The `df` variable looks like a `pandas.DataFrame` to type
checkers, but it's actually a cuDF proxy object. The proxy duck-types the entire
pandas API surface. How would you express this in the type system?

**Sources:**
- [cuDF pandas overview](https://rapids.ai/cudf-pandas/)
- [cuDF pandas - How it Works](https://docs.rapids.ai/api/cudf/legacy/cudf_pandas/how-it-works/)
- [NVIDIA blog on 150x acceleration](https://developer.nvidia.com/blog/rapids-cudf-accelerates-pandas-nearly-150x-with-zero-code-changes/)

### Modin: Drop-in Parallel Pandas

Modin parallelizes pandas with a single import change:

```python
import modin.pandas as pd  # Drop-in replacement for pandas
```

**Key features:**
- 90%+ pandas API coverage
- Distributes computation across cores using Ray, Dask, or MPI backends
- Same pandas API, faster execution on multi-core machines

The Modin DataFrame duck-types pandas.DataFrame - it has the same methods and
attributes, but the implementation distributes work across cores.

Source: [Modin GitHub](https://github.com/modin-project/modin)

### Koalas / pandas API on Spark

Koalas (now integrated into PySpark as "pandas API on Spark") implements the pandas
DataFrame API on Apache Spark for distributed computing:

> "Have a single codebase that works both with pandas (tests, smaller datasets)
> and with Spark (distributed datasets)."

This lets data scientists write pandas code that scales to cluster computing without
learning the Spark DataFrame API.

**Sources:**
- [Koalas documentation](https://koalas.readthedocs.io/)
- [PySpark pandas API migration guide](https://spark.apache.org/docs/latest/api/python/migration_guide/koalas_to_pyspark.html)

### Narwhals: Library-Agnostic DataFrame Code

Narwhals is a compatibility layer that lets you write code once for multiple
dataframe libraries:

> "Extremely lightweight and extensible compatibility layer between dataframe libraries"

Supports pandas, Polars, cuDF, Modin, PyArrow, Dask, DuckDB, PySpark - all without
depending on any of them. Your library code remains agnostic to which backend the
user provides.

This is duck typing as a design principle: write to an interface, accept anything
that quacks like a DataFrame.

Source: [Narwhals documentation](https://narwhals-dev.github.io/narwhals/)

### DataFrame Interchange Protocol

Pandas provides a `__dataframe__()` protocol (similar to NumPy's array protocols)
for exchanging data between libraries:

```python
# Any compliant library can implement __dataframe__()
interchange_object = df.__dataframe__()

# Convert to pandas from any compliant library
df_pandas = pd.api.interchange.from_dataframe(interchange_object)
```

This is formal duck typing - libraries implement the protocol methods, and pandas
can consume any compliant DataFrame without knowing its actual type.

Source: [pandas interchange docs](https://pandas.pydata.org/docs/reference/api/pandas.api.interchange.from_dataframe.html)

### The Static Typing Challenge for DataFrames

These examples present even bigger challenges than the array ecosystem:

| Library | Approach | Typing Challenge |
|---------|----------|------------------|
| cuDF pandas | Proxy interception | Type says `pd.DataFrame`, reality is proxy |
| Modin | Drop-in replacement | Different class, same interface |
| Koalas/Spark | Reimplementation | Looks like pandas, runs on cluster |
| Narwhals | Abstraction layer | Accepts any DataFrame-like object |

**Key questions:**

1. How do you type a function that should accept pandas OR Polars OR cuDF?
   - No shared Protocol exists
   - Runtime duck typing works fine

2. How do you type code where `import pandas` might return a proxy module?
   - The types "lie" after cudf.pandas is loaded
   - But the code works correctly

3. How do library authors like Narwhals type their dataframe-agnostic functions?
   - They need to accept "anything with these DataFrame-like methods"
   - This is exactly what Protocols should solve, but...
   - No standard DataFrame Protocol exists across the ecosystem

### Sources for DataFrame Section

- [cuDF pandas](https://rapids.ai/cudf-pandas/)
- [cuDF pandas internals](https://docs.rapids.ai/api/cudf/legacy/cudf_pandas/how-it-works/)
- [Modin GitHub](https://github.com/modin-project/modin)
- [Koalas documentation](https://koalas.readthedocs.io/)
- [Narwhals](https://narwhals-dev.github.io/narwhals/)
- [pandas interchange protocol](https://pandas.pydata.org/docs/reference/api/pandas.api.interchange.from_dataframe.html)


# Steven's conclusions


The easiest simple example to jot down quickly is a simple io one - there are a
ton of IO datatypes; what do you do if a library specified too-specific a type,
and you need a fake file or something along those lines?

The most interesting real-world examples to point to:
- cupy and cuDF as drop-in replacements for pandas and numpy, but no easy way to
  express that the ndarray and DataFrame types duck-type their targets. In practice
  we usually get around this by monkey patching everything so that type checkers never
  realize it (which leads to a different topic), but it illustrates the problem.
- torch.compile hits a very similar problem - it uses a FakeTensor type that
  duck types tensor to trace a compute graph. The resulting logic in the
  symbolic interpreter doesn't follow static typing rules, it's all duck-typing
  based.

In the data frame world, the Narwals project is one attempt to address this formally
with a well-typed layer and this could be a better long-term solution, but it takes
years for the ecosystem to catch up.


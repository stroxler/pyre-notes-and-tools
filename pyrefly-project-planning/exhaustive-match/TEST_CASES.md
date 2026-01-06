# Test Cases for Exhaustive Match Feature

This document outlines test cases that should pass once the exhaustive match
feature is fully implemented.

## Category 1: Return Type Validation with Exhaustive Enum Matches

Currently, Pyrefly knows these matches are exhaustive (no error on the match),
but it still warns about missing return because control flow analysis doesn't
know about type-based exhaustiveness.

### Test 1.1: Basic Exhaustive Enum Match
```python
from enum import Enum

class Color(Enum):
    RED = "red"
    BLUE = "blue"

def describe(color: Color) -> str:
    match color:  # Should be recognized as exhaustive
        case Color.RED:
            return "It's red"
        case Color.BLUE:
            return "It's blue"
    # Currently warns about missing return - should NOT warn
```

### Test 1.2: Exhaustive Literal Union Match
```python
from typing import Literal

def describe(status: Literal["pending", "done"]) -> str:
    match status:
        case "pending":
            return "Still working"
        case "done":
            return "Finished"
    # Currently warns about missing return - should NOT warn
```

### Test 1.3: Exhaustive Bool Match
```python
def describe(flag: bool) -> str:
    match flag:
        case True:
            return "Yes"
        case False:
            return "No"
    # Should NOT warn about missing return
```

## Category 2: Mixed Returns and Raises

### Test 2.1: All Branches Return or Raise
```python
from enum import Enum

class Status(Enum):
    OK = 1
    ERROR = 2
    UNKNOWN = 3

def handle(s: Status) -> int:
    match s:
        case Status.OK:
            return 0
        case Status.ERROR:
            raise ValueError("error")
        case Status.UNKNOWN:
            return -1
    # Should NOT warn
```

### Test 2.2: Some Branches Fall Through (Should Warn)
```python
from enum import Enum

class Status(Enum):
    OK = 1
    ERROR = 2

def handle(s: Status) -> int:  # E: Missing return (or similar)
    match s:
        case Status.OK:
            return 0
        case Status.ERROR:
            print("error")  # Falls through!
```

## Category 3: Class Pattern Exhaustiveness

### Test 3.1: Union Type Covered by Class Patterns
```python
def process(x: int | str) -> str:
    match x:
        case int():
            return f"number: {x}"
        case str():
            return f"text: {x}"
    # Should NOT warn
```

### Test 3.2: Union Type Partially Covered (Should Warn)
```python
def process(x: int | str | bytes) -> str:  # E: Missing return
    match x:
        case int():
            return f"number: {x}"
        case str():
            return f"text: {x}"
    # Missing bytes case
```

## Category 4: Guards Prevent Exhaustiveness

### Test 4.1: Guard on Otherwise Exhaustive Match
```python
from enum import Enum

class Color(Enum):
    RED = "red"
    BLUE = "blue"

def describe(color: Color) -> str:  # E: Missing return
    match color:
        case Color.RED if some_condition():  # Guard prevents exhaustiveness
            return "It's red"
        case Color.BLUE:
            return "It's blue"
```

### Test 4.2: Guard Followed by Unguarded Case for Same Pattern
```python
from enum import Enum

class Color(Enum):
    RED = "red"
    BLUE = "blue"

def describe(color: Color) -> str:
    match color:
        case Color.RED if some_condition():
            return "It's conditionally red"
        case Color.RED:  # Catches remaining RED cases
            return "It's red"
        case Color.BLUE:
            return "It's blue"
    # Should NOT warn - all cases covered
```

## Category 5: Nested Patterns (Future Enhancement)

### Test 5.1: Tuple of Enums
```python
from enum import Enum

class Bit(Enum):
    ZERO = 0
    ONE = 1

def describe(bits: tuple[Bit, Bit]) -> str:
    match bits:
        case (Bit.ZERO, Bit.ZERO):
            return "00"
        case (Bit.ZERO, Bit.ONE):
            return "01"
        case (Bit.ONE, Bit.ZERO):
            return "10"
        case (Bit.ONE, Bit.ONE):
            return "11"
    # Should NOT warn (all 4 combinations covered)
```

## Category 6: Narrowing After Exhaustive Match

These should already work due to existing narrowing, but verify:

### Test 6.1: Type Narrowed to Never After Exhaustive Match
```python
from typing import assert_type, Never
from enum import Enum

class Color(Enum):
    RED = "red"
    BLUE = "blue"

def test(color: Color):
    match color:
        case Color.RED:
            return
        case Color.BLUE:
            return
    # After exhaustive match with all returns, this is unreachable
    assert_type(color, Never)  # color should be Never here
```

## Category 7: Edge Cases

### Test 7.1: Empty Enum (Degenerate)
```python
from enum import Enum

class Empty(Enum):
    pass  # No members

def describe(e: Empty) -> str:
    match e:
        pass  # No cases needed?
    # What should happen here? Empty type = Never
```

### Test 7.2: Single Member Enum
```python
from enum import Enum

class Single(Enum):
    ONLY = 1

def describe(s: Single) -> str:
    match s:
        case Single.ONLY:
            return "the only one"
    # Should NOT warn
```

### Test 7.3: Wildcard Makes Everything Exhaustive
```python
def describe(x: object) -> str:
    match x:
        case int():
            return "int"
        case _:
            return "other"
    # Should NOT warn (wildcard is syntactically irrefutable)
```

## Non-Goals (Tests That Should Still Warn)

### NG1: Matching on Abstract Base Class
```python
from abc import ABC

class Animal(ABC):
    pass

class Dog(Animal):
    pass

class Cat(Animal):
    pass

def describe(a: Animal) -> str:  # Should STILL warn
    match a:
        case Dog():
            return "woof"
        case Cat():
            return "meow"
    # Animal could have other subclasses at runtime
```

### NG2: Open Union (object, Any)
```python
def describe(x: object) -> str:  # Should STILL warn
    match x:
        case int():
            return "int"
        case str():
            return "str"
    # object has infinitely many possible types
```

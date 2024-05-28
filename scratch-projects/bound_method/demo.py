from typing import Callable
from dataclasses import dataclass, field

class C0:
    f0: Callable[[str], str]
    # obviously nonsense, but I'll throw it in anyway
    f1: Callable[[str], str] = field()
    f2: Callable[[str], str] = lambda x: x + "_from_lambda_in_C1_body"


@dataclass
class C1:
    f0: Callable[[str], str]
    f1: Callable[[str], str] = field()
    f2: Callable[[str], str] = lambda x: x + "_from_lambda_in_C1_body"


c0 = C0()
try:
    print(c0.f0)
except AttributeError:
    print("As expected, c0.f0 is not bound")
print("c0.f1 is: ", c0.f1)
print("c0.f2 is: ", c0.f2)

c1 = C1(
    lambda x: x + "_from_lambda_in_constructor_call (f0)",
    lambda x: x + "_from_lambda_in_constructor_call (f1)",
)
print("c1.f0 is: ", c1.f0)
print("c1.f1 is: ", c1.f1)
print("c1.f2 is: ", c1.f2)

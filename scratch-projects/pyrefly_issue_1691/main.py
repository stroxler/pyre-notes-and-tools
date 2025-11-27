from typing import assert_type, reveal_type
from pkgb.b import PkgB
from pkgc.c import PkgC

b = PkgB()
c = PkgC(b)

c_from_b = b.c
b_from_c = c.b

assert_type(b, PkgB)
assert_type(c, PkgC)
assert_type(c_from_b, PkgC)
assert_type(b_from_c, PkgB)

reveal_type(c_from_b)
reveal_type(b_from_c)
reveal_type(c_from_b.b)
reveal_type(b_from_c.c)

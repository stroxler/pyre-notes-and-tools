"""Progressive demo 03: Elementwise arithmetic.

New operations:
  jnp.add, jnp.subtract, jnp.multiply, jnp.divide, jnp.negative,
  operator overloads (+, -, *, /, **)

Broadcasting rules apply: shapes are matched from the right, and
dimensions of size 1 are broadcast.
"""

import jax.numpy as jnp
from jaxtyping import Array, Float


# === Basic elementwise ops ===

a: Float[Array, "3 4"] = jnp.ones((3, 4))
b: Float[Array, "3 4"] = jnp.full((3, 4), 2.0)

# Operator overloads — same shape in, same shape out
c: Float[Array, "3 4"] = a + b
d: Float[Array, "3 4"] = a - b
e: Float[Array, "3 4"] = a * b
f: Float[Array, "3 4"] = a / b
g: Float[Array, "3 4"] = a ** b


# === Function form ===

c2: Float[Array, "3 4"] = jnp.add(a, b)
d2: Float[Array, "3 4"] = jnp.subtract(a, b)
e2: Float[Array, "3 4"] = jnp.multiply(a, b)
f2: Float[Array, "3 4"] = jnp.divide(a, b)
neg: Float[Array, "3 4"] = jnp.negative(a)


# === Broadcasting ===

# Scalar broadcast
scaled: Float[Array, "3 4"] = a * 2.0

# (3, 4) + (4,) → broadcasts along last dim
bias: Float[Array, "4"] = jnp.array([1.0, 2.0, 3.0, 4.0])
biased: Float[Array, "3 4"] = a + bias

# (3, 4) + (3, 1) → broadcasts along second dim
col: Float[Array, "3 1"] = jnp.array([[10.0], [20.0], [30.0]])
shifted: Float[Array, "3 4"] = a + col

# (1, 4) + (3, 1) → both dimensions broadcast
row: Float[Array, "1 4"] = jnp.array([[1.0, 2.0, 3.0, 4.0]])
outer_sum: Float[Array, "3 4"] = col + row


# === Residual connection pattern (used in every transformer) ===

def residual_add(
    x: Float[Array, "batch seq dim"],
    delta: Float[Array, "batch seq dim"],
) -> Float[Array, "batch seq dim"]:
    """x + sublayer(x) — the fundamental building block."""
    return x + delta


# === Shape verification ===

assert c.shape == (3, 4)
assert biased.shape == (3, 4)
assert shifted.shape == (3, 4)
assert outer_sum.shape == (3, 4)

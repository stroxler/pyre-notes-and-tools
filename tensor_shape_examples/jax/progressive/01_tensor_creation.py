"""Progressive demo 01: Tensor creation.

New operations:
  jnp.array, jnp.zeros, jnp.ones, jnp.full, jnp.eye, jnp.empty,
  jnp.zeros_like, jnp.ones_like, jnp.full_like

These are the most fundamental operations — creating tensors of known shape
and dtype. Every model starts here.
"""

import jax.numpy as jnp
from jaxtyping import Array, Float, Int


# === Explicit construction ===

# From a Python list → shape is inferred from the literal
x_1d: Float[Array, "3"] = jnp.array([1.0, 2.0, 3.0])
x_2d: Float[Array, "2 3"] = jnp.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])

# Integer tensor
x_int: Int[Array, "4"] = jnp.array([0, 1, 2, 3])


# === Zeros, ones, full ===

z1: Float[Array, "3 4"] = jnp.zeros((3, 4))
z2: Float[Array, "3 4"] = jnp.zeros((3, 4), dtype=jnp.float32)

o1: Float[Array, "2 5"] = jnp.ones((2, 5))

f1: Float[Array, "3 3"] = jnp.full((3, 3), fill_value=7.0)


# === Identity matrix ===

eye3: Float[Array, "3 3"] = jnp.eye(3)
eye34: Float[Array, "3 4"] = jnp.eye(3, 4)  # rectangular


# === Like variants (shape matches input) ===

z_like: Float[Array, "2 3"] = jnp.zeros_like(x_2d)
o_like: Float[Array, "2 3"] = jnp.ones_like(x_2d)
f_like: Float[Array, "2 3"] = jnp.full_like(x_2d, fill_value=42.0)


# === Shape verification ===

assert z1.shape == (3, 4)
assert o1.shape == (2, 5)
assert f1.shape == (3, 3)
assert eye3.shape == (3, 3)
assert z_like.shape == (2, 3)

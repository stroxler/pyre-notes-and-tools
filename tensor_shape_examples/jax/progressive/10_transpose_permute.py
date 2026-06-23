"""Progressive demo 10: Transpose and axis permutation.

New operations:
  jnp.transpose, jnp.swapaxes, jnp.moveaxis

Shape rules:
  transpose(x, axes):  reorders dimensions according to axes permutation
  swapaxes(x, a, b):   swaps exactly two axes
  moveaxis(x, src, dst): moves one axis to a new position

Used in: multi-head attention, BHWC↔BCHW format conversion, sequence axis reordering.
"""

import jax.numpy as jnp
from jaxtyping import Array, Float


# === Basic transpose ===

m: Float[Array, "3 4"] = jnp.ones((3, 4))
mt: Float[Array, "4 3"] = jnp.transpose(m)  # or m.T


# === Permutation of axes ===

x: Float[Array, "2 3 4 5"] = jnp.ones((2, 3, 4, 5))

# Swap middle two axes: (2, 3, 4, 5) → (2, 4, 3, 5)
perm1: Float[Array, "2 4 3 5"] = jnp.transpose(x, (0, 2, 1, 3))

# swapaxes is more readable for swapping exactly two
perm2: Float[Array, "2 4 3 5"] = jnp.swapaxes(x, 1, 2)

# moveaxis: move axis 3 to position 1
moved: Float[Array, "2 5 3 4"] = jnp.moveaxis(x, 3, 1)


# === BHWC ↔ BCHW conversion (vision models) ===

# JAX convolutions default to NHWC, but some operations want NCHW
bhwc: Float[Array, "2 8 8 3"] = jnp.ones((2, 8, 8, 3))

# BHWC → BCHW: (B, H, W, C) → (B, C, H, W)
bchw: Float[Array, "2 3 8 8"] = jnp.transpose(bhwc, (0, 3, 1, 2))

# BCHW → BHWC: (B, C, H, W) → (B, H, W, C)
back: Float[Array, "2 8 8 3"] = jnp.transpose(bchw, (0, 2, 3, 1))


# === Attention head transpose ===
# (B, T, H, D) → (B, H, T, D)

def heads_first(
    x: Float[Array, "batch seq heads dim"],
) -> Float[Array, "batch heads seq dim"]:
    return jnp.transpose(x, (0, 2, 1, 3))


def heads_last(
    x: Float[Array, "batch heads seq dim"],
) -> Float[Array, "batch seq heads dim"]:
    return jnp.transpose(x, (0, 2, 1, 3))


assert mt.shape == (4, 3)
assert perm1.shape == (2, 4, 3, 5)
assert bchw.shape == (2, 3, 8, 8)
assert back.shape == (2, 8, 8, 3)

"""Progressive demo 20: Cumulative operations.

New operations:
  jnp.cumsum, jnp.cumprod

Shape rules:
  cumsum(x, axis): same shape as input (running sum along axis)
  cumprod(x, axis): same shape as input (running product along axis)

Used in: position index computation, prefix sums, attention weight accumulation.
"""

import jax.numpy as jnp
from jaxtyping import Array, Float, Int


x: Float[Array, "3 4"] = jnp.ones((3, 4))

# === Cumulative sum ===

cs_all: Float[Array, "12"] = jnp.cumsum(x)  # flattened
cs_rows: Float[Array, "3 4"] = jnp.cumsum(x, axis=1)  # along columns
cs_cols: Float[Array, "3 4"] = jnp.cumsum(x, axis=0)  # along rows


# === Cumulative product ===

cp: Float[Array, "3 4"] = jnp.cumprod(x, axis=1)


# === Prefix sum for computing offsets ===

def compute_offsets(
    lengths: Int[Array, "batch"],
) -> Int[Array, "batch"]:
    """Compute start offsets from sequence lengths."""
    return jnp.cumsum(lengths) - lengths


assert cs_rows.shape == (3, 4)
assert cp.shape == (3, 4)

"""Progressive demo 02: Ranges and evenly spaced tensors.

New operations:
  jnp.arange, jnp.linspace

Used extensively for:
  - Position indices in transformers (jnp.arange(seq_len))
  - Frequency bands in positional encodings
  - Interpolation grids
"""

import jax.numpy as jnp
from jaxtyping import Array, Float, Int


# === jnp.arange ===

# Integer range
pos_ids: Int[Array, "10"] = jnp.arange(10)  # [0, 1, ..., 9]

# Float range with step
freq: Float[Array, "5"] = jnp.arange(0.0, 1.0, 0.2)  # [0.0, 0.2, 0.4, 0.6, 0.8]

# Common transformer pattern: position indices
seq_len = 128
positions: Int[Array, "128"] = jnp.arange(seq_len)


# === jnp.linspace ===

# Evenly spaced including endpoints
lin: Float[Array, "5"] = jnp.linspace(0.0, 1.0, 5)  # [0.0, 0.25, 0.5, 0.75, 1.0]

# Frequency bands for sinusoidal positional encoding
d_model = 64
# This pattern appears in every transformer with sinusoidal pos encoding:
# frequencies = 1 / (10000 ** (2i / d_model))
i = jnp.arange(0, d_model, 2)  # [0, 2, 4, ..., 62]
freqs: Float[Array, "32"] = 1.0 / (10000.0 ** (i / d_model))


# === Shape verification ===

assert pos_ids.shape == (10,)
assert positions.shape == (128,)
assert lin.shape == (5,)
assert freqs.shape == (32,)

"""Progressive demo 11: Expand dims, squeeze, broadcast.

New operations:
  jnp.expand_dims, jnp.squeeze, jnp.broadcast_to

Shape rules:
  expand_dims(x, axis):  inserts a size-1 dimension at axis
  squeeze(x, axis):      removes a size-1 dimension at axis
  broadcast_to(x, shape): explicitly broadcasts to target shape

Used in: mask construction, bias broadcasting, condition tiling.
"""

import jax.numpy as jnp
from jaxtyping import Array, Float


x: Float[Array, "3 4"] = jnp.ones((3, 4))

# === expand_dims: insert size-1 dimension ===

# Add batch dim: (3, 4) → (1, 3, 4)
batched: Float[Array, "1 3 4"] = jnp.expand_dims(x, axis=0)

# Add trailing dim: (3, 4) → (3, 4, 1)
trailing: Float[Array, "3 4 1"] = jnp.expand_dims(x, axis=-1)

# Multiple axes: (3, 4) → (1, 3, 1, 4)
multi: Float[Array, "1 3 1 4"] = jnp.expand_dims(x, axis=(0, 2))

# Using None/newaxis (idiomatic)
batched2: Float[Array, "1 3 4"] = x[None, :, :]
trailing2: Float[Array, "3 4 1"] = x[:, :, None]


# === squeeze: remove size-1 dimension ===

y: Float[Array, "1 3 1 4"] = jnp.ones((1, 3, 1, 4))

sq_all: Float[Array, "3 4"] = jnp.squeeze(y)  # removes all size-1 dims
sq_0: Float[Array, "3 1 4"] = jnp.squeeze(y, axis=0)  # remove only axis 0


# === broadcast_to: explicit broadcasting ===

# (4,) → (3, 4): broadcast a bias vector to match a matrix
bias: Float[Array, "4"] = jnp.ones(4)
bias_bc: Float[Array, "3 4"] = jnp.broadcast_to(bias, (3, 4))

# (1, 1, 4) → (2, 3, 4): useful for attention masks
mask_1d: Float[Array, "1 1 4"] = jnp.ones((1, 1, 4))
mask_bc: Float[Array, "2 3 4"] = jnp.broadcast_to(mask_1d, (2, 3, 4))


# === Mask construction patterns ===

def make_attention_mask(
    query_mask: Float[Array, "batch seq_q"],
    key_mask: Float[Array, "batch seq_k"],
) -> Float[Array, "batch 1 seq_q seq_k"]:
    """Create attention mask from padding masks.

    Broadcast outer product of masks, with extra head dimension.
    """
    # (B, Q, 1) * (B, 1, K) → (B, Q, K)
    mask = query_mask[:, :, None] * key_mask[:, None, :]
    # Add head dimension: (B, Q, K) → (B, 1, Q, K)
    return mask[:, None, :, :]


# === StarGAN condition tiling pattern ===

def tile_condition(
    condition: Float[Array, "batch channels"],
    height: int,
    width: int,
) -> Float[Array, "batch channels height width"]:
    """Spatially tile a condition vector for concatenation with an image."""
    # (B, C) → (B, C, 1, 1) → (B, C, H, W)
    c = condition[:, :, None, None]
    return jnp.broadcast_to(c, (condition.shape[0], condition.shape[1], height, width))


assert batched.shape == (1, 3, 4)
assert trailing.shape == (3, 4, 1)
assert sq_all.shape == (3, 4)
assert bias_bc.shape == (3, 4)

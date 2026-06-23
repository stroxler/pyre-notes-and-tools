"""Progressive demo 17: Reductions (sum, prod, mean).

New operations:
  jnp.sum, jnp.prod, jnp.mean

Shape rules:
  reduce(x, axis=None):             → scalar
  reduce(x, axis=i):                removes dimension i
  reduce(x, axis=i, keepdims=True): dimension i becomes 1

Used in: loss computation, normalization, global average pooling.
"""

import jax.numpy as jnp
from jaxtyping import Array, Float


x: Float[Array, "3 4"] = jnp.arange(12.0).reshape(3, 4)

# === Full reduction → scalar ===

total: Float[Array, ""] = jnp.sum(x)
product: Float[Array, ""] = jnp.prod(x)
average: Float[Array, ""] = jnp.mean(x)


# === Reduction along axis ===

# Sum along axis 0 (across rows): (3, 4) → (4,)
col_sums: Float[Array, "4"] = jnp.sum(x, axis=0)

# Sum along axis 1 (across cols): (3, 4) → (3,)
row_sums: Float[Array, "3"] = jnp.sum(x, axis=1)

# Mean along axis 1: (3, 4) → (3,)
row_means: Float[Array, "3"] = jnp.mean(x, axis=1)


# === keepdims=True: preserve the reduced dimension as 1 ===

# (3, 4) → (3, 1) — useful for broadcasting
row_sums_kd: Float[Array, "3 1"] = jnp.sum(x, axis=1, keepdims=True)

# Subtract mean (broadcasting): common normalization pattern
centered: Float[Array, "3 4"] = x - jnp.mean(x, axis=1, keepdims=True)


# === Multiple axes ===

y: Float[Array, "2 3 4"] = jnp.ones((2, 3, 4))

# Sum over spatial dims: (2, 3, 4) → (2,)
spatial_sum: Float[Array, "2"] = jnp.sum(y, axis=(1, 2))


# === Global average pooling pattern (vision models) ===

def global_avg_pool(
    x: Float[Array, "batch channels height width"],
) -> Float[Array, "batch channels"]:
    """Global average pooling: (B, C, H, W) → (B, C)."""
    return jnp.mean(x, axis=(2, 3))


# Alternative: NHWC format (more common in JAX)
def global_avg_pool_nhwc(
    x: Float[Array, "batch height width channels"],
) -> Float[Array, "batch channels"]:
    """Global average pooling for NHWC: (B, H, W, C) → (B, C)."""
    return jnp.mean(x, axis=(1, 2))


# === Cross-entropy loss pattern ===

def cross_entropy_loss(
    logits: Float[Array, "batch classes"],
    targets: Float[Array, "batch classes"],  # one-hot
) -> Float[Array, ""]:
    """Cross-entropy loss from logits and one-hot targets."""
    log_probs = logits - jnp.log(jnp.sum(jnp.exp(logits), axis=-1, keepdims=True))
    return -jnp.mean(jnp.sum(targets * log_probs, axis=-1))


assert col_sums.shape == (4,)
assert row_sums.shape == (3,)
assert row_sums_kd.shape == (3, 1)
assert centered.shape == (3, 4)

"""Progressive demo 06: Comparisons and conditional selection.

New operations:
  jnp.equal, jnp.not_equal, jnp.greater, jnp.less,
  jnp.greater_equal, jnp.less_equal,
  jnp.maximum, jnp.minimum, jnp.clip, jnp.where

All elementwise (shape in == shape out), except jnp.where which broadcasts.
Used in: masking, clipping gradients, relu implementation, attention masks.
"""

import jax.numpy as jnp
from jaxtyping import Array, Bool, Float


x: Float[Array, "3 4"] = jnp.array([
    [-1.0, 0.0, 1.0, 2.0],
    [3.0, -2.0, 0.5, -0.5],
    [4.0, 5.0, -3.0, 1.5],
])


# === Comparison ops → boolean arrays (same shape) ===

pos_mask: Bool[Array, "3 4"] = x > 0.0
eq_zero: Bool[Array, "3 4"] = jnp.equal(x, 0.0)


# === jnp.where: conditional selection ===

# where(condition, true_val, false_val) — broadcasts all three
relu_manual: Float[Array, "3 4"] = jnp.where(x > 0.0, x, 0.0)

# Attention mask pattern: fill masked positions with -inf
mask: Bool[Array, "3 4"] = jnp.array([
    [True, True, False, False],
    [True, True, True, False],
    [True, True, True, True],
])
scores: Float[Array, "3 4"] = jnp.ones((3, 4))
masked_scores: Float[Array, "3 4"] = jnp.where(mask, scores, -1e9)


# === Clipping ===

clipped: Float[Array, "3 4"] = jnp.clip(x, -1.0, 1.0)
clipped_min: Float[Array, "3 4"] = jnp.maximum(x, 0.0)  # another way to do relu


# === Masking pattern for attention ===

def apply_attention_mask(
    scores: Float[Array, "batch heads seq_q seq_k"],
    mask: Bool[Array, "batch 1 1 seq_k"],
) -> Float[Array, "batch heads seq_q seq_k"]:
    """Apply boolean mask to attention scores, filling False with -inf."""
    return jnp.where(mask, scores, jnp.finfo(scores.dtype).min)


assert relu_manual.shape == (3, 4)
assert masked_scores.shape == (3, 4)
assert clipped.shape == (3, 4)

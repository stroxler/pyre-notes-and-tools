"""Progressive demo 18: Min, max, argmin, argmax.

New operations:
  jnp.max, jnp.min, jnp.argmax, jnp.argmin

Shape rules:
  max/min follow the same rules as sum/mean
  argmax/argmin return integer indices

Used in: top-k selection, greedy decoding, double-Q min (RL).
"""

import jax.numpy as jnp
from jaxtyping import Array, Float, Int


x: Float[Array, "3 4"] = jnp.array([
    [1.0, 4.0, 2.0, 3.0],
    [5.0, 2.0, 8.0, 1.0],
    [3.0, 6.0, 4.0, 7.0],
])

# === Reductions ===

global_max: Float[Array, ""] = jnp.max(x)
row_max: Float[Array, "3"] = jnp.max(x, axis=1)
col_min: Float[Array, "4"] = jnp.min(x, axis=0)
row_max_kd: Float[Array, "3 1"] = jnp.max(x, axis=1, keepdims=True)


# === Argmax/argmin → integer indices ===

global_argmax: Int[Array, ""] = jnp.argmax(x)
row_argmax: Int[Array, "3"] = jnp.argmax(x, axis=1)  # index of max in each row
col_argmin: Int[Array, "4"] = jnp.argmin(x, axis=0)


# === Greedy decoding pattern ===

def greedy_decode(
    logits: Float[Array, "batch vocab"],
) -> Int[Array, "batch"]:
    """Select highest-probability token at each position."""
    return jnp.argmax(logits, axis=-1)


# === Double-Q minimum pattern (RL: SAC, DrQ) ===

def double_q_min(
    q1: Float[Array, "batch 1"],
    q2: Float[Array, "batch 1"],
) -> Float[Array, "batch 1"]:
    """Take minimum of two Q-value estimates (reduce overestimation)."""
    return jnp.minimum(q1, q2)


assert row_max.shape == (3,)
assert row_argmax.shape == (3,)

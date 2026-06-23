"""Progressive demo 26: Softmax family.

New operations:
  jax.nn.softmax, jax.nn.log_softmax,
  jax.nn.sigmoid, jax.nn.hard_sigmoid, jax.nn.hard_tanh

Softmax: reduces along an axis while preserving shape.
Sigmoid/tanh: elementwise.

Used in: attention weights, output probabilities, gating.
"""

import jax.nn as nn
import jax.numpy as jnp
from jaxtyping import Array, Float


logits: Float[Array, "2 5"] = jnp.array([
    [1.0, 2.0, 3.0, 0.5, 0.1],
    [0.1, 0.2, 0.3, 4.0, 0.5],
])

# === Softmax (preserves shape) ===

probs: Float[Array, "2 5"] = nn.softmax(logits, axis=-1)
log_probs: Float[Array, "2 5"] = nn.log_softmax(logits, axis=-1)

# Verify: each row sums to 1
row_sums = jnp.sum(probs, axis=-1)  # should be [1.0, 1.0]


# === Sigmoid and tanh (elementwise) ===

x: Float[Array, "3 4"] = jnp.ones((3, 4))
sig: Float[Array, "3 4"] = nn.sigmoid(x)
th: Float[Array, "3 4"] = jnp.tanh(x)  # jnp.tanh, not nn.tanh


# === Attention weights pattern ===

def attention_weights(
    scores: Float[Array, "batch heads seq_q seq_k"],
    mask: Float[Array, "batch 1 1 seq_k"] | None = None,
) -> Float[Array, "batch heads seq_q seq_k"]:
    """Compute attention weights from scores with optional masking."""
    if mask is not None:
        scores = jnp.where(mask, scores, jnp.finfo(scores.dtype).min)
    return nn.softmax(scores, axis=-1)


# === Gating patterns ===

def sigmoid_gate(
    x: Float[Array, "batch dim"],
    gate_logits: Float[Array, "batch dim"],
) -> Float[Array, "batch dim"]:
    """Sigmoid gating (used in LSTMs, GLU, etc.)."""
    return x * nn.sigmoid(gate_logits)


# === GLU (Gated Linear Unit) ===

def glu(
    x: Float[Array, "batch dim_times_2"],
) -> Float[Array, "batch dim"]:
    """GLU: split in half, gate one half with sigmoid of the other."""
    a, b = jnp.split(x, 2, axis=-1)
    return a * nn.sigmoid(b)


assert probs.shape == (2, 5)
assert log_probs.shape == (2, 5)
assert sig.shape == (3, 4)

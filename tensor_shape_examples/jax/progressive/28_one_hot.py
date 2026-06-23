"""Progressive demo 28: One-hot encoding.

New operations:
  jax.nn.one_hot

Shape rules:
  one_hot(x, num_classes): adds a new dimension of size num_classes
  (batch,) → (batch, num_classes)

Used in: cross-entropy loss, embedding input, label encoding.
"""

import jax.nn as nn
import jax.numpy as jnp
from jaxtyping import Array, Float, Int


# === Basic one-hot ===

labels: Int[Array, "4"] = jnp.array([0, 2, 1, 3])
one_hot: Float[Array, "4 5"] = nn.one_hot(labels, num_classes=5)
# [[1,0,0,0,0], [0,0,1,0,0], [0,1,0,0,0], [0,0,0,1,0]]


# === Batched one-hot ===

batch_labels: Int[Array, "2 3"] = jnp.array([[0, 1, 2], [3, 4, 0]])
batch_onehot: Float[Array, "2 3 5"] = nn.one_hot(batch_labels, num_classes=5)


# === Cross-entropy loss with one-hot ===

def cross_entropy_loss(
    logits: Float[Array, "batch vocab"],
    targets: Int[Array, "batch"],
    num_classes: int,
) -> Float[Array, ""]:
    """Cross-entropy loss from logits and integer targets."""
    target_onehot = nn.one_hot(targets, num_classes)
    log_probs = nn.log_softmax(logits, axis=-1)
    return -jnp.mean(jnp.sum(target_onehot * log_probs, axis=-1))


# === Label smoothing pattern ===

def smooth_labels(
    targets: Int[Array, "batch"],
    num_classes: int,
    smoothing: float = 0.1,
) -> Float[Array, "batch num_classes"]:
    """Apply label smoothing to one-hot targets."""
    one_hot_targets = nn.one_hot(targets, num_classes)
    return one_hot_targets * (1.0 - smoothing) + smoothing / num_classes


assert one_hot.shape == (4, 5)
assert batch_onehot.shape == (2, 3, 5)

"""Progressive demo 47: Loss functions from primitives.

Assembles: log_softmax, one_hot, sum, mean, square.

Cross-entropy, MSE, and label-smoothed CE.
"""

import jax
import jax.numpy as jnp
import jax.nn as nn
from jaxtyping import Array, Float, Int


# === Cross-entropy loss (from logits + integer labels) ===

def cross_entropy(
    logits: Float[Array, "batch classes"],
    labels: Int[Array, "batch"],
) -> Float[Array, ""]:
    """Standard cross-entropy loss."""
    log_probs = nn.log_softmax(logits, axis=-1)  # (B, C)
    one_hot_labels = nn.one_hot(labels, logits.shape[-1])  # (B, C)
    return -jnp.mean(jnp.sum(one_hot_labels * log_probs, axis=-1))


# === Sequence cross-entropy (language models) ===

def seq_cross_entropy(
    logits: Float[Array, "batch seq vocab"],
    targets: Int[Array, "batch seq"],
    mask: Float[Array, "batch seq"] | None = None,
) -> Float[Array, ""]:
    """Cross-entropy for sequence models with optional padding mask.

    logits:  (B, T, V) — predictions for each position
    targets: (B, T)    — ground truth token IDs
    mask:    (B, T)    — 1.0 for real tokens, 0.0 for padding
    """
    # Flatten: (B, T, V) → (B*T, V) and (B, T) → (B*T,)
    batch, seq, vocab = logits.shape
    flat_logits = logits.reshape(-1, vocab)
    flat_targets = targets.reshape(-1)

    log_probs = nn.log_softmax(flat_logits, axis=-1)
    one_hot = nn.one_hot(flat_targets, vocab)
    per_token_loss = -jnp.sum(one_hot * log_probs, axis=-1)  # (B*T,)

    if mask is not None:
        flat_mask = mask.reshape(-1)
        return jnp.sum(per_token_loss * flat_mask) / jnp.sum(flat_mask)
    else:
        return jnp.mean(per_token_loss)


# === MSE loss ===

def mse_loss(
    pred: Float[Array, "batch dim"],
    target: Float[Array, "batch dim"],
) -> Float[Array, ""]:
    """Mean squared error loss."""
    return jnp.mean(jnp.sum(jnp.square(pred - target), axis=-1))


# === Label-smoothed cross-entropy ===

def label_smoothed_cross_entropy(
    logits: Float[Array, "batch classes"],
    labels: Int[Array, "batch"],
    smoothing: float = 0.1,
) -> Float[Array, ""]:
    """Cross-entropy with label smoothing."""
    num_classes = logits.shape[-1]
    log_probs = nn.log_softmax(logits, axis=-1)

    one_hot = nn.one_hot(labels, num_classes)
    smooth_targets = one_hot * (1.0 - smoothing) + smoothing / num_classes

    return -jnp.mean(jnp.sum(smooth_targets * log_probs, axis=-1))


# Test
key = jax.random.PRNGKey(0)
logits = jax.random.normal(key, (4, 10))
labels = jnp.array([0, 3, 5, 9])

loss = cross_entropy(logits, labels)
assert loss.shape == ()

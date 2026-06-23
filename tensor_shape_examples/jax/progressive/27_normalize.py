"""Progressive demo 27: Normalization utilities.

New operations:
  jax.nn.normalize, jax.nn.standardize

These are building blocks for LayerNorm, BatchNorm, etc.
The actual Flax modules (nn.LayerNorm, nn.BatchNorm) wrap these.
"""

import jax.numpy as jnp
from jaxtyping import Array, Float


x: Float[Array, "2 3 4"] = jnp.ones((2, 3, 4)) * 5.0


# === Manual normalization patterns ===

# Layer norm (normalize last axis)
def layer_norm(
    x: Float[Array, "batch seq dim"],
    gamma: Float[Array, "dim"],
    beta: Float[Array, "dim"],
    eps: float = 1e-5,
) -> Float[Array, "batch seq dim"]:
    mean = jnp.mean(x, axis=-1, keepdims=True)
    var = jnp.var(x, axis=-1, keepdims=True)
    return gamma * (x - mean) / jnp.sqrt(var + eps) + beta


# RMS norm (used in LLaMA, Gemma)
def rms_norm(
    x: Float[Array, "batch seq dim"],
    weight: Float[Array, "dim"],
    eps: float = 1e-6,
) -> Float[Array, "batch seq dim"]:
    variance = jnp.mean(jnp.square(x), axis=-1, keepdims=True)
    return weight * x * jnp.reciprocal(jnp.sqrt(variance + eps))


# Batch norm (normalize over batch dim)
def batch_norm_inference(
    x: Float[Array, "batch channels height width"],
    running_mean: Float[Array, "channels"],
    running_var: Float[Array, "channels"],
    gamma: Float[Array, "channels"],
    beta: Float[Array, "channels"],
    eps: float = 1e-5,
) -> Float[Array, "batch channels height width"]:
    """BatchNorm at inference time (using running statistics)."""
    # Reshape for broadcasting: (C,) → (1, C, 1, 1)
    mean = running_mean[None, :, None, None]
    var = running_var[None, :, None, None]
    g = gamma[None, :, None, None]
    b = beta[None, :, None, None]
    return g * (x - mean) / jnp.sqrt(var + eps) + b


# Group norm
def group_norm(
    x: Float[Array, "batch channels height width"],
    num_groups: int,
    gamma: Float[Array, "channels"],
    beta: Float[Array, "channels"],
    eps: float = 1e-5,
) -> Float[Array, "batch channels height width"]:
    """Group normalization."""
    batch, channels, height, width = x.shape
    group_size = channels // num_groups

    # Reshape to (B, G, C//G, H, W)
    x = x.reshape(batch, num_groups, group_size, height, width)
    mean = jnp.mean(x, axis=(2, 3, 4), keepdims=True)
    var = jnp.var(x, axis=(2, 3, 4), keepdims=True)
    x = (x - mean) / jnp.sqrt(var + eps)

    # Back to (B, C, H, W)
    x = x.reshape(batch, channels, height, width)
    return gamma[None, :, None, None] * x + beta[None, :, None, None]

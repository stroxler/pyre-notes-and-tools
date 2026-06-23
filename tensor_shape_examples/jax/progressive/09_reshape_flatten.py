"""Progressive demo 09: Reshape and flatten.

New operations:
  jnp.reshape, .reshape(), jnp.ravel

Shape transforms:
  reshape: (*old_shape) → (*new_shape)  [product must match]
  ravel:   (*shape) → (product,)

Used in: multi-head attention (view to heads), flattening for FC layers,
         MoE batch merging/unmerging.
"""

import jax.numpy as jnp
from jaxtyping import Array, Float


x: Float[Array, "2 3 4"] = jnp.ones((2, 3, 4))

# === Basic reshape ===

# Flatten last two dims: (2, 3, 4) → (2, 12)
flat: Float[Array, "2 12"] = x.reshape(2, 12)
flat2: Float[Array, "2 12"] = jnp.reshape(x, (2, 12))

# Add a dimension: (2, 3, 4) → (2, 3, 4, 1)
expanded: Float[Array, "2 3 4 1"] = x.reshape(2, 3, 4, 1)

# Use -1 for automatic size: (2, 3, 4) → (6, 4)
auto: Float[Array, "6 4"] = x.reshape(-1, 4)

# Complete flatten
raveled: Float[Array, "24"] = jnp.ravel(x)


# === Multi-head attention reshape pattern ===
# This is the single most important reshape pattern in transformers.

def split_heads(
    x: Float[Array, "batch seq d_model"],
    num_heads: int,
) -> Float[Array, "batch num_heads seq head_dim"]:
    """Split last dim into heads: (B, T, D) → (B, T, H, D//H) → (B, H, T, D//H)"""
    batch, seq, d_model = x.shape
    head_dim = d_model // num_heads
    # Split: (B, T, D) → (B, T, H, D/H)
    x = x.reshape(batch, seq, num_heads, head_dim)
    # Transpose to: (B, H, T, D/H)
    x = jnp.transpose(x, (0, 2, 1, 3))
    return x


def merge_heads(
    x: Float[Array, "batch num_heads seq head_dim"],
) -> Float[Array, "batch seq d_model"]:
    """Merge heads back: (B, H, T, D/H) → (B, T, H, D/H) → (B, T, D)"""
    batch, num_heads, seq, head_dim = x.shape
    # Transpose: (B, H, T, D/H) → (B, T, H, D/H)
    x = jnp.transpose(x, (0, 2, 1, 3))
    # Merge: (B, T, H, D/H) → (B, T, D)
    x = x.reshape(batch, seq, num_heads * head_dim)
    return x


# === MoE batch merge/unmerge pattern (from Mixtral) ===

def merge_batch_seq(
    x: Float[Array, "batch seq dim"],
) -> Float[Array, "tokens dim"]:
    """Flatten batch and seq dims for routing."""
    batch, seq, dim = x.shape
    return x.reshape(-1, dim)


def unmerge_batch_seq(
    x: Float[Array, "tokens dim"],
    batch: int,
    seq: int,
) -> Float[Array, "batch seq dim"]:
    """Restore batch and seq dims after routing."""
    return x.reshape(batch, seq, -1)


assert flat.shape == (2, 12)
assert auto.shape == (6, 4)
assert raveled.shape == (24,)

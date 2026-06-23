"""Progressive demo 16: Repeat and tile.

New operations:
  jnp.repeat, jnp.tile

Shape rules:
  repeat(x, repeats, axis): repeat each element along axis
  tile(x, reps):            tile the whole array

Used in: GQA head replication (repeat_interleave), spatial tiling.
"""

import jax.numpy as jnp
from jaxtyping import Array, Float


x: Float[Array, "2 3"] = jnp.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])

# === jnp.repeat: repeat each element ===

# Repeat each element 2x along axis 1: (2, 3) → (2, 6)
rep: Float[Array, "2 6"] = jnp.repeat(x, 2, axis=1)

# Repeat along axis 0: (2, 3) → (4, 3)
rep0: Float[Array, "4 3"] = jnp.repeat(x, 2, axis=0)


# === jnp.tile: tile the whole array ===

# Tile 2x along axis 0: (2, 3) → (4, 3)
tiled: Float[Array, "4 3"] = jnp.tile(x, (2, 1))

# Tile in both dims: (2, 3) → (4, 9)
tiled2: Float[Array, "4 9"] = jnp.tile(x, (2, 3))


# === Grouped-Query Attention (GQA) head replication ===
# In GQA (Mixtral, LLaMA-2), KV heads < Q heads.
# Replicate KV heads to match Q head count.

def replicate_kv_heads(
    kv: Float[Array, "batch kv_heads seq dim"],
    num_repeats: int,
) -> Float[Array, "batch q_heads seq dim"]:
    """Replicate KV heads for grouped-query attention.

    (B, KV_H, T, D) → (B, KV_H, 1, T, D) → (B, KV_H, R, T, D) → (B, KV_H*R, T, D)
    """
    batch, kv_heads, seq, dim = kv.shape
    kv = kv[:, :, None, :, :]                    # (B, KV_H, 1, T, D)
    kv = jnp.tile(kv, (1, 1, num_repeats, 1, 1)) # (B, KV_H, R, T, D)
    return kv.reshape(batch, kv_heads * num_repeats, seq, dim)


assert rep.shape == (2, 6)
assert tiled.shape == (4, 3)
assert tiled2.shape == (4, 9)

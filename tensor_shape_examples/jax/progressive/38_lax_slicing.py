"""Progressive demo 38: Dynamic slicing.

New operations:
  jax.lax.dynamic_slice, jax.lax.dynamic_update_slice

Shape rules:
  dynamic_slice(x, start_indices, slice_sizes): extracts a fixed-size slice
  dynamic_update_slice(x, update, start_indices): writes update into x

Unlike Python slicing, start indices can be dynamic (traced) values.

Used in: KV cache updates, positional embedding lookup, dynamic batching.
"""

import jax
import jax.numpy as jnp
import jax.lax as lax
from jaxtyping import Array, Float, Int


# === Basic dynamic_slice ===

x: Float[Array, "10 8"] = jnp.arange(80.0).reshape(10, 8)

# Extract a (3, 4) slice starting at (2, 1)
sliced: Float[Array, "3 4"] = lax.dynamic_slice(
    x,
    start_indices=(2, 1),
    slice_sizes=(3, 4),
)
assert sliced.shape == (3, 4)


# === Dynamic slice with traced index (works in jit) ===

@jax.jit
def get_row(x: Float[Array, "10 8"], i: Int[Array, ""]) -> Float[Array, "1 8"]:
    return lax.dynamic_slice(x, (i, 0), (1, 8))

row = get_row(x, jnp.int32(5))
assert row.shape == (1, 8)


# === dynamic_update_slice: write into array ===

y: Float[Array, "10 8"] = jnp.zeros((10, 8))
update: Float[Array, "3 4"] = jnp.ones((3, 4))

# Write (3, 4) block at position (2, 1)
updated: Float[Array, "10 8"] = lax.dynamic_update_slice(y, update, (2, 1))
assert updated.shape == (10, 8)


# === KV cache update pattern ===

def update_kv_cache(
    cache_k: Float[Array, "batch max_len heads dim"],
    cache_v: Float[Array, "batch max_len heads dim"],
    new_k: Float[Array, "batch 1 heads dim"],
    new_v: Float[Array, "batch 1 heads dim"],
    cache_index: Int[Array, ""],
) -> tuple[
    Float[Array, "batch max_len heads dim"],
    Float[Array, "batch max_len heads dim"],
]:
    """Update KV cache at current position.

    This is the core autoregressive decoding pattern.
    """
    # Write new K, V at cache_index
    cache_k = lax.dynamic_update_slice(
        cache_k, new_k, (0, cache_index, 0, 0)
    )
    cache_v = lax.dynamic_update_slice(
        cache_v, new_v, (0, cache_index, 0, 0)
    )
    return cache_k, cache_v


# === Positional embedding lookup ===

def get_position_embedding(
    pos_embed_table: Float[Array, "max_len dim"],
    start_pos: Int[Array, ""],
    seq_len: int,
) -> Float[Array, "seq_len dim"]:
    """Look up positional embeddings starting at start_pos."""
    return lax.dynamic_slice(
        pos_embed_table,
        (start_pos, 0),
        (seq_len, pos_embed_table.shape[1]),
    )

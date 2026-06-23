"""Progressive demo 49: KV cache update pattern.

Assembles: dynamic_slice, dynamic_update_slice, zeros.

The KV cache is essential for efficient autoregressive decoding.
At each step, we compute K, V for the new token and append them
to the cache rather than recomputing for the entire sequence.
"""

import jax
import jax.numpy as jnp
import jax.lax as lax
from jaxtyping import Array, Float, Int


def init_kv_cache(
    batch_size: int,
    max_len: int,
    num_heads: int,
    head_dim: int,
) -> tuple[Float[Array, "batch max_len heads dim"], Float[Array, "batch max_len heads dim"]]:
    """Initialize empty KV cache."""
    shape = (batch_size, max_len, num_heads, head_dim)
    return jnp.zeros(shape), jnp.zeros(shape)


def update_cache(
    cache: Float[Array, "batch max_len heads dim"],
    new_entry: Float[Array, "batch 1 heads dim"],
    position: Int[Array, ""],
) -> Float[Array, "batch max_len heads dim"]:
    """Write a new K or V entry at the current position."""
    return lax.dynamic_update_slice(
        cache,
        new_entry,
        (0, position, 0, 0),
    )


def get_cached_kv(
    cache: Float[Array, "batch max_len heads dim"],
    current_len: Int[Array, ""],
) -> Float[Array, "batch current_len heads dim"]:
    """Retrieve the valid portion of the cache (positions 0..current_len-1)."""
    return lax.dynamic_slice(
        cache,
        (0, 0, 0, 0),
        (cache.shape[0], current_len, cache.shape[2], cache.shape[3]),
    )


# === Full autoregressive attention with KV cache ===

def cached_attention(
    q: Float[Array, "batch 1 heads dim"],
    new_k: Float[Array, "batch 1 heads dim"],
    new_v: Float[Array, "batch 1 heads dim"],
    cache_k: Float[Array, "batch max_len heads dim"],
    cache_v: Float[Array, "batch max_len heads dim"],
    position: Int[Array, ""],
) -> tuple[
    Float[Array, "batch 1 heads dim"],
    Float[Array, "batch max_len heads dim"],
    Float[Array, "batch max_len heads dim"],
]:
    """Single-step attention with KV cache update.

    1. Insert new K, V into cache at `position`
    2. Attend over all cached positions (0..position)
    3. Return attention output + updated caches
    """
    # Update cache
    cache_k = update_cache(cache_k, new_k, position)
    cache_v = update_cache(cache_v, new_v, position)

    # Retrieve valid K, V up to current position + 1
    current_len = position + 1
    k = lax.dynamic_slice(cache_k, (0, 0, 0, 0),
                          (cache_k.shape[0], current_len, cache_k.shape[2], cache_k.shape[3]))
    v = lax.dynamic_slice(cache_v, (0, 0, 0, 0),
                          (cache_v.shape[0], current_len, cache_v.shape[2], cache_v.shape[3]))

    # Transpose for attention: (B, T, H, D) → (B, H, T, D)
    q_t = jnp.transpose(q, (0, 2, 1, 3))    # (B, H, 1, D)
    k_t = jnp.transpose(k, (0, 2, 1, 3))    # (B, H, T, D)
    v_t = jnp.transpose(v, (0, 2, 1, 3))    # (B, H, T, D)

    # Scaled dot-product attention
    head_dim = q.shape[-1]
    scores = jnp.einsum("bhqd,bhkd->bhqk", q_t, k_t) / jnp.sqrt(jnp.float32(head_dim))
    weights = jax.nn.softmax(scores, axis=-1)
    attn_out = jnp.einsum("bhqk,bhkd->bhqd", weights, v_t)  # (B, H, 1, D)

    # Back to (B, 1, H, D)
    attn_out = jnp.transpose(attn_out, (0, 2, 1, 3))

    return attn_out, cache_k, cache_v


# Test
batch, max_len, heads, dim = 2, 128, 8, 32
cache_k, cache_v = init_kv_cache(batch, max_len, heads, dim)

key = jax.random.PRNGKey(0)
k1, k2, k3 = jax.random.split(key, 3)
q = jax.random.normal(k1, (batch, 1, heads, dim))
new_k = jax.random.normal(k2, (batch, 1, heads, dim))
new_v = jax.random.normal(k3, (batch, 1, heads, dim))

out, cache_k, cache_v = cached_attention(q, new_k, new_v, cache_k, cache_v, jnp.int32(0))
assert out.shape == (batch, 1, heads, dim)

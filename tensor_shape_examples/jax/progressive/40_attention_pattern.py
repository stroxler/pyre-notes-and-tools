"""Progressive demo 40: Multi-head attention pattern.

Assembles: matmul, reshape, transpose, softmax, einsum, where.

This is the single most important pattern in modern deep learning.
Every transformer model uses this exact sequence of operations.
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Bool, Float


def multi_head_attention(
    q: Float[Array, "batch seq_q d_model"],
    k: Float[Array, "batch seq_k d_model"],
    v: Float[Array, "batch seq_k d_model"],
    w_q: Float[Array, "d_model d_model"],
    w_k: Float[Array, "d_model d_model"],
    w_v: Float[Array, "d_model d_model"],
    w_o: Float[Array, "d_model d_model"],
    num_heads: int,
    mask: Bool[Array, "batch 1 seq_q seq_k"] | None = None,
) -> Float[Array, "batch seq_q d_model"]:
    """Multi-head attention from scratch.

    Steps:
      1. Project Q, K, V
      2. Split into heads: (B, T, D) → (B, H, T, D/H)
      3. Scaled dot-product attention per head
      4. Merge heads: (B, H, T, D/H) → (B, T, D)
      5. Output projection
    """
    batch, seq_q, d_model = q.shape
    _, seq_k, _ = k.shape
    head_dim = d_model // num_heads

    # 1. Linear projections
    q = q @ w_q  # (B, T_q, D)
    k = k @ w_k  # (B, T_k, D)
    v = v @ w_v  # (B, T_k, D)

    # 2. Split into heads
    q = q.reshape(batch, seq_q, num_heads, head_dim)
    k = k.reshape(batch, seq_k, num_heads, head_dim)
    v = v.reshape(batch, seq_k, num_heads, head_dim)

    q = jnp.transpose(q, (0, 2, 1, 3))  # (B, H, T_q, D/H)
    k = jnp.transpose(k, (0, 2, 1, 3))  # (B, H, T_k, D/H)
    v = jnp.transpose(v, (0, 2, 1, 3))  # (B, H, T_k, D/H)

    # 3. Scaled dot-product attention
    scale = jnp.sqrt(jnp.float32(head_dim))
    scores = jnp.einsum("bhqd,bhkd->bhqk", q, k) / scale  # (B, H, T_q, T_k)

    if mask is not None:
        scores = jnp.where(mask, scores, jnp.finfo(scores.dtype).min)

    weights = jax.nn.softmax(scores, axis=-1)  # (B, H, T_q, T_k)
    attn_out = jnp.einsum("bhqk,bhkd->bhqd", weights, v)  # (B, H, T_q, D/H)

    # 4. Merge heads
    attn_out = jnp.transpose(attn_out, (0, 2, 1, 3))  # (B, T_q, H, D/H)
    attn_out = attn_out.reshape(batch, seq_q, d_model)  # (B, T_q, D)

    # 5. Output projection
    return attn_out @ w_o  # (B, T_q, D)


# === Test it ===

key = jax.random.PRNGKey(0)
keys = jax.random.split(key, 7)

batch, seq, d_model, num_heads = 2, 10, 64, 8
q = jax.random.normal(keys[0], (batch, seq, d_model))
k = jax.random.normal(keys[1], (batch, seq, d_model))
v = jax.random.normal(keys[2], (batch, seq, d_model))
w_q = jax.random.normal(keys[3], (d_model, d_model))
w_k = jax.random.normal(keys[4], (d_model, d_model))
w_v = jax.random.normal(keys[5], (d_model, d_model))
w_o = jax.random.normal(keys[6], (d_model, d_model))

out = multi_head_attention(q, k, v, w_q, w_k, w_v, w_o, num_heads)
assert out.shape == (2, 10, 64)

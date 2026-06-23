"""Progressive demo 41: Positional encoding patterns.

Assembles: sin, cos, arange, expand_dims, concatenate.

Covers sinusoidal (Vaswani), learned, and RoPE (LLaMA).
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Float


# === Sinusoidal positional encoding (Attention Is All You Need) ===

def sinusoidal_pe(
    seq_len: int,
    d_model: int,
) -> Float[Array, "1 seq_len d_model"]:
    """Fixed sinusoidal positional encoding.

    PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))
    PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
    """
    position = jnp.arange(seq_len)[:, None]             # (T, 1)
    div_term = jnp.exp(
        jnp.arange(0, d_model, 2) * -(jnp.log(10000.0) / d_model)
    )                                                     # (D/2,)

    pe = jnp.zeros((seq_len, d_model))
    pe = pe.at[:, 0::2].set(jnp.sin(position * div_term))  # even indices
    pe = pe.at[:, 1::2].set(jnp.cos(position * div_term))  # odd indices
    return pe[None, :, :]  # (1, T, D) for broadcasting over batch

pe = sinusoidal_pe(128, 64)
assert pe.shape == (1, 128, 64)


# === Learned positional encoding ===

def learned_pe(
    key: jax.Array,
    max_len: int,
    d_model: int,
) -> Float[Array, "1 max_len d_model"]:
    """Learned positional encoding (initialized from normal distribution)."""
    return jax.random.normal(key, (1, max_len, d_model)) * 0.02

lpe = learned_pe(jax.random.PRNGKey(0), 128, 64)
assert lpe.shape == (1, 128, 64)


# === Rotary Position Embedding (RoPE) — used in LLaMA, GPT-NeoX ===

def compute_rope_frequencies(
    dim: int,
    max_seq_len: int,
    base: float = 10000.0,
) -> tuple[Float[Array, "max_seq_len half_dim"], Float[Array, "max_seq_len half_dim"]]:
    """Precompute cos and sin for RoPE."""
    freqs = 1.0 / (base ** (jnp.arange(0, dim, 2).astype(jnp.float32) / dim))
    t = jnp.arange(max_seq_len, dtype=jnp.float32)
    angles = jnp.outer(t, freqs)  # (T, D/2)
    return jnp.cos(angles), jnp.sin(angles)


def apply_rope(
    x: Float[Array, "batch heads seq dim"],
    cos: Float[Array, "seq half_dim"],
    sin: Float[Array, "seq half_dim"],
) -> Float[Array, "batch heads seq dim"]:
    """Apply RoPE to queries or keys.

    Splits dim in half, rotates pairs: [x0, x1] → [x0*cos - x1*sin, x0*sin + x1*cos]
    """
    d = x.shape[-1]
    x1 = x[..., :d // 2]  # first half
    x2 = x[..., d // 2:]  # second half

    # Broadcast cos/sin: (T, D/2) → (1, 1, T, D/2)
    cos = cos[None, None, :, :]
    sin = sin[None, None, :, :]

    rotated = jnp.concatenate([
        x1 * cos - x2 * sin,
        x1 * sin + x2 * cos,
    ], axis=-1)
    return rotated


# Test RoPE
cos, sin = compute_rope_frequencies(64, 128)
x = jax.random.normal(jax.random.PRNGKey(0), (2, 8, 128, 64))
rotated = apply_rope(x, cos, sin)
assert rotated.shape == (2, 8, 128, 64)

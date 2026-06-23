"""Progressive demo 05: Trigonometric functions.

New operations:
  jnp.sin, jnp.cos, jnp.tan, jnp.tanh, jnp.arctan2

All elementwise: shape in == shape out.
Used in: sinusoidal positional encoding, RoPE, activations (tanh).
"""

import jax.numpy as jnp
from jaxtyping import Array, Float


x: Float[Array, "3 4"] = jnp.ones((3, 4))

sin_x: Float[Array, "3 4"] = jnp.sin(x)
cos_x: Float[Array, "3 4"] = jnp.cos(x)
tanh_x: Float[Array, "3 4"] = jnp.tanh(x)


# === Sinusoidal positional encoding pattern ===
# From "Attention Is All You Need" — used in nearly all transformers

def sinusoidal_position_encoding(
    seq_len: int,
    d_model: int,
) -> Float[Array, "seq_len d_model"]:
    """Compute sinusoidal positional encodings.

    PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))
    PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
    """
    position = jnp.arange(seq_len)[:, None]        # [seq_len, 1]
    dim = jnp.arange(0, d_model, 2)[None, :]       # [1, d_model/2]
    angle = position / (10000.0 ** (dim / d_model)) # [seq_len, d_model/2]

    pe_sin = jnp.sin(angle)  # [seq_len, d_model/2]
    pe_cos = jnp.cos(angle)  # [seq_len, d_model/2]

    # Interleave sin and cos: [seq_len, d_model]
    pe = jnp.zeros((seq_len, d_model))
    pe = pe.at[:, 0::2].set(pe_sin)
    pe = pe.at[:, 1::2].set(pe_cos)
    return pe


pe = sinusoidal_position_encoding(128, 64)
assert pe.shape == (128, 64)


# === RoPE frequency computation pattern (used in LLaMA, GPT-Fast) ===

def compute_rope_freqs(
    dim: int,
    seq_len: int,
    base: float = 10000.0,
) -> Float[Array, "seq_len half_dim"]:
    """Compute rotary position embedding frequencies."""
    freqs = 1.0 / (base ** (jnp.arange(0, dim, 2) / dim))  # [dim/2]
    t = jnp.arange(seq_len)                                  # [seq_len]
    freqs = jnp.outer(t, freqs)                               # [seq_len, dim/2]
    return freqs


rope_freqs = compute_rope_freqs(64, 128)
assert rope_freqs.shape == (128, 32)

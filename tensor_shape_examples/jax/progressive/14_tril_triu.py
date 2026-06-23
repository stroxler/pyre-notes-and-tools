"""Progressive demo 14: Triangular matrices.

New operations:
  jnp.tril, jnp.triu

Used in: causal attention masks (every autoregressive model).
"""

import jax.numpy as jnp
from jaxtyping import Array, Bool, Float


# === Basic tril/triu ===

m: Float[Array, "4 4"] = jnp.ones((4, 4))
lower: Float[Array, "4 4"] = jnp.tril(m)   # lower triangular
upper: Float[Array, "4 4"] = jnp.triu(m)   # upper triangular

# With diagonal offset
lower_k1: Float[Array, "4 4"] = jnp.tril(m, k=1)   # include one above diagonal
upper_k1: Float[Array, "4 4"] = jnp.triu(m, k=1)   # exclude diagonal

# Non-square
rect: Float[Array, "3 5"] = jnp.ones((3, 5))
rect_lower: Float[Array, "3 5"] = jnp.tril(rect)


# === Causal mask pattern (used in GPT, LLaMA, etc.) ===

def make_causal_mask(
    seq_len: int,
) -> Bool[Array, "1 1 seq_len seq_len"]:
    """Create causal attention mask.

    Returns a mask where position i can attend to positions j <= i.
    Shape: (1, 1, T, T) for broadcasting across batch and heads.
    """
    mask = jnp.tril(jnp.ones((seq_len, seq_len), dtype=jnp.bool_))
    return mask[None, None, :, :]  # (1, 1, T, T)


causal = make_causal_mask(4)
assert causal.shape == (1, 1, 4, 4)


# === Sliding window attention mask (used in Mistral/Mixtral) ===

def make_sliding_window_mask(
    seq_len: int,
    window_size: int,
) -> Bool[Array, "seq_len seq_len"]:
    """Causal mask with limited window: attend to at most window_size past positions."""
    causal = jnp.tril(jnp.ones((seq_len, seq_len), dtype=jnp.bool_))
    window = jnp.triu(jnp.ones((seq_len, seq_len), dtype=jnp.bool_), k=-(window_size - 1))
    return causal & window


sw_mask = make_sliding_window_mask(8, 3)
assert sw_mask.shape == (8, 8)

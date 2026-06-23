"""Progressive demo 42: Causal masking patterns.

Assembles: tril, where, expand_dims, broadcast_to.
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Bool, Float


# === Basic causal mask ===

def causal_mask(
    seq_len: int,
) -> Bool[Array, "1 1 seq_len seq_len"]:
    """Standard causal mask for autoregressive attention."""
    mask = jnp.tril(jnp.ones((seq_len, seq_len), dtype=jnp.bool_))
    return mask[None, None, :, :]


# === Combined causal + padding mask ===

def combined_mask(
    padding_mask: Bool[Array, "batch seq_k"],
    seq_q: int,
) -> Bool[Array, "batch 1 seq_q seq_k"]:
    """Combine causal mask with padding mask.

    padding_mask: True = real token, False = padding
    """
    seq_k = padding_mask.shape[-1]

    # Causal: (1, 1, Q, K)
    causal = jnp.tril(jnp.ones((seq_q, seq_k), dtype=jnp.bool_))[None, None, :, :]

    # Padding: (B, 1, 1, K) — broadcast over heads and queries
    pad = padding_mask[:, None, None, :]

    # Both must be True to attend
    return causal & pad


# === Apply mask to attention scores ===

def apply_mask(
    scores: Float[Array, "batch heads seq_q seq_k"],
    mask: Bool[Array, "batch 1 seq_q seq_k"],
    mask_value: float = -1e9,
) -> Float[Array, "batch heads seq_q seq_k"]:
    """Fill masked positions with large negative value before softmax."""
    return jnp.where(mask, scores, mask_value)


# === Prefix mask (for prefix LM / encoder-decoder) ===

def prefix_mask(
    prefix_len: int,
    total_len: int,
) -> Bool[Array, "1 1 total_len total_len"]:
    """Mask that allows full attention in prefix, causal in suffix.

    Positions 0..prefix_len-1 can attend to all prefix positions.
    Positions prefix_len.. can attend to prefix + causally to suffix.
    """
    # All-to-all in prefix region
    prefix_block = jnp.ones((total_len, prefix_len), dtype=jnp.bool_)
    # Causal in suffix region
    suffix_len = total_len - prefix_len
    suffix_block = jnp.tril(jnp.ones((total_len, suffix_len), dtype=jnp.bool_))
    # Zero out suffix→suffix for prefix positions
    suffix_block = suffix_block.at[:prefix_len, :].set(False)

    full_mask = jnp.concatenate([prefix_block, suffix_block], axis=-1)
    return full_mask[None, None, :, :]


# Test
cm = causal_mask(8)
assert cm.shape == (1, 1, 8, 8)

pm = prefix_mask(3, 8)
assert pm.shape == (1, 1, 8, 8)

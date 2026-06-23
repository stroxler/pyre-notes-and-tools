"""Progressive demo 48: Weight tying (output projection via embedding transpose).

Assembles: matmul with transposed embedding matrix.

Used in: GPT-2, many language models where the output projection
shares weights with the token embedding table.
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Float, Int


def tied_output_projection(
    hidden: Float[Array, "batch seq d_model"],
    embed_table: Float[Array, "vocab d_model"],
) -> Float[Array, "batch seq vocab"]:
    """Project hidden states to logits using the transposed embedding matrix.

    Instead of a separate nn.Dense(d_model, vocab), reuse embed_table.T.
    This reduces parameters and often improves performance.
    """
    return hidden @ embed_table.T  # (B, T, D) @ (D, V) → (B, T, V)


# === Full embedding + output with weight tying ===

def language_model_head(
    token_ids: Int[Array, "batch seq"],
    embed_table: Float[Array, "vocab d_model"],
    pos_embed: Float[Array, "max_len d_model"],
    transformer_fn,  # callable that takes (B, T, D) → (B, T, D)
) -> Float[Array, "batch seq vocab"]:
    """Full LM: embed → transform → project (with tied weights).

    The same embed_table is used for both input embedding and output logits.
    """
    seq_len = token_ids.shape[1]

    # Embed
    x = embed_table[token_ids] + pos_embed[:seq_len]  # (B, T, D)

    # Transform (placeholder for transformer blocks)
    x = transformer_fn(x)

    # Output: tied projection
    logits = x @ embed_table.T  # (B, T, D) @ (D, V) → (B, T, V)
    return logits


# === With optional scaling (used in WMT Transformer) ===

def tied_output_scaled(
    hidden: Float[Array, "batch seq d_model"],
    embed_table: Float[Array, "vocab d_model"],
) -> Float[Array, "batch seq vocab"]:
    """Tied projection with 1/sqrt(d_model) scaling."""
    d_model = hidden.shape[-1]
    return hidden @ embed_table.T / jnp.sqrt(jnp.float32(d_model))


# Test
key = jax.random.PRNGKey(0)
k1, k2 = jax.random.split(key)

vocab, d_model = 1000, 64
embed_table = jax.random.normal(k1, (vocab, d_model)) * 0.02
hidden = jax.random.normal(k2, (2, 10, d_model))

logits = tied_output_projection(hidden, embed_table)
assert logits.shape == (2, 10, 1000)

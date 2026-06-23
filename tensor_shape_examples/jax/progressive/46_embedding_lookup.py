"""Progressive demo 46: Embedding lookup.

Assembles: take (or indexing), addition.

Token embedding + position embedding — the first step in every
transformer model.
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Float, Int


# === Token embedding ===

def token_embed(
    token_ids: Int[Array, "batch seq"],
    embed_table: Float[Array, "vocab d_model"],
) -> Float[Array, "batch seq d_model"]:
    """Look up token embeddings from an embedding table."""
    return embed_table[token_ids]


# === Token + position embedding ===

def embed(
    token_ids: Int[Array, "batch seq"],
    token_embed_table: Float[Array, "vocab d_model"],
    pos_embed_table: Float[Array, "max_len d_model"],
) -> Float[Array, "batch seq d_model"]:
    """Token embedding + learned positional embedding."""
    seq_len = token_ids.shape[1]
    tok_emb = token_embed_table[token_ids]       # (B, T, D)
    pos_emb = pos_embed_table[:seq_len]           # (T, D)
    return tok_emb + pos_emb                      # broadcast: (B, T, D) + (T, D)


# === Token + sinusoidal position ===

def embed_with_sinusoidal(
    token_ids: Int[Array, "batch seq"],
    token_embed_table: Float[Array, "vocab d_model"],
    d_model: int,
) -> Float[Array, "batch seq d_model"]:
    """Token embedding + sinusoidal positional encoding."""
    seq_len = token_ids.shape[1]
    tok_emb = token_embed_table[token_ids]

    # Compute sinusoidal PE inline
    position = jnp.arange(seq_len)[:, None]
    div_term = jnp.exp(jnp.arange(0, d_model, 2) * -(jnp.log(10000.0) / d_model))
    pe = jnp.zeros((seq_len, d_model))
    pe = pe.at[:, 0::2].set(jnp.sin(position * div_term))
    pe = pe.at[:, 1::2].set(jnp.cos(position * div_term))

    return tok_emb + pe  # (B, T, D)


# === Segment embedding (BERT) ===

def embed_bert(
    token_ids: Int[Array, "batch seq"],
    segment_ids: Int[Array, "batch seq"],
    token_table: Float[Array, "vocab d_model"],
    segment_table: Float[Array, "2 d_model"],
    pos_table: Float[Array, "max_len d_model"],
) -> Float[Array, "batch seq d_model"]:
    """BERT: token + segment + position embeddings."""
    seq_len = token_ids.shape[1]
    return (
        token_table[token_ids]
        + segment_table[segment_ids]
        + pos_table[:seq_len]
    )


# Test
key = jax.random.PRNGKey(0)
k1, k2 = jax.random.split(key)
vocab, d_model, max_len = 1000, 64, 512

token_table = jax.random.normal(k1, (vocab, d_model)) * 0.02
pos_table = jax.random.normal(k2, (max_len, d_model)) * 0.02
token_ids = jnp.array([[1, 5, 100, 42], [7, 8, 9, 10]])

out = embed(token_ids, token_table, pos_table)
assert out.shape == (2, 4, 64)

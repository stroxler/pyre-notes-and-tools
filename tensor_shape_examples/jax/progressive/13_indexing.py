"""Progressive demo 13: Indexing and gathering.

New operations:
  basic indexing, slicing, boolean indexing,
  jnp.take, jnp.take_along_axis

Used in: embedding lookup, CLS token extraction, KV cache indexing,
         last-token selection, top-k selection.
"""

import jax.numpy as jnp
from jaxtyping import Array, Float, Int


x: Float[Array, "4 5"] = jnp.arange(20.0).reshape(4, 5)

# === Basic indexing ===

row: Float[Array, "5"] = x[0]            # first row
elem: Float[Array, ""] = x[1, 2]         # scalar element
col: Float[Array, "4"] = x[:, 0]         # first column


# === Slicing ===

sub: Float[Array, "2 3"] = x[1:3, 0:3]    # submatrix
last_row: Float[Array, "1 5"] = x[-1:]     # last row, keeping dims
every_other: Float[Array, "2 5"] = x[::2]  # stride-2 selection


# === jnp.take: gather along axis ===

indices: Int[Array, "3"] = jnp.array([0, 2, 3])
gathered: Float[Array, "3 5"] = jnp.take(x, indices, axis=0)  # select rows 0, 2, 3


# === jnp.take_along_axis: gather with index array ===

# For top-k style gathering
vals: Float[Array, "3 4"] = jnp.array([
    [1.0, 4.0, 2.0, 3.0],
    [5.0, 2.0, 8.0, 1.0],
    [3.0, 6.0, 4.0, 7.0],
])
# Indices of top-2 per row (simulated)
top_idx: Int[Array, "3 2"] = jnp.array([[1, 3], [2, 0], [3, 1]])
top_vals: Float[Array, "3 2"] = jnp.take_along_axis(vals, top_idx, axis=1)


# === CLS token extraction pattern (BERT) ===

def extract_cls_token(
    sequence_output: Float[Array, "batch seq dim"],
) -> Float[Array, "batch dim"]:
    """Extract [CLS] token (position 0) for classification."""
    return sequence_output[:, 0]


# === Last token selection pattern (causal LMs) ===

def extract_last_token(
    sequence_output: Float[Array, "batch seq dim"],
) -> Float[Array, "batch 1 dim"]:
    """Extract last token for next-token prediction."""
    return sequence_output[:, -1:, :]


# === Embedding lookup pattern ===

def embed_tokens(
    token_ids: Int[Array, "batch seq"],
    embedding_table: Float[Array, "vocab dim"],
) -> Float[Array, "batch seq dim"]:
    """Look up token embeddings."""
    return jnp.take(embedding_table, token_ids, axis=0)


assert gathered.shape == (3, 5)
assert top_vals.shape == (3, 2)

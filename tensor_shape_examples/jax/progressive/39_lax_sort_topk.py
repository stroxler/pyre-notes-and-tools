"""Progressive demo 39: Sorting and top-k.

New operations:
  jax.lax.sort, jax.lax.top_k

Shape rules:
  sort(x):        same shape, sorted
  top_k(x, k):    returns (values: (..., k), indices: (..., k))

Used in: MoE expert selection (top-k gating), beam search, top-k sampling.
"""

import jax
import jax.numpy as jnp
import jax.lax as lax
from jaxtyping import Array, Float, Int


x: Float[Array, "3 5"] = jnp.array([
    [3.0, 1.0, 4.0, 1.0, 5.0],
    [9.0, 2.0, 6.0, 5.0, 3.0],
    [5.0, 8.0, 9.0, 7.0, 1.0],
])


# === jax.lax.top_k: get top k values and their indices ===

# Top 3 per row
top_vals: Float[Array, "3 3"]
top_idx: Int[Array, "3 3"]
top_vals, top_idx = lax.top_k(x, k=3)

assert top_vals.shape == (3, 3)
assert top_idx.shape == (3, 3)


# === jnp.sort ===

sorted_x: Float[Array, "3 5"] = jnp.sort(x, axis=-1)
assert sorted_x.shape == (3, 5)

# argsort
sort_idx: Int[Array, "3 5"] = jnp.argsort(x, axis=-1)
assert sort_idx.shape == (3, 5)


# === MoE gating pattern (Mixtral) ===

def top_k_gating(
    router_logits: Float[Array, "tokens num_experts"],
    k: int = 2,
) -> tuple[Float[Array, "tokens k"], Int[Array, "tokens k"]]:
    """Select top-k experts per token with softmax weights."""
    # Get top-k expert indices and logits
    top_logits, top_indices = lax.top_k(router_logits, k=k)
    # Softmax over selected experts only
    top_weights = jax.nn.softmax(top_logits, axis=-1)
    return top_weights, top_indices


# === Beam search pattern ===

def beam_step(
    log_probs: Float[Array, "batch*beam vocab"],
    beam_size: int,
) -> tuple[Float[Array, "batch*beam"], Int[Array, "batch*beam"]]:
    """Select top beam_size candidates from log probabilities."""
    # Flatten and take top-k across entire vocab for each beam
    flat_probs = log_probs.reshape(-1, log_probs.shape[-1])
    top_scores, top_indices = lax.top_k(flat_probs, k=beam_size)
    return top_scores, top_indices

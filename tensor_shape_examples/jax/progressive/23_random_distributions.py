"""Progressive demo 23: Discrete distributions and shuffling.

New operations:
  jax.random.bernoulli, jax.random.categorical,
  jax.random.choice, jax.random.permutation

Used in: dropout, sampling from language models, data augmentation.
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Float, Int, Bool


key = jax.random.PRNGKey(0)
k1, k2, k3, k4 = jax.random.split(key, 4)


# === Bernoulli: coin flips ===

# Probability p=0.5 (default), shape (3, 4)
flips: Bool[Array, "3 4"] = jax.random.bernoulli(k1, p=0.5, shape=(3, 4))


# === Categorical: sample from logits ===

# Sample from a distribution over 5 categories
logits: Float[Array, "2 5"] = jnp.array([
    [1.0, 2.0, 0.5, 0.1, 0.3],
    [0.1, 0.2, 3.0, 0.5, 0.1],
])

# One sample per row: (2, 5) → (2,)
samples: Int[Array, "2"] = jax.random.categorical(k2, logits, axis=-1)


# === Choice: sample from array ===

pool: Float[Array, "10"] = jnp.arange(10.0)

# Sample 3 without replacement
chosen: Float[Array, "3"] = jax.random.choice(k3, pool, shape=(3,), replace=False)


# === Permutation: random shuffle ===

perm: Int[Array, "10"] = jax.random.permutation(k4, 10)

# Shuffle an array
arr: Float[Array, "10"] = jnp.arange(10.0)
shuffled: Float[Array, "10"] = jax.random.permutation(k4, arr)


# === Language model sampling pattern ===

def sample_token(
    key: jax.Array,
    logits: Float[Array, "vocab"],
    temperature: float = 1.0,
) -> Int[Array, ""]:
    """Sample a single token from logits with temperature."""
    scaled_logits = logits / temperature
    return jax.random.categorical(key, scaled_logits)


# === Top-k sampling pattern ===

def top_k_sample(
    key: jax.Array,
    logits: Float[Array, "vocab"],
    k: int,
) -> Int[Array, ""]:
    """Sample from top-k logits only."""
    top_k_vals, top_k_idx = jax.lax.top_k(logits, k)
    sampled_idx = jax.random.categorical(key, top_k_vals)
    return top_k_idx[sampled_idx]


assert flips.shape == (3, 4)
assert samples.shape == (2,)
assert chosen.shape == (3,)
assert perm.shape == (10,)

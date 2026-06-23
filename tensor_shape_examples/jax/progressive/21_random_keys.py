"""Progressive demo 21: JAX random key management.

New operations:
  jax.random.PRNGKey, jax.random.key,
  jax.random.split, jax.random.fold_in

JAX uses a stateless PRNG system: no global random state.
Every random operation takes an explicit key, and you must split
keys to get independent streams.
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Float


# === Creating keys ===

key = jax.random.PRNGKey(0)      # shape: (2,) for default impl
key2 = jax.random.PRNGKey(42)


# === Splitting keys ===
# split(key) → two new keys; the original should not be reused.

key, subkey = jax.random.split(key)

# Split into multiple keys
key, *subkeys = jax.random.split(key, num=5)  # 1 for continuation + 4 for use


# === fold_in: deterministic key derivation ===
# Useful for deriving per-layer or per-step keys

layer_key = jax.random.fold_in(key, 0)  # key for layer 0
layer_key2 = jax.random.fold_in(key, 1)  # key for layer 1


# === Pattern: managing keys in a training loop ===

def training_step_keys(key: jax.Array, num_layers: int) -> list[jax.Array]:
    """Generate one dropout key per layer."""
    return [jax.random.fold_in(key, i) for i in range(num_layers)]


# === Pattern: key splitting for init vs. train ===

def init_model(seed: int) -> tuple[jax.Array, jax.Array]:
    """Split seed into param init key and training key."""
    key = jax.random.PRNGKey(seed)
    init_key, train_key = jax.random.split(key)
    return init_key, train_key

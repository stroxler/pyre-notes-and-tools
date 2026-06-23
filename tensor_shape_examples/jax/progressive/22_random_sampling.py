"""Progressive demo 22: Random sampling.

New operations:
  jax.random.normal, jax.random.uniform, jax.random.randint,
  jax.random.truncated_normal

All return arrays of the requested shape.
Used in: weight initialization, noise injection, dropout masks.
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Float, Int


key = jax.random.PRNGKey(0)

# === Normal distribution ===

k1, k2, k3, k4 = jax.random.split(key, 4)

# Standard normal: shape (3, 4)
normal: Float[Array, "3 4"] = jax.random.normal(k1, shape=(3, 4))

# With dtype
normal_f16: Float[Array, "3 4"] = jax.random.normal(k1, shape=(3, 4), dtype=jnp.float16)


# === Uniform distribution ===

# Uniform in [0, 1): shape (2, 5)
uniform: Float[Array, "2 5"] = jax.random.uniform(k2, shape=(2, 5))

# Uniform in [low, high)
uniform_range: Float[Array, "2 5"] = jax.random.uniform(
    k2, shape=(2, 5), minval=-1.0, maxval=1.0
)


# === Random integers ===

# Integers in [0, 10): shape (3,)
ints: Int[Array, "3"] = jax.random.randint(k3, shape=(3,), minval=0, maxval=10)


# === Truncated normal (for weight init) ===

trunc: Float[Array, "3 4"] = jax.random.truncated_normal(
    k4, lower=-2.0, upper=2.0, shape=(3, 4)
)


# === Weight initialization pattern ===

def init_linear_weights(
    key: jax.Array,
    in_features: int,
    out_features: int,
) -> tuple[Float[Array, "in_features out_features"], Float[Array, "out_features"]]:
    """Xavier/Glorot uniform initialization."""
    k1, k2 = jax.random.split(key)
    limit = jnp.sqrt(6.0 / (in_features + out_features))
    weight = jax.random.uniform(k1, (in_features, out_features), minval=-limit, maxval=limit)
    bias = jnp.zeros(out_features)
    return weight, bias


# === Dropout mask pattern ===

def make_dropout_mask(
    key: jax.Array,
    shape: tuple[int, ...],
    rate: float = 0.1,
) -> Float[Array, "..."]:
    """Create a dropout mask (1 = keep, 0 = drop)."""
    keep_rate = 1.0 - rate
    mask = jax.random.bernoulli(key, keep_rate, shape)
    return mask / keep_rate  # scale to maintain expected value


assert normal.shape == (3, 4)
assert uniform.shape == (2, 5)
assert ints.shape == (3,)

"""Progressive demo 24: Weight initializers.

New operations:
  jax.nn.initializers.glorot_uniform, glorot_normal,
  he_normal, lecun_normal, orthogonal,
  zeros, ones, constant, normal, uniform

Each initializer is a function that returns an init function:
  init_fn(key, shape, dtype) → Array

Used in: every model that manually initializes parameters.
"""

import jax
import jax.numpy as jnp
from jax.nn.initializers import (
    glorot_uniform, glorot_normal,
    he_normal, lecun_normal,
    orthogonal, zeros, ones, normal, uniform,
)
from jaxtyping import Array, Float


key = jax.random.PRNGKey(0)
k1, k2, k3, k4, k5 = jax.random.split(key, 5)


# === Xavier/Glorot (default for Dense layers) ===

w_glorot_u: Float[Array, "64 128"] = glorot_uniform()(k1, (64, 128))
w_glorot_n: Float[Array, "64 128"] = glorot_normal()(k2, (64, 128))


# === He/Kaiming (for ReLU networks) ===

w_he: Float[Array, "64 128"] = he_normal()(k3, (64, 128))


# === LeCun (for SELU) ===

w_lecun: Float[Array, "64 128"] = lecun_normal()(k4, (64, 128))


# === Orthogonal (for RNNs) ===

w_orth: Float[Array, "64 64"] = orthogonal()(k5, (64, 64))


# === Constant initializers ===

w_zeros: Float[Array, "64 128"] = zeros(k1, (64, 128))
w_ones: Float[Array, "64 128"] = ones(k1, (64, 128))


# === Custom normal/uniform ===

w_normal: Float[Array, "64 128"] = normal(stddev=0.02)(k1, (64, 128))
w_uniform: Float[Array, "64 128"] = uniform(scale=0.1)(k2, (64, 128))


# === Pattern: initialize a simple MLP ===

def init_mlp(
    key: jax.Array,
    layer_sizes: list[int],
) -> list[tuple[Float[Array, "..."], Float[Array, "..."]]]:
    """Initialize MLP parameters with Glorot uniform + zero biases."""
    params = []
    for i in range(len(layer_sizes) - 1):
        key, k = jax.random.split(key)
        w = glorot_uniform()(k, (layer_sizes[i], layer_sizes[i + 1]))
        b = jnp.zeros(layer_sizes[i + 1])
        params.append((w, b))
    return params


params = init_mlp(key, [784, 256, 128, 10])
assert params[0][0].shape == (784, 256)
assert params[0][1].shape == (256,)
assert params[2][0].shape == (128, 10)

"""Progressive demo 19: Norms and variance.

New operations:
  jnp.linalg.norm, jnp.var, jnp.std

Used in: LayerNorm implementation, weight normalization, gradient clipping.
"""

import jax.numpy as jnp
from jaxtyping import Array, Float


x: Float[Array, "3 4"] = jnp.arange(12.0).reshape(3, 4)

# === Variance and standard deviation ===

# Global
var_all: Float[Array, ""] = jnp.var(x)
std_all: Float[Array, ""] = jnp.std(x)

# Along axis
row_var: Float[Array, "3"] = jnp.var(x, axis=1)
row_std: Float[Array, "3"] = jnp.std(x, axis=1)

# With keepdims
row_var_kd: Float[Array, "3 1"] = jnp.var(x, axis=1, keepdims=True)


# === Vector/matrix norms ===

v: Float[Array, "4"] = jnp.array([1.0, 2.0, 3.0, 4.0])
l2_norm: Float[Array, ""] = jnp.linalg.norm(v)        # L2 norm (default)
l1_norm: Float[Array, ""] = jnp.linalg.norm(v, ord=1)  # L1 norm

# Norm along axis
row_norms: Float[Array, "3"] = jnp.linalg.norm(x, axis=1)


# === LayerNorm from primitives ===

def layer_norm(
    x: Float[Array, "batch seq dim"],
    weight: Float[Array, "dim"],
    bias: Float[Array, "dim"],
    eps: float = 1e-5,
) -> Float[Array, "batch seq dim"]:
    """Layer normalization from basic operations."""
    mean = jnp.mean(x, axis=-1, keepdims=True)
    var = jnp.var(x, axis=-1, keepdims=True)
    x_norm = (x - mean) / jnp.sqrt(var + eps)
    return x_norm * weight + bias


# === Gradient clipping by norm ===

def clip_grad_norm(
    grad: Float[Array, "..."],
    max_norm: float,
) -> Float[Array, "..."]:
    """Clip gradient to max_norm."""
    grad_norm = jnp.linalg.norm(jnp.ravel(grad))
    scale = jnp.minimum(1.0, max_norm / (grad_norm + 1e-6))
    return grad * scale


assert row_var.shape == (3,)
assert l2_norm.shape == ()
assert row_norms.shape == (3,)

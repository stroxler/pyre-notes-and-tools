"""Progressive demo 36: lax conditional execution.

New operations:
  jax.lax.cond, jax.lax.switch

These replace Python if/else inside jit-compiled code.
Both branches must produce the same output shape.

Used in: conditional architectures, training vs. eval mode.
"""

import jax
import jax.numpy as jnp
import jax.lax as lax
from jaxtyping import Array, Bool, Float


# === lax.cond: if/else in JIT ===

def maybe_relu(
    x: Float[Array, "batch dim"],
    use_relu: Bool[Array, ""],
) -> Float[Array, "batch dim"]:
    """Conditionally apply ReLU (both branches same output shape)."""
    return lax.cond(
        use_relu,
        lambda x: jax.nn.relu(x),   # true branch
        lambda x: x,                 # false branch
        x,
    )

x = jnp.array([[-1.0, 2.0], [3.0, -4.0]])
result_relu = maybe_relu(x, jnp.bool_(True))
result_id = maybe_relu(x, jnp.bool_(False))
assert result_relu.shape == (2, 2)


# === lax.switch: multi-way branch ===

def apply_activation(
    x: Float[Array, "batch dim"],
    index: int,
) -> Float[Array, "batch dim"]:
    """Choose activation by index: 0=relu, 1=gelu, 2=silu, 3=identity."""
    return lax.switch(
        index,
        [
            lambda x: jax.nn.relu(x),
            lambda x: jax.nn.gelu(x),
            lambda x: jax.nn.silu(x),
            lambda x: x,
        ],
        x,
    )


# === Pattern: train/eval mode ===

def batch_norm_forward(
    x: Float[Array, "batch channels"],
    mean: Float[Array, "channels"],
    var: Float[Array, "channels"],
    gamma: Float[Array, "channels"],
    beta: Float[Array, "channels"],
    is_training: Bool[Array, ""],
) -> Float[Array, "batch channels"]:
    """BatchNorm with train/eval mode via lax.cond."""
    def train_branch(x):
        batch_mean = jnp.mean(x, axis=0)
        batch_var = jnp.var(x, axis=0)
        return gamma * (x - batch_mean) / jnp.sqrt(batch_var + 1e-5) + beta

    def eval_branch(x):
        return gamma * (x - mean) / jnp.sqrt(var + 1e-5) + beta

    return lax.cond(is_training, train_branch, eval_branch, x)

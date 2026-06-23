"""Progressive demo 29: JIT compilation.

New operations:
  jax.jit

jit traces a function and compiles it with XLA for fast execution.
The key constraint: traced code must have static control flow shapes.

Note: jit doesn't change tensor shapes — it's about performance.
But shape annotations must be compatible with tracing.
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Float


# === Basic jit ===

@jax.jit
def add_scaled(
    x: Float[Array, "batch dim"],
    y: Float[Array, "batch dim"],
    scale: float,
) -> Float[Array, "batch dim"]:
    return x + scale * y


key = jax.random.PRNGKey(0)
k1, k2 = jax.random.split(key)
x = jax.random.normal(k1, (4, 8))
y = jax.random.normal(k2, (4, 8))
result = add_scaled(x, y, 0.5)
assert result.shape == (4, 8)


# === jit with static_argnums ===
# Arguments that affect control flow or shapes must be marked static

@jax.jit
def mlp_forward(
    x: Float[Array, "batch features"],
    params: list[tuple[Float[Array, "..."], Float[Array, "..."]]],
) -> Float[Array, "batch output"]:
    """Forward pass through MLP with jit."""
    for w, b in params[:-1]:
        x = jax.nn.relu(x @ w + b)
    w, b = params[-1]
    return x @ w + b


# === Pattern: jitted training step ===

@jax.jit
def train_step(
    params: dict,
    x: Float[Array, "batch features"],
    y: Float[Array, "batch targets"],
    learning_rate: float,
) -> tuple[Float[Array, ""], dict]:
    """Single training step: forward + backward + update."""
    def loss_fn(params):
        pred = params["w"] @ x.T + params["b"][:, None]
        return jnp.mean((pred.T - y) ** 2)

    loss, grads = jax.value_and_grad(loss_fn)(params)
    new_params = jax.tree.map(lambda p, g: p - learning_rate * g, params, grads)
    return loss, new_params

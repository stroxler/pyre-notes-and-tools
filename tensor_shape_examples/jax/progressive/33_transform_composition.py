"""Progressive demo 33: Composing transforms.

No new operations — this shows how jit, grad, and vmap compose,
which is the core of idiomatic JAX.
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Float


# === jit(grad(f)): compiled gradient computation ===

def loss_fn(
    w: Float[Array, "in_dim out_dim"],
    b: Float[Array, "out_dim"],
    x: Float[Array, "batch in_dim"],
    y: Float[Array, "batch out_dim"],
) -> Float[Array, ""]:
    pred = x @ w + b
    return jnp.mean(jnp.sum((pred - y) ** 2, axis=-1))

# Compose: compiled gradient function
fast_grad = jax.jit(jax.grad(loss_fn, argnums=(0, 1)))


# === vmap(grad(f)): per-example gradients, then average ===

def per_example_loss(
    w: Float[Array, "in_dim out_dim"],
    x_single: Float[Array, "in_dim"],
    y_single: Float[Array, "out_dim"],
) -> Float[Array, ""]:
    pred = x_single @ w
    return jnp.sum((pred - y_single) ** 2)

# Per-example gradients
per_ex_grad_fn = jax.vmap(jax.grad(per_example_loss), in_axes=(None, 0, 0))


# === Full training loop composition ===

def init(key, in_dim, out_dim):
    k1, k2 = jax.random.split(key)
    return {
        "w": jax.random.normal(k1, (in_dim, out_dim)) * 0.01,
        "b": jnp.zeros(out_dim),
    }

def predict(params, x):
    return x @ params["w"] + params["b"]

def loss(params, x, y):
    return jnp.mean(jnp.sum((predict(params, x) - y) ** 2, axis=-1))

@jax.jit
def train_step(params, x, y, lr=0.01):
    """jit(value_and_grad(loss)) + pytree update — the canonical pattern."""
    l, grads = jax.value_and_grad(loss)(params, x, y)
    params = jax.tree.map(lambda p, g: p - lr * g, params, grads)
    return l, params

# Run it
key = jax.random.PRNGKey(0)
params = init(key, 4, 2)
k1, k2 = jax.random.split(key)
x = jax.random.normal(k1, (32, 4))
y = jax.random.normal(k2, (32, 2))

for step in range(5):
    l, params = train_step(params, x, y)

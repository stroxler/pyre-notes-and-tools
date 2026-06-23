"""Progressive demo 30: Automatic differentiation.

New operations:
  jax.grad, jax.value_and_grad, jax.jacfwd, jax.jacrev

Shape rules:
  grad(f)(x):           returns gradient with same shape as x
  value_and_grad(f)(x): returns (f(x), grad_x) — value + gradient
  jacfwd/jacrev:        returns Jacobian matrix

Used in: every training loop.
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Float


# === Basic grad ===

def scalar_loss(
    w: Float[Array, "dim"],
    x: Float[Array, "batch dim"],
    y: Float[Array, "batch"],
) -> Float[Array, ""]:
    """Simple linear regression loss."""
    pred = x @ w
    return jnp.mean((pred - y) ** 2)


key = jax.random.PRNGKey(0)
k1, k2, k3 = jax.random.split(key, 3)
w = jax.random.normal(k1, (4,))
x = jax.random.normal(k2, (8, 4))
y = jax.random.normal(k3, (8,))

# grad returns the gradient w.r.t. first argument
grad_w: Float[Array, "4"] = jax.grad(scalar_loss)(w, x, y)
assert grad_w.shape == w.shape


# === value_and_grad: get both loss and gradient ===

loss_val, grad_w2 = jax.value_and_grad(scalar_loss)(w, x, y)
assert grad_w2.shape == w.shape


# === grad w.r.t. specific arguments ===

def loss_with_bias(
    w: Float[Array, "dim"],
    b: Float[Array, ""],
    x: Float[Array, "batch dim"],
    y: Float[Array, "batch"],
) -> Float[Array, ""]:
    pred = x @ w + b
    return jnp.mean((pred - y) ** 2)

# Gradient w.r.t. both w (arg 0) and b (arg 1)
grad_fn = jax.grad(loss_with_bias, argnums=(0, 1))
b = jnp.float32(0.0)
dw, db = grad_fn(w, b, x, y)
assert dw.shape == (4,)
assert db.shape == ()


# === Gradient of a pytree ===

def pytree_loss(
    params: dict[str, Float[Array, "..."]],
    x: Float[Array, "batch dim"],
    y: Float[Array, "batch"],
) -> Float[Array, ""]:
    pred = x @ params["weight"] + params["bias"]
    return jnp.mean((pred - y) ** 2)

params = {"weight": w, "bias": b}
grads = jax.grad(pytree_loss)(params, x, y)
# grads has the same tree structure as params
assert grads["weight"].shape == (4,)
assert grads["bias"].shape == ()


# === Training step pattern ===

def sgd_step(
    params: dict,
    x: Float[Array, "batch dim"],
    y: Float[Array, "batch"],
    lr: float = 0.01,
) -> tuple[Float[Array, ""], dict]:
    loss, grads = jax.value_and_grad(pytree_loss)(params, x, y)
    new_params = jax.tree.map(lambda p, g: p - lr * g, params, grads)
    return loss, new_params

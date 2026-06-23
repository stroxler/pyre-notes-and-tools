"""Progressive demo 31: Vectorized map (vmap).

New operations:
  jax.vmap

Shape rules:
  vmap adds a batch dimension to a function that operates on unbatched inputs.
  f: (M, K) → (M, N)
  vmap(f): (B, M, K) → (B, M, N)

in_axes and out_axes control which axes are mapped over.

Used in: per-example gradients, batching over non-batched code.
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Float


# === Basic vmap: auto-batching ===

def single_forward(
    x: Float[Array, "dim"],
    w: Float[Array, "dim hidden"],
    b: Float[Array, "hidden"],
) -> Float[Array, "hidden"]:
    """Forward pass for a single example (no batch dim)."""
    return jax.nn.relu(x @ w + b)


# Vectorize over first argument (x), keep w and b fixed
batched_forward = jax.vmap(single_forward, in_axes=(0, None, None))

key = jax.random.PRNGKey(0)
k1, k2 = jax.random.split(key)
x_batch = jax.random.normal(k1, (8, 4))     # (batch=8, dim=4)
w = jax.random.normal(k2, (4, 16))          # (dim=4, hidden=16)
b = jnp.zeros(16)                            # (hidden=16,)

# Result: (8, 16) — batch dim added automatically
result: Float[Array, "8 16"] = batched_forward(x_batch, w, b)
assert result.shape == (8, 16)


# === in_axes: control which args are batched ===

def dot_product(
    a: Float[Array, "dim"],
    b: Float[Array, "dim"],
) -> Float[Array, ""]:
    return jnp.sum(a * b)

# Both args batched
batched_dot = jax.vmap(dot_product, in_axes=(0, 0))
a_batch = jax.random.normal(k1, (5, 3))
b_batch = jax.random.normal(k2, (5, 3))
dots: Float[Array, "5"] = batched_dot(a_batch, b_batch)
assert dots.shape == (5,)


# === Per-example gradients (unique to JAX) ===

def per_example_loss(
    params: dict,
    x: Float[Array, "dim"],
    y: Float[Array, ""],
) -> Float[Array, ""]:
    pred = x @ params["w"] + params["b"]
    return (pred - y) ** 2

params = {
    "w": jax.random.normal(k1, (4,)),
    "b": jnp.float32(0.0),
}
x_batch = jax.random.normal(k1, (8, 4))
y_batch = jax.random.normal(k2, (8,))

# Per-example gradients: vmap over grad
per_example_grads = jax.vmap(
    jax.grad(per_example_loss),
    in_axes=(None, 0, 0),  # params shared, x and y batched
)(params, x_batch, y_batch)

# Each gradient has shape matching params, but with batch dim prepended
assert per_example_grads["w"].shape == (8, 4)
assert per_example_grads["b"].shape == (8,)


# === Nested vmap for multi-head attention ===

def single_head_attention(
    q: Float[Array, "seq_q dim"],
    k: Float[Array, "seq_k dim"],
    v: Float[Array, "seq_k dim"],
) -> Float[Array, "seq_q dim"]:
    """Single-head attention without batch or head dims."""
    scores = q @ k.T / jnp.sqrt(jnp.float32(q.shape[-1]))
    weights = jax.nn.softmax(scores, axis=-1)
    return weights @ v

# vmap over heads, then over batch
multi_head_attention = jax.vmap(  # batch dim
    jax.vmap(single_head_attention, in_axes=(0, 0, 0)),  # head dim
    in_axes=(0, 0, 0),
)

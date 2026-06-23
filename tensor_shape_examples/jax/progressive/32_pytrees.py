"""Progressive demo 32: Pytree manipulation.

New operations:
  jax.tree.map, jax.tree.leaves, jax.tree.structure,
  jax.tree.flatten, jax.tree.unflatten

Pytrees are JAX's way of working with nested parameter structures.
Every model's parameters are a pytree (nested dicts/lists of arrays).

Used in: parameter updates, gradient clipping, model initialization.
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Float


# === Pytree basics ===

# A simple parameter tree (dict of arrays)
params = {
    "layer1": {
        "weight": jnp.ones((4, 8)),
        "bias": jnp.zeros(8),
    },
    "layer2": {
        "weight": jnp.ones((8, 2)),
        "bias": jnp.zeros(2),
    },
}


# === tree.map: apply a function to every leaf ===

# Scale all parameters by 0.1
scaled_params = jax.tree.map(lambda x: x * 0.1, params)
assert scaled_params["layer1"]["weight"].shape == (4, 8)

# SGD update: params = params - lr * grads
def sgd_update(params, grads, lr=0.01):
    return jax.tree.map(lambda p, g: p - lr * g, params, grads)


# === tree.leaves: get flat list of all arrays ===

leaves = jax.tree.leaves(params)
assert len(leaves) == 4  # 2 weights + 2 biases

# Total parameter count
total_params = sum(x.size for x in jax.tree.leaves(params))
assert total_params == 4*8 + 8 + 8*2 + 2  # = 50


# === tree.structure: get the tree structure without values ===

structure = jax.tree.structure(params)


# === tree.flatten / tree.unflatten: roundtrip ===

flat_leaves, tree_def = jax.tree.flatten(params)
reconstructed = jax.tree.unflatten(tree_def, flat_leaves)
assert reconstructed["layer1"]["weight"].shape == (4, 8)


# === Gradient clipping on a pytree ===

def clip_grads_global_norm(grads, max_norm: float):
    """Clip gradient pytree by global norm."""
    leaves = jax.tree.leaves(grads)
    total_norm = jnp.sqrt(sum(jnp.sum(g ** 2) for g in leaves))
    scale = jnp.minimum(1.0, max_norm / (total_norm + 1e-6))
    return jax.tree.map(lambda g: g * scale, grads)


# === Pattern: initialize and update model ===

def init_params(key):
    k1, k2 = jax.random.split(key)
    return {
        "w": jax.random.normal(k1, (4, 8)),
        "b": jnp.zeros(8),
    }

def forward(params, x):
    return jax.nn.relu(x @ params["w"] + params["b"])

def loss_fn(params, x, y):
    pred = forward(params, x)
    return jnp.mean((pred - y) ** 2)

@jax.jit
def train_step(params, x, y, lr=0.01):
    loss, grads = jax.value_and_grad(loss_fn)(params, x, y)
    grads = clip_grads_global_norm(grads, max_norm=1.0)
    params = jax.tree.map(lambda p, g: p - lr * g, params, grads)
    return loss, params

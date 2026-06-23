"""Progressive demo 50: Complete training step.

Assembles: value_and_grad, tree.map, jit, and optionally optax.

This ties everything together into the canonical JAX training pattern:
  1. Forward pass (compute loss)
  2. Backward pass (compute gradients via value_and_grad)
  3. Update parameters (SGD, Adam, or optax)
  4. Wrap in jit for performance
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Float, Int


# === Simple MLP for demonstration ===

def init_params(key: jax.Array, layer_sizes: list[int]) -> list[dict]:
    """Initialize MLP parameters."""
    params = []
    for i in range(len(layer_sizes) - 1):
        key, k = jax.random.split(key)
        fan_in, fan_out = layer_sizes[i], layer_sizes[i + 1]
        scale = jnp.sqrt(2.0 / fan_in)
        params.append({
            "w": jax.random.normal(k, (fan_in, fan_out)) * scale,
            "b": jnp.zeros(fan_out),
        })
    return params


def forward(
    params: list[dict],
    x: Float[Array, "batch features"],
) -> Float[Array, "batch output"]:
    """MLP forward pass."""
    for layer in params[:-1]:
        x = jax.nn.relu(x @ layer["w"] + layer["b"])
    last = params[-1]
    return x @ last["w"] + last["b"]


def loss_fn(
    params: list[dict],
    x: Float[Array, "batch features"],
    y: Int[Array, "batch"],
    num_classes: int,
) -> Float[Array, ""]:
    """Cross-entropy loss."""
    logits = forward(params, x)
    log_probs = jax.nn.log_softmax(logits, axis=-1)
    targets = jax.nn.one_hot(y, num_classes)
    return -jnp.mean(jnp.sum(targets * log_probs, axis=-1))


# === SGD training step ===

@jax.jit
def sgd_train_step(
    params: list[dict],
    x: Float[Array, "batch features"],
    y: Int[Array, "batch"],
    lr: float = 0.01,
) -> tuple[Float[Array, ""], list[dict]]:
    """Single SGD training step with gradient clipping."""
    loss, grads = jax.value_and_grad(loss_fn)(params, x, y, num_classes=10)

    # Gradient clipping by global norm
    leaves = jax.tree.leaves(grads)
    global_norm = jnp.sqrt(sum(jnp.sum(g ** 2) for g in leaves))
    clip_scale = jnp.minimum(1.0, 1.0 / (global_norm + 1e-6))
    grads = jax.tree.map(lambda g: g * clip_scale, grads)

    # SGD update
    params = jax.tree.map(lambda p, g: p - lr * g, params, grads)
    return loss, params


# === Adam training step (manual, no optax) ===

def init_adam_state(params):
    """Initialize Adam optimizer state."""
    m = jax.tree.map(jnp.zeros_like, params)  # first moment
    v = jax.tree.map(jnp.zeros_like, params)  # second moment
    return m, v


@jax.jit
def adam_train_step(
    params: list[dict],
    m: list[dict],
    v: list[dict],
    x: Float[Array, "batch features"],
    y: Int[Array, "batch"],
    step: int,
    lr: float = 0.001,
    beta1: float = 0.9,
    beta2: float = 0.999,
    eps: float = 1e-8,
) -> tuple[Float[Array, ""], list[dict], list[dict], list[dict]]:
    """Single Adam training step."""
    loss, grads = jax.value_and_grad(loss_fn)(params, x, y, num_classes=10)

    # Update moments
    m = jax.tree.map(lambda mi, gi: beta1 * mi + (1 - beta1) * gi, m, grads)
    v = jax.tree.map(lambda vi, gi: beta2 * vi + (1 - beta2) * gi ** 2, v, grads)

    # Bias correction
    m_hat = jax.tree.map(lambda mi: mi / (1 - beta1 ** (step + 1)), m)
    v_hat = jax.tree.map(lambda vi: vi / (1 - beta2 ** (step + 1)), v)

    # Update params
    params = jax.tree.map(
        lambda p, mh, vh: p - lr * mh / (jnp.sqrt(vh) + eps),
        params, m_hat, v_hat,
    )
    return loss, params, m, v


# === Run training ===

key = jax.random.PRNGKey(42)
k1, k2, k3 = jax.random.split(key, 3)

params = init_params(k1, [784, 256, 128, 10])
x = jax.random.normal(k2, (32, 784))
y = jax.random.randint(k3, (32,), 0, 10)

# SGD
for step in range(3):
    loss, params = sgd_train_step(params, x, y)
    print(f"Step {step}: loss = {loss:.4f}")

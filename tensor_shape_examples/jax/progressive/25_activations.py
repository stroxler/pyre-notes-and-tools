"""Progressive demo 25: Activation functions.

New operations:
  jax.nn.relu, jax.nn.gelu, jax.nn.silu (swish), jax.nn.elu,
  jax.nn.leaky_relu, jax.nn.relu6

All elementwise: shape in == shape out.
"""

import jax.nn as nn
import jax.numpy as jnp
from jaxtyping import Array, Float


x: Float[Array, "3 4"] = jnp.array([
    [-1.0, 0.0, 1.0, 2.0],
    [3.0, -2.0, 0.5, -0.5],
    [0.1, -0.1, 4.0, -3.0],
])

# === Standard activations (all preserve shape) ===

r: Float[Array, "3 4"] = nn.relu(x)
g: Float[Array, "3 4"] = nn.gelu(x)
s: Float[Array, "3 4"] = nn.silu(x)        # also known as swish
e: Float[Array, "3 4"] = nn.elu(x)
lr: Float[Array, "3 4"] = nn.leaky_relu(x, negative_slope=0.01)
r6: Float[Array, "3 4"] = nn.relu6(x)       # clipped relu for MobileNet

# GELU with approximate=True (matches GPT-2)
g_approx: Float[Array, "3 4"] = nn.gelu(x, approximate=True)


# === Activation in a feed-forward block ===

def ffn_block(
    x: Float[Array, "batch seq d_model"],
    w1: Float[Array, "d_model d_ff"],
    w2: Float[Array, "d_ff d_model"],
) -> Float[Array, "batch seq d_model"]:
    """Feed-forward block: Dense → GELU → Dense."""
    h = nn.gelu(x @ w1)
    return h @ w2


# === SwiGLU pattern (LLaMA, Gemma) ===

def swiglu(
    x: Float[Array, "batch seq dim"],
    w_gate: Float[Array, "dim hidden"],
    w_up: Float[Array, "dim hidden"],
    w_down: Float[Array, "hidden dim"],
) -> Float[Array, "batch seq dim"]:
    """SwiGLU activation: silu(xW_gate) * (xW_up) then project down."""
    gate = nn.silu(x @ w_gate)
    up = x @ w_up
    return (gate * up) @ w_down


assert r.shape == (3, 4)
assert g.shape == (3, 4)
assert s.shape == (3, 4)

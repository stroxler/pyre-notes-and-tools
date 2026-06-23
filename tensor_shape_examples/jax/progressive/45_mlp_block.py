"""Progressive demo 45: MLP / Feed-forward block.

Assembles: matmul, activation, dropout mask.

The transformer feed-forward block: Dense → activation → Dense.
Variants: standard (ReLU/GELU), SwiGLU (LLaMA), GLU.
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Float


# === Standard FFN (GPT-2, BERT, ViT) ===

def ffn(
    x: Float[Array, "batch seq d_model"],
    w1: Float[Array, "d_model d_ff"],
    b1: Float[Array, "d_ff"],
    w2: Float[Array, "d_ff d_model"],
    b2: Float[Array, "d_model"],
) -> Float[Array, "batch seq d_model"]:
    """Feed-forward network: Dense → GELU → Dense."""
    h = jax.nn.gelu(x @ w1 + b1)
    return h @ w2 + b2


# === SwiGLU FFN (LLaMA, Gemma, Mixtral) ===

def swiglu_ffn(
    x: Float[Array, "batch seq d_model"],
    w_gate: Float[Array, "d_model d_ff"],
    w_up: Float[Array, "d_model d_ff"],
    w_down: Float[Array, "d_ff d_model"],
) -> Float[Array, "batch seq d_model"]:
    """SwiGLU: silu(x·W_gate) ⊙ (x·W_up) then project down.

    No bias (LLaMA convention).
    """
    return (jax.nn.silu(x @ w_gate) * (x @ w_up)) @ w_down


# === FFN with dropout ===

def ffn_with_dropout(
    x: Float[Array, "batch seq d_model"],
    w1: Float[Array, "d_model d_ff"],
    w2: Float[Array, "d_ff d_model"],
    key: jax.Array,
    dropout_rate: float = 0.1,
    training: bool = True,
) -> Float[Array, "batch seq d_model"]:
    """FFN with dropout (applied after each linear layer in training)."""
    h = jax.nn.gelu(x @ w1)
    if training:
        mask = jax.random.bernoulli(key, 1.0 - dropout_rate, h.shape)
        h = jnp.where(mask, h / (1.0 - dropout_rate), 0.0)
    return h @ w2


# Test
key = jax.random.PRNGKey(0)
keys = jax.random.split(key, 4)

batch, seq, d_model, d_ff = 2, 10, 64, 256
x = jax.random.normal(keys[0], (batch, seq, d_model))
w1 = jax.random.normal(keys[1], (d_model, d_ff)) * 0.01
b1 = jnp.zeros(d_ff)
w2 = jax.random.normal(keys[2], (d_ff, d_model)) * 0.01
b2 = jnp.zeros(d_model)

out = ffn(x, w1, b1, w2, b2)
assert out.shape == (2, 10, 64)

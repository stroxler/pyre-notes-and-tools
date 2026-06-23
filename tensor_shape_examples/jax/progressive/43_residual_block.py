"""Progressive demo 43: Residual block patterns.

Assembles: matmul, activation, normalization, addition.

Pre-norm vs. post-norm, with and without projection shortcut.
"""

import jax
import jax.numpy as jnp
from jaxtyping import Array, Float


# === Pre-norm residual (modern transformers: GPT-2, LLaMA) ===

def pre_norm_residual(
    x: Float[Array, "batch seq dim"],
    w1: Float[Array, "dim d_ff"],
    w2: Float[Array, "d_ff dim"],
    ln_scale: Float[Array, "dim"],
    ln_bias: Float[Array, "dim"],
) -> Float[Array, "batch seq dim"]:
    """Pre-norm: LayerNorm → sublayer → residual add."""
    # Normalize
    mean = jnp.mean(x, axis=-1, keepdims=True)
    var = jnp.var(x, axis=-1, keepdims=True)
    x_norm = ln_scale * (x - mean) / jnp.sqrt(var + 1e-5) + ln_bias
    # FFN sublayer
    h = jax.nn.gelu(x_norm @ w1)
    h = h @ w2
    # Residual
    return x + h


# === Post-norm residual (original Transformer, BERT) ===

def post_norm_residual(
    x: Float[Array, "batch seq dim"],
    w1: Float[Array, "dim d_ff"],
    w2: Float[Array, "d_ff dim"],
    ln_scale: Float[Array, "dim"],
    ln_bias: Float[Array, "dim"],
) -> Float[Array, "batch seq dim"]:
    """Post-norm: sublayer → residual add → LayerNorm."""
    h = jax.nn.gelu(x @ w1) @ w2
    x = x + h
    mean = jnp.mean(x, axis=-1, keepdims=True)
    var = jnp.var(x, axis=-1, keepdims=True)
    return ln_scale * (x - mean) / jnp.sqrt(var + 1e-5) + ln_bias


# === ResNet-style residual (vision) ===

def resnet_residual_block(
    x: Float[Array, "batch channels height width"],
    w1: Float[Array, "kh kw in_c mid_c"],
    w2: Float[Array, "kh kw mid_c out_c"],
    shortcut_w: Float[Array, "1 1 in_c out_c"] | None,
    bn1_params: tuple[Float[Array, "mid_c"], Float[Array, "mid_c"]],
    bn2_params: tuple[Float[Array, "out_c"], Float[Array, "out_c"]],
) -> Float[Array, "batch out_c height width"]:
    """ResNet basic block with optional projection shortcut."""
    import jax.lax as lax

    # Main path
    h = lax.conv_general_dilated(
        x, w1, (1, 1), "SAME", dimension_numbers=("NHWC", "HWIO", "NHWC")
    )
    gamma1, beta1 = bn1_params
    h_mean = jnp.mean(h, axis=(0, 1, 2), keepdims=True)
    h = gamma1[None, None, None, :] * (h - h_mean) + beta1[None, None, None, :]
    h = jax.nn.relu(h)

    h = lax.conv_general_dilated(
        h, w2, (1, 1), "SAME", dimension_numbers=("NHWC", "HWIO", "NHWC")
    )
    gamma2, beta2 = bn2_params
    h_mean = jnp.mean(h, axis=(0, 1, 2), keepdims=True)
    h = gamma2[None, None, None, :] * (h - h_mean) + beta2[None, None, None, :]

    # Shortcut (identity or projection)
    if shortcut_w is not None:
        x = lax.conv_general_dilated(
            x, shortcut_w, (1, 1), "SAME", dimension_numbers=("NHWC", "HWIO", "NHWC")
        )

    return jax.nn.relu(h + x)

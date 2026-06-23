"""Progressive demo 44: Conv → BatchNorm → ReLU pattern.

Assembles: lax.conv_general_dilated, mean, var, sqrt, relu.

The canonical vision network building block (ResNet, DenseNet, MobileNet, etc.).
"""

import jax
import jax.numpy as jnp
import jax.lax as lax
from jaxtyping import Array, Float


def conv_bn_relu(
    x: Float[Array, "batch height width in_channels"],
    conv_kernel: Float[Array, "kh kw in_channels out_channels"],
    bn_gamma: Float[Array, "out_channels"],
    bn_beta: Float[Array, "out_channels"],
    stride: tuple[int, int] = (1, 1),
    eps: float = 1e-5,
) -> Float[Array, "batch height2 width2 out_channels"]:
    """Conv2d → BatchNorm → ReLU (NHWC format)."""
    # Convolution
    h = lax.conv_general_dilated(
        x,
        conv_kernel,
        window_strides=stride,
        padding="SAME",
        dimension_numbers=("NHWC", "HWIO", "NHWC"),
    )

    # Batch normalization (training mode: use batch statistics)
    mean = jnp.mean(h, axis=(0, 1, 2))           # (out_channels,)
    var = jnp.var(h, axis=(0, 1, 2))              # (out_channels,)
    h = bn_gamma[None, None, None, :] * (
        (h - mean[None, None, None, :]) / jnp.sqrt(var[None, None, None, :] + eps)
    ) + bn_beta[None, None, None, :]

    # ReLU
    return jax.nn.relu(h)


# === Depthwise separable conv block (MobileNet) ===

def depthwise_separable_conv(
    x: Float[Array, "batch height width channels"],
    dw_kernel: Float[Array, "kh kw 1 1"],
    pw_kernel: Float[Array, "1 1 channels out_channels"],
    bn1_gamma: Float[Array, "channels"],
    bn1_beta: Float[Array, "channels"],
    bn2_gamma: Float[Array, "out_channels"],
    bn2_beta: Float[Array, "out_channels"],
    stride: tuple[int, int] = (1, 1),
) -> Float[Array, "batch height2 width2 out_channels"]:
    """Depthwise separable convolution: depthwise conv → BN → ReLU → 1x1 conv → BN → ReLU."""
    channels = x.shape[-1]

    # Depthwise convolution
    h = lax.conv_general_dilated(
        x,
        dw_kernel,
        window_strides=stride,
        padding="SAME",
        dimension_numbers=("NHWC", "HWIO", "NHWC"),
        feature_group_count=channels,
    )

    # BN + ReLU
    mean = jnp.mean(h, axis=(0, 1, 2))
    var = jnp.var(h, axis=(0, 1, 2))
    h = bn1_gamma[None, None, None, :] * (h - mean[None, None, None, :]) / jnp.sqrt(var[None, None, None, :] + 1e-5) + bn1_beta[None, None, None, :]
    h = jax.nn.relu(h)

    # Pointwise (1x1) convolution
    h = lax.conv_general_dilated(
        h,
        pw_kernel,
        window_strides=(1, 1),
        padding="SAME",
        dimension_numbers=("NHWC", "HWIO", "NHWC"),
    )

    # BN + ReLU
    mean = jnp.mean(h, axis=(0, 1, 2))
    var = jnp.var(h, axis=(0, 1, 2))
    h = bn2_gamma[None, None, None, :] * (h - mean[None, None, None, :]) / jnp.sqrt(var[None, None, None, :] + 1e-5) + bn2_beta[None, None, None, :]
    return jax.nn.relu(h)


# Test
key = jax.random.PRNGKey(0)
k1, k2 = jax.random.split(key)
x = jax.random.normal(k1, (2, 16, 16, 3))
kernel = jax.random.normal(k2, (3, 3, 3, 32))
gamma = jnp.ones(32)
beta = jnp.zeros(32)

out = conv_bn_relu(x, kernel, gamma, beta)
assert out.shape == (2, 16, 16, 32)

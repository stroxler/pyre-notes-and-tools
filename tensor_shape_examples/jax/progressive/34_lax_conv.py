"""Progressive demo 34: lax convolution primitives.

New operations:
  jax.lax.conv, jax.lax.conv_general_dilated

These are the low-level convolution primitives that Flax nn.Conv wraps.
Shape rules depend on dimension_numbers (e.g., "NHWC" vs "NCHW").

Used in: every vision model (ResNet, DenseNet, U-Net, etc.).
"""

import jax
import jax.numpy as jnp
import jax.lax as lax
from jaxtyping import Array, Float


# === Basic 2D convolution ===
# lax.conv_general_dilated is the workhorse

# Input: (batch, height, width, channels) = NHWC
x: Float[Array, "1 8 8 3"] = jnp.ones((1, 8, 8, 3))

# Kernel: (height, width, in_channels, out_channels)
kernel: Float[Array, "3 3 3 16"] = jnp.ones((3, 3, 3, 16))

# NHWC convolution with "SAME" padding
out_same: Float[Array, "1 8 8 16"] = lax.conv_general_dilated(
    x,
    kernel,
    window_strides=(1, 1),
    padding="SAME",
    dimension_numbers=("NHWC", "HWIO", "NHWC"),
)
assert out_same.shape == (1, 8, 8, 16)


# With stride 2: spatial dimensions halve
out_stride2: Float[Array, "1 4 4 16"] = lax.conv_general_dilated(
    x,
    kernel,
    window_strides=(2, 2),
    padding="SAME",
    dimension_numbers=("NHWC", "HWIO", "NHWC"),
)
assert out_stride2.shape == (1, 4, 4, 16)


# "VALID" padding (no padding): output shrinks
out_valid: Float[Array, "1 6 6 16"] = lax.conv_general_dilated(
    x,
    kernel,
    window_strides=(1, 1),
    padding="VALID",
    dimension_numbers=("NHWC", "HWIO", "NHWC"),
)
assert out_valid.shape == (1, 6, 6, 16)


# === 1D convolution (for audio / sequence models) ===

x_1d: Float[Array, "1 100 8"] = jnp.ones((1, 100, 8))  # (batch, length, channels)
kernel_1d: Float[Array, "5 8 16"] = jnp.ones((5, 8, 16))

out_1d: Float[Array, "1 100 16"] = lax.conv_general_dilated(
    x_1d,
    kernel_1d,
    window_strides=(1,),
    padding="SAME",
    dimension_numbers=("NWC", "WIO", "NWC"),
)
assert out_1d.shape == (1, 100, 16)


# === Depthwise convolution (MobileNet) ===

def depthwise_conv(
    x: Float[Array, "batch height width channels"],
    kernel: Float[Array, "kh kw 1 channel_multiplier"],
    strides: tuple[int, int] = (1, 1),
) -> Float[Array, "batch height2 width2 channels_times_multiplier"]:
    """Depthwise convolution using feature_group_count."""
    channels = x.shape[-1]
    return lax.conv_general_dilated(
        x,
        kernel,
        window_strides=strides,
        padding="SAME",
        dimension_numbers=("NHWC", "HWIO", "NHWC"),
        feature_group_count=channels,
    )

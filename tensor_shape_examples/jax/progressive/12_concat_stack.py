"""Progressive demo 12: Concatenation, stacking, splitting.

New operations:
  jnp.concatenate, jnp.stack, jnp.split, jnp.array_split

Shape rules:
  concatenate([a, b], axis): join along existing axis, other dims must match
  stack([a, b], axis):       join along NEW axis (adds a dimension)
  split(x, n, axis):         split into n equal parts along axis

Used in: skip connections (U-Net, DenseNet), QKV splitting, KV cache,
         multi-branch architectures (SqueezeNet Fire module).
"""

import jax.numpy as jnp
from jaxtyping import Array, Float


# === concatenate: join along existing axis ===

a: Float[Array, "2 3"] = jnp.ones((2, 3))
b: Float[Array, "2 4"] = jnp.ones((2, 4))

# Along axis 1: (2, 3) + (2, 4) → (2, 7)
cat1: Float[Array, "2 7"] = jnp.concatenate([a, b], axis=1)

# Along axis 0: (2, 3) + (3, 3) → (5, 3)
c: Float[Array, "3 3"] = jnp.ones((3, 3))
cat0: Float[Array, "5 3"] = jnp.concatenate([a, c], axis=0)


# === stack: join along NEW axis ===

x: Float[Array, "3 4"] = jnp.ones((3, 4))
y: Float[Array, "3 4"] = jnp.ones((3, 4))

# Stack along new axis 0: two (3, 4) → (2, 3, 4)
stacked: Float[Array, "2 3 4"] = jnp.stack([x, y], axis=0)

# Stack along new axis 1: two (3, 4) → (3, 2, 4)
stacked1: Float[Array, "3 2 4"] = jnp.stack([x, y], axis=1)


# === split: divide into parts ===

big: Float[Array, "6 4"] = jnp.ones((6, 4))

# Split into 3 equal parts along axis 0
parts = jnp.split(big, 3, axis=0)  # list of 3 × (2, 4)
p0: Float[Array, "2 4"] = parts[0]
p1: Float[Array, "2 4"] = parts[1]
p2: Float[Array, "2 4"] = parts[2]

# Split at specific indices
parts2 = jnp.split(big, [2, 4], axis=0)  # (2,4), (2,4), (2,4)


# === Skip connection pattern (U-Net / DenseNet) ===

def unet_skip_connection(
    upsampled: Float[Array, "batch channels_up height width"],
    encoder_feat: Float[Array, "batch channels_enc height width"],
) -> Float[Array, "batch channels_total height width"]:
    """Concatenate skip connection along channel axis."""
    return jnp.concatenate([upsampled, encoder_feat], axis=1)


# === Dense block pattern (DenseNet) ===

def dense_layer(
    x: Float[Array, "batch channels height width"],
    new_features: Float[Array, "batch growth_rate height width"],
) -> Float[Array, "batch channels_plus_growth height width"]:
    """Concatenate new features to running representation."""
    return jnp.concatenate([x, new_features], axis=1)


# === QKV split pattern (transformers) ===

def split_qkv(
    qkv: Float[Array, "batch seq three_d_model"],
    d_model: int,
) -> tuple[
    Float[Array, "batch seq d_model"],
    Float[Array, "batch seq d_model"],
    Float[Array, "batch seq d_model"],
]:
    """Split fused QKV projection into Q, K, V."""
    q, k, v = jnp.split(qkv, 3, axis=-1)
    return q, k, v


# === Fire module pattern (SqueezeNet) ===

def fire_module(
    expand1x1: Float[Array, "batch e1 height width"],
    expand3x3: Float[Array, "batch e3 height width"],
) -> Float[Array, "batch e1_plus_e3 height width"]:
    """Merge parallel expand branches."""
    return jnp.concatenate([expand1x1, expand3x3], axis=1)


assert cat1.shape == (2, 7)
assert stacked.shape == (2, 3, 4)
assert p0.shape == (2, 4)

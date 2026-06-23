"""Progressive demo 35: Pooling via reduce_window.

New operations:
  jax.lax.reduce_window

reduce_window is the general pooling primitive. It applies a reduction
(max, sum, etc.) over a sliding window.

Used in: max pooling (ResNet), average pooling (global avg pool).
"""

import jax
import jax.numpy as jnp
import jax.lax as lax
from jaxtyping import Array, Float


# === Max pooling 2D ===

x: Float[Array, "1 8 8 3"] = jax.random.normal(jax.random.PRNGKey(0), (1, 8, 8, 3))

# 2x2 max pool with stride 2: (1, 8, 8, 3) → (1, 4, 4, 3)
max_pooled: Float[Array, "1 4 4 3"] = lax.reduce_window(
    x,
    init_value=-jnp.inf,
    computation=lax.max,
    window_dimensions=(1, 2, 2, 1),  # pool over H, W only
    window_strides=(1, 2, 2, 1),
    padding="VALID",
)
assert max_pooled.shape == (1, 4, 4, 3)


# === Average pooling 2D ===
# Average = sum / count

sum_pooled = lax.reduce_window(
    x,
    init_value=0.0,
    computation=lax.add,
    window_dimensions=(1, 2, 2, 1),
    window_strides=(1, 2, 2, 1),
    padding="VALID",
)
avg_pooled: Float[Array, "1 4 4 3"] = sum_pooled / 4.0  # window_size = 2*2 = 4
assert avg_pooled.shape == (1, 4, 4, 3)


# === Convenience wrappers ===

def max_pool_2d(
    x: Float[Array, "batch height width channels"],
    pool_size: tuple[int, int] = (2, 2),
    strides: tuple[int, int] = (2, 2),
) -> Float[Array, "batch height2 width2 channels"]:
    """2D max pooling (NHWC format)."""
    return lax.reduce_window(
        x,
        init_value=-jnp.inf,
        computation=lax.max,
        window_dimensions=(1, *pool_size, 1),
        window_strides=(1, *strides, 1),
        padding="VALID",
    )


def avg_pool_2d(
    x: Float[Array, "batch height width channels"],
    pool_size: tuple[int, int] = (2, 2),
    strides: tuple[int, int] = (2, 2),
) -> Float[Array, "batch height2 width2 channels"]:
    """2D average pooling (NHWC format)."""
    window_size = pool_size[0] * pool_size[1]
    pooled = lax.reduce_window(
        x,
        init_value=0.0,
        computation=lax.add,
        window_dimensions=(1, *pool_size, 1),
        window_strides=(1, *strides, 1),
        padding="VALID",
    )
    return pooled / window_size

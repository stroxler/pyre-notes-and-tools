"""Progressive demo 04: Transcendental and power functions.

New operations:
  jnp.exp, jnp.log, jnp.log2, jnp.sqrt, jnp.rsqrt,
  jnp.abs, jnp.square, jnp.power, jnp.sign

All elementwise: shape in == shape out.
Used in: attention scaling (rsqrt), loss computation (log), normalization (sqrt).
"""

import jax.numpy as jnp
from jaxtyping import Array, Float


x: Float[Array, "3 4"] = jnp.ones((3, 4)) * 2.0

# Each preserves shape
exp_x: Float[Array, "3 4"] = jnp.exp(x)
log_x: Float[Array, "3 4"] = jnp.log(x)
sqrt_x: Float[Array, "3 4"] = jnp.sqrt(x)
abs_x: Float[Array, "3 4"] = jnp.abs(x)
sq_x: Float[Array, "3 4"] = jnp.square(x)


# === Attention scaling pattern ===
# In scaled dot-product attention: scores / sqrt(d_k)

def scale_attention_scores(
    scores: Float[Array, "batch heads seq_q seq_k"],
    d_k: int,
) -> Float[Array, "batch heads seq_q seq_k"]:
    return scores / jnp.sqrt(jnp.float32(d_k))


# === RMSNorm pattern (used in LLaMA) ===
# x * rsqrt(mean(x^2) + eps)

def rms_norm(
    x: Float[Array, "batch seq dim"],
    weight: Float[Array, "dim"],
    eps: float = 1e-6,
) -> Float[Array, "batch seq dim"]:
    variance = jnp.mean(jnp.square(x), axis=-1, keepdims=True)
    x_normed = x * jnp.reciprocal(jnp.sqrt(variance + eps))
    return x_normed * weight


assert exp_x.shape == (3, 4)
assert log_x.shape == (3, 4)

"""Progressive demo 07: Matrix multiplication.

New operations:
  jnp.dot, jnp.matmul, @ operator, jnp.inner, jnp.outer

Shape rules:
  dot/matmul: (..., M, K) @ (..., K, N) → (..., M, N)
  inner:      (K,) · (K,) → scalar
  outer:      (M,) ⊗ (N,) → (M, N)

Used in: every linear layer, every attention computation.
"""

import jax.numpy as jnp
from jaxtyping import Array, Float


# === Vector dot product ===

v1: Float[Array, "4"] = jnp.array([1.0, 2.0, 3.0, 4.0])
v2: Float[Array, "4"] = jnp.array([5.0, 6.0, 7.0, 8.0])
s: Float[Array, ""] = jnp.dot(v1, v2)  # scalar: 1*5 + 2*6 + 3*7 + 4*8 = 70


# === Matrix-vector product ===

W: Float[Array, "3 4"] = jnp.ones((3, 4))
x: Float[Array, "4"] = jnp.ones(4)
y: Float[Array, "3"] = jnp.dot(W, x)  # (3, 4) · (4,) → (3,)


# === Matrix-matrix product ===

A: Float[Array, "3 4"] = jnp.ones((3, 4))
B: Float[Array, "4 5"] = jnp.ones((4, 5))
C: Float[Array, "3 5"] = A @ B  # (3, 4) @ (4, 5) → (3, 5)
C2: Float[Array, "3 5"] = jnp.matmul(A, B)  # equivalent


# === Batched matrix multiplication ===
# Batch dimensions are broadcast

batch_A: Float[Array, "2 3 4"] = jnp.ones((2, 3, 4))
batch_B: Float[Array, "2 4 5"] = jnp.ones((2, 4, 5))
batch_C: Float[Array, "2 3 5"] = batch_A @ batch_B  # (2, 3, 4) @ (2, 4, 5) → (2, 3, 5)

# Broadcast: (2, 3, 4) @ (4, 5) → (2, 3, 5)
batch_C2: Float[Array, "2 3 5"] = batch_A @ B


# === Outer product ===
# (M,) ⊗ (N,) → (M, N)

u: Float[Array, "3"] = jnp.array([1.0, 2.0, 3.0])
v: Float[Array, "4"] = jnp.array([4.0, 5.0, 6.0, 7.0])
outer: Float[Array, "3 4"] = jnp.outer(u, v)


# === Linear layer pattern ===

def linear(
    x: Float[Array, "batch features_in"],
    weight: Float[Array, "features_in features_out"],
    bias: Float[Array, "features_out"],
) -> Float[Array, "batch features_out"]:
    """A basic linear / fully-connected layer."""
    return x @ weight + bias


assert C.shape == (3, 5)
assert batch_C.shape == (2, 3, 5)
assert outer.shape == (3, 4)

"""Progressive demo 08: Einstein summation.

New operations:
  jnp.einsum

Einsum is the Swiss army knife of tensor contraction. It can express:
  - dot products, matmul, batched matmul
  - trace, transpose
  - outer products
  - any combination of the above

Used in: attention (QK^T, AV), RoPE, MoE expert dispatch (Mixtral),
         relative position biases (SAM).
"""

import jax.numpy as jnp
from jaxtyping import Array, Float


# === Basic contractions ===

# Vector dot product: (i,), (i,) → ()
a: Float[Array, "4"] = jnp.ones(4)
b: Float[Array, "4"] = jnp.ones(4)
dot: Float[Array, ""] = jnp.einsum("i,i->", a, b)

# Matrix-vector product: (i, j), (j,) → (i,)
W: Float[Array, "3 4"] = jnp.ones((3, 4))
x: Float[Array, "4"] = jnp.ones(4)
y: Float[Array, "3"] = jnp.einsum("ij,j->i", W, x)

# Matrix multiply: (i, k), (k, j) → (i, j)
A: Float[Array, "3 4"] = jnp.ones((3, 4))
B: Float[Array, "4 5"] = jnp.ones((4, 5))
C: Float[Array, "3 5"] = jnp.einsum("ik,kj->ij", A, B)


# === Batched matrix multiply ===

# Batched matmul: (b, i, k), (b, k, j) → (b, i, j)
bA: Float[Array, "2 3 4"] = jnp.ones((2, 3, 4))
bB: Float[Array, "2 4 5"] = jnp.ones((2, 4, 5))
bC: Float[Array, "2 3 5"] = jnp.einsum("bik,bkj->bij", bA, bB)


# === Attention pattern: Q @ K^T ===

def attention_scores(
    q: Float[Array, "batch heads seq_q dim"],
    k: Float[Array, "batch heads seq_k dim"],
) -> Float[Array, "batch heads seq_q seq_k"]:
    """Compute attention scores via einsum (Q K^T)."""
    return jnp.einsum("bhqd,bhkd->bhqk", q, k)


# === MoE expert-batched matmul pattern (from Mixtral) ===

def expert_matmul(
    x: Float[Array, "tokens dim_in"],
    weights: Float[Array, "tokens num_experts dim_out dim_in"],
) -> Float[Array, "tokens num_experts dim_out"]:
    """Batched matmul for mixture-of-experts."""
    return jnp.einsum("ti,taoi->tao", x, weights)


# === Relative position bias pattern (from SAM) ===

def relative_position_attention(
    q: Float[Array, "batch height width channels"],
    rel_pos: Float[Array, "height num_rel channels"],
) -> Float[Array, "batch height width num_rel"]:
    """Compute relative position attention bias."""
    return jnp.einsum("bhwc,hkc->bhwk", q, rel_pos)


# === Transpose via einsum ===

M: Float[Array, "3 4"] = jnp.ones((3, 4))
Mt: Float[Array, "4 3"] = jnp.einsum("ij->ji", M)

# Trace
sq: Float[Array, "3 3"] = jnp.ones((3, 3))
tr: Float[Array, ""] = jnp.einsum("ii->", sq)


assert C.shape == (3, 5)
assert bC.shape == (2, 3, 5)
assert Mt.shape == (4, 3)

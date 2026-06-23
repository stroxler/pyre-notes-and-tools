"""Progressive demo 15: Padding.

New operations:
  jnp.pad

Shape rules:
  pad(x, pad_width): each dimension can be padded by (before, after)
  output shape = input shape + padding per dimension

Used in: convolution padding, sequence padding, spatial padding.
"""

import jax.numpy as jnp
from jaxtyping import Array, Float


x: Float[Array, "3 4"] = jnp.ones((3, 4))

# === Constant padding ===

# Pad 1 on all sides: (3, 4) → (5, 6)
padded: Float[Array, "5 6"] = jnp.pad(x, pad_width=1, mode="constant", constant_values=0)

# Asymmetric padding: (3, 4) → (4, 7)
asym: Float[Array, "4 7"] = jnp.pad(x, ((0, 1), (1, 2)), mode="constant")

# Pad only one dimension: (3, 4) → (3, 6)
padded_cols: Float[Array, "3 6"] = jnp.pad(x, ((0, 0), (1, 1)), mode="constant")


# === Reflect padding ===

reflected: Float[Array, "5 6"] = jnp.pad(x, pad_width=1, mode="reflect")


# === Sequence padding pattern ===

def pad_sequence(
    x: Float[Array, "seq dim"],
    target_len: int,
) -> Float[Array, "target_len dim"]:
    """Right-pad a sequence to target length."""
    pad_len = target_len - x.shape[0]
    return jnp.pad(x, ((0, pad_len), (0, 0)), mode="constant")


seq = jnp.ones((5, 8))
padded_seq = pad_sequence(seq, 10)
assert padded_seq.shape == (10, 8)


assert padded.shape == (5, 6)
assert asym.shape == (4, 7)

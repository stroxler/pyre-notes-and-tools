"""Progressive demo 37: lax loops (scan, fori_loop, while_loop).

New operations:
  jax.lax.scan, jax.lax.fori_loop, jax.lax.while_loop

These replace Python for/while loops inside jit-compiled code.
scan is the most important: it's used for RNNs and repeated layers.

Shape rules:
  scan(f, init, xs):
    f: (carry, x) → (carry, y)
    carry has fixed shape throughout
    xs: (length, ...) — scanned over first axis
    returns: (final_carry, ys) where ys: (length, ...)
"""

import jax
import jax.numpy as jnp
import jax.lax as lax
from jaxtyping import Array, Float


# === lax.scan: the workhorse ===

# Simple cumulative sum via scan
def cumsum_scan(xs: Float[Array, "length"]) -> Float[Array, "length"]:
    """Cumulative sum implemented with scan."""
    def step(carry, x):
        carry = carry + x
        return carry, carry  # new carry, output
    _, cumulative = lax.scan(step, jnp.float32(0.0), xs)
    return cumulative

result = cumsum_scan(jnp.array([1.0, 2.0, 3.0, 4.0]))
assert result.shape == (4,)


# === LSTM cell with scan (RNN pattern) ===

def lstm_cell(
    carry: tuple[Float[Array, "hidden"], Float[Array, "hidden"]],
    x: Float[Array, "input_dim"],
    w_ih: Float[Array, "input_dim 4*hidden"],
    w_hh: Float[Array, "hidden 4*hidden"],
    b: Float[Array, "4*hidden"],
) -> tuple[tuple[Float[Array, "hidden"], Float[Array, "hidden"]], Float[Array, "hidden"]]:
    """Single LSTM step."""
    h, c = carry
    hidden = h.shape[0]
    gates = x @ w_ih + h @ w_hh + b
    i, f, g, o = jnp.split(gates, 4, axis=-1)
    i = jax.nn.sigmoid(i)
    f = jax.nn.sigmoid(f)
    g = jnp.tanh(g)
    o = jax.nn.sigmoid(o)
    new_c = f * c + i * g
    new_h = o * jnp.tanh(new_c)
    return (new_h, new_c), new_h


# Scan over sequence to run LSTM
def lstm_forward(
    x_seq: Float[Array, "seq_len input_dim"],
    h0: Float[Array, "hidden"],
    c0: Float[Array, "hidden"],
    w_ih: Float[Array, "input_dim 4*hidden"],
    w_hh: Float[Array, "hidden 4*hidden"],
    b: Float[Array, "4*hidden"],
) -> Float[Array, "seq_len hidden"]:
    """Run LSTM over a sequence using scan."""
    def step(carry, x):
        return lstm_cell(carry, x, w_ih, w_hh, b)

    (final_h, final_c), outputs = lax.scan(step, (h0, c0), x_seq)
    return outputs


# === fori_loop: simple counted loop ===

def power_iter(
    x: Float[Array, "dim"],
    n: int,
) -> Float[Array, "dim"]:
    """Apply element-wise squaring n times."""
    def body(i, x):
        return x * x
    return lax.fori_loop(0, n, body, x)


# === Repeated transformer layers via scan ===

def repeated_layers(
    x: Float[Array, "batch seq dim"],
    layer_params: Float[Array, "num_layers ..."],  # stacked params
) -> Float[Array, "batch seq dim"]:
    """Apply the same layer architecture N times via scan.

    This is memory-efficient: O(1) in number of layers during backprop
    when combined with gradient checkpointing.
    """
    def apply_layer(x, params):
        # Each layer is a residual MLP (simplified)
        h = jax.nn.gelu(x)  # placeholder for actual layer
        return x + h, None   # carry=output, no per-layer output needed

    final_x, _ = lax.scan(apply_layer, x, layer_params)
    return final_x

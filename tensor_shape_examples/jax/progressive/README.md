# Progressive JAX/numpy API Demos

~50 small, focused examples that each introduce a few new operations.
Each file is self-contained and exercises specific operations that need
stub support in Pyrefly.

These are ordered so that each commit adds a few new operations, building
on the previous ones. The progression is driven by what the real models
(in `../models/`) actually need.

## Ladder

### Phase 1: Tensor Creation & Basic Math (commits 1-8)

These introduce the absolute fundamentals — what every JAX program uses.

| # | File | New operations | Description |
|---|------|---------------|-------------|
| 1 | `01_tensor_creation.py` | `jnp.array`, `jnp.zeros`, `jnp.ones`, `jnp.full`, `jnp.eye`, `jnp.empty` | Create tensors of various shapes and dtypes |
| 2 | `02_arange_linspace.py` | `jnp.arange`, `jnp.linspace` | Create ranges and evenly spaced tensors |
| 3 | `03_elementwise_math.py` | `jnp.add`, `jnp.multiply`, `jnp.subtract`, `jnp.divide`, `jnp.negative`, operator overloads (+, -, *, /) | Elementwise arithmetic, broadcasting basics |
| 4 | `04_transcendental.py` | `jnp.exp`, `jnp.log`, `jnp.sqrt`, `jnp.abs`, `jnp.square`, `jnp.power` | Transcendental and power functions |
| 5 | `05_trig.py` | `jnp.sin`, `jnp.cos`, `jnp.tan`, `jnp.tanh` | Trigonometric functions (used in positional encodings) |
| 6 | `06_comparison.py` | `jnp.equal`, `jnp.greater`, `jnp.less`, `jnp.maximum`, `jnp.minimum`, `jnp.clip`, `jnp.where` | Comparisons, clipping, conditional selection |
| 7 | `07_dot_matmul.py` | `jnp.dot`, `jnp.matmul`, `@` operator | Matrix multiplication, vector dot products |
| 8 | `08_einsum.py` | `jnp.einsum` | Einstein summation for batched matmul, traces, outer products |

### Phase 2: Shape Manipulation (commits 9-16)

The bread and butter of neural network shape wrangling.

| # | File | New operations | Description |
|---|------|---------------|-------------|
| 9 | `09_reshape_flatten.py` | `jnp.reshape`, `.reshape()`, `jnp.ravel` | Reshaping tensors, flattening |
| 10 | `10_transpose_permute.py` | `jnp.transpose`, `jnp.swapaxes`, `jnp.moveaxis` | Axis reordering (critical for attention heads) |
| 11 | `11_expand_squeeze.py` | `jnp.expand_dims`, `jnp.squeeze`, `jnp.broadcast_to` | Adding/removing dimensions, explicit broadcasting |
| 12 | `12_concat_stack.py` | `jnp.concatenate`, `jnp.stack`, `jnp.split`, `jnp.array_split` | Joining and splitting along axes |
| 13 | `13_indexing.py` | basic indexing, slicing, `jnp.take`, `jnp.take_along_axis` | Indexing patterns (gather-like ops) |
| 14 | `14_tril_triu.py` | `jnp.tril`, `jnp.triu` | Triangular matrices (causal masks) |
| 15 | `15_pad.py` | `jnp.pad` | Padding tensors (used in convolutions, sequences) |
| 16 | `16_repeat_tile.py` | `jnp.repeat`, `jnp.tile` | Repeating and tiling tensors |

### Phase 3: Reductions & Statistics (commits 17-20)

| # | File | New operations | Description |
|---|------|---------------|-------------|
| 17 | `17_reductions.py` | `jnp.sum`, `jnp.prod`, `jnp.mean` | Sum, product, mean over axes; keepdims |
| 18 | `18_minmax.py` | `jnp.max`, `jnp.min`, `jnp.argmax`, `jnp.argmin` | Min/max reductions and argmin/argmax |
| 19 | `19_norms.py` | `jnp.linalg.norm`, `jnp.var`, `jnp.std` | Norms and variance (used in LayerNorm) |
| 20 | `20_cumulative.py` | `jnp.cumsum`, `jnp.cumprod` | Cumulative operations |

### Phase 4: Random Number Generation (commits 21-24)

JAX's stateless PRNG system is fundamental and unique.

| # | File | New operations | Description |
|---|------|---------------|-------------|
| 21 | `21_random_keys.py` | `jax.random.PRNGKey`, `jax.random.key`, `jax.random.split`, `jax.random.fold_in` | PRNG key management |
| 22 | `22_random_sampling.py` | `jax.random.normal`, `jax.random.uniform`, `jax.random.randint` | Basic random sampling |
| 23 | `23_random_distributions.py` | `jax.random.bernoulli`, `jax.random.categorical`, `jax.random.choice`, `jax.random.permutation` | Discrete distributions and shuffling |
| 24 | `24_random_init.py` | `jax.nn.initializers.glorot_uniform`, `glorot_normal`, `he_normal`, `lecun_normal`, `zeros`, `ones` | Weight initializers (used in all models) |

### Phase 5: Activation Functions & NN Utilities (commits 25-28)

| # | File | New operations | Description |
|---|------|---------------|-------------|
| 25 | `25_activations.py` | `jax.nn.relu`, `jax.nn.gelu`, `jax.nn.silu`/`swish`, `jax.nn.elu`, `jax.nn.leaky_relu`, `jax.nn.relu6` | All standard activations |
| 26 | `26_softmax.py` | `jax.nn.softmax`, `jax.nn.log_softmax`, `jax.nn.sigmoid`, `jax.nn.tanh` | Softmax family |
| 27 | `27_normalize.py` | `jax.nn.normalize`, `jax.nn.standardize`, manual LayerNorm via jnp ops | Normalization utilities |
| 28 | `28_one_hot.py` | `jax.nn.one_hot` | One-hot encoding |

### Phase 6: JAX Transforms (commits 29-33)

These are JAX-specific and critical for understanding real code.

| # | File | New operations | Description |
|---|------|---------------|-------------|
| 29 | `29_jit.py` | `jax.jit` | JIT compilation basics |
| 30 | `30_grad.py` | `jax.grad`, `jax.value_and_grad` | Automatic differentiation |
| 31 | `31_vmap.py` | `jax.vmap` | Vectorized map (auto-batching) |
| 32 | `32_pytrees.py` | `jax.tree.map`, `jax.tree.leaves`, `jax.tree.structure` | Pytree manipulation (parameter trees) |
| 33 | `33_transform_composition.py` | composing `jit`, `grad`, `vmap` | Composing transforms (real training patterns) |

### Phase 7: lax Primitives (commits 34-39)

Low-level operations that underlie many nn layers.

| # | File | New operations | Description |
|---|------|---------------|-------------|
| 34 | `34_lax_conv.py` | `jax.lax.conv`, `jax.lax.conv_general_dilated` | Convolution primitives |
| 35 | `35_lax_pooling.py` | `jax.lax.reduce_window` | Pooling via reduce_window |
| 36 | `36_lax_control_flow.py` | `jax.lax.cond`, `jax.lax.switch` | Conditional execution in JIT |
| 37 | `37_lax_loops.py` | `jax.lax.scan`, `jax.lax.fori_loop`, `jax.lax.while_loop` | Loops in JIT (RNNs, scan) |
| 38 | `38_lax_slicing.py` | `jax.lax.dynamic_slice`, `jax.lax.dynamic_update_slice` | Dynamic slicing (KV cache, etc.) |
| 39 | `39_lax_sort_topk.py` | `jax.lax.sort`, `jax.lax.top_k` | Sorting and top-k (MoE gating) |

### Phase 8: Patterns from Real Models (commits 40-50)

These assemble primitives from earlier phases into patterns found in real
neural networks. Each one is a small but complete computation graph.

| # | File | New operations / patterns | Description |
|---|------|--------------------------|-------------|
| 40 | `40_attention_pattern.py` | Multi-head attention from scratch | QKV projection, reshape to heads, scaled dot-product attention, reassemble |
| 41 | `41_positional_encoding.py` | Sinusoidal and learned positional encodings | `jnp.sin`/`jnp.cos` interleaving, `jnp.arange` frequency computation |
| 42 | `42_causal_mask.py` | Causal masking patterns | `jnp.tril` mask, `jnp.where` with -inf fill, attention mask combination |
| 43 | `43_residual_block.py` | Residual connection patterns | Pre-norm and post-norm residual blocks |
| 44 | `44_conv_bn_relu.py` | Conv → BatchNorm → ReLU | Standard vision network building block |
| 45 | `45_mlp_block.py` | Feed-forward network block | Dense → activation → Dense with dropout mask |
| 46 | `46_embedding_lookup.py` | Token + position embedding | Embedding table lookup, position addition |
| 47 | `47_loss_functions.py` | Cross-entropy, MSE from primitives | `jax.nn.log_softmax`, reductions for loss computation |
| 48 | `48_weight_tying.py` | Output projection via embedding transpose | Reusing embedding matrix for logits |
| 49 | `49_kv_cache.py` | KV cache update pattern | `jax.lax.dynamic_update_slice` for autoregressive decoding |
| 50 | `50_training_step.py` | Complete training step | `jax.value_and_grad` → optax update → pytree manipulation |

---

## Usage

Each file should be self-contained and runnable (assuming jax + jaxtyping
are installed). The jaxtyping annotations serve as the test: Pyrefly should
be able to infer and verify the tensor shapes.

Example pattern for each file:

```python
import jax
import jax.numpy as jnp
from jaxtyping import Array, Float, Int

# Demonstrate operations with explicit shape annotations

def example_matmul(
    x: Float[Array, "batch seq features"],
    w: Float[Array, "features hidden"],
) -> Float[Array, "batch seq hidden"]:
    return x @ w

# Concrete examples with known shapes
key = jax.random.PRNGKey(0)
x = jax.random.normal(key, (2, 10, 64))  # [batch=2, seq=10, features=64]
w = jax.random.normal(key, (64, 128))    # [features=64, hidden=128]
y = example_matmul(x, w)                 # [batch=2, seq=10, hidden=128]
assert y.shape == (2, 10, 128)
```

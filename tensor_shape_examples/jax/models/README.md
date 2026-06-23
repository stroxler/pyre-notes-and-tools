# Real-World JAX Model Examples

Models sourced from well-known open-source JAX repositories, annotated with
jaxtyping shape annotations. The goal is to prove out a flow for adding
annotations to existing, idiomatic JAX code.

## Source Catalog

Each model is drawn from a real open-source implementation. We link to the
source and note which framework it uses (raw JAX, Flax Linen, Flax NNX,
Haiku, Equinox) and which domain it covers.

### Torch example mapping

For reference, the existing pyrefly torch examples cover these 29 models:

```
Vision (classification): resnet, densenet, mobilenetv2, squeezenet
Vision (segmentation):   unet, sam
Vision (generation/GAN): dcgan, stargan
NLP (transformers):      nanogpt, bert, llama, gptfast, mixtral_moe
Audio:                   demucs, wavernn, tacotron2, tts_angular, speech_transformer
RL:                      drq, soft_actor_critic
Other:                   apg, background_matting, deeprecommender, dlrm,
                         finalmlp, learning_to_paint, masknet, openpose,
                         super_slomo
```

### JAX model sources

We prioritize real implementations from official repos. Where a model doesn't
exist in JAX, we note it as a gap. Models are organized by domain.

---

## Vision — Classification

| # | Model | Source repo | File(s) | Framework | Torch analog |
|---|-------|------------|---------|-----------|--------------|
| 1 | **ResNet-50** | [google/flax: examples/imagenet](https://github.com/google/flax/tree/main/examples/imagenet) | `models.py` | Flax Linen | `resnet.py` |
| 2 | **ViT** (Vision Transformer) | [google-research/vision_transformer](https://github.com/google-research/vision_transformer) | `vit_jax/models_vit.py` | Flax Linen | (no torch analog) |
| 3 | **MLP-Mixer** | [google-research/vision_transformer](https://github.com/google-research/vision_transformer) | `vit_jax/models_mixer.py` | Flax Linen | (no torch analog) |
| 4 | **ResNet** (Haiku) | [dm-haiku: haiku/_src/nets](https://github.com/google-deepmind/dm-haiku/tree/main/haiku/_src/nets) | `resnet.py` | Haiku | `resnet.py` |
| 5 | **MobileNetV1** (Haiku) | [dm-haiku: haiku/_src/nets](https://github.com/google-deepmind/dm-haiku/tree/main/haiku/_src/nets) | `mobilenetv1.py` | Haiku | `mobilenetv2.py` |
| 6 | **DenseNet** | [DarshanDeshpande/jax-models](https://github.com/DarshanDeshpande/jax-models) | DenseNet files | Flax | `densenet.py` |
| 7 | **MNIST CNN** | [jax-ml/jax: examples](https://github.com/jax-ml/jax/tree/main/examples) | `mnist_classifier.py` | Raw JAX | (simplest baseline) |

## Vision — Segmentation

| # | Model | Source repo | File(s) | Framework | Torch analog |
|---|-------|------------|---------|-----------|--------------|
| 8 | **U-Net** | Community impl (e.g. [jakubclark/jax-unet](https://github.com/jakubclark/jax-unet) or similar) | model file | Flax | `unet.py` |

## Vision — Generation / GANs

| # | Model | Source repo | File(s) | Framework | Torch analog |
|---|-------|------------|---------|-----------|--------------|
| 9 | **DCGAN** | [dm-haiku: examples](https://github.com/google-deepmind/dm-haiku/blob/main/examples/mnist_gan.ipynb) | notebook → .py | Haiku | `dcgan.py` |
| 10 | **VAE** | [google/flax: examples/vae](https://github.com/google/flax/tree/main/examples/vae) | `models.py` | Flax Linen | (no torch analog) |
| 11 | **MNIST VAE** (raw JAX) | [jax-ml/jax: examples](https://github.com/jax-ml/jax/tree/main/examples) | `mnist_vae.py` | Raw JAX | (no torch analog) |
| 12 | **VQ-VAE** (Haiku) | [dm-haiku: haiku/_src/nets](https://github.com/google-deepmind/dm-haiku/tree/main/haiku/_src/nets) | `vqvae.py` | Haiku | (no torch analog) |

## NLP — Transformers / Language Models

| # | Model | Source repo | File(s) | Framework | Torch analog |
|---|-------|------------|---------|-----------|--------------|
| 13 | **Transformer** (enc-dec, WMT) | [google/flax: examples/wmt](https://github.com/google/flax/tree/main/examples/wmt) | `models.py` | Flax Linen | `speech_transformer.py` |
| 14 | **Transformer LM** (decoder) | [google/flax: examples/lm1b](https://github.com/google/flax/tree/main/examples/lm1b) | `models.py` | Flax Linen | `nanogpt.py` |
| 15 | **GPT-2** (nanoGPT port) | [jenkspt/gpt-jax](https://github.com/jenkspt/gpt-jax) | `model.py` | Flax Linen | `nanogpt.py` |
| 16 | **Transformer LM** (Haiku) | [dm-haiku: examples/transformer](https://github.com/google-deepmind/dm-haiku/tree/main/examples/transformer) | `model.py` | Haiku | `nanogpt.py` |
| 17 | **Gemma** (LLM) | [google/flax: examples/gemma](https://github.com/google/flax/tree/main/examples/gemma) | `transformer.py`, `layers.py` | Flax NNX | `llama.py` |
| 18 | **Seq2Seq** (LSTM) | [google/flax: examples/seq2seq](https://github.com/google/flax/tree/main/examples/seq2seq) | `models.py` | Flax Linen | (no torch analog) |

## NLP — Sequence Labeling

| # | Model | Source repo | File(s) | Framework | Torch analog |
|---|-------|------------|---------|-----------|--------------|
| 19 | **NLP Seq** (sequence labeling) | [google/flax: examples/nlp_seq](https://github.com/google/flax/tree/main/examples/nlp_seq) | model files | Flax Linen | `bert.py` |
| 20 | **SST-2** (sentiment) | [google/flax: examples/sst2](https://github.com/google/flax/tree/main/examples/sst2) | model files | Flax Linen | `bert.py` |

## Reinforcement Learning

| # | Model | Source repo | File(s) | Framework | Torch analog |
|---|-------|------------|---------|-----------|--------------|
| 21 | **PPO** (Atari) | [google/flax: examples/ppo](https://github.com/google/flax/tree/main/examples/ppo) | `models.py` | Flax Linen | `soft_actor_critic.py` |
| 22 | **SAC / DrQ** | [ikostrikov/jaxrl](https://github.com/ikostrikov/jaxrl) | `networks/`, `agents/` | Flax | `drq.py` |
| 23 | **DQN** (CleanRL) | [cleanrl: dqn_jax.py](https://github.com/vwxyzjn/cleanrl/blob/master/cleanrl/dqn_jax.py) | single file | Flax | (no torch analog) |
| 24 | **TD3** (CleanRL) | [cleanrl: td3_continuous_action_jax.py](https://github.com/vwxyzjn/cleanrl/blob/master/cleanrl/td3_continuous_action_jax.py) | single file | Flax | `drq.py` |

## Other Domains

| # | Model | Source repo | File(s) | Framework | Torch analog |
|---|-------|------------|---------|-----------|--------------|
| 25 | **GNN** (OGB-MolPCBA) | [google/flax: examples/ogbg_molpcba](https://github.com/google/flax/tree/main/examples/ogbg_molpcba) | model files | Flax Linen | (no torch analog) |
| 26 | **IMPALA** (RL agent) | [dm-haiku: examples](https://github.com/google-deepmind/dm-haiku/blob/main/examples/impala_lite.py) | `impala_lite.py` | Haiku | (no torch analog) |
| 27 | **MNIST MLP** (Haiku) | [dm-haiku: examples](https://github.com/google-deepmind/dm-haiku/blob/main/examples/mnist.py) | `mnist.py` | Haiku | (simplest baseline) |
| 28 | **LSTM** (Haiku) | [dm-haiku: examples](https://github.com/google-deepmind/dm-haiku/blob/main/examples/haiku_lstms.ipynb) | notebook | Haiku | (no torch analog) |

---

## Coverage Gaps vs. Torch Examples

These torch examples have **no direct JAX equivalent** in well-known repos:

| Torch example | Domain | Notes |
|---------------|--------|-------|
| `demucs.py` | Audio (source separation) | No known JAX impl |
| `wavernn.py` | Audio (synthesis) | No known JAX impl |
| `tacotron2.py` | Audio (TTS) | No known JAX impl |
| `tts_angular.py` | Audio (TTS) | No known JAX impl |
| `sam.py` | Vision (segment anything) | Too complex / no JAX port |
| `stargan.py` | Vision (conditional GAN) | No well-known JAX impl |
| `mixtral_moe.py` | NLP (MoE) | No standalone JAX impl |
| `dlrm.py` | Recommendation | No known JAX impl |
| `deeprecommender.py` | Recommendation | No known JAX impl |
| `super_slomo.py` | Video (interpolation) | No known JAX impl |
| `background_matting.py` | Vision (matting) | No known JAX impl |
| `openpose.py` | Vision (pose) | No known JAX impl |
| `learning_to_paint.py` | Vision (RL+rendering) | No known JAX impl |

**Key observation:** Audio and recommendation domains are underrepresented in
JAX's open-source ecosystem. The JAX ecosystem's strength is in vision
transformers, language models, and RL — which are well covered above.

---

## Operations Inventory (from model analysis)

These are the key operations used across all the models above, which need
stub support. This drives the progressive demo ladder.

### High Priority (used in nearly all models)
- `jnp.array`, `jnp.zeros`, `jnp.ones`, `jnp.full`
- `jnp.reshape`, `jnp.transpose`, `jnp.expand_dims`, `jnp.squeeze`
- `jnp.concatenate`, `jnp.stack`
- `jnp.matmul`, `jnp.dot`, `jnp.einsum`
- `jnp.mean`, `jnp.sum`, `jnp.max`, `jnp.min`
- `jnp.exp`, `jnp.log`, `jnp.sqrt`, `jnp.abs`
- `jnp.where`
- `jax.nn.relu`, `jax.nn.gelu`, `jax.nn.softmax`, `jax.nn.log_softmax`
- `jax.nn.sigmoid`, `jax.nn.tanh`, `jax.nn.silu`
- `jax.random.PRNGKey`, `jax.random.split`, `jax.random.normal`, `jax.random.uniform`

### Medium Priority (used in many models)
- `jnp.arange`, `jnp.linspace`
- `jnp.sin`, `jnp.cos`
- `jnp.tril`, `jnp.triu`
- `jnp.pad`
- `jnp.split`, `jnp.chunk` (via split)
- `jnp.take`, `jnp.take_along_axis`
- `jnp.argmax`, `jnp.argmin`
- `jnp.clip`
- `jnp.broadcast_to`
- `jnp.swapaxes`, `jnp.moveaxis`
- `jnp.flatten` (via reshape)
- `jax.nn.one_hot`
- `jax.nn.initializers.*`
- `jax.random.categorical`, `jax.random.bernoulli`, `jax.random.randint`

### Lower Priority (specialized use)
- `jnp.linalg.norm`, `jnp.linalg.inv`
- `jnp.fft.fft`, `jnp.fft.ifft`
- `jnp.convolve`
- `jax.lax.conv_general_dilated`
- `jax.lax.scan`, `jax.lax.cond`, `jax.lax.while_loop`
- `jax.lax.dynamic_slice`, `jax.lax.dynamic_update_slice`
- `jax.lax.gather`, `jax.lax.scatter`
- `jax.lax.top_k`
- `jax.lax.reduce_window` (pooling)
- `jax.scipy.special.logsumexp`

### Flax-specific (need Flax stubs, not just numpy)
- `nn.Dense`, `nn.Conv`, `nn.Embed`
- `nn.LayerNorm`, `nn.BatchNorm`, `nn.GroupNorm`, `nn.RMSNorm`
- `nn.relu`, `nn.gelu`, `nn.silu`
- `nn.Dropout`
- `nn.MultiHeadDotProductAttention`
- `nn.max_pool`, `nn.avg_pool`
- `nn.make_causal_mask`, `nn.make_attention_mask`
- `nn.initializers.*`

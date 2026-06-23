"""Random array generation: rand, randn, randint, uniform, normal, seed, choice."""

import numpy as np


def basic_random() -> None:
    # Uniform [0, 1) and standard normal
    np.random.seed(42)
    a = np.random.rand(5)  # shape: (5,)  uniform [0, 1)
    b = np.random.rand(3, 4)  # shape: (3, 4)
    c = np.random.randn(5)  # shape: (5,)  standard normal
    d = np.random.randn(2, 3)  # shape: (2, 3)


def integers_and_distributions() -> None:
    # Integers and parameterized distributions
    a = np.random.randint(0, 10, size=8)  # shape: (8,)  ints in [0, 10)
    b = np.random.randint(0, 100, size=(3, 4))  # shape: (3, 4)
    c = np.random.uniform(-1.0, 1.0, size=(4, 4))  # shape: (4, 4)
    d = np.random.normal(0.0, 1.0, size=(5,))  # shape: (5,)
    e = np.random.normal(10.0, 2.0, size=(3, 3))  # shape: (3, 3)


def sampling() -> None:
    # Choice and permutation
    pool = np.arange(20)  # shape: (20,)
    a = np.random.choice(pool, size=5, replace=False)  # shape: (5,)
    b = np.random.choice(pool, size=(2, 3))  # shape: (2, 3)
    shuffled = pool.copy()
    np.random.shuffle(shuffled)  # in-place, shape unchanged: (20,)

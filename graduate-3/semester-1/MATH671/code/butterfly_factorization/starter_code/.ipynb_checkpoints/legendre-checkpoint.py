"""Legendre tools: Gauss nodes/weights, Vandermonde matrix, transforms.

Provided as part of the Project 1 starter code. Everything here is a
dense O(N^2) reference implementation -- your job in Part I is to beat
the apply cost, not to rewrite these.
"""

import numpy as np


def gauss_legendre(N, tol=1e-15, maxit=100):
    """Gauss--Legendre nodes and weights on [-1, 1] by Newton iteration.

    O(N) per Newton sweep using the three-term recurrence; standard
    asymptotic initial guesses. Accurate to ~1e-15 for N up to at least
    2^16.

    Returns
    -------
    x : (N,) nodes in increasing order
    w : (N,) quadrature weights
    """
    k = np.arange(1, N + 1)
    # Tricomi-type initial guess
    x = np.cos(np.pi * (4 * k - 1) / (4 * N + 2))
    for _ in range(maxit):
        p, dp = _legendre_and_derivative(N, x)
        dx = -p / dp
        x = x + dx
        if np.max(np.abs(dx)) < tol:
            break
    x = np.sort(x)
    _, dp = _legendre_and_derivative(N, x)
    w = 2.0 / ((1.0 - x**2) * dp**2)
    return x, w


def _legendre_and_derivative(N, x):
    """P_N(x) and P_N'(x) by the three-term recurrence (vectorized)."""
    x = np.asarray(x)
    p0 = np.ones_like(x)
    p1 = x.copy()
    for n in range(1, N):
        p0, p1 = p1, ((2 * n + 1) * x * p1 - n * p0) / (n + 1)
    # p1 = P_N, p0 = P_{N-1}
    dp = N * (x * p1 - p0) / (x**2 - 1.0)
    return p1, dp


def legendre_vandermonde(N, x=None):
    """Dense Legendre--Vandermonde matrix P[j, n] = P_n(x_j).

    If x is None, uses the N Gauss--Legendre nodes. Columns n = 0..N-1.
    Computed column-by-column with the stable three-term recurrence.
    """
    if x is None:
        x, _ = gauss_legendre(N)
    x = np.asarray(x)
    M = len(x)
    P = np.empty((M, N))
    P[:, 0] = 1.0
    if N > 1:
        P[:, 1] = x
    for n in range(1, N - 1):
        P[:, n + 1] = ((2 * n + 1) * x * P[:, n] - n * P[:, n - 1]) / (n + 1)
    return P


def synthesis_matrix(N):
    """Coefficients -> point values at Gauss nodes (this is P itself)."""
    return legendre_vandermonde(N)


def analysis_matrix(N):
    """Point values at Gauss nodes -> coefficients.

    Uses discrete orthogonality: c_n = (n + 1/2) * sum_j w_j P_n(x_j) f(x_j).
    Exact for polynomials of degree < N (Gauss quadrature).
    """
    x, w = gauss_legendre(N)
    P = legendre_vandermonde(N, x)
    scale = np.arange(N) + 0.5
    return (P * w[:, None]).T * scale[:, None]


def eval_block(row_idx, col_idx, x):
    """Entries P_n(x_j) for j in row_idx (into node vector x) and
    n in col_idx, computed on demand without forming all of P.

    Used by the butterfly construction to form individual blocks.
    Cost O(len(row_idx) * max(col_idx)).
    """
    xs = x[np.asarray(row_idx)]
    nmax = int(np.max(col_idx))
    cols = np.asarray(col_idx)
    p0 = np.ones_like(xs)
    p1 = xs.copy()
    out = np.empty((len(xs), len(cols)))
    lookup = {int(n): i for i, n in enumerate(cols)}
    if 0 in lookup:
        out[:, lookup[0]] = p0
    if nmax >= 1 and 1 in lookup:
        out[:, lookup[1]] = p1
    for n in range(1, nmax):
        p0, p1 = p1, ((2 * n + 1) * xs * p1 - n * p0) / (n + 1)
        if (n + 1) in lookup:
            out[:, lookup[n + 1]] = p1
    return out

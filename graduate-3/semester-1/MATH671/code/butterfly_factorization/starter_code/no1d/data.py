"""Data generation for Task 6/7 (provided).

Boundary value problem on [-1, 1]:

    -(a(x) u')' = f(x),   u(-1) = u(1) = 0,

with a(x) > 0 a random smooth coefficient field and f either fixed
(default) or sampled per example (vary_f=True). Solved by spectral
collocation on Legendre--Gauss--Lobatto (LGL) nodes with a barycentric
differentiation matrix; solutions are then interpolated onto the two
model grids:

    * an equispaced grid (for the padded-Fourier FNO baseline),
    * the Gauss--Legendre grid (for your Legendre neural operator).

Everything is NumPy; the torch wrappers live in no1d/train.py.
"""

import numpy as np

from ..legendre import gauss_legendre, _legendre_and_derivative


# ------------------------- LGL collocation ---------------------------

def lgl_nodes(M, tol=1e-14, maxit=100):
    """Legendre--Gauss--Lobatto nodes: +-1 and the roots of P'_{M-1}."""
    if M < 3:
        raise ValueError("need M >= 3")
    Nn = M - 1
    k = np.arange(1, Nn)
    # Chebyshev--Lobatto interior points: excellent, collision-free
    # initial guesses for the LGL interior nodes
    x = np.cos(np.pi * k / Nn)
    for _ in range(maxit):
        # Newton on q(x) = P'_N(x) using recurrences
        p, dp = _legendre_and_derivative(Nn, x)
        # q = dp ; q' from the Legendre ODE: (1-x^2) P'' = 2x P' - N(N+1) P
        ddp = (2 * x * dp - Nn * (Nn + 1) * p) / (1.0 - x**2)
        dx = -dp / ddp
        x = x + dx
        if np.max(np.abs(dx)) < tol:
            break
    return np.concatenate([[-1.0], np.sort(x), [1.0]])


def _bary_weights(x):
    """Barycentric weights, computed in log space to avoid overflow for
    large node counts (returned up to a harmless common scale)."""
    x = np.asarray(x)
    C = x[:, None] - x[None, :]
    np.fill_diagonal(C, 1.0)
    logw = -np.sum(np.log(np.abs(C)), axis=1)
    sgn = np.prod(np.sign(C), axis=1)
    return sgn * np.exp(logw - np.max(logw))


def diff_matrix(x):
    """Barycentric differentiation matrix on arbitrary distinct nodes."""
    x = np.asarray(x)
    C = x[:, None] - x[None, :]
    np.fill_diagonal(C, 1.0)
    w = _bary_weights(x)
    D = (w[None, :] / w[:, None]) / C
    np.fill_diagonal(D, 0.0)
    np.fill_diagonal(D, -np.sum(D, axis=1))
    return D


def bary_interp(x_from, f_from, x_to):
    """Barycentric Lagrange interpolation from nodes x_from to x_to."""
    x_from = np.asarray(x_from)
    w = _bary_weights(x_from)
    diff = x_to[:, None] - x_from[None, :]
    exact = np.isclose(diff, 0.0)
    diff[exact] = 1.0
    K = w[None, :] / diff
    out = (K @ f_from) / np.sum(K, axis=1)
    hit_rows, hit_cols = np.where(exact)
    out[hit_rows] = f_from[hit_cols]
    return out


def solve_bvp(a_vals, f_vals, D):
    """Solve -(a u')' = f on the LGL grid with u(+-1)=0.

    a_vals, f_vals: values on the LGL nodes. D: differentiation matrix.
    """
    M = D.shape[0]
    L = -D @ (a_vals[:, None] * D)
    L[0, :] = 0.0
    L[0, 0] = 1.0
    L[-1, :] = 0.0
    L[-1, -1] = 1.0
    rhs = f_vals.copy()
    rhs[0] = 0.0
    rhs[-1] = 0.0
    return np.linalg.solve(L, rhs)


# ------------------------- random smooth fields -----------------------

def random_field(rng, x, kmax=8, decay=1.5, positive=False, amp=1.0):
    """Random smooth field as a decaying Chebyshev series; exp'd if
    positive=True (so a(x) > 0 with O(1) contrast)."""
    theta = np.arccos(np.clip(x, -1.0, 1.0))
    c = rng.standard_normal(kmax + 1) / (1 + np.arange(kmax + 1))**decay
    g = amp * sum(ck * np.cos(k * theta) for k, ck in enumerate(c))
    return np.exp(g) if positive else g


def default_forcing(x):
    """Fixed forcing used when vary_f=False."""
    return np.sin(2.5 * x) + 0.5 * np.cos(4.0 * x) + 1.0


# ------------------------- dataset ------------------------------------

def generate_dataset(n_samples, n_grid=256, M=129, vary_f=False, seed=0,
                     kmax=8):
    """Generate the operator-learning dataset.

    Returns a dict with, for each sample, the fields (a, f, u) sampled on
    (i) the equispaced grid 'eq' and (ii) the Gauss-Legendre grid 'gl',
    plus the grids themselves.
    """
    rng = np.random.default_rng(seed)
    x_lgl = lgl_nodes(M)
    D = diff_matrix(x_lgl)
    x_eq = np.linspace(-1.0, 1.0, n_grid)
    x_gl, _ = gauss_legendre(n_grid)

    out = {k: np.empty((n_samples, n_grid)) for k in
           ("a_eq", "f_eq", "u_eq", "a_gl", "f_gl", "u_gl")}
    for i in range(n_samples):
        a = random_field(rng, x_lgl, kmax=kmax, positive=True)
        f = (random_field(rng, x_lgl, kmax=kmax, amp=2.0) + 2.0
             if vary_f else default_forcing(x_lgl))
        u = solve_bvp(a, f, D)
        for name, vals in (("a", a), ("f", f), ("u", u)):
            out[f"{name}_eq"][i] = bary_interp(x_lgl, vals, x_eq)
            out[f"{name}_gl"][i] = bary_interp(x_lgl, vals, x_gl)
    out["x_eq"] = x_eq
    out["x_gl"] = x_gl
    out["vary_f"] = vary_f
    return out

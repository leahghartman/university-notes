"""Rank-adaptive interpolative decomposition (provided).

interp_decomp(A, tol) returns (J, X) with

    || A - A[:, J] @ X ||_2  <=  ~tol * ||A||_2,

where J is a list of skeleton column indices and X contains an identity
in those columns. Built on pivoted QR.
"""

import numpy as np
import scipy.linalg as sla


def interp_decomp(A, tol, max_rank=None):
    """Column ID of A to relative tolerance tol.

    Parameters
    ----------
    A : (m, n) array
    tol : relative spectral-norm tolerance
    max_rank : optional cap on the rank

    Returns
    -------
    J : (k,) integer array of skeleton column indices (into A's columns)
    X : (k, n) interpolation matrix, X[:, J] == I_k
    """
    A = np.asarray(A, dtype=float)
    m, n = A.shape
    if m == 0 or n == 0:
        return np.arange(0), np.zeros((0, n))
    Q, R, piv = sla.qr(A, mode="economic", pivoting=True)
    diag = np.abs(np.diag(R))
    if diag[0] == 0.0:
        return np.array([piv[0]]), np.zeros((1, n))
    k = int(np.searchsorted(-diag, -tol * diag[0]))
    k = max(k, 1)
    if max_rank is not None:
        k = min(k, max_rank)
    k = min(k, min(m, n))
    R11 = R[:k, :k]
    R12 = R[:k, k:]
    # T solves R11 T = R12 (well-conditioned thanks to pivoting)
    T = sla.solve_triangular(R11, R12, lower=False)
    X = np.zeros((k, n))
    X[:, piv[:k]] = np.eye(k)
    X[:, piv[k:]] = T
    J = piv[:k].copy()
    return J, X

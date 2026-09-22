"""Butterfly factorization of the Legendre--Vandermonde matrix: YOUR JOB.

Fill in the four TODO blocks below. Everything else -- trees, sampling,
ID, sparse compilation -- is provided. When you are done,

    P  ~=  S_D  S_{D-1} ... S_0        (compiled sparse factors)

and `butterfly_apply` evaluates P @ x in O(N r log N).

Scheme (see Lec 5, Section 4, and the project handout): dyadic trees
of equal depth D on targets (rows / theta-intervals) and degrees (columns
/ bands). Sweep stages ell = 0..D pair target nodes at depth ell with
degree nodes at depth D - ell. At stage 0 you compress each leaf degree
band against (a row sample of) all targets; at stage ell you merge the
two sibling skeletons from stage ell-1 and re-compress against the
halved target interval; at the final stage you evaluate small dense
blocks at the target leaves.
"""

import numpy as np
import scipy.sparse as sp

from .legendre import gauss_legendre, eval_block
from .interp_decomp import interp_decomp
from .blocks import tree_intervals, default_depth


def _sample_rows(rng, lo, hi, ncols, oversamp=4, nmin=16):
    """Random row sample within [lo, hi) of size ~ oversamp * ncols."""
    size = min(hi - lo, max(oversamp * ncols, nmin))
    return np.sort(rng.choice(np.arange(lo, hi), size=size, replace=False))


def butterfly_setup(N, tol=1e-8, depth=None, seed=0):
    """Construct and compile the butterfly factors."""
    if depth is None:
        depth = default_depth(N)
    D = depth
    x, _ = gauss_legendre(N)
    iv = tree_intervals(N, D)
    rng = np.random.default_rng(seed)

    ids = {}  # (ell, t, s) -> (Jglobal, X)

    # ---- stage 0: T = all targets, S = leaf degree bands --------------
    for s in range(2**D):
        clo, chi = iv[(D, s)]
        cols = np.arange(clo, chi)
        # TODO(1): form the block K[rows, cols] with eval_block, using
        # either all rows of the target range (simplest) or a row
        # sample via _sample_rows (faster; see Lec 5, Remark 2.5);
        # compress it with interp_decomp(tol) and store the *global*
        # skeleton column indices and X:
        #   ids[(0, 0, s)] = (cols[J], X)
        raise NotImplementedError("stage 0")

    # ---- stages ell = 1..D-1: halve targets, merge degree siblings ----
    for ell in range(1, D):
        for t in range(2**ell):
            rlo, rhi = iv[(ell, t)]
            for s in range(2 ** (D - ell)):
                # TODO(2): concatenate the two child skeletons from
                # stage ell-1 (which pairs (ell-1, ?, ?) are the
                # children? -- work this out on paper first); form the
                # block on the rows [rlo, rhi) (all of them, or a
                # sample), compress, and store
                # ids[(ell, t, s)] = (Jc[J], X).
                raise NotImplementedError("merge stage")

    # ---- final stage: dense evaluation blocks at target leaves --------
    dense = {}
    for t in range(2**D):
        rlo, rhi = iv[(D, t)]
        # TODO(3): concatenate the two stage-(D-1) skeletons that reach
        # this target leaf and store the dense block
        #   dense[t] = eval_block(np.arange(rlo, rhi), Jc, x)
        raise NotImplementedError("final stage")

    return _compile(N, D, ids, dense)


# ------------------------- provided below ----------------------------

def _compile(N, D, ids, dense):
    """Compile the per-block factors into per-stage sparse matrices,
    folding the child-gather selections into the factors. Provided."""
    stages = []
    order0 = [(0, s) for s in range(2**D)]
    S0 = sp.block_diag([ids[(0, 0, s)][1] for s in range(2**D)],
                       format="csr")
    stages.append((None, S0))
    offsets = _offsets(order0, {(0, s): ids[(0, 0, s)][1].shape[0]
                                for s in range(2**D)})
    for ell in range(1, D):
        order = [(t, s) for t in range(2**ell)
                 for s in range(2 ** (D - ell))]
        perm, blocks, sizes = [], [], {}
        for (t, s) in order:
            for child in (2 * s, 2 * s + 1):
                lo, ln = offsets[(t // 2, child)]
                perm.extend(range(lo, lo + ln))
            X = ids[(ell, t, s)][1]
            blocks.append(X)
            sizes[(t, s)] = X.shape[0]
        stages.append((np.asarray(perm),
                       sp.block_diag(blocks, format="csr")))
        offsets = _offsets(order, sizes)
    perm, blocks = [], []
    for t in range(2**D):
        for child in (0, 1):
            lo, ln = offsets[(t // 2, child)]
            perm.extend(range(lo, lo + ln))
        blocks.append(dense[t])
    stages.append((np.asarray(perm),
                   sp.block_diag(blocks, format="csr")))

    compiled = []
    in_len = N
    for perm, S in stages:
        compiled.append(S.tocsr() if perm is None
                        else _fold_gather(S, perm, in_len))
        in_len = S.shape[0]
    return dict(N=N, depth=D, stages=compiled, ids=ids)


def _fold_gather(S, perm, in_len):
    """M with M @ y == S @ y[perm] (perm may repeat entries). Provided."""
    m = len(perm)
    G = sp.csr_matrix((np.ones(m), (np.arange(m), perm)),
                      shape=(m, in_len))
    return (S @ G).tocsr()


def _offsets(order, sizes):
    out, pos = {}, 0
    for key in order:
        out[key] = (pos, sizes[key])
        pos += sizes[key]
    return out


def butterfly_apply(factors, xvec):
    """Return ~ P @ xvec using the compiled stages."""
    y = np.asarray(xvec, dtype=float)
    # TODO(4): apply the chain of compiled sparse factors, in order.
    raise NotImplementedError("apply")
    return y


def butterfly_nnz(factors):
    """Total stored entries (memory proxy) of the factorization."""
    return int(sum(S.nnz for S in factors["stages"]))


def max_rank(factors):
    """Largest skeleton size encountered (diagnostic)."""
    return max(len(J) for J, _ in factors["ids"].values())

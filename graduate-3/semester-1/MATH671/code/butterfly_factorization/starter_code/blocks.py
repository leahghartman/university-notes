"""Dyadic block structure for the Legendre--Vandermonde matrix (provided).

The butterfly pairs a dyadic tree on the target nodes (rows; intervals
in theta = arccos x) with a dyadic tree on the polynomial degrees
(columns; degree bands). At sweep stage `ell`, target nodes at depth
`ell` pair with degree nodes at depth `depth - ell`, and each such block
satisfies the complementary low-rank condition -- except near the
endpoints theta = 0, pi, where the interior asymptotics degenerate.
Those blocks are flagged.
"""

import numpy as np


def tree_intervals(N, depth):
    """Contiguous index intervals [lo, hi) of a dyadic tree over range(N).

    Returns a dict: (level, node) -> (lo, hi), for level = 0..depth,
    node = 0..2^level - 1.
    """
    iv = {}
    for level in range(depth + 1):
        m = 2**level
        edges = np.linspace(0, N, m + 1).astype(int)
        for t in range(m):
            iv[(level, t)] = (edges[t], edges[t + 1])
    return iv


def dyadic_blocks(N, level, depth=None, boundary_frac=0.03):
    """Row/column index sets of the complementary blocks at one sweep stage.

    Parameters
    ----------
    N : matrix size (rows = Gauss nodes, cols = degrees 0..N-1)
    level : target-tree depth `ell` of the stage (0 <= ell <= depth)
    depth : total tree depth (default: chosen so leaves have ~32 indices)
    boundary_frac : fraction of the theta-range near each endpoint whose
        blocks are flagged as boundary blocks

    Returns
    -------
    list of dicts with keys:
        'rows'     : (lo, hi) row interval
        'cols'     : (lo, hi) column interval
        'tnode'    : (level, t) target-tree node
        'snode'    : (depth - level, s) degree-tree node
        'boundary' : bool, True if the block touches the flagged region
    """
    if depth is None:
        depth = default_depth(N)
    assert 0 <= level <= depth
    iv = tree_intervals(N, depth)
    out = []
    n_bd = max(1, int(boundary_frac * N))
    for t in range(2**level):
        rlo, rhi = iv[(level, t)]
        is_bd = (rlo < n_bd) or (rhi > N - n_bd)
        for s in range(2 ** (depth - level)):
            clo, chi = iv[(depth - level, s)]
            out.append(dict(rows=(rlo, rhi), cols=(clo, chi),
                            tnode=(level, t), snode=(depth - level, s),
                            boundary=is_bd))
    return out


def default_depth(N, leaf=32):
    """Tree depth such that leaves hold about `leaf` indices."""
    d = int(np.log2(max(N // leaf, 1)))
    return max(d, 1)

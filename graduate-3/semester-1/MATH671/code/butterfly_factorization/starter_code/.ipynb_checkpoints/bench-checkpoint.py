"""Benchmark and figure harness for Tasks 1--4 (provided).

Usage:
    python -m p1.bench task1          # rank diagnostics -> figs/F1.png
    python -m p1.bench task3          # accuracy + timing -> figs/F2, F3
Both accept --solution to run against the instructor solution if
present (for TA use); by default they import your p1.butterfly.
"""

import argparse
import os
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .legendre import gauss_legendre, legendre_vandermonde, eval_block
from .blocks import dyadic_blocks, default_depth

FIGDIR = os.path.join(os.path.dirname(__file__), "..", "figs")


def _butterfly_module(use_solution=False):
    if use_solution:
        from instructor import butterfly_solution as B
    else:
        from . import butterfly as B
    return B


def eps_rank(A, eps):
    s = np.linalg.svd(A, compute_uv=False)
    if s[0] == 0:
        return 0
    return int(np.sum(s > eps * s[0]))


def task1(N=4096, levels=None, epss=(1e-3, 1e-6, 1e-9), sample=4):
    """Epsilon-ranks of the complementary blocks at several stages."""
    os.makedirs(FIGDIR, exist_ok=True)
    D = default_depth(N)
    if levels is None:
        levels = [1, D // 2, D - 1]
    x, _ = gauss_legendre(N)
    rng = np.random.default_rng(0)
    fig, axes = plt.subplots(1, len(levels), figsize=(4 * len(levels), 3.2),
                             sharey=True)
    for ax, ell in zip(np.atleast_1d(axes), levels):
        blocks = dyadic_blocks(N, ell)
        for eps in epss:
            ranks, is_bd = [], []
            for b in blocks:
                rlo, rhi = b["rows"]
                clo, chi = b["cols"]
                cols = np.arange(clo, chi)
                nrow = min(rhi - rlo, sample * len(cols))
                rows = np.sort(rng.choice(np.arange(rlo, rhi), size=nrow,
                                          replace=False))
                A = eval_block(rows, cols, x)
                ranks.append(eps_rank(A, eps))
                is_bd.append(b["boundary"])
            ranks = np.array(ranks)
            is_bd = np.array(is_bd)
            idx = np.arange(len(ranks))
            ax.plot(idx[~is_bd], ranks[~is_bd], ".",
                    label=f"interior, eps={eps:g}")
            ax.plot(idx[is_bd], ranks[is_bd], "x",
                    label=f"boundary, eps={eps:g}")
        ax.set_title(f"stage ell={ell} (of {D})")
        ax.set_xlabel("block index")
    np.atleast_1d(axes)[0].set_ylabel("eps-rank")
    np.atleast_1d(axes)[0].legend(fontsize=7)
    fig.suptitle(f"F1: complementary block ranks, N={N}")
    fig.tight_layout()
    out = os.path.join(FIGDIR, "F1_ranks.png")
    fig.savefig(out, dpi=160)
    print("wrote", out)


def task3(Ns=(1024, 2048, 4096, 8192), tols=(1e-3, 1e-6, 1e-9),
          use_solution=False, dense_max=8192):
    """F2: error vs tolerance (fixed N). F3: timing vs N."""
    os.makedirs(FIGDIR, exist_ok=True)
    B = _butterfly_module(use_solution)

    # ---- F2: accuracy at N = Ns[-2] ----
    Nerr = Ns[min(len(Ns) - 1, 2)]
    P = legendre_vandermonde(Nerr)
    v = np.random.default_rng(1).standard_normal(Nerr)
    yd = P @ v
    errs = []
    for tol in tols:
        f = B.butterfly_setup(Nerr, tol=tol)
        y = B.butterfly_apply(f, v)
        errs.append(np.linalg.norm(y - yd) / np.linalg.norm(yd))
        print(f"  N={Nerr} tol={tol:g}: rel err {errs[-1]:.2e}, "
              f"nnz/N^2 {B.butterfly_nnz(f)/Nerr**2:.3f}, "
              f"rmax {B.max_rank(f)}")
    fig, ax = plt.subplots(figsize=(4, 3.2))
    ax.loglog(tols, errs, "o-", label="measured")
    ax.loglog(tols, tols, "k--", label="tol")
    ax.set_xlabel("ID tolerance")
    ax.set_ylabel("relative error")
    ax.legend()
    ax.set_title(f"F2: accuracy vs tolerance, N={Nerr}")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "F2_accuracy.png"), dpi=160)
    print("wrote figs/F2_accuracy.png")

    # ---- F3: timing ----
    t_bf, t_dn, kept = [], [], []
    for N in Ns:
        f = B.butterfly_setup(N, tol=1e-6)
        v = np.random.default_rng(1).standard_normal(N)
        reps = max(3, int(2e7 // (N * 40)))
        t0 = time.time()
        for _ in range(reps):
            y = B.butterfly_apply(f, v)
        tb = (time.time() - t0) / reps
        if N <= dense_max:
            P = legendre_vandermonde(N)
            t0 = time.time()
            for _ in range(reps):
                P @ v
            td = (time.time() - t0) / reps
        else:
            td = np.nan
        t_bf.append(tb)
        t_dn.append(td)
        kept.append(N)
        print(f"  N={N}: butterfly {tb*1e3:.2f} ms, dense {td*1e3:.2f} ms")
    kept = np.array(kept, float)
    fig, ax = plt.subplots(figsize=(4, 3.2))
    ax.loglog(kept, t_bf, "o-", label="butterfly")
    ax.loglog(kept, t_dn, "s-", label="dense")
    ax.loglog(kept, np.array(t_bf)[0] * (kept / kept[0]) * np.log2(kept)
              / np.log2(kept[0]), "k:", label="N log N")
    ax.loglog(kept, np.nanmax([t_dn[0], 1e-6]) * (kept / kept[0])**2,
              "k--", label="N^2")
    ax.set_xlabel("N")
    ax.set_ylabel("apply time (s)")
    ax.legend(fontsize=8)
    ax.set_title("F3: apply cost")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "F3_timing.png"), dpi=160)
    print("wrote figs/F3_timing.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("task", choices=["task1", "task3"])
    ap.add_argument("--solution", action="store_true",
                    help="use instructor solution (TA testing)")
    args = ap.parse_args()
    if args.task == "task1":
        task1()
    else:
        task3(use_solution=args.solution)

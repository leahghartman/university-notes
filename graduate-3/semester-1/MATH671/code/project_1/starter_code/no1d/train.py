"""Training and evaluation for Tasks 6--7 (provided; requires PyTorch).

Usage:
    python -m p1.no1d.train task6            # F5(a): a -> u, fixed f
    python -m p1.no1d.train task6b           # F5(b): (a, f) -> u
    python -m p1.no1d.train task7            # plain-Poisson control

Each command trains the padded-Fourier FNO and the Legendre NO at
matched parameter budgets across a range of training-set sizes and
writes the error curves and a sample prediction to figs/.
"""

import argparse
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import torch
import torch.nn as nn

from .data import generate_dataset
from .models import FNO1d, LegNO1d, LinearMap

FIGDIR = os.path.join(os.path.dirname(__file__), "..", "..", "figs")


def rel_l2(pred, true):
    return (torch.linalg.norm(pred - true, dim=-1)
            / torch.linalg.norm(true, dim=-1)).mean().item()


def _tensors(data, grid, fields):
    xs = np.stack([data[f"{f}_{grid}"] for f in fields], axis=1)
    ys = data[f"u_{grid}"]
    return (torch.tensor(xs, dtype=torch.float32),
            torch.tensor(ys, dtype=torch.float32))


def train_model(model, X, Y, Xte, Yte, epochs=400, lr=2e-3, bs=32,
                verbose=False):
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    n = X.shape[0]
    for ep in range(epochs):
        perm = torch.randperm(n)
        for i in range(0, n, bs):
            idx = perm[i:i + bs]
            opt.zero_grad()
            loss = torch.mean(
                (model(X[idx]) - Y[idx])**2) / torch.mean(Y[idx]**2)
            loss.backward()
            opt.step()
        sched.step()
        if verbose and ep % 100 == 0:
            print(f"    ep {ep}: train {loss.item():.3e}, "
                  f"test {rel_l2(model(Xte), Yte):.3e}")
    with torch.no_grad():
        return rel_l2(model(Xte), Yte)


def run(vary_f=False, task7=False, n_grid=256, n_test=200,
        train_sizes=(50, 100, 200, 400), epochs=400, seed=0, tag="task6"):
    os.makedirs(FIGDIR, exist_ok=True)
    fields = ["f"] if task7 else (["a", "f"] if vary_f else ["a"])
    n_max = max(train_sizes)
    n_tot = n_max + n_test
    print(f"generating {n_tot} samples (fields={fields}) ...")
    if task7:
        # plain Poisson: a == 1, sampled f
        from .data import (lgl_nodes, diff_matrix, solve_bvp,
                           random_field, bary_interp)
        from ..legendre import gauss_legendre
        rng = np.random.default_rng(seed)
        x_lgl = lgl_nodes(129)
        Dm = diff_matrix(x_lgl)
        x_eq = np.linspace(-1.0, 1.0, n_grid)
        x_gl, _ = gauss_legendre(n_grid)
        data = {k: np.empty((n_tot, n_grid)) for k in
                ("a_eq", "f_eq", "u_eq", "a_gl", "f_gl", "u_gl")}
        data["x_eq"], data["x_gl"] = x_eq, x_gl
        for g in ("eq", "gl"):
            data[f"a_{g}"][:] = 1.0
        for i in range(n_tot):
            f = random_field(rng, x_lgl, amp=2.0) + 2.0
            u = solve_bvp(np.ones_like(x_lgl), f, Dm)
            for name, vals in (("f", f), ("u", u)):
                data[f"{name}_eq"][i] = bary_interp(x_lgl, vals, x_eq)
                data[f"{name}_gl"][i] = bary_interp(x_lgl, vals, x_gl)
    else:
        data = generate_dataset(n_tot, n_grid=n_grid, vary_f=vary_f,
                                seed=seed)

    Xeq, Yeq = _tensors(data, "eq", fields)
    Xgl, Ygl = _tensors(data, "gl", fields)
    results = {}
    models = {}

    def make_models():
        m = {"FNO (padded)": (FNO1d(n_grid, in_fields=len(fields)),
                              Xeq, Yeq),
             "LegNO": (LegNO1d(n_grid, in_fields=len(fields)),
                       Xgl, Ygl)}
        if task7:
            m["Linear map"] = (LinearMap(n_grid), Xeq, Yeq)
        return m

    for ntr in train_sizes:
        for name, (model, X, Y) in make_models().items():
            err = train_model(model, X[:ntr], Y[:ntr],
                              X[n_max:], Y[n_max:], epochs=epochs)
            results.setdefault(name, []).append(err)
            models[name] = (model, X, Y)
            print(f"  n_train={ntr:5d}  {name:14s} rel L2 = {err:.3e}")

    # error curves
    fig, ax = plt.subplots(figsize=(4.2, 3.4))
    for name, errs in results.items():
        ax.loglog(train_sizes, errs, "o-", label=name)
    ax.set_xlabel("training samples")
    ax.set_ylabel("relative L2 test error")
    ax.legend(fontsize=8)
    ax.set_title(f"F5: {tag}")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, f"F5_{tag}_curves.png"), dpi=160)

    # sample prediction
    fig, ax = plt.subplots(figsize=(4.2, 3.4))
    with torch.no_grad():
        for name, (model, X, Y) in models.items():
            xg = data["x_gl"] if name == "LegNO" else data["x_eq"]
            ax.plot(xg, model(X[n_max:n_max + 1])[0].numpy(), "--",
                    label=name)
    ax.plot(data["x_eq"], data["u_eq"][n_max], "k-", lw=1, label="true")
    ax.set_xlabel("x")
    ax.set_ylabel("u")
    ax.legend(fontsize=8)
    ax.set_title("representative prediction")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, f"F5_{tag}_sample.png"), dpi=160)
    print("wrote figs/F5_%s_*.png" % tag)
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("task", choices=["task6", "task6b", "task7"])
    ap.add_argument("--epochs", type=int, default=400)
    args = ap.parse_args()
    if args.task == "task6":
        run(vary_f=False, epochs=args.epochs, tag="task6")
    elif args.task == "task6b":
        run(vary_f=True, epochs=args.epochs, tag="task6b")
    else:
        run(task7=True, epochs=args.epochs, tag="task7")

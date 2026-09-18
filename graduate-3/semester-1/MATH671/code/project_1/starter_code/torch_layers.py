"""Trainable butterfly layers for Task 5 (provided).

Two modules:

* ButterflyLinear -- a linear layer whose *sparsity pattern* is a chain
  of butterfly stage factors. The pattern is fixed; the nonzero values
  are the trainable parameters.
    - init_random():        keep the pattern, draw random values;
    - init_from_factors(f): copy the values of your Part I factorization
      (so the layer starts as your fast Legendre transform, exactly).
  Construct the pattern either from your Part I factors
  (ButterflyLinear.from_factors) or as the classical radix-2 FFT
  pattern (ButterflyLinear.radix2) when you want the generic shape.

* DenseLinear -- the N^2-parameter baseline for the comparison in F4.

Requires PyTorch. The rest of the Part I code has no torch dependency.
"""

import numpy as np

try:
    import torch
    import torch.nn as nn
    _HAVE_TORCH = True
except ImportError:  # pragma: no cover
    _HAVE_TORCH = False

    class nn:  # minimal shim so the module imports without torch
        Module = object


class ButterflyLinear(nn.Module):
    """y = S_L ... S_1 S_0 x with fixed sparsity patterns and trainable
    nonzero values."""

    def __init__(self, patterns, shape):
        """patterns: list of (row_idx, col_idx, shape) per stage, in
        application order. shape: (out_dim, in_dim) of the whole map."""
        if not _HAVE_TORCH:
            raise ImportError("PyTorch is required for ButterflyLinear")
        super().__init__()
        self.shape = shape
        self.stage_meta = []
        self.values = nn.ParameterList()
        for rows, cols, shp in patterns:
            idx = torch.tensor(np.vstack([rows, cols]), dtype=torch.long)
            self.stage_meta.append((idx, shp))
            self.values.append(nn.Parameter(torch.zeros(len(rows))))
        self.init_random()

    # ---------------- constructors ----------------
    @classmethod
    def from_factors(cls, factors):
        """Build the layer with the sparsity pattern of a compiled
        Part I factorization (values randomly initialized; call
        init_from_factors to start from the computed transform)."""
        patterns = []
        for S in factors["stages"]:
            S = S.tocoo()
            patterns.append((S.row, S.col, S.shape))
        N = factors["N"]
        return cls(patterns, (N, N))

    @classmethod
    def radix2(cls, N):
        """Classical radix-2 butterfly pattern: log2(N) stages, each with
        2N nonzeros (pairs at stride 2^level), plus bit-reversal."""
        if not _HAVE_TORCH:
            raise ImportError("PyTorch is required for ButterflyLinear")
        L = int(np.log2(N))
        assert 2**L == N, "radix2 pattern needs N = 2^L"
        # bit-reversal permutation as a fixed first stage (identity values
        # would also work; we fold it into the first pattern)
        rev = np.array([int(format(i, f"0{L}b")[::-1], 2)
                        for i in range(N)])
        patterns = []
        # stage 0: permutation pattern (trainable scalars on the perm)
        patterns.append((np.arange(N), rev, (N, N)))
        for level in range(L):
            stride = 2**level
            rows, cols = [], []
            for i in range(N):
                partner = i ^ stride
                rows.extend([i, i])
                cols.extend([i, partner])
            patterns.append((np.array(rows), np.array(cols), (N, N)))
        return cls(patterns, (N, N))

    # ---------------- initializers ----------------
    def init_random(self):
        for p in self.values:
            nn.init.normal_(p, std=1.0 / np.sqrt(max(len(p), 1)))

    def init_from_factors(self, factors):
        """Copy the numeric values of a compiled factorization whose
        pattern this layer was built from (see from_factors)."""
        if len(factors["stages"]) != len(self.values):
            raise ValueError("factorization does not match this "
                             "layer's pattern (build the layer with "
                             "from_factors)")
        for p, S in zip(self.values, factors["stages"]):
            S = S.tocoo()
            if len(S.data) != len(p):
                raise ValueError("stage nnz mismatch; pattern was not "
                                 "built from these factors")
            with torch.no_grad():
                p.copy_(torch.tensor(S.data, dtype=p.dtype))

    # ---------------- forward ----------------
    def forward(self, x):
        """x: (..., in_dim) -> (..., out_dim)."""
        single = x.dim() == 1
        lead = x.shape[:-1]
        y = x.unsqueeze(0) if single else x.reshape(-1, x.shape[-1])
        for (idx, shp), vals in zip(self.stage_meta, self.values):
            S = torch.sparse_coo_tensor(idx, vals, size=shp)
            y = torch.sparse.mm(S, y.T).T
        return y.squeeze(0) if single else y.reshape(*lead, y.shape[-1])

    def n_parameters(self):
        return sum(len(p) for p in self.values)


class DenseLinear(nn.Module):
    """N^2-parameter dense baseline."""

    def __init__(self, N):
        if not _HAVE_TORCH:
            raise ImportError("PyTorch is required for DenseLinear")
        super().__init__()
        self.lin = nn.Linear(N, N, bias=False)

    def forward(self, x):
        return self.lin(x)

    def n_parameters(self):
        return self.lin.weight.numel()

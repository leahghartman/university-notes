"""Neural-operator models for Tasks 6--7 (provided; requires PyTorch).

* FNO1d       -- Fourier neural operator with zero-padding for the
                 non-periodic domain (the baseline).
* LegNO1d     -- the same architecture with the Fourier transform
                 replaced by the Legendre transform (learned multipliers
                 on Legendre coefficients). Uses the dense
                 analysis/synthesis matrices by default; you may swap in
                 your fast butterfly apply, but at n_grid=256 dense is
                 fine -- the point of Task 6 is the basis, not the speed.
* LinearMap   -- single linear layer f -> u for the Task 7 control.
"""

import numpy as np

try:
    import torch
    import torch.nn as nn
    _HAVE_TORCH = True
except ImportError:  # pragma: no cover
    _HAVE_TORCH = False

    class nn:
        Module = object

from ..legendre import analysis_matrix, synthesis_matrix


# ------------------------- Fourier branch ----------------------------

class SpectralConv1d(nn.Module):
    """Fourier layer: rfft -> learned complex multipliers on kmax modes
    -> irfft."""

    def __init__(self, width, kmax):
        super().__init__()
        self.kmax = kmax
        scale = 1.0 / (width * width)
        self.w = nn.Parameter(
            scale * torch.randn(width, width, kmax, dtype=torch.cfloat))

    def forward(self, v):
        # v: (batch, width, n)
        vh = torch.fft.rfft(v)
        out = torch.zeros_like(vh)
        k = min(self.kmax, vh.shape[-1])
        out[:, :, :k] = torch.einsum("bix,iox->box", vh[:, :, :k],
                                     self.w[:, :, :k])
        return torch.fft.irfft(out, n=v.shape[-1])


class LegendreSpectralConv1d(nn.Module):
    """Legendre layer: analysis -> learned real multipliers on the first
    kmax coefficients -> synthesis. A (analysis) and S (synthesis) are
    fixed; only the mode-mixing weights train."""

    def __init__(self, width, kmax, n_grid):
        super().__init__()
        self.kmax = kmax
        A = analysis_matrix(n_grid)[:kmax, :]        # (kmax, n)
        S = synthesis_matrix(n_grid)[:, :kmax]       # (n, kmax)
        self.register_buffer("A", torch.tensor(A, dtype=torch.float32))
        self.register_buffer("S", torch.tensor(S, dtype=torch.float32))
        scale = 1.0 / (width * width)
        self.w = nn.Parameter(scale * torch.randn(width, width, kmax))

    def forward(self, v):
        # v: (batch, width, n)
        c = torch.einsum("kn,bin->bik", self.A, v)
        c = torch.einsum("bik,iok->bok", c, self.w)
        return torch.einsum("nk,bok->bon", self.S, c)


# ------------------------- shared trunk ------------------------------

class _NO1d(nn.Module):
    def __init__(self, spectral_layers, width, in_ch):
        super().__init__()
        self.lift = nn.Conv1d(in_ch, width, 1)
        self.spec = nn.ModuleList(spectral_layers)
        self.loc = nn.ModuleList(
            [nn.Conv1d(width, width, 1) for _ in spectral_layers])
        self.proj1 = nn.Conv1d(width, width, 1)
        self.proj2 = nn.Conv1d(width, 1, 1)

    def _trunk(self, v):
        v = self.lift(v)
        for spec, loc in zip(self.spec, self.loc):
            v = torch.nn.functional.gelu(spec(v) + loc(v))
        return self.proj2(torch.nn.functional.gelu(self.proj1(v)))


class FNO1d(_NO1d):
    """Padded-Fourier baseline. Input channels: fields + coordinate."""

    def __init__(self, n_grid, width=32, kmax=16, layers=4, in_fields=1,
                 pad=32):
        if not _HAVE_TORCH:
            raise ImportError("PyTorch required")
        self.pad = pad
        spec = [SpectralConv1d(width, kmax) for _ in range(layers)]
        super().__init__(spec, width, in_fields + 1)
        x = torch.linspace(-1, 1, n_grid)
        self.register_buffer("coord", x[None, None, :])

    def forward(self, fields):
        # fields: (batch, in_fields, n)
        b = fields.shape[0]
        v = torch.cat([fields, self.coord.expand(b, -1, -1)], dim=1)
        v = torch.nn.functional.pad(v, (0, self.pad))   # zero-pad right
        out = self._trunk(v)
        return out[:, 0, :fields.shape[-1]]


class LegNO1d(_NO1d):
    """Legendre neural operator on the Gauss grid; no padding needed."""

    def __init__(self, n_grid, width=32, kmax=16, layers=4, in_fields=1):
        if not _HAVE_TORCH:
            raise ImportError("PyTorch required")
        spec = [LegendreSpectralConv1d(width, kmax, n_grid)
                for _ in range(layers)]
        super().__init__(spec, width, in_fields + 1)
        from ..legendre import gauss_legendre
        x, _ = gauss_legendre(n_grid)
        self.register_buffer("coord",
                             torch.tensor(x, dtype=torch.float32)[None, None, :])

    def forward(self, fields):
        b = fields.shape[0]
        v = torch.cat([fields, self.coord.expand(b, -1, -1)], dim=1)
        return self._trunk(v)[:, 0, :]


class LinearMap(nn.Module):
    """Task 7 control: a single linear map f -> u (no bias)."""

    def __init__(self, n_grid):
        if not _HAVE_TORCH:
            raise ImportError("PyTorch required")
        super().__init__()
        self.lin = nn.Linear(n_grid, n_grid, bias=False)

    def forward(self, fields):
        # fields: (batch, 1, n)
        return self.lin(fields[:, 0, :])

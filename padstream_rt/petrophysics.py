"""Porosity / permeability evolution and transmissibility refresh.

Porosity from mineral volume balance (review Part 1.5):
    phi = 1 - phi_inert - sum_m vf_m,   phi_inert = 1 - phi0 - sum_m vf_m,0

Permeability laws (review Part 11.2):
    Kozeny-Carman   k/k0 = (phi/phi0)^3 * ((1-phi0)/(1-phi))^2
    Verma-Pruess    k/k0 = ((phi - phi_c)/(phi0 - phi_c))^n   (Verma & Pruess 1988)
    Learned         k/k0 = g_theta(phi, phi0, features), guarded:
                    * falls back to Kozeny-Carman outside the training phi range,
                    * must not move opposite to the porosity change,
                    * ratio clipped to [ratio_min, ratio_max].

Transmissibilities follow V15-SG2 exactly (harmonic face permeability,
kz = KV_KH * k handled by the caller through the perm tensor), returned in
mD*ft/cP so that they can be fed to the existing SG3 pressure solve.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import numpy as np

from .state import FT_TO_M, MD_TO_M2, GridGeometry, ReactiveState


def update_porosity(state: ReactiveState, vf_old: np.ndarray) -> np.ndarray:
    """Return new porosity after mineral volume fractions changed from vf_old."""
    dvf = (state.mineral_vf - vf_old).sum(axis=1)
    return np.clip(state.porosity - dvf, 1e-6, 1.0)


def kozeny_carman(phi, phi0):
    return (phi / phi0) ** 3 * ((1.0 - phi0) / (1.0 - phi)) ** 2


def verma_pruess(phi, phi0, phi_c=0.0, n=2.0):
    num = np.clip(phi - phi_c, 0.0, None)
    return (num / np.maximum(phi0 - phi_c, 1e-12)) ** n


@dataclass
class LearnedPermeability:
    """Guarded wrapper for a learned phi->k closure (claim 4 of the review)."""

    model: Callable[[np.ndarray, np.ndarray], np.ndarray]
    phi_train_min: float
    phi_train_max: float
    ratio_min: float = 1e-3
    ratio_max: float = 1e3

    def __call__(self, phi, phi0, phi_prev=None, ratio_prev=None):
        kc = kozeny_carman(phi, phi0)
        try:
            r = np.asarray(self.model(phi, phi0), dtype=float)
        except Exception:
            return kc, np.ones_like(phi, dtype=bool)
        fb = ~np.isfinite(r) | (phi < self.phi_train_min) | (phi > self.phi_train_max)
        if phi_prev is not None and ratio_prev is not None:
            dphi = phi - phi_prev
            fb |= (dphi > 0) & (r < ratio_prev) | (dphi < 0) & (r > ratio_prev)
        r = np.where(fb, kc, r)
        return np.clip(r, self.ratio_min, self.ratio_max), fb


def update_permeability(state: ReactiveState, law: str | LearnedPermeability = "kozeny_carman",
                        phi_prev: Optional[np.ndarray] = None, **kw) -> Tuple[np.ndarray, np.ndarray]:
    """Return (new perm (n,3) in m^2, fallback mask)."""
    phi, phi0 = state.porosity, state.porosity0
    fb = np.zeros_like(phi, dtype=bool)
    if isinstance(law, LearnedPermeability):
        ratio_prev = (state.perm[:, 0] / state.perm0[:, 0]) if phi_prev is not None else None
        ratio, fb = law(phi, phi0, phi_prev, ratio_prev)
    elif law == "kozeny_carman":
        ratio = kozeny_carman(phi, phi0)
    elif law == "verma_pruess":
        ratio = verma_pruess(phi, phi0, **kw)
    else:
        raise ValueError(f"unknown permeability law {law!r}")
    return state.perm0 * ratio[:, None], fb


def harmonic_average(a, b):
    return 2.0 * a * b / (a + b)


def transmissibilities_field_units(perm_m2: np.ndarray, geom: GridGeometry, mu_cp: float):
    """(tx, ty, tz) in mD*ft/cP with the V15-SG2 shapes:
    tx (NZ, NY, NX-1), ty (NZ, NY-1, NX), tz (NZ-1, NY, NX)."""
    k = perm_m2.reshape(geom.shape + (3,)) / MD_TO_M2
    dx, dy, dz = geom.dx / FT_TO_M, geom.dy / FT_TO_M, geom.dz / FT_TO_M
    kfx = harmonic_average(k[:, :, :-1, 0], k[:, :, 1:, 0])
    kfy = harmonic_average(k[:, :-1, :, 1], k[:, 1:, :, 1])
    kfz = harmonic_average(k[:-1, :, :, 2], k[1:, :, :, 2])
    tx = kfx * (dy * dz) / (mu_cp * dx)
    ty = kfy * (dx * dz) / (mu_cp * dy)
    tz = kfz * (dx * dy) / (mu_cp * dz)
    return tx, ty, tz


def needs_retrace(perm_old: np.ndarray, perm_new: np.ndarray, rel_tol: float = 0.02) -> bool:
    """Retrace streamlines when any cell's permeability changed by > rel_tol."""
    return bool(np.max(np.abs(perm_new / perm_old - 1.0)) > rel_tol)

"""State containers for reactive transport on the PAD-Stream 3D grid.

Conventions (match V15-SG1..SG7):
    * Grid arrays are shaped (NZ, NY, NX) and flattened in C order.
    * SI units internally: m, s, m^3, mol, Pa, K.  Permeability in m^2.
    * Aqueous composition is stored as *total component* amounts
      (mol per m^3 of brine) so that transport is linear in the state and
      element conservation can be checked exactly.

The chemistry is described by a component basis (rows of the formula matrix
``A``).  Every species or mineral is a column of ``A``; a reaction is
conservative iff it leaves ``A @ n_total`` unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

FT_TO_M = 0.3048
MD_TO_M2 = 9.869233e-16


@dataclass(frozen=True)
class GridGeometry:
    """Cartesian corner-point-free grid used by V15-SG1..SG7."""

    nx: int = 50
    ny: int = 50
    nz: int = 15
    dx: float = 20.0 * FT_TO_M
    dy: float = 20.0 * FT_TO_M
    dz: float = 4.0 * FT_TO_M

    @property
    def shape(self):
        return (self.nz, self.ny, self.nx)

    @property
    def ncell(self) -> int:
        return self.nx * self.ny * self.nz

    @property
    def cell_volume(self) -> float:
        return self.dx * self.dy * self.dz

    def cell_index(self, xyz: np.ndarray) -> np.ndarray:
        """Flat (C-order) cell index for points ``xyz`` (N, 3) in metres.

        Points exactly on the upper domain boundary are assigned to the last
        cell, matching Pollock tracing that terminates on faces.
        """
        xyz = np.atleast_2d(np.asarray(xyz, dtype=float))
        i = np.clip((xyz[:, 0] // self.dx).astype(np.int64), 0, self.nx - 1)
        j = np.clip((xyz[:, 1] // self.dy).astype(np.int64), 0, self.ny - 1)
        k = np.clip((xyz[:, 2] // self.dz).astype(np.int64), 0, self.nz - 1)
        return (k * self.ny + j) * self.nx + i


@dataclass
class Mineral:
    """One reacting mineral, written as a dissolution reaction.

    ``nu`` gives the stoichiometric coefficients of the *aqueous components*
    released when one mole of mineral dissolves (negative = consumed), in the
    order of ``ChemicalSystem.components``.  ``molar_volume`` in m^3/mol.
    ``log10_K`` is a callable of temperature (K) or a constant.
    Kinetic parameters follow Palandri & Kharaka (2004): log10 k25 in
    mol m^-2 s^-1, E in J/mol, and the H+ / OH- reaction orders.
    """

    name: str
    nu: Sequence[float]
    molar_volume: float
    log10_K: object
    log10_k25_neutral: float
    E_neutral: float
    log10_k25_acid: Optional[float] = None
    E_acid: Optional[float] = None
    n_acid: float = 0.0
    log10_k25_base: Optional[float] = None
    E_base: Optional[float] = None
    n_base: float = 0.0
    log10_k25_carb: Optional[float] = None   # carbonate mechanism (PK 2004 Table 33)
    E_carb: Optional[float] = None
    n_carb: float = 0.0                      # order with respect to P(CO2)
    specific_area: float = 1.0e3  # m^2 per m^3 of mineral (geometric proxy)
    theta: float = 1.0
    eta: float = 1.0

    def logK(self, T: float) -> float:
        return float(self.log10_K(T)) if callable(self.log10_K) else float(self.log10_K)


@dataclass
class ChemicalSystem:
    """Component basis + minerals.

    ``components`` are transported totals (e.g. ["C", "Ca", "Mg", "Fe", "Si",
    "Al", "Na", "K", "Cl", "H+"]).  Charge/proton balance is the user's
    responsibility for the component choice; the coupling only requires that
    mineral reactions be expressed in the same basis.
    ``c_eq_scale`` (mol/m^3 brine) is the characteristic equilibrium
    concentration used to non-dimensionalise the Damkohler number, one value
    per mineral.
    """

    components: List[str]
    minerals: List[Mineral]
    c_eq_scale: Optional[np.ndarray] = None

    @property
    def ncomp(self) -> int:
        return len(self.components)

    @property
    def nmin(self) -> int:
        return len(self.minerals)

    @property
    def nu_matrix(self) -> np.ndarray:
        """(nmin, ncomp) dissolution stoichiometry."""
        return np.array([m.nu for m in self.minerals], dtype=float)


@dataclass
class ReactiveState:
    """Per-cell reactive-transport state on the grid (flattened, C order)."""

    geom: GridGeometry
    system: ChemicalSystem
    porosity: np.ndarray              # (ncell,)
    perm: np.ndarray                  # (ncell, 3) kx, ky, kz in m^2
    brine_saturation: np.ndarray      # (ncell,)
    total_aq: np.ndarray              # (ncell, ncomp) mol / m^3 brine
    mineral_vf: np.ndarray            # (ncell, nmin) m^3 mineral / m^3 bulk
    temperature: np.ndarray           # (ncell,) K
    pressure: np.ndarray              # (ncell,) Pa
    porosity0: np.ndarray = field(default=None)
    perm0: np.ndarray = field(default=None)
    regime: np.ndarray = field(default=None)  # (ncell, nmin) int8 damkohler.Regime codes

    def __post_init__(self):
        n = self.geom.ncell
        for name in ("porosity", "brine_saturation", "temperature", "pressure"):
            a = np.asarray(getattr(self, name), dtype=float)
            if a.shape == ():
                a = np.full(n, float(a))
            if a.shape != (n,):
                raise ValueError(f"{name} must have shape ({n},), got {a.shape}")
            setattr(self, name, a.copy())
        self.perm = np.asarray(self.perm, dtype=float).reshape(n, 3).copy()
        self.total_aq = np.asarray(self.total_aq, dtype=float).reshape(n, self.system.ncomp).copy()
        self.mineral_vf = np.asarray(self.mineral_vf, dtype=float).reshape(n, self.system.nmin).copy()
        if self.porosity0 is None:
            self.porosity0 = self.porosity.copy()
        if self.perm0 is None:
            self.perm0 = self.perm.copy()
        if self.regime is None:
            self.regime = np.zeros((n, self.system.nmin), dtype=np.int8)

    # ------------------------------------------------------------------
    # Inventories used by the mass-balance ledger
    # ------------------------------------------------------------------
    def brine_volume(self) -> np.ndarray:
        """m^3 of brine per cell."""
        return self.porosity * self.brine_saturation * self.geom.cell_volume

    def mineral_moles(self) -> np.ndarray:
        """(ncell, nmin) mol of each mineral per cell."""
        vm = np.array([m.molar_volume for m in self.system.minerals])
        return self.mineral_vf * self.geom.cell_volume / vm[None, :]

    def component_inventory(self) -> np.ndarray:
        """Total moles of every component (aqueous + mineral-bound), (ncomp,).

        Mineral-bound moles are counted with the dissolution stoichiometry so
        that dissolution/precipitation leaves this vector unchanged.
        """
        aq = (self.total_aq * self.brine_volume()[:, None]).sum(axis=0)
        bound = self.mineral_moles().sum(axis=0) @ self.system.nu_matrix
        return aq + bound

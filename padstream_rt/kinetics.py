"""Transition-state-theory mineral rate law (Lasaga 1984; Palandri & Kharaka 2004).

    r_m = A_m * k_m(T, a_H+) * sign(1 - Omega) * |1 - Omega^theta|^eta

    k_m = k25_nu  * exp[-E_nu /R (1/T - 1/298.15)]
        + k25_H   * exp[-E_H  /R (1/T - 1/298.15)] * a_H+^n_H
        + k25_OH  * exp[-E_OH /R (1/T - 1/298.15)] * a_H+^n_OH

In Palandri & Kharaka (2004) the base-mechanism order n_OH is reported with
respect to a_H+ and is negative.  ``r_m`` > 0 means dissolution, in
mol of mineral per second per m^3 bulk when ``A_m`` is m^2/m^3 bulk.
"""

from __future__ import annotations

import numpy as np

from .state import Mineral

R_GAS = 8.314462618
T_REF = 298.15


def _arrh(log10_k25, E, T):
    return 10.0 ** log10_k25 * np.exp(-E / R_GAS * (1.0 / T - 1.0 / T_REF))


def rate_constant(m: Mineral, T, pH=7.0, pCO2=None) -> np.ndarray:
    """k_m in mol m^-2 s^-1 (vectorised over T, pH and pCO2).

    The carbonate mechanism of PK 2004 Table 33 (calcite, dolomite,
    magnesite) is added only when ``pCO2`` is given; it must be in the
    partial-pressure units PK used (check their Table 33 text before use).
    """
    T = np.asarray(T, dtype=float)
    aH = 10.0 ** (-np.asarray(pH, dtype=float))
    k = _arrh(m.log10_k25_neutral, m.E_neutral, T)
    if m.log10_k25_acid is not None:
        k = k + _arrh(m.log10_k25_acid, m.E_acid, T) * aH ** m.n_acid
    if m.log10_k25_base is not None:
        k = k + _arrh(m.log10_k25_base, m.E_base, T) * aH ** m.n_base
    if pCO2 is not None and m.log10_k25_carb is not None:
        k = k + _arrh(m.log10_k25_carb, m.E_carb, T) * np.asarray(pCO2, float) ** m.n_carb
    return np.broadcast_to(k, np.broadcast(T, aH).shape).astype(float)


def saturation_ratio(m: Mineral, activities_of_components: np.ndarray, T) -> np.ndarray:
    """Omega = Q/K for the dissolution reaction written in ``m.nu``.

    ``activities_of_components`` is (..., ncomp).  Components with zero
    stoichiometry are ignored; zero activity of a product gives Omega = 0.
    """
    nu = np.asarray(m.nu, dtype=float)
    a = np.clip(activities_of_components, 1e-300, None)
    logQ = (np.log10(a) * nu).sum(axis=-1)
    return 10.0 ** np.clip(logQ - np.vectorize(m.logK)(T), -300.0, 300.0)


def mineral_rate(m: Mineral, area, T, pH, omega) -> np.ndarray:
    """Net dissolution rate per bulk volume (mol m^-3 s^-1)."""
    k = rate_constant(m, T, pH)
    drive = 1.0 - np.power(np.clip(omega, 0.0, None), m.theta)
    if not getattr(m, "precipitate", True):
        drive = np.clip(drive, 0.0, None)
    return area * k * np.sign(drive) * np.abs(drive) ** m.eta


def load_pk_parameters(name: str) -> dict:
    """Kinetic keyword arguments for ``Mineral`` from the sourced table
    ``data/palandri_kharaka_2004_mt_simon.csv`` (PK 2004, printed pages given
    in the file).  Energies are converted from kJ/mol to J/mol.  Stoichiometry,
    molar volume and log K are NOT in PK 2004 and must come from a
    thermodynamic database.
    """
    import csv
    from pathlib import Path
    path = Path(__file__).with_name("data") / "palandri_kharaka_2004_mt_simon.csv"
    rows = {r["mineral"]: r for r in csv.DictReader(open(path, newline=""))}
    if name not in rows:
        raise KeyError(f"{name!r} not in table; available: {sorted(rows)}")
    r = rows[name]
    if not r["neutral_log_k25"] and not r["acid_log_k25"]:
        raise ValueError(f"{name}: no Palandri & Kharaka (2004) parameters ({r['note']})")
    f = lambda k: float(r[k]) if r[k] not in ("", "--") else None
    kJ = lambda k: None if f(k) is None else 1e3 * f(k)
    out = dict(log10_k25_neutral=f("neutral_log_k25"), E_neutral=kJ("neutral_E_kJ"),
               log10_k25_acid=f("acid_log_k25"), E_acid=kJ("acid_E_kJ"), n_acid=f("acid_n_H") or 0.0,
               log10_k25_base=f("base_log_k25"), E_base=kJ("base_E_kJ"), n_base=f("base_n_H") or 0.0,
               log10_k25_carb=f("carbonate_log_k25"), E_carb=kJ("carbonate_E_kJ"),
               n_carb=f("carbonate_n_PCO2") or 0.0)
    if out["log10_k25_neutral"] is None:      # acid-only minerals: neutral term off
        out["log10_k25_neutral"], out["E_neutral"] = -99.0, 0.0
    return out

"""Tests for the oil phase (PR flash), the PHREEQC backend and CO2 partitioning."""

import csv
from pathlib import Path

import numpy as np
import pytest

from padstream_rt.pvt import Fluid, flash, load_sun2020_fwu, molar_density, phase_props, stability

PSI = 6894.757293168
T_FWU = (168.0 - 32.0) * 5.0 / 9.0 + 273.15      # 168 F, Sun et al. 2020 p. 3


def test_pr_pure_co2_density_against_span_wagner():
    CP = pytest.importorskip("CoolProp.CoolProp")
    co2 = Fluid(["CO2"], [304.13], [7.3773e6], [0.22394], [0.04401])
    errs = []
    for T in (313.15, 323.15, 348.85):
        for Pb in (50, 100, 150, 200, 300):
            rho = molar_density(co2, [[1.0]], T, Pb * 1e5)[0] * 0.04401
            ref = CP.PropsSI("D", "T", T, "P", Pb * 1e5, "CO2")
            errs.append(abs(rho - ref) / ref)
    # plain PR (no volume shift): known few-% error, worst near the critical region
    assert np.mean(errs) < 0.05 and max(errs) < 0.12


def test_fwu_bubble_point_matches_reported_value():
    fl, z = load_sun2020_fwu()
    # Sun et al. 2020 p. 3: bubble point 2073.7 psia at 168 F
    lo, hi = 1500.0, 2600.0
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        unstable, _ = stability(fl, z[None], T_FWU, mid * PSI)
        lo, hi = (mid, hi) if unstable[0] else (lo, mid)
    assert abs(0.5 * (lo + hi) - 2073.7) / 2073.7 < 0.05


def test_flash_equal_fugacities_and_mass_balance():
    fl, z = load_sun2020_fwu()
    zz = z * 0.3; zz[0] = 0.7
    r = flash(fl, zz[None], T_FWU, 3000 * PSI)
    assert 0 < r.beta[0] < 1 and r.converged[0]
    _, lpl = phase_props(fl, r.x, T_FWU, 3000 * PSI, "liquid")
    _, lpv = phase_props(fl, r.y, T_FWU, 3000 * PSI, "vapor")
    fx = r.x * np.exp(lpl); fy = r.y * np.exp(lpv)
    np.testing.assert_allclose(fx, fy, rtol=1e-6, atol=1e-14)
    np.testing.assert_allclose((1 - r.beta[0]) * r.x[0] + r.beta[0] * r.y[0], zz, atol=1e-10)


phreeqc = pytest.importorskip("phreeqc")
from padstream_rt.phreeqc_backend import PhreeqcBackend  # noqa: E402
from padstream_rt.chemistry import ChemInput  # noqa: E402


@pytest.fixture(scope="module")
def be():
    return PhreeqcBackend(["Ca", "Mg", "Na", "Cl", "C"], ["Calcite", "Dolomite"])


def test_stoichiometry_from_database(be):
    np.testing.assert_allclose(be.nu, [[1, 0, 0, 0, 1], [1, 1, 0, 0, 2]], atol=1e-8)


def test_co2_solubility_against_duan_sun_2003(be):
    path = Path(__file__).resolve().parents[1] / "padstream_rt" / "data" / "duan_sun_2003_co2_solubility.csv"
    rows = list(csv.DictReader(l for l in open(path) if not l.startswith("#")))
    errs = []
    for r in rows:
        T, P, m, ref = (float(r[k]) for k in ("T_K", "P_bar", "m_NaCl", "m_CO2"))
        P *= 1e5
        # fugacity of pure CO2 at (T, P) with PHREEQC's own constants
        from padstream_rt.phreeqc_backend import CO2_PHREEQC
        _, lp = phase_props(CO2_PHREEQC, [[1.0]], T, P, "stable")
        f = P * np.exp(lp[0, 0])
        naq = np.array([[0, 0, m, m, 0.0]])          # 1 kg water
        up = be.co2_saturation(naq, np.array([1e-3]), np.array([T]), np.array([P]), np.array([f]))[0]
        errs.append(abs(up - ref) / ref)
    assert np.mean(errs) < 0.06 and max(errs) < 0.13     # phreeqc.dat; see module docstring


def test_equilibrium_brings_calcite_to_saturation(be):
    naq = np.array([[0, 0, 0, 0, 1.0e-3]])             # CO2-charged water, 1 kg
    x = ChemInput(naq, np.array([[0.5, 0.0]]), np.array([1e-3]), 1e-3, np.ones((1, 2)) * 10,
                  np.array([323.15]), np.array([1e7]), 3600.0, np.array([[True, False]]))
    xi = be.equilibrium(x)
    assert xi[0, 0] > 0 and xi[0, 1] == 0
    x2 = ChemInput(naq + xi @ be.nu, x.n_min - xi, x.v_brine, 1e-3, x.area, x.T, x.P, 0.0)
    _, si = be.speciate(x2)
    assert abs(si[0, 0]) < 1e-4   # re-speciation ignores the small water mass PHREEQC consumed


def test_co2_partition_conserves_and_prefers_oil_above_mmp():
    from padstream_rt.partition import HydrocarbonState, equilibrate_co2
    be = PhreeqcBackend(["Na", "Cl", "C"], ["Calcite"])
    fl, z = load_sun2020_fwu()
    P = np.array([2000.0, 5000.0]) * PSI
    oil = molar_density(fl, np.tile(z, (2, 1)), T_FWU, P, "liquid")
    n_hc = 0.3 * oil[:, None] * z[None, :]; n_hc[:, 0] = 0.0
    n_hc[:, 0] = 0.2 * molar_density(fl, np.tile(np.eye(len(z))[0], (2, 1)), T_FWU, P, "vapor")
    naq = np.zeros((2, 3)); naq[:, 0] = naq[:, 1] = 500.0     # 0.5 m3 brine, ~1 m NaCl
    hc = HydrocarbonState(fl, n_hc.copy())
    total = hc.n_hc[:, 0] + naq[:, 2]
    r = equilibrate_co2(hc, be, naq, np.full(2, 0.5), T_FWU, P)
    np.testing.assert_allclose(hc.n_hc[:, 0] + naq[:, 2], total, rtol=1e-12)
    np.testing.assert_allclose(r.co2_gas + r.co2_oil, hc.n_hc[:, 0], rtol=1e-6)
    assert r.co2_oil[1] > naq[1, 2] and r.co2_gas[1] < 1e-6 * total[1]   # miscible: no free gas
    left = be.co2_saturation(naq, np.full(2, 0.5), np.full(2, T_FWU), P, r.fugacity)
    assert np.all(np.abs(left) < 1e-5 * total)


def test_reactive_step_with_oil_and_phreeqc():
    from padstream_rt import ReactiveState, RoutingConfig, StreamlineBundle, TransferOperator, reactive_step
    from padstream_rt.kinetics import load_pk_parameters
    from padstream_rt.partition import HydrocarbonState
    from padstream_rt.state import GridGeometry, MD_TO_M2
    be = PhreeqcBackend(["Ca", "Mg", "Na", "Cl", "C"], ["Calcite", "Dolomite"],
                        kinetic_params={"Calcite": load_pk_parameters("calcite"),
                                        "Dolomite": load_pk_parameters("dolomite (disordered)")},
                        specific_area={"Calcite": 1e4, "Dolomite": 1e3},
                        molar_volume={"Calcite": 36.934e-6, "Dolomite": 64.365e-6})
    sysm = be.chemical_system(c_eq_scale=[5.0, 5.0])
    geom = GridGeometry(nx=4, ny=2, nz=1, dx=6.096, dy=6.096, dz=1.2192)
    n = geom.ncell
    st = ReactiveState(geom, sysm, porosity=0.2, perm=np.full((n, 3), 50 * MD_TO_M2),
                       brine_saturation=0.5, total_aq=np.tile([10.0, 5.0, 1000.0, 1000.0, 1.0], (n, 1)),
                       mineral_vf=np.tile([0.02, 0.02], (n, 1)), temperature=T_FWU, pressure=3000 * PSI)
    xs = np.linspace(0, 4 * geom.dx, 17)
    lines = [np.stack([xs, np.full(17, (j + .5) * geom.dy), np.full(17, .5 * geom.dz)], 1) for j in range(2)]
    taus = [xs * 0.2 * geom.dy * geom.dz / 1e-6 for _ in range(2)]
    op = TransferOperator(geom, StreamlineBundle(np.array(lines), np.array(taus), np.full(2, 1e-6)),
                          st.porosity * geom.cell_volume)
    fl, z = load_sun2020_fwu()
    pv = st.porosity * geom.cell_volume
    oil = molar_density(fl, np.tile(z, (n, 1)), T_FWU, st.pressure, "liquid")
    n_hc = (0.3 * pv * oil)[:, None] * z[None, :]
    n_hc[:, 0] = 0.2 * pv * molar_density(fl, np.tile(np.eye(len(z))[0], (n, 1)), T_FWU, st.pressure, "vapor")
    hc = HydrocarbonState(fl, n_hc)
    rep = reactive_step(st, op, be, 86400.0, np.full(n, 0.3), hydrocarbons=hc,
                        routing=RoutingConfig(da_eq=10.0, da_skip=1e-9))
    assert np.all(np.abs(rep.mass_balance_error) < 1e-8), rep.mass_balance_error
    assert np.all(rep.extra["co2_to_brine"] > 0)
    assert np.all(st.mineral_vf[:, 0] < 0.02)          # CO2-charged brine dissolves calcite

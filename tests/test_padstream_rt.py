import numpy as np
import pytest

from padstream_rt import (ChemicalSystem, GridGeometry, LearnedPermeability, Mineral,
                          ReactiveState, ReferenceBackend, Regime, RoutingConfig,
                          StreamlineBundle, SurrogateBackend, TransferOperator,
                          advect_along_streamlines, kozeny_carman, reactive_step, route,
                          transmissibilities_field_units, verma_pruess)
from padstream_rt.chemistry import ChemInput
from padstream_rt.damkohler import reactive_area
from padstream_rt.state import FT_TO_M, MD_TO_M2

# Calcite written in a {Ca, C, H+} total basis: CaCO3 + H+ -> Ca2+ + HCO3-
CALCITE = Mineral("calcite", nu=[1.0, 1.0, -1.0], molar_volume=36.934e-6, log10_K=1.85,
                  log10_k25_neutral=-5.81, E_neutral=23.5e3,
                  log10_k25_acid=-0.30, E_acid=14.4e3, n_acid=1.0, specific_area=1.0e4)


def system():
    return ChemicalSystem(["Ca", "C", "H+"], [CALCITE], c_eq_scale=np.array([5.0]))


def mini_case(nx=8, ny=5, nz=3, phi=0.2, vf_calcite=0.05):
    geom = GridGeometry(nx=nx, ny=ny, nz=nz, dx=6.096, dy=6.096, dz=1.2192)
    n = geom.ncell
    st = ReactiveState(geom, system(), porosity=phi, perm=np.full((n, 3), 100 * MD_TO_M2),
                       brine_saturation=1.0, total_aq=np.tile([1e-3, 1e-3, 1e-4], (n, 1)),
                       mineral_vf=np.full((n, 1), vf_calcite), temperature=323.15,
                       pressure=15e6)
    # straight streamlines along x through every (j, k) column, 2 per column
    Lx = nx * geom.dx
    nnode = 4 * nx + 1
    xs = np.linspace(0.0, Lx, nnode)
    lines, taus, qs = [], [], []
    q = 1e-6
    for k in range(nz):
        for j in range(ny):
            for off in (0.3, 0.7):
                y = (j + off) * geom.dy
                z = (k + 0.5) * geom.dz
                lines.append(np.stack([xs, np.full(nnode, y), np.full(nnode, z)], 1))
                taus.append(xs * (phi * geom.dy * geom.dz / 2) / q)  # PV = q tau
                qs.append(q)
    bundle = StreamlineBundle(np.array(lines), np.array(taus), np.array(qs))
    op = TransferOperator(geom, bundle, st.porosity * geom.cell_volume)
    return st, op


def test_transfer_roundtrip_and_conservation():
    st, op = mini_case()
    rng = np.random.default_rng(0)
    c = rng.random((st.geom.ncell, 3))
    back = op.to_grid(op.to_cv(c), c)
    assert np.allclose(back, c)
    cv = rng.random(op.pv.shape + (3,))
    grid = op.to_grid(cv, c)
    pore = st.porosity * st.geom.cell_volume
    lhs = (grid * pore[:, None])[op.visited].sum(0)
    rhs = (cv * op.pv[..., None]).reshape(-1, 3).sum(0)
    assert np.allclose(lhs, rhs, rtol=1e-12)
    assert np.all(grid >= 0)
    assert np.allclose(op.capacity_ratio[op.visited], 1.0, atol=1e-12)


def test_advection_conserves_and_stays_positive():
    st, op = mini_case()
    c_cv = op.to_cv(st.total_aq)
    ones = np.ones(op.pv.shape)
    cin = np.array([2e-3, 5e-3, 1e-2])
    m0 = (op.pv[..., None] * c_cv).reshape(-1, 3).sum(0)
    c1, out, inn, nsub = advect_along_streamlines(op, c_cv, ones, ones, 30 * 86400.0, cin)
    m1 = (op.pv[..., None] * c1).reshape(-1, 3).sum(0)
    assert np.allclose(m1 - m0, inn - out, rtol=1e-10, atol=1e-14)
    assert np.all(c1 >= 0) and nsub >= 1


def test_routing_limits_and_dilation():
    st, op = mini_case()
    st.mineral_vf[:] = 0.0
    st.mineral_vf[0, 0] = 0.05           # one reactive cell
    reg = route(st, op.residence_time, 86400.0, RoutingConfig(buffer_cells=0))[:, 0]
    assert reg[0] != Regime.SKIP and np.all(reg[1:] == Regime.SKIP)
    st.mineral_vf[1:5, 0] = 1e-12                      # trace mineral, Da_dt below skip
    reg = route(st, op.residence_time, 86400.0, RoutingConfig(buffer_cells=1, da_skip=1e-3))[:, 0]
    assert reg[1] == Regime.KINETIC                    # promoted by the buffer
    st.mineral_vf[:] = 0.05
    reg = route(st, op.residence_time, 86400.0, RoutingConfig(da_eq=1e-30))
    assert np.all(reg == Regime.EQUILIBRIUM)


def _chem_input(n=20, seed=1):
    rng = np.random.default_rng(seed)
    vb = np.full(n, 1.0)
    n_aq = np.column_stack([rng.uniform(1e-4, 1e-1, n), rng.uniform(1e-4, 1e-1, n),
                            10 ** rng.uniform(-6, -1, n)]) * 1000.0  # mol in 1 m3
    n_min = rng.uniform(0.0, 50.0, (n, 1))
    return ChemInput(n_aq, n_min, vb, 1.0, np.full((n, 1), 10.0), np.full(n, 323.15),
                     np.full(n, 15e6), 86400.0)


def test_reference_equilibrium_and_kinetic_bounds():
    ref = ReferenceBackend(system())
    x = _chem_input()
    xi = ref.equilibrium(x)
    n_aq = x.n_aq + xi @ ref.nu
    n_min = x.n_min - xi
    lo = ref._log_omega(0, n_aq, x.v_brine, x.T)
    at_eq = np.abs(lo) < 1e-6
    exhausted = (n_min[:, 0] < 1e-9) | (n_aq.min(1) < 1e-9)
    assert np.all(at_eq | exhausted)
    xk = ref.kinetic(x)
    lo0 = ref._log_omega(0, x.n_aq, x.v_brine, x.T)
    lok = ref._log_omega(0, x.n_aq + xk @ ref.nu, x.v_brine, x.T)
    assert np.all(np.sign(lo0) * lok >= -1e-6)          # never past equilibrium
    assert np.all(np.abs(xk) <= np.abs(xi) + 1e-9)


def test_surrogate_accepts_good_rejects_bad():
    ref = ReferenceBackend(system())
    x = _chem_input()
    good = SurrogateBackend(lambda inp, mode: {"xi": getattr(ref, mode)(inp)}, ref)
    np.testing.assert_allclose(good.equilibrium(x), ref.equilibrium(x))
    assert good.stats.rejected == 0
    assert good.stats.acceptance("equilibrium") == 1.0
    bad = SurrogateBackend(lambda inp, mode: {"xi": -getattr(ref, mode)(inp)}, ref)  # wrong direction
    out = bad.equilibrium(x)
    np.testing.assert_allclose(out, ref.equilibrium(x))
    assert bad.stats.fallback_rate == 1.0
    assert bad.stats.acceptance("equilibrium") == 0.0
    assert bad.stats.offered["equilibrium"] == x.n_aq.shape[0]
    leak = SurrogateBackend(lambda inp, mode: {"xi": ref.equilibrium(inp),
                                               "d_aq": ref.equilibrium(inp) @ ref.nu + 1.0}, ref)
    leak.equilibrium(x)
    assert leak.stats.reasons.get("conservation", 0) == x.n_aq.shape[0]


def test_permeability_laws_and_learned_guard():
    phi0 = np.full(5, 0.2)
    phi = np.array([0.18, 0.2, 0.22, 0.25, 0.3])
    kc = kozeny_carman(phi, phi0)
    assert kc[1] == pytest.approx(1.0) and np.all(np.diff(kc) > 0)
    vp = verma_pruess(phi, phi0, phi_c=0.1, n=2)
    assert vp[1] == pytest.approx(1.0) and np.all(np.diff(vp) > 0)
    # Eq. 6 with k_c: at phi = phi_c, k -> k_c
    assert verma_pruess(np.array([0.1]), np.array([0.2]), phi_c=0.1, n=2, kc_over_k0=0.05)[0] == pytest.approx(0.05)
    learned = LearnedPermeability(lambda p, p0: (p / p0) ** 5, 0.15, 0.24)
    r, fb = learned(phi, phi0)
    assert fb.tolist() == [False, False, False, True, True]
    np.testing.assert_allclose(r[fb], kc[fb])
    wrong = LearnedPermeability(lambda p, p0: np.full_like(p, 0.5), 0.0, 1.0)
    r, fb = wrong(np.full(1, 0.25), np.full(1, 0.2), phi_prev=np.full(1, 0.22), ratio_prev=np.full(1, 1.3))
    assert fb[0]                                        # k fell while phi rose


def test_transmissibility_matches_sg2_formula():
    geom = GridGeometry()
    k_md = np.random.default_rng(3).uniform(1, 500, geom.shape)
    perm = np.stack([k_md, k_md, 0.1 * k_md], -1).reshape(-1, 3) * MD_TO_M2
    tx, ty, tz = transmissibilities_field_units(perm, geom, mu_cp=1.0)
    h = lambda a, b: 2 * a * b / (a + b)
    np.testing.assert_allclose(tx, h(k_md[:, :, :-1], k_md[:, :, 1:]) * 20 * 4 / 20, rtol=1e-10)
    np.testing.assert_allclose(tz, h(0.1 * k_md[:-1], 0.1 * k_md[1:]) * 20 * 20 / 4, rtol=1e-10)
    assert tx.shape == (15, 50, 49) and ty.shape == (15, 49, 50) and tz.shape == (14, 50, 50)


@pytest.mark.parametrize("use_surrogate", [False, True])
def test_end_to_end_acid_injection(use_surrogate):
    st, op = mini_case()
    ref = ReferenceBackend(system())
    backend = ref
    if use_surrogate:
        backend = SurrogateBackend(lambda inp, mode: {"xi": 1.3 * getattr(ref, mode)(inp)}, ref)
    fb = np.ones(st.geom.ncell)
    acid = np.array([1.0, 1.0, 50.0])                   # mol/m3 brine; pH ~1.3
    phi_start = st.porosity.copy()
    for _ in range(5):
        rep = reactive_step(st, op, backend, 10 * 86400.0, fb, c_inlet=acid,
                            routing=RoutingConfig(da_eq=10.0, da_skip=1e-6))
        assert np.all(np.abs(rep.mass_balance_error) < 1e-9), rep.mass_balance_error
        assert np.all(st.total_aq >= -1e-12) and np.all(st.mineral_vf >= 0)
    inlet = st.porosity.reshape(st.geom.shape)[:, :, 0]
    assert np.all(inlet > phi_start.reshape(st.geom.shape)[:, :, 0])   # dissolution at inlet
    assert np.all(st.perm[:, 0] >= st.perm0[:, 0] * (1 - 1e-12))
    assert sum(rep.regime_counts.values()) == st.geom.ncell
    if use_surrogate:
        assert rep.extra["fallback_rate"] > 0


def test_io_reads_sgsim_permeability():
    from pathlib import Path
    from padstream_rt.io import load_sgsim_perm
    root = Path(__file__).resolve().parents[1]
    if not (root / "SGSIM_50x50x15_PERM_MD.csv").exists():
        pytest.skip("SGSIM permeability file not present")
    perm = load_sgsim_perm(root)
    assert perm.shape == (37500, 3)
    np.testing.assert_allclose(perm[:, 2], 0.1 * perm[:, 0])
    assert perm[0, 0] / MD_TO_M2 == pytest.approx(145.65946620)


def test_pk_table_loader_matches_source_values():
    from padstream_rt.kinetics import load_pk_parameters, rate_constant
    p = load_pk_parameters("calcite")
    assert (p["log10_k25_acid"], p["E_acid"], p["n_acid"]) == (-0.30, 14.4e3, 1.0)
    assert (p["log10_k25_neutral"], p["E_neutral"]) == (-5.81, 23.5e3)
    assert (p["log10_k25_carb"], p["n_carb"]) == (-3.48, 1.0)
    kf = load_pk_parameters("K-feldspar")
    assert (kf["log10_k25_base"], kf["n_base"]) == (-21.20, -0.823)
    m = Mineral("calcite", [1, 1, -1], 36.934e-6, 1.85, **p)
    k25 = rate_constant(m, 298.15, pH=0.0)
    assert np.isclose(k25, 10 ** -0.30 + 10 ** -5.81)   # pH 0: acid + neutral
    with pytest.raises(ValueError):
        load_pk_parameters("ankerite")                      # no sourced values
    sid = load_pk_parameters("siderite (provisional; Sun et al. 2020 Table 4)")
    assert (sid["log10_k25_neutral"], sid["E_neutral"]) == (-10.77, 48.0e3)

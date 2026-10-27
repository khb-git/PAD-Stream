import numpy as np
import pytest

from padstream_rt.surrogate import MLP, fit_mlp, positivity_limit


def test_positivity_limit_shared_elements():
    # two minerals precipitate from the same element; only 1 mol is available
    nu = np.array([[1.0, 0.0], [1.0, 1.0]])
    n_aq = np.array([[1.0, 5.0]])
    xi = positivity_limit(np.array([[-1.0, -1.0]]), n_aq, np.array([[0.0, 0.0]]), nu)
    after = n_aq + xi @ nu
    assert after.min() >= -1e-12
    assert xi[0, 0] == pytest.approx(-0.5) and xi[0, 1] == pytest.approx(-0.5)
    # dissolution capped at the mineral present
    xi = positivity_limit(np.array([[3.0, 0.0]]), n_aq, np.array([[2.0, 0.0]]), nu)
    assert xi[0, 0] == pytest.approx(2.0)


def test_numpy_mlp_learns_smooth_map():
    rng = np.random.default_rng(0)
    X = rng.uniform(-1, 1, (3000, 3))
    Y = np.column_stack([np.sin(2 * X[:, 0]) + X[:, 1] ** 2, X[:, 2] * X[:, 0]])
    m, hist = fit_mlp(X, Y, hidden=(32, 32), epochs=150)
    err = np.abs(m.predict(X) - Y).mean()
    assert err < 0.05
    m2 = MLP.from_state(m.state_dict())
    assert np.allclose(m2.predict(X[:5]), m.predict(X[:5]))


def test_stagnant_cells_not_forced_to_equilibrium():
    from padstream_rt import (ChemicalSystem, GridGeometry, Mineral, ReactiveState,
                              RoutingConfig, route)
    g = GridGeometry(nx=2, ny=1, nz=1)
    m = Mineral("slow", [1.0], 2e-5, 0.0, -12.0, 0.0, specific_area=1e3)
    st = ReactiveState(g, ChemicalSystem(["X"], [m], c_eq_scale=np.array([1.0])), porosity=0.2,
                       perm=np.ones((2, 3)), brine_saturation=1.0, total_aq=np.zeros((2, 1)),
                       mineral_vf=np.full((2, 1), 0.1), temperature=323.15, pressure=1e7)
    tau = np.array([np.inf, 1e3])               # cell 0 has no streamline
    reg = route(st, tau, dt=86400.0, cfg=RoutingConfig(buffer_cells=0))
    assert reg[0, 0] != 2                        # Da_dt ~ 1e-3, so not EQUILIBRIUM


def test_phreeqc_kinetics_keeps_elements_positive():
    pytest.importorskip("phreeqc")
    from padstream_rt import ChemInput, PhreeqcBackend
    from padstream_rt.kinetics import load_pk_parameters
    ph = ["Quartz", "K-feldspar", "Kaolinite"]
    kp = {"Quartz": load_pk_parameters("quartz"), "K-feldspar": load_pk_parameters("K-feldspar"),
          "Kaolinite": load_pk_parameters("kaolinite")}
    b = PhreeqcBackend(["K", "Al", "Si", "C", "Na", "Cl"], ph, kinetic_params=kp)
    n_aq = np.array([[1e-4, 1e-7, 1e-4, 1.0, 2.0, 2.0]])          # 1 kg water, CO2-rich
    x = ChemInput(n_aq, np.array([[10.0, 1.0, 1e-3]]), np.array([1e-3]), 1.0,
                  np.array([[1e3, 1e4, 1e5]]), np.array([323.15]), np.array([15e6]), 30 * 86400.0)
    xi = b.kinetic(x)
    after = n_aq + xi @ b.chemical_system().nu_matrix
    assert after.min() > -1e-10
    assert xi[0, 1] > 0                                          # feldspar dissolves in acid brine


def test_dissolution_only_rate():
    from padstream_rt import Mineral
    from padstream_rt.kinetics import mineral_rate
    m = Mineral("x", [1.0], 2e-5, 0.0, -10.0, 0.0, precipitate=False)
    assert mineral_rate(m, 1.0, 323.15, 5.0, 10.0) == 0.0          # supersaturated: no growth
    assert mineral_rate(m, 1.0, 323.15, 5.0, 0.1) > 0.0            # undersaturated: dissolves

import numpy as np
import pytest

from padstream_rt.mineralogy import (CLAY, grain_diameter_m, load_freiburg_table1,
                                     load_freiburg_table3, unit_mineralogy)


def test_freiburg_table1_transcription():
    t = load_freiburg_table1()
    assert len(t) == 7
    lms = t["Lower Mt. Simon"]
    assert (lms["quartz"], lms["k_feldspar"], lms["plagioclase"]) == (73, 13, 7)
    assert sum(lms[m] for m in CLAY) == pytest.approx(4.0)       # clay split sums to total clay
    for u, d in t.items():
        assert 95 <= sum(d.values()) <= 102, u                     # rounding in the printed table


def test_freiburg_table3_and_grain_size():
    s = [r for r in load_freiburg_table3() if r["unit"] == "Lower Mt. Simon"]
    assert [r["permeability_mD"] for r in s] == [134.71, 85.89, 98.73, 151.31]
    assert grain_diameter_m("medium") == pytest.approx(1e-3 * np.sqrt(0.25 * 0.5))
    assert grain_diameter_m("coarse to very coarse") == pytest.approx(1e-3 * np.sqrt(0.5 * 2.0))


def test_unit_mineralogy_volume_closure():
    m = unit_mineralogy("Lower Mt. Simon")
    assert m.porosity == pytest.approx(np.mean([0.220, 0.167, 0.202, 0.205]))
    assert m.vf_bulk.sum() == pytest.approx(1.0 - m.porosity)
    assert np.all(m.reactive_area > 0)


def test_c_eq_scales_positive():
    pytest.importorskip("phreeqc")
    from padstream_rt.mineralogy import c_eq_scales
    c = c_eq_scales(["Calcite", "Quartz"], 323.15, 15e6, 1.0, 100.0)
    assert np.all(c > 0) and c[0] > c[1]                           # calcite far more soluble

"""Generate PHREEQC training data and train the lower Mt. Simon speciation network.

Reproduces examples/models/lower_mt_simon_speciation_v1.npz (27 Oct 2026; for
that file the primaries were the five rock phases and the secondaries
kaolinite and quartz, as SYSTEMS["lower_mt_simon"] now encodes);
``--system argenta`` trains the carbonate-bearing Argenta network:
100,000 reaction-path / mixing samples (surrogate.sample_states), 5,000
independent test samples, 3 x 128 tanh MLP, 300 epochs.  About 2 min of
sampling and 4 min of training on 2 CPU cores.

    python examples/train_speciation_surrogate.py --out examples/models/lower_mt_simon_speciation_v1.npz
"""

import argparse
import time

import numpy as np

from padstream_rt import PhreeqcBackend
from padstream_rt.surrogate import add_charge_feature, fit_mlp, sample_states

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from routing_ablation import SYSTEMS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100000)
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--out", default="lower_mt_simon_speciation.npz")
    ap.add_argument("--system", default="lower_mt_simon", choices=sorted(SYSTEMS))
    a = ap.parse_args()
    S = SYSTEMS[a.system]
    ELEMENTS, PHASES = S["elements"], S["phases"]
    # primaries: phases present in the rock; secondaries may precipitate
    primaries = [p for p, x in zip(PHASES, S["xrd"]) if x is not None]
    kw = dict(formation_eq=S["formation_eq"])
    b = PhreeqcBackend(ELEMENTS, PHASES)
    t = time.time()
    d = sample_states(b, a.n, np.random.default_rng(1), primaries, S["secondaries"], **kw)
    te = sample_states(b, 5000, np.random.default_rng(99), primaries, S["secondaries"], **kw)
    print(f"sampling {time.time() - t:.0f} s, {d['X'].shape[0]} samples")
    X, Xt = add_charge_feature(d["X"], ELEMENTS), add_charge_feature(te["X"], ELEMENTS)
    m, _ = fit_mlp(X, d["Y"], hidden=(128, 128, 128), epochs=a.epochs, verbose=True)
    err = np.abs(m.predict(Xt) - te["Y"])
    print("test MAE  [pH, SI " + ", ".join(PHASES) + "]:", np.round(err.mean(0), 4))
    print("test p99:", np.round(np.quantile(err, 0.99, axis=0), 4))
    m.save(a.out)


if __name__ == "__main__":
    main()

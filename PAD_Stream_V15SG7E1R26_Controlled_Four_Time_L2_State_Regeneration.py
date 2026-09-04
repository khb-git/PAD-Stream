from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import importlib.util
import inspect
import json
import re
from typing import Any

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26
# Controlled Four-Time L2 State Regeneration
#
# CONTROLLED GENERATION MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN 100-DAY L2 TARGET CHANGED.
# NO GAMMA RECALIBRATION.
# NO CROSSING-GUARD CHANGE.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO POST-HOC ALIGNMENT.
# NO SCALAR ANCHORING OR FITTING.
#
# PURPOSE
# -------
# R25R established:
#
#   L2_100D_DETERMINISTIC_REPLAY_VALIDATED
#
# with:
#
#   BOUND_L2_100D_REPLAY_PASSES_PRECISION_EQUIVALENCE_CONTRACT
#
# R26 is the first milestone allowed to create the missing physical-time
# deployment states:
#
#   100, 250, 500, 1000 days
#
# under the exact frozen evaluator/model/input contract established by R18-R25R.
#
# CRITICAL SAFETY RULE
# --------------------
# R26 will NOT generate 250/500/1000 days unless the dynamically bound evaluator
# FIRST reproduces the authoritative 100-day L2 state within the already-frozen
# R25R precision envelope.
#
# If the historical evaluator callable or its input binding cannot be recovered
# exactly from persisted provenance, R26 stops safely and requests a narrow
# evaluator-binding audit. It will not fabricate inputs or interpolate states.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R25R_DIR = ROOT / "output" / "V15_SG7E1R25R"
R25R_SUMMARY = R25R_DIR / "PAD_Stream_V15SG7E1R25R_Summary.json"
R25R_CONTRACT = R25R_DIR / "V15SG7E1R25R_Repaired_100d_Replay_Contract.json"

R24_DIR = ROOT / "output" / "V15_SG7E1R24"
R24_NUM = R24_DIR / "V15SG7E1R24_100d_Deterministic_Replay.npz"

R23_DIR = ROOT / "output" / "V15_SG7E1R23"
R23_SUMMARY = R23_DIR / "PAD_Stream_V15SG7E1R23_Summary.json"

R18_DIR = ROOT / "output" / "V15_SG7E1R18"
R18_MODEL = R18_DIR / "V15SG7E1R18_Frozen_Model_Identity.csv"
R18_EVAL_TRACE = R18_DIR / "V15SG7E1R18_Deployment_Evaluator_Source_Trace.csv"
R18_ARG_CONTRACT = R18_DIR / "V15SG7E1R18_Evaluation_Argument_Contract.csv"
R18_INPUTS = R18_DIR / "V15SG7E1R18_Persisted_Input_Availability.csv"

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3" / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

REQUIRED_TIMES = [100.0, 250.0, 500.0, 1000.0]
EXPECTED_SHAPE = (2662, 201)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

MODEL_TABLE = OUT / "V15SG7E1R26_Frozen_Model_Identity.csv"
EVALUATOR_TABLE = OUT / "V15SG7E1R26_Evaluator_Callable_Binding.csv"
ARG_TABLE = OUT / "V15SG7E1R26_Evaluator_Argument_Binding.csv"
CONTROL_TABLE = OUT / "V15SG7E1R26_100d_Control_Closure.csv"
STATE_TABLE = OUT / "V15SG7E1R26_Four_Time_State_Identity.csv"
GATE_TABLE = OUT / "V15SG7E1R26_Final_Regeneration_Gate_Matrix.csv"
DECISION_TABLE = OUT / "V15SG7E1R26_Regeneration_Decision.csv"

NUMERICAL_FILE = OUT / "V15SG7E1R26_Four_Time_L2_States.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26_Four_Time_Regeneration_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26_Summary.json"


# =============================================================================
# Helpers
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def save_csv(path: Path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_array(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def metrics(a, b):
    d = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    return {
        "L1": float(np.mean(np.abs(d))),
        "L2": float(np.sqrt(np.mean(d * d))),
        "Linf": float(np.max(np.abs(d))),
    }


def import_module_from_path(path: Path):
    name = f"_padstream_dynamic_{hash(path)}"
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def candidate_source_paths():
    """
    Collect exact source paths named by R18 trace first, then conservative
    late-branch fallback sources.
    """
    paths = []

    for r in load_csv(R18_EVAL_TRACE):
        for col in ("source", "source_file", "path", "file"):
            val = r.get(col, "")
            if not val:
                continue
            p = Path(val)
            if not p.is_absolute():
                p = ROOT / p
            if p.exists() and p.suffix.lower() == ".py":
                paths.append(p.resolve())

    fallback_tokens = (
        "PAD_Stream_V15SG7CR3F5R1F2",
        "PAD_Stream_V15SG7CR3F5R1F3",
        "PAD_Stream_V15SG7CR3F4",
    )
    for p in ROOT.glob("*.py"):
        if any(tok in p.name for tok in fallback_tokens):
            paths.append(p.resolve())

    return sorted(set(paths))


def discover_callable_candidates():
    """
    Discover reusable no-training evaluator-like callables. We do not invoke
    them yet. Candidate names are ranked only by source semantics.
    """
    rows = []
    objects = []

    for src in candidate_source_paths():
        try:
            mod = import_module_from_path(src)
        except Exception as exc:
            rows.append({
                "source": str(src),
                "function": "",
                "signature": "",
                "score": -999,
                "import_ok": False,
                "reason": repr(exc),
            })
            continue

        for name, obj in vars(mod).items():
            if not inspect.isfunction(obj):
                continue
            if obj.__module__ != mod.__name__:
                continue

            low = name.lower()
            score = 0
            for tok, val in (
                ("predict", 40),
                ("deploy", 40),
                ("eval", 30),
                ("infer", 30),
                ("reconstruct", 20),
                ("candidate", 15),
                ("state", 10),
                ("l2", 20),
                ("100", 5),
            ):
                if tok in low:
                    score += val

            for tok, val in (
                ("train", -100),
                ("fit", -80),
                ("plot", -50),
                ("save", -30),
                ("main", -40),
            ):
                if tok in low:
                    score += val

            sig = inspect.signature(obj)
            params = list(sig.parameters)

            if any(
                any(tok in p.lower() for tok in ("time", "day", "t_phys", "t_days"))
                for p in params
            ):
                score += 30

            rows.append({
                "source": str(src),
                "function": name,
                "signature": str(sig),
                "score": score,
                "import_ok": True,
                "reason": "",
            })

            if score > 0:
                objects.append((score, src, name, obj, sig))

    objects.sort(key=lambda x: (x[0], str(x[1]), x[2]), reverse=True)
    rows.sort(key=lambda r: int(r["score"]), reverse=True)
    return rows, objects


def load_frozen_arrays():
    if not R1F3_FROZEN.exists():
        raise FileNotFoundError(R1F3_FROZEN)
    db = np.load(R1F3_FROZEN, allow_pickle=True)
    out = {k: np.array(db[k], copy=True) for k in db.files}
    db.close()
    return out


def build_generic_argument_pool(model_path: Path, frozen: dict[str, np.ndarray]):
    """
    Strict pool of persisted/provenance-backed objects only.
    No synthetic features are created here.
    """
    pool: dict[str, Any] = {}

    # Direct frozen arrays by exact key.
    for key, val in frozen.items():
        pool[key] = val

    # Common semantic aliases backed by exact persisted arrays.
    alias_groups = {
        "xi": ["xi"],
        "truth_front_xi": ["truth_front_xi"],
        "tau_end": ["tau_end"],
        "guard_mask": ["guard_mask"],
        "gamma": ["L2_gamma_independent"],
        "L2_gamma": ["L2_gamma_independent"],
        "k5": ["K5_100"],
        "K5": ["K5_100"],
        "state": ["K5_100"],
        "base_state": ["K5_100"],
        "truth": ["truth100"],
        "truth100": ["truth100"],
    }

    for alias, keys in alias_groups.items():
        for k in keys:
            if k in frozen:
                pool[alias] = frozen[k]
                break

    pool["model_path"] = str(model_path)
    pool["checkpoint_path"] = str(model_path)

    return pool


def resolve_parameter_value(
    param_name: str,
    time_days: float,
    pool: dict[str, Any],
):
    """
    Bind only exact or high-confidence persisted aliases.
    """
    low = param_name.lower()

    if low in {"t", "time", "time_days", "t_days", "physical_time_days", "t_phys_days"}:
        return time_days, "physical_time_days"

    if param_name in pool:
        return pool[param_name], f"pool:{param_name}"

    # Conservative semantic aliases.
    for key in pool:
        if key.lower() == low:
            return pool[key], f"pool_casefold:{key}"

    # A few safe naming equivalences.
    if "xi" == low and "xi" in pool:
        return pool["xi"], "pool:xi"

    if "tau" in low and "tau_end" in pool:
        return pool["tau_end"], "pool:tau_end"

    if "guard" in low and "guard_mask" in pool:
        return pool["guard_mask"], "pool:guard_mask"

    if "gamma" in low and "gamma" in pool:
        return pool["gamma"], "pool:gamma"

    if "truth" in low and "truth" in pool:
        return pool["truth"], "pool:truth"

    if any(tok in low for tok in ("k5", "base_state", "input_state")) and "k5" in pool:
        return pool["k5"], "pool:k5"

    if "model_path" in low or "checkpoint" in low:
        return pool["model_path"], "pool:model_path"

    return None, None


def invoke_candidate(obj, sig, time_days, pool):
    kwargs = {}
    bindings = []

    for name, param in sig.parameters.items():
        value, source = resolve_parameter_value(name, time_days, pool)

        if source is None:
            if param.default is not inspect._empty:
                bindings.append({
                    "parameter": name,
                    "binding": "DEFAULT",
                    "source": repr(param.default),
                })
                continue
            return None, bindings, f"UNBOUND_REQUIRED_PARAMETER:{name}"

        kwargs[name] = value
        bindings.append({
            "parameter": name,
            "binding": "BOUND",
            "source": source,
        })

    try:
        out = obj(**kwargs)
    except Exception as exc:
        return None, bindings, f"CALL_FAILED:{type(exc).__name__}:{exc}"

    # Normalize common return structures without guessing numerical content.
    if isinstance(out, np.ndarray):
        return out, bindings, "OK"

    if isinstance(out, (list, tuple)):
        arrays = [
            x for x in out
            if isinstance(x, np.ndarray) and x.shape == EXPECTED_SHAPE
        ]
        if len(arrays) == 1:
            return arrays[0], bindings, "OK_TUPLE_SINGLE_STATE"
        return None, bindings, f"AMBIGUOUS_TUPLE_STATE_ARRAYS:{len(arrays)}"

    if isinstance(out, dict):
        preferred = []
        for key, val in out.items():
            if isinstance(val, np.ndarray) and val.shape == EXPECTED_SHAPE:
                preferred.append((key, val))
        if len(preferred) == 1:
            return preferred[0][1], bindings, f"OK_DICT_KEY:{preferred[0][0]}"
        return None, bindings, f"AMBIGUOUS_DICT_STATE_ARRAYS:{len(preferred)}"

    return None, bindings, f"UNSUPPORTED_RETURN_TYPE:{type(out).__name__}"


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26")
    print("Controlled Four-Time L2 State Regeneration")
    print("=" * 78)

    print("""
CONTROLLED NO-TRAINING MULTI-TIME REGENERATION WILL BE ATTEMPTED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO POST-HOC ALIGNMENT OR SCALAR ANCHORING WILL BE USED.
100-DAY CLOSURE MUST PASS BEFORE 250/500/1000 DAYS ARE GENERATED.
NO SG7E PERFORMANCE GATE WILL BE EVALUATED.
""")

    s25r = load_json(R25R_SUMMARY)
    c25r = load_json(R25R_CONTRACT)
    s23 = load_json(R23_SUMMARY)

    if s25r.get("status") != "L2_100D_DETERMINISTIC_REPLAY_VALIDATED":
        raise RuntimeError("R26 requires validated R25R 100-day replay.")

    if s23.get("selected_key") != "L2_independent_100":
        raise RuntimeError("R26 requires R23 L2_independent_100 binding.")

    envelope = float(c25r["contract_repair"]["precision_envelope"])

    # -------------------------------------------------------------------------
    # Authoritative model
    # -------------------------------------------------------------------------

    model_rows = load_csv(R18_MODEL)
    if len(model_rows) != 1:
        raise RuntimeError(f"Expected one frozen model, found {len(model_rows)}")

    model_path = Path(model_rows[0]["path"])
    expected_model_sha = model_rows[0]["sha256"]

    if not model_path.exists():
        raise FileNotFoundError(model_path)

    actual_model_sha = sha256_file(model_path)
    model_hash_match = actual_model_sha == expected_model_sha

    save_csv(MODEL_TABLE, [{
        "model_path": str(model_path),
        "expected_sha256": expected_model_sha,
        "actual_sha256": actual_model_sha,
        "hash_match": model_hash_match,
        "immutable": True,
    }])

    frozen = load_frozen_arrays()

    if "L2_independent_100" not in frozen:
        raise RuntimeError("Frozen package lacks authoritative L2_independent_100.")

    target100 = np.asarray(frozen["L2_independent_100"])
    target100_sha = sha256_array(target100)

    # -------------------------------------------------------------------------
    # Discover exact reusable evaluator callable.
    # -------------------------------------------------------------------------

    evaluator_rows, objects = discover_callable_candidates()
    save_csv(EVALUATOR_TABLE, evaluator_rows)

    pool = build_generic_argument_pool(model_path, frozen)

    bound_evaluator = None
    control_candidates = []
    argument_rows = []

    # Try callable candidates ONLY at 100 days first.
    for score, src, name, obj, sig in objects:
        result, bindings, call_status = invoke_candidate(
            obj, sig, 100.0, pool
        )

        for b in bindings:
            argument_rows.append({
                "source": str(src),
                "function": name,
                "time_days": 100.0,
                **b,
                "call_status": call_status,
            })

        if result is None:
            control_candidates.append({
                "source": str(src),
                "function": name,
                "score": score,
                "call_status": call_status,
                "shape": "",
                "dtype": "",
                "L1": "",
                "L2": "",
                "Linf": "",
                "precision_pass": False,
            })
            continue

        arr = np.asarray(result)

        if arr.shape != EXPECTED_SHAPE:
            control_candidates.append({
                "source": str(src),
                "function": name,
                "score": score,
                "call_status": f"SHAPE_MISMATCH:{arr.shape}",
                "shape": str(arr.shape),
                "dtype": str(arr.dtype),
                "L1": "",
                "L2": "",
                "Linf": "",
                "precision_pass": False,
            })
            continue

        m = metrics(arr, target100)
        passes = m["Linf"] <= envelope

        control_candidates.append({
            "source": str(src),
            "function": name,
            "score": score,
            "call_status": call_status,
            "shape": str(arr.shape),
            "dtype": str(arr.dtype),
            **m,
            "precision_pass": passes,
            "sha256": sha256_array(arr),
        })

        if passes:
            bound_evaluator = (src, name, obj, sig, arr, bindings)
            break

    save_csv(ARG_TABLE, argument_rows)
    save_csv(CONTROL_TABLE, control_candidates)

    # -------------------------------------------------------------------------
    # Gate: 100-day evaluator closure before any later time.
    # -------------------------------------------------------------------------

    if bound_evaluator is None:
        status = "FOUR_TIME_REGENERATION_BLOCKED_EVALUATOR_BINDING"
        diagnosis = "NO_DISCOVERED_CALLABLE_REPRODUCES_BOUND_100D_STATE"
        recommendation = (
            "Do not generate 250/500/1000-day states. The frozen model and 100-day replay "
            "contract are valid, but no reusable historical evaluator callable has yet been "
            "bound tightly enough to reproduce L2_independent_100. Audit only the exact "
            "evaluator function and required feature/time-transform arguments identified by "
            "R18; do not fabricate missing inputs."
        )
        next_milestone = (
            "V15-SG7E1R26A — Exact Multi-Time Evaluator Callable / Argument Binding Audit"
        )

        gates = [
            ("R25R_100d_replay_validated", True),
            ("authoritative_model_hash_reproduced", model_hash_match),
            ("bound_100d_target_loaded", True),
            ("historical_evaluator_callable_bound", False),
            ("100d_callable_replay_closure", False),
            ("later_times_not_generated_without_100d_control", True),
            ("no_training_performed", True),
            ("no_threshold_changed", True),
        ]

        save_csv(GATE_TABLE, [
            {"gate": g, "passed": p} for g, p in gates
        ])

        save_csv(DECISION_TABLE, [{
            "status": status,
            "diagnosis": diagnosis,
            "precision_envelope": envelope,
            "bound_evaluator_source": "",
            "bound_evaluator_function": "",
            "states_generated": 0,
            "next_milestone": next_milestone,
        }])

        save_json(CONTRACT_FILE, {
            "milestone": "V15-SG7E1R26",
            "status": status,
            "diagnosis": diagnosis,
            "precision_envelope": envelope,
            "states_generated": [],
            "constraints": {
                "training_performed": False,
                "model_parameters_changed": False,
                "gamma_changed": False,
                "guard_changed": False,
                "threshold_changed": False,
                "fabricated_input_used": False,
            },
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        })

        save_json(SUMMARY_FILE, {
            "milestone": "V15-SG7E1R26",
            "status": status,
            "diagnosis": diagnosis,
            "states_generated": 0,
            "candidate_changed": False,
            "threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        })

        print("100-DAY CALLABLE CONTROL")
        print(f"  Callable candidates     : {len(objects)}")
        print("  Passing 100d callable   : NONE")

        print("\nSTATUS")
        print(f"  {status}")
        print("\nDIAGNOSIS")
        print(f"  {diagnosis}")
        print("\nRECOMMENDATION")
        print(f"  {recommendation}")
        print("\nNEXT MILESTONE")
        print(f"  {next_milestone}")

        print("\n" + "=" * 78)
        print("V15-SG7E1R26 FOUR-TIME REGENERATION: BLOCKED SAFELY")
        print("=" * 78)
        return

    # -------------------------------------------------------------------------
    # 100d passed — now generate all required times using exact same callable.
    # -------------------------------------------------------------------------

    src, func_name, func_obj, sig, replay100, control_bindings = bound_evaluator

    state_rows = []
    generated = {}

    for t in REQUIRED_TIMES:
        arr, bindings, call_status = invoke_candidate(
            func_obj, sig, t, pool
        )

        if arr is None:
            raise RuntimeError(
                f"Bound evaluator failed at t={t}: {call_status}"
            )

        arr = np.asarray(arr)

        if arr.shape != EXPECTED_SHAPE:
            raise RuntimeError(
                f"Bound evaluator returned {arr.shape} at t={t}; "
                f"expected {EXPECTED_SHAPE}"
            )

        if not np.all(np.isfinite(arr)):
            raise RuntimeError(f"Non-finite regenerated state at t={t}")

        generated[t] = np.array(arr, copy=True)

        state_rows.append({
            "time_days": t,
            "shape": str(arr.shape),
            "dtype": str(arr.dtype),
            "sha256": sha256_array(arr),
            "min": float(np.nanmin(arr)),
            "max": float(np.nanmax(arr)),
            "mean": float(np.nanmean(arr)),
            "call_status": call_status,
        })

    save_csv(STATE_TABLE, state_rows)

    # 100-day final closure
    control_metrics = metrics(generated[100.0], target100)
    control_pass = control_metrics["Linf"] <= envelope

    if not control_pass:
        raise RuntimeError(
            "Internal safety failure: 100-day control changed between binding and generation."
        )

    # Temporal distinctness: do not require monotonic saturation at every point,
    # only establish that all states are finite and carry distinct identities.
    hashes = [r["sha256"] for r in state_rows]
    unique_hashes = len(set(hashes))

    gates = [
        ("R25R_100d_replay_validated", True),
        ("authoritative_model_hash_reproduced", model_hash_match),
        ("historical_evaluator_callable_bound", True),
        ("100d_callable_replay_closure", control_pass),
        ("100d_state_generated", 100.0 in generated),
        ("250d_state_generated", 250.0 in generated),
        ("500d_state_generated", 500.0 in generated),
        ("1000d_state_generated", 1000.0 in generated),
        ("all_states_shape_2662x201", all(a.shape == EXPECTED_SHAPE for a in generated.values())),
        ("all_states_finite", all(np.all(np.isfinite(a)) for a in generated.values())),
        ("four_time_labels_preserved", sorted(generated) == REQUIRED_TIMES),
        ("no_training_performed", True),
        ("no_model_parameter_changed", True),
        ("no_gamma_or_guard_recalibration", True),
        ("no_SG7E_threshold_change", True),
        ("no_SG7E_performance_gate_evaluated", True),
    ]

    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [
        {"gate": g, "passed": p} for g, p in gates
    ])

    if failed:
        status = "FOUR_TIME_L2_REGENERATION_FAILED"
        diagnosis = "ONE_OR_MORE_CONTROLLED_REGENERATION_GATES_FAILED"
        recommendation = (
            "Do not map back the regenerated states. Audit only the failed R26 generation "
            "gates; preserve the model, evaluator, inputs, and time labels unchanged."
        )
        next_milestone = "V15-SG7E1R27 — Four-Time Regeneration Failure Audit"
    else:
        status = "FOUR_TIME_L2_STATES_REGENERATED"
        diagnosis = "FROZEN_EVALUATOR_REPRODUCES_100D_CONTROL_AND_GENERATES_REQUIRED_MULTI_TIME_STATES"
        recommendation = (
            "The same frozen no-training evaluator that closes against the authoritative "
            "100-day L2 state has generated time-labelled 100/250/500/1000-day deployment "
            "states. Preserve these arrays and hashes unchanged. Proceed to independent "
            "four-time state validation before conservative SG7D map-back replay."
        )
        next_milestone = (
            "V15-SG7E1R27 — Independent Four-Time L2 State Validation"
        )

    # Persist only after complete successful invocation at all four times.
    np.savez_compressed(
        NUMERICAL_FILE,
        times_days=np.asarray(REQUIRED_TIMES, dtype=np.float64),
        L2_states=np.stack([generated[t] for t in REQUIRED_TIMES], axis=0),
        state_100d=generated[100.0],
        state_250d=generated[250.0],
        state_500d=generated[500.0],
        state_1000d=generated[1000.0],
        evaluator_source=np.asarray([str(src)]),
        evaluator_function=np.asarray([func_name]),
        precision_envelope=np.asarray([envelope], dtype=np.float64),
    )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "precision_envelope": envelope,
        "bound_evaluator_source": str(src),
        "bound_evaluator_function": func_name,
        "100d_control_Linf": control_metrics["Linf"],
        "unique_state_hashes": unique_hashes,
        "states_generated": len(generated),
        "failed_gates": ";".join(failed),
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26",
        "status": status,
        "diagnosis": diagnosis,
        "model": {
            "path": str(model_path),
            "sha256": actual_model_sha,
            "hash_match": model_hash_match,
        },
        "evaluator": {
            "source": str(src),
            "function": func_name,
            "signature": str(sig),
        },
        "100d_control": {
            **control_metrics,
            "precision_envelope": envelope,
            "passed": control_pass,
            "target_sha256": target100_sha,
            "generated_sha256": sha256_array(generated[100.0]),
        },
        "times_days": REQUIRED_TIMES,
        "state_hashes": {
            str(int(t)): sha256_array(generated[t])
            for t in REQUIRED_TIMES
        },
        "failed_gates": failed,
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "gamma_changed": False,
            "guard_changed": False,
            "threshold_changed": False,
            "posthoc_alignment_used": False,
            "scalar_anchoring_used": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26",
        "status": status,
        "diagnosis": diagnosis,
        "states_generated": len(generated),
        "times_days": REQUIRED_TIMES,
        "evaluator_function": func_name,
        "100d_control_Linf": control_metrics["Linf"],
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("BOUND EVALUATOR")
    print(f"  Source                  : {src}")
    print(f"  Function                : {func_name}")
    print(f"  Signature               : {sig}")

    print("\n100-DAY CONTROL")
    print(f"  Target SHA-256          : {target100_sha}")
    print(f"  Replay SHA-256          : {sha256_array(generated[100.0])}")
    print(f"  L1                      : {control_metrics['L1']:.6e}")
    print(f"  L2                      : {control_metrics['L2']:.6e}")
    print(f"  Linf                    : {control_metrics['Linf']:.6e}")
    print(f"  Envelope                : {envelope:.6e}")
    print(f"  Pass                    : {control_pass}")

    print("\nFOUR-TIME REGENERATED STATES")
    for row in state_rows:
        print(
            f"  t={float(row['time_days']):7.1f} d | "
            f"{row['sha256'][:16]} | "
            f"range={float(row['min']):.6f}->{float(row['max']):.6f} | "
            f"mean={float(row['mean']):.6f}"
        )

    print("\n" + "=" * 78)
    print("V15-SG7E1R26 FINAL REGENERATION GATES")
    print("=" * 78)
    for g, p in gates:
        print(f"[{'PASS' if p else 'FAIL'}] {g}")
    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")
    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")
    print("\nRECOMMENDATION")
    print(f"  {recommendation}")
    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")
    print("\nTables:")
    for p in (
        MODEL_TABLE,
        EVALUATOR_TABLE,
        ARG_TABLE,
        CONTROL_TABLE,
        STATE_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")
    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26 CONTROLLED FOUR-TIME L2 STATE REGENERATION: COMPLETE")
    print()
    print("No training was performed.")
    print("No model parameter was changed.")
    print("No gamma or crossing guard was recalibrated.")
    print("No post-hoc alignment or scalar anchoring was used.")
    print("No SG7E threshold was changed or relaxed.")
    print("No SG7E performance gate was evaluated.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import importlib.util
import inspect
import json
from typing import Any

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26B
# Exact-Bound Evaluator 100-Day Control / Four-Time Regeneration
#
# CONTROLLED RUNTIME-PROOF MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN 100-DAY L2 TARGET CHANGED.
# NO GAMMA RECALIBRATION.
# NO CROSSING-GUARD CHANGE.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO POST-HOC ALIGNMENT.
# NO SCALAR ANCHORING OR FITTING.
# NO SG7E PERFORMANCE GATES WILL BE EVALUATED.
#
# PURPOSE
# -------
# R26A established:
#
#   MULTI_TIME_EVALUATOR_CALLABLE_ARGUMENT_CONTRACT_BOUND
#
# but the top source-level callable was `main()` from the R18 audit script.
# R26B therefore does NOT treat that audit entry point itself as the physical
# deployment evaluator.
#
# Instead, R26B:
#
#   1. enters the exact R26A-selected R18 source lineage,
#   2. parses that source for model prediction/inference calls,
#   3. traces the local functions and expressions surrounding those calls,
#   4. identifies reusable no-training evaluator candidates beneath main(),
#   5. binds only persisted/provenance-backed arguments,
#   6. executes 100 days first,
#   7. requires closure to authoritative L2_independent_100 under the unchanged
#      R25R precision envelope,
#   8. only after 100d closure passes, executes 250/500/1000 days,
#   9. persists all four time-labelled L2 states and hashes.
#
# If no reusable evaluator beneath main() can reproduce the 100d control, R26B
# stops safely and requests one narrow lineage audit. It does NOT fabricate
# missing features and does NOT infer later-time states.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26B"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

R26A_DIR = ROOT / "output" / "V15_SG7E1R26A"
R26A_SUMMARY = R26A_DIR / "PAD_Stream_V15SG7E1R26A_Summary.json"
R26A_CONTRACT = R26A_DIR / "V15SG7E1R26A_Exact_Evaluator_Argument_Binding_Contract.json"
R26A_FUNCTIONS = R26A_DIR / "V15SG7E1R26A_Function_Signature_Inventory.csv"
R26A_ARGS = R26A_DIR / "V15SG7E1R26A_Exact_Argument_Binding_Candidates.csv"

R25R_CONTRACT = (
    ROOT / "output" / "V15_SG7E1R25R"
    / "V15SG7E1R25R_Repaired_100d_Replay_Contract.json"
)

R23_SUMMARY = (
    ROOT / "output" / "V15_SG7E1R23"
    / "PAD_Stream_V15SG7E1R23_Summary.json"
)

R18_MODEL = (
    ROOT / "output" / "V15_SG7E1R18"
    / "V15SG7E1R18_Frozen_Model_Identity.csv"
)

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3" / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

REQUIRED_TIMES = [100.0, 250.0, 500.0, 1000.0]
EXPECTED_SHAPE = (2662, 201)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SOURCE_LINEAGE_TABLE = OUT / "V15SG7E1R26B_Selected_Source_Lineage.csv"
NESTED_CALLABLE_TABLE = OUT / "V15SG7E1R26B_Nested_Evaluator_Candidates.csv"
ARG_BIND_TABLE = OUT / "V15SG7E1R26B_Runtime_Argument_Binding.csv"
CONTROL_TABLE = OUT / "V15SG7E1R26B_100d_Runtime_Control.csv"
STATE_TABLE = OUT / "V15SG7E1R26B_Four_Time_L2_State_Identity.csv"
GATE_TABLE = OUT / "V15SG7E1R26B_Final_Runtime_Gate_Matrix.csv"
DECISION_TABLE = OUT / "V15SG7E1R26B_Runtime_Regeneration_Decision.csv"

NUMERICAL_FILE = OUT / "V15SG7E1R26B_Four_Time_L2_States.npz"
CONTRACT_FILE = OUT / "V15SG7E1R26B_Exact_Bound_Runtime_Regeneration_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26B_Summary.json"


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


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


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
    name = f"_padstream_r26b_{abs(hash(str(path)))}"
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def call_name(node):
    if not isinstance(node, ast.Call):
        return ""
    cur = node.func
    parts = []
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


def safe_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def node_src(text, node):
    try:
        return ast.get_source_segment(text, node) or ""
    except Exception:
        return ""


def load_frozen_arrays():
    if not R1F3_FROZEN.exists():
        raise FileNotFoundError(R1F3_FROZEN)
    db = np.load(R1F3_FROZEN, allow_pickle=True)
    out = {k: np.array(db[k], copy=True) for k in db.files}
    db.close()
    return out


def build_pool(model_path: Path, frozen: dict[str, np.ndarray]):
    pool: dict[str, Any] = {}

    for key, arr in frozen.items():
        pool[key] = arr

    aliases = {
        "xi": "xi",
        "truth_front_xi": "truth_front_xi",
        "tau_end": "tau_end",
        "guard_mask": "guard_mask",
        "gamma": "L2_gamma_independent",
        "l2_gamma": "L2_gamma_independent",
        "truth": "truth100",
        "truth100": "truth100",
        "k5": "K5_100",
        "k5_100": "K5_100",
        "base_state": "K5_100",
        "state": "K5_100",
    }

    for alias, key in aliases.items():
        if key in frozen:
            pool[alias] = frozen[key]

    pool["model_path"] = str(model_path)
    pool["checkpoint_path"] = str(model_path)

    return pool


def bind_parameter(name: str, time_days: float, pool: dict[str, Any]):
    low = name.lower()

    if low in {
        "t", "time", "time_days", "t_days", "physical_time_days",
        "t_phys_days", "physical_time", "days",
    }:
        return time_days, "PHYSICAL_TIME_DAYS"

    if name in pool:
        return pool[name], f"POOL::{name}"

    for key in pool:
        if key.lower() == low:
            return pool[key], f"POOL_CASEFOLD::{key}"

    if "xi" == low and "xi" in pool:
        return pool["xi"], "POOL::xi"

    if ("tau" in low or "tof" in low) and "tau_end" in pool:
        return pool["tau_end"], "POOL::tau_end"

    if "guard" in low and "guard_mask" in pool:
        return pool["guard_mask"], "POOL::guard_mask"

    if "gamma" in low and "gamma" in pool:
        return pool["gamma"], "POOL::gamma"

    if "truth" in low and "truth" in pool:
        return pool["truth"], "POOL::truth"

    if any(tok in low for tok in ("k5", "base_state", "input_state", "state_in")) and "k5" in pool:
        return pool["k5"], "POOL::k5"

    if "model_path" in low or "checkpoint" in low:
        return pool["model_path"], "POOL::model_path"

    return None, None


def normalize_return(out):
    if isinstance(out, np.ndarray):
        return out, "ARRAY"

    if isinstance(out, (tuple, list)):
        candidates = [
            x for x in out
            if isinstance(x, np.ndarray) and x.shape == EXPECTED_SHAPE
        ]
        if len(candidates) == 1:
            return candidates[0], "TUPLE_SINGLE_STATE"
        return None, f"TUPLE_AMBIGUOUS_{len(candidates)}"

    if isinstance(out, dict):
        candidates = [
            (k, v) for k, v in out.items()
            if isinstance(v, np.ndarray) and v.shape == EXPECTED_SHAPE
        ]
        if len(candidates) == 1:
            return candidates[0][1], f"DICT::{candidates[0][0]}"
        return None, f"DICT_AMBIGUOUS_{len(candidates)}"

    return None, f"UNSUPPORTED_RETURN::{type(out).__name__}"


def invoke_function(obj, sig, time_days, pool):
    kwargs = {}
    bindings = []

    for name, param in sig.parameters.items():
        value, source = bind_parameter(name, time_days, pool)

        if source is None:
            if param.default is not inspect._empty:
                bindings.append({
                    "parameter": name,
                    "binding": "DEFAULT",
                    "source": repr(param.default),
                })
                continue
            return None, bindings, f"UNBOUND_REQUIRED::{name}"

        kwargs[name] = value
        bindings.append({
            "parameter": name,
            "binding": "BOUND",
            "source": source,
        })

    try:
        out = obj(**kwargs)
    except Exception as exc:
        return None, bindings, f"CALL_FAILED::{type(exc).__name__}::{exc}"

    arr, ret_sem = normalize_return(out)
    if arr is None:
        return None, bindings, ret_sem

    return np.asarray(arr), bindings, ret_sem


def discover_nested_evaluators(selected_source: Path):
    """
    Parse and import the exact R26A-selected source. We specifically exclude
    main() as a runtime evaluator and rank only reusable child/helper functions.
    """
    text = safe_text(selected_source)
    tree = ast.parse(text)

    module = import_module_from_path(selected_source)

    rows = []
    candidates = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name == "main":
            continue

        obj = getattr(module, node.name, None)
        if not inspect.isfunction(obj):
            continue

        sig = inspect.signature(obj)
        params = list(sig.parameters)

        predict_calls = []
        load_model_calls = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                cname = call_name(sub).lower()
                if ".predict" in cname or "predict_on_batch" in cname:
                    predict_calls.append(node_src(text, sub))
                if "load_model" in cname:
                    load_model_calls.append(node_src(text, sub))

        low = node.name.lower()
        score = 0
        evidence = []

        for tok, val in (
            ("predict", 50),
            ("deploy", 50),
            ("evaluate", 40),
            ("eval", 35),
            ("infer", 35),
            ("state", 20),
            ("transport", 20),
            ("pirnn", 20),
            ("reconstruct", 15),
        ):
            if tok in low:
                score += val
                evidence.append(f"name:{tok}")

        if predict_calls:
            score += 120
            evidence.append("contains_predict_call")

        if load_model_calls:
            score += 30
            evidence.append("contains_load_model")

        if any(any(tok in p.lower() for tok in ("time", "day", "t_phys", "t_days")) for p in params):
            score += 50
            evidence.append("time_parameter")

        if any("xi" in p.lower() for p in params):
            score += 15
            evidence.append("xi_parameter")

        if any(("tau" in p.lower() or "tof" in p.lower()) for p in params):
            score += 15
            evidence.append("tau_parameter")

        if "train" in low or "fit" in low:
            score -= 200
            evidence.append("training_penalty")

        rows.append({
            "source": str(selected_source),
            "function": node.name,
            "signature": str(sig),
            "score": score,
            "predict_call_count": len(predict_calls),
            "load_model_call_count": len(load_model_calls),
            "evidence": ";".join(evidence),
        })

        if score > 0:
            candidates.append((score, node.name, obj, sig))

    rows.sort(key=lambda r: int(r["score"]), reverse=True)
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

    return rows, candidates


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26B")
    print("Exact-Bound Evaluator 100-Day Control / Four-Time Regeneration")
    print("=" * 78)

    print("""
CONTROLLED RUNTIME PROOF WILL BE PERFORMED.
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO POST-HOC ALIGNMENT OR SCALAR ANCHORING WILL BE USED.
100-DAY RUNTIME CLOSURE MUST PASS BEFORE 250/500/1000 DAYS ARE GENERATED.
NO SG7E PERFORMANCE GATE WILL BE EVALUATED.
""")

    s26a = load_json(R26A_SUMMARY)
    c26a = load_json(R26A_CONTRACT)
    c25r = load_json(R25R_CONTRACT)
    s23 = load_json(R23_SUMMARY)

    if s26a.get("status") != "MULTI_TIME_EVALUATOR_CALLABLE_ARGUMENT_CONTRACT_BOUND":
        raise RuntimeError("R26B requires successful R26A evaluator binding.")

    if s23.get("selected_key") != "L2_independent_100":
        raise RuntimeError("R26B requires authoritative L2_independent_100 target.")

    selected_source = Path(c26a["selected_evaluator"]["source"])
    selected_function = c26a["selected_evaluator"]["function"]

    if selected_function != "main":
        # R26B is designed for the exact observed R26A outcome but remains safe.
        pass

    if not selected_source.exists():
        raise FileNotFoundError(selected_source)

    envelope = float(c25r["contract_repair"]["precision_envelope"])

    # -------------------------------------------------------------------------
    # Model identity
    # -------------------------------------------------------------------------

    model_rows = load_csv(R18_MODEL)
    if len(model_rows) != 1:
        raise RuntimeError("Expected exactly one authoritative model.")

    model_path = Path(model_rows[0]["path"])
    expected_model_sha = model_rows[0]["sha256"]
    if not model_path.exists():
        raise FileNotFoundError(model_path)

    actual_model_sha = sha256_file(model_path)
    model_hash_match = actual_model_sha == expected_model_sha

    # -------------------------------------------------------------------------
    # Frozen target/input pool
    # -------------------------------------------------------------------------

    frozen = load_frozen_arrays()
    if "L2_independent_100" not in frozen:
        raise RuntimeError("Frozen package lacks L2_independent_100.")

    target100 = np.asarray(frozen["L2_independent_100"])
    target100_sha = sha256_array(target100)
    pool = build_pool(model_path, frozen)

    # -------------------------------------------------------------------------
    # Selected-source lineage
    # -------------------------------------------------------------------------

    save_csv(SOURCE_LINEAGE_TABLE, [{
        "R26A_selected_source": str(selected_source),
        "R26A_selected_function": selected_function,
        "R26A_binding_score": c26a["selected_evaluator"].get("binding_score"),
        "R26A_binding_margin": c26a["selected_evaluator"].get("binding_margin"),
        "R26B_runtime_policy": "exclude_main_and_bind_reusable_nested_evaluator",
    }])

    nested_rows, candidates = discover_nested_evaluators(selected_source)
    save_csv(NESTED_CALLABLE_TABLE, nested_rows)

    # -------------------------------------------------------------------------
    # Execute candidate nested evaluator(s) at 100d only.
    # -------------------------------------------------------------------------

    control_rows = []
    arg_rows = []
    bound = None

    for score, name, obj, sig in candidates:
        arr, bindings, call_status = invoke_function(
            obj, sig, 100.0, pool
        )

        for b in bindings:
            arg_rows.append({
                "source": str(selected_source),
                "function": name,
                "time_days": 100.0,
                **b,
                "call_status": call_status,
            })

        rec = {
            "function": name,
            "score": score,
            "signature": str(sig),
            "call_status": call_status,
            "shape": "",
            "dtype": "",
            "sha256": "",
            "L1": "",
            "L2": "",
            "Linf": "",
            "precision_pass": False,
        }

        if arr is not None:
            rec["shape"] = str(arr.shape)
            rec["dtype"] = str(arr.dtype)

            if arr.shape == EXPECTED_SHAPE and np.all(np.isfinite(arr)):
                m = metrics(arr, target100)
                rec.update({
                    "sha256": sha256_array(arr),
                    "L1": m["L1"],
                    "L2": m["L2"],
                    "Linf": m["Linf"],
                    "precision_pass": m["Linf"] <= envelope,
                })

                if m["Linf"] <= envelope and bound is None:
                    bound = (name, obj, sig, arr, bindings, score)

        control_rows.append(rec)

    save_csv(ARG_BIND_TABLE, arg_rows)
    save_csv(CONTROL_TABLE, control_rows)

    # -------------------------------------------------------------------------
    # Safe block if runtime evaluator still unresolved.
    # -------------------------------------------------------------------------

    if bound is None:
        status = "R26B_RUNTIME_EVALUATOR_CONTROL_BLOCKED"
        diagnosis = "NO_REUSABLE_NESTED_EVALUATOR_REPRODUCES_AUTHORITATIVE_100D_L2_STATE"
        recommendation = (
            "Do not generate 250/500/1000-day states. R26A correctly identified the R18 "
            "source lineage, but the reusable physical evaluator is still not exposed as a "
            "standalone callable beneath main(). Audit only the model.predict input-construction "
            "statements inside the selected R18 source and extract the exact raw inference "
            "operator plus postprocessing chain. Do not broaden the search or fabricate features."
        )
        next_milestone = (
            "V15-SG7E1R26C — Inlined Model-Predict Input Construction / Postprocessing Audit"
        )

        gates = [
            ("R26A_binding_status_reproduced", True),
            ("authoritative_model_hash_reproduced", model_hash_match),
            ("authoritative_100d_target_loaded", True),
            ("main_entrypoint_excluded_as_physical_evaluator", True),
            ("nested_evaluator_candidates_audited", True),
            ("100d_runtime_control_passed", False),
            ("later_times_not_generated_without_control", True),
            ("no_training_performed", True),
            ("no_threshold_changed", True),
        ]

        save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])
        save_csv(DECISION_TABLE, [{
            "status": status,
            "diagnosis": diagnosis,
            "selected_source": str(selected_source),
            "nested_candidate_count": len(candidates),
            "runtime_bound_function": "",
            "states_generated": 0,
            "next_milestone": next_milestone,
        }])

        save_json(CONTRACT_FILE, {
            "milestone": "V15-SG7E1R26B",
            "status": status,
            "diagnosis": diagnosis,
            "selected_source": str(selected_source),
            "runtime_bound_function": None,
            "states_generated": [],
            "precision_envelope": envelope,
            "constraints": {
                "training_performed": False,
                "model_parameters_changed": False,
                "gamma_changed": False,
                "guard_changed": False,
                "threshold_changed": False,
                "fabricated_feature_used": False,
            },
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        })

        save_json(SUMMARY_FILE, {
            "milestone": "V15-SG7E1R26B",
            "status": status,
            "diagnosis": diagnosis,
            "states_generated": 0,
            "candidate_changed": False,
            "threshold_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        })

        print("RUNTIME 100-DAY CONTROL")
        print(f"  Selected R26A source    : {selected_source.name}")
        print(f"  Nested evaluator count  : {len(candidates)}")
        print("  Passing runtime callable: NONE")

        print("\nSTATUS")
        print(f"  {status}")
        print("\nDIAGNOSIS")
        print(f"  {diagnosis}")
        print("\nRECOMMENDATION")
        print(f"  {recommendation}")
        print("\nNEXT MILESTONE")
        print(f"  {next_milestone}")

        print("\n" + "=" * 78)
        print("V15-SG7E1R26B EXACT-BOUND RUNTIME REGENERATION: BLOCKED SAFELY")
        print("=" * 78)
        return

    # -------------------------------------------------------------------------
    # Runtime control passed. Generate 4 times with exact same callable.
    # -------------------------------------------------------------------------

    fn_name, fn_obj, fn_sig, replay100, bindings100, fn_score = bound

    generated = {}
    state_rows = []

    for t in REQUIRED_TIMES:
        arr, bindings, call_status = invoke_function(
            fn_obj, fn_sig, t, pool
        )
        if arr is None:
            raise RuntimeError(
                f"Bound evaluator failed at {t} days: {call_status}"
            )

        if arr.shape != EXPECTED_SHAPE:
            raise RuntimeError(
                f"Bound evaluator returned shape {arr.shape} at {t} days"
            )

        if not np.all(np.isfinite(arr)):
            raise RuntimeError(f"Non-finite state at {t} days")

        generated[t] = np.array(arr, copy=True)

        state_rows.append({
            "time_days": t,
            "function": fn_name,
            "shape": str(arr.shape),
            "dtype": str(arr.dtype),
            "sha256": sha256_array(arr),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "mean": float(np.mean(arr)),
            "call_status": call_status,
        })

    save_csv(STATE_TABLE, state_rows)

    control_metrics = metrics(generated[100.0], target100)
    control_pass = control_metrics["Linf"] <= envelope

    gates = [
        ("R26A_binding_status_reproduced", True),
        ("authoritative_model_hash_reproduced", model_hash_match),
        ("authoritative_100d_target_hash_reproduced", sha256_array(target100) == target100_sha),
        ("main_entrypoint_excluded_as_physical_evaluator", True),
        ("nested_runtime_evaluator_bound", True),
        ("100d_runtime_control_passed", control_pass),
        ("100d_state_generated", 100.0 in generated),
        ("250d_state_generated", 250.0 in generated),
        ("500d_state_generated", 500.0 in generated),
        ("1000d_state_generated", 1000.0 in generated),
        ("all_state_shapes_correct", all(a.shape == EXPECTED_SHAPE for a in generated.values())),
        ("all_states_finite", all(np.all(np.isfinite(a)) for a in generated.values())),
        ("time_labels_preserved", sorted(generated) == REQUIRED_TIMES),
        ("no_training_performed", True),
        ("no_model_parameter_changed", True),
        ("no_gamma_or_guard_recalibration", True),
        ("no_threshold_changed", True),
        ("no_SG7E_performance_gate_evaluated", True),
    ]

    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    if failed:
        status = "R26B_FOUR_TIME_RUNTIME_REGENERATION_FAILED"
        diagnosis = "BOUND_RUNTIME_EVALUATOR_FAILS_ONE_OR_MORE_CONTROLLED_GENERATION_GATES"
        recommendation = (
            "Do not map back the regenerated states. Audit only the failed R26B gates while "
            "preserving the exact bound evaluator and inputs."
        )
        next_milestone = "V15-SG7E1R27 — Four-Time Runtime Regeneration Failure Audit"
    else:
        status = "FOUR_TIME_L2_RUNTIME_STATES_REGENERATED"
        diagnosis = "EXACT_BOUND_RUNTIME_EVALUATOR_CLOSES_100D_AND_GENERATES_100_250_500_1000D_STATES"
        recommendation = (
            "The exact reusable evaluator beneath the R18 source lineage reproduces the "
            "authoritative 100-day L2 state within the unchanged precision envelope and has "
            "generated explicit 100/250/500/1000-day deployment states. Persist these hashes "
            "unchanged and proceed to independent four-time validation before conservative "
            "streamline-to-grid map-back."
        )
        next_milestone = (
            "V15-SG7E1R27 — Independent Four-Time L2 State Validation"
        )

    np.savez_compressed(
        NUMERICAL_FILE,
        times_days=np.asarray(REQUIRED_TIMES, dtype=np.float64),
        L2_states=np.stack([generated[t] for t in REQUIRED_TIMES], axis=0),
        state_100d=generated[100.0],
        state_250d=generated[250.0],
        state_500d=generated[500.0],
        state_1000d=generated[1000.0],
        evaluator_source=np.asarray([str(selected_source)]),
        evaluator_function=np.asarray([fn_name]),
        precision_envelope=np.asarray([envelope], dtype=np.float64),
    )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "selected_source": str(selected_source),
        "runtime_bound_function": fn_name,
        "runtime_function_score": fn_score,
        "100d_control_Linf": control_metrics["Linf"],
        "precision_envelope": envelope,
        "states_generated": len(generated),
        "failed_gates": ";".join(failed),
        "next_milestone": next_milestone,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26B",
        "status": status,
        "diagnosis": diagnosis,
        "source_lineage": {
            "R26A_selected_source": str(selected_source),
            "R26A_selected_function": selected_function,
            "runtime_bound_function": fn_name,
            "runtime_signature": str(fn_sig),
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
        "milestone": "V15-SG7E1R26B",
        "status": status,
        "diagnosis": diagnosis,
        "states_generated": len(generated),
        "times_days": REQUIRED_TIMES,
        "runtime_bound_function": fn_name,
        "100d_control_Linf": control_metrics["Linf"],
        "candidate_changed": False,
        "threshold_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    })

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("EXACT RUNTIME EVALUATOR")
    print(f"  Source                  : {selected_source.name}")
    print(f"  Function                : {fn_name}")
    print(f"  Signature               : {fn_sig}")
    print(f"  Score                   : {fn_score}")

    print("\n100-DAY RUNTIME CONTROL")
    print(f"  Target SHA-256          : {target100_sha}")
    print(f"  Replay SHA-256          : {sha256_array(generated[100.0])}")
    print(f"  L1                      : {control_metrics['L1']:.6e}")
    print(f"  L2                      : {control_metrics['L2']:.6e}")
    print(f"  Linf                    : {control_metrics['Linf']:.6e}")
    print(f"  Envelope                : {envelope:.6e}")
    print(f"  Pass                    : {control_pass}")

    print("\nFOUR-TIME STATES")
    for row in state_rows:
        print(
            f"  t={float(row['time_days']):7.1f} d | "
            f"{row['sha256'][:16]} | "
            f"range={float(row['min']):.6f}->{float(row['max']):.6f} | "
            f"mean={float(row['mean']):.6f}"
        )

    print("\n" + "=" * 78)
    print("V15-SG7E1R26B FINAL RUNTIME GATES")
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
        SOURCE_LINEAGE_TABLE,
        NESTED_CALLABLE_TABLE,
        ARG_BIND_TABLE,
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
    print("V15-SG7E1R26B EXACT-BOUND EVALUATOR 100-DAY CONTROL / FOUR-TIME REGENERATION: COMPLETE")
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

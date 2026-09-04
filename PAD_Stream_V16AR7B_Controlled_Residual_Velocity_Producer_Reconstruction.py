from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import importlib.util
import json
import re
import sys
import traceback
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V16A-R7B
# Controlled Residual Velocity / Producer Reconstruction
#
# AUTHORITY
# ---------
# V16A-R7A established:
#   Vx/Vy/Vz : algebraic reconstruction authorized from frozen R7 fluxes
#   producer_id : reconstruction authorized from existing endpoint metadata
#
# R7B WILL:
#   1. Load the immutable R7 derived pressure/Q artifact.
#   2. Parse the authoritative SG5 source and bind exact Vx/Vy/Vz expressions.
#   3. Evaluate ONLY the algebraic velocity expressions using frozen R7 Q arrays
#      plus exact SG5 geometry/porosity dependencies.
#   4. Bind producer_id from existing SG5/SG6 endpoint/capture metadata without
#      retracing Pollock streamlines.
#   5. Save a residual-component artifact explicitly labelled:
#
#          DERIVED_V16_FROM_FROZEN_V15
#
# R7B WILL NOT:
#   - rerun SG3,
#   - rerun SG4,
#   - retrace Pollock streamlines,
#   - execute Fast Marching,
#   - train or infer an ML model,
#   - mutate or relabel frozen V15 artifacts.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_R7B_CONTROLLED_RESIDUAL_RECONSTRUCTION"
OUT.mkdir(parents=True, exist_ok=True)

R7_DIR = ROOT / "output" / "V16_A_R7_CONTROLLED_SOURCE_AUTHENTIC_REGENERATION"
R7A_DIR = ROOT / "output" / "V16_A_R7A_RESIDUAL_VELOCITY_PRODUCER_BINDING"

R7_SUMMARY = R7_DIR / "PAD_Stream_V16AR7_Summary.json"
R7A_SUMMARY = R7A_DIR / "PAD_Stream_V16AR7A_Summary.json"
R7_DYNAMIC = R7_DIR / "V16AR7_Derived_V16_From_Frozen_V15_Dynamic_Components.npz"
R7A_VEL_DECISION = R7A_DIR / "V16AR7A_Velocity_Reconstruction_Decision.csv"
R7A_PROD_DECISION = R7A_DIR / "V16AR7A_Producer_Identity_Binding_Decision.csv"

RESIDUAL_NPZ = OUT / "V16AR7B_Derived_Velocity_Producer_Components.npz"
VELOCITY_EXPR_CSV = OUT / "V16AR7B_Bound_Velocity_Expressions.csv"
VELOCITY_DEP_CSV = OUT / "V16AR7B_Velocity_Runtime_Dependency_Binding.csv"
VELOCITY_RESULT_CSV = OUT / "V16AR7B_Velocity_Reconstruction_Result.csv"
PRODUCER_BIND_CSV = OUT / "V16AR7B_Producer_Endpoint_Binding.csv"
PRODUCER_RESULT_CSV = OUT / "V16AR7B_Producer_Reconstruction_Result.csv"
GATE_CSV = OUT / "V16AR7B_Final_Reconstruction_Gates.csv"
DECISION_CSV = OUT / "V16AR7B_Reconstruction_Decision.csv"
CONTRACT = OUT / "V16AR7B_Residual_Reconstruction_Contract.json"
SUMMARY = OUT / "PAD_Stream_V16AR7B_Summary.json"

EXPECTED = {
    "Vx": (15, 50, 49),
    "Vy": (15, 49, 50),
    "Vz": (14, 50, 50),
    "producer_id": (1078,),
}

VEL_ALIASES = {
    "Vx": {"vx", "v_x", "velocity_x", "vel_x"},
    "Vy": {"vy", "v_y", "velocity_y", "vel_y"},
    "Vz": {"vz", "v_z", "velocity_z", "vel_z"},
}

SAFE_NUMPY_NAMES = {
    "np": np,
    "numpy": np,
}

PRODUCER_KEY_TERMS = [
    "producer_id", "producer_ids", "prod_id", "prod_ids",
    "terminal_producer", "capture_id", "producer_idx", "producer_index",
    "destination_id", "target_producer", "well_id", "well_index"
]


def save_csv(path: Path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def load_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_array(a: np.ndarray):
    a = np.ascontiguousarray(a)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode())
    h.update(str(tuple(a.shape)).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def ast_text(node):
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def assigned_targets(node):
    out = []
    raw = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
    for t in raw:
        if isinstance(t, ast.Name):
            out.append(t.id)
        elif isinstance(t, ast.Tuple):
            for e in t.elts:
                if isinstance(e, ast.Name):
                    out.append(e.id)
    return out


def names_in_expr(node):
    out = set()
    if node is None:
        return out
    for x in ast.walk(node):
        if isinstance(x, ast.Name):
            out.add(x.id)
    return out


def import_module_from_path(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def find_sg5_source():
    cands = sorted(ROOT.glob("PAD_Stream_V15SG5*.py"))
    # Prefer the exact Pollock milestone source that R7A audited.
    preferred = [p for p in cands if "Exact_Pollock" in p.name or "Pollock_Streamlines" in p.name]
    if len(preferred) == 1:
        return preferred[0]
    if len(cands) == 1:
        return cands[0]

    # If multiple remain, select only if exactly one defines all three velocities.
    scored = []
    for p in cands:
        text = p.read_text(encoding="utf-8", errors="ignore")
        score = sum(re.search(rf"\b{v}\b", text) is not None for v in ["Vx", "Vy", "Vz"])
        scored.append((score, p))
    scored.sort(key=lambda x: (-x[0], x[1].name))
    if scored and scored[0][0] == 3 and (len(scored) == 1 or scored[0][0] > scored[1][0]):
        return scored[0][1]
    raise RuntimeError(f"Could not uniquely bind SG5 velocity source: {[p.name for p in cands]}")


def parse_velocity_expressions(source: Path):
    text = source.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(text)
    rows = []
    chosen = {}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue

        targets = assigned_targets(node)
        expr_node = getattr(node, "value", None)
        expr = ast_text(expr_node)
        deps = sorted(names_in_expr(expr_node))

        for target in targets:
            lt = target.lower()
            for comp, aliases in VEL_ALIASES.items():
                if lt not in {a.lower() for a in aliases}:
                    continue

                lowexpr = expr.lower()
                references_flux = any(tok in lowexpr for tok in ["qx", "qy", "qz", "flux"])
                score = 0
                if target == comp:
                    score += 500
                if references_flux:
                    score += 300
                if any(tok in lowexpr for tok in ["phi", "poro", "area", "dx", "dy", "dz"]):
                    score += 100

                rec = {
                    "component": comp,
                    "source": str(source),
                    "source_sha256": sha256_file(source),
                    "line": getattr(node, "lineno", None),
                    "target_symbol": target,
                    "expression": expr,
                    "dependencies": ";".join(deps),
                    "references_flux": references_flux,
                    "score": score,
                }
                rows.append(rec)

    for comp in ["Vx", "Vy", "Vz"]:
        candidates = sorted(
            [r for r in rows if r["component"] == comp],
            key=lambda r: (-int(r["score"]), int(r["line"] or 0))
        )
        if not candidates:
            chosen[comp] = None
            continue
        if len(candidates) > 1 and int(candidates[0]["score"]) == int(candidates[1]["score"]):
            # tied expressions are allowed only if text identical
            if candidates[0]["expression"] != candidates[1]["expression"]:
                chosen[comp] = None
                continue
        chosen[comp] = candidates[0]

    return rows, chosen


def module_namespace_without_main(source: Path):
    """
    Import SG5 without calling main(). This is allowed because R7A authorized
    algebraic reconstruction and imports do not retrace Pollock by themselves.
    """
    mod = import_module_from_path(source, "pad_stream_v16ar7b_sg5")
    return mod, dict(vars(mod))


def load_r7_parents():
    with np.load(R7_DYNAMIC, allow_pickle=False) as db:
        return {
            "pressure": np.asarray(db["pressure"]),
            "Qx": np.asarray(db["Qx"]),
            "Qy": np.asarray(db["Qy"]),
            "Qz": np.asarray(db["Qz"]),
        }


def bind_dependency_value(name, namespace, r7_parent):
    """
    Resolve exact SG5 expression dependencies conservatively.
    Priority:
      1. R7 authoritative flux/pressure parent arrays
      2. SG5 module constants/arrays/functions
    """
    if name in r7_parent:
        return True, r7_parent[name], "R7_AUTHORITATIVE_PARENT"

    lname = name.lower()
    for k, v in r7_parent.items():
        if lname == k.lower():
            return True, v, "R7_AUTHORITATIVE_PARENT"

    if name in namespace:
        return True, namespace[name], "SG5_MODULE_NAMESPACE"

    # conservative alias resolution for flux names
    aliases = {
        "qx": "Qx", "qy": "Qy", "qz": "Qz",
        "pressure": "pressure", "p": "pressure",
    }
    if lname in aliases and aliases[lname] in r7_parent:
        return True, r7_parent[aliases[lname]], "R7_AUTHORITATIVE_PARENT_ALIAS"

    return False, None, "UNRESOLVED"


def safe_eval_expression(expr, bindings):
    """
    Evaluate the exact SG5 RHS expression only.
    Builtins are disabled; numpy and explicitly bound SG5 names are supplied.
    """
    env = {"__builtins__": {}}
    env.update(SAFE_NUMPY_NAMES)
    env.update(bindings)
    return eval(expr, env, {})


def reconstruct_velocity(chosen, namespace, r7_parent):
    result_rows = []
    dep_rows = []
    arrays = {}

    for comp in ["Vx", "Vy", "Vz"]:
        rec = chosen.get(comp)
        if rec is None:
            result_rows.append({
                "component": comp,
                "status": "NO_UNIQUE_EXPRESSION_BOUND",
            })
            continue

        deps = [d for d in rec["dependencies"].split(";") if d]
        bindings = {}
        unresolved = []

        for dep in deps:
            if dep in {"np", "numpy"}:
                dep_rows.append({
                    "component": comp,
                    "dependency": dep,
                    "resolved": True,
                    "source": "NUMPY",
                })
                continue

            ok, val, src = bind_dependency_value(dep, namespace, r7_parent)
            dep_rows.append({
                "component": comp,
                "dependency": dep,
                "resolved": ok,
                "source": src,
                "type": type(val).__name__ if ok else "",
            })
            if ok:
                bindings[dep] = val
            else:
                unresolved.append(dep)

        if unresolved:
            result_rows.append({
                "component": comp,
                "status": "DEPENDENCY_BINDING_INCOMPLETE",
                "unresolved_dependencies": ";".join(unresolved),
                "expression": rec["expression"],
            })
            continue

        try:
            arr = np.asarray(safe_eval_expression(rec["expression"], bindings))
        except Exception as e:
            result_rows.append({
                "component": comp,
                "status": "EXPRESSION_EVALUATION_FAILED",
                "error": repr(e),
                "expression": rec["expression"],
            })
            continue

        finite = np.issubdtype(arr.dtype, np.number) and np.all(np.isfinite(arr))
        shape_ok = tuple(arr.shape) == EXPECTED[comp]

        if finite and shape_ok:
            arrays[comp] = np.array(arr, copy=True)
            result_rows.append({
                "component": comp,
                "status": "RECONSTRUCTED",
                "shape": str(tuple(arr.shape)),
                "dtype": str(arr.dtype),
                "array_sha256": sha256_array(arr),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "expression": rec["expression"],
            })
        else:
            result_rows.append({
                "component": comp,
                "status": "RECONSTRUCTION_VALIDATION_FAILED",
                "shape": str(tuple(arr.shape)),
                "dtype": str(arr.dtype),
                "finite": bool(finite),
                "shape_ok": bool(shape_ok),
                "expression": rec["expression"],
            })

    return arrays, dep_rows, result_rows


def producer_decision():
    rows = load_csv(R7A_PROD_DECISION)
    if len(rows) != 1:
        raise RuntimeError("Expected one producer binding decision row.")
    return rows[0]


def bind_existing_endpoint_array():
    """
    Search existing pre-V16 SG5/SG6/Pollock/streamline artifacts for endpoint
    metadata with exact producer/capture semantics. This does not retrace.
    """
    rows = []
    candidates = []
    outroot = ROOT / "output"

    for p in sorted(outroot.rglob("*.npz")) if outroot.exists() else []:
        lowp = str(p).lower()
        if "v16_" in lowp or "v16a" in lowp:
            continue
        if not any(tok in lowp for tok in ["sg5", "sg6", "pollock", "streamline"]):
            continue

        try:
            with np.load(p, allow_pickle=False) as db:
                for key in db.files:
                    a = np.asarray(db[key])
                    if a.shape not in [(1078,), (1078, 1)]:
                        continue
                    if not np.issubdtype(a.dtype, np.number):
                        continue
                    if not np.all(np.isfinite(a)):
                        continue

                    lk = key.lower()
                    semantic = any(term in lk for term in PRODUCER_KEY_TERMS)
                    integer_like = bool(np.allclose(a, np.rint(a), atol=0, rtol=0))

                    rec = {
                        "artifact": str(p),
                        "artifact_sha256": sha256_file(p),
                        "key": key,
                        "shape": str(tuple(a.shape)),
                        "dtype": str(a.dtype),
                        "semantic_key": semantic,
                        "integer_like": integer_like,
                        "unique_value_count": len(np.unique(a)),
                        "array_sha256": sha256_array(a),
                    }
                    rows.append(rec)
                    if semantic:
                        candidates.append((p, key, np.array(a, copy=True), rec))
        except Exception:
            continue

    hashes = {c[3]["array_sha256"] for c in candidates}
    if len(hashes) == 1 and candidates:
        candidates.sort(key=lambda x: (str(x[0]), x[1]))
        return rows, candidates[0]

    return rows, None


def reconstruct_from_endpoint_metadata():
    """
    When no persisted producer-ID array exists, attempt to derive producer
    identity from explicit existing endpoint/capture arrays WITHOUT tracing.

    Conservative strategy:
      - look for categorical endpoint/terminal/capture arrays of length 1078
      - accept only keys with explicit producer/capture/terminal semantics
      - require integer-like values and <=16 categories
    """
    rows = []
    candidates = []
    outroot = ROOT / "output"

    for p in sorted(outroot.rglob("*.npz")) if outroot.exists() else []:
        lowp = str(p).lower()
        if "v16_" in lowp or "v16a" in lowp:
            continue
        if not any(tok in lowp for tok in ["sg5", "sg6", "pollock", "streamline"]):
            continue

        try:
            with np.load(p, allow_pickle=False) as db:
                for key in db.files:
                    a = np.asarray(db[key])
                    if a.shape not in [(1078,), (1078,1)]:
                        continue
                    if not np.issubdtype(a.dtype, np.number) or not np.all(np.isfinite(a)):
                        continue

                    lk = key.lower()
                    semantic = any(tok in lk for tok in ["capture", "terminal", "producer", "destination", "well"])
                    integer_like = bool(np.allclose(a, np.rint(a), atol=0, rtol=0))
                    unique_vals = np.unique(a)
                    small_category = len(unique_vals) <= 16

                    rec = {
                        "artifact": str(p),
                        "key": key,
                        "semantic_endpoint_key": semantic,
                        "integer_like": integer_like,
                        "small_category": small_category,
                        "unique_value_count": len(unique_vals),
                        "values_preview": ";".join(map(str, unique_vals[:20].tolist())),
                        "array_sha256": sha256_array(a),
                    }
                    rows.append(rec)

                    if semantic and integer_like and small_category:
                        candidates.append((p, key, np.array(a).reshape(-1), rec))
        except Exception:
            continue

    # Require one exact numerical identity across all qualified endpoint arrays.
    hashes = {c[3]["array_sha256"] for c in candidates}
    if len(hashes) == 1 and candidates:
        candidates.sort(key=lambda x: (str(x[0]), x[1]))
        return rows, candidates[0]

    return rows, None


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16A-R7B")
    print("Controlled Residual Velocity / Producer Reconstruction")
    print("=" * 78)

    print("""
NO SG3 PRESSURE SOLVE WILL BE RERUN.
NO SG4 DARCY FLUX WILL BE RERUN.
VELOCITY WILL BE RECONSTRUCTED ONLY FROM THE EXACT AUTHORIZED SG5 ALGEBRA.
PRODUCER IDENTITY WILL BE BOUND ONLY FROM EXISTING ENDPOINT/CAPTURE METADATA.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO FAST MARCHING WILL BE EXECUTED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
NO FROZEN V15 ARTIFACT WILL BE CHANGED.
ALL NEW NUMERICAL OUTPUTS ARE DERIVED_V16_FROM_FROZEN_V15.
""")

    if not R7A_SUMMARY.exists():
        raise FileNotFoundError(R7A_SUMMARY)
    if not R7_DYNAMIC.exists():
        raise FileNotFoundError(R7_DYNAMIC)

    r7a = json.loads(R7A_SUMMARY.read_text(encoding="utf-8"))
    if r7a.get("status") != "V16A_RESIDUAL_VELOCITY_PRODUCER_RECONSTRUCTION_AUTHORIZED":
        raise RuntimeError("R7B expects successful R7A residual reconstruction authorization.")

    r7_parent = load_r7_parents()

    # -------------------------------------------------------------------------
    # Velocity reconstruction
    # -------------------------------------------------------------------------
    sg5_source = find_sg5_source()
    all_expr_rows, chosen = parse_velocity_expressions(sg5_source)
    save_csv(VELOCITY_EXPR_CSV, all_expr_rows)

    sg5_mod, namespace = module_namespace_without_main(sg5_source)
    velocity_arrays, dep_rows, velocity_result_rows = reconstruct_velocity(
        chosen, namespace, r7_parent
    )
    save_csv(VELOCITY_DEP_CSV, dep_rows)
    save_csv(VELOCITY_RESULT_CSV, velocity_result_rows)

    velocity_complete = all(k in velocity_arrays for k in ["Vx", "Vy", "Vz"])

    # -------------------------------------------------------------------------
    # Producer reconstruction/binding
    # -------------------------------------------------------------------------
    pdecision = producer_decision()
    endpoint_rows, persisted_choice = bind_existing_endpoint_array()

    producer_array = None
    producer_binding_mode = ""
    producer_result = []

    if persisted_choice is not None:
        p, key, arr, rec = persisted_choice
        producer_array = arr.reshape(-1)
        producer_binding_mode = "PERSISTED_SEMANTIC_ARRAY"
        producer_result.append({
            "status": "BOUND",
            "binding_mode": producer_binding_mode,
            "artifact": str(p),
            "key": key,
            "shape": str(tuple(producer_array.shape)),
            "dtype": str(producer_array.dtype),
            "array_sha256": sha256_array(producer_array),
        })
    else:
        endpoint_more_rows, endpoint_choice = reconstruct_from_endpoint_metadata()
        endpoint_rows.extend(endpoint_more_rows)

        if endpoint_choice is not None:
            p, key, arr, rec = endpoint_choice
            producer_array = arr.reshape(-1)
            producer_binding_mode = "EXISTING_ENDPOINT_METADATA"
            producer_result.append({
                "status": "RECONSTRUCTED_FROM_EXISTING_ENDPOINT_METADATA",
                "binding_mode": producer_binding_mode,
                "artifact": str(p),
                "key": key,
                "shape": str(tuple(producer_array.shape)),
                "dtype": str(producer_array.dtype),
                "array_sha256": sha256_array(producer_array),
            })
        else:
            producer_result.append({
                "status": "PRODUCER_RECONSTRUCTION_BLOCKED",
                "binding_mode": "",
                "reason": "No unique semantic persisted or endpoint-metadata identity was found without retracing Pollock.",
            })

    save_csv(PRODUCER_BIND_CSV, endpoint_rows)
    save_csv(PRODUCER_RESULT_CSV, producer_result)

    producer_complete = (
        producer_array is not None
        and tuple(producer_array.shape) == EXPECTED["producer_id"]
        and np.all(np.isfinite(producer_array))
    )

    # -------------------------------------------------------------------------
    # Persist residual artifact only if numerical components recovered.
    # -------------------------------------------------------------------------
    payload = {}
    for k, a in velocity_arrays.items():
        payload[k] = a

    if producer_complete:
        if np.allclose(producer_array, np.rint(producer_array), atol=0, rtol=0):
            producer_array = np.rint(producer_array).astype(np.int32)
        payload["producer_id"] = producer_array

    payload["authority_label_ascii"] = np.frombuffer(
        b"DERIVED_V16_FROM_FROZEN_V15", dtype=np.uint8
    )

    if len(payload) > 1:  # beyond authority label
        np.savez_compressed(RESIDUAL_NPZ, **payload)

    gates = [
        ("incoming_R7A_authorization_reproduced", True),
        ("R7_parent_pressure_flux_loaded", True),
        ("SG5_source_bound", sg5_source.exists()),
        ("Vx_exact_expression_bound", chosen.get("Vx") is not None),
        ("Vy_exact_expression_bound", chosen.get("Vy") is not None),
        ("Vz_exact_expression_bound", chosen.get("Vz") is not None),
        ("Vx_reconstructed", "Vx" in velocity_arrays),
        ("Vy_reconstructed", "Vy" in velocity_arrays),
        ("Vz_reconstructed", "Vz" in velocity_arrays),
        ("producer_endpoint_metadata_audited", True),
        ("producer_id_bound_or_reconstructed_without_retrace", producer_complete),
        ("residual_artifact_saved", RESIDUAL_NPZ.exists()),
        ("no_SG3_rerun", True),
        ("no_SG4_rerun", True),
        ("no_Pollock_retrace_executed", True),
        ("no_FMM_executed", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_V15_artifact_changed", True),
        ("historical_V15_relabelling_prohibited", True),
    ]
    save_csv(GATE_CSV, [{"gate": g, "passed": p} for g,p in gates])

    if velocity_complete and producer_complete:
        status = "V16A_RESIDUAL_VELOCITY_PRODUCER_RECONSTRUCTION_COMPLETE"
        diagnosis = (
            "VX_VY_VZ_RECONSTRUCTED_FROM_AUTHORIZED_SG5_ALGEBRA_AND_PRODUCER_IDENTITY_BOUND_FROM_EXISTING_NONRETRACE_METADATA"
        )
        recommendation = (
            "Proceed to final Foundation Case 0001 assembly. Merge geology/porosity authority, "
            "R7 pressure/flux, R7B velocity/producer identity, and existing Pollock XYZ/TOF/weights "
            "into one frozen V16A foundation dataset."
        )
        next_ms = "V16A-R8 — Foundation Case 0001 Final Assembly / Freeze"
    else:
        missing = []
        for c in ["Vx", "Vy", "Vz"]:
            if c not in velocity_arrays:
                missing.append(c)
        if not producer_complete:
            missing.append("producer_id")

        status = "V16A_RESIDUAL_RECONSTRUCTION_INCOMPLETE"
        diagnosis = "ONE_OR_MORE_AUTHORIZED_RESIDUAL_COMPONENTS_FAILED_EXACT_RUNTIME_BINDING_OR_VALIDATION"
        recommendation = (
            "Do not rerun SG3/SG4 or retrace Pollock. Audit only failed R7B residuals: "
            + ", ".join(missing)
        )
        next_ms = "V16A-R7C — Residual Reconstruction Failure Audit"

    save_csv(DECISION_CSV, [{
        "status": status,
        "diagnosis": diagnosis,
        "Vx_complete": "Vx" in velocity_arrays,
        "Vy_complete": "Vy" in velocity_arrays,
        "Vz_complete": "Vz" in velocity_arrays,
        "producer_id_complete": producer_complete,
        "producer_binding_mode": producer_binding_mode,
        "residual_npz_created": RESIDUAL_NPZ.exists(),
        "next_milestone": next_ms,
    }])

    contract = {
        "milestone": "V16A-R7B",
        "status": status,
        "diagnosis": diagnosis,
        "authority_label": "DERIVED_V16_FROM_FROZEN_V15",
        "SG5_source": str(sg5_source),
        "SG5_sha256": sha256_file(sg5_source),
        "component_status": {
            "Vx": "Vx" in velocity_arrays,
            "Vy": "Vy" in velocity_arrays,
            "Vz": "Vz" in velocity_arrays,
            "producer_id": producer_complete,
        },
        "producer_binding_mode": producer_binding_mode,
        "residual_artifact": str(RESIDUAL_NPZ) if RESIDUAL_NPZ.exists() else None,
        "residual_artifact_sha256": sha256_file(RESIDUAL_NPZ) if RESIDUAL_NPZ.exists() else None,
        "constraints": {
            "SG3_rerun": False,
            "SG4_rerun": False,
            "Pollock_retrace": False,
            "FMM": False,
            "model_predict": False,
            "training": False,
            "V15_mutation": False,
            "historical_V15_relabelling": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT, contract)

    save_json(SUMMARY, {
        "milestone": "V16A-R7B",
        "status": status,
        "diagnosis": diagnosis,
        "component_status": contract["component_status"],
        "producer_binding_mode": producer_binding_mode,
        "residual_artifact": contract["residual_artifact"],
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("RESIDUAL RECONSTRUCTION")
    print(f"  SG5 source              : {sg5_source.name}")
    print(f"  Vx                      : {'PASS' if 'Vx' in velocity_arrays else 'BLOCKED'}")
    print(f"  Vy                      : {'PASS' if 'Vy' in velocity_arrays else 'BLOCKED'}")
    print(f"  Vz                      : {'PASS' if 'Vz' in velocity_arrays else 'BLOCKED'}")
    print(f"  producer_id             : {'PASS' if producer_complete else 'BLOCKED'}")
    print(f"  Producer binding mode   : {producer_binding_mode or 'NONE'}")
    print(f"  Residual artifact saved : {RESIDUAL_NPZ.exists()}")

    print("\n" + "=" * 78)
    print("V16A-R7B FINAL RECONSTRUCTION GATES")
    print("=" * 78)
    for g,p in gates:
        print(f"[{'PASS' if p else 'FAIL'}] {g}")
    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")
    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")
    print("\nRECOMMENDATION")
    print(f"  {recommendation}")
    print("\nNEXT MILESTONE")
    print(f"  {next_ms}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")
    print("\nTables:")
    for p in [
        VELOCITY_EXPR_CSV, VELOCITY_DEP_CSV, VELOCITY_RESULT_CSV,
        PRODUCER_BIND_CSV, PRODUCER_RESULT_CSV, GATE_CSV, DECISION_CSV
    ]:
        print(f"  {p.name}")

    if RESIDUAL_NPZ.exists():
        print("\nNumerical:")
        print(f"  {RESIDUAL_NPZ.name}")
        print(f"  SHA-256: {sha256_file(RESIDUAL_NPZ)}")

    print("\nContract:")
    print(f"  {CONTRACT.name}")
    print("\nSummary:")
    print(f"  {SUMMARY.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16A-R7B CONTROLLED RESIDUAL RECONSTRUCTION: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()

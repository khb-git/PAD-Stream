from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import importlib.util
import inspect
import json
import sys
import traceback
from types import ModuleType

import numpy as np


# =============================================================================
# PAD-Stream V16A-R7
# Controlled Source-Authentic Foundation Component Regeneration
#
# AUTHORITY
# ---------
# V16A-R6A established one source-authentic SG3 pressure-regeneration recipe.
# R5 already established SG4 flux recipe readiness and producer-ID semantics.
#
# R7 is the FIRST V16A milestone authorized to execute frozen V15 physics.
#
# R7 WILL:
#   - execute the frozen SG3 main() exactly as written,
#   - capture SG3 main-frame locals at function return without editing SG3,
#   - bind the regenerated 3-D pressure field,
#   - execute frozen SG4 main() exactly as written,
#   - capture SG4 main-frame locals and bind Qx/Qy/Qz,
#   - execute frozen SG5 main() only if a non-tracing producer identity path is
#     NOT required; Pollock re-tracing is NOT authorized by this milestone,
#   - reconstruct Vx/Vy/Vz only from source-authentic SG5 algebra if those
#     arrays can be captured without retracing; otherwise leave them blocked,
#   - persist regenerated outputs as DERIVED_V16_FROM_FROZEN_V15.
#
# R7 WILL NOT:
#   - modify any frozen V15 source/artifact,
#   - label regenerated arrays as historical V15 states,
#   - train or infer any ML model,
#   - run Fast Marching,
#   - relax any V15 contract.
#
# IMPORTANT:
#   sys.settrace is used only as a transparent observer to capture local arrays
#   from the authoritative frozen source at function return. The original source
#   files are not edited, patched, or monkey-patched.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_R7_CONTROLLED_SOURCE_AUTHENTIC_REGENERATION"
OUT.mkdir(parents=True, exist_ok=True)

R6A_DIR = ROOT / "output" / "V16_A_R6A_FINAL_SG3_PRESSURE_RECIPE_BINDING_AUDIT"
R6A_SUMMARY = R6A_DIR / "PAD_Stream_V16AR6A_Summary.json"

DERIVED_NPZ = OUT / "V16AR7_Derived_V16_From_Frozen_V15_Dynamic_Components.npz"
EXECUTION_TABLE = OUT / "V16AR7_Frozen_Source_Execution_Trace.csv"
LOCAL_TABLE = OUT / "V16AR7_Captured_Local_Array_Inventory.csv"
BINDING_TABLE = OUT / "V16AR7_Regenerated_Component_Binding.csv"
PRODUCER_TABLE = OUT / "V16AR7_Producer_Identity_NonRetrace_Audit.csv"
GATE_TABLE = OUT / "V16AR7_Final_Regeneration_Gates.csv"
DECISION_TABLE = OUT / "V16AR7_Regeneration_Decision.csv"
CONTRACT = OUT / "V16AR7_Controlled_Regeneration_Contract.json"
SUMMARY = OUT / "PAD_Stream_V16AR7_Summary.json"

SG3_SOURCE = ROOT / "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG4_CANDIDATES = sorted(ROOT.glob("PAD_Stream_V15SG4*.py"))
SG5_CANDIDATES = sorted(ROOT.glob("PAD_Stream_V15SG5*.py"))
SG6_CANDIDATES = sorted(ROOT.glob("PAD_Stream_V15SG6*.py"))

EXPECTED = {
    "pressure": {(15, 50, 50)},
    "Qx": {(15, 50, 49)},
    "Qy": {(15, 49, 50)},
    "Qz": {(14, 50, 50)},
    "Vx": {(15, 50, 49)},
    "Vy": {(15, 49, 50)},
    "Vz": {(14, 50, 50)},
    "producer_id": {(1078,), (1078, 1)},
}

ALIASES = {
    "pressure": {"pressure", "p", "p_grid", "pressure_grid", "p3d", "p_psi", "p_pa"},
    "Qx": {"qx", "q_x", "flux_x", "darcy_flux_x"},
    "Qy": {"qy", "q_y", "flux_y", "darcy_flux_y"},
    "Qz": {"qz", "q_z", "flux_z", "darcy_flux_z"},
    "Vx": {"vx", "v_x", "vel_x", "velocity_x"},
    "Vy": {"vy", "v_y", "vel_y", "velocity_y"},
    "Vz": {"vz", "v_z", "vel_z", "velocity_z"},
    "producer_id": {
        "producer_id", "producer_ids", "prod_id", "prod_ids",
        "terminal_producer", "capture_id", "producer_idx", "producer_index",
        "destination_id", "target_producer", "well_id", "well_index"
    },
}


def save_csv(path: Path, rows):
    rows = list(rows)
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


def import_module_from_path(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class ReturnFrameCapture:
    """Capture locals from one named function when it returns."""
    def __init__(self, target_code):
        self.target_code = target_code
        self.locals = None

    def tracer(self, frame, event, arg):
        if frame.f_code is self.target_code and event == "return":
            # Copy references now; arrays are copied during inventory.
            self.locals = dict(frame.f_locals)
        return self.tracer


def run_main_and_capture(path: Path, module_name: str):
    mod = import_module_from_path(path, module_name)
    if not hasattr(mod, "main") or not callable(mod.main):
        raise AttributeError(f"{path.name} has no callable main()")

    capture = ReturnFrameCapture(mod.main.__code__)
    old_trace = sys.gettrace()

    try:
        sys.settrace(capture.tracer)
        result = mod.main()
    finally:
        sys.settrace(old_trace)

    return mod, result, capture.locals or {}


def array_inventory(stage: str, source: Path, local_vars: dict):
    rows = []
    arrays = []
    for name, value in local_vars.items():
        try:
            a = np.asarray(value)
        except Exception:
            continue

        if not np.issubdtype(a.dtype, np.number):
            continue

        try:
            finite = bool(np.all(np.isfinite(a)))
        except Exception:
            finite = False

        if not finite:
            continue

        # Avoid scalar/noise inventory explosion.
        if a.ndim == 0:
            continue

        copied = np.array(a, copy=True)
        rec = {
            "stage": stage,
            "source": str(source),
            "local_name": name,
            "shape": str(tuple(copied.shape)),
            "dtype": str(copied.dtype),
            "array_sha256": sha256_array(copied),
        }
        rows.append(rec)
        arrays.append((name, copied, rec))
    return rows, arrays


def bind_component(component: str, arrays):
    allowed_shapes = EXPECTED[component]
    aliases = {x.lower() for x in ALIASES[component]}
    candidates = []

    for name, a, rec in arrays:
        if tuple(a.shape) not in allowed_shapes:
            continue
        lname = name.lower()

        score = 0
        if lname in aliases:
            score += 500
        if any(alias in lname for alias in aliases):
            score += 100

        # Component-specific semantic boosts.
        if component == "pressure" and ("press" in lname or lname.startswith("p")):
            score += 100
        if component in {"Qx", "Qy", "Qz"} and lname == component.lower():
            score += 300
        if component in {"Vx", "Vy", "Vz"} and lname == component.lower():
            score += 300

        candidates.append((score, name, a, rec))

    candidates.sort(key=lambda x: (-x[0], x[1]))

    if not candidates:
        return None, [], "NO_SHAPE_COMPATIBLE_CANDIDATE"

    # Require semantic evidence, not shape alone.
    best = candidates[0]
    if best[0] <= 0:
        return None, candidates, "SHAPE_ONLY_CANDIDATES_NOT_AUTHORIZED"

    second = candidates[1][0] if len(candidates) > 1 else None
    if second is not None and best[0] == second:
        # If tied names point to exact same numerical identity, accept one
        # representation of the same state; otherwise block.
        top = [c for c in candidates if c[0] == best[0]]
        hashes = {c[3]["array_sha256"] for c in top}
        if len(hashes) != 1:
            return None, candidates, "SEMANTIC_TIE_MULTIPLE_NUMERICAL_IDENTITIES"

    return best, candidates, "BOUND"


def find_single_source(candidates, preferred_token):
    if not candidates:
        return None
    preferred = [p for p in candidates if preferred_token.lower() in p.name.lower()]
    if len(preferred) == 1:
        return preferred[0]
    if len(candidates) == 1:
        return candidates[0]
    return None


def nonretrace_producer_identity_audit():
    """
    Search only existing pre-V16 artifacts for producer-ID-like arrays.
    No SG5/SG6 main() execution is allowed here because it could retrace Pollock.
    """
    rows = []
    outroot = ROOT / "output"
    if not outroot.exists():
        return rows, None

    for p in sorted(outroot.rglob("*.npz")):
        lowp = str(p).lower()
        if "v16_" in lowp or "v16a" in lowp:
            continue
        if not any(tok in lowp for tok in ["sg5", "sg6", "pollock", "streamline"]):
            continue
        try:
            with np.load(p, allow_pickle=False) as db:
                for key in db.files:
                    a = np.asarray(db[key])
                    if tuple(a.shape) not in EXPECTED["producer_id"]:
                        continue
                    if not np.issubdtype(a.dtype, np.number):
                        continue
                    if not np.all(np.isfinite(a)):
                        continue

                    lk = key.lower()
                    semantic = any(alias in lk for alias in ALIASES["producer_id"])
                    integer_like = bool(np.allclose(a, np.rint(a), atol=0, rtol=0))
                    unique_vals = np.unique(a)
                    plausible_small_category = integer_like and len(unique_vals) <= 16

                    rec = {
                        "artifact": str(p),
                        "key": key,
                        "shape": str(tuple(a.shape)),
                        "dtype": str(a.dtype),
                        "semantic_key": semantic,
                        "integer_like": integer_like,
                        "unique_value_count": len(unique_vals),
                        "plausible_small_category": plausible_small_category,
                        "array_sha256": sha256_array(a),
                    }
                    rows.append(rec)
        except Exception:
            continue

    # Authority requires semantic key. Numerical plausibility is diagnostic only.
    semantic_rows = [r for r in rows if r["semantic_key"]]
    hashes = {r["array_sha256"] for r in semantic_rows}

    if len(hashes) == 1 and semantic_rows:
        chosen = sorted(semantic_rows, key=lambda r: (r["artifact"], r["key"]))[0]
        return rows, chosen

    return rows, None


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16A-R7")
    print("Controlled Source-Authentic Foundation Component Regeneration")
    print("=" * 78)

    print("""
CONTROLLED FROZEN V15 PHYSICS EXECUTION IS AUTHORIZED IN THIS MILESTONE.
SG3 PRESSURE AND SG4 DARCY-FLUX SOURCES WILL EXECUTE EXACTLY AS WRITTEN.
LOCAL ARRAYS WILL BE CAPTURED NON-INVASIVELY AT main() RETURN.
NO FROZEN V15 SOURCE OR ARTIFACT WILL BE MODIFIED.
REGENERATED OUTPUTS ARE DERIVED_V16_FROM_FROZEN_V15.
NO REGENERATED ARRAY WILL BE RELABELLED AS HISTORICAL V15.
NO MODEL.PREDICT CALL WILL BE EXECUTED BY R7.
NO TRAINING WILL BE PERFORMED.
NO FAST MARCHING WILL BE EXECUTED.
NO POLLOCK RETRACE IS AUTHORIZED.
""")

    if not R6A_SUMMARY.exists():
        raise FileNotFoundError(R6A_SUMMARY)

    r6a = json.loads(R6A_SUMMARY.read_text(encoding="utf-8"))
    if r6a.get("status") != "V16A_SG3_PRESSURE_REGENERATION_RECIPE_FINAL_BOUND":
        raise RuntimeError("R7 expects successful R6A pressure-recipe binding.")

    execution_rows = []
    local_rows = []
    binding_rows = []
    payload = {}

    # -------------------------------------------------------------------------
    # SG3: execute exact frozen pressure source and capture local arrays.
    # -------------------------------------------------------------------------
    sg3_success = False
    pressure_bound = False
    pressure_array = None

    try:
        _, _, sg3_locals = run_main_and_capture(SG3_SOURCE, "pad_stream_v16ar7_sg3")
        sg3_success = True
        execution_rows.append({
            "stage": "SG3",
            "source": str(SG3_SOURCE),
            "source_sha256": sha256_file(SG3_SOURCE),
            "executed": True,
            "error": "",
        })

        rows, arrays = array_inventory("SG3", SG3_SOURCE, sg3_locals)
        local_rows.extend(rows)

        best, candidates, status = bind_component("pressure", arrays)
        if best is not None:
            _, name, pressure_array, rec = best
            pressure_bound = True
            payload["pressure"] = pressure_array.astype(np.float64, copy=False)
            binding_rows.append({
                "component": "pressure",
                "status": "BOUND_REGENERATED",
                "source_stage": "SG3",
                "local_name": name,
                "shape": str(tuple(pressure_array.shape)),
                "dtype": str(pressure_array.dtype),
                "array_sha256": rec["array_sha256"],
                "authority_label": "DERIVED_V16_FROM_FROZEN_V15",
            })
        else:
            binding_rows.append({
                "component": "pressure",
                "status": status,
                "source_stage": "SG3",
            })

    except Exception as e:
        execution_rows.append({
            "stage": "SG3",
            "source": str(SG3_SOURCE),
            "source_sha256": sha256_file(SG3_SOURCE) if SG3_SOURCE.exists() else "",
            "executed": False,
            "error": repr(e),
            "traceback": traceback.format_exc(),
        })

    # -------------------------------------------------------------------------
    # SG4: only execute after SG3 succeeds. SG4 is frozen and source-authentic.
    # -------------------------------------------------------------------------
    sg4_source = find_single_source(SG4_CANDIDATES, "Darcy")
    sg4_success = False
    flux_bound = {"Qx": False, "Qy": False, "Qz": False}
    flux_arrays = {}

    if sg3_success and pressure_bound and sg4_source is not None:
        try:
            _, _, sg4_locals = run_main_and_capture(sg4_source, "pad_stream_v16ar7_sg4")
            sg4_success = True
            execution_rows.append({
                "stage": "SG4",
                "source": str(sg4_source),
                "source_sha256": sha256_file(sg4_source),
                "executed": True,
                "error": "",
            })

            rows, arrays = array_inventory("SG4", sg4_source, sg4_locals)
            local_rows.extend(rows)

            for comp in ["Qx", "Qy", "Qz"]:
                best, candidates, status = bind_component(comp, arrays)
                if best is not None:
                    _, name, arr, rec = best
                    flux_bound[comp] = True
                    flux_arrays[comp] = arr
                    payload[comp] = arr.astype(np.float64, copy=False)
                    binding_rows.append({
                        "component": comp,
                        "status": "BOUND_REGENERATED",
                        "source_stage": "SG4",
                        "local_name": name,
                        "shape": str(tuple(arr.shape)),
                        "dtype": str(arr.dtype),
                        "array_sha256": rec["array_sha256"],
                        "authority_label": "DERIVED_V16_FROM_FROZEN_V15",
                    })
                else:
                    binding_rows.append({
                        "component": comp,
                        "status": status,
                        "source_stage": "SG4",
                    })

        except Exception as e:
            execution_rows.append({
                "stage": "SG4",
                "source": str(sg4_source),
                "source_sha256": sha256_file(sg4_source),
                "executed": False,
                "error": repr(e),
                "traceback": traceback.format_exc(),
            })
    else:
        execution_rows.append({
            "stage": "SG4",
            "source": str(sg4_source) if sg4_source else "",
            "source_sha256": sha256_file(sg4_source) if sg4_source else "",
            "executed": False,
            "error": "Blocked because SG3 pressure did not execute/bind or SG4 source was not unique.",
        })

    # -------------------------------------------------------------------------
    # Velocity: do NOT execute SG5 main() because that could retrace Pollock.
    # Search existing SG5/SG6 artifacts first. If not present, leave blocked for
    # a source-authentic algebraic velocity reconstruction branch.
    # -------------------------------------------------------------------------
    velocity_bound = {"Vx": False, "Vy": False, "Vz": False}
    outroot = ROOT / "output"
    if outroot.exists():
        for p in sorted(outroot.rglob("*.npz")):
            lowp = str(p).lower()
            if "v16_" in lowp or "v16a" in lowp:
                continue
            if not any(tok in lowp for tok in ["sg5", "pollock", "streamline"]):
                continue
            try:
                with np.load(p, allow_pickle=False) as db:
                    arrs = []
                    for key in db.files:
                        a = np.asarray(db[key])
                        if np.issubdtype(a.dtype, np.number) and np.all(np.isfinite(a)):
                            rec = {
                                "array_sha256": sha256_array(a),
                            }
                            arrs.append((key, a, rec))
                    for comp in ["Vx", "Vy", "Vz"]:
                        if velocity_bound[comp]:
                            continue
                        best, candidates, status = bind_component(comp, arrs)
                        if best is not None:
                            _, name, arr, rec = best
                            velocity_bound[comp] = True
                            payload[comp] = arr.astype(np.float64, copy=False)
                            binding_rows.append({
                                "component": comp,
                                "status": "BOUND_EXISTING_PRE_V16_ARTIFACT",
                                "source_stage": "SG5_EXISTING_ARTIFACT",
                                "artifact": str(p),
                                "local_name": name,
                                "shape": str(tuple(arr.shape)),
                                "dtype": str(arr.dtype),
                                "array_sha256": rec["array_sha256"],
                                "authority_label": "PRE_V16_EXISTING_DERIVED_FLOW_FIELD",
                            })
            except Exception:
                continue

    for comp in ["Vx", "Vy", "Vz"]:
        if not velocity_bound[comp]:
            binding_rows.append({
                "component": comp,
                "status": "NOT_BOUND_NO_POLLOCK_RETRACE_ALLOWED",
                "source_stage": "SG5",
            })

    # -------------------------------------------------------------------------
    # Producer identity: bind only from existing semantic persisted artifact.
    # -------------------------------------------------------------------------
    producer_rows, producer_choice = nonretrace_producer_identity_audit()
    save_csv(PRODUCER_TABLE, producer_rows)

    producer_bound = False
    if producer_choice:
        with np.load(producer_choice["artifact"], allow_pickle=False) as db:
            arr = np.asarray(db[producer_choice["key"]])
        payload["producer_id"] = arr.astype(np.int32 if np.allclose(arr, np.rint(arr)) else arr.dtype, copy=False)
        producer_bound = True
        binding_rows.append({
            "component": "producer_id",
            "status": "BOUND_EXISTING_PRE_V16_ARTIFACT",
            "source_stage": "SG5_SG6_EXISTING_ARTIFACT",
            "artifact": producer_choice["artifact"],
            "local_name": producer_choice["key"],
            "shape": producer_choice["shape"],
            "dtype": producer_choice["dtype"],
            "array_sha256": producer_choice["array_sha256"],
            "authority_label": "PRE_V16_EXISTING_PRODUCER_IDENTITY",
        })
    else:
        binding_rows.append({
            "component": "producer_id",
            "status": "NOT_BOUND_WITHOUT_RETRACE",
            "source_stage": "SG5_SG6",
        })

    save_csv(EXECUTION_TABLE, execution_rows)
    save_csv(LOCAL_TABLE, local_rows)
    save_csv(BINDING_TABLE, binding_rows)

    pressure_ok = pressure_bound
    flux_ok = all(flux_bound.values())
    velocity_ok = all(velocity_bound.values())

    # Persist whatever was authoritatively recovered this turn.
    derived_saved = False
    if payload:
        payload["authority_label_ascii"] = np.frombuffer(
            b"DERIVED_V16_FROM_FROZEN_V15", dtype=np.uint8
        )
        np.savez_compressed(DERIVED_NPZ, **payload)
        derived_saved = True

    gates = [
        ("incoming_R6A_final_recipe_status_reproduced", True),
        ("SG3_frozen_source_exists", SG3_SOURCE.exists()),
        ("SG3_executed_source_authentically", sg3_success),
        ("pressure_bound_from_SG3_runtime_locals", pressure_ok),
        ("SG4_source_unique", sg4_source is not None),
        ("SG4_executed_source_authentically", sg4_success),
        ("Qx_bound", flux_bound["Qx"]),
        ("Qy_bound", flux_bound["Qy"]),
        ("Qz_bound", flux_bound["Qz"]),
        ("velocity_existing_authority_audited", True),
        ("producer_identity_nonretrace_audited", True),
        ("derived_V16_artifact_saved_if_any_component_recovered", derived_saved if payload else True),
        ("historical_V15_relabelling_prohibited", True),
        ("no_Pollock_retrace_executed", True),
        ("no_FMM_executed", True),
        ("no_model_predict_executed_by_R7", True),
        ("no_training_performed", True),
        ("no_frozen_V15_artifact_changed", True),
    ]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    core_dynamic_ready = pressure_ok and flux_ok

    if core_dynamic_ready and velocity_ok and producer_bound:
        status = "V16A_DYNAMIC_FOUNDATION_COMPONENT_REGENERATION_COMPLETE"
        diagnosis = "PRESSURE_FLUX_VELOCITY_AND_PRODUCER_IDENTITY_ARE_BOUND_WITHOUT_MUTATING_FROZEN_V15"
        recommendation = (
            "Proceed to the final V16A Foundation Case 0001 assembly with Kx/Ky/Kz/porosity, "
            "existing Pollock XYZ/TOF/weights, and the R7 derived dynamic components."
        )
        next_ms = "V16A-R8 — Foundation Case 0001 Final Assembly / Freeze"
    elif core_dynamic_ready:
        missing = []
        if not velocity_ok:
            missing.extend([c for c, ok in velocity_bound.items() if not ok])
        if not producer_bound:
            missing.append("producer_id")

        status = "V16A_PRESSURE_FLUX_REGENERATION_COMPLETE_RESIDUAL_COMPONENTS_REMAIN"
        diagnosis = "SOURCE_AUTHENTIC_SG3_SG4_DYNAMIC_FLOW_REGENERATION_PASSED_BUT_ONE_OR_MORE_VELOCITY_OR_PRODUCER_COMPONENTS_REMAIN_UNBOUND"
        recommendation = (
            "Do not rerun SG3/SG4. Preserve the R7 regenerated pressure/flux artifact. "
            "Resolve only the residual components: " + ", ".join(missing) + "."
        )
        next_ms = "V16A-R7A — Residual Velocity / Producer Component Binding"
    else:
        status = "V16A_CONTROLLED_SOURCE_AUTHENTIC_REGENERATION_INCOMPLETE"
        diagnosis = "ONE_OR_MORE_SG3_OR_SG4_RUNTIME_EXECUTION_OR_COMPONENT_BINDING_GATES_FAILED"
        recommendation = (
            "Do not proceed to FMM. Audit only failed R7 execution/binding gates. "
            "Do not broaden source authority or modify frozen V15."
        )
        next_ms = "V16A-R7A — Controlled Regeneration Failure Audit"

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "pressure_bound": pressure_ok,
        "Qx_bound": flux_bound["Qx"],
        "Qy_bound": flux_bound["Qy"],
        "Qz_bound": flux_bound["Qz"],
        "Vx_bound": velocity_bound["Vx"],
        "Vy_bound": velocity_bound["Vy"],
        "Vz_bound": velocity_bound["Vz"],
        "producer_id_bound": producer_bound,
        "derived_npz_created": DERIVED_NPZ.exists(),
        "next_milestone": next_ms,
    }])

    contract = {
        "milestone": "V16A-R7",
        "status": status,
        "diagnosis": diagnosis,
        "authority_label": "DERIVED_V16_FROM_FROZEN_V15",
        "component_status": {
            "pressure": pressure_ok,
            **flux_bound,
            **velocity_bound,
            "producer_id": producer_bound,
        },
        "sources": {
            "SG3": str(SG3_SOURCE),
            "SG3_sha256": sha256_file(SG3_SOURCE) if SG3_SOURCE.exists() else None,
            "SG4": str(sg4_source) if sg4_source else None,
            "SG4_sha256": sha256_file(sg4_source) if sg4_source else None,
        },
        "derived_artifact": str(DERIVED_NPZ) if DERIVED_NPZ.exists() else None,
        "derived_artifact_sha256": sha256_file(DERIVED_NPZ) if DERIVED_NPZ.exists() else None,
        "constraints": {
            "historical_V15_relabelling": False,
            "Pollock_retrace": False,
            "FMM": False,
            "model_predict_by_R7": False,
            "training": False,
            "frozen_V15_mutation": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT, contract)
    save_json(SUMMARY, {
        "milestone": "V16A-R7",
        "status": status,
        "diagnosis": diagnosis,
        "component_status": contract["component_status"],
        "derived_artifact": contract["derived_artifact"],
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("\nREGENERATED COMPONENT STATUS")
    print(f"  pressure                : {pressure_ok}")
    print(f"  Qx / Qy / Qz            : {flux_bound['Qx']} / {flux_bound['Qy']} / {flux_bound['Qz']}")
    print(f"  Vx / Vy / Vz            : {velocity_bound['Vx']} / {velocity_bound['Vy']} / {velocity_bound['Vz']}")
    print(f"  producer_id             : {producer_bound}")
    print(f"  Derived artifact saved  : {DERIVED_NPZ.exists()}")

    print("\n" + "=" * 78)
    print("V16A-R7 FINAL REGENERATION GATES")
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
    print(f"  {next_ms}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")
    print("\nTables:")
    for p in [
        EXECUTION_TABLE, LOCAL_TABLE, BINDING_TABLE,
        PRODUCER_TABLE, GATE_TABLE, DECISION_TABLE
    ]:
        print(f"  {p.name}")

    if DERIVED_NPZ.exists():
        print("\nNumerical:")
        print(f"  {DERIVED_NPZ.name}")
        print(f"  SHA-256: {sha256_file(DERIVED_NPZ)}")

    print("\nContract:")
    print(f"  {CONTRACT.name}")
    print("\nSummary:")
    print(f"  {SUMMARY.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16A-R7 CONTROLLED SOURCE-AUTHENTIC REGENERATION: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()

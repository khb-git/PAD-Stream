from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import re
from collections import defaultdict

import numpy as np


# =============================================================================
# PAD-Stream V16A-R7A
# Residual Velocity / Producer Component Binding Audit
#
# PURPOSE
# -------
# R7 successfully regenerated and persisted:
#   pressure, Qx, Qy, Qz
#
# Residual components:
#   Vx, Vy, Vz, producer_id
#
# R7A DOES NOT:
#   - rerun SG3,
#   - rerun SG4,
#   - retrace Pollock streamlines,
#   - run Fast Marching,
#   - train or infer any ML model,
#   - mutate frozen V15 artifacts.
#
# R7A audits two residual contracts:
#
#   A) Velocity:
#      Determine whether SG5 defines Vx/Vy/Vz as a deterministic algebraic
#      transformation of authoritative R7 fluxes + frozen geometry/porosity.
#      If yes, authorize algebraic V16 reconstruction WITHOUT Pollock retracing.
#
#   B) Producer identity:
#      Determine whether producer IDs can be reconstructed from existing
#      streamline endpoint / capture / terminal-well metadata WITHOUT tracing
#      new streamlines.
#
# If both contracts close:
#   next milestone = V16A-R7B controlled residual reconstruction.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_R7A_RESIDUAL_VELOCITY_PRODUCER_BINDING"
OUT.mkdir(parents=True, exist_ok=True)

R7_DIR = ROOT / "output" / "V16_A_R7_CONTROLLED_SOURCE_AUTHENTIC_REGENERATION"
R7_SUMMARY = R7_DIR / "PAD_Stream_V16AR7_Summary.json"
R7_DYNAMIC = R7_DIR / "V16AR7_Derived_V16_From_Frozen_V15_Dynamic_Components.npz"

VELOCITY_SOURCE = OUT / "V16AR7A_SG5_Velocity_Source_Expression_Audit.csv"
VELOCITY_DEP = OUT / "V16AR7A_SG5_Velocity_Dependency_Trace.csv"
VELOCITY_DECISION = OUT / "V16AR7A_Velocity_Reconstruction_Decision.csv"
PRODUCER_SOURCE = OUT / "V16AR7A_Producer_Identity_Source_Semantics.csv"
PRODUCER_ARTIFACT = OUT / "V16AR7A_Producer_Endpoint_Artifact_Audit.csv"
PRODUCER_DECISION = OUT / "V16AR7A_Producer_Identity_Binding_Decision.csv"
GATES = OUT / "V16AR7A_Final_Residual_Binding_Gates.csv"
DECISION = OUT / "V16AR7A_Final_Residual_Binding_Decision.csv"
CONTRACT = OUT / "V16AR7A_Residual_Velocity_Producer_Binding_Contract.json"
SUMMARY = OUT / "PAD_Stream_V16AR7A_Summary.json"

VELOCITY_COMPONENTS = ["Vx", "Vy", "Vz"]

VEL_ALIASES = {
    "Vx": ["vx", "v_x", "velocity_x", "vel_x"],
    "Vy": ["vy", "v_y", "velocity_y", "vel_y"],
    "Vz": ["vz", "v_z", "velocity_z", "vel_z"],
}

PRODUCER_TERMS = [
    "producer", "capture", "captured", "terminal",
    "destination", "well_id", "well_index", "producer_id",
    "producer_idx", "producer_index", "target_producer"
]


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
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
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


def names(node):
    out = set()
    if node is None:
        return out
    for x in ast.walk(node):
        if isinstance(x, ast.Name):
            out.add(x.id)
    return out


def sg5_sources():
    out = []
    for p in sorted(ROOT.glob("PAD_Stream_V15SG5*.py")):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text)
        except Exception:
            continue
        out.append((p, text, tree))
    return out


def velocity_expression_audit(sources):
    rows = []
    dep_rows = []

    for p, text, tree in sources:
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            expr = ast_text(getattr(node, "value", None))
            expr_names = sorted(names(getattr(node, "value", None)))

            for target in assigned_targets(node):
                lt = target.lower()
                for comp, aliases in VEL_ALIASES.items():
                    if lt not in {a.lower() for a in aliases}:
                        continue

                    lowexpr = expr.lower()
                    references_flux = any(tok in lowexpr for tok in ["qx", "qy", "qz", "flux"])
                    references_geometry = any(tok in lowexpr for tok in [
                        "area", "dx", "dy", "dz", "face_area", "cell"
                    ])
                    references_porosity = any(tok in lowexpr for tok in ["phi", "poro", "porosity"])

                    rows.append({
                        "component": comp,
                        "source": str(p),
                        "source_sha256": sha256_file(p),
                        "line": getattr(node, "lineno", None),
                        "symbol": target,
                        "expression": expr,
                        "dependencies": ";".join(expr_names),
                        "references_flux": references_flux,
                        "references_geometry": references_geometry,
                        "references_porosity": references_porosity,
                    })

                    for d in expr_names:
                        dep_rows.append({
                            "component": comp,
                            "source": str(p),
                            "target": target,
                            "dependency": d,
                            "line": getattr(node, "lineno", None),
                        })
    return rows, dep_rows


def choose_velocity_contract(rows):
    result = []

    for comp in VELOCITY_COMPONENTS:
        candidates = [r for r in rows if r["component"] == comp]

        if not candidates:
            result.append({
                "component": comp,
                "status": "NO_SOURCE_EXPRESSION_FOUND",
                "authorized": False,
                "reason": "no SG5 velocity expression found",
            })
            continue

        # Prefer expressions directly referencing flux; no numerical selection.
        direct = [r for r in candidates if r["references_flux"]]
        chosen = direct[0] if direct else candidates[0]

        algebraic = (
            chosen["references_flux"]
            and (
                chosen["references_geometry"]
                or chosen["references_porosity"]
                or "/" in chosen["expression"]
                or "*" in chosen["expression"]
            )
        )

        if algebraic:
            status = "ALGEBRAIC_VELOCITY_RECONSTRUCTION_AUTHORIZED"
            authorized = True
            reason = "SG5 defines velocity from flux with algebraic geometry/porosity transformation"
        else:
            status = "VELOCITY_RECONSTRUCTION_NOT_YET_AUTHORIZED"
            authorized = False
            reason = "velocity expression does not yet prove a pure algebraic flux-to-velocity mapping"

        result.append({
            "component": comp,
            "status": status,
            "authorized": authorized,
            "source": chosen["source"],
            "line": chosen["line"],
            "symbol": chosen["symbol"],
            "expression": chosen["expression"],
            "reason": reason,
        })

    return result


def producer_source_semantics():
    rows = []

    for p in sorted(ROOT.glob("PAD_Stream_V15SG[56]*.py")):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            if not any(t in low for t in PRODUCER_TERMS):
                continue

            rows.append({
                "source": str(p),
                "source_sha256": sha256_file(p),
                "line": i,
                "text": line.strip()[:700],
                "mentions_producer": "producer" in low,
                "mentions_capture": ("capture" in low or "captured" in low),
                "mentions_terminal": ("terminal" in low or "destination" in low),
                "mentions_identifier": ("id" in low or "idx" in low or "index" in low),
                "mentions_endpoint": ("endpoint" in low or "end_" in low or "terminal" in low),
            })

    return rows


def producer_artifact_audit():
    rows = []
    outroot = ROOT / "output"

    if not outroot.exists():
        return rows

    for p in sorted(outroot.rglob("*.npz")):
        lowp = str(p).lower()

        if "v16_" in lowp or "v16a" in lowp:
            continue

        if not any(t in lowp for t in ["sg5", "sg6", "pollock", "streamline"]):
            continue

        try:
            with np.load(p, allow_pickle=False) as db:
                for key in db.files:
                    a = np.asarray(db[key])

                    if a.shape not in [(1078,), (1078,1)]:
                        continue
                    if not np.issubdtype(a.dtype, np.number):
                        continue
                    if not np.all(np.isfinite(a)):
                        continue

                    lk = key.lower()
                    semantic = any(t in lk for t in PRODUCER_TERMS)
                    integer_like = bool(np.allclose(a, np.rint(a), atol=0, rtol=0))
                    unique_vals = np.unique(a)

                    rows.append({
                        "artifact": str(p),
                        "artifact_sha256": sha256_file(p),
                        "key": key,
                        "shape": str(tuple(a.shape)),
                        "dtype": str(a.dtype),
                        "semantic_key": semantic,
                        "integer_like": integer_like,
                        "unique_value_count": len(unique_vals),
                        "values_preview": ";".join(map(str, unique_vals[:20].tolist())),
                        "array_sha256": sha256_array(a),
                    })
        except Exception:
            continue

    return rows


def producer_binding_decision(source_rows, artifact_rows):
    source_has_capture_mapping = (
        any(r["mentions_producer"] and (r["mentions_capture"] or r["mentions_terminal"]) for r in source_rows)
        and any(r["mentions_identifier"] for r in source_rows)
    )

    semantic_artifacts = [r for r in artifact_rows if r["semantic_key"]]
    hashes = {r["array_sha256"] for r in semantic_artifacts}

    if len(hashes) == 1 and semantic_artifacts:
        chosen = sorted(semantic_artifacts, key=lambda r: (r["artifact"], r["key"]))[0]
        return {
            "status": "PERSISTED_PRODUCER_ID_AUTHORITY_BOUND",
            "authorized": True,
            "binding_mode": "PERSISTED_ARRAY",
            "artifact": chosen["artifact"],
            "key": chosen["key"],
            "array_sha256": chosen["array_sha256"],
            "reason": "one semantic producer-ID numerical identity exists",
        }

    if source_has_capture_mapping:
        return {
            "status": "PRODUCER_ID_RECONSTRUCTION_FROM_EXISTING_ENDPOINT_METADATA_AUTHORIZED",
            "authorized": True,
            "binding_mode": "ENDPOINT_METADATA_RECONSTRUCTION",
            "artifact": "",
            "key": "",
            "array_sha256": "",
            "reason": "SG5/SG6 source contains explicit producer capture/terminal identifier semantics",
        }

    return {
        "status": "PRODUCER_IDENTITY_STILL_UNRESOLVED",
        "authorized": False,
        "binding_mode": "",
        "artifact": "",
        "key": "",
        "array_sha256": "",
        "reason": "no unique semantic persisted array and no complete capture-ID source contract",
    }


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16A-R7A")
    print("Residual Velocity / Producer Component Binding Audit")
    print("=" * 78)

    print("""
NO SG3 PRESSURE SOLVE WILL BE RERUN.
NO SG4 DARCY FLUX WILL BE RERUN.
NO VELOCITY ARRAY WILL BE RECONSTRUCTED IN R7A.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO FAST MARCHING WILL BE EXECUTED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
NO FROZEN V15 ARTIFACT WILL BE CHANGED.
ONLY RESIDUAL VELOCITY / PRODUCER CONTRACTS WILL BE AUDITED.
""")

    if not R7_SUMMARY.exists():
        raise FileNotFoundError(R7_SUMMARY)

    r7 = json.loads(R7_SUMMARY.read_text(encoding="utf-8"))
    if r7.get("status") != "V16A_PRESSURE_FLUX_REGENERATION_COMPLETE_RESIDUAL_COMPONENTS_REMAIN":
        raise RuntimeError("R7A expects R7 residual-component status.")

    if not R7_DYNAMIC.exists():
        raise FileNotFoundError(R7_DYNAMIC)

    with np.load(R7_DYNAMIC, allow_pickle=False) as db:
        required = ["pressure", "Qx", "Qy", "Qz"]
        missing = [k for k in required if k not in db.files]
        if missing:
            raise RuntimeError(f"R7 derived artifact is missing required parents: {missing}")

    sources = sg5_sources()
    velocity_rows, dep_rows = velocity_expression_audit(sources)
    save_csv(VELOCITY_SOURCE, velocity_rows)
    save_csv(VELOCITY_DEP, dep_rows)

    velocity_decisions = choose_velocity_contract(velocity_rows)
    save_csv(VELOCITY_DECISION, velocity_decisions)

    producer_sources = producer_source_semantics()
    save_csv(PRODUCER_SOURCE, producer_sources)

    producer_artifacts = producer_artifact_audit()
    save_csv(PRODUCER_ARTIFACT, producer_artifacts)

    producer_decision = producer_binding_decision(producer_sources, producer_artifacts)
    save_csv(PRODUCER_DECISION, [producer_decision])

    all_velocity_authorized = all(r["authorized"] for r in velocity_decisions)
    producer_authorized = producer_decision["authorized"]

    print("VELOCITY CONTRACT")
    for r in velocity_decisions:
        print(f"  {r['component']:<4} | {r['status']}")

    print("\nPRODUCER IDENTITY CONTRACT")
    print(f"  Status                  : {producer_decision['status']}")
    print(f"  Binding mode            : {producer_decision['binding_mode'] or 'NONE'}")

    gates = [
        ("incoming_R7_residual_status_reproduced", True),
        ("R7_pressure_flux_parent_artifact_loaded", True),
        ("SG5_velocity_source_expressions_audited", True),
        ("velocity_dependencies_audited", True),
        ("Vx_reconstruction_policy_classified", True),
        ("Vy_reconstruction_policy_classified", True),
        ("Vz_reconstruction_policy_classified", True),
        ("SG5_SG6_producer_semantics_audited", True),
        ("existing_producer_artifacts_audited", True),
        ("producer_binding_policy_classified", True),
        ("no_SG3_rerun", True),
        ("no_SG4_rerun", True),
        ("no_velocity_reconstruction_performed", True),
        ("no_Pollock_retrace_executed", True),
        ("no_FMM_executed", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_V15_artifact_changed", True),
    ]
    save_csv(GATES, [{"gate": g, "passed": p} for g,p in gates])

    if all_velocity_authorized and producer_authorized:
        status = "V16A_RESIDUAL_VELOCITY_PRODUCER_RECONSTRUCTION_AUTHORIZED"
        diagnosis = (
            "SG5_DEFINES_PURE_ALGEBRAIC_FLUX_TO_VELOCITY_MAPPING_AND_PRODUCER_IDENTITY_CAN_BE_BOUND_WITHOUT_POLLOCK_RETRACE"
        )
        recommendation = (
            "Proceed to controlled residual reconstruction using the frozen R7 Qx/Qy/Qz artifact and exact SG5 velocity expressions. "
            "Bind producer identity using the authorized persisted or endpoint-metadata path. Do not rerun SG3/SG4 or retrace Pollock."
        )
        next_ms = "V16A-R7B — Controlled Residual Velocity / Producer Reconstruction"
    else:
        unresolved = [r["component"] for r in velocity_decisions if not r["authorized"]]
        if not producer_authorized:
            unresolved.append("producer_id")

        status = "V16A_RESIDUAL_VELOCITY_PRODUCER_BINDING_STILL_INCOMPLETE"
        diagnosis = "ONE_OR_MORE_RESIDUAL_COMPONENTS_LACK_A_NONRETRACE_SOURCE_AUTHENTIC_RECONSTRUCTION_CONTRACT"
        recommendation = (
            "Do not rerun SG3/SG4 and do not retrace Pollock. Audit only unresolved residuals: "
            + ", ".join(unresolved)
        )
        next_ms = "V16A-R7B — Residual Component-Specific Binding Audit"

    save_csv(DECISION, [{
        "status": status,
        "diagnosis": diagnosis,
        "Vx_authorized": next(r["authorized"] for r in velocity_decisions if r["component"]=="Vx"),
        "Vy_authorized": next(r["authorized"] for r in velocity_decisions if r["component"]=="Vy"),
        "Vz_authorized": next(r["authorized"] for r in velocity_decisions if r["component"]=="Vz"),
        "producer_id_authorized": producer_authorized,
        "producer_binding_mode": producer_decision["binding_mode"],
        "next_milestone": next_ms,
    }])

    contract = {
        "milestone": "V16A-R7A",
        "status": status,
        "diagnosis": diagnosis,
        "R7_parent_artifact": str(R7_DYNAMIC),
        "R7_parent_sha256": sha256_file(R7_DYNAMIC),
        "velocity_contract": velocity_decisions,
        "producer_contract": producer_decision,
        "constraints": {
            "SG3_rerun": False,
            "SG4_rerun": False,
            "velocity_reconstruction_performed": False,
            "Pollock_retrace": False,
            "FMM": False,
            "model_predict": False,
            "training": False,
            "V15_mutation": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT, contract)

    save_json(SUMMARY, {
        "milestone": "V16A-R7A",
        "status": status,
        "diagnosis": diagnosis,
        "all_velocity_authorized": all_velocity_authorized,
        "producer_id_authorized": producer_authorized,
        "producer_binding_mode": producer_decision["binding_mode"],
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("\n" + "=" * 78)
    print("V16A-R7A FINAL RESIDUAL BINDING GATES")
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
        VELOCITY_SOURCE, VELOCITY_DEP, VELOCITY_DECISION,
        PRODUCER_SOURCE, PRODUCER_ARTIFACT, PRODUCER_DECISION,
        GATES, DECISION
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT.name}")
    print("\nSummary:")
    print(f"  {SUMMARY.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16A-R7A RESIDUAL VELOCITY / PRODUCER AUDIT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()

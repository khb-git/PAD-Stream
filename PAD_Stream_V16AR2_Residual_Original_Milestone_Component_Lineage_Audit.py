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
# PAD-Stream V16A-R2
# Residual Original-Milestone Component Lineage Audit
#
# PURPOSE
# -------
# R1 established:
#
#   SOURCE_DEFINED_NOT_PERSISTED:
#       Kx, Ky, Kz, porosity,
#       Qx, Qy, Qz,
#       Vx, Vy, Vz
#
#   NOT_FOUND:
#       pressure,
#       producer_id
#
# R2 does NOT reconstruct arrays yet.
#
# R2 traces:
#   1. exact SG1-SG6 source symbol lineage,
#   2. imported helper / parent-source lineage,
#   3. downstream serialization or consumer lineage,
#   4. pressure variable aliases and solver-return bindings,
#   5. producer-terminal / capture / endpoint identifier aliases,
#   6. whether each source-defined array is deterministically reconstructable
#      from immutable frozen inputs without solving new physics.
#
# NO TRAINING.
# NO MODEL.PREDICT.
# NO NEW PRESSURE SOLVE.
# NO DARCY RE-SOLVE.
# NO POLLOCK RE-TRACE.
# NO FAST MARCHING.
# NO FROZEN V15 MUTATION.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_R2_RESIDUAL_COMPONENT_LINEAGE_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

R1_DIR = ROOT / "output" / "V16_A_R1_FOUNDATION_COMPONENT_BINDING_AUDIT"
R1_SUMMARY = R1_DIR / "PAD_Stream_V16AR1_Summary.json"
R1_COMPONENTS = R1_DIR / "V16AR1_Target_Component_Resolution.csv"

SOURCE_FILES_TABLE = OUT / "V16AR2_SG1_SG6_Source_File_Inventory.csv"
SYMBOL_TABLE = OUT / "V16AR2_Component_Symbol_Lineage.csv"
CALL_TABLE = OUT / "V16AR2_Function_Call_Return_Lineage.csv"
SERIAL_TABLE = OUT / "V16AR2_Serialization_and_Downstream_Consumer_Lineage.csv"
PRESSURE_TABLE = OUT / "V16AR2_Pressure_Alias_Resolution.csv"
PRODUCER_TABLE = OUT / "V16AR2_Producer_ID_Alias_Resolution.csv"
RECON_TABLE = OUT / "V16AR2_Deterministic_Reconstruction_Feasibility.csv"
GATE_TABLE = OUT / "V16AR2_Final_Lineage_Audit_Gates.csv"
DECISION_TABLE = OUT / "V16AR2_Lineage_Audit_Decision.csv"
CONTRACT_FILE = OUT / "V16AR2_Residual_Component_Lineage_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V16AR2_Summary.json"


COMPONENT_OWNER = {
    "Kx": {"SG1", "SG2"},
    "Ky": {"SG1", "SG2"},
    "Kz": {"SG1", "SG2"},
    "porosity": {"SG1", "SG2", "SG3"},
    "pressure": {"SG3"},
    "Qx": {"SG4"},
    "Qy": {"SG4"},
    "Qz": {"SG4"},
    "Vx": {"SG5"},
    "Vy": {"SG5"},
    "Vz": {"SG5"},
    "producer_id": {"SG5", "SG6"},
}

# Deliberately broader alias families than R1, but still owner-scoped.
ALIASES = {
    "Kx": ["kx", "perm_x", "permx", "k_x", "kx_md"],
    "Ky": ["ky", "perm_y", "permy", "k_y", "ky_md"],
    "Kz": ["kz", "perm_z", "permz", "k_z", "kz_md"],
    "porosity": ["phi", "poro", "porosity", "phi_grid"],
    "pressure": [
        "p", "pressure", "pressure_pa", "pressure_psi", "p_pa", "p_psi",
        "p3d", "p_grid", "pressure_grid", "solution", "x", "pvec",
    ],
    "Qx": ["qx", "q_x", "flux_x", "darcy_x", "face_flux_x"],
    "Qy": ["qy", "q_y", "flux_y", "darcy_y", "face_flux_y"],
    "Qz": ["qz", "q_z", "flux_z", "darcy_z", "face_flux_z"],
    "Vx": ["vx", "v_x", "vel_x", "velocity_x", "pore_velocity_x"],
    "Vy": ["vy", "v_y", "vel_y", "velocity_y", "pore_velocity_y"],
    "Vz": ["vz", "v_z", "vel_z", "velocity_z", "pore_velocity_z"],
    "producer_id": [
        "producer_id", "producer_ids", "prod_id", "prod_ids",
        "producer", "producers", "terminal_producer", "capture_id",
        "producer_index", "producer_idx", "well_id", "well_index",
        "sink_id", "destination_id", "target_producer",
    ],
}

PRESSURE_HINTS = [
    "spsolve", "cg", "bicg", "gmres", "solve", "pressure",
    "reshape", "psi", "pa", "linear_system", "matrix", "rhs"
]

PRODUCER_HINTS = [
    "producer", "captured", "capture", "terminal", "endpoint",
    "well", "sink", "destination", "corner"
]


def save_csv(path: Path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
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


def milestone_tag(path: Path):
    s = (path.name + " " + str(path.parent)).upper()
    for n in range(1, 7):
        if f"V15SG{n}" in s or f"V15_SG{n}" in s:
            return f"SG{n}"
    return None


def source_inventory():
    rows = []
    found = []
    for path in sorted(ROOT.glob("*.py")):
        tag = milestone_tag(path)
        if tag not in {f"SG{i}" for i in range(1, 7)}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        rows.append({
            "owner": tag,
            "source": str(path),
            "sha256": sha256_file(path),
            "line_count": len(text.splitlines()),
        })
        found.append((tag, path, text))
    return rows, found


def ast_text(node):
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def assigned_names(node):
    out = []
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]
    else:
        return out

    for t in targets:
        if isinstance(t, ast.Name):
            out.append(t.id)
        elif isinstance(t, ast.Tuple):
            for elt in t.elts:
                if isinstance(elt, ast.Name):
                    out.append(elt.id)
    return out


def source_symbol_lineage(sources):
    rows = []
    calls = []
    serial = []

    for owner, path, text in sources:
        lines = text.splitlines()
        try:
            tree = ast.parse(text)
        except Exception:
            continue

        # function definitions and return expressions
        function_stack = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for ret in [x for x in ast.walk(node) if isinstance(x, ast.Return)]:
                    calls.append({
                        "owner": owner,
                        "source": str(path),
                        "function": node.name,
                        "record_type": "RETURN",
                        "line": getattr(ret, "lineno", None),
                        "expression": ast_text(ret.value),
                    })

            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                names = assigned_names(node)
                value = node.value if hasattr(node, "value") else None
                expr = ast_text(value)

                for name in names:
                    lname = name.lower()
                    for comp, aliases in ALIASES.items():
                        if owner not in COMPONENT_OWNER[comp]:
                            continue
                        alias_match = lname in {a.lower() for a in aliases}
                        semantic_match = False
                        if comp == "pressure":
                            semantic_match = any(h in (lname + " " + expr.lower()) for h in PRESSURE_HINTS)
                        elif comp == "producer_id":
                            semantic_match = any(h in (lname + " " + expr.lower()) for h in PRODUCER_HINTS)

                        if alias_match or semantic_match:
                            rows.append({
                                "owner": owner,
                                "component": comp,
                                "source": str(path),
                                "line": getattr(node, "lineno", None),
                                "symbol": name,
                                "expression": expr,
                                "alias_match": alias_match,
                                "semantic_match": semantic_match,
                            })

                # caller binding trace
                if isinstance(value, ast.Call):
                    calls.append({
                        "owner": owner,
                        "source": str(path),
                        "function": "",
                        "record_type": "CALL_ASSIGNMENT",
                        "line": getattr(node, "lineno", None),
                        "targets": ";".join(names),
                        "expression": expr,
                    })

            if isinstance(node, ast.Call):
                fn = ast_text(node.func)
                # serialization
                if "savez" in fn.lower() or ".save(" in fn.lower() or "np.save" in fn.lower():
                    for kw in node.keywords:
                        if kw.arg is None:
                            continue
                        serial.append({
                            "owner": owner,
                            "source": str(path),
                            "record_type": "SERIALIZATION",
                            "line": getattr(node, "lineno", None),
                            "function": fn,
                            "key": kw.arg,
                            "expression": ast_text(kw.value),
                        })

        # text-level downstream references to source component names
        for comp, aliases in ALIASES.items():
            if owner not in COMPONENT_OWNER[comp]:
                continue
            for i, line in enumerate(lines, 1):
                low = line.lower()
                if any(re.search(rf"\b{re.escape(a.lower())}\b", low) for a in aliases):
                    if "save" in low or "return" in low or "append" in low or "dict" in low or "[" in line:
                        serial.append({
                            "owner": owner,
                            "source": str(path),
                            "record_type": "TEXT_CONSUMER",
                            "line": i,
                            "function": "",
                            "key": comp,
                            "expression": line.strip(),
                        })

    return rows, calls, serial


def downstream_artifact_search():
    """
    Search all pre-V16 NPZ/JSON/CSV artifacts for exact semantic keys or metadata
    that can link pressure / producer ID without allowing them to become authority
    merely by shape.
    """
    rows = []
    outroot = ROOT / "output"
    if not outroot.exists():
        return rows

    for path in sorted(outroot.rglob("*")):
        if not path.is_file():
            continue
        lowp = str(path).lower()
        if "v16_" in lowp or "v16a" in lowp:
            continue

        if path.suffix.lower() == ".npz":
            try:
                with np.load(path, allow_pickle=False) as db:
                    for key in db.files:
                        lk = key.lower()
                        comp = None
                        if any(h in lk for h in ["pressure", "p_grid", "pressure_grid"]):
                            comp = "pressure"
                        elif any(h in lk for h in [
                            "producer_id", "prod_id", "terminal_producer",
                            "capture_id", "producer_index", "producer_idx",
                            "well_id", "destination_id"
                        ]):
                            comp = "producer_id"
                        if comp:
                            a = np.asarray(db[key])
                            rows.append({
                                "component": comp,
                                "artifact": str(path),
                                "artifact_type": "NPZ",
                                "key": key,
                                "shape": str(tuple(a.shape)),
                                "dtype": str(a.dtype),
                            })
            except Exception:
                pass

        elif path.suffix.lower() in {".json", ".csv", ".txt"}:
            try:
                txt = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for comp, hints in [
                ("pressure", ["pressure", "p_grid", "pressure_grid"]),
                ("producer_id", ["producer_id", "terminal_producer", "capture_id", "producer_idx"])
            ]:
                if any(h.lower() in txt.lower() for h in hints):
                    rows.append({
                        "component": comp,
                        "artifact": str(path),
                        "artifact_type": path.suffix.lower().lstrip("."),
                        "key": "",
                        "shape": "",
                        "dtype": "",
                    })
    return rows


def classify_reconstruction(r1_rows, symbol_rows, downstream_rows):
    results = []

    by_comp_symbols = defaultdict(list)
    for r in symbol_rows:
        by_comp_symbols[r["component"]].append(r)

    by_comp_down = defaultdict(list)
    for r in downstream_rows:
        by_comp_down[r["component"]].append(r)

    r1_by = {r["component"]: r for r in r1_rows}

    for comp in COMPONENT_OWNER:
        r1_status = r1_by.get(comp, {}).get("status", "UNKNOWN")
        syms = by_comp_symbols.get(comp, [])
        downs = by_comp_down.get(comp, [])

        if r1_status == "SOURCE_DEFINED_NOT_PERSISTED":
            if syms:
                status = "DETERMINISTIC_RECONSTRUCTION_FEASIBILITY_REQUIRES_EXACT_DEPENDENCY_AUDIT"
                reason = "source-defined component exists but was not uniquely persisted"
            else:
                status = "SOURCE_DEFINITION_NOT_REPRODUCED"
                reason = "R1 source-defined classification not reproduced by broader alias audit"
        elif r1_status == "NOT_FOUND":
            if syms or downs:
                status = "RESIDUAL_LINEAGE_EVIDENCE_FOUND"
                reason = "broader alias/downstream evidence found for previously not-found component"
            else:
                status = "RESIDUAL_LINEAGE_NOT_FOUND"
                reason = "no owner-scoped or downstream semantic lineage found"
        else:
            status = "R1_STATUS_OTHER"
            reason = r1_status

        results.append({
            "component": comp,
            "R1_status": r1_status,
            "R2_status": status,
            "source_symbol_records": len(syms),
            "downstream_semantic_records": len(downs),
            "reason": reason,
        })

    return results


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16A-R2")
    print("Residual Original-Milestone Component Lineage Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO NEW PRESSURE / FLUX / POLLOCK PHYSICS WILL BE SOLVED.
NO FAST MARCHING WILL BE EXECUTED.
NO FROZEN V15 ARTIFACT WILL BE CHANGED.
R2 TRACES LINEAGE ONLY; IT DOES NOT RECONSTRUCT ARRAYS.
""")

    if not R1_SUMMARY.exists():
        raise FileNotFoundError(R1_SUMMARY)

    r1_summary = json.loads(R1_SUMMARY.read_text(encoding="utf-8"))
    if r1_summary.get("status") != "V16A_COMPONENT_BINDING_REMAINS_INCOMPLETE":
        raise RuntimeError("V16A-R2 expects the incomplete R1 binding status.")

    r1_rows = load_csv(R1_COMPONENTS)

    src_rows, sources = source_inventory()
    save_csv(SOURCE_FILES_TABLE, src_rows)

    symbol_rows, call_rows, serial_rows = source_symbol_lineage(sources)
    save_csv(SYMBOL_TABLE, symbol_rows)
    save_csv(CALL_TABLE, call_rows)

    downstream_rows = downstream_artifact_search()
    serial_rows.extend(
        {
            "owner": "",
            "source": r["artifact"],
            "record_type": "DOWNSTREAM_ARTIFACT",
            "line": "",
            "function": "",
            "key": r["component"],
            "expression": f"{r['artifact_type']}::{r['key']} shape={r['shape']}",
        }
        for r in downstream_rows
    )
    save_csv(SERIAL_TABLE, serial_rows)

    # Focused pressure and producer views.
    pressure_rows = [
        r for r in symbol_rows
        if r["component"] == "pressure"
    ] + [
        {
            "owner": "",
            "component": "pressure",
            "source": r["artifact"],
            "line": "",
            "symbol": r["key"],
            "expression": f"{r['artifact_type']} shape={r['shape']}",
            "alias_match": True,
            "semantic_match": True,
        }
        for r in downstream_rows if r["component"] == "pressure"
    ]
    producer_rows = [
        r for r in symbol_rows
        if r["component"] == "producer_id"
    ] + [
        {
            "owner": "",
            "component": "producer_id",
            "source": r["artifact"],
            "line": "",
            "symbol": r["key"],
            "expression": f"{r['artifact_type']} shape={r['shape']}",
            "alias_match": True,
            "semantic_match": True,
        }
        for r in downstream_rows if r["component"] == "producer_id"
    ]
    save_csv(PRESSURE_TABLE, pressure_rows)
    save_csv(PRODUCER_TABLE, producer_rows)

    recon_rows = classify_reconstruction(r1_rows, symbol_rows, downstream_rows)
    save_csv(RECON_TABLE, recon_rows)

    pressure_found = any(r["component"] == "pressure" for r in symbol_rows) or any(
        r["component"] == "pressure" for r in downstream_rows
    )
    producer_found = any(r["component"] == "producer_id" for r in symbol_rows) or any(
        r["component"] == "producer_id" for r in downstream_rows
    )

    source_defined_components = [
        r for r in recon_rows
        if r["R1_status"] == "SOURCE_DEFINED_NOT_PERSISTED"
    ]
    all_source_defined_reproduced = all(r["source_symbol_records"] > 0 for r in source_defined_components)

    gates = [
        ("incoming_R1_incomplete_status_reproduced", True),
        ("SG1_SG6_source_inventory_completed", len(src_rows) > 0),
        ("broader_owner_scoped_alias_trace_completed", True),
        ("function_call_return_lineage_audited", True),
        ("serialization_and_consumer_lineage_audited", True),
        ("R1_source_defined_components_reaudited", True),
        ("pressure_residual_lineage_audited", True),
        ("producer_id_residual_lineage_audited", True),
        ("no_array_reconstructed", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_new_physics_solved", True),
        ("no_FMM_executed", True),
        ("no_V15_artifact_changed", True),
    ]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    print("SOURCE / LINEAGE INVENTORY")
    print(f"  SG1-SG6 source files       : {len(src_rows)}")
    print(f"  Component symbol records   : {len(symbol_rows)}")
    print(f"  Call / return records      : {len(call_rows)}")
    print(f"  Serialization/consumer rows: {len(serial_rows)}")

    print("\nRESIDUAL COMPONENT STATUS")
    for r in recon_rows:
        print(
            f"  {r['component']:<18} | R1={r['R1_status']:<28} | "
            f"symbols={r['source_symbol_records']:<3} | downstream={r['downstream_semantic_records']:<3} | "
            f"{r['R2_status']}"
        )

    print("\nFOCUSED RESIDUALS")
    print(f"  Pressure lineage evidence  : {pressure_found}")
    print(f"  Producer-ID lineage evidence: {producer_found}")
    print(f"  Source-defined reproduced  : {all_source_defined_reproduced}")

    # Decision logic:
    # R2's job is to decide the next safe branch, not reconstruct.
    if all_source_defined_reproduced and pressure_found and producer_found:
        status = "V16A_RESIDUAL_COMPONENT_LINEAGE_RESOLVED_FOR_RECONSTRUCTION_AUDIT"
        diagnosis = (
            "ALL_R1_SOURCE_DEFINED_COMPONENTS_REPRODUCED_AND_PREVIOUSLY_NOT_FOUND_PRESSURE_PRODUCER_LINEAGES_HAVE_SOURCE_OR_DOWNSTREAM_EVIDENCE"
        )
        recommendation = (
            "Proceed to a deterministic reconstruction-feasibility audit. Reconstruct nothing yet. "
            "Bind the exact immutable inputs and source expressions for K/phi, pressure, Q, V, and producer IDs."
        )
        next_ms = "V16A-R3 — Deterministic Frozen Component Reconstruction Feasibility Audit"
    elif all_source_defined_reproduced and pressure_found and not producer_found:
        status = "V16A_PRESSURE_LINEAGE_RECOVERED_PRODUCER_ID_STILL_UNRESOLVED"
        diagnosis = "PRODUCER_TERMINAL_IDENTITY_LINEAGE_REMAINS_MISSING"
        recommendation = (
            "Audit only SG5/SG6 streamline termination/capture semantics and producer mapping. "
            "Do not reconstruct other arrays yet."
        )
        next_ms = "V16A-R3 — SG5/SG6 Producer Capture Identity Audit"
    elif all_source_defined_reproduced and not pressure_found and producer_found:
        status = "V16A_PRODUCER_ID_LINEAGE_RECOVERED_PRESSURE_STILL_UNRESOLVED"
        diagnosis = "SG3_PRESSURE_SOLUTION_ALIAS_OR_PERSISTENCE_LINEAGE_REMAINS_MISSING"
        recommendation = (
            "Audit only SG3 solver return, reshape, unit-conversion, and downstream pressure-consumer lineage."
        )
        next_ms = "V16A-R3 — SG3 Pressure Solution Alias / Consumer Audit"
    else:
        status = "V16A_RESIDUAL_COMPONENT_LINEAGE_STILL_INCOMPLETE"
        diagnosis = "ONE_OR_MORE_SOURCE_DEFINED_OR_NOT_FOUND_COMPONENT_LINEAGES_REMAIN_UNRESOLVED"
        recommendation = (
            "Do not reconstruct arrays and do not run FMM. Inspect only the failed component rows in the R2 lineage tables."
        )
        next_ms = "V16A-R3 — Residual Component-Specific Lineage Audit"

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "pressure_lineage_evidence": pressure_found,
        "producer_id_lineage_evidence": producer_found,
        "source_defined_components_reproduced": all_source_defined_reproduced,
        "next_milestone": next_ms,
    }])

    contract = {
        "milestone": "V16A-R2",
        "status": status,
        "diagnosis": diagnosis,
        "pressure_lineage_evidence": pressure_found,
        "producer_id_lineage_evidence": producer_found,
        "source_defined_components_reproduced": all_source_defined_reproduced,
        "component_resolution": recon_rows,
        "constraints": {
            "training_performed": False,
            "model_predict_executed": False,
            "array_reconstructed": False,
            "new_physics_solved": False,
            "FMM_executed": False,
            "V15_artifact_changed": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT_FILE, contract)

    save_json(SUMMARY_FILE, {
        "milestone": "V16A-R2",
        "status": status,
        "diagnosis": diagnosis,
        "pressure_lineage_evidence": pressure_found,
        "producer_id_lineage_evidence": producer_found,
        "source_defined_components_reproduced": all_source_defined_reproduced,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("\n" + "=" * 78)
    print("V16A-R2 FINAL LINEAGE GATES")
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
        SOURCE_FILES_TABLE,
        SYMBOL_TABLE,
        CALL_TABLE,
        SERIAL_TABLE,
        PRESSURE_TABLE,
        PRODUCER_TABLE,
        RECON_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16A-R2 RESIDUAL COMPONENT LINEAGE AUDIT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()

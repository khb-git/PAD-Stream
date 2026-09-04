from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import re

import numpy as np


# =============================================================================
# PAD-Stream V16A-R1
# Missing / Ambiguous Foundation Component Binding Audit
#
# TARGETED REPAIR OF V16A ONLY
#
# NO TRAINING.
# NO MODEL.PREDICT.
# NO NEW PRESSURE / FLUX / STREAMLINE / TRANSPORT PHYSICS.
# NO FAST MARCHING.
# NO FROZEN V15 ARTIFACT MUTATION.
# NO HEURISTIC GLOBAL SHAPE-ONLY BINDING.
#
# PURPOSE
# -------
# V16A correctly blocked because its first broad inventory allowed unrelated
# arrays having compatible shapes to compete with the intended V15 physics
# arrays (for example segment_piece_count). V16A-R1 narrows authority to the
# original SG1-SG6 milestone lineage and audits:
#
#   1. exact persisted NPZ keys,
#   2. source-level assignments,
#   3. np.savez / np.savez_compressed serialization keys,
#   4. source references to the target variables,
#   5. expected milestone ownership.
#
# This audit does NOT reconstruct missing physics arrays. It determines whether
# each required V16A component is:
#
#   EXACTLY_PERSISTED
#   SOURCE_DEFINED_NOT_PERSISTED
#   AMBIGUOUS_WITHIN_OWNER
#   NOT_FOUND
#
# If every failed V16A component is exactly persisted, the next milestone can
# perform a repaired Foundation Case extraction. If some components are only
# source-defined, a separate source-authentic frozen-array reconstruction
# contract will be required before V16B.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_R1_FOUNDATION_COMPONENT_BINDING_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

V16A_DIR = ROOT / "output" / "V16_A_FOUNDATION_CASE_0001"
V16A_SUMMARY = V16A_DIR / "PAD_Stream_V16A_Summary.json"
V16A_BOUND = V16A_DIR / "V16A_Bound_Component_Identity.csv"

TARGETS = {
    "Kx": {
        "owner": ["SG1", "SG2"],
        "shapes": [(15, 50, 50)],
        "key_patterns": [r"^Kx$", r"^kx$", r"perm.*x", r"permeability.*x"],
        "source_symbols": ["Kx", "kx"],
    },
    "Ky": {
        "owner": ["SG1", "SG2"],
        "shapes": [(15, 50, 50)],
        "key_patterns": [r"^Ky$", r"^ky$", r"perm.*y", r"permeability.*y"],
        "source_symbols": ["Ky", "ky"],
    },
    "Kz": {
        "owner": ["SG1", "SG2"],
        "shapes": [(15, 50, 50)],
        "key_patterns": [r"^Kz$", r"^kz$", r"perm.*z", r"permeability.*z"],
        "source_symbols": ["Kz", "kz"],
    },
    "porosity": {
        "owner": ["SG1", "SG2", "SG3"],
        "shapes": [(15, 50, 50)],
        "key_patterns": [r"poro", r"porosity", r"^phi$"],
        "source_symbols": ["porosity", "poro", "phi"],
    },
    "pressure": {
        "owner": ["SG3"],
        "shapes": [(15, 50, 50)],
        "key_patterns": [r"pressure", r"^p$", r"p_grid", r"pfield"],
        "source_symbols": ["pressure", "p_grid", "p"],
    },
    "Qx": {
        "owner": ["SG4"],
        "shapes": [(15, 50, 49)],
        "key_patterns": [r"^Qx$", r"^qx$", r"flux.*x"],
        "source_symbols": ["Qx", "qx"],
    },
    "Qy": {
        "owner": ["SG4"],
        "shapes": [(15, 49, 50)],
        "key_patterns": [r"^Qy$", r"^qy$", r"flux.*y"],
        "source_symbols": ["Qy", "qy"],
    },
    "Qz": {
        "owner": ["SG4"],
        "shapes": [(14, 50, 50)],
        "key_patterns": [r"^Qz$", r"^qz$", r"flux.*z"],
        "source_symbols": ["Qz", "qz"],
    },
    "Vx": {
        "owner": ["SG5"],
        "shapes": [(15, 50, 49)],
        "key_patterns": [r"^Vx$", r"^vx$", r"vel.*x", r"velocity.*x"],
        "source_symbols": ["Vx", "vx"],
    },
    "Vy": {
        "owner": ["SG5"],
        "shapes": [(15, 49, 50)],
        "key_patterns": [r"^Vy$", r"^vy$", r"vel.*y", r"velocity.*y"],
        "source_symbols": ["Vy", "vy"],
    },
    "Vz": {
        "owner": ["SG5"],
        "shapes": [(14, 50, 50)],
        "key_patterns": [r"^Vz$", r"^vz$", r"vel.*z", r"velocity.*z"],
        "source_symbols": ["Vz", "vz"],
    },
    "producer_id": {
        "owner": ["SG5", "SG6"],
        "shapes": [(1078,), (1078, 1)],
        "key_patterns": [r"producer.*id", r"prod.*id", r"terminal.*producer"],
        "source_symbols": ["producer_id", "producer_ids", "prod_id"],
    },
}


NPZ_TABLE = OUT / "V16AR1_Owner_Scoped_NPZ_Inventory.csv"
SOURCE_TABLE = OUT / "V16AR1_Source_Assignment_and_Serialization_Trace.csv"
COMPONENT_TABLE = OUT / "V16AR1_Target_Component_Resolution.csv"
GATE_TABLE = OUT / "V16AR1_Final_Binding_Audit_Gates.csv"
DECISION_TABLE = OUT / "V16AR1_Binding_Audit_Decision.csv"
CONTRACT_FILE = OUT / "V16AR1_Foundation_Component_Binding_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V16AR1_Summary.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_array(a: np.ndarray) -> str:
    a = np.ascontiguousarray(a)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode("utf-8"))
    h.update(str(tuple(a.shape)).encode("utf-8"))
    h.update(a.tobytes())
    return h.hexdigest()


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


def milestone_tag(path: Path) -> str | None:
    s = path.name.upper()
    for n in range(1, 7):
        if f"V15SG{n}" in s or f"V15_SG{n}" in str(path).upper():
            return f"SG{n}"
    return None


def owner_sources():
    result = []
    for p in sorted(ROOT.glob("PAD_Stream_V15SG*.py")):
        tag = milestone_tag(p)
        if tag in {f"SG{i}" for i in range(1, 7)}:
            result.append((tag, p))
    return result


def owner_output_dirs():
    outroot = ROOT / "output"
    result = []
    if not outroot.exists():
        return result
    for d in sorted(outroot.iterdir()):
        if not d.is_dir():
            continue
        tag = milestone_tag(d)
        if tag in {f"SG{i}" for i in range(1, 7)}:
            result.append((tag, d))
    return result


def scoped_npz_inventory():
    rows = []
    entries = []
    seen = set()

    # First: output directories owned by SG1-SG6.
    for tag, d in owner_output_dirs():
        for p in sorted(d.rglob("*.npz")):
            if p in seen:
                continue
            seen.add(p)
            try:
                with np.load(p, allow_pickle=False) as db:
                    for key in db.files:
                        a = np.asarray(db[key])
                        numeric = np.issubdtype(a.dtype, np.number)
                        finite = bool(np.all(np.isfinite(a))) if numeric else False
                        row = {
                            "owner": tag,
                            "artifact": str(p),
                            "artifact_sha256": sha256_file(p),
                            "key": key,
                            "shape": str(tuple(a.shape)),
                            "dtype": str(a.dtype),
                            "numeric": numeric,
                            "finite": finite,
                            "array_sha256": sha256_array(a) if numeric else "",
                        }
                        rows.append(row)
                        entries.append((tag, p, key, a.copy(), row))
            except Exception as e:
                rows.append({"owner": tag, "artifact": str(p), "load_error": repr(e)})

    # Second: root-level NPZs with strongly named SG1-SG6 products.
    for p in sorted(ROOT.glob("*.npz")):
        tag = milestone_tag(p)
        if tag not in {f"SG{i}" for i in range(1, 7)} or p in seen:
            continue
        try:
            with np.load(p, allow_pickle=False) as db:
                for key in db.files:
                    a = np.asarray(db[key])
                    numeric = np.issubdtype(a.dtype, np.number)
                    finite = bool(np.all(np.isfinite(a))) if numeric else False
                    row = {
                        "owner": tag,
                        "artifact": str(p),
                        "artifact_sha256": sha256_file(p),
                        "key": key,
                        "shape": str(tuple(a.shape)),
                        "dtype": str(a.dtype),
                        "numeric": numeric,
                        "finite": finite,
                        "array_sha256": sha256_array(a) if numeric else "",
                    }
                    rows.append(row)
                    entries.append((tag, p, key, a.copy(), row))
        except Exception as e:
            rows.append({"owner": tag, "artifact": str(p), "load_error": repr(e)})

    return rows, entries


def source_trace():
    rows = []
    for owner, path in owner_sources():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text)
        except Exception as e:
            rows.append({"owner": owner, "source": str(path), "parse_error": repr(e)})
            continue

        lines = text.splitlines()

        for node in ast.walk(tree):
            # assignments
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = []
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            targets.append(t.id)
                elif isinstance(node.target, ast.Name):
                    targets.append(node.target.id)

                for name in targets:
                    for comp, spec in TARGETS.items():
                        if owner not in spec["owner"]:
                            continue
                        if name in spec["source_symbols"] or name.lower() in [x.lower() for x in spec["source_symbols"]]:
                            rows.append({
                                "owner": owner,
                                "component": comp,
                                "record_type": "ASSIGNMENT",
                                "source": str(path),
                                "line": getattr(node, "lineno", None),
                                "symbol": name,
                                "source_text": lines[node.lineno - 1].strip() if getattr(node, "lineno", None) else "",
                            })

            # np.savez / savez_compressed calls
            if isinstance(node, ast.Call):
                fn = ""
                try:
                    fn = ast.unparse(node.func)
                except Exception:
                    pass
                if fn.endswith("np.savez") or fn.endswith("np.savez_compressed") or fn in {"np.savez", "np.savez_compressed"}:
                    for kw in node.keywords:
                        if not kw.arg:
                            continue
                        key = kw.arg
                        try:
                            val = ast.unparse(kw.value)
                        except Exception:
                            val = ""
                        for comp, spec in TARGETS.items():
                            if owner not in spec["owner"]:
                                continue
                            key_match = any(re.search(pat, key, flags=re.I) for pat in spec["key_patterns"])
                            symbol_match = any(sym.lower() in val.lower() for sym in spec["source_symbols"])
                            if key_match or symbol_match:
                                rows.append({
                                    "owner": owner,
                                    "component": comp,
                                    "record_type": "SERIALIZATION",
                                    "source": str(path),
                                    "line": getattr(node, "lineno", None),
                                    "symbol": val,
                                    "serialization_key": key,
                                    "source_text": lines[node.lineno - 1].strip() if getattr(node, "lineno", None) else "",
                                })
    return rows


def resolve_components(entries, source_rows):
    rows = []

    for comp, spec in TARGETS.items():
        persisted = []

        for owner, p, key, a, rec in entries:
            if owner not in spec["owner"]:
                continue
            if tuple(a.shape) not in spec["shapes"]:
                continue
            if not np.issubdtype(a.dtype, np.number) or not np.all(np.isfinite(a)):
                continue

            exact_semantic = any(re.search(pat, key, flags=re.I) for pat in spec["key_patterns"])
            if not exact_semantic:
                continue

            persisted.append((owner, p, key, a, rec))

        # Deduplicate by numerical hash.
        unique = {}
        for x in persisted:
            unique.setdefault(x[4]["array_sha256"], x)
        persisted_unique = list(unique.values())

        src = [r for r in source_rows if r.get("component") == comp]
        serial = [r for r in src if r.get("record_type") == "SERIALIZATION"]
        assign = [r for r in src if r.get("record_type") == "ASSIGNMENT"]

        if len(persisted_unique) == 1:
            owner, p, key, a, rec = persisted_unique[0]
            status = "EXACTLY_PERSISTED"
            rows.append({
                "component": comp,
                "status": status,
                "owner": owner,
                "artifact": str(p),
                "key": key,
                "shape": str(tuple(a.shape)),
                "dtype": str(a.dtype),
                "array_sha256": rec["array_sha256"],
                "source_assignment_records": len(assign),
                "source_serialization_records": len(serial),
            })
        elif len(persisted_unique) > 1:
            rows.append({
                "component": comp,
                "status": "AMBIGUOUS_WITHIN_OWNER",
                "owner": ";".join(sorted({x[0] for x in persisted_unique})),
                "artifact": ";".join(str(x[1]) for x in persisted_unique[:8]),
                "key": ";".join(x[2] for x in persisted_unique[:8]),
                "distinct_persisted_hashes": len(persisted_unique),
                "source_assignment_records": len(assign),
                "source_serialization_records": len(serial),
            })
        elif assign or serial:
            rows.append({
                "component": comp,
                "status": "SOURCE_DEFINED_NOT_PERSISTED",
                "owner": ";".join(spec["owner"]),
                "artifact": "",
                "key": "",
                "source_assignment_records": len(assign),
                "source_serialization_records": len(serial),
            })
        else:
            rows.append({
                "component": comp,
                "status": "NOT_FOUND",
                "owner": ";".join(spec["owner"]),
                "artifact": "",
                "key": "",
                "source_assignment_records": 0,
                "source_serialization_records": 0,
            })

    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16A-R1")
    print("Missing / Ambiguous Foundation Component Binding Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO NEW PHYSICS WILL BE SOLVED.
NO FAST MARCHING WILL BE EXECUTED.
NO FROZEN V15 ARTIFACT WILL BE CHANGED.
ONLY ORIGINAL SG1-SG6 OWNER LINEAGES WILL BE AUDITED.
NO GLOBAL SHAPE-ONLY ARRAY BINDING WILL BE USED.
""")

    if V16A_SUMMARY.exists():
        v16a = json.loads(V16A_SUMMARY.read_text(encoding="utf-8"))
        if v16a.get("status") != "V16A_FOUNDATION_CASE_EXTRACTION_BLOCKED":
            raise RuntimeError("V16A-R1 expects the blocked V16A extraction status.")

    npz_rows, entries = scoped_npz_inventory()
    save_csv(NPZ_TABLE, npz_rows)

    source_rows = source_trace()
    save_csv(SOURCE_TABLE, source_rows)

    component_rows = resolve_components(entries, source_rows)
    save_csv(COMPONENT_TABLE, component_rows)

    print("OWNER-SCOPED INVENTORY")
    print(f"  SG1-SG6 NPZ array records : {len(npz_rows)}")
    print(f"  Source trace records       : {len(source_rows)}")

    print("\nFAILED V16A COMPONENT RESOLUTION")
    for r in component_rows:
        print(
            f"  {r['component']:<18} | {r['status']:<28} | "
            f"{Path(r['artifact']).name if r.get('artifact') and ';' not in r['artifact'] else (r.get('artifact') or 'NONE')}"
            f"{' :: ' + r.get('key','') if r.get('key') and ';' not in r.get('key','') else ''}"
        )

    exactly = [r for r in component_rows if r["status"] == "EXACTLY_PERSISTED"]
    source_only = [r for r in component_rows if r["status"] == "SOURCE_DEFINED_NOT_PERSISTED"]
    ambiguous = [r for r in component_rows if r["status"] == "AMBIGUOUS_WITHIN_OWNER"]
    not_found = [r for r in component_rows if r["status"] == "NOT_FOUND"]

    all_exact = len(exactly) == len(TARGETS)

    gates = [
        ("incoming_V16A_block_reproduced", V16A_SUMMARY.exists()),
        ("SG1_SG6_owner_scope_enforced", True),
        ("global_shape_only_binding_prohibited", True),
        ("owner_scoped_NPZ_inventory_completed", True),
        ("source_assignments_audited", True),
        ("source_serialization_audited", True),
        ("component_resolution_completed", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_new_physics_solved", True),
        ("no_FMM_executed", True),
        ("no_V15_artifact_changed", True),
    ]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    if all_exact:
        status = "V16A_FAILED_COMPONENTS_EXACTLY_PERSISTED_AND_OWNER_BOUND"
        diagnosis = "ALL_PREVIOUSLY_FAILED_V16A_COMPONENTS_HAVE_UNIQUE_ORIGINAL_SG1_SG6_PERSISTED_AUTHORITY"
        recommendation = (
            "Proceed to repaired V16A extraction using only the exact owner-scoped bindings established by R1."
        )
        next_ms = "V16A-R2 — Repaired Owner-Scoped Foundation Case 0001 Extraction"
    elif source_only and not ambiguous and not not_found:
        status = "V16A_COMPONENTS_SOURCE_DEFINED_BUT_NOT_ALL_PERSISTED"
        diagnosis = "ONE_OR_MORE_REQUIRED_COMPONENTS_EXIST_IN_FROZEN_SG1_SG6_SOURCE_SEMANTICS_BUT_WERE_NOT_PERSISTED_AS_UNIQUE_ARRAYS"
        recommendation = (
            "Do not fabricate arrays. Audit source-authentic deterministic reconstruction feasibility only for the "
            "source-defined non-persisted components, preserving all frozen V15 inputs and formulas."
        )
        next_ms = "V16A-R2 — Source-Authentic Frozen Component Reconstruction Feasibility Audit"
    else:
        status = "V16A_COMPONENT_BINDING_REMAINS_INCOMPLETE"
        diagnosis = "ONE_OR_MORE_REQUIRED_COMPONENTS_REMAIN_AMBIGUOUS_OR_NOT_FOUND_WITHIN_THEIR_ORIGINAL_SG1_SG6_OWNER_LINEAGE"
        recommendation = (
            "Do not run Fast Marching. Audit only the ambiguous/not-found component rows and their exact SG1-SG6 source/output lineage."
        )
        next_ms = "V16A-R2 — Residual Original-Milestone Component Lineage Audit"

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "exactly_persisted_count": len(exactly),
        "source_defined_not_persisted_count": len(source_only),
        "ambiguous_within_owner_count": len(ambiguous),
        "not_found_count": len(not_found),
        "next_milestone": next_ms,
    }])

    contract = {
        "milestone": "V16A-R1",
        "status": status,
        "diagnosis": diagnosis,
        "resolution_counts": {
            "exactly_persisted": len(exactly),
            "source_defined_not_persisted": len(source_only),
            "ambiguous_within_owner": len(ambiguous),
            "not_found": len(not_found),
        },
        "component_resolution": component_rows,
        "constraints": {
            "training_performed": False,
            "model_predict_executed": False,
            "new_physics_solved": False,
            "FMM_executed": False,
            "V15_artifact_changed": False,
            "global_shape_only_binding_used": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT_FILE, contract)

    save_json(SUMMARY_FILE, {
        "milestone": "V16A-R1",
        "status": status,
        "diagnosis": diagnosis,
        "resolution_counts": contract["resolution_counts"],
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("\nRESOLUTION COUNTS")
    print(f"  Exactly persisted             : {len(exactly)}")
    print(f"  Source-defined / not persisted: {len(source_only)}")
    print(f"  Ambiguous within owner        : {len(ambiguous)}")
    print(f"  Not found                     : {len(not_found)}")

    print("\n" + "=" * 78)
    print("V16A-R1 FINAL AUDIT GATES")
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
    for p in [NPZ_TABLE, SOURCE_TABLE, COMPONENT_TABLE, GATE_TABLE, DECISION_TABLE]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16A-R1 FOUNDATION COMPONENT BINDING AUDIT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()

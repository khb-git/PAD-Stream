from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import re

import numpy as np


# =============================================================================
# PAD-Stream V16A-R8A
# Final Kz / Horizontal-Anisotropy Binding Repair Audit
#
# PURPOSE
# -------
# R8 failed before assembly because infer_kz_ratio() could not bind the exact
# SG2 vertical/horizontal permeability relation from source.
#
# R8A repairs ONLY that binding.
#
# It does NOT:
#   - rerun SG3 pressure,
#   - rerun SG4 flux,
#   - recompute velocity,
#   - retrace Pollock,
#   - run Fast Marching,
#   - train/infer ML,
#   - mutate V15 artifacts,
#   - assemble/freeze Foundation Case 0001 yet.
#
# R8A searches source-authentically for the SG2 Kz relation using:
#   1. direct assignments (Kz = ...),
#   2. array/list assignments that contain Kz,
#   3. scalar anisotropy constants,
#   4. multiplication/division expressions,
#   5. source text context around Kx/Ky/Kz,
#   6. persisted SG2 summary/contract metadata.
#
# Numerical closeness is never used to select the ratio.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_R8A_KZ_ANISOTROPY_BINDING_REPAIR"
OUT.mkdir(parents=True, exist_ok=True)

R8_SOURCE = ROOT / "PAD_Stream_V16AR8_Foundation_Case_0001_Final_Assembly_Freeze.py"
SG2_CANDIDATES = sorted(ROOT.glob("PAD_Stream_V15SG2*.py"))

SOURCE_TRACE = OUT / "V16AR8A_SG2_Kz_Source_Expression_Trace.csv"
CONSTANT_TRACE = OUT / "V16AR8A_SG2_Anisotropy_Constant_Trace.csv"
METADATA_TRACE = OUT / "V16AR8A_SG2_Persisted_Anisotropy_Metadata.csv"
DECISION_CSV = OUT / "V16AR8A_Kz_Ratio_Binding_Decision.csv"
GATE_CSV = OUT / "V16AR8A_Final_Kz_Binding_Gates.csv"
CONTRACT = OUT / "V16AR8A_Kz_Anisotropy_Binding_Contract.json"
SUMMARY = OUT / "PAD_Stream_V16AR8A_Summary.json"


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


def find_sg2():
    if len(SG2_CANDIDATES) == 1:
        return SG2_CANDIDATES[0]
    preferred = [p for p in SG2_CANDIDATES if "Transmiss" in p.name or "Anisotropic" in p.name]
    if len(preferred) == 1:
        return preferred[0]
    raise RuntimeError(f"Could not uniquely resolve SG2 source: {[p.name for p in SG2_CANDIDATES]}")


def parse_numeric_constants(tree):
    rows = []
    constants = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        try:
            val = ast.literal_eval(getattr(node, "value", None))
        except Exception:
            continue
        if not isinstance(val, (int, float)):
            continue
        for target in assigned_targets(node):
            constants[target] = float(val)
            rows.append({
                "symbol": target,
                "value": float(val),
                "line": getattr(node, "lineno", None),
                "expression": ast_text(node),
            })
    return constants, rows


def trace_kz_expressions(source: Path, text: str, tree):
    rows = []
    lines = text.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        expr = ast_text(getattr(node, "value", None))
        targets = assigned_targets(node)
        joined = (" ".join(targets) + " " + expr).lower()

        if any(tok in joined for tok in ["kz", "vertical", "anisot", "k_v", "kv"]):
            rows.append({
                "source": str(source),
                "source_sha256": sha256_file(source),
                "line": getattr(node, "lineno", None),
                "targets": ";".join(targets),
                "expression": expr,
                "source_text": lines[node.lineno - 1].strip() if getattr(node, "lineno", None) else "",
            })

    # Also retain contextual text lines that mention Kx/Ky/Kz.
    for i, line in enumerate(lines, 1):
        low = line.lower()
        if "kz" in low or ("vertical" in low and "perm" in low) or "anisot" in low:
            rows.append({
                "source": str(source),
                "source_sha256": sha256_file(source),
                "line": i,
                "targets": "",
                "expression": "",
                "source_text": line.strip(),
            })

    return rows


def ratio_from_ast(tree, constants):
    candidates = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue

        targets = assigned_targets(node)
        if not any(t.lower() in {"kz", "k_z", "kv", "k_v"} or "kz" in t.lower() for t in targets):
            continue

        value = getattr(node, "value", None)

        # Kz = c * K
        if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Mult):
            left, right = value.left, value.right

            for num_node, other_node in [(left, right), (right, left)]:
                if isinstance(num_node, ast.Constant) and isinstance(num_node.value, (int, float)):
                    ratio = float(num_node.value)
                    if 0 < ratio <= 1:
                        candidates.append((ratio, f"direct multiplication at line {node.lineno}", ast_text(node)))

                if isinstance(num_node, ast.Name) and num_node.id in constants:
                    ratio = float(constants[num_node.id])
                    if 0 < ratio <= 1:
                        candidates.append((ratio, f"constant {num_node.id} multiplication at line {node.lineno}", ast_text(node)))

        # Kz = K / c  -> ratio 1/c
        if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Div):
            denom = value.right
            if isinstance(denom, ast.Constant) and isinstance(denom.value, (int, float)):
                d = float(denom.value)
                if d >= 1:
                    candidates.append((1.0/d, f"direct division at line {node.lineno}", ast_text(node)))
            if isinstance(denom, ast.Name) and denom.id in constants:
                d = float(constants[denom.id])
                if d >= 1:
                    candidates.append((1.0/d, f"constant {denom.id} division at line {node.lineno}", ast_text(node)))

        # Kz = some_name; inspect referenced scalar if name is a ratio-like constant
        if isinstance(value, ast.Name) and value.id in constants:
            ratio = float(constants[value.id])
            if 0 < ratio <= 1:
                candidates.append((ratio, f"direct constant assignment {value.id} at line {node.lineno}", ast_text(node)))

    return candidates


def ratio_from_source_text(text, constants):
    candidates = []

    # Robust patterns including indexing/casts/spaces.
    patterns = [
        r'Kz\s*=\s*([0-9]*\.?[0-9]+)\s*\*\s*[A-Za-z_][A-Za-z0-9_\[\]\(\),:\s]*',
        r'Kz\s*=\s*[A-Za-z_][A-Za-z0-9_\[\]\(\),:\s]*\*\s*([0-9]*\.?[0-9]+)',
        r'Kz\s*=\s*[A-Za-z_][A-Za-z0-9_\[\]\(\),:\s]*\/\s*([0-9]*\.?[0-9]+)',
        r'KZ_RATIO\s*=\s*([0-9]*\.?[0-9]+)',
        r'KZ_KX_RATIO\s*=\s*([0-9]*\.?[0-9]+)',
        r'VERTICAL_PERM_RATIO\s*=\s*([0-9]*\.?[0-9]+)',
        r'ANISOTROPY_RATIO\s*=\s*([0-9]*\.?[0-9]+)',
    ]

    for patt in patterns:
        for m in re.finditer(patt, text, flags=re.I | re.S):
            v = float(m.group(1))
            if "\\/\\s*" in patt:
                if v >= 1:
                    v = 1.0 / v
            if 0 < v <= 1:
                candidates.append((v, f"source regex {patt}", m.group(0)[:500]))

    # Search scalar constants whose names are semantically tied to vertical perm.
    for name, val in constants.items():
        lname = name.lower()
        if (
            "kz" in lname
            or "vertical" in lname
            or "anisot" in lname
            or lname in {"kvkh", "kv_kh", "kz_kx", "kz_ratio"}
        ):
            if 0 < val <= 1:
                candidates.append((float(val), f"semantic scalar constant {name}", f"{name}={val}"))

    return candidates


def persisted_metadata_audit():
    rows = []
    outroot = ROOT / "output"
    if not outroot.exists():
        return rows

    for p in sorted(outroot.rglob("*")):
        if not p.is_file():
            continue
        lowp = str(p).lower()
        if "v16_" in lowp or "v16a" in lowp:
            continue
        if "sg2" not in lowp:
            continue
        if p.suffix.lower() not in {".json", ".csv", ".txt"}:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for patt in [
            r'Kz[^0-9]{0,40}([0-9]*\.?[0-9]+)\s*\*',
            r'Kz[^0-9]{0,40}([0-9]*\.?[0-9]+)',
            r'vertical[^0-9]{0,50}([0-9]*\.?[0-9]+)',
            r'anisot[^0-9]{0,50}([0-9]*\.?[0-9]+)',
        ]:
            for m in re.finditer(patt, text, flags=re.I):
                try:
                    v = float(m.group(1))
                except Exception:
                    continue
                if 0 < v <= 1:
                    rows.append({
                        "artifact": str(p),
                        "artifact_sha256": sha256_file(p),
                        "pattern": patt,
                        "candidate_ratio": v,
                        "match": m.group(0)[:500],
                    })
    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16A-R8A")
    print("Final Kz / Horizontal-Anisotropy Binding Repair Audit")
    print("=" * 78)

    print("""
NO FOUNDATION PACKAGE WILL BE FROZEN IN R8A.
NO SG3 PRESSURE SOLVE WILL BE RERUN.
NO SG4 DARCY FLUX WILL BE RERUN.
NO VELOCITY ARRAY WILL BE RECOMPUTED.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO FAST MARCHING WILL BE EXECUTED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
NO FROZEN V15 ARTIFACT WILL BE CHANGED.
ONLY THE FAILED R8 Kz/K HORIZONTAL-ANISOTROPY BINDING WILL BE REPAIRED.
""")

    if not R8_SOURCE.exists():
        raise FileNotFoundError(R8_SOURCE)

    sg2 = find_sg2()
    text = sg2.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(text)

    constants, constant_rows = parse_numeric_constants(tree)
    source_rows = trace_kz_expressions(sg2, text, tree)
    metadata_rows = persisted_metadata_audit()

    save_csv(SOURCE_TRACE, source_rows)
    save_csv(CONSTANT_TRACE, constant_rows)
    save_csv(METADATA_TRACE, metadata_rows)

    candidates = []
    candidates.extend(ratio_from_ast(tree, constants))
    candidates.extend(ratio_from_source_text(text, constants))
    candidates.extend(
        (float(r["candidate_ratio"]), f"persisted SG2 metadata {r['artifact']}", r["match"])
        for r in metadata_rows
    )

    # Deduplicate by ratio while retaining provenance.
    grouped = {}
    for ratio, source, expr in candidates:
        grouped.setdefault(round(float(ratio), 12), []).append((source, expr))

    unique_ratios = sorted(grouped.keys())

    if len(unique_ratios) == 1:
        ratio = float(unique_ratios[0])
        bound = True
        evidence = grouped[unique_ratios[0]]
        status = "V16A_KZ_ANISOTROPY_RATIO_FINAL_BOUND"
        diagnosis = "ONE_UNIQUE_SOURCE_AUTHENTIC_VERTICAL_TO_HORIZONTAL_PERMEABILITY_RATIO_IS_SUPPORTED_BY_SG2_PROVENANCE"
        recommendation = (
            "Patch R8 to consume the R8A bound ratio contract instead of rediscovering the ratio heuristically, "
            "then rerun Foundation Case 0001 assembly/freeze."
        )
        next_ms = "V16A-R8R — Repaired Foundation Case 0001 Final Assembly / Freeze"
    elif len(unique_ratios) == 0:
        ratio = None
        bound = False
        evidence = []
        status = "V16A_KZ_ANISOTROPY_RATIO_STILL_UNRESOLVED"
        diagnosis = "NO_SOURCE_AUTHENTIC_KZ_HORIZONTAL_RATIO_FOUND_IN_SG2_SOURCE_OR_PERSISTED_METADATA"
        recommendation = (
            "Do not freeze Foundation Case 0001. Inspect only SG2 Kx/Ky/Kz construction lines and their exact upstream permeability bindings."
        )
        next_ms = "V16A-R8A1 — Direct SG2 K-Array Construction Audit"
    else:
        ratio = None
        bound = False
        evidence = []
        status = "V16A_KZ_ANISOTROPY_RATIO_CONFLICT"
        diagnosis = "MULTIPLE_DISTINCT_SOURCE_AUTHENTIC_KZ_HORIZONTAL_RATIO_CANDIDATES_FOUND"
        recommendation = (
            "Do not select by expectation or numerical plausibility. Resolve only the conflicting SG2 ratio candidates."
        )
        next_ms = "V16A-R8A1 — SG2 Kz Ratio Conflict Audit"

    decision_rows = []
    if bound:
        for source, expr in evidence:
            decision_rows.append({
                "status": status,
                "bound_ratio": ratio,
                "evidence_source": source,
                "evidence_expression": expr,
            })
    else:
        decision_rows.append({
            "status": status,
            "bound_ratio": "",
            "candidate_ratios": ";".join(map(str, unique_ratios)),
        })
    save_csv(DECISION_CSV, decision_rows)

    gates = [
        ("incoming_R8_Kz_binding_failure_targeted", True),
        ("authoritative_SG2_source_bound", True),
        ("SG2_Kz_source_expressions_audited", True),
        ("SG2_numeric_constants_audited", True),
        ("persisted_SG2_metadata_audited", True),
        ("no_ratio_selected_by_numerical_closeness", True),
        ("no_foundation_freeze_executed", True),
        ("no_SG3_rerun", True),
        ("no_SG4_rerun", True),
        ("no_velocity_recompute", True),
        ("no_Pollock_retrace", True),
        ("no_FMM", True),
        ("no_model_predict", True),
        ("no_training", True),
        ("no_V15_mutation", True),
    ]
    save_csv(GATE_CSV, [{"gate": g, "passed": p} for g,p in gates])

    contract = {
        "milestone": "V16A-R8A",
        "status": status,
        "diagnosis": diagnosis,
        "SG2_source": str(sg2),
        "SG2_sha256": sha256_file(sg2),
        "kz_horizontal_ratio_bound": bound,
        "kz_horizontal_ratio": ratio,
        "candidate_ratios": unique_ratios,
        "evidence": [
            {"source": s, "expression": e}
            for s, e in evidence
        ],
        "constraints": {
            "foundation_freeze_executed": False,
            "SG3_rerun": False,
            "SG4_rerun": False,
            "velocity_recompute": False,
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
        "milestone": "V16A-R8A",
        "status": status,
        "diagnosis": diagnosis,
        "kz_horizontal_ratio_bound": bound,
        "kz_horizontal_ratio": ratio,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("Kz / HORIZONTAL PERMEABILITY BINDING")
    print(f"  SG2 source              : {sg2.name}")
    print(f"  Candidate ratio count   : {len(unique_ratios)}")
    print(f"  Candidate ratios        : {unique_ratios if unique_ratios else 'NONE'}")
    print(f"  Unique ratio bound      : {bound}")
    print(f"  Bound ratio             : {ratio if ratio is not None else 'UNRESOLVED'}")

    print("\n" + "=" * 78)
    print("V16A-R8A FINAL Kz BINDING GATES")
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
    for p in [SOURCE_TRACE, CONSTANT_TRACE, METADATA_TRACE, DECISION_CSV, GATE_CSV]:
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT.name}")
    print("\nSummary:")
    print(f"  {SUMMARY.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16A-R8A Kz ANISOTROPY BINDING REPAIR AUDIT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()

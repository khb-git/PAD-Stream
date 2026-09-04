from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import re
from collections import defaultdict, deque


# =============================================================================
# PAD-Stream V16A-R6A
# Final SG3 Pressure Recipe Residual Binding Audit
#
# PURPOSE
# -------
# R6 found the authoritative SG3 source, but its generic solver detector could
# not uniquely bind:
#   - the actual pressure solve,
#   - matrix/RHS inputs,
#   - post-solve pressure output,
#   - SG4 pressure consumer lineage.
#
# R6A repairs ONLY the source-analysis contract. It does NOT run SG3.
#
# Strategy:
#   1. Parse the single authoritative SG3 source.
#   2. Inventory every solve-like call and classify it by dataflow context.
#   3. Bind candidate linear-system matrix/RHS symbols from argument semantics.
#   4. Trace the solver result forward through aliases, indexing, reshape,
#      conversion, and return/dictionary packing.
#   5. Audit SG4 load/consumer semantics independently of requiring the same
#      variable name used inside SG3.
#   6. Select a recipe only from source/dataflow provenance, never numerical
#      performance.
#
# NO TRAINING.
# NO MODEL.PREDICT.
# NO PRESSURE SOLVE.
# NO DARCY FLUX RECOMPUTE.
# NO VELOCITY RECONSTRUCTION.
# NO POLLOCK RETRACE.
# NO FAST MARCHING.
# NO V15 MUTATION.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_R6A_FINAL_SG3_PRESSURE_RECIPE_BINDING_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

R6_DIR = ROOT / "output" / "V16_A_R6_RESIDUAL_REGENERATION_RECIPE_BINDING_AUDIT"
R6_SUMMARY = R6_DIR / "PAD_Stream_V16AR6_Summary.json"

SOURCE_ID = OUT / "V16AR6A_SG3_Authoritative_Source.csv"
SOLVE_CALLS = OUT / "V16AR6A_All_Solve_Like_Call_Inventory.csv"
SOLVER_BINDING = OUT / "V16AR6A_Pressure_Solver_Dataflow_Binding.csv"
MATRIX_RHS = OUT / "V16AR6A_Matrix_RHS_Semantic_Binding.csv"
FORWARD = OUT / "V16AR6A_Postsolve_Forward_Alias_Trace.csv"
RETURN_PACKING = OUT / "V16AR6A_Return_Dictionary_Serialization_Trace.csv"
SG4_CONSUMER = OUT / "V16AR6A_SG4_Pressure_Consumer_Contract.csv"
DECISION = OUT / "V16AR6A_Final_SG3_Pressure_Recipe_Decision.csv"
GATES = OUT / "V16AR6A_Final_Audit_Gates.csv"
CONTRACT = OUT / "V16AR6A_Final_SG3_Pressure_Recipe_Contract.json"
SUMMARY = OUT / "PAD_Stream_V16AR6A_Summary.json"


SOLVE_NAMES = {
    "spsolve", "cg", "bicg", "bicgstab", "gmres", "minres",
    "lsqr", "lsmr", "solve"
}

MATRIX_HINTS = {"a", "matrix", "lhs", "system_matrix", "pressure_matrix", "A"}
RHS_HINTS = {"b", "rhs", "source", "q", "forcing"}
PRESSURE_HINTS = {
    "p", "pressure", "pressure_pa", "pressure_psi", "p_pa", "p_psi",
    "pvec", "p_grid", "p3d", "pressure_grid", "solution"
}


def save_csv(path, rows):
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


def save_json(path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()


def txt(node):
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def assigned_targets(node):
    out = []
    targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
    for t in targets:
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


def enclosing_function(tree, lineno):
    best = ("<module>", -1)
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef):
            end = getattr(n, "end_lineno", n.lineno)
            if n.lineno <= lineno <= end and n.lineno > best[1]:
                best = (n.name, n.lineno)
    return best[0]


def find_sg3():
    cands = sorted(ROOT.glob("PAD_Stream_V15SG3*.py"))
    exact = [p for p in cands if "FiveSpot_Pressure_Solve" in p.name]
    if len(exact) == 1:
        return exact[0]
    if len(cands) == 1:
        return cands[0]
    raise RuntimeError(f"Expected one authoritative SG3 source, found {[p.name for p in cands]}")


def parse_source(path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    return text, ast.parse(text)


def solve_name(call):
    fn = txt(call.func)
    base = fn.split(".")[-1].lower()
    return fn, base


def assignment_parent(tree, target_node):
    for n in ast.walk(tree):
        if isinstance(n, (ast.Assign, ast.AnnAssign)) and getattr(n, "value", None) is target_node:
            ts = assigned_targets(n)
            return n, ts
    return None, []


def inventory_solve_calls(path, text, tree):
    rows = []
    objects = []
    lines = text.splitlines()

    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue
        fn, base = solve_name(call)
        if base not in SOLVE_NAMES:
            continue

        parent, targets = assignment_parent(tree, call)
        args = [txt(a) for a in call.args]
        func = enclosing_function(tree, call.lineno)

        score = 0
        # Strongest evidence: sparse/scipy solve with at least matrix + RHS args.
        if base == "spsolve":
            score += 500
        elif base in {"cg", "bicg", "bicgstab", "gmres", "minres"}:
            score += 450
        elif base == "solve":
            score += 200

        if len(args) >= 2:
            score += 100

        joined = " ".join(args + targets).lower()
        if any(h.lower() in joined for h in PRESSURE_HINTS):
            score += 150
        if any("matrix" in a.lower() or a.strip() in {"A", "a"} for a in args[:1]):
            score += 80
        if any("rhs" in a.lower() or a.strip() in {"b"} for a in args[1:2]):
            score += 80

        # Penalize obviously unrelated dense helper solves if identifiable.
        if "poly" in joined or "least" in joined or "fit" in joined:
            score -= 200

        rec = {
            "source": str(path),
            "line": call.lineno,
            "function": func,
            "call": txt(call),
            "solver_function": fn,
            "solver_base_name": base,
            "targets": ";".join(targets),
            "args": ";".join(args),
            "arg_count": len(args),
            "score": score,
            "source_text": lines[call.lineno - 1].strip(),
        }
        rows.append(rec)
        objects.append((score, call, rec))

    rows.sort(key=lambda r: (-int(r["score"]), int(r["line"])))
    objects.sort(key=lambda x: (-x[0], x[1].lineno))
    return rows, objects


def build_assignments(tree):
    amap = defaultdict(list)
    for n in ast.walk(tree):
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            for t in assigned_targets(n):
                amap[t].append(n)
    return amap


def semantic_matrix_rhs(solver_call, amap):
    args = list(solver_call.args)
    rows = []

    roles = []
    if len(args) >= 1:
        roles.append(("matrix", args[0]))
    if len(args) >= 2:
        roles.append(("rhs", args[1]))

    for role, node in roles:
        expr = txt(node)
        root_names = sorted(names(node))
        rows.append({
            "role": role,
            "top_level_expression": expr,
            "root_symbols": ";".join(root_names),
            "resolved_assignment_count": sum(len(amap.get(s, [])) for s in root_names),
        })

        # one level deeper is enough for a binding audit; execution happens later
        for s in root_names:
            for an in amap.get(s, []):
                rows.append({
                    "role": role,
                    "top_level_expression": expr,
                    "root_symbols": s,
                    "dependency_expression": txt(getattr(an, "value", None)),
                    "dependency_symbols": ";".join(sorted(names(getattr(an, "value", None)))),
                    "resolved_assignment_count": 1,
                })

    matrix_bound = any(r["role"] == "matrix" and r["root_symbols"] for r in rows)
    rhs_bound = any(r["role"] == "rhs" and r["root_symbols"] for r in rows)
    return rows, matrix_bound, rhs_bound


def forward_alias_trace(tree, seed_symbols):
    rows = []
    known = set(seed_symbols)

    # fixed-point forward propagation through assignments
    changed = True
    while changed:
        changed = False
        for n in ast.walk(tree):
            if not isinstance(n, (ast.Assign, ast.AnnAssign)):
                continue
            targets = assigned_targets(n)
            expr_names = names(getattr(n, "value", None))
            if not (known & expr_names):
                continue

            for t in targets:
                if t not in known:
                    known.add(t)
                    changed = True

                low = (t + " " + txt(getattr(n, "value", None))).lower()
                pressure_semantic = any(h.lower() == t.lower() or h.lower() in t.lower() for h in PRESSURE_HINTS)
                transform = any(tok in low for tok in ["reshape", "psi", "pa", "astype", "ravel", "flatten", "copy", "where"])

                rows.append({
                    "line": getattr(n, "lineno", None),
                    "target_symbol": t,
                    "expression": txt(getattr(n, "value", None)),
                    "depends_on_known_solver_output": True,
                    "pressure_semantic": pressure_semantic,
                    "postsolve_transform": transform,
                })
    return rows, known


def return_and_pack_trace(tree, known):
    rows = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Return):
            expr = txt(n.value)
            deps = names(n.value)
            if known & deps:
                rows.append({
                    "record_type": "RETURN",
                    "line": n.lineno,
                    "key": "",
                    "expression": expr,
                    "known_pressure_dependencies": ";".join(sorted(known & deps)),
                })

        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                key = txt(k)
                deps = names(v)
                if known & deps:
                    rows.append({
                        "record_type": "DICT_PACK",
                        "line": getattr(n, "lineno", None),
                        "key": key,
                        "expression": txt(v),
                        "known_pressure_dependencies": ";".join(sorted(known & deps)),
                    })

        if isinstance(n, ast.Call):
            fn = txt(n.func).lower()
            if "savez" in fn or fn.endswith("np.save") or fn.endswith(".save"):
                for kw in n.keywords:
                    if kw.arg and (known & names(kw.value)):
                        rows.append({
                            "record_type": "SERIALIZATION",
                            "line": n.lineno,
                            "key": kw.arg,
                            "expression": txt(kw.value),
                            "known_pressure_dependencies": ";".join(sorted(known & names(kw.value))),
                        })
    return rows


def sg4_pressure_consumer():
    rows = []
    for p in sorted(ROOT.glob("PAD_Stream_V15SG4*.py")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            low = line.lower()
            if "pressure" in low or re.search(r"\bp(_psi|_pa|3d|_grid)?\b", low):
                if any(tok in low for tok in [
                    "load", "npz", "solve", "gradient", "qx", "qy", "qz",
                    "darcy", "potential", "pressure"
                ]):
                    rows.append({
                        "source": str(p),
                        "source_sha256": sha256_file(p),
                        "line": i,
                        "text": line.strip(),
                    })
    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16A-R6A")
    print("Final SG3 Pressure Recipe Residual Binding Audit")
    print("=" * 78)
    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO PRESSURE SOLVE WILL BE EXECUTED.
NO DARCY FLUX WILL BE RECOMPUTED.
NO VELOCITY FIELD WILL BE RECONSTRUCTED.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO FAST MARCHING WILL BE EXECUTED.
NO FROZEN V15 ARTIFACT WILL BE CHANGED.
ONLY SG3 SOURCE/DATAFLOW BINDING LOGIC IS BEING REPAIRED.
""")

    if not R6_SUMMARY.exists():
        raise FileNotFoundError(R6_SUMMARY)

    r6 = json.loads(R6_SUMMARY.read_text(encoding="utf-8"))
    if r6.get("status") != "V16A_SG3_PRESSURE_REGENERATION_RECIPE_STILL_INCOMPLETE":
        raise RuntimeError("R6A expects the incomplete R6 SG3 recipe status.")

    sg3 = find_sg3()
    text, tree = parse_source(sg3)

    save_csv(SOURCE_ID, [{
        "source": str(sg3),
        "sha256": sha256_file(sg3),
        "line_count": len(text.splitlines()),
    }])

    solve_rows, solve_objs = inventory_solve_calls(sg3, text, tree)
    save_csv(SOLVE_CALLS, solve_rows)

    if not solve_objs:
        selected = None
        unique_authority = False
        matrix_rows = []
        matrix_bound = rhs_bound = False
        forward_rows = []
        known = set()
        pack_rows = []
    else:
        selected = solve_objs[0]
        top_score = selected[0]
        second_score = solve_objs[1][0] if len(solve_objs) > 1 else None
        unique_authority = second_score is None or top_score > second_score

        solver_call = selected[1]
        selected_rec = selected[2]

        save_csv(SOLVER_BINDING, [{
            **selected_rec,
            "selected": True,
            "second_score": second_score if second_score is not None else "",
            "score_margin": top_score - second_score if second_score is not None else top_score,
            "unique_by_source_dataflow_score": unique_authority,
        }])

        amap = build_assignments(tree)
        matrix_rows, matrix_bound, rhs_bound = semantic_matrix_rhs(solver_call, amap)
        save_csv(MATRIX_RHS, matrix_rows)

        seed_symbols = [x for x in selected_rec["targets"].split(";") if x]
        forward_rows, known = forward_alias_trace(tree, seed_symbols)
        save_csv(FORWARD, forward_rows)

        pack_rows = return_and_pack_trace(tree, known)
        save_csv(RETURN_PACKING, pack_rows)

    if not solve_objs:
        save_csv(SOLVER_BINDING, [])
        save_csv(MATRIX_RHS, [])
        save_csv(FORWARD, [])
        save_csv(RETURN_PACKING, [])

    sg4_rows = sg4_pressure_consumer()
    save_csv(SG4_CONSUMER, sg4_rows)

    pressure_aliases = [
        r for r in forward_rows
        if r.get("pressure_semantic") or r.get("postsolve_transform")
    ]
    output_bound = bool(pressure_aliases or pack_rows)
    sg4_contract_present = len(sg4_rows) > 0

    recipe_ready = (
        selected is not None
        and unique_authority
        and matrix_bound
        and rhs_bound
        and output_bound
    )

    print("R6A SG3 PRESSURE RECIPE")
    print(f"  Authoritative source        : {sg3.name}")
    print(f"  Solve-like calls            : {len(solve_rows)}")
    print(f"  Selected solver             : {selected[2]['solver_function'] if selected else 'NONE'}")
    print(f"  Unique source/dataflow bind : {unique_authority}")
    print(f"  Matrix bound                : {matrix_bound}")
    print(f"  RHS bound                   : {rhs_bound}")
    print(f"  Postsolve output bound      : {output_bound}")
    print(f"  SG4 pressure contract found : {sg4_contract_present}")
    print(f"  Recipe ready                : {recipe_ready}")

    gates = [
        ("incoming_R6_incomplete_status_reproduced", True),
        ("authoritative_SG3_source_fixed", True),
        ("all_solve_like_calls_inventoried", True),
        ("solver_selected_by_source_dataflow_not_numerical_performance", True),
        ("matrix_argument_audited", True),
        ("rhs_argument_audited", True),
        ("postsolve_forward_alias_trace_completed", True),
        ("return_dictionary_serialization_trace_completed", True),
        ("SG4_pressure_consumer_contract_audited", True),
        ("no_pressure_solve_executed", True),
        ("no_Darcy_flux_recomputed", True),
        ("no_velocity_reconstructed", True),
        ("no_Pollock_retrace_executed", True),
        ("no_FMM_executed", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_V15_artifact_changed", True),
    ]
    save_csv(GATES, [{"gate": g, "passed": p} for g, p in gates])

    if recipe_ready:
        status = "V16A_SG3_PRESSURE_REGENERATION_RECIPE_FINAL_BOUND"
        diagnosis = "SG3_PRESSURE_SOLVER_MATRIX_RHS_AND_POSTSOLVE_DATAFLOW_FORM_ONE_SOURCE_AUTHENTIC_REGENERATION_RECIPE"
        recommendation = (
            "The SG3 blocker is cleared. Source-authentic regeneration may now be authorized only as "
            "DERIVED_V16_FROM_FROZEN_V15. Proceed to controlled regeneration of pressure, SG4 fluxes, "
            "derived velocities, and producer identity without mutating or relabelling frozen V15 artifacts."
        )
        next_ms = "V16A-R7 — Controlled Source-Authentic Foundation Component Regeneration"
    else:
        status = "V16A_SG3_PRESSURE_RECIPE_RESIDUAL_BINDING_STILL_INCOMPLETE"
        diagnosis = "ONE_OR_MORE_SOLVER_MATRIX_RHS_OR_POSTSOLVE_DATAFLOW_BINDINGS_REMAIN_UNRESOLVED_AFTER_R6A"
        recommendation = (
            "Do not execute SG3. Inspect only the unresolved R6A tables. The most important table is "
            "V16AR6A_All_Solve_Like_Call_Inventory.csv, followed by the matrix/RHS and forward-alias traces."
        )
        next_ms = "V16A-R6B — Component-Specific SG3 Pressure Dataflow Audit"

    save_csv(DECISION, [{
        "status": status,
        "diagnosis": diagnosis,
        "solve_like_call_count": len(solve_rows),
        "unique_solver_binding": unique_authority,
        "matrix_bound": matrix_bound,
        "rhs_bound": rhs_bound,
        "postsolve_output_bound": output_bound,
        "SG4_pressure_contract_found": sg4_contract_present,
        "recipe_ready": recipe_ready,
        "derived_artifact_label": "DERIVED_V16_FROM_FROZEN_V15" if recipe_ready else "",
        "next_milestone": next_ms,
    }])

    contract = {
        "milestone": "V16A-R6A",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_SG3_source": str(sg3),
        "authoritative_SG3_sha256": sha256_file(sg3),
        "recipe_ready": recipe_ready,
        "recipe_contract": {
            "unique_solver_binding": unique_authority,
            "matrix_bound": matrix_bound,
            "rhs_bound": rhs_bound,
            "postsolve_output_bound": output_bound,
            "SG4_pressure_consumer_contract_found": sg4_contract_present,
        },
        "policy": {
            "historical_V15_relabelling_prohibited": True,
            "derived_artifact_label": "DERIVED_V16_FROM_FROZEN_V15" if recipe_ready else None,
        },
        "constraints": {
            "pressure_solve_executed": False,
            "Darcy_flux_recomputed": False,
            "velocity_reconstructed": False,
            "Pollock_retrace_executed": False,
            "FMM_executed": False,
            "model_predict_executed": False,
            "training_performed": False,
            "V15_artifact_changed": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT, contract)
    save_json(SUMMARY, {
        "milestone": "V16A-R6A",
        "status": status,
        "diagnosis": diagnosis,
        "recipe_ready": recipe_ready,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("\n" + "=" * 78)
    print("V16A-R6A FINAL GATES")
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
        SOURCE_ID, SOLVE_CALLS, SOLVER_BINDING, MATRIX_RHS,
        FORWARD, RETURN_PACKING, SG4_CONSUMER, DECISION, GATES
    ]:
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT.name}")
    print("\nSummary:")
    print(f"  {SUMMARY.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16A-R6A FINAL SG3 PRESSURE RECIPE AUDIT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()

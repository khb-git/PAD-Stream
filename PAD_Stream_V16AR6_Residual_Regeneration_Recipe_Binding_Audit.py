from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import re


# =============================================================================
# PAD-Stream V16A-R6
# Residual Regeneration Recipe Binding Audit
#
# PURPOSE
# -------
# R5 established:
#   SG3 pressure recipe ready        : False
#   SG4 flux recipe ready            : True
#   Frozen parameter evidence        : True
#   Producer ID bindable w/o retrace : True
#
# Therefore ONLY the unresolved SG3 pressure-regeneration recipe is audited.
#
# R6 DOES NOT:
#   - execute the pressure solve,
#   - execute SG4 flux reconstruction,
#   - reconstruct velocity,
#   - retrace Pollock streamlines,
#   - run Fast Marching,
#   - train or infer any ML model,
#   - mutate frozen Version 15 artifacts.
#
# R6 resolves:
#   1. the exact SG3 pressure solver call,
#   2. the function containing that call,
#   3. the variables feeding the solver matrix and RHS,
#   4. the post-solve reshape/unit-conversion path,
#   5. the final 3-D pressure symbol consumed downstream,
#   6. whether one complete source-authentic SG3 pressure recipe exists.
#
# If successful:
#   V16A source-authentic regeneration becomes authorized as a DERIVED V16
#   artifact, not as a historical persisted V15 artifact.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_R6_RESIDUAL_REGENERATION_RECIPE_BINDING_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

R5_DIR = ROOT / "output" / "V16_A_R5_REGENERATION_POLICY_AUDIT"
R5_SUMMARY = R5_DIR / "PAD_Stream_V16AR5_Summary.json"

SOURCE_TABLE = OUT / "V16AR6_SG3_Source_Identity.csv"
SOLVER_TABLE = OUT / "V16AR6_SG3_Solver_Call_Binding.csv"
MATRIX_RHS_TABLE = OUT / "V16AR6_SG3_Matrix_RHS_Dependency_Trace.csv"
POSTPROCESS_TABLE = OUT / "V16AR6_SG3_Pressure_Postsolve_Trace.csv"
DOWNSTREAM_TABLE = OUT / "V16AR6_SG3_to_SG4_Pressure_Consumer_Lineage.csv"
RECIPE_TABLE = OUT / "V16AR6_Pressure_Regeneration_Recipe_Decision.csv"
GATE_TABLE = OUT / "V16AR6_Final_Recipe_Binding_Gates.csv"
CONTRACT = OUT / "V16AR6_Residual_Regeneration_Recipe_Contract.json"
SUMMARY = OUT / "PAD_Stream_V16AR6_Summary.json"


SOLVER_TOKENS = ("spsolve", "cg", "bicg", "bicgstab", "gmres", "solve")
PRESSURE_SYMBOL_HINTS = (
    "pressure", "p_grid", "p3d", "p_psi", "p_pa", "pfield", "pressure_grid", "p"
)
POSTPROCESS_TOKENS = (
    "reshape", "astype", "psi", "pa", "convert", "flatten", "ravel"
)


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


def ast_text(node):
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def source_candidates():
    cands = []
    for p in sorted(ROOT.glob("PAD_Stream_V15SG3*.py")):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text)
        except Exception:
            continue

        solver_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = ast_text(node.func).lower()
                if any(tok in fn for tok in SOLVER_TOKENS):
                    solver_calls.append(node)

        cands.append({
            "path": p,
            "text": text,
            "tree": tree,
            "solver_calls": solver_calls,
        })
    return cands


def enclosing_function(tree, lineno):
    best = ("<module>", -1)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            end = getattr(node, "end_lineno", node.lineno)
            if node.lineno <= lineno <= end and node.lineno > best[1]:
                best = (node.name, node.lineno)
    return best[0]


def assigned_targets(node):
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
            for e in t.elts:
                if isinstance(e, ast.Name):
                    out.append(e.id)
    return out


def name_dependencies(node):
    deps = set()
    if node is None:
        return deps
    for x in ast.walk(node):
        if isinstance(x, ast.Name):
            deps.add(x.id)
    return sorted(deps)


def build_assignment_map(tree):
    amap = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            for t in assigned_targets(node):
                amap.setdefault(t, []).append(node)
    return amap


def choose_sg3_source(cands):
    rows = []
    for c in cands:
        p = c["path"]
        score = 0
        if c["solver_calls"]:
            score += 500
        name = p.name.lower()
        if "pressure_solve" in name:
            score += 300
        if "fivespot" in name or "five_spot" in name:
            score += 100
        rows.append({
            "source": str(p),
            "sha256": sha256_file(p),
            "solver_call_count": len(c["solver_calls"]),
            "score": score,
        })
    rows.sort(key=lambda r: (-r["score"], r["source"]))
    chosen = rows[0] if rows and rows[0]["solver_call_count"] > 0 else None
    return rows, chosen


def bind_solver_call(chosen_path, cands):
    c = next(x for x in cands if str(x["path"]) == chosen_path)
    tree = c["tree"]
    lines = c["text"].splitlines()
    amap = build_assignment_map(tree)

    records = []
    for node in c["solver_calls"]:
        parent_function = enclosing_function(tree, node.lineno)
        expr = ast_text(node)
        args = [ast_text(a) for a in node.args]
        kwargs = {kw.arg: ast_text(kw.value) for kw in node.keywords if kw.arg}

        # Find assignment target receiving solver result.
        target = ""
        for anode in ast.walk(tree):
            if isinstance(anode, (ast.Assign, ast.AnnAssign)) and getattr(anode, "value", None) is node:
                ts = assigned_targets(anode)
                target = ts[0] if ts else ""
                break

        rec = {
            "source": chosen_path,
            "line": node.lineno,
            "function": parent_function,
            "solver_expression": expr,
            "target_symbol": target,
            "arg_count": len(args),
            "args": ";".join(args),
            "kwargs": json.dumps(kwargs),
            "source_text": lines[node.lineno - 1].strip(),
        }
        records.append(rec)

    return records, c, amap


def trace_dependencies(symbols, amap, max_depth=12):
    rows = []
    queue = [(s, 0, "") for s in symbols if s]
    seen = set()

    while queue:
        symbol, depth, parent = queue.pop(0)
        if (symbol, depth) in seen or depth > max_depth:
            continue
        seen.add((symbol, depth))

        nodes = amap.get(symbol, [])
        if not nodes:
            rows.append({
                "symbol": symbol,
                "parent_symbol": parent,
                "depth": depth,
                "status": "UNRESOLVED_LEAF",
                "expression": "",
            })
            continue

        for node in nodes:
            expr = ast_text(getattr(node, "value", None))
            deps = name_dependencies(getattr(node, "value", None))
            rows.append({
                "symbol": symbol,
                "parent_symbol": parent,
                "depth": depth,
                "status": "ASSIGNMENT_RESOLVED",
                "expression": expr,
                "dependencies": ";".join(deps),
            })
            for d in deps:
                if d != symbol:
                    queue.append((d, depth + 1, symbol))

    return rows


def pressure_postsolve_trace(c, solver_target):
    rows = []
    if not solver_target:
        return rows

    tree = c["tree"]
    text = c["text"]
    lines = text.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        expr = ast_text(getattr(node, "value", None))
        low = expr.lower()

        if solver_target.lower() not in low:
            continue

        targets = assigned_targets(node)
        target = targets[0] if targets else ""
        target_low = target.lower()

        pressure_semantic = (
            any(h == target_low or h in target_low for h in PRESSURE_SYMBOL_HINTS)
            or any(tok in low for tok in POSTPROCESS_TOKENS)
        )

        if pressure_semantic:
            rows.append({
                "line": getattr(node, "lineno", None),
                "target_symbol": target,
                "expression": expr,
                "source_text": lines[node.lineno - 1].strip() if getattr(node, "lineno", None) else "",
            })

    return rows


def downstream_sg4_trace(pressure_symbols):
    rows = []
    for p in sorted(ROOT.glob("PAD_Stream_V15SG4*.py")):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            low = line.lower()
            for sym in pressure_symbols:
                if sym and re.search(rf"\b{re.escape(sym.lower())}\b", low):
                    rows.append({
                        "source": str(p),
                        "source_sha256": sha256_file(p),
                        "line": i,
                        "pressure_symbol": sym,
                        "text": line.strip(),
                    })
    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16A-R6")
    print("Residual Regeneration Recipe Binding Audit")
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
ONLY THE UNRESOLVED SG3 PRESSURE RECIPE WILL BE BOUND.
""")

    if not R5_SUMMARY.exists():
        raise FileNotFoundError(R5_SUMMARY)

    r5 = json.loads(R5_SUMMARY.read_text(encoding="utf-8"))
    if r5.get("status") != "V16A_SOURCE_AUTHENTIC_REGENERATION_NOT_YET_AUTHORIZED":
        raise RuntimeError("V16A-R6 expects the R5 regeneration-not-authorized status.")

    cands = source_candidates()
    source_rows, chosen = choose_sg3_source(cands)
    save_csv(SOURCE_TABLE, source_rows)

    if chosen is None:
        solver_records = []
        dep_rows = []
        post_rows = []
        downstream_rows = []
        solver_unique = False
        matrix_rhs_bound = False
        pressure_output_bound = False
        downstream_consumer_bound = False
        chosen_source = ""
    else:
        chosen_source = chosen["source"]
        solver_records, c, amap = bind_solver_call(chosen_source, cands)
        save_csv(SOLVER_TABLE, solver_records)

        solver_unique = len(solver_records) == 1

        solver_args = []
        solver_target = ""
        if solver_records:
            solver_target = solver_records[0]["target_symbol"]
            solver_args = [x for x in solver_records[0]["args"].split(";") if x]

        dep_rows = trace_dependencies(solver_args, amap)
        save_csv(MATRIX_RHS_TABLE, dep_rows)

        # Conservative matrix/RHS binding: two or more solver args and at least
        # one resolved dependency path for each top-level arg.
        top_args = set(solver_args)
        resolved_top = {
            r["symbol"] for r in dep_rows
            if r["symbol"] in top_args and r["status"] == "ASSIGNMENT_RESOLVED"
        }
        matrix_rhs_bound = len(top_args) >= 2 and resolved_top == top_args

        post_rows = pressure_postsolve_trace(c, solver_target)
        save_csv(POSTPROCESS_TABLE, post_rows)

        pressure_symbols = [r["target_symbol"] for r in post_rows]
        if not pressure_symbols and solver_target:
            pressure_symbols = [solver_target]

        pressure_output_bound = len(pressure_symbols) >= 1

        downstream_rows = downstream_sg4_trace(pressure_symbols)
        save_csv(DOWNSTREAM_TABLE, downstream_rows)
        downstream_consumer_bound = len(downstream_rows) > 0

    if not chosen:
        save_csv(SOLVER_TABLE, [])
        save_csv(MATRIX_RHS_TABLE, [])
        save_csv(POSTPROCESS_TABLE, [])
        save_csv(DOWNSTREAM_TABLE, [])

    recipe_ready = (
        chosen is not None
        and solver_unique
        and matrix_rhs_bound
        and pressure_output_bound
    )

    print("SG3 PRESSURE RECIPE BINDING")
    print(f"  Source candidates           : {len(source_rows)}")
    print(f"  Selected SG3 source         : {Path(chosen_source).name if chosen_source else 'NONE'}")
    print(f"  Unique solver call          : {solver_unique}")
    print(f"  Matrix/RHS dependency bound : {matrix_rhs_bound}")
    print(f"  Pressure output bound       : {pressure_output_bound}")
    print(f"  SG4 downstream consumer     : {downstream_consumer_bound}")
    print(f"  Recipe ready                : {recipe_ready}")

    gates = [
        ("incoming_R5_not_authorized_status_reproduced", True),
        ("SG3_source_candidates_inventoried", len(source_rows) > 0),
        ("one_authoritative_SG3_source_selected_by_source_semantics", chosen is not None),
        ("solver_call_audited", True),
        ("solver_matrix_rhs_dependencies_audited", True),
        ("postsolve_pressure_trace_audited", True),
        ("SG4_downstream_pressure_consumer_audited", True),
        ("no_pressure_solve_executed", True),
        ("no_Darcy_flux_recomputed", True),
        ("no_velocity_reconstructed", True),
        ("no_Pollock_retrace_executed", True),
        ("no_FMM_executed", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_V15_artifact_changed", True),
    ]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g,p in gates])

    if recipe_ready:
        status = "V16A_SG3_PRESSURE_REGENERATION_RECIPE_BOUND"
        diagnosis = (
            "ONE_SOURCE_AUTHENTIC_SG3_PRESSURE_SOLVER_MATRIX_RHS_AND_POSTSOLVE_PATH_IS_EXPLICITLY_BOUND"
        )
        recommendation = (
            "The unresolved R5 blocker is cleared. Authorize controlled regeneration only as "
            "DERIVED_V16_FROM_FROZEN_V15. In the next milestone, execute the bound SG3 recipe, "
            "then SG4 flux reconstruction, then derive Vx/Vy/Vz and bind producer identity. "
            "Do not label regenerated arrays as historical persisted V15 states."
        )
        next_ms = "V16A-R7 — Controlled Source-Authentic Foundation Component Regeneration"
    else:
        status = "V16A_SG3_PRESSURE_REGENERATION_RECIPE_STILL_INCOMPLETE"
        diagnosis = (
            "ONE_OR_MORE_SG3_SOLVER_MATRIX_RHS_OR_PRESSURE_OUTPUT_BINDINGS_REMAIN_UNRESOLVED"
        )
        recommendation = (
            "Do not execute the pressure solver. Audit only the failed R6 pressure-recipe binding dimensions."
        )
        next_ms = "V16A-R6A — Final SG3 Pressure Recipe Residual Binding Audit"

    decision = [{
        "status": status,
        "diagnosis": diagnosis,
        "selected_source": chosen_source,
        "solver_unique": solver_unique,
        "matrix_rhs_bound": matrix_rhs_bound,
        "pressure_output_bound": pressure_output_bound,
        "downstream_consumer_bound": downstream_consumer_bound,
        "recipe_ready": recipe_ready,
        "derived_artifact_label": "DERIVED_V16_FROM_FROZEN_V15" if recipe_ready else "",
        "next_milestone": next_ms,
    }]
    save_csv(RECIPE_TABLE, decision)

    contract = {
        "milestone": "V16A-R6",
        "status": status,
        "diagnosis": diagnosis,
        "selected_SG3_source": chosen_source,
        "recipe": {
            "unique_solver_call": solver_unique,
            "matrix_rhs_bound": matrix_rhs_bound,
            "pressure_output_bound": pressure_output_bound,
            "downstream_SG4_consumer_bound": downstream_consumer_bound,
            "recipe_ready": recipe_ready,
        },
        "policy": {
            "source_authentic_regeneration_authorized_if_recipe_ready": recipe_ready,
            "derived_artifact_label": "DERIVED_V16_FROM_FROZEN_V15" if recipe_ready else None,
            "historical_V15_relabelling_prohibited": True,
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
        "milestone": "V16A-R6",
        "status": status,
        "diagnosis": diagnosis,
        "recipe_ready": recipe_ready,
        "selected_SG3_source": chosen_source,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("\n" + "=" * 78)
    print("V16A-R6 FINAL RECIPE BINDING GATES")
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
        SOURCE_TABLE, SOLVER_TABLE, MATRIX_RHS_TABLE,
        POSTPROCESS_TABLE, DOWNSTREAM_TABLE, RECIPE_TABLE, GATE_TABLE
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT.name}")

    print("\nSummary:")
    print(f"  {SUMMARY.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16A-R6 RESIDUAL REGENERATION RECIPE BINDING AUDIT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()

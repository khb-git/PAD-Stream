from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import re
from collections import defaultdict, deque

import numpy as np


# =============================================================================
# PAD-Stream V16A-R3
# Deterministic Frozen Component Reconstruction Feasibility Audit
#
# PURPOSE
# -------
# R2 established that every required V16A component now has source/downstream
# lineage evidence. R3 determines whether each component can be recovered
# WITHOUT solving new physics.
#
# R3 DOES NOT reconstruct any array.
#
# It binds:
#   - exact source assignment / alias expression,
#   - source function in which the component is produced,
#   - direct dependencies,
#   - persisted immutable leaf inputs,
#   - downstream exact persisted copies where available,
#   - whether recovery is:
#
#       PERSISTED_COPY_AVAILABLE
#       DETERMINISTIC_ALGEBRAIC_RECONSTRUCTION_FEASIBLE
#       REQUIRES_NEW_PHYSICS_EXECUTION
#       REQUIRES_STREAMLINE_RETRACE
#       REQUIRES_UNRESOLVED_RUNTIME_STATE
#       UNRESOLVED
#
# Conservative rule:
#   Pressure solve execution, Darcy-flux recomputation from pressure, and
#   Pollock streamline tracing are considered NEW PHYSICS for V16A and are not
#   authorized by this audit unless an exact persisted copy already exists.
#
# NO TRAINING.
# NO MODEL.PREDICT.
# NO PRESSURE SOLVE.
# NO DARCY RE-SOLVE.
# NO POLLOCK RE-TRACE.
# NO FAST MARCHING.
# NO FROZEN V15 MUTATION.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_R3_RECONSTRUCTION_FEASIBILITY_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

R2_DIR = ROOT / "output" / "V16_A_R2_RESIDUAL_COMPONENT_LINEAGE_AUDIT"
R2_SUMMARY = R2_DIR / "PAD_Stream_V16AR2_Summary.json"
R2_SYMBOLS = R2_DIR / "V16AR2_Component_Symbol_Lineage.csv"
R2_PRESSURE = R2_DIR / "V16AR2_Pressure_Alias_Resolution.csv"
R2_PRODUCER = R2_DIR / "V16AR2_Producer_ID_Alias_Resolution.csv"

SOURCE_EXPR_TABLE = OUT / "V16AR3_Component_Source_Expression_Binding.csv"
DEPENDENCY_TABLE = OUT / "V16AR3_Component_Dependency_Graph.csv"
PERSISTED_TABLE = OUT / "V16AR3_Persisted_Copy_and_Leaf_Input_Audit.csv"
FEASIBILITY_TABLE = OUT / "V16AR3_Component_Reconstruction_Feasibility.csv"
GATE_TABLE = OUT / "V16AR3_Final_Feasibility_Gates.csv"
DECISION_TABLE = OUT / "V16AR3_Reconstruction_Feasibility_Decision.csv"
CONTRACT_FILE = OUT / "V16AR3_Deterministic_Reconstruction_Feasibility_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V16AR3_Summary.json"


COMPONENTS = [
    "Kx", "Ky", "Kz", "porosity", "pressure",
    "Qx", "Qy", "Qz", "Vx", "Vy", "Vz", "producer_id",
]

OWNER = {
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

ALIASES = {
    "Kx": {"kx", "perm_x", "permx", "k_x", "kx_md"},
    "Ky": {"ky", "perm_y", "permy", "k_y", "ky_md"},
    "Kz": {"kz", "perm_z", "permz", "k_z", "kz_md"},
    "porosity": {"phi", "poro", "porosity", "phi_grid"},
    "pressure": {
        "p", "pressure", "pressure_pa", "pressure_psi", "p_pa", "p_psi",
        "p3d", "p_grid", "pressure_grid", "solution", "pvec"
    },
    "Qx": {"qx", "q_x", "flux_x", "darcy_flux_x", "face_flux_x"},
    "Qy": {"qy", "q_y", "flux_y", "darcy_flux_y", "face_flux_y"},
    "Qz": {"qz", "q_z", "flux_z", "darcy_flux_z", "face_flux_z"},
    "Vx": {"vx", "v_x", "vel_x", "velocity_x", "pore_velocity_x"},
    "Vy": {"vy", "v_y", "vel_y", "velocity_y", "pore_velocity_y"},
    "Vz": {"vz", "v_z", "vel_z", "velocity_z", "pore_velocity_z"},
    "producer_id": {
        "producer_id", "producer_ids", "prod_id", "prod_ids",
        "terminal_producer", "capture_id", "producer_index", "producer_idx",
        "destination_id", "target_producer", "well_id", "well_index"
    },
}

EXPECTED_SHAPES = {
    "Kx": {(15, 50, 50)},
    "Ky": {(15, 50, 50)},
    "Kz": {(15, 50, 50)},
    "porosity": {(15, 50, 50)},
    "pressure": {(15, 50, 50)},
    "Qx": {(15, 50, 49)},
    "Qy": {(15, 49, 50)},
    "Qz": {(14, 50, 50)},
    "Vx": {(15, 50, 49)},
    "Vy": {(15, 49, 50)},
    "Vz": {(14, 50, 50)},
    "producer_id": {(1078,), (1078, 1)},
}

PHYSICS_CALL_TOKENS = {
    "pressure": [
        "spsolve", "cg(", "bicg", "gmres", "solve_pressure",
        "pressure_solve", "linear_solve"
    ],
    "flux": [
        "darcy", "face_flux", "compute_flux", "calculate_flux",
        "conservative_flux"
    ],
    "pollock": [
        "trace_streamline", "pollock", "trace_particle",
        "trace_all", "streamline_trace"
    ],
}


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


def milestone_tag(path: Path):
    s = (path.name + " " + str(path.parent)).upper()
    for i in range(1, 7):
        if f"V15SG{i}" in s or f"V15_SG{i}" in s:
            return f"SG{i}"
    return None


def source_files():
    rows = []
    for p in sorted(ROOT.glob("*.py")):
        tag = milestone_tag(p)
        if tag in {f"SG{i}" for i in range(1, 7)}:
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(text)
            except Exception:
                continue
            rows.append((tag, p, text, tree))
    return rows


def ast_unparse(node):
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def names_in_expr(node):
    out = set()
    if node is None:
        return out
    for x in ast.walk(node):
        if isinstance(x, ast.Name):
            out.add(x.id)
    return out


def assignment_targets(node):
    targets = []
    raw = []
    if isinstance(node, ast.Assign):
        raw = node.targets
    elif isinstance(node, ast.AnnAssign):
        raw = [node.target]
    else:
        return targets

    for t in raw:
        if isinstance(t, ast.Name):
            targets.append(t.id)
        elif isinstance(t, ast.Tuple):
            for e in t.elts:
                if isinstance(e, ast.Name):
                    targets.append(e.id)
    return targets


def enclosing_function(tree, lineno):
    best = ("<module>", -1)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            end = getattr(node, "end_lineno", node.lineno)
            if node.lineno <= lineno <= end and node.lineno > best[1]:
                best = (node.name, node.lineno)
    return best[0]


def bind_source_expressions(sources):
    rows = []
    dep_rows = []

    for owner, p, text, tree in sources:
        lines = text.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue

            targets = assignment_targets(node)
            value = getattr(node, "value", None)
            expr = ast_unparse(value)
            deps = sorted(names_in_expr(value))
            func = enclosing_function(tree, getattr(node, "lineno", 0))

            for target in targets:
                lt = target.lower()
                for comp in COMPONENTS:
                    if owner not in OWNER[comp]:
                        continue
                    aliases = {x.lower() for x in ALIASES[comp]}
                    if lt not in aliases:
                        continue

                    rec = {
                        "component": comp,
                        "owner": owner,
                        "source": str(p),
                        "source_sha256": sha256_file(p),
                        "function": func,
                        "line": getattr(node, "lineno", None),
                        "symbol": target,
                        "expression": expr,
                        "dependencies": ";".join(deps),
                    }
                    rows.append(rec)

                    for d in deps:
                        dep_rows.append({
                            "component": comp,
                            "owner": owner,
                            "source": str(p),
                            "function": func,
                            "target_symbol": target,
                            "dependency_symbol": d,
                            "line": getattr(node, "lineno", None),
                        })

    return rows, dep_rows


def semantic_key_match(component, key):
    k = key.lower()
    if component == "pressure":
        return any(t in k for t in ["pressure", "p_grid", "pressure_grid", "p_psi", "p_pa"])
    if component == "producer_id":
        return any(t in k for t in [
            "producer_id", "prod_id", "terminal_producer", "capture_id",
            "producer_idx", "producer_index", "destination_id", "target_producer"
        ])
    return k in {x.lower() for x in ALIASES[component]}


def persisted_copy_inventory():
    rows = []
    matches = defaultdict(list)
    outroot = ROOT / "output"

    if not outroot.exists():
        return rows, matches

    for p in sorted(outroot.rglob("*.npz")):
        lowp = str(p).lower()
        if "v16_" in lowp or "v16a" in lowp:
            continue
        try:
            with np.load(p, allow_pickle=False) as db:
                for key in db.files:
                    a = np.asarray(db[key])
                    if not np.issubdtype(a.dtype, np.number):
                        continue
                    if not np.all(np.isfinite(a)):
                        continue
                    for comp in COMPONENTS:
                        if tuple(a.shape) not in EXPECTED_SHAPES[comp]:
                            continue
                        if not semantic_key_match(comp, key):
                            continue

                        rec = {
                            "component": comp,
                            "artifact": str(p),
                            "artifact_sha256": sha256_file(p),
                            "key": key,
                            "shape": str(tuple(a.shape)),
                            "dtype": str(a.dtype),
                            "array_sha256": sha256_array(a),
                            "owner_tag": milestone_tag(p) or "",
                        }
                        rows.append(rec)
                        matches[comp].append(rec)
        except Exception:
            pass

    return rows, matches


def build_local_assignment_map(source_path, tree):
    amap = defaultdict(list)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            for t in assignment_targets(node):
                amap[t].append(node)
    return amap


def physics_signature(expr: str):
    low = expr.lower()
    if any(tok in low for tok in PHYSICS_CALL_TOKENS["pressure"]):
        return "PRESSURE_SOLVE"
    if any(tok in low for tok in PHYSICS_CALL_TOKENS["flux"]):
        return "DARCY_FLUX_PHYSICS"
    if any(tok in low for tok in PHYSICS_CALL_TOKENS["pollock"]):
        return "POLLOCK_TRACE"
    return ""


def dependency_closure(source_records, sources):
    """
    For each chosen source expression, recursively trace same-file assignments
    and classify whether the chain contains a physics execution call.
    """
    src_map = {str(p): (owner, p, text, tree) for owner, p, text, tree in sources}
    out = []

    for rec in source_records:
        source = rec["source"]
        if source not in src_map:
            continue
        owner, p, text, tree = src_map[source]
        amap = build_local_assignment_map(p, tree)

        roots = [x for x in rec["dependencies"].split(";") if x]
        q = deque((x, 0) for x in roots)
        seen = set()
        physics = set()
        unresolved = set()
        traced = 0

        while q:
            sym, depth = q.popleft()
            if sym in seen or depth > 12:
                continue
            seen.add(sym)

            nodes = amap.get(sym, [])
            if not nodes:
                unresolved.add(sym)
                continue

            traced += len(nodes)
            for node in nodes:
                expr = ast_unparse(getattr(node, "value", None))
                ps = physics_signature(expr)
                if ps:
                    physics.add(ps)
                for d in names_in_expr(getattr(node, "value", None)):
                    if d != sym:
                        q.append((d, depth + 1))

        out.append({
            "component": rec["component"],
            "owner": owner,
            "source": source,
            "symbol": rec["symbol"],
            "function": rec["function"],
            "physics_signatures": ";".join(sorted(physics)),
            "unresolved_leaf_symbols": ";".join(sorted(unresolved)),
            "resolved_assignment_records": traced,
        })

    return out


def choose_source_record(component, source_rows):
    candidates = [r for r in source_rows if r["component"] == component]
    if not candidates:
        return None

    # Prefer later owner stage within allowed component authority because it is
    # closest to the downstream state actually consumed by V15.
    owner_rank = {"SG1": 1, "SG2": 2, "SG3": 3, "SG4": 4, "SG5": 5, "SG6": 6}
    candidates.sort(
        key=lambda r: (
            -owner_rank.get(r["owner"], 0),
            0 if r["function"] != "<module>" else 1,
            int(r["line"] or 0),
        )
    )
    return candidates[0]


def classify(component, source_rec, closure_rec, persisted_matches):
    # Exact semantic persisted copy always wins and requires no reconstruction.
    hashes = {r["array_sha256"] for r in persisted_matches}
    if len(hashes) == 1 and persisted_matches:
        return "PERSISTED_COPY_AVAILABLE", "one unique semantic persisted numerical identity exists"

    if len(hashes) > 1:
        return "MULTIPLE_PERSISTED_IDENTITIES_REQUIRE_BINDING", "multiple semantic persisted numerical identities exist"

    if source_rec is None:
        return "UNRESOLVED", "no exact owner-scoped source expression bound"

    physics = set()
    unresolved = set()

    if closure_rec:
        physics = {x for x in closure_rec["physics_signatures"].split(";") if x}
        unresolved = {x for x in closure_rec["unresolved_leaf_symbols"].split(";") if x}

    if component == "pressure":
        if "PRESSURE_SOLVE" in physics or not persisted_matches:
            return "REQUIRES_NEW_PHYSICS_EXECUTION", "pressure is source-defined through solver/runtime lineage and no exact persisted copy is bound"

    if component in {"Qx", "Qy", "Qz"}:
        if "DARCY_FLUX_PHYSICS" in physics:
            return "REQUIRES_NEW_PHYSICS_EXECUTION", "flux source chain contains Darcy/face-flux physics execution"
        # Even algebraic Darcy recomputation from p is considered physics for V16A.
        return "REQUIRES_NEW_PHYSICS_EXECUTION", "face flux was not persisted and recomputing it would regenerate V15 physics"

    if component in {"Vx", "Vy", "Vz"}:
        # Velocity is normally a deterministic algebraic transformation of
        # frozen Q/phi/geometry, but only after Q is authoritative.
        return "DEPENDENT_ON_AUTHORITATIVE_FLUX_RECOVERY", "velocity may be algebraic, but its frozen flux parent must first be recovered authoritatively"

    if component == "producer_id":
        if "POLLOCK_TRACE" in physics:
            return "REQUIRES_STREAMLINE_RETRACE", "producer identity derives from streamline termination/capture execution"
        return "REQUIRES_UNRESOLVED_RUNTIME_STATE", "producer identity is not uniquely persisted and depends on termination/capture runtime state"

    if component in {"Kx", "Ky", "Kz", "porosity"}:
        # These may be deterministic transforms of the frozen SGSim property.
        if unresolved:
            return "DETERMINISTIC_ALGEBRAIC_RECONSTRUCTION_FEASIBLE_PENDING_LEAF_BINDING", "source expression is algebraic but one or more immutable leaves require exact binding"
        return "DETERMINISTIC_ALGEBRAIC_RECONSTRUCTION_FEASIBLE", "source expression has no detected physics execution"

    return "UNRESOLVED", "classification rule not reached"


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16A-R3")
    print("Deterministic Frozen Component Reconstruction Feasibility Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO ARRAY WILL BE RECONSTRUCTED.
NO PRESSURE SOLVE WILL BE EXECUTED.
NO DARCY FLUX WILL BE RECOMPUTED.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO FAST MARCHING WILL BE EXECUTED.
NO FROZEN V15 ARTIFACT WILL BE CHANGED.
""")

    if not R2_SUMMARY.exists():
        raise FileNotFoundError(R2_SUMMARY)

    r2 = json.loads(R2_SUMMARY.read_text(encoding="utf-8"))
    if r2.get("status") != "V16A_RESIDUAL_COMPONENT_LINEAGE_RESOLVED_FOR_RECONSTRUCTION_AUDIT":
        raise RuntimeError("V16A-R3 expects successful R2 lineage-resolution status.")

    sources = source_files()
    source_rows, dep_rows = bind_source_expressions(sources)
    save_csv(SOURCE_EXPR_TABLE, source_rows)
    save_csv(DEPENDENCY_TABLE, dep_rows)

    persisted_rows, persisted = persisted_copy_inventory()
    save_csv(PERSISTED_TABLE, persisted_rows)

    chosen_sources = {}
    for comp in COMPONENTS:
        chosen_sources[comp] = choose_source_record(comp, source_rows)

    chosen_list = [x for x in chosen_sources.values() if x is not None]
    closure_rows = dependency_closure(chosen_list, sources)
    closure_by = {r["component"]: r for r in closure_rows}

    feasibility = []
    for comp in COMPONENTS:
        srec = chosen_sources.get(comp)
        crec = closure_by.get(comp)
        pmatches = persisted.get(comp, [])

        status, reason = classify(comp, srec, crec, pmatches)

        feasibility.append({
            "component": comp,
            "source_bound": srec is not None,
            "source_owner": srec["owner"] if srec else "",
            "source_file": srec["source"] if srec else "",
            "source_symbol": srec["symbol"] if srec else "",
            "source_expression": srec["expression"] if srec else "",
            "persisted_semantic_candidates": len(pmatches),
            "persisted_distinct_hashes": len({r["array_sha256"] for r in pmatches}),
            "physics_signatures": crec["physics_signatures"] if crec else "",
            "unresolved_leaf_symbols": crec["unresolved_leaf_symbols"] if crec else "",
            "reconstruction_class": status,
            "reason": reason,
        })

    save_csv(FEASIBILITY_TABLE, feasibility)

    print("RECONSTRUCTION FEASIBILITY")
    for r in feasibility:
        print(
            f"  {r['component']:<18} | {r['reconstruction_class']:<58} | "
            f"persisted={r['persisted_semantic_candidates']:<3} | "
            f"owner={r['source_owner'] or 'NONE'}"
        )

    no_new_physics_components = [
        r for r in feasibility
        if r["reconstruction_class"] in {
            "PERSISTED_COPY_AVAILABLE",
            "DETERMINISTIC_ALGEBRAIC_RECONSTRUCTION_FEASIBLE",
            "DETERMINISTIC_ALGEBRAIC_RECONSTRUCTION_FEASIBLE_PENDING_LEAF_BINDING",
        }
    ]
    blocked_components = [
        r for r in feasibility
        if r["reconstruction_class"] in {
            "REQUIRES_NEW_PHYSICS_EXECUTION",
            "REQUIRES_STREAMLINE_RETRACE",
            "REQUIRES_UNRESOLVED_RUNTIME_STATE",
            "MULTIPLE_PERSISTED_IDENTITIES_REQUIRE_BINDING",
            "UNRESOLVED",
            "DEPENDENT_ON_AUTHORITATIVE_FLUX_RECOVERY",
        }
    ]

    gates = [
        ("incoming_R2_status_reproduced", True),
        ("owner_scoped_source_expressions_bound", len(source_rows) > 0),
        ("dependency_graph_constructed", len(dep_rows) > 0),
        ("persisted_semantic_copy_inventory_completed", True),
        ("pressure_reconstruction_feasibility_classified", any(r["component"] == "pressure" for r in feasibility)),
        ("flux_reconstruction_feasibility_classified", all(any(r["component"] == c for r in feasibility) for c in ["Qx","Qy","Qz"])),
        ("velocity_reconstruction_feasibility_classified", all(any(r["component"] == c for r in feasibility) for c in ["Vx","Vy","Vz"])),
        ("producer_id_reconstruction_feasibility_classified", any(r["component"] == "producer_id" for r in feasibility)),
        ("no_array_reconstructed", True),
        ("no_pressure_solve_executed", True),
        ("no_Darcy_flux_recomputed", True),
        ("no_Pollock_retrace_executed", True),
        ("no_FMM_executed", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_V15_artifact_changed", True),
    ]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g,p in gates])

    # Branch decision.
    if not blocked_components:
        status = "V16A_ALL_COMPONENTS_RECOVERABLE_WITHOUT_NEW_PHYSICS"
        diagnosis = "ALL_FOUNDATION_COMPONENTS_HAVE_PERSISTED_OR_DETERMINISTIC_NONPHYSICS_RECOVERY_PATHS"
        recommendation = (
            "Proceed to repaired Foundation Case 0001 extraction using only persisted copies and exact deterministic algebraic reconstruction."
        )
        next_ms = "V16A-R4 — Repaired Foundation Case 0001 Extraction"
    else:
        # Most likely / scientifically expected outcome: geology can be
        # reconstructed algebraically, but pressure/Q/producer identity require
        # recovering an existing persisted authoritative artifact rather than
        # re-solving V15 physics.
        status = "V16A_FOUNDATION_EXTRACTION_REQUIRES_ADDITIONAL_PERSISTED_AUTHORITY_RECOVERY"
        diagnosis = "ONE_OR_MORE_REQUIRED_COMPONENTS_CANNOT_BE_RECONSTRUCTED_WITHOUT_REEXECUTING_FROZEN_V15_PHYSICS_OR_RUNTIME_STATE"
        recommendation = (
            "Do not rerun V15 physics yet. Recover exact persisted downstream copies or frozen serialized parents for the blocked components. "
            "Prioritize pressure, Qx/Qy/Qz, and producer_id; velocity can then be resolved from authoritative flux lineage if no exact persisted copy exists."
        )
        next_ms = "V16A-R4 — Persisted Pressure / Flux / Producer Authority Recovery Audit"

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "recoverable_without_new_physics_count": len(no_new_physics_components),
        "blocked_component_count": len(blocked_components),
        "blocked_components": ";".join(r["component"] for r in blocked_components),
        "next_milestone": next_ms,
    }])

    contract = {
        "milestone": "V16A-R3",
        "status": status,
        "diagnosis": diagnosis,
        "component_feasibility": feasibility,
        "recoverable_without_new_physics": [r["component"] for r in no_new_physics_components],
        "blocked_components": [r["component"] for r in blocked_components],
        "constraints": {
            "array_reconstructed": False,
            "pressure_solve_executed": False,
            "Darcy_flux_recomputed": False,
            "Pollock_retrace_executed": False,
            "FMM_executed": False,
            "model_predict_executed": False,
            "training_performed": False,
            "V15_artifact_changed": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT_FILE, contract)

    save_json(SUMMARY_FILE, {
        "milestone": "V16A-R3",
        "status": status,
        "diagnosis": diagnosis,
        "recoverable_without_new_physics": contract["recoverable_without_new_physics"],
        "blocked_components": contract["blocked_components"],
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("\nSUMMARY")
    print(f"  Recoverable without new physics : {len(no_new_physics_components)}")
    print(f"  Blocked components              : {len(blocked_components)}")
    if blocked_components:
        print("  Blocked                         : " + ", ".join(r["component"] for r in blocked_components))

    print("\n" + "=" * 78)
    print("V16A-R3 FINAL FEASIBILITY GATES")
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
        SOURCE_EXPR_TABLE,
        DEPENDENCY_TABLE,
        PERSISTED_TABLE,
        FEASIBILITY_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16A-R3 RECONSTRUCTION FEASIBILITY AUDIT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()

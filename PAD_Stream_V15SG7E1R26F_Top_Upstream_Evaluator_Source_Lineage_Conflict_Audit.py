from __future__ import annotations
from pathlib import Path
import ast, csv, json, hashlib

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26F"
OUT.mkdir(parents=True, exist_ok=True)

R26E = ROOT / "output" / "V15_SG7E1R26E"
R18 = ROOT / "output" / "V15_SG7E1R18"

SUMMARY_IN = R26E / "PAD_Stream_V15SG7E1R26E_Summary.json"
CROSSWALK = R26E / "V15SG7E1R26E_R18_Trace_to_Project_Source_Crosswalk.csv"
MODEL_ID = R18 / "V15SG7E1R18_Frozen_Model_Identity.csv"

TOP_TABLE = OUT / "V15SG7E1R26F_Top_Runtime_Source_Candidates.csv"
LINEAGE_TABLE = OUT / "V15SG7E1R26F_Model_Checkpoint_Lineage.csv"
ROLE_TABLE = OUT / "V15SG7E1R26F_Source_Runtime_Role.csv"
FUNCTION_TABLE = OUT / "V15SG7E1R26F_Function_Lineage.csv"
SCORING_TABLE = OUT / "V15SG7E1R26F_Lineage_Resolution_Scoring.csv"
DECISION_TABLE = OUT / "V15SG7E1R26F_Upstream_Evaluator_Lineage_Decision.csv"
CONTRACT = OUT / "V15SG7E1R26F_Top_Upstream_Evaluator_Lineage_Contract.json"
SUMMARY = OUT / "PAD_Stream_V15SG7E1R26F_Summary.json"


def read_json(p):
    return json.loads(p.read_text(encoding="utf-8"))


def read_csv(p):
    if not p.exists():
        return []
    with p.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(p, rows):
    if not rows:
        p.write_text("", encoding="utf-8")
        return
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_json(p, obj):
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")


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


def src_text(p):
    return p.read_text(encoding="utf-8", errors="ignore")


def classify(path, text):
    low = text.lower()
    fit = low.count(".fit(") + low.count("train_on_batch")
    pred = low.count(".predict(") + low.count("predict_on_batch")
    load = low.count("load_model")
    save = low.count(".save(") + low.count("save_weights")
    time = low.count("time_days") + low.count("t_days") + low.count("physical_time")
    xi = low.count("xi")
    tau = low.count("tau") + low.count("tof")

    lname = path.name.lower()
    if fit > 0 or "training" in lname or "finetuning" in lname:
        role = "TRAINING_OR_FINETUNING"
    elif "validation" in lname or "audit" in lname:
        role = "VALIDATION_OR_AUDIT"
    elif "refinement" in lname or "calibration" in lname:
        role = "REFINEMENT_OR_CALIBRATION"
    elif pred > 0 and fit == 0:
        role = "NO_TRAINING_RUNTIME_INFERENCE"
    else:
        role = "UNRESOLVED"

    return role, fit, pred, load, save, time, xi, tau


def function_audit(path, text):
    rows = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return rows

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        pred = fit = load = time = xi = tau = ret = 0
        for sub in ast.walk(node):
            seg = ast.get_source_segment(text, sub) or ""
            low = seg.lower()
            if isinstance(sub, ast.Call):
                cname = call_name(sub).lower()
                if ".predict" in cname or "predict_on_batch" in cname:
                    pred += 1
                if ".fit" in cname or "train_on_batch" in cname:
                    fit += 1
                if "load_model" in cname:
                    load += 1
            if isinstance(sub, ast.Return):
                ret += 1
            if "time_days" in low or "t_days" in low or "physical_time" in low:
                time += 1
            if "xi" in low:
                xi += 1
            if "tau" in low or "tof" in low:
                tau += 1

        score = 200*pred + 60*load + 4*min(time,10) + 3*min(xi,10) + 3*min(tau,10) + 30*(ret>0) - 500*fit
        if node.name == "main":
            score -= 20

        rows.append({
            "source": str(path),
            "function": node.name,
            "line": node.lineno,
            "parameters": ";".join(a.arg for a in node.args.args),
            "predict_calls": pred,
            "fit_calls": fit,
            "load_model_calls": load,
            "time_mentions": time,
            "xi_mentions": xi,
            "tau_tof_mentions": tau,
            "return_count": ret,
            "function_score": score,
        })
    return rows


def main():
    print("\n" + "="*78)
    print("PAD-Stream Version 15-SG7E1R26F")
    print("Top Upstream Evaluator Source Lineage Conflict Audit")
    print("="*78)
    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO GAMMA OR CROSSING GUARD WILL BE RECALIBRATED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO SG7E PERFORMANCE GATE WILL BE EVALUATED.
""")

    s = read_json(SUMMARY_IN)
    if s.get("status") != "TRUE_UPSTREAM_RUNTIME_SOURCE_CONFLICT_REMAINS":
        raise RuntimeError("R26F requires R26E runtime-source conflict status.")

    model_rows = read_csv(MODEL_ID)
    if len(model_rows) != 1:
        raise RuntimeError("Expected one authoritative model record.")
    model_path = Path(model_rows[0]["path"])
    model_name = model_path.name
    model_sha = model_rows[0]["sha256"]

    cross = read_csv(CROSSWALK)
    top = []
    for r in cross:
        if str(r.get("is_R18_meta_program","")).lower() in {"true","1"}:
            continue
        if int(float(r.get("runtime_call_count",0) or 0)) <= 0:
            continue
        top.append(r)
        if len(top) >= 12:
            break
    write_csv(TOP_TABLE, top)

    lineage_rows = []
    role_rows = []
    function_rows = []
    scoring = []

    for rank, r in enumerate(top, 1):
        p = Path(r["source"])
        if not p.exists():
            continue
        text = src_text(p)
        role, fit, pred, load, save, time, xi, tau = classify(p, text)
        model_ref = model_name.lower() in text.lower()
        sha_ref = model_sha.lower() in text.lower()

        lineage_rows.append({
            "source": str(p),
            "exact_model_filename_match": model_ref,
            "exact_model_sha_match": sha_ref,
            "fit_count": fit,
            "predict_count": pred,
            "load_model_count": load,
            "save_model_count": save,
            "time_mentions": time,
            "xi_mentions": xi,
            "tau_tof_mentions": tau,
        })
        role_rows.append({
            "source": str(p),
            "role": role,
            "creates_or_trains_model": fit > 0,
            "consumes_model_for_inference": pred > 0 and fit == 0,
        })
        function_rows.extend(function_audit(p, text))

        score = 0
        reasons = []
        if model_ref:
            score += 500; reasons.append("exact_model_filename_reference")
        if sha_ref:
            score += 1000; reasons.append("exact_model_sha_reference")
        if load:
            score += 120; reasons.append("loads_model")
        if pred:
            score += 120; reasons.append("runtime_predict")
        if fit == 0:
            score += 150; reasons.append("no_training_call")
        else:
            score -= 700; reasons.append("contains_training_call")
        if role == "NO_TRAINING_RUNTIME_INFERENCE":
            score += 250; reasons.append("runtime_inference_role")
        if role == "REFINEMENT_OR_CALIBRATION":
            score += 80; reasons.append("refinement_lineage")
        if role == "TRAINING_OR_FINETUNING":
            score -= 600; reasons.append("training_role")
        if time or xi or tau:
            score += 80; reasons.append("time_xi_tau_semantics")
        score += min(int(float(r.get("crosswalk_score",0) or 0))//10, 150)
        reasons.append("R26E_crosswalk_support")

        scoring.append({
            "rank_R26E": rank,
            "source": str(p),
            "source_role": role,
            "exact_model_filename_match": model_ref,
            "exact_model_sha_match": sha_ref,
            "load_model_count": load,
            "predict_count": pred,
            "fit_count": fit,
            "R26E_crosswalk_score": int(float(r.get("crosswalk_score",0) or 0)),
            "lineage_score": score,
            "reasons": ";".join(reasons),
        })

    write_csv(LINEAGE_TABLE, lineage_rows)
    write_csv(ROLE_TABLE, role_rows)
    write_csv(FUNCTION_TABLE, function_rows)

    scoring.sort(key=lambda x: int(x["lineage_score"]), reverse=True)
    write_csv(SCORING_TABLE, scoring)

    eligible = [r for r in scoring if int(r["predict_count"]) > 0 and int(r["fit_count"]) == 0 and r["source_role"] != "TRAINING_OR_FINETUNING"]

    selected_source = None
    margin = 0
    if eligible:
        top1 = eligible[0]
        second = int(eligible[1]["lineage_score"]) if len(eligible) > 1 else -999
        margin = int(top1["lineage_score"]) - second
        if top1["exact_model_filename_match"] or top1["exact_model_sha_match"] or len(eligible) == 1 or margin >= 100:
            selected_source = top1

    selected_function = None
    fmargin = 0
    if selected_source:
        fs = [r for r in function_rows if r["source"] == selected_source["source"] and int(r["predict_calls"]) > 0 and int(r["fit_calls"]) == 0]
        fs.sort(key=lambda r: int(r["function_score"]), reverse=True)
        if fs:
            second = int(fs[1]["function_score"]) if len(fs) > 1 else -999
            fmargin = int(fs[0]["function_score"]) - second
            if len(fs) == 1 or fmargin >= 30:
                selected_function = fs[0]

    if selected_source and selected_function:
        status = "UPSTREAM_EVALUATOR_LINEAGE_RESOLVED"
        diagnosis = "FROZEN_MODEL_CONSUMPTION_AND_NO_TRAINING_RUNTIME_LINEAGE_IDENTIFY_ONE_EVALUATOR_SOURCE_FUNCTION"
        rec = "One no-training runtime source/function is resolved by checkpoint/model lineage. Bind its exact inputs, physical-time transform, output shape, and postprocessing before executing the 100-day control."
        nxt = "V15-SG7E1R26G — Resolved Evaluator Input / Output Contract Audit"
    else:
        status = "UPSTREAM_EVALUATOR_LINEAGE_CONFLICT_REMAINS"
        diagnosis = "TOP_RUNTIME_SOURCES_REMAIN_TIED_AFTER_MODEL_AND_NO_TRAINING_LINEAGE_AUDIT"
        rec = "Do not generate later-time states. Audit only the top two lineage candidates using exact checkpoint parent-manifest and saved-array consumer provenance."
        nxt = "V15-SG7E1R26G — Final Evaluator Parent-Manifest / Consumer Conflict Audit"

    write_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "eligible_no_training_runtime_sources": len(eligible),
        "selected_source": selected_source["source"] if selected_source else "",
        "selected_source_score": selected_source["lineage_score"] if selected_source else "",
        "source_margin": margin,
        "selected_function": selected_function["function"] if selected_function else "",
        "selected_function_score": selected_function["function_score"] if selected_function else "",
        "function_margin": fmargin,
        "next_milestone": nxt,
    }])

    write_json(CONTRACT, {
        "milestone": "V15-SG7E1R26F",
        "status": status,
        "diagnosis": diagnosis,
        "authoritative_model": {"path": str(model_path), "filename": model_name, "sha256": model_sha},
        "resolved_evaluator": {
            "resolved": bool(selected_source and selected_function),
            "source": selected_source["source"] if selected_source else None,
            "source_margin": margin,
            "function": selected_function["function"] if selected_function else None,
            "function_margin": fmargin,
        },
        "constraints": {
            "training_performed": False,
            "model_parameters_changed": False,
            "gamma_changed": False,
            "guard_changed": False,
            "threshold_changed": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
            "candidate_performance_used": False,
        },
        "recommendation": rec,
        "next_milestone": nxt,
    })

    write_json(SUMMARY, {
        "milestone": "V15-SG7E1R26F",
        "status": status,
        "diagnosis": diagnosis,
        "selected_upstream_source": selected_source["source"] if selected_source else None,
        "selected_upstream_function": selected_function["function"] if selected_function else None,
        "recommendation": rec,
        "next_milestone": nxt,
    })

    print("AUTHORITATIVE FROZEN MODEL")
    print(f"  File                    : {model_name}")
    print(f"  SHA-256                 : {model_sha}")

    print("\nTOP LINEAGE CANDIDATES")
    for r in scoring[:12]:
        print(
            f"  score={int(r['lineage_score']):5d} | "
            f"role={r['source_role']:<28s} | "
            f"load={int(r['load_model_count']):2d} | "
            f"pred={int(r['predict_count']):2d} | "
            f"fit={int(r['fit_count']):2d} | "
            f"modelRef={r['exact_model_filename_match']} | "
            f"{Path(r['source']).name}"
        )

    if selected_source:
        print("\nSELECTED SOURCE")
        print(f"  Source                  : {selected_source['source']}")
        print(f"  Lineage score / margin  : {selected_source['lineage_score']} / {margin}")
    if selected_function:
        print("\nSELECTED FUNCTION")
        print(f"  Function                : {selected_function['function']}")
        print(f"  Function score / margin : {selected_function['function_score']} / {fmargin}")

    print("\nSTATUS")
    print(f"  {status}")
    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")
    print("\nRECOMMENDATION")
    print(f"  {rec}")
    print("\nNEXT MILESTONE")
    print(f"  {nxt}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")
    for p in (TOP_TABLE, LINEAGE_TABLE, ROLE_TABLE, FUNCTION_TABLE, SCORING_TABLE, DECISION_TABLE):
        print(f"  {p.name}")
    print(f"\nContract:\n  {CONTRACT.name}")
    print(f"\nSummary:\n  {SUMMARY.name}")

    print("\n" + "="*78)
    print("V15-SG7E1R26F TOP UPSTREAM EVALUATOR SOURCE LINEAGE CONFLICT AUDIT: COMPLETE")
    print("="*78)


if __name__ == "__main__":
    main()

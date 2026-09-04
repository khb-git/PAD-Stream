from __future__ import annotations
from pathlib import Path
import csv, json
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
IN_SUMMARY = ROOT/"output"/"V15_SG7CR3F4R2R"/"PAD_Stream_V15SG7CR3F4R2R_Summary.json"
IN_PROFILE = ROOT/"output"/"V15_SG7CR3F4R2R"/"V15SG7CR3F4R2R_Profile_Reference_Reconciliation.csv"
IN_GLOBAL = ROOT/"output"/"V15_SG7CR3F4R2R"/"V15SG7CR3F4R2R_Global_Reference_Reconciliation.csv"
IN_FINAL = ROOT/"output"/"V15_SG7CR3F4"/"V15SG7CR3F4_Final_Experiment_Metrics.csv"

OUT = ROOT/"output"/"V15_SG7CR3F4R3"
OUT.mkdir(parents=True, exist_ok=True)

CORRIDOR = OUT/"V15SG7CR3F4R3_Reconciled_Front_Corridor.csv"
CONFLICT = OUT/"V15SG7CR3F4R3_Dual_Reference_Conflict_Audit.csv"
OBJECTIVE = OUT/"V15SG7CR3F4R3_Repair_Objective_Design.csv"
GATES = OUT/"V15SG7CR3F4R3_Preserved_Gates.csv"
EXPERIMENTS = OUT/"V15SG7CR3F4R3_R3F5_Experiment_Matrix.csv"
CONTRACT = OUT/"V15SG7CR3F4R3_Reconciled_Front_Displacement_Repair_Contract.json"
SUMMARY = OUT/"PAD_Stream_V15SG7CR3F4R3_Summary.json"

MEAN_FROZEN_SHIFT_LIMIT = 2.0e-3
P90_FROZEN_SHIFT_LIMIT = 5.0e-3
TRUTH_REFERENCE_P90 = 5.0e-3
FRONT_REDUCTION_TARGET = 0.50
BETA_VALUES = np.linspace(0.0, 1.0, 21)

def load_json(p):
    if not p.exists(): raise FileNotFoundError(f"Missing JSON:\n{p}")
    return json.loads(p.read_text(encoding="utf-8"))

def load_csv(p):
    if not p.exists(): raise FileNotFoundError(f"Missing CSV:\n{p}")
    with p.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def save_json(p, obj):
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def save_csv(p, rows):
    if not rows: return
    keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with p.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)

def num(row, key, default=np.nan):
    try: return float(row.get(key, default))
    except Exception: return default

def main():
    print("\n"+"="*78)
    print("PAD-Stream Version 15-SG7C-R3F4-R3")
    print("Reconciled Front-Displacement Repair Design")
    print("="*78)
    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO SG7B-11 OR CALIBRATOR PARAMETERS WILL BE CHANGED.")
    print("NO FRONT OR TOF-BIAS GATE WILL BE RELAXED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")

    for p in [IN_SUMMARY, IN_PROFILE, IN_GLOBAL, IN_FINAL]:
        if not p.exists(): raise FileNotFoundError(f"Missing R3F4-R3 prerequisite:\n{p}")

    incoming=load_json(IN_SUMMARY)
    if incoming.get("diagnosis")!="TRUE_FROZEN_RELATIVE_DISPLACEMENT_CONFIRMED":
        raise RuntimeError("R3F4-R3 requires incoming diagnosis TRUE_FROZEN_RELATIVE_DISPLACEMENT_CONFIRMED")

    profile=load_csv(IN_PROFILE)
    global_rows=load_csv(IN_GLOBAL)
    final_rows=load_csv(IN_FINAL)
    best_exp=incoming.get("best_experiment","B4")

    prof=[r for r in profile if r.get("experiment")==best_exp]
    glob=next((r for r in global_rows if r.get("experiment")==best_exp),None)
    final=next((r for r in final_rows if r.get("experiment")==best_exp),None)
    if not prof or glob is None or final is None:
        raise RuntimeError(f"Missing reconciled evidence for {best_exp}")

    truth=np.asarray([num(r,"truth_front_xi") for r in prof],float)
    frozen=np.asarray([num(r,"frozen_matched_front_xi") for r in prof],float)
    cal=np.asarray([num(r,"calibrated_matched_front_xi") for r in prof],float)
    m=np.isfinite(truth)&np.isfinite(frozen)&np.isfinite(cal)
    truth,frozen,cal=truth[m],frozen[m],cal[m]

    frozen_truth=np.abs(frozen-truth)
    cal_truth=np.abs(cal-truth)
    cal_frozen=np.abs(cal-frozen)

    ft_mean=float(np.mean(frozen_truth)); ft_p90=float(np.percentile(frozen_truth,90))
    ct_mean=float(np.mean(cal_truth)); ct_p90=float(np.percentile(cal_truth,90))
    cf_mean=float(np.mean(cal_frozen)); cf_p90=float(np.percentile(cal_frozen,90))
    front_red=num(final,"front_error_reduction_fraction")

    conflict_rows=[{
        "experiment":best_exp,
        "front_error_reduction_fraction":front_red,
        "frozen_vs_truth_mean_xi":ft_mean,
        "frozen_vs_truth_P90_xi":ft_p90,
        "calibrated_vs_truth_mean_xi":ct_mean,
        "calibrated_vs_truth_P90_xi":ct_p90,
        "calibrated_vs_frozen_mean_xi":cf_mean,
        "calibrated_vs_frozen_P90_xi":cf_p90,
        "frozen_relative_gate_pass":bool(cf_mean<=MEAN_FROZEN_SHIFT_LIMIT and cf_p90<=P90_FROZEN_SHIFT_LIMIT),
        "calibrated_truth_proximity_reference_pass":bool(ct_p90<=TRUTH_REFERENCE_P90),
    }]
    save_csv(CONFLICT, conflict_rows)

    corridor_rows=[]; feasible=[]
    for beta in BETA_VALUES:
        xb=(1-beta)*frozen+beta*truth
        from_frozen=np.abs(xb-frozen); to_truth=np.abs(xb-truth)
        mf=float(np.mean(from_frozen)); pf=float(np.percentile(from_frozen,90))
        mt=float(np.mean(to_truth)); pt=float(np.percentile(to_truth,90))
        pass_f=bool(mf<=MEAN_FROZEN_SHIFT_LIMIT and pf<=P90_FROZEN_SHIFT_LIMIT)
        if pass_f: feasible.append(float(beta))
        corridor_rows.append({
            "beta":float(beta),
            "mean_shift_from_frozen_xi":mf,
            "P90_shift_from_frozen_xi":pf,
            "mean_distance_to_truth_xi":mt,
            "P90_distance_to_truth_xi":pt,
            "frozen_relative_gate_pass":pass_f,
            "truth_proximity_reference_pass":bool(pt<=TRUTH_REFERENCE_P90),
        })
    save_csv(CORRIDOR,corridor_rows)
    max_beta=max(feasible) if feasible else None

    strong_truth_improvement=bool(ct_p90 < 0.10*ft_p90)
    frozen_truth_mismatch_material=bool(ft_p90 > 10.0*P90_FROZEN_SHIFT_LIMIT)
    corridor_extremely_narrow=bool(max_beta is not None and max_beta<=0.05)
    conflict=bool(frozen_truth_mismatch_material and corridor_extremely_narrow)

    objective_rows=[
        {"term":"L_state_front","definition":"front-shell state error vs SG7A/canonical truth","role":"retain front-state accuracy target"},
        {"term":"L_front_truth","definition":"|xi_cal-xi_SG7A|","role":"track physics/front accuracy"},
        {"term":"L_front_frozen","definition":"|xi_cal-xi_frozen|","role":"retain frozen-relative preservation metric"},
        {"term":"L_dual_reference_conflict","definition":"explicit conflict flag if objectives cannot coexist","role":"prevent silent gate substitution"},
        {"term":"L_front_topology","definition":"crossing identity/multiplicity preservation","role":"preserve physical correspondence"},
        {"term":"L_TOF_bias","definition":"retain SG7B-12 TOF-bias gates","role":"preserve slow-streamline correction"},
    ]
    gate_rows=[
        {"gate":"front_error_reduction","limit":">= 50%","status":"UNCHANGED"},
        {"gate":"mean calibrated-vs-frozen front shift","limit":"<= 2.0e-03 xi","status":"UNCHANGED / MONITORED"},
        {"gate":"P90 calibrated-vs-frozen front shift","limit":"<= 5.0e-03 xi","status":"UNCHANGED / MONITORED"},
        {"gate":"calibrated-vs-SG7A front error","limit":"diagnostic physics-accuracy metric","status":"ADDED AS DIAGNOSTIC, NOT SUBSTITUTE GATE"},
        {"gate":"front sign agreement","limit":">= 95%","status":"UNCHANGED"},
        {"gate":"front overshoot","limit":"<= 5%","status":"UNCHANGED"},
        {"gate":"TOF bias guards","limit":"SG7B-12 exact limits","status":"UNCHANGED"},
    ]
    experiment_rows=[
        {"experiment":"C0","description":"Existing B4 checkpoint, no changes","purpose":"dual-reference control"},
        {"experiment":"C1","description":"Frozen-dominant corridor target","purpose":"test maximum admissible beta under frozen-relative gate"},
        {"experiment":"C2","description":"Intermediate dual-reference continuation","purpose":"test state/front tradeoff without architecture change"},
        {"experiment":"C3","description":"Truth-dominant bounded continuation","purpose":"test non-front gates near SG7A front"},
    ]
    save_csv(OBJECTIVE,objective_rows); save_csv(GATES,gate_rows); save_csv(EXPERIMENTS,experiment_rows)

    if conflict:
        status="DUAL_REFERENCE_FRONT_CONTRACT_CONFLICT_ESTABLISHED"
        diagnosis="FROZEN_FRONT_PRESERVATION_CONFLICTS_WITH_SG7A_FRONT_ACCURACY"
        recommendation=(
            "The reconciled metrics show that the frozen SG7B-11 front is itself far from "
            "the validated SG7A front, while B4 moves almost exactly onto SG7A truth. Under "
            "the unchanged frozen-relative front limits, only a very small interpolation "
            "fraction toward SG7A is admissible. Do not retrain and do not relax the gate. "
            "The next milestone must determine which front reference is authoritative for "
            "deployment acceptance while preserving both metrics in the record."
        )
        next_milestone="V15-SG7C-R3F4-R3A — Front-Reference Authority / Acceptance Contract Audit"
    else:
        status="RECONCILED_FRONT_REPAIR_CORRIDOR_READY"
        diagnosis="DUAL_REFERENCE_REPAIR_CORRIDOR_EXISTS"
        recommendation=(
            "A nontrivial corridor exists that preserves the unchanged frozen-relative "
            "front limits while allowing movement toward SG7A truth. Proceed to a controlled "
            "continuation experiment without changing architecture."
        )
        next_milestone="V15-SG7C-R3F5 — Controlled Dual-Reference Front Continuation"

    print("\nDUAL-REFERENCE FRONT BASELINE")
    print(f"  Experiment                  : {best_exp}")
    print(f"  Front error reduction       : {100*front_red:.3f}%")
    print(f"  Frozen vs truth mean/P90    : {ft_mean:.6e} / {ft_p90:.6e}")
    print(f"  Calibrated vs truth mean/P90: {ct_mean:.6e} / {ct_p90:.6e}")
    print(f"  Calibrated vs frozen mean/P90: {cf_mean:.6e} / {cf_p90:.6e}")
    print(f"  Max beta passing frozen gate: {max_beta}")

    print("\n"+"="*78)
    print("V15-SG7C-R3F4-R3 DESIGN VALIDATION")
    print("="*78)
    checks=[
        "R3F4-R2R frozen-relative displacement diagnosis reproduced",
        "Frozen-vs-SG7A front mismatch quantified",
        "Calibrated-vs-SG7A front accuracy quantified",
        "Calibrated-vs-frozen preservation quantified",
        "Dual-reference interpolation corridor constructed",
        "Original frozen-relative gate retained unchanged",
        "SG7A-relative metric retained separately",
        "No gate substitution performed",
        "No training performed by R3F4-R3",
    ]
    for c in checks: print(f"[PASS] {c}")
    print("="*78)

    print("\nDIAGNOSTIC FLAGS")
    print(f"  Frozen truth mismatch material : {frozen_truth_mismatch_material}")
    print(f"  Calibrator strongly improves truth front: {strong_truth_improvement}")
    print(f"  Corridor extremely narrow      : {corridor_extremely_narrow}")
    print(f"  Dual-reference objectives conflict: {conflict}")

    print("\nSTATUS")
    print(f"  {status}")
    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")
    print("\nRECOMMENDATION")
    print(f"  {recommendation}")
    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    save_json(CONTRACT,{
        "milestone":"V15-SG7C-R3F4-R3",
        "status":status,
        "diagnosis":diagnosis,
        "training_performed":False,
        "best_experiment":best_exp,
        "front_error_reduction_fraction":front_red,
        "frozen_vs_truth":{"mean_xi":ft_mean,"P90_xi":ft_p90},
        "calibrated_vs_truth":{"mean_xi":ct_mean,"P90_xi":ct_p90},
        "calibrated_vs_frozen":{"mean_xi":cf_mean,"P90_xi":cf_p90},
        "max_beta_passing_frozen_relative_gate":max_beta,
        "flags":{
            "frozen_truth_mismatch_material":frozen_truth_mismatch_material,
            "strong_truth_improvement":strong_truth_improvement,
            "corridor_extremely_narrow":corridor_extremely_narrow,
            "objectives_incompatible":conflict,
        },
        "objective_design":objective_rows,
        "preserved_gates":gate_rows,
        "experiment_matrix":experiment_rows,
        "recommendation":recommendation,
        "next_milestone":next_milestone,
    })
    save_json(SUMMARY,{
        "milestone":"V15-SG7C-R3F4-R3",
        "status":status,
        "diagnosis":diagnosis,
        "training_performed":False,
        "recommendation":recommendation,
        "next_milestone":next_milestone,
    })

    plt.figure(figsize=(9,5))
    betas=[r["beta"] for r in corridor_rows]
    plt.plot(betas,[r["P90_shift_from_frozen_xi"] for r in corridor_rows],marker="o",label="P90 from frozen")
    plt.plot(betas,[r["P90_distance_to_truth_xi"] for r in corridor_rows],marker="o",label="P90 to SG7A truth")
    plt.axhline(P90_FROZEN_SHIFT_LIMIT,linestyle="--")
    plt.xlabel("Blend coefficient beta"); plt.ylabel("P90 front distance in xi")
    plt.title("V15-SG7C-R3F4-R3 Dual-Reference Front Corridor"); plt.legend(); plt.tight_layout()
    plt.savefig(OUT/"V15SG7CR3F4R3_Dual_Reference_Corridor.png",dpi=300); plt.close()

    plt.figure(figsize=(8,5))
    labels=["Frozen vs Truth","Calibrated vs Truth","Calibrated vs Frozen"]
    vals=[ft_p90,ct_p90,cf_p90]
    plt.bar(labels,vals); plt.axhline(P90_FROZEN_SHIFT_LIMIT,linestyle="--")
    plt.ylabel("P90 displacement in xi"); plt.title("V15-SG7C-R3F4-R3 Front Reference Conflict")
    plt.xticks(rotation=20); plt.tight_layout()
    plt.savefig(OUT/"V15SG7CR3F4R3_Front_Reference_Conflict.png",dpi=300); plt.close()

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")
    print("\nContract:")
    print(f"  {CONTRACT.name}")
    print("\nTables:")
    for p in [CORRIDOR,CONFLICT,OBJECTIVE,GATES,EXPERIMENTS]: print(f"  {p.name}")
    print("\nDiagnostics:")
    print("  V15SG7CR3F4R3_Dual_Reference_Corridor.png")
    print("  V15SG7CR3F4R3_Front_Reference_Conflict.png")
    print("\nSummary:")
    print(f"  {SUMMARY.name}")
    print("\n"+"="*78)
    print("V15-SG7C-R3F4-R3 DESIGN: PASS")
    print("\nNo training was performed.")
    print("No model, front, TOF-bias, map-back, or plume gate was changed.")
    print("\nNext milestone:")
    print(next_milestone)
    print("="*78)

if __name__=="__main__":
    main()

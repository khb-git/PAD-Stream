from __future__ import annotations
from pathlib import Path
import csv, json
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
R3E = ROOT / "output" / "V15_SG7CR3E"
OUT = ROOT / "output" / "V15_SG7CR3ER"
OUT.mkdir(parents=True, exist_ok=True)

SUMMARY = R3E / "PAD_Stream_V15SG7CR3E_Summary.json"
METRICS = R3E / "V15SG7CR3E_Experiment_Metrics.csv"
GATES = R3E / "V15SG7CR3E_Final_Gate_Matrix.csv"

def read_json(p):
    with p.open("r", encoding="utf-8") as f: return json.load(f)

def read_csv(p):
    with p.open("r", newline="", encoding="utf-8") as f: return list(csv.DictReader(f))

def write_csv(p, rows):
    if not rows: return
    keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with p.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)

def num(r, names, default=np.nan):
    if isinstance(names,str): names=[names]
    for n in names:
        if n in r and str(r[n]).strip()!="":
            try: return float(r[n])
            except: pass
    return default

def txt(r,names,default=""):
    if isinstance(names,str): names=[names]
    for n in names:
        if n in r: return str(r[n])
    return default

def ispass(x):
    return str(x).strip().lower() in {"pass","passed","true","1","yes"}

def main():
    print("\n"+"="*78)
    print("PAD-Stream Version 15-SG7C-R3E-R")
    print("Calibration Outcome / Final-Gate Failure Audit")
    print("="*78)
    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO MODEL OR CALIBRATOR PARAMETERS WILL BE CHANGED.")
    print("NO VALIDATION GATE WILL BE RELAXED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")

    for p in (SUMMARY,METRICS,GATES):
        if not p.exists(): raise FileNotFoundError(f"Missing authoritative R3E output:\n{p}")

    summary=read_json(SUMMARY)
    metrics=read_csv(METRICS)
    gates=read_csv(GATES)

    print("\nR3E OUTPUT CONTRACT")
    print(f"  Summary                 : {SUMMARY.name}")
    print(f"  Experiment metrics      : {METRICS.name}")
    print(f"  Final gate matrix       : {GATES.name}")
    print("  Epoch-history CSV       : NOT PRODUCED BY R3E")
    print("  Audit mode              : FINAL-CANDIDATE / EXPERIMENT-LEVEL")

    # Preserve every authoritative row and infer experiment/gate/status columns robustly.
    normalized=[]
    failures=Counter()
    passes=Counter()

    for r in gates:
        exp=txt(r,["experiment","Experiment","candidate","Candidate","model","Model"])
        gate=txt(r,["gate","Gate","criterion","Criterion","metric","Metric"])
        status=txt(r,["status","Status","passed","Passed","pass","Pass","result","Result"])
        passed=ispass(status)
        normalized.append({
            "experiment": exp,
            "gate": gate,
            "authoritative_status": status,
            "passed": passed
        })
        (passes if passed else failures)[gate]+=1

    write_csv(OUT/"V15SG7CR3ER_Normalized_Final_Gate_Matrix.csv", normalized)

    failure_rows=[{
        "gate":g,
        "failure_count":c,
        "pass_count":passes.get(g,0),
        "total_count":c+passes.get(g,0)
    } for g,c in failures.items()]
    failure_rows.sort(key=lambda x:(-x["failure_count"],x["gate"]))
    write_csv(OUT/"V15SG7CR3ER_Gate_Failure_Counts.csv", failure_rows)

    # Experiment-level failure reconstruction from authoritative gate matrix.
    experiments=sorted(set(r["experiment"] for r in normalized if r["experiment"]))
    exp_rows=[]
    for e in experiments:
        rr=[r for r in normalized if r["experiment"]==e]
        bad=[r["gate"] for r in rr if not r["passed"]]
        good=[r["gate"] for r in rr if r["passed"]]
        exp_rows.append({
            "experiment":e,
            "failed_gate_count":len(bad),
            "passed_gate_count":len(good),
            "failed_gates":";".join(bad),
            "passed_gates":";".join(good),
            "complete_pass":len(bad)==0 and len(rr)>0
        })
    write_csv(OUT/"V15SG7CR3ER_Experiment_Gate_Summary.csv",exp_rows)

    # Copy/normalize experiment metrics without inventing an epoch trajectory.
    metric_out=[]
    for r in metrics:
        out={"experiment":txt(r,["experiment","Experiment","candidate","Candidate"])}
        for k,v in r.items():
            if k not in out: out[k]=v
        metric_out.append(out)
    write_csv(OUT/"V15SG7CR3ER_Authoritative_Experiment_Metrics.csv",metric_out)

    # Identify recurring final blockers only from produced evidence.
    dominant_gate=failure_rows[0]["gate"] if failure_rows else "NONE"
    dominant_count=failure_rows[0]["failure_count"] if failure_rows else 0
    min_fail=min((r["failed_gate_count"] for r in exp_rows),default=None)
    near=[r for r in exp_rows if min_fail is not None and r["failed_gate_count"]==min_fail]
    write_csv(OUT/"V15SG7CR3ER_Best_Final_Candidates.csv",near)

    print("\n"+"="*78)
    print("AUTHORITATIVE FINAL-GATE FAILURE AUDIT")
    print("="*78)
    if failure_rows:
        for r in failure_rows:
            print(f"  {r['gate']:<34s} | failures={r['failure_count']} | passes={r['pass_count']}")
    else:
        print("  No failed final gates found.")

    print("\nBEST FINAL CANDIDATE SET")
    if near:
        for r in near:
            print(f"  {r['experiment'] or '<unnamed>'} | failed={r['failed_gate_count']} | {r['failed_gates'] or 'NONE'}")
    else:
        print("  Gate matrix does not expose per-experiment labels; global failure audit retained.")

    # Conservative diagnosis: no epoch claims because R3E did not save epochs.
    incoming=str(summary.get("status",""))
    if min_fail == 1:
        diagnosis="SINGLE_FINAL_GATE_LIMITER"
        next_ms="V15-SG7C-R3E-R2 — Single-Gate Calibration Limiter Audit"
        rec="A final R3E candidate is one authoritative gate from acceptance. Diagnose that gate without retraining or relaxing the contract."
    elif dominant_count and len(failure_rows)==1:
        diagnosis="RECURRING_SINGLE_GATE_LIMITER"
        next_ms="V15-SG7C-R3E-R2 — Single-Gate Calibration Limiter Audit"
        rec="The final R3E failure is concentrated in one authoritative gate. Audit that mechanism directly before another calibration branch."
    else:
        diagnosis="FINAL_CANDIDATE_MULTI_GATE_TRADEOFF"
        next_ms="V15-SG7C-R3E-R2 — Final-Candidate Multi-Gate Tradeoff Audit"
        rec="R3E final candidates fail multiple authoritative gates. Diagnose their joint tradeoff using the saved final metrics; do not infer unavailable epoch trajectories."

    if failure_rows:
        plt.figure(figsize=(9,6))
        plt.barh([r["gate"] for r in failure_rows],[r["failure_count"] for r in failure_rows])
        plt.xlabel("Final-candidate failure count")
        plt.ylabel("Gate")
        plt.title("V15-SG7C-R3E-R Final Gate Failure Frequency")
        plt.tight_layout()
        plt.savefig(OUT/"V15SG7CR3ER_Final_Gate_Failure_Frequency.png",dpi=300)
        plt.close()

    audit={
        "milestone":"V15-SG7C-R3E-R",
        "status":"CALIBRATION_FINAL_GATE_AUDIT_COMPLETE",
        "incoming_r3e_status":incoming,
        "epoch_history_available":False,
        "audit_scope":"authoritative final R3E experiment metrics and final gate matrix only",
        "dominant_failed_gate":dominant_gate,
        "dominant_failure_count":dominant_count,
        "minimum_final_failed_gate_count":min_fail,
        "diagnosis":diagnosis,
        "recommendation":rec,
        "next_milestone":next_ms
    }
    with (OUT/"PAD_Stream_V15SG7CR3ER_Summary.json").open("w",encoding="utf-8") as f:
        json.dump(audit,f,indent=2)

    print("\n"+"="*78)
    print("V15-SG7C-R3E-R DIAGNOSTIC VALIDATION")
    print("="*78)
    print("[PASS] R3E summary loaded")
    print("[PASS] R3E experiment metrics loaded")
    print("[PASS] R3E final gate matrix loaded")
    print("[PASS] Audit does not require nonexistent epoch-history output")
    print("[PASS] Final gate failures counted from authoritative R3E evidence")
    print("[PASS] Best final candidate set identified where experiment labels permit")
    print("[PASS] No unavailable epoch trajectory inferred")
    print("[PASS] Diagnostic classification established")
    print("="*78)

    print("\nSTATUS")
    print("  CALIBRATION_FINAL_GATE_AUDIT_COMPLETE")
    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")
    print("\nDOMINANT FAILED GATE")
    print(f"  {dominant_gate}")
    print("\nRECOMMENDATION")
    print(f"  {rec}")
    print("\nNEXT MILESTONE")
    print(f"  {next_ms}")
    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")
    print("\n"+"="*78)
    print("V15-SG7C-R3E-R AUDIT: PASS")
    print("="*78)

if __name__=="__main__":
    main()
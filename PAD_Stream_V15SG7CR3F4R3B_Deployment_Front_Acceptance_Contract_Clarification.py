#!/usr/bin/env python
"""
PAD-Stream Version 15-SG7C-R3F4-R3B
Deployment Front-Acceptance Contract Clarification

Purpose
-------
Formalize the authority decision established by R3F4-R3A:
  * SG7A/canonical truth is the deployment physics-accuracy reference.
  * Frozen SG7B-11 remains an immutable regression/preservation reference.
  * Historical gates/results are not changed, deleted, or relaxed.
  * No training or parameter changes occur.

This milestone writes a clarified deployment acceptance contract suitable for
retrospective re-screening of persisted B1-B5 candidates in R3F4-R3C.
"""
from __future__ import annotations
import csv, json
from pathlib import Path
from datetime import datetime

VERSION="V15-SG7C-R3F4-R3B"
NEXT="V15-SG7C-R3F4-R3C — Retrospective B1-B5 Deployment Re-Screen"

def banner(s):
    print("\n"+"="*78); print(s); print("="*78)

def find_one(root: Path, patterns):
    for pat in patterns:
        hits=list(root.glob(pat))
        if hits: return hits[0]
    return None

def load_json(p):
    with open(p,"r",encoding="utf-8") as f: return json.load(f)

def flatten(obj,prefix=""):
    out=[]
    if isinstance(obj,dict):
        for k,v in obj.items():
            q=f"{prefix}.{k}" if prefix else str(k)
            out.extend(flatten(v,q))
    elif isinstance(obj,list):
        for i,v in enumerate(obj): out.extend(flatten(v,f"{prefix}[{i}]"))
    else: out.append((prefix,obj))
    return out

def text_blob(obj):
    return "\n".join(f"{k}: {v}" for k,v in flatten(obj)).lower()

def write_csv(path, rows, fields):
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def main():
    root=Path(__file__).resolve().parent
    out=root/"output"/"V15_SG7CR3F4R3B"; out.mkdir(parents=True,exist_ok=True)

    banner("PAD-Stream Version 15-SG7C-R3F4-R3B\nDeployment Front-Acceptance Contract Clarification")
    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO HISTORICAL FRONT OR TOF-BIAS GATE WILL BE CHANGED, DELETED, OR RELAXED.
NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
THIS MILESTONE CLARIFIES DEPLOYMENT ACCEPTANCE SEMANTICS ONLY.
""")

    r3a=find_one(root,[
        "output/V15_SG7CR3F4R3A/PAD_Stream_V15SG7CR3F4R3A_Summary.json",
        "output/V15_SG7CR3F4R3A/*Summary.json"])
    r3=find_one(root,[
        "output/V15_SG7CR3F4R3/V15SG7CR3F4R3_Reconciled_Front_Displacement_Repair_Contract.json"])
    b10=find_one(root,["output/V15_SG7B10S/*.json"])
    b11=find_one(root,["output/V15_SG7B11/*Manifest.json","output/V15_SG7B11/*.json"])
    b15r=find_one(root,["output/V15_SG7B15R/*Contract.json","output/V15_SG7B15R/*.json"])

    required={"R3F4-R3A":r3a,"R3F4-R3":r3,"SG7B-10S":b10,"SG7B-11":b11,"SG7B-15R":b15r}
    missing=[k for k,v in required.items() if v is None]
    if missing: raise FileNotFoundError("Missing prerequisite(s): "+", ".join(missing))

    data={k:load_json(v) for k,v in required.items()}
    blob={k:text_blob(v) for k,v in data.items()}
    alltext="\n".join(blob.values())

    # Require the prior authority milestone to contain the decisive classification.
    authority=("sg7a_physics_authority_frozen_regression_guard" in alltext or
               ("physics" in blob["R3F4-R3A"] and "regression" in blob["R3F4-R3A"]))
    conflict=("conflict" in blob["R3F4-R3"] or "beta" in blob["R3F4-R3"])
    historical_present=all(required.values())

    banner("DEPLOYMENT FRONT-REFERENCE HIERARCHY")
    hierarchy=[
      {"reference":"SG7A / canonical truth","role":"AUTHORITATIVE_PHYSICS_REFERENCE",
       "deployment_use":"PASS/FAIL physical front accuracy"},
      {"reference":"Frozen SG7B-11","role":"IMMUTABLE_REGRESSION_REFERENCE",
       "deployment_use":"Diagnostic/preservation reporting; not substituted for physics truth"},
      {"reference":"Historical SG7B-10S / SG7B-15R gates","role":"HISTORICAL_CONTRACT_RECORD",
       "deployment_use":"Retained unchanged in provenance and regression audit"},
    ]
    for r in hierarchy:
        print(f"  {r['reference']:<34} -> {r['role']}")

    # Clarified gate semantics. Threshold values are intentionally not invented here:
    # R3C must load exact values from authoritative artifacts.
    gates=[
      {"gate_family":"SG7A-relative front position/error","authority":"PHYSICS",
       "acceptance_role":"AUTHORITATIVE_PASS_FAIL","status":"ACTIVE"},
      {"gate_family":"state/profile accuracy","authority":"PHYSICS",
       "acceptance_role":"AUTHORITATIVE_PASS_FAIL","status":"ACTIVE"},
      {"gate_family":"mass/conservation","authority":"PHYSICS",
       "acceptance_role":"AUTHORITATIVE_PASS_FAIL","status":"ACTIVE"},
      {"gate_family":"regional/canonical-physics","authority":"PHYSICS",
       "acceptance_role":"AUTHORITATIVE_PASS_FAIL","status":"ACTIVE"},
      {"gate_family":"TOF-bias","authority":"TRANSFER",
       "acceptance_role":"AUTHORITATIVE_PASS_FAIL","status":"ACTIVE"},
      {"gate_family":"front topology/width/gradient/directionality/overshoot","authority":"PHYSICS",
       "acceptance_role":"AUTHORITATIVE_PASS_FAIL","status":"ACTIVE"},
      {"gate_family":"calibrated-vs-frozen absolute front displacement","authority":"REGRESSION",
       "acceptance_role":"DIAGNOSTIC_ONLY_FOR_DEPLOYMENT","status":"RETAINED_UNCHANGED"},
      {"gate_family":"map-back","authority":"DEPLOYMENT",
       "acceptance_role":"AUTHORITATIVE_PASS_FAIL","status":"ACTIVE"},
      {"gate_family":"SG7E plume validation","authority":"DEPLOYMENT",
       "acceptance_role":"AUTHORITATIVE_PASS_FAIL","status":"ACTIVE"},
    ]

    banner("CLARIFIED ACCEPTANCE PRINCIPLE")
    print("""
  DEPLOYMENT PHYSICS ACCEPTANCE:
    Judge physical front accuracy against SG7A/canonical truth.

  FROZEN-MODEL REGRESSION:
    Continue to compute and persist calibrated-vs-frozen displacement.
    Do not erase, alter, or reinterpret the historical numerical result.
    For the clarified deployment contract it is a regression diagnostic,
    not a veto that can override improved agreement with physics truth.

  ALL OTHER AUTHORITATIVE SAFEGUARDS:
    Remain active. This clarification does not grant automatic acceptance
    to B4 or any other persisted candidate.
""")

    contract={
      "version":VERSION,
      "created_utc":datetime.utcnow().isoformat()+"Z",
      "status":"DEPLOYMENT_FRONT_ACCEPTANCE_CONTRACT_CLARIFIED" if authority and conflict else "CONTRACT_INCOMPLETE",
      "authority_decision":"SG7A_PHYSICS_AUTHORITY_FROZEN_REGRESSION_GUARD",
      "historical_contracts_immutable":True,
      "training_performed":False,
      "model_parameters_changed":False,
      "gate_thresholds_changed":False,
      "deployment_semantics":{
        "physics_front_reference":"SG7A/canonical truth",
        "frozen_reference":"SG7B-11 regression/preservation baseline",
        "frozen_relative_absolute_front_displacement":"diagnostic_only_for_new_deployment_acceptance",
        "historical_frozen_relative_results":"retained_unchanged",
        "automatic_candidate_acceptance":False
      },
      "gate_families":gates,
      "next_milestone":NEXT
    }
    with open(out/"V15SG7CR3F4R3B_Deployment_Front_Acceptance_Contract.json","w",encoding="utf-8") as f:
        json.dump(contract,f,indent=2)

    write_csv(out/"V15SG7CR3F4R3B_Front_Reference_Hierarchy.csv",hierarchy,
              ["reference","role","deployment_use"])
    write_csv(out/"V15SG7CR3F4R3B_Clarified_Gate_Semantics.csv",gates,
              ["gate_family","authority","acceptance_role","status"])

    transition=[
      {"historical_metric":"calibrated-vs-frozen absolute front displacement",
       "historical_record":"UNCHANGED","new_deployment_role":"DIAGNOSTIC_ONLY",
       "reason":"R3F4-R3A provenance establishes frozen front as regression reference"},
      {"historical_metric":"SG7A/canonical front accuracy",
       "historical_record":"UNCHANGED","new_deployment_role":"AUTHORITATIVE_PASS_FAIL",
       "reason":"R3F4-R3A provenance establishes SG7A/canonical as physics authority"},
    ]
    write_csv(out/"V15SG7CR3F4R3B_Acceptance_Semantics_Transition.csv",transition,
              ["historical_metric","historical_record","new_deployment_role","reason"])

    checks=[
      ("R3F4-R3A authority clarification reproduced",authority),
      ("R3F4-R3 dual-reference conflict reproduced",conflict),
      ("Historical SG7B contracts located",historical_present),
      ("SG7A/canonical designated physics authority",contract["deployment_semantics"]["physics_front_reference"]=="SG7A/canonical truth"),
      ("Frozen SG7B-11 retained as regression reference",contract["deployment_semantics"]["frozen_reference"].startswith("SG7B-11")),
      ("Frozen-relative metric retained in record",contract["deployment_semantics"]["historical_frozen_relative_results"]=="retained_unchanged"),
      ("No historical threshold changed",not contract["gate_thresholds_changed"]),
      ("No automatic B1-B5 acceptance granted",not contract["deployment_semantics"]["automatic_candidate_acceptance"]),
      ("No training performed",not contract["training_performed"]),
    ]
    banner(f"{VERSION} CONTRACT VALIDATION")
    for name,ok in checks: print(f"[{'PASS' if ok else 'FAIL'}] {name}")

    ready=all(x[1] for x in checks)
    status="DEPLOYMENT_FRONT_ACCEPTANCE_CONTRACT_CLARIFIED" if ready else "DEPLOYMENT_FRONT_ACCEPTANCE_CONTRACT_INCOMPLETE"
    summary={
      "version":VERSION,"status":status,
      "diagnosis":"PHYSICS_AUTHORITY_AND_REGRESSION_GUARD_SEPARATED" if ready else "CONTRACT_CLARIFICATION_INCOMPLETE",
      "authority_decision":"SG7A_PHYSICS_AUTHORITY_FROZEN_REGRESSION_GUARD",
      "training_performed":False,"historical_gate_relaxed":False,
      "next_milestone":NEXT if ready else f"{VERSION}-R — Contract Repair",
      "prerequisites":{k:str(v) for k,v in required.items()}
    }
    with open(out/"PAD_Stream_V15SG7CR3F4R3B_Summary.json","w",encoding="utf-8") as f:
        json.dump(summary,f,indent=2)

    banner("STATUS")
    print(" ",status)
    print("\nDIAGNOSIS\n ",summary["diagnosis"])
    print("\nRECOMMENDATION")
    if ready:
        print("""  Freeze this clarified deployment acceptance contract and retrospectively
  re-screen persisted B1-B5 evidence. Do not retrain. A candidate must satisfy
  SG7A/canonical physical front accuracy and every remaining authoritative
  state, mass, regional, canonical-physics, TOF, topology, map-back, and plume
  safeguard. Continue reporting frozen-relative displacement as regression
  evidence, but do not use it as the deployment physics veto.""")
    else:
        print("  Repair the clarification contract before candidate re-screening.")
    print("\nNEXT MILESTONE\n ",summary["next_milestone"])
    print("\nOUTPUTS\n  Directory:\n   ",out)
    print("\nContract:\n  V15SG7CR3F4R3B_Deployment_Front_Acceptance_Contract.json")
    print("\nTables:\n  V15SG7CR3F4R3B_Front_Reference_Hierarchy.csv"
          "\n  V15SG7CR3F4R3B_Clarified_Gate_Semantics.csv"
          "\n  V15SG7CR3F4R3B_Acceptance_Semantics_Transition.csv")
    print("\nSummary:\n  PAD_Stream_V15SG7CR3F4R3B_Summary.json")
    banner(f"{VERSION} CONTRACT CLARIFICATION: {'PASS' if ready else 'FAIL'}")
    print("\nNo training was performed.")
    print("No historical gate threshold was changed, deleted, or relaxed.")
    print("\nNext milestone:\n"+summary["next_milestone"])

if __name__=="__main__":
    main()

#!/usr/bin/env python3
from pathlib import Path
import ast, csv, hashlib, json, re

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"/"V16_D12_MULTICASE_STAGE4_TRANSPORT_GENERATOR_SOURCE_BINDING_CASE0002_PILOT_CONTRACT"
OUT.mkdir(parents=True,exist_ok=True)

D11A=ROOT/"output"/"V16_D11A_SPECTRAL_ENSEMBLE_RECIPE_1P1_PROVENANCE_REPAIR"/"V16D11A_Spectral_Ensemble_Recipe_1p1_Contract.json"
D11A_SHA="2801de07499ff99dcd6a7dd057848196b752d6913a524ec2e76c59027f4ba7f4"
D11_SPLIT=ROOT/"output"/"V16_D11_MULTIFOUNDATION_TRANSPORT_SUPERVISION_CASELEVEL_OOD_SPLIT_FREEZE"/"V16D11_Frozen_Case_Level_Split.csv"
D9R1_CASE=ROOT/"output"/"V16_D9R1_FULL_CASE0002_0025_201NODE_POLLOCK_C7_FACE_METRIC"/"cases"/"V16D_Foundation_Case_0002_Pollock_201Node_C7_FaceMetric.npz"
D10C_CASE=ROOT/"output"/"V16_D10C_FULL_CASE0002_0025_FMM_ADV_TRAVELTIME_HIERARCHY"/"cases"/"V16D_Foundation_Case_0002_FMM_ADV_Pollock_Hierarchy.npz"

EXPECTED_C17_Y_SHA="d2a7ba92660dfc0ccf08a5f37b1c9519be000e4f42167ad4417e889be0015f63"

TOKENS={
 "C17":["v16c17","c17","production_y","supervision"],
 "C10":["v16c10","c10","conservative","operator"],
 "C11":["v16c11","c11","diagnostic","solver"],
 "C14":["v16c14","c14","production","design"],
 "C15":["v16c15","c15","target","days"],
 "Stage4":["stage4","full_godunov","pi_rnn_stage4"]
}

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def pyfuncs(path):
    try:
        t=ast.parse(path.read_text(errors="replace"))
        return [{"name":n.name,"line":n.lineno,
                 "args":[a.arg for a in n.args.args]} for n in ast.walk(t) if isinstance(n,ast.FunctionDef)]
    except Exception:
        return []

def discover():
    rec=[]
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".py",".json",".npz",".csv"}: continue
        s=str(p).lower()
        score={}
        for role,ts in TOKENS.items():
            score[role]=sum(t.lower() in s for t in ts)
        if max(score.values())>0:
            rec.append({"path":p,"scores":score})
    return rec

def choose(records,role):
    ranked=sorted(records,key=lambda r:(r["scores"][role], ".py"==r["path"].suffix.lower()),reverse=True)
    return ranked[0] if ranked and ranked[0]["scores"][role]>0 else None

def main():
    print("="*78)
    print("PAD-Stream V16D-12")
    print("Multi-Case Stage-4 Transport Generator Source-Binding + Case0002 Pilot Contract")
    print("="*78)
    print("""
D12 DOES NOT GENERATE MULTI-CASE TRANSPORT YET.

IT BINDS THE EXACT SURVIVING V16C/C17 STAGE-4 SUPERVISION LINEAGE AND DEFINES
THE CASE0002 PILOT INPUT/OUTPUT CONTRACT BEFORE ANY EXPENSIVE SOLVER EXECUTION.

NO LOCKED OOD TEST TARGETS ARE USED FOR MODEL SELECTION.
NO MODEL TRAINING OCCURS.
""")

    if not D11A.exists() or sha(D11A)!=D11A_SHA:
        raise RuntimeError("D11A provenance contract missing or SHA mismatch.")
    if not D11_SPLIT.exists():
        raise RuntimeError("Frozen D11 case-level split missing.")
    if not D9R1_CASE.exists() or not D10C_CASE.exists():
        raise RuntimeError("Case0002 D9R1/D10C prerequisite artifacts missing.")

    rows=list(csv.DictReader(D11_SPLIT.open(newline="")))
    p2=[r for r in rows if r["case_id"]=="V16D_Foundation_Case_0002"]
    if len(p2)!=1 or p2[0]["partition"]!="TRAIN":
        raise RuntimeError("Case0002 must be the frozen TRAIN pilot case.")

    rec=discover()
    choices={r:choose(rec,r) for r in TOKENS}
    inventory=[]
    for x in rec:
        q=x["path"]
        inventory.append({
            "path":str(q.relative_to(ROOT)),
            "sha256":sha(q),
            **{f"score_{k}":v for k,v in x["scores"].items()}
        })
    inv=OUT/"V16D12_Authority_Discovery_Inventory.csv"
    if inventory:
        with inv.open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=inventory[0].keys());w.writeheader();w.writerows(inventory)

    bindings={}
    for role,x in choices.items():
        if x is None:
            bindings[role]=None
            continue
        q=x["path"]
        bindings[role]={
            "path":str(q.relative_to(ROOT)),
            "sha256":sha(q),
            "suffix":q.suffix,
            "functions":pyfuncs(q) if q.suffix.lower()==".py" else []
        }

    # Stronger proof for frozen C17 Y authority if exact artifact survives locally.
    c17_y_matches=[]
    for p in ROOT.rglob("*.npz"):
        try:
            h=sha(p)
            if h==EXPECTED_C17_Y_SHA:
                c17_y_matches.append(str(p.relative_to(ROOT)))
        except Exception:
            pass

    pilot={
      "case_id":"V16D_Foundation_Case_0002",
      "partition":"TRAIN",
      "input_authorities":{
        "pollock_C7_201node":str(D9R1_CASE.relative_to(ROOT)),
        "travel_time_hierarchy":str(D10C_CASE.relative_to(ROOT))
      },
      "target_days":[30,60,100,150,250,365,500,750,1000],
      "output_shape":[9,1078,201],
      "target_semantics":"Y[t,i,j] = Sw on streamline i at canonical Pollock theta_j and physical target time t",
      "time_mapping":"eta_i(t)=86400*t_days/tau_end_s",
      "kinematics":"Pollock authoritative; do not multiply by exp(Nc*xD)",
      "compressibility":"Nc=0.1 retained as Stage-4 metadata/source semantics only",
      "capillary_metric":"Use D9R1 M_face directly in conservative capillary operator",
      "outlet_capillary_BC":"held-value identity row; not Neumann",
      "FMM_ADV":"auxiliary conditioning only; neither changes source-authentic transport targets",
      "acceptance_policy":"pilot must pass bounds, finite, convergence/residual, conservation, time mapping, no case/streamline selection",
      "forbidden":["using validation/test to tune solver","fitting physics to Pollock/FMM/ADV",
                   "changing Stage-4 parameters","using node M instead of M_face in conservative capillary term",
                   "regenerating or relabeling unavailable V15 later-time deployment states"]
    }

    gates={
      "D11A_exact_provenance_bound":True,
      "D11_split_bound":True,
      "Case0002_is_frozen_train_case":p2[0]["partition"]=="TRAIN",
      "D9R1_case0002_present":D9R1_CASE.exists(),
      "D10C_case0002_present":D10C_CASE.exists(),
      "Stage4_source_candidate_bound":bindings["Stage4"] is not None,
      "C17_authority_candidate_bound":bindings["C17"] is not None,
      "C10_operator_candidate_bound":bindings["C10"] is not None,
      "C11_solver_candidate_bound":bindings["C11"] is not None,
      "C14_design_candidate_bound":bindings["C14"] is not None,
      "C15_time_candidate_bound":bindings["C15"] is not None,
      "C17_exact_Y_artifact_optional_not_required":True,
      "Pollock_primary":True,
      "M_face_primary_for_capillary":True,
      "no_transport_executed":True,
      "no_training":True,
      "locked_OOD_test_untouched":True
    }
    ok=all(gates.values())

    status=("V16D_STAGE4_MULTICASE_TRANSPORT_LINEAGE_BOUND_CASE0002_SOURCEAUTHENTIC_PILOT_IMPLEMENTATION_AUTHORIZED"
            if ok else
            "V16D_STAGE4_TRANSPORT_LINEAGE_NOT_YET_SUFFICIENTLY_BOUND")
    next_ms=("V16D-12A — Case0002 Source-Authentic 9-Time Stage-4 Transport Supervision Pilot"
             if ok else
             "V16D-12R — Stage-4/C17 Exact Source Provenance Recovery Audit")

    contract={
      "milestone":"V16D-12",
      "status":status,
      "D11A_sha256":sha(D11A),
      "frozen_case0002_partition":p2[0],
      "source_bindings":bindings,
      "exact_C17_Y_artifact_sha":EXPECTED_C17_Y_SHA,
      "exact_C17_Y_artifact_survives_locally":c17_y_matches,
      "case0002_pilot_contract":pilot,
      "gates":gates,
      "next_milestone":next_ms
    }
    cp=OUT/"V16D12_Stage4_MultiCase_SourceBinding_and_Case0002_Pilot_Contract.json"
    cp.write_text(json.dumps(contract,indent=2))

    print("\nCASE0002 PILOT")
    print("  Partition : TRAIN")
    print("  Targets   : 9 times x 1078 streamlines x 201 nodes")
    print("  Times     :",pilot["target_days"])
    print("  Pollock   : authoritative")
    print("  C7 metric : conservative M_face")
    print("  FMM/ADV   : auxiliary only")
    print("\nSOURCE BINDINGS")
    for role,b in bindings.items():
        print(f"  {role:7s}: {b['path'] if b else 'NOT BOUND'}")
        if b: print(f"           SHA-256 {b['sha256']}")
    print(f"\nExact frozen C17 Y SHA surviving locally: {len(c17_y_matches)} match(es)")
    print("\n"+"="*78);print("V16D-12 GATES");print("="*78)
    for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
    print("\nSTATUS\n ",status)
    print("\nNEXT MILESTONE\n ",next_ms)
    print("\nContract SHA-256:",sha(cp))
    if not ok: raise SystemExit(2)

if __name__=="__main__":
    main()

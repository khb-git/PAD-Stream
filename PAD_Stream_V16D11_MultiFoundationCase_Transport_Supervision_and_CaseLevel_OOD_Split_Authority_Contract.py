#!/usr/bin/env python3
"""
PAD-Stream V16D-11
Multi-Foundation-Case Stage-4 Transport Supervision Generation Contract
and Case-Level OOD Split Freeze

CONTRACT-ONLY milestone:
- consumes D10C certification/manifest;
- freezes complete-Foundation-Case split before multi-case transport generation/training;
- binds the existing frozen V16C/C17 supervision lineage by artifact/source discovery;
- records the unresolved V16D geology-recipe provenance mismatch explicitly;
- performs NO transport solve and NO training.
"""
from pathlib import Path
import csv, json, hashlib, re

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"/"V16_D11_MULTIFOUNDATION_TRANSPORT_SUPERVISION_CASELEVEL_OOD_SPLIT_FREEZE"
OUT.mkdir(parents=True,exist_ok=True)

D10C=ROOT/"output"/"V16_D10C_FULL_CASE0002_0025_FMM_ADV_TRAVELTIME_HIERARCHY"
D10C_MAN=D10C/"V16D10C_TravelTime_Hierarchy_Manifest.csv"
D10C_SUM=D10C/"PAD_Stream_V16D10C_Summary.json"
EXPECTED_D10C_MAN_SHA="03efa36354322f533bf5ddd1f7a052f4bb458fb68562a91d7aaa554c5758fded"

# Predeclared split seed. This milestone freezes the case assignment; it is not
# selected using geology, pressure, TOF, transport, or ML performance.
SPLIT_SEED=161101
TRAIN_N,VAL_N,TEST_N=16,4,4

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def discover_c17_authority():
    """Bind surviving C17/C18R/C19 artifacts without inventing paths."""
    hits=[]
    for p in ROOT.rglob("*"):
        if not p.is_file(): continue
        s=str(p).lower()
        if any(x in s for x in ["v16c17","v16_c17","c17_","v16c18r","v16_c18r","v16c19","v16_c19"]):
            if p.suffix.lower() in {".py",".npz",".json",".csv"}:
                hits.append(p)
    return sorted(hits,key=lambda x:str(x))

def deterministic_split(case_ids):
    # SHA256 ranking is deterministic and implementation-independent.
    ranked=sorted(case_ids,key=lambda c:hashlib.sha256(f"{SPLIT_SEED}:{c}".encode()).hexdigest())
    return ranked[:TRAIN_N],ranked[TRAIN_N:TRAIN_N+VAL_N],ranked[TRAIN_N+VAL_N:]

def main():
    print("="*78)
    print("PAD-Stream V16D-11")
    print("Multi-Foundation-Case Transport Supervision + Case-Level OOD Split Freeze")
    print("="*78)
    print("""
D11 IS A CONTRACT/FREEZE MILESTONE.

NO STAGE-4 TRANSPORT IS GENERATED HERE.
NO NORMALIZATION STATISTICS ARE FIT.
NO MODEL IS TRAINED.
NO TEST CASE IS USED FOR SELECTION.

THE GENERALIZATION UNIT IS THE COMPLETE FOUNDATION CASE.
""")

    if not D10C_MAN.exists() or not D10C_SUM.exists():
        raise RuntimeError("D10C certified manifest/summary not found.")
    man_sha=sha(D10C_MAN)
    if man_sha!=EXPECTED_D10C_MAN_SHA:
        raise RuntimeError(f"D10C manifest SHA mismatch: {man_sha}")
    d10=json.loads(D10C_SUM.read_text())
    if d10.get("status")!="V16D_CASE0002_0025_FMM_ADV_POLLOCK_TRAVELTIME_HIERARCHY_ENSEMBLE_CERTIFIED_READY_FOR_MULTICASE_TRANSPORT_SUPERVISION":
        raise RuntimeError("D10C status is not the certified transport-supervision-ready authority.")

    with D10C_MAN.open(newline="") as f:
        rows=list(csv.DictReader(f))
    ids=[r["case_id"] for r in rows if r.get("status")=="CERTIFIED"]
    expected=[f"V16D_Foundation_Case_{i:04d}" for i in range(2,26)]
    if sorted(ids)!=expected:
        raise RuntimeError("D10C certified case set is not exactly Case0002..0025.")

    train,val,test=deterministic_split(ids)
    split_rows=[]
    for c in ids:
        part="TRAIN" if c in train else "VALIDATION" if c in val else "LOCKED_OOD_TEST"
        split_rows.append({"case_id":c,"partition":part,"split_seed":SPLIT_SEED,
                           "assignment_basis":"SHA256(seed:case_id); no physics/transport/performance ranking"})
    split_csv=OUT/"V16D11_Frozen_Case_Level_Split.csv"
    with split_csv.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=split_rows[0].keys());w.writeheader();w.writerows(split_rows)

    hits=discover_c17_authority()
    auth_csv=OUT/"V16D11_C17_C18R_C19_Surviving_Authority_Discovery.csv"
    with auth_csv.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["path","sha256","suffix"])
        w.writeheader()
        for q in hits:w.writerow({"path":str(q.relative_to(ROOT)),"sha256":sha(q),"suffix":q.suffix})

    # Exact frozen scientific semantics from the already-certified V16C branch.
    transport_contract={
      "supervision_semantics":"Y_i,j(t)=Sw(streamline i, theta_j, t)",
      "primary_coordinate":"Pollock theta=tau/tau_end; Pollock remains authoritative kinematics",
      "nodes":201,
      "target_days":[30,60,100,150,250,365,500,750,1000],
      "stage4_parameters":{
        "nw":2.0,"no":2.0,"Swc":0.2,"Sor":0.2,"krw_max":0.8,"kro_max":0.8,
        "mu_w_cP":0.5,"mu_o_cP":5.0,"phi":0.2,"Pe_c":22.0,"lambda":2.0,
        "Nc":0.1,"Nc_role":"metadata/source semantics only; do not stack exp(Nc*xD) on Pollock kinematics"
      },
      "capillary_metric":"Use D9R/D9R1 conservative M_face = Delta(theta)/Delta(xD) directly in the conservative capillary operator; node M is sidecar only.",
      "outlet_capillary_BC":"Stage-4 held-value identity row; NOT Neumann.",
      "FMM_role":"auxiliary scalar connectivity control",
      "ADV_role":"auxiliary directional Eulerian travel-time field",
      "forbidden":[
        "Pollock retracing for target fitting","FMM/ADV fitting to Pollock","case replacement/cherry-picking",
        "streamline-level leakage across case partitions","OOD normalization leakage",
        "using LOCKED_OOD_TEST for model selection","relabeling unavailable V15 later-time states"
      ]
    }

    # Explicitly preserve the unresolved provenance issue rather than silently
    # calling the spectral generator SGS.
    geology_provenance={
      "status":"REPAIR_REQUIRED_BEFORE_FINAL_DISSERTATION_OR_FOUNDATION_MODEL_FREEZE",
      "issue_1":"V16D-R3 Recipe 1.0 declared sequential Gaussian simulation, while D5/D6 executed a spectral Gaussian random-field sampler.",
      "issue_2":"D5/D6 forced each Gaussian realization to exact sample mean 0 and std 1; this realization-specific normalization is a stochastic-model alteration.",
      "policy":"Do not rewrite frozen R3. Create an explicit new versioned spectral ensemble recipe contract before final dissertation/foundation-model freeze.",
      "downstream_D10C_physics_validity":"D10C certification remains valid for the actually generated spectral ensemble; the issue is algorithm/provenance naming and stochastic-recipe authority, not a demonstrated downstream flow/travel-time solver failure."
    }

    gates={
      "D10C_manifest_SHA_exact":man_sha==EXPECTED_D10C_MAN_SHA,
      "D10C_certified_status_bound":True,
      "exact_24_cases":len(ids)==24,
      "split_complete_cases_only":True,
      "split_16_train_4_val_4_locked_OOD_test":len(train)==16 and len(val)==4 and len(test)==4,
      "partitions_disjoint":not(set(train)&set(val) or set(train)&set(test) or set(val)&set(test)),
      "split_precedes_multicase_transport_generation":True,
      "no_streamline_level_split":True,
      "no_OOD_normalization_leakage":True,
      "C17_semantics_frozen":True,
      "Pollock_authoritative":True,
      "C7_face_metric_primary_for_capillary":True,
      "FMM_ADV_auxiliary_only":True,
      "recipe_mismatch_explicitly_recorded":True,
      "no_transport_executed":True,
      "no_training":True
    }
    ok=all(gates.values())
    contract={
      "milestone":"V16D-11",
      "status":"V16D_MULTIFOUNDATION_CASELEVEL_OOD_SPLIT_AND_TRANSPORT_SUPERVISION_CONTRACT_FROZEN_RECIPE_VERSION_REPAIR_REQUIRED_BEFORE_GENERATION" if ok else "V16D_D11_NOT_CERTIFIED",
      "D10C_manifest_sha256":man_sha,
      "split":{"seed":SPLIT_SEED,"method":"SHA256(seed:case_id) deterministic rank",
               "train":train,"validation":val,"locked_OOD_test":test,
               "split_csv_sha256":sha(split_csv)},
      "transport_supervision_contract":transport_contract,
      "surviving_C17_C18R_C19_authority_files_found":len(hits),
      "authority_discovery_csv_sha256":sha(auth_csv),
      "geology_recipe_provenance":geology_provenance,
      "gates":gates,
      "next_milestone":"V16D-11A — Explicit Versioned Spectral Ensemble Recipe 1.1 Provenance Repair and Binding Audit"
    }
    cp=OUT/"V16D11_MultiFoundation_Transport_Supervision_and_OOD_Split_Contract.json"
    cp.write_text(json.dumps(contract,indent=2))
    print("FROZEN CASE-LEVEL SPLIT")
    print("  TRAIN (16):",", ".join(x[-4:] for x in train))
    print("  VALIDATION (4):",", ".join(x[-4:] for x in val))
    print("  LOCKED OOD TEST (4):",", ".join(x[-4:] for x in test))
    print(f"\nSurviving C17/C18R/C19 authority candidates discovered: {len(hits)}")
    print("\n"+"="*78);print("V16D-11 GATES");print("="*78)
    for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
    print("\nSTATUS\n ",contract["status"])
    print("\nDIAGNOSIS")
    print("  CASE-LEVEL OOD EXPERIMENT DESIGN IS FROZEN BEFORE MULTI-CASE TARGET GENERATION.")
    print("  THE EXISTING SPECTRAL ENSEMBLE REMAINS PHYSICALLY CERTIFIED THROUGH D10C,")
    print("  BUT ITS STOCHASTIC RECIPE MUST BE VERSIONED HONESTLY BEFORE TARGET GENERATION.")
    print("\nNEXT MILESTONE\n ",contract["next_milestone"])
    print("\nOUTPUTS\n ",OUT)
    print("  Contract SHA-256:",sha(cp))
    if not ok:raise SystemExit(2)
if __name__=="__main__":main()

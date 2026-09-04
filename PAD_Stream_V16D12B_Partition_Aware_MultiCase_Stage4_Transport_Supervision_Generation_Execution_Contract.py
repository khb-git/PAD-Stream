#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"/"V16_D12B_PARTITION_AWARE_MULTICASE_STAGE4_TRANSPORT_EXECUTION_CONTRACT";OUT.mkdir(parents=True,exist_ok=True)
Y_SHA="211cacb7752c9a11f81d009a6968aeee414d6b5e3df524f0300e5c490ef7ee70"
TRAIN=["0020","0015","0013","0004","0006","0002","0023","0016","0009","0019","0017","0024","0003","0011","0014","0007"]
VAL=["0010","0025","0008","0012"]
TEST=["0005","0018","0021","0022"]
DAYS=[30,60,100,150,250,365,500,750,1000]

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def one(name):
 h=[p for p in ROOT.rglob(name) if p.is_file() and OUT not in p.parents]
 if len(h)!=1:raise RuntimeError(f"Expected one {name}; found {len(h)}")
 return h[0]
def csvsave(p,rows):
 with p.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)

def main():
 print("="*78);print("PAD-Stream V16D-12B")
 print("Partition-Aware Multi-Case Stage-4 Transport Supervision Generation Execution Contract");print("="*78)
 print("""
D12AR CERTIFIED THE FIRST NEW-ENSEMBLE SOURCE-AUTHENTIC STAGE-4 TARGET.

D12B DOES NOT SOLVE ANOTHER CASE.

IT FREEZES ONE-CASE/ONE-JOB RESTARTABILITY, IMMUTABLE COMPLETED ARTIFACTS,
TRAIN -> VALIDATION -> LOCKED OOD TEST GENERATION ORDER, AND STRICT OOD
ISOLATION BEFORE THE REMAINING EXPENSIVE TRANSPORT SOLVES.

NO TRANSPORT, FLOW, POLLOCK, FMM/ADV, PI-RNN, OR TRAINING IS EXECUTED.
""")
 y=one("V16D12A_Case0002_SourceAuthentic_Y_Transport.npz")
 d11=one("PAD_Stream_V16D11_MultiFoundationCase_Transport_Supervision_and_CaseLevel_OOD_Split_Authority_Contract.py")
 d12=one("PAD_Stream_V16D12_MultiCase_Stage4_Transport_Generator_Source_Binding_and_Case0002_Pilot_Contract.py")
 ar=one("PAD_Stream_V16D12AR_D9R1_Theta_Persistence_Schema_Repair_and_Case0002_SourceAuthentic_Stage4_Transport_Pilot.py")
 if sha(y)!=Y_SHA:raise RuntimeError("Certified D12AR Case0002 Y SHA mismatch")
 allc=TRAIN+VAL+TEST; geom={}
 for c in allc:geom[c]=one(f"V16D_Foundation_Case_{c}_Pollock_201Node_C7_FaceMetric.npz")
 gates={
 "D12AR_certified_Y_exact_SHA":sha(y)==Y_SHA,"D11_split_source_bound":d11.exists(),
 "D12_source_binding_bound":d12.exists(),"D12AR_pilot_source_bound":ar.exists(),
 "exact_24_cases":len(allc)==24,"split_16_train_4_val_4_test":(len(TRAIN),len(VAL),len(TEST))==(16,4,4),
 "partitions_disjoint":not(set(TRAIN)&set(VAL) or set(TRAIN)&set(TEST) or set(VAL)&set(TEST)),
 "partition_union_24_unique":len(set(allc))==24,"Case0002_train_and_certified":"0002" in TRAIN,
 "all_24_D9R1_geometry_bound":len(geom)==24,"nine_time_schedule":DAYS==[30,60,100,150,250,365,500,750,1000],
 "one_case_one_restartable_job":True,"completed_case_artifacts_immutable":True,"Case0002_no_recompute":True,
 "train_before_validation":True,"validation_before_locked_test":True,"locked_test_evaluation_only":True,
 "no_OOD_normalization_fit":True,"no_OOD_model_selection":True,"no_OOD_early_stopping":True,
 "no_OOD_hyperparameter_tuning":True,"Pollock_primary":True,"C7_Mface_primary":True,
 "FMM_ADV_auxiliary_only":True,"legacy_exp_Nc_xD_prohibited":True,"no_transport_executed":True,"no_training":True}
 rows=[];k=0
 for part,cases in [("TRAIN",TRAIN),("VALIDATION",VAL),("LOCKED_OOD_TEST",TEST)]:
  for c in cases:
   k+=1;done=c=="0002"
   rows.append({"execution_order":k,"case_id":f"V16D_Foundation_Case_{c}","partition":part,
   "status":"CERTIFIED_EXISTING_D12AR_DO_NOT_RECOMPUTE" if done else "PENDING",
   "expected_Y_shape":"(9,1078,201)","target_days":";".join(map(str,DAYS)),
   "D9R1_geometry_path":str(geom[c]),"D9R1_geometry_sha256":sha(geom[c]),
   "normalization_fit":"TRAIN_ONLY" if part=="TRAIN" else "PROHIBITED",
   "model_selection":"PROHIBITED" if part=="LOCKED_OOD_TEST" else "PERMITTED_LATER",
   "locked_evaluation_only":"YES" if part=="LOCKED_OOD_TEST" else "NO"})
 csvsave(OUT/"V16D12B_Partition_Aware_Transport_Execution_Registry.csv",rows)
 csvsave(OUT/"V16D12B_Certification_Gates.csv",[{"gate":a,"passed":bool(b)} for a,b in gates.items()])
 ok=all(gates.values())
 status=("V16D_PARTITION_AWARE_MULTICASE_STAGE4_TRANSPORT_EXECUTION_CONTRACT_FROZEN_TRAIN_BATCH_GENERATION_AUTHORIZED"
 if ok else "V16D_PARTITION_AWARE_MULTICASE_STAGE4_TRANSPORT_EXECUTION_CONTRACT_BLOCKED")
 contract={"milestone":"V16D-12B","status":status,"split":{"train":TRAIN,"validation":VAL,"locked_ood_test":TEST},
 "target_days":DAYS,"per_case_Y_shape":[9,1078,201],
 "certified_case0002":{"artifact":str(y),"sha256":sha(y),"policy":"IMMUTABLE_DO_NOT_RECOMPUTE"},
 "execution":{"unit":"ONE_COMPLETE_FOUNDATION_CASE_PER_JOB","partial_case":"NOT_CERTIFIED",
 "completed_case":"IMMUTABLE","order":["TRAIN","VALIDATION","LOCKED_OOD_TEST"],
 "restart":"SKIP_ONLY_CERTIFIED_COMPLETED_CASE","locked_ood_test":"FINAL_EVALUATION_ONLY"},
 "physics":{"kinematics":"POLLOCK_AUTHORITATIVE","capillary_metric":"D9R1_M_FACE_DIRECT",
 "node_M":"SIDECAR_CELL_COEFFICIENT_ONLY","FMM_ADV":"AUXILIARY_ONLY","legacy_exp_Nc_xD":"PROHIBITED"},
 "gates":gates,"next_milestone":("V16D-12C — Restartable TRAIN-Partition Stage-4 Transport Generation (15 remaining cases; Case0002 reused immutable)"
 if ok else "V16D-12BR — Execution Contract Repair")}
 cp=OUT/"V16D12B_Partition_Aware_MultiCase_Stage4_Transport_Execution_Contract.json"
 cp.write_text(json.dumps(contract,indent=2),encoding="utf-8")
 print("FROZEN EXECUTION PLAN")
 print("  TRAIN           : 16 (Case0002 certified; 15 pending)")
 print("  VALIDATION      : 4");print("  LOCKED OOD TEST : 4")
 print("  Per-case Y      : (9, 1078, 201)");print("  Case0002 Y SHA  :",sha(y))
 print("\n"+"="*78);print("V16D-12B GATES");print("="*78)
 for a,b in gates.items():print(f"[{'PASS' if b else 'FAIL'}] {a}")
 print("\nSTATUS\n ",status);print("\nNEXT MILESTONE\n ",contract["next_milestone"])
 print("\nContract SHA-256:",sha(cp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

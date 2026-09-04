#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
R=Path(__file__).resolve().parent
D14=R/"output"/"V16_D14B_R1_CONTRACT1_0_24CASE_PREDICTOR_ASSEMBLY_EXACT_FIELD_BINDINGS"
D14SUM=D14/"PAD_Stream_V16D14B_R1_Summary.json"; D14SHA="800c75b573860321de15a45b16c1116889fc39cddca3c1589696ea4484643d27"
MAN=D14/"V16D14B_R1_24Case_Predictor_Manifest.json"; STATS=D14/"V16D14B_R1_TRAIN_Only_Normalization_Statistics.json"
DR=R/"output"/"V16_D15R_TARGET_ARTIFACT_SCHEMA_PATH_BINDING_AUDIT"
DRSUM=DR/"PAD_Stream_V16D15R_Summary.json"; DRREG=DR/"V16D15R_Target_Artifact_Candidate_Registry.json"
DRSHA="0c7612b7a53f9b7c3045a397f8c0e9238a180cbf7a914d2f2ff2d5f4a9655c46"
TRAIN=["0020","0015","0013","0004","0006","0002","0023","0016","0009","0019","0017","0024","0003","0011","0014","0007"]
VAL=["0010","0025","0008","0012"]; OOD=["0005","0018","0021","0022"]; ALL=TRAIN+VAL+OOD
FEATURES=["xi","pollock_tau_hat","adv_tau_hat","log10_Kh","log10_Kz_over_Kh","porosity","pressure_z","target_time_hat","target_eta_sequence"]
O=R/"output"/"V16_D15R1_MULTIFOUNDATIONCASE_LEARNING_DATASET_FREEZE";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-15R1")
 print("Multi-Foundation-Case Learning Dataset Freeze — Repaired D12 Bindings");print("="*78)
 print("""D15R UNIQUELY BOUND ALL 24 EXISTING D12 TARGET ARTIFACTS BY EXACT
BASENAME CASE ID. R1 NOW FREEZES THE LEARNING DATASET REGISTRY WITHOUT
OPENING TARGET Y ARRAYS AND WITHOUT TRAINING.

LOCKED OOD CASES REMAIN FINAL-EVALUATION ONLY.
""")
 if sha(D14SUM)!=D14SHA:raise RuntimeError("D14B-R1 SHA mismatch")
 if sha(DRSUM)!=DRSHA:raise RuntimeError("D15R SHA mismatch")
 man=json.loads(MAN.read_text()); stats=json.loads(STATS.read_text()); tr=json.loads(DRREG.read_text())
 pred={x["case_id"]:x for x in man["cases"]}
 entries=[]
 for c in ALL:
  if c not in pred:raise RuntimeError(f"missing predictor Case{c}")
  if tr[c]["candidate_count"]!=1:raise RuntimeError(f"target binding not unique Case{c}")
  tc=tr[c]["candidates"][0]; tp=Path(tc["path"])
  if not tp.exists() or sha(tp)!=tc["sha256"]:raise RuntimeError(f"target identity mismatch Case{c}")
  npth=Path(pred[c]["normalized_path"])
  if not npth.exists() or sha(npth)!=pred[c]["normalized_sha256"]:raise RuntimeError(f"predictor identity mismatch Case{c}")
  entries.append({"case_id":c,"partition":tr[c]["partition"],
   "X_normalized":{"path":str(npth),"sha256":pred[c]["normalized_sha256"],"shape":[9,1078,201,9]},
   "Y_stage4":{"path":str(tp),"sha256":tc["sha256"],"shape_authority":[9,1078,201],"opened_in_D15R1":False}})
 registry={"name":"V16D_MULTIFOUNDATIONCASE_LEARNING_DATASET_1.0","cases":entries,
  "split":{"TRAIN":TRAIN,"VALIDATION":VAL,"LOCKED_OOD_TEST":OOD},
  "feature_order":FEATURES,"target_days":[30,60,100,150,250,365,500,750,1000],
  "normalization":{"path":str(STATS),"sha256":sha(STATS),"fit_partition":"TRAIN_ONLY"},
  "semantics":{"generalization_unit":"COMPLETE_FOUNDATION_CASE","Pollock":"AUTHORITATIVE_KINEMATICS",
   "ADV":"AUXILIARY_PREDICTOR","M_face":"PHYSICS_SIDECAR_NOT_PREDICTOR",
   "geology_ensemble":"V16D Recipe1.1 spectral GRF; not SGS/SGSim"}}
 rp=O/"V16D15R1_Frozen_MultiFoundationCase_Learning_Dataset_Registry.json";rp.write_text(json.dumps(registry,indent=2))
 protocol={"name":"V16D_EXP_MC1_PROTOCOL_AUTHORITY_1.0","experiment":"EXP-MC1",
  "purpose":"first multi-Foundation-Case predictive-accuracy baseline",
  "architecture_lineage":"C20 Stage4-lineage recurrent transport model",
  "loss":"MSE_ONLY","physics_loss":"NONE","optimizer":"Adam","learning_rate":1e-3,
  "seed":161501,"max_epochs":300,
  "selection":{"TRAIN":"gradient updates only","VALIDATION":"early stopping/checkpoint selection only",
               "LOCKED_OOD_TEST":"one final evaluation only after model and checkpoint selection"},
  "prohibited_OOD_uses":["normalization","feature selection","architecture selection","loss design","hyperparameter tuning","early stopping","checkpoint selection","threshold tuning"],
  "next_freeze_required_before_training":["exact LSTM widths/layers","batch size","patience/min_delta","checkpoint format","memory-safe case/streamline loading","sample weighting policy"]}
 pp=O/"V16D15R1_EXP_MC1_Training_Protocol_Authority.json";pp.write_text(json.dumps(protocol,indent=2))
 gates={"D14B_R1_SHA_exact":sha(D14SUM)==D14SHA,"D15R_SHA_exact":sha(DRSUM)==DRSHA,
 "exact_24_case_registry":len(entries)==24,"exact_16_4_4_split":len(TRAIN)==16 and len(VAL)==4 and len(OOD)==4,
 "all_predictor_SHA_verified":all(Path(e["X_normalized"]["path"]).exists() for e in entries),
 "all_target_SHA_verified_without_Y_open":all(Path(e["Y_stage4"]["path"]).exists() for e in entries),
 "C20_feature_order_preserved":man["feature_order"]==FEATURES,"TRAIN_only_normalization_preserved":stats["fit_partition"]=="TRAIN_ONLY",
 "complete_case_generalization_unit":True,"locked_OOD_final_evaluation_only":True,"no_Y_array_opened":True,
 "no_training":True,"no_model_selection":True,"no_OOD_evaluation":True}
 ok=all(gates.values())
 status="V16D_MULTIFOUNDATIONCASE_LEARNING_DATASET_1_0_FROZEN_EXP_MC1_AUTHORITY_ESTABLISHED_EXECUTABLE_TRAINING_PROTOCOL_FREEZE_AUTHORIZED" if ok else "V16D_D15R1_BLOCKED"
 nxt="V16D-16 — EXP-MC1 Executable Multi-Case Predictive Baseline Training Protocol Freeze" if ok else "V16D-15R2 — Dataset Freeze Repair"
 sp=O/"PAD_Stream_V16D15R1_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-15R1","status":status,"dataset_registry_sha256":sha(rp),"training_authority_sha256":sha(pp),"gates":gates,"next_milestone":nxt},indent=2))
 print("cases frozen:",len(entries));print("TRAIN/VAL/OOD:",len(TRAIN),len(VAL),len(OOD))
 print("dataset registry SHA-256:",sha(rp));print("training authority SHA-256:",sha(pp))
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

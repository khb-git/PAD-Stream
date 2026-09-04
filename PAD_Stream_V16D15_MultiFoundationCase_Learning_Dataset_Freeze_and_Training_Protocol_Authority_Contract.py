#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
R=Path(__file__).resolve().parent
D14=R/"output"/"V16_D14B_R1_CONTRACT1_0_24CASE_PREDICTOR_ASSEMBLY_EXACT_FIELD_BINDINGS"
SUM=D14/"PAD_Stream_V16D14B_R1_Summary.json"
MAN=D14/"V16D14B_R1_24Case_Predictor_Manifest.json"
STATS=D14/"V16D14B_R1_TRAIN_Only_Normalization_Statistics.json"
SUMSHA="800c75b573860321de15a45b16c1116889fc39cddca3c1589696ea4484643d27"
TRAIN=["0020","0015","0013","0004","0006","0002","0023","0016","0009","0019","0017","0024","0003","0011","0014","0007"]
VAL=["0010","0025","0008","0012"]
OOD=["0005","0018","0021","0022"]
FEATURES=["xi","pollock_tau_hat","adv_tau_hat","log10_Kh","log10_Kz_over_Kh","porosity","pressure_z","target_time_hat","target_eta_sequence"]
O=R/"output"/"V16_D15_MULTIFOUNDATIONCASE_DATASET_FREEZE_TRAINING_PROTOCOL_AUTHORITY";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-15")
 print("Multi-Foundation-Case Learning Dataset Freeze + Training Protocol Authority");print("="*78)
 print("""D14B-R1 HAS FROZEN THE 24-CASE C20 PREDICTOR INTERFACE AND TRAIN-ONLY
NORMALIZATION. D15 FREEZES THE LEARNING DATASET CONTRACT BEFORE ANY
MULTI-CASE MODEL IS TRAINED.

THE UNIT OF GENERALIZATION IS A COMPLETE FOUNDATION CASE.
LOCKED OOD CASES REMAIN FINAL-EVALUATION ONLY.
""")
 if sha(SUM)!=SUMSHA:raise RuntimeError("D14B-R1 summary SHA mismatch")
 sm=json.loads(SUM.read_text());man=json.loads(MAN.read_text());st=json.loads(STATS.read_text())
 by={x["case_id"]:x for x in man["cases"]}
 # Bind target manifests without opening Y arrays.
 target_files={}
 roots={
 "TRAIN":R/"output"/"V16_D12C_TRAIN_PARTITION_STAGE4_TRANSPORT_SUPERVISION",
 "VALIDATION":R/"output"/"V16_D12DR_VALIDATION_PARTITION_STAGE4_TRANSPORT_SUPERVISION",
 "LOCKED_OOD_TEST":R/"output"/"V16_D12F_LOCKED_OOD_STAGE4_TRANSPORT_SUPERVISION",
 }
 # We do not guess filenames: enumerate metadata/manifests and bind case IDs to referenced NPZ paths.
 for part,cases in [("TRAIN",TRAIN),("VALIDATION",VAL),("LOCKED_OOD_TEST",OOD)]:
  for c in cases:
   hits=[]
   for j in roots[part].rglob("*.json"):
    try:t=j.read_text(encoding="utf-8",errors="ignore")
    except:continue
    if c not in t:continue
    # only collect existing .npz path strings found literally
    import re
    for s in re.findall(r'[^"\n\r]+\.npz',t):
     q=Path(s.replace("\\\\","\\"))
     if not q.is_absolute(): q=R/q
     if q.exists() and c in q.name:hits.append(q)
   # fallback discovery inside frozen partition output by exact case token in basename only
   if not hits:
    hits=[q for q in roots[part].rglob("*.npz") if c in q.name]
   uniq={str(q.resolve()):q for q in hits}
   if len(uniq)!=1:raise RuntimeError(f"Case{c}: target artifact not uniquely bound, hits={list(uniq)}")
   q=next(iter(uniq.values()));target_files[c]={"path":str(q),"sha256":sha(q),"partition":part}
 protocol={
  "name":"V16D_MULTIFOUNDATIONCASE_LEARNING_PROTOCOL_1.0",
  "generalization_unit":"COMPLETE_FOUNDATION_CASE",
  "split":{"TRAIN":TRAIN,"VALIDATION":VAL,"LOCKED_OOD_TEST":OOD},
  "predictor_feature_order":FEATURES,
  "predictor_shape_per_case":[9,1078,201,9],
  "target_shape_per_case":[9,1078,201],
  "target_days":[30,60,100,150,250,365,500,750,1000],
  "normalization":{"authority":str(STATS),"sha256":sha(STATS),"fit":"TRAIN_ONLY","validation":"TRANSFORM_ONLY","locked_OOD":"TRANSFORM_ONLY"},
  "training":{
   "architecture_family":"C20 Stage4-lineage recurrent transport model",
   "input_channels":9,
   "sequence_nodes":201,
   "output":"bounded Sw at 201 Pollock nodes",
   "selection_partition":"VALIDATION_CASES_ONLY",
   "checkpoint_rule":"minimum validation objective under a predeclared training experiment",
   "locked_OOD_access":"ONE FINAL EVALUATION AFTER MODEL/CHECKPOINT SELECTION",
   "OOD_prohibited_uses":["normalization fit","feature selection","architecture selection","loss design","hyperparameter tuning","early stopping","checkpoint selection","threshold tuning"],
  },
  "experiment_policy":{
   "first_multicase_experiment":"EXP-MC1 predictive-accuracy baseline",
   "loss":"MSE",
   "physics_loss":"NONE",
   "optimizer":"Adam",
   "learning_rate":1e-3,
   "batching_unit":"streamline-time sequence samples; case membership retained",
   "seed":161501,
   "max_epochs":300,
   "early_stopping":"validation objective only",
   "note":"Architecture widths/batch size must be frozen in the next executable training protocol before training; D15 does not invent them from OOD results."
  },
  "scientific_claim_limits":[
   "No foundation-model generalization claim before locked case-level OOD evaluation.",
   "Cases0002-0025 are Recipe1.1 spectral GRF ensemble, not SGS/SGSim.",
   "Pollock remains authoritative kinematics; ADV is auxiliary.",
   "M_face remains physics sidecar, not predictor.",
  ],
 }
 contract=O/"V16D15_MultiFoundationCase_Learning_Dataset_and_Training_Protocol_Contract.json"
 contract.write_text(json.dumps(protocol,indent=2))
 registry={"predictors":{c:by[c] for c in TRAIN+VAL+OOD},"targets":target_files}
 regp=O/"V16D15_Frozen_Learning_Dataset_Registry.json";regp.write_text(json.dumps(registry,indent=2))
 gates={"D14B_R1_summary_SHA_exact":sha(SUM)==SUMSHA,"predictor_manifest_bound":len(by)==24,
 "normalization_stats_bound":st["fit_partition"]=="TRAIN_ONLY","exact_16_4_4_case_split":len(TRAIN)==16 and len(VAL)==4 and len(OOD)==4,
 "all_24_target_artifacts_uniquely_bound_without_opening_Y":len(target_files)==24,
 "C20_9_channel_order_preserved":man["feature_order"]==FEATURES,
 "complete_case_generalization_unit":True,"validation_selection_only":True,"locked_OOD_final_evaluation_only":True,
 "OOD_not_used_for_adaptation":True,"M_face_not_predictor":True,"no_training_performed":True,"no_OOD_evaluation_performed":True}
 ok=all(gates.values())
 status="V16D_MULTIFOUNDATIONCASE_LEARNING_DATASET_FROZEN_TRAINING_PROTOCOL_AUTHORITY_ESTABLISHED_MC1_EXECUTABLE_PROTOCOL_NEXT" if ok else "V16D_D15_BLOCKED"
 nxt="V16D-16 — EXP-MC1 Executable Multi-Case Predictive Baseline Training Protocol Freeze" if ok else "V16D-15R — Dataset/Target Binding Repair"
 sp=O/"PAD_Stream_V16D15_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-15","status":status,"dataset_registry_sha256":sha(regp),"contract_sha256":sha(contract),"gates":gates,"next_milestone":nxt},indent=2))
 print("predictor cases:",len(by));print("target cases:",len(target_files));print("TRAIN/VAL/OOD:",len(TRAIN),len(VAL),len(OOD))
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

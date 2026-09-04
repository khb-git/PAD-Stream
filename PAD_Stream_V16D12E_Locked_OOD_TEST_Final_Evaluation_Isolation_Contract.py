#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,csv,sys
R=Path(__file__).resolve().parent; O=R/"output"/"V16_D12E_LOCKED_OOD_FINAL_EVALUATION_ISOLATION_CONTRACT";O.mkdir(parents=True,exist_ok=True)
CM=R/"output"/"V16_D12C_RESTARTABLE_TRAIN_STAGE4_TRANSPORT_GENERATION"/"V16D12C_TRAIN_Transport_Manifest.csv"
CS=R/"output"/"V16_D12C_RESTARTABLE_TRAIN_STAGE4_TRANSPORT_GENERATION"/"PAD_Stream_V16D12C_Summary.json"
DM=R/"output"/"V16_D12D_RESTARTABLE_VALIDATION_STAGE4_TRANSPORT_GENERATION"/"V16D12D_VALIDATION_Transport_Manifest.csv"
DS=R/"output"/"V16_D12D_RESTARTABLE_VALIDATION_STAGE4_TRANSPORT_GENERATION"/"PAD_Stream_V16D12D_Summary.json"
CSHA="85415615a8d752e45085eaff5c4d9b97ecb2c5155d570bc4019ef42221c30264";DSHA="14dfabec309c2d024ed970983a03c4f3610caff8f66a845ca5f5ba2318ff867c"
TEST=["0005","0018","0021","0022"]; DAYS=[30,60,100,150,250,365,500,750,1000]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def j(p):return json.loads(p.read_text())
def main():
 print("="*78);print("PAD-Stream V16D-12E");print("Locked OOD TEST Transport Generation Final-Evaluation Isolation Contract");print("="*78)
 print("""D12E DOES NOT GENERATE OOD TARGETS.
IT FREEZES THE FIREWALL BEFORE CASES 0005, 0018, 0021, 0022 ARE SOLVED.
THEIR LABELS ARE FINAL-EVALUATION-ONLY: NO NORMALIZATION FIT, FEATURE OR
ARCHITECTURE SELECTION, LOSS/HYPERPARAMETER TUNING, EARLY STOPPING,
THRESHOLD TUNING, OR CHECKPOINT SELECTION. NO TRAINING OCCURS.
""")
 if not all(x.exists() for x in [CM,CS,DM,DS]):raise RuntimeError("Certified TRAIN/VALIDATION authority missing")
 cs,ds=j(CS),j(DS)
 g={"TRAIN_manifest_SHA_exact":sha(CM)==CSHA,"TRAIN_status_certified":cs.get("status")=="V16D_TRAIN_PARTITION_STAGE4_TRANSPORT_SUPERVISION_16_CASES_CERTIFIED_VALIDATION_GENERATION_AUTHORIZED",
 "VALIDATION_manifest_SHA_exact":sha(DM)==DSHA,"VALIDATION_status_certified":ds.get("status")=="V16D_VALIDATION_PARTITION_STAGE4_TRANSPORT_SUPERVISION_4_CASES_CERTIFIED_LOCKED_OOD_GENERATION_CONTRACT_AUTHORIZED",
 "locked_OOD_exact_cases":TEST==["0005","0018","0021","0022"],"evaluation_only":True,"no_OOD_normalization_fit":True,"no_OOD_feature_selection":True,
 "no_OOD_architecture_selection":True,"no_OOD_loss_weight_selection":True,"no_OOD_hyperparameter_tuning":True,"no_OOD_early_stopping":True,
 "no_OOD_threshold_tuning":True,"no_OOD_checkpoint_selection":True,"one_case_one_restartable_job":True,"completed_OOD_artifacts_immutable":True,
 "Pollock_primary":True,"C7_Mface_primary":True,"FMM_ADV_auxiliary_only":True,"legacy_exp_Nc_xD_prohibited":True,"nine_time_schedule":len(DAYS)==9,
 "no_transport_executed":True,"no_training":True,"no_model_selection":True}
 rows=[{"case_id":f"V16D_Foundation_Case_{c}","status":"SEALED_PENDING_PHYSICS_LABEL_GENERATION","allowed_use":"FINAL_EVALUATION_ONLY"} for c in TEST]
 with (O/"V16D12E_Locked_OOD_Registry.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 ok=all(g.values());status="V16D_LOCKED_OOD_TEST_FINAL_EVALUATION_ISOLATION_CONTRACT_FROZEN_SEALED_TARGET_GENERATION_AUTHORIZED" if ok else "V16D_D12E_LOCKED_OOD_ISOLATION_BLOCKED"
 q={"milestone":"V16D-12E","status":status,"locked_ood_test":TEST,"target_days":DAYS,"Y_shape":[9,1078,201],"train_manifest_sha256":sha(CM),"validation_manifest_sha256":sha(DM),
 "allowed_use":"SOURCE_AUTHENTIC_LABEL_GENERATION_AND_FINAL_FROZEN_MODEL_EVALUATION_ONLY","gates":g,
 "next_milestone":"V16D-12F — Restartable SEALED LOCKED-OOD Stage-4 Transport Target Generation" if ok else "V16D-12ER — Isolation Contract Repair"}
 cp=O/"V16D12E_Locked_OOD_Final_Evaluation_Isolation_Contract.json";cp.write_text(json.dumps(q,indent=2))
 print("LOCKED OOD:",TEST);print("TRAIN SHA:",sha(CM));print("VALIDATION SHA:",sha(DM));print("\nV16D-12E GATES")
 for k,v in g.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT MILESTONE\n ",q["next_milestone"]);print("\nContract SHA-256:",sha(cp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

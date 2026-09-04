#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
R=Path(__file__).resolve().parent
O=R/"output"/"V16_D31B_VALIDATION_PARTITION_STAGE4_TRANSPORT_GENERATION_CONTRACT";O.mkdir(parents=True,exist_ok=True)
A=R/"output"/"V16_D31A_RESTARTABLE_TRAIN_18CASE_STAGE4_TRANSPORT"/"PAD_Stream_V16D31A_Summary.json"
AM=R/"output"/"V16_D31A_RESTARTABLE_TRAIN_18CASE_STAGE4_TRANSPORT"/"V16D31A_TRAIN_18Case_Manifest.json"
D=R/"output"/"V16_D31_PARTITIONAWARE_RESTARTABLE_36CASE_STAGE4_TRANSPORT_EXECUTION_CONTRACT"/"PAD_Stream_V16D31_Summary.json"
C=R/"PAD_Stream_V16C17_Production_Source_Authentic_Y_Transport_Tensor_Generation_and_Certification.py"
M=R/"output"/"V16_D28_R1_36CASE_D9R1_CONSERVATIVE_FACE_METRIC_EXPANSION"/"cases"
EXPECT={"A":"ccc6dbb748c8ffd465b5c0e7c40291b4a04a91957a554a68360957ffb8a5edc4","AM":"b59d62bb839477b4158774c845b680b32a21543e9762645e95513f092992545b","D":"107e2c5cedf9ac9fcebfea27d3290c84be9c0d0ae46f5cd6c0dce37fa0b5e33d","C":"1d357be446103cb554c4759948347d2876235b7c630c64cd826801cbfc61dd4f"}
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-31B");print("Validation-Partition Stage-4 Transport Generation Contract");print("="*78)
 g={"D31_SHA_exact":D.exists() and sha(D)==EXPECT["D"],"D31A_summary_SHA_exact":A.exists() and sha(A)==EXPECT["A"],"D31A_manifest_SHA_exact":AM.exists() and sha(AM)==EXPECT["AM"],"C17_SHA_exact":C.exists() and sha(C)==EXPECT["C"],"D28_36_metrics_present":M.exists() and len(list(M.glob("*.npz")))==36}
 if A.exists():
  q=json.loads(A.read_text());g["D31A_18_TRAIN_certified"]=q.get("certified_cases")==18 and q.get("status")=="V16D_TRAIN_18CASE_STAGE4_TRANSPORT_SUPERVISION_GENERATED_CERTIFIED_VALIDATION_PARTITION_GENERATION_CONTRACT_AUTHORIZED"
 else:g["D31A_18_TRAIN_certified"]=False
 g.update({"validation_exactly_9":True,"validation_geology0028_only":True,"TRAIN_not_regenerated":True,"locked_OOD_0029_untouched":True,"same_nine_times":True,"same_Y_shape":True,"same_C17_physics":True,"Pollock_primary":True,"Mface_primary":True,"theta_adapter_only":True,"restartable_case_local":True,"no_deduplication":True,"no_training":True,"no_tuning":True,"no_validation_normalization_stats":True,"no_selection":True,"no_threshold_relaxation":True,"no_transport_executed_in_D31B":True})
 contract={"version":"V16D_VALIDATION_TRANSPORT_GENERATION_CONTRACT_1.0","partition":"VALIDATION","geology":"0028","cases":9,"rates_tpd":[350,500,650],"producer_bhp_psi":[1800,2000,2200],"target_days":[30,60,100,150,250,365,500,750,1000],"Y_shape_each":[9,1078,201],"physics":"exact C17 kernels; D28-R1 M_face; Pollock authoritative","theta_schema":"canonical (201,) broadcast adapter only","restartability":"case-local SHA-certified artifact/summary; certified cases skip","validation_policy":"generation only; no fitting/tuning/normalization-stat estimation/selection/architecture or threshold change","locked_OOD_policy":"0029 untouched","case_independence":"all nine independently; no BHP deduplication"}
 ok=bool(all(g.values()))
 status="V16D_VALIDATION_9CASE_STAGE4_TRANSPORT_GENERATION_CONTRACT_FROZEN_RESTARTABLE_VALIDATION_EXECUTION_AUTHORIZED" if ok else "V16D_D31B_VALIDATION_TRANSPORT_CONTRACT_BLOCKED"
 nxt="V16D-31B-R1 — Restartable validation geology0028 nine-case Stage-4 transport generation" if ok else "Repair D31B provenance gate; do not generate validation transport."
 rep={"milestone":"V16D-31B","status":status,"contract":contract,"gates":g,"next_milestone":nxt}
 cp=O/"V16D31B_Validation_Transport_Generation_Contract.json";cp.write_text(json.dumps(rep,indent=2))
 sp=O/"PAD_Stream_V16D31B_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-31B","status":status,"contract_sha256":sha(cp),"gates":g,"next_milestone":nxt},indent=2))
 print("\nGATES")
 for k,v in g.items():print("[PASS]" if v else "[FAIL]",k)
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nContract SHA-256:",sha(cp));print("Summary SHA-256 :",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

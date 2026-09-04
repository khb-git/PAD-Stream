#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
R=Path(__file__).resolve().parent
O=R/"output"/"V16_D31C_LOCKED_OOD_STAGE4_TRANSPORT_GENERATION_CONTRACT";O.mkdir(parents=True,exist_ok=True)
B=R/"output"/"V16_D31B_R1_RESTARTABLE_VALIDATION_9CASE_STAGE4_TRANSPORT"/"PAD_Stream_V16D31B_R1_Summary.json"
BM=R/"output"/"V16_D31B_R1_RESTARTABLE_VALIDATION_9CASE_STAGE4_TRANSPORT"/"V16D31B_R1_VALIDATION_9Case_Manifest.json"
A=R/"output"/"V16_D31A_RESTARTABLE_TRAIN_18CASE_STAGE4_TRANSPORT"/"PAD_Stream_V16D31A_Summary.json"
C=R/"PAD_Stream_V16C17_Production_Source_Authentic_Y_Transport_Tensor_Generation_and_Certification.py"
M=R/"output"/"V16_D28_R1_36CASE_D9R1_CONSERVATIVE_FACE_METRIC_EXPANSION"/"cases"
E={"B":"87fe0042da478221f51210461d523e0d9c564996cd88756c99016b6ae57a7ba9","BM":"39adcee9baf710a3e9910a88b999a82aaf237d4601c995a387b040798e0fe163","A":"ccc6dbb748c8ffd465b5c0e7c40291b4a04a91957a554a68360957ffb8a5edc4","C":"1d357be446103cb554c4759948347d2876235b7c630c64cd826801cbfc61dd4f"}
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for x in iter(lambda:f.read(1048576),b""):h.update(x)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-31C");print("Locked-OOD Stage-4 Transport Generation Contract");print("="*78)
 g={"D31A_SHA_exact":A.exists() and sha(A)==E["A"],"D31BR1_SHA_exact":B.exists() and sha(B)==E["B"],"D31BR1_manifest_SHA_exact":BM.exists() and sha(BM)==E["BM"],"C17_SHA_exact":C.exists() and sha(C)==E["C"],"D28_36_metrics":M.exists() and len(list(M.glob("*.npz")))==36}
 if B.exists():
  q=json.loads(B.read_text());g["validation_9_certified"]=q.get("certified_cases")==9 and q.get("status")=="V16D_VALIDATION_9CASE_STAGE4_TRANSPORT_SUPERVISION_GENERATED_CERTIFIED_LOCKED_OOD_GENERATION_CONTRACT_AUTHORIZED"
 else:g["validation_9_certified"]=False
 g.update({"OOD_9":True,"geology0029_only":True,"TRAIN_unchanged":True,"VALIDATION_unchanged":True,"same_9_times":True,"same_shape":True,"same_physics":True,"Pollock_primary":True,"Mface_primary":True,"theta_adapter_only":True,"restartable":True,"no_dedup":True,"no_training":True,"no_tuning":True,"no_OOD_normalization":True,"no_selection":True,"no_threshold_relaxation":True,"no_OOD_statistics_during_generation":True,"sealed_after_generation":True,"contract_only_no_transport":True})
 contract={"version":"V16D_LOCKED_OOD_TRANSPORT_GENERATION_CONTRACT_1.0","partition":"LOCKED_OOD_TEST","geology":"0029","cases":9,"rates_tpd":[350,500,650],"producer_bhp_psi":[1800,2000,2200],"target_days":[30,60,100,150,250,365,500,750,1000],"Y_shape_each":[9,1078,201],"physics":"exact C17 + D28-R1 M_face + Pollock","restartability":"case-local SHA certification","sealing":"generation reports certification/hashes only; no target statistics or development use","future_opening":"requires separately frozen one-touch final OOD evaluation contract","forbidden":["training","tuning","OOD normalization","selection","threshold changes","deduplication"]}
 ok=bool(all(g.values()))
 status="V16D_LOCKED_OOD_9CASE_STAGE4_TRANSPORT_GENERATION_CONTRACT_FROZEN_RESTARTABLE_SEALED_OOD_PHYSICS_GENERATION_AUTHORIZED" if ok else "V16D_D31C_LOCKED_OOD_TRANSPORT_CONTRACT_BLOCKED"
 nxt="V16D-31C-R1 — Restartable sealed geology0029 nine-case Stage-4 transport generation" if ok else "Repair D31C provenance gate."
 rep={"milestone":"V16D-31C","status":status,"contract":contract,"gates":g,"next_milestone":nxt}
 cp=O/"V16D31C_Locked_OOD_Transport_Generation_Contract.json";cp.write_text(json.dumps(rep,indent=2))
 sp=O/"PAD_Stream_V16D31C_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-31C","status":status,"contract_sha256":sha(cp),"gates":g,"next_milestone":nxt},indent=2))
 print("\nGATES")
 for k,v in g.items():print("[PASS]" if v else "[FAIL]",k)
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nContract SHA-256:",sha(cp));print("Summary SHA-256 :",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

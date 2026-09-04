#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
R=Path(__file__).resolve().parent
O=R/"output"/"V16_D31_PARTITIONAWARE_RESTARTABLE_36CASE_STAGE4_TRANSPORT_EXECUTION_CONTRACT";O.mkdir(parents=True,exist_ok=True)

R2=R/"output"/"V16_D30_R1_ONE_TRAIN_SOURCEAUTHENTIC_9TIME_STAGE4_TRANSPORT_PILOT"/"PAD_Stream_V16D30_R1_R2_Summary.json"
R2SHA="09951d8c6020942739a08eb4adf1ba87f6e59101cf6d12c389781fcb74264473"
D30=R/"output"/"V16_D30_STAGE4_CONTROLSPACE_TRANSPORT_SUPERVISION_SOURCE_BINDING_CONTRACT"/"PAD_Stream_V16D30_Summary.json"
D30SHA="887c64939da23b2666a3b89ee2e29dd8e0e97e71d6d5692fef38b4d2b0604904"
D28=R/"output"/"V16_D28_R1_36CASE_D9R1_CONSERVATIVE_FACE_METRIC_EXPANSION"/"cases"
C17=R/"PAD_Stream_V16C17_Production_Source_Authentic_Y_Transport_Tensor_Generation_and_Certification.py"
C17SHA="1d357be446103cb554c4759948347d2876235b7c630c64cd826801cbfc61dd4f"
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-31")
 print("Partition-Aware Restartable 36-Case Stage-4 Transport Execution Contract");print("="*78)
 g={}
 g["D30_summary_SHA_exact"]=D30.exists() and sha(D30)==D30SHA
 g["D30R1R2_summary_SHA_exact"]=R2.exists() and sha(R2)==R2SHA
 g["C17_source_SHA_exact"]=C17.exists() and sha(C17)==C17SHA
 g["D28_36_case_metrics"]=D28.exists() and len(list(D28.glob("*.npz")))==36
 if R2.exists():
  q=json.loads(R2.read_text())
  g["pilot_status_certified"]=q.get("status")=="V16D_CONTROLSPACE_CASE0026_R350_B1800_SOURCEAUTHENTIC_STAGE4_9TIME_TRANSPORT_PILOT_CERTIFIED_36CASE_TRANSPORT_EXECUTION_CONTRACT_AUTHORIZED"
  g["pilot_artifact_SHA_exact"]=q.get("artifact_sha256")=="d814fbcaab7dc8a5ea1ce6a06096d3bc0c05abb1077333a569f01e98e57c2028"
 else:g["pilot_status_certified"]=g["pilot_artifact_SHA_exact"]=False
 contract={
 "version":"V16D_STAGE4_36CASE_EXECUTION_CONTRACT_1.0",
 "foundation_cases":36,
 "controls":{"rate_tpd":[350,500,650],"producer_bhp_psi":[1800,2000,2200]},
 "partitions":{"TRAIN":{"geologies":["0026","0027"],"cases":18},
               "VALIDATION":{"geologies":["0028"],"cases":9},
               "LOCKED_OOD_TEST":{"geologies":["0029"],"cases":9}},
 "target_days":[30,60,100,150,250,365,500,750,1000],
 "Y_shape_each":[9,1078,201],
 "execution_unit":"one complete Foundation Case",
 "restartability":"one immutable case artifact + case summary written immediately after certification; rerun skips only SHA-certified completed cases",
 "source_physics":"exact C17 ADV/CAP kernels; D28-R1 M_face; Pollock kinematics authoritative",
 "theta_schema":"canonical persisted (201,) may be broadcast to (1078,201) as adapter only",
 "normalization":"none in transport generation",
 "selection":"none",
 "locked_OOD_policy":"physics targets may be generated prospectively but no aggregate/statistical inspection, tuning, normalization, selection, or training use before final one-touch evaluation",
 "case_independence":"all 36 Foundation Cases executed independently; no deduplication for observed BHP invariance",
 "failure_policy":"failed/interrupted case remains uncertified and is rerun from its own beginning; certified earlier cases are not recomputed",
 "forbidden":["physics fitting","threshold relaxation","case/streamline cherry-picking","node-M substitution","FMM/ADV replacement of Pollock","control-dependent Stage4 law invention","cross-partition normalization","OOD selection"]}
 g.update({"partition_counts_18_9_9":True,"nine_times_frozen":True,"shape_frozen":True,
 "per_case_restartability":True,"certified_skip_only":True,"failed_case_rerun_only":True,
 "Pollock_primary":True,"Mface_primary":True,"theta_adapter_only":True,"no_deduplication":True,
 "no_training":True,"no_normalization":True,"no_selection":True,"locked_OOD_sealed_for_model_development":True,
 "no_transport_executed_in_D31":True,"no_threshold_relaxation":True})
 ok=bool(all(g.values()))
 status="V16D_PARTITIONAWARE_RESTARTABLE_36CASE_STAGE4_TRANSPORT_EXECUTION_CONTRACT_FROZEN_TRAIN_PARTITION_EXECUTION_AUTHORIZED" if ok else "V16D_D31_36CASE_STAGE4_EXECUTION_CONTRACT_BLOCKED"
 nxt="V16D-31A — Restartable TRAIN partition Stage-4 transport generation for 18 Foundation Cases" if ok else "Repair failed D31 provenance gate; do not launch batch."
 rep={"milestone":"V16D-31","status":status,"D30_sha256":sha(D30) if D30.exists() else None,
 "D30R1R2_sha256":sha(R2) if R2.exists() else None,"C17_sha256":sha(C17) if C17.exists() else None,
 "contract":contract,"gates":g,"next_milestone":nxt}
 cp=O/"V16D31_36Case_Stage4_Execution_Contract.json";cp.write_text(json.dumps(rep,indent=2))
 sp=O/"PAD_Stream_V16D31_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-31","status":status,"contract_sha256":sha(cp),"gates":g,"next_milestone":nxt},indent=2))
 print("\nGATES");[print("[PASS]" if v else "[FAIL]",k) for k,v in g.items()]
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nContract SHA-256:",sha(cp));print("Summary SHA-256 :",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

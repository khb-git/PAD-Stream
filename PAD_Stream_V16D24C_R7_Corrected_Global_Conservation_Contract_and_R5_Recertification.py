#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
import numpy as np
R=Path(__file__).resolve().parent
S6=R/"output"/"V16_D24C_R6_GLOBAL_CONSERVATION_METRIC_SEMANTICS_AUDIT"/"PAD_Stream_V16D24C_R6_Summary.json"
SHA6="efb3b52e3f4fff88f7205d6221b8646a04f5c8a703cc427b36add7500c09e5dc"
S5=R/"output"/"V16_D24C_R5_MATCHED_SG3_SG4_0026_TRAIN_PILOT"/"PAD_Stream_V16D24C_R5_Summary.json"
SHA5="983e5cf3723bcc42913e8f499aab98481013b159e74538d82390c038c4b33aa0"
ART=R/"output"/"V16_D24C_R5_MATCHED_SG3_SG4_0026_TRAIN_PILOT"/"V16D24CR5_Geology0026_TRAIN_350tpd_1800psi_MatchedFlow.npz"
O=R/"output"/"V16_D24C_R7_CORRECTED_GLOBAL_CONSERVATION_CONTRACT_RECERTIFICATION";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-24C-R7")
 print("Corrected Global Conservation Contract + Existing R5 Pilot Recertification");print("="*78)
 gates={"R6_SHA_exact":sha(S6)==SHA6,"R5_SHA_exact":sha(S5)==SHA5,"R5_artifact_exists":ART.exists()}
 if not all(gates.values()):raise RuntimeError("authority pre-gate failure")
 z=np.load(ART);div=np.asarray(z["divergence"],float);ws=np.asarray(z["well_source"],float)
 residual=div-ws
 local=float(np.linalg.norm(residual.ravel())/max(np.linalg.norm(ws.ravel()),1e-30))
 abs_global=abs(float(residual.sum()))
 gross=float(np.abs(ws).sum())
 inj=float(ws[ws>0].sum());prod=float(-ws[ws<0].sum())
 throughput=max(abs(inj),abs(prod),1e-30)
 global_gross=abs_global/max(gross,1e-30)
 global_throughput=abs_global/throughput
 net=float(ws.sum())
 gates["local_rel_L2_le_1e_9"]=local<=1e-9
 gates["global_gross_scaled_le_1e_9"]=global_gross<=1e-9
 gates["global_throughput_scaled_le_1e_9"]=global_throughput<=1e-9
 gates["balanced_injection_production_rel_le_1e_9"]=abs(inj-prod)/throughput<=1e-9
 gates["net_source_near_zero"]=abs(net)/max(gross,1e-30)<=1e-9
 contract={
  "id":"V16D_CONSERVATION_CERTIFICATION_1.0",
  "local_metric":"||div(Q)-q_well||_2 / ||q_well||_2",
  "local_threshold":1e-9,
  "global_primary_metric":"|sum(div(Q)-q_well)| / sum(|q_well|)",
  "global_primary_threshold":1e-9,
  "global_secondary_metric":"|sum(div(Q)-q_well)| / max(Q_injection,Q_production)",
  "global_secondary_threshold":1e-9,
  "well_balance_metric":"|Q_injection-Q_production| / max(Q_injection,Q_production)",
  "well_balance_threshold":1e-9,
  "deprecated_metric":"|sum(div(Q)-q_well)| / |sum(q_well)|",
  "deprecated_reason":"For balanced closed/no-flow systems sum(q_well) is physically approximately zero, so the denominator is ill-conditioned. It must not be used as a certification denominator.",
  "scope":"Prospective V16D control-space flow certification. Does not rewrite historical V15/earlier V16 results.",
  "physics":"No governing equation, solver, flux, well, or tolerance was altered; only the dimensionless global normalization is corrected."
 }
 cp=O/"V16D24C_R7_Conservation_Certification_Contract_1p0.json";cp.write_text(json.dumps(contract,indent=2))
 recert={"source_artifact":str(ART.relative_to(R)),"source_artifact_sha256":sha(ART),
 "controls":{"geology":"0026","split":"TRAIN","injection_tonnes_day":350.0,"producer_BHP_psi":1800.0},
 "metrics":{"local_relative_L2":local,"absolute_global_residual_m3_s":abs_global,"gross_well_throughput_m3_s":gross,
 "injection_m3_s":inj,"production_m3_s":prod,"net_well_source_m3_s":net,
 "global_gross_scaled":global_gross,"global_throughput_scaled":global_throughput,
 "well_balance_relative":abs(inj-prod)/throughput},"gates":gates}
 rp=O/"V16D24C_R7_R5_Pilot_Recertification.json";rp.write_text(json.dumps(recert,indent=2))
 ok=all(gates.values())
 status="V16D_GEOLOGY0026_350TPD_1800PSI_MATCHED_CONTROL_PILOT_RECERTIFIED_CONSERVATIVE_36CASE_FLOW_ENSEMBLE_AUTHORIZED" if ok else "V16D_D24C_R7_RECERTIFICATION_BLOCKED"
 nxt="V16D-25 — D7B-Derived 36-Foundation-Case Control-Space SG2/SG3/SG4 Flow Ensemble Execution" if ok else "Diagnose recertification gate; do not batch."
 sp=O/"PAD_Stream_V16D24C_R7_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-24C-R7","status":status,
 "contract_sha256":sha(cp),"recertification_sha256":sha(rp),"gates":gates,"next_milestone":nxt},indent=2))
 print("\nRECERTIFIED METRICS")
 print(f"  local relative L2              : {local:.16e}")
 print(f"  absolute global residual m3/s  : {abs_global:.16e}")
 print(f"  global / gross well throughput : {global_gross:.16e}")
 print(f"  global / one-way throughput    : {global_throughput:.16e}")
 print(f"  injection m3/s                 : {inj:.16e}")
 print(f"  production m3/s                : {prod:.16e}")
 print(f"  well balance relative          : {abs(inj-prod)/throughput:.16e}")
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,importlib.util,re,sys
import numpy as np
R=Path(__file__).resolve().parent
S=R/"output"/"V16_D24C_R5_MATCHED_SG3_SG4_0026_TRAIN_PILOT"/"PAD_Stream_V16D24C_R5_Summary.json"
SSHA="983e5cf3723bcc42913e8f499aab98481013b159e74538d82390c038c4b33aa0"
ART=R/"output"/"V16_D24C_R5_MATCHED_SG3_SG4_0026_TRAIN_PILOT"/"V16D24CR5_Geology0026_TRAIN_350tpd_1800psi_MatchedFlow.npz"
SG4=R/"PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SHA4="86a1c88ffc35033314ae6598ade23f0bebfa709f62cbe2cbef1830cd607e0af9"
O=R/"output"/"V16_D24C_R6_GLOBAL_CONSERVATION_METRIC_SEMANTICS_AUDIT";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-24C-R6")
 print("Global Conservation Metric Semantics Audit");print("="*78)
 gates={"R5_SHA_exact":sha(S)==SSHA,"SG4_SHA_exact":sha(SG4)==SHA4,"R5_artifact_exists":ART.exists()}
 if not all(gates.values()):raise RuntimeError("authority pre-gate failure")
 z=np.load(ART);div=np.asarray(z["divergence"],float);ws=np.asarray(z["well_source"],float)
 ds=float(div.sum());wss=float(ws.sum());res=float((div-ws).sum())
 local=float(np.linalg.norm((div-ws).ravel())/max(np.linalg.norm(ws.ravel()),1e-30))
 # Correct global residual scale must not divide by a near-zero NET well-source sum
 # in a balanced injector/producer system. Use gross source/sink throughput.
 gross=float(np.sum(np.abs(ws)))
 global_gross=abs(res)/max(gross,1e-30)
 inj=float(ws[ws>0].sum());prod=float(-ws[ws<0].sum())
 throughput=max(abs(inj),abs(prod),1e-30)
 global_throughput=abs(res)/throughput
 print("\nR5 ARTIFACT CONSERVATION ACCOUNTING")
 print(f"  sum(divergence)          = {ds:.16e} m3/s")
 print(f"  sum(well_source)         = {wss:.16e} m3/s")
 print(f"  sum(divergence-source)   = {res:.16e} m3/s")
 print(f"  gross |well_source|      = {gross:.16e} m3/s")
 print(f"  injection source total   = {inj:.16e} m3/s")
 print(f"  production sink total    = {prod:.16e} m3/s")
 print(f"  local relative L2        = {local:.16e}")
 print(f"  global/gross metric      = {global_gross:.16e}")
 print(f"  global/throughput metric = {global_throughput:.16e}")
 # Inspect frozen SG4's own conservation metric implementation.
 t=SG4.read_text(encoding="utf-8",errors="replace");lines=t.splitlines()
 ev=[]
 for i,l in enumerate(lines,1):
  if 500<=i<=590 or re.search(r"global.*mismatch|mass.*balance|conservation",l,re.I):
   if re.search(r"global|well_source|diverg|mismatch|balance|conserv|residual|sum\(",l,re.I):
    ev.append({"line":i,"text":l})
 print("\nFROZEN SG4 CONSERVATION EVIDENCE")
 for x in ev[:100]:print(f"  L{x['line']}: {x['text'][:220]}")
 gates["R5_local_conservation_passed"]=local<=1e-9
 gates["net_well_source_is_near_zero_relative_to_gross"]=abs(wss)/max(gross,1e-30)<=1e-9
 gates["global_residual_gross_scaled_le_1e_9"]=global_gross<=1e-9
 gates["global_residual_throughput_scaled_le_1e_9"]=global_throughput<=1e-9
 gates["R5_global_failure_identified_as_denominator_pathology"]=(
   abs(wss) < 1e-9*gross and global_gross<=1e-9 and local<=1e-9)
 report={"milestone":"V16D-24C-R6","accounting":{"sum_divergence_m3_s":ds,"sum_well_source_m3_s":wss,
 "sum_residual_m3_s":res,"gross_well_source_m3_s":gross,"injection_m3_s":inj,"production_m3_s":prod,
 "local_relative_L2":local,"global_gross_scaled":global_gross,"global_throughput_scaled":global_throughput},
 "diagnosis":"R5 divided the global residual by abs(net well_source). For a balanced no-flow system net source is physically ~0, making that denominator ill-conditioned. This can report O(1) despite machine-small absolute residual. Gross/throughput scaling is the meaningful dimensionless global check.",
 "frozen_SG4_evidence":ev,"gates":gates}
 rp=O/"V16D24C_R6_Global_Conservation_Semantics_Report.json";rp.write_text(json.dumps(report,indent=2))
 ok=all(gates.values())
 status="V16D_R5_GLOBAL_GATE_DENOMINATOR_PATHOLOGY_CONFIRMED_CONSERVATION_CERTIFICATION_REFORMULATION_AUTHORIZED" if ok else "V16D_D24C_R6_CONSERVATION_DIAGNOSIS_BLOCKED"
 nxt="V16D-24C-R7 — Freeze corrected global conservation metric and recertify existing R5 pilot without rerunning physics" if ok else "Inspect absolute/global accounting and frozen SG4 semantics; do not batch."
 sp=O/"PAD_Stream_V16D24C_R6_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-24C-R6","status":status,"report_sha256":sha(rp),"gates":gates,"next_milestone":nxt},indent=2))
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

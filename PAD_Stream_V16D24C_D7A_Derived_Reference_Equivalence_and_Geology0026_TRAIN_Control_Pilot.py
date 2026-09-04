#!/usr/bin/env python3
from pathlib import Path
import ast,hashlib,json,re,sys
R=Path(__file__).resolve().parent
S=R/"output"/"V16_D24B_R2_CORRECTED_D7_ROLE_AUDIT"/"PAD_Stream_V16D24B_R2_Summary.json"
SSHA="b0a4a3539e3e8f0132a66507faef65712b68eddd2162db744f0e96365fe48a32"
D7A=R/"PAD_Stream_V16D7A_SourceBound_SG2_SG3_SG4_Adapter_and_Case0002_Pilot.py"
D7ASHA="3bdb11fe60703c05ffd27ea2eab122badcf2894406ff7399f9f55af261038452"
SG3=R/"PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3SHA="d3ba7b7be45636f6d3ee254fd6cb95268cef9e6f35e85d53b5793596cb22b14d"
G26=R/"output"/"V16_D23_FRESH_RECIPE1P1_GEOLOGIES_0026_0029"/"V16D_Geology_Case_0026_Recipe1p1.npz"
O=R/"output"/"V16_D24C_D7A_DERIVED_REFERENCE_EQUIVALENCE_TRAIN_PILOT";O.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def main():
 print("="*78);print("PAD-Stream V16D-24C")
 print("D7A-Derived Reference-Equivalence + Geology0026 TRAIN Control Pilot Builder")
 print("="*78)
 if sha(S)!=SSHA or sha(D7A)!=D7ASHA or sha(SG3)!=SG3SHA:raise RuntimeError("authority SHA mismatch")
 t=D7A.read_text(encoding="utf-8",errors="replace")
 # This builder derives an executable copy from D7A rather than recreating its internals.
 # We must identify D7A's CASE and OUT assignments exactly.
 case_pat=re.compile(r'(?m)^CASE\s*=.*$')
 out_pat=re.compile(r'(?m)^OUT\s*=.*$')
 cm=case_pat.findall(t);om=out_pat.findall(t)
 gates={"R2_SHA_exact":True,"D7A_SHA_exact":True,"SG3_SHA_exact":True,"G26_exists":G26.exists(),
        "one_D7A_CASE_assignment":len(cm)==1,"one_D7A_OUT_assignment":len(om)==1}
 print("D7A CASE assignment:",cm)
 print("D7A OUT assignment:",om)
 # We cannot safely execute until D7A's internal source-adapter mechanics are inspected
 # for the exact SG3 copy/patch/run mechanism. Extract those lines for the next generated executor.
 evidence=[]
 for i,l in enumerate(t.splitlines(),1):
  if re.search(r"SG2|SG3|SG4|runpy|subprocess|exec|compile|copy|write_text|CASE|artifact|pressure_psi|Qx|Qy|Qz",l,re.I):
   evidence.append({"line":i,"text":l})
 ep=O/"V16D24C_D7A_Execution_Mechanics_Evidence.json";ep.write_text(json.dumps(evidence,indent=2))
 # Strong mechanics indicators.
 txt="\n".join(x["text"] for x in evidence)
 gates["D7A_mechanics_evidence_extracted"]=len(evidence)>0
 gates["D7A_has_pressure_flux_outputs"]=all(x in t for x in ("pressure_psi","Qx","Qy","Qz"))
 # Freeze exact equivalence definition now.
 contract={"reference_equivalence":{
   "geology":"0026","control":{"rate_tonnes_day":500.0,"producer_BHP_psi":2000.0},
   "comparison":"unmodified frozen-SG3 path vs parameterized-adapter path on identical geology0026",
   "required":"array-level equality/near-machine precision for pressure and Qx/Qy/Qz; same conservation gates"},
 "new_control_pilot":{"geology":"0026","split":"TRAIN","control":{"rate_tonnes_day":350.0,"producer_BHP_psi":1800.0},
   "required":"finite pressure/fluxes, SG3 residual/mass-balance gates, SG4 local/global conservation gates"},
 "prohibitions":["no locked geology0029","no batch36 before pilot","no physics rewrite","no numerical fitting"]}
 cp=O/"V16D24C_Reference_and_Pilot_Execution_Contract.json";cp.write_text(json.dumps(contract,indent=2))
 if all(gates.values()):
  status="V16D_D7A_EXECUTION_MECHANICS_EXTRACTED_D24C_R1_EXECUTOR_GENERATION_AUTHORIZED"
  nxt="V16D-24C-R1 — Generate exact D7A-derived executable for reference equivalence and one 0026 TRAIN pilot"
 else:
  status="V16D_D24C_EXECUTOR_GENERATION_BLOCKED"
  nxt="Inspect D7A mechanics evidence; do not execute flow."
 sp=O/"PAD_Stream_V16D24C_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-24C","status":status,
 "mechanics_evidence_sha256":sha(ep),"contract_sha256":sha(cp),"gates":gates,"next_milestone":nxt},indent=2))
 print(f"\nExtracted D7A mechanics lines: {len(evidence)}")
 for x in evidence[:40]:print(f"  L{x['line']}: {x['text'][:200]}")
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not all(gates.values()):sys.exit(2)
if __name__=="__main__":main()

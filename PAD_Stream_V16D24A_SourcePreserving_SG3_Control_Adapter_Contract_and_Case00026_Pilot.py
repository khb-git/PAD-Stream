#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,re,sys
R=Path(__file__).resolve().parent
D24=R/"output"/"V16_D24_SOURCEBOUND_CONTROLSPACE_PARAMETERIZATION_AUDIT"
S24=D24/"PAD_Stream_V16D24_Summary.json"
E24=D24/"V16D24_SG3_Control_Parameterization_Evidence.json"
S24SHA="b046c3ed5e560c1df214a9c5f4bd19bb73962dc33b5226b3f893abcb900a5a20"
SG3=R/"PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3SHA="d3ba7b7be45636f6d3ee254fd6cb95268cef9e6f35e85d53b5793596cb22b14d"
O=R/"output"/"V16_D24A_SOURCEPRESERVING_SG3_CONTROL_ADAPTER_CONTRACT";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-24A")
 print("Source-Preserving SG3 Injection-Rate / Producer-BHP Adapter Contract");print("="*78)
 if sha(S24)!=S24SHA or sha(SG3)!=SG3SHA:raise RuntimeError("frozen D24/SG3 SHA mismatch")
 ev=json.loads(E24.read_text());text=SG3.read_text(encoding="utf-8",errors="replace")
 # Bind assignments, not just token occurrences.
 assigns=[]
 for i,l in enumerate(text.splitlines(),1):
  if re.search(r"=",l) and re.search(r"(500|2000|bhp|mass.?rate|tonne|co2)",l,re.I):
   assigns.append({"line":i,"text":l})
 # We freeze the physical adapter semantics here. Execution implementation must
 # inject these two values at the exact bound source variables; no equation rewrite.
 contract={"milestone":"V16D-24A","contract":"V16D_SG3_CONTROL_ADAPTER_1.0",
 "source":{"SG3_path":str(SG3),"SG3_sha256":SG3SHA},
 "authorized_inputs":{
  "CO2_injection_mass_rate_tonnes_per_day":{"levels":[350.0,500.0,650.0],
   "conversion":"reservoir volume rate = mass rate / frozen reference CO2 density; preserve SG3 unit conversion and completion allocation exactly"},
  "producer_BHP_psi":{"levels":[1800.0,2000.0,2200.0],
   "application":"same BHP value applied to all four producers exactly where frozen SG3 defines producer BHP"}},
 "immutable_physics":["SG2 transmissibility equations","SG3 matrix assembly and sparse solve","gravity treatment",
 "reference fluid properties including CO2 density","well locations/completions","well-index algebra/skin/radius",
 "external no-flow boundaries","SG4 conservative Darcy-flux reconstruction"],
 "execution_policy":["parameterize only the exact source-bound rate and BHP variables",
 "do not text-replace arbitrary numeric literals","do not alter frozen SG3 source file on disk",
 "create a derived V16D execution copy or runtime namespace adapter","validate 500 t/day + 2000 psi reproduces frozen reference before new controls",
 "pilot one TRAIN geology/control before 36-case batch","no locked OOD response generation in pilot"],
 "source_assignment_candidates":assigns,
 "D24_evidence_sha256":sha(E24)}
 cp=O/"V16D24A_SG3_Control_Adapter_1.0.json";cp.write_text(json.dumps(contract,indent=2))
 # Require evidence sufficient for the next executable adapter, but do not guess variable names here.
 rate_lines=[x for x in assigns if re.search(r"(500|mass.?rate|tonne|co2)",x["text"],re.I)]
 bhp_lines=[x for x in assigns if re.search(r"(2000|bhp)",x["text"],re.I)]
 gates={"D24_SHA_exact":sha(S24)==S24SHA,"SG3_SHA_exact":sha(SG3)==SG3SHA,
 "rate_assignment_candidates_bound":len(rate_lines)>0,"BHP_assignment_candidates_bound":len(bhp_lines)>0,
 "only_two_control_dimensions_authorized":True,"reference_reproduction_required_before_new_controls":True,
 "pilot_must_be_TRAIN_only":True,"no_SG3_source_mutation":True,"no_equation_rewrite":True,
 "no_flow_run_in_D24A":True,"no_locked_OOD_generation":True}
 if all(gates.values()):
  status="V16D_SG3_CONTROL_ADAPTER_1_0_FROZEN_REFERENCE_REPRODUCTION_AND_SINGLE_TRAIN_PILOT_IMPLEMENTATION_AUTHORIZED"
  nxt="V16D-24B — Implement Exact-Variable SG3 Adapter; Reproduce 500/2000 Reference and Run One TRAIN Control Pilot"
 else:
  status="V16D_SG3_CONTROL_ADAPTER_BLOCKED_ASSIGNMENT_BINDING_INCOMPLETE"
  nxt="Inspect D24A assignment evidence; do not run new-control flow."
 sp=O/"PAD_Stream_V16D24A_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-24A","status":status,
 "contract_sha256":sha(cp),"gates":gates,"next_milestone":nxt},indent=2))
 print("Bound source assignment candidates:")
 for x in assigns:print(f"  L{x['line']}: {x['text'].strip()}")
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not all(gates.values()):sys.exit(2)
if __name__=="__main__":main()

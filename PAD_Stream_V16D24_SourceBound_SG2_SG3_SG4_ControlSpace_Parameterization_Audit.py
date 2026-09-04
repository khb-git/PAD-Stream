#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,sys
R=Path(__file__).resolve().parent
D23=R/"output"/"V16_D23_FRESH_RECIPE1P1_GEOLOGIES_0026_0029"
S23=D23/"PAD_Stream_V16D23_Summary.json"
S23SHA="ba96b21a0a33f5b2aae5e3ad408d11fbc0421e55770b233652c78d856fe19c98"
EXPECTED={
"SG2":("PAD_Stream_V15SG2_Anisotropic_Transmissibility.py","8dfc3485682830ef854178720d32050b6b2e9d25befa7ee9669993df1e544416"),
"SG3":("PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py","d3ba7b7be45636f6d3ee254fd6cb95268cef9e6f35e85d53b5793596cb22b14d"),
"SG4":("PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py","86a1c88ffc35033314ae6598ade23f0bebfa709f62cbe2cbef1830cd607e0af9")}
O=R/"output"/"V16_D24_SOURCEBOUND_CONTROLSPACE_PARAMETERIZATION_AUDIT";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def find_exact(name,want):
 hits=[]
 for p in R.rglob(name):
  try:
   if sha(p)==want:hits.append(p)
  except:pass
 return hits
def snippets(text,patterns,window=5):
 lines=text.splitlines();out=[]
 for i,l in enumerate(lines):
  if any(re.search(q,l,re.I) for q in patterns):
   a=max(0,i-window);b=min(len(lines),i+window+1)
   out.append({"line":i+1,"context":"\n".join(f"{j+1}: {lines[j]}" for j in range(a,b))})
 return out
def main():
 print("="*78);print("PAD-Stream V16D-24")
 print("Source-Bound SG2/SG3/SG4 Control-Space Parameterization Audit");print("="*78)
 print("NO FLOW IS RUN IN THIS MILESTONE. D24 MUST FIRST PROVE HOW THE FROZEN")
 print("SG3 SOURCE ACCEPTS/ENCODES INJECTION RATE AND PRODUCER BHP. NUMERICAL")
 print("CLOSENESS OR MEMORY-BASED REIMPLEMENTATION IS NOT AUTHORIZED.\n")
 if sha(S23)!=S23SHA:raise RuntimeError("D23 summary SHA mismatch")
 bound={};gates={"D23_SHA_exact":True}
 for tag,(name,want) in EXPECTED.items():
  hits=find_exact(name,want)
  print(f"{tag}: exact SHA matches = {len(hits)}")
  if len(hits)==1:
   print(" ",hits[0]);bound[tag]={"path":str(hits[0]),"sha256":want};gates[f"{tag}_unique_exact_source"]=True
  else:
   bound[tag]={"matches":[str(x) for x in hits],"sha256":want};gates[f"{tag}_unique_exact_source"]=False
 if gates.get("SG3_unique_exact_source"):
  p=Path(bound["SG3"]["path"]);t=p.read_text(encoding="utf-8",errors="replace")
  rate=snippets(t,[r"500",r"tonne",r"mass.?rate",r"co2",r"714\.286",r"700"])
  bhp=snippets(t,[r"2000",r"\bbhp\b",r"bottom.?hole"])
  bind={"rate_evidence":rate,"bhp_evidence":bhp}
  bp=O/"V16D24_SG3_Control_Parameterization_Evidence.json";bp.write_text(json.dumps(bind,indent=2))
  gates["SG3_rate_evidence_found"]=len(rate)>0;gates["SG3_BHP_evidence_found"]=len(bhp)>0
  # Deliberately do not infer mutation algebra merely from token occurrence.
  gates["no_unproven_parameter_mutation"]=True
 else:
  gates["SG3_rate_evidence_found"]=False;gates["SG3_BHP_evidence_found"]=False;gates["no_unproven_parameter_mutation"]=True
 report={"milestone":"V16D-24","sources":bound,"gates":gates,
 "decision":"CONTROL_PARAMETERIZATION_BINDING_REQUIRED_BEFORE_36CASE_FLOW_EXECUTION",
 "authorized_controls":{"injection_tonnes_per_day":[350.,500.,650.],"producer_BHP_psi":[1800.,2000.,2200.]},
 "prohibitions":["do not rewrite SG2/SG3/SG4 from memory","do not fit controls by numerical closeness",
 "do not run locked geology responses before a versioned control adapter is frozen"]}
 rp=O/"V16D24_Source_Binding_Report.json";rp.write_text(json.dumps(report,indent=2))
 allsrc=all(gates.get(f"{x}_unique_exact_source",False) for x in ("SG2","SG3","SG4"))
 evidence=gates["SG3_rate_evidence_found"] and gates["SG3_BHP_evidence_found"]
 if allsrc and evidence:
  status="V16D_SG2_SG3_SG4_EXACT_SOURCES_AND_CONTROL_EVIDENCE_BOUND_VERSIONED_CONTROL_ADAPTER_CONTRACT_AUTHORIZED"
  nxt="V16D-24A — Freeze Source-Preserving SG3 Injection-Rate/BHP Adapter, Then Execute 36-Case Flow Ensemble"
 else:
  status="V16D_CONTROLSPACE_FLOW_BLOCKED_EXACT_SOURCE_OR_CONTROL_BINDING_INCOMPLETE"
  nxt="Recover/bind the exact frozen SG2/SG3/SG4 source files in the project; do not generate flow."
 sp=O/"PAD_Stream_V16D24_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-24","status":status,
 "report_sha256":sha(rp),"gates":gates,"next_milestone":nxt},indent=2))
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not (allsrc and evidence):sys.exit(2)
if __name__=="__main__":main()

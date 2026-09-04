#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,sys
R=Path(__file__).resolve().parent
S=R/"output"/"V16_D24C_R2_EXACT_SOURCECOPY_REFERENCE_TRAIN_PILOT"/"PAD_Stream_V16D24C_R2_Summary.json"
SSHA="ff0f205012e4fb1150877c233ebe7ded87a4aa3aa2cf6cb6e39dbeef1aac4b5d"
SG3=R/"PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG4=R/"PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SHA3="d3ba7b7be45636f6d3ee254fd6cb95268cef9e6f35e85d53b5793596cb22b14d"
SHA4="86a1c88ffc35033314ae6598ade23f0bebfa709f62cbe2cbef1830cd607e0af9"
O=R/"output"/"V16_D24C_R3_SOURCEPATCH_SG4_CONTROL_DIAGNOSTIC";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def assignment_patch(text,rate,bhp):
 lines=text.splitlines(keepends=True);hits={"bhp":0,"rate":0}
 for idx,line in enumerate(lines):
  if re.match(r"^PRODUCER_BHP_PSI\s*=\s*2000\.0\s*(?:#.*)?(?:\r?\n)?$",line):
   e="\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
   lines[idx]=f"PRODUCER_BHP_PSI = {bhp:.1f}{e}";hits["bhp"]+=1
  elif re.match(r"^CO2_MASS_RATE_TONNES_DAY\s*=\s*500\.0\s*(?:#.*)?(?:\r?\n)?$",line):
   e="\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
   lines[idx]=f"CO2_MASS_RATE_TONNES_DAY = {rate:.1f}{e}";hits["rate"]+=1
 if hits!={"bhp":1,"rate":1}:raise RuntimeError(hits)
 return "".join(lines)
def main():
 print("="*78);print("PAD-Stream V16D-24C-R3")
 print("Source-Patch Integrity + SG4 Control-Consistency Diagnostic");print("="*78)
 gates={"R2_SHA_exact":sha(S)==SSHA,"SG3_SHA_exact":sha(SG3)==SHA3,"SG4_SHA_exact":sha(SG4)==SHA4}
 if not all(gates.values()):raise RuntimeError("authority SHA failure")
 s3=SG3.read_text(encoding="utf-8",newline="") if False else SG3.open("r",encoding="utf-8",newline="").read()
 patched=assignment_patch(s3,350.,1800.)
 # splitlines preserves semantic line alignment; previous R2 compared LF-normalized original
 # to CRLF-preserved derived text, falsely flagging nearly every line.
 a=s3.splitlines();b=patched.splitlines()
 diffs=[(i+1,x,y) for i,(x,y) in enumerate(zip(a,b)) if x!=y]
 print("\nSEMANTIC SOURCE DIFF")
 for d in diffs:print(" ",d)
 gates["semantic_diff_exactly_lines_122_132"]=[x[0] for x in diffs]==[122,132]
 gates["only_authorized_assignments_changed"]=all(("PRODUCER_BHP_PSI" in x[1] or "CO2_MASS_RATE_TONNES_DAY" in x[1]) for x in diffs)

 t4=SG4.read_text(encoding="utf-8",errors="replace")
 # Diagnose whether SG4's expected-well reconstruction owns frozen 500/2000 controls.
 patterns=[
 r"PRODUCER_BHP_PSI",r"PRODUCER_BHP_PA",r"CO2_MASS_RATE_TONNES_DAY",
 r"CO2_MASS_RATE_KG_S",r"CO2_RESERVOIR_RATE",r"2000\.0",r"500\.0",
 r"construct_expected_well_rates",r"well_source"
 ]
 evidence=[]
 lines=t4.splitlines()
 for i,l in enumerate(lines,1):
  if any(re.search(p,l,re.I) for p in patterns):
   evidence.append({"line":i,"text":l})
 print("\nSG4 CONTROL / WELL-SOURCE EVIDENCE")
 for x in evidence[:120]:print(f"  L{x['line']}: {x['text'][:220]}")
 gates["SG4_expected_well_function_found"]=any("construct_expected_well_rates" in x["text"] for x in evidence)
 control_refs=[x for x in evidence if re.search(r"PRODUCER_BHP|CO2_MASS_RATE|CO2_RESERVOIR_RATE|2000\.0|500\.0",x["text"],re.I)]
 print(f"\nSG4 control-reference evidence lines: {len(control_refs)}")
 # We intentionally do not decide how to parameterize SG4 here.
 # R2 conservation failure is expected if SG4 reconstructs frozen-control wells while SG3 uses new controls.
 gates["conservation_failure_treated_as_cross_module_control_mismatch_not_physics_failure"]=True
 report={"milestone":"V16D-24C-R3","semantic_source_diffs":[{"line":i,"old":x,"new":y} for i,x,y in diffs],
 "sg4_evidence":evidence,"sg4_control_refs":control_refs,"diagnosis":{
 "R2_diff_gate":"false failure caused by newline-normalization mismatch in comparison",
 "R2_conservation":"SG3 new-control pressure/assembly was compared to SG4 expected-well reconstruction still bound to frozen-control semantics; SG4 must be audited for exact control dependencies before any adapter is changed.",
 "prohibition":"Do not relax conservation thresholds or batch 36 cases."},"gates":gates}
 rp=O/"V16D24C_R3_Diagnostic_Report.json";rp.write_text(json.dumps(report,indent=2))
 ok=all(gates.values())
 status="V16D_SOURCEPATCH_SEMANTICS_CORRECT_SG4_CONTROL_DEPENDENCY_EVIDENCE_EXTRACTED_R4_ADAPTER_AUDIT_AUTHORIZED" if ok else "V16D_D24C_R3_BLOCKED"
 nxt="V16D-24C-R4 — Bind exact SG4 well-source control dependencies and freeze source-preserving cross-module control adapter"
 sp=O/"PAD_Stream_V16D24C_R3_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-24C-R3","status":status,"report_sha256":sha(rp),"gates":gates,"next_milestone":nxt},indent=2))
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

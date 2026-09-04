#!/usr/bin/env python
from pathlib import Path
import ast,json,hashlib,importlib.util,re
import numpy as np

ROOT=Path(__file__).resolve().parent
D7BR=ROOT/"output"/"V16_D7BR_JSON_SERIALIZATION_REPAIR_EXISTING_FLOW_ENSEMBLE_CERTIFICATION"/"PAD_Stream_V16D7BR_Summary.json"
FLOW=ROOT/"output"/"V16_D7B_FULL_FROZEN_CASE0002_0025_SOURCEBOUND_SG2_SG3_SG4_FLOW_ENSEMBLE"/"cases"/"V16D_Foundation_Case_0002_Flow.npz"
SG5=ROOT/"PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
OUT=ROOT/"output"/"V16_D8_SOURCEBOUND_SG5_VELOCITY_POLLOCK_BINDING_CASE0002_PILOT";OUT.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256();h.update(p.read_bytes());return h.hexdigest()

def loadmod(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def functions(text):
 t=ast.parse(text);out=[]
 for n in ast.walk(t):
  if isinstance(n,ast.FunctionDef):out.append((n.name,[a.arg for a in n.args.args],n.lineno))
 return sorted(out,key=lambda x:x[2])

def main():
 print("="*78);print("PAD-Stream V16D-8")
 print("Source-Bound SG5 Velocity/Pollock Multi-Case Execution Binding and Case 0002 Pilot");print("="*78)
 s=json.loads(D7BR.read_text())
 if s["status"]!="V16D_CASE0002_0025_SOURCEBOUND_FLOW_ENSEMBLE_CERTIFIED_READY_FOR_VELOCITY_POLLOCK_TRAVELTIME_PIPELINE":raise RuntimeError("D7BR mismatch")
 if not SG5.exists():raise RuntimeError("SG5 source missing")
 text=SG5.read_text(errors="ignore");low=text.lower();fs=functions(text)
 print(f"\nSG5 source: {SG5.name}\nSHA-256: {sha(SG5)}")
 for n,args,line in fs:print(f"  line {line:4d}: {n}({', '.join(args)})")
 tokens={k:(k in low) for k in ["pollock","streamline","velocity","porosity","seed","tof"]}
 print("\nSemantic tokens:",tokens)
 print("""
D8 BINDS SG5 AND ATTEMPTS ONLY CASE 0002.

THE PILOT MAY EXECUTE ONLY FUNCTIONS EXPOSED BY THE SURVIVING SG5 SOURCE.
IF SG5 DOES NOT PROVIDE A CLEAN ARRAY-LEVEL ENTRY POINT FOR NEW Q/K/PHI
INPUTS, THIS MILESTONE STOPS AND PRESCRIBES AN ADAPTER REPAIR RATHER THAN
REIMPLEMENTING POLLOCK FROM MEMORY.
""")
 # Identify likely array-level velocity/tracing entry points conservatively.
 vel=[x for x in fs if "veloc" in x[0].lower()]
 trace=[x for x in fs if any(k in x[0].lower() for k in ["trace","pollock","streamline"]) and x[0]!="main"]
 seed=[x for x in fs if "seed" in x[0].lower()]
 clean=bool(vel and trace and seed)
 executed=False;pilot={}
 # We intentionally require inspectable functions before execution; no guessed call signatures.
 if clean:
  pilot={"velocity_candidates":[x[0] for x in vel],"seed_candidates":[x[0] for x in seed],
         "trace_candidates":[x[0] for x in trace],
         "note":"Candidate functions bound; exact argument/return adapter must be frozen before calling."}
 gates={
  "D7BR_bound":True,"SG5_source_present":True,"SG5_hash_recorded":True,
  "pollock_semantics_present":tokens["pollock"],"streamline_semantics_present":tokens["streamline"],
  "velocity_semantics_present":tokens["velocity"],"seed_semantics_present":tokens["seed"],
  "array_level_velocity_entrypoint_identified":bool(vel),
  "array_level_seed_entrypoint_identified":bool(seed),
  "array_level_trace_entrypoint_identified":bool(trace),
  "no_pollock_reimplementation":True,"no_multicase_execution":True,"no_transport":True,"no_training":True}
 ok=all(gates.values())
 status=("V16D_SG5_SOURCE_BOUND_ARRAY_ENTRYPOINTS_IDENTIFIED_CASE0002_ADAPTER_EXECUTION_AUTHORIZED"
         if ok else "V16D_SG5_SOURCE_BOUND_BUT_ARRAY_ADAPTER_CONTRACT_INCOMPLETE_EXECUTION_BLOCKED")
 nxt=("V16D-8A — Exact SG5 Function-Signature Adapter and Case 0002 Pollock Pilot"
      if ok else "V16D-8R — SG5 Exact Execution-Path/Function-Contract Recovery Audit")
 summary={"milestone":"V16D-8","status":status,"SG5":{"path":SG5.name,"sha256":sha(SG5),
  "functions":[{"name":n,"args":a,"line":l} for n,a,l in fs],"semantic_tokens":tokens},
  "pilot":pilot,"pollock_executed":executed,"gates":gates,"next_milestone":nxt}
 sp=OUT/"PAD_Stream_V16D8_Summary.json";sp.write_text(json.dumps(summary,indent=2))
 print("\n"+"="*78);print("V16D-8 GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nPOLLOCK EXECUTION\n  NOT EXECUTED IN D8")
 print("\nNEXT MILESTONE\n ",nxt)
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()

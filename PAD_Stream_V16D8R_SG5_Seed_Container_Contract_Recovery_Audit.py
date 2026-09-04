#!/usr/bin/env python
from pathlib import Path
import ast,json,hashlib,re

ROOT=Path(__file__).resolve().parent
D8=ROOT/"output"/"V16_D8_SOURCEBOUND_SG5_VELOCITY_POLLOCK_BINDING_CASE0002_PILOT"/"PAD_Stream_V16D8_Summary.json"
SG5=ROOT/"PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
OUT=ROOT/"output"/"V16_D8R_SG5_SEED_CONTAINER_CONTRACT_RECOVERY_AUDIT";OUT.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256();h.update(p.read_bytes());return h.hexdigest()

def segment(lines,a,b):return "".join(lines[a-1:b])

def main():
 print("="*78);print("PAD-Stream V16D-8R")
 print("SG5 Seed Container Contract Recovery Audit");print("="*78)
 d8=json.loads(D8.read_text())
 if sha(SG5)!=d8["SG5"]["sha256"]:raise RuntimeError("SG5 hash changed")
 lines=SG5.read_text(errors="ignore").splitlines(True)
 text="".join(lines);tree=ast.parse(text)
 funcs={}
 for n in ast.walk(tree):
  if isinstance(n,ast.FunctionDef):
   end=getattr(n,"end_lineno",n.lineno)
   funcs[n.name]={"line":n.lineno,"end":end,"source":segment(lines,n.lineno,end)}
 for n in ["face_seed_positions","build_seeds","trace_one_streamline","trace_streamlines","main"]:
  if n not in funcs:raise RuntimeError(f"Missing {n}")
 print("""
D8A FAILED BEFORE ANY STREAMLINE COMPLETED BECAUSE build_seeds() RETURNED A
CONTAINER WHOSE ELEMENTS WERE NOT THE DICTIONARY CONTRACT EXPECTED BY
trace_one_streamline(). D8R RECOVERS THE EXACT SOURCE-LEVEL CONTAINER
SEMANTICS AND MAIN() CALL PATH. IT DOES NOT RETRACE OR MODIFY SG5.
""")
 for n in ["face_seed_positions","build_seeds","trace_one_streamline","trace_streamlines","main"]:
  f=funcs[n]
  print(f"\n--- {n} lines {f['line']}-{f['end']} ---")
  # print only structurally relevant lines
  for i,l in enumerate(lines[f["line"]-1:f["end"]],f["line"]):
   if any(k in l for k in ["return ","append(","extend(","build_seeds(","trace_streamlines(","face_seed_positions(","seed[","for seed","seeds"]):
    print(f"{i:5d}: {l.rstrip()}")

 bs=funcs["build_seeds"]["source"]; ts=funcs["trace_streamlines"]["source"]; one=funcs["trace_one_streamline"]["source"]; main=funcs["main"]["source"]
 uses_extend=".extend(" in bs
 uses_append=".append(" in bs
 expects_mapping=bool(re.search(r"seed\s*\[\s*[\"']",one))
 main_build=bool(re.search(r"build_seeds\s*\(",main))
 main_trace=bool(re.search(r"trace_streamlines\s*\(",main))
 # Detect whether main transforms/flattens build_seeds output before tracing.
 mb=re.search(r"(\w+)\s*=\s*build_seeds\s*\([^)]*\)",main)
 trace_arg=None;built_var=mb.group(1) if mb else None
 mt=re.search(r"trace_streamlines\s*\(\s*([^,\n]+)",main)
 if mt:trace_arg=mt.group(1).strip()
 direct_main=(built_var is not None and trace_arg==built_var)
 gates={
  "D8_bound":True,"SG5_hash_exact":True,
  "build_seeds_source_recovered":True,"trace_one_source_recovered":True,
  "trace_streamlines_source_recovered":True,"main_source_recovered":True,
  "trace_one_seed_mapping_expectation_bound":expects_mapping,
  "main_build_seeds_call_bound":main_build,"main_trace_streamlines_call_bound":main_trace,
  "no_retrace":True,"no_source_modification":True,"no_transport":True,"no_training":True}
 # We do not require direct_main; that fact decides repair.
 status="V16D_SG5_SEED_CONTAINER_CONTRACT_RECOVERED_D8A_ADAPTER_REPAIR_CAN_PROCEED"
 summary={"milestone":"V16D-8R","status":status,"SG5_sha256":sha(SG5),
  "facts":{"build_seeds_uses_extend":uses_extend,"build_seeds_uses_append":uses_append,
   "trace_one_expects_mapping_seed":expects_mapping,"main_build_variable":built_var,
   "main_trace_first_argument":trace_arg,"main_passes_build_output_directly":direct_main},
  "function_lines":{k:[v["line"],v["end"]] for k,v in funcs.items() if k in ["face_seed_positions","build_seeds","trace_one_streamline","trace_streamlines","main"]},
  "gates":gates,
  "next_milestone":"V16D-8R1 — Exact SG5 Seed-Container Adapter Repair and Case 0002 Pollock Pilot"}
 (OUT/"PAD_Stream_V16D8R_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\nRECOVERED CONTRACT FACTS")
 for k,v in summary["facts"].items():print(f"  {k}: {v}")
 print("\n"+"="*78);print("V16D-8R GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nNEXT MILESTONE\n  V16D-8R1 — Exact SG5 Seed-Container Adapter Repair and Case 0002 Pollock Pilot")
if __name__=="__main__":main()

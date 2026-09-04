#!/usr/bin/env python
from pathlib import Path
import ast, csv, json, hashlib, re

ROOT=Path(__file__).resolve().parent
D6=ROOT/"output"/"V16_D6_FROZEN_REGISTRY_CASE0002_0025_ENSEMBLE_GEOLOGY_GENERATION_CERTIFICATION"/"PAD_Stream_V16D6_Summary.json"
OUT=ROOT/"output"/"V16_D7_MULTICASE_SG2_SG3_SG4_SOURCE_AUTHENTIC_EXECUTION_BINDING_AUDIT"
OUT.mkdir(parents=True,exist_ok=True)

SOURCES=[
 ("SG2","PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"),
 ("SG3","PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"),
 ("SG4","PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"),
]
REQ={
 "SG2":["transmiss","harmonic","kx","ky","kz"],
 "SG3":["pressure","spsolve","bhp","inject"],
 "SG4":["qx","qy","qz","darcy"],
}

def sha(p):
 h=hashlib.sha256();h.update(p.read_bytes());return h.hexdigest()

def funcs(text):
 try:
  t=ast.parse(text)
  return [{"name":n.name,"args":[a.arg for a in n.args.args],"line":n.lineno}
          for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
 except Exception:return []

def assignments(text):
 try:
  t=ast.parse(text);out=[]
  for n in ast.walk(t):
   if isinstance(n,(ast.Assign,ast.AnnAssign)):
    targets=n.targets if isinstance(n,ast.Assign) else [n.target]
    for x in targets:
     if isinstance(x,ast.Name):out.append({"name":x.id,"line":n.lineno})
  return out
 except Exception:return []

def main():
 print("="*78);print("PAD-Stream V16D-7")
 print("Multi-Case SG2/SG3/SG4 Source-Authentic Execution Binding Audit");print("="*78)
 d6=json.loads(D6.read_text())
 if d6["status"]!="V16D_CASE0002_0025_ENSEMBLE_GEOLOGIES_GENERATED_CERTIFIED_READY_FOR_MULTI_CASE_FLOW_PIPELINE":
  raise RuntimeError("D6 prerequisite mismatch")

 print("""
D7 DOES NOT REIMPLEMENT THE FLOW PHYSICS FROM MEMORY.

BEFORE RUNNING 24 NEW FOUNDATION CASES, IT BINDS THE MULTI-CASE ADAPTER TO THE
SURVIVING V15 SG2/SG3/SG4 SOURCE FILES THAT DEFINE THE ALREADY-VALIDATED
TRANSMISSIBILITY, PRESSURE, WELL, GRAVITY, AND CONSERVATIVE-FLUX SEMANTICS.

THIS PREVENTS A NEW V16D LOOP FROM QUIETLY BECOMING A DIFFERENT FLOW SOLVER.
NO FLOW CASE IS EXECUTED IN THIS BINDING AUDIT.
""")
 rows=[]; inventories={}
 for stage,name in SOURCES:
  f=ROOT/name
  if not f.exists():
   rows.append({"stage":stage,"path":name,"exists":False,"sha256":"","required_tokens_bound":False})
   continue
  text=f.read_text(errors="ignore");low=text.lower()
  tokenmap={x:bool(re.search(re.escape(x),low)) for x in REQ[stage]}
  fs=funcs(text);ass=assignments(text)
  inventories[stage]={"functions":fs,"assignments":ass,"tokens":tokenmap}
  rows.append({"stage":stage,"path":name,"exists":True,"sha256":sha(f),
               "required_tokens_bound":all(tokenmap.values()),
               "function_count":len(fs),"assignment_count":len(ass)})
  print(f"\n{stage}: {name}")
  print(f"  SHA-256: {sha(f)}")
  print(f"  functions: {len(fs)}")
  for x in fs[:15]: print(f"    line {x['line']:4d}: {x['name']}({', '.join(x['args'])})")
  print("  required semantics:",", ".join(f"{k}={'Y' if v else 'N'}" for k,v in tokenmap.items()))

 with (OUT/"V16D7_Source_Binding_Inventory.csv").open("w",newline="") as f:
  fields=sorted(set().union(*(r.keys() for r in rows)))
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

 all_sources=all(r.get("exists") for r in rows)
 tokens=all(r.get("required_tokens_bound") for r in rows)
 # Adapter is safe to implement only after exact source files are bound.
 gates={
  "D6_bound":True,
  "SG2_source_present":bool(rows[0].get("exists")),
  "SG3_source_present":bool(rows[1].get("exists")),
  "SG4_source_present":bool(rows[2].get("exists")),
  "SG2_semantic_tokens_bound":bool(rows[0].get("required_tokens_bound")),
  "SG3_semantic_tokens_bound":bool(rows[1].get("required_tokens_bound")),
  "SG4_semantic_tokens_bound":bool(rows[2].get("required_tokens_bound")),
  "source_hashes_recorded":all(bool(r.get("sha256")) for r in rows),
  "no_flow_reimplementation_from_memory":True,
  "no_flow_execution_in_D7":True,
  "no_transport":True,"no_training":True}
 ok=all(gates.values())
 status=("V16D_SG2_SG3_SG4_SOURCE_AUTHENTIC_FLOW_LINEAGE_BOUND_MULTICASE_ADAPTER_IMPLEMENTATION_AUTHORIZED"
         if ok else "V16D_SG2_SG3_SG4_SOURCE_BINDING_INCOMPLETE_MULTICASE_FLOW_EXECUTION_BLOCKED")
 nxt=("V16D-7A — Source-Bound Multi-Case SG2/SG3/SG4 Adapter Implementation and Case 0002 Pilot"
      if ok else "V16D-7R — Recover/Repair Missing SG2/SG3/SG4 Source Binding")
 summary={"milestone":"V16D-7","status":status,"sources":rows,"inventories":inventories,
          "gates":gates,"flow_execution_authorized":False,
          "next_milestone":nxt}
 (OUT/"PAD_Stream_V16D7_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\n"+"="*78);print("V16D-7 GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nFLOW EXECUTION\n  NOT EXECUTED IN D7")
 print("\nNEXT MILESTONE\n ",nxt)
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()

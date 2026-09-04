#!/usr/bin/env python3
from pathlib import Path
import ast,json,hashlib,re

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"/"V16_D10A_V16B_FMM_ADV_EXACT_EXECUTION_PATH_ARRAY_INTERFACE_AUDIT";OUT.mkdir(parents=True,exist_ok=True)
FMM=ROOT/"PAD_Stream_V16B2_Exact_3D_Fast_Marching_Arrival_Time_Baseline.py"
B6=ROOT/"PAD_Stream_V16B6_Directional_Advective_Travel_Time_Numerical_Scheme_Contract.py"
B7=ROOT/"PAD_Stream_V16B7_Controlled_Directional_Advective_Travel_Time_Solve.py"
HASH={"FMM":"0b26e3cdbc41276c53f4778e7eddcddd0cc8ef081ffb495b71df548152e8f049",
      "B6":"fc03e5c9cdeb06a490182d305653a06f4f9d3ddf2a4bd1a80838fc8c89715892",
      "B7":"2355f3eecd41bb6571f7ead3ebb1c5d90a1907ae681826159e79463166994c56"}

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def extract(path):
 text=path.read_text(errors="replace");tree=ast.parse(text)
 funcs={}
 for n in ast.walk(tree):
  if isinstance(n,ast.FunctionDef):
   funcs[n.name]={"line":n.lineno,"end":getattr(n,"end_lineno",n.lineno),
                  "args":[a.arg for a in n.args.args]}
 return text,funcs

def lines(text,a,b):
 ls=text.splitlines();return [{"line":i,"text":ls[i-1].strip()} for i in range(a,min(b,len(ls))+1)
                              if any(x in ls[i-1].lower() for x in
                              ["fast_marching_3d(","bind_injector_sources(","load_inputs(","spsolve","csr_matrix",
                               "lil_matrix","coo_matrix","diags","save","tau","source","velocity","qx","qy","qz",
                               "matrix","rhs","closed","boundary"])][:100]

def main():
 print("="*78);print("PAD-Stream V16D-10A")
 print("V16B FMM/ADV Exact Execution-Path and Array-Interface Audit");print("="*78)
 print("""
D10 IDENTIFIED B2 AS THE FMM IMPLEMENTATION, BUT B6 IS A NUMERICAL-SCHEME
CONTRACT WHILE B7 IS THE CONTROLLED ADV SOLVE. BEFORE WRITING A MULTICASE
ADAPTER, D10A BINDS THE ACTUAL CALL/ARRAY PATH ACROSS B2, B6, AND B7.

THIS IS A SOURCE AUDIT ONLY. NO FMM/ADV SOLVE IS EXECUTED.
""")
 rec={}
 for key,path in [("FMM",FMM),("B6",B6),("B7",B7)]:
  if not path.exists():raise FileNotFoundError(path)
  text,fs=extract(path); rec[key]={"path":path.name,"sha256":sha(path),"functions":fs,
                                  "relevant_lines":lines(text,1,len(text.splitlines()))}
  print(f"\n{key}: {path.name}\n  SHA-256: {sha(path)}")
  for n,v in fs.items():print(f"  line {v['line']:4d}: {n}({', '.join(v['args'])})")
 print("\nSOURCE-LEVEL RELEVANT LINES")
 for key in rec:
  print(f"\n--- {key} ---")
  for x in rec[key]["relevant_lines"]:print(f"{x['line']:5d}: {x['text']}")

 ffunc=rec["FMM"]["functions"]
 # B2 has callable computational kernel; B7 historically may be main-only.
 fmm_array=all(x in ffunc for x in ["fast_marching_3d","bind_injector_sources"])
 b7text=B7.read_text(errors="replace").lower()
 b6text=B6.read_text(errors="replace").lower()
 b7_solver=("spsolve" in b7text)
 b7_reads_b6=("v16b6" in b7text or "directional_advective_travel_time_numerical_scheme" in b7text)
 b6_matrix=("matrix" in b6text or "sparse" in b6text or "csr" in b6text)
 # Determine whether direct function-level adapter is safe or controlled execution/capture is needed.
 b7_nonhelper=[n for n in rec["B7"]["functions"] if n not in {"sha256_file","load_json","save_json","save_csv","flat","main"}]
 direct_adv=len(b7_nonhelper)>0
 mode="DIRECT_ARRAY_FUNCTION" if direct_adv else "CONTROLLED_MAIN_EXECUTION_CAPTURE"

 gates={"D10_hash_FMM_exact":sha(FMM)==HASH["FMM"],"D10_hash_B6_exact":sha(B6)==HASH["B6"],
        "B7_exact_source_present":sha(B7)==HASH["B7"],"FMM_array_kernel_bound":fmm_array,
        "ADV_scheme_contract_present":b6_matrix,"ADV_controlled_solver_present":b7_solver,
        "no_FMM_execution":True,"no_ADV_execution":True,"no_reimplementation":True,
        "no_transport":True,"no_training":True}
 ok=all(gates.values())
 status=("V16D_V16B_FMM_ADV_EXACT_EXECUTION_PATH_BOUND_CASE0002_CONTROLLED_PILOT_AUTHORIZED"
         if ok else "V16D_V16B_FMM_ADV_EXECUTION_PATH_INCOMPLETE")
 nxt=("V16D-10B — Case 0002 Source-Authentic FMM/ADV Controlled Pilot"
      if ok else "V16D-10AR — V16B Travel-Time Execution Provenance Repair")
 summary={"milestone":"V16D-10A","status":status,"ADV_adapter_mode":mode,
          "B7_reads_or_mentions_B6":b7_reads_b6,"sources":rec,"gates":gates,"next_milestone":nxt}
 (OUT/"PAD_Stream_V16D10A_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\nRECOVERED ADAPTER POLICY")
 print(f"  FMM adapter : DIRECT_ARRAY_FUNCTION ({'available' if fmm_array else 'not available'})")
 print(f"  ADV adapter : {mode}")
 print(f"  B7 spsolve  : {b7_solver}")
 print(f"  B7 B6 bind  : {b7_reads_b6}")
 print("\n"+"="*78);print("V16D-10A GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT MILESTONE\n  "+nxt)
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()

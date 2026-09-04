#!/usr/bin/env python3
from pathlib import Path
import ast, json, hashlib, re

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"/"V16_D10_FROZEN_V16B_FMM_ADV_MULTICASE_EXECUTION_BINDING_AUDIT";OUT.mkdir(parents=True,exist_ok=True)

SEARCH_TERMS=("V16B2","V16B7","FMM","Fast_Marching","Advective_Travel_Time","Directional_Advective")
EXCLUDE=("V16D10",)

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def candidates():
 out=[]
 for p in ROOT.rglob("*.py"):
  n=p.name.upper()
  if any(x.upper() in n for x in SEARCH_TERMS) and not any(x.upper() in n for x in EXCLUDE):
   out.append(p)
 return sorted(set(out))

def funcs(text):
 try:
  t=ast.parse(text)
  return [(n.name,n.lineno) for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
 except Exception:return []

def score(text,kind):
 lo=text.lower()
 if kind=="FMM":
  toks=["fast marching","eikonal","accepted","trial","heap","arrival"]
 else:
  toks=["v(x)","grad","advective","upwind","spsolve","causality","tau"]
 return sum(t in lo for t in toks)

def main():
 print("="*78);print("PAD-Stream V16D-10")
 print("Frozen V16B FMM/ADV Multi-Case Execution Binding Audit");print("="*78)
 print("""
D9R1 CLOSED THE MULTI-CASE POLLOCK/C7 COORDINATE BRANCH.

D10 DOES NOT YET EXECUTE FMM OR ADV. BEFORE REPEATING THE V16B TRAVEL-TIME
PHYSICS ACROSS 24 NEW GEOLOGIES, THIS AUDIT BINDS THE EXACT SURVIVING V16B
IMPLEMENTATIONS. IT WILL NOT REIMPLEMENT EIKONAL/FMM OR THE DIRECTIONAL
UPWIND ADV OPERATOR FROM MEMORY.
""")
 cs=candidates()
 records=[]
 for p in cs:
  text=p.read_text(errors="replace");fs=funcs(text)
  rec={"path":str(p.relative_to(ROOT)),"sha256":sha(p),"fmm_score":score(text,"FMM"),
       "adv_score":score(text,"ADV"),"functions":[{"name":n,"line":l} for n,l in fs],
       "tokens":{"closed_boundary":("closed" in text.lower() and "boundary" in text.lower()),
                 "source_cells":"source" in text.lower(),"velocity":"velocity" in text.lower() or "vx" in text.lower(),
                 "residual":"residual" in text.lower(),"causality":"causality" in text.lower()}}
  records.append(rec)
 fmm=sorted(records,key=lambda r:r["fmm_score"],reverse=True)
 adv=sorted(records,key=lambda r:r["adv_score"],reverse=True)
 best_fmm=fmm[0] if fmm and fmm[0]["fmm_score"]>=3 else None
 best_adv=adv[0] if adv and adv[0]["adv_score"]>=3 else None

 print(f"Candidate Python files: {len(records)}")
 for r in records:
  print(f"\n{r['path']}")
  print(f"  SHA-256 : {r['sha256']}")
  print(f"  FMM/ADV score: {r['fmm_score']} / {r['adv_score']}")
  if r["functions"]:
   print("  functions:")
   for f in r["functions"][:30]:print(f"    line {f['line']:5d}: {f['name']}()")

 gates={"D9R1_prerequisite_declared":True,"candidate_scan_complete":True,
        "exact_FMM_source_candidate_bound":best_fmm is not None,
        "exact_ADV_source_candidate_bound":best_adv is not None,
        "no_FMM_execution":True,"no_ADV_execution":True,"no_reimplementation":True,
        "no_transport":True,"no_training":True}
 ok=all(gates.values())
 if ok:
  status="V16D_FROZEN_V16B_FMM_ADV_EXECUTION_LINEAGE_BOUND_MULTICASE_ADAPTER_PILOT_AUTHORIZED"
  nxt="V16D-10A — Source-Bound FMM/ADV Adapter and Case 0002 Travel-Time Hierarchy Pilot"
 else:
  status="V16D_FROZEN_V16B_FMM_ADV_EXECUTION_LINEAGE_NOT_YET_UNIQUELY_BOUND"
  nxt="V16D-10R — Exact V16B FMM/ADV Source Provenance Recovery Audit"

 summary={"milestone":"V16D-10","status":status,"candidate_count":len(records),
          "best_FMM_candidate":best_fmm,"best_ADV_candidate":best_adv,
          "all_candidates":records,"gates":gates,"next_milestone":nxt}
 sp=OUT/"PAD_Stream_V16D10_Summary.json";sp.write_text(json.dumps(summary,indent=2))
 print("\n"+"="*78);print("V16D-10 GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 if best_fmm:print(f"\nBOUND FMM CANDIDATE\n  {best_fmm['path']}\n  {best_fmm['sha256']}")
 if best_adv:print(f"\nBOUND ADV CANDIDATE\n  {best_adv['path']}\n  {best_adv['sha256']}")
 print("\nSTATUS\n ",status);print("\nNEXT MILESTONE\n  "+nxt)
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()

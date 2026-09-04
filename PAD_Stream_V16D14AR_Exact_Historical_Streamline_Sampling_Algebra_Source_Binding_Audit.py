#!/usr/bin/env python3
from pathlib import Path
import ast,hashlib,json,re,sys
R=Path(__file__).resolve().parent
A=R/"output"/"V16_D14A_EXACT_FIELD_BINDING"/"V16D14A_Field_Level_Preflight_Registry.json"
ASHA="6c62537158596f1aaa565e8da281b04e21b68d7f889425e9afed0c37d32d3941"
O=R/"output"/"V16_D14AR_STREAMLINE_SAMPLING_ALGEBRA_SOURCE_BINDING_AUDIT";O.mkdir(parents=True,exist_ok=True)
# Search source only. Numerical artifacts are never used to infer algebra.
TOKENS=("streamline_xyz","transport_xyz","log10_Kh","pressure_z","porosity_path","porosity_sampled",
        "floor(","clip(","searchsorted(","astype(int","DX_M","DY_M","DZ_M","FT_TO_M","6.096","1.2192")
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def candidates():
 out=[]
 for p in R.rglob("*.py"):
  if p.resolve()==Path(__file__).resolve():continue
  try:t=p.read_text(encoding="utf-8",errors="ignore")
  except:continue
  hits=[x for x in TOKENS if x.lower() in t.lower()]
  # Need path coordinates plus evidence of geology/pressure sampling/index conversion.
  path=any(x.lower() in t.lower() for x in ("streamline_xyz","transport_xyz"))
  field=any(x.lower() in t.lower() for x in ("log10_kh","pressure_z","porosity_path","porosity_sampled","kx","pressure"))
  index=any(x.lower() in t.lower() for x in ("floor(","clip(","searchsorted(","astype(int","dx_m","dy_m","dz_m","6.096","1.2192"))
  if path and field and index:out.append((p,t,hits))
 return out
def extract_functions(text):
 tree=ast.parse(text);lines=text.splitlines();out=[]
 for n in ast.walk(tree):
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
   seg="\n".join(lines[n.lineno-1:getattr(n,"end_lineno",n.lineno)])
   low=seg.lower()
   if any(x in low for x in ("streamline_xyz","transport_xyz")) and any(x in low for x in ("kx","pressure","porosity","log10")) and any(x in low for x in ("floor","clip","searchsorted","astype(int","dx_m","dy_m","dz_m")):
    out.append({"name":n.name,"lineno":n.lineno,"end_lineno":getattr(n,"end_lineno",n.lineno),"source":seg})
 return out
def main():
 print("="*78);print("PAD-Stream V16D-14AR");print("Exact Historical Streamline Sampling Algebra Source-Binding Audit");print("="*78)
 print("""D14A CORRECTLY BLOCKED BEFORE ASSEMBLY.
THIS AUDIT SEARCHES EXECUTABLE SOURCE FOR THE EXACT XYZ->CELL/PATH-FIELD
SAMPLING ALGEBRA. IT DOES NOT INFER INDEXING FROM NUMERICAL VALUES,
DOES NOT FIT ANYTHING, AND DOES NOT READ OOD TARGET LABELS.
""")
 if not A.exists() or sha(A)!=ASHA:raise RuntimeError("D14A preflight registry SHA mismatch")
 cs=candidates();records=[]
 for p,t,hits in cs:
  try:fs=extract_functions(t)
  except SyntaxError:fs=[]
  records.append({"path":str(p),"sha256":sha(p),"token_hits":hits,"sampling_functions":fs})
 rp=O/"V16D14AR_Sampling_Source_Candidates.json";rp.write_text(json.dumps(records,indent=2))
 coherent=[r for r in records if len(r["sampling_functions"])>0]
 # Do not auto-select among multiple plausible executable implementations.
 unique=len(coherent)==1
 gates={"D14A_registry_SHA_exact":sha(A)==ASHA,"source_candidates_found":len(records)>0,
        "executable_sampling_function_found":len(coherent)>0,"unique_coherent_source":unique,
        "no_numerical_closeness_selection":True,"no_fitting":True,"no_OOD_target_read":True,"no_training":True}
 ok=all(gates.values())
 status="V16D_EXACT_HISTORICAL_STREAMLINE_SAMPLING_ALGEBRA_UNIQUELY_SOURCE_BOUND_D14B_AUTHORIZED" if ok else "V16D_STREAMLINE_SAMPLING_SOURCE_NOT_UNIQUELY_BOUND_MANUAL_PROVENANCE_NARROWING_REQUIRED"
 nxt="V16D-14B — Source-Authentic 24-Case Predictor Assembly + TRAIN-Only Normalization Statistics Freeze" if ok else "V16D-14AR1 — Sampling Source Candidate Disambiguation Audit"
 q={"milestone":"V16D-14AR","status":status,"candidate_count":len(records),"coherent_executable_count":len(coherent),
    "coherent_sources":[{"path":r["path"],"sha256":r["sha256"],"functions":[f["name"] for f in r["sampling_functions"]]} for r in coherent],
    "gates":gates,"next_milestone":nxt}
 sp=O/"PAD_Stream_V16D14AR_Summary.json";sp.write_text(json.dumps(q,indent=2))
 print("source candidates:",len(records));print("coherent executable candidates:",len(coherent))
 for r in coherent:print(" ",r["path"],"|",r["sha256"],"|",[f["name"] for f in r["sampling_functions"]])
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

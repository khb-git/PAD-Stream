#!/usr/bin/env python3
from pathlib import Path
import ast,hashlib,json,re,sys
R=Path(__file__).resolve().parent
AR1=R/"output"/"V16_D14AR1_SAMPLING_SOURCE_CANDIDATE_DISAMBIGUATION"/"PAD_Stream_V16D14AR1_Summary.json"
AR1SHA="d41c85c4a441d2bf1a3432ce36ef59adcd892fc9b09d75a9abdff177e28523b7"
O=R/"output"/"V16_D14AR2_EXACT_SAMPLING_STATEMENT_LINEAGE_BINDING";O.mkdir(parents=True,exist_ok=True)
CANDS=[
("B1","PAD_Stream_V16B1_Fast_Marching_Governing_Metric_Speed_Field_Contract_Audit.py","0b8f3448f4da2a5022c3e1b14041351e925aa564dbced51746954e972ac6ce80"),
("B4","PAD_Stream_V16B4_FMM_Pollock_Discrepancy_Structure_Directionality_Audit.py","b505e453a689b094c7587bb2b92391c31ae5e532b6a80dec12c1c73729319ff9"),
("C2","PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py","315a25cab35c1da6d58fa9bb8254eecb55dbe0abca71f112ac319f123ea7cea6")]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def lines_of_interest(t):
 ls=t.splitlines();idx=[]
 terms=("streamline_xyz","transport_xyz","floor(","clip(","astype(int","searchsorted(","kx[","ky[","kz[","poro","pressure[","dx_m","dy_m","dz_m")
 for i,l in enumerate(ls):
  if any(x in l.lower() for x in terms):idx.append(i)
 spans=[];seen=set()
 for i in idx:
  a=max(0,i-6);b=min(len(ls),i+7)
  key=(a,b)
  if key not in seen:seen.add(key);spans.append({"start":a+1,"end":b,"text":"\n".join(ls[a:b])})
 return spans
def assignments(t):
 tree=ast.parse(t);ls=t.splitlines();out=[]
 for n in ast.walk(tree):
  if isinstance(n,(ast.Assign,ast.AnnAssign,ast.AugAssign)):
   seg="\n".join(ls[n.lineno-1:getattr(n,"end_lineno",n.lineno)])
   low=seg.lower()
   if any(x in low for x in ("streamline_xyz","transport_xyz","floor","clip","astype(int","searchsorted","kx[","ky[","kz[","poro","pressure[")):
    out.append({"line":n.lineno,"end":getattr(n,"end_lineno",n.lineno),"source":seg})
 return out
def main():
 print("="*78);print("PAD-Stream V16D-14AR2");print("Exact Sampling Statement / Lineage Binding Repair");print("="*78)
 print("""AR1 PROVED NO SINGLE HISTORICAL FILE CONTAINS THE FINAL C20 DERIVED
CHANNEL NAMES. AR2 NOW ASKS THE CORRECT LOWER-LEVEL QUESTION:
DO THE PRESERVED SOURCES DEFINE ONE CONSISTENT XYZ->CELL INDEXING AND
RAW K/POROSITY/PRESSURE SAMPLING ALGEBRA THAT CAN BE VERSION-BINDINGLY
REUSED, WITH LOG10/ZSCORE DERIVATIONS APPLIED EXPLICITLY AFTERWARD?

NO NUMERICAL CLOSENESS, FITTING, OOD LABEL ACCESS, OR TRAINING OCCURS.
""")
 if not AR1.exists() or sha(AR1)!=AR1SHA:raise RuntimeError("AR1 authority SHA mismatch")
 rec=[]
 for tag,name,hx in CANDS:
  p=R/name
  if not p.exists() or sha(p)!=hx:raise RuntimeError(name+" SHA mismatch")
  t=p.read_text(encoding="utf-8",errors="ignore")
  rec.append({"tag":tag,"file":name,"sha256":hx,"statements":assignments(t),"context":lines_of_interest(t)})
 rp=O/"V16D14AR2_Exact_Sampling_Statements.json";rp.write_text(json.dumps(rec,indent=2))
 # Extract normalized statement text to compare source algebra structurally, not numerically.
 def sig(r):
  ss=[]
  for x in r["statements"]:
   z=re.sub(r"\s+","",x["source"].lower())
   if any(k in z for k in ("floor","clip","astype(int","searchsorted")):ss.append(z)
  return ss
 sigs={r["tag"]:sig(r) for r in rec}
 # C2 is the historical database assembler; authorize it only when it itself contains
 # explicit index conversion plus raw property sampling statements.
 c2=rec[2];txt="\n".join(x["source"] for x in c2["statements"]).lower()
 has_index=any(k in txt for k in ("floor","clip","astype(int","searchsorted"))
 has_k=any(k in txt for k in ("kx[","ky[","kz["))
 has_phi="poro" in txt
 has_p="pressure[" in txt
 gates={"AR1_SHA_exact":sha(AR1)==AR1SHA,"candidate_SHAs_exact":True,"exact_statements_persisted":True,
        "C2_explicit_index_conversion":has_index,"C2_raw_permeability_sampling":has_k,
        "C2_raw_porosity_sampling":has_phi,"C2_raw_pressure_sampling":has_p,
        "no_numerical_closeness":True,"no_fitting":True,"no_OOD_labels":True,"no_training":True}
 ok=all(gates.values())
 if ok:
  status="V16D_C2_RAW_STREAMLINE_SAMPLING_ALGEBRA_SOURCE_BOUND_DERIVED_C20_CHANNEL_CONSTRUCTION_AUTHORIZED"
  nxt="V16D-14B — Source-Authentic 24-Case Predictor Assembly + TRAIN-Only Normalization Statistics Freeze"
 else:
  status="V16D_PRESERVED_SOURCES_DO_NOT_FULLY_BIND_RAW_C20_SAMPLING_ALGEBRA_NEW_VERSIONED_SAMPLING_CONTRACT_REQUIRED"
  nxt="V16D-14AR3 — New Explicit V16D Streamline-to-Grid Sampling Contract (No Historical Relabeling)"
 q={"milestone":"V16D-14AR2","status":status,"C2_checks":{"index":has_index,"K":has_k,"porosity":has_phi,"pressure":has_p},
    "statement_registry_sha256":sha(rp),"index_statement_signatures":sigs,"gates":gates,"next_milestone":nxt}
 sp=O/"PAD_Stream_V16D14AR2_Summary.json";sp.write_text(json.dumps(q,indent=2))
 print("C2 raw sampling checks:",q["C2_checks"]);print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

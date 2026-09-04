#!/usr/bin/env python3
from pathlib import Path
import ast,hashlib,json,re,sys
R=Path(__file__).resolve().parent
AR=R/"output"/"V16_D14AR_STREAMLINE_SAMPLING_ALGEBRA_SOURCE_BINDING_AUDIT"/"PAD_Stream_V16D14AR_Summary.json"
ARSHA="db3e4c2702d7271c7df942f27622226aac8721aa3981ae69000a02592e1f350b"
O=R/"output"/"V16_D14AR1_SAMPLING_SOURCE_CANDIDATE_DISAMBIGUATION";O.mkdir(parents=True,exist_ok=True)
EXPECTED={
"PAD_Stream_V16B1_Fast_Marching_Governing_Metric_Speed_Field_Contract_Audit.py":"0b8f3448f4da2a5022c3e1b14041351e925aa564dbced51746954e972ac6ce80",
"PAD_Stream_V16B4_FMM_Pollock_Discrepancy_Structure_Directionality_Audit.py":"b505e453a689b094c7587bb2b92391c31ae5e532b6a80dec12c1c73729319ff9",
"PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py":"315a25cab35c1da6d58fa9bb8254eecb55dbe0abca71f112ac319f123ea7cea6"}
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def snippets(text):
 ls=text.splitlines();out=[]
 keys=("streamline_xyz","transport_xyz","floor(","clip(","astype(int","searchsorted(","dx_m","dy_m","dz_m","log10_kh","pressure_z","porosity")
 for i,l in enumerate(ls):
  if any(k in l.lower() for k in keys):
   a=max(0,i-4);b=min(len(ls),i+5);out.append({"lines":[a+1,b],"text":"\n".join(ls[a:b])})
 return out
def imports_calls(text):
 tree=ast.parse(text);im=[];calls=[]
 for n in ast.walk(tree):
  if isinstance(n,ast.Import):
   im += [x.name for x in n.names]
  elif isinstance(n,ast.ImportFrom): im.append((n.module or "")+":"+",".join(x.name for x in n.names))
  elif isinstance(n,ast.Call):
   f=n.func
   if isinstance(f,ast.Name):calls.append(f.id)
   elif isinstance(f,ast.Attribute):calls.append(f.attr)
 return sorted(set(im)),sorted(set(calls))
def main():
 print("="*78);print("PAD-Stream V16D-14AR1");print("Sampling Source Candidate Disambiguation Audit");print("="*78)
 print("""THREE EXECUTABLE SOURCES SURVIVED D14AR.
AR1 COMPARES THEIR SOURCE ROLE, IMPORT/CALL LINEAGE, AND EXACT SAMPLING
STATEMENTS. IT DOES NOT COMPARE NUMERICAL OUTPUTS OR SELECT BY CLOSENESS.
THE C20/C2 DATABASE ASSEMBLY SOURCE HAS PRIORITY ONLY IF SOURCE TEXT SHOWS
IT ACTUALLY DEFINES THE PREDICTOR PATH-SAMPLING SEMANTICS RATHER THAN
MERELY CONSUMING THEM.
""")
 if not AR.exists() or sha(AR)!=ARSHA:raise RuntimeError("D14AR authority SHA mismatch")
 rec=[]
 for name,hx in EXPECTED.items():
  p=R/name
  if not p.exists() or sha(p)!=hx:raise RuntimeError(f"candidate authority mismatch: {name}")
  t=p.read_text(encoding="utf-8",errors="ignore");im,ca=imports_calls(t);sn=snippets(t)
  low=t.lower()
  role={"defines_xyz_to_cell":any(x in low for x in ("floor(","astype(int","searchsorted(")) and "streamline_xyz" in low,
        "contains_log10_Kh":"log10_kh" in low,"contains_pressure_z":"pressure_z" in low,
        "contains_porosity":"porosity" in low,"is_C2_transport_database":"multi_coordinate_streamline_transport_database" in low or "v16c2" in low}
  rec.append({"file":name,"sha256":hx,"role":role,"imports":im,"calls":ca,"sampling_snippets":sn})
 rp=O/"V16D14AR1_Candidate_Source_Semantics.json";rp.write_text(json.dumps(rec,indent=2))
 # Source-semantic authority: candidate must define xyz->cell AND all C20 geology/pressure path fields.
 full=[r for r in rec if r["role"]["defines_xyz_to_cell"] and r["role"]["contains_log10_Kh"] and r["role"]["contains_pressure_z"] and r["role"]["contains_porosity"]]
 unique=len(full)==1
 gates={"D14AR_SHA_exact":sha(AR)==ARSHA,"three_candidate_SHAs_exact":True,
        "source_semantics_examined":True,"no_numerical_output_comparison":True,
        "full_predictor_sampling_semantics_candidate_found":len(full)>0,"unique_full_semantics_authority":unique,
        "no_fitting":True,"no_OOD_target_read":True,"no_training":True}
 if unique:
  auth=full[0];status="V16D_STREAMLINE_SAMPLING_ALGEBRA_SOURCE_AUTHORITY_UNIQUELY_DISAMBIGUATED_D14B_AUTHORIZED";nxt="V16D-14B — Source-Authentic 24-Case Predictor Assembly + TRAIN-Only Normalization Statistics Freeze"
 else:
  auth=None;status="V16D_SAMPLING_ALGEBRA_NOT_UNIQUELY_DISAMBIGUATED_NO_ASSEMBLY";nxt="V16D-14AR2 — Exact Sampling Statement/Lineage Binding Repair"
 q={"milestone":"V16D-14AR1","status":status,"selected_authority":auth and {"file":auth["file"],"sha256":auth["sha256"]},
    "full_semantics_candidates":[x["file"] for x in full],"candidate_semantics_sha256":sha(rp),"gates":gates,"next_milestone":nxt}
 sp=O/"PAD_Stream_V16D14AR1_Summary.json";sp.write_text(json.dumps(q,indent=2))
 for r in rec:print(r["file"],r["role"])
 print("\nfull-semantics candidates:",[x["file"] for x in full] or "none")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not all(gates.values()):sys.exit(2)
if __name__=="__main__":main()

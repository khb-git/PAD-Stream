#!/usr/bin/env python
from pathlib import Path
import json,re,hashlib,csv
ROOT=Path(__file__).resolve().parent
D2=ROOT/"output"/"V16_D2_SGSIM_MULTI_REALIZATION_GEOLOGY_RECIPE_CONTROL_SPACE_DESIGN_AUTHORITY_CONTRACT"/"PAD_Stream_V16D2_Summary.json"
OUT=ROOT/"output"/"V16_D3_EXACT_CASE0001_SGSIM_RECIPE_PROVENANCE_EXECUTABLE_BINDING_AUDIT";OUT.mkdir(parents=True,exist_ok=True)

TEXT_EXT={".py",".txt",".json",".csv",".md",".xml",".par",".params",".sgems",".prj",".project",".yaml",".yml",".ini",".cfg",".log"}
TOKENS=["sgsim","sgems","variogram","azimuth","range","seed","50x50x15","gauss","transform_sgsim_perm","ah_min","vertical"]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-3")
 print("Exact Case 0001 SGSim Geostatistical Recipe Provenance and Executable Binding Audit");print("="*78)
 print("""D3 DOES NOT GENERATE A NEW REALIZATION.

IT SEARCHES THE LOCAL PROJECT TREE FOR SOURCE-AUTHENTIC CASE-0001 SGSim/SGeMS
RECIPE EVIDENCE. NUMERICAL OUTPUT SIMILARITY IS NOT ACCEPTED AS A SUBSTITUTE
FOR THE GENERATION RECIPE. IF THE EXACT RECIPE CANNOT BE BOUND, D3 FAILS
SAFELY AND CASE 0002+ GENERATION REMAINS PROHIBITED.
""")
 if json.loads(D2.read_text())["status"]!="V16D_SGSIM_MULTI_REALIZATION_EXPERIMENT_DESIGN_FROZEN_EXACT_CASE0001_GEOSTATISTICAL_RECIPE_BINDING_REQUIRED":
  raise RuntimeError("D2 prerequisite mismatch")
 hits=[]
 for f in ROOT.rglob("*"):
  if not f.is_file() or OUT in f.parents or f.suffix.lower() not in TEXT_EXT:continue
  try:
   if f.stat().st_size>20_000_000:continue
   text=f.read_text(errors="ignore")
  except Exception:continue
  low=text.lower(); score=sum(t in low for t in TOKENS)
  if score:
   snippets=[]
   for pat in ["sgsim","variogram","azimuth","seed","ah_min","vertical range","transform_sgsim_perm"]:
    m=re.search(rf".{{0,120}}{re.escape(pat)}.{{0,220}}",text,re.I|re.S)
    if m:snippets.append(" ".join(m.group(0).split()))
   hits.append(dict(path=str(f.relative_to(ROOT)),sha256=sha(f),score=score,snippet=" | ".join(snippets[:5])[:2500]))
 hits.sort(key=lambda x:(-x["score"],x["path"]))
 with (OUT/"V16D3_SGSim_Recipe_Source_Candidates.csv").open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=["path","sha256","score","snippet"]);w.writeheader();w.writerows(hits)
 # Strict source-authentic indicators. We intentionally do not infer missing values.
 candidate_text="\n".join(x["snippet"].lower() for x in hits)
 indicators={
 "sgsim_source_evidence":("sgsim" in candidate_text),
 "variogram_evidence":("variogram" in candidate_text),
 "azimuth_evidence":("azimuth" in candidate_text),
 "seed_evidence":("seed" in candidate_text),
 "vertical_evidence":("vertical" in candidate_text),
 }
 # Exact executable recipe requires source/config evidence sufficient to regenerate
 # a new realization, including stochastic seed handling and variogram definition.
 exact=all(indicators.values())
 gates={
 "D2_bound":True,
 "local_source_search_completed":True,
 "candidate_inventory_written":True,
 "numerical_similarity_not_used":True,
 "no_missing_parameter_invention":True,
 "no_new_realization_generated":True,
 "exact_executable_recipe_bound":exact}
 status="V16D_CASE0001_SGSIM_GEOSTATISTICAL_RECIPE_SOURCE_BOUND_GENERATION_CONTRACT_CAN_PROCEED" if exact else "V16D_CASE0001_SGSIM_EXACT_RECIPE_NOT_YET_SOURCE_BOUND_GENERATION_REMAINS_BLOCKED"
 summary={"milestone":"V16D-3","status":status,"candidate_count":len(hits),"indicators":indicators,
 "top_candidates":hits[:20],"gates":gates,
 "generation_authorized":False,
 "next_milestone":("V16D-4 — Predeclared SGSim Seed Registry and Case 0002+ Generation Contract" if exact else
 "V16D-3R — Bind Missing Case 0001 SGeMS Project/Parameter Export or Explicitly Freeze a New Versioned Multi-Case SGSim Recipe")}
 (OUT/"PAD_Stream_V16D3_Summary.json").write_text(json.dumps(summary,indent=2))
 print(f"\nCandidate source files found: {len(hits)}")
 for x in hits[:10]:print(f"  score={x['score']:2d}  {x['path']}")
 print("\nRECIPE EVIDENCE")
 for k,v in indicators.items():print(f"  {k:28s}: {'FOUND' if v else 'NOT BOUND'}")
 print("\n"+"="*78);print("V16D-3 GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nGENERATION AUTHORIZATION\n  NOT AUTHORIZED IN D3")
 print("\nNEXT MILESTONE")
 print(" ",summary["next_milestone"])
 if not exact:
  print("\nACTION IF BLOCKED:")
  print("  Inspect V16D3_SGSim_Recipe_Source_Candidates.csv.")
  print("  If the original SGeMS project/parameter export exists outside this project, copy it into the project unchanged and rerun D3.")
  print("  If it does not survive, do NOT reconstruct it from memory; D3R will version and freeze a new explicit recipe.")
if __name__=="__main__":main()

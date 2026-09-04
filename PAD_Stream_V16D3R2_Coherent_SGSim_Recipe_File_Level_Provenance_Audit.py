#!/usr/bin/env python
from pathlib import Path
import json, re, hashlib, csv

ROOT = Path(__file__).resolve().parent
D3R = ROOT/"output"/"V16_D3R_EXACT_CASE0001_SGSIM_RECIPE_SOURCE_AUTHENTICITY_RESIDUAL_AUDIT"/"PAD_Stream_V16D3R_Summary.json"
OUT = ROOT/"output"/"V16_D3R2_COHERENT_SGSIM_RECIPE_FILE_LEVEL_PROVENANCE_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

TEXT_EXT={".py",".txt",".json",".csv",".md",".xml",".par",".params",".sgems",
          ".prj",".project",".yaml",".yml",".ini",".cfg",".log"}

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20), b""):
            h.update(b)
    return h.hexdigest()

def excluded(p):
    rel=str(p.relative_to(ROOT)).replace("\\","/").lower()
    name=p.name.lower()
    # Exclude dependencies and generated provenance/audit inventories: they can
    # quote unrelated source and cannot themselves establish the SGSim recipe.
    if "/.venv/" in "/"+rel or rel.startswith(".venv/"):
        return True
    if rel.startswith("output/"):
        return True
    if "v16d" in name:
        return True
    return False

def flags(text):
    low=text.lower()
    return {
      "sgsim": bool(re.search(r"\bsgsim\b|\bsgems\b",low)),
      "seed_numeric": bool(re.search(r"\bseed\b\s*(?:=|:|\s)\s*-?\d+",low)),
      "variogram_model": bool(re.search(r"\b(spherical|exponential|gaussian)\b",low)),
      "major_range": bool(re.search(r"(major|ah_max|range[_ ]?1|horizontal range).{0,100}\d",low,re.S)),
      "minor_range": bool(re.search(r"(minor|ah_min|range[_ ]?2).{0,100}\d",low,re.S)),
      "vertical_range": bool(re.search(r"(vertical|vert|range[_ ]?3).{0,100}\d",low,re.S)),
      "azimuth": bool(re.search(r"\bazimuth\b.{0,70}-?\d",low,re.S)),
      "nugget_cov": bool(re.search(r"\b(nugget|sill|contribution|covariance)\b.{0,100}\d",low,re.S)),
      "grid": ("50x50x15" in low or bool(re.search(r"nx.{0,30}50.*ny.{0,30}50.*nz.{0,30}15",low,re.S))),
    }

CRITICAL=["sgsim","seed_numeric","variogram_model","major_range","minor_range",
          "vertical_range","azimuth","nugget_cov","grid"]

def main():
    print("="*78)
    print("PAD-Stream V16D-3R2")
    print("Coherent SGSim Recipe File-Level Provenance Audit")
    print("="*78)
    print("""
D3R2 REPAIRS A SECOND PROVENANCE RISK.

D3R POOLED SNIPPETS ACROSS THOUSANDS OF FILES, INCLUDING .venv AND GENERATED
V15 AUDIT INVENTORIES. THAT CAN SYNTHESIZE A COMPLETE-LOOKING RECIPE FROM
UNRELATED FILES.

D3R2 REQUIRES THE CRITICAL SGSim GENERATION FIELDS TO CO-OCCUR IN ONE
SOURCE-AUTHENTIC RECIPE/PROJECT/PARAMETER FILE (OR AN EXPLICIT ORIGINAL
SGeMS PROJECT EXPORT). DOWNSTREAM PERMEABILITY TRANSFORM CODE MAY BE BOUND
SEPARATELY.

NO GENERATION. NO INFERENCE. NO CROSS-FILE PARAMETER ASSEMBLY.
""")
    d=json.loads(D3R.read_text())
    if d["status"]!="V16D_CASE0001_SGSIM_RECIPE_SOURCE_AUTHENTICALLY_BOUND_D4_SEED_REGISTRY_CAN_PROCEED":
        raise RuntimeError("D3R prerequisite mismatch")

    rows=[]
    coherent=[]
    transform=[]
    for f in ROOT.rglob("*"):
        if not f.is_file() or excluded(f) or f.suffix.lower() not in TEXT_EXT:
            continue
        try:
            if f.stat().st_size>20_000_000: continue
            text=f.read_text(errors="ignore")
        except Exception:
            continue
        fl=flags(text)
        score=sum(fl[k] for k in CRITICAL)
        if score:
            row={"path":str(f.relative_to(ROOT)),"sha256":sha256(f),
                 "critical_score":score, **fl}
            rows.append(row)
            if all(fl[k] for k in CRITICAL):
                coherent.append(row)
        low=text.lower()
        if "transform_sgsim_perm" in f.name.lower() or ("gauss" in low and "perm" in low and "sgsim" in low):
            transform.append({"path":str(f.relative_to(ROOT)),"sha256":sha256(f)})

    rows.sort(key=lambda r:(-r["critical_score"],r["path"]))
    coherent.sort(key=lambda r:r["path"])
    with (OUT/"V16D3R2_File_Level_Recipe_Candidates.csv").open("w",newline="",encoding="utf-8") as fh:
        fields=["path","sha256","critical_score"]+CRITICAL
        w=csv.DictWriter(fh,fieldnames=fields);w.writeheader()
        for r in rows:w.writerow({k:r[k] for k in fields})

    exact=len(coherent)>0
    gates={
      "D3R_bound":True,
      "venv_excluded":True,
      "generated_output_excluded":True,
      "cross_file_parameter_pooling_prohibited":True,
      "file_level_candidate_inventory_written":True,
      "no_numerical_similarity":True,
      "no_parameter_inference":True,
      "no_case_generation":True,
      "coherent_original_recipe_file_bound":exact,
    }

    if exact:
        status="V16D_CASE0001_COHERENT_SGSIM_RECIPE_FILE_BOUND_D4_SEED_REGISTRY_CAN_PROCEED"
        nextm="V16D-4 — Predeclared SGSim Seed Registry and Case 0002+ Generation Contract"
    else:
        status="V16D_CASE0001_COHERENT_SGSIM_RECIPE_FILE_NOT_BOUND_NEW_VERSIONED_ENSEMBLE_RECIPE_REQUIRED"
        nextm="V16D-3R3 — Explicit New Versioned V16D SGSim Ensemble Recipe Authority Contract"

    summary={
      "milestone":"V16D-3R2","status":status,
      "D3R_result_superseded_for_exact_recipe_claim":True,
      "coherent_recipe_files":coherent,
      "transform_sources":transform,
      "gates":gates,
      "generation_authorized":False,
      "next_milestone":nextm
    }
    (OUT/"PAD_Stream_V16D3R2_Summary.json").write_text(json.dumps(summary,indent=2))

    print(f"\nEligible file-level candidates: {len(rows)}")
    for r in rows[:15]:
        print(f"  score={r['critical_score']:2d}/9  {r['path']}")
    print(f"\nCoherent complete recipe files: {len(coherent)}")
    for r in coherent:
        print(" ",r["path"],r["sha256"])
    print(f"Downstream SGSim permeability transform candidates: {len(transform)}")
    for r in transform[:5]: print(" ",r["path"])

    print("\n"+"="*78);print("V16D-3R2 GATES");print("="*78)
    for k,v in gates.items():
        print(f"[{'PASS' if v else 'FAIL'}] {k}")
    print("\nSTATUS\n ",status)
    print("\nGENERATION AUTHORIZATION\n  NOT AUTHORIZED IN D3R2")
    print("\nNEXT MILESTONE\n ",nextm)
    if not exact:
        print("""
INTERPRETATION:
  No single surviving source-authentic file proves the complete historical
  Case 0001 SGSim generation recipe. Do not assemble one by combining unrelated
  audit snippets. The clean next step is to freeze a new explicit V16D ensemble
  recipe before assigning seeds or generating Case 0002+.
""")

if __name__=="__main__":
    main()

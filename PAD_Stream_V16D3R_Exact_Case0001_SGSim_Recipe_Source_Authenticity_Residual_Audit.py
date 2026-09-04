#!/usr/bin/env python
from pathlib import Path
import json, re, hashlib, csv

ROOT = Path(__file__).resolve().parent
D3 = ROOT/"output"/"V16_D3_EXACT_CASE0001_SGSIM_RECIPE_PROVENANCE_EXECUTABLE_BINDING_AUDIT"/"PAD_Stream_V16D3_Summary.json"
OUT = ROOT/"output"/"V16_D3R_EXACT_CASE0001_SGSIM_RECIPE_SOURCE_AUTHENTICITY_RESIDUAL_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

# Deliberately exclude V16D contract/audit files and generated audit output.
# A recipe cannot authenticate itself by repeating remembered/project metadata.
EXCLUDED_NAME_PATTERNS = (
    "V16D1_", "V16D2_", "V16D3_", "V16D3R_",
)
TEXT_EXT = {".py",".txt",".json",".csv",".md",".xml",".par",".params",
            ".sgems",".prj",".project",".yaml",".yml",".ini",".cfg",".log"}

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20), b""):
            h.update(b)
    return h.hexdigest()

def source_authentic_file(p):
    rel=str(p.relative_to(ROOT))
    if "output\\V16_D" in rel or "output/V16_D" in rel:
        return False
    if any(x in p.name for x in EXCLUDED_NAME_PATTERNS):
        return False
    return True

def snippets(text, terms):
    out=[]
    for term in terms:
        m=re.search(rf".{{0,180}}{re.escape(term)}.{{0,350}}", text, re.I|re.S)
        if m:
            out.append(" ".join(m.group(0).split()))
    return " | ".join(out)[:5000]

def main():
    print("="*78)
    print("PAD-Stream V16D-3R")
    print("Exact Case 0001 SGSim Recipe Source-Authenticity Residual Audit")
    print("="*78)
    print("""
D3R REPAIRS A FALSE-POSITIVE RISK IN D3.

D3 FOUND THE WORDS 'SGSIM', 'VARIOGRAM', 'AZIMUTH', 'SEED', AND 'VERTICAL',
BUT ITS HIGHEST-SCORING FILES INCLUDED D3 ITSELF, D2, AND GENERATED AUDIT
OUTPUT. TERM PRESENCE IS NOT SUFFICIENT TO PROVE AN EXECUTABLE SGSim RECIPE.

D3R EXCLUDES V16D CONTRACT/AUDIT SELF-EVIDENCE AND REQUIRES SOURCE-AUTHENTIC
PRE-D3 EVIDENCE FOR THE ACTUAL STOCHASTIC GENERATION PARAMETERS.

NO CASE IS GENERATED. NO MISSING PARAMETER IS INFERRED.
""")
    if not D3.exists():
        raise RuntimeError("D3 summary not found.")
    d3=json.loads(D3.read_text())
    if d3["status"]!="V16D_CASE0001_SGSIM_GEOSTATISTICAL_RECIPE_SOURCE_BOUND_GENERATION_CONTRACT_CAN_PROCEED":
        raise RuntimeError("D3 did not produce the result targeted by this residual audit.")

    terms=["sgsim","sgems","variogram","azimuth","seed","vertical","range",
           "nugget","sill","covariance","search ellipsoid","ah_min",
           "50x50x15","gauss","transform_sgsim_perm"]

    candidates=[]
    for f in ROOT.rglob("*"):
        if not f.is_file() or not source_authentic_file(f):
            continue
        if f.suffix.lower() not in TEXT_EXT:
            continue
        try:
            if f.stat().st_size > 20_000_000:
                continue
            text=f.read_text(errors="ignore")
        except Exception:
            continue
        low=text.lower()
        score=sum(t in low for t in terms)
        if score:
            candidates.append({
                "path":str(f.relative_to(ROOT)),
                "sha256":sha256(f),
                "score":score,
                "snippet":snippets(text, terms)
            })

    candidates.sort(key=lambda x:(-x["score"],x["path"]))
    with (OUT/"V16D3R_Source_Authentic_SGSim_Candidates.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["path","sha256","score","snippet"])
        w.writeheader(); w.writerows(candidates)

    corpus="\n".join(c["snippet"].lower() for c in candidates)

    # Strict regeneration fields. These must be evidenced, not merely mentioned.
    evidence = {
        "sgsim_or_sgems_generation_source": bool(re.search(r"\b(sgsim|sgems)\b", corpus)),
        "stochastic_seed_value_or_explicit_seed_parameter": bool(
            re.search(r"\bseed\b\s*(?:=|:|\s)\s*-?\d+", corpus)),
        "variogram_model_type": bool(
            re.search(r"\b(spherical|exponential|gaussian)\b", corpus)),
        "variogram_major_range_numeric": bool(
            re.search(r"(major|ah_max|range[_ ]?1|horizontal range).{0,80}\d", corpus)),
        "variogram_minor_range_numeric": bool(
            re.search(r"(minor|ah_min|range[_ ]?2).{0,80}\d", corpus)),
        "variogram_vertical_range_numeric": bool(
            re.search(r"(vertical|vert|range[_ ]?3).{0,80}\d", corpus)),
        "azimuth_numeric": bool(
            re.search(r"\bazimuth\b.{0,50}-?\d", corpus)),
        "nugget_or_covariance_contribution": bool(
            re.search(r"\b(nugget|sill|contribution|covariance)\b.{0,80}\d", corpus)),
        "grid_dimensions_bound": ("50x50x15" in corpus or
            bool(re.search(r"(nx.{0,30}50.*ny.{0,30}50.*nz.{0,30}15)", corpus, re.S))),
        "gaussian_to_perm_transform_source": ("transform_sgsim_perm" in corpus or
            ("gauss" in corpus and "perm" in corpus)),
    }

    # Exact recipe means enough to reproduce the stochastic field class, not just downstream transform.
    critical = [
        "sgsim_or_sgems_generation_source",
        "stochastic_seed_value_or_explicit_seed_parameter",
        "variogram_model_type",
        "variogram_major_range_numeric",
        "variogram_minor_range_numeric",
        "variogram_vertical_range_numeric",
        "azimuth_numeric",
        "nugget_or_covariance_contribution",
        "grid_dimensions_bound",
    ]
    exact = all(evidence[k] for k in critical)

    gates = {
        "D3_result_residually_audited": True,
        "V16D_self_evidence_excluded": True,
        "generated_V16D_output_excluded": True,
        "source_authentic_candidate_inventory_written": True,
        "numerical_output_similarity_not_used": True,
        "missing_parameters_not_inferred": True,
        "no_case_generated": True,
        "exact_regeneration_recipe_source_bound": exact,
    }

    if exact:
        status="V16D_CASE0001_SGSIM_RECIPE_SOURCE_AUTHENTICALLY_BOUND_D4_SEED_REGISTRY_CAN_PROCEED"
        nextm="V16D-4 — Predeclared SGSim Seed Registry and Case 0002+ Generation Contract"
    else:
        status="V16D_CASE0001_SGSIM_EXACT_RECIPE_NOT_SOURCE_AUTHENTICALLY_BOUND_D3_FALSE_POSITIVE_REPAIRED"
        nextm="V16D-3R2 — Recover Original SGeMS Project/Parameter Export or Freeze a New Explicit Versioned V16D SGSim Ensemble Recipe"

    summary={
        "milestone":"V16D-3R",
        "status":status,
        "D3_original_status":d3["status"],
        "D3_interpretation":"D3 term-presence result is superseded by D3R source-authenticity audit.",
        "candidate_count":len(candidates),
        "evidence":evidence,
        "critical_fields":critical,
        "exact_recipe_bound":exact,
        "generation_authorized":False,
        "gates":gates,
        "top_candidates":candidates[:20],
        "next_milestone":nextm
    }
    (OUT/"PAD_Stream_V16D3R_Summary.json").write_text(json.dumps(summary,indent=2))

    print(f"\nSource-authentic candidate files found: {len(candidates)}")
    for c in candidates[:12]:
        print(f"  score={c['score']:2d}  {c['path']}")

    print("\nSTRICT REGENERATION EVIDENCE")
    for k,v in evidence.items():
        print(f"  {k:48s}: {'BOUND' if v else 'NOT BOUND'}")

    print("\n"+"="*78)
    print("V16D-3R GATES")
    print("="*78)
    for k,v in gates.items():
        print(f"[{'PASS' if v else 'FAIL'}] {k}")

    print("\nSTATUS\n ",status)
    print("\nGENERATION AUTHORIZATION\n  NOT AUTHORIZED IN D3R")
    print("\nNEXT MILESTONE\n ",nextm)

    if not exact:
        print("""
INTERPRETATION:
  D3's PASS was not sufficient provenance evidence because its detector admitted
  self-generated V16D metadata. Do NOT proceed to Case 0002 generation yet.

  Inspect V16D3R_Source_Authentic_SGSim_Candidates.csv. If an original SGeMS
  project/parameter export survives elsewhere, copy it into the project unchanged
  and rerun D3R. Otherwise the scientifically clean path is D3R2: freeze a NEW,
  fully explicit V16D SGSim ensemble recipe and identify Case 0001 as the historical
  reference rather than claiming exact same-recipe regeneration.
""")

if __name__=="__main__":
    main()

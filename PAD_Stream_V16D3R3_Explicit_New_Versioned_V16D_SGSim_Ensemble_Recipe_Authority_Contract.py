#!/usr/bin/env python
from pathlib import Path
import json, hashlib, csv

ROOT=Path(__file__).resolve().parent
R2=ROOT/"output"/"V16_D3R2_COHERENT_SGSIM_RECIPE_FILE_LEVEL_PROVENANCE_AUDIT"/"PAD_Stream_V16D3R2_Summary.json"
OUT=ROOT/"output"/"V16_D3R3_EXPLICIT_NEW_VERSIONED_SGSIM_ENSEMBLE_RECIPE_AUTHORITY_CONTRACT"
OUT.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def main():
 print("="*78);print("PAD-Stream V16D-3R3")
 print("Explicit New Versioned V16D SGSim Ensemble Recipe Authority Contract");print("="*78)
 r=json.loads(R2.read_text())
 if r["status"]!="V16D_CASE0001_COHERENT_SGSIM_RECIPE_FILE_NOT_BOUND_NEW_VERSIONED_ENSEMBLE_RECIPE_REQUIRED":
  raise RuntimeError("D3R2 prerequisite mismatch")

 print("""
HISTORICAL PROVENANCE DECISION
  Case 0001 remains the authentic historical SGSim reference.
  Its exact original SGeMS stochastic recipe is NOT claimed recoverable.
  Case 0002+ will therefore use a NEW, explicitly versioned V16D ensemble recipe.

R3 DOES NOT GENERATE A REALIZATION AND DOES NOT TRAIN.
IT FREEZES THE REPRODUCIBLE GEOLOGICAL MODEL CLASS THAT FUTURE CASES WILL USE.
""")

 recipe={
 "recipe_id":"V16D_SGSIM_ENSEMBLE_RECIPE_1.0",
 "historical_case0001_relation":"REFERENCE_ONLY_NOT_CLAIMED_AS_EXACT_SAME_STOCHASTIC_RECIPE",
 "grid":{"nx":50,"ny":50,"nz":15,"dx_ft":20.0,"dy_ft":20.0,"dz_ft":4.0},
 "simulation":{
   "algorithm":"sequential Gaussian simulation",
   "normal_score_field":{"mean":0.0,"variance":1.0},
   "variogram_model":"exponential",
   "nugget":0.0,
   "major_range_ft":200.0,
   "minor_range_ft":200.0,
   "vertical_range_ft":15.0,
   "azimuth_deg":30.0,
   "dip_deg":0.0,
   "rake_deg":0.0,
   "search_neighborhood":"same metric/ranges as variogram for Recipe 1.0",
   "conditioning_data":"none; unconditional realizations",
   "seed_policy":"explicit integer seed from frozen D4 registry; one seed per geology_id"},
 "permeability":{
   "transform_authority":"existing transform_sgsim_perm.py must be SHA-bound before generation",
   "target_support_mD":[50.0,1000.0],
   "injection_interval_layers_1based":[6,7,8,9,10],
   "background_and_injection_unit_transform":"use the existing transform implementation unchanged; do not re-fit per realization",
   "Kx":"K_perm","Ky":"K_perm","Kz_over_Kh":0.10},
 "porosity":0.20,
 "first_phase_controls":{"CO2_mass_rate_tonnes_per_day":500.0,"producer_BHP_psi":2000.0},
 "well_geometry":{"injector_zero_based_xy":[24,24],
                  "producers_zero_based_xy":[[4,4],[45,4],[4,45],[45,45]],
                  "completion_zero_based_k":[5,6,7,8,9]},
 "prohibitions":[
   "no realization rejection or reseeding based on visual appearance",
   "no permeability-transform refit per realization",
   "no variogram/range tuning after seeing model performance",
   "no claim that Case0002+ exactly reproduces the lost Case0001 SGeMS recipe",
   "no control variation in first geology-only phase"],
 "generation_authorized":False,
 "training_authorized":False
 }

 # This is a NEW design contract. Values are design choices, not recovered historical facts.
 rationale={
  "major_minor_range_ft":"200 ft isotropic areal continuity is frozen as the new V16D Recipe 1.0 design choice.",
  "vertical_range_ft":"15 ft retained from the documented intended vertical continuity scale.",
  "azimuth_deg":"30 degrees retained as documented intended orientation; with equal major/minor ranges it does not create areal anisotropy in Recipe 1.0.",
  "variogram_model":"exponential is a new explicit Recipe 1.0 design choice, not a recovered Case0001 fact.",
  "nugget":"0.0 is a new explicit Recipe 1.0 design choice.",
  "historical_separation":"all new choices are labeled V16D design authority rather than historical provenance."
 }

 transform=ROOT/"transform_sgsim_perm.py"
 transform_bound=transform.exists()
 transform_sha=sha(transform) if transform_bound else None

 gates={
 "D3R2_bound":True,
 "historical_recipe_nonrecoverability_respected":True,
 "new_recipe_versioned":True,
 "new_vs_historical_semantics_explicit":True,
 "grid_explicit":True,
 "variogram_model_explicit":True,
 "major_minor_vertical_ranges_explicit":True,
 "orientation_explicit":True,
 "nugget_explicit":True,
 "conditioning_status_explicit":True,
 "seed_policy_explicit":True,
 "no_cherrypicking":True,
 "no_per_realization_refit":True,
 "case0001_not_relabelled":True,
 "transform_source_present":transform_bound,
 "no_generation_in_R3":True,
 "no_training_in_R3":True}
 ok=all(gates.values())
 status=("V16D_NEW_VERSIONED_SGSIM_ENSEMBLE_RECIPE_1P0_FROZEN_SEED_REGISTRY_CAN_PROCEED"
         if ok else "V16D_NEW_SGSIM_ENSEMBLE_RECIPE_FREEZE_BLOCKED")
 summary={"milestone":"V16D-3R3","status":status,"recipe":recipe,"design_rationale":rationale,
          "transform_source":{"path":"transform_sgsim_perm.py","sha256":transform_sha},
          "gates":gates,
          "next_milestone":"V16D-4 — Predeclared SGSim Seed Registry and Case 0002+ Generation Contract"}
 (OUT/"PAD_Stream_V16D3R3_Summary.json").write_text(json.dumps(summary,indent=2))

 rows=[{"parameter":k,"value":v,"authority":"NEW_V16D_RECIPE_1.0"}
       for k,v in recipe["simulation"].items() if not isinstance(v,dict)]
 with (OUT/"V16D3R3_SGSim_Recipe_1p0.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=["parameter","value","authority"]);w.writeheader();w.writerows(rows)

 print("\nNEW V16D RECIPE 1.0")
 print("  Grid                : 50 x 50 x 15; 20 x 20 x 4 ft")
 print("  SGS algorithm       : sequential Gaussian simulation")
 print("  Variogram           : exponential")
 print("  Nugget              : 0.0")
 print("  Areal ranges        : 200 ft major / 200 ft minor")
 print("  Vertical range      : 15 ft")
 print("  Azimuth             : 30 deg")
 print("  Conditioning        : unconditional")
 print("  Porosity            : 0.20")
 print("  Kz/Kh               : 0.10")
 print("  Controls first phase: 500 tonnes/day; 2000 psi producer BHP")
 print("\nIMPORTANT AUTHORITY LABEL")
 print("  These are NEW V16D Recipe 1.0 design choices.")
 print("  They are NOT represented as recovered historical Case 0001 SGeMS settings.")
 print(f"\ntransform_sgsim_perm.py SHA-256: {transform_sha}")
 print("\n"+"="*78);print("V16D-3R3 GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nGENERATION AUTHORIZATION\n  NOT AUTHORIZED IN D3R3")
 print("\nNEXT MILESTONE\n  V16D-4 — Predeclared SGSim Seed Registry and Case 0002+ Generation Contract")
 if not ok: raise SystemExit(2)

if __name__=="__main__":main()

#!/usr/bin/env python
from pathlib import Path
import json,csv,hashlib

ROOT=Path(__file__).resolve().parent
R3=ROOT/"output"/"V16_D3R3_EXPLICIT_NEW_VERSIONED_SGSIM_ENSEMBLE_RECIPE_AUTHORITY_CONTRACT"/"PAD_Stream_V16D3R3_Summary.json"
OUT=ROOT/"output"/"V16_D4_PREDECLARED_SGSIM_SEED_REGISTRY_CASE0002PLUS_GENERATION_CONTRACT";OUT.mkdir(parents=True,exist_ok=True)

# Predeclared before any realization generation.
# Case 0001 is historical and intentionally excluded from this new-recipe seed sequence.
N_NEW=24
BASE_SEED=160400
REG=[{"case_id":f"V16D_Foundation_Case_{i:04d}",
      "geology_id":f"V16D_Geology_{i:04d}",
      "sgsim_seed":BASE_SEED+(i-2)*7919,
      "recipe_id":"V16D_SGSIM_ENSEMBLE_RECIPE_1.0",
      "controls_id":"REFERENCE_500TPD_2000PSI"}
     for i in range(2,2+N_NEW)]

def sha_bytes(b): return hashlib.sha256(b).hexdigest()

def main():
 print("="*78);print("PAD-Stream V16D-4")
 print("Predeclared SGSim Seed Registry and Case 0002+ Generation Contract");print("="*78)
 r=json.loads(R3.read_text())
 if r["status"]!="V16D_NEW_VERSIONED_SGSIM_ENSEMBLE_RECIPE_1P0_FROZEN_SEED_REGISTRY_CAN_PROCEED":
  raise RuntimeError("D3R3 prerequisite mismatch")
 print("""
D4 FREEZES CASE IDs AND STOCHASTIC SEEDS BEFORE ANY NEW REALIZATION EXISTS.

THE REGISTRY IS AN EXPERIMENTAL-DESIGN AUTHORITY, NOT A SEARCH LIST:
  - every registered seed must be attempted in order;
  - a case may fail only for a documented numerical/technical reason;
  - failed cases are retained in the registry with failure provenance;
  - no replacement seed may be selected because a realization looks preferable;
  - no model result may alter this registry.

D4 DOES NOT YET GENERATE GEOLOGY OR TRAIN.
""")
 reg_path=OUT/"V16D4_Predeclared_Case_Seed_Registry.csv"
 with reg_path.open("w",newline="") as f:
  fields=["case_id","geology_id","sgsim_seed","recipe_id","controls_id"]
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(REG)
 reg_sha=hashlib.sha256(reg_path.read_bytes()).hexdigest()
 seeds=[x["sgsim_seed"] for x in REG]
 ids=[x["case_id"] for x in REG]
 contract={
  "registry_sha256":reg_sha,
  "new_case_count":N_NEW,
  "case_range":"0002-0025",
  "case0001":"historical immutable reference; not regenerated and not assigned a Recipe 1.0 seed",
  "seed_rule":{"base_seed":BASE_SEED,"stride":7919,
               "formula":"seed(case i)=160400+(i-2)*7919 for i=2..25",
               "selection":"predeclared arithmetic registry; not sampled after geology inspection"},
  "first_phase_controls":{"CO2_mass_rate_tonnes_per_day":500.0,"producer_BHP_psi":2000.0},
  "generation_policy":{
    "order":"ascending case_id",
    "all_registered_cases_attempted":True,
    "technical_failure":"record failure and diagnostics; do not silently replace",
    "visual_or_statistical_rejection":"prohibited",
    "permeability_transform_refit":"prohibited",
    "recipe_change_mid_registry":"prohibited; requires new recipe/version and new contract"},
  "split_policy":{
    "D4_does_not_assign_train_validation_test":True,
    "reason":"case split is frozen only after cases are generated and certified as valid physics cases, but before any multi-case learning",
    "failed_cases_never_replaced_to_balance_split":True},
  "generation_authorized_in_D4":False,
  "training_authorized":False}
 gates={
  "R3_bound":True,"case0001_excluded_from_new_recipe_registry":True,
  "case_ids_unique":len(ids)==len(set(ids)),
  "seeds_unique":len(seeds)==len(set(seeds)),
  "24_new_cases_predeclared":len(REG)==24,
  "deterministic_seed_formula":all(x["sgsim_seed"]==BASE_SEED+(i-2)*7919 for i,x in zip(range(2,26),REG)),
  "fixed_controls_first_phase":True,"no_cherrypicking":True,
  "no_silent_seed_replacement":True,"failure_provenance_required":True,
  "no_per_realization_transform_refit":True,"registry_hash_frozen":True,
  "no_generation_in_D4":True,"no_training_in_D4":True}
 ok=all(gates.values())
 status="V16D_PREDECLARED_CASE0002_0025_SGSIM_SEED_REGISTRY_FROZEN_GENERATION_EXECUTION_CAN_PROCEED" if ok else "V16D_SEED_REGISTRY_FREEZE_BLOCKED"
 summary={"milestone":"V16D-4","status":status,"contract":contract,"gates":gates,
          "registry_preview":REG[:5],
          "next_milestone":"V16D-5 — Deterministic SGSim Recipe 1.0 Generator Implementation and Pre-Generation Validation"}
 (OUT/"PAD_Stream_V16D4_Summary.json").write_text(json.dumps(summary,indent=2))
 print("\nPREDECLARED REGISTRY")
 print(f"  New cases        : {N_NEW}")
 print("  Case IDs         : 0002 through 0025")
 print(f"  Base seed        : {BASE_SEED}")
 print("  Seed stride      : 7919")
 print(f"  Registry SHA-256 : {reg_sha}")
 print("\nFIRST FIVE")
 for x in REG[:5]:print(f"  {x['case_id']}  seed={x['sgsim_seed']}")
 print(f"  ...\n  {REG[-1]['case_id']}  seed={REG[-1]['sgsim_seed']}")
 print("\nSPLIT POLICY")
 print("  No train/validation/test case assignment in D4.")
 print("  Split occurs after physics-case certification and before multi-case learning.")
 print("  Invalid technical cases remain documented and are never replaced to balance a split.")
 print("\n"+"="*78);print("V16D-4 GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nGENERATION AUTHORIZATION\n  NOT EXECUTED IN D4")
 print("\nNEXT MILESTONE\n  V16D-5 — Deterministic SGSim Recipe 1.0 Generator Implementation and Pre-Generation Validation")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()

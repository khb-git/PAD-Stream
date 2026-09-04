#!/usr/bin/env python
from pathlib import Path
import json,csv
ROOT=Path(__file__).resolve().parent
C28=ROOT/"output"/"V16_C28_TRANSPORT_LEARNING_BRANCH_FREEZE_INTERPRETATION_FORWARD_ARCHITECTURE_DECISION"/"PAD_Stream_V16C28_Summary.json"
OUT=ROOT/"output"/"V16_D1_MULTI_FOUNDATION_CASE_TRUE_OOD_GEOLOGY_CONTROL_EXPANSION_AUTHORITY_CONTRACT";OUT.mkdir(parents=True,exist_ok=True)

def main():
 print("="*78);print("PAD-Stream V16D-1")
 print("Multi-Foundation-Case and True OOD Geology/Control Expansion Authority Contract");print("="*78)
 print("""D1 DOES NOT GENERATE GEOLOGIES, RUN FLOW, GENERATE TRANSPORT, OR TRAIN.

PURPOSE:
MOVE PAD-STREAM FROM THE SINGLE FOUNDATION CASE 0001 BASELINE TO A
MULTI-FOUNDATION-CASE DATA ARCHITECTURE CAPABLE OF TRUE CASE-LEVEL OOD TESTS.

FOUNDATION CASE = one immutable tuple of:
  geology + grid + rock properties + wells/completions + controls +
  pressure/flux solution + Pollock kinematics + travel-time auxiliaries +
  source-authentic transport supervision + provenance.

CASE 0001 REMAINS FROZEN AND IS NOT RE-RANDOMIZED.

TRUE OOD IS DEFINED AT FOUNDATION-CASE LEVEL, NOT BY HOLDING OUT STREAMLINES
FROM THE SAME CASE.
""")
 c=json.loads(C28.read_text())
 if c["status"]!="V16C_TRANSPORT_LEARNING_BRANCH_FROZEN_EXP1_EXP2_TRADEOFF_CERTIFIED_FORWARD_OOD_CASE_EXPANSION_REQUIRED":
  raise RuntimeError("C28 prerequisite mismatch")
 contract={
 "unit_of_generalization":"FOUNDATION_CASE",
 "case_0001_role":"FROZEN_REFERENCE_FOUNDATION_CASE",
 "required_case_components":[
  "case_id","geology_id_and_seed","grid_geometry","Kx_Ky_Kz","porosity",
  "well_locations_and_completions","injection_and_production_controls",
  "pressure","Qx_Qy_Qz","Vx_Vy_Vz","Pollock_streamlines_and_TOF_weights",
  "FMM_connectivity_context","ADV_directional_travel_time_context",
  "C7_Pollock_spatial_metric","C17_style_source_authentic_transport_targets",
  "immutable_parameter_and_time_schedule_metadata","source_hashes_and_provenance"],
 "variation_axes":{
  "geology":"independent SGSim realizations/seeds under a separately frozen geostatistical recipe",
  "controls":"well/control variants under separately frozen admissible ranges",
  "physics":"same source-authentic governing hierarchy unless a new versioned contract changes it"},
 "split_hierarchy":{
  "inner_case_split":"streamline-group train/validation only inside development cases when required",
  "case_level_development":"multiple complete Foundation Cases available to model fitting",
  "case_level_validation":"entire unseen Foundation Cases for architecture/hyperparameter selection",
  "case_level_test":"entire unseen Foundation Cases touched only after selection",
  "OOD_definition":"unseen geology and/or unseen control Foundation Cases"},
 "leakage_prohibitions":[
  "no streamline from an OOD case may appear in training",
  "no target time from an OOD case may appear in training",
  "no normalization statistics may be fit using OOD cases",
  "no OOD test result may select architecture/loss weight/hyperparameters",
  "case seeds and control assignments must be frozen before model training"],
 "foundation_model_claim_requirements":[
  "more than one training Foundation Case",
  "case-level validation",
  "case-level locked test",
  "explicit geology/control coverage statement",
  "no claim beyond tested distribution"],
 "immediate_next_step":"freeze the SGSim multi-realization generation recipe and admissible control-space design before creating Case 0002+",
 "training_authorized":False
 }
 gates=dict(C28_bound=True,case0001_immutable=True,foundation_case_unit_defined=True,
  geology_variation_axis_defined=True,control_variation_axis_defined=True,true_OOD_case_level=True,
  no_streamline_level_OOD_relabeling=True,case_level_validation_required=True,case_level_locked_test_required=True,
  OOD_normalization_leakage_prohibited=True,OOD_selection_leakage_prohibited=True,
  multi_case_foundation_claim_requirements_defined=True,no_case_generation_in_D1=True,no_training_in_D1=True)
 ok=all(gates.values())
 status="V16D_MULTI_FOUNDATION_CASE_TRUE_OOD_EXPANSION_ARCHITECTURE_FROZEN_CASE_GENERATION_RECIPE_REQUIRED" if ok else "V16D_MULTI_FOUNDATION_CASE_CONTRACT_BLOCKED"
 summary={"milestone":"V16D-1","status":status,"contract":contract,"gates":gates,
 "next_milestone":"V16D-2 — SGSim Multi-Realization Geology Recipe and Control-Space Design Authority Contract"}
 (OUT/"PAD_Stream_V16D1_Summary.json").write_text(json.dumps(summary,indent=2))
 rows=[
 {"level":"Case 0001","role":"Frozen reference","training_access":"existing V16C baseline only"},
 {"level":"Development cases","role":"multi-case model fitting","training_access":"allowed after case certification"},
 {"level":"Case-level validation","role":"model selection","training_access":"prohibited"},
 {"level":"Case-level locked test","role":"final true-OOD evaluation","training_access":"prohibited"}]
 with (OUT/"V16D1_Foundation_Case_Split_Hierarchy.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print("\nFROZEN MULTI-CASE ARCHITECTURE")
 print("  Generalization unit : complete Foundation Case")
 print("  Case 0001           : immutable frozen reference")
 print("  Geology variation   : independent SGSim realizations")
 print("  Control variation   : separately frozen admissible design space")
 print("  True OOD            : entirely unseen Foundation Cases")
 print("  OOD normalization   : prohibited")
 print("  OOD model selection : prohibited")
 print("  Training now        : NOT AUTHORIZED")
 print("\nFOUNDATION-MODEL CLAIM")
 print("  Requires multiple training cases + case-level validation + locked case-level test.")
 print("  Current Case 0001-only evidence remains a single-case baseline.")
 print("\n"+"="*78);print("V16D-1 GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nNEXT MILESTONE\n  V16D-2 — SGSim Multi-Realization Geology Recipe and Control-Space Design Authority Contract")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()

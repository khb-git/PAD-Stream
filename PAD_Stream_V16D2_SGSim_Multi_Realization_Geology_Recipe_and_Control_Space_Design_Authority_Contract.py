#!/usr/bin/env python
from pathlib import Path
import json,csv
ROOT=Path(__file__).resolve().parent
D1=ROOT/"output"/"V16_D1_MULTI_FOUNDATION_CASE_TRUE_OOD_GEOLOGY_CONTROL_EXPANSION_AUTHORITY_CONTRACT"/"PAD_Stream_V16D1_Summary.json"
OUT=ROOT/"output"/"V16_D2_SGSIM_MULTI_REALIZATION_GEOLOGY_RECIPE_CONTROL_SPACE_DESIGN_AUTHORITY_CONTRACT";OUT.mkdir(parents=True,exist_ok=True)

def main():
 print("="*78);print("PAD-Stream V16D-2")
 print("SGSim Multi-Realization Geology Recipe and Control-Space Design Authority Contract");print("="*78)
 print("""D2 DOES NOT GENERATE CASES, RUN FLOW, GENERATE TRANSPORT, OR TRAIN.

D2 FREEZES THE FIRST MULTI-CASE EXPERIMENT DESIGN BEFORE CASE 0002+ EXISTS.
THE GOAL IS TO VARY STOCHASTIC GEOLOGICAL REALIZATION WITHOUT CHANGING THE
BASE GEOLOGICAL MODEL CLASS, THEN INTRODUCE CONTROL VARIATION AS A SEPARATE
AXIS SO GEOLOGY AND CONTROL GENERALIZATION CAN BE DISTINGUISHED.

CASE 0001 REMAINS THE IMMUTABLE REFERENCE.
""")
 d1=json.loads(D1.read_text())
 if d1["status"]!="V16D_MULTI_FOUNDATION_CASE_TRUE_OOD_EXPANSION_ARCHITECTURE_FROZEN_CASE_GENERATION_RECIPE_REQUIRED":
  raise RuntimeError("D1 prerequisite mismatch")
 recipe={
 "grid":{"nx":50,"ny":50,"nz":15,"dx_ft":20.0,"dy_ft":20.0,"dz_ft":4.0},
 "sgsim_model_class":{
  "method":"sequential Gaussian simulation (SGSim)",
  "stationarity_class":"same as Foundation Case 0001",
  "variogram_vertical_range_ft":15.0,
  "azimuth_deg":30.0,
  "continuity_and_variogram_parameters":"MUST BE BOUND TO THE CASE-0001 SOURCE RECIPE BEFORE GENERATION; D2 DOES NOT GUESS UNRECOVERED SGeMS PARAMETERS",
  "realization_rule":"independent stochastic seed per geology_id; seed registry frozen before generation"},
 "property_transform":{
  "permeability_transform":"same frozen Case-0001 Gaussian-to-permeability transform implementation",
  "permeability_support_mD":[50.0,1000.0],
  "injection_interval_layers_1based":[6,7,8,9,10],
  "porosity":0.20,
  "Kx":"K_SGSim","Ky":"K_SGSim","Kz_over_Kh":0.10,
  "no_post_generation_case_selection":"prohibited"},
 "well_geometry":{
  "pattern":"five-spot",
  "injector_zero_based_xy":[24,24],
  "producers_zero_based_xy":[[4,4],[45,4],[4,45],[45,45]],
  "completion_zero_based_k":[5,6,7,8,9]},
 "control_design":{
  "reference":{"CO2_mass_rate_tonnes_per_day":500.0,"producer_BHP_psi":2000.0},
  "first_multi_case_phase":"GEOLOGY-ONLY VARIATION: hold reference controls fixed to isolate geology effect",
  "later_control_phase":"CONTROL VARIATION REQUIRES A SEPARATE D-series contract defining admissible injection-rate/BHP combinations before generation",
  "reason":"do not confound geology OOD and control OOD in the first expansion"},
 "case_registry":{
  "Case0001":"frozen reference, never regenerated",
  "Case0002_plus":"new independent SGSim realizations only after exact Case0001 geostatistical recipe binding",
  "case_id_assignment":"deterministic and immutable",
  "seed_assignment":"predeclared registry; never chosen by visual/numerical desirability"},
 "split_design":{
  "assignment_timing":"case-level train/validation/test assignment must be frozen before any multi-case model training",
  "first_phase_OOD":"unseen geology at fixed controls",
  "future_OOD":"unseen controls and joint unseen geology+controls"},
 "training_authorized":False,
 "case_generation_authorized":False,
 "blocker":"exact executable/source binding of the Case0001 SGSim geostatistical recipe must precede realization generation"
 }
 gates=dict(D1_bound=True,grid_frozen=True,Case0001_immutable=True,independent_seed_rule=True,
  no_cherrypicking=True,property_transform_same_lineage=True,porosity_frozen=True,anisotropy_ratio_frozen=True,
  well_geometry_fixed_first_phase=True,reference_controls_fixed_first_phase=True,
  geology_and_control_axes_separated=True,true_OOD_geology_defined=True,
  unrecovered_SGeMS_parameters_not_invented=True,seed_registry_required_before_generation=True,
  case_split_required_before_training=True,no_generation_in_D2=True,no_training_in_D2=True)
 ok=all(gates.values())
 status="V16D_SGSIM_MULTI_REALIZATION_EXPERIMENT_DESIGN_FROZEN_EXACT_CASE0001_GEOSTATISTICAL_RECIPE_BINDING_REQUIRED" if ok else "V16D_SGSIM_MULTI_REALIZATION_DESIGN_BLOCKED"
 summary={"milestone":"V16D-2","status":status,"recipe":recipe,"gates":gates,
 "next_milestone":"V16D-3 — Exact Case 0001 SGSim Geostatistical Recipe Provenance and Executable Binding Audit"}
 (OUT/"PAD_Stream_V16D2_Summary.json").write_text(json.dumps(summary,indent=2))
 rows=[
 {"axis":"geology","phase":"first","variation":"independent SGSim realization","controls":"500 t/day, 2000 psi BHP"},
 {"axis":"control","phase":"later","variation":"separately contracted admissible controls","controls":"to be frozen before generation"},
 {"axis":"joint geology+control","phase":"later OOD","variation":"both unseen","controls":"to be frozen"}]
 with (OUT/"V16D2_Expansion_Axes.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print("\nFROZEN FIRST-PHASE DESIGN")
 print("  Grid                 : 50 x 50 x 15")
 print("  Cell size            : 20 x 20 x 4 ft")
 print("  Geology variation    : independent SGSim realizations")
 print("  Porosity             : 0.20")
 print("  Kz/Kh                : 0.10")
 print("  Wells                : same five-spot geometry as Case 0001")
 print("  Controls             : 500 tonnes/day injector; producers 2000 psi BHP")
 print("  First OOD question   : unseen geology at fixed controls")
 print("  Case cherry-picking  : PROHIBITED")
 print("\nPROVENANCE BLOCKER")
 print("  D2 will NOT invent missing SGeMS/SGSim recipe parameters.")
 print("  Exact Case 0001 geostatistical recipe must be source-bound before Case 0002+ generation.")
 print("  Generation now       : NOT AUTHORIZED")
 print("  Training now         : NOT AUTHORIZED")
 print("\n"+"="*78);print("V16D-2 GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nNEXT MILESTONE\n  V16D-3 — Exact Case 0001 SGSim Geostatistical Recipe Provenance and Executable Binding Audit")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()

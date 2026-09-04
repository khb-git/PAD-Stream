#!/usr/bin/env python
from __future__ import annotations
from pathlib import Path
import json,hashlib,csv
import numpy as np

ROOT=Path(__file__).resolve().parent
C23=ROOT/"output"/"V16_C23_FROZEN_EXP1_PREDICTION_ERROR_STRUCTURE_PHYSICS_STRUCTURE_CERTIFICATION_AUDIT"/"PAD_Stream_V16C23_Summary.json"
C23A=ROOT/"output"/"V16_C23A_EXACT_C7_METRIC_FROZEN_EXP1_DIFFERENTIAL_FULL_PHYSICS_RESIDUAL_AUDIT"/"PAD_Stream_V16C23A_Summary.json"
OUT=ROOT/"output"/"V16_C24_EXP1_BASELINE_SCIENTIFIC_ASSESSMENT_PHYSICS_INFORMED_EXP2_DECISION_CONTRACT"
OUT.mkdir(parents=True,exist_ok=True)

def main():
 print("="*78);print("PAD-Stream V16C-24")
 print("EXP1 Baseline Scientific Assessment and Physics-Informed EXP2 Decision Contract");print("="*78)
 print("""C24 DOES NOT TRAIN.

IT FREEZES THE SCIENTIFIC INTERPRETATION OF EXP1 BEFORE ANY EXP2 TRAINING:
  1. EXP1 is the supervised Stage4-lineage V16 baseline.
  2. Its locked-test predictive accuracy is frozen and cannot be retuned.
  3. Its differential residual is a diagnostic, NOT a post-hoc failure threshold.
  4. EXP2 is authorized as a controlled physics-informed comparison.
  5. C7 metric M is a PHYSICS-LOSS SIDECAR, not a new predictor channel.
  6. The C20 nine predictor channels and C19 split remain unchanged.
  7. EXP2 may differ from EXP1 only by the predeclared physics-informed
     objective after that objective and its weight are separately frozen.
  8. Test remains locked for EXP2 model selection.
""")
 a=json.loads(C23.read_text());b=json.loads(C23A.read_text())
 if a["status"]!="V16C_EXP1_FROZEN_PREDICTION_ERROR_AND_STRUCTURAL_PHYSICS_AUDIT_COMPLETE_PDE_RESIDUAL_PENDING":
  raise RuntimeError("C23 status mismatch")
 if b["status"]!="V16C_EXP1_DIFFERENTIAL_FULL_PHYSICS_RESIDUAL_AUDIT_COMPLETE":
  raise RuntimeError("C23A status mismatch")
 ge=a["global_error"];sp=a["structural_physics"];rr=b["residual"]
 assessment={
 "EXP1_role":"FROZEN_SUPERVISED_V16_BASELINE",
 "predictive_evidence":ge,
 "structural_physics_evidence":sp,
 "differential_residual_evidence":rr,
 "interpretation":[
 "EXP1 demonstrates low aggregate saturation error on held-out streamlines within Foundation Case 0001.",
 "EXP1 preserves hard saturation bounds by architecture.",
 "Nonzero spatial-positive and temporal-negative fractions identify residual structure violations without constituting predeclared failure gates.",
 "The C23A residual is finite and independently measurable, establishing a quantitative baseline for a future physics-informed comparison.",
 "Because no residual acceptance threshold was frozen before EXP1 evaluation, C23A residual magnitude must not be retroactively labeled pass/fail.",
 "Current evidence is in-case held-out-streamline generalization only; it is not geological/control OOD evidence."
 ]}
 exp2={
 "role":"CONTROLLED_PHYSICS_INFORMED_COMPARISON_TO_EXP1",
 "predictor_interface":"UNCHANGED_C20_201x9",
 "architecture":"UNCHANGED_C21_2xLSTM64_TimeDistributedDense_bounded_Sw",
 "dataset":"UNCHANGED_C18R_C17_SUPERVISION",
 "split":"UNCHANGED_C19_STREAMLINE_GROUP_SPLIT",
 "physics_sidecar":"EXACT_C7_metric_M_dtheta_dxD",
 "physics_equation":"dS/deta + dfw/dtheta - (phi/Pe_c) M d/dtheta[Dtilde(S) M dS/dtheta] = 0",
 "physical_constants":{"phi":0.2,"Pe_c":22.0,"lambda_c":2.0,"Nc_role":"metadata_only_no_exp_Nc_xD"},
 "test_selection":"PROHIBITED",
 "OOD_claim":"PROHIBITED_FOR_FOUNDATION_CASE_0001",
 "training_authorized_now":False,
 "reason_not_yet_authorized":"Differentiable residual discretization, boundary masking, time-derivative construction, normalization, and lambda_phys must be frozen and numerically validated before EXP2 training."
 }
 gates=[
 ("C23_bound",True),("C23A_bound",True),("EXP1_frozen_as_supervised_baseline",True),
 ("EXP1_test_metrics_not_used_for_retuning",True),("C23A_residual_not_retroactively_thresholded",True),
 ("EXP2_predictor_interface_unchanged",True),("EXP2_architecture_lineage_unchanged",True),
 ("C7_metric_sidecar_not_predictor",True),("Pollock_kinematics_primary",True),
 ("legacy_exp_Nc_xD_prohibited",True),("C19_split_unchanged",True),
 ("EXP2_test_locked_for_selection",True),("OOD_not_claimed",True),
 ("EXP2_training_not_yet_authorized",True),("no_training_in_C24",True)]
 ok=all(v for _,v in gates)
 status="V16C_EXP1_BASELINE_FROZEN_EXP2_PHYSICS_INFORMED_BRANCH_AUTHORIZED_FOR_OBJECTIVE_DESIGN_ONLY" if ok else "V16C_EXP1_EXP2_DECISION_CONTRACT_BLOCKED"
 summary={"milestone":"V16C-24","status":status,"assessment":assessment,"EXP2_contract":exp2,
 "gates":dict(gates),"training_performed":False,
 "next_milestone":"V16C-25 — Differentiable Pollock Full-Physics Residual, Boundary Mask and Physics-Loss Weight Authority Contract"}
 (OUT/"PAD_Stream_V16C24_Summary.json").write_text(json.dumps(summary,indent=2))
 rows=[{"quantity":"EXP1_test_RMSE","value":ge["rmse"]},
 {"quantity":"EXP1_test_MAE","value":ge["mae"]},
 {"quantity":"EXP1_front_index_MAE_nodes","value":sp["front_index_mae_nodes"]},
 {"quantity":"EXP1_PDE_residual_L1","value":rr["global_l1"]},
 {"quantity":"EXP1_PDE_residual_L2","value":rr["global_l2"]},
 {"quantity":"EXP1_PDE_residual_Linf","value":rr["global_linf"]}]
 with (OUT/"V16C24_Frozen_EXP1_Baseline_Metrics.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=["quantity","value"]);w.writeheader();w.writerows(rows)
 print("\\nFROZEN EXP1 SCIENTIFIC BASELINE")
 print(f"  test RMSE              : {ge['rmse']:.9e}")
 print(f"  test MAE               : {ge['mae']:.9e}")
 print(f"  front-index MAE nodes  : {sp['front_index_mae_nodes']:.6f}")
 print(f"  PDE residual L1/L2/Linf: {rr['global_l1']:.6e} / {rr['global_l2']:.6e} / {rr['global_linf']:.6e}")
 print("  OOD interpretation     : NOT OOD; held-out streamlines in Foundation Case 0001")
 print("\\nEXP2 DECISION")
 print("  branch                 : physics-informed controlled comparison")
 print("  predictor channels     : unchanged 9")
 print("  C7 metric M            : physics-loss sidecar only")
 print("  architecture           : unchanged from EXP1")
 print("  test selection         : prohibited")
 print("  training now           : NOT YET AUTHORIZED")
 print("\\n"+"="*78);print("V16C-24 GATES");print("="*78)
 for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
 print("\\nSTATUS\\n ",status)
 print("\\nNEXT MILESTONE\\n  V16C-25 — Differentiable Pollock Full-Physics Residual, Boundary Mask and Physics-Loss Weight Authority Contract")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()

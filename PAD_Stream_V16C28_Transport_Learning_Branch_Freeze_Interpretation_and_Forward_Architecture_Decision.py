#!/usr/bin/env python
from pathlib import Path
import json, csv
ROOT=Path(__file__).resolve().parent
C27=ROOT/"output"/"V16_C27_FROZEN_EXP1_VS_EXP2_COMPARATIVE_AUDIT"/"PAD_Stream_V16C27_Summary.json"
OUT=ROOT/"output"/"V16_C28_TRANSPORT_LEARNING_BRANCH_FREEZE_INTERPRETATION_FORWARD_ARCHITECTURE_DECISION";OUT.mkdir(parents=True,exist_ok=True)

def main():
 print("="*78);print("PAD-Stream V16C-28")
 print("Transport Learning Branch Freeze, Interpretation and Forward Architecture Decision");print("="*78)
 print("""C28 DOES NOT TRAIN, RETUNE, OR SELECT A NEW MODEL.

IT FREEZES THE OBSERVED EXP1-vs-EXP2 TRADEOFF AND DEFINES WHAT MAY HAPPEN NEXT.
NO POST-HOC WINNER CRITERION IS INVENTED.

EXP1 remains the predictive-accuracy baseline.
EXP2 remains the first physics-informed controlled experiment.
Neither is promoted to a universal/Foundation-model claim because all current
evidence comes from Foundation Case 0001 with held-out streamlines, not unseen
geology/control cases.
""")
 c=json.loads(C27.read_text())
 if c["status"]!="V16C_EXP1_VS_EXP2_FROZEN_COMPARATIVE_AUDIT_COMPLETE":raise RuntimeError("C27 prerequisite mismatch")
 pr=c["predictive"];ph=c["physics_residual"];st=c["structural"]
 rmse1=pr["EXP1"]["rmse"];rmse2=pr["EXP2"]["rmse"]
 l21=ph["EXP1"]["l2"];l22=ph["EXP2"]["l2"]
 spos1=st["EXP1"]["spatial_positive_fraction"];spos2=st["EXP2"]["spatial_positive_fraction"]
 tneg1=st["EXP1"]["temporal_negative_fraction"];tneg2=st["EXP2"]["temporal_negative_fraction"]
 decision={
 "EXP1":{"role":"FROZEN_SUPERVISED_PREDICTIVE_BASELINE","promotion":"RETAIN","reason":"lower locked-test saturation error"},
 "EXP2":{"role":"FROZEN_FIRST_PHYSICS_INFORMED_CONTROLLED_EXPERIMENT","promotion":"RETAIN","reason":"lower differential residual and fewer structural violations"},
 "observed_tradeoff":{
  "EXP2_RMSE_change_percent":100*(rmse2-rmse1)/rmse1,
  "EXP2_L2_residual_reduction_percent":100*(l21-l22)/l21,
  "EXP2_spatial_positive_fraction_reduction_percent":100*(spos1-spos2)/spos1,
  "EXP2_temporal_negative_fraction_reduction_percent":100*(tneg1-tneg2)/tneg1},
 "winner":"NOT_DECLARED_BECAUSE_NO_PREDECLARED_COMPOSITE_UTILITY_CRITERION_EXISTS",
 "foundation_model_claim":"NOT_AUTHORIZED_SINGLE_FOUNDATION_CASE_ONLY",
 "EXP3_status":"NOT_AUTHORIZED",
 "EXP3_requirements":[
  "predeclare a new objective/weight or architecture before training",
  "do not tune against locked EXP1/EXP2 test results",
  "validate any changed differentiable residual/operator before training",
  "preserve C19 split for same-case comparisons",
  "reserve true OOD evaluation for unseen Foundation Cases/geologies/controls"],
 "forward_architecture_decision":"CLOSE V16C SINGLE-CASE TRANSPORT LEARNING BASELINE BRANCH; NEXT BUILD MULTI-FOUNDATION-CASE/OOD DATA AUTHORITY BEFORE FOUNDATION-MODEL CLAIMS OR USE A SEPARATELY PREDECLARED EXP3 RESEARCH BRANCH."
 }
 gates=dict(C27_bound=True,EXP1_role_frozen=True,EXP2_role_frozen=True,tradeoff_recorded=True,
  no_posthoc_winner=True,no_retraining=True,no_retuning=True,no_new_model_selection=True,
  EXP3_not_authorized=True,no_foundation_model_claim=True,true_OOD_reserved_for_future_cases=True)
 ok=all(gates.values())
 status="V16C_TRANSPORT_LEARNING_BRANCH_FROZEN_EXP1_EXP2_TRADEOFF_CERTIFIED_FORWARD_OOD_CASE_EXPANSION_REQUIRED" if ok else "V16C_TRANSPORT_BRANCH_FREEZE_BLOCKED"
 summary={"milestone":"V16C-28","status":status,"decision":decision,"gates":gates,
 "next_milestone":"V16D-1 — Multi-Foundation-Case and True OOD Geology/Control Expansion Authority Contract"}
 (OUT/"PAD_Stream_V16C28_Summary.json").write_text(json.dumps(summary,indent=2))
 rows=[
 {"metric":"locked_test_RMSE","EXP1":rmse1,"EXP2":rmse2},
 {"metric":"full_physics_residual_L2","EXP1":l21,"EXP2":l22},
 {"metric":"spatial_positive_fraction","EXP1":spos1,"EXP2":spos2},
 {"metric":"temporal_negative_fraction","EXP1":tneg1,"EXP2":tneg2}]
 with (OUT/"V16C28_Frozen_EXP1_EXP2_Tradeoff.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=["metric","EXP1","EXP2"]);w.writeheader();w.writerows(rows)
 print("\nFROZEN SCIENTIFIC INTERPRETATION")
 print(f"  EXP1 RMSE                         : {rmse1:.9e}")
 print(f"  EXP2 RMSE                         : {rmse2:.9e}")
 print(f"  EXP2 predictive RMSE increase     : {100*(rmse2-rmse1)/rmse1:.3f}%")
 print(f"  EXP1 full-physics residual L2     : {l21:.9e}")
 print(f"  EXP2 full-physics residual L2     : {l22:.9e}")
 print(f"  EXP2 residual L2 reduction        : {100*(l21-l22)/l21:.3f}%")
 print(f"  spatial violation reduction       : {100*(spos1-spos2)/spos1:.3f}%")
 print(f"  temporal violation reduction      : {100*(tneg1-tneg2)/tneg1:.3f}%")
 print("\nMODEL ROLES")
 print("  EXP1 : predictive-accuracy baseline")
 print("  EXP2 : physics-consistency baseline")
 print("  Winner: NOT DECLARED")
 print("  EXP3 : NOT AUTHORIZED")
 print("  Foundation-model claim: NOT AUTHORIZED from Case 0001 alone")
 print("\nFORWARD DECISION")
 print("  Close V16C single-case learning baseline branch.")
 print("  Proceed to multi-Foundation-Case / true-OOD expansion authority.")
 print("\n"+"="*78);print("V16C-28 GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nNEXT MILESTONE\n  V16D-1 — Multi-Foundation-Case and True OOD Geology/Control Expansion Authority Contract")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()

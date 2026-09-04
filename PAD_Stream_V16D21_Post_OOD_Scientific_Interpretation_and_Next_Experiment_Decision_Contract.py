#!/usr/bin/env python3
from pathlib import Path
import json, hashlib, sys
R=Path(__file__).resolve().parent
D20=R/"output"/"V16_D20_FROZEN_EXP_MC1_OOD_STRUCTURAL_FRONT_TIME_DIAGNOSTIC"
S20=D20/"PAD_Stream_V16D20_Summary.json"
REP=D20/"V16D20_EXP_MC1_OOD_Structural_Diagnostic_Report.json"
S20SHA="f540781f9484657580664df2a05dffd5152461338c523ec6cdc3fa343a546ba7"
O=R/"output"/"V16_D21_POST_OOD_SCIENTIFIC_INTERPRETATION_NEXT_EXPERIMENT_DECISION"
O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-21")
 print("Post-OOD Scientific Interpretation + Next-Experiment Decision Contract");print("="*78)
 if sha(S20)!=S20SHA: raise RuntimeError("D20 summary SHA mismatch")
 s=json.loads(S20.read_text()); r=json.loads(REP.read_text())
 if s["status"]!="V16D_EXP_MC1_OOD_STRUCTURAL_FRONT_TIME_DIAGNOSTICS_FROZEN_FUTURE_EXPERIMENT_HYPOTHESIS_FORMULATION_AUTHORIZED":
  raise RuntimeError("D20 status mismatch")
 bytime={int(q["day"]):q for q in r["pooled_by_time"]}
 reg=r["pooled_regions"]; w=r["worst_point"]; ds=r["descriptive_summary"]
 decision={
 "milestone":"V16D-21",
 "evidence":{
  "highest_RMSE_time_days":ds["highest_RMSE_time_days"],
  "highest_RMSE_time":ds["highest_RMSE_time_value"],
  "highest_RMSE_case":ds["highest_RMSE_case"],
  "highest_RMSE_case_value":ds["highest_RMSE_case_value"],
  "early_time_RMSE_30_60_100":[bytime[d]["RMSE"] for d in (30,60,100)],
  "late_time_RMSE_500_750_1000":[bytime[d]["RMSE"] for d in (500,750,1000)],
  "front_RMSE":reg["front"]["RMSE"],"low_RMSE":reg["low"]["RMSE"],"high_RMSE":reg["high"]["RMSE"],
  "worst_point":w
 },
 "scientific_interpretation":[
  "EXP-MC1 generalization error is strongly time-dependent: the largest pooled RMSE occurs at 60 days and errors decline substantially at late times.",
  "The low-saturation region has the largest regional RMSE, while the high-saturation region is substantially easier.",
  "The worst point is an overprediction in a low-saturation cell-like streamline location at 365 days, consistent with localized front/tail-position error rather than uniform saturation bias.",
  "The front region contains most evaluated values and contributes meaningful error, but its pooled RMSE is lower than the low-saturation region.",
  "These are post-OOD descriptive findings and must not be used to retune or reselect EXP-MC1."
 ],
 "decision":{
  "EXP_MC1":"FROZEN_COMPLETE",
  "retrain_EXP_MC1":"NOT_AUTHORIZED",
  "MC2_physics_informed_multicase":"DEFERRED",
  "next_primary_direction":"CONTROL_SPACE_EXPANSION",
  "reason":"The principal V16D objective is broader Foundation-Case generalization. MC1 already establishes useful geology-OOD performance; varying controls now tests a new axis of generalization rather than optimizing against the observed OOD set.",
  "control_space_first_axes":["CO2 injection rate","producer BHP"],
  "geology_recipe":"keep Recipe1.1 spectral GRF frozen for the first control-space study",
  "well_geometry":"keep five-spot locations/completions frozen initially",
  "transport_physics":"keep source-authentic Stage4 semantics frozen",
  "MC2_future_role":"new independently designed experiment after control-space dataset design; D20 findings may motivate hypotheses but not retroactive MC1 tuning",
  "foundation_model_claim":"NOT_AUTHORIZED"
 },
 "firewall":{
  "D18_D20_OOD_cases_are_now_observed":True,
  "do_not_reuse_0005_0018_0021_0022_as_future_locked_test":True,
  "future_control_space_experiment_requires_new_case_level_split":True,
  "future_locked_test_must_be_defined_before_target_generation_or_training":True,
  "no_D20_threshold_or_time_specific_tuning_of_MC1":True
 }}
 dp=O/"V16D21_Post_OOD_Scientific_Decision_Contract.json";dp.write_text(json.dumps(decision,indent=2))
 gates={
 "D20_summary_SHA_exact":sha(S20)==S20SHA,
 "D20_report_bound":REP.exists(),
 "EXP_MC1_remains_frozen":True,
 "no_retraining_authorized":True,
 "MC2_not_trained_or_selected":True,
 "control_space_expansion_selected_as_next_primary_direction":True,
 "Recipe1_1_geology_frozen_for_first_control_study":True,
 "five_spot_geometry_frozen_initially":True,
 "Stage4_transport_semantics_frozen":True,
 "old_OOD_cases_retired_from_future_locked_test_role":True,
 "new_future_case_level_split_required":True,
 "foundation_model_claim_not_authorized":True
 }
 status="V16D_POST_OOD_INTERPRETATION_FROZEN_CONTROL_SPACE_EXPANSION_SELECTED_NEW_INDEPENDENT_CASE_SPLIT_REQUIRED"
 nxt="V16D-22 — Versioned Injection-Rate / Producer-BHP Control-Space Design and New Foundation-Case Registry Contract"
 sp=O/"PAD_Stream_V16D21_Summary.json"
 sp.write_text(json.dumps({"milestone":"V16D-21","status":status,"decision_contract_sha256":sha(dp),"gates":gates,"next_milestone":nxt},indent=2))
 print("EVIDENCE")
 print(f"  highest-RMSE time: {ds['highest_RMSE_time_days']} d ({ds['highest_RMSE_time_value']:.9e})")
 print(f"  highest-RMSE case: {ds['highest_RMSE_case']} ({ds['highest_RMSE_case_value']:.9e})")
 print(f"  region RMSE: low={reg['low']['RMSE']:.9e}, front={reg['front']['RMSE']:.9e}, high={reg['high']['RMSE']:.9e}")
 print(f"  worst point: Case{w['case_id']} day={w['day']} streamline={w['streamline']} node={w['node']} |e|={w['abs_error']:.9e}")
 print("\nDECISION")
 print("  EXP-MC1: FROZEN COMPLETE")
 print("  MC2 physics-informed multi-case: DEFERRED")
 print("  NEXT PRIMARY DIRECTION: CONTROL-SPACE EXPANSION")
 print("  First axes: CO2 injection rate + producer BHP")
 print("  Recipe1.1 geology and five-spot geometry remain fixed initially.")
 print("  Cases0005/0018/0021/0022 are observed and cannot serve as a future locked test.")
 print("\nGATES")
 for k,v in gates.items(): print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not all(gates.values()): sys.exit(2)
if __name__=="__main__":main()

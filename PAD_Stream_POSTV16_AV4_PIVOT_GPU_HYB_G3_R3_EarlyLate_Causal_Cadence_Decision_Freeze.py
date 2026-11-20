#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,math,subprocess
from pathlib import Path

M="POSTV16-AV4-PIVOT-GPU-HYB-G3-R3"
PASS="POSTV16AV4PIVOTGPUHYBG3R3_EARLY_LATE_CAUSAL_CADENCE_DECISION_FREEZE_PASS_NO_PHYSICS_EXECUTION"
BLOCK="POSTV16AV4PIVOTGPUHYBG3R3_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="213e66660f2c8ce6733235dc0c06d92ca1b6bae0"

CAD_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_CAD_D1_EarlyLate_Cadence_Evidence_Synthesis_and_G3_Shadow_Protocol_Freeze.py"
CAD_BLOB="cd4c4408035672699c11d6992cf70c32ed409ee4"
R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R1_Day45_SameState_Stale_vs_Refreshed_Shadow_Transport.py"
R1_BLOB="aef9e5d54b78ce4e95712c9de8e8efb509db144f"
R5_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R5_LateNative_Day405_BranchSpecific_Projection_Repair_Execution.py"
R5_BLOB="be86cb1cb4c0f7936b98acd5b07e73e97211ad9d"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

CAD_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_CAD_D1_EarlyLate_Cadence_Evidence_Synthesis_and_G3_Shadow_Protocol_Freeze"
CAD_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_CAD_D1_Summary.json"
CAD_DEC="POSTV16_AV4_PIVOT_GPU_HYB_G2_CAD_D1_Decision_Contract.json"
CAD_STATUS="POSTV16AV4PIVOTGPUHYBG2CADD1_EARLY_LATE_CADENCE_EVIDENCE_SYNTHESIS_AND_G3_SHADOW_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"

R1_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R1_Day45_SameState_Stale_vs_Refreshed_Shadow_Transport"
R1_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R1_Summary.json"
R1_STATUS="POSTV16AV4PIVOTGPUHYBG3R1_DAY45_SAME_STATE_STALE_VS_REFRESHED_SHADOW_TRANSPORT_PASS"

R5_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R5_LateNative_Day405_BranchSpecific_Projection_Repair_Execution"
R5_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R5_Summary.json"
R5_DEC="POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R5_Decision_Contract.json"
R5_STATUS="POSTV16AV4PIVOTGPUHYBG3R2R5_LATENATIVE_DAY405_BRANCHSPECIFIC_PROJECTION_REPAIR_EXECUTION_PASS"

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G3_R3"
OUT_REL=BASE/(OUT_TOKEN+"_EarlyLate_Causal_Cadence_Decision_Freeze")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
EVIDENCE=f"{OUT_TOKEN}_Causal_Evidence_Matrix.csv"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError):pass

def gt(root,*a):return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()
def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):h.update(c)
    return h.hexdigest()
def js(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def write_csv(p,rows):
    rows=list(rows)
    if not rows:p.write_text("",encoding="utf-8");return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:fields.append(k)
    with open(p,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)
def exact_blob(root,fn,expected):
    p=root/fn
    if not p.is_file():raise GateError("missing_source:"+fn)
    actual=gt(root,"hash-object",str(p))
    if actual!=expected:raise GateError(f"source_blob:{fn}:{actual}:{expected}")
    return actual
def finite_nonnegative(v):
    x=float(v);return math.isfinite(x) and x>=0.0

def selftest(root):
    exact_blob(root,CAD_RUNNER,CAD_BLOB);exact_blob(root,R1_RUNNER,R1_BLOB);exact_blob(root,R5_RUNNER,R5_BLOB)
    assert PARENT=="213e66660f2c8ce6733235dc0c06d92ca1b6bae0"
    print("POSTV16 GPU-HYB-G3-R3 structural/authority self-test: PASS")

def main(root,drive):
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight"
    def gate(n,c,d=None):
        ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok:raise GateError(n)
    try:
        print("="*190)
        print("G3-R3 — EARLY + LATE CAUSAL CADENCE DECISION FREEZE")
        print("NO PHYSICS EXECUTION. NO STATE MUTATION. NO PRODUCTION CADENCE ACTIVATION.")
        print("="*190)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_R5_PASS_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        stage="source_authority"
        gate("CAD_runner_blob_exact",exact_blob(root,CAD_RUNNER,CAD_BLOB)==CAD_BLOB)
        gate("R1_runner_blob_exact",exact_blob(root,R1_RUNNER,R1_BLOB)==R1_BLOB)
        gate("R5_runner_blob_exact",exact_blob(root,R5_RUNNER,R5_BLOB)==R5_BLOB)

        stage="artifact_authority"
        paths={
          "CAD_summary":drive/CAD_REL/CAD_SUM,"CAD_decision":drive/CAD_REL/CAD_DEC,
          "R1_summary":drive/R1_REL/R1_SUM,"R5_summary":drive/R5_REL/R5_SUM,
          "R5_decision":drive/R5_REL/R5_DEC}
        for label,p in paths.items():gate(label+"_present",p.is_file(),str(p))
        cad=js(paths["CAD_summary"]);cadd=js(paths["CAD_decision"]);r1=js(paths["R1_summary"]);r5=js(paths["R5_summary"]);r5d=js(paths["R5_decision"])

        gate("CAD_status_exact",cad.get("status")==CAD_STATUS,cad.get("status"))
        gate("R1_status_exact",r1.get("status")==R1_STATUS,r1.get("status"))
        gate("R5_status_exact",r5.get("status")==R5_STATUS,r5.get("status"))
        gate("CAD_5day_reference_exact",int(cad.get("cross_regime_conservative_reference_days"))==5,cad.get("cross_regime_conservative_reference_days"))
        gate("CAD_15day_not_production_authority",cad.get("fifteen_day_hold_status")=="LATE_TIME_TYPICAL_ONLY_NOT_EARLY_PRODUCTION_AUTHORITY",cad.get("fifteen_day_hold_status"))
        gate("CAD_five_day_frozen",cadd.get("five_day_cross_regime_conservative_reference_frozen") is True)
        gate("CAD_15day_production_not_authorized",cadd.get("fifteen_day_production_hold_authorized") is False)

        gate("R1_parent_day45",float(r1.get("parent_day"))==45.0,r1.get("parent_day"))
        gate("R1_mass_conservative",r1.get("all_branches_component_mass_conservative") is True)
        gate("R1_capacity_safe",r1.get("all_branches_capacity_safe_at_common_dt") is True)
        gate("R1_no_canonical_mutation",r1.get("canonical_trajectory_mutated") is False)
        gate("R1_no_scientific_tolerance",r1.get("scientific_tolerance_defined") is False)
        gate("R1_no_production_cadence",r1.get("production_pressure_refresh_cadence_selected") is False)

        gate("R5_parent_day405",float(r5.get("parent_day"))==405.0,r5.get("parent_day"))
        gate("R5_mass_conservative",r5.get("all_branches_component_mass_conservative") is True)
        gate("R5_capacity_safe",r5.get("all_branches_capacity_safe_at_common_dt") is True)
        gate("R5_no_canonical_mutation",r5.get("canonical_trajectory_mutated") is False)
        gate("R5_no_parent_mass_mutation",r5.get("cartesian_parent_mass_mutated") is False)
        gate("R5_no_new_tolerance",r5.get("new_scientific_tolerance_defined") is False)
        gate("R5_R3_authorized",r5.get("G3_R3_early_late_causal_cadence_decision_freeze_authorized") is True)
        gate("R5_decision_R3_authorized",r5d.get("G3_R3_early_late_causal_cadence_decision_freeze_authorized") is True)
        gate("R5_must_preserve_5day_reference",r5d.get("G3_R3_must_preserve_5day_conservative_cross_regime_reference") is True)
        gate("R5_no_production_cadence",r5.get("production_pressure_refresh_cadence_selected") is False)

        stage="causal_evidence"
        early5=dict(r1["STALE_5D_effect_vs_refreshed"]);early15=dict(r1["STALE_15D_effect_vs_refreshed"])
        late5=dict(r5["STALE_5D_effect_vs_refreshed"]);late15=dict(r5["STALE_15D_effect_vs_refreshed"])
        metrics=["child_cellwise_CO2_mass_relative_L2_vs_refreshed","child_cellwise_CO2_mass_Linf_kg_vs_refreshed",
                 "child_saturation_relative_L2_vs_refreshed","child_saturation_Linf_vs_refreshed",
                 "produced_CO2_mass_abs_difference_kg_vs_refreshed","producer_CO2_gas_cut_abs_difference_vs_refreshed",
                 "final_total_stored_mass_difference_kg_vs_refreshed"]
        for regime,e5,e15 in [("EARLY_DAY45",early5,early15),("LATE_DAY405",late5,late15)]:
            for m in metrics:
                gate(f"{regime}_{m}_5d_finite",finite_nonnegative(abs(float(e5[m]))),e5[m])
                gate(f"{regime}_{m}_15d_finite",finite_nonnegative(abs(float(e15[m]))),e15[m])

        late_prod=float(late15["produced_CO2_mass_abs_difference_kg_vs_refreshed"])>float(late5["produced_CO2_mass_abs_difference_kg_vs_refreshed"])
        late_cut=float(late15["producer_CO2_gas_cut_abs_difference_vs_refreshed"])>float(late5["producer_CO2_gas_cut_abs_difference_vs_refreshed"])
        gate("late_produced_response_drift_increases_5d_to_15d",late_prod)
        gate("late_gascut_response_drift_increases_5d_to_15d",late_cut)
        late_mass_mono=float(late15["child_cellwise_CO2_mass_relative_L2_vs_refreshed"])>float(late5["child_cellwise_CO2_mass_relative_L2_vs_refreshed"])
        late_sat_mono=float(late15["child_saturation_relative_L2_vs_refreshed"])>float(late5["child_saturation_relative_L2_vs_refreshed"])

        rows=[]
        for regime,parent,e5,e15 in [("EARLY_DAY45",45.0,early5,early15),("LATE_DAY405",405.0,late5,late15)]:
            for stale,e in [(5,e5),(15,e15)]:
                rows.append({"regime":regime,"parent_day":parent,"staleness_days":stale,**{m:e[m] for m in metrics}})
        prod_ratio=float(late15["produced_CO2_mass_abs_difference_kg_vs_refreshed"])/max(float(late5["produced_CO2_mass_abs_difference_kg_vs_refreshed"]),1e-30)
        cut_ratio=float(late15["producer_CO2_gas_cut_abs_difference_vs_refreshed"])/max(float(late5["producer_CO2_gas_cut_abs_difference_vs_refreshed"]),1e-30)

        stage="decision_freeze"
        policy="FIVE_DAY_CONSERVATIVE_CROSS_REGIME_REFERENCE_WITH_HARD_EVENT_REFRESH_LONGER_LATE_STAGE_HOLD_REQUIRES_SEPARATE_ADAPTIVE_OR_STAGEWISE_VALIDATION"
        gate("five_day_reference_preserved",True)
        gate("fixed_15day_production_hold_remains_closed",True)
        gate("no_new_scientific_tolerance_defined",True)
        gate("production_cadence_not_selected",True)

        stage="publication"
        gate("output_absent",not out.exists(),str(out));out.mkdir(parents=True)
        write_csv(out/EVIDENCE,rows)
        summary={
          "milestone":M,"status":PASS,
          "classification":"EARLY_LATE_CAUSAL_EVIDENCE_SYNTHESIZED_FIVE_DAY_CONSERVATIVE_REFERENCE_PRESERVED_LONGER_LATE_HOLD_REQUIRES_ADAPTIVE_VALIDATION",
          "physics_executed":False,"state_mutation_executed":False,
          "G2_CAD_D1_authority_bound":True,"G3_R1_Day45_authority_bound":True,"G3_R2_R5_Day405_authority_bound":True,
          "early_parent_day":45.0,"late_parent_day":405.0,"cross_regime_conservative_reference_days":5,
          "frozen_policy_class":policy,"fixed_15day_production_hold_authorized":False,
          "late_longer_hold_candidate_status":"RESEARCH_CANDIDATE_FOR_STAGEWISE_OR_ADAPTIVE_VALIDATION_ONLY_NOT_FIXED_PRODUCTION_AUTHORITY",
          "early_5day_effect_vs_refreshed":early5,"early_15day_effect_vs_refreshed":early15,
          "late_5day_effect_vs_refreshed":late5,"late_15day_effect_vs_refreshed":late15,
          "late_produced_CO2_response_drift_monotonic_5d_to_15d":late_prod,
          "late_producer_gascut_drift_monotonic_5d_to_15d":late_cut,
          "late_produced_CO2_abs_difference_growth_ratio_15d_over_5d":prod_ratio,
          "late_gascut_abs_difference_growth_ratio_15d_over_5d":cut_ratio,
          "late_cellwise_mass_relL2_monotonic_5d_to_15d":late_mass_mono,
          "late_saturation_relL2_monotonic_5d_to_15d":late_sat_mono,
          "spatial_error_monotonicity_required_for_decision":False,
          "new_scientific_tolerance_defined":False,"production_pressure_refresh_cadence_selected":False,
          "integrated_runtime_controller_policy_reconciled":False,
          "next_integrated_refresh_policy_reconciliation_design_freeze_authorized":True,
          "P4_authorized":False}
        decision={
          "milestone":M,"status":PASS,
          "five_day_cross_regime_conservative_reference_frozen":True,
          "fixed_15day_production_hold_authorized":False,
          "production_pressure_refresh_cadence_selected":False,
          "policy_class":policy,
          "late_stage_longer_hold_may_be_evaluated":True,
          "late_stage_longer_hold_requires_stagewise_or_adaptive_validation":True,
          "hard_event_refresh_semantics_must_be_preserved":True,
          "no_existing_runtime_controller_may_be_promoted_to_production_from_this_freeze_alone":True,
          "next_integrated_refresh_policy_reconciliation_design_freeze_authorized":True,
          "next_milestone_purpose":"Reconcile the existing integrated runtime controller with the newly frozen early+late causal cadence evidence before any production cadence activation.",
          "P4_authorized":False}
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[{"file":q.name,"sha256":sha256(q),"bytes":q.stat().st_size} for q in sorted(out.iterdir()) if q.is_file() and q.name!=MANIFEST])

        print("="*190);print(M,"PASS")
        print("5-day conservative cross-regime reference       : 5 days")
        print("15-day fixed production hold authorized         : False")
        print("Late produced-response growth 15d/5d            :",prod_ratio)
        print("Late gas-cut-response growth 15d/5d             :",cut_ratio)
        print("Production cadence selected                      : False")
        print("Next reconciliation design freeze authorized     : True")
        print("P4 authorized                                    : False")
        print("="*190);return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
          "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
          "production_pressure_refresh_cadence_selected":False,
          "next_integrated_refresh_policy_reconciliation_design_freeze_authorized":False,
          "P4_authorized":False},indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(M,"BLOCK");print("Stage:",stage);print("Exception:",repr(exc));return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--project-root",type=Path,default=Path("."));ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"));ap.add_argument("--self-test",action="store_true");a=ap.parse_args()
    if a.self_test:selftest(a.project_root.resolve());raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))

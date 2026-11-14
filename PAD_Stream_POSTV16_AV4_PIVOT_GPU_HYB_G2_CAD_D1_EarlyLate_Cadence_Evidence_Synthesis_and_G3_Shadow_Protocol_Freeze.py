#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,subprocess
from pathlib import Path

M="POSTV16-AV4-PIVOT-GPU-HYB-G2-CAD-D1"
PASS="POSTV16AV4PIVOTGPUHYBG2CADD1_EARLY_LATE_CADENCE_EVIDENCE_SYNTHESIS_AND_G3_SHADOW_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"
BLOCK="POSTV16AV4PIVOTGPUHYBG2CADD1_AUTHORITY_OR_EVIDENCE_BLOCK_NO_PHYSICS_EXECUTION"
BRANCH="postv16-av4-pivot"
PARENT="5e6353f3dcf3890666340065e0aa3e0ade104888"
RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

A1_REL=BASE/"POSTV16_P_CAD_A1_Empirical_5Day_Envelope_and_Targeted_Early_Probe_Design_Freeze"
A1_SUM="PAD_Stream_POSTV16_P_CAD_A1_Summary.json"
A1_STATUS="POSTV16PCADA1_EMPIRICAL_5DAY_ENVELOPE_AND_TARGETED_EARLY_PROBE_DESIGN_FREEZE_PASS_NO_EXPENSIVE_EXECUTION"

A2_REL=BASE/"POSTV16_P_CAD_A2_HoldEnvelope_FailureDriver_and_GPU_TargetedProbe_Protocol_Freeze"
A2_SUM="PAD_Stream_POSTV16_P_CAD_A2_Summary.json"
A2_STATUS="POSTV16PCADA2_HOLD_ENVELOPE_FAILURE_DRIVER_AND_GPU_TARGETED_PROBE_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"

R1_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Rank1_Day75_Day80_ExactFlow_and_Hybrid_Endpoint_Diagnostic"
R1_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Summary.json"
R1_STATUS="POSTV16AV4PIVOTGPUHYBG2R1R1_RANK1_DAY75_DAY80_EXACT_FLOW_AND_READONLY_HYBRID_ENDPOINT_DIAGNOSTIC_PASS"

R2_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Rank2_Day120_Day125_ExactFlow_and_Hybrid_Endpoint_Diagnostic"
R2_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Summary.json"
R2_STATUS="POSTV16AV4PIVOTGPUHYBG2R2_RANK2_DAY120_DAY125_EXACT_FLOW_AND_READONLY_HYBRID_ENDPOINT_DIAGNOSTIC_PASS"

R3_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Rank3_Day40_Day45_ExactFlow_and_Hybrid_Endpoint_Diagnostic"
R3_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Summary.json"
R3_STATUS="POSTV16AV4PIVOTGPUHYBG2R3_RANK3_DAY40_DAY45_EXACT_FLOW_AND_READONLY_HYBRID_ENDPOINT_DIAGNOSTIC_PASS"

VIS_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_VIS_A1_R1_Certified_EarlyTime_3D_Visualization_Repair"
VIS_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_VIS_A1_R1_Summary.json"
VIS_STATUS="POSTV16AV4PIVOTGPUHYBG2VISA1R1_CERTIFIED_EARLYTIME_3D_VISUALIZATION_REPAIR_PASS_NO_PHYSICS_MUTATION"

DAY30_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_A0_Day30_CurrentAuthority_SameTime_Flow_Refresh_Bridge"
DAY30_FLOW="POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_A0_Day30_Exact_Flow_Diagnostic.npz"
DAY30_RESTART="POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_A0_Day30_CurrentAuthority_Refreshed_Restart.npz"
DAY40_STATE="POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Exact_Day40_State.npz"
DAY40_DIAG="POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Day40_ExactFlow_and_Hybrid_Diagnostic.npz"
DAY45_STATE="POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Exact_Day45_State.npz"
DAY45_DIAG="POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Day45_ExactFlow_and_Hybrid_Diagnostic.npz"

PRIMARY=["pressure_relative_L2","flux_relative_L2","tau_end_relative_L2",
         "streamline_weight_relative_L2","producer_connectivity_mismatch_fraction",
         "path_RMS_displacement_ft"]

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G2_CAD_D1"
OUT_REL=BASE/(OUT_TOKEN+"_EarlyLate_Cadence_Evidence_Synthesis_and_G3_Shadow_Protocol_Freeze")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
EVIDENCE=f"{OUT_TOKEN}_EarlyLate_Evidence_Matrix.csv"
PROTOCOL=f"{OUT_TOKEN}_G3_SameState_Shadow_Protocol.json"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError): pass
def gt(root,*a): return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()
def js(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()
def write_csv(p,rows):
    if not rows: Path(p).write_text("",encoding="utf-8"); return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with open(p,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)

def selftest():
    assert len(PRIMARY)==6
    print("POSTV16 GPU-HYB-G2-CAD-D1 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve(); drive=drive.resolve(); out=drive/OUT_REL; blocked=drive/BLOCK_REL
    gates=[]; stage="preflight"
    def gate(n,c,d=None):
        ok=bool(c); gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok: raise GateError(n)
    try:
        print("="*180)
        print("G2-CAD-D1 — EARLY+LATE CADENCE SYNTHESIS / G3 SAME-STATE SHADOW PROTOCOL FREEZE")
        print("NO PHYSICS EXECUTION. NO CADENCE SELECTION. NO STATE MUTATION.")
        print("="*180)

        stage="repository"
        gate("branch",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_VIS_A1_R1",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("clean",gt(root,"status","--porcelain")=="")

        stage="authorities"
        a1=js(drive/A1_REL/A1_SUM); a2=js(drive/A2_REL/A2_SUM)
        r1=js(drive/R1_REL/R1_SUM); r2=js(drive/R2_REL/R2_SUM); r3=js(drive/R3_REL/R3_SUM)
        vis=js(drive/VIS_REL/VIS_SUM)
        gate("A1_status",a1.get("status")==A1_STATUS,a1.get("status"))
        gate("A2_status",a2.get("status")==A2_STATUS,a2.get("status"))
        gate("R1_status",r1.get("status")==R1_STATUS,r1.get("status"))
        gate("R2_status",r2.get("status")==R2_STATUS,r2.get("status"))
        gate("R3_status",r3.get("status")==R3_STATUS,r3.get("status"))
        gate("VIS_status",vis.get("status")==VIS_STATUS,vis.get("status"))

        strict=int(a1["strict_longest_hold_with_all_primary_maxima_within_5day_max_envelope_days"])
        typical=int(a1["typical_longest_hold_with_all_primary_means_within_5day_max_envelope_days"])
        gate("late_strict_longest_5d",strict==5,strict)
        gate("late_typical_longest_15d",typical==15,typical)
        gate("all_three_early_complete",r3.get("all_three_ranked_early_probe_pairs_complete") is True)
        gate("cadence_freeze_authorized",r3.get("cadence_decision_freeze_authorized") is True)
        gate("no_production_cadence_selected",
             all(x.get("production_pressure_refresh_cadence_selected") is False for x in [a1,a2,r1,r2,r3]))

        stage="early_evidence"
        early=[("Day40->45",r3),("Day75->80",r1),("Day120->125",r2)]
        rows=[]; max_inf={m:0.0 for m in PRIMARY}
        for label,s in early:
            gate(label+"_all_primary_within",s.get("all_primary_within_late_5day_max_envelope") is True)
            gate(label+"_no_exceed",s.get("primary_metrics_exceeding_late_5day_max")==[],s.get("primary_metrics_exceeding_late_5day_max"))
            for m in PRIMARY:
                inf=float(s["P_CAD_inflation_vs_late_5day_max"][m]); max_inf[m]=max(max_inf[m],inf)
                rows.append({"regime":"EARLY","window":label,"hold_days":5,"metric":m,
                             "change":float(s["P_CAD_primary_metrics"][m]),
                             "reference_late_5day_max":float(s["late_5day_max_envelope"][m]),
                             "ratio_vs_reference":inf,"within_reference":True})
        for m in PRIMARY:
            rows.append({"regime":"EARLY_SYNTHESIS","window":"max across three early 5-day probes","hold_days":5,
                         "metric":m,"change":"","reference_late_5day_max":"",
                         "ratio_vs_reference":max_inf[m],"within_reference":max_inf[m] <= 1.0+1e-12})

        stage="G3_inputs"
        required=[drive/DAY30_REL/DAY30_FLOW,drive/DAY30_REL/DAY30_RESTART,
                  drive/R3_REL/DAY40_STATE,drive/R3_REL/DAY40_DIAG,
                  drive/R3_REL/DAY45_STATE,drive/R3_REL/DAY45_DIAG]
        for p in required: gate("present:"+p.name,p.is_file(),str(p))

        protocol={
          "milestone":M,"status":PASS,
          "purpose":"Causal same-parent-state test of stale versus refreshed global flow authority.",
          "rank1_parent_state":{
            "physical_time_days":45.0,
            "state_sha256":sha(drive/R3_REL/DAY45_STATE),
            "physical_state_definition":"freeze Day45 cellwise CO2 component mass and all cumulative ledgers"
          },
          "branches":[
            {"name":"REFRESHED_0D","flow_epoch_source_day":45.0,"staleness_days":0.0},
            {"name":"STALE_5D","flow_epoch_source_day":40.0,"staleness_days":5.0},
            {"name":"STALE_15D","flow_epoch_source_day":30.0,"staleness_days":15.0}
          ],
          "same_state_mass_consistency":{
            "canonical_parent_quantity":"cellwise CO2 component mass at exact Day45",
            "branch_pressure_handling":"for each branch pressure field, invert the SAME frozen Day45 cellwise CO2 mass to a branch-consistent saturation before CV sampling",
            "cumulative_injection_production_stored_ledgers_must_be_identical":True
          },
          "shadow_transport":{
            "geometry":"branch-specific exact Pollock/TOF/control-volume geometry",
            "common_dt":"minimum admissible exact CFL timestep across all three branches",
            "transport_operator":"existing exact conservative E37A control-volume transport",
            "mapback":"existing exact E37A component-mass map-back",
            "capacity_and_EOS":"existing production capacity preflight and EOS inversion",
            "capillary":"same conservative Cartesian no-flow capillary redistribution",
            "canonical_state_mutation":False
          },
          "comparison_metrics":[
            "child_cellwise_CO2_mass_relative_L2_vs_refreshed",
            "child_cellwise_CO2_mass_Linf_kg_vs_refreshed",
            "child_saturation_relative_L2_vs_refreshed",
            "child_saturation_Linf_vs_refreshed",
            "produced_CO2_mass_difference_kg_vs_refreshed",
            "producer_CO2_gas_cut_difference_vs_refreshed",
            "mapback_mass_closure_kg","capacity_margin_kg"
          ],
          "scientific_tolerance_defined":False,
          "G3_rank1_shadow_execution_authorized":True
        }

        stage="publication"
        gate("output_absent",not out.exists(),str(out)); out.mkdir(parents=True)
        summary={
          "milestone":M,"status":PASS,
          "classification":"FIVE_DAY_CROSS_REGIME_CONSERVATIVE_REFERENCE_CERTIFIED_FIFTEEN_DAY_LATE_TYPICAL_ONLY_G3_SAME_STATE_STALE_VS_REFRESHED_SHADOW_EXECUTION_AUTHORIZED",
          "late_strict_longest_hold_days":strict,
          "late_typical_longest_hold_days":typical,
          "early_5day_probe_windows":[[40,45],[75,80],[120,125]],
          "all_three_early_5day_probes_within_late_5day_max_envelope":True,
          "maximum_early_inflation_vs_late_5day_max_by_metric":max_inf,
          "cross_regime_conservative_reference_days":5,
          "fifteen_day_hold_status":"LATE_TIME_TYPICAL_ONLY_NOT_EARLY_PRODUCTION_AUTHORITY",
          "production_pressure_refresh_cadence_selected":False,
          "G3_rank1_same_state_shadow_execution_authorized":True,
          "G3_rank1_parent_day":45,
          "G3_rank1_staleness_branches_days":[0,5,15],
          "new_scientific_tolerance_defined":False,
          "Hybrid_recurrent_state_mutation_authorized":False,
          "P4_authorized":False
        }
        decision={
          "milestone":M,"status":PASS,
          "five_day_cross_regime_conservative_reference_frozen":True,
          "fifteen_day_production_hold_authorized":False,
          "production_pressure_refresh_cadence_selected":False,
          "G3_same_state_shadow_protocol_frozen":True,
          "G3_rank1_execution_authorized":True,
          "G3_rank1_parent_day":45,
          "G3_rank1_branches":["REFRESHED_0D","STALE_5D","STALE_15D"],
          "next_decision_after_G3":"Use causal same-state transport-impact evidence to decide whether a longer fixed/stagewise/adaptive flow hold is defensible.",
          "P4_authorized":False
        }
        write_csv(out/EVIDENCE,rows)
        (out/PROTOCOL).write_text(json.dumps(protocol,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/GATES,gates)
        manifest=[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
                  for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST]
        write_csv(out/MANIFEST,manifest)

        print("="*180)
        print(M,"PASS")
        print("Late strict longest hold days            :",strict)
        print("Late typical longest hold days           :",typical)
        print("All three early 5-day probes pass        : True")
        print("Cross-regime conservative reference      : 5 days")
        print("15-day production hold authorized        : False")
        print("Production cadence selected              : False")
        print("G3 Day45 shadow execution authorized     : True")
        print("G3 branches                              : 0d / 5d / 15d stale")
        print("P4 authorized                            : False")
        print("="*180)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps(
          {"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
           "production_pressure_refresh_cadence_selected":False,"G3_rank1_execution_authorized":False,
           "P4_authorized":False},indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(M,"BLOCK");print("Stage:",stage);print("Exception:",repr(exc));return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:selftest();raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))

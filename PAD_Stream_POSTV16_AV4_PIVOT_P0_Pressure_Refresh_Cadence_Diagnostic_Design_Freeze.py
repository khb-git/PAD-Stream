#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any

MILESTONE = "POSTV16-AV4-PIVOT-P0"
STATUS_PASS = (
    "AV4PIVOTP0_PARALLEL_PRESSURE_REFRESH_CADENCE_DIAGNOSTIC_DESIGN_FREEZE_PASS_"
    "EXACT_CERTIFICATION_BRANCH_UNCHANGED_NO_PHYSICAL_TIME_ADVANCE_NO_TRAINING"
)

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT = "50726da2dad3058fc92a7182f2a34ac9117cd32c"
EXPECTED_BRANCH = "postv16-av4-pivot"

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
OUT_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P0_Pressure_Refresh_Cadence_Diagnostic_Design_Freeze"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P0_BLOCKED"

A1 = "PAD_Stream_POSTV16_AV4_A1_Spatial_Mobility_Pressure_Refresh_and_Flow_Epoch_Contract_Freeze.py"
A1_BLOB = "9c48fd564be748295576264a9f9c6ad67327fdd2"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
A6E = "PAD_Stream_POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution.py"
A6E_BLOB = "e3dcb0aa9354c399904f7f0e830b6a1fddd78987"
F4R3 = "PAD_Stream_POSTV16_AV4_F4_R3_Terminal_Producer_PassThrough_Repair_Execution.py"
F4R3_BLOB = "2e84ab09f9ae7af6f977eabc3d9465d325fad717"
SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
SG4 = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG4_BLOB = "8d49f88bdf55b0da087af2bed04e69967740e695"
SG5 = "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
SG5_BLOB = "9a0b64ea7e669904d0d9855ade1c6b052f05ecea"
SG6 = "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py"
SG6_BLOB = "70ceda68e02894167958d753d88b4dbd694731ab"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"
R3R2R1 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3R2R1_BLOB = "740c6da03e73906646bf0153633187e749449f31"

SOURCE_BLOBS = {
    A1:A1_BLOB, A2E:A2E_BLOB, A6E:A6E_BLOB, F4R3:F4R3_BLOB,
    SG2:SG2_BLOB, SG3:SG3_BLOB, SG4:SG4_BLOB, SG5:SG5_BLOB,
    SG6:SG6_BLOB, SG7D:SG7D_BLOB, R3R2R1:R3R2R1_BLOB,
}

A1_REL = BASE_AV4 / "POSTV16_AV4_A1_Spatial_Mobility_Pressure_Refresh_and_Flow_Epoch_Contract_Freeze"
A1_CADENCE = "POSTV16_AV4_A1_Refresh_State_Machine_and_Cadence_Policy.json"

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_STATUS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
CONTROL_STATE_FILE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
CONTROL_STATE_SHA256 = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"
TARGET_DAYS = [30.0,60.0,100.0,150.0,250.0,365.0,500.0,750.0,1000.0]

class GateError(RuntimeError):
    pass

def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git","-C",str(root),*args],
        check=True,text=True,capture_output=True
    ).stdout.strip()

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()

def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj,indent=2,sort_keys=True)+"\n").encode("utf-8")

def csv_bytes(rows: list[dict[str,Any]]) -> bytes:
    if not rows:
        return b""
    buf=io.StringIO()
    w=csv.DictWriter(buf,fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")

def immutable_publish(out: Path, files: dict[str,bytes]) -> None:
    if out.exists():
        existing=[p for p in out.iterdir() if p.is_file()]
        if existing:
            raise GateError(f"output_already_exists:{out}")
    out.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():
        p=out/name
        if p.exists():
            raise GateError(f"artifact_already_exists:{p}")
        tmp=p.with_suffix(p.suffix+".tmp")
        tmp.write_bytes(data)
        tmp.replace(p)

def self_test() -> None:
    assert EXPECTED_BRANCH == "postv16-av4-pivot"
    assert TARGET_DAYS[5] == 365.0
    assert TARGET_DAYS[6] == 500.0
    assert 50.0 > 5.0
    assert A1_BLOB != A2E_BLOB
    print("POSTV16 AV4 PIVOT P0 design-freeze structural self-test: PASS")

def main(project_root: Path, drive_root: Path) -> int:
    root=Path(project_root).resolve()
    drive=Path(drive_root).resolve()
    out=drive/OUT_REL
    block=drive/BLOCK_REL

    gates: dict[str,dict[str,Any]]={}
    def gate(name: str, passed: Any, value: Any=None):
        ok=bool(passed)
        gates[name]={"status":"PASS" if ok else "FAIL","detail":value}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    print("="*180)
    print("POSTV16-AV4-PIVOT-P0 -- PARALLEL PRESSURE-REFRESH CADENCE DIAGNOSTIC DESIGN FREEZE")
    print("="*180)
    print("PARALLEL TO R3-R6-R1 EXACT SAME-TIME FIXED-POINT CERTIFICATION.")
    print("NO READ/WRITE OF R3-R6-R1 RECOVERY CHECKPOINTS.")
    print("NO FIVE-STAGE E2 ASSIGNMENT. NO MAPBACK. NO TRAINING. NO PHYSICAL-TIME ADVANCE.")
    print()

    try:
        gate("repository_branch_is_pivot", git_text(root,"branch","--show-current")==EXPECTED_BRANCH,
             git_text(root,"branch","--show-current"))
        gate("repository_parent_is_R3R6R1_commit", git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,
             git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean", git_text(root,"status","--porcelain")=="",
             repr(git_text(root,"status","--porcelain")))

        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual==expected, actual)

        # Bind original A1 cadence policy: cadence explicitly deferred, not abandoned.
        a1dir=drive/A1_REL
        cadence_path=a1dir/A1_CADENCE
        gate("A1_cadence_policy_present", cadence_path.is_file(), str(cadence_path))
        cadence=json.loads(cadence_path.read_text(encoding="utf-8"))
        periodic=cadence["production_periodic_cadence"]
        gate("A1_numeric_cadence_was_deferred",
             periodic["selected_numeric_interval"] is None
             and periodic["policy"]=="DEFER_UNTIL_SINGLE_REFRESH_OPERATOR_VALIDATION_PASSES",
             periodic)

        # Bind successful single refresh operator validation.
        a2edir=drive/A2E_REL
        a2e_summary_path=a2edir/A2E_SUMMARY
        gate("A2E_summary_present", a2e_summary_path.is_file(), str(a2e_summary_path))
        a2e_summary=json.loads(a2e_summary_path.read_text(encoding="utf-8"))
        gate("A2E_single_refresh_operator_PASS",
             a2e_summary.get("status")==A2E_STATUS,
             a2e_summary.get("status"))

        # Bind the frozen integrated state that carries all nine diagnostic target times.
        control=drive/A6E_REL/CONTROL_STATE_FILE
        gate("A6E_integrated_state_present", control.is_file(), str(control))
        gate("A6E_integrated_state_sha_exact",
             sha256_file(control)==CONTROL_STATE_SHA256,
             sha256_file(control) if control.is_file() else "missing")

        purpose={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "research_question":(
                "How rapidly do pressure, Darcy fluxes, Pollock streamline geometry and TOF "
                "become stale as saturation evolves, and what pressure-refresh cadence is "
                "actually required before ML acceleration is introduced?"
            ),
            "relationship_to_exact_branch":{
                "R3R6R1_role":"exact same-time conservative fixed-point certification / teacher-authority research branch",
                "pivot_role":"flow-staleness and cadence-sensitivity diagnostics",
                "replacement":False,
                "parallel":True,
                "R3R6R1_checkpoints_read":False,
                "R3R6R1_checkpoints_written":False,
            },
            "reason_for_pivot":(
                "A1 explicitly deferred numeric periodic cadence until the single-refresh operator "
                "was validated. A2E has now validated one same-time spatial-mobility pressure/Darcy/"
                "Pollock/TOF refresh. The cadence question is therefore eligible for direct study "
                "without requiring the exact certification branch to finish first."
            ),
        }

        architecture={
            "pivot_id":"AV4_PARALLEL_REFRESH_CADENCE_DIAGNOSTIC_V1",
            "phase_P1":{
                "name":"existing-snapshot pressure-staleness pilot",
                "input_authority":"A6E AV3CR0003 integrated Cartesian states",
                "target_days":TARGET_DAYS,
                "primary_post_day365_days":[365.0,500.0,750.0,1000.0],
                "operations":[
                    "load frozen Cartesian saturation only",
                    "recompute spatial Corey total mobility",
                    "recompute exact pressure using frozen SG2/SG3 physics",
                    "recompute conservative Darcy fluxes",
                    "optionally retrace Pollock and rebuild SG6 TOF",
                    "compare refreshed fields with selected reference flow epoch",
                ],
                "forbidden":[
                    "five-stage E2 assignment",
                    "streamline-to-grid mapback",
                    "same-time fixed-point iteration",
                    "transport feedback from refreshed geometry",
                ],
            },
            "phase_P2":{
                "name":"dense frozen-flow snapshot generation for scheduled-cadence study",
                "window_days":[365.0,500.0],
                "diagnostic_snapshot_spacing_days":5.0,
                "cadence_policies_days":[50.0,5.0],
                "transport_authority":"unchanged frozen-flow F4-R3 transport physics",
                "feedback":"none during snapshot generation",
            },
            "phase_P3":{
                "name":"exact flow-field refresh diagnostics at dense snapshots",
                "pipeline":[
                    "S(t)","spatial mobility","pressure","Darcy flux","Pollock","TOF"
                ],
                "same_time":True,
                "transport_restart_from_refreshed_geometry":False,
            },
            "phase_P4":{
                "name":"cadence comparison and selection",
                "policies":["frozen flow","50-day refresh","5-day refresh"],
                "selection_rule":"accuracy-versus-cost evidence; no cadence preselected in P0",
            },
            "phase_P5":{
                "name":"ML refresh comparison",
                "comparison":[
                    "exact refreshed pressure vs ML pressure",
                    "exact vs ML Darcy flux",
                    "exact vs ML streamline geometry",
                    "exact vs ML TOF",
                ],
                "training_authorized_now":False,
            },
        }

        metrics={
            "pressure":[
                "relative_L2_vs_reference",
                "Linf_psi_vs_reference",
                "producer-cell pressure changes",
            ],
            "darcy":[
                "face-flux relative_L2",
                "face-flux Linf",
                "local conservation residual",
                "global conservation mismatch",
            ],
            "streamlines":[
                "producer-capture count",
                "RMS node displacement_m",
                "maximum node displacement_m",
                "endpoint displacement_m",
            ],
            "tof":[
                "relative_L2",
                "weighted mean shift_days",
                "weighted P50 shift_days",
                "weighted P90 shift_days",
            ],
            "compute":[
                "pressure refresh wall time",
                "Darcy wall time",
                "Pollock wall time",
                "TOF rebuild wall time",
                "total diagnostic refresh wall time",
            ],
            "P0_numeric_acceptance_thresholds":"NONE; P0 freezes observables, not an arbitrary production cadence.",
        }

        guardrails={
            "main_exact_branch_commit":EXPECTED_PARENT,
            "pivot_git_branch":EXPECTED_BRANCH,
            "R3R6R1_execution_may_continue_in_parallel":True,
            "R3R6R1_outcome_required_before_P1":False,
            "R3R6R1_recovery_tree_access":"FORBIDDEN",
            "O3R7_authorized":False,
            "F5_dataset_generation_authorized":False,
            "training_authorized":False,
            "dynamic_teacher_authority_claimed":False,
            "diagnostic_refresh_is_not_a_same_time_fixed_point_claim":True,
            "diagnostic_refresh_is_not_a_conservative_transport_restart_claim":True,
            "support_expansion":False,
            "capacity_relaxation":False,
            "per_CV_mass_relaxation":False,
        }

        plots={
            "P1_required_quantitative":[
                "pressure_relative_L2_vs_day.png",
                "pressure_Linf_psi_vs_day.png",
                "darcy_flux_relative_L2_vs_day.png",
                "tof_relative_L2_vs_day.png",
                "streamline_RMS_displacement_vs_day.png",
                "diagnostic_refresh_runtime_vs_day.png",
            ],
            "P1_required_3D":[
                "3D_CO2_saturation_plume_by_snapshot.png",
                "3D_pressure_field_by_snapshot.png",
                "3D_Darcy_flow_by_snapshot.png",
                "3D_Pollock_streamlines_by_snapshot.png",
                "3D_TOF_colored_streamlines_by_snapshot.png",
                "3D_frozen_vs_refreshed_streamline_overlay_by_snapshot.png",
            ],
            "P2_P4_required_quantitative":[
                "frozen_vs_50d_vs_5d_pressure_error.png",
                "frozen_vs_50d_vs_5d_darcy_error.png",
                "frozen_vs_50d_vs_5d_tof_error.png",
                "frozen_vs_50d_vs_5d_streamline_displacement.png",
                "cadence_accuracy_vs_compute_cost.png",
            ],
            "P2_P4_required_3D":[
                "3D_frozen_vs_50d_vs_5d_pressure_comparison.png",
                "3D_frozen_vs_50d_vs_5d_Darcy_comparison.png",
                "3D_frozen_vs_50d_vs_5d_streamline_comparison.png",
                "3D_frozen_vs_50d_vs_5d_TOF_colored_streamline_comparison.png",
                "3D_frozen_vs_50d_vs_5d_CO2_plume_comparison.png",
            ],
            "matched_view_requirement":(
                "All frozen/50-day/5-day 3D comparison figures must use matched camera, "
                "domain bounds, axis orientation, and consistent scalar normalization within "
                "each compared physical quantity so geometric and field differences are visually honest."
            ),
            "visual_story_requirement":(
                "For selected snapshots, publish the same-time spatial chain "
                "S(x,t) -> P(x,t) -> u(x,t) -> Pollock geometry -> TOF so plume evolution "
                "can be directly related to flow-field and path changes."
            ),
            "advisor_use":(
                "P1 quantitative and 3D figures are explicitly intended to provide immediate "
                "AV-series evidence while exact R3-R6-R1 certification continues."
            ),
        }

        handoff={
            "milestone":"POSTV16-AV4-PIVOT-P1",
            "authorized":True,
            "name":"Existing-Snapshot Pressure/Darcy/Pollock/TOF Staleness Pilot",
            "execution":True,
            "must_use_A6E_integrated_state":True,
            "must_use_frozen_SG2_to_SG6_physics":True,
            "must_not_run_five_stage_assignment":True,
            "must_not_read_R3R6R1_recovery":True,
            "must_publish_required_P1_plots":True,
            "must_publish_required_P1_3D_visuals":True,
            "must_use_matched_view_for_cross_policy_3D_comparisons":True,
            "P2_dense_5day_snapshot_generation_authorized":False,
        }

        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "AV4_PIVOT_P1_authorized":True,
            "current_R3R6R1_execution_invalidated":False,
            "current_R3R6R1_execution_superseded":False,
            "periodic_cadence_selected_now":False,
            "candidate_cadences_days":[50.0,5.0],
            "O3R7_authorized":False,
            "F5_dataset_generation_authorized":False,
            "training_authorized":False,
        }

        files={
            "PAD_Stream_POSTV16_AV4_PIVOT_P0_Summary.json":json_bytes({
                "milestone":MILESTONE,
                "status":STATUS_PASS,
                "design_freeze_only":True,
                "scientific_execution":False,
                "parallel_to_R3R6R1":True,
                "A1_numeric_cadence_was_deferred":True,
                "A2E_single_refresh_operator_validated":True,
                "P1_authorized":True,
            }),
            "POSTV16_AV4_PIVOT_P0_Purpose_and_Branch_Relationship.json":json_bytes(purpose),
            "POSTV16_AV4_PIVOT_P0_Diagnostic_Architecture.json":json_bytes(architecture),
            "POSTV16_AV4_PIVOT_P0_Observable_Metric_Contract.json":json_bytes(metrics),
            "POSTV16_AV4_PIVOT_P0_Scientific_Guardrails.json":json_bytes(guardrails),
            "POSTV16_AV4_PIVOT_P0_Advisor_Plot_Contract.json":json_bytes(plots),
            "POSTV16_AV4_PIVOT_P0_P1_Handoff_Contract.json":json_bytes(handoff),
            "POSTV16_AV4_PIVOT_P0_Decision_Contract.json":json_bytes(decision),
            "POSTV16_AV4_PIVOT_P0_Final_Gate_Matrix.csv":csv_bytes([
                {"gate":k,"status":v["status"],"detail":json.dumps(v["detail"],sort_keys=True)}
                for k,v in gates.items()
            ]),
        }

        manifest_rows=[]
        for name,data in files.items():
            manifest_rows.append({
                "file":name,
                "sha256":hashlib.sha256(data).hexdigest(),
                "bytes":len(data),
            })
        files["POSTV16_AV4_PIVOT_P0_Artifact_Manifest.csv"]=csv_bytes(manifest_rows)

        immutable_publish(out,files)

        print()
        print("="*180)
        print("POSTV16-AV4-PIVOT-P0: PASS")
        print("P1 existing-snapshot staleness pilot authorized.")
        print("R3-R6-R1 exact certification branch remains unchanged and may continue running.")
        print("No cadence selected yet; 50-day and 5-day remain comparison candidates.")
        print("="*180)
        return 0

    except Exception as exc:
        block.mkdir(parents=True,exist_ok=True)
        p=block/"POSTV16_AV4_PIVOT_P0_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":"AV4PIVOTP0_TECHNICAL_OR_AUTHORITY_BLOCK",
                "exception":repr(exc),
                "R3R6R1_execution_invalidated":False,
                "R3R6R1_recovery_tree_touched":False,
            },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(MILESTONE+": BLOCKED")
        print("Exception:",repr(exc))
        return 2

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path("."))
    p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test",action="store_true")
    return p.parse_args()

if __name__=="__main__":
    args=parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))

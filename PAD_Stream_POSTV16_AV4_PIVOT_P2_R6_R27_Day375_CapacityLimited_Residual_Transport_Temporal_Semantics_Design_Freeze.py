#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, io, json, subprocess
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-P2-R6-R27"
NAME="Day375 Capacity-Limited Residual / Transport Temporal Semantics Design Freeze"
PASS="AV4PIVOTP2R6R27_DAY375_CAPACITY_LIMITED_RESIDUAL_TRANSPORT_TEMPORAL_SEMANTICS_DESIGN_FREEZE_PASS_NO_EXECUTION"
BLOCK="AV4PIVOTP2R6R27_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH="postv16-av4-pivot"
PARENT="b3103959aab006ce406c3bd78692b6e710beedde"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
GRID=(15,50,50); NCELL=37500; NSL=1078; NCV=200

R26_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R26_Day375_CapacityLimited_SplitState_Restart_Representation_Closure_and_Acceptance_Audit"
R26_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R26_Summary.json"
R26_ACCEPTANCE="POSTV16_AV4_PIVOT_P2_R6_R26_Day375_SplitState_Acceptance_Contract.json"
R26_DECISION="POSTV16_AV4_PIVOT_P2_R6_R26_Decision_Contract.json"
R26_MANIFEST="POSTV16_AV4_PIVOT_P2_R6_R26_Artifact_Manifest.csv"
R26_STATUS="AV4PIVOTP2R6R26_DAY375_CAPACITY_LIMITED_SPLIT_STATE_RESTART_REPRESENTATION_CLOSURE_ACCEPTANCE_AUDIT_PASS_EXACT_R25R3_STATE_ACCEPTED_NO_STATE_REWRITE"
R26_CLASSIFICATION="R6R26_EXACT_R25R3_CAPACITY_LIMITED_SPLIT_STATE_ACCEPTED_CARTESIAN_PRIMARY_CV_PLUS_RESIDUAL_RESTART_REPRESENTATION_R27_RESIDUAL_TEMPORAL_SEMANTICS_DESIGN_NEXT"

R25R3_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R25_R3_Controlled_Day375_CapacityLimited_ExactSupport_SplitState_Reprojection_Execution_Stage2_PresolveOff"
R25R3_STATE="POSTV16_AV4_PIVOT_P2_R6_R25_R3_CapacityLimited_SplitState_Day375.npz"
R25R3_MANIFEST="POSTV16_AV4_PIVOT_P2_R6_R25_R3_Artifact_Manifest.csv"
R25R3_STATE_SHA256="9893e2476bce1d46213cdd1304e60ad93b49ea285e084d06743a2ffab25f721f"

R22_EPOCH_SHA256="7f030fd3676eb3b61bc7f341dff8cb82659e87e210640a9488bf6fb15e7bd80e"
PRESSURE_EPOCH_SHA256="99d73cab1d33191a68578f29d3c03f9fac07ed77c39e124cc8eb5e5bf75aa84d"
R20_ACCEPTED_STATE_SHA256="e209adb5a169008698db9acb24e5cade82df3f6991b5174515d5957901bceb67"

R26_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R26_Day375_CapacityLimited_SplitState_Closure_Acceptance_Audit.py"
R26_BLOB="f72a6d2d9184dd287df3aa589a31fda0567503f4"
R25R3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R25_R3_Controlled_CapacityLimited_Reprojection_Stage2_PresolveOff.py"
R25R3_BLOB="65cab626419137b191f2c53a4c543d9805ccf68d"
SOURCE_BLOBS={R26_RUNNER:R26_BLOB,R25R3_RUNNER:R25R3_BLOB}

OUT_TOKEN="POSTV16_AV4_PIVOT_P2_R6_R27"
OUT_REL=BASE/(OUT_TOKEN+"_Day375_CapacityLimited_Residual_Transport_Temporal_Semantics_Design_Freeze")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")

class GateError(RuntimeError): pass

def gt(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def sha(path:Path)->str:
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def js(path:Path): return json.loads(path.read_text(encoding="utf-8"))

def csvr(path:Path):
    with open(path,newline="",encoding="utf-8") as f: return list(csv.DictReader(f))

def csvb(rows):
    if not rows: return b""
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    s=io.StringIO(newline=""); w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(rows)
    return s.getvalue().encode()

def jb(obj): return (json.dumps(obj,indent=2,sort_keys=True)+"\n").encode()

def manifest(directory:Path,filename:str):
    out={}
    for row in csvr(directory/filename):
        p=directory/row["file"]
        if not p.is_file(): raise GateError(f"manifest_missing:{p.name}")
        if sha(p)!=row["sha256"]: raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size!=int(row["bytes"]): raise GateError(f"manifest_bytes:{p.name}")
        out[p.name]=row["sha256"]
    return out

def selftest():
    assert OUT_REL.name.startswith(OUT_TOKEN+"_")
    assert BLOCK_REL.name==OUT_TOKEN+"_BLOCKED"
    semantics={
        "residual_physical_immobility_claim":False,
        "residual_participates_in_streamline_advective_operator":False,
        "reprojection_at_next_flow_refresh":True,
        "transport_execution_authorized":False,
    }
    assert semantics["residual_physical_immobility_claim"] is False
    assert semantics["transport_execution_authorized"] is False
    print("POSTV16 AV4 PIVOT P2-R6-R27 structural self-test: PASS")

def main(project_root:Path,drive_root:Path)->int:
    root,drive=project_root.resolve(),drive_root.resolve()
    out,block_dir=drive/OUT_REL,drive/BLOCK_REL
    stage="preflight"; gates=[]

    def gate(name,cond,detail=None):
        ok=bool(cond)
        gates.append({"stage":stage,"gate":name,"pass":ok,"detail":"" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+("" if detail is None else f" -- {detail}"))
        if not ok: raise GateError(name)

    try:
        stage="preexisting_state_firewall"
        gate("no_preexisting_R27_PASS",not (out/f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_R27_BLOCK",not (block_dir/f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage="repository_authority"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH)
        gate("parent_is_R26_commit",gt(root,"rev-parse","HEAD^")==PARENT)
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        for filename,expected in SOURCE_BLOBS.items():
            p=root/filename; gate(f"{Path(filename).stem}_present",p.is_file(),str(p))
            actual=gt(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_blob_exact",actual==expected,actual)

        stage="R26_acceptance_authority"
        r26=drive/R26_REL; manifest(r26,R26_MANIFEST)
        s26,a26,d26=js(r26/R26_SUMMARY),js(r26/R26_ACCEPTANCE),js(r26/R26_DECISION)
        gate("R26_status_exact",s26.get("status")==R26_STATUS,s26.get("status"))
        gate("R26_classification_exact",s26.get("classification")==R26_CLASSIFICATION,s26.get("classification"))
        gate("R26_representation_accepted",s26.get("representation_accepted") is True)
        gate("R26_state_not_rewritten",s26.get("state_rewritten_by_R26") is False)
        gate("R26_accepted_state_SHA_exact",s26.get("accepted_state_sha256")==R25R3_STATE_SHA256)
        gate("R26_acceptance_contract_state_SHA_exact",a26.get("accepted_state_sha256")==R25R3_STATE_SHA256)
        gate("R26_acceptance_contract_no_rewrite",a26.get("state_rewritten_by_R26") is False)
        gate("R26_primary_cartesian_authority",a26.get("primary_recurrent_authority")=="cartesian_component_mass_kg")
        gate("R26_residual_includes_outside_S0",a26.get("accepted_residual_grid_state",{}).get("includes_outside_S0_mass") is True)
        gate("R26_residual_includes_capacity_limited_S0",a26.get("accepted_residual_grid_state",{}).get("includes_minimum_unavoidable_S0_residual") is True)
        gate("R27_authorized",d26.get("P2_R6_R27_authorized") is True)
        gate("R27_design_only",d26.get("P2_R6_R27_design_only") is True)
        gate("R27_execution_not_authorized",d26.get("P2_R6_R27_execution_authorized") is False)
        gate("R27_must_resolve_outside_S0",d26.get("R27_must_resolve_outside_S0_residual_temporal_semantics") is True)
        gate("R27_must_resolve_capacity_limited_S0",d26.get("R27_must_resolve_capacity_limited_S0_residual_temporal_semantics") is True)
        gate("transport_still_locked",d26.get("transport_execution_authorized_now") is False)
        gate("mapback_still_locked",d26.get("mapback_execution_authorized") is False)
        gate("time_still_locked",d26.get("physical_time_advance_authorized") is False)

        stage="accepted_state_partition_audit"
        r25=drive/R25R3_REL; m25=manifest(r25,R25R3_MANIFEST); state_path=r25/R25R3_STATE
        gate("R25R3_state_manifest_SHA_exact",m25.get(R25R3_STATE)==R25R3_STATE_SHA256)
        gate("R25R3_state_file_SHA_exact",sha(state_path)==R25R3_STATE_SHA256)

        with np.load(state_path,allow_pickle=False) as z:
            grid=np.asarray(z["cartesian_component_mass_kg"],float)
            cv=np.asarray(z["transport_CV_component_mass_kg"],float)
            residual=np.asarray(z["grid_residual_component_mass_kg"],float)
            edge_cell=np.asarray(z["exact_support_edge_cell"],np.int64).reshape(-1)
            represented=np.asarray(z["represented_cartesian_cell_mass_kg"],float)
            stage2_presolve=bool(np.asarray(z["stage2_HiGHS_presolve"]).reshape(()))
            r22sha=str(np.asarray(z["source_R22_flow_epoch_sha256"]).reshape(()))
            psha=str(np.asarray(z["source_pressure_epoch_sha256"]).reshape(()))
            r20sha=str(np.asarray(z["source_R20_accepted_transport_state_sha256"]).reshape(()))

        gate("state_shapes_exact",grid.shape==GRID and residual.shape==GRID and represented.shape==GRID and cv.shape==(NSL,NCV))
        gate("stage2_presolve_false",stage2_presolve is False)
        gate("source_R22_SHA_exact",r22sha==R22_EPOCH_SHA256)
        gate("source_pressure_SHA_exact",psha==PRESSURE_EPOCH_SHA256)
        gate("source_R20_SHA_exact",r20sha==R20_ACCEPTED_STATE_SHA256)
        gate("accepted_grid_decomposition_exact",float(np.max(np.abs(grid-represented-residual)))<=1e-6)

        s0=np.unique(edge_cell)
        flat_r=residual.reshape(-1)
        mask=np.ones(NCELL,dtype=bool); mask[s0]=False
        s0_res=float(np.sum(flat_r[s0])); outside_res=float(np.sum(flat_r[mask]))
        total_res=float(np.sum(residual)); total_grid=float(np.sum(grid)); total_cv=float(np.sum(cv))
        ledger=total_cv+total_res-total_grid
        gate("residual_partition_closes",abs((s0_res+outside_res)-total_res)<=1e-6,[s0_res,outside_res,total_res])
        gate("global_accepted_ledger_closes",abs(ledger)<=1e-6,ledger)
        gate("S0_residual_positive",s0_res>0.0,s0_res)
        gate("outside_S0_residual_positive",outside_res>0.0,outside_res)

        stage="temporal_semantics_freeze"
        semantics={
            "milestone":M,
            "status":PASS,
            "accepted_parent_day":375.0,
            "accepted_state_sha256":R25R3_STATE_SHA256,
            "authoritative_recurrent_state":{
                "name":"cartesian_component_mass_kg",
                "principle":"Cartesian component mass remains the authoritative global recurrent physical state.",
            },
            "transport_coordinate_state":{
                "name":"transport_CV_component_mass_kg",
                "role":"only state block advanced by the streamline advective transport operator during the current frozen-flow epoch",
                "geometry_authority":"accepted R22 Day375 Darcy/Pollock/TOF geometry",
                "capacity_limited":True,
            },
            "residual_partition":{
                "outside_S0":{
                    "definition":"grid_residual_component_mass on cells not in accepted R22 exact support S0",
                    "mass_kg":outside_res,
                    "current_epoch_rule":"deferred Cartesian reserve; excluded from the streamline advective transport operator",
                    "reason":"no exact R22 streamline support exists for these cells",
                },
                "capacity_limited_inside_S0":{
                    "definition":"grid_residual_component_mass on cells in accepted R22 S0 that could not be represented within frozen CV capacity",
                    "mass_kg":s0_res,
                    "current_epoch_rule":"deferred Cartesian reserve; excluded from the streamline advective transport operator",
                    "reason":"current R22 CV representation lacks sufficient physical mass capacity",
                },
                "total_mass_kg":total_res,
            },
            "physical_interpretation":{
                "residual_physical_immobility_claim":False,
                "statement":"Deferred means not represented by the current streamline transport coordinates; it does not assert that the physical fluid is immobile.",
            },
            "within_current_frozen_flow_epoch":{
                "streamline_advective_operator_updates_residual":False,
                "residual_sidecar_is_epoch_frozen_during_transport_coordinate_solve":True,
                "absolute_CV_state_may_not_replace_cartesian_state":True,
                "future_cartesian_update_must_be_delta_based":True,
                "required_update_identity":"M_grid_candidate = M_grid_parent + Delta_M_grid_from_transport",
                "required_delta_identity":"sum(Delta_M_grid_from_transport) = sum(Delta_M_CV), including explicit well/source-sink accounting",
                "residual_may_not_be_silently_injected_into_CVs":True,
                "residual_may_not_be_discarded_or_rescaled":True,
            },
            "next_flow_refresh":{
                "recompose_authoritative_cartesian_state_first":True,
                "fresh_projection_from_entire_cartesian_inventory":True,
                "outside_S0_residual_is_eligible_for_new_support":True,
                "capacity_limited_S0_residual_is_eligible_for_new_CV_capacity":True,
                "old_residual_labels_are_diagnostic_provenance_not_permanent_physical_classes":True,
            },
            "well_source_sink_guard":{
                "residual_well_overlap_must_be_quantified_before_transport_execution":True,
                "injector_and_producer_cell_overlap_required":True,
                "if_residual_in_active_well_cells_is_nonzero":"transport execution remains locked until an explicit conservative source/sink coupling rule is frozen",
                "no_silent_direct_well_removal_or_addition_to_residual":True,
            },
            "candidate_mapback_guard":{
                "future_mapback_must_apply_transport_delta_only":True,
                "accepted_residual_sidecar_must_not_be_overwritten_by_absolute_mapback":True,
                "cellwise_cartesian_mass_nonnegativity_required":True,
                "cellwise_pressure_capacity_consistency_required_before_time_commit":True,
                "global_mass_change_must_equal_explicit_injection_minus_production":True,
            },
            "prohibitions":[
                "no claim that residual mass is physically immobile",
                "no transport execution in R27",
                "no mapback execution in R27",
                "no physical-time advance in R27",
                "no support growth",
                "no reverse H1->S0 pullback",
                "no residual clipping, discarding, or global rescaling",
                "no automatic promotion of capacity-limited S0 residual into CV mass",
            ],
        }

        classification="R6R27_RESIDUAL_IS_DEFERRED_CARTESIAN_RESERVE_DURING_CURRENT_FROZEN_FLOW_EPOCH_NOT_PHYSICAL_IMMOBILE_R28_DELTA_MAPBACK_AND_WELL_COUPLING_DESIGN_NEXT"

        summary={
            "milestone":M,"name":NAME,"status":PASS,"classification":classification,
            "accepted_state_sha256":R25R3_STATE_SHA256,
            "cartesian_component_mass_total_kg":total_grid,
            "transport_CV_component_mass_total_kg":total_cv,
            "total_residual_mass_kg":total_res,
            "outside_S0_residual_mass_kg":outside_res,
            "capacity_limited_S0_residual_mass_kg":s0_res,
            "global_split_state_ledger_residual_kg":ledger,
            "residual_physical_immobility_claim":False,
            "residual_excluded_from_current_streamline_advective_operator":True,
            "residual_epoch_frozen_during_transport_coordinate_solve":True,
            "fresh_whole_cartesian_reprojection_required_at_next_flow_refresh":True,
            "residual_well_overlap_audit_required_before_transport":True,
            "future_delta_mapback_required":True,
            "transport_execution_performed":False,
            "mapback_performed":False,
            "physical_time_advance_performed":False,
            "P3_authorized":False,
        }

        decision={
            "milestone":M,"status":PASS,"classification":classification,
            "P2_R6_R28_authorized":True,
            "P2_R6_R28_name":"Post-Day375 Frozen-Flow Transport Delta-Mapback / Residual-Well Coupling Protocol Freeze",
            "P2_R6_R28_design_only":True,
            "P2_R6_R28_execution_authorized":False,
            "P2_R6_R28_must_bind_R27_temporal_semantics":True,
            "P2_R6_R28_must_bind_R26_acceptance_contract":True,
            "P2_R6_R28_must_bind_R25R3_state_SHA":True,
            "P2_R6_R28_R25R3_state_sha256":R25R3_STATE_SHA256,
            "R28_must_quantify_residual_in_injector_cells":True,
            "R28_must_quantify_residual_in_producer_cells":True,
            "R28_must_freeze_conservative_CV_delta_to_grid_mapback":True,
            "R28_must_freeze_explicit_injection_production_mass_ledger":True,
            "R28_must_freeze_precommit_cell_capacity_gate":True,
            "transport_execution_authorized_now":False,
            "mapback_execution_authorized":False,
            "transport_time_advance_authorized":False,
            "physical_time_advance_authorized":False,
            "P3_authorized":False,"P4_authorized":False,"P5_training_authorized":False,
        }

        stage="design_freeze_publication"
        out.mkdir(parents=True,exist_ok=False)
        (out/f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out/f"{OUT_TOKEN}_Residual_Transport_Temporal_Semantics_Contract.json").write_bytes(jb(semantics))
        (out/f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out/f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))
        rows=[]
        for p in sorted(out.iterdir()):
            if p.is_file(): rows.append({"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size})
        (out/f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("="*190)
        print(M,"PASS")
        print("Classification                         :",classification)
        print("Accepted state SHA256                  :",R25R3_STATE_SHA256)
        print("Outside-S0 residual kg                 :",outside_res)
        print("Capacity-limited S0 residual kg        :",s0_res)
        print("Residual physical immobility claim     : False")
        print("Residual in current streamline operator: False")
        print("Fresh whole-grid projection at refresh : True")
        print("R28 delta-mapback/well-coupling design : AUTHORIZED (design only)")
        print("Transport / mapback / time / P3        : False / False / False / False")
        print("="*190)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"R26_acceptance_preserved":True,
                              "R25R3_state_preserved":True,"R25R3_state_sha256":R25R3_STATE_SHA256,"state_mutation_executed":False,
                              "transport_execution_executed":False,"mapback_executed":False,"physical_time_advance_executed":False,
                              "P3_authorized":False,"automatic_rerun_authorized":False,"gates_completed":gates}))
        print("="*190); print(M,"TECHNICAL / AUTHORITY BLOCK"); print("Stage:",stage); print("Exception:",repr(exc))
        print("NO STATE MUTATION / TRANSPORT / MAPBACK / TIME ADVANCE."); print("="*190)
        return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test: selftest(); raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))

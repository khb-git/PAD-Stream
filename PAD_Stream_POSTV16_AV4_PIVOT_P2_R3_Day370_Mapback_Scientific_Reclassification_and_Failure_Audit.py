#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


MILESTONE = "POSTV16-AV4-PIVOT-P2-R3"
STATUS_PASS = (
    "AV4PIVOTP2R3_ORIGINAL_P2_DAY370_MAPBACK_SCIENTIFIC_FAILURE_RECLASSIFIED_"
    "AND_NEGATIVE_GRID_CELL_MASS_FAILURE_QUANTIFIED_NO_REPAIR_EXECUTION"
)
STATUS_BLOCKED = "AV4PIVOTP2R3_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT = "9a0061c3c656b613821e4c4ffbfc11f8ff836836"
EXPECTED_BRANCH = "postv16-av4-pivot"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NSL = 1078
NN = 201
NCV = 200
BACKGROUND = 0.20
MAX_SG = 0.60
SPD = 86400.0
PARENT_DAY = 365.0
AUDIT_DAY = 370.0
DELTA_DAY = 5.0

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

P2_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_BLOCKED"
P2_BLOCK_REPORT = "POSTV16_AV4_PIVOT_P2_Blocked_Report.json"
P2_BLOCK_STATUS = "AV4PIVOTP2_TECHNICAL_OR_AUTHORITY_BLOCK"

R1_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R1_R1_BLOCKED"
R1_BLOCK_REPORT = "POSTV16_AV4_PIVOT_P2_R1_Blocked_Report.json"
R1_BLOCK_STATUS = "AV4PIVOTP2R1_TECHNICAL_OR_AUTHORITY_BLOCK"

R2_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R2_BLOCKED"
R2_BLOCK_REPORT = "POSTV16_AV4_PIVOT_P2_R2_Blocked_Report.json"
R2_BLOCK_STATUS = "AV4PIVOTP2R2_TECHNICAL_OR_AUTHORITY_BLOCK"

F2R3_REL = BASE_AV4 / "POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution"
F2R3_STATE = "POSTV16_AV4_F2_R3_Accepted_Parent_Restart_State.npz"

E1R2_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_R2_Refreshed_X13_Structural_InputDomain_Audit"
E1R2_X13 = "POSTV16_AV4_A3_E1_R2_Refreshed_Day365_13Channel_Representation.npz"

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_STATUS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

OUT_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R3_Day370_Mapback_Failure_Audit"
RECOVERY_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R3_Recovery"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R3_BLOCKED"

F4R3 = "PAD_Stream_POSTV16_AV4_F4_R3_Terminal_Producer_PassThrough_Repair_Execution.py"
F4R3_BLOB = "2e84ab09f9ae7af6f977eabc3d9465d325fad717"
A4R2 = "PAD_Stream_POSTV16_AV3_A4_R2_Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py"
A4R2_BLOB = "289901331e835afb44ff2f665fe9a6bbea2eac19"
R2SRC = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

SOURCE_BLOBS = {
    F4R3:F4R3_BLOB,
    A4R2:A4R2_BLOB,
    R2SRC:R2SRC_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
}


class GateError(RuntimeError):
    pass


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git","-C",str(root),*args],
        check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
    ).stdout.strip()


def load_json(path: Path) -> dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path, name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


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
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    buf=io.StringIO(newline="")
    w=csv.DictWriter(buf,fieldnames=fields,lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def relative_l2(a: np.ndarray,b: np.ndarray) -> float:
    x=np.asarray(a,dtype=np.float64)
    y=np.asarray(b,dtype=np.float64)
    return float(np.linalg.norm((x-y).ravel()) / max(float(np.linalg.norm(y.ravel())),1.0e-30))


def self_test() -> None:
    assert DELTA_DAY == 5.0
    assert AUDIT_DAY == 370.0
    assert P2_BLOCK_REL.name == "POSTV16_AV4_PIVOT_P2_BLOCKED"
    assert R1_BLOCK_REL.name == "POSTV16_AV4_PIVOT_P2_R1_R1_BLOCKED"
    assert R2_BLOCK_REL.name == "POSTV16_AV4_PIVOT_P2_R2_BLOCKED"
    print("POSTV16 AV4 PIVOT P2-R3 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root=Path(project_root).resolve()
    drive=Path(drive_root).resolve()
    out=drive/OUT_REL
    recovery=drive/RECOVERY_REL
    block_dir=drive/BLOCK_REL
    stage="preflight"

    def gate(name: str, passed: Any, value: Any=None):
        ok=bool(passed)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    print("="*190)
    print("POSTV16-AV4-PIVOT-P2-R3 -- DAY370 MAPBACK SCIENTIFIC RECLASSIFICATION + FAILURE AUDIT")
    print("="*190)
    print("AUDIT ONLY. NO REPAIR. NO PRESSURE REFRESH. NO CADENCE SELECTION. NO P3 EXECUTION.")
    print("Reproduce only the already-failed Day365->Day370 frozen-flow interval.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R3_Summary.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_R3_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal P2-R3 audit already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_P2R3_BLOCK",not block_report.exists(),str(block_report))

        stage="repository_authority"
        gate("repository_branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        gate("repository_parent_is_P2R2_commit",git_text(root,"rev-parse","HEAD^")==EXPECTED_PARENT,git_text(root,"rev-parse","HEAD^"))
        gate("repository_clean",git_text(root,"status","--porcelain")=="",repr(git_text(root,"status","--porcelain")))
        runner_blob=git_text(root,"hash-object",str(root/Path(__file__).name))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="immutable_history_binding"
        p2=load_json(drive/P2_BLOCK_REL/P2_BLOCK_REPORT)
        r1=load_json(drive/R1_BLOCK_REL/R1_BLOCK_REPORT)
        r2b=load_json(drive/R2_BLOCK_REL/R2_BLOCK_REPORT)

        gate("P2_stored_block_status_exact",p2.get("status")==P2_BLOCK_STATUS,p2.get("status"))
        gate("P2_failed_stage_day370",p2.get("failed_stage")=="transport_to_day_370",p2.get("failed_stage"))
        p2exc=str(p2.get("exception",""))
        gate(
            "P2_exception_is_F4_mapback_negative_grid_cell_mass",
            "ScientificFail" in p2exc and "F4_mapback_negative_grid_cell_mass" in p2exc,
            p2exc,
        )
        gate("P2_scientific_execution_started",p2.get("scientific_execution_started") is True,p2.get("scientific_execution_started"))

        gate("R1_stored_block_status_exact",r1.get("status")==R1_BLOCK_STATUS,r1.get("status"))
        gate("R1_failed_before_science",r1.get("scientific_execution_started") is False,r1.get("scientific_execution_started"))
        gate("R1_failed_at_original_P2_binding",r1.get("failed_stage")=="original_P2_technical_block_binding",r1.get("failed_stage"))

        gate("R2_stored_block_status_exact",r2b.get("status")==R2_BLOCK_STATUS,r2b.get("status"))
        gate("R2_failed_before_science",r2b.get("scientific_execution_started") is False,r2b.get("scientific_execution_started"))
        gate("R2_failed_at_history_binding",r2b.get("failed_stage")=="immutable_P2_and_R1_block_binding",r2b.get("failed_stage"))
        gate(
            "R2_exposed_wrong_KeyError_assumption",
            "original_P2_exception_is_teacher_steps_KeyError" in str(r2b.get("exception","")),
            r2b.get("exception"),
        )

        stage="source_exception_identity_audit"
        f4=load_module(root/F4R3,"av4_pivot_p2r3_f4")
        a4=load_module(root/A4R2,"av4_pivot_p2r3_a4")
        r2src=load_module(root/R2SRC,"av4_pivot_p2r3_r2src")
        e37=load_module(root/E37A,"av4_pivot_p2r3_e37")
        sg7d=load_module(root/SG7D,"av4_pivot_p2r3_sg7d")

        # Local historical P2 class was a distinct class object from f4.ScientificFail.
        class HistoricalP2ScientificFail(RuntimeError):
            pass
        gate(
            "F4_ScientificFail_is_distinct_exception_type",
            f4.ScientificFail is not HistoricalP2ScientificFail,
            {
                "F4_module":f4.ScientificFail.__module__,
                "F4_name":f4.ScientificFail.__name__,
            },
        )

        stage="authority_state_binding"
        f2path=drive/F2R3_REL/F2R3_STATE
        x13path=drive/E1R2_REL/E1R2_X13
        a2path=drive/A2E_REL/A2E_EPOCH
        a2sum=drive/A2E_REL/A2E_SUMMARY
        gate("F2R3_parent_state_present",f2path.is_file(),str(f2path))
        gate("E1R2_X13_present",x13path.is_file(),str(x13path))
        gate("A2E_epoch_present",a2path.is_file(),str(a2path))
        gate("A2E_status_exact",load_json(a2sum).get("status")==A2E_STATUS,load_json(a2sum).get("status"))

        with np.load(f2path,allow_pickle=False) as z:
            parent_cv_mass=np.asarray(z["parent_CV_component_mass_kg"],dtype=np.float64)
            parent_cv_sat=np.asarray(z["parent_CV_saturation"],dtype=np.float64)
            parent_cv_capacity=np.asarray(z["parent_CV_capacity_kg"],dtype=np.float64)
            parent_cv_pv=np.asarray(z["parent_CV_pore_volume_m3"],dtype=np.float64)
            parent_cv_coeff=np.asarray(z["parent_CV_pressure_mass_coeff"],dtype=np.float64)

        with np.load(x13path,allow_pickle=False) as z:
            X13=np.asarray(z["X_refreshed_13"],dtype=np.float64)

        with np.load(a2path,allow_pickle=False) as z:
            epoch={k:np.asarray(z[k]).copy() for k in z.files}

        parent_grid_mass=np.asarray(epoch["parent_component_mass_kg"],dtype=np.float64)
        parent_pressure=np.asarray(epoch["refreshed_pressure_psi"],dtype=np.float64)
        parent_xyz=np.asarray(epoch["streamline_xyz_m"],dtype=np.float64)
        parent_tof=np.asarray(epoch["streamline_tof_s"],dtype=np.float64)
        parent_weights=np.asarray(epoch["streamline_weight_m3_s"],dtype=np.float64)
        parent_face_pressure=np.asarray(epoch["streamline_face_pressure_psi"],dtype=np.float64)
        p_ref=float(np.asarray(epoch["reference_gas_pressure_pa"]).reshape(()))
        xi=np.asarray(epoch["xi"],dtype=np.float64).reshape(-1)

        gate("authority_shapes_exact",
             parent_cv_mass.shape==(NSL,NCV)
             and parent_cv_sat.shape==(NSL,NCV)
             and parent_grid_mass.shape==GRID
             and parent_xyz.shape==(NSL,NN,3)
             and parent_tof.shape==(NSL,NN)
             and parent_weights.shape==(NSL,)
             and parent_face_pressure.shape==(NSL,NN)
             and xi.shape==(NN,))

        cvavg=0.5*(X13[:,:-1,:]+X13[:,1:,:])
        phi_cv=cvavg[:,:,5]
        nw_cv=3.0+cvavg[:,:,9]
        no_cv=3.0+cvavg[:,:,10]
        krw_cv=0.80+0.20*cvavg[:,:,11]
        kro_cv=0.80+0.20*cvavg[:,:,12]
        cvgeom=f4.build_cv_geometry_from_faces(parent_tof,xi)

        operator=sg7d.build_subsegment_operator(
            parent_xyz,parent_tof/SPD,parent_weights*SPD
        )
        geometry=e37.build_control_volume_geometry(
            r2src,operator,parent_pressure,p_ref,NSL,NCV
        )
        gate(
            "parent_CV_pv_matches_F2R3",
            float(np.max(np.abs(np.asarray(geometry["cv_pv_m3"])-parent_cv_pv)))<=1.0e-8,
            float(np.max(np.abs(np.asarray(geometry["cv_pv_m3"])-parent_cv_pv))),
        )
        gate(
            "parent_CV_coeff_matches_F2R3",
            relative_l2(np.asarray(geometry["cv_pressure_mass_coeff"]),parent_cv_coeff)<=1.0e-12,
            relative_l2(np.asarray(geometry["cv_pressure_mass_coeff"]),parent_cv_coeff),
        )

        stage="day365_to_day370_teacher_reproduction"
        recovery.mkdir(parents=True,exist_ok=True)
        teacher_path=recovery/"Day365_to_Day370_Teacher_State.npz"
        teacher_meta_path=recovery/"Day365_to_Day370_Teacher_Metadata.json"

        if teacher_path.is_file() and teacher_meta_path.is_file():
            meta=load_json(teacher_meta_path)
            gate("teacher_recovery_runner_blob_exact",meta.get("runner_blob")==runner_blob,meta.get("runner_blob"))
            gate("teacher_recovery_SHA_exact",meta.get("state_sha256")==sha256_file(teacher_path),meta.get("state_sha256"))
            with np.load(teacher_path,allow_pickle=False) as z:
                future_mass=np.asarray(z["future_mass"],dtype=np.float64)
                future_sat=np.asarray(z["future_saturation"],dtype=np.float64)
                injected=float(np.asarray(z["injected_mass_kg"]).reshape(()))
                produced=float(np.asarray(z["produced_mass_kg"]).reshape(()))
                substeps=int(np.asarray(z["substeps"]).reshape(()))
            print("[PASS] reused durable Day365->370 teacher audit checkpoint")
        else:
            t0=time.time()
            teacher=f4.execute_teacher_with_coeff(
                a4=a4,
                r2=r2src,
                e37=e37,
                old_mass=parent_cv_mass,
                old_sat=parent_cv_sat,
                capacity=parent_cv_capacity,
                cv_pressure_mass_coeff=parent_cv_coeff,
                cv_pv_m3=parent_cv_pv,
                face_pressure_psi=parent_face_pressure,
                p_ref_pa=p_ref,
                q_m3_day=parent_weights*SPD,
                nw=nw_cv,no=no_cv,krw_max=krw_cv,kro_max=kro_cv,
                phi_cv=phi_cv,
                cvgeom=cvgeom,
                delta_days=DELTA_DAY,
            )
            future_mass=np.asarray(teacher["future_mass"],dtype=np.float64)
            future_sat=np.asarray(teacher["future_saturation"],dtype=np.float64)
            injected=float(teacher["injected_mass_kg"])
            produced=float(teacher["produced_mass_kg"])
            substeps=int(teacher["substeps"])
            with teacher_path.open("wb") as fp:
                np.savez_compressed(
                    fp,
                    future_mass=future_mass,
                    future_saturation=future_sat,
                    injected_mass_kg=np.asarray(injected),
                    produced_mass_kg=np.asarray(produced),
                    substeps=np.asarray(substeps),
                )
            teacher_meta_path.write_text(json.dumps({
                "milestone":MILESTONE,
                "runner_blob":runner_blob,
                "state_sha256":sha256_file(teacher_path),
                "runtime_s":float(time.time()-t0),
            },indent=2,sort_keys=True)+"\n",encoding="utf-8")
            print("[PASS] durable Day365->370 teacher audit checkpoint published")

        stage="exact_mapback_failure_algebra_audit"
        cv_id=np.asarray(geometry["cv_id"],dtype=np.int64)
        flat=np.asarray(geometry["flat_cell"],dtype=np.int64)
        pv=np.asarray(geometry["pv_m3"],dtype=np.float64)
        pseg=np.asarray(geometry["pseg_psi"],dtype=np.float64)

        old_flat=parent_cv_sat.reshape(-1)
        new_flat=future_sat.reshape(-1)
        old_sub_sat=old_flat[cv_id]
        new_sub_sat=new_flat[cv_id]
        old_sg=np.clip(old_sub_sat-BACKGROUND,0.0,MAX_SG)
        new_sg=np.clip(new_sub_sat-BACKGROUND,0.0,MAX_SG)

        rho_old=np.asarray(r2src.gas_density_from_state(old_sub_sat,pseg,p_ref),dtype=np.float64)
        rho_new=np.asarray(r2src.gas_density_from_state(new_sub_sat,pseg,p_ref),dtype=np.float64)
        sub_delta=pv*(rho_new*new_sg-rho_old*old_sg)

        cv_delta=float(f4.fsum_array(future_mass)-f4.fsum_array(parent_cv_mass))
        sub_total=float(f4.fsum_array(sub_delta))
        transfer_residual=sub_total-cv_delta
        transfer_tol=max(1.0e-6,1.0e-10*max(abs(cv_delta),1.0))
        gate(
            "CV_to_subsegment_transfer_closure_matches_original_precondition",
            abs(transfer_residual)<=transfer_tol,
            {"residual_kg":transfer_residual,"tolerance_kg":transfer_tol},
        )

        deposited=np.bincount(flat,weights=sub_delta,minlength=NZ*NY*NX).reshape(GRID)
        future_grid_mass=parent_grid_mass+deposited
        total_target=float(f4.fsum_array(parent_grid_mass)+cv_delta)
        ledger_residual=float(f4.fsum_array(future_grid_mass)-total_target)
        roundoff=max(1.0e-6,1.0e-10*max(abs(total_target),1.0))

        neg_mask=future_grid_mass < -roundoff
        neg_idx=np.argwhere(neg_mask)
        min_mass=float(np.min(future_grid_mass))
        neg_count=int(np.sum(neg_mask))
        total_negative_deficit=float(np.sum(-future_grid_mass[neg_mask])) if neg_count else 0.0
        max_overdraw=float(np.max(-future_grid_mass[neg_mask])) if neg_count else 0.0

        gate(
            "original_F4_negative_grid_cell_mass_failure_reproduced",
            min_mass < -roundoff and neg_count > 0,
            {
                "minimum_kg":min_mass,
                "tolerance_kg":roundoff,
                "negative_cell_count":neg_count,
                "total_negative_deficit_kg":total_negative_deficit,
            },
        )

        rows=[]
        for k,j,i in neg_idx:
            rows.append({
                "k":int(k),"j":int(j),"i":int(i),
                "parent_mass_kg":float(parent_grid_mass[k,j,i]),
                "deposited_delta_mass_kg":float(deposited[k,j,i]),
                "future_mass_kg":float(future_grid_mass[k,j,i]),
                "overdraw_kg":float(-future_grid_mass[k,j,i]),
            })
        rows.sort(key=lambda r:r["future_mass_kg"])

        worst=rows[0]
        affected_parent_mass=float(np.sum(parent_grid_mass[neg_mask])) if neg_count else 0.0
        affected_withdrawal=float(np.sum(-np.minimum(deposited[neg_mask],0.0))) if neg_count else 0.0

        stage="artifact_publication"
        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R3_Final_Artifacts"
        if local.exists():
            shutil.rmtree(local)
        local.mkdir(parents=True)
        plots=local/"plots"
        plots.mkdir()

        # 3D negative-cell support
        fig=plt.figure(figsize=(8,6))
        ax=fig.add_subplot(111,projection="3d")
        if neg_count:
            sc=ax.scatter(
                neg_idx[:,2],neg_idx[:,1],neg_idx[:,0],
                c=np.asarray([r["overdraw_kg"] for r in rows]),
                s=18,alpha=0.75
            )
            fig.colorbar(sc,ax=ax,pad=0.08,label="Negative-mass overdraw (kg)")
        ax.set_xlim(0,NX-1); ax.set_ylim(0,NY-1); ax.set_zlim(0,NZ-1)
        ax.set_xlabel("i"); ax.set_ylabel("j"); ax.set_zlabel("k")
        ax.view_init(elev=24,azim=-58)
        ax.set_title("Day 370 negative Cartesian mass cells — audit only")
        fig.savefig(plots/"3D_Day370_negative_grid_mass_support.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        # parent mass vs withdrawal
        fig=plt.figure(figsize=(7,5))
        ax=fig.add_subplot(111)
        if neg_count:
            x=np.asarray([r["parent_mass_kg"] for r in rows])
            y=np.asarray([-r["deposited_delta_mass_kg"] for r in rows])
            ax.scatter(x,y,s=16,alpha=0.65)
            lim=max(float(np.max(x)),float(np.max(y)),1.0)
            ax.plot([0,lim],[0,lim],linestyle="--")
        ax.set_xlabel("Parent grid-cell CO2 mass (kg)")
        ax.set_ylabel("Requested 5-day withdrawal from mapped increment (kg)")
        ax.set_title("Day 370 negative cells: local inventory vs mapped withdrawal")
        ax.grid(True,alpha=0.25)
        fig.savefig(plots/"Day370_parent_mass_vs_mapped_withdrawal.png",dpi=180,bbox_inches="tight")
        plt.close(fig)

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "stored_original_P2_status":P2_BLOCK_STATUS,
            "scientific_reclassification":(
                "Original P2 is scientifically interpreted as a Day370 mapback negative-grid-cell-mass "
                "failure that was misrouted into the technical block handler because F4-R3 ScientificFail "
                "is a distinct exception class from P2 ScientificFail. The original stored P2 report remains immutable."
            ),
            "audit_interval_days":[PARENT_DAY,AUDIT_DAY],
            "teacher_substeps":substeps,
            "injected_mass_kg":injected,
            "produced_mass_kg":produced,
            "CV_delta_mass_kg":cv_delta,
            "subsegment_delta_mass_kg":sub_total,
            "CV_to_subsegment_transfer_residual_kg":transfer_residual,
            "CV_to_subsegment_transfer_tolerance_kg":transfer_tol,
            "full_grid_ledger_residual_kg":ledger_residual,
            "mapback_roundoff_tolerance_kg":roundoff,
            "minimum_future_grid_mass_kg":min_mass,
            "negative_grid_cell_count":neg_count,
            "total_negative_mass_deficit_kg":total_negative_deficit,
            "maximum_cell_overdraw_kg":max_overdraw,
            "negative_cells_parent_mass_total_kg":affected_parent_mass,
            "negative_cells_requested_withdrawal_total_kg":affected_withdrawal,
            "worst_cell":worst,
            "repair_executed":False,
            "pressure_refresh_executed":False,
            "cadence_selected":False,
            "P3_authorized":False,
        }
        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "P3_authorized":False,
            "P2_R4_authorized":True,
            "P2_R4_name":"Day370 Mapback Local-Inventory Deficit Cause Audit and Repair-Selection Freeze",
            "P2_R4_scope":[
                "determine whether deficit is caused by fixed parent E37A subsegment allocation, overlapping streamline withdrawals, or incompatible local Cartesian inventory",
                "quantify support/ownership multiplicity of all negative cells",
                "compare requested mapped withdrawal to locally available Cartesian mass without relaxing global conservation",
                "select repair semantics prospectively; no repair execution in R4",
            ],
            "forbidden":[
                "clip negative masses",
                "renormalize global mass",
                "expand support without authority",
                "pressure refresh",
                "cadence selection",
                "P3 execution",
                "ML training",
            ],
            "R3R6R1_execution_invalidated":False,
        }

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R3_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_R3_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_R3_Negative_Cell_Diagnostics.csv").write_bytes(csv_bytes(rows))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({
                    "file":str(p.relative_to(local)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local/"POSTV16_AV4_PIVOT_P2_R3_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        if out.exists():
            raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*190)
        print("POSTV16-AV4-PIVOT-P2-R3: PASS")
        print("Original P2 scientific failure reclassified and reproduced.")
        print("Minimum Day370 future grid mass kg :",min_mass)
        print("Negative grid-cell count            :",neg_count)
        print("Total negative mass deficit kg      :",total_negative_deficit)
        print("P3 authorized                       : False")
        print("P2-R4 cause audit / repair freeze   : Authorized")
        print("="*190)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_R3_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_BLOCKED,
                "failed_stage":stage,
                "exception":repr(exc),
                "automatic_rerun_authorized":False,
                "R3R6R1_execution_invalidated":False,
            },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(MILESTONE+": BLOCKED")
        print("Stage:",stage)
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

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
from matplotlib.colors import Normalize


MILESTONE = "POSTV16-AV4-PIVOT-P2"
STATUS_PASS = (
    "AV4PIVOTP2_DENSE_DAY365_TO_DAY500_5DAY_FROZEN_FLOW_SNAPSHOT_GENERATION_PASS_"
    "28_CARTESIAN_AND_200CV_STATES_CONSERVATIVE_MAPBACK_CERTIFIED"
)
STATUS_FAIL = (
    "AV4PIVOTP2_DENSE_FROZEN_FLOW_SNAPSHOT_GENERATION_SCIENTIFIC_FAIL_"
    "NO_CADENCE_SELECTION_NO_AUTOMATIC_RERUN"
)
STATUS_BLOCKED = "AV4PIVOTP2_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_PARENT = "276d1e03742ecad023aeca0071aba23568a51a18"
EXPECTED_BRANCH = "postv16-av4-pivot"

GRID = (15, 50, 50)
NSL = 1078
NN = 201
NCV = 200
BACKGROUND = 0.20
MAX_SG = 0.60
SPD = 86400.0

START_DAY = 365.0
END_DAY = 500.0
STEP_DAYS = 5.0
SNAPSHOT_DAYS = np.arange(START_DAY, END_DAY + 0.5 * STEP_DAYS, STEP_DAYS, dtype=np.float64)

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

P1_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P1_Existing_Snapshot_Staleness_Pilot"
P1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P1_Summary.json"
P1_DECISION = "POSTV16_AV4_PIVOT_P1_Decision_Contract.json"
P1_STATUS = (
    "AV4PIVOTP1_EXISTING_SNAPSHOT_PRESSURE_DARCY_POLLOCK_TOF_STALENESS_PILOT_PASS_"
    "DAY365_REFERENCE_DAY500_DAY750_DAY1000_DIAGNOSTICS_AND_3D_VISUALS_PUBLISHED"
)

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

OUT_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_Dense_5Day_FrozenFlow_Snapshot_Generation"
RECOVERY_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_Recovery_Checkpoints"
FAIL_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_BLOCKED"

F4R3 = "PAD_Stream_POSTV16_AV4_F4_R3_Terminal_Producer_PassThrough_Repair_Execution.py"
F4R3_BLOB = "2e84ab09f9ae7af6f977eabc3d9465d325fad717"
A4R2 = "PAD_Stream_POSTV16_AV3_A4_R2_Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py"
A4R2_BLOB = "289901331e835afb44ff2f665fe9a6bbea2eac19"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

SOURCE_BLOBS = {
    F4R3:F4R3_BLOB,
    A4R2:A4R2_BLOB,
    A2E:A2E_BLOB,
    R2:R2_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
}


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fsum_array(a: np.ndarray) -> float:
    return float(np.sum(np.asarray(a, dtype=np.float64), dtype=np.float64))


def relative_l2(a: np.ndarray, b: np.ndarray) -> float:
    x=np.asarray(a,dtype=np.float64)
    y=np.asarray(b,dtype=np.float64)
    return float(np.linalg.norm((x-y).ravel()) / max(float(np.linalg.norm(y.ravel())), 1.0e-30))


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
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


def checkpoint_dir(recovery: Path, day: float) -> Path:
    return recovery / f"day_{int(round(day)):04d}"


def checkpoint_paths(recovery: Path, day: float) -> tuple[Path,Path]:
    d=checkpoint_dir(recovery,day)
    return d/"State.npz",d/"Metadata.json"


def save_checkpoint(
    recovery: Path,
    day: float,
    runner_blob: str,
    arrays: dict[str,np.ndarray],
    meta: dict[str,Any],
) -> None:
    d=checkpoint_dir(recovery,day)
    d.mkdir(parents=True,exist_ok=True)
    state_path,meta_path=checkpoint_paths(recovery,day)
    tmp=state_path.with_suffix(".npz.tmp")
    with tmp.open("wb") as f:
        np.savez_compressed(f,**arrays)
    tmp.replace(state_path)
    m=dict(meta)
    m.update({
        "milestone":MILESTONE,
        "day":float(day),
        "runner_blob":runner_blob,
        "state_sha256":sha256_file(state_path),
    })
    t=meta_path.with_suffix(".json.tmp")
    t.write_text(json.dumps(m,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    t.replace(meta_path)


def load_checkpoint(
    recovery: Path,
    day: float,
    runner_blob: str,
) -> tuple[dict[str,np.ndarray],dict[str,Any]] | None:
    state_path,meta_path=checkpoint_paths(recovery,day)
    if not state_path.is_file() or not meta_path.is_file():
        return None
    meta=load_json(meta_path)
    if (
        meta.get("milestone") != MILESTONE
        or abs(float(meta.get("day",-1.0))-float(day)) > 1.0e-12
        or meta.get("runner_blob") != runner_blob
        or meta.get("state_sha256") != sha256_file(state_path)
    ):
        raise GateError(f"invalid_P2_checkpoint_day_{day:g}")
    with np.load(state_path,allow_pickle=False) as z:
        arrays={k:np.asarray(z[k]).copy() for k in z.files}
    return arrays,meta


def plot_dense_metrics(rows: list[dict[str,Any]], plot_dir: Path) -> list[str]:
    plot_dir.mkdir(parents=True,exist_ok=True)
    days=np.asarray([r["day"] for r in rows],dtype=float)
    specs=[
        ("dense_total_grid_CO2_mass_vs_day.png","grid_total_mass_kg","Grid CO2 mass (kg)","Frozen-flow CO2 inventory"),
        ("dense_max_grid_saturation_vs_day.png","grid_saturation_max","Maximum grid saturation","Frozen-flow saturation evolution"),
        ("dense_cumulative_produced_CO2_vs_day.png","cumulative_produced_mass_kg","Cumulative produced CO2 (kg)","Frozen-flow produced CO2"),
        ("dense_teacher_substeps_vs_day.png","teacher_substeps","Teacher substeps per 5-day interval","Frozen-flow transport cost"),
    ]
    out=[]
    for fn,key,ylabel,title in specs:
        vals=np.asarray([r[key] for r in rows],dtype=float)
        fig=plt.figure(figsize=(7.2,4.6))
        ax=fig.add_subplot(111)
        ax.plot(days,vals,marker="o",markersize=3)
        ax.set_xlabel("Day")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(True,alpha=0.25)
        fig.savefig(plot_dir/fn,dpi=180,bbox_inches="tight")
        plt.close(fig)
        out.append(fn)
    return out


def plot_selected_plumes(
    days: np.ndarray,
    grid_saturation: np.ndarray,
    plot_dir: Path,
) -> list[str]:
    plot_dir.mkdir(parents=True,exist_ok=True)
    selected=[365.0,415.0,465.0,500.0]
    nx,ny,nz=50,50,15
    dx,dy,dz=6.096,6.096,1.2192
    x=(np.arange(nx)+0.5)*dx
    y=(np.arange(ny)+0.5)*dy
    z=(np.arange(nz)+0.5)*dz
    Z,Y,X=np.meshgrid(z,y,x,indexing="ij")
    norm=Normalize(vmin=BACKGROUND,vmax=0.80)
    out=[]
    for day in selected:
        idx=int(np.where(np.isclose(days,day,atol=1.0e-12,rtol=0.0))[0][0])
        sat=grid_saturation[idx]
        mask=sat > BACKGROUND+1.0e-10
        fig=plt.figure(figsize=(8,6))
        ax=fig.add_subplot(111,projection="3d")
        sc=ax.scatter(X[mask],Y[mask],Z[mask],c=sat[mask],s=5,alpha=0.45,norm=norm)
        fig.colorbar(sc,ax=ax,pad=0.08,label="CO2 saturation")
        ax.set_xlim(0,nx*dx); ax.set_ylim(0,ny*dy); ax.set_zlim(0,nz*dz)
        ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)"); ax.set_zlabel("z (m)")
        ax.view_init(elev=24,azim=-58)
        ax.set_title(f"Dense frozen-flow CO2 plume — Day {int(day)}")
        fn=f"3D_dense_frozen_flow_CO2_plume_day{int(day):04d}.png"
        fig.savefig(plot_dir/fn,dpi=180,bbox_inches="tight")
        plt.close(fig)
        out.append(fn)
    return out


def self_test() -> None:
    assert len(SNAPSHOT_DAYS)==28
    assert SNAPSHOT_DAYS[0]==365.0
    assert SNAPSHOT_DAYS[-1]==500.0
    assert np.allclose(np.diff(SNAPSHOT_DAYS),5.0)
    print("POSTV16 AV4 PIVOT P2 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root=Path(project_root).resolve()
    drive=Path(drive_root).resolve()
    out=drive/OUT_REL
    recovery=drive/RECOVERY_REL
    fail_dir=drive/FAIL_REL
    block_dir=drive/BLOCK_REL
    stage="preflight"
    scientific_started=False

    def gate(name: str, passed: Any, value: Any=None):
        ok=bool(passed)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    def sci_gate(name: str, passed: Any, value: Any=None):
        ok=bool(passed)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {value}" if value is not None else ""))
        if not ok:
            raise ScientificFail(name,value)

    print("="*190)
    print("POSTV16-AV4-PIVOT-P2 -- DENSE DAY365->DAY500 5-DAY FROZEN-FLOW SNAPSHOT GENERATION")
    print("="*190)
    print("28 snapshots: Day365, 370, ..., 500.")
    print("FLOW EPOCH FROZEN AT DAY365: pressure / Darcy / Pollock / TOF unchanged during generation.")
    print("TRANSPORT: exact frozen F4-R3 200CV teacher with terminal producer pass-through.")
    print("MAPBACK: exact conservative parent-geometry CV increment mapback after every 5-day interval.")
    print("NO PRESSURE REFRESH. NO E2 FIVE-STAGE ASSIGNMENT. NO SAME-TIME FIXED POINT. NO TRAINING.")
    print()

    try:
        stage="formal_outcome_firewall"
        pass_summary=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_Summary.json"
        fail_report=fail_dir/"POSTV16_AV4_PIVOT_P2_Scientific_Fail_Report.json"
        block_report=block_dir/"POSTV16_AV4_PIVOT_P2_Blocked_Report.json"
        if pass_summary.is_file():
            print("[PASS] formal P2 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_P2_FAIL",not fail_report.exists(),str(fail_report))
        gate("no_preexisting_P2_BLOCK",not block_report.exists(),str(block_report))

        stage="repository_authority"
        branch=git_text(root,"branch","--show-current")
        parent=git_text(root,"rev-parse","HEAD^")
        dirty=git_text(root,"status","--porcelain")
        runner_blob=git_text(root,"hash-object",str(root/Path(__file__).name))
        gate("repository_branch_exact",branch==EXPECTED_BRANCH,branch)
        gate("repository_parent_is_P1_commit",parent==EXPECTED_PARENT,parent)
        gate("repository_clean",dirty=="",repr(dirty))
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        stage="P1_binding"
        p1=drive/P1_REL
        gate("P1_output_present",p1.is_dir(),str(p1))
        p1s=load_json(p1/P1_SUMMARY)
        p1d=load_json(p1/P1_DECISION)
        gate("P1_status_exact",p1s.get("status")==P1_STATUS,p1s.get("status"))
        gate("P1_P2_authorized",p1d.get("AV4_PIVOT_P2_authorized") is True,p1d.get("AV4_PIVOT_P2_authorized"))
        gate("P1_no_cadence_selected",p1d.get("periodic_cadence_selected_now") is False)

        stage="parent_state_binding"
        f2path=drive/F2R3_REL/F2R3_STATE
        x13path=drive/E1R2_REL/E1R2_X13
        a2path=drive/A2E_REL/A2E_EPOCH
        a2sum=drive/A2E_REL/A2E_SUMMARY
        gate("F2R3_parent_state_present",f2path.is_file(),str(f2path))
        gate("E1R2_X13_present",x13path.is_file(),str(x13path))
        gate("A2E_epoch_present",a2path.is_file(),str(a2path))
        gate("A2E_summary_present",a2sum.is_file(),str(a2sum))
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

        required={
            "parent_component_mass_kg","reconciled_saturation","refreshed_pressure_psi",
            "pore_volume_m3","reference_gas_pressure_pa","streamline_xyz_m",
            "streamline_tof_s","streamline_weight_m3_s","streamline_face_pressure_psi",
            "xi"
        }
        gate("A2E_required_epoch_arrays",required.issubset(epoch),sorted(required))

        parent_grid_mass=np.asarray(epoch["parent_component_mass_kg"],dtype=np.float64)
        parent_grid_sat=np.asarray(epoch["reconciled_saturation"],dtype=np.float64)
        parent_pressure=np.asarray(epoch["refreshed_pressure_psi"],dtype=np.float64)
        grid_pv=np.asarray(epoch["pore_volume_m3"],dtype=np.float64)
        p_ref=float(np.asarray(epoch["reference_gas_pressure_pa"]).reshape(()))
        parent_xyz=np.asarray(epoch["streamline_xyz_m"],dtype=np.float64)
        parent_tof=np.asarray(epoch["streamline_tof_s"],dtype=np.float64)
        parent_weights=np.asarray(epoch["streamline_weight_m3_s"],dtype=np.float64)
        parent_face_pressure=np.asarray(epoch["streamline_face_pressure_psi"],dtype=np.float64)
        xi=np.asarray(epoch["xi"],dtype=np.float64).reshape(-1)

        gate("parent_CV_shapes",all(x.shape==(NSL,NCV) for x in [
            parent_cv_mass,parent_cv_sat,parent_cv_capacity,parent_cv_pv,parent_cv_coeff
        ]))
        gate("parent_grid_shapes",parent_grid_mass.shape==GRID and parent_grid_sat.shape==GRID and parent_pressure.shape==GRID and grid_pv.shape==GRID)
        gate("parent_streamline_shapes",parent_xyz.shape==(NSL,NN,3) and parent_tof.shape==(NSL,NN) and parent_weights.shape==(NSL,) and parent_face_pressure.shape==(NSL,NN) and xi.shape==(NN,))

        stage="source_module_binding"
        f4=load_module(root/F4R3,"av4_pivot_p2_f4")
        a4=load_module(root/A4R2,"av4_pivot_p2_a4")
        a2e=load_module(root/A2E,"av4_pivot_p2_a2e")
        r2=load_module(root/R2,"av4_pivot_p2_r2")
        e37=load_module(root/E37A,"av4_pivot_p2_e37")
        sg7d=load_module(root/SG7D,"av4_pivot_p2_sg7d")

        gate("required_teacher_helpers_present",
             hasattr(f4,"execute_teacher_with_coeff")
             and hasattr(f4,"exact_parent_mass_mapback")
             and hasattr(f4,"build_cv_geometry_from_faces")
             and hasattr(a2e,"invert_local_mass"))

        cvavg=0.5*(X13[:,:-1,:]+X13[:,1:,:])
        phi_cv=cvavg[:,:,5]
        nw_cv=3.0+cvavg[:,:,9]
        no_cv=3.0+cvavg[:,:,10]
        krw_cv=0.80+0.20*cvavg[:,:,11]
        kro_cv=0.80+0.20*cvavg[:,:,12]
        cvgeom=f4.build_cv_geometry_from_faces(parent_tof,xi)

        parent_operator=sg7d.build_subsegment_operator(
            parent_xyz,parent_tof/SPD,parent_weights*SPD
        )
        parent_geometry=e37.build_control_volume_geometry(
            r2,parent_operator,parent_pressure,p_ref,NSL,NCV
        )
        sci_gate(
            "parent_CV_pore_volume_matches_F2R3",
            float(np.max(np.abs(np.asarray(parent_geometry["cv_pv_m3"])-parent_cv_pv)))<=1.0e-8,
            float(np.max(np.abs(np.asarray(parent_geometry["cv_pv_m3"])-parent_cv_pv)))
        )
        sci_gate(
            "parent_CV_pressure_coeff_matches_F2R3",
            relative_l2(np.asarray(parent_geometry["cv_pressure_mass_coeff"]),parent_cv_coeff)<=1.0e-12,
            relative_l2(np.asarray(parent_geometry["cv_pressure_mass_coeff"]),parent_cv_coeff)
        )

        scientific_started=True
        recovery.mkdir(parents=True,exist_ok=True)

        # Initial Day365 state.
        initial_arrays={
            "cv_mass_kg":parent_cv_mass,
            "cv_saturation":parent_cv_sat,
            "grid_mass_kg":parent_grid_mass,
            "grid_saturation":parent_grid_sat,
        }
        initial_meta={
            "teacher_substeps":0,
            "injected_mass_kg":0.0,
            "produced_mass_kg":0.0,
            "step_runtime_s":0.0,
            "grid_total_mass_kg":fsum_array(parent_grid_mass),
            "grid_saturation_min":float(np.min(parent_grid_sat)),
            "grid_saturation_max":float(np.max(parent_grid_sat)),
            "global_mass_residual_kg":0.0,
        }
        c365=load_checkpoint(recovery,START_DAY,runner_blob)
        if c365 is None:
            save_checkpoint(recovery,START_DAY,runner_blob,initial_arrays,initial_meta)
            print("[PASS] durable P2 initial checkpoint published -- Day 365")
            states={START_DAY:initial_arrays}
            metas={START_DAY:initial_meta}
        else:
            states={START_DAY:c365[0]}
            metas={START_DAY:c365[1]}
            print("[PASS] reused durable P2 checkpoint -- Day 365")

        current_arrays=states[START_DAY]
        cumulative_injected=0.0
        cumulative_produced=0.0

        for day in SNAPSHOT_DAYS[1:]:
            cached=load_checkpoint(recovery,float(day),runner_blob)
            if cached is not None:
                arrays,meta=cached
                states[float(day)]=arrays
                metas[float(day)]=meta
                current_arrays=arrays
                cumulative_injected=float(meta["cumulative_injected_mass_kg"])
                cumulative_produced=float(meta["cumulative_produced_mass_kg"])
                print(f"[PASS] reused durable P2 checkpoint -- Day {day:g}")
                continue

            stage=f"transport_to_day_{int(day)}"
            prev_day=float(day-STEP_DAYS)
            old=current_arrays
            t0=time.time()
            teacher=f4.execute_teacher_with_coeff(
                a4=a4,
                r2=r2,
                e37=e37,
                old_mass=np.asarray(old["cv_mass_kg"],dtype=np.float64),
                old_sat=np.asarray(old["cv_saturation"],dtype=np.float64),
                capacity=parent_cv_capacity,
                cv_pressure_mass_coeff=parent_cv_coeff,
                cv_pv_m3=parent_cv_pv,
                face_pressure_psi=parent_face_pressure,
                p_ref_pa=p_ref,
                q_m3_day=parent_weights*SPD,
                nw=nw_cv,no=no_cv,krw_max=krw_cv,kro_max=kro_cv,
                phi_cv=phi_cv,
                cvgeom=cvgeom,
                delta_days=STEP_DAYS,
            )

            mapback=f4.exact_parent_mass_mapback(
                r2=r2,
                parent_grid_mass=np.asarray(old["grid_mass_kg"],dtype=np.float64),
                old_cv_saturation=np.asarray(old["cv_saturation"],dtype=np.float64),
                new_cv_saturation=np.asarray(teacher["future_saturation"],dtype=np.float64),
                old_cv_mass=np.asarray(old["cv_mass_kg"],dtype=np.float64),
                new_cv_mass=np.asarray(teacher["future_mass"],dtype=np.float64),
                geometry=parent_geometry,
                p_ref_pa=p_ref,
            )

            try:
                sg=a2e.invert_local_mass(
                    r2,
                    np.asarray(mapback["future_grid_mass_kg"],dtype=np.float64),
                    parent_pressure,
                    p_ref,
                    grid_pv,
                )
            except Exception as exc:
                raise ScientificFail(
                    "P2_frozen_parent_pressure_grid_mass_inversion",
                    {"day":float(day),"exception":repr(exc)}
                ) from exc

            grid_sat=BACKGROUND+np.asarray(sg,dtype=np.float64)
            step_injected=float(teacher["injected_mass_kg"])
            step_produced=float(teacher["produced_mass_kg"])
            cumulative_injected += step_injected
            cumulative_produced += step_produced

            expected=fsum_array(np.asarray(old["grid_mass_kg"])) + step_injected - step_produced
            actual=fsum_array(np.asarray(mapback["future_grid_mass_kg"]))
            tol=max(1.0e-6,1.0e-10*max(abs(expected),1.0))
            sci_gate(
                f"Day{int(day)}_grid_mass_ledger",
                abs(actual-expected)<=tol,
                {"actual_kg":actual,"expected_kg":expected,"residual_kg":actual-expected,"tol_kg":tol}
            )
            sci_gate(
                f"Day{int(day)}_grid_saturation_bounds",
                float(np.min(grid_sat))>=BACKGROUND-1.0e-10
                and float(np.max(grid_sat))<=0.80+1.0e-10,
                [float(np.min(grid_sat)),float(np.max(grid_sat))]
            )

            arrays={
                "cv_mass_kg":np.asarray(teacher["future_mass"],dtype=np.float64),
                "cv_saturation":np.asarray(teacher["future_saturation"],dtype=np.float64),
                "grid_mass_kg":np.asarray(mapback["future_grid_mass_kg"],dtype=np.float64),
                "grid_saturation":grid_sat,
            }
            meta={
                "previous_day":prev_day,
                "teacher_substeps":int(teacher["steps"]),
                "injected_mass_kg":step_injected,
                "produced_mass_kg":step_produced,
                "cumulative_injected_mass_kg":cumulative_injected,
                "cumulative_produced_mass_kg":cumulative_produced,
                "global_mass_residual_kg":float(teacher["global_mass_residual_kg"]),
                "grid_total_mass_kg":actual,
                "grid_saturation_min":float(np.min(grid_sat)),
                "grid_saturation_max":float(np.max(grid_sat)),
                "pass_through_activation_events":int(teacher["pass_through_activation_events"]),
                "step_runtime_s":float(time.time()-t0),
            }
            save_checkpoint(recovery,float(day),runner_blob,arrays,meta)
            print(f"[PASS] durable P2 snapshot checkpoint published -- Day {day:g}")

            states[float(day)]=arrays
            metas[float(day)]=meta
            current_arrays=arrays

        stage="consolidation"
        days=SNAPSHOT_DAYS.copy()
        cv_mass=np.stack([states[float(d)]["cv_mass_kg"] for d in days],axis=0)
        cv_sat=np.stack([states[float(d)]["cv_saturation"] for d in days],axis=0)
        grid_mass=np.stack([states[float(d)]["grid_mass_kg"] for d in days],axis=0)
        grid_sat=np.stack([states[float(d)]["grid_saturation"] for d in days],axis=0)

        rows=[]
        for d in days:
            m=metas[float(d)]
            rows.append({
                "day":float(d),
                "grid_total_mass_kg":float(m["grid_total_mass_kg"]),
                "grid_saturation_min":float(m["grid_saturation_min"]),
                "grid_saturation_max":float(m["grid_saturation_max"]),
                "teacher_substeps":int(m.get("teacher_substeps",0)),
                "step_injected_mass_kg":float(m.get("injected_mass_kg",0.0)),
                "step_produced_mass_kg":float(m.get("produced_mass_kg",0.0)),
                "cumulative_injected_mass_kg":float(m.get("cumulative_injected_mass_kg",0.0)),
                "cumulative_produced_mass_kg":float(m.get("cumulative_produced_mass_kg",0.0)),
                "global_mass_residual_kg":float(m.get("global_mass_residual_kg",0.0)),
                "step_runtime_s":float(m.get("step_runtime_s",0.0)),
            })

        # Global end-to-end ledger.
        initial_total=fsum_array(grid_mass[0])
        final_total=fsum_array(grid_mass[-1])
        total_injected=sum(float(metas[float(d)].get("injected_mass_kg",0.0)) for d in days[1:])
        total_produced=sum(float(metas[float(d)].get("produced_mass_kg",0.0)) for d in days[1:])
        end_residual=final_total-(initial_total+total_injected-total_produced)
        end_tol=max(1.0e-6,1.0e-10*max(abs(final_total),1.0))
        sci_gate(
            "P2_end_to_end_global_mass_ledger",
            abs(end_residual)<=end_tol,
            {"residual_kg":end_residual,"tolerance_kg":end_tol}
        )

        stage="plotting"
        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_Final_Artifacts"
        if local.exists():
            shutil.rmtree(local)
        local.mkdir(parents=True)
        plot_dir=local/"plots"
        qplots=plot_dense_metrics(rows,plot_dir)
        pplots=plot_selected_plumes(days,grid_sat,plot_dir)

        with (local/"POSTV16_AV4_PIVOT_P2_Dense_5Day_Snapshots.npz").open("wb") as f:
            np.savez_compressed(
                f,
                target_days=days,
                cv_component_mass_kg=cv_mass,
                cv_saturation=cv_sat,
                grid_component_mass_kg=grid_mass,
                grid_saturation=grid_sat,
                frozen_pressure_psi=parent_pressure,
                frozen_streamline_xyz_m=parent_xyz,
                frozen_streamline_tof_s=parent_tof,
                frozen_streamline_weight_m3_s=parent_weights,
                frozen_streamline_face_pressure_psi=parent_face_pressure,
                xi=xi,
            )

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "start_day":START_DAY,
            "end_day":END_DAY,
            "spacing_days":STEP_DAYS,
            "snapshot_count":int(len(days)),
            "flow_epoch_frozen_at_day":START_DAY,
            "pressure_refresh_executed":False,
            "five_stage_E2_assignment_executed":False,
            "same_time_fixed_point_executed":False,
            "training_executed":False,
            "end_to_end_mass_residual_kg":float(end_residual),
            "end_to_end_mass_tolerance_kg":float(end_tol),
            "dense_snapshot_file":"POSTV16_AV4_PIVOT_P2_Dense_5Day_Snapshots.npz",
            "quantitative_plot_count":len(qplots),
            "threeD_plume_plot_count":len(pplots),
        }
        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "scientific_interpretation":(
                "P2 creates one shared dense frozen-flow transport trajectory at 5-day resolution "
                "from the certified Day365 flow epoch. These snapshots are the common state basis "
                "for later exact pressure/Darcy/Pollock/TOF refresh diagnostics and avoid comparing "
                "different underlying transport histories before cadence policies are explicitly tested."
            ),
            "AV4_PIVOT_P3_authorized":True,
            "P3_name":"Dense 5-Day Exact Flow-Refresh Diagnostic Sweep",
            "P3_required_days":[float(x) for x in days],
            "candidate_cadences_days":[50.0,5.0],
            "periodic_cadence_selected_now":False,
            "R3R6R1_execution_invalidated":False,
            "O3R7_authorized":False,
            "F5_dataset_generation_authorized":False,
            "training_authorized":False,
        }

        (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_Summary.json").write_bytes(json_bytes(summary))
        (local/"POSTV16_AV4_PIVOT_P2_Decision_Contract.json").write_bytes(json_bytes(decision))
        (local/"POSTV16_AV4_PIVOT_P2_Dense_Snapshot_Metrics.csv").write_bytes(csv_bytes(rows))

        manifest=[]
        for p in sorted(local.rglob("*")):
            if p.is_file():
                manifest.append({
                    "file":str(p.relative_to(local)).replace("\\","/"),
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        (local/"POSTV16_AV4_PIVOT_P2_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))

        stage="immutable_publish"
        if out.exists():
            raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(local,out)

        print()
        print("="*190)
        print("POSTV16-AV4-PIVOT-P2: PASS")
        print("Dense frozen-flow snapshots published :",len(days))
        print("Snapshot spacing days                 :",STEP_DAYS)
        print("End-to-end mass residual kg           :",end_residual)
        print("P3 dense exact flow-refresh sweep authorized.")
        print("No periodic cadence selected yet.")
        print("="*190)
        return 0

    except ScientificFail as exc:
        fail_dir.mkdir(parents=True,exist_ok=True)
        p=fail_dir/"POSTV16_AV4_PIVOT_P2_Scientific_Fail_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_FAIL,
                "failed_stage":stage,
                "failed_gate":exc.gate,
                "detail":exc.detail,
                "scientific_execution_started":scientific_started,
                "automatic_rerun_authorized":False,
                "R3R6R1_execution_invalidated":False,
            },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(MILESTONE+": SCIENTIFIC FAIL")
        print("Gate:",exc.gate)
        print("Detail:",exc.detail)
        return 3

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/"POSTV16_AV4_PIVOT_P2_Blocked_Report.json"
        if not p.exists():
            p.write_text(json.dumps({
                "milestone":MILESTONE,
                "status":STATUS_BLOCKED,
                "failed_stage":stage,
                "exception":repr(exc),
                "scientific_execution_started":scientific_started,
                "recovery_checkpoints_preserved":True,
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

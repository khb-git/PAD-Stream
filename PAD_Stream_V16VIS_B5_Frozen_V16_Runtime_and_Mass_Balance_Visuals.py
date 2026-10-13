from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import io
import json
import subprocess
from typing import Any

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


MILESTONE = "V16VIS-B5"
STATUS = "FROZEN_V16_RUNTIME_AND_MASS_BALANCE_VISUALS_VALIDATED"
NEXT = "V16VIS-B6 - Frozen V16 Architecture and Release Visuals"

RELEASE_ID = "PAD-STREAM-V16-RC1-B92D52088D01078A"
RELEASE_PATH_ID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

A1_RUNNER = "PAD_Stream_V16VIS_A1_Visual_Authority_Manifest_and_Data_Extraction.py"
A1_GIT_BLOB = "7ed31f0e69b63489f25a1833cdc3693f735b1233"
B4_RUNNER = "PAD_Stream_V16VIS_B4_Frozen_V16_CO2_Plume_Evolution_Visuals.py"
B4_GIT_BLOB = "9f80237ce626c96ff9ec2f8e74f854f1ec7c779b"

EXPECTED_A1_STATUS = "V16_VISUAL_AUTHORITY_MANIFEST_AND_DATA_EXTRACTION_VALIDATED"
EXPECTED_B4_STATUS = "FROZEN_V16_CO2_PLUME_EVOLUTION_VISUALS_VALIDATED"
EXPECTED_A1_CACHE_SHA256 = "2acbbbc8608eb771d1a6ea6909c7d37caec2ee77666a7828226e3a9e531d316e"

A1_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_A_Authority_and_Data_Extraction"
B4_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_B4_CO2_Plume_Evolution"
OUT_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_B5_Runtime_and_Mass_Balance"
BLOCKED_REL = Path("visuals") / RELEASE_PATH_ID / "Phase_B5_BLOCKED"

A1_CACHE = "V16VIS_A1_Authoritative_Visual_Data.npz"
A1_SUMMARY = "PAD_Stream_V16VIS_A1_Summary.json"
A1_CLOSURE = "V16VIS_A1_Final_Closure.json"
A1_MANIFEST = "V16VIS_A1_Artifact_Manifest.csv"

B4_SUMMARY = "PAD_Stream_V16VIS_B4_Summary.json"
B4_CLOSURE = "V16VIS_B4_Final_Closure.json"
B4_MANIFEST = "V16VIS_B4_Artifact_Manifest.csv"

OBSERVATION_DAYS = np.asarray([30.0,60.0,100.0,150.0,250.0,365.0,500.0,750.0,1000.0], dtype=np.float64)
OBSERVATION_STEPS = np.asarray([611,1222,4640,5747,7931,10400,13259,18490,23668], dtype=np.int64)
CAPACITY_DAYS = np.asarray([100.0,150.0,250.0,365.0,500.0,750.0,1000.0], dtype=np.float64)

DPI = 300
FIGSIZE = (9.0, 6.5)
FIGURE_VARIANTS = [
    ("R01", "mass_inventory", "R01_Injected_Produced_Stored_CO2_vs_Time"),
    ("R02", "producer_gas_cut", "R02_Producer_CO2_Gas_Cut_vs_Time"),
    ("R03", "mass_residual", "R03_Component_Mass_Residual_vs_Time"),
    ("R04", "capacity_margin", "R04_Minimum_Capacity_Margin_vs_Time"),
]


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_blob_sha(path: Path, root: Path) -> str:
    proc = subprocess.run(["git", "-C", str(root), "hash-object", str(path)], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.stdout.strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists():
            if p.read_bytes() != data:
                raise GateError(f"existing_output_differs:{name}")
        else:
            p.write_bytes(data)


def save_figure(fig: plt.Figure, out: Path, stem: str) -> list[dict[str, Any]]:
    rows = []
    for ext in ("png", "pdf"):
        p = out / f"{stem}.{ext}"
        if p.exists():
            raise GateError(f"existing_figure:{p.name}")
        fig.savefig(p, dpi=DPI, bbox_inches="tight")
        rows.append({"file":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size})
    plt.close(fig)
    return rows


def render_r01(out: Path, days: np.ndarray, injected: np.ndarray, produced: np.ndarray, stored: np.ndarray):
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(days, injected/1000.0, marker="o", linewidth=1.8, label="Cumulative injected CO₂")
    ax.plot(days, produced/1000.0, marker="o", linewidth=1.8, label="Cumulative produced CO₂")
    ax.plot(days, stored/1000.0, marker="o", linewidth=1.8, label="Stored CO₂")
    ax.set_xlabel("Physical time, days")
    ax.set_ylabel("CO₂ mass, tonnes")
    ax.set_title("R01 — Frozen V16 CO₂ Inventory vs Time")
    ax.grid(True, alpha=0.25); ax.legend()
    return save_figure(fig, out, "R01_Injected_Produced_Stored_CO2_vs_Time")


def render_r02(out: Path, days: np.ndarray, gas_cut: np.ndarray):
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(days, gas_cut, marker="o", linewidth=1.8)
    ax.set_xlabel("Physical time, days")
    ax.set_ylabel("Producer CO₂ gas cut, fraction")
    ax.set_title("R02 — Frozen V16 Producer CO₂ Gas Cut vs Time")
    ax.set_ylim(bottom=0.0)
    ax.grid(True, alpha=0.25)
    return save_figure(fig, out, "R02_Producer_CO2_Gas_Cut_vs_Time")


def render_r03(out: Path, days: np.ndarray, residual: np.ndarray):
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(days, residual, marker="o", linewidth=1.8)
    ax.axhline(0.0, linewidth=1.0)
    ax.set_xlabel("Physical time, days")
    ax.set_ylabel("Recomputed cumulative component-mass residual, kg")
    ax.set_title("R03 — Frozen V16 Component-Mass Residual vs Time")
    ax.grid(True, alpha=0.25)
    return save_figure(fig, out, "R03_Component_Mass_Residual_vs_Time")


def render_r04(out: Path, days: np.ndarray, margin: np.ndarray, refresh_count: np.ndarray, adjustments: np.ndarray):
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(days, margin/1000.0, marker="o", linewidth=1.8)
    ax.axhline(0.0, linewidth=1.0)
    ax.set_xlabel("Physical time, days")
    ax.set_ylabel("Minimum raw capacity margin, tonnes")
    ax.set_title("R04 — Frozen V16 Minimum Capacity Margin vs Time")
    ax.grid(True, alpha=0.25)
    ax.text(0.02, 0.97, f"Capacity refresh count = {int(np.sum(refresh_count))}\nController adjustments = {int(np.sum(adjustments))}", transform=ax.transAxes, va="top")
    return save_figure(fig, out, "R04_Minimum_Capacity_Margin_vs_Time")


def self_test() -> None:
    if RELEASE_ID != "PAD-STREAM-V16-RC1-B92D52088D01078A": raise RuntimeError("release_identity")
    if len(FIGURE_VARIANTS) != 4: raise RuntimeError("figure_variant_count")
    if OBSERVATION_DAYS.tolist() != [30.0,60.0,100.0,150.0,250.0,365.0,500.0,750.0,1000.0]: raise RuntimeError("observation_days")
    if CAPACITY_DAYS.tolist() != [100.0,150.0,250.0,365.0,500.0,750.0,1000.0]: raise RuntimeError("capacity_days")
    if OUT_REL != Path("visuals") / RELEASE_PATH_ID / "Phase_B5_Runtime_and_Mass_Balance": raise RuntimeError("output_path")
    print("PAD-Stream V16VIS-B5 runtime / mass-balance visual self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve(); drive = Path(drive_root).resolve()
    a1 = drive / A1_REL; b4 = drive / B4_REL; out = drive / OUT_REL; blocked = drive / BLOCKED_REL
    gates: dict[str,dict[str,Any]] = {}; failed_stage = None
    def gate(name: str, passed: bool, detail: Any="") -> None:
        gates[name] = {"passed":bool(passed),"detail":str(detail)}
        if not passed: raise GateError(name)
    try:
        print("\n" + "="*164)
        print("PAD-Stream V16VIS-B5 — Frozen V16 Runtime and Mass-Balance Visuals")
        print("="*164)
        print("Release                    :", RELEASE_ID)
        print("Simulation                  : none")
        print("Accepted-state mutation     : none")
        print("Runtime authority           : frozen E48 audit arrays carried by A1 cache")

        failed_stage = "repository_source_binding"
        for role, filename, expected in [("A1",A1_RUNNER,A1_GIT_BLOB),("B4",B4_RUNNER,B4_GIT_BLOB)]:
            p = root / filename; gate(f"{role}_exists",p.is_file(),p)
            actual = git_blob_sha(p,root); gate(f"{role}_git_blob_exact",actual==expected,actual)

        failed_stage = "phase_prerequisite_binding"
        for name in [A1_CACHE,A1_SUMMARY,A1_CLOSURE,A1_MANIFEST]: gate(f"A1_exists_{name}",(a1/name).is_file(),a1/name)
        for name in [B4_SUMMARY,B4_CLOSURE,B4_MANIFEST]: gate(f"B4_exists_{name}",(b4/name).is_file(),b4/name)
        a1_summary=load_json(a1/A1_SUMMARY); a1_closure=load_json(a1/A1_CLOSURE)
        b4_summary=load_json(b4/B4_SUMMARY); b4_closure=load_json(b4/B4_CLOSURE)
        gate("A1_status_exact",a1_summary.get("status")==EXPECTED_A1_STATUS,a1_summary.get("status"))
        gate("A1_release_exact",a1_summary.get("release_id")==RELEASE_ID,a1_summary.get("release_id"))
        gate("A1_closure_passed",a1_closure.get("all_gates_passed") is True)
        gate("B4_status_exact",b4_summary.get("status")==EXPECTED_B4_STATUS,b4_summary.get("status"))
        gate("B4_release_exact",b4_summary.get("release_id")==RELEASE_ID,b4_summary.get("release_id"))
        gate("B4_closure_passed",b4_closure.get("all_gates_passed") is True)
        gate("B4_phase_B5_authorized",b4_closure.get("phase_B5_authorized") is True)

        cache_path=a1/A1_CACHE; cache_sha=sha256_file(cache_path)
        gate("A1_cache_SHA_exact",cache_sha==EXPECTED_A1_CACHE_SHA256,cache_sha)
        gate("A1_summary_cache_SHA_exact",a1_summary.get("visual_cache_sha256")==cache_sha)

        failed_stage = "frozen_runtime_metric_extraction"
        with np.load(cache_path,allow_pickle=False) as z:
            metric_days=np.asarray(z["metric_days"],dtype=np.float64)
            metric_steps=np.asarray(z["metric_steps"],dtype=np.int64)
            injected=np.asarray(z["cumulative_injected_co2_mass_kg"],dtype=np.float64)
            produced=np.asarray(z["cumulative_produced_co2_mass_kg"],dtype=np.float64)
            stored=np.asarray(z["stored_co2_mass_kg"],dtype=np.float64)
            residual=np.asarray(z["cumulative_mass_residual_kg"],dtype=np.float64)
            gas_cut=np.asarray(z["producer_co2_gas_cut"],dtype=np.float64)
            capacity_days=np.asarray(z["capacity_days"],dtype=np.float64)
            capacity_margin=np.asarray(z["minimum_raw_capacity_margin_kg"],dtype=np.float64)
            refresh_count=np.asarray(z["capacity_refresh_count"],dtype=np.int64)
            adjustments=np.asarray(z["capacity_controller_adjustments_total"],dtype=np.int64)

        gate("metric_days_exact",np.array_equal(metric_days,OBSERVATION_DAYS),metric_days.tolist())
        gate("metric_steps_exact",np.array_equal(metric_steps,OBSERVATION_STEPS),metric_steps.tolist())
        for key,arr in [("injected",injected),("produced",produced),("stored",stored),("residual",residual),("gas_cut",gas_cut)]:
            gate(f"{key}_shape_exact",arr.shape==(9,),arr.shape)
            gate(f"{key}_finite",bool(np.all(np.isfinite(arr))))
        gate("injected_nondecreasing",bool(np.all(np.diff(injected)>=-1e-9)))
        gate("produced_nondecreasing",bool(np.all(np.diff(produced)>=-1e-9)))
        gate("stored_nonnegative",float(np.min(stored))>=-1e-9,float(np.min(stored)))
        gate("gas_cut_bounds",float(np.min(gas_cut))>=-1e-12 and float(np.max(gas_cut))<=1.0+1e-12,(float(np.min(gas_cut)),float(np.max(gas_cut))))
        gate("capacity_days_exact",np.array_equal(capacity_days,CAPACITY_DAYS),capacity_days.tolist())
        for key,arr in [("capacity_margin",capacity_margin),("refresh_count",refresh_count),("adjustments",adjustments)]:
            gate(f"{key}_shape_exact",arr.shape==(7,),arr.shape)
        gate("capacity_margin_finite",bool(np.all(np.isfinite(capacity_margin))))
        gate("capacity_margin_positive",float(np.min(capacity_margin))>0.0,float(np.min(capacity_margin)))
        gate("capacity_refresh_zero",int(np.sum(refresh_count))==0,int(np.sum(refresh_count)))
        gate("capacity_adjustments_zero",int(np.sum(adjustments))==0,int(np.sum(adjustments)))

        failed_stage = "figure_rendering"
        if out.exists() and any(out.iterdir()): raise GateError("B5_output_directory_not_empty:refusing_to_overwrite_existing_visual_release")
        out.mkdir(parents=True,exist_ok=True)
        rendered=[]
        rendered.extend(render_r01(out,metric_days,injected,produced,stored))
        rendered.extend(render_r02(out,metric_days,gas_cut))
        rendered.extend(render_r03(out,metric_days,residual))
        rendered.extend(render_r04(out,capacity_days,capacity_margin,refresh_count,adjustments))
        gate("rendered_file_count_exact",len(rendered)==8,len(rendered))
        gate("all_rendered_files_nonempty",all(int(r["bytes"])>0 for r in rendered))

        failed_stage = "visual_contract_and_closeout"
        rendered_by_stem={}
        for row in rendered: rendered_by_stem.setdefault(Path(row["file"]).stem,[]).append(row)
        authority={
            "R01":"DERIVED_FROM_FROZEN_AUDIT: E48 observation audit arrays carried by A1 cache",
            "R02":"DERIVED_FROM_FROZEN_AUDIT: E48 producer CO2 gas-cut audit array carried by A1 cache",
            "R03":"DERIVED_FROM_FROZEN_AUDIT: E48 recomputed cumulative component-mass residual carried by A1 cache",
            "R04":"DERIVED_FROM_FROZEN_AUDIT: E48 capacity-safety audit arrays carried by A1 cache",
        }
        figure_index=[]
        for fid,variant,stem in FIGURE_VARIANTS:
            figure_index.append({"figure_id":fid,"variant":variant,"title_or_stem":stem,"authority":authority[fid],"source_cache_sha256":cache_sha,"release_id":RELEASE_ID,"accepted_state_mutation":False,"files":";".join(sorted(r["file"] for r in rendered_by_stem[stem]))})
        captions=[
            {"figure_id":"R01","caption":"Cumulative injected CO2, cumulative produced CO2, and stored CO2 versus physical time, derived only from the frozen E48 observation audit metrics preserved in the A1 visual cache. Display units are tonnes; source values remain kilograms."},
            {"figure_id":"R02","caption":"Frozen audited producer CO2 gas-cut metric versus physical time across the nine exact observation checkpoints."},
            {"figure_id":"R03","caption":"Recomputed cumulative component-mass residual versus time from the frozen E48 observation audit. The zero line is a display reference only."},
            {"figure_id":"R04","caption":"Minimum raw capacity margin versus time from the frozen E48 capacity-safety audit. The audited capacity-refresh and controller-adjustment counts remain zero across the displayed checkpoints."},
        ]
        contract={
            "release_id":RELEASE_ID,"milestone":MILESTONE,"source_visual_cache_sha256":cache_sha,
            "runtime_authority":"E48 frozen observation and capacity audits carried by A1 cache",
            "metric_days":metric_days.tolist(),"metric_steps":metric_steps.tolist(),"capacity_days":capacity_days.tolist(),
            "source_units":{"mass":"kg","gas_cut":"fraction","capacity_margin":"kg"},
            "display_units":{"R01":"tonnes","R02":"fraction","R03":"kg","R04":"tonnes"},
            "capacity_refresh_count_total":int(np.sum(refresh_count)),"capacity_controller_adjustments_total":int(np.sum(adjustments)),
            "simulation_executed":False,"accepted_state_mutation":False,"physical_time_advance":False,"accepted_step_advance":False,"transport_update":False,"ledger_update":False,"parameter_change":False,"calibration":False,
        }
        summary={
            "milestone":MILESTONE,"status":STATUS,"release_id":RELEASE_ID,"simulation_executed":False,"accepted_state_mutation":False,
            "source_visual_cache_sha256":cache_sha,"figure_families_completed":["R01","R02","R03","R04"],"rendered_variants":4,"rendered_files_png_pdf":8,
            "runtime_observation_count":len(metric_days),"capacity_checkpoint_count":len(capacity_days),"terminal_injected_co2_mass_kg":float(injected[-1]),"terminal_produced_co2_mass_kg":float(produced[-1]),"terminal_stored_co2_mass_kg":float(stored[-1]),"terminal_cumulative_mass_residual_kg":float(residual[-1]),"terminal_producer_co2_gas_cut":float(gas_cut[-1]),"minimum_capacity_margin_kg":float(np.min(capacity_margin)),"next":NEXT,
        }
        closure={
            "milestone":MILESTONE,"status":STATUS,"all_gates_passed":all(v["passed"] for v in gates.values()),"gate_count":len(gates),
            "R01_complete":True,"R02_complete":True,"R03_complete":True,"R04_complete":True,"frozen_E48_runtime_metrics_used":True,"diagnostic_or_simulation_reconstruction_used":False,"accepted_simulation_state_modified":False,"phase_B6_authorized":True,"next":NEXT,
        }
        immutable_publish(out,{
            "V16VIS_B5_Figure_Index.csv":csv_bytes(figure_index),"V16VIS_B5_Figure_Captions.csv":csv_bytes(captions),"V16VIS_B5_Runtime_Mass_Balance_Contract.json":json_bytes(contract),"PAD_Stream_V16VIS_B5_Summary.json":json_bytes(summary),"V16VIS_B5_Final_Gate_Matrix.csv":csv_bytes([{"gate":k,**v} for k,v in gates.items()]),"V16VIS_B5_Final_Closure.json":json_bytes(closure),
        })
        manifest=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="V16VIS_B5_Artifact_Manifest.csv": manifest.append({"file":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size})
        immutable_publish(out,{"V16VIS_B5_Artifact_Manifest.csv":csv_bytes(manifest)})

        print("\n"+"="*164); print("PAD-Stream V16VIS-B5: PASS"); print("="*164)
        print(f"{'Status':72}: {STATUS}")
        print(f"{'Release ID':72}: {RELEASE_ID}")
        print(f"{'A1 visual cache SHA':72}: {cache_sha}")
        print(f"{'Figure families completed':72}: R01, R02, R03, R04")
        print(f"{'Rendered variants':72}: 4")
        print(f"{'Rendered PNG/PDF files':72}: 8")
        print(f"{'Runtime observation checkpoints':72}: {len(metric_days)}")
        print(f"{'Capacity audit checkpoints':72}: {len(capacity_days)}")
        print(f"{'Terminal injected / produced / stored CO2':72}: {injected[-1]/1000.0:.6f} / {produced[-1]/1000.0:.6f} / {stored[-1]/1000.0:.6f} tonnes")
        print(f"{'Terminal cumulative mass residual':72}: {residual[-1]:.12g} kg")
        print(f"{'Terminal producer CO2 gas cut':72}: {gas_cut[-1]:.12g}")
        print(f"{'Minimum raw capacity margin':72}: {np.min(capacity_margin)/1000.0:.6f} tonnes")
        print(f"{'Capacity refresh / controller adjustments':72}: {int(np.sum(refresh_count))} / {int(np.sum(adjustments))}")
        print(f"{'Accepted simulation state modified':72}: False")
        print(f"{'Phase B6 authorized':72}: True")
        print(f"{'Next':72}: {NEXT}")
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report={"milestone":MILESTONE,"status":"FROZEN_V16_RUNTIME_AND_MASS_BALANCE_VISUALS_BLOCKED","failed_stage":failed_stage,"exception":repr(exc),"gates":gates}
        data=json_bytes(report); p=blocked/"V16VIS_B5_Blocked_Report.json"
        if p.exists() and p.read_bytes()!=data: p=blocked/("V16VIS_B5_Blocked_Report_"+hashlib.sha256(data).hexdigest()[:12]+".json")
        p.write_bytes(data)
        print("\n"+"="*164); print("PAD-Stream V16VIS-B5: BLOCKED"); print("="*164)
        print("Report      :",p); print("Failed stage:",failed_stage); print("Exception   :",repr(exc))
        return 2


def parse_args() -> argparse.Namespace:
    p=argparse.ArgumentParser(); p.add_argument("--project-root",type=Path,default=Path(".")); p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute")); p.add_argument("--self-test",action="store_true"); return p.parse_args()

if __name__=="__main__":
    args=parse_args()
    if args.self_test:
        self_test(); raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))

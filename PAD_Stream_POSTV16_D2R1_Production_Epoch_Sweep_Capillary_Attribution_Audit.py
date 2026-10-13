from __future__ import annotations

from pathlib import Path
import argparse
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from typing import Any

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MILESTONE = "POSTV16-D2R1"
STATUS = "POSTV16_PRODUCTION_EPOCH_SWEEP_CAPILLARY_ATTRIBUTION_AUDIT_COMPLETED"
NEXT = (
    "POSTV16-D2R1 interpretation gate - decide whether an earlier-time 0-69.883d "
    "attribution audit is required before variable-porosity sensitivity or IBDP handoff"
)
RELEASE_ID = "PAD-STREAM-V16-RC1-B92D52088D01078A"
RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_GRID = (15, 50, 50)
BACKGROUND_SATURATION = 0.20
POROSITY = 0.20
DAY_TO_S = 86400.0
DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0
FT_TO_M = 0.3048
PRODUCTION_START_DAY = 69.88346704782309
PRODUCTION_END_DAY = 1000.0

D2_RUNNER = "PAD_Stream_POSTV16_D2_Streamline_to_Grid_CO2_Saturation_Attribution_Audit.py"
D2_RUNNER_BLOB = "f7c594ed5ef8e00093ed5fe317b355d17b0fbe60"
R2_RUNNER = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
E37A_RUNNER = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
R3R5_RUNNER = "PAD_Stream_V16E41R3R5_Multi_Refresh_Cadence_Sensitivity_Runtime_Refresh_Policy_Calibration.py"
R3R5_BLOB = "15aae3224ba4337cad72f9b4aa9166d602791349"
R3R4R1_RUNNER = "PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4R1_BLOB = "5f8433437ce111533338ceada922f51abb2edefe"

REPLAY_RUNNERS = [
    ("R3R7_100D", "PAD_Stream_V16E41R3R7_Repaired_Production_Rollout_to_Exact_100Day_Observation.py", "1e7e54f17477788fe518e440c21a65a544b30a48"),
    ("E42_150D", "PAD_Stream_V16E42_Repaired_Production_Continuation_to_Exact_150Day_Observation.py", "7efe0cb943b40e976b7364241dc7f41dc819a2df"),
    ("E43_250D", "PAD_Stream_V16E43_Repaired_Production_Continuation_to_Exact_250Day_Observation.py", "1aca85b46129ecc47d4089ea2d2e4b0e00500283"),
    ("E44R1_365D", "PAD_Stream_V16E44R1_Predecessor_Binding_Repair_and_Exact_365Day_Observation.py", "44db79e0553e7a2853e54f057d66874595d51716"),
    ("E45_500D", "PAD_Stream_V16E45_Repaired_Production_Continuation_to_Exact_500Day_Observation.py", "82d730049c18a2ce529f0a80a736bc395c5cf125"),
    ("E46_750D", "PAD_Stream_V16E46_Repaired_Production_Continuation_to_Exact_750Day_Observation.py", "969fae98d3d8ad4b500f3f6d266d838e093ef173"),
    ("E47_1000D", "PAD_Stream_V16E47_Repaired_Production_Continuation_to_Exact_1000Day_Observation.py", "b3f6a4212e18e13239eb7bd5703c43484b376dcb"),
]

R3R8_RUNNER = "PAD_Stream_V16E41R3R8_100Day_Legacy_Numerical_Regression_and_E41_Closure.py"
R3R8_BLOB = "607536622c3b0ff0d4aef451652e724ad4689baa"

D2_REL = Path("post_v16") / RID / "POSTV16_D2_Streamline_to_Grid_CO2_Saturation_Attribution_Audit"
OUT_REL = Path("post_v16") / RID / "POSTV16_D2R1_Production_Epoch_Sweep_Capillary_Attribution_Audit"
BLOCKED_REL = Path("post_v16") / RID / "POSTV16_D2R1_BLOCKED"

SEED_RELS = [
    Path("provenance/hybrid_dp/V16E41R3R1_ACCEPTED_TRANSITION_BUDGET_CAPACITY_REGIME_AUDIT"),
    Path("provenance/hybrid_dp/V16E41R3R6_PRODUCTION_RUNTIME_REFRESH_POLICY_FREEZE"),
    Path("provenance/hybrid_dp/V16E41R3R8_100D_LEGACY_NUMERICAL_REGRESSION_AND_E41_CLOSURE"),
]

class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_blob_sha(path: Path, repo_root: Path) -> str:
    p = subprocess.run(
        ["git", "-C", str(repo_root), "hash-object", str(path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


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
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader(); w.writerows(rows)
    return s.getvalue().encode("utf-8")


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            b = io.BytesIO(); np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


def immutable_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise GateError(f"existing_output_differs:{path}")
    else:
        path.write_bytes(data)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def scalar(a: Any) -> float:
    return float(np.asarray(a).reshape(()))


def cell_mass_from_state(physics: Any, state: dict[str, np.ndarray]) -> np.ndarray:
    sat = np.asarray(state["transport_saturation"], dtype=np.float64)
    p = np.asarray(state["accepted_pressure_psi"], dtype=np.float64)
    pref = scalar(state["co2_density_reference_pressure_pa"])
    pv = POROSITY * (DX_FT * FT_TO_M) * (DY_FT * FT_TO_M) * (DZ_FT * FT_TO_M)
    sg = np.clip(sat - BACKGROUND_SATURATION, 0.0, 0.60)
    rho = np.asarray(physics.gas_density_from_state(sat, p, pref), dtype=np.float64)
    return pv * rho * sg


def state_sg(state: dict[str, np.ndarray]) -> np.ndarray:
    return np.clip(np.asarray(state["transport_saturation"], dtype=np.float64) - BACKGROUND_SATURATION, 0.0, 0.60)


def stats(a: np.ndarray) -> dict[str, float]:
    x = np.asarray(a, dtype=np.float64).ravel()
    return {
        "min": float(np.min(x)), "p01": float(np.quantile(x, .01)),
        "p10": float(np.quantile(x, .10)), "p25": float(np.quantile(x, .25)),
        "p50": float(np.quantile(x, .50)), "mean": float(np.mean(x)),
        "p75": float(np.quantile(x, .75)), "p90": float(np.quantile(x, .90)),
        "p99": float(np.quantile(x, .99)), "max": float(np.max(x)),
        "std": float(np.std(x)),
    }


def save_figure(fig: plt.Figure, out: Path, stem: str) -> list[dict[str, Any]]:
    rows = []
    for ext in ("png", "pdf"):
        p = out / f"{stem}.{ext}"
        if p.exists():
            raise GateError(f"existing_figure:{p.name}")
        fig.savefig(p, dpi=300, bbox_inches="tight")
        rows.append({"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size})
    plt.close(fig)
    return rows


class AuditState:
    def __init__(self) -> None:
        self.cumulative_support = np.zeros(EXPECTED_GRID, dtype=bool)
        self.first_path_day = np.full(EXPECTED_GRID, np.nan, dtype=np.float64)
        self.direct_gain_kg = np.zeros(EXPECTED_GRID, dtype=np.float64)
        self.direct_loss_kg = np.zeros(EXPECTED_GRID, dtype=np.float64)
        self.direct_net_kg = np.zeros(EXPECTED_GRID, dtype=np.float64)
        self.cap_gain_kg = np.zeros(EXPECTED_GRID, dtype=np.float64)
        self.cap_loss_kg = np.zeros(EXPECTED_GRID, dtype=np.float64)
        self.cap_net_kg = np.zeros(EXPECTED_GRID, dtype=np.float64)
        self.first_direct_event = np.full(EXPECTED_GRID, -1, dtype=np.int64)
        self.first_cap_event = np.full(EXPECTED_GRID, -1, dtype=np.int64)
        self.epoch_rows: list[dict[str, Any]] = []
        self.step_rows: list[dict[str, Any]] = []
        self.segment_rows: list[dict[str, Any]] = []
        self.observation_snapshots: dict[float, dict[str, np.ndarray]] = {}
        self.pending_direct: np.ndarray | None = None
        self.current_time = PRODUCTION_START_DAY
        self.segment = ""
        self.segment_epoch_start = 0
        self.segment_step_start = 0


def make_instrumented_loader(runner: Any, audit: AuditState):
    original_loader = runner.load_module

    def instrumented_load(path: Path, name: str):
        mod = original_loader(path, name)

        if hasattr(mod, "build_flow_epoch"):
            original = mod.build_flow_epoch
            def wrapped_build_flow_epoch(*args, **kwargs):
                current = kwargs.get("current")
                if current is None:
                    raise GateError("instrumentation_missing_current_on_flow_refresh")
                t = scalar(current["physical_time_days"])
                step = int(np.asarray(current["accepted_step_index"]).reshape(()))
                result = original(*args, **kwargs)
                epoch = result[1]
                flat = np.unique(np.asarray(epoch["geometry"]["flat_cell"], dtype=np.int64))
                mask = np.zeros(int(np.prod(EXPECTED_GRID)), dtype=bool)
                mask[flat] = True
                mask = mask.reshape(EXPECTED_GRID)
                new = mask & ~audit.cumulative_support
                audit.first_path_day[new] = t
                audit.cumulative_support |= mask
                audit.epoch_rows.append({
                    "segment": audit.segment,
                    "local_refresh_index": len(audit.epoch_rows) - audit.segment_epoch_start + 1,
                    "physical_time_days": t,
                    "accepted_step_index": step,
                    "epoch_supported_cells": int(np.count_nonzero(mask)),
                    "epoch_supported_fraction": float(np.mean(mask)),
                    "newly_supported_cells": int(np.count_nonzero(new)),
                    "cumulative_supported_cells": int(np.count_nonzero(audit.cumulative_support)),
                    "cumulative_supported_fraction": float(np.mean(audit.cumulative_support)),
                    "streamline_count": int(epoch["nstream"]),
                    "CFL_dt_days": float(epoch["cfl_dt_days"]),
                })
                return result
            mod.build_flow_epoch = wrapped_build_flow_epoch

        if hasattr(mod, "map_control_volume_increment_to_grid"):
            original = mod.map_control_volume_increment_to_grid
            def wrapped_map(*args, **kwargs):
                result = original(*args, **kwargs)
                delta = np.asarray(result["deposited_delta_mass"], dtype=np.float64)
                if delta.shape != EXPECTED_GRID:
                    raise GateError(f"instrumentation_direct_mass_shape:{delta.shape}")
                audit.pending_direct = delta.copy()
                return result
            mod.map_control_volume_increment_to_grid = wrapped_map

        if hasattr(mod, "conservative_capillary_mass_redistribution"):
            original = mod.conservative_capillary_mass_redistribution
            def wrapped_capillary(*args, **kwargs):
                pre = np.asarray(kwargs["transport_saturation"], dtype=np.float64)
                p = np.asarray(kwargs["pressure_psi"], dtype=np.float64)
                pref = float(kwargs["p_ref_pa"])
                pv = float(kwargs["cell_pore_volume_m3"])
                dt_days = float(kwargs["dt_seconds"]) / DAY_TO_S
                sg0 = np.clip(pre - BACKGROUND_SATURATION, 0.0, 0.60)
                rho0 = np.asarray(mod.gas_density_from_state(pre, p, pref), dtype=np.float64)
                m0 = pv * rho0 * sg0
                result = original(*args, **kwargs)
                post = np.asarray(result["corrected"], dtype=np.float64)
                sg1 = np.clip(post - BACKGROUND_SATURATION, 0.0, 0.60)
                rho1 = np.asarray(mod.gas_density_from_state(post, p, pref), dtype=np.float64)
                m1 = pv * rho1 * sg1
                cap_delta = m1 - m0
                if audit.pending_direct is None:
                    raise GateError("instrumentation_capillary_without_pending_mapback")
                direct = audit.pending_direct
                event_index = len(audit.step_rows)
                dg = np.maximum(direct, 0.0); dl = np.maximum(-direct, 0.0)
                cg = np.maximum(cap_delta, 0.0); cl = np.maximum(-cap_delta, 0.0)
                audit.direct_gain_kg += dg; audit.direct_loss_kg += dl; audit.direct_net_kg += direct
                audit.cap_gain_kg += cg; audit.cap_loss_kg += cl; audit.cap_net_kg += cap_delta
                new_d = (dg > 1e-12) & (audit.first_direct_event < 0)
                new_c = (cg > 1e-12) & (audit.first_cap_event < 0)
                audit.first_direct_event[new_d] = event_index
                audit.first_cap_event[new_c] = event_index
                parent_time = audit.current_time
                accepted_time = parent_time + dt_days
                audit.step_rows.append({
                    "segment": audit.segment,
                    "local_step_index": len(audit.step_rows) - audit.segment_step_start + 1,
                    "parent_time_days_instrumented": parent_time,
                    "accepted_time_days_instrumented": accepted_time,
                    "accepted_dt_days_instrumented": dt_days,
                    "direct_positive_mass_kg": float(np.sum(dg)),
                    "direct_negative_mass_kg": float(np.sum(dl)),
                    "direct_net_mass_kg": float(np.sum(direct)),
                    "direct_changed_cells": int(np.count_nonzero(np.abs(direct) > 1e-12)),
                    "capillary_positive_mass_kg": float(np.sum(cg)),
                    "capillary_negative_mass_kg": float(np.sum(cl)),
                    "capillary_net_mass_kg": float(np.sum(cap_delta)),
                    "capillary_changed_cells": int(np.count_nonzero(np.abs(cap_delta) > 1e-12)),
                })
                audit.current_time = accepted_time
                audit.pending_direct = None
                return result
            mod.conservative_capillary_mass_redistribution = wrapped_capillary

        return mod

    return instrumented_load


def find_single(path: Path, pattern: str) -> Path:
    items = list(path.glob(pattern))
    if len(items) != 1:
        raise GateError(f"expected_one_file:{path}:{pattern}:{len(items)}")
    return items[0]


def seed_shadow_drive(real_drive: Path, shadow_drive: Path) -> None:
    for rel in SEED_RELS:
        src = real_drive / rel
        dst = shadow_drive / rel
        if not src.is_dir():
            raise GateError(f"missing_seed_directory:{src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(src, dst, target_is_directory=True)


def replay_segment(root: Path, real_drive: Path, shadow_drive: Path, audit: AuditState,
                   label: str, runner_file: str, expected_blob: str, log_dir: Path) -> None:
    path = root / runner_file
    if git_blob_sha(path, root) != expected_blob:
        raise GateError(f"replay_runner_blob_mismatch:{runner_file}")
    runner = load_module(path, f"postv16_d2r1_{label.lower()}")
    audit.segment = label
    audit.segment_epoch_start = len(audit.epoch_rows)
    audit.segment_step_start = len(audit.step_rows)
    audit.current_time = float(runner.EXPECTED_PARENT_TIME_DAYS)
    runner.load_module = make_instrumented_loader(runner, audit)

    log_path = log_dir / f"{label}_authoritative_shadow_replay.log"
    with log_path.open("w", encoding="utf-8") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        rc = runner.main(root, shadow_drive)
    if rc != 0:
        raise GateError(f"authoritative_shadow_replay_failed:{label}:{rc}:{log_path}")

    shadow_out = shadow_drive / runner.OUT_REL
    real_out = real_drive / runner.OUT_REL
    for name in [runner.OBSERVATION_STATE_NAME, runner.RESTART_STATE_NAME]:
        sp = shadow_out / name; rp = real_out / name
        if not sp.is_file() or not rp.is_file():
            raise GateError(f"missing_replay_or_authoritative_state:{label}:{name}")
        if sha256_file(sp) != sha256_file(rp):
            raise GateError(f"shadow_state_not_exact:{label}:{name}:{sha256_file(sp)}:{sha256_file(rp)}")

    accepted_csv = find_single(shadow_out, "*Accepted_Transitions.csv")
    refresh_csv = find_single(shadow_out, "*Flow_Refreshes.csv")
    with accepted_csv.open(newline="", encoding="utf-8") as f:
        accepted = list(csv.DictReader(f))
    with refresh_csv.open(newline="", encoding="utf-8") as f:
        refresh = list(csv.DictReader(f))

    local_steps = audit.step_rows[audit.segment_step_start:]
    local_epochs = audit.epoch_rows[audit.segment_epoch_start:]
    if len(local_steps) != len(accepted):
        raise GateError(f"instrumented_step_count_mismatch:{label}:{len(local_steps)}:{len(accepted)}")
    if len(local_epochs) != len(refresh):
        raise GateError(f"instrumented_refresh_count_mismatch:{label}:{len(local_epochs)}:{len(refresh)}")

    for rec, auth in zip(local_steps, accepted):
        rec["accepted_step_index"] = int(auth["accepted_step_index"])
        rec["parent_time_days"] = float(auth["parent_time_days"])
        rec["accepted_time_days"] = float(auth["accepted_time_days"])
        rec["accepted_dt_days"] = float(auth["accepted_dt_days"])
        rec["stored_CO2_mass_kg"] = float(auth["stored_CO2_mass_kg"])
        rec["producer_CO2_gas_cut"] = float(auth["producer_CO2_gas_cut"])
    for rec, auth in zip(local_epochs, refresh):
        rec["trigger"] = auth["trigger"]
        rec["refresh_index_segment"] = int(auth["refresh_index"])

    obs_state = load_npz(shadow_out / runner.OBSERVATION_STATE_NAME)
    day = float(runner.TARGET_DAY)
    audit.observation_snapshots[day] = {
        "support": audit.cumulative_support.copy(),
        "direct_gain": audit.direct_gain_kg.copy(),
        "direct_loss": audit.direct_loss_kg.copy(),
        "cap_gain": audit.cap_gain_kg.copy(),
        "cap_loss": audit.cap_loss_kg.copy(),
        "sg": state_sg(obs_state),
    }
    audit.segment_rows.append({
        "segment": label,
        "start_day": float(runner.EXPECTED_PARENT_TIME_DAYS),
        "target_day": day,
        "accepted_transitions": len(local_steps),
        "flow_refreshes": len(local_epochs),
        "cumulative_supported_cells": int(np.count_nonzero(audit.cumulative_support)),
        "cumulative_supported_fraction": float(np.mean(audit.cumulative_support)),
        "shadow_observation_sha256": sha256_file(shadow_out / runner.OBSERVATION_STATE_NAME),
        "authoritative_observation_sha256": sha256_file(real_out / runner.OBSERVATION_STATE_NAME),
        "shadow_restart_sha256": sha256_file(shadow_out / runner.RESTART_STATE_NAME),
        "authoritative_restart_sha256": sha256_file(real_out / runner.RESTART_STATE_NAME),
    })


def self_test() -> None:
    if EXPECTED_GRID != (15, 50, 50): raise RuntimeError("grid")
    if POROSITY != 0.20: raise RuntimeError("porosity")
    if PRODUCTION_START_DAY <= 60.0 or PRODUCTION_START_DAY >= 100.0: raise RuntimeError("start")
    if len(REPLAY_RUNNERS) != 7: raise RuntimeError("segments")
    if REPLAY_RUNNERS[-1][0] != "E47_1000D": raise RuntimeError("terminal")
    print("PAD-Stream POSTV16-D2R1 production-epoch/capillary attribution self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve(); drive = drive_root.resolve()
    out = drive / OUT_REL; blocked = drive / BLOCKED_REL
    gates: dict[str, dict[str, Any]] = {}; stage = "start"
    def gate(name: str, ok: Any, detail: Any = "") -> None:
        passed = bool(ok); gates[name] = {"passed": passed, "detail": str(detail)}
        if not passed: raise GateError(name)

    try:
        print("\n" + "=" * 164)
        print("PAD-Stream POSTV16-D2R1 — Production-Era Full Flow-Epoch Sweep / Integrated Capillary Attribution Audit")
        print("=" * 164)
        print("Release                    :", RELEASE_ID)
        print("Replay window              : 69.88346704782309 d -> 1000 d")
        print("Replay mode                : deterministic shadow replay of frozen authoritative production runners")
        print("Accepted V16 mutation      : none")
        print("Frozen porosity            : 0.20 constant; no variable-porosity sensitivity")
        print("Scope caveat               : pre-69.883467 d history is inherited, not replayed here")

        stage = "source_binding"
        bindings = [(D2_RUNNER, D2_RUNNER_BLOB), (R2_RUNNER, R2_BLOB), (E37A_RUNNER, E37A_BLOB),
                    (R3R5_RUNNER, R3R5_BLOB), (R3R4R1_RUNNER, R3R4R1_BLOB), (R3R8_RUNNER, R3R8_BLOB)]
        bindings += [(fn, blob) for _, fn, blob in REPLAY_RUNNERS]
        for fn, expected in bindings:
            p = root / fn; gate(f"source_exists_{fn}", p.is_file(), p)
            actual = git_blob_sha(p, root); gate(f"source_blob_{fn}", actual == expected, actual)

        stage = "D2_authority"
        d2s = drive / D2_REL / "PAD_Stream_POSTV16_D2_Summary.json"
        d2c = drive / D2_REL / "POSTV16_D2_Final_Closure.json"
        gate("D2_summary_exists", d2s.is_file(), d2s); gate("D2_closure_exists", d2c.is_file(), d2c)
        ds = load_json(d2s); dc = load_json(d2c)
        gate("D2_status_exact", ds.get("status") == "POSTV16_STREAMLINE_TO_GRID_CO2_SATURATION_ATTRIBUTION_AUDIT_COMPLETED", ds.get("status"))
        gate("D2_all_gates_passed", dc.get("all_gates_passed") is True)
        gate("D2_constant_porosity", float(ds.get("frozen_porosity")) == POROSITY, ds.get("frozen_porosity"))
        gate("D2_no_variable_porosity", ds.get("variable_porosity_sensitivity_executed") is False)

        if out.exists() and any(out.iterdir()):
            raise GateError("D2R1_output_directory_not_empty")
        out.mkdir(parents=True, exist_ok=True)
        log_dir = out / "shadow_replay_logs"; log_dir.mkdir(parents=True, exist_ok=True)

        stage = "load_physics"
        physics = load_module(root / R2_RUNNER, "postv16_d2r1_physics")

        stage = "shadow_drive_seed"
        with tempfile.TemporaryDirectory(prefix="PAD_STREAM_POSTV16_D2R1_") as tmp:
            shadow_drive = Path(tmp) / "PAD_Stream_Compute"; shadow_drive.mkdir(parents=True, exist_ok=True)
            seed_shadow_drive(drive, shadow_drive)
            # Starting authoritative production parent is the R3R1 diagnostic state.
            r3r4 = load_module(root / R3R4R1_RUNNER, "postv16_d2r1_r3r4")
            start_path = drive / r3r4.R3R1_REL / r3r4.R3R1_STATE
            gate("production_start_state_exists", start_path.is_file(), start_path)
            start_state = load_npz(start_path)
            gate("production_start_time_exact", abs(scalar(start_state["physical_time_days"]) - PRODUCTION_START_DAY) <= 1e-12, scalar(start_state["physical_time_days"]))
            start_sg = state_sg(start_state); start_mass = cell_mass_from_state(physics, start_state)
            start_stats = stats(start_sg)

            audit = AuditState()
            for label, fn, blob in REPLAY_RUNNERS:
                stage = f"shadow_replay_{label}"
                print(f"\n[REPLAY] {label}: starting deterministic shadow interval", flush=True)
                replay_segment(root, drive, shadow_drive, audit, label, fn, blob, log_dir)
                seg = audit.segment_rows[-1]
                print(
                    f"[PASS] {label}: {seg['accepted_transitions']} accepted transitions, "
                    f"{seg['flow_refreshes']} refreshes, cumulative path support "
                    f"{100*seg['cumulative_supported_fraction']:.3f}%",
                    flush=True,
                )

            stage = "terminal_authority"
            # E47 authoritative pre-refresh observation.
            terminal_runner = load_module(root / REPLAY_RUNNERS[-1][1], "postv16_d2r1_terminal_runner")
            terminal_path = drive / terminal_runner.OUT_REL / terminal_runner.OBSERVATION_STATE_NAME
            gate("terminal_authoritative_state_exists", terminal_path.is_file(), terminal_path)
            final_state = load_npz(terminal_path); final_sg = state_sg(final_state); final_mass = cell_mass_from_state(physics, final_state)
            final_stats = stats(final_sg)

            gate("pending_direct_cleared", audit.pending_direct is None)
            gate("instrumented_step_count_positive", len(audit.step_rows) > 0, len(audit.step_rows))
            gate("instrumented_epoch_count_positive", len(audit.epoch_rows) > 0, len(audit.epoch_rows))

            stage = "event_times"
            accepted_times = np.asarray([float(r["accepted_time_days"]) for r in audit.step_rows], dtype=np.float64)
            first_direct_day = np.full(EXPECTED_GRID, np.nan, dtype=np.float64)
            first_cap_day = np.full(EXPECTED_GRID, np.nan, dtype=np.float64)
            md = audit.first_direct_event >= 0; mc = audit.first_cap_event >= 0
            first_direct_day[md] = accepted_times[audit.first_direct_event[md]]
            first_cap_day[mc] = accepted_times[audit.first_cap_event[mc]]

            stage = "mass_attribution_closure"
            reconstructed_delta = audit.direct_net_kg + audit.cap_net_kg
            authoritative_delta = final_mass - start_mass
            cell_resid = reconstructed_delta - authoritative_delta
            global_resid = float(np.sum(cell_resid))
            rel_l2 = float(np.linalg.norm(cell_resid.ravel()) / max(np.linalg.norm(authoritative_delta.ravel()), 1e-30))
            mass_scale = max(abs(float(np.sum(final_mass))), 1.0)
            gate("production_window_global_mass_attribution_closure", abs(global_resid) <= 1e-8 * mass_scale, global_resid)
            gate("production_window_cellwise_mass_attribution_relL2", rel_l2 <= 1e-8, rel_l2)
            gate("capillary_global_net_zero", abs(float(np.sum(audit.cap_net_kg))) <= 1e-8 * mass_scale, float(np.sum(audit.cap_net_kg)))
            direct_subset = (audit.direct_gain_kg <= 1e-12) | audit.cumulative_support
            gate("direct_gain_subset_of_epoch_path_support", bool(np.all(direct_subset)), int(np.count_nonzero(~direct_subset)))

            stage = "observation_metrics"
            observation_rows: list[dict[str, Any]] = []
            for day in sorted(audit.observation_snapshots):
                snap = audit.observation_snapshots[day]
                support = np.asarray(snap["support"], bool); sg = np.asarray(snap["sg"], float)
                outside = ~support
                observation_rows.append({
                    "day": day,
                    "cumulative_actual_refresh_supported_cells": int(np.count_nonzero(support)),
                    "cumulative_actual_refresh_supported_fraction": float(np.mean(support)),
                    "mean_sg_inside_support": float(np.mean(sg[support])) if np.any(support) else float("nan"),
                    "mean_sg_outside_support": float(np.mean(sg[outside])) if np.any(outside) else float("nan"),
                    "outside_cells": int(np.count_nonzero(outside)),
                    "outside_fraction_sg_gt_0p01": float(np.mean(sg[outside] > .01)) if np.any(outside) else 0.0,
                    "outside_fraction_sg_gt_0p05": float(np.mean(sg[outside] > .05)) if np.any(outside) else 0.0,
                    "outside_fraction_sg_gt_0p10": float(np.mean(sg[outside] > .10)) if np.any(outside) else 0.0,
                    "cumulative_direct_positive_mass_kg": float(np.sum(snap["direct_gain"])),
                    "cumulative_direct_negative_mass_kg": float(np.sum(snap["direct_loss"])),
                    "cumulative_capillary_positive_turnover_kg": float(np.sum(snap["cap_gain"])),
                    "cumulative_capillary_negative_turnover_kg": float(np.sum(snap["cap_loss"])),
                })

            stage = "cell_table"
            # Coordinates and permeability from D2 terminal table preserve exact dissertation-grid indexing.
            d2cells_path = drive / D2_REL / "POSTV16_D2_Terminal_37500_Cell_CO2_State.csv"
            gate("D2_terminal_cell_table_exists", d2cells_path.is_file(), d2cells_path)
            with d2cells_path.open(newline="", encoding="utf-8") as f:
                d2cells = list(csv.DictReader(f))
            gate("D2_terminal_cell_rows_exact", len(d2cells) == 37500, len(d2cells))

            direct_gain = audit.direct_gain_kg; cap_gain = audit.cap_gain_kg
            dominant = np.full(EXPECTED_GRID, "mixed", dtype="<U16")
            dominant[direct_gain > 1.05 * cap_gain] = "direct"
            dominant[cap_gain > 1.05 * direct_gain] = "capillary"
            no_gain = (direct_gain <= 1e-12) & (cap_gain <= 1e-12)
            dominant[no_gain] = "inherited_only"
            inherited_gt_010 = start_sg > .10

            cell_rows: list[dict[str, Any]] = []
            for row in d2cells:
                k = int(row["k"]); j = int(row["j"]); i = int(row["i"])
                cell_rows.append({
                    "k": k, "j": j, "i": i, "physical_layer": int(row["physical_layer"]),
                    "x_ft": float(row["x_ft"]), "y_ft": float(row["y_ft"]), "depth_ft": float(row["depth_ft"]),
                    "permeability_md": float(row["permeability_md"]), "frozen_porosity": POROSITY,
                    "production_start_sg_69p883d": float(start_sg[k,j,i]),
                    "terminal_sg_1000d": float(final_sg[k,j,i]),
                    "production_start_cell_co2_mass_kg": float(start_mass[k,j,i]),
                    "terminal_cell_co2_mass_kg": float(final_mass[k,j,i]),
                    "ever_supported_by_production_refresh_streamline": bool(audit.cumulative_support[k,j,i]),
                    "first_production_path_support_day": float(audit.first_path_day[k,j,i]) if np.isfinite(audit.first_path_day[k,j,i]) else "",
                    "first_direct_mapback_gain_day": float(first_direct_day[k,j,i]) if np.isfinite(first_direct_day[k,j,i]) else "",
                    "first_capillary_gain_day": float(first_cap_day[k,j,i]) if np.isfinite(first_cap_day[k,j,i]) else "",
                    "cumulative_direct_gain_kg": float(audit.direct_gain_kg[k,j,i]),
                    "cumulative_direct_loss_kg": float(audit.direct_loss_kg[k,j,i]),
                    "cumulative_direct_net_kg": float(audit.direct_net_kg[k,j,i]),
                    "cumulative_capillary_gain_kg": float(audit.cap_gain_kg[k,j,i]),
                    "cumulative_capillary_loss_kg": float(audit.cap_loss_kg[k,j,i]),
                    "cumulative_capillary_net_kg": float(audit.cap_net_kg[k,j,i]),
                    "authoritative_mass_change_69p883_to_1000_kg": float(authoritative_delta[k,j,i]),
                    "attribution_residual_kg": float(cell_resid[k,j,i]),
                    "dominant_post69p883_gain_mechanism": str(dominant[k,j,i]),
                    "already_sg_gt_0p10_at_69p883d": bool(inherited_gt_010[k,j,i]),
                })

            immutable_write(out / "POSTV16_D2R1_Production_Flow_Epoch_Coverage.csv", csv_bytes(audit.epoch_rows))
            immutable_write(out / "POSTV16_D2R1_Accepted_Step_Mass_Attribution.csv", csv_bytes(audit.step_rows))
            immutable_write(out / "POSTV16_D2R1_Observation_Attribution.csv", csv_bytes(observation_rows))
            immutable_write(out / "POSTV16_D2R1_Replay_Segment_Closure.csv", csv_bytes(audit.segment_rows))
            immutable_write(out / "POSTV16_D2R1_Terminal_37500_Cell_Attribution.csv", csv_bytes(cell_rows))
            immutable_write(out / "POSTV16_D2R1_Attribution_Arrays.npz", deterministic_npz_bytes({
                "production_start_sg": start_sg,
                "terminal_sg": final_sg,
                "cumulative_production_epoch_support": audit.cumulative_support.astype(np.uint8),
                "first_path_support_day": audit.first_path_day,
                "first_direct_gain_day": first_direct_day,
                "first_capillary_gain_day": first_cap_day,
                "cumulative_direct_gain_kg": audit.direct_gain_kg,
                "cumulative_direct_loss_kg": audit.direct_loss_kg,
                "cumulative_direct_net_kg": audit.direct_net_kg,
                "cumulative_capillary_gain_kg": audit.cap_gain_kg,
                "cumulative_capillary_loss_kg": audit.cap_loss_kg,
                "cumulative_capillary_net_kg": audit.cap_net_kg,
                "authoritative_cell_mass_change_kg": authoritative_delta,
                "attribution_residual_kg": cell_resid,
            }))

            stage = "figures"
            rendered: list[dict[str, Any]] = []
            # F1 exact production refresh coverage.
            fig, ax = plt.subplots(figsize=(9.5, 6.2))
            ax.plot([r["physical_time_days"] for r in audit.epoch_rows], [100*r["cumulative_supported_fraction"] for r in audit.epoch_rows], linewidth=1.6)
            ax.scatter([r["physical_time_days"] for r in audit.epoch_rows], [100*r["cumulative_supported_fraction"] for r in audit.epoch_rows], s=8)
            ax.set_xlabel("Physical time, days"); ax.set_ylabel("Cumulative cells intersected by production-era flow epochs, %")
            ax.set_title("D2R1-01 — Exact production refresh-epoch cumulative Pollock support")
            ax.grid(alpha=.25); rendered += save_figure(fig, out, "D2R1_01_Exact_Production_Epoch_Cumulative_Streamline_Support")

            # F2 first path contact layer 8.
            fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), constrained_layout=True)
            im = axes[0].imshow(audit.first_path_day[7], origin="lower", extent=[0,1000,0,1000])
            axes[0].set_title("Layer 8 first production-era path support day"); fig.colorbar(im, ax=axes[0], label="day")
            im2 = axes[1].imshow(audit.cumulative_support[7], origin="lower", extent=[0,1000,0,1000], vmin=0, vmax=1)
            axes[1].set_title("Layer 8 ever supported by production refresh streamline")
            for ax in axes: ax.set_xlabel("X, ft"); ax.set_ylabel("Y, ft")
            fig.suptitle("D2R1-02 — When did refreshed streamline geometry first reach each cell?")
            rendered += save_figure(fig, out, "D2R1_02_First_Path_Support_Day")

            # F3 direct vs capillary gross gains.
            fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
            a = np.log10(audit.direct_gain_kg[7] + 1e-6); b = np.log10(audit.cap_gain_kg[7] + 1e-6)
            im0=axes[0].imshow(a,origin="lower",extent=[0,1000,0,1000]); fig.colorbar(im0,ax=axes[0],label="log10 cumulative direct gain kg")
            im1=axes[1].imshow(b,origin="lower",extent=[0,1000,0,1000]); fig.colorbar(im1,ax=axes[1],label="log10 cumulative capillary gain kg")
            ratio=np.log10((audit.cap_gain_kg[7]+1e-6)/(audit.direct_gain_kg[7]+1e-6)); im2=axes[2].imshow(ratio,origin="lower",extent=[0,1000,0,1000]); fig.colorbar(im2,ax=axes[2],label="log10 capillary/direct gross gain")
            for ax in axes: ax.set_xlabel("X, ft"); ax.set_ylabel("Y, ft")
            axes[0].set_title("Direct E37A map-back gain"); axes[1].set_title("Capillary gain turnover"); axes[2].set_title("Gain-mechanism ratio")
            fig.suptitle("D2R1-03 — Integrated production-era cellwise supply mechanisms")
            rendered += save_figure(fig, out, "D2R1_03_Direct_vs_Capillary_Cellwise_Gain")

            # F4 inherited floor vs terminal.
            fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
            im0=axes[0].imshow(start_sg[7],origin="lower",extent=[0,1000,0,1000],vmin=0,vmax=.60); fig.colorbar(im0,ax=axes[0],label="Sg")
            im1=axes[1].imshow(final_sg[7],origin="lower",extent=[0,1000,0,1000],vmin=0,vmax=.60); fig.colorbar(im1,ax=axes[1],label="Sg")
            im2=axes[2].imshow(final_sg[7]-start_sg[7],origin="lower",extent=[0,1000,0,1000]); fig.colorbar(im2,ax=axes[2],label="ΔSg")
            axes[0].set_title("69.883 d inherited state"); axes[1].set_title("1000 d terminal state"); axes[2].set_title("Production-era change")
            for ax in axes: ax.set_xlabel("X, ft"); ax.set_ylabel("Y, ft")
            fig.suptitle("D2R1-04 — Was the domain-wide saturation floor already inherited before the frozen production policy?")
            rendered += save_figure(fig, out, "D2R1_04_Inherited_vs_Production_Era_CO2_Saturation")

            # F5 observation support vs Sg.
            fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), constrained_layout=True)
            axes[0].plot([r["day"] for r in observation_rows], [100*r["cumulative_actual_refresh_supported_fraction"] for r in observation_rows], marker="o")
            axes[0].set_xlabel("Observation day"); axes[0].set_ylabel("Exact replay cumulative support, %"); axes[0].grid(alpha=.25)
            axes[0].set_title("Actual production refresh-epoch path union")
            axes[1].plot([r["day"] for r in observation_rows], [r["mean_sg_inside_support"] for r in observation_rows], marker="o", label="inside support")
            axes[1].plot([r["day"] for r in observation_rows], [r["mean_sg_outside_support"] for r in observation_rows], marker="s", label="outside support")
            axes[1].set_xlabel("Observation day"); axes[1].set_ylabel("Mean Sg"); axes[1].grid(alpha=.25); axes[1].legend()
            axes[1].set_title("Saturation inside vs outside exact production path union")
            fig.suptitle("D2R1-05 — Production-era sweep attribution through frozen observations")
            rendered += save_figure(fig, out, "D2R1_05_Observation_Support_vs_Saturation")

            # F6 global mass mechanism closure.
            fig, ax = plt.subplots(figsize=(9.5,6.2))
            times=np.asarray([r["accepted_time_days"] for r in audit.step_rows]);
            direct=np.cumsum([r["direct_net_mass_kg"] for r in audit.step_rows]); cap=np.cumsum([r["capillary_net_mass_kg"] for r in audit.step_rows])
            ax.plot(times,direct,label="cumulative direct map-back net mass")
            ax.plot(times,cap,label="cumulative capillary net mass")
            ax.plot(times,direct+cap,label="combined attributed storage change",linewidth=2)
            ax.set_xlabel("Physical time, days"); ax.set_ylabel("Cumulative component-mass change, kg"); ax.grid(alpha=.25); ax.legend()
            ax.set_title("D2R1-06 — Global production-era mass attribution closure")
            rendered += save_figure(fig, out, "D2R1_06_Production_Era_Mass_Attribution_Closure")
            gate("rendered_file_count_exact", len(rendered)==12, len(rendered))
            gate("rendered_files_nonempty", all(r["bytes"]>0 for r in rendered))

            stage = "closeout"
            terminal_support_fraction = float(np.mean(audit.cumulative_support))
            start_floor_fraction = float(np.mean(start_sg > .10))
            terminal_outside = ~audit.cumulative_support
            terminal_outside_fraction = float(np.mean(terminal_outside))
            outside_start_gt_010 = float(np.mean(start_sg[terminal_outside] > .10)) if np.any(terminal_outside) else 0.0
            outside_final_mean = float(np.mean(final_sg[terminal_outside])) if np.any(terminal_outside) else float("nan")
            outside_cap_gain = float(np.sum(audit.cap_gain_kg[terminal_outside])) if np.any(terminal_outside) else 0.0
            outside_direct_gain = float(np.sum(audit.direct_gain_kg[terminal_outside])) if np.any(terminal_outside) else 0.0
            early_time_needed = bool(start_floor_fraction >= 0.95)

            theory = {
                "streamline_chain": "K->pressure->Darcy flux->refreshed Pollock paths->TOF/control-volume transport->E37A local component-mass deposition->pairwise no-flow Cartesian capillary redistribution->grid Sg",
                "replay_window_days": [PRODUCTION_START_DAY, PRODUCTION_END_DAY],
                "why_window_starts_at_69p883": "This is the exact authoritative parent state used by the frozen repaired production rollout. Earlier V16 development history is not silently reconstructed by this audit.",
                "exact_refresh_epoch_replay": True,
                "accepted_transition_shadow_replay": True,
                "porosity": POROSITY,
                "variable_porosity_used": False,
                "no_accepted_state_mutation": True,
                "interpretation_rule": "If at least 95% of cells already have Sg>0.10 at 69.883d, a pre-production early-time attribution audit is required before using variable porosity as an explanation for the domain-wide floor.",
            }
            summary = {
                "milestone": MILESTONE, "status": STATUS, "release_id": RELEASE_ID,
                "V16_frozen": True, "accepted_state_mutation": False,
                "production_replay_start_day": PRODUCTION_START_DAY, "production_replay_end_day": PRODUCTION_END_DAY,
                "frozen_porosity": POROSITY, "variable_porosity_sensitivity_executed": False,
                "production_start_sg_stats": start_stats, "terminal_sg_stats": final_stats,
                "production_start_fraction_cells_sg_gt_0p10": start_floor_fraction,
                "exact_production_flow_refresh_epochs_replayed": len(audit.epoch_rows),
                "exact_production_accepted_transitions_replayed": len(audit.step_rows),
                "terminal_cumulative_production_epoch_support_fraction": terminal_support_fraction,
                "terminal_cells_outside_production_epoch_support_fraction": terminal_outside_fraction,
                "outside_support_fraction_already_sg_gt_0p10_at_69p883d": outside_start_gt_010,
                "terminal_mean_sg_outside_production_epoch_support": outside_final_mean,
                "outside_support_cumulative_direct_gain_kg": outside_direct_gain,
                "outside_support_cumulative_capillary_gain_kg": outside_cap_gain,
                "production_window_global_mass_attribution_residual_kg": global_resid,
                "production_window_cellwise_mass_attribution_relative_L2": rel_l2,
                "production_window_capillary_net_mass_kg": float(np.sum(audit.cap_net_kg)),
                "early_time_pre69p883_attribution_required_before_porosity_decision": early_time_needed,
                "terminal_cellwise_rows": len(cell_rows), "next": NEXT,
            }
            closure = {
                "milestone": MILESTONE, "status": STATUS,
                "all_gates_passed": all(v["passed"] for v in gates.values()), "gate_count": len(gates),
                "authoritative_production_intervals_shadow_replayed_exact": True,
                "observation_and_restart_state_hashes_exact": True,
                "all_actual_production_refresh_epochs_in_replayed_window_instrumented": True,
                "integrated_direct_mapback_and_capillary_cell_mass_attribution_completed": True,
                "full_37500_cell_attribution_exported": True,
                "accepted_simulation_state_modified": False, "V16_release_modified": False,
                "variable_porosity_used": False,
                "pre69p883_history_not_replayed": True,
                "early_time_pre69p883_attribution_required_before_porosity_decision": early_time_needed,
                "next": NEXT,
            }
            immutable_write(out / "POSTV16_D2R1_Theory_Contract.json", json_bytes(theory))
            immutable_write(out / "PAD_Stream_POSTV16_D2R1_Summary.json", json_bytes(summary))
            immutable_write(out / "POSTV16_D2R1_Final_Gate_Matrix.csv", csv_bytes([{"gate":k,**v} for k,v in gates.items()]))
            immutable_write(out / "POSTV16_D2R1_Final_Closure.json", json_bytes(closure))

            manifest=[]
            for p in sorted(out.rglob("*")):
                if p.is_file() and p.name != "POSTV16_D2R1_Artifact_Manifest.csv":
                    manifest.append({"file": str(p.relative_to(out)), "sha256": sha256_file(p), "bytes": p.stat().st_size})
            immutable_write(out / "POSTV16_D2R1_Artifact_Manifest.csv", csv_bytes(manifest))

            print("\n" + "="*164)
            print("PAD-Stream POSTV16-D2R1: PASS")
            print("="*164)
            print(f"{'Status':78}: {STATUS}")
            print(f"{'Production start Sg min / mean / median / max':78}: {start_stats['min']:.6f} / {start_stats['mean']:.6f} / {start_stats['p50']:.6f} / {start_stats['max']:.6f}")
            print(f"{'Production start cells with Sg > 0.10':78}: {100*start_floor_fraction:.3f}%")
            print(f"{'Exact production flow refresh epochs replayed':78}: {len(audit.epoch_rows)}")
            print(f"{'Exact production accepted transitions replayed':78}: {len(audit.step_rows)}")
            print(f"{'1000d cumulative production-epoch streamline support':78}: {100*terminal_support_fraction:.3f}%")
            print(f"{'1000d cells outside production-era path union':78}: {100*terminal_outside_fraction:.3f}%")
            print(f"{'Outside-path cells already Sg>0.10 at 69.883d':78}: {100*outside_start_gt_010:.3f}%")
            print(f"{'Terminal mean Sg outside production-era path union':78}: {outside_final_mean:.6f}")
            print(f"{'Outside-path cumulative direct gain':78}: {outside_direct_gain:.6e} kg")
            print(f"{'Outside-path cumulative capillary gain':78}: {outside_cap_gain:.6e} kg")
            print(f"{'Global mass attribution residual':78}: {global_resid:.12e} kg")
            print(f"{'Cellwise attribution relative L2':78}: {rel_l2:.12e}")
            print(f"{'Integrated capillary net mass':78}: {float(np.sum(audit.cap_net_kg)):.12e} kg")
            print(f"{'Variable porosity sensitivity executed':78}: False")
            print(f"{'Pre-69.883d attribution required before porosity decision':78}: {early_time_needed}")
            print(f"{'Accepted simulation state modified':78}: False")
            print(f"{'V16 release modified':78}: False")
            print(f"{'Next':78}: {NEXT}")
            return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {"milestone":MILESTONE,"status":"POSTV16_D2R1_BLOCKED","failed_stage":stage,"exception":repr(exc),"gates":gates}
        p = blocked / "POSTV16_D2R1_Blocked_Report.json"; p.write_bytes(json_bytes(report))
        print("\n" + "="*164); print("PAD-Stream POSTV16-D2R1: BLOCKED"); print("="*164)
        print("Report      :", p); print("Failed stage:", stage); print("Exception   :", repr(exc))
        return 2


def parse_args():
    p=argparse.ArgumentParser(); p.add_argument("--project-root",type=Path,default=Path(".")); p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute")); p.add_argument("--self-test",action="store_true"); return p.parse_args()

if __name__ == "__main__":
    a=parse_args()
    if a.self_test:
        self_test(); raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))

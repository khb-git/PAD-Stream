from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import sys
import zipfile
from collections import Counter
from typing import Any

import numpy as np


MILESTONE = "V16E-41-R3-R1"
STATUS = "R3_ACCEPTED_TRANSITION_BUDGET_CAPACITY_REGIME_AUDITED"
NEXT = (
    "V16E-41-R3-R2 - Stage-Appropriate Long-Horizon Progress Repair Design "
    "(only after R3-R1 interpretation)"
)

R3_RUNNER = (
    "PAD_Stream_V16E41R3_Capacity_Aware_Production_100D_"
    "Legacy_Regression.py"
)
R3_RUNNER_SHA256 = (
    "992dcaee7661f3ff98b03cc1f8cbed0fd0ada29e109ee0d06293f5a2f8514939"
)

EXPECTED_R3_BLOCK_STATUS = (
    "CAPACITY_AWARE_PRODUCTION_100D_LEGACY_REGRESSION_BLOCKED"
)
EXPECTED_R3_FAILED_STAGE = "capacity_aware_1475_to_100d_rollout"
EXPECTED_R3_EXCEPTION = "accepted_transition_budget_exceeded:2500"
EXPECTED_ACCEPTED_TRANSITIONS = 2500

R2_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R2_CAPACITY_AWARE_CONSERVATIVE_MAPBACK_TIMESTEP_REPAIR"
)
R2_STATE = (
    "V16E41R2_Accepted_Repaired_SGSim_Runtime_State_Step_1475.npz"
)
R2_STATE_SHA256 = (
    "23d7fb28fa126e4914b8529355a783f321208baecd966b1517f5eb3cd76f7b79"
)
EXPECTED_R2_STEP = 1475
EXPECTED_R2_TIME_DAYS = 69.88219208575286

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R1_ACCEPTED_TRANSITION_BUDGET_CAPACITY_REGIME_AUDIT"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R1_BLOCKED_ACCEPTED_TRANSITION_BUDGET_CAPACITY_REGIME_AUDIT"
)

PARTIAL_STATE_NAME = (
    "V16E41R3R1_Diagnostic_Partial_Runtime_State_After_2500_Accepted_"
    "Transitions.npz"
)


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(
        outer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(
                f"{key}.npy",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists():
            if p.read_bytes() != data:
                raise GateError(f"existing_output_differs:{name}")
        else:
            p.write_bytes(data)


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


def int_scalar(a: Any) -> int:
    return int(np.asarray(a).reshape(()))


def safe_float(v: Any, default: float = float("nan")) -> float:
    try:
        return float(v)
    except Exception:
        return default


def self_test() -> None:
    dts = np.asarray([0.05, 0.04, 0.03, 0.02], dtype=np.float64)
    if not (
        float(np.min(dts)) == 0.02
        and float(np.max(dts)) == 0.05
        and float(np.median(dts)) == 0.035
    ):
        raise RuntimeError("self_test_dt_statistics")

    start = 69.0
    end = start + float(np.sum(dts))
    if not (end > start):
        raise RuntimeError("self_test_time_progress")

    print(
        "PAD-Stream V16E-41-R3-R1 accepted-transition budget / "
        "capacity-regime audit self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}
    failed_stage: str | None = None

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {"passed": bool(passed), "detail": str(detail)}
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "=" * 148)
        print(
            "PAD-Stream V16E-41-R3-R1 — Accepted-Transition Budget / "
            "Capacity-Limited Regime Audit"
        )
        print("=" * 148)
        print("ROLE          : diagnostic only")
        print("SOURCE        : exact published V16E-41-R3 runner")
        print("REPAIR        : none")
        print("BUDGET        : unchanged at 2500 accepted transitions")
        print("100-DAY CLAIM : none")
        print("REGRESSION    : not started")
        print(
            "OBJECTIVE     : capture exact partial trajectory at the R3 "
            "budget boundary and quantify timestep/limiter behavior"
        )

        failed_stage = "source_and_restart_binding"

        r3_path = root / R3_RUNNER
        gate("R3_runner_exists", r3_path.is_file(), r3_path)
        r3_sha_before = sha256_file(r3_path)
        gate(
            "R3_runner_SHA_exact",
            r3_sha_before == R3_RUNNER_SHA256,
            r3_sha_before,
        )

        r2_state_path = drive / R2_REL / R2_STATE
        gate("R2_restart_exists", r2_state_path.is_file(), r2_state_path)
        r2_sha_before = sha256_file(r2_state_path)
        gate(
            "R2_restart_SHA_exact",
            r2_sha_before == R2_STATE_SHA256,
            r2_sha_before,
        )

        r3 = load_module(r3_path, "pad_stream_v16e41r3r1_source_r3")
        gate(
            "R3_transition_budget_exact",
            int(r3.MAX_ACCEPTED_TRANSITIONS) == EXPECTED_ACCEPTED_TRANSITIONS,
            r3.MAX_ACCEPTED_TRANSITIONS,
        )

        capture: dict[str, Any] = {}

        def global_trace(frame, event, arg):
            if (
                event == "call"
                and frame.f_code.co_name == "main"
                and Path(frame.f_code.co_filename).resolve() == r3_path
            ):
                return local_trace
            return None

        def local_trace(frame, event, arg):
            if event == "exception":
                exc_type, exc_value, _tb = arg
                if EXPECTED_R3_EXCEPTION in str(exc_value):
                    loc = frame.f_locals

                    current = loc.get("current")
                    if isinstance(current, dict):
                        capture["current"] = {
                            k: np.asarray(v).copy()
                            for k, v in current.items()
                        }

                    capture["rollout_rows"] = [
                        dict(r)
                        for r in loc.get("rollout_rows", [])
                    ]
                    capture["controller_rows"] = [
                        dict(r)
                        for r in loc.get("controller_rows", [])
                    ]
                    capture["rejection_rows"] = [
                        dict(r)
                        for r in loc.get("rejection_rows", [])
                    ]
                    for key in [
                        "accepted_transitions",
                        "native_rejected_trials",
                        "capacity_adjustments_total",
                        "capacity_limited_steps",
                        "max_capacity_adjustments_one_step",
                        "post_preflight_capacity_gate_failures",
                        "nominal_dt_days",
                        "restart_time",
                        "restart_step",
                        "current_time",
                        "target_step",
                    ]:
                        if key in loc:
                            capture[key] = loc[key]
                    capture["exception_repr"] = repr(exc_value)
            return local_trace

        failed_stage = "exact_R3_budget_boundary_replay"

        old_trace = sys.gettrace()
        sys.settrace(global_trace)
        try:
            rc = int(r3.main(root, drive))
        finally:
            sys.settrace(old_trace)

        gate("R3_replay_returned_blocked", rc == 2, rc)
        gate(
            "budget_boundary_exception_captured",
            EXPECTED_R3_EXCEPTION in str(capture.get("exception_repr", "")),
            capture.get("exception_repr"),
        )

        current = capture.get("current")
        rollout_rows = capture.get("rollout_rows", [])
        controller_rows = capture.get("controller_rows", [])
        rejection_rows = capture.get("rejection_rows", [])

        gate("captured_partial_state", isinstance(current, dict), type(current))
        gate(
            "captured_accepted_transition_count_exact",
            int(capture.get("accepted_transitions", -1))
            == EXPECTED_ACCEPTED_TRANSITIONS
            == len(rollout_rows),
            (
                capture.get("accepted_transitions"),
                len(rollout_rows),
            ),
        )

        blocked_dir = drive / r3.BLOCKED_REL
        blocked_reports = (
            sorted(
                blocked_dir.glob("V16E41R3_Blocked_100D_Rollout_Regression*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if blocked_dir.exists()
            else []
        )
        gate("R3_blocked_report_exists", bool(blocked_reports))
        r3_blocked_path = blocked_reports[0]
        r3_blocked = json.loads(r3_blocked_path.read_text(encoding="utf-8"))
        gate(
            "R3_block_status_exact",
            r3_blocked.get("status") == EXPECTED_R3_BLOCK_STATUS,
            r3_blocked.get("status"),
        )
        gate(
            "R3_block_failed_stage_exact",
            r3_blocked.get("failed_stage") == EXPECTED_R3_FAILED_STAGE,
            r3_blocked.get("failed_stage"),
        )
        gate(
            "R3_block_exception_exact",
            EXPECTED_R3_EXCEPTION in str(r3_blocked.get("exception", "")),
            r3_blocked.get("exception"),
        )

        failed_stage = "trajectory_statistics"

        final_time = scalar(current["physical_time_days"])
        final_step = int_scalar(current["accepted_step_index"])
        final_stored = scalar(current["stored_co2_mass_current_kg"])
        final_cum_resid = scalar(current["cumulative_mass_residual_kg"])
        final_cut = scalar(current["current_producer_co2_gas_cut"])

        gate(
            "partial_state_still_before_100d",
            final_time < float(r3.TARGET_OBSERVATION_DAY),
            final_time,
        )
        gate(
            "partial_step_matches_accepted_count",
            final_step == EXPECTED_R2_STEP + EXPECTED_ACCEPTED_TRANSITIONS,
            final_step,
        )
        gate(
            "partial_state_not_100d_canonical",
            not bool(np.asarray(
                current["V16E41_canonical_100d_observation_state"]
            ).reshape(())),
        )

        accepted_dts = np.asarray(
            [float(r["accepted_dt_days"]) for r in rollout_rows],
            dtype=np.float64,
        )
        cap_adj_per_step = np.asarray(
            [int(r.get("capacity_adjustments", 0)) for r in rollout_rows],
            dtype=np.int64,
        )
        native_retry_per_step = np.asarray(
            [int(r.get("native_retry_count", 0)) for r in rollout_rows],
            dtype=np.int64,
        )

        gate(
            "all_accepted_dt_positive_finite",
            bool(np.all(np.isfinite(accepted_dts)))
            and bool(np.all(accepted_dts > 0.0)),
            (
                float(np.min(accepted_dts)),
                float(np.max(accepted_dts)),
            ),
        )

        capacity_reject_rows = [
            r
            for r in controller_rows
            if r.get("controller_action")
            == "REJECT_AND_RETRY_AT_CAPACITY_BOUND"
        ]
        limiter_counter: Counter[tuple[int, int, int]] = Counter()
        for row in capacity_reject_rows:
            cell = tuple(
                int(x)
                for x in row.get(
                    "upper_limiting_cell_zero_based",
                    [-1, -1, -1],
                )
            )
            limiter_counter[cell] += 1

        window_rows: list[dict[str, Any]] = []
        window = 100
        for start in range(0, len(rollout_rows), window):
            subset = rollout_rows[start : start + window]
            dts = np.asarray(
                [float(r["accepted_dt_days"]) for r in subset],
                dtype=np.float64,
            )
            first = subset[0]
            last = subset[-1]
            window_rows.append(
                {
                    "accepted_transition_start_1based": start + 1,
                    "accepted_transition_end_1based": start + len(subset),
                    "step_start": int(first["accepted_step_index"]),
                    "step_end": int(last["accepted_step_index"]),
                    "time_start_days": float(first["parent_time_days"]),
                    "time_end_days": float(last["accepted_time_days"]),
                    "time_gain_days": (
                        float(last["accepted_time_days"])
                        - float(first["parent_time_days"])
                    ),
                    "dt_min_days": float(np.min(dts)),
                    "dt_median_days": float(np.median(dts)),
                    "dt_mean_days": float(np.mean(dts)),
                    "dt_max_days": float(np.max(dts)),
                    "capacity_limited_steps": int(
                        sum(int(r.get("capacity_adjustments", 0)) > 0 for r in subset)
                    ),
                    "capacity_adjustments": int(
                        sum(int(r.get("capacity_adjustments", 0)) for r in subset)
                    ),
                    "native_retry_trials": int(
                        sum(int(r.get("native_retry_count", 0)) for r in subset)
                    ),
                }
            )

        first500 = accepted_dts[:500]
        last500 = accepted_dts[-500:]
        first100 = accepted_dts[:100]
        last100 = accepted_dts[-100:]

        elapsed_days = final_time - EXPECTED_R2_TIME_DAYS
        remaining_days = float(r3.TARGET_OBSERVATION_DAY) - final_time
        progress_fraction = (
            elapsed_days
            / (float(r3.TARGET_OBSERVATION_DAY) - EXPECTED_R2_TIME_DAYS)
        )

        last500_median = float(np.median(last500))
        last500_mean = float(np.mean(last500))
        last500_gain = float(np.sum(last500))
        projected_more_by_last500_median = (
            float(remaining_days / last500_median)
            if last500_median > 0.0
            else float("inf")
        )
        projected_more_by_last500_mean = (
            float(remaining_days / last500_mean)
            if last500_mean > 0.0
            else float("inf")
        )

        limiter_rows = [
            {
                "k_zero_based": cell[0],
                "j_zero_based": cell[1],
                "i_zero_based": cell[2],
                "capacity_adjustment_count": int(count),
                "fraction_of_all_capacity_adjustments": (
                    float(count / len(capacity_reject_rows))
                    if capacity_reject_rows
                    else 0.0
                ),
            }
            for cell, count in limiter_counter.most_common()
        ]

        last100_rows = [dict(r) for r in rollout_rows[-100:]]
        last100_rejections = [
            dict(r)
            for r in rejection_rows
            if int(r.get("target_step", -1))
            >= int(last100_rows[0]["accepted_step_index"])
        ]

        partial_state_bytes = deterministic_npz_bytes(current)
        partial_state_sha = hashlib.sha256(partial_state_bytes).hexdigest()

        classification = (
            "PERSISTENT_SMALL_TIMESTEP_CAPACITY_LIMITED_REGIME"
            if (
                progress_fraction < 0.50
                and last500_median < 0.25 * float(capture["nominal_dt_days"])
            )
            else "TRANSITION_BUDGET_INSUFFICIENT_WITH_MEANINGFUL_PROGRESS"
        )

        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "diagnostic_only": True,
            "solver_repair_performed": False,
            "transition_budget_modified": False,
            "R3_source_runner_sha256": r3_sha_before,
            "R3_blocked_report_sha256": sha256_file(r3_blocked_path),
            "R2_restart_sha256": r2_sha_before,
            "restart_step_index": EXPECTED_R2_STEP,
            "restart_time_days": EXPECTED_R2_TIME_DAYS,
            "accepted_transition_budget": EXPECTED_ACCEPTED_TRANSITIONS,
            "accepted_transitions_captured": len(rollout_rows),
            "partial_final_step_index": final_step,
            "partial_final_time_days": final_time,
            "elapsed_physical_time_days": elapsed_days,
            "remaining_to_100d_days": remaining_days,
            "fraction_of_R2_to_100d_interval_completed": progress_fraction,
            "partial_state_sha256": partial_state_sha,
            "partial_stored_CO2_mass_kg": final_stored,
            "partial_cumulative_mass_residual_kg": final_cum_resid,
            "partial_producer_CO2_gas_cut": final_cut,
            "nominal_dt_days": float(capture["nominal_dt_days"]),
            "accepted_dt_min_days": float(np.min(accepted_dts)),
            "accepted_dt_median_days": float(np.median(accepted_dts)),
            "accepted_dt_mean_days": float(np.mean(accepted_dts)),
            "accepted_dt_max_days": float(np.max(accepted_dts)),
            "first_100_median_dt_days": float(np.median(first100)),
            "last_100_median_dt_days": float(np.median(last100)),
            "first_500_median_dt_days": float(np.median(first500)),
            "last_500_median_dt_days": last500_median,
            "first500_to_last500_median_dt_ratio": (
                float(last500_median / np.median(first500))
                if float(np.median(first500)) > 0.0
                else float("nan")
            ),
            "last_500_time_gain_days": last500_gain,
            "capacity_limited_steps": int(np.sum(cap_adj_per_step > 0)),
            "capacity_limited_step_fraction": float(np.mean(cap_adj_per_step > 0)),
            "capacity_adjustments_total": int(np.sum(cap_adj_per_step)),
            "native_retry_trials_total": int(np.sum(native_retry_per_step)),
            "unique_capacity_limiter_cells": len(limiter_counter),
            "dominant_capacity_limiter_cell_zero_based": (
                list(limiter_counter.most_common(1)[0][0])
                if limiter_counter
                else None
            ),
            "dominant_capacity_limiter_adjustment_count": (
                int(limiter_counter.most_common(1)[0][1])
                if limiter_counter
                else 0
            ),
            "projected_additional_transitions_if_last500_median_dt_held": (
                projected_more_by_last500_median
            ),
            "projected_additional_transitions_if_last500_mean_dt_held": (
                projected_more_by_last500_mean
            ),
            "projection_is_diagnostic_only": True,
            "regime_classification": classification,
            "canonical_100d_state_created": False,
            "legacy_regression_started": False,
            "next_milestone": NEXT,
        }

        closure = {
            "milestone": MILESTONE,
            "status": STATUS,
            "all_audit_gates_passed": all(v["passed"] for v in gates.values()),
            "gate_count": len(gates),
            "diagnostic_only": True,
            "solver_repair_performed": False,
            "transition_budget_modified": False,
            "partial_state_filename": PARTIAL_STATE_NAME,
            "partial_state_sha256": partial_state_sha,
            "canonical_100d_state_created": False,
            "legacy_regression_started": False,
            "R3_source_unmodified": sha256_file(r3_path) == r3_sha_before,
            "R2_restart_unmodified": sha256_file(r2_state_path) == r2_sha_before,
            "next_milestone": NEXT,
        }

        gate(
            "R3_source_unchanged",
            sha256_file(r3_path) == r3_sha_before,
            sha256_file(r3_path),
        )
        gate(
            "R2_restart_unchanged",
            sha256_file(r2_state_path) == r2_sha_before,
            sha256_file(r2_state_path),
        )

        closure["all_audit_gates_passed"] = all(
            v["passed"] for v in gates.values()
        )
        closure["gate_count"] = len(gates)

        files = {
            PARTIAL_STATE_NAME: partial_state_bytes,
            "PAD_Stream_V16E41R3R1_Summary.json": json_bytes(summary),
            "V16E41R3R1_100Step_Window_Trend.csv": csv_bytes(window_rows),
            "V16E41R3R1_Capacity_Limiter_Cell_Counts.csv": csv_bytes(limiter_rows),
            "V16E41R3R1_Last_100_Accepted_Transitions.csv": csv_bytes(last100_rows),
            "V16E41R3R1_Last_100_Step_Rejections.csv": csv_bytes(last100_rejections),
            "V16E41R3R1_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
            "V16E41R3R1_Final_Closure.json": json_bytes(closure),
        }

        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "V16E41R3R1_Artifact_Manifest.csv":
                manifest_rows.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_publish(
            out,
            {
                "V16E41R3R1_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print("\n" + "=" * 148)
        print("PAD-Stream V16E-41-R3-R1: PASS")
        print("=" * 148)
        print(f"{'Status':58}: {STATUS}")
        print(
            f"{'Budget-boundary step / time':58}: "
            f"{final_step} / {final_time:.15g} d"
        )
        print(
            f"{'Elapsed from R2 restart':58}: "
            f"{elapsed_days:.15g} d"
        )
        print(
            f"{'Remaining to 100d':58}: "
            f"{remaining_days:.15g} d"
        )
        print(
            f"{'R2->100d interval completed':58}: "
            f"{100.0 * progress_fraction:.6f}%"
        )
        print(
            f"{'Accepted dt min / median / max':58}: "
            f"{np.min(accepted_dts):.6e} / "
            f"{np.median(accepted_dts):.6e} / "
            f"{np.max(accepted_dts):.6e} d"
        )
        print(
            f"{'First500 / last500 median dt':58}: "
            f"{np.median(first500):.6e} / "
            f"{last500_median:.6e} d"
        )
        print(
            f"{'Capacity-limited steps':58}: "
            f"{int(np.sum(cap_adj_per_step > 0))} / "
            f"{len(rollout_rows)}"
        )
        print(
            f"{'Capacity adjustments total':58}: "
            f"{int(np.sum(cap_adj_per_step))}"
        )
        print(
            f"{'Unique limiter cells':58}: "
            f"{len(limiter_counter)}"
        )
        print(
            f"{'Dominant limiter cell':58}: "
            f"{summary['dominant_capacity_limiter_cell_zero_based']}"
        )
        print(
            f"{'Diagnostic regime classification':58}: "
            f"{classification}"
        )
        print(
            f"{'Partial state SHA-256':58}: "
            f"{partial_state_sha}"
        )
        print(f"{'Output':58}: {out}")
        print(f"{'Next':58}: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "R3_ACCEPTED_TRANSITION_BUDGET_CAPACITY_REGIME_AUDIT_BLOCKED",
            "failed_stage": failed_stage,
            "exception": repr(exc),
            "gates": gates,
        }
        data = json_bytes(report)
        p = blocked / "V16E41R3R1_Blocked_Audit.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "V16E41R3R1_Blocked_Audit_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        p.write_bytes(data)

        print("\n" + "=" * 148)
        print("PAD-Stream V16E-41-R3-R1: BLOCKED")
        print("=" * 148)
        print("Report      :", p)
        print("Failed stage:", failed_stage)
        print("Exception   :", repr(exc))
        return 2


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))

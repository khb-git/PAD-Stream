#!/usr/bin/env python3
"""
PAD-Stream V16D-9
Multi-Case Pollock TOF / 201-Node Transport Coordinate and C7 Metric Construction

Purpose
-------
Construct the canonical Pollock transport-coordinate representation for every
certified V16D Case 0002-0025 streamline, without running FMM/ADV, transport,
or ML.

Authoritative inputs
--------------------
- V16D-8B certified Pollock ensemble artifacts.
- Exact SG5 source-native trajectory fields:
    points_m, times_s, travel_time_s, weight_m3_s, producer
- Frozen C7 coordinate/metric semantics:
    theta = tau / tau_end
    x_D   = s / s_end
    M     = dtheta / dx_D

Important
---------
This milestone does NOT alter streamline geometry, TOF, weights, producer
identity, flow, geology, or case membership. It only resamples each
source-authentic trajectory onto a common 201-node theta grid and constructs
the physical-path metric required by the transformed capillary operator.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_D9_MULTICASE_POLLOCK_201NODE_C7_METRIC"
OUT.mkdir(parents=True, exist_ok=True)

CASE_IDS = [f"V16D_Foundation_Case_{i:04d}" for i in range(2, 26)]
N_THETA = 201
THETA = np.linspace(0.0, 1.0, N_THETA, dtype=np.float64)

# D8B's expected output directory. Search fallback is provenance-safe:
# only files whose names contain the exact case ID are considered.
D8B_DIR_CANDIDATES = [
    ROOT / "output" / "V16_D8B_FULL_CASE0002_0025_SOURCEBOUND_SG5_POLLOCK_ENSEMBLE",
    ROOT / "output" / "V16D8B_FULL_CASE0002_0025_SOURCEBOUND_SG5_POLLOCK_ENSEMBLE",
    ROOT / "output" / "V16D-8B",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def native(v: Any) -> Any:
    if isinstance(v, dict):
        return {str(k): native(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [native(x) for x in v]
    if isinstance(v, np.ndarray):
        return native(v.tolist())
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, Path):
        return str(v)
    return v


def locate_d8b_dir() -> Path:
    for p in D8B_DIR_CANDIDATES:
        if p.exists():
            return p

    candidates = []
    output = ROOT / "output"
    if output.exists():
        for p in output.iterdir():
            if p.is_dir():
                name = p.name.upper()
                if "D8B" in name and "POLLOCK" in name:
                    candidates.append(p)

    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError(
            "Could not locate the V16D-8B output directory. "
            "D9 will not guess or regenerate Pollock data."
        )
    raise RuntimeError(
        "Multiple D8B-like directories found; provenance is ambiguous:\n  "
        + "\n  ".join(str(p) for p in candidates)
    )


def locate_case_artifact(d8b_dir: Path, case_id: str) -> Path:
    matches = []
    for p in d8b_dir.rglob("*.npz"):
        if case_id.lower() in p.name.lower() or case_id.lower() in str(p.parent).lower():
            matches.append(p)

    # Prefer explicit Pollock artifacts if multiple case-associated NPZ files exist.
    pollock = [p for p in matches if "pollock" in p.name.lower()]
    if len(pollock) == 1:
        return pollock[0]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(f"No D8B NPZ artifact found for {case_id}.")
    raise RuntimeError(
        f"Ambiguous D8B artifacts for {case_id}; D9 refuses to select by numerical content:\n  "
        + "\n  ".join(str(p) for p in matches)
    )


def unpack_object_array(a: np.ndarray) -> list[Any]:
    if a.dtype == object:
        return list(a.tolist())
    return list(a)


def first_existing_key(data: Any, names: list[str]) -> str | None:
    for n in names:
        if n in data.files:
            return n
    return None


def extract_streamlines(npz_path: Path) -> list[dict[str, Any]]:
    """
    Supports source-native D8B serialization patterns without reconstructing
    trajectories from derived statistics.
    """
    with np.load(npz_path, allow_pickle=True) as z:
        # Preferred: object array of original streamline dictionaries.
        for key in ("streamlines", "pollock_streamlines", "streamline_records"):
            if key in z.files:
                records = unpack_object_array(z[key])
                if records and isinstance(records[0], dict):
                    return records

        # Alternate faithful serialization: parallel object arrays / numeric arrays.
        pk = first_existing_key(z, ["points_m", "streamline_points_m", "xyz_m"])
        tk = first_existing_key(z, ["times_s", "streamline_times_s", "pollock_times_s"])
        ek = first_existing_key(z, ["travel_time_s", "tau_end_s", "terminal_tof_s"])
        wk = first_existing_key(z, ["weight_m3_s", "streamline_weight_m3_s", "weights_m3_s"])
        rk = first_existing_key(z, ["producer", "producer_id", "producer_name"])
        sk = first_existing_key(z, ["status", "streamline_status"])

        if pk is None or tk is None:
            raise KeyError(
                f"{npz_path.name} does not expose source-native points_m/times_s "
                "or an object array of streamline dictionaries."
            )

        points = unpack_object_array(z[pk])
        times = unpack_object_array(z[tk])
        n = len(points)

        def arr_or_default(key: str | None, default: Any) -> list[Any]:
            if key is None:
                return [default for _ in range(n)]
            vals = unpack_object_array(z[key])
            if len(vals) != n:
                raise ValueError(f"Parallel array {key} length {len(vals)} != {n}")
            return vals

        travel = arr_or_default(ek, None)
        weights = arr_or_default(wk, np.nan)
        producers = arr_or_default(rk, None)
        statuses = arr_or_default(sk, "PRODUCER")

        records = []
        for i in range(n):
            t = np.asarray(times[i], dtype=np.float64)
            tau_end = float(travel[i]) if travel[i] is not None else float(t[-1])
            records.append({
                "seed_id": i,
                "points_m": np.asarray(points[i], dtype=np.float64),
                "times_s": t,
                "travel_time_s": tau_end,
                "weight_m3_s": float(weights[i]),
                "producer": producers[i],
                "status": statuses[i],
            })
        return records


def strict_unique_time_series(points: np.ndarray, times: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"points_m must have shape (n,3), got {points.shape}")
    if times.ndim != 1 or len(times) != len(points):
        raise ValueError("times_s must be 1-D and align with points_m")
    if len(times) < 2:
        raise ValueError("Streamline has fewer than two trajectory points")
    if not np.all(np.isfinite(points)) or not np.all(np.isfinite(times)):
        raise ValueError("Non-finite source-native trajectory values")
    if np.any(np.diff(times) < 0.0):
        raise ValueError("Source-native Pollock times are non-monotone")

    # Exact duplicate times can occur at bookkeeping boundaries. Preserve the
    # last point at each time; no geometric smoothing or fitting is performed.
    keep = np.r_[np.diff(times) > 0.0, True]
    p = points[keep]
    t = times[keep]
    if len(t) < 2 or np.any(np.diff(t) <= 0.0):
        raise ValueError("Unable to obtain a strictly increasing Pollock time series")
    return p, t


def resample_one(stream: dict[str, Any]) -> dict[str, Any]:
    points = np.asarray(stream["points_m"], dtype=np.float64)
    times = np.asarray(stream["times_s"], dtype=np.float64)
    points, times = strict_unique_time_series(points, times)

    tau0 = float(times[0])
    tau_end_native = float(stream.get("travel_time_s", times[-1]))
    # SG5 cumulative times are expected to begin at zero. We tolerate machine
    # zero only; a material offset would change theta semantics and is blocked.
    scale = max(1.0, abs(tau_end_native))
    if abs(tau0) > 1e-10 * scale:
        raise ValueError(f"Pollock times_s does not begin at zero: {tau0}")

    tau_end = float(times[-1])
    if not np.isfinite(tau_end) or tau_end <= 0.0:
        raise ValueError("Non-positive terminal Pollock TOF")
    if not math.isclose(tau_end_native, tau_end, rel_tol=1e-10, abs_tol=1e-8):
        raise ValueError(
            f"travel_time_s ({tau_end_native}) != final times_s ({tau_end})"
        )

    theta_native = times / tau_end
    xyz = np.column_stack([
        np.interp(THETA, theta_native, points[:, d]) for d in range(3)
    ])

    # Physical arc length along the 201-node resampled Pollock trajectory.
    ds = np.linalg.norm(np.diff(xyz, axis=0), axis=1)
    if not np.all(np.isfinite(ds)) or np.any(ds < 0.0):
        raise ValueError("Invalid resampled segment lengths")
    s = np.r_[0.0, np.cumsum(ds)]
    s_end = float(s[-1])
    if not np.isfinite(s_end) or s_end <= 0.0:
        raise ValueError("Non-positive streamline arc length")

    xD = s / s_end

    # Frozen C7 metric semantics: M = dtheta/dxD.
    # Use the coordinate derivative on the canonical nodes; no smoothing/fitting.
    if np.any(np.diff(xD) <= 0.0):
        raise ValueError(
            "Repeated 201-node spatial coordinates produce non-positive dx_D; "
            "metric construction is undefined without altering the trajectory."
        )
    M = np.gradient(THETA, xD, edge_order=2)

    # Reciprocal physical metric useful for conservative integration:
    # dx_D/dtheta = 1/M. Retained explicitly for later source-authentic C10 use.
    invM = np.gradient(xD, THETA, edge_order=2)

    if not np.all(np.isfinite(M)) or np.any(M <= 0.0):
        raise ValueError("C7 metric M contains non-finite/non-positive values")
    if not np.all(np.isfinite(invM)) or np.any(invM <= 0.0):
        raise ValueError("C7 inverse metric contains non-finite/non-positive values")

    return {
        "xyz_m": xyz,
        "tau_s": THETA * tau_end,
        "theta": THETA.copy(),
        "arc_length_m": s,
        "xD": xD,
        "M_dtheta_dxD": M,
        "dxD_dtheta": invM,
        "tau_end_s": tau_end,
        "path_length_m": s_end,
        "weight_m3_s": float(stream.get("weight_m3_s", np.nan)),
        "producer": stream.get("producer", None),
        "status": stream.get("status", None),
        "seed_id": stream.get("seed_id", None),
    }


def producer_string(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, bytes):
        return x.decode("utf-8", errors="replace")
    return str(x)


def main() -> None:
    print("=" * 78)
    print("PAD-Stream V16D-9")
    print("Multi-Case Pollock TOF / 201-Node Transport Coordinate and C7 Metric Construction")
    print("=" * 78)
    print()
    print("D9 RESAMPLES ONLY THE CERTIFIED D8B SOURCE-NATIVE POLLOCK TRAJECTORIES.")
    print("IT DOES NOT RUN FMM/ADV, STAGE-4 TRANSPORT, FLOW, OR MACHINE LEARNING.")
    print()
    print("CANONICAL COORDINATES:")
    print("  theta = tau / tau_end")
    print("  x_D   = s / s_end")
    print("  M     = dtheta / dx_D")
    print()

    d8b_dir = locate_d8b_dir()
    print(f"D8B directory: {d8b_dir}")

    manifest_rows = []
    case_summaries = []
    all_case_artifacts = []

    for icase, case_id in enumerate(CASE_IDS, 1):
        src = locate_case_artifact(d8b_dir, case_id)
        streams = extract_streamlines(src)

        if len(streams) != 1078:
            raise RuntimeError(
                f"{case_id}: expected frozen D8B count 1078, found {len(streams)}"
            )

        out_case = OUT / case_id
        out_case.mkdir(parents=True, exist_ok=True)

        n = len(streams)
        xyz = np.empty((n, N_THETA, 3), dtype=np.float64)
        tau = np.empty((n, N_THETA), dtype=np.float64)
        arc = np.empty((n, N_THETA), dtype=np.float64)
        xD = np.empty((n, N_THETA), dtype=np.float64)
        M = np.empty((n, N_THETA), dtype=np.float64)
        invM = np.empty((n, N_THETA), dtype=np.float64)
        tau_end = np.empty(n, dtype=np.float64)
        path_len = np.empty(n, dtype=np.float64)
        weights = np.empty(n, dtype=np.float64)
        producers = np.empty(n, dtype="U32")
        statuses = np.empty(n, dtype="U32")
        seed_ids = np.empty(n, dtype=np.int64)

        for i, srec in enumerate(streams):
            r = resample_one(srec)
            xyz[i] = r["xyz_m"]
            tau[i] = r["tau_s"]
            arc[i] = r["arc_length_m"]
            xD[i] = r["xD"]
            M[i] = r["M_dtheta_dxD"]
            invM[i] = r["dxD_dtheta"]
            tau_end[i] = r["tau_end_s"]
            path_len[i] = r["path_length_m"]
            weights[i] = r["weight_m3_s"]
            producers[i] = producer_string(r["producer"])
            statuses[i] = producer_string(r["status"])
            sid = r["seed_id"]
            seed_ids[i] = int(sid) if sid is not None else i

        artifact = out_case / f"{case_id}_Pollock_201Node_C7_Metric.npz"
        np.savez_compressed(
            artifact,
            theta=THETA,
            xyz_m=xyz,
            pollock_tau_s=tau,
            pollock_tau_end_s=tau_end,
            arc_length_m=arc,
            path_length_m=path_len,
            xD=xD,
            M_dtheta_dxD=M,
            dxD_dtheta=invM,
            streamline_weight_m3_s=weights,
            producer=producers,
            status=statuses,
            seed_id=seed_ids,
            source_d8b_artifact=str(src),
            source_d8b_sha256=sha256_file(src),
            coordinate_contract="theta=tau/tau_end; xD=s/s_end; M=dtheta/dxD",
        )
        art_sha = sha256_file(artifact)
        all_case_artifacts.append(artifact)

        gates = {
            "streamline_count_1078": n == 1078,
            "theta_201": THETA.shape == (201,),
            "theta_zero_one": bool(np.isclose(THETA[0], 0.0) and np.isclose(THETA[-1], 1.0)),
            "xyz_shape": xyz.shape == (1078, 201, 3),
            "tau_shape": tau.shape == (1078, 201),
            "metric_shape": M.shape == (1078, 201),
            "all_finite": bool(
                np.all(np.isfinite(xyz)) and np.all(np.isfinite(tau))
                and np.all(np.isfinite(arc)) and np.all(np.isfinite(xD))
                and np.all(np.isfinite(M)) and np.all(np.isfinite(invM))
                and np.all(np.isfinite(tau_end)) and np.all(np.isfinite(path_len))
                and np.all(np.isfinite(weights))
            ),
            "positive_terminal_tof": bool(np.all(tau_end > 0.0)),
            "positive_path_length": bool(np.all(path_len > 0.0)),
            "positive_weights": bool(np.all(weights > 0.0)),
            "tau_monotone": bool(np.all(np.diff(tau, axis=1) >= 0.0)),
            "arc_monotone": bool(np.all(np.diff(arc, axis=1) > 0.0)),
            "xD_monotone": bool(np.all(np.diff(xD, axis=1) > 0.0)),
            "metric_positive": bool(np.all(M > 0.0)),
            "xD_zero_one": bool(
                np.allclose(xD[:, 0], 0.0, atol=1e-12)
                and np.allclose(xD[:, -1], 1.0, atol=1e-12)
            ),
            "tau_terminal_matches": bool(np.allclose(tau[:, -1], tau_end, rtol=1e-12, atol=1e-8)),
            "all_producer_status": bool(np.all(statuses == "PRODUCER")),
            "all_four_producers": len(set(producers.tolist())) == 4,
        }
        certified = all(gates.values())

        case_summary = {
            "case_id": case_id,
            "source_artifact": str(src),
            "source_sha256": sha256_file(src),
            "artifact": str(artifact),
            "artifact_sha256": art_sha,
            "n_streamlines": n,
            "tau_end_days_min": float(np.min(tau_end) / 86400.0),
            "tau_end_days_median": float(np.median(tau_end) / 86400.0),
            "tau_end_days_max": float(np.max(tau_end) / 86400.0),
            "path_length_m_min": float(np.min(path_len)),
            "path_length_m_median": float(np.median(path_len)),
            "path_length_m_max": float(np.max(path_len)),
            "metric_min": float(np.min(M)),
            "metric_median": float(np.median(M)),
            "metric_max": float(np.max(M)),
            "producer_labels": sorted(set(producers.tolist())),
            "gates": gates,
            "certified": bool(certified),
        }
        case_summaries.append(case_summary)

        manifest_rows.append({
            "case_id": case_id,
            "status": "CERTIFIED" if certified else "FAILED",
            "n_streamlines": n,
            "median_tof_days": case_summary["tau_end_days_median"],
            "max_tof_days": case_summary["tau_end_days_max"],
            "median_path_length_m": case_summary["path_length_m_median"],
            "artifact_sha256": art_sha,
        })

        print(
            f"[{icase:02d}/24] {case_id} -> "
            f"{'CERTIFIED' if certified else 'FAILED'} | "
            f"TOF50={case_summary['tau_end_days_median']:.3f} d | "
            f"L50={case_summary['path_length_m_median']:.3f} m"
        )

    manifest = OUT / "PAD_Stream_V16D9_Manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest_rows[0].keys()))
        w.writeheader()
        w.writerows(manifest_rows)

    manifest_sha = sha256_file(manifest)
    certified_count = sum(r["status"] == "CERTIFIED" for r in manifest_rows)

    ensemble_gates = {
        "D8B_bound": d8b_dir.exists(),
        "exact_24_cases": len(case_summaries) == 24,
        "case_ids_exact_ordered": [x["case_id"] for x in case_summaries] == CASE_IDS,
        "all_24_certified": certified_count == 24,
        "all_1078_streamlines": all(x["n_streamlines"] == 1078 for x in case_summaries),
        "canonical_201_nodes": True,
        "pollock_theta_primary": True,
        "C7_metric_constructed": True,
        "producer_identity_preserved": True,
        "weights_preserved": True,
        "no_case_selection": True,
        "no_streamline_selection": True,
        "no_flow": True,
        "no_FMM": True,
        "no_ADV": True,
        "no_transport": True,
        "no_training": True,
    }

    summary = {
        "milestone": "V16D-9",
        "title": "Multi-Case Pollock TOF / 201-Node Transport Coordinate and C7 Metric Construction",
        "d8b_directory": str(d8b_dir),
        "case_ids": CASE_IDS,
        "n_cases": 24,
        "n_streamlines_per_case": 1078,
        "total_streamlines": 24 * 1078,
        "n_theta_nodes": N_THETA,
        "coordinate_contract": {
            "theta": "tau/tau_end",
            "xD": "s/s_end",
            "M": "dtheta/dxD",
            "pollock_role": "AUTHORITATIVE_TRAJECTORY_TOF_REFERENCE",
        },
        "manifest": str(manifest),
        "manifest_sha256": manifest_sha,
        "cases": case_summaries,
        "gates": ensemble_gates,
        "status": (
            "V16D_CASE0002_0025_POLLOCK_201NODE_C7_METRIC_ENSEMBLE_CERTIFIED_"
            "READY_FOR_MULTICASE_FMM_ADV_TRAVELTIME_HIERARCHY"
            if all(ensemble_gates.values())
            else "V16D_D9_BLOCKED"
        ),
        "next_milestone": (
            "V16D-10 — Multi-Case FMM/ADV Travel-Time Hierarchy Construction and Certification"
        ),
    }

    summary_path = OUT / "PAD_Stream_V16D9_Summary.json"
    summary_path.write_text(json.dumps(native(summary), indent=2), encoding="utf-8")
    summary_sha = sha256_file(summary_path)

    print()
    print("=" * 78)
    print("V16D-9 ENSEMBLE SUMMARY")
    print("=" * 78)
    med_tofs = np.array([x["tau_end_days_median"] for x in case_summaries])
    max_tofs = np.array([x["tau_end_days_max"] for x in case_summaries])
    med_len = np.array([x["path_length_m_median"] for x in case_summaries])
    print(f"  certified cases       : {certified_count}/24")
    print(f"  total trajectories     : {24 * 1078}")
    print(f"  nodes / trajectory     : {N_THETA}")
    print(
        "  median TOF d min/median/max: "
        f"{med_tofs.min():.3f} / {np.median(med_tofs):.3f} / {med_tofs.max():.3f}"
    )
    print(
        "  max TOF d min/median/max   : "
        f"{max_tofs.min():.3f} / {np.median(max_tofs):.3f} / {max_tofs.max():.3f}"
    )
    print(
        "  median path m min/median/max: "
        f"{med_len.min():.3f} / {np.median(med_len):.3f} / {med_len.max():.3f}"
    )
    print(f"  manifest SHA-256      : {manifest_sha}")
    print(f"  summary SHA-256       : {summary_sha}")

    print()
    print("=" * 78)
    print("V16D-9 GATES")
    print("=" * 78)
    for k, v in ensemble_gates.items():
        print(f"[{'PASS' if v else 'FAIL'}] {k}")

    print()
    print("STATUS")
    print(f"  {summary['status']}")
    print()
    print("NEXT MILESTONE")
    print(f"  {summary['next_milestone']}")

    if not all(ensemble_gates.values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()

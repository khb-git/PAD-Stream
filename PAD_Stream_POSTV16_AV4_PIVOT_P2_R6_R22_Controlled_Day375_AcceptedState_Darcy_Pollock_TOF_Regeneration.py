#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


M = "POSTV16-AV4-PIVOT-P2-R6-R22"
NAME = "Controlled Day375 Accepted-State Darcy/Pollock/TOF Regeneration"

PASS = (
    "AV4PIVOTP2R6R22_DAY375_ACCEPTED_STATE_DARCY_POLLOCK_TOF_"
    "REGENERATION_PASS_NO_TRANSPORT_MUTATION_NO_TIME_ADVANCE"
)
FAIL = (
    "AV4PIVOTP2R6R22_DAY375_ACCEPTED_STATE_DARCY_POLLOCK_TOF_"
    "REGENERATION_SCIENTIFIC_FAIL_NO_AUTOMATIC_RERUN"
)
BLOCK = "AV4PIVOTP2R6R22_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "cab515e3d2b0345deb29173b11c260adbd67c3ce"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
DAY = 375.0
DAY_TO_S = 86400.0

FLOW_LOCAL_REL_L2_MAX = 1.0e-8
FLOW_GLOBAL_REL_MISMATCH_MAX = 1.0e-8
INJECTOR_WEIGHT_REL_CLOSURE_MAX = 1.0e-10

# --------------------------------------------------------------------------------------------------
# Comprehensive Day375 pressure-refresh authority.
# --------------------------------------------------------------------------------------------------

CLOSURE_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_R1_R1"
CLOSURE_REL = BASE / (
    CLOSURE_TOKEN
    + "_Comprehensive_Technical_Closure_and_Pressure_Refresh_Acceptance"
)

CLOSURE_SUMMARY = f"PAD_Stream_{CLOSURE_TOKEN}_Summary.json"
CLOSURE_CONTRACT = f"{CLOSURE_TOKEN}_Accepted_Pressure_Refresh_Contract.json"
CLOSURE_DECISION = f"{CLOSURE_TOKEN}_Decision_Contract.json"
CLOSURE_MANIFEST = f"{CLOSURE_TOKEN}_Artifact_Manifest.csv"
PRESSURE_EPOCH = f"{CLOSURE_TOKEN}_Accepted_Day375_Pressure_Epoch.npz"

CLOSURE_STATUS = (
    "AV4PIVOTP2R6R21R4R1R5R1R1R1R1_COMPREHENSIVE_TECHNICAL_CLOSURE_"
    "PASS_DAY375_PRESSURE_REFRESH_ACCEPTED_NO_COUPLED_SCIENCE_RERUN"
)
PRESSURE_EPOCH_SHA256 = "99d73cab1d33191a68578f29d3c03f9fac07ed77c39e124cc8eb5e5bf75aa84d"
ACCEPTED_TRANSPORT_SHA256 = "e209adb5a169008698db9acb24e5cade82df3f6991b5174515d5957901bceb67"

# --------------------------------------------------------------------------------------------------
# Exact source authorities.
# --------------------------------------------------------------------------------------------------

CLOSURE_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_R1_R1_"
    "Comprehensive_Technical_Closure.py"
)
CLOSURE_RUNNER_BLOB = "ea1a26342e5367943bf459cefc5ff7aacefd0798"

SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"

SG4 = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG4_BLOB = "8d49f88bdf55b0da087af2bed04e69967740e695"

SG5 = "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
SG5_BLOB = "9a0b64ea7e669904d0d9855ade1c6b052f05ecea"

SG6 = "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py"
SG6_BLOB = "70ceda68e02894167958d753d88b4dbd694731ab"

R3PHYS = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3PHYS_BLOB = "740c6da03e73906646bf0153633187e749449f31"

SOURCE_BLOBS = {
    CLOSURE_RUNNER: CLOSURE_RUNNER_BLOB,
    SG3: SG3_BLOB,
    SG4: SG4_BLOB,
    SG5: SG5_BLOB,
    SG6: SG6_BLOB,
    R3PHYS: R3PHYS_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Output.
# --------------------------------------------------------------------------------------------------

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R22"
OUT_REL = BASE / (
    OUT_TOKEN
    + "_Controlled_Day375_AcceptedState_Darcy_Pollock_TOF_Regeneration"
)
FAIL_REL = BASE / (OUT_TOKEN + "_SCIENTIFIC_FAIL")
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csvb(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            arr = np.asarray(arrays[key])
            if arr.dtype == object:
                raise GateError(f"object_array_forbidden:{key}")
            b = io.BytesIO()
            np.save(b, arr, allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


def manifest(directory: Path, filename: str) -> dict[str, str]:
    rows = csvr(directory / filename)
    out: dict[str, str] = {}
    for row in rows:
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        out[p.name] = row["sha256"]
    return out


def mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def reconstruct_producer_wi(epoch: Any, sg3: Any) -> dict[str, list[dict[str, float]]]:
    names = np.asarray(epoch["producer_name"]).astype("U32").reshape(-1)
    ii = np.asarray(epoch["producer_i"], dtype=np.int64).reshape(-1)
    jj = np.asarray(epoch["producer_j"], dtype=np.int64).reshape(-1)
    kk = np.asarray(epoch["producer_k"], dtype=np.int64).reshape(-1)
    wi = np.asarray(epoch["producer_wi_si"], dtype=np.float64).reshape(-1)
    wi_ref = np.asarray(epoch["producer_wi_reference_si"], dtype=np.float64).reshape(-1)
    scale = np.asarray(epoch["producer_mobility_scale"], dtype=np.float64).reshape(-1)
    re_m = np.asarray(epoch["producer_re_m"], dtype=np.float64).reshape(-1)

    n = len(names)
    if not (len(ii) == len(jj) == len(kk) == len(wi) == len(wi_ref) == len(scale) == len(re_m) == n):
        raise GateError("producer_WI_parallel_array_length_mismatch")

    result: dict[str, list[dict[str, float]]] = {name: [] for name in sg3.PRODUCERS}

    for idx in range(n):
        name = str(names[idx])
        if name not in sg3.PRODUCERS:
            raise GateError(f"unknown_producer_name:{name}")
        well = sg3.PRODUCERS[name]
        if int(ii[idx]) != int(well["i"]) or int(jj[idx]) != int(well["j"]):
            raise GateError(f"producer_IJ_mismatch:{name}")
        result[name].append({
            "k": int(kk[idx]),
            "wi_si": float(wi[idx]),
            "wi_reference_si": float(wi_ref[idx]),
            "mobility_scale": float(scale[idx]),
            "re_m": float(re_m[idx]),
        })

    for name in result:
        result[name].sort(key=lambda x: int(x["k"]))
        ks = [int(x["k"]) for x in result[name]]
        if ks != list(sg3.COMPLETION_K):
            raise GateError(f"producer_completion_K_mismatch:{name}:{ks}")

    return result


def convert_sg5_to_sg6(streamlines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted = []
    for s in streamlines:
        converted.append({
            "id": int(s["seed_id"]),
            "points_m": np.asarray(s["points_m"], dtype=np.float64),
            "tau_s": np.asarray(s["times_s"], dtype=np.float64),
            "weight_m3_s": float(s["weight_m3_s"]),
            "tau_end_s": float(s["travel_time_s"]),
            "status": str(s["status"]),
            "producer": str(s["producer"]),
        })
    return converted


def selftest() -> None:
    # Static namespace / authority checks.
    assert OUT_REL.name.startswith(OUT_TOKEN + "_")
    assert FAIL_REL.name == OUT_TOKEN + "_SCIENTIFIC_FAIL"
    assert BLOCK_REL.name == OUT_TOKEN + "_BLOCKED"
    assert CLOSURE_REL.name.startswith(CLOSURE_TOKEN + "_")
    assert len(PRESSURE_EPOCH_SHA256) == 64
    assert len(ACCEPTED_TRANSPORT_SHA256) == 64

    # SG5->SG6 conversion contract.
    s = [{
        "seed_id": 7,
        "points_m": np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        "times_s": np.asarray([0.0, 2.0]),
        "weight_m3_s": 3.0,
        "travel_time_s": 2.0,
        "status": "PRODUCER",
        "producer": "PROD_SW",
    }]
    c = convert_sg5_to_sg6(s)
    assert c[0]["id"] == 7
    assert c[0]["tau_end_s"] == 2.0
    assert c[0]["status"] == "PRODUCER"

    print("POSTV16 AV4 PIVOT P2-R6-R22 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()

    out = drive / OUT_REL
    fail_dir = drive / FAIL_REL
    block_dir = drive / BLOCK_REL

    stage = "preflight"
    gates: list[dict[str, Any]] = []
    scientific_execution_started = False

    def gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    def sci_gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "scientific_execution_gate": True,
            "detail": "" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise ScientificFail(name, detail)

    try:
        # ------------------------------------------------------------------------------------------
        # Immutable outcome firewall.
        # ------------------------------------------------------------------------------------------
        stage = "preexisting_state_firewall"

        pass_summary = out / f"PAD_Stream_{OUT_TOKEN}_Summary.json"
        fail_report = fail_dir / f"{OUT_TOKEN}_Scientific_Fail_Report.json"
        block_report = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"

        gate("no_preexisting_R22_PASS", not pass_summary.exists(), str(pass_summary))
        gate("no_preexisting_R22_FAIL", not fail_report.exists(), str(fail_report))
        gate("no_preexisting_R22_BLOCK", not block_report.exists(), str(block_report))

        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_comprehensive_closure_commit", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        for filename, expected_blob in SOURCE_BLOBS.items():
            p = root / filename
            gate(f"{Path(filename).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_blob_exact", actual == expected_blob, actual)

        # ------------------------------------------------------------------------------------------
        # Comprehensive closure binding.
        # ------------------------------------------------------------------------------------------
        stage = "comprehensive_pressure_closure_authority"

        cdir = drive / CLOSURE_REL
        gate("comprehensive_closure_directory_present", cdir.is_dir(), str(cdir))

        cmanifest = manifest(cdir, CLOSURE_MANIFEST)
        gate("pressure_epoch_in_manifest", PRESSURE_EPOCH in cmanifest, list(cmanifest))
        gate("pressure_epoch_manifest_SHA_exact", cmanifest.get(PRESSURE_EPOCH) == PRESSURE_EPOCH_SHA256)

        csummary = js(cdir / CLOSURE_SUMMARY)
        ccontract = js(cdir / CLOSURE_CONTRACT)
        cdecision = js(cdir / CLOSURE_DECISION)

        gate("comprehensive_closure_status_exact", csummary.get("status") == CLOSURE_STATUS, csummary.get("status"))
        gate("technical_wrapper_full_audit_complete", csummary.get("technical_wrapper_full_audit_completed") is True)
        gate("all_inherited_BLOCK_paths_static_exact", csummary.get("all_inherited_BLOCK_paths_static_exact") is True)
        gate("pressure_refresh_accepted_summary", csummary.get("pressure_refresh_accepted") is True)
        gate("pressure_refresh_accepted_contract", ccontract.get("accepted_Day375_pressure_refresh") is True)
        gate("R22_authorized", cdecision.get("P2_R6_R22_authorized") is True)
        gate("R22_Darcy_authorized", cdecision.get("P2_R6_R22_Darcy_flux_regeneration_authorized") is True)
        gate("R22_Pollock_authorized", cdecision.get("P2_R6_R22_Pollock_streamline_regeneration_authorized") is True)
        gate("R22_TOF_authorized", cdecision.get("P2_R6_R22_TOF_regeneration_authorized") is True)
        gate("R22_must_bind_pressure_epoch_SHA", cdecision.get("P2_R6_R22_must_bind_comprehensive_closure_pressure_epoch_SHA") is True)
        gate("physical_time_advance_forbidden", cdecision.get("physical_time_advance_authorized") is False)
        gate("P3_remains_locked", cdecision.get("P3_authorized") is False)

        epoch_path = cdir / PRESSURE_EPOCH
        gate("pressure_epoch_present", epoch_path.is_file(), str(epoch_path))
        gate("pressure_epoch_SHA_exact", sha(epoch_path) == PRESSURE_EPOCH_SHA256, sha(epoch_path))

        # ------------------------------------------------------------------------------------------
        # Load frozen executable modules and pressure epoch.
        # ------------------------------------------------------------------------------------------
        stage = "accepted_pressure_epoch_schema"

        sg3 = mod(root / SG3, "r22_sg3")
        sg4 = mod(root / SG4, "r22_sg4")
        sg5 = mod(root / SG5, "r22_sg5")
        sg6 = mod(root / SG6, "r22_sg6")
        r3phys = mod(root / R3PHYS, "r22_r3phys")

        with np.load(epoch_path, allow_pickle=False) as z:
            required = [
                "canonical_day",
                "accepted_transport_base_R20_sha256",
                "refreshed_pressure_psi",
                "reconciled_saturation",
                "pressure_compatible_grid_mass_kg",
                "Tx_dynamic",
                "Ty_dynamic",
                "Tz_dynamic",
                "lambda_total",
                "producer_name",
                "producer_i",
                "producer_j",
                "producer_k",
                "producer_wi_si",
                "producer_wi_reference_si",
                "producer_mobility_scale",
                "producer_re_m",
                "physical_time_advanced",
                "Darcy_Pollock_TOF_regenerated",
            ]
            missing = [k for k in required if k not in z.files]
            gate("pressure_epoch_schema_complete", not missing, missing)

            canonical_day = float(np.asarray(z["canonical_day"]).reshape(()))
            accepted_transport_sha = str(np.asarray(z["accepted_transport_base_R20_sha256"]).reshape(()))
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            saturation = np.asarray(z["reconciled_saturation"], dtype=np.float64)
            component_mass = np.asarray(z["pressure_compatible_grid_mass_kg"], dtype=np.float64)
            tx = np.asarray(z["Tx_dynamic"], dtype=np.float64)
            ty = np.asarray(z["Ty_dynamic"], dtype=np.float64)
            tz = np.asarray(z["Tz_dynamic"], dtype=np.float64)
            lambda_total = np.asarray(z["lambda_total"], dtype=np.float64)
            physical_time_advanced = bool(np.asarray(z["physical_time_advanced"]).reshape(()))
            previously_regenerated = bool(np.asarray(z["Darcy_Pollock_TOF_regenerated"]).reshape(()))

            producer_wi = reconstruct_producer_wi(z, sg3)

        gate("canonical_day_375", canonical_day == DAY, canonical_day)
        gate("accepted_transport_SHA_exact", accepted_transport_sha == ACCEPTED_TRANSPORT_SHA256, accepted_transport_sha)
        gate("pressure_shape_finite", pressure.shape == GRID and np.isfinite(pressure).all())
        gate("saturation_shape_finite", saturation.shape == GRID and np.isfinite(saturation).all())
        gate("component_mass_shape_finite", component_mass.shape == GRID and np.isfinite(component_mass).all())
        gate("lambda_total_shape_positive", lambda_total.shape == GRID and np.isfinite(lambda_total).all() and np.all(lambda_total > 0.0))
        gate("Tx_shape_finite", tx.shape == (NZ, NY, NX - 1) and np.isfinite(tx).all())
        gate("Ty_shape_finite", ty.shape == (NZ, NY - 1, NX) and np.isfinite(ty).all())
        gate("Tz_shape_finite", tz.shape == (NZ - 1, NY, NX) and np.isfinite(tz).all())
        gate("producer_completion_count_exact_20", sum(len(v) for v in producer_wi.values()) == 20)
        gate("pressure_epoch_no_time_advance", physical_time_advanced is False)
        gate("pressure_epoch_Darcy_Pollock_TOF_not_yet_regenerated", previously_regenerated is False)

        # Scientific execution begins here.
        scientific_execution_started = True

        # ------------------------------------------------------------------------------------------
        # Darcy face flux regeneration.
        # ------------------------------------------------------------------------------------------
        stage = "Darcy_face_flux_regeneration"

        producer_rates, producer_sink = r3phys.producer_rates_updated(
            sg3,
            pressure,
            producer_wi,
        )

        sci_gate(
            "all_BHP_wells_remain_producers",
            all(float(v["m3_s"]) > 0.0 for v in producer_rates.values()),
            {k: float(v["m3_day"]) for k, v in producer_rates.items()},
        )

        qx, qy, qz = sg4.compute_face_fluxes(
            pressure,
            tx,
            ty,
            tz,
        )

        sci_gate(
            "Darcy_face_flux_shapes_exact",
            qx.shape == (NZ, NY, NX - 1)
            and qy.shape == (NZ, NY - 1, NX)
            and qz.shape == (NZ - 1, NY, NX),
            [qx.shape, qy.shape, qz.shape],
        )
        sci_gate(
            "Darcy_face_fluxes_finite",
            np.isfinite(qx).all() and np.isfinite(qy).all() and np.isfinite(qz).all(),
        )

        conservation = r3phys.flow_conservation_metrics(
            sg3,
            sg4,
            qx,
            qy,
            qz,
            producer_sink,
        )

        sci_gate(
            "Darcy_local_conservation",
            float(conservation["local_relative_l2_error"]) < FLOW_LOCAL_REL_L2_MAX,
            conservation["local_relative_l2_error"],
        )
        sci_gate(
            "Darcy_global_conservation",
            float(conservation["global_relative_mismatch"]) < FLOW_GLOBAL_REL_MISMATCH_MAX,
            conservation["global_relative_mismatch"],
        )

        # ------------------------------------------------------------------------------------------
        # Exact Pollock retrace.
        # ------------------------------------------------------------------------------------------
        stage = "exact_Pollock_retrace"

        vx, vy, vz = sg5.construct_face_pore_velocities(qx, qy, qz)
        faces, seeds = sg5.build_seeds(qx, qy, qz)

        sci_gate("Pollock_outgoing_injector_face_count_positive", len(faces) > 0, len(faces))
        sci_gate("Pollock_seed_count_positive", len(seeds) > 0, len(seeds))

        streamlines = sg5.trace_streamlines(seeds, vx, vy, vz)

        try:
            sg5_validation = sg5.validate_streamlines(faces, seeds, streamlines)
        except Exception as exc:
            raise ScientificFail("source_SG5_validation_failure", repr(exc)) from exc

        statuses = [str(s["status"]) for s in streamlines]
        captured_producers = [
            str(s["producer"])
            for s in streamlines
            if str(s["status"]) == "PRODUCER"
        ]

        sci_gate(
            "all_streamlines_terminal_producer_captured",
            len(streamlines) == len(seeds)
            and len(streamlines) > 0
            and all(status == "PRODUCER" for status in statuses),
            {
                "seeds": len(seeds),
                "streamlines": len(streamlines),
                "statuses": {
                    status: statuses.count(status)
                    for status in sorted(set(statuses))
                },
            },
        )

        sci_gate(
            "all_four_producers_represented",
            all(name in captured_producers for name in sg5.PRODUCERS),
            sorted(set(captured_producers)),
        )

        seed_weight_m3_s = float(sum(float(s["weight_m3_s"]) for s in seeds))
        injection_weight_rel = abs(seed_weight_m3_s - float(sg3.Q_INJ_M3_S)) / max(
            abs(float(sg3.Q_INJ_M3_S)),
            1.0e-30,
        )
        sci_gate(
            "injector_seed_weight_relative_closure",
            injection_weight_rel <= INJECTOR_WEIGHT_REL_CLOSURE_MAX,
            injection_weight_rel,
        )

        # ------------------------------------------------------------------------------------------
        # SG6 TOF rebuild.
        # ------------------------------------------------------------------------------------------
        stage = "SG6_TOF_rebuild"

        sg6_streamlines = convert_sg5_to_sg6(streamlines)
        transport_db = sg6.build_transport_database(sg6_streamlines)

        try:
            sg6.validate_transport(transport_db)
        except Exception as exc:
            raise ScientificFail("source_SG6_validation_failure", repr(exc)) from exc

        xyz_m = np.asarray(transport_db["xyz_m"], dtype=np.float64)
        tof_s = np.asarray(transport_db["tau_s"], dtype=np.float64)
        xi = np.asarray(transport_db["xi"], dtype=np.float64)
        path_length_m = np.asarray(transport_db["path_length_m"], dtype=np.float64)
        weights_m3_s = np.asarray(transport_db["weights_m3_s"], dtype=np.float64)
        tau_end_s = np.asarray(transport_db["tau_end_s"], dtype=np.float64)
        producer_labels = np.asarray(transport_db["producer"]).astype("U32")
        streamline_id = np.asarray(transport_db["streamline_id"], dtype=np.int64)

        sci_gate(
            "TOF_database_shapes_exact",
            xyz_m.ndim == 3
            and xyz_m.shape[1:] == (201, 3)
            and tof_s.shape == xyz_m.shape[:2]
            and path_length_m.shape == tof_s.shape
            and weights_m3_s.shape == (xyz_m.shape[0],)
            and tau_end_s.shape == (xyz_m.shape[0],)
            and producer_labels.shape == (xyz_m.shape[0],)
            and streamline_id.shape == (xyz_m.shape[0],),
            {
                "xyz": xyz_m.shape,
                "tof": tof_s.shape,
                "weights": weights_m3_s.shape,
            },
        )
        sci_gate(
            "TOF_finite_positive_monotone",
            np.isfinite(xyz_m).all()
            and np.isfinite(tof_s).all()
            and np.all(weights_m3_s > 0.0)
            and np.all(tau_end_s > 0.0)
            and np.all(np.diff(tof_s, axis=1) >= -1.0e-12),
        )
        sci_gate(
            "TOF_endpoint_matches_terminal",
            np.allclose(tof_s[:, -1], tau_end_s, rtol=1.0e-10, atol=1.0e-8),
        )
        sci_gate(
            "TOF_all_four_producers_represented",
            all(np.any(producer_labels == name) for name in sg6.PRODUCER_NAMES),
            sorted(set(producer_labels.tolist())),
        )

        transport_weight_rel = abs(float(np.sum(weights_m3_s)) - seed_weight_m3_s) / max(
            abs(seed_weight_m3_s),
            1.0e-30,
        )
        sci_gate(
            "TOF_streamline_weight_preservation",
            transport_weight_rel <= 1.0e-14,
            transport_weight_rel,
        )

        # ------------------------------------------------------------------------------------------
        # PASS-only publication.
        # ------------------------------------------------------------------------------------------
        stage = "atomic_PASS_publication"

        producer_rows = []
        for name in sorted(producer_rates):
            info = producer_rates[name]
            producer_rows.append({
                "producer": name,
                "rate_m3_s": float(info["m3_s"]),
                "rate_m3_day": float(info["m3_day"]),
                "completion_rates_m3_day": json.dumps(
                    [float(x) for x in info["perf_m3_day"]]
                ),
            })

        flow_audit = {
            **{k: float(v) for k, v in conservation.items()},
            "Qx_min_m3_s": float(np.min(qx)),
            "Qx_max_m3_s": float(np.max(qx)),
            "Qy_min_m3_s": float(np.min(qy)),
            "Qy_max_m3_s": float(np.max(qy)),
            "Qz_min_m3_s": float(np.min(qz)),
            "Qz_max_m3_s": float(np.max(qz)),
        }

        pollock_audit = {
            **sg5_validation,
            "outgoing_injector_face_count": int(len(faces)),
            "seed_count": int(len(seeds)),
            "streamline_count": int(len(streamlines)),
            "all_streamlines_producer_captured": True,
            "injector_seed_weight_m3_s": seed_weight_m3_s,
            "injector_seed_weight_relative_closure": injection_weight_rel,
            "producer_labels": sorted(set(producer_labels.tolist())),
        }

        tof_audit = {
            "streamline_count": int(xyz_m.shape[0]),
            "nodes_per_streamline": int(xyz_m.shape[1]),
            "tau_end_min_days": float(np.min(tau_end_s) / DAY_TO_S),
            "tau_end_median_days": float(np.median(tau_end_s) / DAY_TO_S),
            "tau_end_max_days": float(np.max(tau_end_s) / DAY_TO_S),
            "streamline_weight_total_m3_day": float(np.sum(weights_m3_s) * DAY_TO_S),
            "streamline_weight_relative_to_seed_error": transport_weight_rel,
            "all_four_producers_represented": True,
            "TOF_finite_positive_monotone": True,
        }

        arrays = {
            "canonical_day": np.asarray(DAY, dtype=np.float64),
            "source_pressure_epoch_sha256": np.asarray(PRESSURE_EPOCH_SHA256, dtype="U64"),
            "accepted_transport_base_R20_sha256": np.asarray(ACCEPTED_TRANSPORT_SHA256, dtype="U64"),
            "refreshed_pressure_psi": pressure,
            "reconciled_saturation": saturation,
            "pressure_compatible_grid_mass_kg": component_mass,
            "lambda_total": lambda_total,
            "Tx_dynamic": tx,
            "Ty_dynamic": ty,
            "Tz_dynamic": tz,
            "Qx": qx,
            "Qy": qy,
            "Qz": qz,
            "streamline_xyz_m": xyz_m,
            "streamline_tof_s": tof_s,
            "streamline_weight_m3_s": weights_m3_s,
            "streamline_path_length_m": path_length_m,
            "tau_end_s": tau_end_s,
            "xi": xi,
            "producer_labels": producer_labels,
            "streamline_id": streamline_id,
            "physical_time_advance": np.asarray(False, dtype=np.bool_),
            "transport_state_mutation": np.asarray(False, dtype=np.bool_),
            "Darcy_Pollock_TOF_regenerated": np.asarray(True, dtype=np.bool_),
        }

        output_npz = deterministic_npz_bytes(arrays)

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": (
                "R6R22_DAY375_DARCY_POLLOCK_TOF_REGENERATION_PASS_"
                "REFRESHED_GEOMETRY_COMPATIBILITY_AUDIT_NEXT"
            ),
            "source_pressure_epoch_sha256": PRESSURE_EPOCH_SHA256,
            "accepted_transport_base_R20_sha256": ACCEPTED_TRANSPORT_SHA256,
            "canonical_day": DAY,
            "flow_local_relative_L2_error": float(conservation["local_relative_l2_error"]),
            "flow_global_relative_mismatch": float(conservation["global_relative_mismatch"]),
            "injector_seed_weight_relative_closure": injection_weight_rel,
            "outgoing_injector_face_count": int(len(faces)),
            "streamline_count": int(xyz_m.shape[0]),
            "TOF_nodes": int(xyz_m.shape[1]),
            "tau_end_min_days": float(np.min(tau_end_s) / DAY_TO_S),
            "tau_end_median_days": float(np.median(tau_end_s) / DAY_TO_S),
            "tau_end_max_days": float(np.max(tau_end_s) / DAY_TO_S),
            "all_four_producers_represented": True,
            "Darcy_Pollock_TOF_regeneration_executed": True,
            "accepted_transport_state_mutated": False,
            "pressure_epoch_mutated": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": summary["classification"],
            "P2_R6_R23_authorized": True,
            "P2_R6_R23_name": (
                "Day375 Regenerated Streamline Geometry / Accepted Transport "
                "Representation Compatibility Audit"
            ),
            "P2_R6_R23_design_or_diagnostic_only": True,
            "P2_R6_R23_must_bind_R22_flow_epoch_SHA": True,
            "accepted_Day375_transport_state_remains_authoritative": True,
            "accepted_Day375_pressure_refresh_remains_authoritative": True,
            "Darcy_Pollock_TOF_regeneration_accepted": True,
            "transport_state_mutation_authorized": False,
            "mapback_execution_authorized": False,
            "physical_time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        out.mkdir(parents=True, exist_ok=False)

        epoch_name = f"{OUT_TOKEN}_Day375_Regenerated_Darcy_Pollock_TOF_Epoch.npz"
        epoch_path_out = out / epoch_name
        epoch_path_out.write_bytes(output_npz)
        epoch_sha = sha(epoch_path_out)

        summary["regenerated_flow_epoch_sha256"] = epoch_sha
        decision["P2_R6_R23_R22_flow_epoch_sha256"] = epoch_sha

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Darcy_Flow_Conservation_Audit.json").write_bytes(jb(flow_audit))
        (out / f"{OUT_TOKEN}_Producer_Rates.csv").write_bytes(csvb(producer_rows))
        (out / f"{OUT_TOKEN}_Pollock_Audit.json").write_bytes(jb(pollock_audit))
        (out / f"{OUT_TOKEN}_TOF_Audit.json").write_bytes(jb(tof_audit))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                manifest_rows.append({
                    "file": p.name,
                    "sha256": sha(p),
                    "bytes": p.stat().st_size,
                })
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(manifest_rows))

        print("=" * 190)
        print(M, "PASS")
        print("Source pressure epoch SHA256               :", PRESSURE_EPOCH_SHA256)
        print("Regenerated flow epoch SHA256              :", epoch_sha)
        print("Darcy local relative L2                    :", conservation["local_relative_l2_error"])
        print("Darcy global relative mismatch             :", conservation["global_relative_mismatch"])
        print("Injector seed weight relative closure      :", injection_weight_rel)
        print("Outgoing injector faces / seeds            :", len(faces), "/", len(seeds))
        print("Streamlines / TOF nodes                    :", xyz_m.shape[0], "/", xyz_m.shape[1])
        print("TOF min / median / max days                :", tof_audit["tau_end_min_days"], "/", tof_audit["tau_end_median_days"], "/", tof_audit["tau_end_max_days"])
        print("All four producers represented             : True")
        print("Accepted transport state mutated           : False")
        print("Pressure epoch mutated                     : False")
        print("Physical time advanced                     : False")
        print("R23 compatibility audit authorized         : True")
        print("P3 authorized                              : False")
        print("=" * 190)
        return 0

    except ScientificFail as exc:
        fail_dir.mkdir(parents=True, exist_ok=True)
        p = fail_dir / f"{OUT_TOKEN}_Scientific_Fail_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": FAIL,
                "failed_stage": stage,
                "failed_gate": exc.gate,
                "detail": exc.detail,
                "scientific_execution_started": scientific_execution_started,
                "accepted_transport_state_preserved": True,
                "accepted_pressure_epoch_preserved": True,
                "automatic_rerun_authorized": False,
                "transport_state_mutation_authorized": False,
                "physical_time_advance_authorized": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print("=" * 190)
        print(M, "SCIENTIFIC FAIL")
        print("Stage :", stage)
        print("Gate  :", exc.gate)
        print("Detail:", exc.detail)
        print("NO AUTOMATIC RERUN / TRANSPORT MUTATION / TIME ADVANCE AUTHORIZED.")
        print("=" * 190)
        return 3

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        p = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "scientific_execution_started": scientific_execution_started,
                "accepted_transport_state_preserved": True,
                "accepted_pressure_epoch_preserved": True,
                "automatic_rerun_authorized": False,
                "transport_state_mutation_authorized": False,
                "physical_time_advance_authorized": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print("=" * 190)
        print(M, "TECHNICAL BLOCK")
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO AUTOMATIC RERUN / TRANSPORT MUTATION / TIME ADVANCE AUTHORIZED.")
        print("=" * 190)
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        selftest()
        raise SystemExit(0)

    raise SystemExit(main(args.project_root, args.drive_root))

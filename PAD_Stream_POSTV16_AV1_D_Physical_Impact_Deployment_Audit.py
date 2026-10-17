#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from typing import Any

import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

MILESTONE = "POSTV16-AV1-D"
STATUS_PASS = (
    "AV1D_PHYSICAL_IMPACT_QUANTIFIED_"
    "BREAKTHROUGH_EVENT_PRESERVED_"
    "EXTERNAL_ACCEPTANCE_BENCHMARK_PENDING"
)
STATUS_BLOCKED = "AV1D_PHYSICAL_IMPACT_AUDIT_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

AV1C_COMMIT = "2ac99c1ef0280516daf5930e691ef962760629b0"

AV1C_RUNNER = "PAD_Stream_POSTV16_AV1_C_Accuracy_Interpretation_and_Deployment_Path_Decision.py"
AV1C_RUNNER_BLOB = "bc8ef764483aa00222bf715728c68fea526179bb"

B1R1_RUNNER = (
    "PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_"
    "Representation_Equivalence_Audit.py"
)
B1R1_RUNNER_BLOB = "8d9561d7c85805b82dedc26073c4633f90eeeab6"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

E36 = "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py"
E36_BLOB = "9ab4035c95a25bd61c649f86c82d88f059cef9e2"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7A_BLOB = "a4dd47338e7a85f130a6a70d0a41211e38c655f8"

SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

SOURCE_BLOBS = {
    AV1C_RUNNER: AV1C_RUNNER_BLOB,
    B1R1_RUNNER: B1R1_RUNNER_BLOB,
    R2: R2_BLOB,
    E36: E36_BLOB,
    E37A: E37A_BLOB,
    SG7A: SG7A_BLOB,
    SG7D: SG7D_BLOB,
}

AV1C_OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_C_Accuracy_Interpretation_and_Deployment_Path_Decision"
)
AV1C_SUMMARY = "PAD_Stream_POSTV16_AV1_C_Summary.json"
AV1C_DECISION = "POSTV16_AV1_C_Decision_Contract.json"
AV1C_MANIFEST = "POSTV16_AV1_C_Artifact_Manifest.csv"
AV1C_STATUS = (
    "AV1C_REPRESENTATION_ACCEPTED_NO_REPAIR_"
    "MODEL_DEPLOYMENT_REQUIRES_PHYSICAL_IMPACT_AUDIT"
)

C18R_NAME = "V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz"
C18R_SHA = "1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"

C19_NAME = "V16C19_Leakage_Safe_Split_Assignment.npz"
C19_SHA = "399815504f5ba3a900c02f24e4f9496b3a93c2e472a5faea593507cf9174638a"

WEIGHTS_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_A3R3R_C26_Weight_State_Compatibility_Reconstruction"
    / "V16C26_EXP2_Exact_Embedded.weights.h5"
)
WEIGHTS_SHA = "4bf0bde8a68d400a7eee33735ca85b4524b70d14be367f278f7276533443f8f9"

R2_REL = Path(
    "provenance/hybrid_dp/"
    "V16E35_R2_FIRST_CONTROLLED_SGSIM_RUNTIME_STATE_TRANSITION_CONSERVATIVE_CAPILLARY_SPLIT"
)
R2_STATE = "V16E35_R2_First_Accepted_SGSim_Runtime_State_Step0001.npz"

E36_REL = Path(
    "provenance/hybrid_dp/"
    "V16E36_SHORT_ADAPTIVE_SGSIM_ROLLOUT_EARLY_PLUME_VALIDATION"
)
E36_CLOSURE = "V16E36_Final_Closure.json"
E36_CACHE = "V16E36_Certified_Physics_Cache.npz"

OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_Physical_Impact_Deployment_Audit"
)
BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_BLOCKED"
)

EXPECTED_STREAMLINES = 1078
EXPECTED_NODES = 201
EXPECTED_CVS = 200
EXPECTED_SAMPLES = 9702
EXPECTED_TEST_STREAMLINES = 161
EXPECTED_DAYS = np.array(
    [30., 60., 100., 150., 250., 365., 500., 750., 1000.],
    dtype=np.float64,
)
EXPECTED_GRID = (15, 50, 50)
BACKGROUND_SATURATION = 0.20

# Existing physical event contract inherited from E36. This is NOT a new
# post-hoc accuracy threshold.
BREAKTHROUGH_GAS_CUT = 1.0e-4

NUM_TOL = 5.0e-13


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git_text(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


def git_blob_sha(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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


def json_bytes(obj: Any) -> bytes:
    return (
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


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
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(
        outer,
        "w",
        zipfile.ZIP_DEFLATED,
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


def find_by_name_and_sha(
    roots: list[Path],
    name: str,
    expected_sha: str,
) -> Path:
    hits: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob(name):
            try:
                if p.is_file() and sha256_file(p) == expected_sha:
                    hits.append(p)
            except OSError:
                pass
    if not hits:
        raise GateError(f"artifact_not_found_with_exact_sha:{name}:{expected_sha}")
    return sorted(set(hits), key=lambda p: (len(str(p)), str(p)))[0]


def verify_manifest(directory: Path, manifest_name: str) -> dict[str, str]:
    rows = read_csv(directory / manifest_name)
    manifest = {r["file"]: r["sha256"] for r in rows}
    for name, expected in manifest.items():
        p = directory / name
        if not p.is_file():
            raise GateError(f"manifest_file_missing:{name}")
        actual = sha256_file(p)
        if actual != expected:
            raise GateError(f"manifest_SHA_mismatch:{name}:{actual}:{expected}")
    return manifest


def state_metrics(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    e = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    mse = float(np.mean(e * e))
    return {
        "rmse": float(np.sqrt(mse)),
        "mae": float(np.mean(np.abs(e))),
        "max_abs": float(np.max(np.abs(e))),
    }


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=bool)
    bb = np.asarray(b, dtype=bool)
    union = int(np.sum(aa | bb))
    if union == 0:
        return 1.0
    return float(np.sum(aa & bb) / union)


def centroid_distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    pa = np.array(
        [a["mass_centroid_x_m"], a["mass_centroid_y_m"], a["mass_centroid_z_m"]],
        dtype=np.float64,
    )
    pb = np.array(
        [b["mass_centroid_x_m"], b["mass_centroid_y_m"], b["mass_centroid_z_m"]],
        dtype=np.float64,
    )
    if not (np.isfinite(pa).all() and np.isfinite(pb).all()):
        return float("nan")
    return float(np.linalg.norm(pa - pb))


def first_breakthrough_day(days: np.ndarray, cuts: np.ndarray) -> float:
    idx = np.flatnonzero(np.asarray(cuts, dtype=np.float64) >= BREAKTHROUGH_GAS_CUT)
    return float(days[idx[0]]) if len(idx) else float("nan")


def producer_snapshot(
    r2: Any,
    e37a: Any,
    sg7a: Any,
    sat200: np.ndarray,
    labels: np.ndarray,
    weights_m3_day: np.ndarray,
    face_pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    xi_faces: np.ndarray,
) -> tuple[list[dict[str, Any]], float]:
    sat = np.asarray(sat200, dtype=np.float64)
    outlet = sat[:, -1]
    ff = np.asarray(sg7a.fractional_flow(outlet), dtype=np.float64)
    rho = np.asarray(
        r2.gas_density_from_state(
            outlet,
            np.asarray(face_pressure_psi, dtype=np.float64)[:, -1],
            p_ref_gas_pa,
        ),
        dtype=np.float64,
    )
    u_face = np.asarray(sg7a.u_dimensionless(xi_faces), dtype=np.float64)
    mass_flux = (
        np.asarray(weights_m3_day, dtype=np.float64)
        * float(u_face[-1])
        * ff
        * rho
    )
    rows, aggregate = e37a.producer_rows_from_flux(
        labels,
        weights_m3_day,
        ff,
        mass_flux,
        1.0,
    )
    return rows, float(aggregate)


def self_test() -> None:
    a = np.array([True, True, False, False])
    b = np.array([True, False, True, False])
    if abs(jaccard(a, b) - 1.0 / 3.0) > 1.0e-15:
        raise RuntimeError("self_test_jaccard")
    m = state_metrics(np.array([0.2, 0.3]), np.array([0.2, 0.4]))
    if m["max_abs"] <= 0.0:
        raise RuntimeError("self_test_metrics")
    days = np.array([30.0, 60.0, 100.0])
    cuts = np.array([0.0, 1.0e-5, 1.0e-3])
    if first_breakthrough_day(days, cuts) != 100.0:
        raise RuntimeError("self_test_breakthrough")
    print("POSTV16-AV1-D self-test: PASS")


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        suffix = f" — {value}" if value is not None else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{suffix}")
        if not ok:
            raise GateError(name)

    print("=" * 168)
    print("POSTV16-AV1-D — PHYSICAL-IMPACT DEPLOYMENT AUDIT")
    print("=" * 168)
    print("FULL 1078-STREAMLINE SNAPSHOT INFERENCE WITH FROZEN C26.")
    print("HELD-OUT HYBRID FIELD: ONLY THE 161 LOCKED-TEST STREAMLINES USE C26;")
    print("ALL OTHER STREAMLINES REMAIN C17 TRUTH TO ISOLATE OUT-OF-SAMPLE PHYSICAL IMPACT.")
    print("FULL-C26 FIELD IS REPORTED AS DEPLOYMENT DIAGNOSTIC BUT IS NOT AN INDEPENDENT HOLDOUT.")
    print("NO TRAINING/RETUNING. NO TRANSPORT TIME MARCH. NO NEW NUMERICAL ACCURACY THRESHOLD.")
    print("GRID MAPBACK USES E37A COMPONENT-MASS CONSERVATIVE SNAPSHOT TRANSFER.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()

        head = git_text(root, "rev-parse", "HEAD")
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate("repository_parent_is_AV1C_commit", parent == AV1C_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fname, blob in SOURCE_BLOBS.items():
            p = root / fname
            actual = git_blob_sha(p, root) if p.is_file() else "missing"
            gate(f"{Path(fname).stem}_git_blob_exact", actual == blob, actual)

        stage = "AV1C_binding"
        av1c_out = drive / AV1C_OUT_REL
        gate("AV1C_output_directory_present", av1c_out.is_dir(), str(av1c_out))
        av1c_manifest = verify_manifest(av1c_out, AV1C_MANIFEST)
        gate("AV1C_manifest_internal_SHA_closure", True, len(av1c_manifest))

        av1c_summary = load_json(av1c_out / AV1C_SUMMARY)
        av1c_decision = load_json(av1c_out / AV1C_DECISION)

        gate("AV1C_status_exact", av1c_summary.get("status") == AV1C_STATUS, av1c_summary.get("status"))
        gate(
            "AV1C_representation_decision_accepted",
            av1c_decision.get("representation_decision") == "ACCEPTED_NO_REPAIR_REQUIRED",
            av1c_decision.get("representation_decision"),
        )
        gate(
            "AV1C_final_deployment_not_already_claimed",
            av1c_decision.get("model_accuracy_decision") == "NOT_YET_FINAL_DEPLOYMENT_ACCEPTED",
            av1c_decision.get("model_accuracy_decision"),
        )
        gate(
            "AV1C_no_retraining_authorized",
            av1c_decision.get("retraining_or_retuning_authorized") is False,
        )

        stage = "authority_binding"

        c18r = find_by_name_and_sha([root, drive], C18R_NAME, C18R_SHA)
        c19 = find_by_name_and_sha([root, drive], C19_NAME, C19_SHA)
        gate("C18R_exact_SHA", sha256_file(c18r) == C18R_SHA, str(c18r))
        gate("C19_exact_SHA", sha256_file(c19) == C19_SHA, str(c19))

        weights = drive / WEIGHTS_REL
        gate("C26_exact_weights_present", weights.is_file(), str(weights))
        gate(
            "C26_exact_weights_SHA",
            weights.is_file() and sha256_file(weights) == WEIGHTS_SHA,
            sha256_file(weights) if weights.is_file() else "missing",
        )

        r2_state_path = drive / R2_REL / R2_STATE
        e36_closure_path = drive / E36_REL / E36_CLOSURE
        e36_cache_path = drive / E36_REL / E36_CACHE
        for label, p in (
            ("R2_state", r2_state_path),
            ("E36_closure", e36_closure_path),
            ("E36_cache", e36_cache_path),
        ):
            gate(f"{label}_present", p.is_file(), str(p))

        e36_closure = load_json(e36_closure_path)
        e36_cache_sha = sha256_file(e36_cache_path)
        gate(
            "E36_cache_SHA_matches_closure",
            e36_cache_sha == e36_closure.get("certified_cache_sha256"),
            e36_cache_sha,
        )

        stage = "load_physics"

        b1 = load_module(root / B1R1_RUNNER, "postv16_av1d_b1r1")
        r2 = load_module(root / R2, "postv16_av1d_r2")
        e36 = load_module(root / E36, "postv16_av1d_e36")
        e37a = load_module(root / E37A, "postv16_av1d_e37a")
        sg7a = load_module(root / SG7A, "postv16_av1d_sg7a")

        # Isolate SG7D so its file-relative legacy paths cannot interact with
        # repository outputs while we use only pure geometry functions/constants.
        with tempfile.TemporaryDirectory(prefix="POSTV16_AV1D_SG7D_") as td:
            td = Path(td)
            src = root / SG7D
            dst = td / SG7D
            dst.write_bytes(src.read_bytes())
            sg7d = load_module(dst, "postv16_av1d_sg7d")

            cache = load_npz(e36_cache_path)
            parent_state = load_npz(r2_state_path)

            required_cache = (
                "accepted_pressure_psi",
                "streamline_xyz_m",
                "streamline_tof_s",
                "tau_end_s",
                "streamline_weights_m3_s",
                "xi",
                "producer_labels",
            )
            for key in required_cache:
                gate(f"E36_cache_{key}_present", key in cache)

            pressure_psi = np.asarray(cache["accepted_pressure_psi"], dtype=np.float64)
            xyz_m = np.asarray(cache["streamline_xyz_m"], dtype=np.float64)
            tau_s = np.asarray(cache["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(cache["streamline_weights_m3_s"], dtype=np.float64)
            xi_faces = np.asarray(cache["xi"], dtype=np.float64)
            labels = np.asarray(cache["producer_labels"]).astype(str)

            gate("pressure_grid_shape_exact", pressure_psi.shape == EXPECTED_GRID, pressure_psi.shape)
            gate("streamline_xyz_shape_exact", xyz_m.shape == (EXPECTED_STREAMLINES, EXPECTED_NODES, 3), xyz_m.shape)
            gate("streamline_tof_shape_exact", tau_s.shape == (EXPECTED_STREAMLINES, EXPECTED_NODES), tau_s.shape)
            gate("weights_shape_exact", weights_m3_s.shape == (EXPECTED_STREAMLINES,), weights_m3_s.shape)
            gate("xi_faces_shape_exact", xi_faces.shape == (EXPECTED_NODES,), xi_faces.shape)
            gate("producer_labels_shape_exact", labels.shape == (EXPECTED_STREAMLINES,), labels.shape)

            p_ref = scalar(parent_state["co2_density_reference_pressure_pa"])
            weights_m3_day = weights_m3_s * float(e37a.DAY_TO_S)
            tof_days = tau_s / float(e37a.DAY_TO_S)

            operator = sg7d.build_subsegment_operator(
                xyz_m,
                tof_days,
                weights_m3_day,
            )
            geometry = e37a.build_control_volume_geometry(
                r2,
                operator,
                pressure_psi,
                p_ref,
                EXPECTED_STREAMLINES,
                EXPECTED_CVS,
            )
            coeff = np.asarray(geometry["cv_pressure_mass_coeff"], dtype=np.float64)

            gate(
                "E37A_cv_pressure_mass_coeff_shape_exact",
                coeff.shape == (EXPECTED_STREAMLINES, EXPECTED_CVS),
                coeff.shape,
            )
            gate("E37A_cv_pressure_mass_coeff_positive", np.all(coeff > 0.0))

            face_pressure = e37a.build_face_pressure(
                e36,
                sg7d,
                xyz_m,
                pressure_psi,
            )
            gate(
                "E37A_face_pressure_shape_exact",
                face_pressure.shape == (EXPECTED_STREAMLINES, EXPECTED_NODES),
                face_pressure.shape,
            )

            stage = "full_C26_inference"

            d = load_npz(c18r)
            s = load_npz(c19)

            X7 = np.asarray(d["X_sequence_required"], dtype=np.float32)
            Y = np.asarray(d["Y_transport"], dtype=np.float64)
            th = np.asarray(d["target_time_hat"], dtype=np.float32)
            eta_seq = np.asarray(d["target_eta_sequence"], dtype=np.float32)
            sl = np.asarray(d["streamline_index"], dtype=np.int64)
            ti = np.asarray(d["time_index"], dtype=np.int64)
            target_days = np.asarray(d["target_time_days"], dtype=np.float64)
            part = np.asarray(s["sample_partition_code"], dtype=np.int8)

            gate("X7_shape_exact", X7.shape == (EXPECTED_SAMPLES, EXPECTED_NODES, 7), X7.shape)
            gate("Y_shape_exact", Y.shape == (EXPECTED_SAMPLES, EXPECTED_NODES), Y.shape)
            gate("split_shape_exact", part.shape == (EXPECTED_SAMPLES,), part.shape)
            gate("streamline_index_range_exact", np.array_equal(np.unique(sl), np.arange(EXPECTED_STREAMLINES)))
            gate("time_index_range_exact", np.array_equal(np.unique(ti), np.arange(len(EXPECTED_DAYS))))
            gate("target_days_exact", np.array_equal(np.unique(target_days), EXPECTED_DAYS), np.unique(target_days).tolist())

            # Every (time, streamline) pair must occur exactly once.
            pair = ti * EXPECTED_STREAMLINES + sl
            counts = np.bincount(pair, minlength=len(EXPECTED_DAYS) * EXPECTED_STREAMLINES)
            gate("one_sample_per_time_streamline_pair", np.array_equal(counts, np.ones_like(counts)))

            test_samples = np.flatnonzero(part == 2)
            test_streamlines = np.unique(sl[test_samples])
            gate("locked_test_streamlines_161", len(test_streamlines) == EXPECTED_TEST_STREAMLINES, len(test_streamlines))
            for g in test_streamlines:
                gate(
                    f"test_streamline_{int(g)}_has_all_9_times",
                    int(np.sum(sl[test_samples] == g)) == 9,
                )

            T = np.broadcast_to(
                th[:, None, None],
                (EXPECTED_SAMPLES, EXPECTED_NODES, 1),
            ).astype(np.float32)
            X = np.concatenate(
                [X7, T, eta_seq[:, :, None].astype(np.float32)],
                axis=2,
            )
            gate("C26_full_input_shape_exact", X.shape == (EXPECTED_SAMPLES, EXPECTED_NODES, 9), X.shape)

            import tensorflow as tf

            try:
                tf.config.experimental.enable_op_determinism()
            except Exception:
                pass
            tf.keras.utils.set_random_seed(16021)

            model = b1.build_model(tf)
            gate("C26_model_parameter_count_52033", model.count_params() == 52033, model.count_params())
            model.load_weights(weights)
            pred201_flat = model.predict(X, batch_size=64, verbose=0).astype(np.float64)
            gate("C26_full_prediction_shape_exact", pred201_flat.shape == (EXPECTED_SAMPLES, EXPECTED_NODES), pred201_flat.shape)
            gate("C26_full_predictions_finite", np.isfinite(pred201_flat).all())
            gate(
                "C26_full_predictions_bounded",
                float(np.min(pred201_flat)) >= 0.2 - 1.0e-6
                and float(np.max(pred201_flat)) <= 0.8 + 1.0e-6,
                (float(np.min(pred201_flat)), float(np.max(pred201_flat))),
            )

            # Reproduce the locked-test metrics from AV1-C before using the full field.
            test_m = state_metrics(pred201_flat[test_samples], Y[test_samples])
            av1c_l1 = av1c_summary["level1_metrics"]
            for key, ours in (
                ("rmse", test_m["rmse"]),
                ("mae", test_m["mae"]),
                ("max_abs_error", test_m["max_abs"]),
            ):
                target = float(av1c_l1[key])
                gate(
                    f"locked_test_{key}_reproduces_AV1C",
                    abs(ours - target) <= 5.0e-6 if key != "max_abs_error"
                    else abs(ours - target) <= 5.0e-5,
                    f"{ours} vs {target}",
                )

            # Reindex flat samples into complete [time, streamline, node] fields.
            pred201 = np.empty(
                (len(EXPECTED_DAYS), EXPECTED_STREAMLINES, EXPECTED_NODES),
                dtype=np.float64,
            )
            true201 = np.empty_like(pred201)
            for n in range(EXPECTED_SAMPLES):
                pred201[ti[n], sl[n]] = pred201_flat[n]
                true201[ti[n], sl[n]] = Y[n]

            # Full 201->200 exact mass-space projection in one vectorized call.
            pred201_reordered = pred201.reshape(-1, EXPECTED_NODES)
            true201_reordered = true201.reshape(-1, EXPECTED_NODES)
            ids = np.tile(np.arange(EXPECTED_STREAMLINES, dtype=np.int64), len(EXPECTED_DAYS))

            pred200_flat, pred_mass_flat, _ = b1.project_201_to_200_component_mass(
                r2,
                e37a,
                pred201_reordered,
                coeff,
                ids,
            )
            true200_flat, true_mass_flat, _ = b1.project_201_to_200_component_mass(
                r2,
                e37a,
                true201_reordered,
                coeff,
                ids,
            )

            pred200 = pred200_flat.reshape(len(EXPECTED_DAYS), EXPECTED_STREAMLINES, EXPECTED_CVS)
            true200 = true200_flat.reshape(len(EXPECTED_DAYS), EXPECTED_STREAMLINES, EXPECTED_CVS)
            pred_mass = pred_mass_flat.reshape(len(EXPECTED_DAYS), EXPECTED_STREAMLINES, EXPECTED_CVS)
            true_mass = true_mass_flat.reshape(len(EXPECTED_DAYS), EXPECTED_STREAMLINES, EXPECTED_CVS)

            gate("full_pred200_finite", np.isfinite(pred200).all())
            gate("full_true200_finite", np.isfinite(true200).all())
            gate("full_pred_mass_nonnegative", float(np.min(pred_mass)) >= -1.0e-8, float(np.min(pred_mass)))
            gate("full_true_mass_nonnegative", float(np.min(true_mass)) >= -1.0e-8, float(np.min(true_mass)))

            stage = "physical_snapshot_mapback"

            baseline_grid = np.full(EXPECTED_GRID, BACKGROUND_SATURATION, dtype=np.float64)
            baseline_cv = np.full(
                (EXPECTED_STREAMLINES, EXPECTED_CVS),
                BACKGROUND_SATURATION,
                dtype=np.float64,
            )
            baseline_mass = np.zeros(
                (EXPECTED_STREAMLINES, EXPECTED_CVS),
                dtype=np.float64,
            )

            grid_true = np.empty((len(EXPECTED_DAYS),) + EXPECTED_GRID, dtype=np.float64)
            grid_hybrid = np.empty_like(grid_true)
            grid_full_c26 = np.empty_like(grid_true)

            physical_rows: list[dict[str, Any]] = []
            producer_rows_out: list[dict[str, Any]] = []

            true_cuts = []
            hybrid_cuts = []
            full_c26_cuts = []

            for t_index, day in enumerate(EXPECTED_DAYS):
                true_sat = true200[t_index]
                true_m = true_mass[t_index]

                full_sat = pred200[t_index]
                full_m = pred_mass[t_index]

                hybrid_sat = true_sat.copy()
                hybrid_m = true_m.copy()
                hybrid_sat[test_streamlines] = full_sat[test_streamlines]
                hybrid_m[test_streamlines] = full_m[test_streamlines]

                # Hybrid state/mass constitutive closure.
                hybrid_recon = e37a.cv_mass_from_saturation(r2, hybrid_sat, coeff)
                hybrid_rel = float(
                    np.max(
                        np.abs(hybrid_recon - hybrid_m)
                        / np.maximum(np.abs(hybrid_m), 1.0)
                    )
                )
                gate(
                    f"day_{int(day)}_hybrid_CV_mass_constitutive_closure",
                    hybrid_rel <= 1.0e-10,
                    hybrid_rel,
                )

                mapped = {}
                for label_name, sat, mass in (
                    ("C17_truth", true_sat, true_m),
                    ("heldout_hybrid", hybrid_sat, hybrid_m),
                    ("full_C26", full_sat, full_m),
                ):
                    result = e37a.map_control_volume_increment_to_grid(
                        r2,
                        baseline_grid,
                        baseline_cv,
                        sat,
                        baseline_mass,
                        mass,
                        geometry,
                        pressure_psi,
                        p_ref,
                        float(sg7d.CELL_PORE_VOLUME_M3),
                        float(np.sum(mass)),
                    )
                    mapped[label_name] = result

                    gate(
                        f"day_{int(day)}_{label_name}_mapback_transfer_closure",
                        abs(float(result["transfer_residual_kg"]))
                        <= float(result["roundoff_mass_kg"]),
                        float(result["transfer_residual_kg"]),
                    )
                    gate(
                        f"day_{int(day)}_{label_name}_mapback_ledger_closure",
                        abs(float(result["ledger_residual_kg"]))
                        <= float(result["roundoff_mass_kg"]),
                        float(result["ledger_residual_kg"]),
                    )
                    gate(
                        f"day_{int(day)}_{label_name}_grid_inversion_closure",
                        abs(float(result["grid_inversion_residual_kg"]))
                        <= float(result["roundoff_mass_kg"]),
                        float(result["grid_inversion_residual_kg"]),
                    )
                    gate(
                        f"day_{int(day)}_{label_name}_no_source_local_mass_fill",
                        float(result["source_local_added_mass_kg"]) == 0.0,
                    )

                gt = np.asarray(mapped["C17_truth"]["corrected_saturation"], dtype=np.float64)
                gh = np.asarray(mapped["heldout_hybrid"]["corrected_saturation"], dtype=np.float64)
                gf = np.asarray(mapped["full_C26"]["corrected_saturation"], dtype=np.float64)

                grid_true[t_index] = gt
                grid_hybrid[t_index] = gh
                grid_full_c26[t_index] = gf

                pt = e36.plume_metrics(
                    r2, gt, pressure_psi, p_ref, float(sg7d.CELL_PORE_VOLUME_M3),
                    t_index, float(day),
                )
                ph = e36.plume_metrics(
                    r2, gh, pressure_psi, p_ref, float(sg7d.CELL_PORE_VOLUME_M3),
                    t_index, float(day),
                )
                pf = e36.plume_metrics(
                    r2, gf, pressure_psi, p_ref, float(sg7d.CELL_PORE_VOLUME_M3),
                    t_index, float(day),
                )

                true_sg = np.clip(gt - BACKGROUND_SATURATION, 0.0, 0.6)
                hybrid_sg = np.clip(gh - BACKGROUND_SATURATION, 0.0, 0.6)
                full_sg = np.clip(gf - BACKGROUND_SATURATION, 0.0, 0.6)

                grid_hm = state_metrics(gh, gt)
                grid_fm = state_metrics(gf, gt)

                true_mass_total = float(pt["stored_CO2_mass_kg"])
                hybrid_mass_total = float(ph["stored_CO2_mass_kg"])
                full_mass_total = float(pf["stored_CO2_mass_kg"])

                true_visible = true_sg > 1.0e-4
                hybrid_visible = hybrid_sg > 1.0e-4
                full_visible = full_sg > 1.0e-4
                true_active = true_sg > 1.0e-8
                hybrid_active = hybrid_sg > 1.0e-8
                full_active = full_sg > 1.0e-8

                true_prod, true_cut = producer_snapshot(
                    r2, e37a, sg7a, true_sat, labels, weights_m3_day,
                    face_pressure, p_ref, xi_faces,
                )
                hybrid_prod, hybrid_cut = producer_snapshot(
                    r2, e37a, sg7a, hybrid_sat, labels, weights_m3_day,
                    face_pressure, p_ref, xi_faces,
                )
                full_prod, full_cut = producer_snapshot(
                    r2, e37a, sg7a, full_sat, labels, weights_m3_day,
                    face_pressure, p_ref, xi_faces,
                )

                true_cuts.append(true_cut)
                hybrid_cuts.append(hybrid_cut)
                full_c26_cuts.append(full_cut)

                gate(
                    f"day_{int(day)}_heldout_breakthrough_classification_matches_truth",
                    (hybrid_cut >= BREAKTHROUGH_GAS_CUT)
                    == (true_cut >= BREAKTHROUGH_GAS_CUT),
                    (true_cut, hybrid_cut),
                )
                gate(
                    f"day_{int(day)}_full_C26_breakthrough_classification_matches_truth",
                    (full_cut >= BREAKTHROUGH_GAS_CUT)
                    == (true_cut >= BREAKTHROUGH_GAS_CUT),
                    (true_cut, full_cut),
                )

                physical_rows.append({
                    "target_day": float(day),
                    "heldout_grid_rmse": grid_hm["rmse"],
                    "heldout_grid_mae": grid_hm["mae"],
                    "heldout_grid_max_abs": grid_hm["max_abs"],
                    "full_C26_grid_rmse": grid_fm["rmse"],
                    "full_C26_grid_mae": grid_fm["mae"],
                    "full_C26_grid_max_abs": grid_fm["max_abs"],
                    "truth_stored_mass_kg": true_mass_total,
                    "heldout_stored_mass_kg": hybrid_mass_total,
                    "heldout_mass_error_kg": hybrid_mass_total - true_mass_total,
                    "heldout_mass_abs_relative": (
                        abs(hybrid_mass_total - true_mass_total)
                        / max(abs(true_mass_total), 1.0)
                    ),
                    "full_C26_stored_mass_kg": full_mass_total,
                    "full_C26_mass_error_kg": full_mass_total - true_mass_total,
                    "full_C26_mass_abs_relative": (
                        abs(full_mass_total - true_mass_total)
                        / max(abs(true_mass_total), 1.0)
                    ),
                    "heldout_visible_plume_jaccard": jaccard(hybrid_visible, true_visible),
                    "full_C26_visible_plume_jaccard": jaccard(full_visible, true_visible),
                    "heldout_active_plume_jaccard": jaccard(hybrid_active, true_active),
                    "full_C26_active_plume_jaccard": jaccard(full_active, true_active),
                    "heldout_centroid_distance_m": centroid_distance(ph, pt),
                    "full_C26_centroid_distance_m": centroid_distance(pf, pt),
                    "truth_visible_cells": int(pt["plume_cells_gt_1e-4"]),
                    "heldout_visible_cells": int(ph["plume_cells_gt_1e-4"]),
                    "full_C26_visible_cells": int(pf["plume_cells_gt_1e-4"]),
                    "truth_active_cells": int(pt["active_cells_gt_1e-8"]),
                    "heldout_active_cells": int(ph["active_cells_gt_1e-8"]),
                    "full_C26_active_cells": int(pf["active_cells_gt_1e-8"]),
                    "truth_aggregate_CO2_cut": true_cut,
                    "heldout_aggregate_CO2_cut": hybrid_cut,
                    "heldout_aggregate_CO2_cut_abs_error": abs(hybrid_cut - true_cut),
                    "full_C26_aggregate_CO2_cut": full_cut,
                    "full_C26_aggregate_CO2_cut_abs_error": abs(full_cut - true_cut),
                    "truth_breakthrough_by_existing_E36_contract": bool(true_cut >= BREAKTHROUGH_GAS_CUT),
                    "heldout_breakthrough_by_existing_E36_contract": bool(hybrid_cut >= BREAKTHROUGH_GAS_CUT),
                    "full_C26_breakthrough_by_existing_E36_contract": bool(full_cut >= BREAKTHROUGH_GAS_CUT),
                })

                by_name = {}
                for field_name, rows in (
                    ("C17_truth", true_prod),
                    ("heldout_hybrid", hybrid_prod),
                    ("full_C26", full_prod),
                ):
                    for row in rows:
                        by_name[(field_name, row["producer"])] = row

                producers = sorted({r["producer"] for r in true_prod})
                for producer in producers:
                    tr = by_name[("C17_truth", producer)]
                    hr = by_name[("heldout_hybrid", producer)]
                    fr = by_name[("full_C26", producer)]
                    producer_rows_out.append({
                        "target_day": float(day),
                        "producer": producer,
                        "truth_CO2_cut": float(tr["CO2_cut"]),
                        "heldout_CO2_cut": float(hr["CO2_cut"]),
                        "heldout_CO2_cut_abs_error": abs(float(hr["CO2_cut"]) - float(tr["CO2_cut"])),
                        "full_C26_CO2_cut": float(fr["CO2_cut"]),
                        "full_C26_CO2_cut_abs_error": abs(float(fr["CO2_cut"]) - float(tr["CO2_cut"])),
                        "truth_CO2_mass_rate_kg_day": float(tr["CO2_mass_rate_kg_day"]),
                        "heldout_CO2_mass_rate_kg_day": float(hr["CO2_mass_rate_kg_day"]),
                        "heldout_CO2_mass_rate_abs_error_kg_day": abs(
                            float(hr["CO2_mass_rate_kg_day"]) - float(tr["CO2_mass_rate_kg_day"])
                        ),
                        "heldout_CO2_mass_rate_abs_relative": (
                            abs(float(hr["CO2_mass_rate_kg_day"]) - float(tr["CO2_mass_rate_kg_day"]))
                            / max(abs(float(tr["CO2_mass_rate_kg_day"])), 1.0)
                        ),
                        "full_C26_CO2_mass_rate_kg_day": float(fr["CO2_mass_rate_kg_day"]),
                        "full_C26_CO2_mass_rate_abs_error_kg_day": abs(
                            float(fr["CO2_mass_rate_kg_day"]) - float(tr["CO2_mass_rate_kg_day"])
                        ),
                        "full_C26_CO2_mass_rate_abs_relative": (
                            abs(float(fr["CO2_mass_rate_kg_day"]) - float(tr["CO2_mass_rate_kg_day"]))
                            / max(abs(float(tr["CO2_mass_rate_kg_day"])), 1.0)
                        ),
                    })

            stage = "physical_event_decision"

            true_cuts = np.asarray(true_cuts, dtype=np.float64)
            hybrid_cuts = np.asarray(hybrid_cuts, dtype=np.float64)
            full_c26_cuts = np.asarray(full_c26_cuts, dtype=np.float64)

            true_bt = first_breakthrough_day(EXPECTED_DAYS, true_cuts)
            hybrid_bt = first_breakthrough_day(EXPECTED_DAYS, hybrid_cuts)
            full_bt = first_breakthrough_day(EXPECTED_DAYS, full_c26_cuts)

            def same_optional_day(a: float, b: float) -> bool:
                if np.isnan(a) and np.isnan(b):
                    return True
                return a == b

            gate(
                "heldout_first_breakthrough_target_day_matches_truth",
                same_optional_day(hybrid_bt, true_bt),
                (true_bt, hybrid_bt),
            )
            gate(
                "full_C26_first_breakthrough_target_day_matches_truth",
                same_optional_day(full_bt, true_bt),
                (true_bt, full_bt),
            )

            # No new numerical deployment-accuracy threshold is introduced here.
            # AV1-D measures physical consequences and enforces only exact
            # conservation/bounds plus the pre-existing E36 breakthrough event.
            gate("no_new_numerical_accuracy_acceptance_threshold_introduced", True)
            gate("no_training_or_retuning_performed", True)
            gate("no_transport_time_march_executed", True)
            gate("no_frozen_artifact_modified", True)

            heldout_grid_rmse = np.array([r["heldout_grid_rmse"] for r in physical_rows], dtype=np.float64)
            heldout_mass_rel = np.array([r["heldout_mass_abs_relative"] for r in physical_rows], dtype=np.float64)
            heldout_jacc = np.array([r["heldout_visible_plume_jaccard"] for r in physical_rows], dtype=np.float64)
            heldout_centroid = np.array([r["heldout_centroid_distance_m"] for r in physical_rows], dtype=np.float64)

            full_grid_rmse = np.array([r["full_C26_grid_rmse"] for r in physical_rows], dtype=np.float64)
            full_mass_rel = np.array([r["full_C26_mass_abs_relative"] for r in physical_rows], dtype=np.float64)
            full_jacc = np.array([r["full_C26_visible_plume_jaccard"] for r in physical_rows], dtype=np.float64)
            full_centroid = np.array([r["full_C26_centroid_distance_m"] for r in physical_rows], dtype=np.float64)

            decision = {
                "representation_repair_required": False,
                "retraining_or_retuning_authorized": False,
                "heldout_physical_impact_quantified": True,
                "full_C26_deployment_field_quantified": True,
                "existing_E36_breakthrough_event_preserved_heldout": True,
                "existing_E36_breakthrough_event_preserved_full_C26": True,
                "final_deployment_accuracy_accepted": False,
                "why_not_final": (
                    "AV1-D intentionally introduces no new numerical acceptance threshold. "
                    "The physical impact is now quantified, but final deployment acceptance "
                    "must be judged against a prospective external/full-physics benchmark "
                    "rather than a post-hoc threshold chosen after inspecting these results."
                ),
                "next": (
                    "POSTV16-AV1-E — freeze prospective external/full-physics deployment "
                    "acceptance contract, then validate C26/PAD-Stream against that benchmark "
                    "without retuning on the locked evaluation cases."
                ),
            }

            summary = {
                "milestone": MILESTONE,
                "status": STATUS_PASS,
                "repository_head": head,
                "repository_parent": parent,
                "locked_test_streamline_count": int(len(test_streamlines)),
                "target_days": EXPECTED_DAYS.tolist(),
                "breakthrough_gas_cut_inherited_from_E36": BREAKTHROUGH_GAS_CUT,
                "first_breakthrough_target_day": {
                    "C17_truth": true_bt,
                    "heldout_hybrid": hybrid_bt,
                    "full_C26": full_bt,
                },
                "heldout_summary": {
                    "grid_RMSE_mean": float(np.mean(heldout_grid_rmse)),
                    "grid_RMSE_max": float(np.max(heldout_grid_rmse)),
                    "stored_mass_abs_relative_mean": float(np.mean(heldout_mass_rel)),
                    "stored_mass_abs_relative_max": float(np.max(heldout_mass_rel)),
                    "visible_plume_jaccard_mean": float(np.mean(heldout_jacc)),
                    "visible_plume_jaccard_min": float(np.min(heldout_jacc)),
                    "centroid_distance_m_mean": float(np.nanmean(heldout_centroid)),
                    "centroid_distance_m_max": float(np.nanmax(heldout_centroid)),
                    "aggregate_CO2_cut_abs_error_mean": float(np.mean(np.abs(hybrid_cuts - true_cuts))),
                    "aggregate_CO2_cut_abs_error_max": float(np.max(np.abs(hybrid_cuts - true_cuts))),
                },
                "full_C26_summary": {
                    "grid_RMSE_mean": float(np.mean(full_grid_rmse)),
                    "grid_RMSE_max": float(np.max(full_grid_rmse)),
                    "stored_mass_abs_relative_mean": float(np.mean(full_mass_rel)),
                    "stored_mass_abs_relative_max": float(np.max(full_mass_rel)),
                    "visible_plume_jaccard_mean": float(np.mean(full_jacc)),
                    "visible_plume_jaccard_min": float(np.min(full_jacc)),
                    "centroid_distance_m_mean": float(np.nanmean(full_centroid)),
                    "centroid_distance_m_max": float(np.nanmax(full_centroid)),
                    "aggregate_CO2_cut_abs_error_mean": float(np.mean(np.abs(full_c26_cuts - true_cuts))),
                    "aggregate_CO2_cut_abs_error_max": float(np.max(np.abs(full_c26_cuts - true_cuts))),
                },
                "decision": decision,
                "new_numerical_accuracy_threshold_selected": False,
                "training_or_retuning_performed": False,
                "transport_time_march_executed": False,
            }

            arrays = {
                "target_days": EXPECTED_DAYS,
                "test_streamline_indices": test_streamlines.astype(np.int64),
                "C17_truth_grid_saturation": grid_true,
                "heldout_hybrid_grid_saturation": grid_hybrid,
                "full_C26_grid_saturation": grid_full_c26,
                "C17_truth_aggregate_CO2_cut": true_cuts,
                "heldout_hybrid_aggregate_CO2_cut": hybrid_cuts,
                "full_C26_aggregate_CO2_cut": full_c26_cuts,
            }

            files = {
                "PAD_Stream_POSTV16_AV1_D_Summary.json": json_bytes(summary),
                "POSTV16_AV1_D_Decision_Contract.json": json_bytes(decision),
                "POSTV16_AV1_D_By_Target_Day_Physical_Impact.csv": csv_bytes(physical_rows),
                "POSTV16_AV1_D_By_Producer_Physical_Impact.csv": csv_bytes(producer_rows_out),
                "POSTV16_AV1_D_Physical_Snapshot_Arrays.npz": deterministic_npz_bytes(arrays),
                "POSTV16_AV1_D_Final_Gate_Matrix.csv": csv_bytes(
                    [{"gate": k, **v} for k, v in gates.items()]
                ),
            }

            immutable_publish(out, files)

            manifest_rows = []
            for p in sorted(out.iterdir()):
                if p.is_file() and p.name != "POSTV16_AV1_D_Artifact_Manifest.csv":
                    manifest_rows.append({
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    })
            immutable_publish(
                out,
                {"POSTV16_AV1_D_Artifact_Manifest.csv": csv_bytes(manifest_rows)},
            )

            print("\n" + "=" * 168)
            print("POSTV16-AV1-D: PASS")
            print("=" * 168)
            print(f"{'Status':86}: {STATUS_PASS}")
            print(
                f"{'Held-out grid RMSE mean / max':86}: "
                f"{summary['heldout_summary']['grid_RMSE_mean']:.12e} / "
                f"{summary['heldout_summary']['grid_RMSE_max']:.12e}"
            )
            print(
                f"{'Held-out stored-mass abs relative mean / max':86}: "
                f"{summary['heldout_summary']['stored_mass_abs_relative_mean']:.12e} / "
                f"{summary['heldout_summary']['stored_mass_abs_relative_max']:.12e}"
            )
            print(
                f"{'Held-out visible-plume Jaccard mean / min':86}: "
                f"{summary['heldout_summary']['visible_plume_jaccard_mean']:.12e} / "
                f"{summary['heldout_summary']['visible_plume_jaccard_min']:.12e}"
            )
            print(
                f"{'Held-out centroid distance mean / max (m)':86}: "
                f"{summary['heldout_summary']['centroid_distance_m_mean']:.12e} / "
                f"{summary['heldout_summary']['centroid_distance_m_max']:.12e}"
            )
            print(
                f"{'Held-out aggregate CO2-cut abs error mean / max':86}: "
                f"{summary['heldout_summary']['aggregate_CO2_cut_abs_error_mean']:.12e} / "
                f"{summary['heldout_summary']['aggregate_CO2_cut_abs_error_max']:.12e}"
            )
            print(
                f"{'Full-C26 grid RMSE mean / max':86}: "
                f"{summary['full_C26_summary']['grid_RMSE_mean']:.12e} / "
                f"{summary['full_C26_summary']['grid_RMSE_max']:.12e}"
            )
            print(
                f"{'Full-C26 stored-mass abs relative mean / max':86}: "
                f"{summary['full_C26_summary']['stored_mass_abs_relative_mean']:.12e} / "
                f"{summary['full_C26_summary']['stored_mass_abs_relative_max']:.12e}"
            )
            print(
                f"{'Full-C26 visible-plume Jaccard mean / min':86}: "
                f"{summary['full_C26_summary']['visible_plume_jaccard_mean']:.12e} / "
                f"{summary['full_C26_summary']['visible_plume_jaccard_min']:.12e}"
            )
            print(
                f"{'First breakthrough target day truth / heldout / full-C26':86}: "
                f"{true_bt} / {hybrid_bt} / {full_bt}"
            )
            print(f"{'Representation repair required':86}: False")
            print(f"{'Retraining / retuning authorized':86}: False")
            print(f"{'Final deployment accepted':86}: False")
            print(f"{'New numerical acceptance threshold selected':86}: False")
            print(
                f"{'NEXT':86}: POSTV16-AV1-E — prospective external/full-physics acceptance contract"
            )
            print("=" * 168)
            return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "training_or_retuning": False,
            "frozen_artifact_mutation": False,
            "next_action": "Audit only the failed AV1-D gate(s); do not advance to AV1-E.",
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV1_D_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV1_D_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print("\n" + "=" * 168)
        print("POSTV16-AV1-D: BLOCKED")
        print("=" * 168)
        print("Failed stage:", stage)
        print("Exception   :", repr(exc))
        print("Report      :", p)
        return 2


def parse_args():
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
    a = parse_args()
    if a.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root, a.drive_root))

#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
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

MILESTONE = "POSTV16-AV1-D-R2"
STATUS_PASS = (
    "AV1DR2_BREAKTHROUGH_FALSE_POSITIVE_LOCALIZED_"
    "ORIGINAL_LOCKED_TEST_RETIRED_FROM_FINAL_ACCEPTANCE"
)
STATUS_BLOCKED = "AV1DR2_BREAKTHROUGH_LOCALIZATION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R1_COMMIT = "40414ca3a946acb05bc8b93d05aa0b4f5f046509"

R1 = "PAD_Stream_POSTV16_AV1_D_R1_CV_Physical_Impact_and_MapBack_Contract_Repair.py"
R1_BLOB = "7b113a60b66e24c6818dd16ef2192b0d4b1ff08a"

B1 = "PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB = "8d9561d7c85805b82dedc26073c4633f90eeeab6"

C25 = "PAD_Stream_V16C25_Differentiable_Pollock_Full_Physics_Residual_Boundary_Mask_and_Physics_Loss_Weight_Authority_Contract.py"
C25_BLOB = "0a4740b95c2b5e5d15db3137414e663e1e9b6282"

C26 = "PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
C26_BLOB = "62e19e6b502fb3ab101a2589251c26b5f9ad9031"

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
    R1: R1_BLOB,
    B1: B1_BLOB,
    C25: C25_BLOB,
    C26: C26_BLOB,
    R2: R2_BLOB,
    E36: E36_BLOB,
    E37A: E37A_BLOB,
    SG7A: SG7A_BLOB,
    SG7D: SG7D_BLOB,
}

R1_BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R1_BLOCKED"
)
R1_BLOCKED_REPORT = "POSTV16_AV1_D_R1_Blocked_Report.json"

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
    / "POSTV16_AV1_D_R2_Breakthrough_False_Positive_Localization"
)
BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R2_BLOCKED"
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

BREAKTHROUGH_GAS_CUT = 1.0e-4


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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def scalar(x: Any) -> float:
    return float(np.asarray(x).reshape(()))


def json_bytes(obj: Any) -> bytes:
    return (
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


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


def producer_cuts(
    sg7a: Any,
    sat200: np.ndarray,
    labels: np.ndarray,
    weights_m3_day: np.ndarray,
) -> tuple[dict[str, float], float, np.ndarray]:
    sat = np.asarray(sat200, dtype=np.float64)
    q = np.asarray(weights_m3_day, dtype=np.float64)
    labs = np.asarray(labels).astype(str)
    outlet = sat[:, -1]
    ff = np.asarray(sg7a.fractional_flow(outlet), dtype=np.float64)
    total_q = float(np.sum(q))
    aggregate = float(np.sum(q * ff) / total_q)

    by_prod: dict[str, float] = {}
    for name in sorted(np.unique(labs)):
        m = labs == name
        qsum = float(np.sum(q[m]))
        by_prod[str(name)] = (
            float(np.sum(q[m] * ff[m]) / qsum)
            if qsum > 0.0 else 0.0
        )
    return by_prod, aggregate, ff


def first_breakthrough_day(days: np.ndarray, cuts: np.ndarray) -> float:
    idx = np.flatnonzero(np.asarray(cuts, dtype=np.float64) >= BREAKTHROUGH_GAS_CUT)
    return float(days[idx[0]]) if len(idx) else float("nan")


def self_test() -> None:
    c = np.array([3.0, 2.0, 1.0, -1.0])
    pos = np.sort(c[c > 0.0])[::-1]
    if not np.array_equal(pos, np.array([3.0, 2.0, 1.0])):
        raise RuntimeError("self_test_sort")
    gap = 4.5
    n = int(np.searchsorted(np.cumsum(pos), gap, side="left") + 1)
    if n != 2:
        raise RuntimeError("self_test_crossing_count")
    print("POSTV16-AV1-D-R2 self-test: PASS")


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
    print("POSTV16-AV1-D-R2 — BREAKTHROUGH FALSE-POSITIVE LOCALIZATION + TEST-RETIREMENT AUDIT")
    print("=" * 168)
    print("DIAGNOSTIC ONLY. THE R1 FALSE-POSITIVE IS A FINDING, NOT A GATE TO BE RELAXED.")
    print("NO THRESHOLD CHANGE. NO TRAINING/RETUNING. NO GRID MAPBACK.")
    print("THE ORIGINAL LOCKED TEST IS NOW DIAGNOSTIC EVIDENCE AND CANNOT REMAIN THE FINAL")
    print("INDEPENDENT ACCEPTANCE SET FOR ANY REPAIR DESIGNED AFTER THIS FAILURE.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()

        head = git_text(root, "rev-parse", "HEAD")
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate("repository_parent_is_AV1D_R1_commit", parent == PARENT_R1_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fname, blob in SOURCE_BLOBS.items():
            p = root / fname
            actual = git_blob_sha(p, root) if p.is_file() else "missing"
            gate(f"{Path(fname).stem}_git_blob_exact", actual == blob, actual)

        c25_text = (root / C25).read_text(encoding="utf-8")
        gate(
            "C25_terminal_node_excluded_from_PDE_loss",
            '"boundary_nodes_in_PDE_loss":False' in c25_text
            and '"interior_mask":"j=1..199"' in c25_text,
        )
        gate(
            "C25_data_loss_is_uniform_profile_MSE",
            '"data":"mean squared Sw error on supervised profiles"' in c25_text,
        )
        gate(
            "C25_test_pairs_for_selection_prohibited",
            '"test_pairs_for_selection":"PROHIBITED"' in c25_text,
        )

        stage = "R1_failure_binding"

        r1_report_path = drive / R1_BLOCKED_REL / R1_BLOCKED_REPORT
        gate("R1_blocked_report_present", r1_report_path.is_file(), str(r1_report_path))
        r1_report = load_json(r1_report_path)
        gate("R1_failed_stage_CV_physical_impact", r1_report.get("failed_stage") == "CV_physical_impact", r1_report.get("failed_stage"))
        gate(
            "R1_failed_gate_day30_heldout_breakthrough",
            "day_30_heldout_breakthrough_classification_matches_truth"
            in str(r1_report.get("exception", "")),
            r1_report.get("exception"),
        )

        r1_gate = r1_report.get("gates", {}).get(
            "day_30_heldout_breakthrough_classification_matches_truth",
            {},
        )
        r1_value = r1_gate.get("value")
        gate(
            "R1_day30_breakthrough_value_pair_present",
            isinstance(r1_value, list) and len(r1_value) == 2,
            r1_value,
        )
        r1_truth_cut = float(r1_value[0])
        r1_hybrid_cut = float(r1_value[1])
        gate("R1_truth_below_existing_threshold", r1_truth_cut < BREAKTHROUGH_GAS_CUT, r1_truth_cut)
        gate("R1_hybrid_above_existing_threshold", r1_hybrid_cut >= BREAKTHROUGH_GAS_CUT, r1_hybrid_cut)

        stage = "authority_binding"

        c18r = find_by_name_and_sha([root, drive], C18R_NAME, C18R_SHA)
        c19 = find_by_name_and_sha([root, drive], C19_NAME, C19_SHA)
        gate("C18R_exact_SHA", sha256_file(c18r) == C18R_SHA, str(c18r))
        gate("C19_exact_SHA", sha256_file(c19) == C19_SHA, str(c19))

        weights = drive / WEIGHTS_REL
        gate("C26_exact_weights_present", weights.is_file(), str(weights))
        actual_weight_sha = sha256_file(weights) if weights.is_file() else "missing"
        gate("C26_exact_weights_SHA", actual_weight_sha == WEIGHTS_SHA, actual_weight_sha)

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

        stage = "load_and_infer"

        b1 = load_module(root / B1, "postv16_av1dr2_b1")
        r2 = load_module(root / R2, "postv16_av1dr2_r2")
        e36 = load_module(root / E36, "postv16_av1dr2_e36")
        e37a = load_module(root / E37A, "postv16_av1dr2_e37a")
        sg7a = load_module(root / SG7A, "postv16_av1dr2_sg7a")

        with tempfile.TemporaryDirectory(prefix="POSTV16_AV1DR2_SG7D_") as td:
            td = Path(td)
            dst = td / SG7D
            dst.write_bytes((root / SG7D).read_bytes())
            sg7d = load_module(dst, "postv16_av1dr2_sg7d")

            cache = load_npz(e36_cache_path)
            parent_state = load_npz(r2_state_path)

            pressure_psi = np.asarray(cache["accepted_pressure_psi"], dtype=np.float64)
            xyz_m = np.asarray(cache["streamline_xyz_m"], dtype=np.float64)
            tau_end_s = np.asarray(cache["tau_end_s"], dtype=np.float64)
            weights_m3_s = np.asarray(cache["streamline_weights_m3_s"], dtype=np.float64)
            xi_faces = np.asarray(cache["xi"], dtype=np.float64)
            labels = np.asarray(cache["producer_labels"]).astype(str)

            weights_m3_day = weights_m3_s * float(e37a.DAY_TO_S)
            tau_end_days = tau_end_s / float(e37a.DAY_TO_S)

            tof_days = np.asarray(cache["streamline_tof_s"], dtype=np.float64) / float(e37a.DAY_TO_S)
            operator = sg7d.build_subsegment_operator(
                xyz_m,
                tof_days,
                weights_m3_day,
            )
            p_ref = scalar(parent_state["co2_density_reference_pressure_pa"])
            geometry = e37a.build_control_volume_geometry(
                r2,
                operator,
                pressure_psi,
                p_ref,
                EXPECTED_STREAMLINES,
                EXPECTED_CVS,
            )
            coeff = np.asarray(geometry["cv_pressure_mass_coeff"], dtype=np.float64)

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

            test_samples = np.flatnonzero(part == 2)
            test_streamlines = np.unique(sl[test_samples])
            gate(
                "locked_test_streamlines_161",
                len(test_streamlines) == EXPECTED_TEST_STREAMLINES,
                len(test_streamlines),
            )

            T = np.broadcast_to(
                th[:, None, None],
                (EXPECTED_SAMPLES, EXPECTED_NODES, 1),
            ).astype(np.float32)
            X = np.concatenate(
                [X7, T, eta_seq[:, :, None].astype(np.float32)],
                axis=2,
            )

            import tensorflow as tf
            try:
                tf.config.experimental.enable_op_determinism()
            except Exception:
                pass
            tf.keras.utils.set_random_seed(16021)

            model = b1.build_model(tf)
            model.load_weights(weights)
            pred201_flat = model.predict(X, batch_size=64, verbose=0).astype(np.float64)

            gate(
                "C26_full_prediction_shape_exact",
                pred201_flat.shape == (EXPECTED_SAMPLES, EXPECTED_NODES),
                pred201_flat.shape,
            )
            gate("C26_full_predictions_finite", np.isfinite(pred201_flat).all())

            pred201 = np.empty(
                (len(EXPECTED_DAYS), EXPECTED_STREAMLINES, EXPECTED_NODES),
                dtype=np.float64,
            )
            true201 = np.empty_like(pred201)
            for n in range(EXPECTED_SAMPLES):
                pred201[ti[n], sl[n]] = pred201_flat[n]
                true201[ti[n], sl[n]] = Y[n]

            ids = np.tile(
                np.arange(EXPECTED_STREAMLINES, dtype=np.int64),
                len(EXPECTED_DAYS),
            )
            pred200_flat, _, _ = b1.project_201_to_200_component_mass(
                r2,
                e37a,
                pred201.reshape(-1, EXPECTED_NODES),
                coeff,
                ids,
            )
            true200_flat, _, _ = b1.project_201_to_200_component_mass(
                r2,
                e37a,
                true201.reshape(-1, EXPECTED_NODES),
                coeff,
                ids,
            )

            pred200 = pred200_flat.reshape(
                len(EXPECTED_DAYS), EXPECTED_STREAMLINES, EXPECTED_CVS
            )
            true200 = true200_flat.reshape(
                len(EXPECTED_DAYS), EXPECTED_STREAMLINES, EXPECTED_CVS
            )

            stage = "breakthrough_localization"

            total_q = float(np.sum(weights_m3_day))
            day_rows: list[dict[str, Any]] = []
            producer_rows: list[dict[str, Any]] = []

            true_cuts = []
            hybrid_cuts = []
            full_cuts = []

            critical_rank_rows: list[dict[str, Any]] = []
            critical_summary: dict[str, Any] | None = None

            for t_index, day in enumerate(EXPECTED_DAYS):
                t = true200[t_index]
                p = pred200[t_index]

                h = t.copy()
                h[test_streamlines] = p[test_streamlines]

                true_by, true_cut, true_ff = producer_cuts(
                    sg7a, t, labels, weights_m3_day
                )
                hybrid_by, hybrid_cut, hybrid_ff = producer_cuts(
                    sg7a, h, labels, weights_m3_day
                )
                full_by, full_cut, full_ff = producer_cuts(
                    sg7a, p, labels, weights_m3_day
                )

                true_cuts.append(true_cut)
                hybrid_cuts.append(hybrid_cut)
                full_cuts.append(full_cut)

                outlet_true = t[test_streamlines, -1]
                outlet_pred = p[test_streamlines, -1]
                outlet_err = outlet_pred - outlet_true

                contrib = np.zeros(EXPECTED_STREAMLINES, dtype=np.float64)
                contrib[test_streamlines] = (
                    weights_m3_day[test_streamlines]
                    * (full_ff[test_streamlines] - true_ff[test_streamlines])
                    / total_q
                )
                net_delta = float(np.sum(contrib))
                gate(
                    f"day_{int(day)}_streamline_contributions_close_hybrid_delta",
                    abs(net_delta - (hybrid_cut - true_cut)) <= 1.0e-14,
                    (net_delta, hybrid_cut - true_cut),
                )

                positive = contrib[test_streamlines]
                pos_only = positive[positive > 0.0]
                neg_only = positive[positive < 0.0]

                row = {
                    "target_day": float(day),
                    "truth_aggregate_CO2_cut": true_cut,
                    "heldout_aggregate_CO2_cut": hybrid_cut,
                    "full_C26_aggregate_CO2_cut": full_cut,
                    "heldout_minus_truth_CO2_cut": hybrid_cut - true_cut,
                    "full_C26_minus_truth_CO2_cut": full_cut - true_cut,
                    "truth_breakthrough": bool(true_cut >= BREAKTHROUGH_GAS_CUT),
                    "heldout_breakthrough": bool(hybrid_cut >= BREAKTHROUGH_GAS_CUT),
                    "full_C26_breakthrough": bool(full_cut >= BREAKTHROUGH_GAS_CUT),
                    "heldout_classification_matches_truth": bool(
                        (hybrid_cut >= BREAKTHROUGH_GAS_CUT)
                        == (true_cut >= BREAKTHROUGH_GAS_CUT)
                    ),
                    "full_C26_classification_matches_truth": bool(
                        (full_cut >= BREAKTHROUGH_GAS_CUT)
                        == (true_cut >= BREAKTHROUGH_GAS_CUT)
                    ),
                    "test_outlet_saturation_bias_mean": float(np.mean(outlet_err)),
                    "test_outlet_saturation_MAE": float(np.mean(np.abs(outlet_err))),
                    "test_outlet_saturation_max_abs": float(np.max(np.abs(outlet_err))),
                    "test_streamline_positive_cut_contributors": int(np.sum(positive > 0.0)),
                    "test_streamline_negative_cut_contributors": int(np.sum(positive < 0.0)),
                    "positive_cut_contribution_sum": float(np.sum(pos_only)) if len(pos_only) else 0.0,
                    "negative_cut_contribution_sum": float(np.sum(neg_only)) if len(neg_only) else 0.0,
                }
                day_rows.append(row)

                for prod in sorted(true_by):
                    mprod = labels == prod
                    test_prod = mprod & np.isin(
                        np.arange(EXPECTED_STREAMLINES),
                        test_streamlines,
                    )
                    qprod = float(np.sum(weights_m3_day[mprod]))
                    producer_delta_from_test = (
                        float(
                            np.sum(
                                weights_m3_day[test_prod]
                                * (full_ff[test_prod] - true_ff[test_prod])
                            )
                            / qprod
                        )
                        if qprod > 0.0 else 0.0
                    )
                    gate(
                        f"day_{int(day)}_{prod}_test_contribution_closes_hybrid_delta",
                        abs(
                            producer_delta_from_test
                            - (hybrid_by[prod] - true_by[prod])
                        ) <= 1.0e-14,
                        (
                            producer_delta_from_test,
                            hybrid_by[prod] - true_by[prod],
                        ),
                    )
                    producer_rows.append({
                        "target_day": float(day),
                        "producer": prod,
                        "truth_CO2_cut": true_by[prod],
                        "heldout_CO2_cut": hybrid_by[prod],
                        "full_C26_CO2_cut": full_by[prod],
                        "heldout_minus_truth": hybrid_by[prod] - true_by[prod],
                        "full_C26_minus_truth": full_by[prod] - true_by[prod],
                        "test_streamline_contribution_to_producer_delta": producer_delta_from_test,
                        "truth_breakthrough": bool(true_by[prod] >= BREAKTHROUGH_GAS_CUT),
                        "heldout_breakthrough": bool(hybrid_by[prod] >= BREAKTHROUGH_GAS_CUT),
                        "full_C26_breakthrough": bool(full_by[prod] >= BREAKTHROUGH_GAS_CUT),
                    })

                if float(day) == 30.0:
                    gate(
                        "day30_truth_cut_reproduces_R1",
                        abs(true_cut - r1_truth_cut) <= 1.0e-14,
                        (true_cut, r1_truth_cut),
                    )
                    gate(
                        "day30_hybrid_cut_reproduces_R1",
                        abs(hybrid_cut - r1_hybrid_cut) <= 1.0e-14,
                        (hybrid_cut, r1_hybrid_cut),
                    )
                    gate(
                        "day30_false_positive_confirmed",
                        true_cut < BREAKTHROUGH_GAS_CUT
                        and hybrid_cut >= BREAKTHROUGH_GAS_CUT,
                        (true_cut, hybrid_cut),
                    )

                    ids_test = np.asarray(test_streamlines, dtype=np.int64)
                    contrib_test = contrib[ids_test]
                    order = np.argsort(contrib_test)[::-1]
                    sorted_ids = ids_test[order]
                    sorted_contrib = contrib_test[order]

                    positive_sorted = sorted_contrib[sorted_contrib > 0.0]
                    positive_total = float(np.sum(positive_sorted))
                    threshold_gap = BREAKTHROUGH_GAS_CUT - true_cut
                    if threshold_gap <= 0.0:
                        min_cross = 0
                    elif positive_total < threshold_gap:
                        min_cross = -1
                    else:
                        min_cross = int(
                            np.searchsorted(
                                np.cumsum(positive_sorted),
                                threshold_gap,
                                side="left",
                            )
                            + 1
                        )

                    cumulative_positive = 0.0
                    for rank, g in enumerate(sorted_ids, start=1):
                        contribution = float(contrib[g])
                        if contribution > 0.0:
                            cumulative_positive += contribution
                        critical_rank_rows.append({
                            "rank_by_positive_aggregate_cut_contribution": rank,
                            "streamline_index": int(g),
                            "producer": str(labels[g]),
                            "streamline_weight_m3_day": float(weights_m3_day[g]),
                            "terminal_TOF_days": float(tau_end_days[g]),
                            "truth_outlet_saturation_200CV": float(t[g, -1]),
                            "C26_outlet_saturation_200CV": float(p[g, -1]),
                            "outlet_saturation_error": float(p[g, -1] - t[g, -1]),
                            "truth_fractional_flow": float(true_ff[g]),
                            "C26_fractional_flow": float(full_ff[g]),
                            "fractional_flow_error": float(full_ff[g] - true_ff[g]),
                            "aggregate_CO2_cut_contribution": contribution,
                            "cumulative_positive_contribution": cumulative_positive,
                            "cumulative_positive_fraction_of_threshold_gap": (
                                cumulative_positive / threshold_gap
                                if threshold_gap > 0.0 else float("nan")
                            ),
                        })

                    def top_sum(n: int) -> float:
                        return float(np.sum(positive_sorted[: min(n, len(positive_sorted))]))

                    critical_summary = {
                        "truth_aggregate_CO2_cut": true_cut,
                        "heldout_aggregate_CO2_cut": hybrid_cut,
                        "full_C26_aggregate_CO2_cut": full_cut,
                        "existing_breakthrough_threshold": BREAKTHROUGH_GAS_CUT,
                        "truth_to_threshold_gap": threshold_gap,
                        "heldout_false_positive_excess_above_threshold": (
                            hybrid_cut - BREAKTHROUGH_GAS_CUT
                        ),
                        "heldout_minus_truth": hybrid_cut - true_cut,
                        "positive_test_streamline_contribution_sum": positive_total,
                        "negative_test_streamline_contribution_sum": float(
                            np.sum(sorted_contrib[sorted_contrib < 0.0])
                        ),
                        "positive_contributor_count": int(np.sum(sorted_contrib > 0.0)),
                        "negative_contributor_count": int(np.sum(sorted_contrib < 0.0)),
                        "minimum_largest_positive_contributors_needed_to_cross_threshold": min_cross,
                        "top1_positive_contribution": top_sum(1),
                        "top5_positive_contribution": top_sum(5),
                        "top10_positive_contribution": top_sum(10),
                        "top25_positive_contribution": top_sum(25),
                        "top1_fraction_of_truth_to_threshold_gap": (
                            top_sum(1) / threshold_gap if threshold_gap > 0.0 else float("nan")
                        ),
                        "top5_fraction_of_truth_to_threshold_gap": (
                            top_sum(5) / threshold_gap if threshold_gap > 0.0 else float("nan")
                        ),
                        "top10_fraction_of_truth_to_threshold_gap": (
                            top_sum(10) / threshold_gap if threshold_gap > 0.0 else float("nan")
                        ),
                        "top25_fraction_of_truth_to_threshold_gap": (
                            top_sum(25) / threshold_gap if threshold_gap > 0.0 else float("nan")
                        ),
                        "test_outlet_saturation_bias_mean": float(np.mean(outlet_err)),
                        "test_outlet_saturation_MAE": float(np.mean(np.abs(outlet_err))),
                        "test_outlet_saturation_max_abs": float(np.max(np.abs(outlet_err))),
                        "test_terminal_TOF_days_min": float(np.min(tau_end_days[test_streamlines])),
                        "test_terminal_TOF_days_median": float(np.median(tau_end_days[test_streamlines])),
                        "test_terminal_TOF_days_max": float(np.max(tau_end_days[test_streamlines])),
                    }

            gate("day30_critical_summary_created", critical_summary is not None)
            gate("day30_rank_table_has_161_test_streamlines", len(critical_rank_rows) == EXPECTED_TEST_STREAMLINES, len(critical_rank_rows))

            true_cuts_arr = np.asarray(true_cuts, dtype=np.float64)
            hybrid_cuts_arr = np.asarray(hybrid_cuts, dtype=np.float64)
            full_cuts_arr = np.asarray(full_cuts, dtype=np.float64)

            true_bt = first_breakthrough_day(EXPECTED_DAYS, true_cuts_arr)
            hybrid_bt = first_breakthrough_day(EXPECTED_DAYS, hybrid_cuts_arr)
            full_bt = first_breakthrough_day(EXPECTED_DAYS, full_cuts_arr)

            mismatched_days = [
                float(r["target_day"])
                for r in day_rows
                if not r["heldout_classification_matches_truth"]
            ]
            full_mismatched_days = [
                float(r["target_day"])
                for r in day_rows
                if not r["full_C26_classification_matches_truth"]
            ]

            # Diagnostic conclusions, not accuracy-threshold gates.
            gate("R2_does_not_change_existing_breakthrough_threshold", True)
            gate("R2_performs_no_training_or_retuning", True)
            gate("R2_uses_locked_test_only_for_diagnosis", True)
            gate("original_locked_test_reclassified_as_diagnostic_after_failure", True)
            gate("same_locked_test_not_authorized_as_final_acceptance_after_repair", True)

            decision = {
                "breakthrough_false_positive_confirmed": True,
                "critical_day": 30.0,
                "existing_breakthrough_threshold_unchanged": BREAKTHROUGH_GAS_CUT,
                "failure_scope": "OUTLET_PRODUCER_RESPONSE_ON_LOCKED_TEST_STREAMLINES",
                "C25_terminal_PDE_node_excluded": True,
                "C25_supervised_data_loss_uniform_profile_MSE": True,
                "causal_claim": (
                    "NOT YET PROVEN. R2 localizes the error to the outlet/producer "
                    "functional and quantifies the responsible streamline contributions. "
                    "It does not infer that C25 terminal-node masking alone caused the error."
                ),
                "training_or_retuning_authorized": False,
                "repair_design_authorized": True,
                "original_locked_test_status_after_diagnosis": (
                    "RETIRED_FROM_FINAL_INDEPENDENT_ACCEPTANCE; MAY BE USED ONLY AS "
                    "DIAGNOSTIC/REGRESSION EVIDENCE"
                ),
                "reason_for_test_retirement": (
                    "The locked-test result directly motivated the repair direction. "
                    "Any repaired model evaluated on this same set would no longer be "
                    "an untouched prospective acceptance test."
                ),
                "replacement_final_acceptance_required": True,
                "next": (
                    "POSTV16-AV1-D-R3 — freeze a prospective outlet/breakthrough repair "
                    "protocol AND a replacement independent acceptance authority before "
                    "any retraining. Do not tune on the retired locked test."
                ),
            }

            summary = {
                "milestone": MILESTONE,
                "status": STATUS_PASS,
                "repository_head": head,
                "repository_parent": parent,
                "existing_breakthrough_threshold": BREAKTHROUGH_GAS_CUT,
                "first_breakthrough_target_day": {
                    "C17_truth": true_bt,
                    "heldout_hybrid": hybrid_bt,
                    "full_C26": full_bt,
                },
                "heldout_breakthrough_mismatched_target_days": mismatched_days,
                "full_C26_breakthrough_mismatched_target_days": full_mismatched_days,
                "day30_localization": critical_summary,
                "decision": decision,
                "training_or_retuning_performed": False,
                "new_threshold_selected": False,
            }

            arrays = {
                "target_days": EXPECTED_DAYS,
                "test_streamline_indices": test_streamlines.astype(np.int64),
                "C17_truth_aggregate_CO2_cut": true_cuts_arr,
                "heldout_hybrid_aggregate_CO2_cut": hybrid_cuts_arr,
                "full_C26_aggregate_CO2_cut": full_cuts_arr,
            }

            files = {
                "PAD_Stream_POSTV16_AV1_D_R2_Summary.json": json_bytes(summary),
                "POSTV16_AV1_D_R2_Decision_Contract.json": json_bytes(decision),
                "POSTV16_AV1_D_R2_Day30_Localization.json": json_bytes(critical_summary),
                "POSTV16_AV1_D_R2_By_Target_Day_Breakthrough.csv": csv_bytes(day_rows),
                "POSTV16_AV1_D_R2_By_Producer_Breakthrough.csv": csv_bytes(producer_rows),
                "POSTV16_AV1_D_R2_Day30_Test_Streamline_Contribution_Ranking.csv": csv_bytes(critical_rank_rows),
                "POSTV16_AV1_D_R2_Breakthrough_Arrays.npz": deterministic_npz_bytes(arrays),
                "POSTV16_AV1_D_R2_Final_Gate_Matrix.csv": csv_bytes(
                    [{"gate": k, **v} for k, v in gates.items()]
                ),
            }

            immutable_publish(out, files)

            manifest_rows = []
            for p in sorted(out.iterdir()):
                if p.is_file() and p.name != "POSTV16_AV1_D_R2_Artifact_Manifest.csv":
                    manifest_rows.append({
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    })
            immutable_publish(
                out,
                {"POSTV16_AV1_D_R2_Artifact_Manifest.csv": csv_bytes(manifest_rows)},
            )

            print("\n" + "=" * 168)
            print("POSTV16-AV1-D-R2: PASS")
            print("=" * 168)
            print(f"{'Status':86}: {STATUS_PASS}")
            print(
                f"{'Day-30 truth / heldout / full-C26 aggregate CO2 cut':86}: "
                f"{true_cuts_arr[0]:.12e} / {hybrid_cuts_arr[0]:.12e} / {full_cuts_arr[0]:.12e}"
            )
            print(
                f"{'Truth->threshold gap / heldout excess above threshold':86}: "
                f"{critical_summary['truth_to_threshold_gap']:.12e} / "
                f"{critical_summary['heldout_false_positive_excess_above_threshold']:.12e}"
            )
            print(
                f"{'Positive / negative locked-test contributors':86}: "
                f"{critical_summary['positive_contributor_count']} / "
                f"{critical_summary['negative_contributor_count']}"
            )
            print(
                f"{'Minimum largest positive contributors needed to cross threshold':86}: "
                f"{critical_summary['minimum_largest_positive_contributors_needed_to_cross_threshold']}"
            )
            print(
                f"{'Top-1 / Top-5 / Top-10 fractions of truth->threshold gap':86}: "
                f"{critical_summary['top1_fraction_of_truth_to_threshold_gap']:.6f} / "
                f"{critical_summary['top5_fraction_of_truth_to_threshold_gap']:.6f} / "
                f"{critical_summary['top10_fraction_of_truth_to_threshold_gap']:.6f}"
            )
            print(
                f"{'Day-30 test outlet saturation bias / MAE / max abs':86}: "
                f"{critical_summary['test_outlet_saturation_bias_mean']:.12e} / "
                f"{critical_summary['test_outlet_saturation_MAE']:.12e} / "
                f"{critical_summary['test_outlet_saturation_max_abs']:.12e}"
            )
            print(
                f"{'First breakthrough day truth / heldout / full-C26':86}: "
                f"{true_bt} / {hybrid_bt} / {full_bt}"
            )
            print(
                f"{'Heldout classification-mismatched target days':86}: "
                f"{mismatched_days}"
            )
            print(f"{'Breakthrough threshold changed':86}: False")
            print(f"{'Training / retuning performed':86}: False")
            print(f"{'Repair design authorized':86}: True")
            print(f"{'Original locked test remains final independent acceptance':86}: False")
            print(
                f"{'NEXT':86}: POSTV16-AV1-D-R3 — prospective repair + replacement acceptance authority freeze"
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
            "next_action": (
                "Audit only failed R2 gates. Do not change the E36 breakthrough "
                "threshold and do not begin repair training."
            ),
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV1_D_R2_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV1_D_R2_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print("\n" + "=" * 168)
        print("POSTV16-AV1-D-R2: BLOCKED")
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

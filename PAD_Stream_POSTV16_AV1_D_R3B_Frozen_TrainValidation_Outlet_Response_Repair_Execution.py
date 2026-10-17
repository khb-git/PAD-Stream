#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

MILESTONE = "POSTV16-AV1-D-R3B"
STATUS_PASS = (
    "AV1DR3B_THREE_CANDIDATE_TRAIN_VALIDATION_REPAIR_EXECUTED_"
    "SELECTED_CHECKPOINT_FROZEN_GEOLOGY0030_REMAINS_SEALED"
)
STATUS_BLOCKED = "AV1DR3B_REPAIR_TRAINING_OR_SELECTION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R3A_COMMIT = "c6c1636ad2b2189d3ff497ebe73248a1085c5909"

R3A_RUNNER = "PAD_Stream_POSTV16_AV1_D_R3A_Generate_and_Seal_Geology0030_Acceptance_Authority.py"
R3A_RUNNER_BLOB = "8a12228f488394e24fdf11479e335f245c800478"

R3R1_RUNNER = (
    "PAD_Stream_POSTV16_AV1_D_R3_R1_"
    "Threshold_Schema_Binding_Repair_and_Prospective_Freeze.py"
)
R3R1_RUNNER_BLOB = "9d8c5b47b33e69e641df28ab130fddf401a11492"

C25_RUNNER = (
    "PAD_Stream_V16C25_Differentiable_Pollock_Full_Physics_Residual_"
    "Boundary_Mask_and_Physics_Loss_Weight_Authority_Contract.py"
)
C25_BLOB = "0a4740b95c2b5e5d15db3137414e663e1e9b6282"

C26_RUNNER = (
    "PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_"
    "Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
)
C26_BLOB = "62e19e6b502fb3ab101a2589251c26b5f9ad9031"

SOURCE_BLOBS = {
    R3A_RUNNER: R3A_RUNNER_BLOB,
    R3R1_RUNNER: R3R1_RUNNER_BLOB,
    C25_RUNNER: C25_BLOB,
    C26_RUNNER: C26_BLOB,
}

C18R_NAME = "V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz"
C18R_SHA = "1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"

C19_NAME = "V16C19_Leakage_Safe_Split_Assignment.npz"
C19_SHA = "399815504f5ba3a900c02f24e4f9496b3a93c2e472a5faea593507cf9174638a"

C4_NAME = "V16C4_Model_Ready_Conditioning_Tensors.npz"
C4_SHA = "98a0b65a221433877f3d6d6e8b65b3c4028925cf0dc5304d42421707a33d5b9c"

C7_NAME = "V16C7_Pollock_TOF_Streamline_Metric_Contract.npz"
C7_SHA = "5a47ef2a4154291b424e43d1b0e21e30baa0c805c846e9943f62f8b389289e6d"

C26_WEIGHTS_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_A3R3R_C26_Weight_State_Compatibility_Reconstruction"
    / "V16C26_EXP2_Exact_Embedded.weights.h5"
)
C26_WEIGHTS_SHA = "4bf0bde8a68d400a7eee33735ca85b4524b70d14be367f278f7276533443f8f9"

R3R1_OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R3_R1_Prospective_Repair_and_Replacement_Acceptance_Freeze"
)
R3R1_REPAIR = "POSTV16_AV1_D_R3_R1_Repair_Protocol.json"
R3R1_REPLACEMENT = "POSTV16_AV1_D_R3_R1_Replacement_Acceptance_Authority.json"
R3R1_MANIFEST = "POSTV16_AV1_D_R3_R1_Artifact_Manifest.csv"

R3A_OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R3A_Geology0030_Sealed_Acceptance_Authority"
)
R3A_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R3A_Summary.json"
R3A_AUTHORITY = "POSTV16_AV1_D_R3A_Sealed_Acceptance_Authority.json"
R3A_MANIFEST = "POSTV16_AV1_D_R3A_Artifact_Manifest.csv"
R3A_STATUS = (
    "AV1DR3A_GEOLOGY0030_REFERENCE_CONTROL_SOURCE_AUTHENTIC_"
    "STAGE4_ACCEPTANCE_AUTHORITY_GENERATED_CERTIFIED_AND_SHA_SEALED"
)

OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R3B_Frozen_TrainValidation_Repair_Execution"
)
BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R3B_BLOCKED"
)

EXPECTED_SAMPLES = 9702
EXPECTED_STREAMLINES = 1078
EXPECTED_NODES = 201
EXPECTED_CHANNELS = 9
EXPECTED_TRAIN_STREAMLINES = 755
EXPECTED_VALIDATION_STREAMLINES = 162
EXPECTED_TEST_STREAMLINES = 161

BATCH = 64
MAX_EPOCHS = 300
PATIENCE = 30
MIN_DELTA = 1.0e-6
LR_PATIENCE = 10
MIN_LR = 1.0e-6
INITIAL_LR = 1.0e-3
RNG_SEED = 16021
LAMBDA_PHYS = 0.01

CANDIDATES = [
    {
        "candidate_id": "R3A_TERMINAL",
        "lambda_terminal": 1.0,
        "lambda_outlet_response": 0.0,
    },
    {
        "candidate_id": "R3B_RESPONSE",
        "lambda_terminal": 0.0,
        "lambda_outlet_response": 1.0,
    },
    {
        "candidate_id": "R3C_TERMINAL_PLUS_RESPONSE",
        "lambda_terminal": 1.0,
        "lambda_outlet_response": 1.0,
    },
]


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
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


def json_bytes(obj: Any) -> bytes:
    return (
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    import io
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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


def find_named_exact(roots: list[Path], name: str, expected_sha: str) -> Path:
    matches: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob(name):
            try:
                if p.is_file() and sha256_file(p) == expected_sha:
                    matches.append(p)
            except OSError:
                pass
    if not matches:
        raise GateError(f"exact_authority_not_found:{name}:{expected_sha}")
    return sorted(set(matches), key=lambda p: (len(str(p)), str(p)))[0]


def partition_pairs(ids: np.ndarray, sl: np.ndarray, ti: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    allowed = set(map(int, ids))
    A: list[int] = []
    B: list[int] = []
    for g in np.unique(sl[ids]):
        q = ids[sl[ids] == g]
        q = q[np.argsort(ti[q])]
        for a, b in zip(q[:-1], q[1:]):
            if int(a) in allowed and int(b) in allowed:
                A.append(int(a))
                B.append(int(b))
    return np.asarray(A, dtype=np.int64), np.asarray(B, dtype=np.int64)


def candidate_paths(out: Path, cid: str) -> dict[str, Path]:
    d = out / "candidates" / cid
    return {
        "dir": d,
        "weights": d / f"{cid}_Best_Lexicographic_Validation.weights.h5",
        "history": d / f"{cid}_Training_History.csv",
        "summary": d / f"{cid}_Certification.json",
    }


def candidate_certified(paths: dict[str, Path], config: dict[str, Any]) -> bool:
    try:
        if not paths["weights"].is_file() or not paths["summary"].is_file():
            return False
        s = load_json(paths["summary"])
        return bool(
            s.get("status") == "CERTIFIED"
            and s.get("candidate_id") == config["candidate_id"]
            and float(s.get("lambda_terminal")) == float(config["lambda_terminal"])
            and float(s.get("lambda_outlet_response")) == float(config["lambda_outlet_response"])
            and s.get("weights_sha256") == sha256_file(paths["weights"])
            and s.get("retired_test_used") is False
            and s.get("geology0030_opened") is False
        )
    except Exception:
        return False


def self_test() -> None:
    sl = np.repeat(np.arange(3), 3)
    ti = np.tile(np.arange(3), 3)
    ids = np.arange(9)
    a, b = partition_pairs(ids, sl, ti)
    if a.tolist() != [0, 1, 3, 4, 6, 7]:
        raise RuntimeError("pair_a")
    if b.tolist() != [1, 2, 4, 5, 7, 8]:
        raise RuntimeError("pair_b")
    if len(CANDIDATES) != 3:
        raise RuntimeError("candidate_count")
    print("POSTV16-AV1-D-R3B self-test: PASS")


def main(root: Path, drive: Path) -> int:
    import tensorflow as tf

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
    print("POSTV16-AV1-D-R3B — FROZEN TRAIN/VALIDATION OUTLET-RESPONSE REPAIR EXECUTION")
    print("=" * 168)
    print("THREE PREDECLARED CANDIDATES ONLY. EXACT C26 ARCHITECTURE + INITIAL WEIGHTS.")
    print("C19 TRAIN ONLY FOR GRADIENTS. C19 VALIDATION ONLY FOR CHECKPOINT/CANDIDATE SELECTION.")
    print("RETIRED C19 TEST IS NOT PREDICTED OR SCORED.")
    print("SEALED GEOLOGY0030 TARGET IS HASH-VERIFIED ONLY; ITS VALUES ARE NOT OPENED.")
    print("NO BREAKTHROUGH THRESHOLD ENTERS TRAINING OR MODEL SELECTION.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()
        out.mkdir(parents=True, exist_ok=True)

        head = git_text(root, "rev-parse", "HEAD")
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate("repository_parent_is_R3A_commit", parent == PARENT_R3A_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fname, blob in SOURCE_BLOBS.items():
            p = root / fname
            actual = git_blob_sha(p, root) if p.is_file() else "missing"
            gate(f"{Path(fname).stem}_git_blob_exact", actual == blob, actual)

        stage = "R3_R3A_contract_binding"

        r3r1 = drive / R3R1_OUT_REL
        r3a = drive / R3A_OUT_REL

        gate("R3R1_output_present", r3r1.is_dir(), str(r3r1))
        gate("R3A_output_present", r3a.is_dir(), str(r3a))

        r3r1_manifest = verify_manifest(r3r1, R3R1_MANIFEST)
        r3a_manifest = verify_manifest(r3a, R3A_MANIFEST)
        gate("R3R1_manifest_SHA_closure", True, len(r3r1_manifest))
        gate("R3A_manifest_SHA_closure", True, len(r3a_manifest))

        repair = load_json(r3r1 / R3R1_REPAIR)
        replacement = load_json(r3r1 / R3R1_REPLACEMENT)
        r3a_summary = load_json(r3a / R3A_SUMMARY)
        r3a_authority = load_json(r3a / R3A_AUTHORITY)

        gate("R3A_status_exact", r3a_summary.get("status") == R3A_STATUS, r3a_summary.get("status"))
        gate("R3A_geology0030_authority_exact", r3a_authority.get("authority_id") == "POSTV16_AV1_REPLACEMENT_LOCKED_ACCEPTANCE_GEOLOGY0030")
        gate("R3A_target_performance_unopened", r3a_authority["firewall"]["model_performance_computed"] is False)
        gate("R3A_model_inference_false", r3a_authority["firewall"]["model_inference_performed"] is False)
        gate("R3A_target_values_not_printed", r3a_authority["firewall"]["target_values_printed"] is False)

        frozen_registry = repair["candidate_family"]
        gate("R3R1_candidate_registry_exact", frozen_registry == CANDIDATES, frozen_registry)
        gate("R3R1_architecture_unchanged", repair["candidate_policy"]["no_architecture_change"] is True)
        gate("R3R1_predictor_features_unchanged", repair["candidate_policy"]["no_predictor_feature_change"] is True)
        gate("R3R1_lambda_phys_unchanged", repair["candidate_policy"]["no_C25_physics_weight_change"] is True)
        gate("R3R1_retired_test_selection_false", repair["validation_selection"]["retired_test_used"] is False)
        gate("R3R1_breakthrough_threshold_not_selection_metric", repair["validation_selection"]["breakthrough_threshold_used_for_candidate_selection"] is False)
        gate("R3R1_selected_checkpoint_must_freeze_before_geology0030", repair["post_selection"]["selected_checkpoint_frozen_before_any_replacement_test_opening"] is True)
        gate("replacement_geology0030_exact", replacement["geology_id"] == "0030")
        gate("replacement_seed382132_exact", int(replacement["seed"]) == 382132)

        # Verify every R3A file by SHA, including the sealed target, without opening NPZ values.
        sealed_target_name = "POSTV16_AV1_D_R3A_Geology0030_R500_B2000_SEALED_Stage4_Target.npz"
        gate("sealed_target_in_R3A_manifest", sealed_target_name in r3a_manifest)
        sealed_target_path = r3a / sealed_target_name
        gate(
            "sealed_target_SHA_verified_without_opening",
            sealed_target_path.is_file()
            and sha256_file(sealed_target_path) == r3a_manifest[sealed_target_name],
            r3a_manifest.get(sealed_target_name),
        )

        stage = "training_authority_binding"

        c18r = find_named_exact([root, drive], C18R_NAME, C18R_SHA)
        c19 = find_named_exact([root, drive], C19_NAME, C19_SHA)
        c4 = find_named_exact([root, drive], C4_NAME, C4_SHA)
        c7 = find_named_exact([root, drive], C7_NAME, C7_SHA)

        gate("C18R_exact_SHA", sha256_file(c18r) == C18R_SHA, str(c18r))
        gate("C19_exact_SHA", sha256_file(c19) == C19_SHA, str(c19))
        gate("C4_exact_SHA", sha256_file(c4) == C4_SHA, str(c4))
        gate("C7_exact_SHA", sha256_file(c7) == C7_SHA, str(c7))

        initial_weights = drive / C26_WEIGHTS_REL
        gate("C26_exact_initial_weights_present", initial_weights.is_file(), str(initial_weights))
        actual_initial_sha = sha256_file(initial_weights) if initial_weights.is_file() else "missing"
        gate("C26_exact_initial_weights_SHA", actual_initial_sha == C26_WEIGHTS_SHA, actual_initial_sha)

        c26 = load_module(root / C26_RUNNER, "postv16_r3b_c26")

        with np.load(c18r, allow_pickle=False) as z:
            d = {k: z[k].copy() for k in z.files}
        with np.load(c19, allow_pickle=False) as z:
            s = {k: z[k].copy() for k in z.files}
        with np.load(c4, allow_pickle=False) as z:
            c4x = {k: z[k].copy() for k in z.files}
        with np.load(c7, allow_pickle=False) as z:
            mk = next(
                (
                    k
                    for k in (
                        "metric_M_dtheta_dxD",
                        "metric_M",
                        "M_dtheta_dxD",
                    )
                    if k in z.files
                ),
                None,
            )
            if mk is None:
                raise GateError(f"C7_metric_key_unresolved:{z.files}")
            Mall = np.asarray(z[mk], dtype=np.float32)

        X7 = np.asarray(d["X_sequence_required"], dtype=np.float32)
        Y = np.asarray(d["Y_transport"], dtype=np.float32)
        th = np.asarray(d["target_time_hat"], dtype=np.float32)
        eta_seq = np.asarray(d["target_eta_sequence"], dtype=np.float32)
        sl = np.asarray(d["streamline_index"], dtype=np.int64)
        ti = np.asarray(d["time_index"], dtype=np.int64)
        part = np.asarray(s["sample_partition_code"], dtype=np.int8)

        c4_static = np.asarray(c4x["X_static_required"], dtype=np.float32)
        weights = np.asarray(c4x["streamline_weight_m3_s"], dtype=np.float64)

        gate("X7_shape_exact", X7.shape == (EXPECTED_SAMPLES, EXPECTED_NODES, 7), X7.shape)
        gate("Y_shape_exact", Y.shape == (EXPECTED_SAMPLES, EXPECTED_NODES), Y.shape)
        gate("partition_shape_exact", part.shape == (EXPECTED_SAMPLES,), part.shape)
        gate("C7_M_shape_exact", Mall.shape == (EXPECTED_STREAMLINES, EXPECTED_NODES), Mall.shape)
        gate("C4_static_shape_exact", c4_static.shape == (EXPECTED_STREAMLINES, 1), c4_static.shape)
        gate("C4_weight_shape_exact", weights.shape == (EXPECTED_STREAMLINES,), weights.shape)
        gate("C4_weights_positive_finite", np.isfinite(weights).all() and np.all(weights > 0.0))

        # C18R explicitly replicated C4 static rows in time-major order.
        xstatic_r = np.asarray(d["X_static_required"], dtype=np.float32)
        gate("C18R_static_shape_exact", xstatic_r.shape == (EXPECTED_SAMPLES, 1), xstatic_r.shape)
        xstatic_9 = xstatic_r.reshape(9, EXPECTED_STREAMLINES, 1)
        gate(
            "C18R_C4_streamline_order_identity_exact",
            np.array_equal(
                xstatic_9,
                np.broadcast_to(c4_static[None, :, :], xstatic_9.shape),
            ),
        )

        T = np.broadcast_to(
            th[:, None, None],
            (EXPECTED_SAMPLES, EXPECTED_NODES, 1),
        ).astype(np.float32)
        X = np.concatenate(
            [X7, T, eta_seq[:, :, None].astype(np.float32)],
            axis=2,
        )
        gate("C26_input_shape_exact", X.shape == (EXPECTED_SAMPLES, EXPECTED_NODES, EXPECTED_CHANNELS), X.shape)

        train = np.flatnonzero(part == 0)
        val = np.flatnonzero(part == 1)
        test = np.flatnonzero(part == 2)

        train_streamlines = np.unique(sl[train])
        val_streamlines = np.unique(sl[val])
        test_streamlines = np.unique(sl[test])

        gate("train_streamlines_755", len(train_streamlines) == EXPECTED_TRAIN_STREAMLINES, len(train_streamlines))
        gate("validation_streamlines_162", len(val_streamlines) == EXPECTED_VALIDATION_STREAMLINES, len(val_streamlines))
        gate("retired_test_streamlines_161", len(test_streamlines) == EXPECTED_TEST_STREAMLINES, len(test_streamlines))
        gate("partition_streamline_disjoint", len(set(train_streamlines) & set(val_streamlines)) == 0 and len(set(train_streamlines) & set(test_streamlines)) == 0 and len(set(val_streamlines) & set(test_streamlines)) == 0)

        ta, tb = partition_pairs(train, sl, ti)
        va, vb = partition_pairs(val, sl, ti)
        gate("train_pairs_6040", len(ta) == 6040, len(ta))
        gate("validation_pairs_1296", len(va) == 1296, len(va))
        gate("no_retired_test_samples_in_train_pairs", not np.isin(np.r_[ta, tb], test).any())
        gate("no_retired_test_samples_in_validation_pairs", not np.isin(np.r_[va, vb], test).any())

        mean_train_weight = float(np.mean(weights[train_streamlines]))
        gate("mean_train_streamline_weight_positive", np.isfinite(mean_train_weight) and mean_train_weight > 0.0, mean_train_weight)

        # Validation-only metric helpers.
        def validation_prediction_metrics(model) -> dict[str, float]:
            preds = []
            for st in range(0, len(val), BATCH):
                q = val[st : st + BATCH]
                preds.append(model(X[q], training=False).numpy().astype(np.float64))
            P = np.concatenate(preds, axis=0)
            Tt = Y[val].astype(np.float64)

            terminal_err = P[:, -1] - Tt[:, -1]
            terminal_rmse = float(np.sqrt(np.mean(terminal_err ** 2)))
            profile_rmse = float(np.sqrt(np.mean((P - Tt) ** 2)))

            fw_pred = c26.fw(tf.convert_to_tensor(P[:, -1], dtype=tf.float32)).numpy().astype(np.float64)
            fw_true = c26.fw(tf.convert_to_tensor(Tt[:, -1], dtype=tf.float32)).numpy().astype(np.float64)
            wv = weights[sl[val]]
            response_rmse = float(
                np.sqrt(
                    np.sum(wv * (fw_pred - fw_true) ** 2)
                    / np.sum(wv)
                )
            )
            return {
                "validation_flow_weighted_outlet_fractional_flow_RMSE": response_rmse,
                "validation_terminal_saturation_RMSE": terminal_rmse,
                "validation_full_profile_RMSE": profile_rmse,
            }

        def validation_base_total(model) -> tuple[float, float, float]:
            vd: list[float] = []
            vp: list[float] = []
            vt: list[float] = []
            for st in range(0, len(va), BATCH):
                a = va[st : st + BATCH]
                b = vb[st : st + BATCH]
                Sa = model(X[a], training=False)
                Sb = model(X[b], training=False)
                ld = 0.5 * (
                    tf.reduce_mean((Sa - Y[a]) ** 2)
                    + tf.reduce_mean((Sb - Y[b]) ** 2)
                )
                ea = tf.reduce_mean(eta_seq[a], axis=1)
                eb = tf.reduce_mean(eta_seq[b], axis=1)
                lp = c26.phys_pair_loss(
                    Sa,
                    Sb,
                    ea,
                    eb,
                    tf.gather(Mall, sl[a]),
                )
                tot = ld + LAMBDA_PHYS * lp
                vd.append(float(ld))
                vp.append(float(lp))
                vt.append(float(tot))
            return float(np.mean(vd)), float(np.mean(vp)), float(np.mean(vt))

        def lexicographic_tuple(metrics: dict[str, float], base_total: float) -> tuple[float, float, float, float]:
            return (
                metrics["validation_flow_weighted_outlet_fractional_flow_RMSE"],
                metrics["validation_terminal_saturation_RMSE"],
                metrics["validation_full_profile_RMSE"],
                base_total,
            )

        stage = "baseline_validation_characterization"

        tf.keras.utils.set_random_seed(RNG_SEED)
        baseline_model = c26.model()
        baseline_model.load_weights(initial_weights)
        gate("C26_model_parameter_count_52033", baseline_model.count_params() == 52033, baseline_model.count_params())

        baseline_metrics = validation_prediction_metrics(baseline_model)
        bvd, bvp, bvt = validation_base_total(baseline_model)
        baseline_metrics.update({
            "validation_base_data_loss": bvd,
            "validation_base_physics_loss": bvp,
            "validation_base_total_objective": bvt,
        })
        gate("baseline_validation_metrics_finite", all(np.isfinite(v) for v in baseline_metrics.values()))

        del baseline_model
        tf.keras.backend.clear_session()

        stage = "three_candidate_training"

        candidate_records: list[dict[str, Any]] = []

        for cindex, config in enumerate(CANDIDATES, start=1):
            cid = config["candidate_id"]
            paths = candidate_paths(out, cid)

            if candidate_certified(paths, config):
                rec = load_json(paths["summary"])
                candidate_records.append(rec)
                print(f"[REUSE {cindex}/3] {cid} — SHA-certified candidate")
                continue

            print("\n" + "=" * 120)
            print(f"TRAINING CANDIDATE {cindex}/3: {cid}")
            print(
                f"lambda_terminal={config['lambda_terminal']} "
                f"lambda_outlet_response={config['lambda_outlet_response']}"
            )
            print("=" * 120)

            tf.keras.backend.clear_session()
            tf.keras.utils.set_random_seed(RNG_SEED)

            model = c26.model()
            model.load_weights(initial_weights)
            optimizer = tf.keras.optimizers.Adam(INITIAL_LR)
            rng = np.random.default_rng(RNG_SEED)

            best_tuple: tuple[float, float, float, float] | None = None
            best_epoch: int | None = None
            best_metrics: dict[str, float] | None = None
            best_base = None

            # C26 patience/LR mechanics retained; monitor is the R3-frozen
            # primary validation selection quantity: outlet-response RMSE.
            es_best = np.inf
            lr_best = np.inf
            wait = 0
            lrwait = 0

            history_rows: list[dict[str, Any]] = []

            with tempfile.TemporaryDirectory(prefix=f"POSTV16_R3B_{cid}_") as td:
                td = Path(td)
                temp_weights = td / f"{cid}.weights.h5"

                for epoch in range(1, MAX_EPOCHS + 1):
                    order = rng.permutation(len(ta))
                    tr_data: list[float] = []
                    tr_phys: list[float] = []
                    tr_terminal: list[float] = []
                    tr_response: list[float] = []
                    tr_total: list[float] = []

                    for st in range(0, len(order), BATCH):
                        z = order[st : st + BATCH]
                        a = ta[z]
                        b = tb[z]

                        with tf.GradientTape() as tape:
                            Sa = model(X[a], training=True)
                            Sb = model(X[b], training=True)

                            L_profile = 0.5 * (
                                tf.reduce_mean((Sa - Y[a]) ** 2)
                                + tf.reduce_mean((Sb - Y[b]) ** 2)
                            )

                            ea = tf.reduce_mean(eta_seq[a], axis=1)
                            eb = tf.reduce_mean(eta_seq[b], axis=1)
                            L_phys = c26.phys_pair_loss(
                                Sa,
                                Sb,
                                ea,
                                eb,
                                tf.gather(Mall, sl[a]),
                            )

                            L_terminal = 0.5 * (
                                tf.reduce_mean((Sa[:, -1] - Y[a, -1]) ** 2)
                                + tf.reduce_mean((Sb[:, -1] - Y[b, -1]) ** 2)
                            )

                            wa = tf.convert_to_tensor(
                                weights[sl[a]] / mean_train_weight,
                                dtype=tf.float32,
                            )
                            wb = tf.convert_to_tensor(
                                weights[sl[b]] / mean_train_weight,
                                dtype=tf.float32,
                            )

                            fpa = c26.fw(Sa[:, -1])
                            fta = c26.fw(Y[a, -1])
                            fpb = c26.fw(Sb[:, -1])
                            ftb = c26.fw(Y[b, -1])

                            L_response = 0.5 * (
                                tf.reduce_mean(wa * tf.square(fpa - fta))
                                + tf.reduce_mean(wb * tf.square(fpb - ftb))
                            )

                            loss = (
                                L_profile
                                + LAMBDA_PHYS * L_phys
                                + float(config["lambda_terminal"]) * L_terminal
                                + float(config["lambda_outlet_response"]) * L_response
                            )

                        grads = tape.gradient(loss, model.trainable_variables)
                        optimizer.apply_gradients(zip(grads, model.trainable_variables))

                        tr_data.append(float(L_profile))
                        tr_phys.append(float(L_phys))
                        tr_terminal.append(float(L_terminal))
                        tr_response.append(float(L_response))
                        tr_total.append(float(loss))

                    # Validation uses NO repair term in the optimization
                    # objective. The repair terms are TRAIN-only by the R3
                    # contract; validation computes their physical observables
                    # separately for selection.
                    vd, vp, vbase = validation_base_total(model)
                    vm = validation_prediction_metrics(model)
                    key = lexicographic_tuple(vm, vbase)

                    raw_primary = vm[
                        "validation_flow_weighted_outlet_fractional_flow_RMSE"
                    ]

                    if best_tuple is None or key < best_tuple:
                        best_tuple = key
                        best_epoch = epoch
                        best_metrics = dict(vm)
                        best_base = {
                            "validation_base_data_loss": vd,
                            "validation_base_physics_loss": vp,
                            "validation_base_total_objective": vbase,
                        }
                        model.save_weights(temp_weights)

                    # Same C26 patience/min-delta/LR-patience mechanics with
                    # the R3-frozen primary validation selection observable.
                    if raw_primary < lr_best:
                        lr_best = raw_primary
                        lrwait = 0
                    else:
                        lrwait += 1

                    if raw_primary < es_best - MIN_DELTA:
                        es_best = raw_primary
                        wait = 0
                    else:
                        wait += 1

                    if lrwait >= LR_PATIENCE:
                        optimizer.learning_rate.assign(
                            max(
                                float(optimizer.learning_rate.numpy()) * 0.5,
                                MIN_LR,
                            )
                        )
                        lrwait = 0

                    row = {
                        "epoch": epoch,
                        "train_profile": float(np.mean(tr_data)),
                        "train_phys": float(np.mean(tr_phys)),
                        "train_terminal": float(np.mean(tr_terminal)),
                        "train_outlet_response": float(np.mean(tr_response)),
                        "train_total": float(np.mean(tr_total)),
                        "val_base_data": vd,
                        "val_base_phys": vp,
                        "val_base_total": vbase,
                        **vm,
                        "learning_rate": float(optimizer.learning_rate.numpy()),
                        "lexicographic_best_epoch_so_far": best_epoch,
                    }
                    history_rows.append(row)

                    print(
                        f"{cid} epoch {epoch:03d}: "
                        f"train={row['train_total']:.6e} "
                        f"val_response={vm['validation_flow_weighted_outlet_fractional_flow_RMSE']:.6e} "
                        f"val_terminal={vm['validation_terminal_saturation_RMSE']:.6e} "
                        f"val_profile={vm['validation_full_profile_RMSE']:.6e} "
                        f"val_base={vbase:.6e} "
                        f"lr={row['learning_rate']:.3e}"
                    )

                    if wait >= PATIENCE:
                        print(
                            f"{cid}: early stopping at epoch {epoch}; "
                            f"lexicographic best epoch={best_epoch}"
                        )
                        break

                if not temp_weights.is_file() or best_epoch is None or best_metrics is None or best_base is None:
                    raise GateError(f"{cid}:best_checkpoint_not_created")

                # Re-load exact best lexicographic checkpoint and recompute
                # validation metrics before certification.
                best_model = c26.model()
                best_model.load_weights(temp_weights)
                check_vm = validation_prediction_metrics(best_model)
                cvd, cvp, cvbase = validation_base_total(best_model)
                check_tuple = lexicographic_tuple(check_vm, cvbase)

                if best_tuple is None or not np.allclose(
                    np.asarray(check_tuple),
                    np.asarray(best_tuple),
                    rtol=1.0e-7,
                    atol=1.0e-10,
                ):
                    raise GateError(
                        f"{cid}:best_checkpoint_validation_recompute_mismatch"
                    )

                paths["dir"].mkdir(parents=True, exist_ok=True)
                shutil.copyfile(temp_weights, paths["weights"])

                history_data = csv_bytes(history_rows)
                if paths["history"].exists():
                    if paths["history"].read_bytes() != history_data:
                        raise GateError(f"{cid}:existing_history_differs")
                else:
                    paths["history"].write_bytes(history_data)

                rec = {
                    "candidate_id": cid,
                    "status": "CERTIFIED",
                    "lambda_terminal": float(config["lambda_terminal"]),
                    "lambda_outlet_response": float(config["lambda_outlet_response"]),
                    "initial_weights_sha256": C26_WEIGHTS_SHA,
                    "weights_sha256": sha256_file(paths["weights"]),
                    "epochs_completed": len(history_rows),
                    "best_epoch": int(best_epoch),
                    "selection_tuple": {
                        "validation_flow_weighted_outlet_fractional_flow_RMSE": check_vm[
                            "validation_flow_weighted_outlet_fractional_flow_RMSE"
                        ],
                        "validation_terminal_saturation_RMSE": check_vm[
                            "validation_terminal_saturation_RMSE"
                        ],
                        "validation_full_profile_RMSE": check_vm[
                            "validation_full_profile_RMSE"
                        ],
                        "validation_base_total_objective": cvbase,
                    },
                    "validation_base_data_loss": cvd,
                    "validation_base_physics_loss": cvp,
                    "training_partition": "C19 TRAIN only",
                    "selection_partition": "C19 VALIDATION only",
                    "retired_test_used": False,
                    "retired_test_predictions_computed": False,
                    "geology0030_opened": False,
                    "geology0030_model_inference": False,
                    "breakthrough_threshold_used_for_training_or_selection": False,
                    "history_sha256": sha256_file(paths["history"]),
                }
                summary_bytes = json_bytes(rec)
                if paths["summary"].exists():
                    if paths["summary"].read_bytes() != summary_bytes:
                        raise GateError(f"{cid}:existing_summary_differs")
                else:
                    paths["summary"].write_bytes(summary_bytes)

                candidate_records.append(rec)

                del best_model
                del model
                tf.keras.backend.clear_session()

        gate("exactly_three_candidates_certified", len(candidate_records) == 3, len(candidate_records))
        gate("all_candidates_retired_test_unused", all(r["retired_test_used"] is False for r in candidate_records))
        gate("all_candidates_geology0030_unopened", all(r["geology0030_opened"] is False for r in candidate_records))
        gate("all_candidates_started_from_exact_C26", all(r["initial_weights_sha256"] == C26_WEIGHTS_SHA for r in candidate_records))

        stage = "candidate_selection_and_freeze"

        def record_tuple(r: dict[str, Any]) -> tuple[float, float, float, float]:
            s = r["selection_tuple"]
            return (
                float(s["validation_flow_weighted_outlet_fractional_flow_RMSE"]),
                float(s["validation_terminal_saturation_RMSE"]),
                float(s["validation_full_profile_RMSE"]),
                float(s["validation_base_total_objective"]),
            )

        sorted_records = sorted(candidate_records, key=record_tuple)
        winner = sorted_records[0]
        winner_id = winner["candidate_id"]
        winner_paths = candidate_paths(out, winner_id)

        selected_weights = out / "POSTV16_AV1_D_R3B_SELECTED_FROZEN.weights.h5"
        if selected_weights.exists():
            if sha256_file(selected_weights) != sha256_file(winner_paths["weights"]):
                raise GateError("existing_selected_weights_differs")
        else:
            shutil.copyfile(winner_paths["weights"], selected_weights)

        selected_sha = sha256_file(selected_weights)
        gate("selected_weights_SHA_matches_winning_candidate", selected_sha == winner["weights_sha256"], selected_sha)

        selection_registry = []
        for rank, rec in enumerate(sorted_records, start=1):
            tup = record_tuple(rec)
            selection_registry.append({
                "rank": rank,
                "candidate_id": rec["candidate_id"],
                "validation_flow_weighted_outlet_fractional_flow_RMSE": tup[0],
                "validation_terminal_saturation_RMSE": tup[1],
                "validation_full_profile_RMSE": tup[2],
                "validation_base_total_objective": tup[3],
                "best_epoch": rec["best_epoch"],
                "weights_sha256": rec["weights_sha256"],
                "selected": rec["candidate_id"] == winner_id,
            })

        selection = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "selection_rule": [
                "minimum validation flow-weighted outlet fractional-flow RMSE",
                "minimum validation terminal saturation RMSE",
                "minimum validation full-profile RMSE",
                "minimum validation frozen base total objective",
            ],
            "winner": winner,
            "selected_frozen_weights_sha256": selected_sha,
            "baseline_C26_validation_descriptive_only": baseline_metrics,
            "retired_test_used_for_selection": False,
            "geology0030_opened_for_selection": False,
            "breakthrough_threshold_used_for_selection": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "repository_head": head,
            "repository_parent": parent,
            "candidate_count": 3,
            "winner_candidate_id": winner_id,
            "selected_frozen_weights_sha256": selected_sha,
            "selected_best_epoch": winner["best_epoch"],
            "selected_validation_tuple": winner["selection_tuple"],
            "baseline_C26_validation_descriptive_only": baseline_metrics,
            "training_data": "C19 TRAIN only",
            "selection_data": "C19 VALIDATION only",
            "retired_C19_test_role": "NOT USED; remains diagnostic/regression only",
            "geology0030_status": "SHA-SEALED AND UNOPENED FOR MODEL EVALUATION",
            "geology0030_model_inference": False,
            "next": (
                "POSTV16-AV1-D-R3C — one-touch final evaluation of the frozen "
                "R3B selected checkpoint on sealed geology0030 under the already-"
                "frozen R3-R1 event acceptance contract."
            ),
        }

        contract_files = {
            "PAD_Stream_POSTV16_AV1_D_R3B_Summary.json": json_bytes(summary),
            "POSTV16_AV1_D_R3B_Selected_Checkpoint_Contract.json": json_bytes(selection),
            "POSTV16_AV1_D_R3B_Candidate_Ranking.csv": csv_bytes(selection_registry),
            "POSTV16_AV1_D_R3B_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
        }
        immutable_publish(out, contract_files)

        manifest_rows = []
        for p in sorted(out.rglob("*")):
            if p.is_file() and p.name != "POSTV16_AV1_D_R3B_Artifact_Manifest.csv":
                manifest_rows.append({
                    "file": str(p.relative_to(out)),
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                })
        immutable_publish(
            out,
            {"POSTV16_AV1_D_R3B_Artifact_Manifest.csv": csv_bytes(manifest_rows)},
        )

        print("\n" + "=" * 168)
        print("POSTV16-AV1-D-R3B: PASS")
        print("=" * 168)
        print(f"{'Status':86}: {STATUS_PASS}")
        print(f"{'Candidates certified':86}: 3 / 3")
        for row in selection_registry:
            print(
                f"  rank {row['rank']} {row['candidate_id']}: "
                f"response={row['validation_flow_weighted_outlet_fractional_flow_RMSE']:.12e}, "
                f"terminal={row['validation_terminal_saturation_RMSE']:.12e}, "
                f"profile={row['validation_full_profile_RMSE']:.12e}, "
                f"base={row['validation_base_total_objective']:.12e}, "
                f"epoch={row['best_epoch']}"
            )
        print(f"{'Selected candidate':86}: {winner_id}")
        print(f"{'Selected weights SHA256':86}: {selected_sha}")
        print(f"{'Retired C19 test predicted/scored':86}: False / False")
        print(f"{'Geology0030 target opened for model evaluation':86}: False")
        print(f"{'Geology0030 model inference performed':86}: False")
        print(f"{'Breakthrough threshold used in training/selection':86}: False")
        print(f"{'NEXT':86}: POSTV16-AV1-D-R3C — one-touch sealed geology0030 final evaluation")
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
            "retired_test_predictions_computed": False,
            "geology0030_model_inference": False,
            "next_action": (
                "Audit only failed R3B authority/training/selection gates. "
                "Do not open geology0030 and do not alter the frozen candidate family."
            ),
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV1_D_R3B_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV1_D_R3B_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print("\n" + "=" * 168)
        print("POSTV16-AV1-D-R3B: BLOCKED")
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
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))

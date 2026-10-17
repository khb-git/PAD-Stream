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
import shutil
import subprocess
import sys
import tempfile
import zipfile
from typing import Any

import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

MILESTONE = "POSTV16-AV1-B1-R1"
STATUS_PASS = "AV1B1R1_C26_TO_E37A_COMPONENT_MASS_RUNTIME_REPRESENTATION_EQUIVALENCE_AUDITED"
STATUS_BLOCKED = "AV1B1R1_BLOCKED_COMPONENT_MASS_RUNTIME_REPRESENTATION_EQUIVALENCE_INCOMPLETE"
NEXT = "POSTV16-AV1-C — interpret Level-1 vs Level-2 C26 accuracy and decide deployment acceptance/repair path"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_COMMIT = "088dbd8e06e7c1504328005990c4c564e636bbfa"
AV1B_BOUND_COMMIT = "fc2cc7823de630868560ba15fa12bc4af831731a"

# Exact post-BR recovery lineage. B1-R1 is authorized only when its immediate
# parent is the terminal recovery commit and every historical parent edge below
# reproduces exactly.
B1_ORIGINAL_COMMIT = "551bd8a4b0984567173522753583f0343d70f755"
B1R_COMMIT = "8f2faf0c50b5fcc6098826740ca505d4c0cee57d"
B1R2_COMMIT = "41f1e224b05e521f13f691e77eb90eb2b8b31828"
B1R3_R1_COMMIT = "80540b192187b49d7ab69b237ea64de1bae886d8"

RECOVERY_LINEAGE = (
    ("BR", BASE_COMMIT, AV1B_BOUND_COMMIT),
    ("B1", B1_ORIGINAL_COMMIT, BASE_COMMIT),
    ("B1R", B1R_COMMIT, B1_ORIGINAL_COMMIT),
    ("B1R2", B1R2_COMMIT, B1R_COMMIT),
    ("B1R3_R1", B1R3_R1_COMMIT, B1R2_COMMIT),
)

C10 = "PAD_Stream_V16C10_Conservative_201_Node_Pollock_Coordinate_Full_Physics_Operator_Construction.py"
C17 = "PAD_Stream_V16C17_Production_Source_Authentic_Y_Transport_Tensor_Generation_and_Certification.py"
C20 = "PAD_Stream_V16C20_Stage4_PIRNN_to_V16_Training_Interface_and_Architecture_Binding_Contract.py"
C26 = "PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
E36 = "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
BR = "PAD_Stream_POSTV16_AV1_BR_Exact_Half_Half_Geometry_Floating_Point_Failure_Audit.py"

EXPECTED_BLOBS = {
    C10: "753fd3de9490c37173c5c00544a3bb995de4ccfc",
    C17: "310e10853ce6f160ee8c9bd270f2823893bf98d3",
    C20: "70b073faafd76f71c2c97a2df031592f05f6cf9f",
    C26: "62e19e6b502fb3ab101a2589251c26b5f9ad9031",
    R2: "a127f8730a16e150713420ea547a8de6255550ef",
    E36: "9ab4035c95a25bd61c649f86c82d88f059cef9e2",
    E37A: "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0",
    SG7D: "890088c0c0fcab415a2c7351c5079ca8ee12bf82",
    BR: "80a9fb93cb147f9b97c367af8ab3a2caaaf78da1",
}

RECOVERY_RUNNER_BLOBS = {
    "PAD_Stream_POSTV16_AV1_B1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py":
        "75574d5d76ef12c23751bac3716d1a36470c6920",
    "PAD_Stream_POSTV16_AV1_B1R_Exact_Heavy_Artifact_Location_Audit.py":
        "8769941b55c4591176ac8d143228e127d1ef1fc7",
    "PAD_Stream_POSTV16_AV1_B1R2_Windows_Local_Exact_Heavy_Artifact_Recovery_Audit.py":
        "1e0b5c2b6ece1317188f2889e8b514279c2140ad",
    "PAD_Stream_POSTV16_AV1_B1R3_R1_Exact_Authority_Transfer_and_Drive_Materialization.py":
        "8d7900fcee32ae03248174ca486b97d043d0931a",
}

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
R2_SUMMARY = "PAD_Stream_V16E35_R2_Summary.json"
R2_STATE = "V16E35_R2_First_Accepted_SGSim_Runtime_State_Step0001.npz"
R2_EXPECTED_STATUS = "FIRST_CONTROLLED_SGSIM_RUNTIME_STATE_TRANSITION_ACCEPTED_R2"

E36_REL = Path(
    "provenance/hybrid_dp/"
    "V16E36_SHORT_ADAPTIVE_SGSIM_ROLLOUT_EARLY_PLUME_VALIDATION"
)
E36_SUMMARY = "PAD_Stream_V16E36_Summary.json"
E36_CLOSURE = "V16E36_Final_Closure.json"
E36_CACHE = "V16E36_Certified_Physics_Cache.npz"
E36_EXPECTED_STATUS = "SHORT_ADAPTIVE_SGSIM_ROLLOUT_EARLY_PLUME_VALIDATED"

C26_SUMMARY_REL = Path(
    "output/V16_C26_EXP2_PHYSICS_INFORMED_TRAINING_EXECUTION_"
    "BEST_VALIDATION_CHECKPOINT_LOCKED_TEST_EVALUATION/PAD_Stream_V16C26_Summary.json"
)

OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit"
)
BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_B1_R1_BLOCKED"
)

EXPECTED_STREAMLINES = 1078
EXPECTED_NODES = 201
EXPECTED_CVS = 200
EXPECTED_TEST_STREAMLINES = 161
EXPECTED_TEST_SAMPLES = 1449
EXPECTED_TARGET_DAYS = np.array(
    [30., 60., 100., 150., 250., 365., 500., 750., 1000.],
    dtype=np.float64,
)


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git_blob_sha(path: Path, root: Path) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), "hash-object", str(path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


def git_text(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


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
        raise GateError(
            f"artifact_not_found_with_exact_sha:{name}:{expected_sha}"
        )
    matches = sorted(
        set(matches),
        key=lambda p: (len(str(p)), str(p)),
    )
    return matches[0]


def build_model(tf):
    i = tf.keras.Input(
        (201, 9),
        name="v16_required_sequence",
    )
    x = tf.keras.layers.LSTM(
        64,
        return_sequences=True,
        name="lstm_1",
    )(i)
    x = tf.keras.layers.LSTM(
        64,
        return_sequences=True,
        name="lstm_2",
    )(x)
    x = tf.keras.layers.TimeDistributed(
        tf.keras.layers.Dense(1),
        name="td_dense",
    )(x)
    x = tf.keras.layers.Activation(
        "sigmoid",
        name="bounded_sigmoid",
    )(x)
    x = tf.keras.layers.Rescaling(
        .6,
        offset=.2,
        name="bounded_saturation",
    )(x)
    o = tf.keras.layers.Reshape(
        (201,),
        name="Sw_sequence",
    )(x)
    return tf.keras.Model(
        i,
        o,
        name="PAD_Stream_V16C26_EXP2",
    )


def e37a_mass_factor(
    r2: Any,
    saturation: np.ndarray,
) -> np.ndarray:
    sat = np.asarray(saturation, dtype=np.float64)
    sg = np.clip(
        sat - float(r2.BACKGROUND_SATURATION),
        0.0,
        float(r2.MAX_INCREMENTAL_CO2_SATURATION),
    )
    pc = np.asarray(
        r2.capillary_pressure_from_incremental_sg(sg),
        dtype=np.float64,
    )
    return (
        np.exp(
            np.clip(
                float(r2.CO2_COMPRESSIBILITY_1_PA) * pc,
                -50.0,
                50.0,
            )
        )
        * sg
    )


def project_201_to_200_component_mass(
    r2: Any,
    e37a: Any,
    saturation_201: np.ndarray,
    cv_pressure_mass_coeff: np.ndarray,
    streamline_index: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    BR geometry composed with the E37A component-mass constitutive state.

    Target CV j receives one half of state j and one half of state j+1 in
    component-mass space:

        M_j = C_j * [0.5*g(S_j) + 0.5*g(S_{j+1})]

    C_j is E37A's exact target-CV pressure-mass coefficient and
    g(S)=exp(c_g Pc(Sg))*Sg.

    Saturation is recovered only after the conservative mass projection by
    E37A's nonlinear inversion. No saturation averaging is used as the
    conservation operation.
    """
    s = np.asarray(saturation_201, dtype=np.float64)
    ids = np.asarray(streamline_index, dtype=np.int64)

    if s.ndim != 2 or s.shape[1] != EXPECTED_NODES:
        raise GateError(f"source_saturation_shape:{s.shape}")
    if ids.shape != (len(s),):
        raise GateError(
            f"streamline_index_shape:{ids.shape}:{len(s)}"
        )

    coeff = np.asarray(
        cv_pressure_mass_coeff,
        dtype=np.float64,
    )[ids]
    if coeff.shape != (len(s), EXPECTED_CVS):
        raise GateError(f"target_coeff_shape:{coeff.shape}")

    g = e37a_mass_factor(r2, s)
    g200 = 0.5 * g[:, :-1] + 0.5 * g[:, 1:]
    mass200 = coeff * g200

    sat200 = e37a.invert_cv_mass_to_saturation(
        r2,
        mass200,
        coeff,
    )

    # Explicit 201-state mass ledger induced by the exact half-overlap.
    source_mass = np.zeros_like(s, dtype=np.float64)
    source_mass[:, 0] = 0.5 * coeff[:, 0] * g[:, 0]
    source_mass[:, -1] = 0.5 * coeff[:, -1] * g[:, -1]
    source_mass[:, 1:-1] = (
        0.5 * coeff[:, :-1] * g[:, 1:-1]
        + 0.5 * coeff[:, 1:] * g[:, 1:-1]
    )
    return sat200, mass200, source_mass


def metrics(
    pred: np.ndarray,
    truth: np.ndarray,
) -> dict[str, float]:
    e = (
        np.asarray(pred, dtype=np.float64)
        - np.asarray(truth, dtype=np.float64)
    )
    mse = float(np.mean(e * e))
    return {
        "mse": mse,
        "rmse": float(np.sqrt(mse)),
        "mae": float(np.mean(np.abs(e))),
        "max_abs_error": float(np.max(np.abs(e))),
        "prediction_min": float(np.min(pred)),
        "prediction_max": float(np.max(pred)),
    }


def self_test() -> None:
    class R2Stub:
        BACKGROUND_SATURATION = 0.20
        MAX_INCREMENTAL_CO2_SATURATION = 0.60
        CO2_COMPRESSIBILITY_1_PA = 1.0e-8

        @staticmethod
        def capillary_pressure_from_incremental_sg(sg):
            sg = np.asarray(sg, dtype=np.float64)
            sw = 1.0 - sg
            se = np.clip(
                (sw - 0.20) / 0.80,
                1.0e-4,
                1.0,
            )
            return 2.0e6 * se ** (-0.5)

    class E37Stub:
        @staticmethod
        def cv_mass_from_saturation(r2, sat, coeff):
            return coeff * e37a_mass_factor(r2, sat)

        @staticmethod
        def invert_cv_mass_to_saturation(r2, target, coeff):
            target = np.asarray(target, dtype=np.float64)
            coeff = np.asarray(coeff, dtype=np.float64)
            lo = np.zeros_like(target)
            hi = np.full_like(target, 0.60)
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                trial = coeff * e37a_mass_factor(
                    r2,
                    0.20 + mid,
                )
                below = trial < target
                lo = np.where(below, mid, lo)
                hi = np.where(below, hi, mid)
            return 0.20 + 0.5 * (lo + hi)

    r2 = R2Stub()
    e37 = E37Stub()

    coeff = np.vstack(
        [
            np.linspace(100.0, 300.0, EXPECTED_CVS),
            np.linspace(150.0, 350.0, EXPECTED_CVS),
            np.linspace(200.0, 400.0, EXPECTED_CVS),
        ]
    ).astype(np.float64)
    ids = np.array([0, 1, 2], dtype=np.int64)

    sconst = np.full(
        (3, EXPECTED_NODES),
        0.43,
        dtype=np.float64,
    )
    s200, m200, sm = project_201_to_200_component_mass(
        r2,
        e37,
        sconst,
        coeff,
        ids,
    )
    if np.max(np.abs(s200 - 0.43)) > 1.0e-12:
        raise RuntimeError(
            "self_test_constant_state_not_preserved"
        )
    if np.max(
        np.abs(
            np.sum(m200, axis=1)
            - np.sum(sm, axis=1)
        )
    ) > 1.0e-10:
        raise RuntimeError(
            "self_test_constant_mass_not_conserved"
        )

    ramp = np.vstack(
        [
            np.linspace(0.2, 0.8, EXPECTED_NODES),
            np.linspace(0.8, 0.2, EXPECTED_NODES),
            np.full(EXPECTED_NODES, 0.2),
        ]
    )
    s200, m200, sm = project_201_to_200_component_mass(
        r2,
        e37,
        ramp,
        coeff,
        ids,
    )
    if not np.all(np.isfinite(s200)):
        raise RuntimeError("self_test_nonfinite")
    if np.min(s200) < 0.2 - 1.0e-12:
        raise RuntimeError("self_test_lower_bound")
    if np.max(s200) > 0.8 + 1.0e-12:
        raise RuntimeError("self_test_upper_bound")
    if np.max(
        np.abs(
            np.sum(m200, axis=1)
            - np.sum(sm, axis=1)
        )
    ) > 1.0e-10:
        raise RuntimeError(
            "self_test_ramp_mass_not_conserved"
        )

    naive = 0.5 * (
        ramp[:, :-1] + ramp[:, 1:]
    )
    if np.max(np.abs(s200 - naive)) <= 1.0e-10:
        raise RuntimeError(
            "self_test_failed_to_distinguish_"
            "mass_projection_from_saturation_average"
        )

    print("POSTV16-AV1-B1-R1 self-test: PASS")


def main(
    root: Path,
    drive: Path,
) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    blocked = drive / BLOCKED_REL
    out = drive / OUT_REL

    def gate(
        name: str,
        passed: Any,
        value: Any = None,
    ) -> None:
        ok = bool(passed)
        gates[name] = {
            "passed": ok,
            "value": value,
        }
        suffix = (
            f" — {value}"
            if value is not None
            else ""
        )
        print(
            f"[{'PASS' if ok else 'FAIL'}] "
            f"{name}{suffix}"
        )
        if not ok:
            raise GateError(name)

    print("=" * 168)
    print(
        "POSTV16-AV1-B1-R1 — C26 -> E37A COMPONENT-MASS "
        "201-STATE / 200-CV RUNTIME REPRESENTATION-EQUIVALENCE AUDIT"
    )
    print("=" * 168)
    print(
        "LEVEL 1: C26 vs C17 on the frozen 201-state locked test."
    )
    print(
        "LEVEL 2: C26 and C17 independently mapped through exact BR "
        "half-overlap in E37A component-mass space, then inverted "
        "to 200-CV saturation."
    )
    print(
        "NO SATURATION AVERAGING IS AUTHORIZED. "
        "NO TRAINING OR RETUNING. NO TRANSPORT TIME MARCH. "
        "NO GRID MAPBACK. NO FROZEN ARTIFACT MUTATION.\n"
    )

    try:
        root = root.resolve()
        drive = drive.resolve()

        head = git_text(
            root,
            "rev-parse",
            "HEAD",
        )
        parent = git_text(
            root,
            "rev-parse",
            "HEAD^",
        )
        status = git_text(
            root,
            "status",
            "--porcelain",
        )
        is_ancestor = (
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "merge-base",
                    "--is-ancestor",
                    AV1B_BOUND_COMMIT,
                    "HEAD",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).returncode
            == 0
        )

        gate(
            "AV1B_bound_commit_is_ancestor",
            is_ancestor,
            AV1B_BOUND_COMMIT,
        )
        gate(
            "repository_parent_is_B1R3_R1_commit",
            parent == B1R3_R1_COMMIT,
            parent,
        )

        # Do not merely relax BR from immediate-parent to generic ancestor.
        # Reproduce every exact parent edge introduced by the provenance
        # recovery sequence.
        for label, commit, expected_parent in RECOVERY_LINEAGE:
            actual_parent = git_text(
                root,
                "rev-parse",
                f"{commit}^",
            )
            gate(
                f"{label}_historical_parent_exact",
                actual_parent == expected_parent,
                actual_parent,
            )
            ancestor_ok = (
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(root),
                        "merge-base",
                        "--is-ancestor",
                        commit,
                        "HEAD",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                ).returncode
                == 0
            )
            gate(
                f"{label}_is_ancestor_of_HEAD",
                ancestor_ok,
                commit,
            )

        gate(
            "repository_clean",
            status == "",
            repr(status),
        )

        for fname, blob in EXPECTED_BLOBS.items():
            p = root / fname
            actual = (
                git_blob_sha(p, root)
                if p.is_file()
                else "missing"
            )
            gate(
                f"{Path(fname).stem}_git_blob_exact",
                actual == blob,
                actual,
            )

        for fname, blob in RECOVERY_RUNNER_BLOBS.items():
            p = root / fname
            actual = (
                git_blob_sha(p, root)
                if p.is_file()
                else "missing"
            )
            gate(
                f"{Path(fname).stem}_git_blob_exact",
                actual == blob,
                actual,
            )

        stage = "artifact_binding"

        c18r = find_by_name_and_sha(
            [root, drive],
            C18R_NAME,
            C18R_SHA,
        )
        c19 = find_by_name_and_sha(
            [root, drive],
            C19_NAME,
            C19_SHA,
        )
        gate(
            "C18R_exact_dataset_SHA",
            sha256_file(c18r) == C18R_SHA,
            str(c18r),
        )
        gate(
            "C19_exact_split_SHA",
            sha256_file(c19) == C19_SHA,
            str(c19),
        )

        weights = drive / WEIGHTS_REL
        gate(
            "A3R3R_exact_embedded_weights_present",
            weights.is_file(),
            str(weights),
        )
        actual_weight_sha = (
            sha256_file(weights)
            if weights.is_file()
            else "missing"
        )
        gate(
            "A3R3R_exact_embedded_weight_SHA",
            actual_weight_sha == WEIGHTS_SHA,
            actual_weight_sha,
        )

        r2_summary_path = (
            drive / R2_REL / R2_SUMMARY
        )
        r2_state_path = (
            drive / R2_REL / R2_STATE
        )
        e36_summary_path = (
            drive / E36_REL / E36_SUMMARY
        )
        e36_closure_path = (
            drive / E36_REL / E36_CLOSURE
        )
        e36_cache_path = (
            drive / E36_REL / E36_CACHE
        )

        required = [
            ("R2_summary", r2_summary_path),
            ("R2_state", r2_state_path),
            ("E36_summary", e36_summary_path),
            ("E36_closure", e36_closure_path),
            ("E36_cache", e36_cache_path),
        ]
        for label, p in required:
            gate(
                f"{label}_present",
                p.is_file(),
                str(p),
            )

        r2_summary = load_json(
            r2_summary_path
        )
        e36_summary = load_json(
            e36_summary_path
        )
        e36_closure = load_json(
            e36_closure_path
        )

        gate(
            "R2_status_exact",
            r2_summary.get("status")
            == R2_EXPECTED_STATUS,
            r2_summary.get("status"),
        )
        gate(
            "E36_status_exact",
            e36_summary.get("status")
            == E36_EXPECTED_STATUS,
            e36_summary.get("status"),
        )

        e36_cache_sha = sha256_file(
            e36_cache_path
        )
        gate(
            "E36_cache_SHA_matches_E36_closure",
            e36_cache_sha
            == e36_closure.get(
                "certified_cache_sha256"
            ),
            e36_cache_sha,
        )

        stage = "load_authorities"

        r2 = load_module(
            root / R2,
            "postv16_av1_b1_r2",
        )
        e37a = load_module(
            root / E37A,
            "postv16_av1_b1_e37a",
        )

        with tempfile.TemporaryDirectory(
            prefix="POSTV16_AV1_B1_SG7D_"
        ) as td:
            td = Path(td)
            shutil.copy2(
                root / SG7D,
                td / SG7D,
            )
            sg7d = load_module(
                td / SG7D,
                "postv16_av1_b1_sg7d",
            )

            parent_state = load_npz(
                r2_state_path
            )
            cache = load_npz(
                e36_cache_path
            )

            pressure_psi = np.asarray(
                cache["accepted_pressure_psi"],
                dtype=np.float64,
            )
            xyz_m = np.asarray(
                cache["streamline_xyz_m"],
                dtype=np.float64,
            )
            tau_s = np.asarray(
                cache["streamline_tof_s"],
                dtype=np.float64,
            )
            tau_end_s = np.asarray(
                cache["tau_end_s"],
                dtype=np.float64,
            )
            weights_m3_s = np.asarray(
                cache["streamline_weights_m3_s"],
                dtype=np.float64,
            )
            xi_faces = np.asarray(
                cache["xi"],
                dtype=np.float64,
            )

            gate(
                "E36_cache_streamlines_1078",
                len(tau_end_s)
                == EXPECTED_STREAMLINES,
                len(tau_end_s),
            )
            gate(
                "E36_cache_faces_201",
                len(xi_faces)
                == EXPECTED_NODES,
                len(xi_faces),
            )
            gate(
                "E36_cache_runtime_CVs_200",
                len(xi_faces) - 1
                == EXPECTED_CVS,
                len(xi_faces) - 1,
            )
            gate(
                "E36_xi_uniform",
                np.allclose(
                    np.diff(xi_faces),
                    np.diff(xi_faces)[0],
                    rtol=1.0e-12,
                    atol=1.0e-14,
                ),
            )
            gate(
                "E36_xi_domain_0_1",
                abs(
                    float(xi_faces[0])
                )
                <= 1.0e-15
                and abs(
                    float(xi_faces[-1])
                    - 1.0
                )
                <= 1.0e-15,
            )

            weights_m3_day = (
                weights_m3_s
                * float(e37a.DAY_TO_S)
            )
            tof_days = (
                tau_s
                / float(e37a.DAY_TO_S)
            )

            operator = (
                sg7d.build_subsegment_operator(
                    xyz_m,
                    tof_days,
                    weights_m3_day,
                )
            )
            p_ref = scalar(
                parent_state[
                    "co2_density_reference_pressure_pa"
                ]
            )
            geometry = (
                e37a.build_control_volume_geometry(
                    r2,
                    operator,
                    pressure_psi,
                    p_ref,
                    EXPECTED_STREAMLINES,
                    EXPECTED_CVS,
                )
            )

            coeff = np.asarray(
                geometry[
                    "cv_pressure_mass_coeff"
                ],
                dtype=np.float64,
            )
            cv_pv = np.asarray(
                geometry["cv_pv_m3"],
                dtype=np.float64,
            )
            expected_cv_pv = (
                weights_m3_day[:, None]
                * np.diff(
                    tof_days,
                    axis=1,
                )
            )
            cv_pv_rel = float(
                np.linalg.norm(
                    (
                        cv_pv
                        - expected_cv_pv
                    ).ravel()
                )
                / max(
                    float(
                        np.linalg.norm(
                            expected_cv_pv.ravel()
                        )
                    ),
                    1.0e-30,
                )
            )

            gate(
                "E37A_exact_CV_pressure_mass_coeff_shape",
                coeff.shape
                == (
                    EXPECTED_STREAMLINES,
                    EXPECTED_CVS,
                ),
                coeff.shape,
            )
            gate(
                "E37A_exact_CV_pressure_mass_coeff_positive",
                bool(
                    np.all(
                        coeff > 0.0
                    )
                ),
            )
            gate(
                "SG7D_exact_CV_pore_volume_identity",
                cv_pv_rel
                <= 1.0e-10,
                cv_pv_rel,
            )

        stage = "locked_test_binding"

        d = load_npz(c18r)
        s = load_npz(c19)

        X7 = np.asarray(
            d["X_sequence_required"],
            dtype=np.float32,
        )
        Y = np.asarray(
            d["Y_transport"],
            dtype=np.float64,
        )
        th = np.asarray(
            d["target_time_hat"],
            dtype=np.float32,
        )
        eta_seq = np.asarray(
            d["target_eta_sequence"],
            dtype=np.float32,
        )
        sl = np.asarray(
            d["streamline_index"],
            dtype=np.int64,
        )
        ti = np.asarray(
            d["time_index"],
            dtype=np.int64,
        )
        target_days = np.asarray(
            d["target_time_days"],
            dtype=np.float64,
        )
        part = np.asarray(
            s["sample_partition_code"],
            dtype=np.int8,
        )

        gate(
            "C18R_X7_shape_exact",
            X7.shape
            == (9702, 201, 7),
            X7.shape,
        )
        gate(
            "C18R_Y_shape_exact",
            Y.shape
            == (9702, 201),
            Y.shape,
        )
        gate(
            "C19_partition_shape_exact",
            part.shape
            == (9702,),
            part.shape,
        )

        test = np.flatnonzero(
            part == 2
        )
        test_streamlines = np.unique(
            sl[test]
        )

        gate(
            "locked_test_sample_count_1449",
            len(test)
            == EXPECTED_TEST_SAMPLES,
            len(test),
        )
        gate(
            "locked_test_streamline_count_161",
            len(test_streamlines)
            == EXPECTED_TEST_STREAMLINES,
            len(test_streamlines),
        )
        gate(
            "locked_test_all_nine_times_per_streamline",
            all(
                np.sum(
                    sl[test] == g
                )
                == 9
                for g in test_streamlines
            ),
        )
        unique_days = np.unique(
            target_days[test]
        )
        gate(
            "locked_test_target_days_exact",
            np.array_equal(
                unique_days,
                EXPECTED_TARGET_DAYS,
            ),
            unique_days.tolist(),
        )

        T = np.broadcast_to(
            th[:, None, None],
            (
                len(th),
                EXPECTED_NODES,
                1,
            ),
        ).astype(np.float32)
        X = np.concatenate(
            [
                X7,
                T,
                eta_seq[
                    :,
                    :,
                    None,
                ].astype(np.float32),
            ],
            axis=2,
        )

        gate(
            "C26_input_shape_9702_201_9",
            X.shape
            == (9702, 201, 9),
            X.shape,
        )

        stage = "C26_inference"

        import tensorflow as tf

        try:
            tf.config.experimental.enable_op_determinism()
        except Exception:
            pass

        tf.keras.utils.set_random_seed(
            16021
        )
        model = build_model(tf)

        gate(
            "C26_reconstructed_input_shape_201x9",
            model.input_shape
            == (None, 201, 9),
            model.input_shape,
        )
        gate(
            "C26_reconstructed_output_shape_201",
            model.output_shape
            == (None, 201),
            model.output_shape,
        )
        gate(
            "C26_reconstructed_parameter_count_52033",
            model.count_params()
            == 52033,
            model.count_params(),
        )

        model.load_weights(
            weights
        )

        pred201 = (
            model.predict(
                X[test],
                batch_size=64,
                verbose=0,
            )
            .astype(
                np.float64
            )
        )
        true201 = Y[
            test
        ].astype(np.float64)

        gate(
            "C26_locked_test_prediction_shape_1449_201",
            pred201.shape
            == (1449, 201),
            pred201.shape,
        )
        gate(
            "C26_locked_test_predictions_finite",
            bool(
                np.isfinite(
                    pred201
                ).all()
            ),
        )

        pmin = float(
            np.min(
                pred201
            )
        )
        pmax = float(
            np.max(
                pred201
            )
        )
        gate(
            "C26_locked_test_predictions_bounded",
            pmin
            >= 0.2 - 1.0e-6
            and pmax
            <= 0.8 + 1.0e-6,
            (pmin, pmax),
        )

        level1 = metrics(
            pred201,
            true201,
        )
        hist = load_json(
            root / C26_SUMMARY_REL
        )["locked_test"]

        metric_tol = {
            "mse": 5.0e-7,
            "rmse": 5.0e-6,
            "mae": 5.0e-6,
            "max_abs_error": 5.0e-5,
            "prediction_min": 5.0e-5,
            "prediction_max": 5.0e-5,
        }
        for key, tol in metric_tol.items():
            gate(
                f"C26_level1_{key}_reproduces_historical",
                abs(
                    level1[key]
                    - float(
                        hist[key]
                    )
                )
                <= tol,
                (
                    f"{level1[key]} "
                    f"vs {hist[key]} "
                    f"(tol {tol})"
                ),
            )

        stage = "component_mass_projection"

        ids = sl[test]

        (
            pred200,
            pred_mass200,
            pred_source_mass201,
        ) = project_201_to_200_component_mass(
            r2,
            e37a,
            pred201,
            coeff,
            ids,
        )
        (
            true200,
            true_mass200,
            true_source_mass201,
        ) = project_201_to_200_component_mass(
            r2,
            e37a,
            true201,
            coeff,
            ids,
        )

        gate(
            "level2_pred_shape_1449_200",
            pred200.shape
            == (1449, 200),
            pred200.shape,
        )
        gate(
            "level2_true_shape_1449_200",
            true200.shape
            == (1449, 200),
            true200.shape,
        )
        gate(
            "level2_states_finite",
            bool(
                np.isfinite(
                    pred200
                ).all()
                and np.isfinite(
                    true200
                ).all()
            ),
        )

        smin = float(
            min(
                np.min(pred200),
                np.min(true200),
            )
        )
        smax = float(
            max(
                np.max(pred200),
                np.max(true200),
            )
        )
        gate(
            "level2_states_within_0p2_0p8",
            smin
            >= 0.2 - 1.0e-10
            and smax
            <= 0.8 + 1.0e-10,
            (smin, smax),
        )

        pred_mass_resid = (
            np.sum(
                pred_mass200,
                axis=1,
            )
            - np.sum(
                pred_source_mass201,
                axis=1,
            )
        )
        true_mass_resid = (
            np.sum(
                true_mass200,
                axis=1,
            )
            - np.sum(
                true_source_mass201,
                axis=1,
            )
        )
        pred_scale = np.maximum(
            np.sum(
                np.abs(
                    pred_mass200
                ),
                axis=1,
            ),
            1.0,
        )
        true_scale = np.maximum(
            np.sum(
                np.abs(
                    true_mass200
                ),
                axis=1,
            ),
            1.0,
        )
        pred_mass_rel = float(
            np.max(
                np.abs(
                    pred_mass_resid
                )
                / pred_scale
            )
        )
        true_mass_rel = float(
            np.max(
                np.abs(
                    true_mass_resid
                )
                / true_scale
            )
        )

        gate(
            "C26_201_to_200_component_mass_conservation",
            pred_mass_rel
            <= 5.0e-15,
            pred_mass_rel,
        )
        gate(
            "C17_201_to_200_component_mass_conservation",
            true_mass_rel
            <= 5.0e-15,
            true_mass_rel,
        )

        pred_recon = (
            e37a.cv_mass_from_saturation(
                r2,
                pred200,
                coeff[ids],
            )
        )
        true_recon = (
            e37a.cv_mass_from_saturation(
                r2,
                true200,
                coeff[ids],
            )
        )

        pred_inv_rel = float(
            np.max(
                np.abs(
                    pred_recon
                    - pred_mass200
                )
                / np.maximum(
                    np.abs(
                        pred_mass200
                    ),
                    1.0,
                )
            )
        )
        true_inv_rel = float(
            np.max(
                np.abs(
                    true_recon
                    - true_mass200
                )
                / np.maximum(
                    np.abs(
                        true_mass200
                    ),
                    1.0,
                )
            )
        )

        gate(
            "C26_E37A_mass_inversion_closure",
            pred_inv_rel
            <= 1.0e-10,
            pred_inv_rel,
        )
        gate(
            "C17_E37A_mass_inversion_closure",
            true_inv_rel
            <= 1.0e-10,
            true_inv_rel,
        )

        naive_pred = 0.5 * (
            pred201[:, :-1]
            + pred201[:, 1:]
        )
        naive_true = 0.5 * (
            true201[:, :-1]
            + true201[:, 1:]
        )
        nonlinear_gap_pred = float(
            np.max(
                np.abs(
                    pred200
                    - naive_pred
                )
            )
        )
        nonlinear_gap_true = float(
            np.max(
                np.abs(
                    true200
                    - naive_true
                )
            )
        )

        gate(
            "component_mass_projection_not_replaced_by_saturation_average",
            max(
                nonlinear_gap_pred,
                nonlinear_gap_true,
            )
            > 0.0,
            (
                nonlinear_gap_pred,
                nonlinear_gap_true,
            ),
        )
        gate(
            "direct_saturation_average_remains_unauthorized",
            True,
        )

        level2 = metrics(
            pred200,
            true200,
        )

        day_rows = []
        for day in EXPECTED_TARGET_DAYS:
            m = np.isclose(
                target_days[test],
                day,
                rtol=0.0,
                atol=1.0e-12,
            )
            a = metrics(
                pred201[m],
                true201[m],
            )
            b = metrics(
                pred200[m],
                true200[m],
            )
            day_rows.append(
                {
                    "target_day": float(
                        day
                    ),
                    "samples": int(
                        np.sum(m)
                    ),
                    "level1_201_rmse": a[
                        "rmse"
                    ],
                    "level1_201_mae": a[
                        "mae"
                    ],
                    "level1_201_max_abs": a[
                        "max_abs_error"
                    ],
                    "level2_200_rmse": b[
                        "rmse"
                    ],
                    "level2_200_mae": b[
                        "mae"
                    ],
                    "level2_200_max_abs": b[
                        "max_abs_error"
                    ],
                }
            )

        gate(
            "no_new_accuracy_acceptance_threshold_introduced",
            True,
        )
        gate(
            "no_training_or_retuning_performed",
            True,
        )
        gate(
            "no_transport_time_march_executed",
            True,
        )
        gate(
            "no_grid_mapback_executed",
            True,
        )
        gate(
            "no_frozen_V16_artifact_modified",
            True,
        )

        stage = "publish"

        theory = {
            "milestone": MILESTONE,
            "level1": (
                "C26 vs C17 frozen locked-test saturation "
                "on native 201-state representation"
            ),
            "level2": (
                "C26 and C17 separately encoded into E37A "
                "CO2 component mass on exact 200 runtime CVs, "
                "then inverted with E37A constitutive law"
            ),
            "geometry_authority": (
                "POSTV16-AV1-BR exact half-half target-CV overlap"
            ),
            "target_mass_equation": (
                "M_j = C_j * (0.5*g(S_j) + 0.5*g(S_{j+1}))"
            ),
            "g_of_S": (
                "g(S)=exp(c_g*Pc(clip(S-0.2,0,0.6)))"
                "*clip(S-0.2,0,0.6)"
            ),
            "C_j": (
                "E37A exact cv_pressure_mass_coeff from SG7D "
                "subsegments and certified E36 pressure field"
            ),
            "saturation_average_authorized": False,
            "mass_inversion": (
                "E37A invert_cv_mass_to_saturation"
            ),
            "accuracy_threshold_selected": False,
            "interpretation": (
                "B1 measures how the already-frozen C26-vs-C17 "
                "error appears after exact runtime-representation "
                "conversion; it does not retune or accept/reject "
                "deployment accuracy."
            ),
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "repository_head": head,
            "repository_parent": parent,
            "locked_test_samples": int(
                len(test)
            ),
            "locked_test_streamlines": int(
                len(test_streamlines)
            ),
            "target_days": (
                EXPECTED_TARGET_DAYS.tolist()
            ),
            "level1_native_201_state_metrics": (
                level1
            ),
            "level2_E37A_200_CV_component_mass_metrics": (
                level2
            ),
            "max_C26_mass_conservation_relative_residual": (
                pred_mass_rel
            ),
            "max_C17_mass_conservation_relative_residual": (
                true_mass_rel
            ),
            "max_C26_mass_inversion_relative_residual": (
                pred_inv_rel
            ),
            "max_C17_mass_inversion_relative_residual": (
                true_inv_rel
            ),
            "max_C26_mass_vs_naive_saturation_average_gap": (
                nonlinear_gap_pred
            ),
            "max_C17_mass_vs_naive_saturation_average_gap": (
                nonlinear_gap_true
            ),
            "saturation_averaging_authorized": False,
            "training_performed": False,
            "retuning_performed": False,
            "transport_time_march_executed": False,
            "grid_mapback_executed": False,
            "accuracy_acceptance_threshold_selected": False,
            "next": NEXT,
        }

        arrays = {
            "test_sample_indices": (
                test.astype(
                    np.int64
                )
            ),
            "streamline_index": (
                ids.astype(
                    np.int64
                )
            ),
            "time_index": (
                ti[test].astype(
                    np.int64
                )
            ),
            "target_time_days": (
                target_days[
                    test
                ].astype(
                    np.float64
                )
            ),
            "C26_pred_201": (
                pred201.astype(
                    np.float64
                )
            ),
            "C17_true_201": (
                true201.astype(
                    np.float64
                )
            ),
            "C26_pred_E37A_200": (
                pred200.astype(
                    np.float64
                )
            ),
            "C17_true_E37A_200": (
                true200.astype(
                    np.float64
                )
            ),
            "C26_component_mass_200_kg": (
                pred_mass200.astype(
                    np.float64
                )
            ),
            "C17_component_mass_200_kg": (
                true_mass200.astype(
                    np.float64
                )
            ),
        }

        files = {
            "POSTV16_AV1_B1_Theory_Contract.json": (
                json_bytes(
                    theory
                )
            ),
            "POSTV16_AV1_B1_Level1_Level2_By_Target_Day.csv": (
                csv_bytes(
                    day_rows
                )
            ),
            "POSTV16_AV1_B1_Level1_Level2_Arrays.npz": (
                deterministic_npz_bytes(
                    arrays
                )
            ),
            "PAD_Stream_POSTV16_AV1_B1_Summary.json": (
                json_bytes(
                    summary
                )
            ),
            "POSTV16_AV1_B1_Final_Gate_Matrix.csv": (
                csv_bytes(
                    [
                        {
                            "gate": k,
                            **v,
                        }
                        for k, v
                        in gates.items()
                    ]
                )
            ),
        }

        closure = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "all_gates_passed": all(
                v["passed"]
                for v in gates.values()
            ),
            "gate_count": len(
                gates
            ),
            "level1_completed": True,
            "level2_component_mass_projection_completed": True,
            "E37A_exact_pressure_mass_coefficients_used": True,
            "saturation_average_used": False,
            "training_or_retuning": False,
            "frozen_artifact_mutation": False,
            "next": NEXT,
        }
        files[
            "POSTV16_AV1_B1_Final_Closure.json"
        ] = json_bytes(
            closure
        )

        immutable_publish(
            out,
            files,
        )

        manifest = []
        for p in sorted(
            out.iterdir()
        ):
            if (
                p.is_file()
                and p.name
                != "POSTV16_AV1_B1_Artifact_Manifest.csv"
            ):
                manifest.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(
                            p
                        ),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_publish(
            out,
            {
                "POSTV16_AV1_B1_Artifact_Manifest.csv": (
                    csv_bytes(
                        manifest
                    )
                )
            },
        )

        print(
            "\n"
            + "=" * 168
        )
        print(
            "POSTV16-AV1-B1-R1: PASS"
        )
        print(
            "=" * 168
        )
        print(
            f"{'Status':86}: "
            f"{STATUS_PASS}"
        )
        print(
            f"{'Locked test samples / streamlines':86}: "
            f"{len(test)} / {len(test_streamlines)}"
        )
        print(
            f"{'Level 1 — 201-state RMSE / MAE / max abs':86}: "
            f"{level1['rmse']:.12e} / "
            f"{level1['mae']:.12e} / "
            f"{level1['max_abs_error']:.12e}"
        )
        print(
            f"{'Level 2 — E37A 200-CV RMSE / MAE / max abs':86}: "
            f"{level2['rmse']:.12e} / "
            f"{level2['mae']:.12e} / "
            f"{level2['max_abs_error']:.12e}"
        )
        print(
            f"{'C26 max component-mass conservation relative residual':86}: "
            f"{pred_mass_rel:.12e}"
        )
        print(
            f"{'C17 max component-mass conservation relative residual':86}: "
            f"{true_mass_rel:.12e}"
        )
        print(
            f"{'C26 / C17 mass inversion relative residual':86}: "
            f"{pred_inv_rel:.12e} / "
            f"{true_inv_rel:.12e}"
        )
        print(
            f"{'C26 max gap vs prohibited saturation average':86}: "
            f"{nonlinear_gap_pred:.12e}"
        )
        print(
            f"{'C17 max gap vs prohibited saturation average':86}: "
            f"{nonlinear_gap_true:.12e}"
        )
        print(
            f"{'Saturation averaging authorized':86}: False"
        )
        print(
            f"{'Training / retuning performed':86}: False / False"
        )
        print(
            f"{'Transport time march / grid mapback executed':86}: "
            f"False / False"
        )
        print(
            f"{'New accuracy acceptance threshold selected':86}: False"
        )
        print(
            f"{'NEXT':86}: "
            f"{NEXT}"
        )
        print(
            "=" * 168
        )
        return 0

    except Exception as exc:
        blocked.mkdir(
            parents=True,
            exist_ok=True,
        )
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(
                exc
            ),
            "gates": gates,
            "training_or_retuning": False,
            "frozen_artifact_mutation": False,
            "next_action": (
                "Audit only the failed B1 gate(s). "
                "Do not reinterpret Level-2 accuracy or "
                "proceed to deployment acceptance."
            ),
        }
        data = json_bytes(
            report
        )
        p = (
            blocked
            / "POSTV16_AV1_B1_R1_Blocked_Report.json"
        )
        if (
            p.exists()
            and p.read_bytes()
            != data
        ):
            p = (
                blocked
                / (
                    "POSTV16_AV1_B1_R1_Blocked_Report_"
                    f"{hashlib.sha256(data).hexdigest()[:12]}"
                    ".json"
                )
            )
        if not p.exists():
            p.write_bytes(
                data
            )

        print(
            "\n"
            + "=" * 168
        )
        print(
            "POSTV16-AV1-B1-R1: BLOCKED"
        )
        print(
            "=" * 168
        )
        print(
            "Failed stage:",
            stage,
        )
        print(
            "Exception   :",
            repr(
                exc
            ),
        )
        print(
            "Report      :",
            p,
        )
        return 2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
    )
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path(
            "/content/drive/MyDrive/PAD_Stream_Compute"
        ),
    )
    p.add_argument(
        "--self-test",
        action="store_true",
    )
    return p.parse_args()


if __name__ == "__main__":
    a = parse_args()
    if a.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(
        main(
            a.project_root,
            a.drive_root,
        )
    )

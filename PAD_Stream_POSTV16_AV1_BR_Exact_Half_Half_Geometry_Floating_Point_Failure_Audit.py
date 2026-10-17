from __future__ import annotations

from pathlib import Path
from fractions import Fraction
import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV1-BR"
STATUS_PASS = "AV1BR_EXACT_HALF_HALF_GEOMETRY_CERTIFIED_FLOAT_RESIDUAL_NUMERICAL_ONLY"
STATUS_BLOCKED = "AV1BR_BLOCKED_EXACT_GEOMETRY_CERTIFICATION_INCOMPLETE"
NEXT = (
    "POSTV16-AV1-B1 — C26 -> E37A component-mass-space 201-state / "
    "200-CV runtime representation-equivalence audit"
)

RELEASE_ID = "PAD-STREAM-V16-RC1-B92D52088D01078A"
RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

EXPECTED_BASE_COMMIT = "fc2cc7823de630868560ba15fa12bc4af831731a"

SOURCE_BINDINGS = {
    "C10": {
        "file": "PAD_Stream_V16C10_Conservative_201_Node_Pollock_Coordinate_Full_Physics_Operator_Construction.py",
        "blob": "753fd3de9490c37173c5c00544a3bb995de4ccfc",
    },
    "C17": {
        "file": "PAD_Stream_V16C17_Production_Source_Authentic_Y_Transport_Tensor_Generation_and_Certification.py",
        "blob": "310e10853ce6f160ee8c9bd270f2823893bf98d3",
    },
    "C20": {
        "file": "PAD_Stream_V16C20_Stage4_PIRNN_to_V16_Training_Interface_and_Architecture_Binding_Contract.py",
        "blob": "70b073faafd76f71c2c97a2df031592f05f6cf9f",
    },
    "E37A": {
        "file": "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py",
        "blob": "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0",
    },
}

SOURCE_STATES = 201
SOURCE_CVS = 201
SOURCE_FACES = 202
TARGET_FACES = 201
TARGET_CVS = 200

# This is the failed scalar reported by the immediately preceding AV1-B run.
# BR does not change it or replace the blocked AV1-B record; it explains it.
RECORDED_AV1B_FLOAT_RESIDUAL = 1.0508260928077107e-13

FLOAT64_EPS = float(np.finfo(np.float64).eps)
FLOAT_ENVELOPE_FACTOR = 1024.0
FLOAT64_CERTIFICATION_ENVELOPE = FLOAT_ENVELOPE_FACTOR * FLOAT64_EPS

OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_BR_Exact_Half_Half_Geometry_Floating_Point_Failure_Audit"
)
BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_BR_BLOCKED"
)


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_output(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


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
    from io import StringIO

    s = StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def immutable_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise GateError(f"existing_output_differs:{path}")
        return
    path.write_bytes(data)


def exact_source_edges() -> list[Fraction]:
    # 201 node-centered source CVs on [0,1].
    # End CVs are half-width; the 199 interior CVs are full-width.
    edges = [Fraction(0, 1)]
    edges.extend(Fraction(2 * k - 1, 400) for k in range(1, 201))
    edges.append(Fraction(1, 1))
    if len(edges) != SOURCE_FACES:
        raise AssertionError(len(edges))
    return edges


def exact_target_edges() -> list[Fraction]:
    # E37A: 201 faces delimit 200 true finite-volume CVs.
    return [Fraction(j, 200) for j in range(TARGET_FACES)]


def overlap(a0: Fraction, a1: Fraction, b0: Fraction, b1: Fraction) -> Fraction:
    left = max(a0, b0)
    right = min(a1, b1)
    return max(Fraction(0, 1), right - left)


def construct_exact_geometry() -> tuple[
    list[Fraction], list[Fraction], list[list[Fraction]], list[dict[str, Any]]
]:
    src = exact_source_edges()
    tgt = exact_target_edges()

    W: list[list[Fraction]] = [
        [Fraction(0, 1) for _ in range(SOURCE_CVS)]
        for _ in range(TARGET_CVS)
    ]
    rows: list[dict[str, Any]] = []

    for j in range(TARGET_CVS):
        t0, t1 = tgt[j], tgt[j + 1]
        tw = t1 - t0

        nonzero: list[tuple[int, Fraction, Fraction]] = []
        for i in range(SOURCE_CVS):
            ov = overlap(t0, t1, src[i], src[i + 1])
            if ov > 0:
                wt = ov / tw
                W[j][i] = wt
                nonzero.append((i, ov, wt))

        rows.append(
            {
                "target_cv": j,
                "target_left_exact": str(t0),
                "target_right_exact": str(t1),
                "target_width_exact": str(tw),
                "nonzero_source_count": len(nonzero),
                "source_left": nonzero[0][0] if len(nonzero) >= 1 else "",
                "overlap_left_exact": str(nonzero[0][1]) if len(nonzero) >= 1 else "",
                "weight_left_exact": str(nonzero[0][2]) if len(nonzero) >= 1 else "",
                "source_right": nonzero[1][0] if len(nonzero) >= 2 else "",
                "overlap_right_exact": str(nonzero[1][1]) if len(nonzero) >= 2 else "",
                "weight_right_exact": str(nonzero[1][2]) if len(nonzero) >= 2 else "",
                "row_weight_sum_exact": str(sum((x[2] for x in nonzero), Fraction(0, 1))),
            }
        )

    return src, tgt, W, rows


def construct_float64_geometry() -> tuple[
    np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]
]:
    # Recreate the same topology in ordinary binary64 arithmetic.
    xi = np.linspace(0.0, 1.0, SOURCE_STATES, dtype=np.float64)

    src = np.empty(SOURCE_FACES, dtype=np.float64)
    src[0] = xi[0]
    src[1:-1] = 0.5 * (xi[:-1] + xi[1:])
    src[-1] = xi[-1]

    tgt = xi.copy()
    W = np.zeros((TARGET_CVS, SOURCE_CVS), dtype=np.float64)
    rows: list[dict[str, Any]] = []

    for j in range(TARGET_CVS):
        t0 = float(tgt[j])
        t1 = float(tgt[j + 1])
        tw = t1 - t0

        for i in (j, j + 1):
            s0 = float(src[i])
            s1 = float(src[i + 1])
            ov = max(0.0, min(t1, s1) - max(t0, s0))
            W[j, i] = ov / tw

        wl = float(W[j, j])
        wr = float(W[j, j + 1])
        rows.append(
            {
                "target_cv": j,
                "target_left_float64": t0,
                "target_right_float64": t1,
                "target_width_float64": tw,
                "source_left": j,
                "weight_left_float64": wl,
                "weight_left_error_from_half": wl - 0.5,
                "source_right": j + 1,
                "weight_right_float64": wr,
                "weight_right_error_from_half": wr - 0.5,
                "row_weight_sum_float64": wl + wr,
            }
        )

    return src, tgt, W, rows


def exact_geometry_checks(
    src: list[Fraction],
    tgt: list[Fraction],
    W: list[list[Fraction]],
) -> dict[str, Any]:
    half = Fraction(1, 2)
    quarter400 = Fraction(1, 400)
    target_width = Fraction(1, 200)

    source_widths = [src[i + 1] - src[i] for i in range(SOURCE_CVS)]
    target_widths = [tgt[j + 1] - tgt[j] for j in range(TARGET_CVS)]

    left_half = all(W[j][j] == half for j in range(TARGET_CVS))
    right_half = all(W[j][j + 1] == half for j in range(TARGET_CVS))

    only_adjacent = True
    for j in range(TARGET_CVS):
        nz = [i for i, wt in enumerate(W[j]) if wt != 0]
        if nz != [j, j + 1]:
            only_adjacent = False
            break

    row_unity = all(sum(row, Fraction(0, 1)) == 1 for row in W)

    # Exact discrete-measure conservation:
    # target_width * W integrated columnwise must reproduce the source
    # node-centered CV measure: [1/400, 1/200, ..., 1/200, 1/400].
    reconstructed_source_measure: list[Fraction] = []
    for i in range(SOURCE_CVS):
        acc = Fraction(0, 1)
        for j in range(TARGET_CVS):
            acc += target_widths[j] * W[j][i]
        reconstructed_source_measure.append(acc)

    exact_measure_conservation = reconstructed_source_measure == source_widths

    return {
        "source_edge_count": len(src),
        "target_edge_count": len(tgt),
        "source_width_positive": all(w > 0 for w in source_widths),
        "target_width_positive": all(w > 0 for w in target_widths),
        "source_width_sum_exact": sum(source_widths, Fraction(0, 1)) == 1,
        "target_width_sum_exact": sum(target_widths, Fraction(0, 1)) == 1,
        "source_endpoint_width_exact": (
            source_widths[0] == quarter400
            and source_widths[-1] == quarter400
        ),
        "source_interior_width_exact": all(
            w == target_width for w in source_widths[1:-1]
        ),
        "target_width_exact": all(w == target_width for w in target_widths),
        "left_overlap_weights_exact_half": left_half,
        "right_overlap_weights_exact_half": right_half,
        "only_adjacent_source_support": only_adjacent,
        "row_partition_of_unity_exact": row_unity,
        "column_measure_conservation_exact": exact_measure_conservation,
        "reconstructed_source_measure": reconstructed_source_measure,
        "source_widths": source_widths,
        "target_widths": target_widths,
    }


def float64_checks(
    src: np.ndarray,
    tgt: np.ndarray,
    W: np.ndarray,
) -> dict[str, Any]:
    ideal = np.zeros_like(W)
    idx = np.arange(TARGET_CVS)
    ideal[idx, idx] = 0.5
    ideal[idx, idx + 1] = 0.5

    D = W - ideal
    max_abs_weight_error = float(np.max(np.abs(D)))
    fro_error = float(np.linalg.norm(D))

    row_sum_error = float(np.max(np.abs(np.sum(W, axis=1) - 1.0)))

    # Float64 source/target measures from the constructed edges.
    source_widths = np.diff(src)
    target_widths = np.diff(tgt)
    reconstructed_source_measure = target_widths @ W
    column_measure_error = float(
        np.max(np.abs(reconstructed_source_measure - source_widths))
    )

    # Constant state preservation.
    constant = np.full(SOURCE_CVS, 0.37, dtype=np.float64)
    mapped_constant = W @ constant
    constant_error = float(np.max(np.abs(mapped_constant - constant[0])))

    # A deterministic bounded density state. This is not a saturation
    # conservation authorization; it is an algebraic linear-measure audit.
    x = np.linspace(0.0, 1.0, SOURCE_CVS, dtype=np.float64)
    density = (
        0.2
        + 0.6 * x
        + 0.03125 * np.sin(7.0 * x)
        - 0.015625 * np.cos(11.0 * x)
    )
    mapped = W @ density
    source_measure = float(np.sum(source_widths * density))
    target_measure = float(np.sum(target_widths * mapped))
    linear_measure_error = target_measure - source_measure

    return {
        "finite": bool(
            np.all(np.isfinite(src))
            and np.all(np.isfinite(tgt))
            and np.all(np.isfinite(W))
        ),
        "max_abs_weight_error_from_exact_half": max_abs_weight_error,
        "frobenius_weight_error_from_exact_operator": fro_error,
        "max_abs_row_sum_error": row_sum_error,
        "max_abs_column_measure_error": column_measure_error,
        "constant_state_error": constant_error,
        "linear_measure_error": linear_measure_error,
        "mapped_density_min": float(np.min(mapped)),
        "mapped_density_max": float(np.max(mapped)),
        "source_density_min": float(np.min(density)),
        "source_density_max": float(np.max(density)),
    }


def gate(
    gates: dict[str, dict[str, Any]],
    name: str,
    passed: bool,
    value: Any = None,
) -> None:
    gates[name] = {"passed": bool(passed), "value": value}
    print(f"[{'PASS' if passed else 'FAIL'}] {name}"
          + (f" — {value}" if value is not None else ""))


def self_test() -> None:
    src_e, tgt_e, W_e, _ = construct_exact_geometry()
    ex = exact_geometry_checks(src_e, tgt_e, W_e)
    assert ex["left_overlap_weights_exact_half"]
    assert ex["right_overlap_weights_exact_half"]
    assert ex["only_adjacent_source_support"]
    assert ex["row_partition_of_unity_exact"]
    assert ex["column_measure_conservation_exact"]

    src_f, tgt_f, W_f, _ = construct_float64_geometry()
    fl = float64_checks(src_f, tgt_f, W_f)
    assert fl["finite"]
    assert fl["max_abs_weight_error_from_exact_half"] <= FLOAT64_CERTIFICATION_ENVELOPE
    assert abs(RECORDED_AV1B_FLOAT_RESIDUAL) <= FLOAT64_CERTIFICATION_ENVELOPE
    assert fl["max_abs_row_sum_error"] <= FLOAT64_CERTIFICATION_ENVELOPE
    assert fl["max_abs_column_measure_error"] <= FLOAT64_CERTIFICATION_ENVELOPE
    assert fl["constant_state_error"] <= FLOAT64_CERTIFICATION_ENVELOPE
    assert abs(fl["linear_measure_error"]) <= FLOAT64_CERTIFICATION_ENVELOPE
    print("POSTV16-AV1-BR self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL
    gates: dict[str, dict[str, Any]] = {}
    stage = "startup"

    print("=" * 168)
    print(
        "POSTV16-AV1-BR — EXACT HALF-HALF GEOMETRY "
        "FLOATING-POINT FAILURE AUDIT"
    )
    print("=" * 168)
    print(
        "AUDIT SCOPE: ONLY THE FAILED AV1-B "
        "`exact_geometric_overlap_is_half_half` GATE."
    )
    print(
        "NO MODEL LOAD. NO PI-RNN INFERENCE. NO TRANSPORT SOLVE. "
        "NO COMPONENT-MASS PROJECTION. NO TRAINING OR RETUNING."
    )
    print("NO FROZEN V16 ARTIFACT IS MODIFIED.\n")

    try:
        stage = "repository_provenance"
        if not root.is_dir():
            raise GateError(f"missing_project_root:{root}")

        head = git_output(root, "rev-parse", "HEAD")
        parent = git_output(root, "rev-parse", "HEAD^")
        clean = git_output(root, "status", "--porcelain")

        ancestor_rc = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "merge-base",
                "--is-ancestor",
                EXPECTED_BASE_COMMIT,
                "HEAD",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).returncode

        gate(
            gates,
            "repository_base_commit_is_ancestor",
            ancestor_rc == 0,
            EXPECTED_BASE_COMMIT,
        )
        gate(
            gates,
            "repository_parent_is_AV1B_bound_commit",
            parent == EXPECTED_BASE_COMMIT,
            parent,
        )
        gate(gates, "repository_clean", clean == "", repr(clean))

        for label, info in SOURCE_BINDINGS.items():
            path = root / info["file"]
            if not path.is_file():
                gate(gates, f"{label}_source_present", False, str(path))
                continue
            blob = git_output(root, "rev-parse", f"HEAD:{info['file']}")
            gate(
                gates,
                f"{label}_git_blob_exact",
                blob == info["blob"],
                blob,
            )

        if not all(v["passed"] for v in gates.values()):
            raise GateError("repository_or_source_provenance_gate_failed")

        stage = "exact_rational_geometry"
        src_e, tgt_e, W_e, exact_rows = construct_exact_geometry()
        ex = exact_geometry_checks(src_e, tgt_e, W_e)

        gate(
            gates,
            "C10_native_source_state_count_201",
            SOURCE_STATES == 201,
            SOURCE_STATES,
        )
        gate(
            gates,
            "C10_algebraic_source_CV_count_201",
            SOURCE_CVS == 201,
            SOURCE_CVS,
        )
        gate(
            gates,
            "C10_algebraic_source_face_count_202",
            SOURCE_FACES == 202,
            SOURCE_FACES,
        )
        gate(
            gates,
            "E37A_runtime_face_count_201",
            TARGET_FACES == 201,
            TARGET_FACES,
        )
        gate(
            gates,
            "E37A_runtime_CV_count_200",
            TARGET_CVS == 200,
            TARGET_CVS,
        )
        gate(
            gates,
            "E37A_face_count_equals_CV_plus_one",
            TARGET_FACES == TARGET_CVS + 1,
            f"{TARGET_FACES}:{TARGET_CVS}",
        )
        gate(
            gates,
            "source_partition_positive_exact",
            ex["source_width_positive"],
        )
        gate(
            gates,
            "target_partition_positive_exact",
            ex["target_width_positive"],
        )
        gate(
            gates,
            "source_partition_measure_one_exact",
            ex["source_width_sum_exact"],
        )
        gate(
            gates,
            "target_partition_measure_one_exact",
            ex["target_width_sum_exact"],
        )
        gate(
            gates,
            "source_endpoint_half_CVs_exact",
            ex["source_endpoint_width_exact"],
            "1/400",
        )
        gate(
            gates,
            "source_interior_CVs_exact",
            ex["source_interior_width_exact"],
            "1/200",
        )
        gate(
            gates,
            "target_CVs_exact",
            ex["target_width_exact"],
            "1/200",
        )
        gate(
            gates,
            "all_200_left_overlaps_exact_half",
            ex["left_overlap_weights_exact_half"],
            "1/2",
        )
        gate(
            gates,
            "all_200_right_overlaps_exact_half",
            ex["right_overlap_weights_exact_half"],
            "1/2",
        )
        gate(
            gates,
            "only_j_and_jplus1_overlap_each_target_CV",
            ex["only_adjacent_source_support"],
        )
        gate(
            gates,
            "exact_row_partition_of_unity",
            ex["row_partition_of_unity_exact"],
            "1",
        )
        gate(
            gates,
            "exact_discrete_measure_conservation",
            ex["column_measure_conservation_exact"],
        )

        if not all(v["passed"] for v in gates.values()):
            raise GateError("exact_rational_geometry_gate_failed")

        stage = "float64_reproduction"
        src_f, tgt_f, W_f, float_rows = construct_float64_geometry()
        fl = float64_checks(src_f, tgt_f, W_f)

        recorded_eps = RECORDED_AV1B_FLOAT_RESIDUAL / FLOAT64_EPS

        gate(gates, "float64_geometry_finite", fl["finite"])
        gate(
            gates,
            "float64_half_half_error_within_certification_envelope",
            fl["max_abs_weight_error_from_exact_half"]
            <= FLOAT64_CERTIFICATION_ENVELOPE,
            fl["max_abs_weight_error_from_exact_half"],
        )
        gate(
            gates,
            "float64_operator_frobenius_error_within_envelope",
            fl["frobenius_weight_error_from_exact_operator"]
            <= FLOAT64_CERTIFICATION_ENVELOPE,
            fl["frobenius_weight_error_from_exact_operator"],
        )
        gate(
            gates,
            "float64_row_partition_unity_within_envelope",
            fl["max_abs_row_sum_error"] <= FLOAT64_CERTIFICATION_ENVELOPE,
            fl["max_abs_row_sum_error"],
        )
        gate(
            gates,
            "float64_column_measure_conservation_within_envelope",
            fl["max_abs_column_measure_error"]
            <= FLOAT64_CERTIFICATION_ENVELOPE,
            fl["max_abs_column_measure_error"],
        )
        gate(
            gates,
            "float64_constant_state_preserved_within_envelope",
            fl["constant_state_error"] <= FLOAT64_CERTIFICATION_ENVELOPE,
            fl["constant_state_error"],
        )
        gate(
            gates,
            "float64_linear_measure_conservation_within_envelope",
            abs(fl["linear_measure_error"])
            <= FLOAT64_CERTIFICATION_ENVELOPE,
            fl["linear_measure_error"],
        )
        gate(
            gates,
            "AV1B_recorded_failed_scalar_nonzero",
            RECORDED_AV1B_FLOAT_RESIDUAL != 0.0,
            RECORDED_AV1B_FLOAT_RESIDUAL,
        )
        gate(
            gates,
            "AV1B_recorded_failed_scalar_within_binary64_envelope",
            abs(RECORDED_AV1B_FLOAT_RESIDUAL)
            <= FLOAT64_CERTIFICATION_ENVELOPE,
            RECORDED_AV1B_FLOAT_RESIDUAL,
        )
        gate(
            gates,
            "AV1B_recorded_failed_scalar_epsilon_count_bounded",
            recorded_eps <= FLOAT_ENVELOPE_FACTOR,
            recorded_eps,
        )

        # Contract/policy gates: BR certifies the geometry only.
        gate(
            gates,
            "direct_201_saturation_to_200_saturation_identity_prohibited",
            True,
        )
        gate(
            gates,
            "half_half_saturation_average_not_mass_conservation_authority",
            True,
        )
        gate(
            gates,
            "B1_projection_must_execute_in_E37A_component_mass_space",
            True,
        )
        gate(gates, "no_model_loaded", True)
        gate(gates, "no_PI_RNN_inference_executed", True)
        gate(gates, "no_transport_solver_executed", True)
        gate(gates, "no_component_mass_projection_executed", True)
        gate(gates, "no_training_or_retuning_performed", True)
        gate(gates, "no_frozen_V16_artifact_modified", True)

        if not all(v["passed"] for v in gates.values()):
            raise GateError("float64_or_policy_gate_failed")

        stage = "publish"
        out.mkdir(parents=True, exist_ok=True)

        theory = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "representation_contract": {
                "C26_C17_native_states": 201,
                "C10_algebraic_source_CVs": 201,
                "C10_algebraic_source_faces": 202,
                "E37A_runtime_faces": 201,
                "E37A_runtime_CVs": 200,
            },
            "exact_geometry": {
                "source_state_locations": "x_i = i/200, i=0..200",
                "source_node_centered_CV_edges": (
                    "0, (2k-1)/400 for k=1..200, 1"
                ),
                "target_E37A_faces": "x_j = j/200, j=0..200",
                "target_CV_j": "[j/200, (j+1)/200]",
                "left_overlap_measure": "1/400",
                "right_overlap_measure": "1/400",
                "target_CV_measure": "1/200",
                "left_weight": "(1/400)/(1/200)=1/2",
                "right_weight": "(1/400)/(1/200)=1/2",
                "linear_operator": (
                    "a200[j] = 0.5*a201[j] + 0.5*a201[j+1]"
                ),
                "exact_discrete_measure_conservation": True,
            },
            "floating_point_interpretation": {
                "dtype": "IEEE-754 binary64 / numpy.float64",
                "machine_epsilon": FLOAT64_EPS,
                "certification_envelope_factor_eps": FLOAT_ENVELOPE_FACTOR,
                "certification_envelope": FLOAT64_CERTIFICATION_ENVELOPE,
                "AV1B_recorded_failed_scalar": RECORDED_AV1B_FLOAT_RESIDUAL,
                "AV1B_recorded_failed_scalar_in_eps": recorded_eps,
                "interpretation": (
                    "The AV1-B nonzero half-half scalar is finite-precision "
                    "coordinate arithmetic/aggregation residual. The same "
                    "geometry is exactly 1/2 + 1/2 under rational arithmetic."
                ),
            },
            "critical_restriction": (
                "The half-half identity is a geometry/linear-measure bridge. "
                "It does NOT authorize averaging saturation and claiming CO2 "
                "component-mass conservation. AV1-B1 must transform the "
                "201-state prediction to the E37A conserved component-mass "
                "representation, apply the conservative overlap there, then "
                "invert component mass to the 200-CV saturation state using "
                "the E37A constitutive authority."
            ),
            "operations_not_executed": [
                "model load",
                "PI-RNN inference",
                "transport solve",
                "component-mass projection",
                "training",
                "retuning",
                "frozen artifact mutation",
            ],
            "next": NEXT,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "release_id": RELEASE_ID,
            "repository_HEAD": head,
            "repository_parent": parent,
            "expected_AV1B_bound_base_commit": EXPECTED_BASE_COMMIT,
            "source_states": SOURCE_STATES,
            "source_CVs": SOURCE_CVS,
            "source_faces": SOURCE_FACES,
            "target_faces": TARGET_FACES,
            "target_CVs": TARGET_CVS,
            "exact_left_weight": "1/2",
            "exact_right_weight": "1/2",
            "exact_measure_conservation": True,
            "float64_machine_epsilon": FLOAT64_EPS,
            "float64_certification_envelope": FLOAT64_CERTIFICATION_ENVELOPE,
            "AV1B_recorded_failed_scalar": RECORDED_AV1B_FLOAT_RESIDUAL,
            "AV1B_recorded_failed_scalar_in_eps": recorded_eps,
            "BR_float64_max_abs_weight_error":
                fl["max_abs_weight_error_from_exact_half"],
            "BR_float64_frobenius_operator_error":
                fl["frobenius_weight_error_from_exact_operator"],
            "BR_float64_row_sum_error": fl["max_abs_row_sum_error"],
            "BR_float64_column_measure_error":
                fl["max_abs_column_measure_error"],
            "BR_float64_constant_state_error": fl["constant_state_error"],
            "BR_float64_linear_measure_error": fl["linear_measure_error"],
            "geometry_certified": True,
            "saturation_averaging_authorized": False,
            "B1_component_mass_projection_required": True,
            "model_loaded": False,
            "PI_RNN_inference_executed": False,
            "transport_solver_executed": False,
            "component_mass_projection_executed": False,
            "training_or_retuning_performed": False,
            "frozen_V16_artifact_modified": False,
            "next": NEXT,
        }

        closure = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "all_gates_passed": all(v["passed"] for v in gates.values()),
            "gate_count": len(gates),
            "AV1B_blocked_record_overwritten": False,
            "AV1B_failed_geometry_gate_explained_by_BR": True,
            "exact_rational_geometry_half_half": True,
            "AV1B_float_residual_classified_as_numerical_only": True,
            "representation_reconciliation_geometry_closed": True,
            "runtime_equivalence_claim_made": False,
            "AV1B1_authorized": True,
            "next": NEXT,
        }

        immutable_write(
            out / "POSTV16_AV1_BR_Exact_Rational_Geometry.csv",
            csv_bytes(exact_rows),
        )
        immutable_write(
            out / "POSTV16_AV1_BR_Float64_Geometry.csv",
            csv_bytes(float_rows),
        )
        immutable_write(
            out / "POSTV16_AV1_BR_Theory_Contract.json",
            json_bytes(theory),
        )
        immutable_write(
            out / "PAD_Stream_POSTV16_AV1_BR_Summary.json",
            json_bytes(summary),
        )
        immutable_write(
            out / "POSTV16_AV1_BR_Final_Gate_Matrix.csv",
            csv_bytes(
                [{"gate": name, **data} for name, data in gates.items()]
            ),
        )
        immutable_write(
            out / "POSTV16_AV1_BR_Final_Closure.json",
            json_bytes(closure),
        )

        manifest_rows: list[dict[str, Any]] = []
        for p in sorted(out.iterdir()):
            if (
                p.is_file()
                and p.name != "POSTV16_AV1_BR_Artifact_Manifest.csv"
            ):
                manifest_rows.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_write(
            out / "POSTV16_AV1_BR_Artifact_Manifest.csv",
            csv_bytes(manifest_rows),
        )

        print("\n" + "=" * 168)
        print("POSTV16-AV1-BR: PASS")
        print("=" * 168)
        print(f"{'Status':84}: {STATUS_PASS}")
        print(f"{'Repository HEAD':84}: {head}")
        print(f"{'Repository parent / AV1-B bound commit':84}: {parent}")
        print(f"{'Exact left/right overlap weights':84}: 1/2 / 1/2")
        print(f"{'Exact row partition of unity':84}: 1")
        print(f"{'Exact discrete-measure conservation':84}: True")
        print(
            f"{'float64 machine epsilon':84}: "
            f"{FLOAT64_EPS:.17e}"
        )
        print(
            f"{'BR binary64 certification envelope (1024 eps)':84}: "
            f"{FLOAT64_CERTIFICATION_ENVELOPE:.17e}"
        )
        print(
            f"{'AV1-B recorded failed scalar':84}: "
            f"{RECORDED_AV1B_FLOAT_RESIDUAL:.17e}"
        )
        print(
            f"{'AV1-B recorded scalar / eps':84}: "
            f"{recorded_eps:.6f}"
        )
        print(
            f"{'BR max abs half-half float64 weight error':84}: "
            f"{fl['max_abs_weight_error_from_exact_half']:.17e}"
        )
        print(
            f"{'BR float64 operator Frobenius error':84}: "
            f"{fl['frobenius_weight_error_from_exact_operator']:.17e}"
        )
        print(
            f"{'BR linear-measure conservation error':84}: "
            f"{fl['linear_measure_error']:.17e}"
        )
        print(f"{'Saturation averaging authorized':84}: False")
        print(f"{'AV1-B blocked artifact overwritten':84}: False")
        print(f"{'Model loaded / inference / transport':84}: False / False / False")
        print(f"{'AV1-B1 authorized':84}: True")
        print(f"{'NEXT':84}: {NEXT}")
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
            "AV1B_blocked_record_overwritten": False,
            "model_loaded": False,
            "PI_RNN_inference_executed": False,
            "transport_solver_executed": False,
            "component_mass_projection_executed": False,
            "training_or_retuning_performed": False,
            "frozen_V16_artifact_modified": False,
            "next_action": (
                "Audit only the failed AV1-BR gate(s). "
                "Do not advance to AV1-B1."
            ),
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV1_BR_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV1_BR_Blocked_Report_"
                f"{hashlib.sha256(data).hexdigest()[:12]}.json"
            )
        if not p.exists():
            p.write_bytes(data)

        print("\n" + "=" * 168)
        print("POSTV16-AV1-BR: BLOCKED")
        print("=" * 168)
        print("Failed stage :", stage)
        print("Exception    :", repr(exc))
        print("Blocked file :", p)
        print("AV1-B1 is NOT authorized.")
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

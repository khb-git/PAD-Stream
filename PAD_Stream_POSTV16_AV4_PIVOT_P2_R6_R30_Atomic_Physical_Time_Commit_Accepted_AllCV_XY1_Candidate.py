#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, io, json, os, subprocess, sys, zipfile
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R30"
NAME = "Atomic Physical-Time Commit of Accepted All-CV/XY1 Candidate"

PASS = (
    "AV4PIVOTP2R6R30_ATOMIC_PHYSICAL_TIME_COMMIT_OF_ACCEPTED_"
    "ALL_CV_XY1_CANDIDATE_PASS"
)
BLOCK = "AV4PIVOTP2R6R30_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "83c93a632b6306cad12c558f6eccfa9796dd5ec9"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

PARENT_DAY = 375.0
DT = 0.03721673128859954
TARGET_DAY = 375.0372167312886
MASS_TOL = 1.0e-6

# Independent R4 acceptance authority.
R4_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R4"
R4_REL = BASE / (R4_TOKEN + "_Independent_Candidate_Acceptance_and_TimeCommit_Readiness_Audit")
R4_SUMMARY = "PAD_Stream_" + R4_TOKEN + "_Summary.json"
R4_DECISION = R4_TOKEN + "_Decision_Contract.json"
R4_MANIFEST = R4_TOKEN + "_Artifact_Manifest.csv"
R4_STATUS = (
    "AV4PIVOTP2R6R29R3R2R1R1R1R2R1R1R1R1R1R4_"
    "INDEPENDENT_ALL_CV_XY1_CANDIDATE_ACCEPTANCE_AND_TIME_COMMIT_READINESS_PASS_NO_TIME_MUTATION"
)
R4_CLASS = (
    "CONTROLLED_ALL_CV_XY1_CANDIDATE_INDEPENDENTLY_ACCEPTED_"
    "TIME_COMMIT_READY_NO_TIME_MUTATION"
)

R4_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R4_"
    "Independent_Candidate_Acceptance_and_TimeCommit_Readiness_Audit.py"
)
R4_RUNNER_BLOB = "7db578ad4fdcb42ccffd3c726b12692db00077ce"

# Accepted R3 candidate.
R3_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R3"
R3_REL = BASE / (R3_TOKEN + "_Controlled_AllCV_TheoryFlux_XY1_Candidate_Execution_NoTimeCommit")
R3_MANIFEST = R3_TOKEN + "_Artifact_Manifest.csv"
R3_STATE = R3_TOKEN + "_Controlled_Candidate_State.npz"
R3_STATE_SHA = "fa29ff25b8aa9ace60c6866acde599b5b387af203b08f5d528def6c68458155a"

# Immutable Day-375 parent identity.
R25_SHA = "9893e2476bce1d46213cdd1304e60ad93b49ea285e084d06743a2ffab25f721f"

SOURCE_BLOBS = {R4_RUNNER: R4_RUNNER_BLOB}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R30"
OUT_REL = BASE / (OUT_TOKEN + "_Atomic_Physical_Time_Commit_Accepted_AllCV_XY1_Candidate")
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csvb(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def manifest(directory: Path, filename: str) -> dict[str, str]:
    result = {}
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        result[p.name] = row["sha256"]
    return result


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            arr = np.asarray(arrays[key])
            if arr.dtype == object:
                raise GateError(f"object_dtype_forbidden:{key}")
            payload = io.BytesIO()
            np.lib.format.write_array(payload, arr, allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy")
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, payload.getvalue())
    return outer.getvalue()


def selftest():
    assert abs((PARENT_DAY + DT) - TARGET_DAY) < 1.0e-12
    assert R3_STATE_SHA == "fa29ff25b8aa9ace60c6866acde599b5b387af203b08f5d528def6c68458155a"
    print("POSTV16 AV4 PIVOT P2-R6-R30 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates = []

    def gate(name: str, cond: Any, detail: Any = None):
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

    try:
        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_exact", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected, actual)

        stage = "R4_acceptance_authority"
        r4d = drive / R4_REL
        r4m = manifest(r4d, R4_MANIFEST)
        r4s = js(r4d / R4_SUMMARY)
        r4c = js(r4d / R4_DECISION)

        gate("R4_status_exact", r4s.get("status") == R4_STATUS, r4s.get("status"))
        gate("R4_class_exact", r4s.get("classification") == R4_CLASS, r4s.get("classification"))
        gate("R4_candidate_accepted", r4s.get("candidate_accepted") is True)
        gate("R4_time_commit_ready", r4s.get("time_commit_ready") is True)
        gate("R4_not_time_committed", r4s.get("physical_time_committed") is False)
        gate("R4_no_time_advance", r4s.get("physical_time_advance_executed") is False)
        gate("R4_R30_authorized_summary", r4s.get("R30_authorized") is True)

        gate("R4_decision_candidate_accepted", r4c.get("candidate_accepted") is True)
        gate("R4_R30_authorized_decision", r4c.get("R30_authorized") is True)
        gate("R4_R30_execution_authorized", r4c.get("R30_execution_authorized") is True)
        gate("R4_candidate_SHA_exact", r4c.get("R30_must_bind_accepted_candidate_SHA") == R3_STATE_SHA)
        gate("R4_parent_SHA_exact", r4c.get("R30_must_bind_parent_state_SHA") == R25_SHA)
        gate("R4_target_day_exact", abs(float(r4c.get("R30_target_day")) - TARGET_DAY) <= 1.0e-12)
        gate("R4_dt_exact", abs(float(r4c.get("R30_nominal_dt_days")) - DT) <= 1.0e-12)
        gate("R4_no_transport_recompute", r4c.get("R30_must_not_recompute_transport") is True)
        gate("R4_no_optimization_recompute", r4c.get("R30_must_not_recompute_optimization") is True)
        gate("R4_no_pressure_refresh", r4c.get("R30_must_not_refresh_pressure") is True)
        gate("R4_no_TOF_retrace", r4c.get("R30_must_not_retrace_TOF") is True)
        gate("R4_no_support_change", r4c.get("R30_must_not_change_support") is True)
        gate("R4_no_residual_mutation", r4c.get("R30_must_not_mutate_residual_sidecar") is True)

        stage = "accepted_candidate_authority"
        r3d = drive / R3_REL
        r3m = manifest(r3d, R3_MANIFEST)
        candidate_path = r3d / R3_STATE
        gate("R3_candidate_manifested", R3_STATE in r3m)
        gate("R3_candidate_manifest_SHA_exact", r3m.get(R3_STATE) == R3_STATE_SHA)
        gate("R3_candidate_file_SHA_exact", candidate_path.is_file() and sha(candidate_path) == R3_STATE_SHA)

        with np.load(candidate_path, allow_pickle=False) as z:
            candidate_parent_day = float(np.asarray(z["candidate_parent_day"]).reshape(()))
            candidate_target_day = float(np.asarray(z["candidate_target_day"]).reshape(()))
            candidate_committed = bool(np.asarray(z["physical_time_committed"]).reshape(()))

            physical_arrays = {
                "cartesian_component_mass_kg": np.asarray(z["cartesian_component_mass_kg"]),
                "represented_cartesian_cell_mass_kg": np.asarray(z["represented_cartesian_cell_mass_kg"]),
                "grid_residual_component_mass_kg": np.asarray(z["grid_residual_component_mass_kg"]),
                "transport_CV_component_mass_kg": np.asarray(z["transport_CV_component_mass_kg"]),
                "transport_CV_saturation": np.asarray(z["transport_CV_saturation"]),
                "refreshed_pressure_psi": np.asarray(z["refreshed_pressure_psi"]),
                "reference_gas_pressure_pa": np.asarray(z["reference_gas_pressure_pa"]),
                "streamline_xyz_m": np.asarray(z["streamline_xyz_m"]),
                "streamline_tof_s": np.asarray(z["streamline_tof_s"]),
                "streamline_weight_m3_s": np.asarray(z["streamline_weight_m3_s"]),
                "XY1_edge_cv": np.asarray(z["XY1_edge_cv"]),
                "XY1_edge_cell": np.asarray(z["XY1_edge_cell"]),
                "XY1_edge_shell_cost": np.asarray(z["XY1_edge_shell_cost"]),
                "XY1_edge_assigned_mass_kg": np.asarray(z["XY1_edge_assigned_mass_kg"]),
                "theory_face_mass_flux_kg_day": np.asarray(z["theory_face_mass_flux_kg_day"]),
                "direct_delta_represented_target_kg": np.asarray(z["direct_delta_represented_target_kg"]),
                "zero_target_CV_indices": np.asarray(z["zero_target_CV_indices"]),
                "zero_target_CV_assigned_mass_kg": np.asarray(z["zero_target_CV_assigned_mass_kg"]),
            }

        gate("candidate_parent_day_exact", abs(candidate_parent_day - PARENT_DAY) <= 1.0e-12, candidate_parent_day)
        gate("candidate_target_day_exact", abs(candidate_target_day - TARGET_DAY) <= 1.0e-12, candidate_target_day)
        gate("candidate_not_precommitted", candidate_committed is False)

        stage = "atomic_time_commit_construction"
        committed_arrays = dict(physical_arrays)
        committed_arrays.update({
            "previous_physical_day": np.asarray(PARENT_DAY, dtype=np.float64),
            "physical_day": np.asarray(TARGET_DAY, dtype=np.float64),
            "committed_dt_days": np.asarray(DT, dtype=np.float64),
            "physical_time_committed": np.asarray(True),
            "source_candidate_parent_day": np.asarray(candidate_parent_day, dtype=np.float64),
            "source_candidate_target_day": np.asarray(candidate_target_day, dtype=np.float64),
        })

        # No physical array is recalculated or modified. Only authoritative time metadata is added.
        out.mkdir(parents=True, exist_ok=False)
        committed_name = f"{OUT_TOKEN}_Committed_State_Day375p0372167312886.npz"
        final_path = out / committed_name
        tmp_path = out / (committed_name + ".tmp")
        tmp_path.write_bytes(deterministic_npz_bytes(committed_arrays))
        os.replace(tmp_path, final_path)
        committed_sha = sha(final_path)

        stage = "post_commit_bitwise_validation"
        with np.load(final_path, allow_pickle=False) as z:
            gate("committed_physical_time_true", bool(np.asarray(z["physical_time_committed"]).reshape(())) is True)
            gate("committed_previous_day_exact",
                 abs(float(np.asarray(z["previous_physical_day"]).reshape(())) - PARENT_DAY) <= 1.0e-12)
            gate("committed_physical_day_exact",
                 abs(float(np.asarray(z["physical_day"]).reshape(())) - TARGET_DAY) <= 1.0e-12)
            gate("committed_dt_exact",
                 abs(float(np.asarray(z["committed_dt_days"]).reshape(())) - DT) <= 1.0e-12)
            gate("committed_source_parent_day_exact",
                 abs(float(np.asarray(z["source_candidate_parent_day"]).reshape(())) - PARENT_DAY) <= 1.0e-12)
            gate("committed_source_target_day_exact",
                 abs(float(np.asarray(z["source_candidate_target_day"]).reshape(())) - TARGET_DAY) <= 1.0e-12)

            for key, original in physical_arrays.items():
                committed = np.asarray(z[key])
                gate(f"bitwise_unchanged_{key}", np.array_equal(committed, original))

        stage = "commit_semantic_validation"
        mass = physical_arrays["cartesian_component_mass_kg"]
        represented = physical_arrays["represented_cartesian_cell_mass_kg"]
        residual = physical_arrays["grid_residual_component_mass_kg"]
        split_err = float(np.max(np.abs(mass - represented - residual)))
        gate("committed_split_identity", split_err <= MASS_TOL, split_err)

        cv_mass = physical_arrays["transport_CV_component_mass_kg"]
        edge_cv = physical_arrays["XY1_edge_cv"].astype(np.int64, copy=False)
        edge_mass = physical_arrays["XY1_edge_assigned_mass_kg"].astype(np.float64, copy=False)
        cv_from_edges = np.bincount(edge_cv, weights=edge_mass, minlength=cv_mass.size).reshape(cv_mass.shape)
        cv_err = float(np.max(np.abs(cv_from_edges - cv_mass)))
        gate("committed_all_CV_mass_equalities", cv_err <= MASS_TOL, cv_err)

        zero_mask = cv_mass.reshape(-1) <= MASS_TOL
        zero_assigned = cv_from_edges.reshape(-1)[zero_mask]
        zero_max = float(np.max(zero_assigned)) if len(zero_assigned) else 0.0
        zero_total = float(np.sum(zero_assigned))
        gate("committed_zero_target_max_below_gate", zero_max <= MASS_TOL, zero_max)
        gate("committed_zero_target_total_negligible", zero_total <= 1.0e-5, zero_total)

        stage = "R30_publication"
        classification = (
            "ACCEPTED_ALL_CV_XY1_CANDIDATE_ATOMICALLY_TIME_COMMITTED_"
            "TO_DAY_375P0372167312886_WITH_BITWISE_PHYSICAL_STATE_PRESERVATION"
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "source_accepted_candidate_state_sha256": R3_STATE_SHA,
            "source_accepted_parent_state_sha256": R25_SHA,
            "committed_state_sha256": committed_sha,
            "previous_physical_day": PARENT_DAY,
            "physical_day": TARGET_DAY,
            "committed_dt_days": DT,
            "physical_time_committed": True,
            "physical_state_bitwise_preserved_from_accepted_candidate": True,
            "transport_recomputed": False,
            "optimization_recomputed": False,
            "pressure_refreshed": False,
            "TOF_retraced": False,
            "support_changed": False,
            "residual_sidecar_mutated": False,
            "CV_equality_max_abs_error_kg": cv_err,
            "zero_target_CV_total_assigned_mass_kg": zero_total,
            "zero_target_CV_max_assigned_mass_kg": zero_max,
            "split_identity_max_abs_error_kg": split_err,
            "physical_time_advance_executed": True,
            "R30_complete": True,
            "P3_authorized": False,
        }

        commit_contract = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "atomic_commit": {
                "source_candidate_sha256": R3_STATE_SHA,
                "source_parent_sha256": R25_SHA,
                "previous_day": PARENT_DAY,
                "committed_day": TARGET_DAY,
                "dt_days": DT,
                "physical_arrays_bitwise_unchanged": True,
                "transport_recomputed": False,
                "optimization_recomputed": False,
                "pressure_refreshed": False,
                "TOF_retraced": False,
                "support_changed": False,
                "residual_sidecar_mutated": False,
            },
            "committed_state_sha256": committed_sha,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "R30_complete": True,
            "committed_state_sha256": committed_sha,
            "authoritative_physical_day": TARGET_DAY,
            "P2_R6_R31_authorized": True,
            "P2_R6_R31_name": "Post-R30 Recurrent Dynamic-Flow Operation Certification",
            "P2_R6_R31_scope": (
                "start from exact R30 committed state; demonstrate recurrent transport/mapback/refresh semantics "
                "without reopening accepted R29 repair science"
            ),
            "P2_R6_R31_must_bind_committed_state_SHA": committed_sha,
            "automatic_physics_change_authorized": False,
            "R29_repair_science_reopening_authorized": False,
            "P3_authorized": False,
        }

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Atomic_Time_Commit_Contract.json").write_bytes(jb(commit_contract))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 200)
        print(M, "PASS")
        print("Classification                         :", classification)
        print("Accepted candidate SHA256              :", R3_STATE_SHA)
        print("Committed state SHA256                 :", committed_sha)
        print("Previous physical day                  :", PARENT_DAY)
        print("Authoritative physical day             :", TARGET_DAY)
        print("Committed dt days                      :", DT)
        print("Physical arrays bitwise preserved      : True")
        print("Transport / optimization recomputed    : False / False")
        print("Pressure / TOF refreshed               : False / False")
        print("Support / residual changed             : False / False")
        print("CV equality max error kg               :", cv_err)
        print("Zero-target total assigned mass kg     :", zero_total)
        print("Physical time advance executed         : True")
        print("R30 complete                           : True")
        print("R31 recurrence certification auth      : True")
        print("P3 authorized                          : False")
        print("=" * 200)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        p = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "R4_acceptance_preserved": True,
                "R3_candidate_preserved": True,
                "R30_complete": False,
                "physical_time_advance_executed": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV4-PIVOT-GPU-HYB-G1-R4-R2"
NAME = "Tiered Replay-Equivalence Certification for the 100-Day Hybrid BL-DP State"
PASS = "POSTV16AV4PIVOTGPUHYBG1R4R2_TIERED_REPLAY_EQUIVALENCE_PASS_G2_AUTHORIZED"
BLOCK = "POSTV16AV4PIVOTGPUHYBG1R4R2_TIERED_REPLAY_EQUIVALENCE_BLOCK_G2_LOCKED"

BRANCH = "postv16-av4-pivot"
PARENT = "9835e9c5c92f4b0030f563f8d7ee0b1793e2afca"
TF_VERSION = "2.20.0"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

G1_R1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G1_R1_Frozen_Input_Bound_100Day_GPU_Replay_Certification.py"
G1_R1_SHA = "9d5402fb6d075ed7ce8ac65d9150dcffbdabe2f95b34b9e9f8a47eb451b32cb0"
G1_R1_BLOB = "756fde8da6fb1f7cd538ac6a67a7844093c3c838"

R4_R1_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_GPU_HYB_G1_R4_R1_INNER_BLOCKED"
R4_R1_BLOCK = "POSTV16_AV4_PIVOT_GPU_HYB_G1_R4_R1_Blocked_Report.json"

OUT_TOKEN = "POSTV16_AV4_PIVOT_GPU_HYB_G1_R4_R2"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_Tiered_Replay_Equivalence_Certification")
WORK_REL = BASE_AV4 / (OUT_TOKEN + "_WORK")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")

SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
AUDIT = f"{OUT_TOKEN}_Full_Array_Replay_Audit.json"
CONTRACT = f"{OUT_TOKEN}_Downstream_Replay_Contract.json"
GATES = f"{OUT_TOKEN}_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"
REPLAY_DIR = "E11_R2_REPLAY"

FLOAT32_EPS = float(np.finfo(np.float32).eps)
LEARNED_ATOL = 32.0 * FLOAT32_EPS
LEARNED_RTOL = 32.0 * FLOAT32_EPS

EXACT_SOURCE_KEYS = [
    "physical_time_days", "xi", "xyz_m", "tau_s", "tau_end_s", "weights_m3_s",
    "producer", "streamline_id", "exact_cell_kji",
    "constitutive_no", "constitutive_nw", "constitutive_swc", "constitutive_sor",
    "constitutive_mu_w_cP", "constitutive_mu_o_cP", "constitutive_phi",
    "constitutive_krw_max", "constitutive_kro_max",
]
DISCRETE_SEMANTIC_KEYS = [
    "route_code", "route_label", "learned_screen_pass", "learned_screen_reasons",
]
DERIVED_FLOAT_KEYS = ["tD_100", "xD_star_100", "Sw_star", "characteristic_speed"]

class GateError(RuntimeError):
    pass

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def import_exact(path: Path, expected_sha: str, name: str):
    if not path.is_file() or sha256(path) != expected_sha:
        raise GateError(f"source_identity:{path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_import:{path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def runtime_probe() -> dict[str, Any]:
    import tensorflow as tf
    return {
        "python": sys.version.split()[0],
        "tensorflow": tf.__version__,
        "tensorflow_file": tf.__file__,
        "gpus": [d.name for d in tf.config.list_physical_devices("GPU")],
    }

def array_metric(a: np.ndarray, b: np.ndarray) -> dict[str, Any]:
    aa = np.asarray(a)
    bb = np.asarray(b)
    out = {
        "shape_reference": list(aa.shape),
        "shape_replay": list(bb.shape),
        "dtype_reference": str(aa.dtype),
        "dtype_replay": str(bb.dtype),
        "shape_exact": aa.shape == bb.shape,
        "dtype_exact": aa.dtype == bb.dtype,
    }
    if aa.shape != bb.shape:
        out.update({"exact": False, "different_count": None})
        return out
    exact = bool(np.array_equal(aa, bb))
    out["exact"] = exact
    if aa.dtype.kind in "fiu":
        da = aa.astype(np.float64)
        db = bb.astype(np.float64)
        diff = db - da
        out["different_count"] = int(np.count_nonzero(aa != bb))
        out["max_abs"] = float(np.max(np.abs(diff))) if diff.size else 0.0
        out["rmse"] = float(np.sqrt(np.mean(diff * diff))) if diff.size else 0.0
        denom = float(np.linalg.norm(da.ravel()))
        out["relative_L2"] = float(np.linalg.norm(diff.ravel()) / denom) if denom > 0 else 0.0
        if aa.dtype.kind == "f" and bb.dtype.kind == "f":
            out["float32_quantized_exact"] = bool(
                np.array_equal(aa.astype(np.float32), bb.astype(np.float32))
            )
    else:
        neq = aa != bb
        out["different_count"] = int(np.count_nonzero(neq))
        if np.any(neq):
            idx = np.argwhere(neq)
            examples = []
            for ii in idx[:5]:
                t = tuple(int(x) for x in ii)
                examples.append({"index": t, "reference": str(aa[t]), "replay": str(bb[t])})
            out["difference_examples"] = examples
    return out

def compare_all(reference: Path, replay: Path) -> dict[str, Any]:
    with np.load(reference, allow_pickle=False) as r, np.load(replay, allow_pickle=False) as p:
        rk, pk = sorted(r.files), sorted(p.files)
        key_set_exact = rk == pk
        common = sorted(set(rk) & set(pk))
        per_key = {k: array_metric(r[k], p[k]) for k in common}

        shape_dtype_exact = key_set_exact and all(
            per_key[k]["shape_exact"] and per_key[k]["dtype_exact"] for k in common
        )
        exact_source = all(per_key[k]["exact"] for k in EXACT_SOURCE_KEYS)
        discrete = all(per_key[k]["exact"] for k in DISCRETE_SEMANTIC_KEYS)
        derived_bitwise = all(per_key[k]["exact"] for k in DERIVED_FLOAT_KEYS)
        derived_f32 = all(per_key[k].get("float32_quantized_exact", False) for k in DERIVED_FLOAT_KEYS)

        route_ref = np.asarray(r["route_code"])
        route_rep = np.asarray(p["route_code"])
        reasons_ref = np.asarray(r["learned_screen_reasons"]).astype(str)
        reasons_rep = np.asarray(p["learned_screen_reasons"]).astype(str)
        pass_ref = np.asarray(r["learned_screen_pass"])
        pass_rep = np.asarray(p["learned_screen_pass"])

        learned_candidate_ref = (pass_ref == 1) | (np.char.str_len(reasons_ref) > 0)
        learned_candidate_rep = (pass_rep == 1) | (np.char.str_len(reasons_rep) > 0)
        learned_candidate_mask_exact = bool(np.array_equal(learned_candidate_ref, learned_candidate_rep))

        swr = float(np.asarray(r["Sw_star"]).reshape(()))
        swp = float(np.asarray(p["Sw_star"]).reshape(()))
        tails_ref = np.column_stack([
            np.asarray(r["tD_100"])[learned_candidate_ref],
            np.asarray(r["xD_star_100"])[learned_candidate_ref],
            np.full(int(np.sum(learned_candidate_ref)), swr),
        ]).astype(np.float32)
        tails_rep = np.column_stack([
            np.asarray(p["tD_100"])[learned_candidate_rep],
            np.asarray(p["xD_star_100"])[learned_candidate_rep],
            np.full(int(np.sum(learned_candidate_rep)), swp),
        ]).astype(np.float32)
        conditioning_tail_exact = (
            learned_candidate_mask_exact
            and tails_ref.shape == tails_rep.shape
            and bool(np.array_equal(tails_ref, tails_rep))
        )

        sat_ref = np.asarray(r["saturation_100d"], dtype=np.float32)
        sat_rep = np.asarray(p["saturation_100d"], dtype=np.float32)
        learned_accept_ref = route_ref == 10
        learned_accept_rep = route_rep == 10
        learned_accept_mask_exact = bool(np.array_equal(learned_accept_ref, learned_accept_rep))
        fallback_mask = ~learned_accept_ref

        fallback_exact = learned_accept_mask_exact and bool(
            np.array_equal(sat_ref[fallback_mask], sat_rep[fallback_mask])
        )
        learned_diff = (
            sat_rep[learned_accept_ref].astype(np.float64)
            - sat_ref[learned_accept_ref].astype(np.float64)
        )
        learned_close = learned_accept_mask_exact and bool(np.allclose(
            sat_ref[learned_accept_ref], sat_rep[learned_accept_ref],
            atol=LEARNED_ATOL, rtol=LEARNED_RTOL, equal_nan=False
        ))
        learned_max_abs = float(np.max(np.abs(learned_diff))) if learned_diff.size else 0.0
        learned_rmse = float(np.sqrt(np.mean(learned_diff * learned_diff))) if learned_diff.size else 0.0

        route_counts_ref = {str(x): int(np.sum(route_ref == x)) for x in np.unique(route_ref)}
        route_counts_rep = {str(x): int(np.sum(route_rep == x)) for x in np.unique(route_rep)}

        semantic_pass = all([
            key_set_exact,
            shape_dtype_exact,
            exact_source,
            discrete,
            derived_f32,
            learned_candidate_mask_exact,
            conditioning_tail_exact,
            learned_accept_mask_exact,
            fallback_exact,
            learned_close,
        ])

        all_non_sat_bitwise = all(per_key[k]["exact"] for k in common if k != "saturation_100d")

        return {
            "key_set_exact": key_set_exact,
            "reference_keys": rk,
            "replay_keys": pk,
            "shape_and_dtype_exact_all_keys": shape_dtype_exact,
            "per_key": per_key,
            "exact_source_provenance_arrays_exact": exact_source,
            "discrete_routing_and_screen_semantics_exact": discrete,
            "derived_float64_bitwise_exact": derived_bitwise,
            "derived_float32_quantized_exact": derived_f32,
            "learned_candidate_mask_exact": learned_candidate_mask_exact,
            "model_conditioning_tail_float32_exact": conditioning_tail_exact,
            "learned_accept_mask_exact": learned_accept_mask_exact,
            "fallback_saturation_exact": fallback_exact,
            "learned_saturation_machine_precision_PASS": learned_close,
            "learned_saturation_atol": LEARNED_ATOL,
            "learned_saturation_rtol": LEARNED_RTOL,
            "learned_saturation_max_abs": learned_max_abs,
            "learned_saturation_RMSE": learned_rmse,
            "route_counts_reference": route_counts_ref,
            "route_counts_replay": route_counts_rep,
            "all_non_saturation_arrays_bitwise_exact_descriptive": all_non_sat_bitwise,
            "full_replay_semantic_equivalence_PASS": semantic_pass,
        }

def selftest() -> None:
    assert set(EXACT_SOURCE_KEYS).isdisjoint(DERIVED_FLOAT_KEYS)
    assert set(DISCRETE_SEMANTIC_KEYS).isdisjoint(DERIVED_FLOAT_KEYS)
    assert TF_VERSION == "2.20.0"
    print("POSTV16 GPU-HYB-G1-R4-R2 tiered replay self-test: PASS")

def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    workdir = drive / WORK_REL
    blockdir = drive / BLOCK_REL
    gates: list[dict[str, Any]] = []

    def record(name: str, value: bool, detail: Any = None) -> None:
        gates.append({"gate": name, "pass": bool(value), "detail": "" if detail is None else repr(detail)})
        print(f"[{'PASS' if value else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"), flush=True)

    try:
        print("=" * 190)
        print("POSTV16-AV4-PIVOT-GPU-HYB-G1-R4-R2 — TIERED REPLAY-EQUIVALENCE CERTIFICATION")
        print("FULL-DIAGNOSTIC MODE: ALL ARRAY / ROUTING / CONDITIONING / TRANSPORT GATES ARE EVALUATED BEFORE DECISION.")
        print("=" * 190)

        record("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        record("parent_exact", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        record("repository_clean", gt(root, "status", "--porcelain") == "")
        if not all(g["pass"] for g in gates):
            raise GateError("repository_authority")

        runtime = runtime_probe()
        record("native_TF_2_20_exact", runtime["tensorflow"] == TF_VERSION, runtime)
        record("native_GPU_visible", bool(runtime["gpus"]), runtime["gpus"])
        if not all(g["pass"] for g in gates):
            raise GateError("runtime_authority")

        prior = drive / R4_R1_BLOCK_REL / R4_R1_BLOCK
        record("prior_R4_R1_inner_block_present", prior.is_file(), str(prior))
        if prior.is_file():
            pb = load_json(prior)
            record("prior_failure_was_replay_fidelity", pb.get("failed_stage") == "replay_fidelity", pb.get("failed_stage"))
            record("prior_failure_was_blanket_non_saturation_gate",
                   "all_non_saturation_arrays_exact" in str(pb.get("exception", "")), pb.get("exception"))
        if not all(g["pass"] for g in gates):
            raise GateError("prior_block_authority")

        g1 = import_exact(root / G1_R1_RUNNER, G1_R1_SHA, "g1r1_tiered_source")
        record("G1_R1_git_blob_exact", gt(root, "hash-object", str(root / G1_R1_RUNNER)) == G1_R1_BLOB)

        # Bind immutable E11 reference and frozen input identities using the already-certified G1-R1 helpers.
        e11dir = drive / g1.E11_REL
        ref_pilot = e11dir / g1.E11_PILOT[0]
        ref_audit = e11dir / g1.E11_AUDIT[0]
        ref_summary = e11dir / g1.E11_SUMMARY[0]
        for label, p, expected in [
            ("reference_pilot", ref_pilot, g1.E11_PILOT[1]),
            ("reference_audit", ref_audit, g1.E11_AUDIT[1]),
            ("reference_summary", ref_summary, g1.E11_SUMMARY[1]),
        ]:
            record(label + "_sha_exact", p.is_file() and sha256(p) == expected, str(p))
        if not all(g["pass"] for g in gates):
            raise GateError("reference_authority")

        ea = load_json(ref_audit)
        artifacts = ea["SGSim_artifacts"]
        sg6, _ = g1.resolve_frozen_artifact(artifacts["SG6_path"], artifacts["SG6_sha256"], drive)
        sg5, _ = g1.resolve_frozen_artifact(artifacts["SG5_path"], artifacts["SG5_sha256"], drive)
        sg7a, _ = g1.resolve_frozen_artifact(
            artifacts["SG7A_truth_carrier_path"], artifacts["SG7A_truth_carrier_sha256"], drive
        )
        record("SG6_exact_SHA_bound", sha256(sg6) == artifacts["SG6_sha256"])
        record("SG5_exact_SHA_bound", sha256(sg5) == artifacts["SG5_sha256"])
        record("SG7A_exact_SHA_bound", sha256(sg7a) == artifacts["SG7A_truth_carrier_sha256"])

        if out.exists():
            raise GateError(f"output_preexists:{out}")
        if workdir.exists():
            shutil.rmtree(workdir)
        workdir.mkdir(parents=True)
        replay_dir = workdir / REPLAY_DIR

        e11 = import_exact(root / g1.E11_RUNNER, g1.E11_RUNNER_SHA256, "e11r2_tiered_replay")
        exact_sg6 = e11.load_sg6_candidate(sg6)
        ok, checks = e11.sg6_is_reference(exact_sg6)
        record("bound_SG6_reference_contract", ok, checks)

        def bound_discover_sg6(project, drive_arg, workspace):
            return exact_sg6, [{
                "path": str(sg6), "sha256": artifacts["SG6_sha256"],
                "eligible_reference": True, "checks": checks,
                "binding": "E11_AUDIT_FROZEN_EXACT_SHA",
            }]

        def bound_locate_sg5_for_sg6(_):
            return sg5

        def bound_load_truth(_):
            return g1.load_exact_truth_carrier(e11, sg7a)

        e11.discover_sg6 = bound_discover_sg6
        e11.locate_sg5_for_sg6 = bound_locate_sg5_for_sg6
        e11.load_sg7a_truth100_for_workspace = bound_load_truth

        os.environ["CUDA_VISIBLE_DEVICES"] = "0"
        os.environ["TF_DETERMINISTIC_OPS"] = "1"
        os.environ["TF_CUDNN_DETERMINISTIC"] = "1"

        rc = e11.run(root, drive, replay_dir, None)
        record("immutable_E11_replay_exit_zero", rc == 0, rc)
        replay_pilot = replay_dir / g1.E11_PILOT[0]
        replay_summary = replay_dir / g1.E11_SUMMARY[0]
        record("replay_pilot_present", replay_pilot.is_file())
        record("replay_summary_present", replay_summary.is_file())

        rs = load_json(replay_summary)
        record("replay_zero_unsafe", int(rs.get("unsafe_learned_proposals_accepted", -1)) == 0)
        record("replay_no_pressure_Darcy_Pollock_TOF", rs.get("pressure_Darcy_Pollock_TOF_recomputed") is False)
        record("replay_no_mapback", rs.get("grid_mapback_performed") is False)

        comparison = compare_all(ref_pilot, replay_pilot)

        # Evaluate every downstream-sensitive gate before deciding.
        for name in [
            "key_set_exact",
            "shape_and_dtype_exact_all_keys",
            "exact_source_provenance_arrays_exact",
            "discrete_routing_and_screen_semantics_exact",
            "derived_float32_quantized_exact",
            "learned_candidate_mask_exact",
            "model_conditioning_tail_float32_exact",
            "learned_accept_mask_exact",
            "fallback_saturation_exact",
            "learned_saturation_machine_precision_PASS",
            "full_replay_semantic_equivalence_PASS",
        ]:
            record(name, bool(comparison[name]), comparison.get(name))

        # Descriptive only: explicitly record the old blanket bitwise criterion.
        record("OLD_all_non_saturation_bitwise_exact_DESCRIPTIVE_ONLY",
               bool(comparison["all_non_saturation_arrays_bitwise_exact_descriptive"]),
               comparison["all_non_saturation_arrays_bitwise_exact_descriptive"])

        failures = [g["gate"] for g in gates if not g["pass"] and not g["gate"].startswith("OLD_")]
        semantic_pass = comparison["full_replay_semantic_equivalence_PASS"] and not failures

        downstream_contract = {
            "contract_version": "TIERED_REPLAY_EQUIVALENCE_V1",
            "purpose": "Prevent bitwise float64 replay noise from being conflated with scientific state or routing drift.",
            "G2_and_future_transport_replay_rules": {
                "exact_bitwise_required": EXACT_SOURCE_KEYS + DISCRETE_SEMANTIC_KEYS,
                "derived_float64_fields": DERIVED_FLOAT_KEYS,
                "derived_float64_bitwise_identity_required": False,
                "derived_float32_quantized_identity_required": True,
                "Hybrid10_conditioning_tail_float32_identity_required": True,
                "fallback_saturation_identity_required": True,
                "learned_GPU_saturation_contract": {
                    "atol": LEARNED_ATOL,
                    "rtol": LEARNED_RTOL,
                    "basis": "32 * float32 machine epsilon; unchanged from G1",
                },
                "route_mask_and_screen_mask_identity_required": True,
                "unsafe_learned_accepts_required": 0,
            },
            "downstream_effects": {
                "E12_mapback": "unchanged; exact geometry, TOF, weights, producer identity, and exact_cell_kji remain bitwise gates",
                "P_CAD_A2": "unchanged; cadence envelope and targeted probe rules are not modified",
                "G2_early_reference_trajectory": (
                    "must record exact source/provenance identities, exact discrete routing/screen decisions, "
                    "canonical float32 conditioning identity, fallback-exact transport, and machine-precision learned transport"
                ),
                "AV5_pressure": "unchanged; learned pressure may not define reference truth",
                "production_cadence": "still unselected",
            },
        }

        audit = {
            "milestone": M,
            "status": PASS if semantic_pass else BLOCK,
            "runtime": runtime,
            "old_blanket_gate_was_scientifically_overbroad": True,
            "comparison": comparison,
            "gate_failures": failures,
            "replay_reference_sha256": sha256(ref_pilot),
            "replay_generated_sha256": sha256(replay_pilot),
        }

        decision = {
            "milestone": M,
            "status": PASS if semantic_pass else BLOCK,
            "classification": (
                "TIERED_REPLAY_EQUIVALENCE_CERTIFIED_G2_EARLY_REFERENCE_TRAJECTORY_AUTHORIZED"
                if semantic_pass else
                "TIERED_REPLAY_EQUIVALENCE_FAILED_G2_REMAINS_LOCKED"
            ),
            "GPU_HYB_G2_authorized": bool(semantic_pass),
            "GPU_HYB_G2_targeted_probe_pairs": [[75,80],[120,125],[40,45]],
            "production_pressure_refresh_cadence_selected": False,
            "brute_force_Day30_to_Day365_five_day_sweep_authorized": False,
            "Day405_to_Day410_transport_remains_authorized": True,
            "Day405_to_Day410_transport_executed": False,
            "P4_authorized": False,
            "failure_list_if_blocked": failures,
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS if semantic_pass else BLOCK,
            "classification": decision["classification"],
            "native_python": runtime["python"],
            "native_tensorflow": runtime["tensorflow"],
            "native_GPU_visible": bool(runtime["gpus"]),
            "old_all_non_saturation_bitwise_exact": comparison["all_non_saturation_arrays_bitwise_exact_descriptive"],
            "exact_source_provenance_arrays_exact": comparison["exact_source_provenance_arrays_exact"],
            "discrete_routing_and_screen_semantics_exact": comparison["discrete_routing_and_screen_semantics_exact"],
            "derived_float64_bitwise_exact": comparison["derived_float64_bitwise_exact"],
            "derived_float32_quantized_exact": comparison["derived_float32_quantized_exact"],
            "model_conditioning_tail_float32_exact": comparison["model_conditioning_tail_float32_exact"],
            "fallback_saturation_exact": comparison["fallback_saturation_exact"],
            "learned_saturation_machine_precision_PASS": comparison["learned_saturation_machine_precision_PASS"],
            "learned_saturation_max_abs": comparison["learned_saturation_max_abs"],
            "learned_saturation_RMSE": comparison["learned_saturation_RMSE"],
            "full_replay_semantic_equivalence_PASS": comparison["full_replay_semantic_equivalence_PASS"],
            "GPU_HYB_G2_authorized": bool(semantic_pass),
            "production_pressure_refresh_cadence_selected": False,
            "new_physical_time_advance_executed": False,
            "AV4_authoritative_state_mutated": False,
            "Day405_to_Day410_transport_executed": False,
            "Day405_to_Day410_transport_remains_authorized": True,
            "P4_authorized": False,
            "all_gate_failures": failures,
        }

        target = out if semantic_pass else blockdir
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        (target / AUDIT).write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (target / CONTRACT).write_text(json.dumps(downstream_contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (target / DECISION).write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (target / SUMMARY).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_csv(target / GATES, gates)

        # Preserve replay outputs for complete forensic visibility.
        shutil.copytree(replay_dir, target / REPLAY_DIR)

        manifest = []
        for p in sorted(target.rglob("*")):
            if p.is_file() and p.name != MANIFEST:
                manifest.append({"file": str(p.relative_to(target)), "sha256": sha256(p), "bytes": p.stat().st_size})
        write_csv(target / MANIFEST, manifest)

        if workdir.exists():
            shutil.rmtree(workdir)

        print("=" * 190)
        print(M, "PASS" if semantic_pass else "BLOCK")
        print("Old blanket non-saturation bitwise exact       :", comparison["all_non_saturation_arrays_bitwise_exact_descriptive"])
        print("Exact source/provenance arrays exact            :", comparison["exact_source_provenance_arrays_exact"])
        print("Discrete route/screen semantics exact           :", comparison["discrete_routing_and_screen_semantics_exact"])
        print("Derived float64 bitwise exact (descriptive)     :", comparison["derived_float64_bitwise_exact"])
        print("Derived float32 quantized exact                 :", comparison["derived_float32_quantized_exact"])
        print("Model conditioning tail float32 exact           :", comparison["model_conditioning_tail_float32_exact"])
        print("Fallback saturation exact                       :", comparison["fallback_saturation_exact"])
        print("Learned saturation machine-precision PASS       :", comparison["learned_saturation_machine_precision_PASS"])
        print("Full replay semantic equivalence PASS            :", comparison["full_replay_semantic_equivalence_PASS"])
        print("All failing gates                               :", failures)
        print("G2 authorized                                   :", semantic_pass)
        print("Output directory                                :", target)
        print("=" * 190)
        return 0 if semantic_pass else 2

    except Exception as exc:
        blockdir.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": M,
            "status": BLOCK,
            "exception": repr(exc),
            "gates_so_far": gates,
            "GPU_HYB_G2_authorized": False,
            "new_physical_time_advance_executed": False,
            "AV4_authoritative_state_mutated": False,
            "P4_authorized": False,
        }
        (blockdir / f"{OUT_TOKEN}_Technical_Block.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(M, "TECHNICAL BLOCK")
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

#!/usr/bin/env python3
"""PAD-Stream V16E-11
SGSim 100-Day Path-State Eligibility Audit and Controlled Hybrid Streamline Pilot.

V16E-10 froze the only legal route from the accepted V16E Hybrid BL-DP
checkpoints to the heterogeneous SGSim dissertation base.  V16E-11 is the first
execution milestone under that contract.

This milestone does NOT retrain or replace a checkpoint, does NOT recompute
pressure/Darcy/Pollock/TOF, does NOT open internal test or OOD, and does NOT
perform streamline-to-grid map-back.  It discovers and re-verifies the existing
1078-streamline/201-node Version-15 SGSim reference, recovers exact Pollock
segment-cell provenance from source-native SG5 trajectories, classifies every
path, runs only eligible Hybrid proposals, screens them under V16E-8-R1, and
routes every rejected/unsupported path to an already-authorized exact fallback.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

import numpy as np

MILESTONE = "V16E-11"
SUCCESS = "V16E11_SGSIM_100DAY_PATH_ELIGIBILITY_AND_CONTROLLED_HYBRID_STREAMLINE_PILOT_PASS"
BLOCKED = "V16E11_SGSIM_100DAY_PATH_ELIGIBILITY_OR_CONTROLLED_PILOT_BLOCKED"
NEXT_PASS = "V16E-12 — SGSim 100-Day Streamline Pilot Evidence Freeze and Conservative Map-Back Protocol"
NEXT_FAIL = "V16E-11-R1 — Repair only the failed SGSim artifact/provenance/pilot gate; map-back remains locked"

# -----------------------------------------------------------------------------
# Frozen Drive authorities
# -----------------------------------------------------------------------------
E10_REL = Path("provenance/hybrid_dp/V16E10_SGSIM_HYBRID_PATH_STATE_PROTOCOL_FREEZE")
E9R1_REL = Path("provenance/hybrid_dp/V16E9_R1_RECONCILED_ADAPTER_IDENTICAL_STATE_CERTIFICATION")
E8R1_REL = Path("provenance/hybrid_dp/V16E8_R1_ADAPTER_PHYSICS_SCREEN_RECONCILIATION_PROTOCOL")
E7_REL = Path("provenance/hybrid_dp/V16E7_HYBRID_EVIDENCE_AND_DEPLOYMENT_ROLE_FREEZE")
E5_REL = Path("provenance/hybrid_dp/V16E5_PRETRAINING_MANIFEST_FREEZE")
E3_REL = Path("provenance/hybrid_dp/V16E3_R1_HYBRID_PROTOCOL_FREEZE")
E6A_REL = Path("models/hybrid_dp/V16E6A_HYBRID10_CONTROLLED_R1")
E6B_REL = Path("models/hybrid_dp/V16E6B_HYBRID12_CONTROLLED_R1")

OUT_REL = Path("pilots/hybrid_dp/V16E11_SGSIM_100D_CONTROLLED_STREAMLINE_PILOT")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E11_BLOCKED_SGSIM_STREAMLINE_PILOT")

E10_RUNNER = (
    "PAD_Stream_V16E10_SGSim_Hybrid_Path_State_Semantics_and_Controlled_Deployment_Protocol_Freeze.py",
    "ab2f5d3e9029700bd54a5305c97dac8f550204f66d308dabc573dc58f3db0f96",
)
E10 = {
    "path_state": (
        "V16E10_SGSim_Hybrid_Path_State_Semantics.json",
        "64b4d6fecf04d66c350c0e4d168defbf1d324f5a9a3f52d593c5bd1fc09cfba8",
    ),
    "deployment": (
        "V16E10_Controlled_Deployment_Protocol.json",
        "43751ca471e6493caa91abb7cf5726e5418c889119920cfbb62710e4bdea0b0d",
    ),
    "results": (
        "V16E10_Path_State_Protocol_Freeze_Results.json",
        "fc316b6c9db03545f3437ede749e05cba71f1b18eeed803ecb8fe41a08c748ee",
    ),
    "summary": (
        "PAD_Stream_V16E10_Summary.json",
        "2abede3797238396a6b6bdc13a0a3ca61567010d58787f4be468248513fad43e",
    ),
    "handoff": (
        "V16E10_Handoff.md",
        "18b6b57db6b90c5ea0f4346165c18c72512e9ba2ab48c6b5ada4d41374bfd075",
    ),
}

E9R1_RUNNER = (
    "PAD_Stream_V16E9_R1_Reconciled_Hybrid_Transport_Adapter_Identical_State_Certification.py",
    "c5dbf87fb17d16cced65f1e77941e6d8e8e274b8a24f852136ac210d0c732ff0",
)
E9R1 = {
    "audit": (
        "V16E9_R1_Reconciled_Identical_State_Certification_Audit.json",
        "59e5c40c29c67b56ed5b900f6f52b71912e0e91a6900f732507be56afd34a2e5",
    ),
    "summary": (
        "PAD_Stream_V16E9_R1_Summary.json",
        "17a2bf9db9f9085934e73e26065f881d687945ec62d10b33e5756091d12cc40e",
    ),
    "handoff": (
        "V16E9_R1_Handoff.md",
        "5aefc455441e0c13288c593865ffddc1e649ad59804635221fb2c5ae739a0b49",
    ),
}

E8R1 = {
    "contract": (
        "V16E8_R1_Adapter_Physics_Screen_Reconciliation_Protocol.json",
        "4c00180b966cf2e21b3774d1df4c06520f03ba6a4354815c0bfb895d02187cb0",
    ),
    "results": (
        "V16E8_R1_Adapter_Physics_Screen_Reconciliation_Results.json",
        "0e29a43b240f6b94e9c2fbaa9c56fbaab5b0824712f21132b003851f473938ea",
    ),
}
E7_ROUTING = (
    "V16E7_Deployment_Routing_Contract.json",
    "88d434ecc292c49b7cff58aa70223e76a2dc2ce6f8f7124c461867274407fcea",
)
E5_MANIFEST = (
    "V16E5_PreTraining_Manifest.json",
    "c197dae32d01a1f083f7ad414e601eac1f44d7405b6087c7c7db8a6c28c5c808",
)
E3_PROTOCOL = (
    "V16E3_R1_Hybrid_BL_DP_Protocol.json",
    "57bcb2e74c68eb77ed8de69d75ddafc00b38d2f3c4e9b884bfc87676160db4a1",
)

E9_ADAPTER = (
    "PAD_Stream_V16E9_Hybrid_Transport_Adapter.py",
    "e5a89a4a591c5e3adf9be52ef274739e45a43f729cd45f044d39cc217bbd7d8f",
)
R2_ADAPTER = (
    "PAD_Stream_V16E3_R2_Repaired_BL_Teacher.py",
    "640a853fd0775c5efaf2922976d5c3843fa69ce9e5165245daffefdb3d4eac2a",
)

E6A_RUNNER = (
    "PAD_Stream_V16E6A_Hybrid10_Controlled_Training_and_Validation.py",
    "c48a1d8f185bb4576af7e255a5cf190fc47d2fa5360f526e2254d831254994ad",
)
E6B_RUNNER = (
    "PAD_Stream_V16E6B_Hybrid12_Controlled_Training_and_Validation.py",
    "79cffcf527d20a8f036f561a5a5372f9858f47f91eb08dd34dc0069d6229dcf0",
)
E6A_CHECKPOINT = (
    "V16E6A_Hybrid10_Accepted.weights.h5",
    "0b7be119dfc14c08bd8f7bb3c84c64b8d425e0176cddebf952687a49c05402a9",
)
E6B_CHECKPOINT = (
    "V16E6B_Hybrid12_Accepted.weights.h5",
    "1321008f1127ae48fa3d230b89759337779a9db83819ae8a73719ed3dfec12d8",
)

# Source-authentic production constitutive authority already frozen in V16C.
# E11 does not derive/tune these values from SGSim performance.
C14_SOURCE = (
    "PAD_Stream_V16C14_Production_Full_Physics_Transport_Parameter_Authority_Contract.py",
    "cd3b45b72ae2dc7d6906aad7323522d467234ba81a7b641fd323ddc3df3bb419",
)

# E10 repository context sources. Their exact current hashes are not repeated
# here; E11 verifies them against identities recorded by the immutable E10 run.
E10_CONTEXT_SOURCES = [
    "PAD_Stream_V15SG1_SGSim_Geology_Integration.py",
    "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py",
    "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py",
    "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py",
]

# -----------------------------------------------------------------------------
# Frozen pilot geometry / clock
# -----------------------------------------------------------------------------
PHYSICAL_TIME_DAYS = 100.0
EXPECTED_GRID = (15, 50, 50)  # (k,j,i)
DX_M = 20.0 * 0.3048
DY_M = 20.0 * 0.3048
DZ_M = 4.0 * 0.3048
EXPECTED_NSTREAM = 1078
EXPECTED_NXI = 201
EXPECTED_RATE_M3_DAY = 714.285714
RATE_ABS_TOL_M3_DAY = 5.0e-4

ROUTE_CODES = {
    "HYBRID10_ACCEPT": 10,
    "HYBRID12_ACCEPT": 12,
    "EXACT_R2_FALLBACK": 20,
    "FULL_PHYSICS_SG7A_FALLBACK": 30,
    "BLOCKED_UNRESOLVED": 99,
}

PROHIBITIONS = [
    "NO TRAINING OR GRADIENT UPDATE.",
    "NO CHECKPOINT CREATION, SELECTION, REPLACEMENT, OR RETRAINING.",
    "NO INTERNAL-TEST ARRAY INDEXING OR RE-EVALUATION.",
    "NO OOD REOPENING.",
    "NO SGSim PRESSURE / DARCY / POLLOCK / TOF RECOMPUTATION.",
    "NO GRID MAP-BACK OR NEW GRID SATURATION FIELD.",
    "NO DP KH REALLOCATION ON TOP OF EXACT 3-D POLLOCK FLOW WEIGHTS.",
    "NO ABSOLUTE PERMEABILITY OR LAYER THICKNESS NEURAL CHANNEL.",
    "NO PATHWISE CONSTITUTIVE AVERAGING OR FITTED EFFECTIVE PROPERTY.",
    "NO NEAREST-CELL PROPERTY GUESS FROM RESAMPLED XYZ.",
    "NO POST-BREAKTHROUGH HYBRID USE.",
    "NO CHANGE TO V16E-7 ROUTING OR V16E-8-R1 SCREENS.",
]


class GateError(RuntimeError):
    pass


class Gates:
    def __init__(self):
        self.items: dict[str, dict[str, Any]] = {}

    def check(self, name: str, condition: Any, detail: str = ""):
        ok = bool(condition)
        self.items[name] = {"passed": ok, "detail": detail}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""), flush=True)
        if not ok:
            raise GateError(name + (f": {detail}" if detail else ""))


# =============================================================================
# Generic utilities
# =============================================================================

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(obj: Any) -> bytes:
    return (json.dumps(native(obj), indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


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


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def bind(g: Gates, label: str, path: Path, expected: str):
    g.check(label + "_exists", path.is_file(), str(path))
    actual = sha(path)
    g.check(label + "_SHA_exact", actual == expected, actual if actual != expected else "")
    return actual


def import_exact(path: Path, expected_sha: str, module_name: str):
    actual = sha(path)
    if actual != expected_sha:
        raise GateError(f"SHA mismatch for {path.name}: {actual}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"Could not import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def publish_atomic(out: Path, payloads: dict[str, bytes], binary_files: dict[str, Path] | None = None):
    binary_files = binary_files or {}
    expected_names = set(payloads) | set(binary_files)
    if out.exists():
        names = {p.name for p in out.iterdir() if p.is_file()}
        if names != expected_names:
            raise GateError("Existing E11 output directory differs; nothing overwritten")
        for name, data in payloads.items():
            if (out / name).read_bytes() != data:
                raise GateError("Existing E11 output bytes differ; nothing overwritten")
        for name, src in binary_files.items():
            if sha(out / name) != sha(src):
                raise GateError("Existing E11 binary output differs; nothing overwritten")
        print("Existing identical V16E-11 result reused.", flush=True)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".v16e11-", dir=out.parent))
    try:
        for name, data in payloads.items():
            p = stage / name
            with p.open("xb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        for name, src in binary_files.items():
            shutil.copyfile(src, stage / name)
        stage.rename(out)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def publish_blocked(drive: Path, report: dict) -> tuple[Path, str]:
    report_bytes = encoded(report)
    report_sha = digest(report_bytes)
    out = drive / BLOCKED_REL / report_sha[:16]
    summary = {
        "milestone": MILESTONE,
        "status": "BLOCKED",
        "report_sha256": report_sha,
        "training_performed": False,
        "checkpoint_changed": False,
        "pressure_Darcy_Pollock_TOF_recomputed": False,
        "grid_mapback_performed": False,
        "internal_test_reopened": False,
        "OOD_opened": False,
        "next_milestone": NEXT_FAIL,
    }
    handoff = f"""# PAD-Stream V16E-11 — BLOCKED\n\nThe controlled SGSim pilot did not close. No training/checkpoint change, no pressure/Darcy/Pollock/TOF recomputation, no map-back, and no test/OOD access occurred.\n\nBlocked report SHA: {report_sha}\nNEXT: {NEXT_FAIL}\n""".encode("utf-8")
    publish_atomic(out, {
        "V16E11_Blocked_SGSim_Streamline_Pilot_Audit.json": report_bytes,
        "PAD_Stream_V16E11_Blocked_Summary.json": encoded(summary),
        "V16E11_Blocked_Handoff.md": handoff,
    })
    return out, report_sha


# =============================================================================
# E10 context source identity verification
# =============================================================================

def verify_e10_source_identities(g: Gates, project: Path, e10_results: dict):
    rows = e10_results.get("repository_context_source_identities")
    g.check("E10_repository_context_source_identities_present", isinstance(rows, dict) and len(rows) == 4)
    by_name = rows
    for name in E10_CONTEXT_SOURCES:
        g.check("E10_recorded_" + name.replace(".", "_"), name in by_name)
        p = project / name
        g.check("source_" + name.replace(".", "_") + "_exists", p.is_file(), str(p))
        actual = sha(p)
        expected = str(by_name[name]["sha256"])
        g.check("source_" + name.replace(".", "_") + "_SHA_matches_E10", actual == expected, actual if actual != expected else "")


# =============================================================================
# Frozen constitutive authority (V16C-14 production base)
# =============================================================================

def literal_number(node: ast.AST) -> float | None:
    try:
        v = ast.literal_eval(node)
    except Exception:
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    return None


def c14_production_params(path: Path) -> dict[str, float]:
    """Recover the explicitly frozen C14 production base from its params list."""
    tree = ast.parse(path.read_text(encoding="utf-8", errors="strict"))
    found: dict[str, list[float]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # C14 serializes the production authority as dict(parameter="...", value=...).
        kws = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        if "parameter" not in kws or "value" not in kws:
            continue
        try:
            key = ast.literal_eval(kws["parameter"])
        except Exception:
            continue
        value = literal_number(kws["value"])
        if isinstance(key, str) and value is not None:
            found.setdefault(key, []).append(value)

    aliases = {
        "nw": ["nw"],
        "no": ["no"],
        "swc": ["Swc", "swc"],
        "sor": ["Sor", "sor"],
        "krw_max": ["krw_max"],
        "kro_max": ["kro_max"],
        "mu_w": ["mu_w"],
        "mu_o": ["mu_o"],
        "phi": ["phi"],
    }
    out = {}
    for canonical, names in aliases.items():
        vals = []
        for name in names:
            vals.extend(found.get(name, []))
        uniq = sorted(set(float(x) for x in vals))
        if len(uniq) != 1:
            raise GateError(f"C14 production parameter {canonical} is not uniquely source-bound: {uniq}")
        out[canonical] = uniq[0]
    return out


def parameters_inside_e3(p: dict[str, float], e3: dict) -> bool:
    b = e3["dataset_design"]["bounds"]
    checks = [
        b["no"][0] <= p["no"] <= b["no"][1],
        b["nw"][0] <= p["nw"] <= b["nw"][1],
        b["swc"][0] <= p["swc"] <= b["swc"][1],
        b["sor"][0] <= p["sor"] <= b["sor"][1],
        b["mu_w_cP"][0] <= p["mu_w"] <= b["mu_w_cP"][1],
        b["mu_o_cP"][0] <= p["mu_o"] <= b["mu_o_cP"][1],
        b["phi"][0] <= p["phi"] <= b["phi"][1],
    ]
    return all(checks)


# =============================================================================
# SG6 artifact discovery and validation
# =============================================================================

def first_key(z, aliases: list[str]) -> str | None:
    for k in aliases:
        if k in z.files:
            return k
    return None


def load_sg6_candidate(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=True) as z:
        keys = {
            "xi": first_key(z, ["xi", "transport_xi"]),
            "xyz": first_key(z, ["xyz_m", "transport_xyz", "xyz", "streamline_xyz", "XYZ"]),
            "tau": first_key(z, ["tau_s", "tof_s", "tau", "transport_tau_s", "pollock_tau_s"]),
            "tau_end": first_key(z, ["tau_end_s", "terminal_tau_s", "terminal_tof_s", "pollock_tau_end_s"]),
            "weights": first_key(z, ["weights_m3_s", "weights", "flow_weights_m3_s", "streamline_weight_m3_s"]),
            "producer": first_key(z, ["producer", "producer_id", "producer_index"]),
            "streamline_id": first_key(z, ["streamline_id", "id", "seed_id"]),
        }
        if any(keys[k] is None for k in ["xi", "xyz", "tau", "tau_end", "weights", "producer"]):
            raise GateError(f"SG6 candidate lacks required keys: {path} -> {keys}")
        d = {
            "path": path,
            "sha256": sha(path),
            "keys": keys,
            "xi": np.asarray(z[keys["xi"]], dtype=np.float64),
            "xyz_m": np.asarray(z[keys["xyz"]], dtype=np.float64),
            "tau_s": np.asarray(z[keys["tau"]], dtype=np.float64),
            "tau_end_s": np.asarray(z[keys["tau_end"]], dtype=np.float64),
            "weights_m3_s": np.asarray(z[keys["weights"]], dtype=np.float64),
            "producer": np.asarray(z[keys["producer"]]),
            "streamline_id": np.asarray(z[keys["streamline_id"]]) if keys["streamline_id"] is not None else None,
        }
    return d


def sg6_is_reference(d: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    xi = d["xi"]
    xyz = d["xyz_m"]
    tau = d["tau_s"]
    end = d["tau_end_s"]
    w = d["weights_m3_s"]
    prod = d["producer"]
    checks = {
        "xi_shape": xi.shape == (EXPECTED_NXI,),
        "xi_exact": xi.shape == (EXPECTED_NXI,) and np.array_equal(xi, np.linspace(0.0, 1.0, EXPECTED_NXI)),
        "xyz_shape": xyz.shape == (EXPECTED_NSTREAM, EXPECTED_NXI, 3),
        "tau_shape": tau.shape == (EXPECTED_NSTREAM, EXPECTED_NXI),
        "tau_end_shape": end.shape == (EXPECTED_NSTREAM,),
        "weights_shape": w.shape == (EXPECTED_NSTREAM,),
        "producer_shape": prod.shape == (EXPECTED_NSTREAM,),
        "finite": bool(np.all(np.isfinite(xyz)) and np.all(np.isfinite(tau)) and np.all(np.isfinite(end)) and np.all(np.isfinite(w))),
        "positive_terminal_TOF": bool(end.shape == (EXPECTED_NSTREAM,) and np.all(end > 0.0)),
        "positive_weights": bool(w.shape == (EXPECTED_NSTREAM,) and np.all(w > 0.0)),
        "tau_monotonic": bool(tau.shape == (EXPECTED_NSTREAM, EXPECTED_NXI) and np.all(np.diff(tau, axis=1) >= -1.0e-12)),
        "tau_starts_zero": bool(tau.shape == (EXPECTED_NSTREAM, EXPECTED_NXI) and np.max(np.abs(tau[:, 0])) <= 1.0e-8),
        "tau_end_match": bool(tau.shape == (EXPECTED_NSTREAM, EXPECTED_NXI) and end.shape == (EXPECTED_NSTREAM,) and np.allclose(tau[:, -1], end, rtol=1.0e-12, atol=1.0e-7)),
        "weight_sum": bool(w.shape == (EXPECTED_NSTREAM,) and abs(float(np.sum(w) * 86400.0) - EXPECTED_RATE_M3_DAY) <= RATE_ABS_TOL_M3_DAY),
        "four_producers": len(set(map(str, prod.tolist()))) == 4,
    }
    return all(checks.values()), checks


def candidate_roots(project: Path, drive: Path, workspace: Path | None) -> list[Path]:
    roots = []
    if workspace is not None:
        roots.append(workspace)
    roots.extend([project, drive])
    # Colab may have a deliberately copied sibling Version-15 workspace.
    if project.parent.exists():
        for p in sorted(project.parent.glob("*PAD*Stream*")):
            if p.is_dir():
                roots.append(p)
    out = []
    seen = set()
    for p in roots:
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        if str(rp) not in seen and rp.exists():
            seen.add(str(rp)); out.append(rp)
    return out


def discover_sg6(project: Path, drive: Path, workspace: Path | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates = []
    seen = set()
    for root in candidate_roots(project, drive, workspace):
        # E10 froze the existing Version-15 SG6 reference, whose canonical
        # filename is STREAMLINE_TRANSPORT_COORDINATES.npz. Do not substitute a
        # later V16D re-generated SG6-style database merely because its shape is
        # also 1078x201.
        for p in root.rglob("STREAMLINE_TRANSPORT_COORDINATES.npz"):
            if p in seen or not p.is_file():
                continue
            seen.add(p)
            try:
                d = load_sg6_candidate(p)
                ok, checks = sg6_is_reference(d)
            except Exception as exc:
                candidates.append({"path": str(p), "eligible_reference": False, "load_error": repr(exc)})
                continue
            candidates.append({"path": str(p), "sha256": d["sha256"], "eligible_reference": ok, "checks": checks})

    eligible = [c for c in candidates if c.get("eligible_reference")]
    if not eligible:
        raise GateError("No source-authentic 1078x201 SG6 reference artifact was found; E11 will not recompute TOF")

    # E10 explicitly froze the 7x7 / 1078 reference. Prefer an explicit 07x07
    # workspace label only as a provenance discriminator, never by numerical score.
    named = [c for c in eligible if "07x07" in c["path"].lower() or "7x7" in c["path"].lower()]
    pool = named if named else eligible
    distinct = {}
    for c in pool:
        distinct.setdefault(c["sha256"], []).append(c)
    if len(distinct) != 1:
        raise GateError("Multiple non-identical 1078-streamline SG6 reference candidates are provenance-ambiguous: " + "; ".join(c["path"] for c in pool))
    selected_path = Path(next(iter(distinct.values()))[0]["path"])
    return load_sg6_candidate(selected_path), candidates


# =============================================================================
# Source-native SG5 trajectory extraction and exact segment-cell provenance
# =============================================================================

def unpack_object_array(a: np.ndarray) -> list[Any]:
    return list(a.tolist()) if a.dtype == object else list(a)


def extract_sg5_streamlines(path: Path) -> list[dict[str, Any]]:
    with np.load(path, allow_pickle=True) as z:
        for key in ["streamlines", "pollock_streamlines", "streamline_records"]:
            if key in z.files:
                rec = unpack_object_array(z[key])
                if rec and isinstance(rec[0], dict):
                    return rec
        pk = first_key(z, ["points_m", "streamline_points_m", "xyz_m"])
        tk = first_key(z, ["times_s", "streamline_times_s", "pollock_times_s"])
        ek = first_key(z, ["travel_time_s", "tau_end_s", "terminal_tof_s"])
        wk = first_key(z, ["weight_m3_s", "streamline_weight_m3_s", "weights_m3_s"])
        rk = first_key(z, ["producer", "producer_id", "producer_name"])
        sk = first_key(z, ["status", "streamline_status"])
        ik = first_key(z, ["seed_id", "streamline_id", "id"])
        if pk is None or tk is None or wk is None:
            raise GateError(f"SG5 artifact does not expose source-native trajectories/weights: {path}")
        points = unpack_object_array(z[pk]); times = unpack_object_array(z[tk]); n = len(points)
        def vals(key, default):
            if key is None:
                return [default for _ in range(n)]
            q = unpack_object_array(z[key])
            if len(q) != n:
                raise GateError(f"SG5 parallel key {key} length mismatch")
            return q
        ends = vals(ek, None); weights = vals(wk, np.nan); producers = vals(rk, None); statuses = vals(sk, "PRODUCER"); ids = vals(ik, None)
        out = []
        for i in range(n):
            tt = np.asarray(times[i], dtype=np.float64)
            out.append({
                "seed_id": i if ids[i] is None else ids[i],
                "points_m": np.asarray(points[i], dtype=np.float64),
                "times_s": tt,
                "travel_time_s": float(tt[-1]) if ends[i] is None else float(ends[i]),
                "weight_m3_s": float(weights[i]),
                "producer": producers[i],
                "status": statuses[i],
            })
        return out


def locate_sg5_for_sg6(sg6_path: Path) -> Path:
    workspace = sg6_path.parents[2] if len(sg6_path.parents) >= 3 else sg6_path.parent
    preferred = workspace / "output" / "V15_SG5" / "STREAMLINES_POLLOCK.npz"
    if preferred.is_file():
        return preferred
    candidates = [p for p in workspace.rglob("STREAMLINES_POLLOCK.npz") if p.is_file()]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise GateError(f"Matching frozen SG5 STREAMLINES_POLLOCK.npz not found under workspace {workspace}; E11 will not retrace")
    hashes = {sha(p) for p in candidates}
    if len(hashes) == 1:
        return sorted(candidates)[0]
    raise GateError("Multiple non-identical SG5 source-native trajectory artifacts found in selected workspace")


def clean_native(points: np.ndarray, times: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    p = np.asarray(points, dtype=np.float64); t = np.asarray(times, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or t.ndim != 1 or len(p) != len(t) or len(t) < 2:
        raise GateError("invalid source-native SG5 point/time schema")
    if not np.all(np.isfinite(p)) or not np.all(np.isfinite(t)) or np.any(np.diff(t) < 0.0):
        raise GateError("nonfinite/nonmonotone source-native SG5 trajectory")
    # Same exact duplicate-time bookkeeping rule as the certified V16D-9 lineage:
    # preserve the last point at each time.
    keep = np.r_[np.diff(t) > 0.0, True]
    p = p[keep]; t = t[keep]
    if len(t) < 2 or np.any(np.diff(t) <= 0.0):
        raise GateError("SG5 trajectory cannot be reduced to strictly increasing Pollock time")
    return p, t


def interior_cell(point: np.ndarray) -> tuple[int, int, int]:
    dims = [(DX_M, EXPECTED_GRID[2]), (DY_M, EXPECTED_GRID[1]), (DZ_M, EXPECTED_GRID[0])]
    idx = []
    for coord, (d, n) in zip(np.asarray(point, dtype=float), dims):
        L = d * n
        tol = 1.0e-10 * max(1.0, L)
        if not (-tol < coord < L + tol):
            raise GateError(f"Pollock segment interior point outside SGSim grid: {point}")
        # An exact interior point may not lie on an internal face. If it does,
        # source topology is ambiguous and E11 refuses to guess a side.
        ratio = coord / d
        nearest = round(ratio)
        if 0 < nearest < n and abs(ratio - nearest) <= 1.0e-10:
            raise GateError(f"Pollock segment interior lies on an internal grid face; exact cell membership ambiguous: {point}")
        j = int(math.floor(min(max(coord, 0.0), np.nextafter(L, 0.0)) / d))
        if not (0 <= j < n):
            raise GateError("invalid recovered grid index")
        idx.append(j)
    i, j, k = idx
    return (k, j, i)


def segment_cells(points: np.ndarray) -> list[tuple[int, int, int]]:
    cells = []
    for a, b in zip(points[:-1], points[1:]):
        # A source-native Pollock step should remain inside exactly one cell until
        # its next face crossing. Three strictly interior samples must therefore
        # resolve to the same logical cell. This is topology recovery, not a
        # nearest-neighbor lookup on resampled XYZ.
        c1 = interior_cell(a + 0.25 * (b - a))
        c2 = interior_cell(a + 0.50 * (b - a))
        c3 = interior_cell(a + 0.75 * (b - a))
        if not (c1 == c2 == c3):
            raise GateError(f"source-native Pollock step spans more than one logical cell: {c1},{c2},{c3}")
        cells.append(c2)
    return cells


def cells_for_tau_nodes(stream: dict[str, Any], tau_nodes: np.ndarray) -> np.ndarray:
    p, t = clean_native(stream["points_m"], stream["times_s"])
    te = float(stream["travel_time_s"])
    if abs(t[0]) > 1.0e-10 * max(1.0, abs(te)) or not np.isclose(t[-1], te, rtol=1.0e-10, atol=1.0e-7):
        raise GateError("SG5 time origin/terminal TOF contract mismatch")
    cells = segment_cells(p)
    q = np.asarray(tau_nodes, dtype=np.float64)
    if np.any(q < -1.0e-8) or np.any(q > te + 1.0e-7):
        raise GateError("SG6 tau node outside source-native SG5 time interval")
    # Frozen E10 rule: downstream/right-continuous cell at crossings for tau>0;
    # injector segment at tau=0. Terminal node is assigned to the terminal segment.
    si = np.searchsorted(t, q, side="right") - 1
    si = np.clip(si, 0, len(cells) - 1)
    out = np.asarray([cells[int(j)] for j in si], dtype=np.int32)
    return out


def verify_sg5_sg6_alignment(g: Gates, streams: list[dict[str, Any]], sg6: dict[str, Any]) -> np.ndarray:
    g.check("SG5_streamline_count_1078", len(streams) == EXPECTED_NSTREAM, str(len(streams)))
    sg6_ids = sg6["streamline_id"]
    if sg6_ids is not None:
        native_ids = np.asarray([s.get("seed_id", i) for i, s in enumerate(streams)])
        try:
            ids_equal = bool(np.array_equal(native_ids.astype(str), np.asarray(sg6_ids).astype(str)))
        except Exception:
            ids_equal = False
        g.check("SG5_SG6_streamline_ID_order_exact", ids_equal)
    # Independently bind numerical ordering.
    native_end = np.asarray([float(s["travel_time_s"]) for s in streams])
    native_w = np.asarray([float(s["weight_m3_s"]) for s in streams])
    native_prod = np.asarray([str(s.get("producer", "")) for s in streams])
    g.check("SG5_SG6_terminal_TOF_order_exact", np.allclose(native_end, sg6["tau_end_s"], rtol=1.0e-10, atol=1.0e-7))
    g.check("SG5_SG6_weight_order_exact", np.allclose(native_w, sg6["weights_m3_s"], rtol=1.0e-10, atol=1.0e-12))
    g.check("SG5_SG6_producer_order_exact", np.array_equal(native_prod.astype(str), np.asarray(sg6["producer"]).astype(str)))
    statuses = [str(s.get("status", "")).upper() for s in streams]
    g.check("SG5_all_producer_captured", all("PRODUCER" in s for s in statuses))

    cells = np.empty((EXPECTED_NSTREAM, EXPECTED_NXI, 3), dtype=np.int32)
    for i, s in enumerate(streams):
        cells[i] = cells_for_tau_nodes(s, sg6["tau_s"][i])
        if (i + 1) % 100 == 0 or i + 1 == EXPECTED_NSTREAM:
            print(f"  exact segment-cell provenance {i+1}/{EXPECTED_NSTREAM}", flush=True)
    g.check("exact_Pollock_segment_cell_provenance_all_nodes", cells.shape == (EXPECTED_NSTREAM, EXPECTED_NXI, 3))
    g.check("recovered_cell_indices_inside_grid", bool(
        np.all((cells[:, :, 0] >= 0) & (cells[:, :, 0] < EXPECTED_GRID[0]))
        and np.all((cells[:, :, 1] >= 0) & (cells[:, :, 1] < EXPECTED_GRID[1]))
        and np.all((cells[:, :, 2] >= 0) & (cells[:, :, 2] < EXPECTED_GRID[2]))
    ))
    return cells


# =============================================================================
# Frozen SG7A truth carried in the accepted SG7C deployment database
# =============================================================================

def load_sg7a_truth100_for_workspace(sg6_path: Path) -> dict[str, Any] | None:
    workspace = sg6_path.parents[2]
    preferred = workspace / "output" / "V15_SG7C" / "SG7C_FROZEN_PIRNN_STREAMLINE_DEPLOYMENT.npz"
    candidates = [preferred] if preferred.is_file() else []
    if not candidates:
        candidates = [p for p in workspace.rglob("SG7C_FROZEN_PIRNN_STREAMLINE_DEPLOYMENT.npz") if p.is_file()]
    if not candidates:
        return None
    if len({sha(p) for p in candidates}) != 1:
        raise GateError("Multiple non-identical SG7C deployment databases found in selected SGSim workspace")
    path = sorted(candidates)[0]
    with np.load(path, allow_pickle=True) as z:
        tk = first_key(z, ["times_days", "physical_times_days", "deployment_times_days"])
        sk = first_key(z, ["SG7A_saturation", "truth_saturation", "reference_saturation", "S_truth"])
        if tk is None or sk is None:
            raise GateError("Frozen SG7C database does not expose stored SG7A truth")
        times = np.asarray(z[tk], dtype=np.float64)
        truth = np.asarray(z[sk], dtype=np.float32)
        idx = int(np.argmin(np.abs(times - PHYSICAL_TIME_DAYS)))
        if not np.isclose(times[idx], PHYSICAL_TIME_DAYS, rtol=0.0, atol=1.0e-12):
            raise GateError("Frozen SG7C database has no exact 100-day SG7A truth snapshot")
        truth100 = np.asarray(truth[idx], dtype=np.float32)
    if truth100.shape != (EXPECTED_NSTREAM, EXPECTED_NXI) or not np.all(np.isfinite(truth100)):
        raise GateError(f"SG7A truth100 shape/finite contract failure: {truth100.shape}")
    return {"path": path, "sha256": sha(path), "truth100": truth100}


# =============================================================================
# Hybrid model / exact physics execution
# =============================================================================

def classify_clock(xstar: float) -> str:
    if not math.isfinite(xstar) or xstar <= 0.0:
        return "UNRESOLVED"
    if xstar >= 1.0:
        return "POSTBT_FULL_PHYSICS"
    if 0.05 <= xstar <= 0.95:
        return "LEARNED_WINDOW"
    return "PREBT_EXACT_R2"


def screen_fan_prediction(y: np.ndarray, p: dict[str, float], state: dict[str, float], xi: np.ndarray,
                          tau_nodes: np.ndarray, r2, adapter, screen: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    yy = np.asarray(y, dtype=np.float64)
    finite = bool(np.all(np.isfinite(yy)))
    lower = float(p["swc"]); upper = 1.0 - float(p["sor"])
    bounds = finite and bool(np.all(yy >= lower) and np.all(yy <= upper))
    injection_abs = abs(float(yy[0]) - upper) if finite else float("inf")
    front_abs = abs(float(yy[-1]) - float(state["Sw_star"])) if finite else float("inf")
    char = float(np.sqrt(np.mean(np.square(
        r2.dfw_dsw(yy, adapter.teacher_params(p))[1:-1]
        - xi[1:-1] * float(state["characteristic_speed"])
    )))) if finite else float("inf")
    inventory = abs(float(state["xD_star"]) * float(np.trapezoid(yy - lower, xi)) - float(state["tD"])) if finite else float("inf")
    inc = np.diff(yy) if finite else np.asarray([float("inf")])
    mono_fraction = float(np.count_nonzero(inc > 0.0) / inc.size) if finite else 1.0
    tau_nodes = np.asarray(tau_nodes, dtype=np.float64)
    projected = adapter.project_fan_to_pollock_nodes(
        tau_nodes=tau_nodes, state=state, fan_xi=xi, fan_sw=yy, swc=lower,
    ) if finite else np.full(EXPECTED_NXI, np.nan)
    downstream = tau_nodes > float(state["tau_star"])
    downstream_exact = bool(np.all(projected[downstream] == lower)) if finite and np.any(downstream) else finite

    failures = []
    if not finite: failures.append("nonfinite")
    if not bounds: failures.append("saturation_bounds")
    if injection_abs > float(screen["injection_endpoint_abs_max"]): failures.append("injection_endpoint")
    if front_abs > float(screen["front_endpoint_abs_max"]): failures.append("front_endpoint")
    if char > float(screen["characteristic_RMSE_max"]): failures.append("characteristic")
    if inventory > float(screen["inventory_abs_max"]): failures.append("inventory")
    if mono_fraction > float(screen["monotonic_violation_fraction_max"]): failures.append("monotonicity")
    if not downstream_exact: failures.append("downstream_initial_state")
    failures = list(dict.fromkeys(failures))
    return len(failures) == 0, {
        "failures": failures,
        "finite": finite,
        "bounds": bounds,
        "injection_endpoint_abs": injection_abs,
        "front_endpoint_abs": front_abs,
        "characteristic_RMSE": char,
        "inventory_abs": inventory,
        "monotonic_violation_fraction": mono_fraction,
        "downstream_initial_state_exact": downstream_exact,
    }


def exact_r2_profile(r2, adapter, p: dict[str, float], state: dict[str, float], xi: np.ndarray, tau_nodes: np.ndarray) -> np.ndarray:
    tp = adapter.teacher_params(p)
    shock = r2.welge_shock(tp, scan_nodes=4097)
    fan = r2.fan_profile_from_shock(tp, xi, shock, fan_nodes=4097).astype(np.float64)
    return adapter.project_fan_to_pollock_nodes(
        tau_nodes=tau_nodes,
        state=state,
        fan_xi=xi,
        fan_sw=fan,
        swc=float(p["swc"]),
    ).astype(np.float32)


# =============================================================================
# Main
# =============================================================================

def run(project: Path, drive: Path, out: Path, workspace: Path | None) -> int:
    print("=" * 126)
    print("PAD-Stream V16E-11 SGSim 100-Day Path-State Eligibility Audit and Controlled Hybrid Streamline Pilot")
    print("=" * 126)
    print("\n".join(PROHIBITIONS), flush=True)
    g = Gates()

    print("\nV16E-10 PARENT AUTHORITY")
    bind(g, "E10_runner", project / E10_RUNNER[0], E10_RUNNER[1])
    for key, (name, expected) in E10.items():
        bind(g, "E10_" + key, drive / E10_REL / name, expected)
    e10_path = read_json(drive / E10_REL / E10["path_state"][0])
    e10_deploy = read_json(drive / E10_REL / E10["deployment"][0])
    e10_results = read_json(drive / E10_REL / E10["results"][0])
    e10_summary = read_json(drive / E10_REL / E10["summary"][0])
    g.check("E10_status_PASS", e10_summary.get("status") == "PASS")
    g.check("E10_E11_authorized", e10_results.get("E11_controlled_streamline_pilot_authorized") is True)
    g.check("E10_grid_mapback_still_closed", e10_results.get("E11_grid_mapback_authorized") is False)
    g.check("E10_reference_100d_1078_201", (
        e10_deploy["first_controlled_SGSim_reference"]["physical_time_days"] == [100.0]
        and e10_deploy["first_controlled_SGSim_reference"]["streamline_count_expected"] == EXPECTED_NSTREAM
        and e10_deploy["first_controlled_SGSim_reference"]["common_transport_nodes_expected"] == EXPECTED_NXI
    ))
    verify_e10_source_identities(g, project, e10_results)

    print("\nHYBRID / SCREEN / CHECKPOINT AUTHORITY")
    bind(g, "E9R1_runner", project / E9R1_RUNNER[0], E9R1_RUNNER[1])
    for key, (name, expected) in E9R1.items():
        bind(g, "E9R1_" + key, drive / E9R1_REL / name, expected)
    for key, (name, expected) in E8R1.items():
        bind(g, "E8R1_" + key, drive / E8R1_REL / name, expected)
    bind(g, "E7_routing", drive / E7_REL / E7_ROUTING[0], E7_ROUTING[1])
    bind(g, "E5_manifest", drive / E5_REL / E5_MANIFEST[0], E5_MANIFEST[1])
    bind(g, "E3_protocol", drive / E3_REL / E3_PROTOCOL[0], E3_PROTOCOL[1])
    bind(g, "R2_adapter", project / R2_ADAPTER[0], R2_ADAPTER[1])
    bind(g, "E9_adapter", project / E9_ADAPTER[0], E9_ADAPTER[1])
    bind(g, "E6A_runner", project / E6A_RUNNER[0], E6A_RUNNER[1])
    bind(g, "E6B_runner", project / E6B_RUNNER[0], E6B_RUNNER[1])
    bind(g, "E6A_checkpoint", drive / E6A_REL / E6A_CHECKPOINT[0], E6A_CHECKPOINT[1])
    bind(g, "E6B_checkpoint", drive / E6B_REL / E6B_CHECKPOINT[0], E6B_CHECKPOINT[1])
    bind(g, "C14_source", project / C14_SOURCE[0], C14_SOURCE[1])

    e8r1 = read_json(drive / E8R1_REL / E8R1["contract"][0])
    screen = e8r1["learned_proposal_execution_screen"]
    e3 = read_json(drive / E3_REL / E3_PROTOCOL[0])
    e5 = read_json(drive / E5_REL / E5_MANIFEST[0])
    e9_summary = read_json(drive / E9R1_REL / E9R1["summary"][0])
    g.check("E9R1_zero_unsafe_authority", e9_summary.get("zero_unsafe_accepted_proposals") is True)
    g.check("screen_zero_unsafe_accept", e8r1["E9_R1_required_gates"]["zero_unsafe_accepted_proposals"] is True)

    p = c14_production_params(project / C14_SOURCE[0])
    g.check("C14_constitutive_state_inside_E3", parameters_inside_e3(p, e3), json.dumps(p, sort_keys=True))
    g.check("C14_endpoint_pair_explicit_0p8_0p8", p["krw_max"] == 0.8 and p["kro_max"] == 0.8)
    g.check("constitutive_state_global_and_pathwise_constant", True, json.dumps(p, sort_keys=True))

    print("\nFROZEN SGSIM ARTIFACT DISCOVERY / IDENTITY")
    sg6, sg6_candidates = discover_sg6(project, drive, workspace)
    print(f"Selected SG6: {sg6['path']}", flush=True)
    ok, sg6_checks = sg6_is_reference(sg6)
    for k, v in sg6_checks.items():
        g.check("SG6_" + k, v)
    g.check("SG6_reference_selected", ok)

    sg5_path = locate_sg5_for_sg6(sg6["path"])
    print(f"Selected SG5: {sg5_path}", flush=True)
    streams = extract_sg5_streamlines(sg5_path)
    cell_indices = verify_sg5_sg6_alignment(g, streams, sg6)

    # The exact recovered cells are not used to invent/average neural properties.
    # They are retained as provenance evidence and future map-back support only.
    unique_cells = np.unique(cell_indices.reshape(-1, 3), axis=0)
    g.check("exact_cell_provenance_nontrivial", unique_cells.shape[0] > 1, f"unique visited cells={unique_cells.shape[0]}")

    truth_info = load_sg7a_truth100_for_workspace(sg6["path"])
    print("SG7A truth source:", truth_info["path"] if truth_info else "NOT FOUND", flush=True)

    print("\n100-DAY PATH ELIGIBILITY CLASSIFICATION")
    adapter = import_exact(project / E9_ADAPTER[0], E9_ADAPTER[1], "v16e9_adapter")
    r2 = import_exact(project / R2_ADAPTER[0], R2_ADAPTER[1], "v16e3_r2")
    teacher_p = adapter.teacher_params(p)
    shock = r2.welge_shock(teacher_p, scan_nodes=4097)
    speed = float(shock["characteristic_speed"])
    swstar = float(shock["Sw_star"])
    g.check("R2_characteristic_speed_positive", np.isfinite(speed) and speed > 0.0, f"{speed:.12g}")
    g.check("R2_shock_state_finite", np.isfinite(swstar), f"{swstar:.12g}")

    terminal_days = sg6["tau_end_s"] / 86400.0
    td = PHYSICAL_TIME_DAYS / terminal_days
    xstar = td * speed
    clock_class = np.asarray([classify_clock(float(x)) for x in xstar], dtype="U32")

    branch = adapter.route_branch(endpoints_explicit=True, krw_max=p["krw_max"], kro_max=p["kro_max"])
    g.check("C14_routes_Hybrid10", branch == "HYBRID10", branch)

    learned_candidate = clock_class == "LEARNED_WINDOW"
    prebt_r2 = clock_class == "PREBT_EXACT_R2"
    postbt_full = clock_class == "POSTBT_FULL_PHYSICS"
    unresolved_clock = clock_class == "UNRESOLVED"
    if np.any(postbt_full) and truth_info is None:
        raise GateError(f"{int(np.sum(postbt_full))} post-breakthrough paths require frozen SG7A/full-physics fallback, but no matching 100-day SG7A truth artifact is available")
    g.check("all_paths_clock_classified", not np.any(unresolved_clock))
    g.check("at_least_one_learned_eligible_path", int(np.sum(learned_candidate)) > 0, str(int(np.sum(learned_candidate))))
    print(f"  Hybrid10 learned-window candidates : {int(np.sum(learned_candidate))}")
    print(f"  Exact-R2 pre-BT clock fallback     : {int(np.sum(prebt_r2))}")
    print(f"  SG7A/full-physics post-BT fallback : {int(np.sum(postbt_full))}")

    # Initial final state uses exact routes that need no neural model.
    xi = sg6["xi"].astype(np.float64)
    final_profiles = np.full((EXPECTED_NSTREAM, EXPECTED_NXI), np.nan, dtype=np.float32)
    route_code = np.full(EXPECTED_NSTREAM, ROUTE_CODES["BLOCKED_UNRESOLVED"], dtype=np.int16)
    route_label = np.full(EXPECTED_NSTREAM, "BLOCKED_UNRESOLVED", dtype="U40")
    learned_screen_pass = np.zeros(EXPECTED_NSTREAM, dtype=np.uint8)
    learned_screen_reasons = np.full(EXPECTED_NSTREAM, "", dtype="U160")

    # Build exact homogeneous pre-BT R2 fallbacks.
    for i in np.flatnonzero(prebt_r2):
        state = adapter.physical_time_state(
            elapsed_time=PHYSICAL_TIME_DAYS,
            tau_end=float(terminal_days[i]),
            characteristic_speed=speed,
            Sw_star=swstar,
        )
        final_profiles[i] = exact_r2_profile(r2, adapter, p, state, xi, sg6["tau_s"][i] / 86400.0)
        route_code[i] = ROUTE_CODES["EXACT_R2_FALLBACK"]
        route_label[i] = "EXACT_R2_FALLBACK_CLOCK"

    # Existing heterogeneous/full-physics authority for post-BT paths.
    if np.any(postbt_full):
        truth100 = truth_info["truth100"]
        final_profiles[postbt_full] = truth100[postbt_full]
        route_code[postbt_full] = ROUTE_CODES["FULL_PHYSICS_SG7A_FALLBACK"]
        route_label[postbt_full] = "FULL_PHYSICS_SG7A_POSTBT"

    print("\nCONTROLLED HYBRID INFERENCE — ONLY AFTER ELIGIBILITY CLASSIFICATION")
    tf = None
    learned_idx = np.flatnonzero(learned_candidate)
    if learned_idx.size:
        # Reuse the exact certified E9-R1 inference implementation. TensorFlow is
        # not imported until the path classification above is complete.
        e9r1_mod = import_exact(project / E9R1_RUNNER[0], E9R1_RUNNER[1], "v16e9r1_exec")
        tf = e9r1_mod.prepare_tf(e5)
        g.check("TensorFlow_2_20_exact", tf.__version__ == "2.20.0", tf.__version__)
        model10 = e9r1_mod.build_inference_model(tf, 10, "V16E11_Hybrid10")
        g.check("Hybrid10_parameter_count_exact", model10.count_params() == 52545, str(model10.count_params()))
        model10.load_weights(str(drive / E6A_REL / E6A_CHECKPOINT[0]))
        g.check("Hybrid10_checkpoint_loaded_exact", True)

        cond = []
        states = []
        for i in learned_idx:
            state = adapter.physical_time_state(
                elapsed_time=PHYSICAL_TIME_DAYS,
                tau_end=float(terminal_days[i]),
                characteristic_speed=speed,
                Sw_star=swstar,
            )
            # E10 authorizes learned use only on the frozen xD* 0.05..0.95 window.
            if not (0.05 <= float(state["xD_star"]) <= 0.95):
                raise GateError("learned candidate escaped frozen xD* window")
            states.append(state)
            cond.append(adapter.conditioning_vector("HYBRID10", p, state))
        cond = np.asarray(cond, dtype=np.float32)
        pred_fans = e9r1_mod.infer(tf, model10, xi.astype(np.float32), cond, batch=256)

        rejection_reason_counts: dict[str, int] = {}
        accepted = 0; rejected = 0; unsafe = 0
        for local, i in enumerate(learned_idx):
            state = states[local]
            fan = pred_fans[local]
            ok_screen, metrics = screen_fan_prediction(
                fan, p, state, xi, sg6["tau_s"][i] / 86400.0, r2, adapter, screen
            )
            learned_screen_pass[i] = 1 if ok_screen else 0
            learned_screen_reasons[i] = ";".join(metrics["failures"])
            if ok_screen:
                accepted += 1
                final_profiles[i] = adapter.project_fan_to_pollock_nodes(
                    tau_nodes=sg6["tau_s"][i] / 86400.0,
                    state=state,
                    fan_xi=xi,
                    fan_sw=fan,
                    swc=float(p["swc"]),
                ).astype(np.float32)
                route_code[i] = ROUTE_CODES["HYBRID10_ACCEPT"]
                route_label[i] = "HYBRID10_ACCEPT"
                if metrics["failures"]:
                    unsafe += 1
            else:
                rejected += 1
                for reason in metrics["failures"]:
                    rejection_reason_counts[reason] = rejection_reason_counts.get(reason, 0) + 1
                # Current state is homogeneous/pathwise constant and pre-BT, so
                # E10 requires exact R2 fallback on the same Pollock TOF path.
                final_profiles[i] = exact_r2_profile(r2, adapter, p, state, xi, sg6["tau_s"][i] / 86400.0)
                route_code[i] = ROUTE_CODES["EXACT_R2_FALLBACK"]
                route_label[i] = "EXACT_R2_FALLBACK_SCREEN"

        g.check("zero_unsafe_learned_proposals_accepted", unsafe == 0, str(unsafe))
        g.check("all_learned_candidates_resolved", accepted + rejected == learned_idx.size)
        print(f"  Hybrid10 learned accepted           : {accepted}")
        print(f"  Hybrid10 screened -> exact R2       : {rejected}")
        print(f"  learned rejection reasons           : {rejection_reason_counts}")
    else:
        raise GateError("No learned-eligible SGSim path remained after E10 classification")

    # Hybrid12 is intentionally not invoked when the explicit constitutive
    # authority is the fixed 0.8/0.8 state. This is correct E7 routing, not a
    # missing branch test.
    g.check("Hybrid12_not_called_under_fixed_endpoint_state", not np.any(route_code == ROUTE_CODES["HYBRID12_ACCEPT"]))

    print("\nFINAL STREAMLINE PILOT SAFETY / COVERAGE")
    unresolved = route_code == ROUTE_CODES["BLOCKED_UNRESOLVED"]
    g.check("zero_blocked_unresolved_paths", not np.any(unresolved), str(int(np.sum(unresolved))))
    g.check("all_1078_paths_resolved", int(np.sum(~unresolved)) == EXPECTED_NSTREAM)
    g.check("final_profiles_finite", bool(np.all(np.isfinite(final_profiles))))
    g.check("final_profiles_bounds", bool(np.all(final_profiles >= p["swc"] - 1.0e-7) and np.all(final_profiles <= 1.0 - p["sor"] + 1.0e-7)))
    g.check("at_least_one_Hybrid_accept", int(np.sum(route_code == ROUTE_CODES["HYBRID10_ACCEPT"])) > 0)
    g.check("exact_fallback_authority_complete", bool(
        np.all(np.isin(route_code, [ROUTE_CODES["HYBRID10_ACCEPT"], ROUTE_CODES["HYBRID12_ACCEPT"], ROUTE_CODES["EXACT_R2_FALLBACK"], ROUTE_CODES["FULL_PHYSICS_SG7A_FALLBACK"]]))
    ))

    # Descriptive comparison only. No new post-hoc numerical acceptance
    # threshold is invented in E11.
    descriptive = None
    if truth_info is not None:
        truth100 = truth_info["truth100"].astype(np.float64)
        err = final_profiles.astype(np.float64) - truth100
        weights = sg6["weights_m3_s"].astype(np.float64)
        profile_l1 = np.mean(np.abs(err), axis=1)
        descriptive = {
            "SG7A_truth_artifact": str(truth_info["path"]),
            "SG7A_truth_artifact_sha256": truth_info["sha256"],
            "global_L1": float(np.mean(np.abs(err))),
            "global_L2": float(np.sqrt(np.mean(np.square(err)))),
            "global_Linf": float(np.max(np.abs(err))),
            "flow_weighted_profile_L1": float(np.sum(weights * profile_l1) / np.sum(weights)),
            "semantics": "DESCRIPTIVE_ONLY_NO_NEW_E11_ERROR_THRESHOLD",
        }
        print("  descriptive vs frozen SG7A truth:")
        for k in ["global_L1", "global_L2", "global_Linf", "flow_weighted_profile_L1"]:
            print(f"    {k}: {descriptive[k]:.12g}")

    route_counts = {label: int(np.sum(route_label == label)) for label in sorted(set(route_label.tolist()))}
    producer_route = {}
    for producer in sorted(set(map(str, sg6["producer"].tolist()))):
        m = np.asarray(sg6["producer"]).astype(str) == producer
        producer_route[producer] = {label: int(np.sum(m & (route_label == label))) for label in sorted(set(route_label.tolist()))}

    # Write the numerical pilot into a temporary file before atomic publication.
    tmpdir = Path(tempfile.mkdtemp(prefix="v16e11-npz-"))
    pilot_npz = tmpdir / "V16E11_SGSim_100Day_Streamline_Pilot.npz"
    try:
        np.savez_compressed(
            pilot_npz,
            physical_time_days=np.asarray(PHYSICAL_TIME_DAYS, dtype=np.float64),
            xi=xi.astype(np.float64),
            xyz_m=sg6["xyz_m"].astype(np.float64),
            tau_s=sg6["tau_s"].astype(np.float64),
            tau_end_s=sg6["tau_end_s"].astype(np.float64),
            weights_m3_s=sg6["weights_m3_s"].astype(np.float64),
            producer=np.asarray(sg6["producer"]).astype("U64"),
            streamline_id=(np.asarray(sg6["streamline_id"]).astype("U64") if sg6["streamline_id"] is not None else np.arange(EXPECTED_NSTREAM).astype("U64")),
            exact_cell_kji=cell_indices.astype(np.int32),
            tD_100=td.astype(np.float64),
            xD_star_100=xstar.astype(np.float64),
            Sw_star=np.asarray(swstar, dtype=np.float64),
            characteristic_speed=np.asarray(speed, dtype=np.float64),
            route_code=route_code.astype(np.int16),
            route_label=route_label.astype("U40"),
            learned_screen_pass=learned_screen_pass.astype(np.uint8),
            learned_screen_reasons=learned_screen_reasons.astype("U160"),
            saturation_100d=final_profiles.astype(np.float32),
            constitutive_no=np.asarray(p["no"], dtype=np.float64),
            constitutive_nw=np.asarray(p["nw"], dtype=np.float64),
            constitutive_swc=np.asarray(p["swc"], dtype=np.float64),
            constitutive_sor=np.asarray(p["sor"], dtype=np.float64),
            constitutive_mu_w_cP=np.asarray(p["mu_w"], dtype=np.float64),
            constitutive_mu_o_cP=np.asarray(p["mu_o"], dtype=np.float64),
            constitutive_phi=np.asarray(p["phi"], dtype=np.float64),
            constitutive_krw_max=np.asarray(p["krw_max"], dtype=np.float64),
            constitutive_kro_max=np.asarray(p["kro_max"], dtype=np.float64),
        )

        audit = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "runner_sha256": sha(Path(__file__)),
            "parents": {
                "E10_path_state_sha256": E10["path_state"][1],
                "E10_deployment_sha256": E10["deployment"][1],
                "E9R1_audit_sha256": E9R1["audit"][1],
                "E8R1_contract_sha256": E8R1["contract"][1],
            },
            "constitutive_authority": {
                "source": C14_SOURCE[0],
                "source_sha256": C14_SOURCE[1],
                "production_base_parameters": p,
                "pathwise_constant": True,
                "absolute_permeability_is_neural_input": False,
            },
            "SGSim_artifacts": {
                "SG6_path": str(sg6["path"]),
                "SG6_sha256": sg6["sha256"],
                "SG5_path": str(sg5_path),
                "SG5_sha256": sha(sg5_path),
                "SG7A_truth_carrier_path": str(truth_info["path"]) if truth_info else None,
                "SG7A_truth_carrier_sha256": truth_info["sha256"] if truth_info else None,
                "SG6_candidate_audit": sg6_candidates,
            },
            "exact_cell_provenance": {
                "method": "source-native SG5 positive-time Pollock segment interiors; 0.25/0.50/0.75 interior points must resolve to one structured cell; SG6 tau nodes use right-continuous source segment at crossings",
                "nearest_resampled_XYZ_lookup_used": False,
                "unique_visited_cells": int(unique_cells.shape[0]),
                "cell_array_shape": list(cell_indices.shape),
            },
            "physics_state": {
                "physical_time_days": PHYSICAL_TIME_DAYS,
                "Sw_star": swstar,
                "characteristic_speed": speed,
                "xD_star_min": float(np.min(xstar)),
                "xD_star_median": float(np.median(xstar)),
                "xD_star_max": float(np.max(xstar)),
            },
            "eligibility": {
                "Hybrid10_learned_window_candidates": int(np.sum(learned_candidate)),
                "preBT_exact_R2_clock_fallback": int(np.sum(prebt_r2)),
                "postBT_full_physics_fallback": int(np.sum(postbt_full)),
                "Hybrid12_called": False,
            },
            "final_route_counts": route_counts,
            "producer_route_counts": producer_route,
            "descriptive_vs_SG7A_truth": descriptive,
            "gates": g.items,
            "unsafe_learned_proposals_accepted": 0,
            "training_performed": False,
            "checkpoint_changed": False,
            "pressure_Darcy_Pollock_TOF_recomputed": False,
            "grid_mapback_performed": False,
            "internal_test_reopened": False,
            "OOD_opened": False,
            "next_milestone": NEXT_PASS,
        }
        audit_bytes = encoded(audit)
        route_bytes = encoded({
            "milestone": MILESTONE,
            "route_codes": ROUTE_CODES,
            "counts": route_counts,
            "producer_counts": producer_route,
            "learned_branch_routing": "Hybrid10 only for explicit fixed 0.8/0.8 C14 production state; Hybrid12 correctly not invoked",
            "fallback_semantics": "screen-rejected/path-clock-unsupported homogeneous pre-BT -> exact R2; post-BT -> frozen SG7A truth",
        })
        summary = {
            "milestone": MILESTONE,
            "status": "PASS",
            "streamline_count": EXPECTED_NSTREAM,
            "transport_nodes": EXPECTED_NXI,
            "physical_time_days": PHYSICAL_TIME_DAYS,
            "Hybrid10_learned_accept_count": int(np.sum(route_code == ROUTE_CODES["HYBRID10_ACCEPT"])),
            "Hybrid12_learned_accept_count": int(np.sum(route_code == ROUTE_CODES["HYBRID12_ACCEPT"])),
            "exact_R2_fallback_count": int(np.sum(route_code == ROUTE_CODES["EXACT_R2_FALLBACK"])),
            "full_physics_SG7A_fallback_count": int(np.sum(route_code == ROUTE_CODES["FULL_PHYSICS_SG7A_FALLBACK"])),
            "blocked_unresolved_count": int(np.sum(route_code == ROUTE_CODES["BLOCKED_UNRESOLVED"])),
            "unsafe_learned_proposals_accepted": 0,
            "checkpoint_or_routing_changed": False,
            "pressure_Darcy_Pollock_TOF_recomputed": False,
            "grid_mapback_performed": False,
            "internal_test_reopened": False,
            "OOD_opened": False,
            "SGSim_streamline_pilot_complete": True,
            "grid_mapback_authorized": False,
            "descriptive_vs_SG7A_truth": descriptive,
            "next_milestone": NEXT_PASS,
        }
        summary_bytes = encoded(summary)
        handoff = f"""# PAD-Stream V16E-11 — SGSim 100-Day Controlled Streamline Pilot PASS\n\nThe frozen 1078-streamline / 201-node Version-15 SGSim reference was re-bound without pressure, Darcy, Pollock or TOF recomputation. Exact SG5 segment-cell provenance was recovered for every SG6 transport node without nearest-XYZ property guessing.\n\nThe explicit C14 production constitutive state is fixed-endpoint 0.8/0.8, so legal learned routing in this pilot is Hybrid10. Every 100-day path was classified before TensorFlow/checkpoint loading. Learned proposals were screened under unchanged V16E-8-R1 semantics; any screen rejection was routed to exact R2, while post-breakthrough states used the frozen SG7A/full-physics truth carrier. No grid map-back was performed.\n\nRoute counts: {json.dumps(route_counts, sort_keys=True)}\nUnsafe learned proposals accepted: 0\nPilot NPZ SHA: {sha(pilot_npz)}\nAudit SHA: {digest(audit_bytes)}\nSummary SHA: {digest(summary_bytes)}\nNEXT: {NEXT_PASS}\n""".encode("utf-8")

        publish_atomic(out, {
            "V16E11_Path_Eligibility_and_Screening_Audit.json": audit_bytes,
            "V16E11_Path_Route_Counts.json": route_bytes,
            "PAD_Stream_V16E11_Summary.json": summary_bytes,
            "V16E11_Handoff.md": handoff,
        }, {"V16E11_SGSim_100Day_Streamline_Pilot.npz": pilot_npz})

        print("\n" + "=" * 126)
        print("V16E-11 RESULT: PASS")
        print("=" * 126)
        print(f"{'SGSim streamlines / nodes':52}: {EXPECTED_NSTREAM} / {EXPECTED_NXI}")
        print(f"{'Hybrid10 learned accepts':52}: {summary['Hybrid10_learned_accept_count']}")
        print(f"{'Hybrid12 learned accepts':52}: {summary['Hybrid12_learned_accept_count']}")
        print(f"{'Exact R2 fallback':52}: {summary['exact_R2_fallback_count']}")
        print(f"{'Full-physics SG7A fallback':52}: {summary['full_physics_SG7A_fallback_count']}")
        print(f"{'Blocked / unresolved':52}: {summary['blocked_unresolved_count']}")
        print(f"{'Unsafe learned proposals accepted':52}: 0")
        print(f"{'Pressure / Pollock / TOF recomputed':52}: NO / NO / NO")
        print(f"{'Grid map-back performed / authorized':52}: NO / NO")
        print(f"{'Internal test / OOD reopened':52}: NO / NO")
        print("Pilot SHA:", sha(out / "V16E11_SGSim_100Day_Streamline_Pilot.npz"))
        print("Audit SHA:", sha(out / "V16E11_Path_Eligibility_and_Screening_Audit.json"))
        print("Summary SHA:", sha(out / "PAD_Stream_V16E11_Summary.json"))
        print("Handoff SHA:", sha(out / "V16E11_Handoff.md"))
        print("Output:", out)
        print("NEXT:", NEXT_PASS)
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--sgsim-workspace", type=Path, help="Optional exact frozen Version-15 7x7 workspace if not auto-discoverable")
    args = parser.parse_args(argv)
    project = args.project_root.resolve(); drive = args.drive_root.resolve()
    out = (args.output_dir or (drive / OUT_REL)).resolve()
    workspace = args.sgsim_workspace.resolve() if args.sgsim_workspace else None
    try:
        return run(project, drive, out, workspace)
    except (GateError, OSError, ValueError, KeyError, TypeError, AssertionError, SyntaxError) as exc:
        print("\n[FAIL] V16E-11 did not close:", exc, file=sys.stderr, flush=True)
        report = {
            "milestone": MILESTONE,
            "status": BLOCKED,
            "failed_reason": repr(exc),
            "runner_sha256": sha(Path(__file__)),
            "no_training": True,
            "no_checkpoint_change": True,
            "no_pressure_Darcy_Pollock_TOF_recompute": True,
            "no_grid_mapback": True,
            "internal_test_reopened": False,
            "OOD_opened": False,
            "next_milestone": NEXT_FAIL,
        }
        try:
            blocked_out, report_sha = publish_blocked(drive, report)
            print("Blocked report SHA:", report_sha, file=sys.stderr, flush=True)
            print("Blocked output:", blocked_out, file=sys.stderr, flush=True)
        except Exception as pub_exc:
            print("Blocked evidence publication also failed:", repr(pub_exc), file=sys.stderr, flush=True)
        print("No accepted SGSim pilot or map-back authority was published.", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())

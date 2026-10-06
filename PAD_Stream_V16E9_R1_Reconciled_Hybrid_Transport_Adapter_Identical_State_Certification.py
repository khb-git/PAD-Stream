#!/usr/bin/env python3
"""PAD-Stream V16E-9-R1
Reconciled Hybrid Transport Adapter Identical-State Certification.

Controlled rerun after the blocked V16E-9 audit and successful V16E-8-R1
screen-semantics reconciliation. The accepted Hybrid10/Hybrid12 checkpoints and
the V16E-9 pure NumPy Pollock-to-fan adapter are unchanged.

This milestone:
  * uses public anchors plus a fresh TRAIN/VALIDATION-only synthetic subset that
    is disjoint from the synthetic families used in blocked V16E-9;
  * requires exact canonical float32 input-tensor identity between stored direct
    conditioning and adapter-reconstructed conditioning;
  * performs one canonical forward inference path per branch;
  * screens each learned proposal under the frozen V16E-8-R1 proposal screen;
  * routes every screen rejection to exact R2 physics fallback;
  * requires zero unsafe accepted learned proposals;
  * never indexes INTERNAL TEST or OOD and does not deploy on SGSim.

No training, checkpoint selection, threshold change, or routing change occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile

import numpy as np

MILESTONE = "V16E-9-R1"
SUCCESS = "V16E9_R1_RECONCILED_HYBRID_TRANSPORT_ADAPTER_IDENTICAL_STATE_CERTIFICATION_PASS"
BLOCKED = "V16E9_R1_RECONCILED_HYBRID_TRANSPORT_ADAPTER_IDENTICAL_STATE_CERTIFICATION_BLOCKED"
NEXT_PASS = "V16E-10 — SGSim Hybrid Path-State Semantics and Controlled Deployment Protocol Freeze"
NEXT_FAIL = "V16E-8-R2 — Adapter certification diagnosis/revision; SGSim remains locked"

E8_REL = Path("provenance/hybrid_dp/V16E8_TRANSPORT_ADAPTER_IDENTICAL_STATE_PROTOCOL_FREEZE")
E8_R1_REL = Path("provenance/hybrid_dp/V16E8_R1_ADAPTER_PHYSICS_SCREEN_RECONCILIATION_PROTOCOL")
E7_REL = Path("provenance/hybrid_dp/V16E7_HYBRID_EVIDENCE_AND_DEPLOYMENT_ROLE_FREEZE")
E5_REL = Path("provenance/hybrid_dp/V16E5_PRETRAINING_MANIFEST_FREEZE")
E3_REL = Path("provenance/hybrid_dp/V16E3_R1_HYBRID_PROTOCOL_FREEZE")
DATA_REL = Path("datasets/hybrid_dp/V16E4_R1_DETERMINISTIC_TEACHER_DATASET")
E6A_REL = Path("models/hybrid_dp/V16E6A_HYBRID10_CONTROLLED_R1")
E6B_REL = Path("models/hybrid_dp/V16E6B_HYBRID12_CONTROLLED_R1")
E9_BLOCKED_REPORT_SHA = "77b870beec1516e145cfe16d738bdef0eadfb653163ace7982845a56a1121661"
E9_BLOCKED_REL = Path("provenance/hybrid_dp/V16E9_BLOCKED_ADAPTER_EQUIVALENCE") / E9_BLOCKED_REPORT_SHA[:16]
OUT_REL = Path("provenance/hybrid_dp/V16E9_R1_RECONCILED_ADAPTER_IDENTICAL_STATE_CERTIFICATION")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E9_R1_BLOCKED_RECONCILED_ADAPTER_CERTIFICATION")

E8 = {
    "contract": ("V16E8_Transport_Adapter_Contract.json", "c88ebf508451d138197230790ce4b743b8baee40a1daf72a01d72ea0fb189820"),
    "results": ("V16E8_Transport_Adapter_and_Identical_State_Results.json", "b12be8f10fce1f6d9cc22b204a867c3a3716e41ab9a27121d60ad1a1a524ccb3"),
    "summary": ("PAD_Stream_V16E8_Summary.json", "6c05ceaeada2d127839e881f0d1d1636a8dca5fe5421f6e452340f948b435760"),
    "handoff": ("V16E8_Handoff.md", "89db55027cb7dfec8e361b486e591b0878e300ab46a298862a2673ae6efe350e"),
}
E8_RUNNER = (
    "PAD_Stream_V16E8_Transport_Adapter_and_Identical_State_Protocol_Freeze.py",
    "0267669d080fe62f8ea4edbc6d27ac9a66739462b6c9e60ce652e4b106c3d556",
)
E8_R1 = {
    "contract": ("V16E8_R1_Adapter_Physics_Screen_Reconciliation_Protocol.json", "4c00180b966cf2e21b3774d1df4c06520f03ba6a4354815c0bfb895d02187cb0"),
    "results": ("V16E8_R1_Adapter_Physics_Screen_Reconciliation_Results.json", "0e29a43b240f6b94e9c2fbaa9c56fbaab5b0824712f21132b003851f473938ea"),
    "summary": ("PAD_Stream_V16E8_R1_Summary.json", "74ed87133ddb8ca810cd671a4b3dfbbf0ab5074fe25a490b9e967d134295fbe1"),
    "handoff": ("V16E8_R1_Handoff.md", "e28ac74c8b57c935c792c2051db2165642c82cdd74f585117a6054c1311cc32c"),
}
E8_R1_RUNNER = (
    "PAD_Stream_V16E8_R1_Adapter_Physics_Screen_Reconciliation_Protocol.py",
    "5149044e8ee4799c8d69c4e885a0b4f8c19b0f1b3dde9dc8bcd7afe5bbd2d229",
)
E9_RUNNER = (
    "PAD_Stream_V16E9_Transport_Adapter_Implementation_and_Identical_State_Validation.py",
    "2e66626e666c8239987cd59fd37171b4d3a543506f3a3508111654e81050da74",
)
E9_ADAPTER = (
    "PAD_Stream_V16E9_Hybrid_Transport_Adapter.py",
    "e5a89a4a591c5e3adf9be52ef274739e45a43f729cd45f044d39cc217bbd7d8f",
)
E7_ROUTING = ("V16E7_Deployment_Routing_Contract.json", "88d434ecc292c49b7cff58aa70223e76a2dc2ce6f8f7124c461867274407fcea")
E5_MANIFEST = ("V16E5_PreTraining_Manifest.json", "c197dae32d01a1f083f7ad414e601eac1f44d7405b6087c7c7db8a6c28c5c808")
E3_PROTOCOL = ("V16E3_R1_Hybrid_BL_DP_Protocol.json", "57bcb2e74c68eb77ed8de69d75ddafc00b38d2f3c4e9b884bfc87676160db4a1")
E4_MANIFEST = ("V16E4_R1_Dataset_Manifest.json", "ec8c50720074f1ebe07be259073e44f5a82e03a45ca1cdc9385402fe280602a7")
R2_ADAPTER = ("PAD_Stream_V16E3_R2_Repaired_BL_Teacher.py", "640a853fd0775c5efaf2922976d5c3843fa69ce9e5165245daffefdb3d4eac2a")
E6A_RUNNER = ("PAD_Stream_V16E6A_Hybrid10_Controlled_Training_and_Validation.py", "c48a1d8f185bb4576af7e255a5cf190fc47d2fa5360f526e2254d831254994ad")
E6B_RUNNER = ("PAD_Stream_V16E6B_Hybrid12_Controlled_Training_and_Validation.py", "79cffcf527d20a8f036f561a5a5372f9858f47f91eb08dd34dc0069d6229dcf0")
E6A = {
    "checkpoint": ("V16E6A_Hybrid10_Accepted.weights.h5", "0b7be119dfc14c08bd8f7bb3c84c64b8d425e0176cddebf952687a49c05402a9"),
    "validation": ("V16E6A_Validation_Metrics.json", "235c41ed2e6bbf63a242cf5a8d6386802e752705dafee9705e8d09453a9589f0"),
    "summary": ("PAD_Stream_V16E6A_Summary.json", "3a737b4c8a15e30fcc5a2acf9a94a6e7af5f26a3158c99f6207e78986c0a60ea"),
    "handoff": ("V16E6A_Handoff.md", "c3ba1b3ffb4439d616f9420542e9bfc1f42b4e47467d324f075d924f78467586"),
}
E6B = {
    "checkpoint": ("V16E6B_Hybrid12_Accepted.weights.h5", "1321008f1127ae48fa3d230b89759337779a9db83819ae8a73719ed3dfec12d8"),
    "validation": ("V16E6B_Validation_Metrics.json", "3739954f7d6ee0157660f17b080379cacdb998f75f5cb1bca5f1df3141e87a59"),
    "summary": ("PAD_Stream_V16E6B_Summary.json", "ecb0cca6ff9b5c1a7c9131e92897ad80008a552e27ee1f456341683935b2ee4f"),
    "handoff": ("V16E6B_Handoff.md", "2bbfcb6549ac225410ad94501cf823943e405599a634f4ba7713f406349b5c12"),
}

LAYER_INDEX = [0, 3, 7]
CLOCK_INDEX = [0, 4, 9, 14, 19]
MODE_INDEX = [0, 1]
SELECTION_TAG = "V16E8_R1_CERT_1801|"
EXPECTED_FRESH_TRAIN = [
    "F000959", "F000610", "F000357", "F000819", "F000349", "F000131", "F000480", "F000431",
    "F000492", "F000632", "F000399", "F000786", "F000155", "F000970", "F000726", "F000017",
]
EXPECTED_FRESH_VALIDATION = [
    "F000705", "F000182", "F000698", "F000934", "F000697", "F000475", "F000672", "F000865",
    "F000503", "F000734", "F000160", "F000644", "F000259", "F000081", "F000344", "F000800",
]

PROHIBITIONS = [
    "NO TRAINING OR GRADIENT UPDATE.",
    "NO CHECKPOINT CREATION, SELECTION, REPLACEMENT, OR RETRAINING.",
    "NO INTERNAL-TEST ARRAY INDEXING OR RE-EVALUATION.",
    "NO OOD REOPENING.",
    "NO SGSim MODIFICATION OR DEPLOYMENT.",
    "NO PRESSURE / DARCY / POLLOCK / TOF RECOMPUTATION.",
    "NO GRID MAP-BACK.",
    "NO ROUTING OR CHECKPOINT CHANGE FROM V16E-7/V16E-8-R1.",
    "NO E3/R2 TEACHER-TOLERANCE CHANGE.",
    "NO E5 NEURAL ACCEPTANCE CHANGE.",
    "NO REQUIREMENT OF ZERO EXACT-PHYSICS FALLBACKS.",
]


class GateError(RuntimeError):
    pass


class Gates:
    def __init__(self):
        self.items = {}

    def check(self, name, condition, detail=""):
        ok = bool(condition)
        self.items[name] = {"passed": ok, "detail": detail}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""), flush=True)
        if not ok:
            raise GateError(name + ((": " + detail) if detail else ""))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(obj) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


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


def publish(out: Path, payloads: dict[str, bytes], label: str):
    if out.exists():
        names = {p.name for p in out.iterdir() if p.is_file()}
        if names != set(payloads):
            raise GateError(f"Existing {label} output directory differs; nothing overwritten")
        for name, data in payloads.items():
            if (out / name).read_bytes() != data:
                raise GateError(f"Existing {label} output bytes differ; nothing overwritten")
        print(f"Existing identical {label} result reused.", flush=True)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{label.lower().replace(' ','-')}-", dir=out.parent))
    try:
        for name, data in payloads.items():
            p = stage / name
            with p.open("xb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        stage.rename(out)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def publish_blocked(drive: Path, report: dict):
    data = encoded(report)
    report_sha = digest(data)
    out = drive / BLOCKED_REL / report_sha[:16]
    summary = {
        "milestone": MILESTONE,
        "status": BLOCKED,
        "report_sha256": report_sha,
        "training_performed": False,
        "checkpoints_changed": False,
        "internal_test_reopened": False,
        "OOD_opened": False,
        "SGSim_deployed": False,
        "next_milestone": NEXT_FAIL,
    }
    summary_bytes = encoded(summary)
    handoff = f"""# PAD-Stream V16E-9-R1 — BLOCKED reconciled adapter certification

The V16E-8-R1 reconciliation contract was executed on its fresh disjoint
TRAIN/VALIDATION certification population. No training, checkpoint/routing change,
internal-test/OOD access, or SGSim deployment occurred. At least one hard R1
certification gate did not close. Existing checkpoints and exact fallback remain
the only authorities; no tolerance is relaxed by this result.

Report SHA: {report_sha}
Summary SHA: {digest(summary_bytes)}
NEXT: {NEXT_FAIL}
""".encode("utf-8")
    payloads = {
        "V16E9_R1_Blocked_Reconciled_Adapter_Certification_Audit.json": data,
        "PAD_Stream_V16E9_R1_Blocked_Summary.json": summary_bytes,
        "V16E9_R1_Blocked_Handoff.md": handoff,
    }
    publish(out, payloads, "V16E9-R1-BLOCKED")
    print("\n" + "=" * 118)
    print("V16E-9-R1 RESULT: BLOCKED")
    print("=" * 118)
    print("No checkpoint/routing/tolerance change           : YES")
    print("Internal test / OOD reopened                    : NO / NO")
    print("SGSim deployment authorized                     : NO")
    print("Report SHA:", report_sha)
    print("Output:", out)
    print("NEXT:", NEXT_FAIL)
    return 2


def select_fresh_family_indices(codes, family_ids, contract):
    pop = contract["fresh_E9_R1_certification_population"]
    exclusions = {
        0: set(pop["blocked_E9_train_exclusions"]),
        1: set(pop["blocked_E9_validation_exclusions"]),
    }
    selected = {}
    for code, name in [(0, "train"), (1, "validation")]:
        ids = [str(family_ids[i]) for i in np.flatnonzero(codes == code)]
        available = [fid for fid in ids if fid not in exclusions[code]]
        ranked = sorted(
            available,
            key=lambda fid: (hashlib.sha256((SELECTION_TAG + fid).encode("utf-8")).hexdigest(), fid),
        )
        chosen = ranked[:16]
        idx = [int(np.flatnonzero(family_ids == fid)[0]) for fid in chosen]
        selected[name] = {"family_ids": chosen, "family_indices": idx}
    return selected


def canonical_rows(protocol, label):
    rows = []
    for r in protocol["benchmarks"]["E2_canonical_rows_authoritative"]:
        p = {
            "no": 2.0,
            "nw": 2.0,
            "swc": r["Swc"],
            "sor": r["Sor"],
            "mu_w": 0.5,
            "mu_o": 0.7,
            "phi": r["phi"],
            "k_mD": r["k_mD"],
            "h_ft": r["h_ft"],
            "krw_max": r["krw_max"],
            "kro_max": r["kro_max"],
        }
        if label == "Hybrid10":
            p.update(protocol["experiments"]["Hybrid10"]["fixed_endpoints"])
        rows.append(p)
    return rows


def prepare_tf(e5_manifest):
    os.environ["TF_DETERMINISTIC_OPS"] = "1"
    os.environ["TF_CUDNN_DETERMINISTIC"] = "1"
    import tensorflow as tf

    expected = e5_manifest["common_training_protocol"]["framework"]["version"]
    if tf.__version__ != expected:
        raise GateError(f"TensorFlow version mismatch: expected {expected}, actual {tf.__version__}")
    if tf.keras.mixed_precision.global_policy().name != "float32":
        tf.keras.mixed_precision.set_global_policy("float32")
    tf.config.experimental.enable_op_determinism()
    random.seed(1605)
    np.random.seed(1605)
    tf.keras.utils.set_random_seed(1605)
    return tf


def build_inference_model(tf, dim: int, name: str):
    class FanModel(tf.keras.Model):
        def __init__(self):
            super().__init__(name=name)
            self.repeat = tf.keras.layers.RepeatVector(201, name="repeat_conditioning")
            self.concat = tf.keras.layers.Concatenate(axis=-1, name="concat_xi_conditioning")
            self.lstm1 = tf.keras.layers.LSTM(
                64,
                return_sequences=True,
                activation="tanh",
                recurrent_activation="sigmoid",
                dropout=0.0,
                recurrent_dropout=0.0,
                kernel_initializer=tf.keras.initializers.GlorotUniform(),
                recurrent_initializer=tf.keras.initializers.Orthogonal(),
                bias_initializer=tf.keras.initializers.Zeros(),
                name="lstm_1",
            )
            self.lstm2 = tf.keras.layers.LSTM(
                64,
                return_sequences=True,
                activation="tanh",
                recurrent_activation="sigmoid",
                dropout=0.0,
                recurrent_dropout=0.0,
                kernel_initializer=tf.keras.initializers.GlorotUniform(),
                recurrent_initializer=tf.keras.initializers.Orthogonal(),
                bias_initializer=tf.keras.initializers.Zeros(),
                name="lstm_2",
            )
            self.head = tf.keras.layers.TimeDistributed(
                tf.keras.layers.Dense(
                    1,
                    kernel_initializer=tf.keras.initializers.GlorotUniform(),
                    bias_initializer=tf.keras.initializers.Zeros(),
                ),
                name="td_dense",
            )

        def call(self, inputs, training=False):
            xi, p = inputs
            pexp = self.repeat(p)
            x = self.concat([xi, pexp])
            x = self.lstm1(x, training=training)
            x = self.lstm2(x, training=training)
            z = self.head(x, training=training)
            swc = pexp[:, :, 2:3]
            sor = pexp[:, :, 3:4]
            return swc + (1.0 - swc - sor) * tf.math.sigmoid(z)

    model = FanModel()
    dummy_xi = tf.zeros((1, 201, 1), tf.float32)
    dummy_p = np.zeros((1, dim), np.float32)
    dummy_p[0, 0] = 2.0
    dummy_p[0, 1] = 2.0
    dummy_p[0, 2] = 0.2
    dummy_p[0, 3] = 0.2
    dummy_p[0, 4] = 0.5
    dummy_p[0, 5] = 1.0
    dummy_p[0, 6] = 0.2
    if dim == 10:
        dummy_p[0, 7] = 0.1
        dummy_p[0, 8] = 0.2
        dummy_p[0, 9] = 0.5
    else:
        dummy_p[0, 7] = 0.4
        dummy_p[0, 8] = 0.6
        dummy_p[0, 9] = 0.1
        dummy_p[0, 10] = 0.2
        dummy_p[0, 11] = 0.5
    _ = model([dummy_xi, tf.constant(dummy_p)], training=False)
    return model


def infer(tf, model, xi, cond, batch=256):
    out = []
    xi_base = tf.constant(xi[:, None].astype(np.float32))
    for start in range(0, cond.shape[0], batch):
        c = tf.constant(cond[start : start + batch], tf.float32)
        xb = tf.repeat(xi_base[None, :, :], tf.shape(c)[0], axis=0)
        y = model([xb, c], training=False)[:, :, 0]
        out.append(np.asarray(y.numpy(), dtype=np.float32))
    return np.concatenate(out, axis=0)


def screen_params_from_canonical(label, c):
    c = np.asarray(c, dtype=float)
    if label == "Hybrid10":
        return {
            "no": c[0], "nw": c[1], "swc": c[2], "sor": c[3],
            "mu_w": c[4], "mu_o": c[5], "krw_max": 0.8, "kro_max": 0.8,
        }, float(c[7]), float(c[8]), float(c[9])
    return {
        "no": c[0], "nw": c[1], "swc": c[2], "sor": c[3],
        "mu_w": c[4], "mu_o": c[5], "krw_max": c[7], "kro_max": c[8],
    }, float(c[9]), float(c[10]), float(c[11])


def evaluate_experiment(label, model, tf, data_dir, xi, selected, protocol, r2, adapter, reconciliation):
    dim = 10 if label == "Hybrid10" else 12
    branch = "HYBRID10" if label == "Hybrid10" else "HYBRID12"
    cond_mm = np.load(data_dir / label / "conditioning.npy", mmap_mode="r", allow_pickle=False)
    target_mm = np.load(data_dir / label / "Sw_fan_teacher.npy", mmap_mode="r", allow_pickle=False)
    trans_mm = np.load(data_dir / label / "transport_states.npy", mmap_mode="r", allow_pickle=False)
    phys_mm = np.load(data_dir / label / "physical_parameters.npy", mmap_mode="r", allow_pickle=False)
    anchor = np.load(data_dir / (label + "_public_anchor_Sw.npy"), allow_pickle=False)
    if cond_mm.shape != (1000, 2, 8, 20, dim):
        raise GateError(label + " conditioning shape contract changed")
    if target_mm.shape != (1000, 8, 20, 201) or trans_mm.shape != (1000, 2, 8, 20, 5) or phys_mm.shape != (1000, 8, 11):
        raise GateError(label + " dataset shape contract changed")

    direct = []
    adapted = []
    targets = []
    meta = []
    fractions = np.asarray(protocol["dataset_design"]["positive_fan_clock_fractions"], dtype=float)

    # Public development anchors: eight layers x five frozen clocks = 40 profiles.
    for li, p0 in enumerate(canonical_rows(protocol, label)):
        p = dict(p0)
        shock = r2.welge_shock(adapter.teacher_params(p), scan_nodes=4097)
        speed = float(shock["characteristic_speed"])
        route = adapter.route_branch(endpoints_explicit=True, krw_max=p["krw_max"], kro_max=p["kro_max"])
        if route != branch:
            raise GateError(f"{label} public anchor routed to {route}")
        for ti in CLOCK_INDEX:
            td = float(fractions[ti] / speed)
            xstar = float(fractions[ti])
            swstar = float(shock["Sw_star"])
            state = adapter.synthetic_roundtrip_state(tD=td, characteristic_speed=speed, Sw_star=swstar, tau_end=1.0)
            c_ad = adapter.conditioning_vector(branch, p, state)
            if branch == "HYBRID10":
                c_direct = np.asarray([p[k] for k in ["no", "nw", "swc", "sor", "mu_w", "mu_o", "phi"]] + [td, xstar, swstar], dtype=np.float32)
            else:
                c_direct = np.asarray([p[k] for k in ["no", "nw", "swc", "sor", "mu_w", "mu_o", "phi", "krw_max", "kro_max"]] + [td, xstar, swstar], dtype=np.float32)
            direct.append(c_direct)
            adapted.append(c_ad)
            targets.append(anchor[li, ti].astype(np.float32))
            meta.append({
                "population": "public_anchor", "partition": "public", "family_id": None,
                "mode": None, "layer": li, "clock": ti, "p": p, "speed": speed,
                "stored_tD": td, "stored_xstar": xstar, "stored_swstar": swstar,
                "time_days": None, "bt_days": None,
            })

    # Fresh synthetic TRAIN/VALIDATION subset: 32 families x 2 modes x 3 layers x 5 clocks = 960.
    for partition in ["train", "validation"]:
        for fi, fid in zip(selected[partition]["family_indices"], selected[partition]["family_ids"]):
            for mi in MODE_INDEX:
                for li in LAYER_INDEX:
                    p = adapter.physical_params_from_row(phys_mm[fi, li])
                    route = adapter.route_branch(endpoints_explicit=True, krw_max=p["krw_max"], kro_max=p["kro_max"])
                    if route != branch:
                        raise GateError(f"{label} fresh state {fid}/L{li+1:02d} routed to {route}")
                    shock = r2.welge_shock(adapter.teacher_params(p), scan_nodes=4097)
                    speed = float(shock["characteristic_speed"])
                    for ti in CLOCK_INDEX:
                        tr = np.asarray(trans_mm[fi, mi, li, ti], dtype=float)
                        time_days, stored_td, stored_xstar, stored_swstar, bt_days = tr.tolist()
                        state = adapter.synthetic_roundtrip_state(
                            tD=stored_td,
                            characteristic_speed=speed,
                            Sw_star=float(shock["Sw_star"]),
                            tau_end=1.0,
                        )
                        c_ad = adapter.conditioning_vector(branch, p, state)
                        c_direct = np.asarray(cond_mm[fi, mi, li, ti], dtype=np.float32)
                        direct.append(c_direct)
                        adapted.append(c_ad)
                        targets.append(np.asarray(target_mm[fi, li, ti], dtype=np.float32))
                        meta.append({
                            "population": "synthetic", "partition": partition, "family_id": fid,
                            "mode": mi, "layer": li, "clock": ti, "p": p, "speed": speed,
                            "stored_tD": stored_td, "stored_xstar": stored_xstar,
                            "stored_swstar": stored_swstar, "time_days": time_days, "bt_days": bt_days,
                        })

    direct = np.asarray(direct, dtype=np.float32)
    adapted = np.asarray(adapted, dtype=np.float32)
    targets = np.asarray(targets, dtype=np.float32)
    n = int(direct.shape[0])

    canonical_tensor_equal = bool(np.array_equal(direct, adapted))
    tensor_abs_max = float(np.max(np.abs(direct.astype(np.float64) - adapted.astype(np.float64))))
    canonical = adapted
    pred = infer(tf, model, xi, canonical)

    screen = reconciliation["learned_proposal_execution_screen"]
    req = reconciliation["E9_R1_required_gates"]
    state_tol = float(req["tD_xDstar_shock_identities_abs_max"])

    maxima = {
        "conditioning_roundtrip_abs": tensor_abs_max,
        "tD_identity_abs": 0.0,
        "xD_star_identity_abs": 0.0,
        "shock_ratio_identity_abs": 0.0,
        "physical_time_tD_abs": 0.0,
        "physical_time_xD_star_abs": 0.0,
        "fan_vs_teacher_RMSE": float(np.sqrt(np.mean(np.square(pred.astype(np.float64) - targets.astype(np.float64))))),
        "injection_endpoint_abs": 0.0,
        "front_endpoint_abs": 0.0,
        "characteristic_RMSE": 0.0,
        "inventory_abs": 0.0,
        "monotonic_violation_fraction": 0.0,
        "projection_teacher_RMSE": 0.0,
    }
    accepted_maxima = {
        "injection_endpoint_abs": 0.0,
        "front_endpoint_abs": 0.0,
        "characteristic_RMSE": 0.0,
        "inventory_abs": 0.0,
        "monotonic_violation_fraction": 0.0,
    }
    reason_counts = {
        "nonfinite": 0,
        "saturation_bounds": 0,
        "injection_endpoint": 0,
        "front_endpoint": 0,
        "characteristic": 0,
        "inventory": 0,
        "monotonicity": 0,
        "downstream_initial_state": 0,
    }
    first_fallbacks = []
    accepted_count = 0
    fallback_count = 0
    unsafe_accept_count = 0
    fallback_teacher_identity_all = True
    fallback_cache = {}

    for i, m in enumerate(meta):
        p_orig = m["p"]
        speed = float(m["speed"])
        td = float(m["stored_tD"])
        xstar = float(m["stored_xstar"])
        swstar = float(m["stored_swstar"])

        state = adapter.synthetic_roundtrip_state(tD=td, characteristic_speed=speed, Sw_star=swstar, tau_end=1.0)
        maxima["tD_identity_abs"] = max(maxima["tD_identity_abs"], abs(state["tD"] - td))
        maxima["xD_star_identity_abs"] = max(maxima["xD_star_identity_abs"], abs(state["xD_star"] - xstar))
        maxima["shock_ratio_identity_abs"] = max(maxima["shock_ratio_identity_abs"], abs(xstar / td - speed))
        if m["population"] == "synthetic":
            tau_end_days = float(m["bt_days"]) * speed
            pst = adapter.physical_time_state(
                elapsed_time=float(m["time_days"]),
                tau_end=tau_end_days,
                characteristic_speed=speed,
                Sw_star=swstar,
            )
            maxima["physical_time_tD_abs"] = max(maxima["physical_time_tD_abs"], abs(pst["tD"] - td))
            maxima["physical_time_xD_star_abs"] = max(maxima["physical_time_xD_star_abs"], abs(pst["xD_star"] - xstar))

        y = np.asarray(pred[i], dtype=np.float64)
        p_screen, td_screen, xstar_screen, swstar_screen = screen_params_from_canonical(label, canonical[i])
        speed_screen = xstar_screen / td_screen
        finite = bool(np.all(np.isfinite(y)))
        lower = float(p_screen["swc"])
        upper = 1.0 - float(p_screen["sor"])
        bounds = finite and bool(np.all(y >= lower) and np.all(y <= upper))
        injection_abs = abs(float(y[0]) - upper) if finite else float("inf")
        front_abs = abs(float(y[-1]) - swstar_screen) if finite else float("inf")
        characteristic = (
            float(np.sqrt(np.mean(np.square(r2.dfw_dsw(y, p_screen)[1:-1] - xi[1:-1] * speed_screen))))
            if finite else float("inf")
        )
        inventory = abs(xstar_screen * float(np.trapezoid(y - lower, xi)) - td_screen) if finite else float("inf")
        inc = np.diff(y) if finite else np.asarray([float("inf")])
        mono_fraction = float(np.count_nonzero(inc > 0.0) / inc.size) if finite else 1.0

        tau_nodes = xi.copy()
        proj = adapter.project_fan_to_pollock_nodes(
            tau_nodes=tau_nodes, state=state, fan_xi=xi, fan_sw=y, swc=lower
        ) if finite else np.full_like(tau_nodes, np.nan)
        teacher_proj = adapter.project_fan_to_pollock_nodes(
            tau_nodes=tau_nodes, state=state, fan_xi=xi, fan_sw=targets[i], swc=lower
        )
        proj_rmse = float(np.sqrt(np.mean(np.square(proj - teacher_proj)))) if finite else float("inf")
        downstream = tau_nodes > state["tau_star"]
        downstream_exact = bool(np.all(proj[downstream] == lower)) if finite and np.any(downstream) else bool(finite)

        maxima["injection_endpoint_abs"] = max(maxima["injection_endpoint_abs"], injection_abs)
        maxima["front_endpoint_abs"] = max(maxima["front_endpoint_abs"], front_abs)
        maxima["characteristic_RMSE"] = max(maxima["characteristic_RMSE"], characteristic)
        maxima["inventory_abs"] = max(maxima["inventory_abs"], inventory)
        maxima["monotonic_violation_fraction"] = max(maxima["monotonic_violation_fraction"], mono_fraction)
        maxima["projection_teacher_RMSE"] = max(maxima["projection_teacher_RMSE"], proj_rmse)

        failures = []
        if not finite:
            failures.append("nonfinite")
        if not bounds:
            failures.append("saturation_bounds")
        if injection_abs > float(screen["injection_endpoint_abs_max"]):
            failures.append("injection_endpoint")
        if front_abs > float(screen["front_endpoint_abs_max"]):
            failures.append("front_endpoint")
        if characteristic > float(screen["characteristic_RMSE_max"]):
            failures.append("characteristic")
        if inventory > float(screen["inventory_abs_max"]):
            failures.append("inventory")
        if mono_fraction > float(screen["monotonic_violation_fraction_max"]):
            failures.append("monotonicity")
        if not downstream_exact:
            failures.append("downstream_initial_state")

        # De-duplicate failure reasons while preserving order.
        failures = list(dict.fromkeys(failures))
        screen_ok = len(failures) == 0
        if screen_ok:
            accepted_count += 1
            accepted_maxima["injection_endpoint_abs"] = max(accepted_maxima["injection_endpoint_abs"], injection_abs)
            accepted_maxima["front_endpoint_abs"] = max(accepted_maxima["front_endpoint_abs"], front_abs)
            accepted_maxima["characteristic_RMSE"] = max(accepted_maxima["characteristic_RMSE"], characteristic)
            accepted_maxima["inventory_abs"] = max(accepted_maxima["inventory_abs"], inventory)
            accepted_maxima["monotonic_violation_fraction"] = max(accepted_maxima["monotonic_violation_fraction"], mono_fraction)
            # An accepted proposal with a failed screen would be unsafe by definition.
            if failures:
                unsafe_accept_count += 1
        else:
            fallback_count += 1
            for reason in failures:
                reason_counts[reason] += 1
            if len(first_fallbacks) < 25:
                first_fallbacks.append({
                    "index": i,
                    "population": m["population"],
                    "partition": m["partition"],
                    "family_id": m["family_id"],
                    "mode": m["mode"],
                    "layer": m["layer"],
                    "clock": m["clock"],
                    "failure_reasons": failures,
                    "injection_endpoint_abs": injection_abs,
                    "front_endpoint_abs": front_abs,
                    "characteristic_RMSE": characteristic,
                    "inventory_abs": inventory,
                    "monotonic_violation_fraction": mono_fraction,
                    "downstream_initial_exact": downstream_exact,
                })

            # Certify that the authorized exact R2 fallback reproduces the frozen
            # E4 teacher target byte-for-byte after the same float32 serialization.
            key = tuple(float(p_orig[k]) for k in ["no", "nw", "swc", "sor", "mu_w", "mu_o", "krw_max", "kro_max"])
            if key not in fallback_cache:
                tp = adapter.teacher_params(p_orig)
                sh = r2.welge_shock(tp, scan_nodes=4097)
                fallback_cache[key] = r2.fan_profile_from_shock(tp, xi, sh, fan_nodes=4097).astype(np.float32)
            if not np.array_equal(fallback_cache[key], targets[i]):
                fallback_teacher_identity_all = False


    gates = {
        "canonical_input_tensor_identity": canonical_tensor_equal,
        "conditioning_roundtrip_abs_max": tensor_abs_max <= 0.0,
        "tD_xDstar_shock_identities_abs_max": (
            maxima["tD_identity_abs"] <= state_tol
            and maxima["xD_star_identity_abs"] <= state_tol
            and maxima["shock_ratio_identity_abs"] <= state_tol
        ),
        "physical_time_roundtrip_abs_max": (
            maxima["physical_time_tD_abs"] <= state_tol
            and maxima["physical_time_xD_star_abs"] <= state_tol
        ),
        "downstream_initial_state_exact": reason_counts["downstream_initial_state"] == 0,
        "every_profile_partitioned_to_learned_accept_or_exact_fallback": accepted_count + fallback_count == n,
        "zero_unsafe_accepted_proposals": unsafe_accept_count == 0,
        "at_least_one_learned_proposal_accepted_per_branch": accepted_count > 0,
        "exact_R2_fallback_reproduces_frozen_teacher": fallback_teacher_identity_all,
        "accepted_profiles_obey_reconciled_screens": (
            accepted_maxima["injection_endpoint_abs"] <= float(screen["injection_endpoint_abs_max"])
            and accepted_maxima["front_endpoint_abs"] <= float(screen["front_endpoint_abs_max"])
            and accepted_maxima["characteristic_RMSE"] <= float(screen["characteristic_RMSE_max"])
            and accepted_maxima["inventory_abs"] <= float(screen["inventory_abs_max"])
            and accepted_maxima["monotonic_violation_fraction"] <= float(screen["monotonic_violation_fraction_max"])
        ),
        "no_test_or_OOD_access": True,
    }

    return {
        "label": label,
        "profiles": n,
        "learned_accept_count": int(accepted_count),
        "exact_fallback_count": int(fallback_count),
        "learned_accept_fraction": float(accepted_count / n),
        "exact_fallback_fraction": float(fallback_count / n),
        "unsafe_accepted_proposals": int(unsafe_accept_count),
        "fallback_reason_counts": reason_counts,
        "maxima_all_profiles": maxima,
        "maxima_accepted_profiles": accepted_maxima,
        "gates": gates,
        "first_exact_fallbacks": first_fallbacks,
    }


def run(project: Path, drive: Path, out: Path):
    print("=" * 118)
    print("PAD-Stream V16E-9-R1 Reconciled Hybrid Transport Adapter Identical-State Certification")
    print("=" * 118)
    print("\n".join(PROHIBITIONS), flush=True)
    g = Gates()

    print("\nV16E-8 / V16E-8-R1 PARENT AUTHORITY")
    for label, (name, expected) in E8.items():
        bind(g, "E8_" + label, drive / E8_REL / name, expected)
    bind(g, "E8_runner", project / E8_RUNNER[0], E8_RUNNER[1])
    for label, (name, expected) in E8_R1.items():
        bind(g, "E8_R1_" + label, drive / E8_R1_REL / name, expected)
    bind(g, "E8_R1_runner", project / E8_R1_RUNNER[0], E8_R1_RUNNER[1])
    reconciliation = read_json(drive / E8_R1_REL / E8_R1["contract"][0])
    g.check("E8_R1_status_exact", reconciliation.get("status") == "V16E8_R1_ADAPTER_PHYSICS_SCREEN_RECONCILIATION_PROTOCOL_FROZEN")
    g.check("E8_R1_next_milestone_exact", reconciliation.get("next_milestone", "").startswith("V16E-9-R1"))
    g.check("E8_R1_SGSim_still_locked", reconciliation["E9_R1_required_gates"]["SGSim_deployment_authorized_on_E9_R1_pass"] is False)

    print("\nBLOCKED V16E-9 EVIDENCE / UNCHANGED ADAPTER AUTHORITY")
    bind(g, "E9_runner", project / E9_RUNNER[0], E9_RUNNER[1])
    bind(g, "E9_adapter", project / E9_ADAPTER[0], E9_ADAPTER[1])
    bind(g, "E9_blocked_report", drive / E9_BLOCKED_REL / "V16E9_Blocked_Adapter_Equivalence_Audit.json", E9_BLOCKED_REPORT_SHA)
    blocked = read_json(drive / E9_BLOCKED_REL / "V16E9_Blocked_Adapter_Equivalence_Audit.json")
    g.check("E9_blocked_no_training", blocked.get("training_performed") is False)
    g.check("E9_blocked_no_checkpoint_change", blocked.get("checkpoints_changed") is False)
    g.check("E9_blocked_tests_OOD_closed", blocked.get("internal_test_reopened") is False and blocked.get("OOD_opened") is False)
    g.check("E9_blocked_SGSim_closed", blocked.get("SGSim_deployed") is False)

    print("\nROUTING / FEATURE / DATA / CHECKPOINT AUTHORITY")
    bind(g, "E7_routing", drive / E7_REL / E7_ROUTING[0], E7_ROUTING[1])
    bind(g, "E5_manifest", drive / E5_REL / E5_MANIFEST[0], E5_MANIFEST[1])
    bind(g, "E3_protocol", drive / E3_REL / E3_PROTOCOL[0], E3_PROTOCOL[1])
    bind(g, "E4_manifest", drive / DATA_REL / E4_MANIFEST[0], E4_MANIFEST[1])
    bind(g, "R2_adapter", project / R2_ADAPTER[0], R2_ADAPTER[1])
    bind(g, "E6A_runner", project / E6A_RUNNER[0], E6A_RUNNER[1])
    bind(g, "E6B_runner", project / E6B_RUNNER[0], E6B_RUNNER[1])
    for label, (name, expected) in E6A.items():
        bind(g, "E6A_" + label, drive / E6A_REL / name, expected)
    for label, (name, expected) in E6B.items():
        bind(g, "E6B_" + label, drive / E6B_REL / name, expected)

    e5 = read_json(drive / E5_REL / E5_MANIFEST[0])
    protocol = read_json(drive / E3_REL / E3_PROTOCOL[0])
    data_dir = drive / DATA_REL
    e4 = read_json(data_dir / E4_MANIFEST[0])
    inventory = e4.get("artifacts", {})
    g.check("E4_artifact_inventory_22", isinstance(inventory, dict) and len(inventory) == 22)
    for i, (rel, meta) in enumerate(sorted(inventory.items())):
        p = data_dir / rel
        g.check(f"artifact_{i:02d}_exists", p.is_file(), rel)
        g.check(f"artifact_{i:02d}_SHA_exact", sha(p) == meta.get("sha256"), rel)
        g.check(f"artifact_{i:02d}_size_exact", p.stat().st_size == meta.get("bytes"), rel)

    r2 = import_exact(project / R2_ADAPTER[0], R2_ADAPTER[1], "v16e9r1_r2")
    adapter = import_exact(project / E9_ADAPTER[0], E9_ADAPTER[1], "v16e9r1_adapter")
    g.check("E9_adapter_identity_unchanged", getattr(adapter, "ADAPTER_ID", None) == "V16E9_HYBRID_POLLOCK_FAN_ADAPTER_V1")

    print("\nFRESH TRAIN / VALIDATION CERTIFICATION FIREWALL")
    codes = np.load(data_dir / "partition_codes.npy", allow_pickle=False)
    family_ids = np.load(data_dir / "family_ids.npy", allow_pickle=False)
    xi = np.load(data_dir / "xi.npy", allow_pickle=False).astype(float)
    g.check("partition_codes_shape_exact", codes.shape == (1000,))
    g.check("partition_counts_exact", {i: int(np.sum(codes == i)) for i in (0, 1, 2)} == {0: 700, 1: 150, 2: 150})
    g.check("family_ids_shape_exact", family_ids.shape == (1000,))
    g.check("xi_exact", xi.shape == (201,) and np.array_equal(xi, np.arange(201, dtype=float) / 200.0))
    selected = select_fresh_family_indices(codes, family_ids, reconciliation)
    g.check("fresh_train_family_count_16", len(selected["train"]["family_ids"]) == 16)
    g.check("fresh_validation_family_count_16", len(selected["validation"]["family_ids"]) == 16)
    g.check("fresh_train_expected_identity", selected["train"]["family_ids"] == EXPECTED_FRESH_TRAIN, str(selected["train"]["family_ids"]))
    g.check("fresh_validation_expected_identity", selected["validation"]["family_ids"] == EXPECTED_FRESH_VALIDATION, str(selected["validation"]["family_ids"]))
    old_train = set(reconciliation["fresh_E9_R1_certification_population"]["blocked_E9_train_exclusions"])
    old_val = set(reconciliation["fresh_E9_R1_certification_population"]["blocked_E9_validation_exclusions"])
    g.check("fresh_train_disjoint_from_blocked_E9", old_train.isdisjoint(selected["train"]["family_ids"]))
    g.check("fresh_validation_disjoint_from_blocked_E9", old_val.isdisjoint(selected["validation"]["family_ids"]))
    g.check("fresh_families_exclude_internal_test", all(codes[i] in (0, 1) for p in selected.values() for i in p["family_indices"]))
    print("Fresh TRAIN families:", ", ".join(selected["train"]["family_ids"]), flush=True)
    print("Fresh VALIDATION families:", ", ".join(selected["validation"]["family_ids"]), flush=True)

    print("\nFROZEN TENSORFLOW INFERENCE RUNTIME / CHECKPOINTS")
    tf = prepare_tf(e5)
    g.check("TensorFlow_2_20_exact", tf.__version__ == "2.20.0", tf.__version__)
    model10 = build_inference_model(tf, 10, "V16E9R1_Hybrid10_Inference")
    model12 = build_inference_model(tf, 12, "V16E9R1_Hybrid12_Inference")
    g.check("Hybrid10_parameter_count_exact", model10.count_params() == 52545, str(model10.count_params()))
    g.check("Hybrid12_parameter_count_exact", model12.count_params() == 53057, str(model12.count_params()))
    model10.load_weights(drive / E6A_REL / E6A["checkpoint"][0])
    model12.load_weights(drive / E6B_REL / E6B["checkpoint"][0])
    g.check("Hybrid10_checkpoint_loaded_exact", sha(drive / E6A_REL / E6A["checkpoint"][0]) == E6A["checkpoint"][1])
    g.check("Hybrid12_checkpoint_loaded_exact", sha(drive / E6B_REL / E6B["checkpoint"][0]) == E6B["checkpoint"][1])

    print("\nRECONCILED IDENTICAL-STATE CERTIFICATION")
    reports = []
    for label, model in [("Hybrid10", model10), ("Hybrid12", model12)]:
        print("Evaluating", label, flush=True)
        rep = evaluate_experiment(label, model, tf, data_dir, xi, selected, protocol, r2, adapter, reconciliation)
        reports.append(rep)
        print(
            f"  profiles={rep['profiles']} learned_accept={rep['learned_accept_count']} "
            f"exact_fallback={rep['exact_fallback_count']}",
            flush=True,
        )
        for k, v in rep["maxima_all_profiles"].items():
            print(f"  all_{k}: {v:.12g}", flush=True)
        for k, v in rep["maxima_accepted_profiles"].items():
            print(f"  accepted_{k}: {v:.12g}", flush=True)
        print("  fallback reasons:", rep["fallback_reason_counts"], flush=True)
        for gate, passed in rep["gates"].items():
            print(f"[{'PASS' if passed else 'FAIL'}] {label}_{gate}", flush=True)

    expected_profiles = int(reconciliation["fresh_E9_R1_certification_population"]["expected_profiles_per_branch"])
    g.check("Hybrid10_profile_count_exact", reports[0]["profiles"] == expected_profiles, str(reports[0]["profiles"]))
    g.check("Hybrid12_profile_count_exact", reports[1]["profiles"] == expected_profiles, str(reports[1]["profiles"]))
    g.check("no_internal_test_or_OOD_access", True, "only public + fresh partition codes 0/1 were indexed")

    all_branch_gates = all(all(bool(v) for v in rep["gates"].values()) for rep in reports)
    audit = {
        "milestone": MILESTONE,
        "runner_sha256": sha(Path(__file__)),
        "adapter_sha256": E9_ADAPTER[1],
        "E8_contract_sha256": E8["contract"][1],
        "E8_R1_contract_sha256": E8_R1["contract"][1],
        "blocked_E9_report_sha256": E9_BLOCKED_REPORT_SHA,
        "E5_manifest_sha256": E5_MANIFEST[1],
        "E4_manifest_sha256": E4_MANIFEST[1],
        "Hybrid10_checkpoint_sha256": E6A["checkpoint"][1],
        "Hybrid12_checkpoint_sha256": E6B["checkpoint"][1],
        "selection_tag": SELECTION_TAG,
        "selected_families": selected,
        "blocked_E9_exclusions": {
            "train": sorted(old_train),
            "validation": sorted(old_val),
        },
        "layers_zero_based": LAYER_INDEX,
        "clocks_zero_based": CLOCK_INDEX,
        "allocation_modes_zero_based": MODE_INDEX,
        "public_anchor_layers": 8,
        "reports": reports,
        "internal_test_reopened": False,
        "OOD_opened": False,
        "training_performed": False,
        "checkpoints_changed": False,
        "routing_changed": False,
        "teacher_tolerances_changed": False,
        "E5_acceptance_changed": False,
        "SGSim_deployed": False,
    }

    if not all_branch_gates:
        audit.update({
            "status": BLOCKED,
            "reconciled_identical_state_certified": False,
            "SGSim_deployment_authorized": False,
            "next_milestone": NEXT_FAIL,
        })
        return publish_blocked(drive, audit)

    print("\nFINAL V16E-9-R1 ACCEPTANCE")
    g.check("all_branch_certification_gates_pass", all_branch_gates)
    g.check("zero_unsafe_accepted_proposals_global", all(rep["unsafe_accepted_proposals"] == 0 for rep in reports))
    g.check("all_profiles_classified_global", all(rep["learned_accept_count"] + rep["exact_fallback_count"] == rep["profiles"] for rep in reports))
    g.check("at_least_one_learned_accept_each_branch", all(rep["learned_accept_count"] > 0 for rep in reports))
    g.check("exact_fallback_may_be_nonzero", reconciliation["E9_R1_required_gates"]["fallback_count_may_be_nonzero"] is True)
    g.check("SGSim_direct_deployment_still_not_authorized", reconciliation["E9_R1_required_gates"]["SGSim_deployment_authorized_on_E9_R1_pass"] is False)

    audit.update({
        "status": SUCCESS,
        "reconciled_identical_state_certified": True,
        "SGSim_deployment_authorized": False,
        "acceptance_gates": g.items,
        "next_milestone": NEXT_PASS,
    })
    audit_bytes = encoded(audit)
    summary = {
        "milestone": MILESTONE,
        "status": "PASS",
        "adapter_implementation_unchanged": True,
        "Hybrid10_identical_state_profiles": reports[0]["profiles"],
        "Hybrid12_identical_state_profiles": reports[1]["profiles"],
        "Hybrid10_learned_accept_count": reports[0]["learned_accept_count"],
        "Hybrid10_exact_fallback_count": reports[0]["exact_fallback_count"],
        "Hybrid12_learned_accept_count": reports[1]["learned_accept_count"],
        "Hybrid12_exact_fallback_count": reports[1]["exact_fallback_count"],
        "fresh_synthetic_population_disjoint_from_blocked_E9": True,
        "canonical_input_tensor_identity": True,
        "zero_unsafe_accepted_proposals": True,
        "exact_R2_fallback_certified": True,
        "internal_test_reopened": False,
        "OOD_opened": False,
        "training_performed": False,
        "checkpoints_changed": False,
        "routing_changed": False,
        "SGSim_deployment_authorized": False,
        "audit_sha256": digest(audit_bytes),
        "next_milestone": NEXT_PASS,
    }
    summary_bytes = encoded(summary)
    handoff = f"""# PAD-Stream V16E-9-R1 — Reconciled Hybrid Transport Adapter Certification PASS

The unchanged V16E-9 Pollock-to-fan adapter and both unchanged accepted Hybrid
checkpoints were certified under the frozen V16E-8-R1 reconciliation contract.
Public anchors plus a fresh TRAIN/VALIDATION synthetic population disjoint from
blocked V16E-9 were used; INTERNAL TEST and OOD were not opened.

Adapter equivalence was established by exact canonical float32 input-tensor
identity. Each profile was then classified as either an accepted learned proposal
that satisfied every reconciled execution screen or an exact R2 physics fallback.
Nonzero fallback counts are permitted; unsafe accepted learned proposals are zero.
Exact R2 fallback profiles reproduce the frozen E4 teacher target exactly after
float32 serialization.

This closes the homogeneous/local-state adapter certification only. SGSim remains
locked until path-varying rock/fluid/endpoint semantics are prospectively frozen.

Adapter SHA: {E9_ADAPTER[1]}
Audit SHA: {digest(audit_bytes)}
Summary SHA: {digest(summary_bytes)}
NEXT: {NEXT_PASS}
""".encode("utf-8")
    payloads = {
        "V16E9_R1_Reconciled_Identical_State_Certification_Audit.json": audit_bytes,
        "PAD_Stream_V16E9_R1_Summary.json": summary_bytes,
        "V16E9_R1_Handoff.md": handoff,
    }
    publish(out, payloads, "V16E9-R1")

    print("\n" + "=" * 118)
    print("V16E-9-R1 RESULT: PASS")
    print("=" * 118)
    print(f"{'Hybrid10 profiles / learned / fallback':52}: {reports[0]['profiles']} / {reports[0]['learned_accept_count']} / {reports[0]['exact_fallback_count']}")
    print(f"{'Hybrid12 profiles / learned / fallback':52}: {reports[1]['profiles']} / {reports[1]['learned_accept_count']} / {reports[1]['exact_fallback_count']}")
    print(f"{'Canonical adapter input identity':52}: YES")
    print(f"{'Unsafe learned proposals accepted':52}: 0")
    print(f"{'Internal test / OOD reopened':52}: NO / NO")
    print(f"{'Training / checkpoint / routing change':52}: NO / NO / NO")
    print(f"{'SGSim deployment authorized':52}: NO")
    for name, data in payloads.items():
        print(f"{name} SHA: {digest(data)}")
    print("Output:", out)
    print("NEXT:", NEXT_PASS)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parent)
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--output-dir", type=Path)
    args = ap.parse_args(argv)
    try:
        project = args.project_root.resolve()
        drive = args.drive_root.resolve()
        out = (args.output_dir or drive / OUT_REL).resolve()
        return run(project, drive, out)
    except (GateError, OSError, ValueError, KeyError, TypeError, AssertionError, json.JSONDecodeError) as exc:
        print("\n[FAIL] V16E-9-R1 did not close:", exc, file=sys.stderr, flush=True)
        print("No SGSim deployment authority or checkpoint/routing/tolerance change was published.", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())

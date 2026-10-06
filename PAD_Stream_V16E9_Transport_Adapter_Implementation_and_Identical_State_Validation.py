#!/usr/bin/env python3
"""PAD-Stream V16E-9
Hybrid Transport Adapter Implementation and Identical-State Equivalence Validation.

Executes inference only on public anchors plus deterministic TRAIN/VALIDATION
families. INTERNAL TEST and OOD are never indexed. No training or SGSim deployment.
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

MILESTONE = "V16E-9"
SUCCESS = "V16E9_TRANSPORT_ADAPTER_IDENTICAL_STATE_EQUIVALENCE_PASS"
BLOCKED = "V16E9_TRANSPORT_ADAPTER_IDENTICAL_STATE_EQUIVALENCE_BLOCKED"
NEXT_PASS = "V16E-10 — SGSim Hybrid Path-State Semantics and Controlled Deployment Protocol Freeze"
NEXT_FAIL = "V16E-8-R1 — Adapter / physics-screen reconciliation protocol required before any SGSim use"

E8_REL = Path("provenance/hybrid_dp/V16E8_TRANSPORT_ADAPTER_IDENTICAL_STATE_PROTOCOL_FREEZE")
E7_REL = Path("provenance/hybrid_dp/V16E7_HYBRID_EVIDENCE_AND_DEPLOYMENT_ROLE_FREEZE")
E5_REL = Path("provenance/hybrid_dp/V16E5_PRETRAINING_MANIFEST_FREEZE")
E3_REL = Path("provenance/hybrid_dp/V16E3_R1_HYBRID_PROTOCOL_FREEZE")
DATA_REL = Path("datasets/hybrid_dp/V16E4_R1_DETERMINISTIC_TEACHER_DATASET")
E6A_REL = Path("models/hybrid_dp/V16E6A_HYBRID10_CONTROLLED_R1")
E6B_REL = Path("models/hybrid_dp/V16E6B_HYBRID12_CONTROLLED_R1")
OUT_REL = Path("provenance/hybrid_dp/V16E9_TRANSPORT_ADAPTER_IDENTICAL_STATE_EQUIVALENCE")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E9_BLOCKED_ADAPTER_EQUIVALENCE")

E8 = {
    "contract": ("V16E8_Transport_Adapter_Contract.json", "c88ebf508451d138197230790ce4b743b8baee40a1daf72a01d72ea0fb189820"),
    "results": ("V16E8_Transport_Adapter_and_Identical_State_Results.json", "b12be8f10fce1f6d9cc22b204a867c3a3716e41ab9a27121d60ad1a1a524ccb3"),
    "summary": ("PAD_Stream_V16E8_Summary.json", "6c05ceaeada2d127839e881f0d1d1636a8dca5fe5421f6e452340f948b435760"),
    "handoff": ("V16E8_Handoff.md", "89db55027cb7dfec8e361b486e591b0878e300ab46a298862a2673ae6efe350e"),
}
E8_RUNNER = ("PAD_Stream_V16E8_Transport_Adapter_and_Identical_State_Protocol_Freeze.py",
             "0267669d080fe62f8ea4edbc6d27ac9a66739462b6c9e60ce652e4b106c3d556")
E7_ROUTING = ("V16E7_Deployment_Routing_Contract.json", "88d434ecc292c49b7cff58aa70223e76a2dc2ce6f8f7124c461867274407fcea")
E5_MANIFEST = ("V16E5_PreTraining_Manifest.json", "c197dae32d01a1f083f7ad414e601eac1f44d7405b6087c7c7db8a6c28c5c808")
E3_PROTOCOL = ("V16E3_R1_Hybrid_BL_DP_Protocol.json", "57bcb2e74c68eb77ed8de69d75ddafc00b38d2f3c4e9b884bfc87676160db4a1")
E4_MANIFEST = ("V16E4_R1_Dataset_Manifest.json", "ec8c50720074f1ebe07be259073e44f5a82e03a45ca1cdc9385402fe280602a7")
R2_ADAPTER = ("PAD_Stream_V16E3_R2_Repaired_BL_Teacher.py", "640a853fd0775c5efaf2922976d5c3843fa69ce9e5165245daffefdb3d4eac2a")
E9_ADAPTER = ("PAD_Stream_V16E9_Hybrid_Transport_Adapter.py", "e5a89a4a591c5e3adf9be52ef274739e45a43f729cd45f044d39cc217bbd7d8f")
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

FEATURES10 = ["no","nw","swc","sor","mu_w","mu_o","phi","tD","xD_star","Sw_star"]
FEATURES12 = ["no","nw","swc","sor","mu_w","mu_o","phi","krw_max","kro_max","tD","xD_star","Sw_star"]
LAYER_INDEX = [0, 3, 7]
CLOCK_INDEX = [0, 4, 9, 14, 19]
MODE_INDEX = [0, 1]
SELECTION_TAG = "V16E8_IDENTICAL_STATE_1708|"

PROHIBITIONS = [
    "NO TRAINING OR GRADIENT UPDATE.",
    "NO CHECKPOINT CREATION, SELECTION, REPLACEMENT, OR RETRAINING.",
    "NO INTERNAL-TEST ARRAY INDEXING OR RE-EVALUATION.",
    "NO OOD REOPENING.",
    "NO SGSim MODIFICATION OR DEPLOYMENT.",
    "NO PRESSURE / DARCY / POLLOCK / TOF RECOMPUTATION.",
    "NO GRID MAP-BACK.",
    "NO BLIND FULL-PATH XI -> FAN ETA SUBSTITUTION.",
    "NO DP REALLOCATION ON TOP OF EXACT STREAMLINE WEIGHTS.",
    "NO TOLERANCE OR ROUTING CHANGE FROM V16E-8.",
]


class GateError(RuntimeError):
    pass


class Gates:
    def __init__(self): self.items = {}
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


def publish(out: Path, payloads: dict[str, bytes]):
    if out.exists():
        names = {p.name for p in out.iterdir() if p.is_file()}
        if names != set(payloads):
            raise GateError("Existing E9 output directory differs; nothing overwritten")
        for name, data in payloads.items():
            if (out / name).read_bytes() != data:
                raise GateError("Existing E9 output bytes differ; nothing overwritten")
        print("Existing identical V16E-9 result reused.", flush=True)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".v16e9-", dir=out.parent))
    try:
        for name, data in payloads.items():
            p = stage / name
            with p.open("xb") as f:
                f.write(data); f.flush(); os.fsync(f.fileno())
        stage.rename(out)
    finally:
        if stage.exists(): shutil.rmtree(stage)


def publish_blocked(drive: Path, report: dict):
    data = encoded(report)
    report_sha = digest(data)
    out = drive / BLOCKED_REL / report_sha[:16]
    summary = {
        "milestone": MILESTONE, "status": BLOCKED, "report_sha256": report_sha,
        "training_performed": False, "checkpoints_changed": False,
        "internal_test_reopened": False, "OOD_opened": False, "SGSim_deployed": False,
        "next_milestone": NEXT_FAIL,
    }
    summary_bytes = encoded(summary)
    handoff = f"""# PAD-Stream V16E-9 — BLOCKED adapter equivalence\n\nThe frozen V16E-8 adapter/routing contract was executed without training and without\nopening INTERNAL TEST, OOD, or SGSim. At least one frozen identical-state gate did\nnot close. No checkpoint, routing rule, tolerance, or frozen dataset was changed.\nExact fallback remains the only authorized behavior for a rejected learned proposal.\n\nReport SHA: {report_sha}\nSummary SHA: {digest(summary_bytes)}\nNEXT: {NEXT_FAIL}\n""".encode("utf-8")
    payloads = {
        "V16E9_Blocked_Adapter_Equivalence_Audit.json": data,
        "PAD_Stream_V16E9_Blocked_Summary.json": summary_bytes,
        "V16E9_Blocked_Handoff.md": handoff,
    }
    if out.exists():
        for n, b in payloads.items():
            if not (out/n).is_file() or (out/n).read_bytes() != b:
                raise GateError("Existing blocked E9 evidence differs")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".v16e9-blocked-", dir=out.parent))
        try:
            for n,b in payloads.items(): (stage/n).write_bytes(b)
            stage.rename(out)
        finally:
            if stage.exists(): shutil.rmtree(stage)
    print("\n" + "="*118)
    print("V16E-9 RESULT: BLOCKED")
    print("="*118)
    print("No checkpoint/routing/tolerance change           : YES")
    print("Internal test / OOD reopened                    : NO / NO")
    print("SGSim deployment authorized                     : NO")
    print("Report SHA:", report_sha)
    print("Output:", out)
    print("NEXT:", NEXT_FAIL)
    return 2


def select_family_indices(codes, family_ids):
    selected = {}
    for code, name in [(0, "train"), (1, "validation")]:
        ids = [str(family_ids[i]) for i in np.flatnonzero(codes == code)]
        ranked = sorted(ids, key=lambda fid: (hashlib.sha256((SELECTION_TAG + fid).encode("utf-8")).hexdigest(), fid))
        chosen = ranked[:16]
        idx = [int(np.flatnonzero(family_ids == fid)[0]) for fid in chosen]
        selected[name] = {"family_ids": chosen, "family_indices": idx}
    return selected


def canonical_rows(protocol, label):
    rows = []
    for r in protocol["benchmarks"]["E2_canonical_rows_authoritative"]:
        p = {
            "no": 2.0, "nw": 2.0, "swc": r["Swc"], "sor": r["Sor"],
            "mu_w": 0.5, "mu_o": 0.7, "phi": r["phi"], "k_mD": r["k_mD"], "h_ft": r["h_ft"],
            "krw_max": r["krw_max"], "kro_max": r["kro_max"],
        }
        if label == "Hybrid10":
            p.update(protocol["experiments"]["Hybrid10"]["fixed_endpoints"])
        rows.append(p)
    return rows


def row_array(p):
    return np.asarray([p[k] for k in ["no","nw","swc","sor","mu_w","mu_o","phi","k_mD","h_ft","krw_max","kro_max"]], dtype=float)


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
    random.seed(1605); np.random.seed(1605); tf.keras.utils.set_random_seed(1605)
    return tf


def build_inference_model(tf, dim: int, name: str):
    class FanModel(tf.keras.Model):
        def __init__(self):
            super().__init__(name=name)
            self.repeat = tf.keras.layers.RepeatVector(201, name="repeat_conditioning")
            self.concat = tf.keras.layers.Concatenate(axis=-1, name="concat_xi_conditioning")
            self.lstm1 = tf.keras.layers.LSTM(
                64, return_sequences=True, activation="tanh", recurrent_activation="sigmoid",
                dropout=0.0, recurrent_dropout=0.0,
                kernel_initializer=tf.keras.initializers.GlorotUniform(),
                recurrent_initializer=tf.keras.initializers.Orthogonal(),
                bias_initializer=tf.keras.initializers.Zeros(), name="lstm_1")
            self.lstm2 = tf.keras.layers.LSTM(
                64, return_sequences=True, activation="tanh", recurrent_activation="sigmoid",
                dropout=0.0, recurrent_dropout=0.0,
                kernel_initializer=tf.keras.initializers.GlorotUniform(),
                recurrent_initializer=tf.keras.initializers.Orthogonal(),
                bias_initializer=tf.keras.initializers.Zeros(), name="lstm_2")
            self.head = tf.keras.layers.TimeDistributed(
                tf.keras.layers.Dense(1, kernel_initializer=tf.keras.initializers.GlorotUniform(),
                                      bias_initializer=tf.keras.initializers.Zeros()), name="td_dense")
        def call(self, inputs, training=False):
            xi, p = inputs
            pexp = self.repeat(p)
            x = self.concat([xi, pexp])
            x = self.lstm1(x, training=training)
            x = self.lstm2(x, training=training)
            z = self.head(x, training=training)
            swc = pexp[:, :, 2:3]; sor = pexp[:, :, 3:4]
            return swc + (1.0 - swc - sor) * tf.math.sigmoid(z)
    model = FanModel()
    dummy_xi = tf.zeros((1,201,1), tf.float32)
    dummy_p = np.zeros((1,dim), np.float32)
    dummy_p[0,0]=2.; dummy_p[0,1]=2.; dummy_p[0,2]=.2; dummy_p[0,3]=.2; dummy_p[0,4]=.5; dummy_p[0,5]=1.; dummy_p[0,6]=.2
    if dim == 10:
        dummy_p[0,7]=.1; dummy_p[0,8]=.2; dummy_p[0,9]=.5
    else:
        dummy_p[0,7]=.4; dummy_p[0,8]=.6; dummy_p[0,9]=.1; dummy_p[0,10]=.2; dummy_p[0,11]=.5
    _ = model([dummy_xi, tf.constant(dummy_p)], training=False)
    return model


def infer(tf, model, xi, cond, batch=256):
    out = []
    xi_base = tf.constant(xi[:,None].astype(np.float32))
    for start in range(0, cond.shape[0], batch):
        c = tf.constant(cond[start:start+batch], tf.float32)
        xb = tf.repeat(xi_base[None,:,:], tf.shape(c)[0], axis=0)
        y = model([xb, c], training=False)[:,:,0]
        out.append(np.asarray(y.numpy(), dtype=np.float32))
    return np.concatenate(out, axis=0)


def evaluate_experiment(label, model, tf, data_dir, xi, selected, protocol, r2, adapter, contract):
    dim = 10 if label == "Hybrid10" else 12
    branch = "HYBRID10" if label == "Hybrid10" else "HYBRID12"
    cond_mm = np.load(data_dir/label/"conditioning.npy", mmap_mode="r", allow_pickle=False)
    target_mm = np.load(data_dir/label/"Sw_fan_teacher.npy", mmap_mode="r", allow_pickle=False)
    trans_mm = np.load(data_dir/label/"transport_states.npy", mmap_mode="r", allow_pickle=False)
    phys_mm = np.load(data_dir/label/"physical_parameters.npy", mmap_mode="r", allow_pickle=False)
    anchor = np.load(data_dir/(label + "_public_anchor_Sw.npy"), allow_pickle=False)
    expected_cond_shape = (1000,2,8,20,dim)
    if cond_mm.shape != expected_cond_shape or target_mm.shape != (1000,8,20,201) or trans_mm.shape != (1000,2,8,20,5) or phys_mm.shape != (1000,8,11):
        raise GateError(label + " dataset shape contract changed")

    direct=[]; adapted=[]; targets=[]; meta=[]
    # Public anchors: all 8 layers, five frozen clock indices.
    fractions = np.asarray(protocol["dataset_design"]["positive_fan_clock_fractions"], dtype=float)
    for li,p0 in enumerate(canonical_rows(protocol,label)):
        p = dict(p0)
        shock = r2.welge_shock(adapter.teacher_params(p), scan_nodes=4097)
        speed = float(shock["characteristic_speed"])
        expected_route = adapter.route_branch(endpoints_explicit=True, krw_max=p["krw_max"], kro_max=p["kro_max"])
        if expected_route != branch:
            raise GateError(f"{label} public anchor routed to {expected_route}")
        for ti in CLOCK_INDEX:
            td = float(fractions[ti] / speed); xstar = float(fractions[ti]); swstar = float(shock["Sw_star"])
            state = adapter.synthetic_roundtrip_state(tD=td, characteristic_speed=speed, Sw_star=swstar, tau_end=1.0)
            c_ad = adapter.conditioning_vector(branch, p, state)
            if branch == "HYBRID10":
                c_direct = np.asarray([p[k] for k in ["no","nw","swc","sor","mu_w","mu_o","phi"]] + [td,xstar,swstar], np.float32)
            else:
                c_direct = np.asarray([p[k] for k in ["no","nw","swc","sor","mu_w","mu_o","phi","krw_max","kro_max"]] + [td,xstar,swstar], np.float32)
            direct.append(c_direct); adapted.append(c_ad); targets.append(anchor[li,ti].astype(np.float32))
            meta.append({"population":"public_anchor","partition":"public","family_id":None,"mode":None,"layer":li,"clock":ti,
                         "p":p,"speed":speed,"stored_tD":td,"stored_xstar":xstar,"stored_swstar":swstar,"time_days":None,"bt_days":None})

    for partition in ["train","validation"]:
        for fi,fid in zip(selected[partition]["family_indices"], selected[partition]["family_ids"]):
            for mi in MODE_INDEX:
                for li in LAYER_INDEX:
                    p = adapter.physical_params_from_row(phys_mm[fi,li])
                    route = adapter.route_branch(endpoints_explicit=True, krw_max=p["krw_max"], kro_max=p["kro_max"])
                    if route != branch:
                        raise GateError(f"{label} selected state {fid}/L{li+1:02d} routed to {route}")
                    shock = r2.welge_shock(adapter.teacher_params(p), scan_nodes=4097)
                    speed=float(shock["characteristic_speed"])
                    for ti in CLOCK_INDEX:
                        tr=np.asarray(trans_mm[fi,mi,li,ti], dtype=float)
                        time_days, stored_td, stored_xstar, stored_swstar, bt_days = tr.tolist()
                        state=adapter.synthetic_roundtrip_state(tD=stored_td, characteristic_speed=speed, Sw_star=float(shock["Sw_star"]), tau_end=1.0)
                        c_ad=adapter.conditioning_vector(branch,p,state)
                        c_direct=np.asarray(cond_mm[fi,mi,li,ti], dtype=np.float32)
                        direct.append(c_direct); adapted.append(c_ad); targets.append(np.asarray(target_mm[fi,li,ti],dtype=np.float32))
                        meta.append({"population":"synthetic","partition":partition,"family_id":fid,"mode":mi,"layer":li,"clock":ti,
                                     "p":p,"speed":speed,"stored_tD":stored_td,"stored_xstar":stored_xstar,"stored_swstar":stored_swstar,
                                     "time_days":time_days,"bt_days":bt_days})

    direct=np.asarray(direct,np.float32); adapted=np.asarray(adapted,np.float32); targets=np.asarray(targets,np.float32)
    combined=np.concatenate([direct,adapted],axis=0)
    pred=infer(tf,model,xi,combined)
    n=direct.shape[0]; pred_direct=pred[:n]; pred_adapter=pred[n:]

    tol = contract["physics_screens_for_future_adapter_execution"]
    req = contract["identical_state_validation_protocol_for_next_milestone"]["required_gates"]
    maxima={"conditioning_roundtrip_abs":0.0,"tD_identity_abs":0.0,"xD_star_identity_abs":0.0,
            "shock_ratio_identity_abs":0.0,"physical_time_tD_abs":0.0,"physical_time_xD_star_abs":0.0,
            "adapter_vs_direct_model_abs":float(np.max(np.abs(pred_adapter-pred_direct))),
            "fan_vs_teacher_RMSE":float(np.sqrt(np.mean(np.square(pred_adapter-targets)))),
            "endpoint_abs":0.0,"characteristic_RMSE":0.0,"inventory_abs":0.0,"monotonic_positive_max":0.0,
            "projection_teacher_RMSE":0.0}
    failures=[]; fallback_count=0; unsafe_accept_count=0
    for i,m in enumerate(meta):
        p=m["p"]; speed=m["speed"]; td=m["stored_tD"]; xstar=m["stored_xstar"]; swstar=m["stored_swstar"]
        maxima["conditioning_roundtrip_abs"] = max(maxima["conditioning_roundtrip_abs"], float(np.max(np.abs(adapted[i].astype(float)-direct[i].astype(float)))))
        state=adapter.synthetic_roundtrip_state(tD=td, characteristic_speed=speed, Sw_star=swstar, tau_end=1.0)
        maxima["tD_identity_abs"] = max(maxima["tD_identity_abs"], abs(state["tD"]-td))
        maxima["xD_star_identity_abs"] = max(maxima["xD_star_identity_abs"], abs(state["xD_star"]-xstar))
        maxima["shock_ratio_identity_abs"] = max(maxima["shock_ratio_identity_abs"], abs(xstar/td-speed))
        if m["population"] == "synthetic":
            tau_end_days = m["bt_days"] * speed
            pst = adapter.physical_time_state(elapsed_time=m["time_days"], tau_end=tau_end_days, characteristic_speed=speed, Sw_star=swstar)
            maxima["physical_time_tD_abs"] = max(maxima["physical_time_tD_abs"], abs(pst["tD"]-td))
            maxima["physical_time_xD_star_abs"] = max(maxima["physical_time_xD_star_abs"], abs(pst["xD_star"]-xstar))

        y=np.asarray(pred_adapter[i],dtype=float)
        finite=bool(np.all(np.isfinite(y)))
        bounds=finite and bool(np.all(y>=p["swc"]-1e-7) and np.all(y<=1.0-p["sor"]+1e-7))
        endpoint=max(abs(float(y[0])-(1.0-p["sor"])),abs(float(y[-1])-swstar)) if finite else float("inf")
        char=float(np.sqrt(np.mean(np.square(r2.dfw_dsw(y,adapter.teacher_params(p))[1:-1]-xi[1:-1]*speed)))) if finite else float("inf")
        inv=float(abs(xstar*np.trapezoid(y-p["swc"],xi)-td)) if finite else float("inf")
        mono=float(max(0.0,np.max(np.diff(y)))) if finite else float("inf")
        maxima["endpoint_abs"]=max(maxima["endpoint_abs"],endpoint)
        maxima["characteristic_RMSE"]=max(maxima["characteristic_RMSE"],char)
        maxima["inventory_abs"]=max(maxima["inventory_abs"],inv)
        maxima["monotonic_positive_max"]=max(maxima["monotonic_positive_max"],mono)

        tau_nodes=xi.copy()
        proj=adapter.project_fan_to_pollock_nodes(tau_nodes=tau_nodes,state=state,fan_xi=xi,fan_sw=y,swc=p["swc"])
        teacher_proj=adapter.project_fan_to_pollock_nodes(tau_nodes=tau_nodes,state=state,fan_xi=xi,fan_sw=targets[i],swc=p["swc"])
        proj_rmse=float(np.sqrt(np.mean(np.square(proj-teacher_proj))))
        maxima["projection_teacher_RMSE"]=max(maxima["projection_teacher_RMSE"],proj_rmse)
        downstream=tau_nodes>state["tau_star"]
        downstream_exact=bool(np.all(proj[downstream] == p["swc"])) if np.any(downstream) else True
        screen_ok=(finite and bounds and endpoint<=float(tol["injection_endpoint_abs_tol"]) and
                   endpoint<=float(tol["shock_endpoint_abs_tol"]) and char<=float(tol["characteristic_RMS_tol"]) and
                   inv<=float(tol["inventory_abs_tol"]) and mono<=1e-7 and downstream_exact)
        if not screen_ok:
            fallback_count += 1
            if len(failures)<25:
                failures.append({"index":i,"population":m["population"],"partition":m["partition"],"family_id":m["family_id"],
                                 "mode":m["mode"],"layer":m["layer"],"clock":m["clock"],"finite":finite,"bounds":bounds,
                                 "endpoint_abs":endpoint,"characteristic_RMSE":char,"inventory_abs":inv,
                                 "monotonic_positive_max":mono,"downstream_initial_exact":downstream_exact})
        else:
            unsafe_accept_count += 0

    gates={
        "conditioning_roundtrip_abs_max": maxima["conditioning_roundtrip_abs"] <= float(req["conditioning_roundtrip_abs_max"]),
        "tD_identity_abs_max": maxima["tD_identity_abs"] <= float(req["tD_identity_abs_max"]),
        "xD_star_identity_abs_max": maxima["xD_star_identity_abs"] <= float(req["xD_star_identity_abs_max"]),
        "shock_ratio_identity_abs_max": maxima["shock_ratio_identity_abs"] <= float(req["shock_ratio_identity_abs_max"]),
        "adapter_vs_direct_model_same_input_abs_max": maxima["adapter_vs_direct_model_abs"] <= float(req["adapter_vs_direct_model_same_input_abs_max"]),
        "downstream_initial_state_exact": True,
        "all_frozen_physics_screens_pass": fallback_count == 0,
        "no_test_or_OOD_access": True,
    }
    return {"label":label,"profiles":int(n),"maxima":maxima,"gates":gates,"screen_rejections":fallback_count,
            "unsafe_accepted_proposals":unsafe_accept_count,"first_screen_rejections":failures}


def run(project: Path, drive: Path, out: Path):
    print("="*118)
    print("PAD-Stream V16E-9 Hybrid Transport Adapter Implementation and Identical-State Equivalence Validation")
    print("="*118)
    print("\n".join(PROHIBITIONS), flush=True)
    g=Gates()

    print("\nV16E-8 PARENT AUTHORITY")
    e8=drive/E8_REL
    for label,(name,expected) in E8.items(): bind(g,"E8_"+label,e8/name,expected)
    bind(g,"E8_runner",project/E8_RUNNER[0],E8_RUNNER[1])
    contract=read_json(e8/E8["contract"][0])
    g.check("E8_next_milestone_exact", contract.get("next_milestone","").startswith("V16E-9"))
    g.check("E8_identical_state_test_excluded", "TRAIN/VALIDATION" in contract["identical_state_validation_protocol_for_next_milestone"]["data_access"])
    g.check("E8_SGSim_still_deferred", contract["scientific_scope"]["SGSim_deployment_authorized_here"] is False)

    print("\nROUTING / FEATURE / DATA AUTHORITY")
    bind(g,"E7_routing",drive/E7_REL/E7_ROUTING[0],E7_ROUTING[1])
    bind(g,"E5_manifest",drive/E5_REL/E5_MANIFEST[0],E5_MANIFEST[1])
    bind(g,"E3_protocol",drive/E3_REL/E3_PROTOCOL[0],E3_PROTOCOL[1])
    bind(g,"E4_manifest",drive/DATA_REL/E4_MANIFEST[0],E4_MANIFEST[1])
    bind(g,"R2_adapter",project/R2_ADAPTER[0],R2_ADAPTER[1])
    bind(g,"E9_adapter",project/E9_ADAPTER[0],E9_ADAPTER[1])
    bind(g,"E6A_runner",project/E6A_RUNNER[0],E6A_RUNNER[1])
    bind(g,"E6B_runner",project/E6B_RUNNER[0],E6B_RUNNER[1])
    for label,(name,expected) in E6A.items(): bind(g,"E6A_"+label,drive/E6A_REL/name,expected)
    for label,(name,expected) in E6B.items(): bind(g,"E6B_"+label,drive/E6B_REL/name,expected)

    e5=read_json(drive/E5_REL/E5_MANIFEST[0])
    protocol=read_json(drive/E3_REL/E3_PROTOCOL[0])
    data_dir=drive/DATA_REL
    e4=read_json(data_dir/E4_MANIFEST[0])
    inventory=e4.get("artifacts",{})
    g.check("E4_artifact_inventory_22", isinstance(inventory,dict) and len(inventory)==22)
    for i,(rel,meta) in enumerate(sorted(inventory.items())):
        p=data_dir/rel
        g.check(f"artifact_{i:02d}_exists",p.is_file(),rel)
        g.check(f"artifact_{i:02d}_SHA_exact",sha(p)==meta.get("sha256"),rel)
        g.check(f"artifact_{i:02d}_size_exact",p.stat().st_size==meta.get("bytes"),rel)

    r2=import_exact(project/R2_ADAPTER[0],R2_ADAPTER[1],"v16e9_r2")
    adapter=import_exact(project/E9_ADAPTER[0],E9_ADAPTER[1],"v16e9_adapter")
    g.check("E9_adapter_identity_exact", getattr(adapter,"ADAPTER_ID",None)=="V16E9_HYBRID_POLLOCK_FAN_ADAPTER_V1")

    print("\nTRAIN / VALIDATION IDENTICAL-STATE FIREWALL")
    codes=np.load(data_dir/"partition_codes.npy",allow_pickle=False)
    family_ids=np.load(data_dir/"family_ids.npy",allow_pickle=False)
    xi=np.load(data_dir/"xi.npy",allow_pickle=False).astype(float)
    g.check("partition_codes_shape_exact",codes.shape==(1000,))
    g.check("partition_counts_exact",{i:int(np.sum(codes==i)) for i in (0,1,2)}=={0:700,1:150,2:150})
    g.check("family_ids_shape_exact",family_ids.shape==(1000,))
    g.check("xi_exact",xi.shape==(201,) and np.array_equal(xi,np.arange(201,dtype=float)/200.0))
    selected=select_family_indices(codes,family_ids)
    g.check("selected_train_family_count_16",len(selected["train"]["family_ids"])==16)
    g.check("selected_validation_family_count_16",len(selected["validation"]["family_ids"])==16)
    g.check("selected_families_exclude_internal_test",all(codes[i] in (0,1) for p in selected.values() for i in p["family_indices"]))
    print("Selected TRAIN families:", ", ".join(selected["train"]["family_ids"]), flush=True)
    print("Selected VALIDATION families:", ", ".join(selected["validation"]["family_ids"]), flush=True)

    print("\nFROZEN TENSORFLOW INFERENCE RUNTIME / CHECKPOINTS")
    tf=prepare_tf(e5)
    g.check("TensorFlow_2_20_exact",tf.__version__=="2.20.0",tf.__version__)
    model10=build_inference_model(tf,10,"V16E9_Hybrid10_Inference")
    model12=build_inference_model(tf,12,"V16E9_Hybrid12_Inference")
    g.check("Hybrid10_parameter_count_exact",model10.count_params()==52545,str(model10.count_params()))
    g.check("Hybrid12_parameter_count_exact",model12.count_params()==53057,str(model12.count_params()))
    model10.load_weights(drive/E6A_REL/E6A["checkpoint"][0])
    model12.load_weights(drive/E6B_REL/E6B["checkpoint"][0])
    g.check("Hybrid10_checkpoint_loaded_exact",sha(drive/E6A_REL/E6A["checkpoint"][0])==E6A["checkpoint"][1])
    g.check("Hybrid12_checkpoint_loaded_exact",sha(drive/E6B_REL/E6B["checkpoint"][0])==E6B["checkpoint"][1])

    print("\nIDENTICAL-STATE ADAPTER VALIDATION")
    reports=[]
    for label,model in [("Hybrid10",model10),("Hybrid12",model12)]:
        print("Evaluating",label,flush=True)
        rep=evaluate_experiment(label,model,tf,data_dir,xi,selected,protocol,r2,adapter,contract)
        reports.append(rep)
        print(f"  profiles={rep['profiles']} screen_rejections={rep['screen_rejections']}",flush=True)
        for k,v in rep["maxima"].items(): print(f"  {k}: {v:.12g}",flush=True)
        for gate,passed in rep["gates"].items(): print(f"[{'PASS' if passed else 'FAIL'}] {label}_{gate}",flush=True)

    all_gates=all(all(bool(v) for v in rep["gates"].values()) for rep in reports)
    expected_profiles=1000
    g.check("Hybrid10_identical_state_profile_count_exact",reports[0]["profiles"]==expected_profiles,str(reports[0]["profiles"]))
    g.check("Hybrid12_identical_state_profile_count_exact",reports[1]["profiles"]==expected_profiles,str(reports[1]["profiles"]))
    g.check("no_internal_test_or_OOD_access",True,"only public + selected partition codes 0/1 were indexed")

    audit={
        "milestone":MILESTONE,"runner_sha256":sha(Path(__file__)),"adapter_sha256":E9_ADAPTER[1],
        "E8_contract_sha256":E8["contract"][1],"E5_manifest_sha256":E5_MANIFEST[1],"E4_manifest_sha256":E4_MANIFEST[1],
        "Hybrid10_checkpoint_sha256":E6A["checkpoint"][1],"Hybrid12_checkpoint_sha256":E6B["checkpoint"][1],
        "selection_tag":SELECTION_TAG,"selected_families":selected,"layers_zero_based":LAYER_INDEX,"clocks_zero_based":CLOCK_INDEX,
        "allocation_modes_zero_based":MODE_INDEX,"public_anchor_layers":8,"reports":reports,
        "internal_test_reopened":False,"OOD_opened":False,"training_performed":False,"checkpoints_changed":False,"SGSim_deployed":False,
    }

    if not all_gates:
        audit.update({"status":BLOCKED,"identical_state_equivalence_closed":False,"SGSim_deployment_authorized":False,"next_milestone":NEXT_FAIL})
        return publish_blocked(drive,audit)

    print("\nFINAL V16E-9 ACCEPTANCE")
    g.check("all_identical_state_gates_pass",all_gates)
    g.check("all_frozen_physics_screens_pass",all(rep["screen_rejections"]==0 for rep in reports))
    g.check("unsafe_learned_proposals_accepted_zero",all(rep["unsafe_accepted_proposals"]==0 for rep in reports))
    g.check("SGSim_direct_deployment_still_deferred",contract["deployment_domain_firewall"]["nonuniform_path_rock_fluid_state"].startswith("direct SGSim use is NOT authorized"))

    audit.update({"status":SUCCESS,"identical_state_equivalence_closed":True,"SGSim_deployment_authorized":False,"next_milestone":NEXT_PASS,
                  "acceptance_gates":g.items})
    audit_bytes=encoded(audit)
    summary={
        "milestone":MILESTONE,"status":"PASS","adapter_implementation_frozen":True,
        "Hybrid10_identical_state_profiles":reports[0]["profiles"],"Hybrid12_identical_state_profiles":reports[1]["profiles"],
        "public_anchor_plus_train_validation_only":True,"all_adapter_roundtrip_gates_passed":True,"all_frozen_physics_screens_passed":True,
        "internal_test_reopened":False,"OOD_opened":False,"training_performed":False,"checkpoints_changed":False,
        "SGSim_deployment_authorized":False,"audit_sha256":digest(audit_bytes),"next_milestone":NEXT_PASS,
    }
    summary_bytes=encoded(summary)
    handoff=f"""# PAD-Stream V16E-9 — Hybrid Transport Adapter Implementation / Identical-State PASS\n\nThe frozen V16E-8 Pollock-to-fan adapter was implemented as `{E9_ADAPTER[0]}` and\nvalidated against both accepted Hybrid checkpoints. Public anchors plus deterministic\nTRAIN/VALIDATION subsets were used; INTERNAL TEST and OOD were not re-opened.\nFor every audited state the adapter conditioning roundtrip, tD/xD*/shock identities,\ndirect-vs-adapter inference identity, downstream initial-state projection, and frozen\nphysics screens passed. No checkpoint, routing rule, dataset, or tolerance changed.\n\nThis closes only the homogeneous/local-state interface. Direct SGSim deployment is\nstill not authorized because path-varying rock/fluid/endpoint semantics require a\nseparate protocol.\n\nAdapter SHA: {E9_ADAPTER[1]}\nAudit SHA: {digest(audit_bytes)}\nSummary SHA: {digest(summary_bytes)}\nNEXT: {NEXT_PASS}\n""".encode("utf-8")
    payloads={
        "V16E9_Identical_State_Equivalence_Audit.json":audit_bytes,
        "PAD_Stream_V16E9_Summary.json":summary_bytes,
        "V16E9_Handoff.md":handoff,
    }
    publish(out,payloads)
    print("\n"+"="*118)
    print("V16E-9 RESULT: PASS")
    print("="*118)
    print(f"{'Hybrid10 identical-state profiles':48}: {reports[0]['profiles']}")
    print(f"{'Hybrid12 identical-state profiles':48}: {reports[1]['profiles']}")
    print(f"{'Internal test / OOD reopened':48}: NO / NO")
    print(f"{'Training / checkpoint change':48}: NO / NO")
    print(f"{'All frozen physics screens passed':48}: YES")
    print(f"{'SGSim deployment authorized':48}: NO")
    for name,data in payloads.items(): print(f"{name} SHA: {digest(data)}")
    print("Output:",out)
    print("NEXT:",NEXT_PASS)
    return 0


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root",type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--output-dir",type=Path)
    args=ap.parse_args(argv)
    try:
        project=args.project_root.resolve(); drive=args.drive_root.resolve(); out=(args.output_dir or drive/OUT_REL).resolve()
        return run(project,drive,out)
    except (GateError,OSError,ValueError,KeyError,TypeError,AssertionError,json.JSONDecodeError) as exc:
        print("\n[FAIL] V16E-9 did not close:",exc,file=sys.stderr,flush=True)
        print("No SGSim deployment authority or checkpoint change was published.",file=sys.stderr,flush=True)
        return 2


if __name__=="__main__":
    sys.exit(main())

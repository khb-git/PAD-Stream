#!/usr/bin/env python3
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
from typing import Any

import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

MILESTONE = "POSTV16-AV1-D-R5D"
STATUS_PASS = (
    "AV1DR5D_ONE_TOUCH_GEOLOGY0031_FINAL_EVENT_ACCEPTANCE_PASS_"
    "PRODUCER_BALANCED_REPAIR_ACCEPTED_ON_FROZEN_INDEPENDENT_CASE"
)
STATUS_FAIL = (
    "AV1DR5D_ONE_TOUCH_GEOLOGY0031_FINAL_EVENT_ACCEPTANCE_FAIL_"
    "NO_ADAPTATION_OR_RETEST_AUTHORIZED"
)
STATUS_BLOCKED = "AV1DR5D_TECHNICAL_EXECUTION_BLOCKED_BEFORE_VALID_FINAL_DECISION"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R5CR1_COMMIT = "e79a709b1c1fdddfbbbfd65e2e4ec1e3a3585d3f"

R5CR1 = "PAD_Stream_POSTV16_AV1_D_R5C_R1_TimeMajor_Order_Dtype_Repair.py"
R5CR1_BLOB = "f2340b3a258a435833ced5c137fa2215f02dda3d"
R5BR1 = "PAD_Stream_POSTV16_AV1_D_R5B_R1_C7_Metric_Binding_ControlFlow_Repair.py"
R5BR1_BLOB = "773defe3d960cade441ce8dd098b31791747ca80"
R5A = "PAD_Stream_POSTV16_AV1_D_R5A_Producer_Labels_and_Geology0031_Sealed_Authority.py"
R5A_BLOB = "740c4862e934c2b05b2eaa63c4136110c01866e9"
R5 = "PAD_Stream_POSTV16_AV1_D_R5_Prospective_Producer_Resolved_Repair_and_Geology0031_Freeze.py"
R5_BLOB = "c5d2f64f124153b4e352f302302e0558a31c5c58"

C26 = "PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
C26_BLOB = "62e19e6b502fb3ab101a2589251c26b5f9ad9031"
B1 = "PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB = "8d9561d7c85805b82dedc26073c4633f90eeeab6"
R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7A_BLOB = "a4dd47338e7a85f130a6a70d0a41211e38c655f8"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

SOURCE_BLOBS = {
    R5CR1: R5CR1_BLOB,
    R5BR1: R5BR1_BLOB,
    R5A: R5A_BLOB,
    R5: R5_BLOB,
    C26: C26_BLOB,
    B1: B1_BLOB,
    R2: R2_BLOB,
    E37A: E37A_BLOB,
    SG7A: SG7A_BLOB,
    SG7D: SG7D_BLOB,
}

BASE = Path("post_v16") / RID / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"

R5_REL = BASE / "POSTV16_AV1_D_R5_Prospective_Producer_Resolved_Repair_and_Geology0031_Freeze"
R5_ACCEPT = "POSTV16_AV1_D_R5_Geology0031_Independent_Acceptance_Authority.json"
R5_MANIFEST = "POSTV16_AV1_D_R5_Artifact_Manifest.csv"

R5A_REL = BASE / "POSTV16_AV1_D_R5A_Producer_Labels_and_Geology0031_Sealed_Authority"
R5A_MANIFEST = "POSTV16_AV1_D_R5A_Artifact_Manifest.csv"
R5A_AUTHORITY = "POSTV16_AV1_D_R5A_Sealed_Acceptance_Authority.json"
FLOW_NAME = "POSTV16_AV1_D_R5A_Geology0031_R500_B2000_Flow.npz"
METRIC_NAME = "POSTV16_AV1_D_R5A_Geology0031_R500_B2000_201Node_C7_FaceMetric.npz"
TARGET_NAME = "POSTV16_AV1_D_R5A_Geology0031_R500_B2000_SEALED_Stage4_Target.npz"
TARGET_SHA = "cef2647c394909fb268b621a5e6074b49c3aa41a285c75082d7d976f48e62afc"

R5BR1_REL = BASE / "POSTV16_AV1_D_R5B_R1_Producer_Balanced_TrainValidation_Repair_Execution"
R5BR1_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R5B_R1_Summary.json"
R5BR1_SELECTED = "POSTV16_AV1_D_R5B_R1_Selected_Checkpoint_Contract.json"
R5BR1_MANIFEST = "POSTV16_AV1_D_R5B_R1_Artifact_Manifest.csv"
R5BR1_WEIGHTS = "POSTV16_AV1_D_R5B_R1_SELECTED_FROZEN.weights.h5"
R5BR1_STATUS = (
    "AV1DR5BR1_C7_METRIC_BINDING_CONTROLFLOW_REPAIRED_SINGLE_"
    "PRODUCER_BALANCED_TRAIN_VALIDATION_REPAIR_EXECUTED_"
    "SELECTED_CHECKPOINT_FROZEN_GEOLOGY0031_REMAINS_SEALED"
)
SELECTED_ID = "R5B_PRODUCER_BALANCED_RESPONSE"
SELECTED_SHA = "46fa4e4dc9fa3dc9f00aaa0d0270010c7dd2a2048f43f247be691c027497c709"

R5CR1_REL = BASE / "POSTV16_AV1_D_R5C_R1_Geology0031_Deployment_Conditioning_Authority"
R5CR1_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R5C_R1_Summary.json"
R5CR1_AUTHORITY = "POSTV16_AV1_D_R5C_R1_Deployment_Conditioning_Authority.json"
R5CR1_MANIFEST = "POSTV16_AV1_D_R5C_R1_Artifact_Manifest.csv"
CONDITIONING_NAME = "POSTV16_AV1_D_R5C_R1_Geology0031_C26_Deployment_Conditioning.npz"
CONDITIONING_SHA = "c1a6225f14bc90698b45d96ed848add8ec2a5820d0c67f4a1f6f55fc52690f13"
R5CR1_STATUS = (
    "AV1DR5CR1_TIME_MAJOR_ORDER_DTYPE_REPAIRED_"
    "GEOLOGY0031_C26_DEPLOYMENT_CONDITIONING_"
    "AUTHORITY_GENERATED_CERTIFIED_AND_SHA_SEALED"
)

OUT_REL = BASE / "POSTV16_AV1_D_R5D_One_Touch_Final_Geology0031_Acceptance"
BLOCKED_REL = BASE / "POSTV16_AV1_D_R5D_BLOCKED"

DAYS = np.array([30.,60.,100.,150.,250.,365.,500.,750.,1000.], dtype=np.float64)
THRESHOLD = 1.0e-4
N_STREAMLINES = 1078
N_NODES = 201
N_CVS = 200
N_TIMES = 9
N_SAMPLES = N_STREAMLINES * N_TIMES


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
        ["git","-C",str(root),*args],
        check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


def git_blob_sha(path: Path, root: Path) -> str:
    return git_text(root,"hash-object",str(path))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify_manifest(directory: Path, name: str) -> dict[str, str]:
    rows = read_csv(directory / name)
    m = {r["file"]: r["sha256"] for r in rows}
    for fn, expected in m.items():
        p = directory / fn
        if not p.is_file():
            raise GateError(f"manifest_file_missing:{fn}")
        actual = sha256_file(p)
        if actual != expected:
            raise GateError(f"manifest_SHA_mismatch:{fn}:{actual}:{expected}")
    return m


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


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


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists():
            if p.read_bytes() != data:
                raise GateError(f"existing_output_differs:{name}")
        else:
            p.write_bytes(data)


def first_breakthrough_day(cuts: np.ndarray) -> float | None:
    idx = np.flatnonzero(np.asarray(cuts, dtype=np.float64) >= THRESHOLD)
    return float(DAYS[idx[0]]) if len(idx) else None


def producer_cuts(
    sg7a: Any,
    sat200: np.ndarray,
    labels: np.ndarray,
    weights_m3_day: np.ndarray,
) -> tuple[dict[str, float], float]:
    sat = np.asarray(sat200, dtype=np.float64)
    q = np.asarray(weights_m3_day, dtype=np.float64)
    labs = np.asarray(labels).astype(str)
    ff = np.asarray(sg7a.fractional_flow(sat[:, -1]), dtype=np.float64)
    aggregate = float(np.sum(q * ff) / np.sum(q))
    by_prod: dict[str, float] = {}
    for name in sorted(np.unique(labs)):
        m = labs == name
        by_prod[str(name)] = float(np.sum(q[m] * ff[m]) / np.sum(q[m]))
    return by_prod, aggregate


def metrics(pred: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    e = np.asarray(pred, np.float64) - np.asarray(truth, np.float64)
    mse = float(np.mean(e * e))
    return {
        "rmse": float(np.sqrt(mse)),
        "mae": float(np.mean(np.abs(e))),
        "max_abs": float(np.max(np.abs(e))),
        "bias": float(np.mean(e)),
    }


def self_test() -> None:
    if first_breakthrough_day(np.array([0,0,2e-4,3e-4,0,0,0,0,0])) != 100.0:
        raise RuntimeError("first_breakthrough")
    if first_breakthrough_day(np.zeros(9)) is not None:
        raise RuntimeError("never_breakthrough")
    if SELECTED_ID != "R5B_PRODUCER_BALANCED_RESPONSE":
        raise RuntimeError("selected_id")
    if CONDITIONING_SHA != "c1a6225f14bc90698b45d96ed848add8ec2a5820d0c67f4a1f6f55fc52690f13":
        raise RuntimeError("conditioning_sha")
    print("POSTV16-AV1-D-R5D self-test: PASS")


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    target_opened = False
    inference_performed = False
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    def gate(name: str, passed: Any, value: Any = None, scientific: bool = False) -> None:
        ok = bool(passed)
        gates[name] = {
            "passed": ok,
            "value": value,
            "scientific_acceptance_gate": scientific,
        }
        suffix = f" — {value}" if value is not None else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{suffix}")
        if not ok and not scientific:
            raise GateError(name)

    print("=" * 178)
    print("POSTV16-AV1-D-R5D — ONE-TOUCH FINAL GEOLOGY0031 ACCEPTANCE")
    print("=" * 178)
    print("THE MODEL, CONDITIONING TENSOR, TARGET, THRESHOLD, AND ALL ACCEPTANCE GATES ARE FROZEN.")
    print("THIS RUN OPENS GEOLOGY0031 ONCE. NO ADAPTATION, RETUNING, THRESHOLD CHANGE,")
    print("ALTERNATE CHECKPOINT, SUPPRESSION, REPLACEMENT GEOLOGY, OR SECOND TEST IS AUTHORIZED.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()

        head = git_text(root,"rev-parse","HEAD")
        parent = git_text(root,"rev-parse","HEAD^")
        status = git_text(root,"status","--porcelain")

        gate("repository_parent_is_R5CR1_commit", parent == PARENT_R5CR1_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fn, blob in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob_sha(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == blob, actual)

        stage = "frozen_authority_binding"

        r5 = drive / R5_REL
        r5a = drive / R5A_REL
        r5b = drive / R5BR1_REL
        r5c = drive / R5CR1_REL

        for label, d in (("R5",r5),("R5A",r5a),("R5BR1",r5b),("R5CR1",r5c)):
            gate(f"{label}_output_present", d.is_dir(), str(d))

        m5 = verify_manifest(r5,R5_MANIFEST)
        m5a = verify_manifest(r5a,R5A_MANIFEST)
        m5b = verify_manifest(r5b,R5BR1_MANIFEST)
        m5c = verify_manifest(r5c,R5CR1_MANIFEST)
        gate("R5_manifest_SHA_closure",True,len(m5))
        gate("R5A_manifest_SHA_closure",True,len(m5a))
        gate("R5BR1_manifest_SHA_closure",True,len(m5b))
        gate("R5CR1_manifest_SHA_closure",True,len(m5c))

        accept = load_json(r5/R5_ACCEPT)
        a5 = load_json(r5a/R5A_AUTHORITY)
        s5b = load_json(r5b/R5BR1_SUMMARY)
        sel5b = load_json(r5b/R5BR1_SELECTED)
        s5c = load_json(r5c/R5CR1_SUMMARY)
        a5c = load_json(r5c/R5CR1_AUTHORITY)

        gate("R5_geology0031_exact",accept["geology_id"]=="0031",accept["geology_id"])
        gate("R5_seed390051_exact",int(accept["seed"])==390051,accept["seed"])
        gate(
            "R5_threshold_exact_1e4",
            float(accept["primary_event_hard_gates"]["aggregate_CO2_cut_threshold"])==THRESHOLD,
            accept["primary_event_hard_gates"]["aggregate_CO2_cut_threshold"],
        )
        one = accept["one_touch_final_evaluation"]
        gate("R5_all_1078_required",one["all_1078_streamlines"] is True)
        gate("R5_all_9_times_required",one["all_9_target_days"] is True)
        gate("R5_no_suppression",one["no_case_time_streamline_or_node_suppression"] is True)
        gate("R5_no_adaptation_after_opening",one["no_adaptation_after_opening"] is True)
        gate("R5_no_threshold_tuning_after_opening",one["no_threshold_tuning_after_opening"] is True)
        gate("R5_no_alternate_candidate_after_opening",one["no_alternate_candidate_after_opening"] is True)
        gate("R5_no_replacement_geology_after_opening",one["no_replacement_geology_or_seed_after_opening"] is True)
        gate("R5_geology0030_consumed_only",accept["geology0030_role"].startswith("consumed"))

        gate("R5A_authority_geology0031",a5["acceptance_authority"]["geology"]["id"]=="0031")
        gate("R5A_target_performance_unopened_pre_R5D",a5["acceptance_authority"]["firewall"]["model_performance_computed"] is False)

        gate("R5BR1_status_exact",s5b["status"]==R5BR1_STATUS,s5b["status"])
        gate("R5BR1_selected_candidate_exact",s5b["candidate_id"]==SELECTED_ID,s5b["candidate_id"])
        gate("R5BR1_selected_SHA_exact",s5b["selected_frozen_weights_sha256"]==SELECTED_SHA,s5b["selected_frozen_weights_sha256"])
        gate("R5BR1_target_unopened",sel5b["geology0031_target_opened"] is False)
        gate("R5BR1_no_geology0031_inference",sel5b["geology0031_model_inference"] is False)

        weights_path = r5b/R5BR1_WEIGHTS
        gate("selected_weights_present",weights_path.is_file(),str(weights_path))
        gate(
            "selected_weights_SHA_exact",
            weights_path.is_file() and sha256_file(weights_path)==SELECTED_SHA,
            sha256_file(weights_path) if weights_path.is_file() else "missing",
        )

        gate("R5CR1_status_exact",s5c["status"]==R5CR1_STATUS,s5c["status"])
        gate("R5CR1_selected_candidate_exact",s5c["selected_candidate"]==SELECTED_ID,s5c["selected_candidate"])
        gate("R5CR1_selected_SHA_exact",s5c["selected_weights_sha256"]==SELECTED_SHA,s5c["selected_weights_sha256"])
        gate("R5CR1_target_still_unopened",s5c["sealed_target_opened"] is False)
        gate("R5CR1_no_inference",s5c["model_inference_performed"] is False)
        gate("R5CR1_conditioning_SHA_exact",s5c["conditioning_artifact_sha256"]==CONDITIONING_SHA,s5c["conditioning_artifact_sha256"])
        gate("R5CR1_authority_no_target_opening",a5c["firewall"]["sealed_geology0031_target_opened"] is False)
        gate("R5CR1_authority_no_inference",a5c["firewall"]["model_inference_performed"] is False)

        conditioning_path = r5c/CONDITIONING_NAME
        gate("conditioning_file_present",conditioning_path.is_file(),str(conditioning_path))
        gate(
            "conditioning_file_SHA_exact",
            conditioning_path.is_file() and sha256_file(conditioning_path)==CONDITIONING_SHA,
            sha256_file(conditioning_path) if conditioning_path.is_file() else "missing",
        )

        target_path = r5a/TARGET_NAME
        gate("sealed_target_manifest_SHA_exact",m5a.get(TARGET_NAME)==TARGET_SHA,m5a.get(TARGET_NAME))
        gate("sealed_target_file_SHA_exact_before_opening",target_path.is_file() and sha256_file(target_path)==TARGET_SHA)

        flow_path = r5a/FLOW_NAME
        metric_path = r5a/METRIC_NAME
        gate("R5A_flow_SHA_closure",flow_path.is_file() and sha256_file(flow_path)==m5a[FLOW_NAME])
        gate("R5A_metric_SHA_closure",metric_path.is_file() and sha256_file(metric_path)==m5a[METRIC_NAME])

        stage = "load_frozen_inputs_and_model"

        with np.load(conditioning_path,allow_pickle=False) as z:
            X = np.asarray(z["X_full_C26_input"],dtype=np.float32)
            ti = np.asarray(z["time_index"],dtype=np.int64)
            si = np.asarray(z["streamline_index"],dtype=np.int64)
            cond_days = np.asarray(z["target_time_days"],dtype=np.float64)
            cond_weights = np.asarray(z["streamline_weight_m3_s"],dtype=np.float64)
            cond_selected_sha = str(np.asarray(z["selected_checkpoint_sha256"]).item())
            cond_target_sha = str(np.asarray(z["sealed_target_sha256"]).item())

        gate("conditioning_X_shape_exact",X.shape==(N_SAMPLES,N_NODES,9),X.shape)
        gate("conditioning_X_finite",np.isfinite(X).all())
        gate("conditioning_sample_axes_exact",ti.shape==(N_SAMPLES,) and si.shape==(N_SAMPLES,))
        gate("conditioning_days_exact",np.array_equal(np.unique(cond_days),DAYS),np.unique(cond_days).tolist())
        gate("conditioning_weight_shape_exact",cond_weights.shape==(N_STREAMLINES,),cond_weights.shape)
        gate("conditioning_embedded_selected_SHA_exact",cond_selected_sha==SELECTED_SHA,cond_selected_sha)
        gate("conditioning_embedded_target_SHA_exact",cond_target_sha==TARGET_SHA,cond_target_sha)

        c26 = load_module(root/C26,"postv16_r5d_c26")
        b1 = load_module(root/B1,"postv16_r5d_b1")
        r2 = load_module(root/R2,"postv16_r5d_r2")
        e37a = load_module(root/E37A,"postv16_r5d_e37a")
        sg7a = load_module(root/SG7A,"postv16_r5d_sg7a")

        import tensorflow as tf
        try:
            tf.config.experimental.enable_op_determinism()
        except Exception:
            pass
        tf.keras.utils.set_random_seed(16021)

        model = c26.model()
        gate("model_parameter_count_52033",model.count_params()==52033,model.count_params())
        model.load_weights(weights_path)

        # ONE model inference on all frozen geology0031 inputs.
        pred_flat = model.predict(X,batch_size=64,verbose=0).astype(np.float64)
        inference_performed = True

        gate("one_touch_prediction_shape_exact",pred_flat.shape==(N_SAMPLES,N_NODES),pred_flat.shape)
        gate("finite_predictions",np.isfinite(pred_flat).all(),scientific=True)
        gate(
            "saturation_bounds_0p2_0p8",
            float(np.min(pred_flat))>=0.2-1e-12 and float(np.max(pred_flat))<=0.8+1e-12,
            [float(np.min(pred_flat)),float(np.max(pred_flat))],
            scientific=True,
        )

        stage = "one_touch_open_sealed_truth"

        # FIRST AND ONLY target-array opening for final geology0031 acceptance.
        with np.load(target_path,allow_pickle=False) as z:
            truth201 = np.asarray(z["Y_transport"],dtype=np.float64)
            truth_days = np.asarray(z["target_days"],dtype=np.float64)
        target_opened = True

        gate("truth_shape_exact",truth201.shape==(N_TIMES,N_STREAMLINES,N_NODES),truth201.shape)
        gate("truth_days_exact",np.array_equal(truth_days,DAYS),truth_days.tolist())
        gate("truth_finite",np.isfinite(truth201).all())

        pred201 = np.full_like(truth201,np.nan)
        for n in range(N_SAMPLES):
            pred201[ti[n],si[n]] = pred_flat[n]

        gate("prediction_tensor_complete",np.isfinite(pred201).all())
        gate("all_1078_streamlines_used",len(np.unique(si))==N_STREAMLINES,len(np.unique(si)))
        gate("all_9_target_days_used",len(np.unique(ti))==N_TIMES,len(np.unique(ti)))

        stage = "exact_201_to_200_component_mass_projection"

        with np.load(flow_path,allow_pickle=False) as z:
            pressure_psi = np.asarray(z["pressure_psi"],dtype=np.float64)

        with np.load(metric_path,allow_pickle=False) as z:
            xyz_m = np.asarray(z["xyz_m"],dtype=np.float64)
            tau_s = np.asarray(z["pollock_tau_s"],dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"],dtype=np.float64)
            labels = np.asarray(z["producer"]).astype(str)

        gate("metric_labels_four_producers",len(np.unique(labels))==4,sorted(np.unique(labels).tolist()))
        gate("conditioning_metric_weight_identity",np.array_equal(cond_weights,weights_m3_s))

        weights_m3_day = weights_m3_s * float(e37a.DAY_TO_S)
        tof_days = tau_s / float(e37a.DAY_TO_S)

        with tempfile.TemporaryDirectory(prefix="POSTV16_AV1_R5D_SG7D_") as td:
            td = Path(td)
            sg7d_copy = td/SG7D
            sg7d_copy.write_bytes((root/SG7D).read_bytes())
            sg7d = load_module(sg7d_copy,"postv16_r5d_sg7d")

            operator = sg7d.build_subsegment_operator(xyz_m,tof_days,weights_m3_day)

            injection_pc = float(
                r2.capillary_pressure_from_incremental_sg(
                    float(r2.MAX_INCREMENTAL_CO2_SATURATION)
                )
            )
            injector_pw_pa = np.array(
                [
                    pressure_psi[k,int(r2.INJECTOR_J),int(r2.INJECTOR_I)]
                    * float(r2.PSI_TO_PA)
                    for k in r2.COMPLETION_K
                ],
                dtype=np.float64,
            )
            p_ref_gas_pa = float(np.mean(injector_pw_pa)+injection_pc)
            gate("dynamic_reference_gas_pressure_finite",np.isfinite(p_ref_gas_pa),p_ref_gas_pa)

            geometry = e37a.build_control_volume_geometry(
                r2,operator,pressure_psi,p_ref_gas_pa,N_STREAMLINES,N_CVS
            )
            coeff = np.asarray(geometry["cv_pressure_mass_coeff"],dtype=np.float64)
            gate("E37A_coeff_shape_exact",coeff.shape==(N_STREAMLINES,N_CVS),coeff.shape)
            gate("E37A_coeff_positive_finite",np.isfinite(coeff).all() and np.all(coeff>0))

            ids = np.tile(np.arange(N_STREAMLINES,dtype=np.int64),N_TIMES)

            pred200_flat,pred_mass200,pred_source_mass = b1.project_201_to_200_component_mass(
                r2,e37a,pred201.reshape(-1,N_NODES),coeff,ids
            )
            true200_flat,true_mass200,true_source_mass = b1.project_201_to_200_component_mass(
                r2,e37a,truth201.reshape(-1,N_NODES),coeff,ids
            )

        pred200 = pred200_flat.reshape(N_TIMES,N_STREAMLINES,N_CVS)
        true200 = true200_flat.reshape(N_TIMES,N_STREAMLINES,N_CVS)

        pred_den = np.maximum(np.abs(np.sum(pred_mass200,axis=1)),1.0)
        true_den = np.maximum(np.abs(np.sum(true_mass200,axis=1)),1.0)
        pred_closure = np.max(
            np.abs(np.sum(pred_mass200,axis=1)-np.sum(pred_source_mass,axis=1))/pred_den
        )
        true_closure = np.max(
            np.abs(np.sum(true_mass200,axis=1)-np.sum(true_source_mass,axis=1))/true_den
        )
        max_closure = float(max(pred_closure,true_closure))

        gate(
            "E37A_201_to_200_mass_projection_closure",
            max_closure<=1.0e-12,
            max_closure,
            scientific=True,
        )

        naive_pred = 0.5*(pred201[:,:,:-1]+pred201[:,:,1:])
        nonlinear_gap = float(np.max(np.abs(pred200-naive_pred)))
        gate(
            "no_saturation_averaging",
            nonlinear_gap>1.0e-12,
            nonlinear_gap,
            scientific=True,
        )

        stage = "frozen_event_acceptance"

        day_rows: list[dict[str,Any]] = []
        producer_rows: list[dict[str,Any]] = []
        pred_agg=[]
        truth_agg=[]
        all_aggregate_match=True
        all_producer_match=True

        for t_index,day in enumerate(DAYS):
            true_by,true_cut = producer_cuts(sg7a,true200[t_index],labels,weights_m3_day)
            pred_by,pred_cut = producer_cuts(sg7a,pred200[t_index],labels,weights_m3_day)

            truth_agg.append(true_cut)
            pred_agg.append(pred_cut)

            truth_cls=bool(true_cut>=THRESHOLD)
            pred_cls=bool(pred_cut>=THRESHOLD)
            aggregate_match=truth_cls==pred_cls
            all_aggregate_match = all_aggregate_match and aggregate_match

            day_rows.append({
                "target_day":float(day),
                "truth_aggregate_CO2_cut":true_cut,
                "prediction_aggregate_CO2_cut":pred_cut,
                "absolute_CO2_cut_error":abs(pred_cut-true_cut),
                "truth_breakthrough":truth_cls,
                "prediction_breakthrough":pred_cls,
                "classification_match":aggregate_match,
            })

            for prod in sorted(true_by):
                tc=true_by[prod]; pc=pred_by[prod]
                tcls=bool(tc>=THRESHOLD); pcls=bool(pc>=THRESHOLD)
                pmatch=tcls==pcls
                all_producer_match = all_producer_match and pmatch
                producer_rows.append({
                    "target_day":float(day),
                    "producer":prod,
                    "truth_CO2_cut":tc,
                    "prediction_CO2_cut":pc,
                    "absolute_CO2_cut_error":abs(pc-tc),
                    "truth_breakthrough":tcls,
                    "prediction_breakthrough":pcls,
                    "classification_match":pmatch,
                })

        truth_agg=np.asarray(truth_agg,dtype=np.float64)
        pred_agg=np.asarray(pred_agg,dtype=np.float64)
        true_first=first_breakthrough_day(truth_agg)
        pred_first=first_breakthrough_day(pred_agg)
        first_match=true_first==pred_first

        aggregate_mismatches=[
            (r["target_day"],r["truth_breakthrough"],r["prediction_breakthrough"])
            for r in day_rows if not r["classification_match"]
        ]
        producer_mismatches=[
            (r["target_day"],r["producer"],r["truth_breakthrough"],r["prediction_breakthrough"])
            for r in producer_rows if not r["classification_match"]
        ]

        gate(
            "aggregate_classification_match_all_9_times",
            all_aggregate_match,
            aggregate_mismatches,
            scientific=True,
        )
        gate(
            "aggregate_first_breakthrough_target_day_match",
            first_match,
            [true_first,pred_first],
            scientific=True,
        )
        gate(
            "each_producer_classification_match_all_9_times",
            all_producer_match,
            producer_mismatches,
            scientific=True,
        )

        structural_names=[
            "finite_predictions",
            "saturation_bounds_0p2_0p8",
            "E37A_201_to_200_mass_projection_closure",
            "no_saturation_averaging",
        ]
        primary_names=[
            "aggregate_classification_match_all_9_times",
            "aggregate_first_breakthrough_target_day_match",
            "each_producer_classification_match_all_9_times",
        ]
        structural_pass=all(gates[n]["passed"] for n in structural_names)
        event_pass=all(gates[n]["passed"] for n in primary_names)
        final_pass=structural_pass and event_pass

        descriptive={
            "profile_201":metrics(pred201,truth201),
            "profile_200":metrics(pred200,true200),
            "outlet_200":metrics(pred200[:,:,-1],true200[:,:,-1]),
            "aggregate_CO2_cut_MAE":float(np.mean(np.abs(pred_agg-truth_agg))),
            "aggregate_CO2_cut_max_abs":float(np.max(np.abs(pred_agg-truth_agg))),
            "component_mass_200_RMSE_kg":float(np.sqrt(np.mean((pred_mass200-true_mass200)**2))),
            "component_mass_200_MAE_kg":float(np.mean(np.abs(pred_mass200-true_mass200))),
        }

        decision_status=STATUS_PASS if final_pass else STATUS_FAIL
        decision={
            "milestone":MILESTONE,
            "status":decision_status,
            "final_acceptance_pass":bool(final_pass),
            "structural_acceptance_pass":bool(structural_pass),
            "primary_event_acceptance_pass":bool(event_pass),
            "selected_candidate":SELECTED_ID,
            "selected_weights_sha256":SELECTED_SHA,
            "conditioning_sha256":CONDITIONING_SHA,
            "sealed_target_sha256":TARGET_SHA,
            "breakthrough_threshold":THRESHOLD,
            "truth_first_breakthrough_target_day":true_first,
            "prediction_first_breakthrough_target_day":pred_first,
            "aggregate_mismatch_count":len(aggregate_mismatches),
            "producer_day_mismatch_count":len(producer_mismatches),
            "producer_day_mismatches":producer_mismatches,
            "all_1078_streamlines_used":True,
            "all_9_target_days_used":True,
            "adaptation_after_opening":False,
            "threshold_tuning_after_opening":False,
            "alternate_candidate_evaluated":False,
            "replacement_geology_or_seed_used":False,
            "second_test_attempt_authorized":False,
            "geology0030_reused":False,
            "claim_limit":accept["claim_limit"],
        }

        summary={
            **decision,
            "repository_head":head,
            "repository_parent":parent,
            "target_opened":target_opened,
            "model_inference_performed":inference_performed,
            "descriptive_metrics_not_acceptance_gates":descriptive,
        }

        files={
            "PAD_Stream_POSTV16_AV1_D_R5D_Summary.json":json_bytes(summary),
            "POSTV16_AV1_D_R5D_Final_Decision.json":json_bytes(decision),
            "POSTV16_AV1_D_R5D_Aggregate_Event_Audit.csv":csv_bytes(day_rows),
            "POSTV16_AV1_D_R5D_Producer_Event_Audit.csv":csv_bytes(producer_rows),
            "POSTV16_AV1_D_R5D_Final_Gate_Matrix.csv":csv_bytes(
                [{"gate":k,**v} for k,v in gates.items()]
            ),
        }
        immutable_publish(out,files)

        manifest_rows=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="POSTV16_AV1_D_R5D_Artifact_Manifest.csv":
                manifest_rows.append({
                    "file":p.name,
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        immutable_publish(
            out,
            {"POSTV16_AV1_D_R5D_Artifact_Manifest.csv":csv_bytes(manifest_rows)},
        )

        print("\n"+"="*178)
        print("POSTV16-AV1-D-R5D: "+("PASS" if final_pass else "FAIL"))
        print("="*178)
        print(f"{'Status':94}: {decision_status}")
        print(f"{'Selected candidate':94}: {SELECTED_ID}")
        print(f"{'Selected weights SHA256':94}: {SELECTED_SHA}")
        print(f"{'Conditioning SHA256':94}: {CONDITIONING_SHA}")
        print(f"{'Truth SHA256':94}: {TARGET_SHA}")
        print(f"{'Threshold':94}: {THRESHOLD:.1e}")
        print(f"{'Prediction min / max':94}: {float(np.min(pred_flat)):.12e} / {float(np.max(pred_flat)):.12e}")
        print(f"{'Mass projection closure max relative error':94}: {max_closure:.12e}")
        print(f"{'Aggregate classifications match all 9':94}: {all_aggregate_match}")
        print(f"{'Truth / prediction first breakthrough target day':94}: {true_first} / {pred_first}")
        print(f"{'Each producer classification matches all 9':94}: {all_producer_match}")
        print(f"{'Producer-day mismatches':94}: {producer_mismatches}")
        print(f"{'Structural acceptance':94}: {structural_pass}")
        print(f"{'Profile 201 RMSE (descriptive only)':94}: {descriptive['profile_201']['rmse']:.12e}")
        print(f"{'Profile 200 RMSE (descriptive only)':94}: {descriptive['profile_200']['rmse']:.12e}")
        print(f"{'Aggregate cut MAE (descriptive only)':94}: {descriptive['aggregate_CO2_cut_MAE']:.12e}")
        print(f"{'Target opened in this final evaluation':94}: {target_opened}")
        print(f"{'Adaptation / threshold tuning after opening':94}: False / False")
        print(f"{'Alternate candidate / replacement geology attempted':94}: False / False")
        print(f"{'Second test attempt authorized':94}: False")
        print(f"{'FINAL ACCEPTANCE':94}: {'PASS' if final_pass else 'FAIL'}")
        print("="*178)

        # Scientific FAIL is a valid final decision, not a technical runner failure.
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report={
            "milestone":MILESTONE,
            "status":STATUS_BLOCKED,
            "failed_stage":stage,
            "exception":repr(exc),
            "gates":gates,
            "target_opened":target_opened,
            "model_inference_performed":inference_performed,
            "scientific_final_decision_reached":False,
            "next_action":(
                "Audit only this technical execution failure. "
                "If the target had already been opened, do not adapt the model, "
                "threshold, checkpoint, case, seed, or suppression rules. "
                "Preserve the one-touch firewall."
            ),
        }
        data=json_bytes(report)
        p=blocked/"POSTV16_AV1_D_R5D_Blocked_Report.json"
        if p.exists() and p.read_bytes()!=data:
            p=blocked/(
                "POSTV16_AV1_D_R5D_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print("\n"+"="*178)
        print("POSTV16-AV1-D-R5D: TECHNICALLY BLOCKED")
        print("="*178)
        print("Failed stage :",stage)
        print("Exception    :",repr(exc))
        print("Target opened:",target_opened)
        print("Inference run:",inference_performed)
        print("Report       :",p)
        return 2


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path("."))
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    p.add_argument("--self-test",action="store_true")
    return p.parse_args()


if __name__=="__main__":
    a=parse_args()
    if a.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))

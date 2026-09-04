from __future__ import annotations

from pathlib import Path
import csv
import json
import os
import platform
import re
import sys
import zipfile
from datetime import datetime, timezone

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R19A
# Historical SG7B16 Inference Runtime Determinism Provenance Audit
#
# DIAGNOSTIC-ONLY RUNTIME PROVENANCE MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO MODEL.PREDICT CALL WILL BE EXECUTED.
# NO FROZEN L2 ARRAY CHANGED.
# NO GAMMA / GUARD RECALIBRATION.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO PRECISION ENVELOPE WILL BE RELAXED.
# NO CREATOR / MODEL / X100 AUTHORITY WILL BE REOPENED.
#
# PURPOSE
# -------
# R18R established the corrected historical identity result:
#
#   historical exact creator100 matches = 0
#   historical exact frozen100 matches  = 12
#
# and all 12 historical frozen100 identities reproduce the same 90-cell
# exceedance fingerprint relative to the current runtime replay.
#
# This strongly suggests the original frozen100 was produced by a historical
# inference runtime whose numerical execution differs slightly from today's
# runtime, rather than by a downstream serializer operating on today's exact
# creator100 identity.
#
# R19A audits ONLY historical runtime provenance:
#
#   - TensorFlow / Keras version evidence
#   - Python / NumPy version evidence
#   - oneDNN / CPU backend evidence
#   - deterministic-op evidence
#   - inter/intra-op and OMP/MKL threading evidence
#   - batch size and predict-call semantics
#   - .keras metadata where available
#   - historical SG7B11/SG7B16 manifests / summaries / contracts
#   - current runtime values for comparison
#
# NO inference is executed.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR19A"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE_B16 = ROOT / "PAD_Stream_V15SG7B16_Controlled_Front_Preserving_TOF_Refinement.py"
SOURCE_B11 = ROOT / "PAD_Stream_V15SG7B11_Final_Validation.py"

MODEL = ROOT / "output" / "V15_SG7B11" / "V15SG7B_FRONT_AWARE_FROZEN_Model.keras"

R18R_DIR = ROOT / "output" / "V15_SG7E1R26IR18R"
R18R_SUMMARY = R18R_DIR / "PAD_Stream_V15SG7E1R26IR18R_Summary.json"
R18R_FROZEN_LINEAGE = R18R_DIR / "V15SG7E1R26IR18R_Frozen100_Historical_Lineage.csv"

# Outputs
SOURCE_RUNTIME_TABLE = OUT / "V15SG7E1R26IR19A_Source_Runtime_Configuration_Trace.csv"
PREDICT_TABLE = OUT / "V15SG7E1R26IR19A_Predict_Call_Batch_Semantics.csv"
TEXT_META_TABLE = OUT / "V15SG7E1R26IR19A_Historical_Runtime_Metadata_Evidence.csv"
KERAS_META_TABLE = OUT / "V15SG7E1R26IR19A_Keras_Archive_Metadata.csv"
CURRENT_ENV_TABLE = OUT / "V15SG7E1R26IR19A_Current_Runtime_Environment.csv"
COMPARE_TABLE = OUT / "V15SG7E1R26IR19A_Historical_vs_Current_Runtime_Comparison.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR19A_Final_Audit_Gates.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR19A_Runtime_Determinism_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26IR19A_Runtime_Determinism_Provenance_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR19A_Summary.json"


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv(path: Path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def safe_text(path: Path):
    return path.read_text(encoding="utf-8", errors="ignore")


def source_runtime_trace(path: Path):
    rows = []
    if not path.exists():
        return rows

    text = safe_text(path)
    patterns = {
        "TF_IMPORT": r"import\s+tensorflow|from\s+tensorflow",
        "KERAS_IMPORT": r"keras",
        "BATCH_SIZE": r"\bBATCH_SIZE\b\s*=",
        "TF_DETERMINISM_ENV": r"TF_DETERMINISTIC_OPS",
        "ONEDNN_ENV": r"TF_ENABLE_ONEDNN_OPTS",
        "OMP_THREADS": r"OMP_NUM_THREADS",
        "MKL_THREADS": r"MKL_NUM_THREADS",
        "INTRA_THREADS": r"intra_op_parallelism|set_intra_op_parallelism_threads",
        "INTER_THREADS": r"inter_op_parallelism|set_inter_op_parallelism_threads",
        "ENABLE_OP_DETERMINISM": r"enable_op_determinism",
        "RANDOM_SEED": r"set_seed|random\.seed|np\.random\.seed",
        "FLOATX": r"set_floatx|floatx",
        "MIXED_PRECISION": r"mixed_precision|Policy\(",
        "LOAD_MODEL": r"load_model\(",
        "MODEL_PREDICT": r"\.predict\(",
    }

    lines = text.splitlines()
    for name, pat in patterns.items():
        rx = re.compile(pat, flags=re.IGNORECASE)
        for i, line in enumerate(lines, start=1):
            if rx.search(line):
                rows.append({
                    "source": str(path),
                    "line": i,
                    "kind": name,
                    "text": line.strip(),
                })
    return rows


def predict_semantics(path: Path):
    rows = []
    if not path.exists():
        return rows

    text = safe_text(path)
    lines = text.splitlines()

    # Collect local windows around every predict call.
    for i, line in enumerate(lines):
        if ".predict(" not in line:
            continue
        start = max(0, i - 3)
        end = min(len(lines), i + 8)
        window = "\n".join(lines[start:end])

        batch_expr = ""
        m = re.search(r"batch_size\s*=\s*([^,\n\)]+)", window)
        if m:
            batch_expr = m.group(1).strip()

        rows.append({
            "source": str(path),
            "line": i + 1,
            "batch_size_expression": batch_expr,
            "predict_context": window,
            "verbose_zero": "verbose=0" in window.replace(" ", ""),
        })

    return rows


def historical_text_files(frozen_lineage_rows):
    files = set()

    # Direct SG7B11 / SG7B16 sources and output metadata.
    for p in (SOURCE_B16, SOURCE_B11):
        if p.exists():
            files.add(p)

    for base in (
        ROOT / "output" / "V15_SG7B11",
        ROOT / "output" / "V15_SG7B16",
    ):
        if base.exists():
            for pattern in ("*.json", "*.csv", "*.txt"):
                files.update(base.rglob(pattern))

    # Include parent directories of the 12 historical exact frozen100 artifacts.
    for row in frozen_lineage_rows:
        artifact = Path(row["artifact"])
        parent = artifact.parent
        for pattern in ("*.json", "*.csv", "*.txt"):
            files.update(parent.glob(pattern))

    return sorted(p for p in files if p.exists() and p.is_file())


def extract_runtime_metadata(files):
    terms = {
        "tensorflow_version": [
            r"tensorflow[_\s-]*version",
            r'"tensorflow"\s*:',
            r"\btf_version\b",
        ],
        "keras_version": [
            r"keras[_\s-]*version",
            r'"keras"\s*:',
        ],
        "numpy_version": [
            r"numpy[_\s-]*version",
            r'"numpy"\s*:',
        ],
        "python_version": [
            r"python[_\s-]*version",
            r'"python"\s*:',
        ],
        "onednn": [
            r"oneDNN",
            r"TF_ENABLE_ONEDNN_OPTS",
        ],
        "determinism": [
            r"determin",
            r"TF_DETERMINISTIC_OPS",
            r"enable_op_determinism",
        ],
        "omp_threads": [
            r"OMP_NUM_THREADS",
        ],
        "mkl_threads": [
            r"MKL_NUM_THREADS",
        ],
        "intra_threads": [
            r"intra[_\s-]*op",
        ],
        "inter_threads": [
            r"inter[_\s-]*op",
        ],
        "batch_size": [
            r"batch[_\s-]*size",
        ],
        "device": [
            r"GPU",
            r"CPU",
            r"device",
        ],
    }

    rows = []
    for path in files:
        text = safe_text(path)
        lines = text.splitlines()

        for field, patterns in terms.items():
            regexes = [re.compile(p, flags=re.IGNORECASE) for p in patterns]
            for i, line in enumerate(lines, start=1):
                if any(rx.search(line) for rx in regexes):
                    rows.append({
                        "source": str(path),
                        "line": i,
                        "field": field,
                        "evidence": line.strip()[:1200],
                    })
    return rows


def keras_metadata(path: Path):
    rows = []
    if not path.exists():
        return rows

    # Modern .keras is usually a ZIP archive. Read metadata/config only.
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            for name in names:
                if name.endswith("metadata.json") or name.endswith("config.json"):
                    try:
                        raw = zf.read(name).decode("utf-8", errors="ignore")
                        obj = json.loads(raw)
                        flat = json.dumps(obj, ensure_ascii=False)
                        rows.append({
                            "archive": str(path),
                            "member": name,
                            "keras_version": obj.get("keras_version", "") if isinstance(obj, dict) else "",
                            "date_saved": obj.get("date_saved", "") if isinstance(obj, dict) else "",
                            "backend": obj.get("backend", "") if isinstance(obj, dict) else "",
                            "metadata_excerpt": flat[:4000],
                        })
                    except Exception as exc:
                        rows.append({
                            "archive": str(path),
                            "member": name,
                            "keras_version": "",
                            "date_saved": "",
                            "backend": "",
                            "metadata_excerpt": f"{type(exc).__name__}: {exc}",
                        })
    else:
        rows.append({
            "archive": str(path),
            "member": "",
            "keras_version": "",
            "date_saved": "",
            "backend": "",
            "metadata_excerpt": "Model is not a ZIP-format .keras archive.",
        })

    return rows


def current_runtime():
    rows = []

    tf_version = ""
    keras_version = ""
    np_version = np.__version__

    try:
        import tensorflow as tf
        tf_version = tf.__version__
        keras_version = getattr(tf.keras, "__version__", "")
    except Exception as exc:
        tf_version = f"UNAVAILABLE: {type(exc).__name__}: {exc}"

    try:
        import keras
        if not keras_version:
            keras_version = getattr(keras, "__version__", "")
    except Exception:
        pass

    row = {
        "python_version": sys.version.replace("\n", " "),
        "numpy_version": np_version,
        "tensorflow_version": tf_version,
        "keras_version": keras_version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "TF_ENABLE_ONEDNN_OPTS": os.environ.get("TF_ENABLE_ONEDNN_OPTS", ""),
        "TF_DETERMINISTIC_OPS": os.environ.get("TF_DETERMINISTIC_OPS", ""),
        "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", ""),
        "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS", ""),
        "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
    }
    rows.append(row)
    return rows


def evidence_value(rows, field):
    vals = [r["evidence"] for r in rows if r["field"] == field]
    return " | ".join(vals[:10])


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R19A")
    print("Historical SG7B16 Inference Runtime Determinism Provenance Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO PRECISION ENVELOPE WILL BE CHANGED OR RELAXED.
NO CREATOR / MODEL / X100 AUTHORITY WILL BE REOPENED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
ONLY HISTORICAL SG7B16/SG7B11 INFERENCE-RUNTIME PROVENANCE WILL BE AUDITED.
""")

    prev = load_json(R18R_SUMMARY)
    if prev.get("classification") != "HISTORICAL_FROZEN100_PERSISTS_CURRENT_CREATOR100_DOES_NOT":
        raise RuntimeError("R19A requires the corrected R18R runtime-reproducibility classification.")

    frozen_lineage = load_csv(R18R_FROZEN_LINEAGE)
    if len(frozen_lineage) != 12:
        raise RuntimeError(f"Expected 12 historical frozen100 identities, found {len(frozen_lineage)}.")

    source_rows = source_runtime_trace(SOURCE_B16) + source_runtime_trace(SOURCE_B11)
    save_csv(SOURCE_RUNTIME_TABLE, source_rows)

    predict_rows = predict_semantics(SOURCE_B16) + predict_semantics(SOURCE_B11)
    save_csv(PREDICT_TABLE, predict_rows)

    meta_files = historical_text_files(frozen_lineage)
    meta_rows = extract_runtime_metadata(meta_files)
    save_csv(TEXT_META_TABLE, meta_rows)

    keras_rows = keras_metadata(MODEL)
    save_csv(KERAS_META_TABLE, keras_rows)

    current_rows = current_runtime()
    save_csv(CURRENT_ENV_TABLE, current_rows)

    # -------------------------------------------------------------------------
    # Compare available historical evidence to current runtime.
    # We do not invent missing historical values.
    # -------------------------------------------------------------------------
    current = current_rows[0]

    historical_keras_version = ""
    historical_save_date = ""
    historical_backend = ""

    for r in keras_rows:
        if r.get("keras_version") and not historical_keras_version:
            historical_keras_version = r["keras_version"]
        if r.get("date_saved") and not historical_save_date:
            historical_save_date = r["date_saved"]
        if r.get("backend") and not historical_backend:
            historical_backend = r["backend"]

    comparison_rows = [
        {
            "field": "keras_version",
            "historical_value": historical_keras_version,
            "current_value": current.get("keras_version", ""),
            "historical_resolved": bool(historical_keras_version),
            "same": (
                historical_keras_version == current.get("keras_version", "")
                if historical_keras_version else ""
            ),
        },
        {
            "field": "tensorflow_version",
            "historical_value": evidence_value(meta_rows, "tensorflow_version"),
            "current_value": current.get("tensorflow_version", ""),
            "historical_resolved": bool(evidence_value(meta_rows, "tensorflow_version")),
            "same": "",
        },
        {
            "field": "oneDNN",
            "historical_value": evidence_value(meta_rows, "onednn"),
            "current_value": current.get("TF_ENABLE_ONEDNN_OPTS", ""),
            "historical_resolved": bool(evidence_value(meta_rows, "onednn")),
            "same": "",
        },
        {
            "field": "determinism",
            "historical_value": evidence_value(meta_rows, "determinism"),
            "current_value": current.get("TF_DETERMINISTIC_OPS", ""),
            "historical_resolved": bool(evidence_value(meta_rows, "determinism")),
            "same": "",
        },
        {
            "field": "OMP_NUM_THREADS",
            "historical_value": evidence_value(meta_rows, "omp_threads"),
            "current_value": current.get("OMP_NUM_THREADS", ""),
            "historical_resolved": bool(evidence_value(meta_rows, "omp_threads")),
            "same": "",
        },
        {
            "field": "MKL_NUM_THREADS",
            "historical_value": evidence_value(meta_rows, "mkl_threads"),
            "current_value": current.get("MKL_NUM_THREADS", ""),
            "historical_resolved": bool(evidence_value(meta_rows, "mkl_threads")),
            "same": "",
        },
        {
            "field": "saved_model_date",
            "historical_value": historical_save_date,
            "current_value": "",
            "historical_resolved": bool(historical_save_date),
            "same": "",
        },
        {
            "field": "keras_backend",
            "historical_value": historical_backend,
            "current_value": "",
            "historical_resolved": bool(historical_backend),
            "same": "",
        },
    ]
    save_csv(COMPARE_TABLE, comparison_rows)

    # Determine how much of the historical runtime is actually recoverable.
    resolved_fields = [
        r for r in comparison_rows if bool(r["historical_resolved"])
    ]

    batch_resolved = any(r.get("batch_size_expression") for r in predict_rows)
    keras_meta_resolved = bool(historical_keras_version or historical_save_date or historical_backend)

    explicit_determinism = bool(evidence_value(meta_rows, "determinism"))
    explicit_onednn = bool(evidence_value(meta_rows, "onednn"))
    explicit_threads = bool(
        evidence_value(meta_rows, "omp_threads")
        or evidence_value(meta_rows, "mkl_threads")
        or evidence_value(meta_rows, "intra_threads")
        or evidence_value(meta_rows, "inter_threads")
    )

    # If at least one historical runtime-control dimension is missing, we cannot
    # claim an exact deterministic environment yet.
    full_runtime_resolved = bool(
        batch_resolved
        and keras_meta_resolved
        and explicit_determinism
        and explicit_onednn
        and explicit_threads
    )

    if full_runtime_resolved:
        status = "HISTORICAL_SG7B16_RUNTIME_DETERMINISM_CONTRACT_RESOLVED"
        diagnosis = (
            "HISTORICAL_RUNTIME_VERSION_BACKEND_BATCH_THREAD_AND_DETERMINISM_PROVENANCE_IS_EXPLICIT"
        )
        recommendation = (
            "The historical inference-runtime contract is sufficiently explicit to support one "
            "controlled environment replay. Reproduce only those historical runtime settings with "
            "the already-frozen SG7B16 model and X100, then test frozen100 closure without changing "
            "the precision envelope."
        )
        next_ms = (
            "V15-SG7E1R26I-R19B — Historical-Environment Controlled 100-Day Replay"
        )
    else:
        status = "HISTORICAL_SG7B16_RUNTIME_DETERMINISM_PROVENANCE_INCOMPLETE"
        diagnosis = (
            "ONE_OR_MORE_HISTORICAL_RUNTIME_CONTROL_DIMENSIONS_ARE_NOT_PERSISTED_EXPLICITLY"
        )
        recommendation = (
            "Do not run an altered-environment replay yet. Audit only unresolved runtime dimensions "
            "from SG7B11/SG7B16 parent manifests, package-lock/requirements files, environment captures, "
            "and model archive metadata. Do not infer missing oneDNN/thread/determinism settings."
        )
        next_ms = (
            "V15-SG7E1R26I-R19B — Missing Historical Runtime Environment Component Audit"
        )

    gates = [
        ("R18R_runtime_reproducibility_classification_reproduced", True),
        ("12_historical_frozen100_identities_retained", len(frozen_lineage) == 12),
        ("SG7B16_source_runtime_semantics_audited", len(source_rows) > 0),
        ("predict_batch_semantics_audited", len(predict_rows) > 0),
        ("historical_metadata_sources_audited", len(meta_files) > 0),
        ("keras_archive_metadata_audited", MODEL.exists()),
        ("current_runtime_environment_recorded", True),
        ("historical_current_comparison_constructed", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_precision_relaxation", True),
        ("no_authority_reopened", True),
        ("no_later_time_state_generated", True),
    ]
    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "historical_runtime_fields_resolved": len(resolved_fields),
        "batch_semantics_resolved": batch_resolved,
        "keras_metadata_resolved": keras_meta_resolved,
        "explicit_onednn_evidence": explicit_onednn,
        "explicit_determinism_evidence": explicit_determinism,
        "explicit_thread_evidence": explicit_threads,
        "full_runtime_resolved": full_runtime_resolved,
        "failed_gates": ";".join(failed),
        "next_milestone": next_ms,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R19A",
        "status": status,
        "diagnosis": diagnosis,
        "historical_frozen100_identity_count": len(frozen_lineage),
        "authoritative_source": str(SOURCE_B16),
        "authoritative_model": str(MODEL),
        "predict_semantics": predict_rows,
        "keras_metadata": keras_rows,
        "historical_runtime_metadata_evidence_count": len(meta_rows),
        "comparison": comparison_rows,
        "runtime_resolution": {
            "batch_semantics_resolved": batch_resolved,
            "keras_metadata_resolved": keras_meta_resolved,
            "explicit_onednn_evidence": explicit_onednn,
            "explicit_determinism_evidence": explicit_determinism,
            "explicit_thread_evidence": explicit_threads,
            "full_runtime_resolved": full_runtime_resolved,
        },
        "constraints": {
            "training_performed": False,
            "model_predict_executed": False,
            "precision_envelope_relaxed": False,
            "authority_reopened": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R19A",
        "status": status,
        "diagnosis": diagnosis,
        "full_runtime_resolved": full_runtime_resolved,
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("HISTORICAL FROZEN100 LINEAGE")
    print(f"  Exact historical copies : {len(frozen_lineage)}")

    print("\nSOURCE RUNTIME SEMANTICS")
    print(f"  Runtime records          : {len(source_rows)}")
    print(f"  Predict-call records     : {len(predict_rows)}")
    print(f"  Batch semantics resolved : {batch_resolved}")

    print("\nMODEL ARCHIVE METADATA")
    print(f"  Model exists             : {MODEL.exists()}")
    print(f"  Metadata rows            : {len(keras_rows)}")
    print(f"  Historical Keras version : {historical_keras_version or 'UNRESOLVED'}")
    print(f"  Model saved date         : {historical_save_date or 'UNRESOLVED'}")
    print(f"  Backend                  : {historical_backend or 'UNRESOLVED'}")

    print("\nRUNTIME CONTROL EVIDENCE")
    print(f"  oneDNN explicit          : {explicit_onednn}")
    print(f"  Determinism explicit     : {explicit_determinism}")
    print(f"  Thread settings explicit : {explicit_threads}")
    print(f"  Full runtime resolved    : {full_runtime_resolved}")

    print("\nCURRENT RUNTIME")
    print(f"  Python                   : {current.get('python_version', '')}")
    print(f"  NumPy                    : {current.get('numpy_version', '')}")
    print(f"  TensorFlow               : {current.get('tensorflow_version', '')}")
    print(f"  Keras                    : {current.get('keras_version', '')}")
    print(f"  TF_ENABLE_ONEDNN_OPTS    : {current.get('TF_ENABLE_ONEDNN_OPTS', '') or 'UNSET'}")
    print(f"  TF_DETERMINISTIC_OPS     : {current.get('TF_DETERMINISTIC_OPS', '') or 'UNSET'}")
    print(f"  OMP_NUM_THREADS          : {current.get('OMP_NUM_THREADS', '') or 'UNSET'}")
    print(f"  MKL_NUM_THREADS          : {current.get('MKL_NUM_THREADS', '') or 'UNSET'}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R19A FINAL AUDIT GATES")
    print("=" * 78)
    for g, p in gates:
        print(f"[{'PASS' if p else 'FAIL'}] {g}")
    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")
    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")
    print("\nRECOMMENDATION")
    print(f"  {recommendation}")
    print("\nNEXT MILESTONE")
    print(f"  {next_ms}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")
    print("\nTables:")
    for p in (
        SOURCE_RUNTIME_TABLE,
        PREDICT_TABLE,
        TEXT_META_TABLE,
        KERAS_META_TABLE,
        CURRENT_ENV_TABLE,
        COMPARE_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R19A HISTORICAL RUNTIME DETERMINISM PROVENANCE AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("The precision envelope was not relaxed.")
    print("No creator/model/X100 authority was reopened.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()

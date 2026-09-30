#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import json
import math
import os
import sys

import numpy as np


# B3A-R1 is an implementation-only cross-platform source-authority repair.
# The recovered source was materialized with CRLF bytes, while Git checkout
# produced the exact LF-normalized form. Both hashes are frozen below.
# No scientific content, equations, architecture, dataset, or training rule changes.
#
MILESTONE = "V16E-1B3A-R1"
SOURCE_NAME = "pi_rnn_stage3_capillary.py"
EXPECTED_SOURCE_RAW_CRLF_SHA = "dab8eade38ac08c819ac27d803c8f1bceca9722c4c37e82977dbef6e6232ae0f"
EXPECTED_SOURCE_LF_SHA = "980dc6eb51c894bcdbc5bce277bfaa7d24d26b7aec194fa1034005888c2b1845"

REPO = Path("/content/PAD-Stream")
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")
SOURCE = REPO / SOURCE_NAME

PROV = DRIVE / "provenance" / "stage3_capillary" / "V16E1B3AR1_CROSS_PLATFORM_SOURCE_AUTHORITY_AND_PREFLIGHT"
PROV.mkdir(parents=True, exist_ok=True)

RESULTS = PROV / "V16E1B3AR1_Source_Authority_and_Physics_Preflight.json"
SUMMARY = PROV / "PAD_Stream_V16E1B3AR1_Summary.json"
HANDOFF = PROV / "V16E1B3AR1_Handoff.md"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def source_hash_modes(path: Path) -> dict:
    raw = path.read_bytes()
    lf = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")

    def _h(b: bytes) -> str:
        return hashlib.sha256(b).hexdigest()

    return {
        "raw": _h(raw),
        "lf": _h(lf),
        "crlf": _h(crlf),
    }


def gate(name: str, condition: bool):
    ok = bool(condition)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        raise RuntimeError(f"B3A preflight gate failed: {name}")


def atomic_json(path: Path, obj):
    tmp = Path(str(path) + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def import_source(path: Path):
    spec = importlib.util.spec_from_file_location("b3_source_authority", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["b3_source_authority"] = module
    spec.loader.exec_module(module)
    return module


print("=" * 110)
print("PAD-Stream V16E-1B3A-R1")
print("Stage-3 Capillary BL PI-RNN — Source Authority and Physics Preflight")
print("=" * 110)
print()
print("NO TRAINING.")
print("NO SOURCE MODIFICATION.")
print("NO B2 REPAIR.")
print("CROSS-PLATFORM HASH REPAIR ONLY: SOURCE CONTENT/SCIENCE IS UNCHANGED.")
print()

gate("source_exists", SOURCE.exists())

source_hashes = source_hash_modes(SOURCE)

source_authority_match = (
    source_hashes["raw"] in {EXPECTED_SOURCE_RAW_CRLF_SHA, EXPECTED_SOURCE_LF_SHA}
    or source_hashes["lf"] == EXPECTED_SOURCE_LF_SHA
    or source_hashes["crlf"] == EXPECTED_SOURCE_RAW_CRLF_SHA
)

gate("source_cross_platform_authority_exact", source_authority_match)

if source_hashes["raw"] == EXPECTED_SOURCE_RAW_CRLF_SHA:
    source_match_mode = "raw_CRLF"
elif source_hashes["raw"] == EXPECTED_SOURCE_LF_SHA:
    source_match_mode = "raw_LF"
elif source_hashes["lf"] == EXPECTED_SOURCE_LF_SHA:
    source_match_mode = "normalized_LF"
elif source_hashes["crlf"] == EXPECTED_SOURCE_RAW_CRLF_SHA:
    source_match_mode = "normalized_CRLF"
else:
    source_match_mode = "NO_MATCH"

print("  Source raw SHA :", source_hashes["raw"])
print("  Source LF SHA  :", source_hashes["lf"])
print("  Source CRLF SHA:", source_hashes["crlf"])
print("  Match mode     :", source_match_mode)

S = import_source(SOURCE)

print()
print("RUNTIME")
print("  TensorFlow:", S.tf.__version__)
gpus = S.tf.config.list_physical_devices("GPU")
print("  GPUs:", gpus if gpus else "None")
gate("GPU_available", len(gpus) > 0)

P = S.ProjectParams()
P.validate()
base_p = P.as_ml_dict()

print()
print("SOURCE CONTRACT")

gate("N_SEQ_64", int(S.N_SEQ) == 64)
gate("PARAM_DIM_V7_13", int(S.PARAM_DIM_V7) == 13)
gate("hidden_64", int(P.train.hidden) == 64)
gate("layers_2", int(P.train.layers) == 2)
gate("seed_1337", int(P.train.seed) == 1337)
gate("epochs_2000", int(P.train.epochs) == 2000)
gate("learning_rate_1e3", math.isclose(float(P.train.lr), 1e-3, rel_tol=0.0, abs_tol=1e-15))

gate("lambda_data_1", math.isclose(float(P.train.lambda_data), 1.0, rel_tol=0.0, abs_tol=1e-15))
gate("lambda_phys_0p10", math.isclose(float(P.train.lambda_phys), 0.10, rel_tol=0.0, abs_tol=1e-15))
gate("lambda_bc_5", math.isclose(float(P.train.lambda_bc), 5.0, rel_tol=0.0, abs_tol=1e-15))
gate("lambda_tip_5", math.isclose(float(P.train.lambda_tip), 5.0, rel_tol=0.0, abs_tol=1e-15))
gate("lambda_anchor_2", math.isclose(float(P.train.lambda_anchor), 2.0, rel_tol=0.0, abs_tol=1e-15))
gate("lambda_mono_5", math.isclose(float(P.train.lambda_mono), 5.0, rel_tol=0.0, abs_tol=1e-15))
gate("lambda_mass_20", math.isclose(float(P.train.lambda_mass), 20.0, rel_tol=0.0, abs_tol=1e-15))
gate("lambda_curv_1e6", math.isclose(float(P.train.lambda_curv), 1e-6, rel_tol=0.0, abs_tol=1e-18))
gate("lambda_shape_0p5", math.isclose(float(P.train.lambda_shape), 0.5, rel_tol=0.0, abs_tol=1e-15))
gate("phys_warmup_100", int(P.train.phys_warmup_epochs) == 100)

expected_condition_on = (
    "no", "nw", "swi", "sor",
    "mu_w", "mu_o", "phi",
    "tD", "xD_front", "Sw_star",
    "inv_Pec", "lambda_bc",
)
gate("condition_on_exact_12", tuple(P.train.condition_on) == expected_condition_on)
gate("ProjectParams_param_dim_12_as_source_written", int(P.param_dim()) == 12)

# Final source upgrades the runtime conditioning array to 13 dimensions
# by appending log10(mu_w/mu_o). This is a source-authored V7 behavior.
p12_probe = np.array([[
    2.0, 2.0, 0.2, 0.2,
    0.5, 5.0, 0.2,
    0.1, 0.2, 0.5,
    1.0/22.0, 2.0,
]], dtype=np.float32)

p13_probe = S.append_logM(p12_probe)
gate("append_logM_12_to_13", p13_probe.shape == (1, 13))
expected_logM = math.log10(0.5 / 5.0)
gate(
    "append_logM_value_exact",
    math.isclose(float(p13_probe[0, 12]), expected_logM, rel_tol=0.0, abs_tol=1e-6),
)

# The final V9 source defines the deployable interface on the native 64-node
# conditioning grid. The earlier "any x grid" Stage-3 wording is superseded
# by this later source contract.
grid = S.grid_from_conditioning(
    xD_front=0.25,
    inv_pec=1.0/22.0,
    n_points=S.N_SEQ,
)
gate("conditioning_grid_shape_64", grid.shape == (64,))
gate("conditioning_grid_finite", np.isfinite(grid).all())
gate("conditioning_grid_endpoints", abs(float(grid[0])) <= 1e-12 and abs(float(grid[-1]) - 1.0) <= 1e-6)
gate("conditioning_grid_monotone", np.all(np.diff(grid) > 0.0))

print()
print("CAPILLARY PHYSICS SMOKE TEST")
profiles = S.build_capillary_profiles(
    times_days=[100.0],
    p=base_p,
    Pe_c=22.0,
    lambda_bc=2.0,
    n_seq=S.N_SEQ,
    alpha=8.0,
)

# V4+ returns two rows per snapshot: conditioning + uniform.
gate("one_snapshot_returns_two_grid_rows", len(profiles) == 2)

for i, prof in enumerate(profiles):
    x = np.asarray(prof["x_seq"], dtype=float)
    sw = np.asarray(prof["Sw_true"], dtype=float)
    gate(f"profile_{i}_x_shape_64", x.shape == (64,))
    gate(f"profile_{i}_Sw_shape_64", sw.shape == (64,))
    gate(f"profile_{i}_finite", np.isfinite(x).all() and np.isfinite(sw).all())
    gate(f"profile_{i}_x_monotone", np.all(np.diff(x) > 0.0))
    gate(
        f"profile_{i}_saturation_bounds",
        float(sw.min()) >= float(base_p["swc"]) - 1e-6
        and
        float(sw.max()) <= 1.0 - float(base_p["sor"]) + 1e-6,
    )
    gate(f"profile_{i}_invPec_22", math.isclose(float(prof["inv_Pec"]), 1.0/22.0, rel_tol=0.0, abs_tol=1e-8))
    gate(f"profile_{i}_lambda_bc_2", math.isclose(float(prof["lambda_bc"]), 2.0, rel_tol=0.0, abs_tol=1e-12))

conditioning_profile = next(p for p in profiles if p["grid_source"] == "conditioning")

p12 = np.array([[
    base_p["no"], base_p["nw"], base_p["swc"], base_p["sor"],
    base_p["mu_w"], base_p["mu_o"], base_p["phi"],
    conditioning_profile["t_D"],
    conditioning_profile["xD_front"],
    conditioning_profile["Sw_star"],
    conditioning_profile["inv_Pec"],
    conditioning_profile["lambda_bc"],
]], dtype=np.float32)

p13 = S.append_logM(p12)
x_input = conditioning_profile["x_seq"].reshape(1, 64, 1).astype(np.float32)

print()
print("MODEL FORWARD SMOKE TEST")
model = S.build_model(
    input_features=1,
    param_dim=S.PARAM_DIM_V7,
    hidden=P.train.hidden,
    layers=P.train.layers,
)
pred = model([x_input, p13], training=False).numpy()

gate("model_output_shape_1x64x1", pred.shape == (1, 64, 1))
gate("model_output_finite", np.isfinite(pred).all())
gate(
    "model_output_range_map_bounds",
    float(pred.min()) >= float(base_p["swc"]) - 1e-6
    and
    float(pred.max()) <= 1.0 - float(base_p["sor"]) + 1e-6,
)

# Source-level execution/provenance notes. These are documented, not repaired.
source_notes = {
    "runtime_conditioning_dimension": 13,
    "condition_on_tuple_dimension": 12,
    "param_dim_method_value": int(P.param_dim()),
    "source_metadata_note_param_dim": (
        "Final V7/V9 runtime model uses p13 after append_logM, while "
        "ProjectParams.param_dim() remains 12 and the source-written config "
        "JSON therefore records 12. Reproduction will preserve source execution "
        "semantics and document this metadata mismatch rather than silently alter it."
    ),
    "TrainConfig_batch_size_declared": int(P.train.batch_size),
    "main_dataset_batch_size_actual": 4096,
    "source_metadata_note_batch_size": (
        "TrainConfig declares batch_size=16384, but final main explicitly passes "
        "batch_size=4096 to make_tf_datasets_from_arrays. Source-faithful execution "
        "uses the main-path value 4096."
    ),
    "native_interface_nodes": 64,
    "interface_note": (
        "Final V5/V9 source contract defines deployment on the native 64-node "
        "conditioning grid; dense output is obtained by interpolation."
    ),
}

results = {
    "milestone": MILESTONE,
    "source_name": SOURCE_NAME,
    "source_raw_sha256": source_hashes["raw"],
    "source_lf_sha256": source_hashes["lf"],
    "source_crlf_sha256": source_hashes["crlf"],
    "source_authority_match_mode": source_match_mode,
    "frozen_source_LF_sha256": EXPECTED_SOURCE_LF_SHA,
    "frozen_source_CRLF_sha256": EXPECTED_SOURCE_RAW_CRLF_SHA,
    "source_syntax_and_import": "PASS",
    "source_contract": {
        "stage": 3,
        "physics": "capillary pressure only",
        "Pe_c_training_values": [10.0, 22.0, 50.0, 100.0],
        "lambda_bc_training_values": [1.5, 2.0, 3.0],
        "N_SEQ": 64,
        "runtime_param_dim": 13,
        "hidden": 64,
        "layers": 2,
        "epochs": 2000,
        "seed": 1337,
        "lr": 1e-3,
    },
    "source_notes": source_notes,
    "physics_smoke_test": "PASS",
    "model_forward_smoke_test": "PASS",
    "training_performed": False,
    "B3A_source_faithful_reproduction_authorized": True,
    "next": (
        "Run the exact recovered final Stage-3 source in a persistent Drive working "
        "directory as the B3-A source-faithful reproduction. Do not reproduce V2-V8 "
        "historical branches separately."
    ),
}

atomic_json(RESULTS, results)
results_sha = sha256(RESULTS)

summary = {
    "milestone": MILESTONE,
    "source_raw_sha256": source_hashes["raw"],
    "source_lf_sha256": source_hashes["lf"],
    "source_crlf_sha256": source_hashes["crlf"],
    "source_authority_match_mode": source_match_mode,
    "results_sha256": results_sha,
    "physics_preflight_PASS": True,
    "model_forward_preflight_PASS": True,
    "training_performed": False,
    "B3A_source_faithful_reproduction_authorized": True,
    "next": results["next"],
}
atomic_json(SUMMARY, summary)
summary_sha = sha256(SUMMARY)

handoff = f"""# PAD-Stream V16E-1B3A

## Role

Stage-3 capillary BL PI-RNN source-authority binding and physics preflight.

## Frozen source

`{SOURCE_NAME}`

SHA-256:

`LF: {EXPECTED_SOURCE_LF_SHA}`\n\n`CRLF: {EXPECTED_SOURCE_RAW_CRLF_SHA}`

## Result

Physics smoke test: PASS

Model forward smoke test: PASS

Training performed: NO

B3-A source-faithful reproduction authorized: YES

## Source-execution notes

The final source uses a 13-dimensional runtime conditioning vector after
`log10(mu_w/mu_o)` is appended, while the original 12-item `condition_on`
tuple and `ProjectParams.param_dim()` remain 12. This is documented as source
metadata drift; the executable runtime path is not silently altered.

The source dataclass declares batch size 16384, while final `main` explicitly
uses 4096. Source-faithful reproduction follows the final executable main path.

The final interface is the native 64-node conditioning grid.

## Next

Run the exact final Stage-3 source as the B3-A reproduction. Historical V2-V8
iterations are not replayed as separate PAD-Stream branches.

Results SHA-256:

`{results_sha}`

Summary SHA-256:

`{summary_sha}`
"""

HANDOFF.write_text(handoff, encoding="utf-8")
handoff_sha = sha256(HANDOFF)

print()
print("=" * 110)
print("B3A PREFLIGHT RESULT")
print("=" * 110)
print("Source raw SHA                     :", source_hashes["raw"])
print("Source authority match mode        :", source_match_mode)
print("Physics smoke test                 : PASS")
print("Model forward smoke test           : PASS")
print("Training performed                 : NO")
print("B3-A reproduction authorized       : YES")
print("Results SHA                        :", results_sha)
print("Summary SHA                        :", summary_sha)
print("Handoff SHA                        :", handoff_sha)
print()
print("NEXT: exact source-faithful Stage-3 capillary reproduction; no replay of historical V2-V8 branches.")

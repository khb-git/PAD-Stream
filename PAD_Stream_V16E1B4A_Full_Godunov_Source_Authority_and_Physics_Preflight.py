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

MILESTONE = "V16E-1B4A"

REPO = Path("/content/PAD-Stream")
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")

SOURCE = REPO / "pi_rnn_stage4_full_godunov.py"

EXPECTED_SOURCE_RAW_SHA = "165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"
EXPECTED_SOURCE_LF_SHA = "165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"
EXPECTED_SOURCE_CRLF_SHA = "1788a35e45ac5f4b7f4a0558175f08bd698b7c82575f5386f474e3a55c8aabb8"

B3B_ROOT = (
    DRIVE
    / "provenance"
    / "stage3_capillary"
    / "V16E1B3B_REPRODUCTION_FREEZE"
)

B3B_RESULTS = B3B_ROOT / "V16E1B3B_Capillary_Reproduction_Results.json"
B3B_SUMMARY = B3B_ROOT / "PAD_Stream_V16E1B3B_Summary.json"
B3B_HANDOFF = B3B_ROOT / "V16E1B3B_Handoff.md"

EXPECTED_B3B_RESULTS_SHA = "a524f3ed4cf4302160fa24e58cf0de6d9afc8185b1563c73b94dff749e67f89b"
EXPECTED_B3B_SUMMARY_SHA = "46a1870ff5a26f51c931f072dc7aff9057dff4853f4f08555f0a851eb7ea4df3"
EXPECTED_B3B_HANDOFF_SHA = "a85a7b8fea671939172406f649447289a84e1c7f7bae2edc34e8891d82f33c0c"

PROV = (
    DRIVE
    / "provenance"
    / "stage4_full"
    / "V16E1B4A_SOURCE_AUTHORITY_AND_PHYSICS_PREFLIGHT"
)

PROV.mkdir(
    parents=True,
    exist_ok=True,
)

RESULTS = PROV / "V16E1B4A_Source_Authority_and_Physics_Preflight.json"
SUMMARY = PROV / "PAD_Stream_V16E1B4A_Summary.json"
HANDOFF = PROV / "V16E1B4A_Handoff.md"


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

    return {
        "raw": hashlib.sha256(raw).hexdigest(),
        "lf": hashlib.sha256(lf).hexdigest(),
        "crlf": hashlib.sha256(crlf).hexdigest(),
    }


def gate(name, condition):
    ok = bool(condition)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        raise RuntimeError(
            f"B4A preflight gate failed: {name}"
        )


def atomic_json(path: Path, obj):
    tmp = Path(str(path) + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(
            obj,
            f,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def import_source(path: Path):
    spec = importlib.util.spec_from_file_location(
        "b4_full_source_authority",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["b4_full_source_authority"] = module
    spec.loader.exec_module(module)
    return module


print("=" * 110)
print("PAD-Stream V16E-1B4A")
print("Full Buckley-Leverett Godunov PI-RNN — Source Authority and Physics Preflight")
print("=" * 110)

print()
print("NO TRAINING.")
print("NO SOURCE MODIFICATION.")
print("NO B2 OR B3 REPAIR.")
print("B4 BINDS THE RECOVERED FINAL FULL-PHYSICS GODUNOV SOURCE.")
print()


# =============================================================================
# B3 -> B4 forward authority
# =============================================================================

print("B3B FORWARD-TRANSITION AUTHORITY")

for name, path, expected in (
    ("B3B_RESULTS", B3B_RESULTS, EXPECTED_B3B_RESULTS_SHA),
    ("B3B_SUMMARY", B3B_SUMMARY, EXPECTED_B3B_SUMMARY_SHA),
    ("B3B_HANDOFF", B3B_HANDOFF, EXPECTED_B3B_HANDOFF_SHA),
):
    gate(f"{name}_exists", path.exists())
    gate(f"{name}_SHA_exact", sha256(path) == expected)

b3b_summary = json.loads(
    B3B_SUMMARY.read_text(
        encoding="utf-8"
    )
)

gate(
    "B3B_reproduction_complete",
    b3b_summary[
        "reproduction_complete"
    ]
    is True,
)

gate(
    "B3B_frozen_for_forward_progress",
    b3b_summary[
        "B3_frozen_for_forward_progress"
    ]
    is True,
)

gate(
    "B3B_B4_authorized",
    b3b_summary[
        "B4_authorized"
    ]
    is True,
)


# =============================================================================
# Source authority
# =============================================================================

print()
print("B4 SOURCE AUTHORITY")

gate(
    "source_exists",
    SOURCE.exists(),
)

hashes = source_hash_modes(
    SOURCE
)

source_authority_match = (
    hashes["raw"]
    in {
        EXPECTED_SOURCE_RAW_SHA,
        EXPECTED_SOURCE_LF_SHA,
        EXPECTED_SOURCE_CRLF_SHA,
    }
    or hashes["lf"] == EXPECTED_SOURCE_LF_SHA
    or hashes["crlf"] == EXPECTED_SOURCE_CRLF_SHA
)

gate(
    "source_cross_platform_authority_exact",
    source_authority_match,
)

if hashes["raw"] == EXPECTED_SOURCE_RAW_SHA:
    match_mode = "raw_materialized"
elif hashes["raw"] == EXPECTED_SOURCE_LF_SHA:
    match_mode = "raw_LF"
elif hashes["raw"] == EXPECTED_SOURCE_CRLF_SHA:
    match_mode = "raw_CRLF"
elif hashes["lf"] == EXPECTED_SOURCE_LF_SHA:
    match_mode = "normalized_LF"
elif hashes["crlf"] == EXPECTED_SOURCE_CRLF_SHA:
    match_mode = "normalized_CRLF"
else:
    match_mode = "NO_MATCH"

print("  Source raw SHA :", hashes["raw"])
print("  Source LF SHA  :", hashes["lf"])
print("  Source CRLF SHA:", hashes["crlf"])
print("  Match mode     :", match_mode)


S = import_source(
    SOURCE
)


# =============================================================================
# Runtime
# =============================================================================

print()
print("RUNTIME")

print(
    "  TensorFlow:",
    S.tf.__version__,
)

gpus = S.tf.config.list_physical_devices(
    "GPU"
)

print(
    "  GPUs:",
    gpus if gpus else "None",
)

gate(
    "GPU_available",
    len(gpus) > 0,
)


# =============================================================================
# Source contract
# =============================================================================

P = S.ProjectParams()
P.validate()
base_p = P.as_ml_dict()

print()
print("FULL-PHYSICS SOURCE CONTRACT")

gate(
    "PARAM_DIM_S4_14",
    int(S.PARAM_DIM_S4) == 14,
)

gate(
    "N_SEQ_64",
    int(S.N_SEQ) == 64,
)

gate(
    "CONSERVATIVE_FORM_true",
    S.CONSERVATIVE_FORM is True,
)

gate(
    "hidden_64",
    int(P.train.hidden) == 64,
)

gate(
    "layers_2",
    int(P.train.layers) == 2,
)

gate(
    "seed_1337",
    int(P.train.seed) == 1337,
)

gate(
    "epochs_1000",
    int(P.train.epochs) == 1000,
)

gate(
    "learning_rate_1e3",
    math.isclose(
        float(P.train.lr),
        1.0e-3,
        rel_tol=0.0,
        abs_tol=1.0e-15,
    ),
)

gate(
    "lambda_data_1",
    math.isclose(
        float(P.train.lambda_data),
        1.0,
        rel_tol=0.0,
        abs_tol=1.0e-15,
    ),
)

gate(
    "lambda_phys_0p10",
    math.isclose(
        float(P.train.lambda_phys),
        0.10,
        rel_tol=0.0,
        abs_tol=1.0e-15,
    ),
)

gate(
    "lambda_bc_5",
    math.isclose(
        float(P.train.lambda_bc),
        5.0,
        rel_tol=0.0,
        abs_tol=1.0e-15,
    ),
)

gate(
    "lambda_tip_5",
    math.isclose(
        float(P.train.lambda_tip),
        5.0,
        rel_tol=0.0,
        abs_tol=1.0e-15,
    ),
)

gate(
    "lambda_anchor_2",
    math.isclose(
        float(P.train.lambda_anchor),
        2.0,
        rel_tol=0.0,
        abs_tol=1.0e-15,
    ),
)

gate(
    "lambda_mono_5",
    math.isclose(
        float(P.train.lambda_mono),
        5.0,
        rel_tol=0.0,
        abs_tol=1.0e-15,
    ),
)

gate(
    "lambda_mass_20",
    math.isclose(
        float(P.train.lambda_mass),
        20.0,
        rel_tol=0.0,
        abs_tol=1.0e-15,
    ),
)

gate(
    "lambda_curv_1e6",
    math.isclose(
        float(P.train.lambda_curv),
        1.0e-6,
        rel_tol=0.0,
        abs_tol=1.0e-18,
    ),
)

gate(
    "lambda_shape_0p5",
    math.isclose(
        float(P.train.lambda_shape),
        0.5,
        rel_tol=0.0,
        abs_tol=1.0e-15,
    ),
)

gate(
    "phys_warmup_100",
    int(P.train.phys_warmup_epochs) == 100,
)


# Source metadata carries forward Stage-3's 12-item tuple while B4 executable
# arrays carry 13 raw values + appended logM = 14. Document, do not alter.
expected_condition_on = (
    "no", "nw", "swi", "sor",
    "mu_w", "mu_o", "phi",
    "tD", "xD_front", "Sw_star",
    "inv_Pec", "lambda_bc",
)

gate(
    "condition_on_source_tuple_12",
    tuple(P.train.condition_on)
    ==
    expected_condition_on,
)

gate(
    "ProjectParams_param_dim_source_metadata_12",
    int(P.param_dim()) == 12,
)


# =============================================================================
# Stage nesting / compressible transform tests
# =============================================================================

print()
print("STAGE-4 TRANSFORM AND NESTING TESTS")

gate(
    "Y_L_Nc0_exact_1",
    math.isclose(
        float(S.Y_L(0.0)),
        1.0,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    ),
)

y005 = float(
    S.Y_L(0.05)
)

y01 = float(
    S.Y_L(0.10)
)

y02 = float(
    S.Y_L(0.20)
)

gate(
    "Y_L_positive_finite",
    all(
        math.isfinite(v)
        for v in (
            y005,
            y01,
            y02,
        )
    ),
)

gate(
    "Y_L_breakthrough_earlier_for_positive_Nc",
    0.0 < y02 < y01 < y005 < 1.0,
)


# Compute a Stage-1/3 front slope using the source's own physics.
sw_grid = np.linspace(
    base_p["swc"],
    1.0 - base_p["sor"],
    800,
)

_, fw = S.dfw_dsw_np(
    sw_grid,
    base_p,
)

Sw_star, _, slope_star, _ = S.welge_tangent(
    sw_grid,
    fw,
    base_p["swc"],
)

tD_probe = 0.10

xf0 = float(
    S.xfront_from_tD(
        tD_probe,
        slope_star,
        0.0,
    )
)

xf01 = float(
    S.xfront_from_tD(
        tD_probe,
        slope_star,
        0.10,
    )
)

expected_xf0 = min(
    1.0,
    tD_probe * slope_star,
)

gate(
    "Nc0_front_nests_hyperbolic_limit",
    math.isclose(
        xf0,
        expected_xf0,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    ),
)

gate(
    "positive_Nc_front_transform_finite",
    math.isfinite(
        xf01
    )
    and
    0.0 <= xf01 <= 1.0,
)


# =============================================================================
# Full solver physics smoke tests
# =============================================================================

print()
print("FULL SOLVER PHYSICS SMOKE TEST")

times = [
    100.0
]

profiles_nc0 = S.build_capillary_profiles(
    times_days=times,
    p=base_p,
    Pe_c=22.0,
    lambda_bc=2.0,
    nc=0.0,
    n_seq=S.N_SEQ,
    alpha=8.0,
)

profiles_nc01 = S.build_capillary_profiles(
    times_days=times,
    p=base_p,
    Pe_c=22.0,
    lambda_bc=2.0,
    nc=0.10,
    n_seq=S.N_SEQ,
    alpha=8.0,
)

gate(
    "Nc0_snapshot_two_grid_rows",
    len(profiles_nc0) == 2,
)

gate(
    "Nc01_snapshot_two_grid_rows",
    len(profiles_nc01) == 2,
)

for label, profiles, nc_expected in (
    ("Nc0", profiles_nc0, 0.0),
    ("Nc01", profiles_nc01, 0.10),
):
    for i, prof in enumerate(profiles):
        x = np.asarray(
            prof["x_seq"],
            dtype=float,
        )
        sw = np.asarray(
            prof["Sw_true"],
            dtype=float,
        )

        gate(
            f"{label}_profile_{i}_x_shape_64",
            x.shape == (64,),
        )

        gate(
            f"{label}_profile_{i}_Sw_shape_64",
            sw.shape == (64,),
        )

        gate(
            f"{label}_profile_{i}_finite",
            np.isfinite(x).all()
            and
            np.isfinite(sw).all(),
        )

        gate(
            f"{label}_profile_{i}_x_monotone",
            np.all(
                np.diff(x) > 0.0
            ),
        )

        gate(
            f"{label}_profile_{i}_saturation_bounds",
            float(sw.min())
            >=
            float(base_p["swc"])
            -
            1.0e-6
            and
            float(sw.max())
            <=
            1.0
            -
            float(base_p["sor"])
            +
            1.0e-6,
        )

        gate(
            f"{label}_profile_{i}_Nc_exact",
            math.isclose(
                float(prof["Nc"]),
                nc_expected,
                rel_tol=0.0,
                abs_tol=1.0e-7,
            ),
        )


p0 = next(
    p
    for p in profiles_nc0
    if p["grid_source"] == "conditioning"
)

p1 = next(
    p
    for p in profiles_nc01
    if p["grid_source"] == "conditioning"
)

gate(
    "positive_Nc_changes_full_solver_profile",
    not np.allclose(
        np.asarray(p0["Sw_true"]),
        np.asarray(p1["Sw_true"]),
        rtol=0.0,
        atol=1.0e-8,
    ),
)


# =============================================================================
# Runtime conditioning and neural model smoke test
# =============================================================================

print()
print("RUNTIME CONDITIONING / MODEL TEST")

raw13 = np.array([[
    base_p["no"],
    base_p["nw"],
    base_p["swc"],
    base_p["sor"],
    base_p["mu_w"],
    base_p["mu_o"],
    base_p["phi"],
    p1["t_D"],
    p1["xD_front"],
    p1["Sw_star"],
    p1["inv_Pec"],
    p1["lambda_bc"],
    p1["Nc"],
]], dtype=np.float32)

p14 = S.append_logM(
    raw13
)

gate(
    "runtime_conditioning_13_to_14",
    p14.shape == (1, 14),
)

gate(
    "Nc_runtime_index_12",
    math.isclose(
        float(p14[0, 12]),
        0.10,
        rel_tol=0.0,
        abs_tol=1.0e-7,
    ),
)

expected_logM = math.log10(
    base_p["mu_w"]
    /
    base_p["mu_o"]
)

gate(
    "logM_runtime_index_13",
    math.isclose(
        float(p14[0, 13]),
        expected_logM,
        rel_tol=0.0,
        abs_tol=1.0e-6,
    ),
)


model = S.build_model(
    input_features=1,
    param_dim=S.PARAM_DIM_S4,
    hidden=P.train.hidden,
    layers=P.train.layers,
)

x_input = (
    np.asarray(
        p1["x_seq"],
        dtype=np.float32,
    )
    .reshape(
        1,
        64,
        1,
    )
)

pred = model(
    [
        x_input,
        p14,
    ],
    training=False,
).numpy()

gate(
    "model_output_shape_1x64x1",
    pred.shape == (1, 64, 1),
)

gate(
    "model_output_finite",
    np.isfinite(
        pred
    ).all(),
)

gate(
    "model_output_saturation_range",
    float(pred.min())
    >=
    float(base_p["swc"])
    -
    1.0e-6
    and
    float(pred.max())
    <=
    1.0
    -
    float(base_p["sor"])
    +
    1.0e-6,
)


params_fixed = {
    "mu_w": P.rock.mu_w,
    "mu_o": P.rock.mu_o,
    "krw_max": P.rock.krw_max,
    "kro_max": P.rock.kro_max,
}

x_tf = S.tf.convert_to_tensor(
    x_input,
    dtype=S.tf.float32,
)

p_tf = S.tf.convert_to_tensor(
    p14,
    dtype=S.tf.float32,
)

Lp, Lcurv, S_pred = S.pde_residual_loss(
    model,
    x_tf,
    p_tf,
    params_fixed,
)

gate(
    "full_PDE_loss_finite",
    bool(
        S.tf.math.is_finite(
            Lp
        ).numpy()
    ),
)

gate(
    "full_curvature_loss_finite",
    bool(
        S.tf.math.is_finite(
            Lcurv
        ).numpy()
    ),
)

gate(
    "full_PDE_prediction_finite",
    bool(
        S.tf.reduce_all(
            S.tf.math.is_finite(
                S_pred
            )
        ).numpy()
    ),
)


# =============================================================================
# Document inherited metadata/control-flow observations
# =============================================================================

source_notes = {
    "physics_identity":
        (
            "Full Stage-4 Godunov source combines Stage-3 Brooks-Corey "
            "capillary diffusion with Stage-2-style compressible velocity "
            "u_D(x_D)=exp(Nc*x_D), using the conservative advective form "
            "d/dx_D[u_D f_w]."
        ),

    "runtime_conditioning_dimension":
        14,

    "raw_conditioning_dimension":
        13,

    "source_condition_on_tuple_dimension":
        12,

    "ProjectParams_param_dim_value":
        int(P.param_dim()),

    "metadata_dimension_note":
        (
            "Executable B4 arrays carry 13 raw features including Nc, then "
            "append log10(M) for 14 runtime features. The inherited "
            "condition_on tuple remains 12 and the source-written config "
            "therefore reports param_dim=12. This is documented, not silently changed."
        ),

    "TrainConfig_batch_size_declared":
        int(P.train.batch_size),

    "main_dataset_batch_size_actual":
        4096,

    "batch_size_note":
        (
            "TrainConfig declares batch_size=256, while final main explicitly "
            "passes batch_size=4096 to make_tf_datasets_from_arrays. "
            "Source-faithful reproduction follows executable main."
        ),

    "source_header_note":
        (
            "Early module text/comments retain Stage-3 wording because Stage 4 "
            "was built by extending the mature Stage-3 source. S4-tagged "
            "sections and Stage-4 filenames define the actual executable Stage-4 behavior."
        ),

    "supplemental_slab_control_flow_note":
        (
            "As in B3, supplemental slab creation is located inside the "
            "dataset-reload branch. A clean first execution may build the main "
            "dataset and proceed without the slab. This is observed in preflight "
            "and will be documented rather than used to open a new tuning branch."
        ),
}


results = {
    "milestone":
        MILESTONE,

    "source_name":
        SOURCE.name,

    "source_hashes": {
        "raw":
            hashes["raw"],

        "lf":
            hashes["lf"],

        "crlf":
            hashes["crlf"],

        "match_mode":
            match_mode,
    },

    "B3B_authority": {
        "results_sha256":
            EXPECTED_B3B_RESULTS_SHA,

        "summary_sha256":
            EXPECTED_B3B_SUMMARY_SHA,

        "handoff_sha256":
            EXPECTED_B3B_HANDOFF_SHA,
    },

    "full_physics_contract": {
        "variant":
            "godunov_conservative",

        "conservative_form":
            True,

        "compressibility_feature":
            "Nc",

        "velocity_field":
            "u_D(x_D)=exp(Nc*x_D)",

        "capillary_features":
            [
                "inv_Pec",
                "lambda_bc",
            ],

        "training_Nc_values":
            [
                0.0,
                0.05,
                0.10,
                0.20,
            ],

        "training_Pe_c_values":
            [
                10.0,
                22.0,
                50.0,
                100.0,
            ],

        "training_lambda_bc_values":
            [
                1.5,
                2.0,
                3.0,
            ],

        "N_SEQ":
            64,

        "runtime_param_dim":
            14,

        "hidden":
            64,

        "layers":
            2,

        "epochs":
            1000,

        "seed":
            1337,

        "lr":
            1.0e-3,
    },

    "source_notes":
        source_notes,

    "physics_smoke_test":
        "PASS",

    "model_forward_smoke_test":
        "PASS",

    "full_PDE_smoke_test":
        "PASS",

    "training_performed":
        False,

    "B4_source_faithful_reproduction_authorized":
        True,

    "next":
        (
            "Run the exact recovered Stage-4 full Godunov source in a persistent "
            "Drive working directory. Do not reopen B2/B3 or replay historical "
            "Stage-4 development branches."
        ),
}

atomic_json(
    RESULTS,
    results,
)

results_sha = sha256(
    RESULTS
)


summary = {
    "milestone":
        MILESTONE,

    "source_hashes":
        results[
            "source_hashes"
        ],

    "results_sha256":
        results_sha,

    "physics_preflight_PASS":
        True,

    "model_forward_preflight_PASS":
        True,

    "full_PDE_preflight_PASS":
        True,

    "training_performed":
        False,

    "B4_source_faithful_reproduction_authorized":
        True,

    "next":
        results[
            "next"
        ],
}

atomic_json(
    SUMMARY,
    summary,
)

summary_sha = sha256(
    SUMMARY
)


handoff = f"""# PAD-Stream V16E-1B4A

## Role

Full Buckley-Leverett Godunov source-authority binding and physics preflight.

## Physics

The recovered Stage-4 source combines:

- compressible velocity: `u_D(x_D) = exp(Nc x_D)`
- conservative Godunov advection: `d/dx_D[u_D f_w]`
- Brooks-Corey capillary diffusion
- Nc-dependent travel-time/front transform
- the 64-node Stage-3 spatial interface

Nc=0 is included in the Stage-4 training grid, providing explicit Stage-3 nesting.

## Source authority

Raw SHA-256:

`{hashes["raw"]}`

LF-normalized SHA-256:

`{hashes["lf"]}`

CRLF-normalized SHA-256:

`{hashes["crlf"]}`

Authority match mode:

`{match_mode}`

## Preflight

B3B forward authority: PASS

Stage-4 source authority: PASS

Nc=0 nesting transform: PASS

Positive-Nc travel-time transform: PASS

Full conservative solver smoke test: PASS

14-dimensional runtime conditioning: PASS

Model forward smoke test: PASS

Full PDE residual smoke test: PASS

Training performed: NO

B4 source-faithful reproduction authorized: YES

## Documented inherited source notes

The executable runtime vector is 14-dimensional (13 raw features including Nc,
plus log10(M)), while the inherited `condition_on` tuple remains 12-dimensional.

The dataclass declares batch size 256, while final `main` explicitly uses 4096.

Some header/comments retain Stage-3 wording because Stage 4 extends the mature
Stage-3 source. The S4-tagged code and Stage-4 output names govern execution.

The supplemental slab is still located inside the dataset-reload branch; this
will be documented if the clean first B4 run omits it.

## Hashes

Results SHA-256:

`{results_sha}`

Summary SHA-256:

`{summary_sha}`

## Next

Exact source-faithful Stage-4 full Godunov reproduction.
"""

HANDOFF.write_text(
    handoff,
    encoding="utf-8",
)

handoff_sha = sha256(
    HANDOFF
)


print()
print("=" * 110)
print("B4A PREFLIGHT RESULT")
print("=" * 110)

print(
    "Source authority match mode       :",
    match_mode,
)

print(
    "B3B forward authority             : PASS"
)

print(
    "Nc=0 nesting                     : PASS"
)

print(
    "Positive-Nc transform             : PASS"
)

print(
    "Full solver physics smoke test    : PASS"
)

print(
    "Runtime conditioning 14D          : PASS"
)

print(
    "Model forward smoke test          : PASS"
)

print(
    "Full PDE residual smoke test      : PASS"
)

print(
    "Training performed                : NO"
)

print(
    "B4 reproduction authorized        : YES"
)

print(
    "Results SHA                       :",
    results_sha,
)

print(
    "Summary SHA                       :",
    summary_sha,
)

print(
    "Handoff SHA                       :",
    handoff_sha,
)

print()
print(
    "NEXT: exact source-faithful Stage-4 full Godunov reproduction."
)

from __future__ import annotations

from pathlib import Path
import argparse
import copy
import importlib.util
import json
import shutil

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7D-R
# Front-Aware Conservative Streamline-to-Grid Map-Back
#
# NO TRAINING.
# NO LEARNED MAP-BACK.
# NO SEED-DENSITY CHANGE.
# NO SG6 GEOMETRY CHANGE.
# NO CONSERVATIVE PROJECTION CHANGE.
#
# PURPOSE
# -------
# Re-run the accepted SG7D conservative map-back implementation on the exact
# accepted 11x11 SGSim geometry, but replace ONLY the original frozen SG7C
# PI-RNN streamline saturation field with the independently frozen front-aware
# SG7C-R field.
#
# This adapter deliberately imports the accepted SG7D implementation from the
# 11x11 workspace rather than reimplementing the map-back equations.
#
# The authoritative SG7D code therefore remains responsible for:
#
#   - Cartesian streamline/cell intersection,
#   - q*Delta-tau subsegment pore-volume weighting,
#   - direct-support mask,
#   - initial-state fallback in uncovered cells,
#   - bounded conservative inventory projection,
#   - mapped-state validation,
#   - storage closure.
#
# SG7D-R changes only the incoming PI-RNN transport field.
#
# The original 11x11 SG7D outputs are left untouched.
# =============================================================================


ROOT = Path(__file__).resolve().parent

DEFAULT_WORKSPACE = (
    ROOT.parent
    / f"{ROOT.name}_SG5C_seed_11x11"
)

ORIGINAL_SG7D_FILENAME = (
    "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
)

SG7CR_FILE = (
    ROOT
    / "output"
    / "V15_SG7CR"
    / "SG7CR_FRONT_AWARE_FROZEN_PIRNN_STREAMLINE_DEPLOYMENT.npz"
)

SG7CR_SUMMARY_FILE = (
    ROOT
    / "output"
    / "V15_SG7CR"
    / "PAD_Stream_V15SG7CR_Summary.json"
)

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7DR"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

STANDARD_MAPBACK_FILE = (
    OUTPUT_DIR
    / "SG7DR_FRONT_AWARE_CONSERVATIVE_GRID_MAPBACK.npz"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7DR_Summary.json"
)

ADAPTER_AUDIT_FILE = (
    OUTPUT_DIR
    / "V15SG7DR_Adapter_Audit.json"
)


# =============================================================================
# HELPERS
# =============================================================================

def load_json(path: Path):

    if not path.exists():

        raise FileNotFoundError(
            f"Missing JSON:\n{path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:

        return json.load(
            handle
        )


def load_module(
    path: Path,
    name: str,
):

    if not path.exists():

        raise FileNotFoundError(
            f"Missing authoritative SG7D source:\n{path}"
        )

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:

        raise RuntimeError(
            f"Could not import SG7D source:\n{path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


def find_npz_key(
    db,
    aliases,
    description,
):

    for key in aliases:

        if key in db:

            return key

    raise KeyError(
        f"Could not identify {description}.\n"
        f"Accepted aliases: {aliases}\n"
        f"Available keys: {list(db.keys())}"
    )


def recursive_pass_marker(obj):

    """
    Look for an explicit PASS/True marker in an SG7D summary without assuming
    one exact historical JSON schema.
    """

    if isinstance(
        obj,
        dict,
    ):

        for key, value in obj.items():

            key_l = str(
                key
            ).lower()

            if (
                key_l
                in
                {
                    "validation_passed",
                    "passed",
                    "mapback_passed",
                    "map_back_passed",
                    "accepted",
                }
                and
                value is True
            ):

                return True

            if (
                key_l
                in
                {
                    "status",
                    "validation",
                    "result",
                }
                and
                isinstance(
                    value,
                    str,
                )
                and
                "PASS"
                in
                value.upper()
            ):

                return True

            if recursive_pass_marker(
                value
            ):

                return True

    elif isinstance(
        obj,
        list,
    ):

        for value in obj:

            if recursive_pass_marker(
                value
            ):

                return True

    return False


def replace_output_paths(
    module,
    old_output_dir: Path,
    new_output_dir: Path,
):

    """
    Patch only Path-valued SG7D output globals.

    ROOT is intentionally NOT changed because the authoritative 11x11 SG7D
    source must keep reading geometry/support inputs from its own workspace.
    """

    replacements = {}

    old_output_dir = old_output_dir.resolve()

    for name, value in list(
        vars(
            module
        ).items()
    ):

        if not isinstance(
            value,
            Path,
        ):

            continue

        try:

            resolved = value.resolve()

        except Exception:

            continue

        try:

            relative = resolved.relative_to(
                old_output_dir
            )

        except ValueError:

            continue

        new_value = (
            new_output_dir
            /
            relative
        )

        setattr(
            module,
            name,
            new_value,
        )

        replacements[
            name
        ] = {
            "old":
                str(
                    value
                ),

            "new":
                str(
                    new_value
                ),
        }

    # Ensure the most common output-dir global is patched even if it was not
    # captured for an unusual pathlib normalization reason.
    if hasattr(
        module,
        "OUTPUT_DIR",
    ):

        old_value = getattr(
            module,
            "OUTPUT_DIR",
        )

        setattr(
            module,
            "OUTPUT_DIR",
            new_output_dir,
        )

        replacements[
            "OUTPUT_DIR"
        ] = {
            "old":
                str(
                    old_value
                ),

            "new":
                str(
                    new_output_dir
                ),
        }

    new_output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return replacements


def identify_prediction_key_in_loaded_contract(
    original_contract: dict,
    original_sg7c_prediction: np.ndarray,
):

    """
    Identify which dictionary member returned by authoritative load_sg7c()
    is the PI-RNN saturation array.

    Prefer semantic key names. Fall back to numerical identity with the
    accepted original SG7C prediction.
    """

    preferred_tokens = [
        "pirnn",
        "pi_rnn",
        "prediction",
        "predicted",
        "s_pirnn",
    ]

    for key, value in original_contract.items():

        key_l = str(
            key
        ).lower()

        if (
            isinstance(
                value,
                np.ndarray,
            )
            and
            value.shape
            ==
            original_sg7c_prediction.shape
            and
            any(
                token
                in
                key_l
                for token
                in
                preferred_tokens
            )
        ):

            return key

    best_key = None

    best_linf = np.inf

    for key, value in original_contract.items():

        if not isinstance(
            value,
            np.ndarray,
        ):

            continue

        if (
            value.shape
            !=
            original_sg7c_prediction.shape
        ):

            continue

        linf = float(
            np.max(
                np.abs(
                    np.asarray(
                        value,
                        dtype=np.float64,
                    )
                    -
                    np.asarray(
                        original_sg7c_prediction,
                        dtype=np.float64,
                    )
                )
            )
        )

        if linf < best_linf:

            best_linf = linf
            best_key = key

    if (
        best_key
        is None
        or
        best_linf
        >
        1.0e-6
    ):

        raise RuntimeError(
            "Could not identify the PI-RNN saturation member in the "
            "authoritative SG7D load_sg7c() contract."
        )

    return best_key


def identify_truth_key_in_loaded_contract(
    original_contract: dict,
    original_sg7c_truth: np.ndarray,
):

    preferred_tokens = [
        "truth",
        "sg7a",
        "reference",
    ]

    for key, value in original_contract.items():

        key_l = str(
            key
        ).lower()

        if (
            isinstance(
                value,
                np.ndarray,
            )
            and
            value.shape
            ==
            original_sg7c_truth.shape
            and
            any(
                token
                in
                key_l
                for token
                in
                preferred_tokens
            )
        ):

            return key

    best_key = None

    best_linf = np.inf

    for key, value in original_contract.items():

        if not isinstance(
            value,
            np.ndarray,
        ):

            continue

        if (
            value.shape
            !=
            original_sg7c_truth.shape
        ):

            continue

        linf = float(
            np.max(
                np.abs(
                    np.asarray(
                        value,
                        dtype=np.float64,
                    )
                    -
                    np.asarray(
                        original_sg7c_truth,
                        dtype=np.float64,
                    )
                )
            )
        )

        if linf < best_linf:

            best_linf = linf
            best_key = key

    if (
        best_key
        is None
        or
        best_linf
        >
        1.0e-6
    ):

        raise RuntimeError(
            "Could not identify the SG7A truth member in the "
            "authoritative SG7D load_sg7c() contract."
        )

    return best_key


def locate_generated_mapback(
    output_dir: Path,
):

    preferred = (
        output_dir
        /
        "SG7D_CONSERVATIVE_GRID_MAPBACK.npz"
    )

    if preferred.exists():

        return preferred

    matches = sorted(
        output_dir.glob(
            "*GRID*MAPBACK*.npz"
        )
    )

    if len(
        matches
    ) == 1:

        return matches[
            0
        ]

    matches = sorted(
        output_dir.glob(
            "*.npz"
        )
    )

    if len(
        matches
    ) == 1:

        return matches[
            0
        ]

    raise RuntimeError(
        "Could not uniquely identify the SG7D-R map-back database in:\n"
        f"{output_dir}\n"
        f"NPZ files: {[p.name for p in matches]}"
    )


def locate_generated_summary(
    output_dir: Path,
):

    preferred = (
        output_dir
        /
        "PAD_Stream_V15SG7D_Summary.json"
    )

    if preferred.exists():

        return preferred

    matches = sorted(
        output_dir.glob(
            "*Summary*.json"
        )
    )

    if len(
        matches
    ) == 1:

        return matches[
            0
        ]

    return None


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "PAD-Stream V15-SG7D-R front-aware conservative map-back "
            "using the authoritative 11x11 SG7D implementation."
        )
    )

    parser.add_argument(
        "--workspace",
        type=str,
        default=str(
            DEFAULT_WORKSPACE
        ),
        help=(
            "Accepted 11x11 SG5C workspace containing authoritative SG7D."
        ),
    )

    args = parser.parse_args()

    workspace = Path(
        args.workspace
    ).resolve()

    source_file = (
        workspace
        /
        ORIGINAL_SG7D_FILENAME
    )

    original_output_dir = (
        workspace
        /
        "output"
        /
        "V15_SG7D"
    )

    original_sg7c_file = (
        workspace
        /
        "output"
        /
        "V15_SG7C"
        /
        "SG7C_FROZEN_PIRNN_STREAMLINE_DEPLOYMENT.npz"
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG7D-R"
    )

    print(
        "Front-Aware Conservative Streamline-to-Grid Map-Back"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    print(
        "NO LEARNED MAP-BACK WILL BE USED."
    )

    print(
        "NO STREAMLINE SEED DENSITY WILL BE CHANGED."
    )

    print(
        "NO SG6 GEOMETRY WILL BE CHANGED."
    )

    print(
        "NO CONSERVATIVE PROJECTION WILL BE CHANGED."
    )

    print(
        "\nThe accepted 11x11 SG7D implementation is the map-back authority."
    )

    # =========================================================================
    # PRECONDITIONS
    # =========================================================================

    for path in [
        source_file,
        original_sg7c_file,
        SG7CR_FILE,
        SG7CR_SUMMARY_FILE,
    ]:

        if not path.exists():

            raise FileNotFoundError(
                f"Missing SG7D-R prerequisite:\n{path}"
            )

    sg7cr_summary = load_json(
        SG7CR_SUMMARY_FILE
    )

    if not sg7cr_summary.get(
        "validation_passed",
        False,
    ):

        raise RuntimeError(
            "SG7C-R did not pass redeployment validation."
        )

    sg7cr = np.load(
        SG7CR_FILE,
        allow_pickle=True,
    )

    original_sg7c = np.load(
        original_sg7c_file,
        allow_pickle=True,
    )

    sg7cr_pred_key = find_npz_key(
        sg7cr,
        [
            "PI_RNN_saturation",
            "pirnn_saturation",
            "predicted_saturation",
            "S_pirnn",
        ],
        "SG7C-R PI-RNN saturation",
    )

    sg7cr_truth_key = find_npz_key(
        sg7cr,
        [
            "SG7A_saturation",
            "truth_saturation",
            "reference_saturation",
            "S_truth",
        ],
        "SG7C-R SG7A truth",
    )

    original_pred_key = find_npz_key(
        original_sg7c,
        [
            "PI_RNN_saturation",
            "pirnn_saturation",
            "predicted_saturation",
            "S_pirnn",
        ],
        "original SG7C PI-RNN saturation",
    )

    original_truth_key = find_npz_key(
        original_sg7c,
        [
            "SG7A_saturation",
            "truth_saturation",
            "reference_saturation",
            "S_truth",
        ],
        "original SG7C SG7A truth",
    )

    front_aware_prediction = np.asarray(
        sg7cr[
            sg7cr_pred_key
        ],
        dtype=np.float32,
    )

    front_aware_truth = np.asarray(
        sg7cr[
            sg7cr_truth_key
        ],
        dtype=np.float32,
    )

    original_prediction = np.asarray(
        original_sg7c[
            original_pred_key
        ],
        dtype=np.float32,
    )

    original_truth = np.asarray(
        original_sg7c[
            original_truth_key
        ],
        dtype=np.float32,
    )

    if (
        front_aware_prediction.shape
        !=
        original_prediction.shape
    ):

        raise RuntimeError(
            "SG7C-R and original SG7C prediction shapes differ:\n"
            f"SG7C-R: {front_aware_prediction.shape}\n"
            f"SG7C  : {original_prediction.shape}"
        )

    truth_linf = float(
        np.max(
            np.abs(
                front_aware_truth.astype(
                    np.float64
                )
                -
                original_truth.astype(
                    np.float64
                )
            )
        )
    )

    if truth_linf > 1.0e-7:

        raise RuntimeError(
            "SG7C-R and original SG7C do not use identical SG7A truth.\n"
            f"Linf = {truth_linf:.6e}"
        )

    print(
        "\nINPUT A/B CONTRACT"
    )

    print(
        f"  Authoritative SG7D      : "
        f"{source_file}"
    )

    print(
        f"  Original SG7C shape     : "
        f"{original_prediction.shape}"
    )

    print(
        f"  Front-aware SG7C-R shape: "
        f"{front_aware_prediction.shape}"
    )

    print(
        f"  SG7A truth Linf A/B     : "
        f"{truth_linf:.6e}"
    )

    print(
        "  Geometry change         : NONE"
    )

    print(
        "  Map-back change         : NONE"
    )

    print(
        "  Changed field           : PI-RNN streamline saturation only"
    )

    # =========================================================================
    # IMPORT AUTHORITATIVE SG7D
    # =========================================================================

    sg7d = load_module(
        source_file,
        "pad_stream_authoritative_sg7d_11x11",
    )

    if not hasattr(
        sg7d,
        "load_sg7c",
    ):

        raise RuntimeError(
            "Authoritative SG7D source does not expose load_sg7c()."
        )

    if not hasattr(
        sg7d,
        "main",
    ):

        raise RuntimeError(
            "Authoritative SG7D source does not expose main()."
        )

    original_load_sg7c = (
        sg7d.load_sg7c
    )

    original_contract = (
        original_load_sg7c()
    )

    if not isinstance(
        original_contract,
        dict,
    ):

        raise RuntimeError(
            "Authoritative SG7D load_sg7c() did not return a dictionary."
        )

    prediction_contract_key = (
        identify_prediction_key_in_loaded_contract(
            original_contract,
            original_prediction,
        )
    )

    truth_contract_key = (
        identify_truth_key_in_loaded_contract(
            original_contract,
            original_truth,
        )
    )

    print(
        "\nAUTHORITATIVE SG7D LOAD CONTRACT"
    )

    print(
        f"  PI-RNN field key        : "
        f"{prediction_contract_key}"
    )

    print(
        f"  SG7A truth key          : "
        f"{truth_contract_key}"
    )

    print(
        f"  Contract keys           : "
        f"{list(original_contract.keys())}"
    )

    # =========================================================================
    # PATCH ONLY THE INCOMING PI-RNN FIELD
    # =========================================================================

    def load_sg7c_front_aware():

        contract = copy.deepcopy(
            original_contract
        )

        contract[
            prediction_contract_key
        ] = front_aware_prediction.copy()

        # Reassert unchanged truth explicitly.
        contract[
            truth_contract_key
        ] = front_aware_truth.copy()

        return contract

    sg7d.load_sg7c = (
        load_sg7c_front_aware
    )

    # =========================================================================
    # REDIRECT OUTPUTS — LEAVE ORIGINAL SG7D UNTOUCHED
    # =========================================================================

    path_replacements = replace_output_paths(
        sg7d,
        original_output_dir,
        OUTPUT_DIR,
    )

    print(
        "\nOUTPUT REDIRECTION"
    )

    print(
        f"  Original outputs        : "
        f"{original_output_dir}"
    )

    print(
        f"  SG7D-R outputs          : "
        f"{OUTPUT_DIR}"
    )

    print(
        f"  Path globals redirected : "
        f"{len(path_replacements)}"
    )

    # =========================================================================
    # RUN EXACT AUTHORITATIVE SG7D MAIN
    # =========================================================================

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "RUNNING AUTHORITATIVE SG7D MAP-BACK WITH FRONT-AWARE SG7C-R FIELD"
    )

    print(
        "=" * 78
    )

    sg7d.main()

    # =========================================================================
    # LOCATE / STANDARDIZE OUTPUT
    # =========================================================================

    generated_mapback = locate_generated_mapback(
        OUTPUT_DIR
    )

    if (
        generated_mapback.resolve()
        !=
        STANDARD_MAPBACK_FILE.resolve()
    ):

        shutil.copy2(
            generated_mapback,
            STANDARD_MAPBACK_FILE,
        )

    generated_summary = locate_generated_summary(
        OUTPUT_DIR
    )

    authoritative_pass = None

    authoritative_summary = None

    if (
        generated_summary
        is not None
        and
        generated_summary.exists()
    ):

        authoritative_summary = load_json(
            generated_summary
        )

        authoritative_pass = recursive_pass_marker(
            authoritative_summary
        )

    # If the historical summary schema has no explicit PASS marker, successful
    # return from authoritative main() plus existence of its numerical database
    # is retained as the execution-level pass condition. We report that fact.
    if authoritative_pass is None:

        authoritative_pass = bool(
            generated_mapback.exists()
        )

    # =========================================================================
    # POST-RUN DATABASE AUDIT
    # =========================================================================

    mapped = np.load(
        STANDARD_MAPBACK_FILE,
        allow_pickle=True,
    )

    print(
        "\nSG7D-R MAP-BACK DATABASE"
    )

    print(
        f"  File                    : "
        f"{STANDARD_MAPBACK_FILE.name}"
    )

    print(
        f"  Keys                    : "
        f"{list(mapped.keys())}"
    )

    finite_arrays = True

    for key in mapped.keys():

        value = mapped[
            key
        ]

        if (
            isinstance(
                value,
                np.ndarray,
            )
            and
            np.issubdtype(
                value.dtype,
                np.number,
            )
        ):

            if not np.all(
                np.isfinite(
                    value
                )
            ):

                finite_arrays = False

                break

    # =========================================================================
    # WRAPPER VALIDATION
    # =========================================================================

    checks = [
        (
            "SG7C-R passed before SG7D-R",
            bool(
                sg7cr_summary.get(
                    "validation_passed",
                    False,
                )
            ),
        ),

        (
            "SG7C-R and original SG7C use identical SG7A truth",
            truth_linf
            <=
            1.0e-7,
        ),

        (
            "Front-aware and original streamline fields have identical shape",
            front_aware_prediction.shape
            ==
            original_prediction.shape,
        ),

        (
            "Authoritative 11x11 SG7D source loaded",
            source_file.exists(),
        ),

        (
            "Only SG7C PI-RNN field patched in load contract",
            prediction_contract_key
            !=
            truth_contract_key,
        ),

        (
            "Original SG7D output directory not used",
            OUTPUT_DIR.resolve()
            !=
            original_output_dir.resolve(),
        ),

        (
            "Authoritative SG7D completed",
            bool(
                authoritative_pass
            ),
        ),

        (
            "Standard SG7D-R map-back database created",
            STANDARD_MAPBACK_FILE.exists(),
        ),

        (
            "SG7D-R numerical arrays finite",
            finite_arrays,
        ),
    ]

    passed = all(
        flag
        for (
            _,
            flag,
        )
        in checks
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "V15-SG7D-R ADAPTER / CONSERVATIVE MAP-BACK VALIDATION"
    )

    print(
        "=" * 78
    )

    for description, flag in checks:

        print(
            f"[{'PASS' if flag else 'FAIL'}] "
            f"{description}"
        )

    print(
        "=" * 78
    )

    # =========================================================================
    # AUDIT JSON
    # =========================================================================

    audit = {
        "milestone":
            "V15-SG7D-R",

        "authoritative_source":
            str(
                source_file
            ),

        "authoritative_workspace":
            str(
                workspace
            ),

        "original_output_dir":
            str(
                original_output_dir
            ),

        "redeployment_output_dir":
            str(
                OUTPUT_DIR
            ),

        "original_sg7c_file":
            str(
                original_sg7c_file
            ),

        "front_aware_sg7cr_file":
            str(
                SG7CR_FILE
            ),

        "prediction_contract_key":
            str(
                prediction_contract_key
            ),

        "truth_contract_key":
            str(
                truth_contract_key
            ),

        "sg7a_truth_linf_between_A_B":
            truth_linf,

        "path_replacements":
            path_replacements,

        "authoritative_main_completed":
            bool(
                authoritative_pass
            ),

        "standard_mapback_file":
            str(
                STANDARD_MAPBACK_FILE
            ),

        "database_keys":
            list(
                mapped.keys()
            ),

        "all_numeric_arrays_finite":
            bool(
                finite_arrays
            ),

        "wrapper_validation_passed":
            bool(
                passed
            ),
    }

    with ADAPTER_AUDIT_FILE.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            audit,
            handle,
            indent=2,
        )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    if passed:

        status = (
            "FRONT_AWARE_CONSERVATIVE_MAPBACK_COMPLETED"
        )

        recommendation = (
            "The accepted 11x11 SG7D conservative map-back implementation "
            "successfully reconstructed the front-aware frozen PI-RNN field "
            "without changing SG6 geometry, support, accumulation, fallback, "
            "or conservative projection logic. Proceed to full-grid plume "
            "validation and compare directly against the original 11x11 SG7E "
            "failure."
        )

        next_milestone = (
            "V15-SG7E-R — Front-Aware Full-Grid "
            "Plume / Coverage Validation"
        )

    else:

        status = (
            "FRONT_AWARE_CONSERVATIVE_MAPBACK_INCOMPLETE"
        )

        recommendation = (
            "Do not proceed to SG7E-R. Diagnose the failed SG7D-R adapter or "
            "authoritative map-back gate while leaving the original SG7D "
            "workspace unchanged."
        )

        next_milestone = (
            "V15-SG7D-R1 — Front-Aware Map-Back Regression Audit"
        )

    summary = {
        "milestone":
            "V15-SG7D-R",

        "description":
            (
                "Front-aware conservative streamline-to-grid map-back using "
                "the accepted 11x11 SG7D implementation"
            ),

        "training_performed":
            False,

        "learned_mapback_used":
            False,

        "seed_density_changed":
            False,

        "SG6_geometry_changed":
            False,

        "mapback_operator_changed":
            False,

        "conservative_projection_changed":
            False,

        "changed_input":
            "PI-RNN streamline saturation only",

        "authoritative_source":
            str(
                source_file
            ),

        "front_aware_input":
            str(
                SG7CR_FILE
            ),

        "mapback_database":
            str(
                STANDARD_MAPBACK_FILE
            ),

        "validation_passed":
            bool(
                passed
            ),

        "status":
            status,

        "recommendation":
            recommendation,

        "next_milestone":
            next_milestone,
    }

    with SUMMARY_FILE.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            summary,
            handle,
            indent=2,
        )

    # =========================================================================
    # FINAL
    # =========================================================================

    print(
        "\nOUTPUTS"
    )

    print(
        f"  Directory:\n"
        f"    {OUTPUT_DIR}"
    )

    print(
        "\nStandard map-back database:"
    )

    print(
        f"  {STANDARD_MAPBACK_FILE.name}"
    )

    print(
        "\nAdapter audit:"
    )

    print(
        f"  {ADAPTER_AUDIT_FILE.name}"
    )

    print(
        "\nSummary:"
    )

    print(
        f"  {SUMMARY_FILE.name}"
    )

    print(
        "\n"
        +
        "=" * 78
    )

    if passed:

        print(
            "V15-SG7D-R CONSERVATIVE MAP-BACK: PASS"
        )

        print()

        print(
            "STATUS:"
        )

        print(
            "FRONT-AWARE PI-RNN STREAMLINE TRANSPORT SUCCESSFULLY "
            "RECONSTRUCTED ON THE SGSIM GRID"
        )

        print()

        print(
            "The original SG7D implementation and 11x11 outputs remain unchanged."
        )

        print()

        print(
            "Next milestone:"
        )

        print(
            "V15-SG7E-R — Front-Aware Full-Grid "
            "Plume / Coverage Validation"
        )

    else:

        print(
            "V15-SG7D-R CONSERVATIVE MAP-BACK: FAIL"
        )

        print()

        print(
            f"Next milestone:\n  {next_milestone}"
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":

    main()

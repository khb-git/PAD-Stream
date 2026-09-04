from __future__ import annotations

from pathlib import Path
import argparse
import csv
import importlib.util
import json

import numpy as np


# =============================================================================
# PAD-Stream V15-SG7E-R
# Front-Aware Full-Grid Plume / Coverage Validation
#
# NO TRAINING.
# NO SEED-DENSITY CHANGE.
# NO MAP-BACK CHANGE.
# NO PLUME-THRESHOLD CHANGE.
#
# PURPOSE
# -------
# Run the accepted 11x11 SG7E full-grid plume validation implementation on the
# new SG7D-R front-aware map-back database.
#
# This is the causal closure test for the complete diagnostic branch:
#
#   original frozen PI-RNN
#       -> no S=0.21 streamline crossings
#       -> early-time Eulerian plume-volume failure
#
#   front-aware frozen PI-RNN
#       -> 949 / 992 early streamline fronts recovered
#       -> unchanged conservative SG7D map-back
#       -> SG7E-R full-grid validation
#
# The accepted SG7E implementation remains authoritative for:
#   - plume masks / thresholds,
#   - footprint IoU,
#   - strong-plume IoU,
#   - core IoU,
#   - plume-volume error,
#   - centroid displacement,
#   - vertical-extent difference,
#   - projection diagnostics,
#   - final morphology gates.
#
# SG7E-R changes ONLY the SG7D input database.
#
# The original 11x11 SG7E outputs remain untouched.
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent

DEFAULT_WORKSPACE = (
    ROOT.parent
    / f"{ROOT.name}_SG5C_seed_11x11"
)

ORIGINAL_SG7E_FILENAME = (
    "PAD_Stream_V15SG7E_FullGrid_Plume_Coverage_Validation.py"
)

SG7DR_DIR = (
    ROOT
    / "output"
    / "V15_SG7DR"
)

SG7DR_MAPBACK_FILE = (
    SG7DR_DIR
    / "SG7DR_FRONT_AWARE_CONSERVATIVE_GRID_MAPBACK.npz"
)

# Authoritative SG7D summary generated inside SG7D-R output redirection.
SG7DR_AUTHORITATIVE_SUMMARY = (
    SG7DR_DIR
    / "PAD_Stream_V15SG7D_Summary.json"
)

SG7DR_WRAPPER_SUMMARY = (
    SG7DR_DIR
    / "PAD_Stream_V15SG7DR_Summary.json"
)

OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG7ER"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

WRAPPER_SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7ER_Summary.json"
)

A_B_COMPARISON_FILE = (
    OUTPUT_DIR
    / "V15SG7ER_Original_vs_FrontAware_Plume.csv"
)

ADAPTER_AUDIT_FILE = (
    OUTPUT_DIR
    / "V15SG7ER_Adapter_Audit.json"
)


# =============================================================================
# ACCEPTED SG7E PRIMARY CONTRACT
# =============================================================================

PRIMARY_TIME_DAYS = 100.0
PRIMARY_VOLUME_GATE = 0.10
FOOTPRINT_IOU_GATE = 0.90
CENTROID_GATE_CELLS = 2.0
VERTICAL_EXTENT_GATE_LAYERS = 2

# Historical 11x11 primary failure is expected near 18.241%.
# This is only an A/B sanity reference, NOT a gate.
EXPECTED_ORIGINAL_100D_VOLUME_ERROR = 0.18241
ORIGINAL_REFERENCE_TOL = 0.02


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
            f"Missing authoritative SG7E source:\n{path}"
        )

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:

        raise RuntimeError(
            f"Could not import authoritative SG7E source:\n{path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


def save_csv(
    path: Path,
    rows: list[dict],
):

    if not rows:

        return

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=list(
                rows[
                    0
                ].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def read_csv(
    path: Path,
):

    if not path.exists():

        raise FileNotFoundError(
            f"Missing CSV:\n{path}"
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as handle:

        return list(
            csv.DictReader(
                handle
            )
        )


def recursive_pass_marker(obj):

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
                    "plume_morphology_pass",
                    "morphology_pass",
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

    if hasattr(
        module,
        "OUTPUT_DIR",
    ):

        old = getattr(
            module,
            "OUTPUT_DIR"
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
                    old
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


def patch_sg7d_input_paths(
    module,
    new_mapback_file: Path,
    new_summary_file: Path,
):

    """
    Redirect known SG7D input globals in the authoritative SG7E module.
    """

    replacements = {}

    candidate_names = [
        "SG7D_FILE",
        "SG7D_MAPBACK_FILE",
        "SG7D_DATABASE_FILE",
        "MAPBACK_FILE",
    ]

    summary_names = [
        "SG7D_SUMMARY_FILE",
        "SG7D_SUMMARY",
    ]

    for name in candidate_names:

        if hasattr(
            module,
            name,
        ):

            old = getattr(
                module,
                name,
            )

            setattr(
                module,
                name,
                new_mapback_file,
            )

            replacements[
                name
            ] = {
                "old":
                    str(
                        old
                    ),

                "new":
                    str(
                        new_mapback_file
                    ),
            }

    for name in summary_names:

        if hasattr(
            module,
            name,
        ):

            old = getattr(
                module,
                name,
            )

            setattr(
                module,
                name,
                new_summary_file,
            )

            replacements[
                name
            ] = {
                "old":
                    str(
                        old
                    ),

                "new":
                    str(
                        new_summary_file
                    ),
            }

    return replacements


def locate_file(
    directory: Path,
    preferred_name: str,
    pattern: str,
):

    preferred = (
        directory
        /
        preferred_name
    )

    if preferred.exists():

        return preferred

    matches = sorted(
        directory.glob(
            pattern
        )
    )

    if len(
        matches
    ) == 1:

        return matches[
            0
        ]

    raise RuntimeError(
        f"Could not uniquely identify file in {directory}\n"
        f"Preferred: {preferred_name}\n"
        f"Matches: {[p.name for p in matches]}"
    )


def numeric_value(
    row: dict,
    aliases: list[str],
):

    for key in aliases:

        if key in row:

            try:

                return float(
                    row[
                        key
                    ]
                )

            except Exception:

                pass

    raise KeyError(
        f"Could not identify numeric field from aliases {aliases}.\n"
        f"Available fields: {list(row.keys())}"
    )


def time_value(
    row: dict,
):

    return numeric_value(
        row,
        [
            "time_days",
            "time",
            "days",
            "t_days",
        ],
    )


def extract_primary_row(
    rows: list[dict],
    target_time: float,
):

    if not rows:

        raise RuntimeError(
            "Plume metrics table is empty."
        )

    times = np.asarray(
        [
            time_value(
                row
            )
            for row
            in rows
        ],
        dtype=np.float64,
    )

    idx = int(
        np.argmin(
            np.abs(
                times
                -
                target_time
            )
        )
    )

    if abs(
        times[
            idx
        ]
        -
        target_time
    ) > 1.0e-6:

        raise RuntimeError(
            f"No plume metric row found at {target_time} days."
        )

    return rows[
        idx
    ]


def extract_metrics(
    row: dict,
):

    return {
        "time_days":
            time_value(
                row
            ),

        "footprint_IoU":
            numeric_value(
                row,
                [
                    "footprint_IoU",
                    "footprint_iou",
                    "Footprint IoU",
                ],
            ),

        "strong_plume_IoU":
            numeric_value(
                row,
                [
                    "strong_plume_IoU",
                    "strong_iou",
                    "strong_plume_iou",
                ],
            ),

        "core_IoU":
            numeric_value(
                row,
                [
                    "core_IoU",
                    "core_iou",
                    "high_saturation_core_IoU",
                ],
            ),

        "plume_volume_relative_error":
            numeric_value(
                row,
                [
                    "plume_volume_relative_error",
                    "plume_volume_error",
                    "volume_relative_error",
                ],
            ),

        "centroid_displacement_cells":
            numeric_value(
                row,
                [
                    "centroid_displacement_cells",
                    "centroid_offset_cells",
                    "centroid_displacement",
                    "centroid_distance_cells",
                ],
            ),

        "vertical_extent_difference_layers":
            numeric_value(
                row,
                [
                    "vertical_extent_difference_layers",
                    "vertical_extent_diff_layers",
                    "vertical_extent_difference",
                ],
            ),
    }


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "PAD-Stream V15-SG7E-R front-aware full-grid plume validation "
            "using the authoritative 11x11 SG7E implementation."
        )
    )

    parser.add_argument(
        "--workspace",
        type=str,
        default=str(
            DEFAULT_WORKSPACE
        ),
        help=(
            "Accepted 11x11 SG5C workspace containing authoritative SG7E."
        ),
    )

    args = parser.parse_args()

    workspace = Path(
        args.workspace
    ).resolve()

    source_file = (
        workspace
        /
        ORIGINAL_SG7E_FILENAME
    )

    original_sg7e_dir = (
        workspace
        /
        "output"
        /
        "V15_SG7E"
    )

    original_plume_metrics = (
        original_sg7e_dir
        /
        "V15SG7E_Plume_Metrics.csv"
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG7E-R"
    )

    print(
        "Front-Aware Full-Grid Plume / Coverage Validation"
    )

    print(
        "=" * 78
    )

    print(
        "\nNO TRAINING WILL BE PERFORMED."
    )

    print(
        "NO STREAMLINE SEED DENSITY WILL BE CHANGED."
    )

    print(
        "NO MAP-BACK OPERATOR WILL BE CHANGED."
    )

    print(
        "NO PLUME VALIDATION THRESHOLD WILL BE CHANGED."
    )

    print(
        "\nThe accepted 11x11 SG7E implementation is the plume-validation authority."
    )

    # =========================================================================
    # PRECONDITIONS
    # =========================================================================

    for path in [
        source_file,
        SG7DR_MAPBACK_FILE,
        SG7DR_WRAPPER_SUMMARY,
        original_plume_metrics,
    ]:

        if not path.exists():

            raise FileNotFoundError(
                f"Missing SG7E-R prerequisite:\n{path}"
            )

    sg7dr_wrapper = load_json(
        SG7DR_WRAPPER_SUMMARY
    )

    if not sg7dr_wrapper.get(
        "validation_passed",
        False,
    ):

        raise RuntimeError(
            "SG7D-R did not pass conservative map-back validation."
        )

    # Prefer authoritative redirected SG7D summary because SG7E may validate
    # its exact historical schema.
    if not SG7DR_AUTHORITATIVE_SUMMARY.exists():

        raise FileNotFoundError(
            "The authoritative SG7D summary generated inside V15_SG7DR "
            "was not found:\n"
            f"{SG7DR_AUTHORITATIVE_SUMMARY}"
        )

    print(
        "\nINPUT CONTRACT"
    )

    print(
        f"  Authoritative SG7E      : "
        f"{source_file}"
    )

    print(
        f"  SG7D-R map-back         : "
        f"{SG7DR_MAPBACK_FILE}"
    )

    print(
        f"  SG7D-R summary          : "
        f"{SG7DR_AUTHORITATIVE_SUMMARY}"
    )

    print(
        "  Seed density            : 11x11 unchanged"
    )

    print(
        "  Plume thresholds        : unchanged"
    )

    print(
        "  Map-back                : unchanged"
    )

    # =========================================================================
    # IMPORT AUTHORITATIVE SG7E
    # =========================================================================

    sg7e = load_module(
        source_file,
        "pad_stream_authoritative_sg7e_11x11",
    )

    if not hasattr(
        sg7e,
        "main",
    ):

        raise RuntimeError(
            "Authoritative SG7E source does not expose main()."
        )

    input_replacements = patch_sg7d_input_paths(
        sg7e,
        SG7DR_MAPBACK_FILE,
        SG7DR_AUTHORITATIVE_SUMMARY,
    )

    if not input_replacements:

        raise RuntimeError(
            "Could not identify SG7D input path globals in authoritative SG7E."
        )

    output_replacements = replace_output_paths(
        sg7e,
        original_sg7e_dir,
        OUTPUT_DIR,
    )

    print(
        "\nSG7E INPUT REDIRECTION"
    )

    for name, info in input_replacements.items():

        print(
            f"  {name:<24s}: "
            f"{info['new']}"
        )

    print(
        "\nOUTPUT REDIRECTION"
    )

    print(
        f"  Original outputs        : "
        f"{original_sg7e_dir}"
    )

    print(
        f"  SG7E-R outputs          : "
        f"{OUTPUT_DIR}"
    )

    print(
        f"  Path globals redirected : "
        f"{len(output_replacements)}"
    )

    # =========================================================================
    # RUN EXACT AUTHORITATIVE SG7E
    # =========================================================================

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "RUNNING AUTHORITATIVE SG7E ON FRONT-AWARE SG7D-R GRID"
    )

    print(
        "=" * 78
    )

    sg7e.main()

    # =========================================================================
    # LOCATE OUTPUTS
    # =========================================================================

    new_plume_metrics = locate_file(
        OUTPUT_DIR,
        "V15SG7E_Plume_Metrics.csv",
        "*Plume*Metrics*.csv",
    )

    new_summary_file = locate_file(
        OUTPUT_DIR,
        "PAD_Stream_V15SG7E_Summary.json",
        "*Summary*.json",
    )

    new_database_file = locate_file(
        OUTPUT_DIR,
        "V15SG7E_Plume_Coverage_Validation.npz",
        "*Plume*Coverage*Validation*.npz",
    )

    authoritative_summary = load_json(
        new_summary_file
    )

    authoritative_pass = recursive_pass_marker(
        authoritative_summary
    )

    # =========================================================================
    # A/B METRICS
    # =========================================================================

    original_rows = read_csv(
        original_plume_metrics
    )

    new_rows = read_csv(
        new_plume_metrics
    )

    original_primary = extract_metrics(
        extract_primary_row(
            original_rows,
            PRIMARY_TIME_DAYS,
        )
    )

    new_primary = extract_metrics(
        extract_primary_row(
            new_rows,
            PRIMARY_TIME_DAYS,
        )
    )

    original_volume = (
        original_primary[
            "plume_volume_relative_error"
        ]
    )

    new_volume = (
        new_primary[
            "plume_volume_relative_error"
        ]
    )

    absolute_improvement = (
        original_volume
        -
        new_volume
    )

    relative_improvement = (
        absolute_improvement
        /
        max(
            abs(
                original_volume
            ),
            1.0e-14,
        )
    )

    original_reference_reproduced = bool(
        abs(
            original_volume
            -
            EXPECTED_ORIGINAL_100D_VOLUME_ERROR
        )
        <=
        ORIGINAL_REFERENCE_TOL
    )

    new_primary_pass = bool(
        new_volume
        <=
        PRIMARY_VOLUME_GATE
    )

    causal_improvement = bool(
        new_volume
        <
        original_volume
    )

    print(
        "\n"
        +
        "=" * 78
    )

    print(
        "100-DAY ORIGINAL vs FRONT-AWARE PLUME"
    )

    print(
        "=" * 78
    )

    print(
        f"Original plume-volume error   : "
        f"{100.0 * original_volume:.3f}%"
    )

    print(
        f"Front-aware plume-volume error: "
        f"{100.0 * new_volume:.3f}%"
    )

    print(
        f"Absolute improvement          : "
        f"{100.0 * absolute_improvement:.3f} percentage points"
    )

    print(
        f"Relative improvement          : "
        f"{100.0 * relative_improvement:.2f}%"
    )

    print(
        f"Original footprint IoU        : "
        f"{original_primary['footprint_IoU']:.6f}"
    )

    print(
        f"Front-aware footprint IoU     : "
        f"{new_primary['footprint_IoU']:.6f}"
    )

    print(
        f"Original centroid offset      : "
        f"{original_primary['centroid_displacement_cells']:.6f} cells"
    )

    print(
        f"Front-aware centroid offset   : "
        f"{new_primary['centroid_displacement_cells']:.6f} cells"
    )

    # Full A/B table.
    comparison_rows = []

    new_by_time = {
        float(
            time_value(
                row
            )
        ):
            extract_metrics(
                row
            )
        for row
        in new_rows
    }

    for row in original_rows:

        old = extract_metrics(
            row
        )

        t = float(
            old[
                "time_days"
            ]
        )

        if t not in new_by_time:

            continue

        new = new_by_time[
            t
        ]

        comparison_rows.append(
            {
                "time_days":
                    t,

                "original_footprint_IoU":
                    old[
                        "footprint_IoU"
                    ],

                "front_aware_footprint_IoU":
                    new[
                        "footprint_IoU"
                    ],

                "original_strong_plume_IoU":
                    old[
                        "strong_plume_IoU"
                    ],

                "front_aware_strong_plume_IoU":
                    new[
                        "strong_plume_IoU"
                    ],

                "original_core_IoU":
                    old[
                        "core_IoU"
                    ],

                "front_aware_core_IoU":
                    new[
                        "core_IoU"
                    ],

                "original_plume_volume_error":
                    old[
                        "plume_volume_relative_error"
                    ],

                "front_aware_plume_volume_error":
                    new[
                        "plume_volume_relative_error"
                    ],

                "plume_volume_error_change":
                    new[
                        "plume_volume_relative_error"
                    ]
                    -
                    old[
                        "plume_volume_relative_error"
                    ],

                "original_centroid_displacement_cells":
                    old[
                        "centroid_displacement_cells"
                    ],

                "front_aware_centroid_displacement_cells":
                    new[
                        "centroid_displacement_cells"
                    ],

                "original_vertical_extent_difference_layers":
                    old[
                        "vertical_extent_difference_layers"
                    ],

                "front_aware_vertical_extent_difference_layers":
                    new[
                        "vertical_extent_difference_layers"
                    ],
            }
        )

    save_csv(
        A_B_COMPARISON_FILE,
        comparison_rows,
    )

    # =========================================================================
    # WRAPPER VALIDATION
    # =========================================================================

    all_new_volume_pass = all(
        extract_metrics(
            row
        )[
            "plume_volume_relative_error"
        ]
        <=
        PRIMARY_VOLUME_GATE
        for row
        in new_rows
    )

    all_new_footprint_pass = all(
        extract_metrics(
            row
        )[
            "footprint_IoU"
        ]
        >=
        FOOTPRINT_IOU_GATE
        for row
        in new_rows
    )

    all_new_centroid_pass = all(
        extract_metrics(
            row
        )[
            "centroid_displacement_cells"
        ]
        <=
        CENTROID_GATE_CELLS
        for row
        in new_rows
    )

    all_new_vertical_pass = all(
        abs(
            extract_metrics(
                row
            )[
                "vertical_extent_difference_layers"
            ]
        )
        <=
        VERTICAL_EXTENT_GATE_LAYERS
        for row
        in new_rows
    )

    checks = [
        (
            "SG7D-R passed before SG7E-R",
            bool(
                sg7dr_wrapper.get(
                    "validation_passed",
                    False,
                )
            ),
        ),

        (
            "Authoritative 11x11 SG7E source loaded",
            source_file.exists(),
        ),

        (
            "SG7D input redirected to SG7D-R",
            bool(
                input_replacements
            ),
        ),

        (
            "Original SG7E output directory not used",
            OUTPUT_DIR.resolve()
            !=
            original_sg7e_dir.resolve(),
        ),

        (
            "Authoritative SG7E completed",
            new_database_file.exists(),
        ),

        (
            "Original 11x11 100-day failure reference reproduced",
            original_reference_reproduced,
        ),

        (
            "Front-aware 100-day plume-volume error improves",
            causal_improvement,
        ),

        (
            "Front-aware 100-day plume-volume error <= 10%",
            new_primary_pass,
        ),

        (
            "All front-aware plume-volume errors <= 10%",
            all_new_volume_pass,
        ),

        (
            "All front-aware footprint IoU >= 0.90",
            all_new_footprint_pass,
        ),

        (
            "All front-aware centroid offsets <= 2 cells",
            all_new_centroid_pass,
        ),

        (
            "All front-aware vertical extent differences <= 2 layers",
            all_new_vertical_pass,
        ),
    ]

    wrapper_passed = all(
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
        "V15-SG7E-R CAUSAL PLUME VALIDATION"
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
    # DECISION
    # =========================================================================

    if (
        wrapper_passed
        and
        new_primary_pass
        and
        causal_improvement
    ):

        status = (
            "EARLY_TIME_PLUME_FAILURE_RESOLVED"
        )

        recommendation = (
            "The front-aware frozen PI-RNN resolves the original 11x11 "
            "100-day plume-volume failure under the exact same conservative "
            "map-back and SG7E validation contract. The causal chain from "
            "streamline threshold avoidance to Eulerian plume error is now "
            "closed. Proceed to end-to-end front-aware PAD-Stream integration "
            "validation."
        )

        next_milestone = (
            "V15-SG7F-R — End-to-End Front-Aware "
            "PAD-Stream Integration Validation"
        )

    elif (
        authoritative_pass
        and
        causal_improvement
        and
        not new_primary_pass
    ):

        status = (
            "PLUME_IMPROVED_BUT_VOLUME_GATE_NOT_YET_REACHED"
        )

        recommendation = (
            "Front-aware transport materially improves the 100-day plume but "
            "does not yet satisfy the established 10% volume gate. Do not "
            "change thresholds or map-back. Diagnose the remaining full-grid "
            "discrepancy."
        )

        next_milestone = (
            "V15-SG7E-R1 — Residual Front-to-Plume "
            "Discrepancy Audit"
        )

    else:

        status = (
            "FRONT_AWARE_PLUME_VALIDATION_REQUIRES_DIAGNOSIS"
        )

        recommendation = (
            "Do not proceed to end-to-end integration. Diagnose the failed "
            "SG7E-R gate while retaining the accepted front-aware frozen model "
            "and conservative map-back."
        )

        next_milestone = (
            "V15-SG7E-R1 — Front-Aware Full-Grid "
            "Validation Regression Audit"
        )

    # =========================================================================
    # AUDIT / SUMMARY
    # =========================================================================

    audit = {
        "milestone":
            "V15-SG7E-R",

        "authoritative_source":
            str(
                source_file
            ),

        "authoritative_workspace":
            str(
                workspace
            ),

        "SG7D_R_mapback":
            str(
                SG7DR_MAPBACK_FILE
            ),

        "SG7D_R_authoritative_summary":
            str(
                SG7DR_AUTHORITATIVE_SUMMARY
            ),

        "input_replacements":
            input_replacements,

        "output_replacements":
            output_replacements,

        "original_plume_metrics":
            str(
                original_plume_metrics
            ),

        "front_aware_plume_metrics":
            str(
                new_plume_metrics
            ),

        "100_day_original":
            original_primary,

        "100_day_front_aware":
            new_primary,

        "100_day_absolute_improvement":
            absolute_improvement,

        "100_day_relative_improvement":
            relative_improvement,

        "authoritative_summary_pass_marker":
            bool(
                authoritative_pass
            ),

        "wrapper_validation_passed":
            bool(
                wrapper_passed
            ),

        "status":
            status,

        "next_milestone":
            next_milestone,
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

    wrapper_summary = {
        "milestone":
            "V15-SG7E-R",

        "description":
            (
                "Front-aware full-grid plume / coverage validation using "
                "the accepted 11x11 SG7E implementation"
            ),

        "training_performed":
            False,

        "seed_density_changed":
            False,

        "mapback_operator_changed":
            False,

        "plume_threshold_changed":
            False,

        "original_100d_plume_volume_error":
            original_volume,

        "front_aware_100d_plume_volume_error":
            new_volume,

        "absolute_improvement":
            absolute_improvement,

        "relative_improvement":
            relative_improvement,

        "established_volume_gate":
            PRIMARY_VOLUME_GATE,

        "original_failure_resolved":
            bool(
                new_primary_pass
                and
                causal_improvement
            ),

        "validation_passed":
            bool(
                wrapper_passed
            ),

        "status":
            status,

        "recommendation":
            recommendation,

        "next_milestone":
            next_milestone,
    }

    with WRAPPER_SUMMARY_FILE.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            wrapper_summary,
            handle,
            indent=2,
        )

    # =========================================================================
    # FINAL
    # =========================================================================

    print(
        "\nSTATUS"
    )

    print(
        f"  {status}"
    )

    print(
        "\nRECOMMENDATION"
    )

    print(
        f"  {recommendation}"
    )

    print(
        "\nOUTPUTS"
    )

    print(
        f"  Directory:\n"
        f"    {OUTPUT_DIR}"
    )

    print(
        "\nAuthoritative SG7E outputs:"
    )

    print(
        f"  {new_plume_metrics.name}"
    )

    print(
        f"  {new_database_file.name}"
    )

    print(
        f"  {new_summary_file.name}"
    )

    print(
        "\nA/B comparison:"
    )

    print(
        f"  {A_B_COMPARISON_FILE.name}"
    )

    print(
        "\nAdapter audit:"
    )

    print(
        f"  {ADAPTER_AUDIT_FILE.name}"
    )

    print(
        "\nWrapper summary:"
    )

    print(
        f"  {WRAPPER_SUMMARY_FILE.name}"
    )

    print(
        "\n"
        +
        "=" * 78
    )

    if wrapper_passed:

        print(
            "V15-SG7E-R FULL-GRID PLUME VALIDATION: PASS"
        )

        print()

        print(
            f"100-day plume-volume error:"
        )

        print(
            f"  original    = {100.0 * original_volume:.3f}%"
        )

        print(
            f"  front-aware = {100.0 * new_volume:.3f}%"
        )

        print()

        print(
            f"Status:\n  {status}"
        )

        print()

        print(
            f"Next milestone:\n  {next_milestone}"
        )

    else:

        print(
            "V15-SG7E-R FULL-GRID PLUME VALIDATION: FAIL"
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

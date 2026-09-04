from __future__ import annotations

from pathlib import Path
import os
import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import time

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG5C
# Streamline Seed-Density Convergence for Eulerian Coverage
#
# CONTROLLED NUMERICAL SENSITIVITY STUDY
#
# VARIABLE CHANGED
# ----------------
#
#       injector outgoing-face seed subdivision ONLY
#
#
# FIXED
# -----
#
#       SGSim geology
#       pressure solution
#       conservative Darcy fluxes
#       Pollock streamline equations
#       TOF definition
#       SG7A classical transport
#       frozen SG7B PI-RNN
#       SG7D conservative map-back
#       SG7E plume definitions
#       SG7E-1 diagnostic definitions
#
#
# DEFAULT SEED LADDER
# -------------------
#
#       5 x 5
#       7 x 7
#       9 x 9
#
#
# OPTIONAL
# --------
#
#       11 x 11
#
# if the 7 -> 9 refinement has not established convergence / support.
#
#
# IMPORTANT SAFETY DESIGN
# -----------------------
#
# The canonical project is NEVER modified.
#
# For each seed case an isolated sibling workspace is created:
#
#       <project>_SG5C_seed_05x05
#       <project>_SG5C_seed_07x07
#       <project>_SG5C_seed_09x09
#
# The complete:
#
#       SG5
#         ->
#       SG6
#         ->
#       SG7C
#         ->
#       SG7D
#         ->
#       SG7E
#         ->
#       SG7E-1
#
# chain is recomputed inside each workspace.
#
#
# STREAMLINE CONTRACT
# -------------------
#
# SG5 currently reports:
#
#       22 outgoing injector-region faces
#
# Therefore:
#
#       N_streamlines = 22 * n^2
#
# assuming all seeds trace successfully.
#
# Thus:
#
#       5 x 5  ->   550
#       7 x 7  -> 1,078
#       9 x 9  -> 1,782
#      11 x 11 -> 2,662
#
# SG7C and SG7D are patched ONLY INSIDE EACH ISOLATED WORKSPACE so their
# expected streamline-count contracts correspond to the sensitivity case.
#
# =============================================================================


# =============================================================================
# ROOT
# =============================================================================

ROOT = Path(__file__).resolve().parent


OUTPUT_DIR = (
    ROOT
    / "output"
    / "V15_SG5C"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# PHYSICAL / SEED CONTRACT
# =============================================================================

OUTGOING_INJECTOR_FACES = 22

BASELINE_SEED_DENSITY = 7


# =============================================================================
# FORCE UTF-8 SAFE CHILD-PROCESS ENVIRONMENT
#
# Windows PowerShell / subprocess output may otherwise inherit cp1252.
# SG7E-1 prints Unicode diagnostic symbols such as Delta.
#
# This does NOT modify any physics script.
# =============================================================================

def child_process_environment():

    env = dict(
        os.environ
    )

    env[
        "PYTHONIOENCODING"
    ] = "utf-8"

    env[
        "PYTHONUTF8"
    ] = "1"

    return env

# =============================================================================
# PIPELINE FILES
# =============================================================================

SG5_SCRIPT = (
    "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
)

SG6_SCRIPT = (
    "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py"
)

SG7C_SCRIPT = (
    "PAD_Stream_V15SG7C_Frozen_PIRNN_Streamline_Deployment.py"
)

SG7D_SCRIPT = (
    "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
)

SG7E_SCRIPT = (
    "PAD_Stream_V15SG7E_FullGrid_Plume_Coverage_Validation.py"
)

SG7E1_SCRIPT = (
    "PAD_Stream_V15SG7E1_EarlyTime_Plume_Projection_Support_Audit.py"
)


PIPELINE = [
    (
        "SG5",
        SG5_SCRIPT,
    ),

    (
        "SG6",
        SG6_SCRIPT,
    ),

    (
        "SG7C",
        SG7C_SCRIPT,
    ),

    (
        "SG7D",
        SG7D_SCRIPT,
    ),

    (
        "SG7E",
        SG7E_SCRIPT,
    ),

    (
        "SG7E1",
        SG7E1_SCRIPT,
    ),
]


# =============================================================================
# OUTPUT FILE CONTRACTS
# =============================================================================

SG6_DATABASE_RELATIVE = (
    Path("output")
    / "V15_SG6"
    / "STREAMLINE_TRANSPORT_COORDINATES.npz"
)


SG7D_SUMMARY_RELATIVE = (
    Path("output")
    / "V15_SG7D"
    / "PAD_Stream_V15SG7D_Summary.json"
)


SG7E_SUMMARY_RELATIVE = (
    Path("output")
    / "V15_SG7E"
    / "PAD_Stream_V15SG7E_Summary.json"
)


SG7E1_SUMMARY_RELATIVE = (
    Path("output")
    / "V15_SG7E1"
    / "PAD_Stream_V15SG7E1_Summary.json"
)


SG7E1_INVENTORY_RELATIVE = (
    Path("output")
    / "V15_SG7E1"
    / "V15SG7E1_Covered_Uncovered_Inventory.csv"
)


SG7E1_SUPPORT_RELATIVE = (
    Path("output")
    / "V15_SG7E1"
    / "V15SG7E1_Projection_vs_Support.csv"
)


# =============================================================================
# SG5C OUTPUTS
# =============================================================================

CASE_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG5C_Seed_Case_Metrics.csv"
)


CONVERGENCE_TABLE_FILE = (
    OUTPUT_DIR
    / "V15SG5C_Successive_Convergence.csv"
)


DATABASE_FILE = (
    OUTPUT_DIR
    / "V15SG5C_Seed_Convergence.npz"
)


SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG5C_Summary.json"
)


# =============================================================================
# NUMERICAL CONVERGENCE CONTRACT
#
# These are sensitivity / convergence thresholds.
#
# They are NOT surrogate-physics acceptance gates.
# =============================================================================

CELL_COVERAGE_DELTA_MAX = 0.05

COVERED_INVENTORY_DELTA_MAX = 0.05

GRID_L1_DELTA_MAX = 0.002

FOOTPRINT_IOU_DELTA_MAX = 0.02

CENTROID_DELTA_MAX_CELLS = 0.25


# =============================================================================
# SUPPORT ADEQUACY REFERENCE
#
# SG7E-1 diagnosed the current 7x7 case as insufficiently supported.
#
# The new seed-density study therefore also asks whether the refined case
# reaches a materially stronger direct displaced-inventory support level.
# =============================================================================

DESIRED_COVERED_INVENTORY_FRACTION = 0.75


# =============================================================================
# PROJECT COPY EXCLUSIONS
# =============================================================================

EXCLUDED_TOP_LEVEL = {
    ".venv",
    ".git",
    ".idea",
    "__pycache__",
}


# These branches must be rebuilt independently inside each case workspace.
#
# Earlier frozen inputs such as:
#
#       V15_SG7A
#       V15_SG7B3
#       V15_SG7B7R
#
# are intentionally retained.
RECOMPUTED_OUTPUT_DIRS = {
    "V15_SG5",
    "V15_SG6",
    "V15_SG7C",
    "V15_SG7D",
    "V15_SG7E",
    "V15_SG7E1",
    "V15_SG5C",
    "V15_SG5C_CASE_LOGS",
}


# =============================================================================
# TRUSTED SG5 SEED VARIABLE NAMES
#
# The source run established:
#
#       FACE_SUBDIVISIONS = 7
#
# as the actual SG5 control.
#
# The broader list remains for portability, but we never globally replace
# arbitrary integers.
# =============================================================================

TRUSTED_EXACT_NAMES = {
    "face_subdivisions",
    "face_subdivision",
    "seed_subdivisions",
    "seed_subdivision",
    "seed_subdiv",
    "seed_subdivisions_per_axis",
    "seed_subdivision_per_axis",
    "n_seed_subdivisions",
    "n_seed_subdivision",
    "n_subdivisions",
    "n_subdivision",
    "n_subdiv",
    "seed_n",
    "n_seed",
}


TRUSTED_NAME_FRAGMENTS = (
    "seed_subdiv",
    "face_subdiv",
    "seed_resolution",
    "seed_density",
)


# =============================================================================
# BASIC HELPERS
# =============================================================================

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
                rows[0].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def load_json(
    path: Path,
):

    if not path.exists():

        raise FileNotFoundError(
            f"Missing JSON file:\n{path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:

        return json.load(
            handle
        )


def read_csv_rows(
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


def parse_float(
    value,
    default=np.nan,
):

    try:

        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return float(
            default
        )


def expected_streamlines_for_density(
    density: int,
):

    return int(
        OUTGOING_INJECTOR_FACES
        *
        density
        *
        density
    )


def workspace_for_density(
    density: int,
):

    return (
        ROOT.parent
        /
        (
            f"{ROOT.name}"
            f"_SG5C_seed_{density:02d}x{density:02d}"
        )
    )


# =============================================================================
# PREFLIGHT
# =============================================================================

def preflight():

    missing = []

    for (
        stage,
        filename,
    ) in PIPELINE:

        path = (
            ROOT
            /
            filename
        )

        if not path.exists():

            missing.append(
                (
                    stage,
                    path,
                )
            )

    if missing:

        lines = [
            "SG5C preflight failed.",
            "",
            "Required pipeline scripts are missing:",
        ]

        for (
            stage,
            path,
        ) in missing:

            lines.append(
                f"  {stage}: {path}"
            )

        raise FileNotFoundError(
            "\n".join(
                lines
            )
        )

    # -------------------------------------------------------------------------
    # Frozen PI-RNN
    # -------------------------------------------------------------------------

    frozen_model = (
        ROOT
        / "output"
        / "V15_SG7B7R"
        / "V15SG7B_FROZEN_Model.keras"
    )

    if not frozen_model.exists():

        raise FileNotFoundError(
            "Frozen SG7B model is missing:\n"
            f"{frozen_model}"
        )

    # -------------------------------------------------------------------------
    # Frozen SG7A classical transport
    # -------------------------------------------------------------------------

    sg7a = (
        ROOT
        / "output"
        / "V15_SG7A"
        / "FULL_PHYSICS_STREAMLINE_SATURATION.npz"
    )

    if not sg7a.exists():

        raise FileNotFoundError(
            "Frozen SG7A classical transport database is missing:\n"
            f"{sg7a}"
        )

    # -------------------------------------------------------------------------
    # SG7B3 normalization dataset
    # -------------------------------------------------------------------------

    sg7b3 = (
        ROOT
        / "output"
        / "V15_SG7B3"
        / "SG7B3_REFERENCE_DATASET.npz"
    )

    if not sg7b3.exists():

        raise FileNotFoundError(
            "SG7B3 reference dataset is missing:\n"
            f"{sg7b3}"
        )


# =============================================================================
# SAFE SG5 SEED ASSIGNMENT DISCOVERY
# =============================================================================

def trusted_seed_name(
    name: str,
):

    lower = (
        name
        .strip()
        .lower()
    )

    if lower in TRUSTED_EXACT_NAMES:

        return True

    return any(
        fragment
        in
        lower
        for fragment
        in TRUSTED_NAME_FRAGMENTS
    )


def discover_seed_assignments(
    source_text: str,
):

    candidates = []

    lines = (
        source_text
        .splitlines()
    )

    assignment_pattern = re.compile(
        r"^"
        r"(?P<indent>\s*)"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
        r"(?P<annotation>\s*:\s*[^=]+)?"
        r"\s*=\s*"
        r"(?P<value>\d+)"
        r"(?P<tail>\s*(?:#.*)?)"
        r"$"
    )

    for (
        line_index,
        line,
    ) in enumerate(
        lines
    ):

        match = (
            assignment_pattern
            .match(
                line
            )
        )

        if match is None:

            continue

        name = (
            match.group(
                "name"
            )
        )

        value = int(
            match.group(
                "value"
            )
        )

        if not trusted_seed_name(
            name
        ):

            continue

        candidates.append(
            {
                "line_index":
                    line_index,

                "line_number":
                    line_index
                    +
                    1,

                "name":
                    name,

                "value":
                    value,

                "line":
                    line,
            }
        )

    return candidates


# =============================================================================
# PATCH SG5 SEED DENSITY
#
# IMPORTANT:
#
# 7x7 is the canonical source value.  For the 7x7 sensitivity case this
# function returns a successful NO-OP rather than falsely treating the
# unchanged source line as a patch failure.
# =============================================================================

def patch_seed_density(
    sg5_path: Path,
    density: int,
):

    source = (
        sg5_path
        .read_text(
            encoding="utf-8"
        )
    )

    candidates = (
        discover_seed_assignments(
            source
        )
    )

    baseline_candidates = [
        item
        for item
        in candidates
        if item[
            "value"
        ]
        ==
        BASELINE_SEED_DENSITY
    ]

    if len(
        baseline_candidates
    ) != 1:

        print(
            "\n"
            + "=" * 78
        )

        print(
            "SG5C SAFE PATCHER COULD NOT IDENTIFY "
            "ONE UNIQUE BASELINE SEED VARIABLE"
        )

        print(
            "=" * 78
        )

        if candidates:

            print(
                "\nTrusted seed-like assignments found:"
            )

            for item in candidates:

                print(
                    f"  line {item['line_number']:5d} | "
                    f"{item['name']} = {item['value']}"
                )

        else:

            print(
                "\nNo trusted seed-variable assignments were found."
            )

        print(
            "\nSG5 has NOT been modified."
        )

        raise RuntimeError(
            "Ambiguous SG5 seed-density contract."
        )

    target = (
        baseline_candidates[0]
    )

    original_line = (
        target[
            "line"
        ]
    )

    # =========================================================================
    # BASELINE 7x7 CASE
    # =========================================================================

    if density == BASELINE_SEED_DENSITY:

        return {
            "variable":
                target[
                    "name"
                ],

            "line_number":
                target[
                    "line_number"
                ],

            "baseline_value":
                BASELINE_SEED_DENSITY,

            "new_value":
                density,

            "original_line":
                original_line,

            "new_line":
                original_line,

            "modified":
                False,

            "status":
                "BASELINE_NO_PATCH_REQUIRED",
        }

    # =========================================================================
    # NON-BASELINE CASE
    # =========================================================================

    lines = (
        source
        .splitlines()
    )

    replacement_pattern = re.compile(
        r"(?P<prefix>^\s*"
        +
        re.escape(
            target[
                "name"
            ]
        )
        +
        r"(?:\s*:\s*[^=]+)?"
        r"\s*=\s*)"
        +
        str(
            BASELINE_SEED_DENSITY
        )
        +
        r"(?P<tail>\s*(?:#.*)?$)"
    )

    new_line = (
        replacement_pattern
        .sub(
            lambda match:
                (
                    match.group(
                        "prefix"
                    )
                    +
                    str(
                        density
                    )
                    +
                    match.group(
                        "tail"
                    )
                ),
            original_line,
            count=1,
        )
    )

    if new_line == original_line:

        raise RuntimeError(
            "Trusted seed assignment was found but "
            "could not be safely rewritten."
        )

    lines[
        target[
            "line_index"
        ]
    ] = (
        new_line
    )

    sg5_path.write_text(
        "\n".join(
            lines
        )
        +
        "\n",
        encoding="utf-8",
    )

    return {
        "variable":
            target[
                "name"
            ],

        "line_number":
            target[
                "line_number"
            ],

        "baseline_value":
            BASELINE_SEED_DENSITY,

        "new_value":
            density,

        "original_line":
            original_line,

        "new_line":
            new_line,

        "modified":
            True,

        "status":
            "SEED_DENSITY_PATCHED",
    }


# =============================================================================
# PATCH DOWNSTREAM EXPECTED STREAMLINE CONTRACT
#
# Canonical SG7C / SG7D correctly describe the frozen 7x7 system:
#
#       EXPECTED_STREAMLINES = 1078
#
# SG5C deliberately changes the number of seeds.
#
# Therefore the COPIES of SG7C / SG7D in each isolated workspace receive:
#
#       EXPECTED_STREAMLINES = 22 * density^2
#
# No canonical source file is modified.
# =============================================================================

def patch_expected_streamline_contract(
    workspace: Path,
    density: int,
):

    expected_streamlines = (
        expected_streamlines_for_density(
            density
        )
    )

    target_files = [
        (
            "SG7C",
            workspace
            /
            SG7C_SCRIPT,
        ),

        (
            "SG7D",
            workspace
            /
            SG7D_SCRIPT,
        ),
    ]

    patch_records = []

    assignment_pattern = re.compile(
        r"^"
        r"(?P<indent>\s*)"
        r"EXPECTED_STREAMLINES"
        r"\s*=\s*"
        r"(?P<value>\d+)"
        r"(?P<tail>\s*(?:#.*)?)"
        r"$",
        flags=re.MULTILINE,
    )

    for (
        stage,
        path,
    ) in target_files:

        if not path.exists():

            raise FileNotFoundError(
                f"{stage} sensitivity script missing:\n"
                f"{path}"
            )

        source = (
            path
            .read_text(
                encoding="utf-8"
            )
        )

        matches = list(
            assignment_pattern
            .finditer(
                source
            )
        )

        if len(
            matches
        ) != 1:

            raise RuntimeError(
                f"{stage}: expected exactly one "
                f"EXPECTED_STREAMLINES assignment, "
                f"found {len(matches)}."
            )

        old_value = int(
            matches[0]
            .group(
                "value"
            )
        )

        def replacement(
            match,
        ):

            return (
                match.group(
                    "indent"
                )
                +
                "EXPECTED_STREAMLINES = "
                +
                str(
                    expected_streamlines
                )
                +
                match.group(
                    "tail"
                )
            )

        patched_source = (
            assignment_pattern
            .sub(
                replacement,
                source,
                count=1,
            )
        )

        path.write_text(
            patched_source,
            encoding="utf-8",
        )

        # ---------------------------------------------------------------------
        # Verify written result
        # ---------------------------------------------------------------------

        verify_text = (
            path
            .read_text(
                encoding="utf-8"
            )
        )

        verify_matches = list(
            assignment_pattern
            .finditer(
                verify_text
            )
        )

        if len(
            verify_matches
        ) != 1:

            raise RuntimeError(
                f"{stage}: failed to verify patched "
                "EXPECTED_STREAMLINES contract."
            )

        verified_value = int(
            verify_matches[0]
            .group(
                "value"
            )
        )

        if verified_value != expected_streamlines:

            raise RuntimeError(
                f"{stage}: streamline contract patch failed.\n"
                f"Expected {expected_streamlines}, "
                f"found {verified_value}."
            )

        patch_records.append(
            {
                "stage":
                    stage,

                "old_value":
                    old_value,

                "new_value":
                    expected_streamlines,

                "path":
                    str(
                        path
                    ),
            }
        )

    return {
        "density":
            density,

        "outgoing_faces":
            OUTGOING_INJECTOR_FACES,

        "expected_streamlines":
            expected_streamlines,

        "records":
            patch_records,
    }


# =============================================================================
# WORKSPACE COPY
# =============================================================================

def ignore_root_entries(
    directory: str,
    names: list[str],
):

    directory_path = Path(
        directory
    )

    ignored = []

    # -------------------------------------------------------------------------
    # Project-level development metadata / local environment
    # -------------------------------------------------------------------------

    if (
        directory_path.resolve()
        ==
        ROOT.resolve()
    ):

        for name in names:

            if name in EXCLUDED_TOP_LEVEL:

                ignored.append(
                    name
                )

    # -------------------------------------------------------------------------
    # Recomputed SG branches
    # -------------------------------------------------------------------------

    if (
        directory_path.name
        ==
        "output"
    ):

        for name in names:

            if name in RECOMPUTED_OUTPUT_DIRS:

                ignored.append(
                    name
                )

    # -------------------------------------------------------------------------
    # Python caches anywhere
    # -------------------------------------------------------------------------

    if "__pycache__" in names:

        ignored.append(
            "__pycache__"
        )

    return ignored


def prepare_workspace(
    density: int,
    overwrite: bool,
):

    workspace = (
        workspace_for_density(
            density
        )
    )

    if workspace.exists():

        if overwrite:

            print(
                "\nRemoving existing workspace:"
            )

            print(
                f"  {workspace}"
            )

            shutil.rmtree(
                workspace
            )

        else:

            raise RuntimeError(
                "Workspace already exists. "
                "Use --overwrite-workspaces to rebuild it:\n"
                f"{workspace}"
            )

    print(
        "\nCreating isolated workspace:"
    )

    print(
        f"  {workspace}"
    )

    shutil.copytree(
        ROOT,
        workspace,
        ignore=ignore_root_entries,
    )

    return workspace


# =============================================================================
# RUN ONE PIPELINE STAGE
# =============================================================================

def run_stage(
    workspace: Path,
    stage: str,
    filename: str,
):

    script = (
        workspace
        /
        filename
    )

    if not script.exists():

        raise FileNotFoundError(
            f"{stage} script missing from workspace:\n"
            f"{script}"
        )

    log_dir = (
        workspace
        / "output"
        / "V15_SG5C_CASE_LOGS"
    )

    log_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_file = (
        log_dir
        /
        f"{stage}.log"
    )

    print(
        "\n"
        + "-" * 78
    )

    print(
        f"Running {stage}"
    )

    print(
        f"  {filename}"
    )

    print(
        "-" * 78
    )

    start = (
        time.perf_counter()
    )

    process = subprocess.run(
        [
            sys.executable,
            str(
                script
            ),
        ],
        cwd=workspace,

        env=child_process_environment(),

        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,

        text=True,

        encoding="utf-8",
        errors="replace",
    )

    runtime = (
        time.perf_counter()
        -
        start
    )

    log_file.write_text(
        process.stdout,
        encoding="utf-8",
    )

    print(
        process.stdout
    )

    if process.returncode != 0:

        raise RuntimeError(
            f"{stage} failed with return code "
            f"{process.returncode}.\n"
            f"Log:\n{log_file}"
        )

    return {
        "stage":
            stage,

        "runtime_seconds":
            runtime,

        "log":
            str(
                log_file
            ),
    }


# =============================================================================
# COLLECT ONE COMPLETED CASE
# =============================================================================

def collect_case_metrics(
    workspace: Path,
    density: int,
):

    expected_streamlines = (
        expected_streamlines_for_density(
            density
        )
    )

    # =========================================================================
    # SG6 STREAMLINE COUNT
    # =========================================================================

    sg6_path = (
        workspace
        /
        SG6_DATABASE_RELATIVE
    )

    if not sg6_path.exists():

        raise FileNotFoundError(
            f"Missing SG6 database:\n"
            f"{sg6_path}"
        )

    sg6 = np.load(
        sg6_path,
        allow_pickle=True,
    )

    if "tau_end_s" in sg6:

        n_streamlines = int(
            len(
                sg6[
                    "tau_end_s"
                ]
            )
        )

    elif "streamline_id" in sg6:

        n_streamlines = int(
            len(
                sg6[
                    "streamline_id"
                ]
            )
        )

    else:

        raise KeyError(
            "Could not determine streamline count "
            "from SG6 database."
        )

    # -------------------------------------------------------------------------
    # Exact sensitivity-study count check
    # -------------------------------------------------------------------------

    if n_streamlines != expected_streamlines:

        raise RuntimeError(
            "SG5C streamline-count contract mismatch.\n"
            f"Seed density        : {density}x{density}\n"
            f"Outgoing faces      : {OUTGOING_INJECTOR_FACES}\n"
            f"Expected streamlines: {expected_streamlines}\n"
            f"Observed streamlines: {n_streamlines}"
        )

    # =========================================================================
    # SG7D SUMMARY
    # =========================================================================

    sg7d = load_json(
        workspace
        /
        SG7D_SUMMARY_RELATIVE
    )

    if not sg7d.get(
        "validation_passed",
        False,
    ):

        raise RuntimeError(
            f"SG7D did not pass for {density}x{density}."
        )

    sg7d_coverage = (
        sg7d.get(
            "coverage",
            {}
        )
    )

    sg7d_geometry = (
        sg7d.get(
            "geometry",
            {}
        )
    )

    sg7d_accuracy = (
        sg7d.get(
            "accuracy",
            {}
        )
    )

    sg7d_conservation = (
        sg7d.get(
            "conservation",
            {}
        )
    )

    # =========================================================================
    # SG7E SUMMARY
    #
    # SG7E may intentionally fail a plume morphology gate.  That does not
    # invalidate the seed case for SG5C because SG5C needs those metrics.
    # =========================================================================

    sg7e = load_json(
        workspace
        /
        SG7E_SUMMARY_RELATIVE
    )

    plume_agreement = (
        sg7e.get(
            "plume_agreement",
            {}
        )
    )

    projection_dependence = (
        sg7e.get(
            "projection_dependence",
            {}
        )
    )

    # =========================================================================
    # SG7E-1 SUMMARY
    # =========================================================================

    sg7e1 = load_json(
        workspace
        /
        SG7E1_SUMMARY_RELATIVE
    )

    if not sg7e1.get(
        "audit_passed",
        False,
    ):

        raise RuntimeError(
            f"SG7E-1 audit did not complete for "
            f"{density}x{density}."
        )

    flags = (
        sg7e1.get(
            "diagnostic_flags",
            {}
        )
    )

    # =========================================================================
    # SG7E-1 INVENTORY TABLE
    # =========================================================================

    inventory_rows = read_csv_rows(
        workspace
        /
        SG7E1_INVENTORY_RELATIVE
    )

    truth_inventory = [
        row
        for row
        in inventory_rows
        if row[
            "model"
        ]
        ==
        "SG7A"
    ]

    truth_inventory = sorted(
        truth_inventory,
        key=lambda row:
            float(
                row[
                    "time_days"
                ]
            ),
    )

    inventory_by_time = {}

    for row in truth_inventory:

        time_days = int(
            round(
                float(
                    row[
                        "time_days"
                    ]
                )
            )
        )

        inventory_by_time[
            time_days
        ] = float(
            row[
                "covered_fraction"
            ]
        )

    # =========================================================================
    # SG7E-1 SUPPORT TABLE
    # =========================================================================

    support_rows = read_csv_rows(
        workspace
        /
        SG7E1_SUPPORT_RELATIVE
    )

    support_1000_pirnn = [
        row
        for row
        in support_rows
        if (
            row[
                "model"
            ]
            ==
            "PI-RNN"
            and
            np.isclose(
                float(
                    row[
                        "time_days"
                    ]
                ),
                1000.0,
            )
        )
    ]

    support_lookup = {
        row[
            "support_bin"
        ]:
            row
        for row
        in support_1000_pirnn
    }

    n0_projection = (
        parse_float(
            support_lookup.get(
                "N=0",
                {},
            ).get(
                "projection_MAE"
            )
        )
    )

    n16_projection = (
        parse_float(
            support_lookup.get(
                "N>=16",
                {},
            ).get(
                "projection_MAE"
            )
        )
    )

    # =========================================================================
    # CASE RESULT
    # =========================================================================

    return {
        "seed_density":
            density,

        "seed_label":
            f"{density}x{density}",

        "expected_streamlines":
            expected_streamlines,

        "streamlines":
            n_streamlines,

        "cell_coverage_fraction":
            parse_float(
                sg7d_coverage.get(
                    "cell_coverage_fraction"
                )
            ),

        "covered_cells":
            int(
                sg7d_coverage.get(
                    "covered_cells",
                    0,
                )
            ),

        "streamtube_grid_PV_fraction":
            parse_float(
                sg7d_geometry.get(
                    "streamtube_to_grid_pv_fraction"
                )
            ),

        "maximum_covered_grid_L1":
            parse_float(
                sg7d_accuracy.get(
                    "maximum_covered_grid_L1"
                )
            ),

        "maximum_covered_grid_L2":
            parse_float(
                sg7d_accuracy.get(
                    "maximum_covered_grid_L2"
                )
            ),

        "maximum_inventory_projection_residual":
            parse_float(
                sg7d_conservation.get(
                    "maximum_projection_relative_residual"
                )
            ),

        "covered_inventory_100d":
            inventory_by_time.get(
                100,
                np.nan,
            ),

        "covered_inventory_250d":
            inventory_by_time.get(
                250,
                np.nan,
            ),

        "covered_inventory_500d":
            inventory_by_time.get(
                500,
                np.nan,
            ),

        "covered_inventory_1000d":
            inventory_by_time.get(
                1000,
                np.nan,
            ),

        "minimum_covered_inventory_fraction":
            parse_float(
                flags.get(
                    "minimum_SG7A_covered_inventory_fraction"
                )
            ),

        "raw_agreement_good":
            bool(
                flags.get(
                    "raw_PI_RNN_SG7A_agreement_good",
                    False,
                )
            ),

        "N0_projection_MAE_1000d":
            n0_projection,

        "N16plus_projection_MAE_1000d":
            n16_projection,

        "projection_support_hierarchy":
            bool(
                flags.get(
                    "projection_support_hierarchy",
                    False,
                )
            ),

        "minimum_footprint_IoU":
            parse_float(
                plume_agreement.get(
                    "minimum_footprint_IoU"
                )
            ),

        "maximum_plume_volume_relative_error":
            parse_float(
                plume_agreement.get(
                    "maximum_plume_volume_relative_error"
                )
            ),

        "maximum_centroid_distance_cells":
            parse_float(
                plume_agreement.get(
                    "maximum_centroid_distance_cells"
                )
            ),

        "maximum_projection_MAE":
            parse_float(
                projection_dependence.get(
                    "maximum_PI_RNN_projection_MAE"
                )
            ),

        "SG7E_validation_passed":
            bool(
                sg7e.get(
                    "validation_passed",
                    False,
                )
            ),

        "SG7E1_diagnosis":
            str(
                sg7e1.get(
                    "diagnosis",
                    "UNKNOWN",
                )
            ),
    }


# =============================================================================
# SUCCESSIVE CONVERGENCE
# =============================================================================

def build_convergence_rows(
    case_rows: list[dict],
):

    ordered = sorted(
        case_rows,
        key=lambda row:
            row[
                "seed_density"
            ],
    )

    rows = []

    for index in range(
        1,
        len(
            ordered
        ),
    ):

        coarse = (
            ordered[
                index - 1
            ]
        )

        fine = (
            ordered[
                index
            ]
        )

        delta_coverage = abs(
            fine[
                "cell_coverage_fraction"
            ]
            -
            coarse[
                "cell_coverage_fraction"
            ]
        )

        delta_inventory = abs(
            fine[
                "minimum_covered_inventory_fraction"
            ]
            -
            coarse[
                "minimum_covered_inventory_fraction"
            ]
        )

        delta_grid_L1 = abs(
            fine[
                "maximum_covered_grid_L1"
            ]
            -
            coarse[
                "maximum_covered_grid_L1"
            ]
        )

        delta_iou = abs(
            fine[
                "minimum_footprint_IoU"
            ]
            -
            coarse[
                "minimum_footprint_IoU"
            ]
        )

        delta_centroid = abs(
            fine[
                "maximum_centroid_distance_cells"
            ]
            -
            coarse[
                "maximum_centroid_distance_cells"
            ]
        )

        coverage_converged = (
            delta_coverage
            <
            CELL_COVERAGE_DELTA_MAX
        )

        inventory_converged = (
            delta_inventory
            <
            COVERED_INVENTORY_DELTA_MAX
        )

        grid_error_converged = (
            delta_grid_L1
            <
            GRID_L1_DELTA_MAX
        )

        plume_iou_converged = (
            delta_iou
            <
            FOOTPRINT_IOU_DELTA_MAX
        )

        centroid_converged = (
            delta_centroid
            <
            CENTROID_DELTA_MAX_CELLS
        )

        all_converged = (
            coverage_converged
            and
            inventory_converged
            and
            grid_error_converged
            and
            plume_iou_converged
            and
            centroid_converged
        )

        rows.append(
            {
                "coarse_seed":
                    coarse[
                        "seed_label"
                    ],

                "fine_seed":
                    fine[
                        "seed_label"
                    ],

                "coarse_streamlines":
                    coarse[
                        "streamlines"
                    ],

                "fine_streamlines":
                    fine[
                        "streamlines"
                    ],

                "delta_cell_coverage_fraction":
                    delta_coverage,

                "delta_minimum_covered_inventory_fraction":
                    delta_inventory,

                "delta_maximum_covered_grid_L1":
                    delta_grid_L1,

                "delta_minimum_footprint_IoU":
                    delta_iou,

                "delta_maximum_centroid_distance_cells":
                    delta_centroid,

                "coverage_converged":
                    coverage_converged,

                "inventory_converged":
                    inventory_converged,

                "grid_error_converged":
                    grid_error_converged,

                "plume_IoU_converged":
                    plume_iou_converged,

                "centroid_converged":
                    centroid_converged,

                "all_converged":
                    all_converged,
            }
        )

    return rows


# =============================================================================
# PLOTTING
# =============================================================================

def plot_metric(
    case_rows,
    key,
    ylabel,
    filename,
    horizontal=None,
):

    ordered = sorted(
        case_rows,
        key=lambda row:
            row[
                "seed_density"
            ],
    )

    x = [
        row[
            "seed_density"
        ]
        for row
        in ordered
    ]

    y = [
        row[
            key
        ]
        for row
        in ordered
    ]

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        x,
        y,
        marker="o",
    )

    if horizontal is not None:

        ax.axhline(
            horizontal,
            linestyle="--",
            label="Reference",
        )

        ax.legend()

    ax.set_xticks(
        x
    )

    ax.set_xlabel(
        "Seed subdivision per outgoing face axis"
    )

    ax.set_ylabel(
        ylabel
    )

    ax.set_title(
        "PAD-Stream V15-SG5C\n"
        "Seed-Density Convergence"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        /
        filename,
        dpi=300,
    )

    plt.close(
        fig
    )


def plot_streamlines(
    case_rows,
):

    ordered = sorted(
        case_rows,
        key=lambda row:
            row[
                "seed_density"
            ],
    )

    fig, ax = plt.subplots(
        figsize=(
            9,
            6,
        )
    )

    ax.plot(
        [
            row[
                "seed_density"
            ]
            for row
            in ordered
        ],
        [
            row[
                "streamlines"
            ]
            for row
            in ordered
        ],
        marker="o",
    )

    ax.set_xlabel(
        "Seed subdivision per outgoing face axis"
    )

    ax.set_ylabel(
        "Captured streamlines"
    )

    ax.set_title(
        "PAD-Stream V15-SG5C\n"
        "Streamline Sampling Growth"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG5C_Streamlines_vs_SeedDensity.png",
        dpi=300,
    )

    plt.close(
        fig
    )


# =============================================================================
# EXECUTE ONE SEED CASE
# =============================================================================

def execute_case(
    density: int,
    overwrite: bool,
):

    print(
        "\n"
        + "=" * 78
    )

    print(
        f"V15-SG5C SEED CASE: "
        f"{density}x{density}"
    )

    print(
        "=" * 78
    )

    expected_streamlines = (
        expected_streamlines_for_density(
            density
        )
    )

    # =========================================================================
    # ISOLATED WORKSPACE
    # =========================================================================

    workspace = prepare_workspace(
        density,
        overwrite,
    )

    # =========================================================================
    # PATCH SG5 SEED DENSITY
    # =========================================================================

    sg5_workspace_path = (
        workspace
        /
        SG5_SCRIPT
    )

    seed_patch = (
        patch_seed_density(
            sg5_workspace_path,
            density,
        )
    )

    print(
        "\nSG5 SEED PATCH"
    )

    print(
        f"  Variable                : "
        f"{seed_patch['variable']}"
    )

    print(
        f"  Line                    : "
        f"{seed_patch['line_number']}"
    )

    print(
        f"  Baseline                : "
        f"{seed_patch['baseline_value']}"
    )

    print(
        f"  Case                    : "
        f"{seed_patch['new_value']}"
    )

    print(
        f"  Modified                : "
        f"{seed_patch['modified']}"
    )

    print(
        f"  Status                  : "
        f"{seed_patch['status']}"
    )

    print(
        f"  Assignment              : "
        f"{seed_patch['new_line'].strip()}"
    )

    # =========================================================================
    # PATCH SG7C / SG7D STREAMLINE CONTRACT
    # =========================================================================

    streamline_contract = (
        patch_expected_streamline_contract(
            workspace,
            density,
        )
    )

    print(
        "\nSG5C DOWNSTREAM STREAMLINE CONTRACT"
    )

    print(
        f"  Outgoing faces          : "
        f"{streamline_contract['outgoing_faces']}"
    )

    print(
        f"  Seed subdivision        : "
        f"{density} x {density}"
    )

    print(
        f"  Expected streamlines    : "
        f"{expected_streamlines:,}"
    )

    for record in streamline_contract[
        "records"
    ]:

        print(
            f"  {record['stage']:4s} "
            f"EXPECTED_STREAMLINES   : "
            f"{record['old_value']:,} -> "
            f"{record['new_value']:,}"
        )

    # =========================================================================
    # RUN PIPELINE
    # =========================================================================

    stage_records = []

    case_start = (
        time.perf_counter()
    )

    for (
        stage,
        filename,
    ) in PIPELINE:

        stage_records.append(
            run_stage(
                workspace,
                stage,
                filename,
            )
        )

    case_runtime = (
        time.perf_counter()
        -
        case_start
    )

    # =========================================================================
    # COLLECT METRICS
    # =========================================================================

    metrics = (
        collect_case_metrics(
            workspace,
            density,
        )
    )

    metrics[
        "pipeline_runtime_seconds"
    ] = (
        case_runtime
    )

    metrics[
        "workspace"
    ] = (
        str(
            workspace
        )
    )

    # =========================================================================
    # CASE SUMMARY
    # =========================================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        f"SG5C CASE COMPLETE: "
        f"{density}x{density}"
    )

    print(
        "=" * 78
    )

    print(
        f"Streamlines               : "
        f"{metrics['streamlines']:,}"
    )

    print(
        f"Expected streamlines      : "
        f"{metrics['expected_streamlines']:,}"
    )

    print(
        f"Cell coverage             : "
        f"{metrics['cell_coverage_fraction']:.3%}"
    )

    print(
        f"Minimum covered inventory : "
        f"{metrics['minimum_covered_inventory_fraction']:.3%}"
    )

    print(
        f"Maximum grid L1           : "
        f"{metrics['maximum_covered_grid_L1']:.6e}"
    )

    print(
        f"N=0 projection MAE        : "
        f"{metrics['N0_projection_MAE_1000d']:.6e}"
    )

    print(
        f"Minimum footprint IoU     : "
        f"{metrics['minimum_footprint_IoU']:.6f}"
    )

    print(
        f"SG7E validation           : "
        f"{metrics['SG7E_validation_passed']}"
    )

    print(
        f"SG7E-1 diagnosis          : "
        f"{metrics['SG7E1_diagnosis']}"
    )

    print(
        f"Runtime                   : "
        f"{case_runtime:.2f} s"
    )

    return metrics


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "PAD-Stream V15-SG5C streamline seed-density "
            "convergence study."
        )
    )

    parser.add_argument(
        "--include-11",
        action="store_true",
        help=(
            "Also execute the 11x11 seed-density case."
        ),
    )

    parser.add_argument(
        "--overwrite-workspaces",
        action="store_true",
        help=(
            "Delete and rebuild existing SG5C "
            "case workspaces."
        ),
    )

    args = (
        parser.parse_args()
    )

    densities = [
        5,
        7,
        9,
    ]

    if args.include_11:

        densities.append(
            11
        )

    # =========================================================================
    # HEADER
    # =========================================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG5C"
    )

    print(
        "Streamline Seed-Density Convergence "
        "for Eulerian Coverage"
    )

    print(
        "=" * 78
    )

    print(
        "\nCONTROLLED VARIABLE:"
    )

    print(
        "  Injector outgoing-face seed subdivision only"
    )

    print(
        "\nOUTGOING INJECTOR FACES:"
    )

    print(
        f"  {OUTGOING_INJECTOR_FACES}"
    )

    print(
        "\nSEED LADDER:"
    )

    print(
        "  "
        +
        " -> ".join(
            f"{density}x{density}"
            for density
            in densities
        )
    )

    print(
        "\nEXPECTED STREAMLINES:"
    )

    for density in densities:

        print(
            f"  {density}x{density}"
            f" -> "
            f"{expected_streamlines_for_density(density):,}"
        )

    print(
        "\nORIGINAL PROJECT:"
    )

    print(
        f"  {ROOT}"
    )

    print(
        "\nPYTHON INTERPRETER:"
    )

    print(
        f"  {sys.executable}"
    )

    # =========================================================================
    # PREFLIGHT
    # =========================================================================

    preflight()

    print(
        "\nSG5C PREFLIGHT: PASS"
    )

    # =========================================================================
    # RUN ALL CASES
    # =========================================================================

    case_rows = []

    failed_cases = []

    for density in densities:

        try:

            metrics = execute_case(
                density,
                overwrite=args.overwrite_workspaces,
            )

            case_rows.append(
                metrics
            )

        except Exception as exc:

            print(
                "\n"
                + "=" * 78
            )

            print(
                f"SG5C CASE FAILED: "
                f"{density}x{density}"
            )

            print(
                "=" * 78
            )

            print(
                str(
                    exc
                )
            )

            failed_cases.append(
                {
                    "density":
                        density,

                    "seed_label":
                        f"{density}x{density}",

                    "error":
                        repr(
                            exc
                        ),
                }
            )

    # =========================================================================
    # CASE COMPLETENESS
    # =========================================================================

    required_base = {
        5,
        7,
        9,
    }

    completed = {
        int(
            row[
                "seed_density"
            ]
        )
        for row
        in case_rows
    }

    base_ladder_complete = (
        required_base
        .issubset(
            completed
        )
    )

    if not case_rows:

        raise RuntimeError(
            "No SG5C seed cases completed successfully."
        )

    # =========================================================================
    # CONVERGENCE
    # =========================================================================

    convergence_rows = (
        build_convergence_rows(
            case_rows
        )
    )

    save_csv(
        CASE_TABLE_FILE,
        case_rows,
    )

    save_csv(
        CONVERGENCE_TABLE_FILE,
        convergence_rows,
    )

    # =========================================================================
    # 7x7 -> 9x9 DECISION
    # =========================================================================

    comparison_7_9 = next(
        (
            row
            for row
            in convergence_rows
            if (
                row[
                    "coarse_seed"
                ]
                ==
                "7x7"
                and
                row[
                    "fine_seed"
                ]
                ==
                "9x9"
            )
        ),
        None,
    )

    recommended_density = None

    if not base_ladder_complete:

        convergence_decision = (
            "BASE_LADDER_INCOMPLETE"
        )

        next_milestone = (
            "Resolve failed SG5C seed case(s)"
        )

    elif comparison_7_9 is None:

        convergence_decision = (
            "7X7_TO_9X9_COMPARISON_MISSING"
        )

        next_milestone = (
            "Resolve SG5C convergence-table construction"
        )

    else:

        case_9 = next(
            row
            for row
            in case_rows
            if row[
                "seed_density"
            ]
            ==
            9
        )

        converged_7_9 = bool(
            comparison_7_9[
                "all_converged"
            ]
        )

        support_adequate_9 = (
            case_9[
                "minimum_covered_inventory_fraction"
            ]
            >=
            DESIRED_COVERED_INVENTORY_FRACTION
        )

        # ---------------------------------------------------------------------
        # 9x9 accepted
        # ---------------------------------------------------------------------

        if (
            converged_7_9
            and
            support_adequate_9
        ):

            convergence_decision = (
                "SEED_CONVERGENCE_REACHED_AT_9X9"
            )

            recommended_density = 9

            next_milestone = (
                "V15-SG7F — Freeze Deterministic "
                "Full-Grid Transport Baseline"
            )

        # ---------------------------------------------------------------------
        # Need 11x11 but it has not yet been requested
        # ---------------------------------------------------------------------

        elif not args.include_11:

            convergence_decision = (
                "11X11_REQUIRED"
            )

            next_milestone = (
                "Rerun SG5C with --include-11"
            )

        # ---------------------------------------------------------------------
        # 11x11 included
        # ---------------------------------------------------------------------

        else:

            comparison_9_11 = next(
                (
                    row
                    for row
                    in convergence_rows
                    if (
                        row[
                            "coarse_seed"
                        ]
                        ==
                        "9x9"
                        and
                        row[
                            "fine_seed"
                        ]
                        ==
                        "11x11"
                    )
                ),
                None,
            )

            case_11 = next(
                (
                    row
                    for row
                    in case_rows
                    if row[
                        "seed_density"
                    ]
                    ==
                    11
                ),
                None,
            )

            if (
                comparison_9_11 is not None
                and
                case_11 is not None
            ):

                converged_9_11 = bool(
                    comparison_9_11[
                        "all_converged"
                    ]
                )

                support_adequate_11 = (
                    case_11[
                        "minimum_covered_inventory_fraction"
                    ]
                    >=
                    DESIRED_COVERED_INVENTORY_FRACTION
                )

                if (
                    converged_9_11
                    and
                    support_adequate_11
                ):

                    convergence_decision = (
                        "SEED_CONVERGENCE_REACHED_AT_11X11"
                    )

                    recommended_density = 11

                    next_milestone = (
                        "V15-SG7F — Freeze Deterministic "
                        "Full-Grid Transport Baseline"
                    )

                else:

                    convergence_decision = (
                        "SEED_CONVERGENCE_NOT_YET_ESTABLISHED"
                    )

                    next_milestone = (
                        "Review SG5C convergence trajectory "
                        "before further refinement"
                    )

            else:

                convergence_decision = (
                    "11X11_CASE_INCOMPLETE"
                )

                next_milestone = (
                    "Resolve 11x11 SG5C case"
                )

    # =========================================================================
    # PRINT CASE MATRIX
    # =========================================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG5C CASE MATRIX"
    )

    print(
        "=" * 78
    )

    for row in sorted(
        case_rows,
        key=lambda item:
            item[
                "seed_density"
            ],
    ):

        print(
            f"\n{row['seed_label']}"
        )

        print(
            f"  Streamlines             : "
            f"{row['streamlines']:,}"
        )

        print(
            f"  Direct cell coverage    : "
            f"{row['cell_coverage_fraction']:.3%}"
        )

        print(
            f"  Min covered inventory   : "
            f"{row['minimum_covered_inventory_fraction']:.3%}"
        )

        print(
            f"  Max covered-grid L1     : "
            f"{row['maximum_covered_grid_L1']:.6e}"
        )

        print(
            f"  Min footprint IoU       : "
            f"{row['minimum_footprint_IoU']:.6f}"
        )

        print(
            f"  N=0 projection MAE      : "
            f"{row['N0_projection_MAE_1000d']:.6e}"
        )

        print(
            f"  SG7E-1 diagnosis        : "
            f"{row['SG7E1_diagnosis']}"
        )

        print(
            f"  Runtime                 : "
            f"{row['pipeline_runtime_seconds']:.2f} s"
        )

    # =========================================================================
    # PRINT SUCCESSIVE CONVERGENCE
    # =========================================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "SUCCESSIVE SEED CONVERGENCE"
    )

    print(
        "=" * 78
    )

    for row in convergence_rows:

        print(
            f"\n{row['coarse_seed']} -> "
            f"{row['fine_seed']}"
        )

        print(
            f"  Δ cell coverage         : "
            f"{row['delta_cell_coverage_fraction']:.3%}"
        )

        print(
            f"  Δ covered inventory     : "
            f"{row['delta_minimum_covered_inventory_fraction']:.3%}"
        )

        print(
            f"  Δ max grid L1           : "
            f"{row['delta_maximum_covered_grid_L1']:.6e}"
        )

        print(
            f"  Δ footprint IoU         : "
            f"{row['delta_minimum_footprint_IoU']:.6e}"
        )

        print(
            f"  Δ centroid              : "
            f"{row['delta_maximum_centroid_distance_cells']:.6e} cells"
        )

        print(
            f"  Coverage converged      : "
            f"{row['coverage_converged']}"
        )

        print(
            f"  Inventory converged     : "
            f"{row['inventory_converged']}"
        )

        print(
            f"  Grid L1 converged       : "
            f"{row['grid_error_converged']}"
        )

        print(
            f"  Plume IoU converged     : "
            f"{row['plume_IoU_converged']}"
        )

        print(
            f"  Centroid converged      : "
            f"{row['centroid_converged']}"
        )

        print(
            f"  ALL CONVERGED           : "
            f"{row['all_converged']}"
        )

    # =========================================================================
    # PLOTS
    # =========================================================================

    plot_streamlines(
        case_rows
    )

    plot_metric(
        case_rows,
        "cell_coverage_fraction",
        "Direct cell coverage fraction",
        "V15SG5C_Coverage_vs_SeedDensity.png",
    )

    plot_metric(
        case_rows,
        "minimum_covered_inventory_fraction",
        "Minimum directly supported SG7A inventory fraction",
        "V15SG5C_InventorySupport_vs_SeedDensity.png",
        horizontal=DESIRED_COVERED_INVENTORY_FRACTION,
    )

    plot_metric(
        case_rows,
        "N0_projection_MAE_1000d",
        "N=0 projection MAE at 1000 days",
        "V15SG5C_UnsupportedProjection_vs_SeedDensity.png",
    )

    plot_metric(
        case_rows,
        "maximum_covered_grid_L1",
        "Maximum covered-grid PI-RNN vs SG7A L1",
        "V15SG5C_GridError_vs_SeedDensity.png",
    )

    plot_metric(
        case_rows,
        "maximum_projection_MAE",
        "Maximum global projection MAE",
        "V15SG5C_ProjectionDependence_vs_SeedDensity.png",
    )

    # =========================================================================
    # NUMERICAL DATABASE
    # =========================================================================

    ordered_cases = sorted(
        case_rows,
        key=lambda row:
            row[
                "seed_density"
            ],
    )

    np.savez_compressed(
        DATABASE_FILE,

        seed_density=np.asarray(
            [
                row[
                    "seed_density"
                ]
                for row
                in ordered_cases
            ],
            dtype=np.int32,
        ),

        expected_streamline_count=np.asarray(
            [
                row[
                    "expected_streamlines"
                ]
                for row
                in ordered_cases
            ],
            dtype=np.int32,
        ),

        observed_streamline_count=np.asarray(
            [
                row[
                    "streamlines"
                ]
                for row
                in ordered_cases
            ],
            dtype=np.int32,
        ),

        cell_coverage_fraction=np.asarray(
            [
                row[
                    "cell_coverage_fraction"
                ]
                for row
                in ordered_cases
            ],
            dtype=np.float64,
        ),

        minimum_covered_inventory_fraction=np.asarray(
            [
                row[
                    "minimum_covered_inventory_fraction"
                ]
                for row
                in ordered_cases
            ],
            dtype=np.float64,
        ),

        maximum_covered_grid_L1=np.asarray(
            [
                row[
                    "maximum_covered_grid_L1"
                ]
                for row
                in ordered_cases
            ],
            dtype=np.float64,
        ),

        minimum_footprint_IoU=np.asarray(
            [
                row[
                    "minimum_footprint_IoU"
                ]
                for row
                in ordered_cases
            ],
            dtype=np.float64,
        ),

        N0_projection_MAE_1000d=np.asarray(
            [
                row[
                    "N0_projection_MAE_1000d"
                ]
                for row
                in ordered_cases
            ],
            dtype=np.float64,
        ),

        maximum_projection_MAE=np.asarray(
            [
                row[
                    "maximum_projection_MAE"
                ]
                for row
                in ordered_cases
            ],
            dtype=np.float64,
        ),
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    summary = {
        "milestone":
            "V15-SG5C",

        "description":
            (
                "Controlled streamline seed-density convergence "
                "for Eulerian SGSim plume support"
            ),

        "variable_changed":
            (
                "injector outgoing-face seed subdivision only"
            ),

        "outgoing_injector_faces":
            OUTGOING_INJECTOR_FACES,

        "seed_densities":
            densities,

        "expected_streamline_counts": {
            f"{density}x{density}":
                expected_streamlines_for_density(
                    density
                )
            for density
            in densities
        },

        "base_ladder_complete":
            bool(
                base_ladder_complete
            ),

        "failed_cases":
            failed_cases,

        "convergence_contract": {
            "maximum_cell_coverage_change":
                CELL_COVERAGE_DELTA_MAX,

            "maximum_covered_inventory_change":
                COVERED_INVENTORY_DELTA_MAX,

            "maximum_grid_L1_change":
                GRID_L1_DELTA_MAX,

            "maximum_footprint_IoU_change":
                FOOTPRINT_IOU_DELTA_MAX,

            "maximum_centroid_change_cells":
                CENTROID_DELTA_MAX_CELLS,
        },

        "support_reference": {
            "desired_minimum_covered_inventory_fraction":
                DESIRED_COVERED_INVENTORY_FRACTION,
        },

        "decision":
            convergence_decision,

        "recommended_seed_density":
            recommended_density,

        "next_milestone":
            next_milestone,

        "original_project_modified":
            False,
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
    # FINAL DECISION
    # =========================================================================

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG5C SEED-DENSITY CONVERGENCE DECISION"
    )

    print(
        "=" * 78
    )

    print(
        "Decision:"
    )

    print(
        f"  {convergence_decision}"
    )

    if recommended_density is not None:

        print(
            "\nRecommended seed density:"
        )

        print(
            f"  {recommended_density}x"
            f"{recommended_density}"
        )

    print(
        "\nNext milestone:"
    )

    print(
        f"  {next_milestone}"
    )

    print(
        "\nCanonical project modified:"
    )

    print(
        "  False"
    )

    print(
        "=" * 78
    )

    # =========================================================================
    # OUTPUT LIST
    # =========================================================================

    print(
        "\nOUTPUTS"
    )

    print(
        f"  Directory:"
    )

    print(
        f"    {OUTPUT_DIR}"
    )

    print(
        "\nTables:"
    )

    print(
        f"  {CASE_TABLE_FILE.name}"
    )

    print(
        f"  {CONVERGENCE_TABLE_FILE.name}"
    )

    print(
        "\nDatabase:"
    )

    print(
        f"  {DATABASE_FILE.name}"
    )

    print(
        "\nDiagnostics:"
    )

    print(
        "  V15SG5C_Streamlines_vs_SeedDensity.png"
    )

    print(
        "  V15SG5C_Coverage_vs_SeedDensity.png"
    )

    print(
        "  V15SG5C_InventorySupport_vs_SeedDensity.png"
    )

    print(
        "  V15SG5C_UnsupportedProjection_vs_SeedDensity.png"
    )

    print(
        "  V15SG5C_GridError_vs_SeedDensity.png"
    )

    print(
        "  V15SG5C_ProjectionDependence_vs_SeedDensity.png"
    )

    print(
        "\nSummary:"
    )

    print(
        f"  {SUMMARY_FILE.name}"
    )


if __name__ == "__main__":
    main()
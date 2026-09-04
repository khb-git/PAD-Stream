from pathlib import Path
import json

import numpy as np
import matplotlib.pyplot as plt


# ======================================================================
# PAD-Stream Version 15-SG6
# Streamline Time-of-Flight and Transport Coordinates
#
# PURPOSE
# -------
# 1. Load frozen SG5 exact Pollock trajectories.
# 2. Treat Pollock cumulative particle time as physical TOF:
#
#       tau = integral(phi / |u| ds)
#
#    because SG5 tracked using pore velocity v = u / phi.
#
# 3. Calculate cumulative geometric path length.
# 4. Construct normalized transport coordinate:
#
#       xi = tau / tau_end
#
# 5. Resample every streamline to a common transport grid.
# 6. Preserve streamline volumetric weights.
# 7. Calculate producer-specific and global TOF statistics.
#
# NO Buckley-Leverett transport is solved in SG6.
# ======================================================================


# ----------------------------------------------------------------------
# PATHS
# ----------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent

SG5_DIR = ROOT / "output" / "V15_SG5"

STREAMLINE_FILE = (
    SG5_DIR / "STREAMLINES_POLLOCK.npz"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG6"
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

TRANSPORT_FILE = (
    OUTPUT_DIR
    / "STREAMLINE_TRANSPORT_COORDINATES.npz"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG6_Summary.json"
)


# ----------------------------------------------------------------------
# CONSTANTS
# ----------------------------------------------------------------------

DAY_TO_S = 86400.0
FT_TO_M = 0.3048
M_TO_FT = 1.0 / FT_TO_M

POROSITY = 0.20

# Common normalized transport coordinate.
N_XI = 201

XI_GRID = np.linspace(
    0.0,
    1.0,
    N_XI,
)

PRODUCER_NAMES = [
    "PROD_SW",
    "PROD_SE",
    "PROD_NW",
    "PROD_NE",
]


# ======================================================================
# LOAD SG5
# ======================================================================

def load_sg5():

    if not STREAMLINE_FILE.exists():

        raise FileNotFoundError(
            f"Could not find frozen SG5 file:\n"
            f"{STREAMLINE_FILE}"
        )

    data = np.load(
        STREAMLINE_FILE,
    )

    required = [
        "points_m",
        "cumulative_times_s",
        "offsets",
        "weights_m3_s",
        "travel_times_s",
        "statuses",
        "producers",
    ]

    for key in required:

        if key not in data:

            raise KeyError(
                f"Missing SG5 field: {key}"
            )

    return data


# ======================================================================
# RECONSTRUCT INDIVIDUAL STREAMLINES
# ======================================================================

def reconstruct_streamlines(data):

    points = data["points_m"]
    times = data["cumulative_times_s"]
    offsets = data["offsets"]

    weights = data["weights_m3_s"]
    travel_times = data["travel_times_s"]
    statuses = data["statuses"]
    producers = data["producers"]

    n_streamlines = (
        len(offsets) - 1
    )

    streamlines = []

    for s in range(n_streamlines):

        start = offsets[s]
        stop = offsets[s + 1]

        pts = points[start:stop]
        tau = times[start:stop]

        streamlines.append({
            "id": s,
            "points_m": pts,
            "tau_s": tau,
            "weight_m3_s":
                float(weights[s]),
            "tau_end_s":
                float(travel_times[s]),
            "status":
                str(statuses[s]),
            "producer":
                str(producers[s]),
        })

    return streamlines


# ======================================================================
# PATH LENGTH
# ======================================================================

def cumulative_path_length(points):

    if len(points) < 2:

        return np.zeros(
            len(points),
            dtype=float,
        )

    ds = np.linalg.norm(
        np.diff(
            points,
            axis=0,
        ),
        axis=1,
    )

    length = np.concatenate(
        [
            np.array([0.0]),
            np.cumsum(ds),
        ]
    )

    return length


# ======================================================================
# CLEAN / VALIDATE ONE STREAMLINE
# ======================================================================

def prepare_streamline(streamline):

    points = streamline["points_m"]
    tau = streamline["tau_s"]

    if len(points) != len(tau):

        raise ValueError(
            f"Streamline {streamline['id']} "
            f"point/time length mismatch."
        )

    if len(points) < 2:

        raise ValueError(
            f"Streamline {streamline['id']} "
            f"contains fewer than two points."
        )

    if not np.all(
        np.isfinite(points)
    ):

        raise ValueError(
            "Non-finite streamline coordinates."
        )

    if not np.all(
        np.isfinite(tau)
    ):

        raise ValueError(
            "Non-finite TOF coordinates."
        )

    # Numerical duplication can occur when a face/corner is crossed.
    # Keep strictly increasing TOF entries for interpolation.
    keep = np.ones(
        len(tau),
        dtype=bool,
    )

    keep[1:] = (
        np.diff(tau) > 0.0
    )

    points_clean = points[keep]
    tau_clean = tau[keep]

    if len(tau_clean) < 2:

        raise ValueError(
            f"Streamline {streamline['id']} "
            f"has insufficient unique TOF points."
        )

    tau_end = tau_clean[-1]

    if tau_end <= 0.0:

        raise ValueError(
            "Non-positive terminal TOF."
        )

    xi = (
        tau_clean
        / tau_end
    )

    path_length = (
        cumulative_path_length(
            points_clean
        )
    )

    return (
        points_clean,
        tau_clean,
        xi,
        path_length,
    )


# ======================================================================
# COMMON TRANSPORT GRID
# ======================================================================

def resample_streamline(
    points,
    tau,
    xi,
    path_length,
):

    x = np.interp(
        XI_GRID,
        xi,
        points[:, 0],
    )

    y = np.interp(
        XI_GRID,
        xi,
        points[:, 1],
    )

    z = np.interp(
        XI_GRID,
        xi,
        points[:, 2],
    )

    tau_grid = np.interp(
        XI_GRID,
        xi,
        tau,
    )

    length_grid = np.interp(
        XI_GRID,
        xi,
        path_length,
    )

    return (
        x,
        y,
        z,
        tau_grid,
        length_grid,
    )


# ======================================================================
# BUILD TRANSPORT DATABASE
# ======================================================================

def build_transport_database(
    streamlines,
):

    completed = [
        s
        for s in streamlines
        if s["status"] == "PRODUCER"
    ]

    n = len(completed)

    xyz = np.zeros(
        (n, N_XI, 3),
        dtype=float,
    )

    tau = np.zeros(
        (n, N_XI),
        dtype=float,
    )

    path_length = np.zeros(
        (n, N_XI),
        dtype=float,
    )

    weights = np.zeros(
        n,
        dtype=float,
    )

    tau_end = np.zeros(
        n,
        dtype=float,
    )

    producer = np.empty(
        n,
        dtype="U32",
    )

    original_ids = np.zeros(
        n,
        dtype=np.int64,
    )

    for row, s in enumerate(
        completed
    ):

        (
            points_clean,
            tau_clean,
            xi_clean,
            length_clean,
        ) = prepare_streamline(
            s
        )

        (
            x,
            y,
            z,
            tau_grid,
            length_grid,
        ) = resample_streamline(
            points_clean,
            tau_clean,
            xi_clean,
            length_clean,
        )

        xyz[row, :, 0] = x
        xyz[row, :, 1] = y
        xyz[row, :, 2] = z

        tau[row] = tau_grid
        path_length[row] = (
            length_grid
        )

        weights[row] = (
            s["weight_m3_s"]
        )

        tau_end[row] = (
            tau_clean[-1]
        )

        producer[row] = (
            s["producer"]
        )

        original_ids[row] = (
            s["id"]
        )

    return {
        "xyz_m":
            xyz,

        "tau_s":
            tau,

        "xi":
            XI_GRID.copy(),

        "path_length_m":
            path_length,

        "weights_m3_s":
            weights,

        "tau_end_s":
            tau_end,

        "producer":
            producer,

        "streamline_id":
            original_ids,
    }


# ======================================================================
# WEIGHTED STATISTICS
# ======================================================================

def weighted_mean(
    values,
    weights,
):

    return float(
        np.sum(
            values * weights
        )
        /
        np.sum(weights)
    )


def weighted_quantile(
    values,
    weights,
    quantile,
):

    order = np.argsort(
        values
    )

    values_sorted = (
        values[order]
    )

    weights_sorted = (
        weights[order]
    )

    cumulative = np.cumsum(
        weights_sorted
    )

    cumulative /= (
        cumulative[-1]
    )

    return float(
        np.interp(
            quantile,
            cumulative,
            values_sorted,
        )
    )


# ======================================================================
# VALIDATION
# ======================================================================

def validate_transport(db):

    xyz = db["xyz_m"]
    tau = db["tau_s"]
    xi = db["xi"]

    weights = db[
        "weights_m3_s"
    ]

    tau_end = db[
        "tau_end_s"
    ]

    producers = db[
        "producer"
    ]

    checks = []

    checks.append(
        (
            "At least one completed streamline",
            len(tau_end) > 0,
        )
    )

    checks.append(
        (
            "All TOF values finite",
            np.all(
                np.isfinite(tau)
            ),
        )
    )

    checks.append(
        (
            "All XYZ values finite",
            np.all(
                np.isfinite(xyz)
            ),
        )
    )

    checks.append(
        (
            "All streamline weights positive",
            np.all(
                weights > 0.0
            ),
        )
    )

    checks.append(
        (
            "All terminal TOFs positive",
            np.all(
                tau_end > 0.0
            ),
        )
    )

    checks.append(
        (
            "Normalized coordinate starts at zero",
            np.isclose(
                xi[0],
                0.0,
            ),
        )
    )

    checks.append(
        (
            "Normalized coordinate ends at one",
            np.isclose(
                xi[-1],
                1.0,
            ),
        )
    )

    checks.append(
        (
            "TOF monotonic along every streamline",
            np.all(
                np.diff(
                    tau,
                    axis=1,
                )
                >= -1.0e-12
            ),
        )
    )

    checks.append(
        (
            "TOF endpoint matches tau_end",
            np.allclose(
                tau[:, -1],
                tau_end,
                rtol=1.0e-10,
                atol=1.0e-8,
            ),
        )
    )

    checks.append(
        (
            "All four producers represented",
            all(
                np.any(
                    producers
                    == name
                )
                for name
                in PRODUCER_NAMES
            ),
        )
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG6 TOF / TRANSPORT VALIDATION"
    )

    print(
        "=" * 78
    )

    all_passed = True

    for description, passed in checks:

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"[{status:4s}] "
            f"{description}"
        )

        if not passed:
            all_passed = False

    print(
        "=" * 78
    )

    if not all_passed:

        raise RuntimeError(
            "V15-SG6 validation failed."
        )

    print(
        "V15-SG6 TOF / TRANSPORT VALIDATION: PASS"
    )


# ======================================================================
# SUMMARY STATISTICS
# ======================================================================

def calculate_statistics(db):

    tau_days = (
        db["tau_end_s"]
        / DAY_TO_S
    )

    weights = db[
        "weights_m3_s"
    ]

    producers = db[
        "producer"
    ]

    path_end_ft = (
        db["path_length_m"][
            :,
            -1,
        ]
        * M_TO_FT
    )

    stats = {
        "global": {
            "streamlines":
                int(
                    len(tau_days)
                ),

            "total_weight_m3_day":
                float(
                    weights.sum()
                    * DAY_TO_S
                ),

            "tof_min_days":
                float(
                    tau_days.min()
                ),

            "tof_max_days":
                float(
                    tau_days.max()
                ),

            "tof_mean_days":
                float(
                    tau_days.mean()
                ),

            "tof_median_days":
                float(
                    np.median(
                        tau_days
                    )
                ),

            "tof_flux_weighted_mean_days":
                weighted_mean(
                    tau_days,
                    weights,
                ),

            "tof_flux_weighted_p10_days":
                weighted_quantile(
                    tau_days,
                    weights,
                    0.10,
                ),

            "tof_flux_weighted_p50_days":
                weighted_quantile(
                    tau_days,
                    weights,
                    0.50,
                ),

            "tof_flux_weighted_p90_days":
                weighted_quantile(
                    tau_days,
                    weights,
                    0.90,
                ),

            "path_length_mean_ft":
                float(
                    path_end_ft.mean()
                ),

            "path_length_min_ft":
                float(
                    path_end_ft.min()
                ),

            "path_length_max_ft":
                float(
                    path_end_ft.max()
                ),
        },

        "producers": {},
    }

    for name in PRODUCER_NAMES:

        mask = (
            producers == name
        )

        p_tau = tau_days[mask]
        p_weights = weights[mask]

        stats[
            "producers"
        ][name] = {
            "streamlines":
                int(
                    mask.sum()
                ),

            "weight_m3_day":
                float(
                    p_weights.sum()
                    * DAY_TO_S
                ),

            "tof_min_days":
                float(
                    p_tau.min()
                ),

            "tof_max_days":
                float(
                    p_tau.max()
                ),

            "tof_mean_days":
                float(
                    p_tau.mean()
                ),

            "tof_flux_weighted_mean_days":
                weighted_mean(
                    p_tau,
                    p_weights,
                ),
        }

    return stats


# ======================================================================
# PLOTS
# ======================================================================

def plot_weighted_tof_distribution(
    db,
):

    tau_days = (
        db["tau_end_s"]
        / DAY_TO_S
    )

    weights_day = (
        db["weights_m3_s"]
        * DAY_TO_S
    )

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    ax.hist(
        tau_days,
        bins=40,
        weights=weights_day,
    )

    ax.set_xlabel(
        "Terminal time-of-flight (days)"
    )

    ax.set_ylabel(
        "Streamline flow weight (m³/day)"
    )

    ax.set_title(
        "PAD-Stream V15-SG6\n"
        "Flux-Weighted Time-of-Flight Distribution"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG6_TOF_WeightedHistogram.png",
        dpi=300,
    )

    plt.close(fig)


def plot_tof_by_producer(
    db,
):

    producers = db[
        "producer"
    ]

    tau_days = (
        db["tau_end_s"]
        / DAY_TO_S
    )

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    datasets = []

    labels = []

    for name in PRODUCER_NAMES:

        datasets.append(
            tau_days[
                producers == name
            ]
        )

        labels.append(name)

    ax.boxplot(
        datasets,
        tick_labels=labels,
        showfliers=True,
    )

    ax.set_ylabel(
        "Terminal TOF (days)"
    )

    ax.set_title(
        "PAD-Stream V15-SG6\n"
        "Time-of-Flight by Producer"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG6_TOF_ByProducer.png",
        dpi=300,
    )

    plt.close(fig)


def plot_transport_coordinates(
    db,
):

    tau_days = (
        db["tau_s"]
        / DAY_TO_S
    )

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    # Plot representative subset
    stride = max(
        1,
        len(tau_days) // 80,
    )

    for i in range(
        0,
        len(tau_days),
        stride,
    ):

        ax.plot(
            db["xi"],
            tau_days[i],
            linewidth=0.7,
            alpha=0.5,
        )

    ax.set_xlabel(
        r"Normalized transport coordinate $\xi$"
    )

    ax.set_ylabel(
        r"Time-of-flight $\tau$ (days)"
    )

    ax.set_title(
        "PAD-Stream V15-SG6\n"
        "Streamline Transport Coordinates"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG6_Tau_vs_Xi.png",
        dpi=300,
    )

    plt.close(fig)


def plot_pathlength_vs_tof(
    db,
):

    length_ft = (
        db["path_length_m"][
            :,
            -1,
        ]
        * M_TO_FT
    )

    tau_days = (
        db["tau_end_s"]
        / DAY_TO_S
    )

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    ax.scatter(
        length_ft,
        tau_days,
        s=10,
        alpha=0.5,
    )

    ax.set_xlabel(
        "Total streamline length (ft)"
    )

    ax.set_ylabel(
        "Terminal TOF (days)"
    )

    ax.set_title(
        "PAD-Stream V15-SG6\n"
        "Streamline Length vs Time-of-Flight"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG6_PathLength_vs_TOF.png",
        dpi=300,
    )

    plt.close(fig)


# ======================================================================
# SAVE
# ======================================================================

def save_database(db):

    np.savez_compressed(
        TRANSPORT_FILE,

        xyz_m=
            db["xyz_m"],

        tau_s=
            db["tau_s"],

        xi=
            db["xi"],

        path_length_m=
            db["path_length_m"],

        weights_m3_s=
            db["weights_m3_s"],

        tau_end_s=
            db["tau_end_s"],

        producer=
            db["producer"],

        streamline_id=
            db["streamline_id"],
    )


def save_summary(stats):

    summary = {
        "milestone":
            "V15-SG6",

        "description":
            "Streamline time-of-flight and transport coordinates",

        "status":
            "PASS",

        "source":
            "Frozen V15-SG5 exact Pollock trajectories",

        "porosity":
            POROSITY,

        "tof_definition":
            "tau = integral(phi / |u| ds)",

        "pollock_time_interpretation":
            (
                "SG5 used pore velocity u/phi, "
                "therefore cumulative Pollock time "
                "is physical streamline TOF."
            ),

        "normalized_transport_coordinate":
            "xi = tau / tau_end",

        "common_transport_nodes":
            N_XI,

        "statistics":
            stats,

        "next_milestone":
            (
                "V15-SG7 - Buckley-Leverett transport "
                "on SGSim streamline TOF coordinates"
            ),
    }

    with open(
        SUMMARY_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            summary,
            f,
            indent=2,
        )


# ======================================================================
# MAIN
# ======================================================================

def main():

    print(
        "\n"
        + "=" * 78
    )

    print(
        "PAD-Stream Version 15-SG6"
    )

    print(
        "Streamline Time-of-Flight and Transport Coordinates"
    )

    print(
        "=" * 78
    )

    data = load_sg5()

    streamlines = (
        reconstruct_streamlines(
            data
        )
    )

    print(
        f"\nSG5 streamlines loaded  : "
        f"{len(streamlines):,}"
    )

    completed = sum(
        s["status"]
        == "PRODUCER"
        for s in streamlines
    )

    print(
        f"Producer-captured       : "
        f"{completed:,}"
    )

    db = build_transport_database(
        streamlines
    )

    print(
        f"\nCommon xi nodes         : "
        f"{N_XI}"
    )

    print(
        f"Transport XYZ shape     : "
        f"{db['xyz_m'].shape}"
    )

    print(
        f"TOF array shape         : "
        f"{db['tau_s'].shape}"
    )

    validate_transport(
        db
    )

    stats = calculate_statistics(
        db
    )

    g = stats["global"]

    print(
        "\nGLOBAL TOF STATISTICS"
    )

    print(
        f"  Streamlines            : "
        f"{g['streamlines']:,}"
    )

    print(
        f"  Total flow weight      : "
        f"{g['total_weight_m3_day']:.6f} m3/day"
    )

    print(
        f"  Min TOF                : "
        f"{g['tof_min_days']:.3f} days"
    )

    print(
        f"  Median TOF             : "
        f"{g['tof_median_days']:.3f} days"
    )

    print(
        f"  Mean TOF               : "
        f"{g['tof_mean_days']:.3f} days"
    )

    print(
        f"  Max TOF                : "
        f"{g['tof_max_days']:.3f} days"
    )

    print(
        f"  Flux-weighted mean TOF : "
        f"{g['tof_flux_weighted_mean_days']:.3f} days"
    )

    print(
        f"  Flux-weighted P10/P50/P90:"
        f" "
        f"{g['tof_flux_weighted_p10_days']:.3f} / "
        f"{g['tof_flux_weighted_p50_days']:.3f} / "
        f"{g['tof_flux_weighted_p90_days']:.3f} days"
    )

    print(
        "\nTOF BY PRODUCER"
    )

    for name in PRODUCER_NAMES:

        p = stats[
            "producers"
        ][name]

        print(
            f"  {name:10s}: "
            f"N={p['streamlines']:4d}, "
            f"Q={p['weight_m3_day']:9.3f} m3/day, "
            f"weighted mean TOF="
            f"{p['tof_flux_weighted_mean_days']:.3f} days"
        )

    save_database(
        db
    )

    plot_weighted_tof_distribution(
        db
    )

    plot_tof_by_producer(
        db
    )

    plot_transport_coordinates(
        db
    )

    plot_pathlength_vs_tof(
        db
    )

    save_summary(
        stats
    )

    print(
        "\nOUTPUTS"
    )

    print(
        f"  {TRANSPORT_FILE}"
    )

    print(
        f"  {SUMMARY_FILE}"
    )

    print(
        "\nGenerated diagnostics:"
    )

    print(
        "  V15SG6_TOF_WeightedHistogram.png"
    )

    print(
        "  V15SG6_TOF_ByProducer.png"
    )

    print(
        "  V15SG6_Tau_vs_Xi.png"
    )

    print(
        "  V15SG6_PathLength_vs_TOF.png"
    )

    print(
        "\n"
        + "=" * 78
    )

    print(
        "V15-SG6 COMPLETED SUCCESSFULLY"
    )

    print(
        "Next milestone: V15-SG7"
    )

    print(
        "Buckley-Leverett transport on "
        "SGSim streamline TOF coordinates"
    )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()
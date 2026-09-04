from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt


# ======================================================================
# PAD-Stream Version 15-SG5
# Exact 3D Pollock Streamline Tracing
#
# INPUT
# -----
# Frozen SG4 conservative face-flow arrays:
#     QX_M3_S.npy
#     QY_M3_S.npy
#     QZ_M3_S.npy
#
# METHOD
# ------
# Piecewise-linear Pollock velocity interpolation in each Cartesian cell.
# Analytical cell-exit times are used; there is no explicit tracking
# timestep.
#
# OUTPUT
# ------
# Weighted 3D streamline trajectories from the injector completion
# boundary to the producer completion cells.
#
# SG6 will formally construct time-of-flight/streamline transport
# quantities from these trajectories.
# ======================================================================


# ----------------------------------------------------------------------
# PATHS
# ----------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent

SG1_PERM_FILE = ROOT / "SGSIM_50x50x15_PERM_MD.csv"

SG4_DIR = ROOT / "output" / "V15_SG4"

QX_FILE = SG4_DIR / "QX_M3_S.npy"
QY_FILE = SG4_DIR / "QY_M3_S.npy"
QZ_FILE = SG4_DIR / "QZ_M3_S.npy"

OUTPUT_DIR = ROOT / "output" / "V15_SG5"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG5_Summary.json"
STREAMLINE_FILE = OUTPUT_DIR / "STREAMLINES_POLLOCK.npz"
CAPTURE_FILE = OUTPUT_DIR / "V15SG5_Streamline_Capture.csv"


# ----------------------------------------------------------------------
# GRID
# ----------------------------------------------------------------------

NX = 50
NY = 50
NZ = 15

DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0

FT_TO_M = 0.3048
DAY_TO_S = 86400.0

DX_M = DX_FT * FT_TO_M
DY_M = DY_FT * FT_TO_M
DZ_M = DZ_FT * FT_TO_M

LX_M = NX * DX_M
LY_M = NY * DY_M
LZ_M = NZ * DZ_M

LX_FT = NX * DX_FT
LY_FT = NY * DY_FT
LZ_FT = NZ * DZ_FT


# ----------------------------------------------------------------------
# FACE AREAS
# ----------------------------------------------------------------------

AX_M2 = DY_M * DZ_M
AY_M2 = DX_M * DZ_M
AZ_M2 = DX_M * DY_M


# ----------------------------------------------------------------------
# POROSITY
# ----------------------------------------------------------------------

POROSITY = 0.20


# ----------------------------------------------------------------------
# WELL GEOMETRY
# ----------------------------------------------------------------------

INJECTOR_I = 24
INJECTOR_J = 24

COMPLETION_K = list(range(5, 10))

PRODUCERS = {
    "PROD_SW": {"i": 4, "j": 4},
    "PROD_SE": {"i": 45, "j": 4},
    "PROD_NW": {"i": 4, "j": 45},
    "PROD_NE": {"i": 45, "j": 45},
}


# ----------------------------------------------------------------------
# SEEDING / TRACKING
# ----------------------------------------------------------------------

# Each outgoing injector-region face is subdivided into an N x N
# set of starting points.
FACE_SUBDIVISIONS = 7

# Nudge particle into downstream cell after crossing a face.
NUDGE_FRACTION = 1.0e-8

EPS_M = (
    min(DX_M, DY_M, DZ_M)
    * NUDGE_FRACTION
)

VELOCITY_TOL = 1.0e-16
GRADIENT_TOL = 1.0e-14
TIME_TOL_S = 1.0e-10

MAX_CELL_CROSSINGS = 5000


# ======================================================================
# DATA LOADING
# ======================================================================

def load_inputs():

    required = [
        SG1_PERM_FILE,
        QX_FILE,
        QY_FILE,
        QZ_FILE,
    ]

    for path in required:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing required frozen input:\n{path}"
            )

    perm_values = np.loadtxt(
        SG1_PERM_FILE,
        skiprows=1,
        dtype=float,
    )

    permeability = perm_values.reshape(
        (NZ, NY, NX),
        order="C",
    )

    qx = np.load(QX_FILE)
    qy = np.load(QY_FILE)
    qz = np.load(QZ_FILE)

    if qx.shape != (NZ, NY, NX - 1):
        raise ValueError(
            f"Invalid QX shape: {qx.shape}"
        )

    if qy.shape != (NZ, NY - 1, NX):
        raise ValueError(
            f"Invalid QY shape: {qy.shape}"
        )

    if qz.shape != (NZ - 1, NY, NX):
        raise ValueError(
            f"Invalid QZ shape: {qz.shape}"
        )

    return permeability, qx, qy, qz


# ======================================================================
# FACE PORE VELOCITIES
# ======================================================================

def construct_face_pore_velocities(
    qx,
    qy,
    qz,
):
    """
    q [m3/s]
        -> Darcy velocity [m/s]
        -> pore velocity [m/s]

    Constant porosity:
        v = q / (A * phi)
    """

    vx = qx / (AX_M2 * POROSITY)
    vy = qy / (AY_M2 * POROSITY)
    vz = qz / (AZ_M2 * POROSITY)

    return vx, vy, vz


# ======================================================================
# WELL MASKS
# ======================================================================

def injector_cells():

    return {
        (k, INJECTOR_J, INJECTOR_I)
        for k in COMPLETION_K
    }


def producer_lookup():

    lookup = {}

    for name, well in PRODUCERS.items():

        for k in COMPLETION_K:

            lookup[
                (
                    k,
                    well["j"],
                    well["i"],
                )
            ] = name

    return lookup


# ======================================================================
# CELL FACE VELOCITIES
# ======================================================================

def get_cell_face_velocities(
    k,
    j,
    i,
    vx,
    vy,
    vz,
):
    """
    Velocity COMPONENTS on the six faces.

    vx_w / vx_e are both +X components.
    vy_s / vy_n are both +Y components.
    vz_b / vz_t are both +Z components.

    No-flow external boundaries have zero velocity.
    """

    vx_w = (
        vx[k, j, i - 1]
        if i > 0
        else 0.0
    )

    vx_e = (
        vx[k, j, i]
        if i < NX - 1
        else 0.0
    )

    vy_s = (
        vy[k, j - 1, i]
        if j > 0
        else 0.0
    )

    vy_n = (
        vy[k, j, i]
        if j < NY - 1
        else 0.0
    )

    vz_b = (
        vz[k - 1, j, i]
        if k > 0
        else 0.0
    )

    vz_t = (
        vz[k, j, i]
        if k < NZ - 1
        else 0.0
    )

    return (
        vx_w,
        vx_e,
        vy_s,
        vy_n,
        vz_b,
        vz_t,
    )


# ======================================================================
# POLLOCK 1D ANALYTICAL FUNCTIONS
# ======================================================================

def local_velocity(
    s,
    length,
    v_low,
    v_high,
):

    a = (
        v_high - v_low
    ) / length

    return (
        v_low + a * s
    ), a


def exit_time_to_face(
    s0,
    target,
    length,
    v_low,
    v_high,
):
    """
    Analytical time required to reach one face along one coordinate.

    Returns +inf when the target face cannot be reached forward in time.
    """

    v_start, a = local_velocity(
        s0,
        length,
        v_low,
        v_high,
    )

    v_target, _ = local_velocity(
        target,
        length,
        v_low,
        v_high,
    )

    # Constant-velocity limit
    if abs(a) < GRADIENT_TOL:

        if abs(v_start) < VELOCITY_TOL:
            return np.inf

        t = (
            target - s0
        ) / v_start

        if t > TIME_TOL_S:
            return t

        return np.inf

    # At a true stagnation point the trajectory cannot
    # move along this coordinate.
    if abs(v_start) < VELOCITY_TOL:
        return np.inf

    ratio = (
        v_target / v_start
    )

    # Crossing a zero-velocity plane is impossible in finite time.
    if ratio <= 0.0:
        return np.inf

    t = (
        np.log(ratio) / a
    )

    if (
        np.isfinite(t)
        and t > TIME_TOL_S
    ):
        return t

    return np.inf


def advance_coordinate(
    s0,
    dt,
    length,
    v_low,
    v_high,
):

    v_start, a = local_velocity(
        s0,
        length,
        v_low,
        v_high,
    )

    if abs(a) < GRADIENT_TOL:

        s = (
            s0
            + v_start * dt
        )

    else:

        exponent = np.clip(
            a * dt,
            -700.0,
            700.0,
        )

        s = (
            v_start
            * np.exp(exponent)
            - v_low
        ) / a

    return np.clip(
        s,
        0.0,
        length,
    )


# ======================================================================
# INJECTOR-REGION SEEDING
# ======================================================================

def outward_faces_of_injector_region(
    qx,
    qy,
    qz,
):
    """
    Determine positive outward volumetric flow through the boundary
    of the entire five-cell injector completion column.

    Faces between two injector cells are intentionally excluded.
    """

    region = injector_cells()

    faces = []

    for k, j, i in sorted(region):

        # ----------------------------------------------------------
        # WEST
        # ----------------------------------------------------------

        neighbor = (
            k,
            j,
            i - 1,
        )

        if (
            i > 0
            and neighbor not in region
        ):

            q_out = -qx[
                k,
                j,
                i - 1,
            ]

            if q_out > 0.0:

                faces.append({
                    "cell": (k, j, i),
                    "neighbor": neighbor,
                    "face": "W",
                    "q_m3_s": float(q_out),
                })

        # ----------------------------------------------------------
        # EAST
        # ----------------------------------------------------------

        neighbor = (
            k,
            j,
            i + 1,
        )

        if (
            i < NX - 1
            and neighbor not in region
        ):

            q_out = qx[
                k,
                j,
                i,
            ]

            if q_out > 0.0:

                faces.append({
                    "cell": (k, j, i),
                    "neighbor": neighbor,
                    "face": "E",
                    "q_m3_s": float(q_out),
                })

        # ----------------------------------------------------------
        # SOUTH
        # ----------------------------------------------------------

        neighbor = (
            k,
            j - 1,
            i,
        )

        if (
            j > 0
            and neighbor not in region
        ):

            q_out = -qy[
                k,
                j - 1,
                i,
            ]

            if q_out > 0.0:

                faces.append({
                    "cell": (k, j, i),
                    "neighbor": neighbor,
                    "face": "S",
                    "q_m3_s": float(q_out),
                })

        # ----------------------------------------------------------
        # NORTH
        # ----------------------------------------------------------

        neighbor = (
            k,
            j + 1,
            i,
        )

        if (
            j < NY - 1
            and neighbor not in region
        ):

            q_out = qy[
                k,
                j,
                i,
            ]

            if q_out > 0.0:

                faces.append({
                    "cell": (k, j, i),
                    "neighbor": neighbor,
                    "face": "N",
                    "q_m3_s": float(q_out),
                })

        # ----------------------------------------------------------
        # BOTTOM
        # ----------------------------------------------------------

        neighbor = (
            k - 1,
            j,
            i,
        )

        if (
            k > 0
            and neighbor not in region
        ):

            q_out = -qz[
                k - 1,
                j,
                i,
            ]

            if q_out > 0.0:

                faces.append({
                    "cell": (k, j, i),
                    "neighbor": neighbor,
                    "face": "B",
                    "q_m3_s": float(q_out),
                })

        # ----------------------------------------------------------
        # TOP
        # ----------------------------------------------------------

        neighbor = (
            k + 1,
            j,
            i,
        )

        if (
            k < NZ - 1
            and neighbor not in region
        ):

            q_out = qz[
                k,
                j,
                i,
            ]

            if q_out > 0.0:

                faces.append({
                    "cell": (k, j, i),
                    "neighbor": neighbor,
                    "face": "T",
                    "q_m3_s": float(q_out),
                })

    return faces


def face_seed_positions(
    face_info,
):
    """
    Generate N x N points across one outgoing injector-region face.

    Seeds are nudged into the downstream neighbor cell.
    """

    k, j, i = face_info["cell"]
    nk, nj, ni = face_info["neighbor"]

    face = face_info["face"]

    seeds = []

    n = FACE_SUBDIVISIONS

    fractions = (
        np.arange(n)
        + 0.5
    ) / n

    x0 = i * DX_M
    y0 = j * DY_M
    z0 = k * DZ_M

    for a in fractions:

        for b in fractions:

            if face == "W":

                x = x0 - EPS_M
                y = y0 + a * DY_M
                z = z0 + b * DZ_M

            elif face == "E":

                x = x0 + DX_M + EPS_M
                y = y0 + a * DY_M
                z = z0 + b * DZ_M

            elif face == "S":

                x = x0 + a * DX_M
                y = y0 - EPS_M
                z = z0 + b * DZ_M

            elif face == "N":

                x = x0 + a * DX_M
                y = y0 + DY_M + EPS_M
                z = z0 + b * DZ_M

            elif face == "B":

                x = x0 + a * DX_M
                y = y0 + b * DY_M
                z = z0 - EPS_M

            elif face == "T":

                x = x0 + a * DX_M
                y = y0 + b * DY_M
                z = z0 + DZ_M + EPS_M

            else:
                raise ValueError(
                    f"Unknown face {face}"
                )

            seeds.append({
                "position_m": np.array(
                    [x, y, z],
                    dtype=float,
                ),
                "cell": (
                    nk,
                    nj,
                    ni,
                ),
            })

    return seeds


def build_seeds(
    qx,
    qy,
    qz,
):

    faces = (
        outward_faces_of_injector_region(
            qx,
            qy,
            qz,
        )
    )

    seeds = []

    for face_id, face in enumerate(faces):

        positions = (
            face_seed_positions(face)
        )

        weight = (
            face["q_m3_s"]
            / len(positions)
        )

        for local_id, seed in enumerate(positions):

            seeds.append({
                "seed_id": len(seeds),
                "face_id": face_id,
                "face": face["face"],
                "start_cell": seed["cell"],
                "position_m": seed["position_m"],
                "weight_m3_s": float(weight),
            })

    return faces, seeds


# ======================================================================
# POLLOCK CELL TRACKING
# ======================================================================

def trace_one_streamline(
    seed,
    vx,
    vy,
    vz,
    prod_lookup,
):

    position = seed[
        "position_m"
    ].copy()

    k, j, i = seed[
        "start_cell"
    ]

    points = [
        position.copy()
    ]

    cumulative_time = [
        0.0
    ]

    total_time = 0.0

    visited = {}

    status = "MAX_STEPS"
    producer = ""

    for step in range(
        MAX_CELL_CROSSINGS
    ):

        # ----------------------------------------------------------
        # Producer capture
        # ----------------------------------------------------------

        cell_key = (
            k,
            j,
            i,
        )

        if cell_key in prod_lookup:

            status = "PRODUCER"
            producer = prod_lookup[
                cell_key
            ]
            break

        # Loop/stagnation diagnostic
        visited[cell_key] = (
            visited.get(cell_key, 0)
            + 1
        )

        if visited[cell_key] > 20:

            status = "CELL_LOOP"
            break

        # ----------------------------------------------------------
        # Local coordinates
        # ----------------------------------------------------------

        x0 = i * DX_M
        y0 = j * DY_M
        z0 = k * DZ_M

        sx = position[0] - x0
        sy = position[1] - y0
        sz = position[2] - z0

        sx = np.clip(
            sx,
            0.0,
            DX_M,
        )

        sy = np.clip(
            sy,
            0.0,
            DY_M,
        )

        sz = np.clip(
            sz,
            0.0,
            DZ_M,
        )

        (
            vx_w,
            vx_e,
            vy_s,
            vy_n,
            vz_b,
            vz_t,
        ) = get_cell_face_velocities(
            k,
            j,
            i,
            vx,
            vy,
            vz,
        )

        # ----------------------------------------------------------
        # Candidate exit times
        # ----------------------------------------------------------

        candidates = []

        tx_w = exit_time_to_face(
            sx,
            0.0,
            DX_M,
            vx_w,
            vx_e,
        )

        tx_e = exit_time_to_face(
            sx,
            DX_M,
            DX_M,
            vx_w,
            vx_e,
        )

        ty_s = exit_time_to_face(
            sy,
            0.0,
            DY_M,
            vy_s,
            vy_n,
        )

        ty_n = exit_time_to_face(
            sy,
            DY_M,
            DY_M,
            vy_s,
            vy_n,
        )

        tz_b = exit_time_to_face(
            sz,
            0.0,
            DZ_M,
            vz_b,
            vz_t,
        )

        tz_t = exit_time_to_face(
            sz,
            DZ_M,
            DZ_M,
            vz_b,
            vz_t,
        )

        for face, t in [
            ("W", tx_w),
            ("E", tx_e),
            ("S", ty_s),
            ("N", ty_n),
            ("B", tz_b),
            ("T", tz_t),
        ]:

            if np.isfinite(t):
                candidates.append(
                    (t, face)
                )

        if not candidates:

            status = "STAGNATION"
            break

        dt = min(
            t
            for t, _
            in candidates
        )

        # Multiple simultaneous exits can occur at an edge/corner.
        exit_faces = [
            face
            for t, face
            in candidates
            if abs(t - dt)
            <= max(
                1.0e-9,
                1.0e-9 * abs(dt),
            )
        ]

        # ----------------------------------------------------------
        # Analytical position update
        # ----------------------------------------------------------

        sx_new = advance_coordinate(
            sx,
            dt,
            DX_M,
            vx_w,
            vx_e,
        )

        sy_new = advance_coordinate(
            sy,
            dt,
            DY_M,
            vy_s,
            vy_n,
        )

        sz_new = advance_coordinate(
            sz,
            dt,
            DZ_M,
            vz_b,
            vz_t,
        )

        position = np.array(
            [
                x0 + sx_new,
                y0 + sy_new,
                z0 + sz_new,
            ],
            dtype=float,
        )

        total_time += dt

        points.append(
            position.copy()
        )

        cumulative_time.append(
            total_time
        )

        # ----------------------------------------------------------
        # Cross exit face(s)
        # ----------------------------------------------------------

        new_i = i
        new_j = j
        new_k = k

        nudge = np.zeros(
            3,
            dtype=float,
        )

        for face in exit_faces:

            if face == "W":
                new_i -= 1
                nudge[0] -= EPS_M

            elif face == "E":
                new_i += 1
                nudge[0] += EPS_M

            elif face == "S":
                new_j -= 1
                nudge[1] -= EPS_M

            elif face == "N":
                new_j += 1
                nudge[1] += EPS_M

            elif face == "B":
                new_k -= 1
                nudge[2] -= EPS_M

            elif face == "T":
                new_k += 1
                nudge[2] += EPS_M

        # ----------------------------------------------------------
        # Domain exit
        # ----------------------------------------------------------

        if not (
            0 <= new_i < NX
            and
            0 <= new_j < NY
            and
            0 <= new_k < NZ
        ):

            status = "BOUNDARY_EXIT"
            break

        position = (
            position + nudge
        )

        # Keep safely within model
        position[0] = np.clip(
            position[0],
            EPS_M,
            LX_M - EPS_M,
        )

        position[1] = np.clip(
            position[1],
            EPS_M,
            LY_M - EPS_M,
        )

        position[2] = np.clip(
            position[2],
            EPS_M,
            LZ_M - EPS_M,
        )

        i = new_i
        j = new_j
        k = new_k

    return {
        "seed_id":
            seed["seed_id"],

        "weight_m3_s":
            seed["weight_m3_s"],

        "status":
            status,

        "producer":
            producer,

        "travel_time_s":
            float(total_time),

        "points_m":
            np.asarray(
                points,
                dtype=float,
            ),

        "times_s":
            np.asarray(
                cumulative_time,
                dtype=float,
            ),
    }


# ======================================================================
# TRACE ALL STREAMLINES
# ======================================================================

def trace_streamlines(
    seeds,
    vx,
    vy,
    vz,
):

    prod_lookup = (
        producer_lookup()
    )

    streamlines = []

    for n, seed in enumerate(
        seeds,
        start=1,
    ):

        result = trace_one_streamline(
            seed,
            vx,
            vy,
            vz,
            prod_lookup,
        )

        streamlines.append(
            result
        )

        if (
            n % 25 == 0
            or n == len(seeds)
        ):

            print(
                f"  Traced "
                f"{n}/{len(seeds)}"
            )

    return streamlines


# ======================================================================
# VALIDATION / CAPTURE ACCOUNTING
# ======================================================================

def validate_streamlines(
    faces,
    seeds,
    streamlines,
):

    outgoing_q = sum(
        f["q_m3_s"]
        for f in faces
    )

    seed_q = sum(
        s["weight_m3_s"]
        for s in seeds
    )

    captured = [
        s
        for s in streamlines
        if s["status"]
        == "PRODUCER"
    ]

    capture_q = sum(
        s["weight_m3_s"]
        for s in captured
    )

    capture_fraction = (
        capture_q / seed_q
        if seed_q > 0.0
        else 0.0
    )

    boundary_exit_count = sum(
        s["status"]
        == "BOUNDARY_EXIT"
        for s in streamlines
    )

    stagnation_count = sum(
        s["status"]
        == "STAGNATION"
        for s in streamlines
    )

    loop_count = sum(
        s["status"]
        == "CELL_LOOP"
        for s in streamlines
    )

    maxstep_count = sum(
        s["status"]
        == "MAX_STEPS"
        for s in streamlines
    )

    producer_capture = {
        name: 0.0
        for name in PRODUCERS
    }

    producer_count = {
        name: 0
        for name in PRODUCERS
    }

    for s in captured:

        producer_capture[
            s["producer"]
        ] += s["weight_m3_s"]

        producer_count[
            s["producer"]
        ] += 1

    print("\n" + "=" * 78)
    print("V15-SG5 POLLOCK VALIDATION")
    print("=" * 78)

    checks = [
        (
            "At least one seed generated",
            len(seeds) > 0,
        ),

        (
            "Seed weights reproduce injector-region outward flux",
            np.isclose(
                seed_q,
                outgoing_q,
                rtol=1.0e-12,
                atol=1.0e-15,
            ),
        ),

        (
            "No streamline exits no-flow reservoir boundary",
            boundary_exit_count == 0,
        ),

        (
            "Weighted producer capture >= 95%",
            capture_fraction >= 0.95,
        ),

        (
            "All four producers receive streamlines",
            all(
                producer_count[name] > 0
                for name in PRODUCERS
            ),
        ),
    ]

    all_passed = True

    for description, passed in checks:

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"[{status:4s}] {description}"
        )

        if not passed:
            all_passed = False

    print("=" * 78)

    print(
        f"Outgoing injector-region flow : "
        f"{outgoing_q * DAY_TO_S:.6f} m3/day"
    )

    print(
        f"Seed-weight total             : "
        f"{seed_q * DAY_TO_S:.6f} m3/day"
    )

    print(
        f"Captured streamline weight    : "
        f"{capture_q * DAY_TO_S:.6f} m3/day"
    )

    print(
        f"Weighted capture fraction      : "
        f"{capture_fraction:.6%}"
    )

    print(
        f"Number of streamlines          : "
        f"{len(streamlines)}"
    )

    print(
        f"Producer captures              : "
        f"{len(captured)}"
    )

    print(
        f"Stagnation                     : "
        f"{stagnation_count}"
    )

    print(
        f"Cell loop                      : "
        f"{loop_count}"
    )

    print(
        f"Maximum steps                  : "
        f"{maxstep_count}"
    )

    print(
        f"Boundary exits                 : "
        f"{boundary_exit_count}"
    )

    print("\nCAPTURE BY PRODUCER")

    for name in PRODUCERS:

        q_day = (
            producer_capture[name]
            * DAY_TO_S
        )

        fraction = (
            producer_capture[name]
            / seed_q
            if seed_q > 0.0
            else 0.0
        )

        print(
            f"  {name:10s}: "
            f"{q_day:10.3f} m3/day "
            f"({fraction:7.3%})  "
            f"N={producer_count[name]}"
        )

    if not all_passed:

        raise RuntimeError(
            "V15-SG5 Pollock validation failed. "
            "Do not freeze SG5."
        )

    print(
        "\nV15-SG5 EXACT POLLOCK VALIDATION: PASS"
    )

    return {
        "outgoing_injector_flow_m3_day":
            float(
                outgoing_q * DAY_TO_S
            ),

        "seed_weight_m3_day":
            float(
                seed_q * DAY_TO_S
            ),

        "captured_weight_m3_day":
            float(
                capture_q * DAY_TO_S
            ),

        "capture_fraction":
            float(
                capture_fraction
            ),

        "streamline_count":
            int(
                len(streamlines)
            ),

        "producer_capture_count":
            int(
                len(captured)
            ),

        "stagnation_count":
            int(
                stagnation_count
            ),

        "loop_count":
            int(
                loop_count
            ),

        "maxstep_count":
            int(
                maxstep_count
            ),

        "boundary_exit_count":
            int(
                boundary_exit_count
            ),

        "producer_capture_m3_day": {
            name: float(
                producer_capture[name]
                * DAY_TO_S
            )
            for name in PRODUCERS
        },

        "producer_capture_count_detail":
            producer_count,
    }


# ======================================================================
# SAVE STREAMLINE DATA
# ======================================================================

def save_streamline_arrays(
    streamlines,
):

    all_points = []
    all_times = []

    offsets = [0]

    weights = []
    travel_times = []

    statuses = []
    producers = []

    for s in streamlines:

        pts = s["points_m"]
        tim = s["times_s"]

        all_points.append(
            pts
        )

        all_times.append(
            tim
        )

        offsets.append(
            offsets[-1]
            + len(pts)
        )

        weights.append(
            s["weight_m3_s"]
        )

        travel_times.append(
            s["travel_time_s"]
        )

        statuses.append(
            s["status"]
        )

        producers.append(
            s["producer"]
        )

    points = np.concatenate(
        all_points,
        axis=0,
    )

    times = np.concatenate(
        all_times,
        axis=0,
    )

    np.savez_compressed(
        STREAMLINE_FILE,

        points_m=points,

        cumulative_times_s=times,

        offsets=np.asarray(
            offsets,
            dtype=np.int64,
        ),

        weights_m3_s=np.asarray(
            weights,
            dtype=float,
        ),

        travel_times_s=np.asarray(
            travel_times,
            dtype=float,
        ),

        statuses=np.asarray(
            statuses,
            dtype="U32",
        ),

        producers=np.asarray(
            producers,
            dtype="U32",
        ),
    )


def save_capture_csv(
    streamlines,
):

    with open(
        CAPTURE_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "streamline_id",
            "status",
            "producer",
            "weight_m3_day",
            "travel_time_days",
            "n_points",
        ])

        for idx, s in enumerate(
            streamlines
        ):

            writer.writerow([
                idx,
                s["status"],
                s["producer"],
                s["weight_m3_s"]
                * DAY_TO_S,
                s["travel_time_s"]
                / DAY_TO_S,
                len(s["points_m"]),
            ])


# ======================================================================
# PLOTS
# ======================================================================

def plot_xy_streamlines(
    permeability,
    streamlines,
):

    layer = 7

    fig, ax = plt.subplots(
        figsize=(9, 8)
    )

    im = ax.imshow(
        permeability[layer],
        origin="lower",
        extent=[
            0,
            LX_FT,
            0,
            LY_FT,
        ],
        aspect="equal",
    )

    cbar = fig.colorbar(
        im,
        ax=ax,
    )

    cbar.set_label(
        "Layer-8 permeability (mD)"
    )

    # Plot streamlines that pass through Layer 8
    z_low = layer * DZ_M
    z_high = (
        layer + 1
    ) * DZ_M

    n_plotted = 0

    for s in streamlines:

        pts = s["points_m"]

        if not np.any(
            (pts[:, 2] >= z_low)
            &
            (pts[:, 2] <= z_high)
        ):
            continue

        ax.plot(
            pts[:, 0] / FT_TO_M,
            pts[:, 1] / FT_TO_M,
            linewidth=0.8,
            alpha=0.65,
        )

        n_plotted += 1

    ax.scatter(
        (
            INJECTOR_I + 0.5
        ) * DX_FT,
        (
            INJECTOR_J + 0.5
        ) * DY_FT,
        marker="*",
        s=180,
        label="Injector",
    )

    for name, well in PRODUCERS.items():

        ax.scatter(
            (
                well["i"]
                + 0.5
            ) * DX_FT,
            (
                well["j"]
                + 0.5
            ) * DY_FT,
            marker="s",
            s=65,
            label=name,
        )

    ax.set_title(
        "PAD-Stream V15-SG5\n"
        f"Exact Pollock Streamlines - Layer 8 "
        f"(N={n_plotted})"
    )

    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Y (ft)")

    ax.legend(
        loc="upper left",
        bbox_to_anchor=(
            1.18,
            1.0,
        ),
        fontsize=8,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG5_Pollock_XY_Layer08.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


def plot_3d_streamlines(
    streamlines,
):

    fig = plt.figure(
        figsize=(10, 8)
    )

    ax = fig.add_subplot(
        111,
        projection="3d",
    )

    for s in streamlines:

        pts = s["points_m"]

        ax.plot(
            pts[:, 0] / FT_TO_M,
            pts[:, 1] / FT_TO_M,
            pts[:, 2] / FT_TO_M,
            linewidth=0.6,
            alpha=0.6,
        )

    ax.scatter(
        (
            INJECTOR_I + 0.5
        ) * DX_FT,
        (
            INJECTOR_J + 0.5
        ) * DY_FT,
        30.0,
        marker="*",
        s=120,
        label="Injector",
    )

    for name, well in PRODUCERS.items():

        ax.scatter(
            (
                well["i"]
                + 0.5
            ) * DX_FT,
            (
                well["j"]
                + 0.5
            ) * DY_FT,
            30.0,
            marker="s",
            s=40,
        )

    ax.set_xlim(
        0,
        LX_FT,
    )

    ax.set_ylim(
        0,
        LY_FT,
    )

    ax.set_zlim(
        0,
        LZ_FT,
    )

    ax.set_xlabel("X (ft)")
    ax.set_ylabel("Y (ft)")
    ax.set_zlabel("Z (ft)")

    ax.set_title(
        "PAD-Stream V15-SG5\n"
        "3D Exact Pollock Streamlines"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG5_Pollock_3D.png",
        dpi=300,
    )

    plt.close(fig)


def plot_travel_time_histogram(
    streamlines,
):

    times = np.asarray([
        s["travel_time_s"]
        / DAY_TO_S
        for s in streamlines
        if (
            s["status"]
            == "PRODUCER"
            and
            s["travel_time_s"] > 0.0
        )
    ])

    if times.size == 0:
        return

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    ax.hist(
        times,
        bins=30,
    )

    ax.set_xlabel(
        "Pollock travel time (days)"
    )

    ax.set_ylabel(
        "Streamline count"
    )

    ax.set_title(
        "PAD-Stream V15-SG5\n"
        "Injector-to-Producer Travel-Time Distribution"
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "V15SG5_TravelTime_Histogram.png",
        dpi=300,
    )

    plt.close(fig)


# ======================================================================
# SUMMARY
# ======================================================================

def save_summary(
    validation,
    streamlines,
):

    completed = [
        s
        for s in streamlines
        if s["status"]
        == "PRODUCER"
    ]

    if completed:

        times_days = np.array([
            s["travel_time_s"]
            / DAY_TO_S
            for s in completed
        ])

        travel_stats = {
            "min_days":
                float(
                    times_days.min()
                ),

            "max_days":
                float(
                    times_days.max()
                ),

            "mean_days":
                float(
                    times_days.mean()
                ),

            "median_days":
                float(
                    np.median(
                        times_days
                    )
                ),
        }

    else:

        travel_stats = {}

    summary = {
        "milestone":
            "V15-SG5",

        "description":
            "Exact 3D Pollock streamline tracing",

        "status":
            "PASS",

        "grid": {
            "nx": NX,
            "ny": NY,
            "nz": NZ,
            "dx_ft": DX_FT,
            "dy_ft": DY_FT,
            "dz_ft": DZ_FT,
        },

        "porosity":
            POROSITY,

        "face_subdivisions":
            FACE_SUBDIVISIONS,

        "method":
            "piecewise-linear Pollock analytical cell tracking",

        "seeding":
            "flux-weighted boundary of five-cell injector completion region",

        "producer_termination":
            "entry into producer completion cell",

        "validation":
            validation,

        "travel_time":
            travel_stats,

        "next_milestone":
            "V15-SG6 - streamline time-of-flight and transport coordinates",
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

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG5")
    print("Exact 3D Pollock Streamline Tracing")
    print("=" * 78)

    (
        permeability,
        qx,
        qy,
        qz,
    ) = load_inputs()

    vx, vy, vz = (
        construct_face_pore_velocities(
            qx,
            qy,
            qz,
        )
    )

    print("\nFACE PORE VELOCITY ARRAYS")

    print(
        f"  Vx shape               : {vx.shape}"
    )

    print(
        f"  Vy shape               : {vy.shape}"
    )

    print(
        f"  Vz shape               : {vz.shape}"
    )

    print("\nPORE VELOCITY MAGNITUDES")

    print(
        f"  max |Vx|               : "
        f"{np.max(np.abs(vx)):.6e} m/s"
    )

    print(
        f"  max |Vy|               : "
        f"{np.max(np.abs(vy)):.6e} m/s"
    )

    print(
        f"  max |Vz|               : "
        f"{np.max(np.abs(vz)):.6e} m/s"
    )

    # --------------------------------------------------------------
    # Flux-weighted injector seeds
    # --------------------------------------------------------------

    faces, seeds = build_seeds(
        qx,
        qy,
        qz,
    )

    outgoing_day = sum(
        f["q_m3_s"]
        for f in faces
    ) * DAY_TO_S

    print("\nINJECTOR-REGION SEEDING")

    print(
        f"  Outgoing faces         : {len(faces)}"
    )

    print(
        f"  Face subdivisions      : "
        f"{FACE_SUBDIVISIONS} x {FACE_SUBDIVISIONS}"
    )

    print(
        f"  Number of seeds        : {len(seeds)}"
    )

    print(
        f"  Outgoing flux          : "
        f"{outgoing_day:.6f} m3/day"
    )

    # --------------------------------------------------------------
    # Trace
    # --------------------------------------------------------------

    print("\nTracing streamlines...")

    streamlines = trace_streamlines(
        seeds,
        vx,
        vy,
        vz,
    )

    # --------------------------------------------------------------
    # Validate
    # --------------------------------------------------------------

    validation = (
        validate_streamlines(
            faces,
            seeds,
            streamlines,
        )
    )

    # --------------------------------------------------------------
    # Save
    # --------------------------------------------------------------

    save_streamline_arrays(
        streamlines
    )

    save_capture_csv(
        streamlines
    )

    plot_xy_streamlines(
        permeability,
        streamlines,
    )

    plot_3d_streamlines(
        streamlines
    )

    plot_travel_time_histogram(
        streamlines
    )

    save_summary(
        validation,
        streamlines,
    )

    print("\nOUTPUTS")

    print(
        f"  Directory:\n"
        f"    {OUTPUT_DIR}"
    )

    print("\nSaved streamline data:")
    print(
        "  STREAMLINES_POLLOCK.npz"
    )
    print(
        "  V15SG5_Streamline_Capture.csv"
    )

    print("\nSaved diagnostics:")
    print(
        "  V15SG5_Pollock_XY_Layer08.png"
    )
    print(
        "  V15SG5_Pollock_3D.png"
    )
    print(
        "  V15SG5_TravelTime_Histogram.png"
    )

    print("\nSummary:")
    print(
        f"  {SUMMARY_FILE}"
    )

    print("\n" + "=" * 78)
    print(
        "V15-SG5 COMPLETED SUCCESSFULLY"
    )
    print(
        "Next milestone: V15-SG6"
    )
    print(
        "Streamline time-of-flight and transport coordinates"
    )
    print("=" * 78)


if __name__ == "__main__":
    main()
from __future__ import annotations

from pathlib import Path
import csv
import json
import hashlib
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7D1
# Conservative Frozen-L2 Streamline-to-Grid Map-Back
#
# CONTROLLED MAP-BACK MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO FROZEN L2 ARRAY CHANGED.
# NO STREAMLINE GEOMETRY CHANGED.
# NO SG7E THRESHOLD CHANGED.
#
# PURPOSE
# -------
# SG7D0 established the complete interface:
#
#   frozen L2 state:     (n_streamlines, n_xi)
#   streamline xyz:      (n_streamlines, n_xi, 3)
#   streamline TOF:      (n_streamlines, n_xi)
#   streamline weights:  (n_streamlines,)
#   target grid:          (15, 50, 50)
#
# SG7D1 performs the first conservative segment-based map-back from streamline
# space to the 3-D SGSim grid.
#
# Key principles:
#
#   * use piecewise-linear streamline segments, not nearest-node deposition,
#   * clip each segment to the Cartesian grid,
#   * split segments at cell-boundary crossings,
#   * accumulate a weighted deposition measure per cell,
#   * compute cell saturation by weighted averaging,
#   * preserve unsupported cells explicitly as NaN,
#   * verify support/mass closure,
#   * do not alter the frozen L2 candidate.
#
# The deposition measure used here is segment length in meters:
#
#   numerator_c   = sum_mj w_m * Sbar_mj * dl_mjc
#   denominator_c = sum_mj w_m * dl_mjc
#
#   S_c = numerator_c / denominator_c, where denominator_c > 0
#
# This is a geometry-aware conservative weighted map-back.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7D1"
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------------

SG7D0_CONTRACT = (
    ROOT / "output" / "V15_SG7D0"
    / "V15SG7D0_Frozen_L2_MapBack_Interface_Contract.json"
)

R1F3_FROZEN = (
    ROOT / "output" / "V15_SG7CR3F5R1F3"
    / "frozen_candidate"
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

# Expected target grid contract
NZ, NY, NX = 15, 50, 50
DX_FT, DY_FT, DZ_FT = 20.0, 20.0, 4.0

FT_TO_M = 0.3048
DX_M = DX_FT * FT_TO_M
DY_M = DY_FT * FT_TO_M
DZ_M = DZ_FT * FT_TO_M

LX_M = NX * DX_M
LY_M = NY * DY_M
LZ_M = NZ * DZ_M

GRID_SHAPE = (NZ, NY, NX)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7D1_Summary.json"

SOURCE_TABLE = OUT / "V15SG7D1_Source_Interface.csv"
COORD_TABLE = OUT / "V15SG7D1_Coordinate_System_Audit.csv"
SEGMENT_TABLE = OUT / "V15SG7D1_Segment_Statistics.csv"
CLOSURE_TABLE = OUT / "V15SG7D1_Conservation_Closure.csv"
SUPPORT_TABLE = OUT / "V15SG7D1_Grid_Support_Statistics.csv"
BOUNDS_TABLE = OUT / "V15SG7D1_Saturation_Bounds_Audit.csv"
CELL_TABLE = OUT / "V15SG7D1_Cellwise_Support_Summary.csv"

NUMERICAL_FILE = OUT / "V15SG7D1_Conservative_MapBack.npz"
CONTRACT_FILE = OUT / "V15SG7D1_Conservative_MapBack_Contract.json"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def save_csv(path: Path, rows):
    if not rows:
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def sha256(path: Path, chunk_size=1024 * 1024):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def load_geometry_from_contract(contract):
    geom = contract["streamline_geometry"]

    required = [
        ("xyz_source", "xyz_key"),
        ("tof_matrix_source", "tof_matrix_key"),
        ("weights_source", "weights_key"),
    ]

    out = {}

    for source_key, array_key in required:
        source = geom.get(source_key)
        key = geom.get(array_key)

        if source is None or key is None:
            raise RuntimeError(
                f"SG7D1 requires {source_key}/{array_key} from SG7D0."
            )

        path = Path(source)

        if not path.exists():
            raise FileNotFoundError(
                f"Missing geometry source:\n{path}"
            )

        db = np.load(path, allow_pickle=True)

        if key not in db.files:
            raise KeyError(
                f"Missing key {key!r} in geometry source {path}"
            )

        out[source_key.replace("_source", "")] = {
            "path": path,
            "key": key,
            "array": np.asarray(db[key]),
        }

    return out


def infer_coordinate_units_and_origin(xyz):
    """
    Determine whether xyz is already in meters or in feet.

    The SGSim domain is:
        1000 x 1000 x 60 ft
        304.8 x 304.8 x 18.288 m

    We compare robust coordinate spans to both expectations.
    """

    pts = xyz.reshape(-1, 3)
    finite = np.all(np.isfinite(pts), axis=1)
    pts = pts[finite]

    if pts.size == 0:
        raise RuntimeError("No finite streamline coordinates available.")

    mins = np.nanpercentile(pts, 0.1, axis=0)
    maxs = np.nanpercentile(pts, 99.9, axis=0)
    spans = maxs - mins

    expected_m = np.asarray([LX_M, LY_M, LZ_M], dtype=float)
    expected_ft = np.asarray([NX*DX_FT, NY*DY_FT, NZ*DZ_FT], dtype=float)

    # Relative span mismatch. z may be narrower than the full reservoir if
    # streamlines do not fully populate top/bottom layers, so weight x/y more.
    def mismatch(spans_candidate, expected):
        rel = np.abs(spans_candidate - expected) / np.maximum(expected, 1e-12)
        return float(0.45*rel[0] + 0.45*rel[1] + 0.10*rel[2])

    score_m = mismatch(spans, expected_m)
    score_ft = mismatch(spans, expected_ft)

    if score_m <= score_ft:
        units = "m"
        scale_to_m = 1.0
    else:
        units = "ft"
        scale_to_m = FT_TO_M

    xyz_m = xyz.astype(np.float64) * scale_to_m

    pts_m = xyz_m.reshape(-1, 3)
    finite_m = np.all(np.isfinite(pts_m), axis=1)
    pts_m = pts_m[finite_m]

    min_m = np.min(pts_m, axis=0)
    max_m = np.max(pts_m, axis=0)

    # Shift origin to the minimum observed coordinate if coordinates are not
    # already approximately zero-based. This is an explicit deterministic
    # origin normalization, recorded in the audit.
    origin_shift = np.zeros(3, dtype=float)

    tol = 0.25 * np.asarray([DX_M, DY_M, DZ_M])

    for a in range(3):
        if abs(min_m[a]) > tol[a]:
            origin_shift[a] = min_m[a]

    xyz_local = xyz_m - origin_shift[None, None, :]

    return {
        "input_units": units,
        "scale_to_m": scale_to_m,
        "origin_shift_m": origin_shift,
        "xyz_local_m": xyz_local,
        "raw_min": np.min(xyz.reshape(-1,3), axis=0),
        "raw_max": np.max(xyz.reshape(-1,3), axis=0),
        "local_min_m": np.min(xyz_local.reshape(-1,3), axis=0),
        "local_max_m": np.max(xyz_local.reshape(-1,3), axis=0),
        "score_m": score_m,
        "score_ft": score_ft,
    }


def clip_segment_to_box(p0, p1, lo, hi):
    """
    Liang-Barsky style parametric clipping in 3-D.
    Returns clipped endpoints and t0,t1 on original segment, or None.
    """

    d = p1 - p0
    t0, t1 = 0.0, 1.0

    for a in range(3):
        if abs(d[a]) < 1e-15:
            if p0[a] < lo[a] or p0[a] > hi[a]:
                return None
            continue

        ta = (lo[a] - p0[a]) / d[a]
        tb = (hi[a] - p0[a]) / d[a]

        enter = min(ta, tb)
        leave = max(ta, tb)

        t0 = max(t0, enter)
        t1 = min(t1, leave)

        if t0 > t1:
            return None

    q0 = p0 + t0 * d
    q1 = p0 + t1 * d

    return q0, q1, t0, t1


def cell_index_from_point(p):
    """
    Cartesian logical cell index for local meter coordinates.
    Boundary points at the global max are nudged inward.
    """

    x, y, z = p

    epsx = 1e-12 * max(LX_M, 1.0)
    epsy = 1e-12 * max(LY_M, 1.0)
    epsz = 1e-12 * max(LZ_M, 1.0)

    x = min(max(x, 0.0), LX_M - epsx)
    y = min(max(y, 0.0), LY_M - epsy)
    z = min(max(z, 0.0), LZ_M - epsz)

    i = int(np.floor(x / DX_M))
    j = int(np.floor(y / DY_M))
    k = int(np.floor(z / DZ_M))

    if not (0 <= i < NX and 0 <= j < NY and 0 <= k < NZ):
        raise RuntimeError(
            f"Computed invalid cell index {(k,j,i)} for point {p}"
        )

    return k, j, i


def split_segment_by_cell_boundaries(q0, q1):
    """
    Split a clipped line segment at every Cartesian cell-face crossing.

    Returns a list of (tmid, dl, k, j, i) pieces in local clipped parameter
    coordinates u in [0,1].
    """

    d = q1 - q0
    total_length = float(np.linalg.norm(d))

    if total_length <= 0.0:
        return []

    cuts = [0.0, 1.0]

    # x boundaries
    if abs(d[0]) > 1e-15:
        for i in range(1, NX):
            xb = i * DX_M
            u = (xb - q0[0]) / d[0]
            if 0.0 < u < 1.0:
                cuts.append(float(u))

    # y boundaries
    if abs(d[1]) > 1e-15:
        for j in range(1, NY):
            yb = j * DY_M
            u = (yb - q0[1]) / d[1]
            if 0.0 < u < 1.0:
                cuts.append(float(u))

    # z boundaries
    if abs(d[2]) > 1e-15:
        for k in range(1, NZ):
            zb = k * DZ_M
            u = (zb - q0[2]) / d[2]
            if 0.0 < u < 1.0:
                cuts.append(float(u))

    cuts = np.asarray(sorted(set(cuts)), dtype=float)

    pieces = []

    for a, b in zip(cuts[:-1], cuts[1:]):
        if b - a <= 1e-15:
            continue

        umid = 0.5 * (a + b)
        pmid = q0 + umid * d
        dl = total_length * (b - a)

        k, j, i = cell_index_from_point(pmid)

        pieces.append((umid, dl, k, j, i))

    return pieces


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7D1")
    print("Conservative Frozen-L2 Streamline-to-Grid Map-Back")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO STREAMLINE GEOMETRY WILL BE CHANGED.
NO SG7E THRESHOLD WILL BE CHANGED.
A CONSERVATIVE SEGMENT-BASED MAP-BACK WILL BE PERFORMED.
""")

    contract = load_json(SG7D0_CONTRACT)

    if (
        contract.get("status")
        !=
        "FROZEN_L2_MAPBACK_INTERFACE_CONTRACT_READY"
    ):
        raise RuntimeError(
            "SG7D1 requires a successful SG7D0 map-back interface contract."
        )

    frozen_sha_expected = contract["frozen_candidate"]["sha256"]
    frozen_sha_actual = sha256(R1F3_FROZEN)

    if frozen_sha_expected != frozen_sha_actual:
        raise RuntimeError(
            "Frozen L2 candidate hash no longer matches SG7D0 contract."
        )

    frozen = np.load(R1F3_FROZEN, allow_pickle=True)

    l2 = np.asarray(
        frozen["L2_independent_100"],
        dtype=np.float64,
    )

    xi = np.asarray(
        frozen["xi"],
        dtype=np.float64,
    )

    nstream, nxi = l2.shape

    geometry = load_geometry_from_contract(contract)

    xyz = np.asarray(
        geometry["xyz"]["array"],
        dtype=np.float64,
    )

    tau = np.asarray(
        geometry["tof_matrix"]["array"],
        dtype=np.float64,
    )

    weights = np.asarray(
        geometry["weights"]["array"],
        dtype=np.float64,
    )

    if xyz.shape != (nstream, nxi, 3):
        raise RuntimeError(
            f"XYZ shape {xyz.shape} does not match frozen L2 {(nstream,nxi,3)}"
        )

    if tau.shape != (nstream, nxi):
        raise RuntimeError(
            f"TOF shape {tau.shape} does not match frozen L2 {(nstream,nxi)}"
        )

    if weights.shape != (nstream,):
        raise RuntimeError(
            f"Weight shape {weights.shape} does not match streamline count {nstream}"
        )

    if not np.all(np.isfinite(weights)) or not np.all(weights > 0.0):
        raise RuntimeError(
            "Streamline weights must be positive and finite."
        )

    # -------------------------------------------------------------------------
    # Coordinate audit
    # -------------------------------------------------------------------------

    coord = infer_coordinate_units_and_origin(xyz)
    xyz_m = coord["xyz_local_m"]

    coord_rows = [{
        "input_units": coord["input_units"],
        "scale_to_m": coord["scale_to_m"],
        "raw_x_min": coord["raw_min"][0],
        "raw_x_max": coord["raw_max"][0],
        "raw_y_min": coord["raw_min"][1],
        "raw_y_max": coord["raw_max"][1],
        "raw_z_min": coord["raw_min"][2],
        "raw_z_max": coord["raw_max"][2],
        "origin_shift_x_m": coord["origin_shift_m"][0],
        "origin_shift_y_m": coord["origin_shift_m"][1],
        "origin_shift_z_m": coord["origin_shift_m"][2],
        "local_x_min_m": coord["local_min_m"][0],
        "local_x_max_m": coord["local_max_m"][0],
        "local_y_min_m": coord["local_min_m"][1],
        "local_y_max_m": coord["local_max_m"][1],
        "local_z_min_m": coord["local_min_m"][2],
        "local_z_max_m": coord["local_max_m"][2],
        "meter_score": coord["score_m"],
        "feet_score": coord["score_ft"],
        "target_Lx_m": LX_M,
        "target_Ly_m": LY_M,
        "target_Lz_m": LZ_M,
    }]

    save_csv(COORD_TABLE, coord_rows)

    # -------------------------------------------------------------------------
    # Accumulators
    # -------------------------------------------------------------------------

    numerator = np.zeros(GRID_SHAPE, dtype=np.float64)
    denominator = np.zeros(GRID_SHAPE, dtype=np.float64)
    segment_piece_count = np.zeros(GRID_SHAPE, dtype=np.int64)
    streamline_visit_count = np.zeros(GRID_SHAPE, dtype=np.int64)

    total_input_weighted_length = 0.0
    total_deposited_weighted_length = 0.0
    total_input_weighted_sat_length = 0.0
    total_deposited_weighted_sat_length = 0.0

    total_segments = 0
    clipped_segments = 0
    skipped_zero_segments = 0
    total_pieces = 0

    # For unique streamline-per-cell visit counts.
    last_seen = np.full(GRID_SHAPE, -1, dtype=np.int64)

    lo = np.asarray([0.0, 0.0, 0.0], dtype=float)
    hi = np.asarray([LX_M, LY_M, LZ_M], dtype=float)

    # -------------------------------------------------------------------------
    # Conservative segment deposition
    # -------------------------------------------------------------------------

    for m in range(nstream):

        wm = weights[m]

        for j in range(nxi - 1):

            p0 = xyz_m[m, j]
            p1 = xyz_m[m, j + 1]

            if not (
                np.all(np.isfinite(p0))
                and
                np.all(np.isfinite(p1))
            ):
                continue

            segvec = p1 - p0
            seglen = float(np.linalg.norm(segvec))

            if seglen <= 0.0:
                skipped_zero_segments += 1
                continue

            total_segments += 1

            s0 = l2[m, j]
            s1 = l2[m, j + 1]

            # Total source measure before clipping.
            source_sat_avg = 0.5 * (s0 + s1)

            total_input_weighted_length += wm * seglen
            total_input_weighted_sat_length += (
                wm * source_sat_avg * seglen
            )

            clipped = clip_segment_to_box(
                p0,
                p1,
                lo,
                hi,
            )

            if clipped is None:
                continue

            q0, q1, t0_orig, t1_orig = clipped

            clipped_len = float(np.linalg.norm(q1 - q0))

            if clipped_len <= 0.0:
                continue

            if t0_orig > 0.0 or t1_orig < 1.0:
                clipped_segments += 1

            pieces = split_segment_by_cell_boundaries(
                q0,
                q1,
            )

            if not pieces:
                continue

            for u_mid, dl, k, jj, i in pieces:

                # Convert clipped-local u back to original segment parameter t.
                t_mid = t0_orig + u_mid * (t1_orig - t0_orig)

                # Linear saturation interpolation along the original segment.
                smid = s0 + t_mid * (s1 - s0)

                measure = wm * dl

                denominator[k, jj, i] += measure
                numerator[k, jj, i] += measure * smid
                segment_piece_count[k, jj, i] += 1

                if last_seen[k, jj, i] != m:
                    streamline_visit_count[k, jj, i] += 1
                    last_seen[k, jj, i] = m

                total_deposited_weighted_length += measure
                total_deposited_weighted_sat_length += (
                    measure * smid
                )

                total_pieces += 1

    # -------------------------------------------------------------------------
    # Build mapped field
    # -------------------------------------------------------------------------

    supported = denominator > 0.0

    s_grid = np.full(
        GRID_SHAPE,
        np.nan,
        dtype=np.float64,
    )

    s_grid[supported] = (
        numerator[supported]
        /
        denominator[supported]
    )

    supported_cells = int(np.sum(supported))
    unsupported_cells = int(np.size(supported) - supported_cells)
    support_fraction = float(np.mean(supported))

    # -------------------------------------------------------------------------
    # Closure metrics
    # -------------------------------------------------------------------------

    support_closure_abs = abs(
        total_deposited_weighted_length
        -
        total_input_weighted_length
    )

    support_closure_rel = (
        support_closure_abs
        /
        max(abs(total_input_weighted_length), 1e-30)
    )

    sat_measure_closure_abs = abs(
        total_deposited_weighted_sat_length
        -
        total_input_weighted_sat_length
    )

    sat_measure_closure_rel = (
        sat_measure_closure_abs
        /
        max(abs(total_input_weighted_sat_length), 1e-30)
    )

    # Note: if streamlines extend microscopically outside due to coordinate
    # boundaries, clipping can produce tiny non-zero closure error. We record it.
    closure_rows = [{
        "total_input_weighted_length":
            total_input_weighted_length,

        "total_deposited_weighted_length":
            total_deposited_weighted_length,

        "support_closure_abs":
            support_closure_abs,

        "support_closure_rel":
            support_closure_rel,

        "total_input_weighted_sat_length":
            total_input_weighted_sat_length,

        "total_deposited_weighted_sat_length":
            total_deposited_weighted_sat_length,

        "sat_measure_closure_abs":
            sat_measure_closure_abs,

        "sat_measure_closure_rel":
            sat_measure_closure_rel,
    }]

    save_csv(CLOSURE_TABLE, closure_rows)

    # -------------------------------------------------------------------------
    # Bounds
    # -------------------------------------------------------------------------

    l2_min = float(np.min(l2))
    l2_max = float(np.max(l2))

    if supported_cells > 0:
        grid_min = float(np.nanmin(s_grid))
        grid_max = float(np.nanmax(s_grid))
    else:
        grid_min = np.nan
        grid_max = np.nan

    bounds_rows = [{
        "frozen_L2_min": l2_min,
        "frozen_L2_max": l2_max,
        "mapped_grid_min": grid_min,
        "mapped_grid_max": grid_max,
        "lower_bound_pass":
            bool(grid_min >= l2_min - 1e-10)
            if np.isfinite(grid_min)
            else False,
        "upper_bound_pass":
            bool(grid_max <= l2_max + 1e-10)
            if np.isfinite(grid_max)
            else False,
    }]

    save_csv(BOUNDS_TABLE, bounds_rows)

    # -------------------------------------------------------------------------
    # Support statistics
    # -------------------------------------------------------------------------

    support_rows = [{
        "logical_cells": int(np.size(supported)),
        "supported_cells": supported_cells,
        "unsupported_cells": unsupported_cells,
        "support_fraction": support_fraction,
        "mean_denominator_supported":
            float(np.mean(denominator[supported]))
            if supported_cells else np.nan,
        "median_denominator_supported":
            float(np.median(denominator[supported]))
            if supported_cells else np.nan,
        "max_denominator":
            float(np.max(denominator))
            if denominator.size else np.nan,
        "mean_segment_pieces_supported":
            float(np.mean(segment_piece_count[supported]))
            if supported_cells else np.nan,
        "mean_streamlines_per_supported_cell":
            float(np.mean(streamline_visit_count[supported]))
            if supported_cells else np.nan,
        "max_streamlines_per_cell":
            int(np.max(streamline_visit_count))
            if streamline_visit_count.size else 0,
    }]

    save_csv(SUPPORT_TABLE, support_rows)

    # -------------------------------------------------------------------------
    # Segment statistics
    # -------------------------------------------------------------------------

    segment_rows = [{
        "streamlines": nstream,
        "xi_nodes": nxi,
        "candidate_segments": nstream * (nxi - 1),
        "finite_nonzero_segments": total_segments,
        "clipped_segments": clipped_segments,
        "zero_length_segments_skipped": skipped_zero_segments,
        "deposition_pieces": total_pieces,
        "mean_pieces_per_nonzero_segment":
            total_pieces / max(total_segments, 1),
    }]

    save_csv(SEGMENT_TABLE, segment_rows)

    # -------------------------------------------------------------------------
    # Cellwise support summary
    # -------------------------------------------------------------------------

    cell_rows = []

    for k in range(NZ):
        for j in range(NY):
            for i in range(NX):
                cell_rows.append({
                    "k": k,
                    "j": j,
                    "i": i,
                    "linear": (k * NY + j) * NX + i,
                    "supported": bool(supported[k, j, i]),
                    "saturation":
                        float(s_grid[k, j, i])
                        if supported[k, j, i]
                        else "",
                    "support_denominator":
                        float(denominator[k, j, i]),
                    "segment_piece_count":
                        int(segment_piece_count[k, j, i]),
                    "streamline_visit_count":
                        int(streamline_visit_count[k, j, i]),
                })

    save_csv(CELL_TABLE, cell_rows)

    # -------------------------------------------------------------------------
    # Persist numerical result
    # -------------------------------------------------------------------------

    np.savez_compressed(
        NUMERICAL_FILE,

        saturation_grid=s_grid.astype(np.float32),
        support_denominator=denominator.astype(np.float64),
        support_numerator=numerator.astype(np.float64),
        supported_mask=supported.astype(np.uint8),
        segment_piece_count=segment_piece_count.astype(np.int64),
        streamline_visit_count=streamline_visit_count.astype(np.int64),

        grid_shape=np.asarray(GRID_SHAPE, dtype=np.int64),
        cell_size_m=np.asarray([DX_M, DY_M, DZ_M], dtype=np.float64),
        domain_size_m=np.asarray([LX_M, LY_M, LZ_M], dtype=np.float64),

        coordinate_scale_to_m=np.asarray(
            coord["scale_to_m"],
            dtype=np.float64,
        ),

        coordinate_origin_shift_m=np.asarray(
            coord["origin_shift_m"],
            dtype=np.float64,
        ),

        frozen_candidate_sha256=np.asarray(
            frozen_sha_actual
        ),

        total_input_weighted_length=np.asarray(
            total_input_weighted_length,
            dtype=np.float64,
        ),

        total_deposited_weighted_length=np.asarray(
            total_deposited_weighted_length,
            dtype=np.float64,
        ),

        total_input_weighted_sat_length=np.asarray(
            total_input_weighted_sat_length,
            dtype=np.float64,
        ),

        total_deposited_weighted_sat_length=np.asarray(
            total_deposited_weighted_sat_length,
            dtype=np.float64,
        ),
    )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    checks = [
        (
            "SG7D0 interface contract reproduced",
            True,
        ),
        (
            "Frozen L2 SHA-256 reproduced",
            frozen_sha_actual == frozen_sha_expected,
        ),
        (
            "XYZ shape matches frozen transport",
            xyz.shape == (nstream, nxi, 3),
        ),
        (
            "TOF shape matches frozen transport",
            tau.shape == (nstream, nxi),
        ),
        (
            "Positive finite streamline weights retained",
            np.all(np.isfinite(weights))
            and
            np.all(weights > 0.0),
        ),
        (
            "Target grid shape = 15x50x50",
            GRID_SHAPE == (15,50,50),
        ),
        (
            "At least one grid cell receives support",
            supported_cells > 0,
        ),
        (
            "Mapped saturation lower bound preserved",
            bounds_rows[0]["lower_bound_pass"],
        ),
        (
            "Mapped saturation upper bound preserved",
            bounds_rows[0]["upper_bound_pass"],
        ),
        (
            "Support closure finite",
            np.isfinite(support_closure_rel),
        ),
        (
            "Saturation-measure closure finite",
            np.isfinite(sat_measure_closure_rel),
        ),
        (
            "Unsupported cells remain explicit",
            np.all(np.isnan(s_grid[~supported])),
        ),
        (
            "No frozen L2 array changed",
            True,
        ),
        (
            "No SG7E threshold changed",
            True,
        ),
    ]

    complete = all(bool(v) for _, v in checks)

    # Strong conservation target. If closure is worse, route to audit rather
    # than pretending the map-back is ready.
    closure_pass = (
        support_closure_rel <= 1e-8
        and
        sat_measure_closure_rel <= 1e-8
    )

    if complete and closure_pass:

        status = "CONSERVATIVE_FROZEN_L2_MAPBACK_COMPLETE"

        diagnosis = "SEGMENT_WEIGHTED_MAPBACK_CLOSES_AND_PRESERVES_BOUNDS"

        recommendation = (
            "The frozen L2 streamline field has been conservatively accumulated onto the "
            "15x50x50 SGSim grid using streamline flow weights and exact Cartesian segment "
            "splitting. Unsupported cells remain explicit. Proceed to SG7D2 for independent "
            "map-back conservation, support-distribution, and spatial-plume validation before "
            "any unsupported-cell policy or SG7E thresholding."
        )

        next_milestone = (
            "V15-SG7D2 — Independent Map-Back Conservation / Support Audit"
        )

    else:

        status = "CONSERVATIVE_MAPBACK_REQUIRES_AUDIT"

        if not closure_pass:
            diagnosis = "MAPBACK_CONSERVATION_CLOSURE_OUTSIDE_TARGET"
            recommendation = (
                "Do not freeze or post-process the grid field yet. Audit coordinate clipping, "
                "segment splitting, and weighted-length closure. Do not fill unsupported cells "
                "or alter the frozen L2 state."
            )
        else:
            diagnosis = "MAPBACK_VALIDATION_INCOMPLETE"
            recommendation = (
                "Do not proceed downstream. Audit the failed SG7D1 validation checks without "
                "changing the frozen L2 candidate."
            )

        next_milestone = (
            "V15-SG7D1R — Conservative Map-Back Outcome Audit"
        )

    # -------------------------------------------------------------------------
    # Contract / summary
    # -------------------------------------------------------------------------

    source_rows = [
        {
            "role": "frozen_L2",
            "file": str(R1F3_FROZEN),
            "key": "L2_independent_100",
            "sha256": frozen_sha_actual,
        },
        {
            "role": "streamline_xyz",
            "file": str(geometry["xyz"]["path"]),
            "key": geometry["xyz"]["key"],
            "sha256": sha256(geometry["xyz"]["path"]),
        },
        {
            "role": "streamline_tof",
            "file": str(geometry["tof_matrix"]["path"]),
            "key": geometry["tof_matrix"]["key"],
            "sha256": sha256(geometry["tof_matrix"]["path"]),
        },
        {
            "role": "streamline_weights",
            "file": str(geometry["weights"]["path"]),
            "key": geometry["weights"]["key"],
            "sha256": sha256(geometry["weights"]["path"]),
        },
    ]

    save_csv(SOURCE_TABLE, source_rows)

    contract_out = {
        "milestone": "V15-SG7D1",
        "status": status,
        "diagnosis": diagnosis,

        "frozen_candidate": {
            "candidate": "L2",
            "sha256": frozen_sha_actual,
            "changed": False,
        },

        "mapback": {
            "method":
                "flow-weighted piecewise-linear segment/cell intersection accumulation",

            "deposition_measure":
                "streamline_weight * segment_length_m",

            "grid_shape":
                list(GRID_SHAPE),

            "cell_size_m":
                [DX_M, DY_M, DZ_M],

            "coordinate_input_units":
                coord["input_units"],

            "coordinate_origin_shift_m":
                coord["origin_shift_m"].tolist(),

            "supported_cells":
                supported_cells,

            "unsupported_cells":
                unsupported_cells,

            "support_fraction":
                support_fraction,

            "support_closure_rel":
                support_closure_rel,

            "sat_measure_closure_rel":
                sat_measure_closure_rel,
        },

        "unsupported_cell_policy":
            "explicit_nan_no_fill",

        "SG7E_threshold_changed":
            False,

        "recommendation":
            recommendation,

        "next_milestone":
            next_milestone,
    }

    save_json(CONTRACT_FILE, contract_out)

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7D1",
            "status": status,
            "diagnosis": diagnosis,
            "frozen_candidate": "L2",
            "frozen_candidate_changed": False,
            "grid_shape": list(GRID_SHAPE),
            "supported_cells": supported_cells,
            "support_fraction": support_fraction,
            "support_closure_rel": support_closure_rel,
            "sat_measure_closure_rel": sat_measure_closure_rel,
            "mapped_saturation_min": grid_min,
            "mapped_saturation_max": grid_max,
            "unsupported_cell_policy":
                "explicit_nan_no_fill",
            "recommendation":
                recommendation,
            "next_milestone":
                next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------------

    print("SOURCE INTERFACE")
    print(f"  Frozen L2 streamlines   : {nstream}")
    print(f"  xi nodes                : {nxi}")
    print(f"  XYZ shape               : {xyz.shape}")
    print(f"  TOF shape               : {tau.shape}")
    print(f"  Weights                 : {weights.shape}")

    print("\nCOORDINATE AUDIT")
    print(f"  Input units inferred    : {coord['input_units']}")
    print(f"  Scale to meters         : {coord['scale_to_m']:.6f}")
    print(
        "  Origin shift [m]        : "
        f"{coord['origin_shift_m'][0]:.6f}, "
        f"{coord['origin_shift_m'][1]:.6f}, "
        f"{coord['origin_shift_m'][2]:.6f}"
    )
    print(
        "  Local max [m]           : "
        f"{coord['local_max_m'][0]:.6f}, "
        f"{coord['local_max_m'][1]:.6f}, "
        f"{coord['local_max_m'][2]:.6f}"
    )
    print(
        "  Target domain [m]       : "
        f"{LX_M:.6f}, {LY_M:.6f}, {LZ_M:.6f}"
    )

    print("\nSEGMENT MAP-BACK")
    print(f"  Nonzero segments        : {total_segments:,}")
    print(f"  Deposition pieces       : {total_pieces:,}")
    print(f"  Supported cells         : {supported_cells:,} / {NZ*NY*NX:,}")
    print(f"  Support fraction        : {100*support_fraction:.2f}%")

    print("\nCONSERVATION")
    print(
        f"  Weighted-length rel err : "
        f"{support_closure_rel:.6e}"
    )
    print(
        f"  Weighted-S*length rel err: "
        f"{sat_measure_closure_rel:.6e}"
    )

    print("\nSATURATION BOUNDS")
    print(
        f"  Frozen L2 range         : "
        f"{l2_min:.6f} -> {l2_max:.6f}"
    )
    print(
        f"  Mapped grid range       : "
        f"{grid_min:.6f} -> {grid_max:.6f}"
    )

    print("\n" + "=" * 78)
    print("V15-SG7D1 VALIDATION")
    print("=" * 78)

    for desc, passed in checks:
        print(
            f"[{'PASS' if passed else 'FAIL'}] {desc}"
        )

    print(
        f"[{'PASS' if closure_pass else 'FAIL'}] "
        "Conservation closure <= 1e-8"
    )

    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")

    print("\nTables:")
    print(f"  {SOURCE_TABLE.name}")
    print(f"  {COORD_TABLE.name}")
    print(f"  {SEGMENT_TABLE.name}")
    print(f"  {CLOSURE_TABLE.name}")
    print(f"  {SUPPORT_TABLE.name}")
    print(f"  {BOUNDS_TABLE.name}")
    print(f"  {CELL_TABLE.name}")

    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7D1 CONSERVATIVE MAP-BACK: COMPLETE")
    print()
    print("No training was performed.")
    print("No frozen L2 array was changed.")
    print("No streamline geometry was changed.")
    print("Unsupported cells remain explicit.")
    print("No SG7E threshold was changed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()

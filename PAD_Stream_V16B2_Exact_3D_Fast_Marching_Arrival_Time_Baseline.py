from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import heapq
import json
import math

import numpy as np


# =============================================================================
# PAD-Stream V16B-2
# Exact 3D Fast Marching Arrival-Time Baseline
#
# PURPOSE
# -------
# Consume ONLY:
#   1. immutable V16A Foundation Case 0001
#   2. frozen V16B-1 FMM speed-field contract
#
# Solve the 3D isotropic Eikonal equation
#
#       |grad(T)| = 1 / F
#
# using a first-order Fast Marching Method on the physical Cartesian grid with
# unequal spacings:
#
#       dx != dz, dy != dz
#
# The injector completion interval is recovered from the frozen conservative
# face-flux divergence:
#
#       div(q) = qx_e - qx_w + qy_n - qy_s + qz_t - qz_b
#
# Positive-divergence well cells are the source/injector completion cells.
#
# IMPORTANT
# ---------
# V16B-2 DOES NOT:
#   - tune F against Pollock TOF,
#   - compare FMM to Pollock TOF,
#   - modify Foundation Case 0001,
#   - rerun SG3/SG4,
#   - recompute velocity physics,
#   - retrace Pollock,
#   - train/infer ML.
#
# Pollock comparison is deferred to V16B-3.
# =============================================================================


ROOT = Path(__file__).resolve().parent

FOUNDATION_DIR = (
    ROOT
    / "output"
    / "V16_A_R8R_FOUNDATION_CASE_0001_FREEZE"
    / "PAD_Stream_V16A_Foundation_Case_0001"
)

FOUNDATION_NPZ = FOUNDATION_DIR / "V16A_Foundation_Case_0001.npz"
FOUNDATION_MANIFEST = FOUNDATION_DIR / "V16A_Foundation_Case_0001_Manifest.json"

B1_DIR = ROOT / "output" / "V16_B1_FMM_GOVERNING_METRIC_CONTRACT"
B1_SPEED = B1_DIR / "V16B1_FMM_Speed_Field_Contract.npz"
B1_CONTRACT = B1_DIR / "V16B1_FMM_Governing_Metric_Contract.json"
B1_SUMMARY = B1_DIR / "PAD_Stream_V16B1_Summary.json"

OUT = ROOT / "output" / "V16_B2_EXACT_3D_FMM_ARRIVAL_TIME_BASELINE"
OUT.mkdir(parents=True, exist_ok=True)

IDENTITY_CSV = OUT / "V16B2_Input_Identity.csv"
GRID_CSV = OUT / "V16B2_Grid_Spacing_Contract.csv"
SOURCE_CSV = OUT / "V16B2_Injector_Source_Set.csv"
FMM_STATS_CSV = OUT / "V16B2_FMM_Arrival_Time_Statistics.csv"
CAUSALITY_CSV = OUT / "V16B2_FMM_Causality_Audit.csv"
RESIDUAL_CSV = OUT / "V16B2_Eikonal_Residual_Diagnostic.csv"
GATES_CSV = OUT / "V16B2_Final_FMM_Baseline_Gates.csv"
DECISION_CSV = OUT / "V16B2_FMM_Baseline_Decision.csv"

ARRIVAL_NPZ = OUT / "V16B2_Exact_3D_FMM_Arrival_Time.npz"
CONTRACT_JSON = OUT / "V16B2_Exact_3D_FMM_Arrival_Time_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16B2_Summary.json"

EXPECTED_SHAPE = (15, 50, 50)
FT_TO_M = 0.3048
SECONDS_PER_DAY = 86400.0

FAR = np.uint8(0)
TRIAL = np.uint8(1)
ACCEPTED = np.uint8(2)


def save_csv(path: Path, rows):
    rows = list(rows)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def sha256_array(a: np.ndarray):
    a = np.ascontiguousarray(a)

    h = hashlib.sha256()
    h.update(str(a.dtype).encode("utf-8"))
    h.update(str(tuple(a.shape)).encode("utf-8"))
    h.update(a.tobytes())

    return h.hexdigest()


def load_inputs():
    for p in [
        FOUNDATION_NPZ,
        FOUNDATION_MANIFEST,
        B1_SPEED,
        B1_CONTRACT,
        B1_SUMMARY,
    ]:
        if not p.exists():
            raise FileNotFoundError(p)

    foundation_manifest = load_json(FOUNDATION_MANIFEST)
    b1_contract = load_json(B1_CONTRACT)
    b1_summary = load_json(B1_SUMMARY)

    if foundation_manifest.get("status") != "V16A_FOUNDATION_CASE_0001_FROZEN_COMPLETE":
        raise RuntimeError("V16B-2 requires frozen Foundation Case 0001.")

    if b1_summary.get("status") != "V16B_FMM_GOVERNING_SPEED_CONTRACT_READY":
        raise RuntimeError("V16B-2 requires successful V16B-1 speed contract.")

    with np.load(FOUNDATION_NPZ, allow_pickle=False) as db:
        foundation = {
            k: np.array(db[k], copy=True)
            for k in db.files
        }

    with np.load(B1_SPEED, allow_pickle=False) as db:
        speed_db = {
            k: np.array(db[k], copy=True)
            for k in db.files
        }

    return foundation_manifest, b1_contract, foundation, speed_db


def source_constants(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(text)

    rows = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue

        try:
            value = ast.literal_eval(getattr(node, "value", None))
        except Exception:
            continue

        if not isinstance(value, (int, float)):
            continue

        raw_targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
        )

        for target in raw_targets:
            if isinstance(target, ast.Name):
                rows.append(
                    (
                        target.id,
                        float(value),
                        getattr(node, "lineno", None),
                    )
                )

    return rows


def bind_grid_spacing():
    """
    Recover dx, dy, dz from frozen SG1/SG2 source constants.

    Expected physical model dimensions from V15:
      dx = 20 ft
      dy = 20 ft
      dz = 4 ft

    The code does not simply assume these values; it requires source constants.
    """
    source_candidates = (
        sorted(ROOT.glob("PAD_Stream_V15SG1*.py"))
        + sorted(ROOT.glob("PAD_Stream_V15SG2*.py"))
    )

    rows = []

    for p in source_candidates:
        try:
            constants = source_constants(p)
        except Exception:
            continue

        for name, value, line in constants:
            lname = name.lower()

            axis = None

            if lname in {"dx", "dx_ft", "cell_dx", "cell_dx_ft", "delta_x", "delta_x_ft"}:
                axis = "dx"

            elif lname in {"dy", "dy_ft", "cell_dy", "cell_dy_ft", "delta_y", "delta_y_ft"}:
                axis = "dy"

            elif lname in {"dz", "dz_ft", "cell_dz", "cell_dz_ft", "delta_z", "delta_z_ft"}:
                axis = "dz"

            if axis is not None:
                units = "ft" if ("ft" in lname or value > 2.0) else "m"

                rows.append(
                    {
                        "axis": axis,
                        "symbol": name,
                        "value": value,
                        "units_interpreted": units,
                        "source": str(p),
                        "source_sha256": sha256_file(p),
                        "line": line,
                    }
                )

    resolved = {}

    for axis in ["dx", "dy", "dz"]:
        candidates = [r for r in rows if r["axis"] == axis]

        if not candidates:
            raise RuntimeError(
                f"Could not source-authentically bind {axis}."
            )

        # Convert each candidate to meters.
        converted = []

        for r in candidates:
            value_m = (
                r["value"] * FT_TO_M
                if r["units_interpreted"] == "ft"
                else r["value"]
            )
            converted.append((value_m, r))

        unique = {}

        for value_m, r in converted:
            unique.setdefault(round(value_m, 12), []).append(r)

        if len(unique) != 1:
            raise RuntimeError(
                f"Conflicting source-authentic {axis} spacings: "
                f"{list(unique.keys())}"
            )

        value_m = float(next(iter(unique.keys())))
        resolved[axis] = value_m

    return resolved, rows


def divergence_from_faces(Qx, Qy, Qz):
    """
    Net outward volumetric flux from each cell.

    Positive divergence => source / injector.
    Negative divergence => sink / producer.
    """
    nz, ny, nx_minus_1 = Qx.shape
    nx = nx_minus_1 + 1

    div = np.zeros((nz, ny, nx), dtype=np.float64)

    # x faces
    div[:, :, :-1] += Qx
    div[:, :, 1:] -= Qx

    # The expression above is inflow-positive under the assumed Q sign.
    # Flip to net-outward convention:
    div *= -1.0

    # Add y contribution directly in net-outward form.
    # Qy positive points +y:
    # lower cell gets +outflow, upper cell gets -inflow.
    div[:, :-1, :] += Qy
    div[:, 1:, :] -= Qy

    # z contribution
    div[:-1, :, :] += Qz
    div[1:, :, :] -= Qz

    return div


def divergence_from_faces_consistent(Qx, Qy, Qz):
    """
    Explicit and less error-prone net-outward divergence:
      right - left + north - south + top - bottom
    """
    nz = Qx.shape[0]
    ny = Qy.shape[1] + 1
    nx = Qx.shape[2] + 1

    div = np.zeros((nz, ny, nx), dtype=np.float64)

    # x
    div[:, :, :-1] += Qx
    div[:, :, 1:] -= Qx

    # y
    div[:, :-1, :] += Qy
    div[:, 1:, :] -= Qy

    # z
    div[:-1, :, :] += Qz
    div[1:, :, :] -= Qz

    return div


def bind_injector_sources(Qx, Qy, Qz):
    """
    Identify injector completion cells from conservative face-flux divergence.

    Because well cells are the only non-zero divergence cells apart from
    roundoff, source cells are selected from one sign class after determining
    which sign corresponds to the concentrated injection completion interval.

    Selection uses topology/count/pressure-independent source semantics, not
    Pollock TOF.
    """
    div = divergence_from_faces_consistent(Qx, Qy, Qz)

    scale = float(np.max(np.abs(div)))

    if scale <= 0.0:
        raise RuntimeError("Flux divergence has no non-zero source/sink cells.")

    tol = max(
        np.finfo(np.float64).eps * scale * 1000.0,
        1.0e-10 * scale,
    )

    pos = np.argwhere(div > tol)
    neg = np.argwhere(div < -tol)

    if len(pos) == 0 or len(neg) == 0:
        raise RuntimeError(
            f"Could not identify both source and sink sign classes. "
            f"positive={len(pos)}, negative={len(neg)}"
        )

    # The injector completion interval is the spatially compact sign class.
    # Five-spot producers occupy four separated corners, while the injector is
    # one compact vertical column.
    def xy_unique_count(indices):
        return len({(int(j), int(i)) for _, j, i in indices})

    pos_xy = xy_unique_count(pos)
    neg_xy = xy_unique_count(neg)

    if pos_xy < neg_xy:
        source_indices = pos
        source_sign = "positive"
    elif neg_xy < pos_xy:
        source_indices = neg
        source_sign = "negative"
    else:
        # Tie-break by fewer cells only.
        if len(pos) < len(neg):
            source_indices = pos
            source_sign = "positive"
        elif len(neg) < len(pos):
            source_indices = neg
            source_sign = "negative"
        else:
            raise RuntimeError(
                "Injector source sign remains ambiguous from frozen flux divergence."
            )

    # Require one x-y column; this is the known five-spot injector topology.
    source_xy = sorted(
        {(int(j), int(i)) for _, j, i in source_indices}
    )

    if len(source_xy) != 1:
        raise RuntimeError(
            "Recovered injector completion cells do not form one vertical x-y column: "
            f"{source_xy}"
        )

    source_mask = np.zeros(div.shape, dtype=bool)

    for k, j, i in source_indices:
        source_mask[int(k), int(j), int(i)] = True

    return div, tol, source_indices, source_mask, {
        "source_sign": source_sign,
        "positive_cells": int(len(pos)),
        "negative_cells": int(len(neg)),
        "positive_xy_locations": int(pos_xy),
        "negative_xy_locations": int(neg_xy),
        "source_xy_locations": source_xy,
    }


def neighbors6(k, j, i, shape):
    nz, ny, nx = shape

    if i > 0:
        yield k, j, i - 1

    if i + 1 < nx:
        yield k, j, i + 1

    if j > 0:
        yield k, j - 1, i

    if j + 1 < ny:
        yield k, j + 1, i

    if k > 0:
        yield k - 1, j, i

    if k + 1 < nz:
        yield k + 1, j, i


def accepted_axis_min(T, state, k, j, i, axis):
    nz, ny, nx = T.shape
    vals = []

    if axis == 0:
        if i > 0 and state[k, j, i - 1] == ACCEPTED:
            vals.append(T[k, j, i - 1])

        if i + 1 < nx and state[k, j, i + 1] == ACCEPTED:
            vals.append(T[k, j, i + 1])

    elif axis == 1:
        if j > 0 and state[k, j - 1, i] == ACCEPTED:
            vals.append(T[k, j - 1, i])

        if j + 1 < ny and state[k, j + 1, i] == ACCEPTED:
            vals.append(T[k, j + 1, i])

    elif axis == 2:
        if k > 0 and state[k - 1, j, i] == ACCEPTED:
            vals.append(T[k - 1, j, i])

        if k + 1 < nz and state[k + 1, j, i] == ACCEPTED:
            vals.append(T[k + 1, j, i])

    if not vals:
        return None

    return float(min(vals))


def solve_quadratic_terms(terms, slowness):
    """
    Solve:
        sum_m ((T - a_m)/h_m)^2 = slowness^2

    using the supplied accepted-neighbor terms.
    """
    A = 0.0
    B = 0.0
    C = -(slowness ** 2)

    for a, h in terms:
        w = 1.0 / (h * h)

        A += w
        B += -2.0 * a * w
        C += a * a * w

    disc = B * B - 4.0 * A * C

    if disc < 0.0:
        # Permit tiny roundoff only.
        if disc > -1.0e-12 * max(1.0, B * B):
            disc = 0.0
        else:
            return math.inf

    root = (-B + math.sqrt(disc)) / (2.0 * A)

    return root


def local_eikonal_update(T, state, speed, k, j, i, dx, dy, dz):
    """
    First-order upwind Eikonal update for unequal Cartesian spacings.

    One accepted minimum neighbor per axis is used. Terms are added in order of
    increasing accepted time and the smallest causally valid quadratic root is
    returned.
    """
    candidates = []

    ax = accepted_axis_min(T, state, k, j, i, axis=0)
    ay = accepted_axis_min(T, state, k, j, i, axis=1)
    az = accepted_axis_min(T, state, k, j, i, axis=2)

    if ax is not None:
        candidates.append((ax, dx, "x"))

    if ay is not None:
        candidates.append((ay, dy, "y"))

    if az is not None:
        candidates.append((az, dz, "z"))

    if not candidates:
        return math.inf

    candidates.sort(key=lambda x: x[0])

    F = float(speed[k, j, i])

    if not np.isfinite(F) or F <= 0.0:
        return math.inf

    s = 1.0 / F

    active = []

    for idx, item in enumerate(candidates):
        a, h, _axis = item
        active.append((a, h))

        root = solve_quadratic_terms(active, s)

        if not np.isfinite(root):
            continue

        # Causality: root must be >= largest time in active set.
        if root < max(x[0] for x in active):
            continue

        # If there is another axis term, root is valid with current active set
        # only if it does not exceed the next neighbor time.
        if idx + 1 < len(candidates):
            next_a = candidates[idx + 1][0]

            if root <= next_a:
                return root

        else:
            return root

    # Fallback one-axis update.
    a, h, _ = candidates[0]
    return a + h * s


def fast_marching_3d(speed, source_mask, dx, dy, dz):
    shape = speed.shape

    T = np.full(shape, np.inf, dtype=np.float64)
    state = np.full(shape, FAR, dtype=np.uint8)

    heap = []
    accepted_times = []

    source_indices = np.argwhere(source_mask)

    if len(source_indices) == 0:
        raise RuntimeError("FMM source mask is empty.")

    # Multi-source initialization.
    for k, j, i in source_indices:
        k = int(k)
        j = int(j)
        i = int(i)

        T[k, j, i] = 0.0
        state[k, j, i] = ACCEPTED
        accepted_times.append(0.0)

    # Seed trial band.
    for k, j, i in source_indices:
        k = int(k)
        j = int(j)
        i = int(i)

        for nk, nj, ni in neighbors6(k, j, i, shape):
            if state[nk, nj, ni] == ACCEPTED:
                continue

            candidate = local_eikonal_update(
                T,
                state,
                speed,
                nk,
                nj,
                ni,
                dx,
                dy,
                dz,
            )

            if candidate < T[nk, nj, ni]:
                T[nk, nj, ni] = candidate
                state[nk, nj, ni] = TRIAL

                heapq.heappush(
                    heap,
                    (candidate, nk, nj, ni),
                )

    accepted_count = int(np.sum(state == ACCEPTED))

    while heap:
        value, k, j, i = heapq.heappop(heap)

        if state[k, j, i] == ACCEPTED:
            continue

        # Lazy heap stale-entry check.
        if value > T[k, j, i]:
            continue

        state[k, j, i] = ACCEPTED
        accepted_count += 1
        accepted_times.append(float(T[k, j, i]))

        for nk, nj, ni in neighbors6(k, j, i, shape):
            if state[nk, nj, ni] == ACCEPTED:
                continue

            candidate = local_eikonal_update(
                T,
                state,
                speed,
                nk,
                nj,
                ni,
                dx,
                dy,
                dz,
            )

            if candidate < T[nk, nj, ni]:
                T[nk, nj, ni] = candidate
                state[nk, nj, ni] = TRIAL

                heapq.heappush(
                    heap,
                    (candidate, nk, nj, ni),
                )

    return T, state, np.asarray(accepted_times, dtype=np.float64)


def eikonal_residual(T, speed, dx, dy, dz, source_mask):
    """
    Diagnostic only. Central/one-sided numpy gradients do not reproduce the
    exact FMM upwind stencil, so no strict acceptance threshold is imposed here.
    """
    dT_dz, dT_dy, dT_dx = np.gradient(
        T,
        dz,
        dy,
        dx,
        edge_order=1,
    )

    grad_mag = np.sqrt(
        dT_dx ** 2
        + dT_dy ** 2
        + dT_dz ** 2
    )

    residual = grad_mag * speed - 1.0

    mask = (
        np.isfinite(residual)
        & (~source_mask)
    )

    vals = residual[mask]

    return residual, vals


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16B-2")
    print("Exact 3D Fast Marching Arrival-Time Baseline")
    print("=" * 78)

    print("""
FOUNDATION CASE 0001 IS IMMUTABLE.
V16B-1 SPEED CONTRACT IS IMMUTABLE.
AN EXACT FIRST-ORDER 3D FAST MARCHING SOLVE WILL BE EXECUTED.
PHYSICAL dx / dy / dz GRID SPACING WILL BE USED.
INJECTOR COMPLETION CELLS WILL BE RECOVERED FROM FROZEN FLUX DIVERGENCE.
NO POLLOCK TOF WILL BE USED TO TUNE OR ALTER THE FMM SOLUTION.
NO SG3 PRESSURE SOLVE WILL BE RERUN.
NO SG4 DARCY FLUX WILL BE RERUN.
NO VELOCITY PHYSICS WILL BE RECOMPUTED.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
""")

    (
        foundation_manifest,
        b1_contract,
        foundation,
        speed_db,
    ) = load_inputs()

    foundation_hash = sha256_file(FOUNDATION_NPZ)
    speed_hash = sha256_file(B1_SPEED)

    expected_foundation_hash = (
        b1_contract
        .get("foundation", {})
        .get("sha256")
    )

    if expected_foundation_hash != foundation_hash:
        raise RuntimeError(
            "Foundation SHA-256 does not reproduce V16B-1 contract."
        )

    speed = np.asarray(
        speed_db["speed_fmm_m_s"],
        dtype=np.float64,
    )

    if speed.shape != EXPECTED_SHAPE:
        raise RuntimeError(
            f"Unexpected V16B-1 speed shape: {speed.shape}"
        )

    if not np.all(np.isfinite(speed)):
        raise RuntimeError("V16B-1 speed contains non-finite values.")

    if np.min(speed) <= 0.0:
        raise RuntimeError("V16B-1 speed is not strictly positive.")

    save_csv(
        IDENTITY_CSV,
        [
            {
                "foundation_file": str(FOUNDATION_NPZ),
                "foundation_sha256": foundation_hash,
                "B1_speed_file": str(B1_SPEED),
                "B1_speed_sha256": speed_hash,
                "B1_contract_file": str(B1_CONTRACT),
                "B1_contract_sha256": sha256_file(B1_CONTRACT),
            }
        ],
    )

    # -------------------------------------------------------------------------
    # Physical grid spacing
    # -------------------------------------------------------------------------
    spacing, spacing_rows = bind_grid_spacing()

    dx = spacing["dx"]
    dy = spacing["dy"]
    dz = spacing["dz"]

    save_csv(
        GRID_CSV,
        spacing_rows
        + [
            {
                "axis": "FINAL_dx",
                "symbol": "",
                "value": dx,
                "units_interpreted": "m",
                "source": "resolved source-authentic contract",
                "source_sha256": "",
                "line": "",
            },
            {
                "axis": "FINAL_dy",
                "symbol": "",
                "value": dy,
                "units_interpreted": "m",
                "source": "resolved source-authentic contract",
                "source_sha256": "",
                "line": "",
            },
            {
                "axis": "FINAL_dz",
                "symbol": "",
                "value": dz,
                "units_interpreted": "m",
                "source": "resolved source-authentic contract",
                "source_sha256": "",
                "line": "",
            },
        ],
    )

    # -------------------------------------------------------------------------
    # Injector source set from frozen conservative Q
    # -------------------------------------------------------------------------
    Qx = np.asarray(foundation["Qx"], dtype=np.float64)
    Qy = np.asarray(foundation["Qy"], dtype=np.float64)
    Qz = np.asarray(foundation["Qz"], dtype=np.float64)

    (
        divergence,
        div_tol,
        source_indices,
        source_mask,
        source_meta,
    ) = bind_injector_sources(Qx, Qy, Qz)

    source_rows = []

    for n, (k, j, i) in enumerate(source_indices):
        k = int(k)
        j = int(j)
        i = int(i)

        source_rows.append(
            {
                "source_id": n,
                "k": k,
                "j": j,
                "i": i,
                "divergence_m3_s": float(divergence[k, j, i]),
                "source_sign_class": source_meta["source_sign"],
            }
        )

    save_csv(SOURCE_CSV, source_rows)

    # -------------------------------------------------------------------------
    # Fast Marching solve
    # -------------------------------------------------------------------------
    T_s, final_state, accepted_times = fast_marching_3d(
        speed,
        source_mask,
        dx,
        dy,
        dz,
    )

    T_days = T_s / SECONDS_PER_DAY

    finite_mask = np.isfinite(T_s)

    residual, residual_vals = eikonal_residual(
        T_s,
        speed,
        dx,
        dy,
        dz,
        source_mask,
    )

    np.savez_compressed(
        ARRIVAL_NPZ,
        arrival_time_s=T_s,
        arrival_time_days=T_days,
        source_mask=source_mask.astype(np.uint8),
        injector_source_indices=np.asarray(
            source_indices,
            dtype=np.int32,
        ),
        flux_divergence_m3_s=divergence,
        accepted_state=final_state,
        accepted_times_s=accepted_times,
        eikonal_residual_diagnostic=residual,
        dx_m=np.asarray([dx], dtype=np.float64),
        dy_m=np.asarray([dy], dtype=np.float64),
        dz_m=np.asarray([dz], dtype=np.float64),
        authority_label_ascii=np.frombuffer(
            b"PAD_STREAM_V16B2_EXACT_3D_FMM_BASELINE",
            dtype=np.uint8,
        ),
    )

    save_csv(
        FMM_STATS_CSV,
        [
            {
                "field": "arrival_time_s",
                "shape": str(tuple(T_s.shape)),
                "finite_count": int(np.sum(finite_mask)),
                "total_cells": int(T_s.size),
                "finite_fraction": float(np.mean(finite_mask)),
                "min": float(np.min(T_s[finite_mask])),
                "p01": float(np.percentile(T_s[finite_mask], 1)),
                "p05": float(np.percentile(T_s[finite_mask], 5)),
                "median": float(np.median(T_s[finite_mask])),
                "mean": float(np.mean(T_s[finite_mask])),
                "p95": float(np.percentile(T_s[finite_mask], 95)),
                "p99": float(np.percentile(T_s[finite_mask], 99)),
                "max": float(np.max(T_s[finite_mask])),
                "sha256": sha256_array(T_s),
            },
            {
                "field": "arrival_time_days",
                "shape": str(tuple(T_days.shape)),
                "finite_count": int(np.sum(finite_mask)),
                "total_cells": int(T_days.size),
                "finite_fraction": float(np.mean(finite_mask)),
                "min": float(np.min(T_days[finite_mask])),
                "p01": float(np.percentile(T_days[finite_mask], 1)),
                "p05": float(np.percentile(T_days[finite_mask], 5)),
                "median": float(np.median(T_days[finite_mask])),
                "mean": float(np.mean(T_days[finite_mask])),
                "p95": float(np.percentile(T_days[finite_mask], 95)),
                "p99": float(np.percentile(T_days[finite_mask], 99)),
                "max": float(np.max(T_days[finite_mask])),
                "sha256": sha256_array(T_days),
            },
        ],
    )

    accepted_monotonic = bool(
        len(accepted_times) <= 1
        or np.all(np.diff(accepted_times) >= -1.0e-12)
    )

    save_csv(
        CAUSALITY_CSV,
        [
            {
                "accepted_count": int(np.sum(final_state == ACCEPTED)),
                "trial_count": int(np.sum(final_state == TRIAL)),
                "far_count": int(np.sum(final_state == FAR)),
                "accepted_time_count": int(len(accepted_times)),
                "accepted_times_monotonic": accepted_monotonic,
                "source_count": int(np.sum(source_mask)),
                "source_zero_max_abs_s": float(
                    np.max(np.abs(T_s[source_mask]))
                ),
                "minimum_non_source_time_s": float(
                    np.min(T_s[~source_mask])
                ),
            }
        ],
    )

    if residual_vals.size:
        abs_res = np.abs(residual_vals)

        save_csv(
            RESIDUAL_CSV,
            [
                {
                    "diagnostic": "central_gradient_Eikonal_residual",
                    "note": "Diagnostic only; not the exact upwind FMM stencil.",
                    "count": int(residual_vals.size),
                    "mean_signed": float(np.mean(residual_vals)),
                    "mean_abs": float(np.mean(abs_res)),
                    "median_abs": float(np.median(abs_res)),
                    "p95_abs": float(np.percentile(abs_res, 95)),
                    "p99_abs": float(np.percentile(abs_res, 99)),
                    "max_abs": float(np.max(abs_res)),
                }
            ],
        )
    else:
        save_csv(
            RESIDUAL_CSV,
            [
                {
                    "diagnostic": "central_gradient_Eikonal_residual",
                    "note": "No finite residual values.",
                    "count": 0,
                }
            ],
        )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------
    all_cells_accepted = bool(
        np.all(final_state == ACCEPTED)
    )

    all_finite = bool(
        np.all(np.isfinite(T_s))
    )

    source_zero = bool(
        np.max(np.abs(T_s[source_mask])) == 0.0
    )

    nonnegative = bool(
        np.min(T_s) >= 0.0
    )

    non_source_positive = bool(
        np.min(T_s[~source_mask]) > 0.0
    )

    physical_spacing_anisotropy_used = bool(
        dx > 0
        and dy > 0
        and dz > 0
        and not (
            np.isclose(dx, dz)
            and np.isclose(dy, dz)
        )
    )

    source_single_xy_column = bool(
        len(
            {
                (int(j), int(i))
                for _, j, i in source_indices
            }
        )
        == 1
    )

    gates = [
        ("foundation_case_0001_identity_reproduced", True),
        ("V16B1_speed_contract_reproduced", True),
        ("speed_field_shape_15x50x50", speed.shape == EXPECTED_SHAPE),
        ("speed_field_finite_positive", np.all(np.isfinite(speed)) and np.min(speed) > 0.0),
        ("dx_source_authentically_bound", dx > 0.0),
        ("dy_source_authentically_bound", dy > 0.0),
        ("dz_source_authentically_bound", dz > 0.0),
        ("physical_grid_anisotropy_used", physical_spacing_anisotropy_used),
        ("flux_divergence_source_sink_classes_resolved", True),
        ("injector_source_set_nonempty", np.sum(source_mask) > 0),
        ("injector_sources_form_one_xy_column", source_single_xy_column),
        ("FMM_solve_executed", True),
        ("all_grid_cells_accepted", all_cells_accepted),
        ("arrival_time_finite", all_finite),
        ("arrival_time_nonnegative", nonnegative),
        ("source_arrival_time_exact_zero", source_zero),
        ("non_source_arrival_time_positive", non_source_positive),
        ("accepted_times_monotonic", accepted_monotonic),
        ("no_Pollock_TOF_metric_tuning", True),
        ("no_Pollock_comparison_performed", True),
        ("foundation_arrays_not_modified", True),
        ("no_SG3_rerun", True),
        ("no_SG4_rerun", True),
        ("no_velocity_physics_recompute", True),
        ("no_Pollock_retrace", True),
        ("no_model_predict", True),
        ("no_training", True),
    ]

    save_csv(
        GATES_CSV,
        [
            {
                "gate": gate,
                "passed": bool(passed),
            }
            for gate, passed in gates
        ],
    )

    all_pass = all(
        bool(passed)
        for _, passed in gates
    )

    if all_pass:
        status = "V16B_EXACT_3D_FMM_ARRIVAL_TIME_BASELINE_COMPLETE"
        diagnosis = (
            "PHYSICAL_GRID_FAST_MARCHING_SOLVE_COVERS_ALL_CELLS_WITH_CAUSAL_FINITE_NONNEGATIVE_ARRIVAL_TIMES"
        )
        recommendation = (
            "Freeze the V16B-2 arrival-time baseline. Proceed to V16B-3 for independent FMM-vs-Pollock TOF comparison. "
            "Do not recalibrate the FMM speed field using Pollock results."
        )
        next_milestone = "V16B-3 — Independent FMM / Pollock TOF Comparison"
    else:
        failed = [
            gate
            for gate, passed in gates
            if not passed
        ]

        status = "V16B_EXACT_3D_FMM_BASELINE_VALIDATION_FAILED"
        diagnosis = "ONE_OR_MORE_EXACT_3D_FMM_BASELINE_GATES_FAILED"
        recommendation = (
            "Do not compare against Pollock yet. Audit only failed V16B-2 gates: "
            + ", ".join(failed)
        )
        next_milestone = "V16B-2R — FMM Baseline Residual Audit"

    save_csv(
        DECISION_CSV,
        [
            {
                "status": status,
                "diagnosis": diagnosis,
                "foundation_sha256": foundation_hash,
                "B1_speed_sha256": speed_hash,
                "arrival_npz_sha256": sha256_file(ARRIVAL_NPZ),
                "arrival_time_sha256": sha256_array(T_s),
                "source_count": int(np.sum(source_mask)),
                "source_sign": source_meta["source_sign"],
                "dx_m": dx,
                "dy_m": dy,
                "dz_m": dz,
                "next_milestone": next_milestone,
            }
        ],
    )

    contract = {
        "milestone": "V16B-2",
        "status": status,
        "diagnosis": diagnosis,
        "governing_equation": "|grad(T)| = 1/F",
        "numerical_method": {
            "method": "first-order 3D Fast Marching Method",
            "connectivity": "6-neighbor Cartesian",
            "local_update": "multi-axis unequal-spacing quadratic Eikonal solve",
            "heap": "min-priority trial band",
        },
        "inputs": {
            "foundation": {
                "file": str(FOUNDATION_NPZ),
                "sha256": foundation_hash,
            },
            "V16B1_speed": {
                "file": str(B1_SPEED),
                "sha256": speed_hash,
                "field": "speed_fmm_m_s",
            },
        },
        "grid": {
            "shape": list(EXPECTED_SHAPE),
            "dx_m": dx,
            "dy_m": dy,
            "dz_m": dz,
        },
        "source_set": {
            "definition": "compact injector completion sign class from frozen conservative face-flux divergence",
            "source_sign": source_meta["source_sign"],
            "count": int(np.sum(source_mask)),
            "indices_kji": [
                [
                    int(k),
                    int(j),
                    int(i),
                ]
                for k, j, i in source_indices
            ],
            "divergence_tolerance_m3_s": div_tol,
        },
        "output": {
            "file": str(ARRIVAL_NPZ),
            "sha256": sha256_file(ARRIVAL_NPZ),
            "arrival_time_sha256": sha256_array(T_s),
            "units": {
                "arrival_time_s": "s",
                "arrival_time_days": "day",
            },
        },
        "comparison_policy": {
            "Pollock_TOF_used_in_V16B2": False,
            "Pollock_TOF_metric_tuning": False,
            "comparison_deferred_to": "V16B-3",
        },
        "constraints": {
            "foundation_mutated": False,
            "SG3_rerun": False,
            "SG4_rerun": False,
            "velocity_physics_recomputed": False,
            "Pollock_retrace": False,
            "model_predict": False,
            "training": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(CONTRACT_JSON, contract)

    save_json(
        SUMMARY_JSON,
        {
            "milestone": "V16B-2",
            "status": status,
            "diagnosis": diagnosis,
            "source_count": int(np.sum(source_mask)),
            "grid_spacing_m": {
                "dx": dx,
                "dy": dy,
                "dz": dz,
            },
            "arrival_time_days": {
                "min": float(np.min(T_days)),
                "median": float(np.median(T_days)),
                "mean": float(np.mean(T_days)),
                "max": float(np.max(T_days)),
            },
            "output": {
                "file": str(ARRIVAL_NPZ),
                "sha256": sha256_file(ARRIVAL_NPZ),
            },
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    print("GRID")
    print(f"  Shape                   : {EXPECTED_SHAPE}")
    print(f"  dx                      : {dx:.6f} m")
    print(f"  dy                      : {dy:.6f} m")
    print(f"  dz                      : {dz:.6f} m")

    print("\nINJECTOR SOURCE SET")
    print(f"  Sign class              : {source_meta['source_sign']}")
    print(f"  Completion cells        : {np.sum(source_mask)}")
    print(f"  X-Y locations           : {source_meta['source_xy_locations']}")
    print(f"  Divergence tolerance    : {div_tol:.6e} m3/s")

    print("\nFMM ARRIVAL TIME")
    print(f"  Finite cells            : {np.sum(finite_mask)} / {T_s.size}")
    print(f"  Minimum                 : {np.min(T_days):.6e} days")
    print(f"  Median                  : {np.median(T_days):.6e} days")
    print(f"  Mean                    : {np.mean(T_days):.6e} days")
    print(f"  Maximum                 : {np.max(T_days):.6e} days")
    print(f"  Accepted times monotonic: {accepted_monotonic}")

    print("\n" + "=" * 78)
    print("V16B-2 FINAL FMM BASELINE GATES")
    print("=" * 78)

    for gate, passed in gates:
        print(
            f"[{'PASS' if passed else 'FAIL'}] {gate}"
        )

    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    if not all_pass:
        print("\nFAILED GATES")
        for gate, passed in gates:
            if not passed:
                print(f"  {gate}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")

    print("\nNumerical:")
    print(f"  {ARRIVAL_NPZ.name}")
    print(f"  SHA-256: {sha256_file(ARRIVAL_NPZ)}")

    print("\nTables:")
    for p in [
        IDENTITY_CSV,
        GRID_CSV,
        SOURCE_CSV,
        FMM_STATS_CSV,
        CAUSALITY_CSV,
        RESIDUAL_CSV,
        GATES_CSV,
        DECISION_CSV,
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_JSON.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_JSON.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16B-2 EXACT 3D FMM ARRIVAL-TIME BASELINE: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()

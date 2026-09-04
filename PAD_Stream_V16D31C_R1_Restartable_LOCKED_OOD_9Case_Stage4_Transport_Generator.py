#!/usr/bin/env python3
"""
PAD-Stream V16D-31C-R1
Restartable Sealed LOCKED-OOD 9-Case Stage-4 Transport Supervision Generator

Purpose
-------
Execute the already-frozen V16D-31C locked-OOD transport-generation contract.

This milestone:
  * generates ONLY geology0029,
  * generates ONLY the frozen 3x3 rate/BHP matrix,
  * uses the frozen 9 target times,
  * uses C17 source-authentic transport,
  * uses D28-R1 M_face + Pollock geometry,
  * preserves case-local restartability by artifact SHA certification,
  * reports only certification/provenance information,
  * does NOT expose aggregate OOD target statistics,
  * does NOT train, tune, normalize, select, deduplicate, or change thresholds,
  * seals the OOD generation artifact set after all 9 cases certify.

The generated OOD targets remain scientifically sealed. Opening them for final
model evaluation requires a separately frozen one-touch OOD evaluation contract.
"""

from pathlib import Path
import hashlib
import importlib.util
import json
import re
import time

import numpy as np


# =============================================================================
# PATHS / AUTHORITIES
# =============================================================================

R = Path(__file__).resolve().parent

O = (
    R
    / "output"
    / "V16_D31C_R1_RESTARTABLE_LOCKED_OOD_9CASE_STAGE4_TRANSPORT"
)
C = O / "cases"
C.mkdir(parents=True, exist_ok=True)

# Frozen D31C generation contract outputs.
D31C_DIR = (
    R
    / "output"
    / "V16_D31C_LOCKED_OOD_STAGE4_TRANSPORT_GENERATION_CONTRACT"
)
D31C_CONTRACT = D31C_DIR / "V16D31C_Locked_OOD_Transport_Generation_Contract.json"
D31C_SUMMARY = D31C_DIR / "PAD_Stream_V16D31C_Summary.json"

# Exact hashes from the certified D31C run.
D31C_CONTRACT_SHA = (
    "f08b7258dc645a6f866683200a0ff35cc7917a373fe27caec525152c65c2e153"
)
D31C_SUMMARY_SHA = (
    "2d4afc02fd0bd8213e195d5a00a6cbf1151fa3d5e6a83578520a99ba96c69b3e"
)

# Frozen source-authentic Stage-4 transport implementation.
C17 = (
    R
    / "PAD_Stream_V16C17_Production_Source_Authentic_Y_Transport_Tensor_"
      "Generation_and_Certification.py"
)
C17_SHA = (
    "1d357be446103cb554c4759948347d2876235b7c630c64cd826801cbfc61dd4f"
)

# Frozen physical parameter authorities.
C14 = (
    R
    / "output"
    / "V16_C14_PRODUCTION_FULL_PHYSICS_TRANSPORT_PARAMETER_AUTHORITY_CONTRACT"
    / "V16C14_Production_Full_Physics_Parameter_Contract.json"
)

C15 = (
    R
    / "output"
    / "V16_C15_PRODUCTION_PHYSICAL_TARGET_TIME_SCHEDULE_AUTHORITY_CONTRACT"
    / "V16C15_Production_Target_Time_Schedule_Contract.json"
)

# D28-R1 conservative face-metric expansion.
D28 = (
    R
    / "output"
    / "V16_D28_R1_36CASE_D9R1_CONSERVATIVE_FACE_METRIC_EXPANSION"
    / "cases"
)


# =============================================================================
# FROZEN NUMERICS / EXPERIMENT
# =============================================================================

SECONDS_PER_DAY = 86400.0
CFL = 0.25
EPS = 1.0e-12

TARGET_DAYS_EXPECTED = [
    30.0,
    60.0,
    100.0,
    150.0,
    250.0,
    365.0,
    500.0,
    750.0,
    1000.0,
]

# D31C: geology0029 only, 3 rates x 3 producer BHP values.
LOCKED_OOD = [
    ("0029", rate_tpd, producer_bhp_psi)
    for rate_tpd in (350, 500, 650)
    for producer_bhp_psi in (1800, 2000, 2200)
]

EXPECTED_CASES = 9
EXPECTED_STREAMLINES = 1078
EXPECTED_NODES = 201
EXPECTED_MFACE_SHAPE = (1078, 200)
EXPECTED_MNODE_SHAPE = (1078, 201)
EXPECTED_Y_SHAPE = (9, 1078, 201)


# =============================================================================
# HELPERS
# =============================================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text())


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("v16d31c_r1_c17", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def json_default(obj):
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(type(obj).__name__)


def case_id(g: str, r: int, b: int) -> str:
    return f"V16D_Foundation_Case_{g}_R{r}_B{b}"


def metric_path(g: str, r: int, b: int) -> Path:
    """
    Resolve the unique D28-R1 metric artifact corresponding to the exact
    geology/rate/BHP identity.
    """
    hits = [
        p
        for p in D28.glob("*.npz")
        if g in p.name
        and re.search(fr"(?<!\d){r}(?!\d)", p.name)
        and re.search(fr"(?<!\d){b}(?!\d)", p.name)
    ]

    if len(hits) != 1:
        raise RuntimeError(
            f"D28-R1 metric identity {g}/{r}/{b}: expected 1 file, found {len(hits)}"
        )

    return hits[0]


def case_paths(g: str, r: int, b: int):
    stem = f"{case_id(g, r, b)}_Stage4_Transport"
    return (
        C / f"{stem}.npz",
        C / f"{stem}_Summary.json",
    )


def certified(artifact: Path, summary: Path, g: str, r: int, b: int) -> bool:
    """
    Case-local restart rule.

    A case may be skipped ONLY when:
      1. artifact exists,
      2. summary exists,
      3. summary says CERTIFIED,
      4. recorded artifact SHA matches the actual artifact,
      5. case identity is exact,
      6. partition is LOCKED_OOD_TEST.
    """
    if not artifact.exists() or not summary.exists():
        return False

    try:
        record = read_json(summary)

        return bool(
            record.get("status") == "CERTIFIED"
            and record.get("artifact_sha256") == sha256(artifact)
            and record.get("case_id") == case_id(g, r, b)
            and record.get("partition") == "LOCKED_OOD_TEST"
        )
    except Exception:
        return False


def validate_authorities():
    """
    Strict pre-generation provenance gates.
    """
    gates = {
        "D31C_contract_exists": D31C_CONTRACT.exists(),
        "D31C_summary_exists": D31C_SUMMARY.exists(),
        "C17_exists": C17.exists(),
        "C14_exists": C14.exists(),
        "C15_exists": C15.exists(),
        "D28_exists": D28.exists(),
    }

    if D31C_CONTRACT.exists():
        gates["D31C_contract_SHA_exact"] = (
            sha256(D31C_CONTRACT) == D31C_CONTRACT_SHA
        )
    else:
        gates["D31C_contract_SHA_exact"] = False

    if D31C_SUMMARY.exists():
        gates["D31C_summary_SHA_exact"] = (
            sha256(D31C_SUMMARY) == D31C_SUMMARY_SHA
        )
    else:
        gates["D31C_summary_SHA_exact"] = False

    if C17.exists():
        gates["C17_SHA_exact"] = sha256(C17) == C17_SHA
    else:
        gates["C17_SHA_exact"] = False

    gates["D28_exactly_36_metrics"] = (
        D28.exists() and len(list(D28.glob("*.npz"))) == 36
    )

    if D31C_CONTRACT.exists():
        contract_record = read_json(D31C_CONTRACT)
        contract = contract_record.get("contract", {})
        gates.update(
            {
                "contract_status_authorized": (
                    contract_record.get("status")
                    == "V16D_LOCKED_OOD_9CASE_STAGE4_TRANSPORT_GENERATION_"
                       "CONTRACT_FROZEN_RESTARTABLE_SEALED_OOD_PHYSICS_"
                       "GENERATION_AUTHORIZED"
                ),
                "partition_LOCKED_OOD_TEST": (
                    contract.get("partition") == "LOCKED_OOD_TEST"
                ),
                "geology0029_only": contract.get("geology") == "0029",
                "case_count_9": contract.get("cases") == 9,
                "rates_exact": contract.get("rates_tpd") == [350, 500, 650],
                "producer_bhp_exact": (
                    contract.get("producer_bhp_psi") == [1800, 2000, 2200]
                ),
                "target_days_exact": (
                    [float(x) for x in contract.get("target_days", [])]
                    == TARGET_DAYS_EXPECTED
                ),
                "Y_shape_exact": (
                    contract.get("Y_shape_each") == [9, 1078, 201]
                ),
                "restartable_contract": (
                    contract.get("restartability")
                    == "case-local SHA certification"
                ),
                "future_opening_separately_frozen": (
                    contract.get("future_opening")
                    == "requires separately frozen one-touch final OOD "
                       "evaluation contract"
                ),
            }
        )
    else:
        gates.update(
            {
                "contract_status_authorized": False,
                "partition_LOCKED_OOD_TEST": False,
                "geology0029_only": False,
                "case_count_9": False,
                "rates_exact": False,
                "producer_bhp_exact": False,
                "target_days_exact": False,
                "Y_shape_exact": False,
                "restartable_contract": False,
                "future_opening_separately_frozen": False,
            }
        )

    return gates


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 78)
    print("PAD-Stream V16D-31C-R1")
    print("Restartable Sealed LOCKED-OOD 9-Case Stage-4 Transport Generator")
    print("=" * 78)

    # -------------------------------------------------------------------------
    # 1. Frozen-authority / provenance gates
    # -------------------------------------------------------------------------

    provenance_gates = validate_authorities()

    print("\nPROVENANCE / CONTRACT GATES")
    for name, passed in provenance_gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    if not all(provenance_gates.values()):
        raise RuntimeError(
            "D31C-R1 blocked: frozen authority / contract provenance gate failed."
        )

    # Import exact frozen C17 only after SHA certification.
    c17 = load_module(C17)

    # -------------------------------------------------------------------------
    # 2. Frozen transport parameters
    # -------------------------------------------------------------------------

    parameter_contract = read_json(C14)
    time_contract = read_json(C15)

    production_parameters = parameter_contract["production_parameters"]

    def value(key):
        return float(production_parameters[key]["value"])

    par = {
        key: value(source_key)
        for key, source_key in [
            ("nw", "nw"),
            ("no", "no"),
            ("swc", "Swc"),
            ("sor", "Sor"),
            ("krw_max", "krw_max"),
            ("kro_max", "kro_max"),
            ("mu_w", "mu_w"),
            ("mu_o", "mu_o"),
            ("phi", "phi"),
        ]
    }

    par["sw_init"] = par["swc"] + 1.0e-3
    par["sw_inj"] = 1.0 - par["sor"] - 1.0e-3

    Pe_c = value("Pe_c")
    lambda_c = value("lambda_c")
    Nc = value("Nc")  # metadata only, per frozen C17 lineage

    target_days = np.asarray(time_contract["target_days"], dtype=float)

    if target_days.tolist() != TARGET_DAYS_EXPECTED:
        raise RuntimeError(
            f"C15 target days mismatch: {target_days.tolist()}"
        )

    # -------------------------------------------------------------------------
    # 3. Generate / restart exact 9-case locked-OOD partition
    # -------------------------------------------------------------------------

    for icase, (g, r, b) in enumerate(LOCKED_OOD, 1):
        artifact_path, summary_path = case_paths(g, r, b)

        # Case-local SHA-certified restartability.
        if certified(artifact_path, summary_path, g, r, b):
            print(
                f"[SKIP {icase:02d}/09] "
                f"Case{g} R{r} B{b} already SHA-certified"
            )
            continue

        metric = metric_path(g, r, b)

        with np.load(metric, allow_pickle=False) as z:
            theta = np.asarray(z["theta"], dtype=float)
            terminal_tof_s = np.asarray(z["pollock_tau_end_s"], dtype=float)
            M_face = np.asarray(z["M_face_dtheta_dxD"], dtype=float)
            M_node = np.asarray(z["M_node_sidecar_dtheta_dxD"], dtype=float)

        # D28-R1 canonical schema:
        # theta=(201,), M_face=(1078,200), node metric=(1078,201)
        # theta may ONLY be adapted by broadcast over streamlines.
        if theta.ndim == 1:
            if theta.shape != (EXPECTED_NODES,):
                raise RuntimeError(
                    f"theta schema mismatch for {g}/{r}/{b}: {theta.shape}"
                )

            ns = M_face.shape[0]
            n = theta.size
            theta = np.broadcast_to(
                theta[None, :], (ns, n)
            ).copy()
        else:
            ns, n = theta.shape

        if (ns, n) != (EXPECTED_STREAMLINES, EXPECTED_NODES):
            raise RuntimeError(
                f"theta geometry mismatch for {g}/{r}/{b}: {(ns, n)}"
            )

        if M_face.shape != EXPECTED_MFACE_SHAPE:
            raise RuntimeError(
                f"M_face shape mismatch for {g}/{r}/{b}: {M_face.shape}"
            )

        if M_node.shape != EXPECTED_MNODE_SHAPE:
            raise RuntimeError(
                f"M_node shape mismatch for {g}/{r}/{b}: {M_node.shape}"
            )

        if terminal_tof_s.shape != (EXPECTED_STREAMLINES,):
            raise RuntimeError(
                f"terminal Pollock TOF shape mismatch for {g}/{r}/{b}: "
                f"{terminal_tof_s.shape}"
            )

        if not np.isfinite(terminal_tof_s).all() or np.any(terminal_tof_s <= 0.0):
            raise RuntimeError(
                f"nonpositive/nonfinite Pollock terminal TOF for {g}/{r}/{b}"
            )

        # ---------------------------------------------------------------------
        # 4. Exact C17 transport coordinate construction
        # ---------------------------------------------------------------------

        dtheta = np.diff(theta, axis=1)

        M_face_extended = np.empty((ns, n + 1), dtype=float)
        M_face_extended[:, 1:-1] = M_face
        M_face_extended[:, 0] = M_face[:, 0]
        M_face_extended[:, -1] = M_face[:, -1]

        theta_face = np.empty((ns, n + 1), dtype=float)
        theta_face[:, 1:-1] = 0.5 * (
            theta[:, :-1] + theta[:, 1:]
        )
        theta_face[:, 0] = theta[:, 0]
        theta_face[:, -1] = theta[:, -1]

        control_volume = np.diff(theta_face, axis=1)

        if not np.isfinite(control_volume).all():
            raise RuntimeError(
                f"nonfinite transport control volume for {g}/{r}/{b}"
            )

        if np.any(control_volume[:, 1:] <= 0.0):
            raise RuntimeError(
                f"nonpositive interior transport control volume for {g}/{r}/{b}"
            )

        # Physical time -> dimensionless streamline transport coordinate.
        target_eta = (
            target_days[:, None]
            * SECONDS_PER_DAY
            / terminal_tof_s[None, :]
        )

        dt_cfl = float(
            CFL
            * np.min(control_volume[:, 1:])
            / (c17.max_dfw(par) + EPS)
        )

        if not np.isfinite(dt_cfl) or dt_cfl <= 0.0:
            raise RuntimeError(
                f"invalid C17 CFL step for {g}/{r}/{b}: {dt_cfl}"
            )

        # ---------------------------------------------------------------------
        # 5. Initial state
        # ---------------------------------------------------------------------

        S = np.full(
            (ns, n),
            par["sw_init"],
            dtype=float,
        )
        S[:, 0] = par["sw_inj"]

        eta = np.zeros(ns, dtype=float)
        next_target = np.zeros(ns, dtype=int)

        Y = np.full(
            EXPECTED_Y_SHAPE,
            np.nan,
            dtype=float,
        )

        adv_max = 0.0
        cap_max = 0.0
        preclip_max = 0.0
        steps = 0

        eta_max = float(np.max(target_eta))
        step_ceiling = int(np.ceil(eta_max / dt_cfl)) + 109

        print(
            f"\n[RUN {icase:02d}/09] "
            f"Case{g} R{r} B{b} "
            f"dt={dt_cfl:.6e} ceiling={step_ceiling}"
        )

        start = time.time()

        # ---------------------------------------------------------------------
        # 6. Source-authentic transport solve
        # ---------------------------------------------------------------------

        while np.any(next_target < 9):
            active = next_target < 9

            goal = np.zeros(ns, dtype=float)
            active_indices = np.where(active)[0]
            goal[active_indices] = target_eta[
                next_target[active_indices],
                active_indices,
            ]

            dt = np.zeros(ns, dtype=float)
            dt[active] = np.minimum(
                dt_cfl,
                np.maximum(0.0, goal[active] - eta[active]),
            )

            hit = active & (np.abs(goal - eta) <= 5.0e-14)

            if np.any(hit):
                hit_indices = np.where(hit)[0]

                Y[
                    next_target[hit_indices],
                    hit_indices,
                    :,
                ] = S[hit_indices, :]

                next_target[hit_indices] += 1
                continue

            # Exact frozen C17 advection.
            S, _, adv_error = c17.adv(
                S,
                dt,
                control_volume,
                par,
            )

            adv_max = max(adv_max, float(adv_error))

            preclip_max = max(
                preclip_max,
                float(
                    max(
                        0.0,
                        par["swc"] - float(S.min()),
                        float(S.max()) - (1.0 - par["sor"]),
                    )
                ),
            )

            np.clip(
                S,
                par["swc"],
                1.0 - par["sor"],
                out=S,
            )
            S[:, 0] = par["sw_inj"]

            # Exact frozen C17 capillary / implicit update.
            S, cap_residual = c17.cap(
                S,
                dt,
                par["phi"],
                Pe_c,
                lambda_c,
                M_node,
                M_face_extended,
                control_volume,
                dtheta,
                par,
            )

            cap_max = max(cap_max, float(cap_residual))

            preclip_max = max(
                preclip_max,
                float(
                    max(
                        0.0,
                        par["swc"] - float(S.min()),
                        float(S.max()) - (1.0 - par["sor"]),
                    )
                ),
            )

            np.clip(
                S,
                par["swc"],
                1.0 - par["sor"],
                out=S,
            )
            S[:, 0] = par["sw_inj"]

            eta += dt
            steps += 1

            # Progress information contains no OOD target statistics.
            if steps % 2000 == 0:
                print(
                    f"  step {steps}/{step_ceiling} "
                    f"targets {int(np.sum(next_target))}/{ns * 9}"
                )

            if steps > step_ceiling:
                raise RuntimeError(
                    f"CFL step ceiling exceeded for {g}/{r}/{b}"
                )

        if np.any(next_target < 9):
            raise RuntimeError(
                f"target capture incomplete for {g}/{r}/{b}"
            )

        elapsed = time.time() - start

        # ---------------------------------------------------------------------
        # 7. Scientific certification
        # ---------------------------------------------------------------------
        #
        # IMPORTANT:
        # These diagnostics are used ONLY to enforce the already-frozen
        # generation acceptance gates. They are written case-locally for
        # provenance/certification. No aggregate OOD target statistics are
        # produced or used for development/model decisions.
        # ---------------------------------------------------------------------

        S_min = float(Y.min())
        S_max = float(Y.max())

        temporal_negative_fraction = float(
            np.mean(np.diff(Y, axis=0) < -1.0e-8)
        )

        spatial_positive_fraction = float(
            np.mean(np.diff(Y, axis=2) > 1.0e-8)
        )

        scientific_gates = {
            "finite": bool(np.isfinite(Y).all()),
            "shape": Y.shape == EXPECTED_Y_SHAPE,
            "bounds": (
                max(
                    0.0,
                    par["swc"] - S_min,
                    S_max - (1.0 - par["sor"]),
                )
                < 1.0e-8
            ),
            "injector": (
                float(
                    np.max(
                        np.abs(
                            Y[:, :, 0] - par["sw_inj"]
                        )
                    )
                )
                < 1.0e-12
            ),
            "undershoot": (
                max(
                    0.0,
                    par["sw_init"] - float(np.min(Y[:, :, 1:])),
                )
                < 1.0e-8
            ),
            "adv_conservation": adv_max < 1.0e-11,
            "cap_residual": cap_max < 1.0e-10,
            "preclip": preclip_max < 1.0e-8,
            "temporal": temporal_negative_fraction < 0.01,
            "spatial": spatial_positive_fraction < 0.05,
        }

        case_ok = bool(all(scientific_gates.values()))

        # ---------------------------------------------------------------------
        # 8. Write exact case artifact + SHA sidecar
        # ---------------------------------------------------------------------
        #
        # Artifact is written only after all frozen scientific gates have been
        # evaluated. No training/model code is imported or executed here.
        # ---------------------------------------------------------------------

        np.savez_compressed(
            artifact_path,
            Y_transport=Y,
            target_days=target_days,
            theta=theta[0],
            terminal_pollock_tof_s=terminal_tof_s,
            target_eta=target_eta,
            M_face_dtheta_dxD=M_face,
            Pe_c=np.array(Pe_c),
            lambda_c=np.array(lambda_c),
            Nc_metadata_only=np.array(Nc),
            case_id=np.array(case_id(g, r, b)),
            partition=np.array("LOCKED_OOD_TEST"),
        )

        record = {
            "case_id": case_id(g, r, b),
            "partition": "LOCKED_OOD_TEST",
            "status": "CERTIFIED" if case_ok else "BLOCKED",
            "metric_sha256": sha256(metric),
            "artifact_sha256": sha256(artifact_path),
            "steps": steps,
            "elapsed_seconds": elapsed,

            # Case-local frozen gate diagnostics only.
            # Never aggregated into OOD development statistics.
            "S_min": S_min,
            "S_max": S_max,
            "adv_max": adv_max,
            "cap_max": cap_max,
            "preclip_max": preclip_max,
            "temporal_negative_fraction": temporal_negative_fraction,
            "spatial_positive_fraction": spatial_positive_fraction,

            "gates": scientific_gates,

            "ood_firewall": {
                "no_training": True,
                "no_tuning": True,
                "no_OOD_normalization": True,
                "no_selection": True,
                "no_threshold_relaxation": True,
                "no_deduplication": True,
                "no_aggregate_OOD_target_statistics": True,
            },
        }

        summary_path.write_text(
            json.dumps(
                record,
                indent=2,
                default=json_default,
            )
        )

        print(
            "  ->",
            record["status"],
            "artifact",
            record["artifact_sha256"],
        )

        if not case_ok:
            raise SystemExit(2)

    # -------------------------------------------------------------------------
    # 9. Final exact 9/9 certification
    # -------------------------------------------------------------------------

    final_cases = []

    for g, r, b in LOCKED_OOD:
        artifact_path, summary_path = case_paths(g, r, b)

        if not certified(
            artifact_path,
            summary_path,
            g,
            r,
            b,
        ):
            raise RuntimeError(
                f"uncertified final locked-OOD case {g}/{r}/{b}"
            )

        final_cases.append(read_json(summary_path))

    if len(final_cases) != EXPECTED_CASES:
        raise RuntimeError(
            f"expected 9 certified locked-OOD cases, found {len(final_cases)}"
        )

    # -------------------------------------------------------------------------
    # 10. Seal generation manifest
    # -------------------------------------------------------------------------
    #
    # The manifest identifies and hashes generated artifacts but is NOT an
    # authorization to inspect/compare OOD target performance.
    # -------------------------------------------------------------------------

    manifest_path = O / "V16D31C_R1_LOCKED_OOD_9Case_Manifest.json"

    manifest = {
        "milestone": "V16D-31C-R1",
        "status": "CERTIFIED_SEALED",
        "partition": "LOCKED_OOD_TEST",
        "geology": "0029",
        "count": 9,
        "rates_tpd": [350, 500, 650],
        "producer_bhp_psi": [1800, 2000, 2200],
        "target_days": TARGET_DAYS_EXPECTED,
        "Y_shape_each": [9, 1078, 201],
        "cases": final_cases,
        "generation_contract_sha256": D31C_CONTRACT_SHA,
        "generation_contract_summary_sha256": D31C_SUMMARY_SHA,
        "C17_sha256": C17_SHA,
        "sealed": True,
        "OOD_targets_not_opened_for_model_evaluation": True,
        "no_training": True,
        "no_tuning": True,
        "no_OOD_normalization": True,
        "no_selection": True,
        "no_threshold_changes": True,
        "no_deduplication": True,
        "no_aggregate_OOD_target_statistics": True,
        "future_opening_requires": (
            "separately frozen one-touch final OOD evaluation contract"
        ),
    }

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            default=json_default,
        )
    )

    # -------------------------------------------------------------------------
    # 11. Final milestone summary
    # -------------------------------------------------------------------------

    summary_path = O / "PAD_Stream_V16D31C_R1_Summary.json"

    summary = {
        "milestone": "V16D-31C-R1",
        "status": (
            "V16D_LOCKED_OOD_9CASE_STAGE4_TRANSPORT_GENERATED_"
            "CERTIFIED_RESTARTABLE_SEALED_FINAL_OOD_EVALUATION_"
            "CONTRACT_AUTHORIZED"
        ),
        "certified_cases": 9,
        "partition": "LOCKED_OOD_TEST",
        "geology": "0029",
        "manifest_sha256": sha256(manifest_path),
        "D31C_contract_sha256": D31C_CONTRACT_SHA,
        "D31C_summary_sha256": D31C_SUMMARY_SHA,
        "TRAIN_unchanged": True,
        "VALIDATION_unchanged": True,
        "OOD_generation_sealed": True,
        "OOD_targets_not_used_for_training": True,
        "OOD_targets_not_used_for_tuning": True,
        "OOD_targets_not_used_for_normalization": True,
        "OOD_targets_not_used_for_selection": True,
        "next_milestone": (
            "V16D-31D — Frozen one-touch final locked-OOD evaluation contract"
        ),
    }

    summary_path.write_text(
        json.dumps(
            summary,
            indent=2,
            default=json_default,
        )
    )

    print("\n" + "=" * 78)
    print("V16D-31C-R1 COMPLETE — 9/9 LOCKED-OOD CASES CERTIFIED AND SEALED")
    print("=" * 78)
    print("Manifest SHA-256:", sha256(manifest_path))
    print("Summary SHA-256 :", sha256(summary_path))
    print("\nLOCKED-OOD STATUS")
    print("  SEALED — generation complete; no model evaluation authorized yet.")
    print("\nNEXT")
    print("  V16D-31D — Frozen one-touch final locked-OOD evaluation contract")


if __name__ == "__main__":
    main()

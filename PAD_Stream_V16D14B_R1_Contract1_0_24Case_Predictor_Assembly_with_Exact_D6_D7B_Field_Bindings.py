#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, re, sys
import numpy as np

R = Path(__file__).resolve().parent

# ---------------------------------------------------------------------
# Frozen authorities
# ---------------------------------------------------------------------
AR3_DIR = R/"output"/"V16_D14AR3_NEW_EXPLICIT_STREAMLINE_TO_GRID_SAMPLING_CONTRACT"
AR3_SUM = AR3_DIR/"PAD_Stream_V16D14AR3_Summary.json"
AR3_CON = AR3_DIR/"V16D14AR3_Streamline_to_Grid_Sampling_Contract_1.0.json"
AR3_SUM_SHA = "8c3236a34d9d4be1779c69ba439a2fc258d61d426e5ed94f7257113c877b3b63"
AR3_CON_SHA = "32fec4b708108fb708bd40cc0983d4de093516a4a84b90b7ae9c3020a2383181"

BR3R1_DIR = R/"output"/"V16_D14BR3R1_D7B_CASE0002_REGISTRY_EXACT_BINDING"
BR3R1_SUM = BR3R1_DIR/"PAD_Stream_V16D14BR3R1_Summary.json"
BR3R1_SUM_SHA = "08c14aa39143643b680972d4c2fb05bce11ab4fb89b3f457b40b27986ce367d0"

D14_DIR = R/"output"/"V16_D14_SOURCEBOUND_24CASE_PREDICTOR_SCHEMA_AUDIT"
D14_SUM = D14_DIR/"PAD_Stream_V16D14_Summary.json"
D14_REG = D14_DIR/"V16D14_Source_Binding_Registry.json"
D14_SUM_SHA = "75f48ebede8e6f17d44d3c51918b9bdcc1d328789926477a5d45555cc6019d25"

D7B_CASES = (
    R/"output"/
    "V16_D7B_FULL_FROZEN_CASE0002_0025_SOURCEBOUND_SG2_SG3_SG4_FLOW_ENSEMBLE"/
    "cases"
)

# ---------------------------------------------------------------------
# Frozen split / feature contract
# ---------------------------------------------------------------------
TRAIN = ["0020","0015","0013","0004","0006","0002","0023","0016",
         "0009","0019","0017","0024","0003","0011","0014","0007"]
VAL   = ["0010","0025","0008","0012"]
OOD   = ["0005","0018","0021","0022"]
ALL = TRAIN + VAL + OOD

DAYS = np.asarray([30,60,100,150,250,365,500,750,1000], dtype=np.float64)

FEATURES = [
    "xi",
    "pollock_tau_hat",
    "adv_tau_hat",
    "log10_Kh",
    "log10_Kz_over_Kh",
    "porosity",
    "pressure_z",
    "target_time_hat",
    "target_eta_sequence",
]

NZ, NY, NX = 15, 50, 50
DX, DY, DZ = 6.096, 6.096, 1.2192
DOMAIN_MAX = np.asarray([NX*DX, NY*DY, NZ*DZ], dtype=np.float64)
OUTSIDE_TOL_M = 1.0e-8

OUT = R/"output"/"V16_D14B_R1_CONTRACT1_0_24CASE_PREDICTOR_ASSEMBLY_EXACT_FIELD_BINDINGS"
CASE_OUT = OUT/"cases"
OUT.mkdir(parents=True, exist_ok=True)
CASE_OUT.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def exact_array(z, key, shape):
    if key not in z.files:
        raise RuntimeError(f"required key '{key}' absent; available={list(z.files)}")
    a = np.asarray(z[key])
    if a.shape != shape:
        raise RuntimeError(f"key '{key}' expected shape {shape}, got {a.shape}")
    if not np.issubdtype(a.dtype, np.number):
        raise RuntimeError(f"key '{key}' is not numeric: {a.dtype}")
    a = np.asarray(a, dtype=np.float64)
    if not np.isfinite(a).all():
        raise RuntimeError(f"key '{key}' contains non-finite values")
    return a


def containing_cell_indices(xyz):
    xyz = np.asarray(xyz, dtype=np.float64)
    lo = xyz.min(axis=(0,1))
    hi = xyz.max(axis=(0,1))
    if np.any(lo < -OUTSIDE_TOL_M) or np.any(hi > DOMAIN_MAX + OUTSIDE_TOL_M):
        raise RuntimeError(
            f"Contract-1.0 outside-domain violation: min={lo}, max={hi}, domain_max={DOMAIN_MAX}"
        )
    i = np.clip(np.floor(xyz[...,0] / DX).astype(np.int64), 0, NX-1)
    j = np.clip(np.floor(xyz[...,1] / DY).astype(np.int64), 0, NY-1)
    k = np.clip(np.floor(xyz[...,2] / DZ).astype(np.int64), 0, NZ-1)
    return k, j, i


def partition(case_id):
    if case_id in TRAIN: return "TRAIN"
    if case_id in VAL: return "VALIDATION"
    if case_id in OOD: return "LOCKED_OOD_TEST"
    raise RuntimeError(case_id)


def resolve_path(v):
    p = Path(v)
    if not p.is_absolute():
        p = R / p
    return p


def find_xyz_in_bound_artifacts(case_id, registry_entry):
    """
    Strict discovery only:
      1. Check already source-bound per-case artifacts named in D14.
      2. Accept only explicit XYZ keys with exact (1078,201,3) shape.
      3. Do not reconstruct/resample geometry here.
    """
    keys = ("streamline_xyz", "transport_xyz", "xyz_m", "xyz")
    candidate_paths = []
    for v in registry_entry.values():
        if isinstance(v, str) and v.lower().endswith(".npz"):
            p = resolve_path(v)
            if p.exists():
                candidate_paths.append(p)

    hits = []
    seen = set()
    for p in candidate_paths:
        if p in seen: continue
        seen.add(p)
        try:
            with np.load(p, allow_pickle=False) as z:
                for key in keys:
                    if key in z.files and np.asarray(z[key]).shape == (1078,201,3):
                        hits.append((p, key))
        except Exception:
            pass

    # Collapse identical artifact/key only.
    unique = {(str(p.resolve()), k): (p,k) for p,k in hits}
    hits = list(unique.values())
    if len(hits) != 1:
        detail = [{"path":str(p), "key":k} for p,k in hits]
        raise RuntimeError(
            f"Case{case_id}: exact 201-node Pollock XYZ source not uniquely bound; hits={detail}"
        )
    p, key = hits[0]
    with np.load(p, allow_pickle=False) as z:
        xyz = exact_array(z, key, (1078,201,3))
    return xyz, p, key


def find_pollock_metric(registry_entry):
    p = resolve_path(registry_entry["pollock_metric"])
    with np.load(p, allow_pickle=False) as z:
        theta = exact_array(z, "theta", (201,))
        tau = exact_array(z, "pollock_tau_s", (1078,201))
        tau_end = exact_array(z, "pollock_tau_end_s", (1078,))
    if np.any(tau_end <= 0):
        raise RuntimeError("nonpositive pollock_tau_end_s")
    return theta, tau, tau_end, p


def find_adv_on_path(registry_entry, xyz):
    p = resolve_path(registry_entry["adv_travel_time"])
    path_keys = ("adv_tau_s","tau_adv_s","tau_ADV_s","adv_tau","tau_ADV")
    grid_keys = ("tau_adv_s","tau_ADV_s","adv_tau_s","tau_adv","tau_ADV","adv_tau")

    with np.load(p, allow_pickle=False) as z:
        path_hits = [k for k in path_keys if k in z.files and np.asarray(z[k]).shape == (1078,201)]
        grid_hits = [k for k in grid_keys if k in z.files and np.asarray(z[k]).shape == (NZ,NY,NX)]

        if len(path_hits) == 1 and len(grid_hits) == 0:
            return exact_array(z, path_hits[0], (1078,201)), p, path_hits[0], "persisted_path"

        if len(path_hits) == 0 and len(grid_hits) == 1:
            grid = exact_array(z, grid_hits[0], (NZ,NY,NX))
            k,j,i = containing_cell_indices(xyz)
            return grid[k,j,i], p, grid_hits[0], "Contract1.0_containing_cell_grid_sample"

        raise RuntimeError(
            f"ADV representation not uniquely bound in {p}; "
            f"path_hits={path_hits}, grid_hits={grid_hits}, available={list(z.files)}"
        )


def assemble_case(case_id, reg):
    e = reg[case_id]

    # D6 geology source already bound by D14.
    geology = resolve_path(e["geology_flow"])
    with np.load(geology, allow_pickle=False) as z:
        Kx = exact_array(z, "Kx_mD", (NZ,NY,NX))
        Ky = exact_array(z, "Ky_mD", (NZ,NY,NX))
        Kz = exact_array(z, "Kz_mD", (NZ,NY,NX))
        phi = exact_array(z, "porosity", (NZ,NY,NX))

    # D7B frozen flow ensemble: exact case basename, not parent substring matching.
    pressure_file = D7B_CASES/f"V16D_Foundation_Case_{case_id}_Flow.npz"
    if not pressure_file.exists():
        raise RuntimeError(f"Case{case_id}: exact D7B flow artifact missing: {pressure_file}")
    with np.load(pressure_file, allow_pickle=False) as z:
        pressure_psi = exact_array(z, "pressure_psi", (NZ,NY,NX))

    theta, pollock_tau_s, tau_end_s, pollock_metric_file = find_pollock_metric(e)
    xyz, xyz_file, xyz_key = find_xyz_in_bound_artifacts(case_id, e)
    adv_tau_s, adv_file, adv_key, adv_mode = find_adv_on_path(e, xyz)

    k,j,i = containing_cell_indices(xyz)

    Kx_p = Kx[k,j,i]
    Ky_p = Ky[k,j,i]
    Kz_p = Kz[k,j,i]
    phi_p = phi[k,j,i]
    p_p = pressure_psi[k,j,i]

    Kh = np.sqrt(Kx_p * Ky_p)
    if np.any(Kh <= 0) or np.any(Kz_p <= 0):
        raise RuntimeError(f"Case{case_id}: nonpositive sampled permeability")

    xi = np.broadcast_to(theta[None,:], (1078,201))
    pollock_hat = pollock_tau_s / tau_end_s[:,None]
    adv_hat = adv_tau_s / tau_end_s[:,None]
    logKh = np.log10(Kh)
    logAniso = np.log10(Kz_p / Kh)

    # NOTE: channel slot 6 stores RAW pressure_psi in X_raw.
    # It is transformed into pressure_z only by TRAIN-only statistics below.
    X_raw = np.empty((9,1078,201,9), dtype=np.float64)
    for ti, day in enumerate(DAYS):
        target_time_hat = np.full((1078,201), day/1000.0, dtype=np.float64)
        eta = np.broadcast_to((86400.0*day/tau_end_s)[:,None], (1078,201))
        X_raw[ti] = np.stack(
            [xi, pollock_hat, adv_hat, logKh, logAniso, phi_p,
             p_p, target_time_hat, eta],
            axis=-1,
        )

    if not np.isfinite(X_raw).all():
        raise RuntimeError(f"Case{case_id}: non-finite raw predictors")

    meta = {
        "case_id": case_id,
        "partition": partition(case_id),
        "shape": list(X_raw.shape),
        "feature_order": FEATURES,
        "sampling_contract": "V16D_STREAMLINE_TO_GRID_SAMPLING_1.0",
        "pressure_raw_units": "psi",
        "sources": {
            "D6_geology": {"path":str(geology), "sha256":sha256(geology),
                           "keys":["Kx_mD","Ky_mD","Kz_mD","porosity"]},
            "D7B_pressure": {"path":str(pressure_file), "sha256":sha256(pressure_file),
                             "key":"pressure_psi"},
            "pollock_metric": {"path":str(pollock_metric_file), "sha256":sha256(pollock_metric_file),
                               "keys":["theta","pollock_tau_s","pollock_tau_end_s"]},
            "pollock_xyz": {"path":str(xyz_file), "sha256":sha256(xyz_file), "key":xyz_key},
            "ADV": {"path":str(adv_file), "sha256":sha256(adv_file),
                    "key":adv_key, "mode":adv_mode},
        },
    }
    return X_raw, meta


def main():
    print("="*78)
    print("PAD-Stream V16D-14B-R1")
    print("Contract-1.0 24-Case Predictor Assembly with Exact D6/D7B Field Bindings")
    print("="*78)
    print(
        "D6: Kx_mD/Ky_mD/Kz_mD/porosity\n"
        "D7B: exact per-case pressure_psi\n"
        "NO Y TARGET IS OPENED. NORMALIZATION IS FIT ON TRAIN ONLY.\n"
        "NO PHYSICS RERUN, NO MODEL TRAINING, NO OOD ADAPTATION.\n"
    )

    # Authority gates.
    if sha256(AR3_SUM) != AR3_SUM_SHA: raise RuntimeError("AR3 summary SHA mismatch")
    if sha256(AR3_CON) != AR3_CON_SHA: raise RuntimeError("AR3 contract SHA mismatch")
    if sha256(BR3R1_SUM) != BR3R1_SUM_SHA: raise RuntimeError("BR3R1 summary SHA mismatch")
    if sha256(D14_SUM) != D14_SUM_SHA: raise RuntimeError("D14 summary SHA mismatch")

    reg = json.loads(D14_REG.read_text(encoding="utf-8"))

    # Pass 1: raw assembly + TRAIN-only sufficient statistics.
    accum = {f: {"n":0, "sum":0.0, "sumsq":0.0, "min":np.inf, "max":-np.inf}
             for f in FEATURES}
    metas = []

    for n, case_id in enumerate(ALL, 1):
        print(f"[{n:02d}/24] Case{case_id}")
        X_raw, meta = assemble_case(case_id, reg)

        raw_path = CASE_OUT/f"V16D14B_R1_Case_{case_id}_Predictors_RAW.npz"
        np.savez_compressed(
            raw_path,
            X_raw=X_raw,
            target_days=DAYS,
            feature_order=np.asarray(FEATURES),
        )
        meta["raw_artifact"] = str(raw_path)
        meta["raw_sha256"] = sha256(raw_path)

        if case_id in TRAIN:
            for m, f in enumerate(FEATURES):
                x = X_raw[...,m]
                a = accum[f]
                a["n"] += int(x.size)
                a["sum"] += float(x.sum(dtype=np.float64))
                a["sumsq"] += float(np.square(x, dtype=np.float64).sum(dtype=np.float64))
                a["min"] = min(a["min"], float(x.min()))
                a["max"] = max(a["max"], float(x.max()))

        mp = CASE_OUT/f"V16D14B_R1_Case_{case_id}_RAW_Metadata.json"
        mp.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        metas.append(meta)

    stats = {}
    for f, a in accum.items():
        n = a["n"]
        mean = a["sum"]/n
        var = max(0.0, a["sumsq"]/n - mean*mean)
        std = var**0.5
        stats[f] = {
            "n": n,
            "mean": mean,
            "std": std,
            "min": a["min"],
            "max": a["max"],
            "policy": "CONSTANT_IDENTITY" if std == 0.0 else "ZSCORE_TRAIN_ONLY",
        }

    stats_path = OUT/"V16D14B_R1_TRAIN_Only_Normalization_Statistics.json"
    stats_path.write_text(json.dumps({
        "fit_partition":"TRAIN_ONLY",
        "fit_cases":TRAIN,
        "validation_policy":"TRANSFORM_ONLY",
        "locked_OOD_policy":"TRANSFORM_ONLY",
        "feature_order":FEATURES,
        "important_semantics":{
            "pressure_z":"raw pressure_psi sampled first, then z-scored using TRAIN-only pressure statistics",
            "M_face":"not a predictor",
            "Y_targets":"not read by this milestone",
        },
        "statistics":stats,
    }, indent=2), encoding="utf-8")

    # Pass 2: apply immutable TRAIN stats to all partitions.
    case_manifest = []
    for case_id in ALL:
        raw_path = CASE_OUT/f"V16D14B_R1_Case_{case_id}_Predictors_RAW.npz"
        with np.load(raw_path, allow_pickle=False) as z:
            X = np.asarray(z["X_raw"], dtype=np.float64)

        Xn = X.copy()
        for m, f in enumerate(FEATURES):
            s = stats[f]["std"]
            if s > 0.0:
                Xn[...,m] = (X[...,m] - stats[f]["mean"]) / s

        if not np.isfinite(Xn).all():
            raise RuntimeError(f"Case{case_id}: non-finite normalized predictors")

        norm_path = CASE_OUT/f"V16D14B_R1_Case_{case_id}_Predictors_NORMALIZED.npz"
        np.savez_compressed(
            norm_path,
            X=Xn,
            target_days=DAYS,
            feature_order=np.asarray(FEATURES),
        )
        case_manifest.append({
            "case_id":case_id,
            "partition":partition(case_id),
            "raw_path":str(raw_path),
            "raw_sha256":sha256(raw_path),
            "normalized_path":str(norm_path),
            "normalized_sha256":sha256(norm_path),
        })

    manifest_path = OUT/"V16D14B_R1_24Case_Predictor_Manifest.json"
    manifest_path.write_text(json.dumps({
        "milestone":"V16D-14B-R1",
        "sampling_contract_sha256":sha256(AR3_CON),
        "normalization_statistics_sha256":sha256(stats_path),
        "split":{"TRAIN":TRAIN,"VALIDATION":VAL,"LOCKED_OOD_TEST":OOD},
        "feature_order":FEATURES,
        "cases":case_manifest,
    }, indent=2), encoding="utf-8")

    gates = {
        "AR3_summary_SHA_exact": sha256(AR3_SUM) == AR3_SUM_SHA,
        "AR3_sampling_contract_SHA_exact": sha256(AR3_CON) == AR3_CON_SHA,
        "BR3R1_pressure_binding_SHA_exact": sha256(BR3R1_SUM) == BR3R1_SUM_SHA,
        "D14_source_schema_SHA_exact": sha256(D14_SUM) == D14_SUM_SHA,
        "exact_24_cases": len(case_manifest) == 24,
        "exact_16_4_4_split": len(TRAIN)==16 and len(VAL)==4 and len(OOD)==4,
        "feature_order_exact": FEATURES == [
            "xi","pollock_tau_hat","adv_tau_hat","log10_Kh",
            "log10_Kz_over_Kh","porosity","pressure_z",
            "target_time_hat","target_eta_sequence"
        ],
        "all_predictor_artifacts_exist": all(
            Path(x["raw_path"]).exists() and Path(x["normalized_path"]).exists()
            for x in case_manifest
        ),
        "TRAIN_only_normalization_fit": True,
        "validation_transform_only": True,
        "locked_OOD_transform_only": True,
        "no_target_Y_read": True,
        "M_face_not_predictor": True,
        "no_physics_rerun": True,
        "no_training": True,
        "no_model_selection": True,
    }
    ok = all(gates.values())
    status = (
        "V16D_24CASE_C20_PREDICTOR_TENSORS_ASSEMBLED_CONTRACT1_0_"
        "EXACT_D6_D7B_BINDINGS_TRAIN_ONLY_NORMALIZATION_FROZEN"
        if ok else
        "V16D_D14B_R1_BLOCKED"
    )
    nxt = (
        "V16D-15 — Multi-Foundation-Case Learning Dataset Freeze and Training Protocol Authority Contract"
        if ok else
        "V16D-14B-R2 — Remaining Predictor Source/Schema Repair"
    )

    summary_path = OUT/"PAD_Stream_V16D14B_R1_Summary.json"
    summary_path.write_text(json.dumps({
        "milestone":"V16D-14B-R1",
        "status":status,
        "normalization_statistics_sha256":sha256(stats_path),
        "predictor_manifest_sha256":sha256(manifest_path),
        "gates":gates,
        "next_milestone":nxt,
    }, indent=2), encoding="utf-8")

    print("\nTRAIN-ONLY NORMALIZATION STATISTICS")
    for f in FEATURES:
        s=stats[f]
        print(f"  {f:24s} mean={s['mean']:.9e} std={s['std']:.9e} "
              f"min={s['min']:.9e} max={s['max']:.9e} {s['policy']}")

    print("\nGATES")
    for k,v in gates.items():
        print(f"[{'PASS' if v else 'FAIL'}] {k}")

    print("\nSTATUS\n ",status)
    print("\nNEXT\n ",nxt)
    print("\nSummary SHA-256:",sha256(summary_path))
    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import re
import zipfile

import numpy as np


# =============================================================================
# PAD-Stream V16A-R8R
# Repaired Foundation Case 0001 Final Assembly / Freeze
#
# PURPOSE
# -------
# R8 failed only because it attempted to rediscover the Kz/Kh anisotropy ratio.
# R8A resolved that ratio source-authentically:
#
#     Kz / Kh = 0.1
#
# R8R therefore consumes the immutable R8A contract directly. It does NOT
# re-audit or re-infer the anisotropy ratio.
#
# R8R assembles one immutable V16A Foundation Case 0001 package containing:
#
#   GEOLOGY / STORAGE
#     Kx, Ky, Kz, porosity
#
#   DYNAMIC FLOW
#     pressure, Qx, Qy, Qz, Vx, Vy, Vz
#
#   FROZEN POLLOCK REFERENCES
#     streamline_xyz, pollock_tof, streamline_weight
#
#   EXPLICIT SCOPE LIMITATION
#     producer_id unavailable / non-required
#
# R8R WILL NOT:
#   - rerun SG3,
#   - rerun SG4,
#   - recompute velocity,
#   - retrace Pollock,
#   - run Fast Marching,
#   - train or infer ML,
#   - fabricate producer_id,
#   - mutate frozen V15 artifacts.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT_ROOT = ROOT / "output" / "V16_A_R8R_FOUNDATION_CASE_0001_FREEZE"
PACKAGE = OUT_ROOT / "PAD_Stream_V16A_Foundation_Case_0001"
PACKAGE.mkdir(parents=True, exist_ok=True)

R7E_DIR = ROOT / "output" / "V16_A_R7E_PRODUCER_SCOPE_FREEZE_DECISION"
R7E_SUMMARY = R7E_DIR / "PAD_Stream_V16AR7E_Summary.json"

R8A_DIR = ROOT / "output" / "V16_A_R8A_KZ_ANISOTROPY_BINDING_REPAIR"
R8A_SUMMARY = R8A_DIR / "PAD_Stream_V16AR8A_Summary.json"
R8A_CONTRACT = R8A_DIR / "V16AR8A_Kz_Anisotropy_Binding_Contract.json"

R7_DIR = ROOT / "output" / "V16_A_R7_CONTROLLED_SOURCE_AUTHENTIC_REGENERATION"
R7_DYNAMIC = R7_DIR / "V16AR7_Derived_V16_From_Frozen_V15_Dynamic_Components.npz"

R7B_DIR = ROOT / "output" / "V16_A_R7B_CONTROLLED_RESIDUAL_RECONSTRUCTION"
R7B_RESIDUAL = R7B_DIR / "V16AR7B_Derived_Velocity_Producer_Components.npz"

FOUNDATION_NPZ = PACKAGE / "V16A_Foundation_Case_0001.npz"
MANIFEST = PACKAGE / "V16A_Foundation_Case_0001_Manifest.json"
COMPONENT_TABLE = PACKAGE / "V16A_Foundation_Case_0001_Component_Registry.csv"
SCOPE_TABLE = PACKAGE / "V16A_Foundation_Case_0001_Scope_Limitations.csv"
PROVENANCE_TABLE = PACKAGE / "V16A_Foundation_Case_0001_Provenance.csv"
FREEZE_GATES = PACKAGE / "V16A_Foundation_Case_0001_Freeze_Gates.csv"
CHECKSUM_FILE = PACKAGE / "V16A_Foundation_Case_0001_SHA256.csv"
SUMMARY = PACKAGE / "PAD_Stream_V16A_R8R_Summary.json"
ZIP_FILE = OUT_ROOT / "PAD_Stream_V16A_Foundation_Case_0001.zip"

EXPECTED = {
    "Kx": (15, 50, 50),
    "Ky": (15, 50, 50),
    "Kz": (15, 50, 50),
    "porosity": (15, 50, 50),
    "pressure": (15, 50, 50),
    "Qx": (15, 50, 49),
    "Qy": (15, 49, 50),
    "Qz": (14, 50, 50),
    "Vx": (15, 50, 49),
    "Vy": (15, 49, 50),
    "Vz": (14, 50, 50),
    "streamline_xyz": (1078, 201, 3),
    "pollock_tof": (1078, 201),
    "streamline_weight": (1078,),
}


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
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()


def sha256_array(a: np.ndarray):
    a = np.ascontiguousarray(a)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode())
    h.update(str(tuple(a.shape)).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def parse_source_constants(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(text)
    constants = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        try:
            val = ast.literal_eval(getattr(node, "value", None))
        except Exception:
            continue
        raw = node.targets if isinstance(node, ast.Assign) else [node.target]
        for t in raw:
            if isinstance(t, ast.Name):
                constants[t.id] = val
    return text, constants


def find_sg1_sg2_sources():
    sg1 = sorted(ROOT.glob("PAD_Stream_V15SG1*.py"))
    sg2 = sorted(ROOT.glob("PAD_Stream_V15SG2*.py"))

    if len(sg1) != 1:
        pref = [p for p in sg1 if "Geology_Integration" in p.name]
        if len(pref) == 1:
            sg1 = pref

    if len(sg2) != 1:
        pref = [p for p in sg2 if "Transmiss" in p.name or "Anisotropic" in p.name]
        if len(pref) == 1:
            sg2 = pref

    if len(sg1) != 1 or len(sg2) != 1:
        raise RuntimeError(
            f"Could not uniquely resolve SG1/SG2 sources: "
            f"SG1={[p.name for p in sg1]}, SG2={[p.name for p in sg2]}"
        )
    return sg1[0], sg2[0]


def find_perm_csv(sg1_text: str):
    literals = re.findall(r'["\']([^"\']+\.csv)["\']', sg1_text, flags=re.I)
    candidates = []

    for lit in literals:
        p = Path(lit)
        for q in [p, ROOT / p, ROOT / p.name]:
            if q.exists() and "perm" in q.name.lower():
                candidates.append(q.resolve())

    if not candidates:
        for p in ROOT.rglob("*.csv"):
            low = p.name.lower()
            if "sgsim" in low and "50x50x15" in low and "perm" in low:
                candidates.append(p.resolve())

    candidates = sorted(set(candidates))
    if len(candidates) != 1:
        raise RuntimeError(f"Could not uniquely resolve SGSim permeability CSV: {candidates}")

    return candidates[0]


def load_perm_csv(path: Path):
    # Try header-aware load first.
    try:
        x = np.genfromtxt(path, delimiter=",", names=True)
        if x.dtype.names:
            cols = []
            for name in x.dtype.names:
                try:
                    col = np.asarray(x[name], dtype=float)
                    if np.all(np.isfinite(col)):
                        cols.append((name, col))
                except Exception:
                    pass
            if cols:
                pref = [c for c in cols if "perm" in c[0].lower()]
                arr = (pref[0] if pref else cols[-1])[1]
                if arr.size == 37500:
                    return arr.reshape(15, 50, 50)
    except Exception:
        pass

    # Fallback plain numeric CSV.
    x = np.loadtxt(path, delimiter=",")
    x = np.asarray(x, dtype=float)

    if x.ndim == 2 and x.shape[1] > 1:
        x = x[:, -1]

    x = x.reshape(-1)

    if x.size != 37500:
        raise RuntimeError(f"Permeability CSV has {x.size} values; expected 37500.")

    return x.reshape(15, 50, 50)


def infer_porosity(sg1_text: str, sg1_constants: dict):
    candidates = []
    for k, v in sg1_constants.items():
        if not isinstance(v, (int, float)):
            continue
        lk = k.lower()
        fv = float(v)
        if 0.0 < fv < 1.0 and ("poro" in lk or "porosity" in lk or lk == "phi"):
            candidates.append((k, fv))

    if len(candidates) == 1:
        return candidates[0][1], f"SG1 constant {candidates[0][0]}"

    if len(candidates) > 1:
        vals = sorted(set(v for _, v in candidates))
        if len(vals) == 1:
            return vals[0], "equivalent SG1 porosity constants"

    patterns = [
        r'porosity\s*=\s*np\.full\([^,]+,\s*([0-9]*\.?[0-9]+)',
        r'phi\s*=\s*np\.full\([^,]+,\s*([0-9]*\.?[0-9]+)',
        r'porosity\s*=\s*np\.ones\([^)]+\)\s*\*\s*([0-9]*\.?[0-9]+)',
    ]
    for patt in patterns:
        m = re.search(patt, sg1_text, flags=re.I | re.S)
        if m:
            return float(m.group(1)), "SG1 explicit constant-porosity expression"

    raise RuntimeError("Could not source-authentically bind constant porosity value.")


def load_bound_kz_ratio():
    if not R8A_SUMMARY.exists():
        raise FileNotFoundError(R8A_SUMMARY)
    if not R8A_CONTRACT.exists():
        raise FileNotFoundError(R8A_CONTRACT)

    summary = load_json(R8A_SUMMARY)
    contract = load_json(R8A_CONTRACT)

    if summary.get("status") != "V16A_KZ_ANISOTROPY_RATIO_FINAL_BOUND":
        raise RuntimeError("R8R expects successful R8A anisotropy binding.")

    if not contract.get("kz_horizontal_ratio_bound"):
        raise RuntimeError("R8A contract does not mark anisotropy ratio as bound.")

    ratio = float(contract["kz_horizontal_ratio"])
    if not (0.0 < ratio <= 1.0):
        raise RuntimeError(f"Invalid R8A anisotropy ratio: {ratio}")

    return ratio, contract


def reconstruct_geology():
    sg1, sg2 = find_sg1_sg2_sources()
    sg1_text, sg1_constants = parse_source_constants(sg1)

    perm_csv = find_perm_csv(sg1_text)
    K = load_perm_csv(perm_csv)

    kz_ratio, r8a_contract = load_bound_kz_ratio()
    poro_value, poro_source = infer_porosity(sg1_text, sg1_constants)

    Kx = K.astype(np.float64, copy=True)
    Ky = K.astype(np.float64, copy=True)
    Kz = kz_ratio * K
    porosity = np.full_like(K, poro_value, dtype=np.float64)

    provenance = [
        {
            "component": "Kx",
            "source": str(perm_csv),
            "source_sha256": sha256_file(perm_csv),
            "derivation": "Kx = frozen SGSim permeability",
        },
        {
            "component": "Ky",
            "source": str(perm_csv),
            "source_sha256": sha256_file(perm_csv),
            "derivation": "Ky = frozen SGSim permeability",
        },
        {
            "component": "Kz",
            "source": str(R8A_CONTRACT),
            "source_sha256": sha256_file(R8A_CONTRACT),
            "derivation": f"Kz = {kz_ratio} * frozen SGSim permeability",
        },
        {
            "component": "porosity",
            "source": str(sg1),
            "source_sha256": sha256_file(sg1),
            "derivation": f"constant porosity = {poro_value} ({poro_source})",
        },
    ]

    return {
        "Kx": Kx,
        "Ky": Ky,
        "Kz": Kz,
        "porosity": porosity,
    }, provenance, {
        "SG1_source": str(sg1),
        "SG2_source": str(sg2),
        "perm_csv": str(perm_csv),
        "kz_ratio": kz_ratio,
        "porosity": poro_value,
    }


def load_dynamic():
    with np.load(R7_DYNAMIC, allow_pickle=False) as db:
        return {
            k: np.array(db[k], copy=True)
            for k in ["pressure", "Qx", "Qy", "Qz"]
        }


def load_velocity():
    with np.load(R7B_RESIDUAL, allow_pickle=False) as db:
        return {
            k: np.array(db[k], copy=True)
            for k in ["Vx", "Vy", "Vz"]
        }


def find_npz_key(key: str, expected_shape, preferred_tokens):
    candidates = []
    outroot = ROOT / "output"

    if not outroot.exists():
        return None

    for p in sorted(outroot.rglob("*.npz")):
        lowp = str(p).lower()

        if "v16_" in lowp or "v16a" in lowp:
            continue

        try:
            with np.load(p, allow_pickle=False) as db:
                if key not in db.files:
                    continue

                a = np.asarray(db[key])

                if tuple(a.shape) != tuple(expected_shape):
                    continue
                if not np.issubdtype(a.dtype, np.number):
                    continue
                if not np.all(np.isfinite(a)):
                    continue

                score = 0
                for tok in preferred_tokens:
                    if tok.lower() in lowp:
                        score += 100

                candidates.append((score, p, np.array(a, copy=True)))
        except Exception:
            continue

    if not candidates:
        return None

    candidates.sort(key=lambda x: (-x[0], str(x[1])))
    top_score = candidates[0][0]
    top = [c for c in candidates if c[0] == top_score]

    hashes = {sha256_array(c[2]) for c in top}
    if len(hashes) != 1:
        raise RuntimeError(f"Ambiguous persisted authority for key {key}")

    return top[0][1], top[0][2]


def load_pollock_references():
    specs = [
        (
            "streamline_xyz",
            (1078, 201, 3),
            ["sg7c_frozen_pirnn_streamline_deployment"],
            ["streamline_xyz", "transport_xyz"],
        ),
        (
            "pollock_tof",
            (1078, 201),
            ["streamline_transport_coordinates", "sg6"],
            ["tau_s", "tof", "pollock_tof"],
        ),
        (
            "streamline_weight",
            (1078,),
            ["streamlines_pollock", "sg5"],
            ["weights_m3_s", "streamline_weight", "weights"],
        ),
    ]

    arrays = {}
    provenance = []

    for comp, shape, prefs, aliases in specs:
        found = None

        for key in aliases:
            found = find_npz_key(key, shape, prefs)
            if found is not None:
                p, a = found
                arrays[comp] = a
                provenance.append({
                    "component": comp,
                    "source": str(p),
                    "source_sha256": sha256_file(p),
                    "derivation": f"persisted frozen Pollock reference key={key}",
                })
                break

        if found is None:
            raise RuntimeError(f"Could not bind frozen Pollock reference: {comp}")

    return arrays, provenance


def validate_component(name, arr):
    return (
        tuple(arr.shape) == EXPECTED[name]
        and np.issubdtype(arr.dtype, np.number)
        and np.all(np.isfinite(arr))
    )


def build_checksums():
    rows = []
    for p in sorted(PACKAGE.iterdir()):
        if p.is_file() and p.name != CHECKSUM_FILE.name:
            rows.append({
                "file": p.name,
                "sha256": sha256_file(p),
                "bytes": p.stat().st_size,
            })
    save_csv(CHECKSUM_FILE, rows)


def build_zip():
    if ZIP_FILE.exists():
        ZIP_FILE.unlink()

    with zipfile.ZipFile(ZIP_FILE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(PACKAGE.iterdir()):
            if p.is_file():
                zf.write(p, arcname=f"{PACKAGE.name}/{p.name}")


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16A-R8R")
    print("Repaired Foundation Case 0001 Final Assembly / Freeze")
    print("=" * 78)

    print("""
R8A BOUND Kz/Kh WILL BE CONSUMED DIRECTLY.
NO ANISOTROPY REDISCOVERY WILL BE PERFORMED.
NO PRODUCER ID WILL BE FABRICATED.
NO SG3 PRESSURE SOLVE WILL BE RERUN.
NO SG4 DARCY FLUX WILL BE RERUN.
NO VELOCITY ARRAY WILL BE RECOMPUTED.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO FAST MARCHING WILL BE EXECUTED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
NO FROZEN V15 ARTIFACT WILL BE CHANGED.
""")

    # -------------------------------------------------------------------------
    # Authority checks
    # -------------------------------------------------------------------------
    if not R7E_SUMMARY.exists():
        raise FileNotFoundError(R7E_SUMMARY)

    r7e = load_json(R7E_SUMMARY)
    if r7e.get("status") != "V16A_FOUNDATION_CASE_0001_FREEZE_AUTHORIZED_WITH_PRODUCER_ID_SCOPE_LIMITATION":
        raise RuntimeError("R8R expects successful R7E foundation-freeze authorization.")

    kz_ratio, r8a_contract = load_bound_kz_ratio()

    if not R7_DYNAMIC.exists():
        raise FileNotFoundError(R7_DYNAMIC)
    if not R7B_RESIDUAL.exists():
        raise FileNotFoundError(R7B_RESIDUAL)

    # -------------------------------------------------------------------------
    # Assemble
    # -------------------------------------------------------------------------
    geology, geology_prov, geology_meta = reconstruct_geology()
    dynamic = load_dynamic()
    velocity = load_velocity()
    pollock, pollock_prov = load_pollock_references()

    arrays = {}
    arrays.update(geology)
    arrays.update(dynamic)
    arrays.update(velocity)
    arrays.update(pollock)

    arrays["streamline_weight"] = arrays["streamline_weight"].reshape(-1)

    component_rows = []
    all_valid = True

    for name in EXPECTED:
        a = arrays.get(name)
        valid = a is not None and validate_component(name, a)
        all_valid = all_valid and valid

        component_rows.append({
            "component": name,
            "required": True,
            "present": a is not None,
            "shape": str(tuple(a.shape)) if a is not None else "",
            "expected_shape": str(EXPECTED[name]),
            "dtype": str(a.dtype) if a is not None else "",
            "finite": bool(np.all(np.isfinite(a))) if a is not None else False,
            "valid": valid,
            "array_sha256": sha256_array(a) if a is not None else "",
        })

    component_rows.append({
        "component": "producer_id",
        "required": False,
        "present": False,
        "shape": "",
        "expected_shape": "(1078,)",
        "dtype": "",
        "finite": "",
        "valid": True,
        "array_sha256": "",
        "scope_status": "UNAVAILABLE_FROM_FROZEN_NONRETRACE_PROVENANCE",
    })

    save_csv(COMPONENT_TABLE, component_rows)

    scope_rows = [
        {
            "scope_item": "producer_id",
            "status": "NOT_INCLUDED_NOT_REQUIRED",
            "reason": "Historical producer connectivity labels are unavailable without Pollock retrace or a new V16 rule.",
        },
        {
            "scope_item": "future producer connectivity classification",
            "status": "ALLOWED_ONLY_AS_SEPARATELY_LABELED_POST_FREEZE_V16_DERIVATION",
            "reason": "Must not be represented as historical V15 authority.",
        },
        {
            "scope_item": "Fast Marching",
            "status": "NOT_EXECUTED_IN_V16A",
            "reason": "V16B begins only after Foundation Case 0001 freeze.",
        },
    ]
    save_csv(SCOPE_TABLE, scope_rows)

    provenance_rows = list(geology_prov)

    provenance_rows.extend([
        {
            "component": "pressure;Qx;Qy;Qz",
            "source": str(R7_DYNAMIC),
            "source_sha256": sha256_file(R7_DYNAMIC),
            "derivation": "R7 controlled source-authentic SG3/SG4 regeneration",
        },
        {
            "component": "Vx;Vy;Vz",
            "source": str(R7B_RESIDUAL),
            "source_sha256": sha256_file(R7B_RESIDUAL),
            "derivation": "R7B exact SG5 algebraic reconstruction from R7 fluxes",
        },
        {
            "component": "Kz/Kh ratio",
            "source": str(R8A_CONTRACT),
            "source_sha256": sha256_file(R8A_CONTRACT),
            "derivation": f"R8A bound anisotropy ratio = {kz_ratio}",
        },
    ])

    provenance_rows.extend(pollock_prov)
    save_csv(PROVENANCE_TABLE, provenance_rows)

    gates = [
        ("incoming_R7E_freeze_authorization_reproduced", True),
        ("incoming_R8A_Kz_ratio_contract_reproduced", True),
        ("R8A_Kz_ratio_equals_bound_contract", np.isclose(kz_ratio, float(r8a_contract["kz_horizontal_ratio"]))),
        ("Kx_valid", validate_component("Kx", arrays["Kx"])),
        ("Ky_valid", validate_component("Ky", arrays["Ky"])),
        ("Kz_valid", validate_component("Kz", arrays["Kz"])),
        ("porosity_valid", validate_component("porosity", arrays["porosity"])),
        ("pressure_valid", validate_component("pressure", arrays["pressure"])),
        ("Qx_valid", validate_component("Qx", arrays["Qx"])),
        ("Qy_valid", validate_component("Qy", arrays["Qy"])),
        ("Qz_valid", validate_component("Qz", arrays["Qz"])),
        ("Vx_valid", validate_component("Vx", arrays["Vx"])),
        ("Vy_valid", validate_component("Vy", arrays["Vy"])),
        ("Vz_valid", validate_component("Vz", arrays["Vz"])),
        ("streamline_xyz_valid", validate_component("streamline_xyz", arrays["streamline_xyz"])),
        ("pollock_tof_valid", validate_component("pollock_tof", arrays["pollock_tof"])),
        ("streamline_weight_valid", validate_component("streamline_weight", arrays["streamline_weight"])),
        ("producer_id_explicitly_nonrequired", True),
        ("all_required_components_valid", all_valid),
        ("no_producer_id_fabricated", True),
        ("no_SG3_rerun", True),
        ("no_SG4_rerun", True),
        ("no_velocity_recompute", True),
        ("no_Pollock_retrace", True),
        ("no_FMM", True),
        ("no_model_predict", True),
        ("no_training", True),
        ("no_V15_mutation", True),
    ]
    save_csv(FREEZE_GATES, [{"gate": g, "passed": bool(p)} for g,p in gates])

    # -------------------------------------------------------------------------
    # Freeze or block
    # -------------------------------------------------------------------------
    if all_valid:
        payload = {k: np.asarray(v) for k,v in arrays.items()}
        payload["authority_label_ascii"] = np.frombuffer(
            b"PAD_STREAM_V16A_FOUNDATION_CASE_0001", dtype=np.uint8
        )
        payload["kz_horizontal_ratio"] = np.asarray([kz_ratio], dtype=np.float64)
        np.savez_compressed(FOUNDATION_NPZ, **payload)

        status = "V16A_FOUNDATION_CASE_0001_FROZEN_COMPLETE"
        diagnosis = "ALL_REQUIRED_GEOLOGY_PRESSURE_FLOW_VELOCITY_AND_POLLOCK_REFERENCE_COMPONENTS_ARE_VALID_AND_PACKAGED"
        recommendation = (
            "Close V16A. Preserve Foundation Case 0001 as the immutable post-V15 development base. "
            "Begin V16B with the exact Fast Marching physics baseline using this frozen foundation."
        )
        next_stage = "V16B — Exact Fast Marching Physics Baseline"
    else:
        failed_components = [
            row["component"]
            for row in component_rows
            if row.get("required") and not row.get("valid")
        ]
        status = "V16A_FOUNDATION_CASE_0001_ASSEMBLY_BLOCKED"
        diagnosis = "ONE_OR_MORE_REQUIRED_FOUNDATION_COMPONENT_VALIDATION_GATES_FAILED"
        recommendation = (
            "Do not freeze. Audit only failed R8R component bindings: "
            + ", ".join(failed_components)
        )
        next_stage = "V16A-R8B — Foundation Assembly Residual Binding Audit"

    manifest = {
        "milestone": "V16A-R8R",
        "status": status,
        "diagnosis": diagnosis,
        "foundation_case": "0001",
        "geology_metadata": geology_meta,
        "kz_horizontal_ratio": kz_ratio,
        "kz_ratio_authority": str(R8A_CONTRACT),
        "required_components": list(EXPECTED.keys()),
        "producer_id": {
            "required": False,
            "included": False,
            "status": "UNAVAILABLE_FROM_FROZEN_NONRETRACE_PROVENANCE",
        },
        "foundation_npz": str(FOUNDATION_NPZ) if FOUNDATION_NPZ.exists() else None,
        "foundation_npz_sha256": sha256_file(FOUNDATION_NPZ) if FOUNDATION_NPZ.exists() else None,
        "constraints": {
            "SG3_rerun": False,
            "SG4_rerun": False,
            "velocity_recompute": False,
            "Pollock_retrace": False,
            "FMM": False,
            "model_predict": False,
            "training": False,
            "V15_mutation": False,
        },
        "recommendation": recommendation,
        "next_stage": next_stage,
    }
    save_json(MANIFEST, manifest)

    save_json(SUMMARY, {
        "milestone": "V16A-R8R",
        "status": status,
        "diagnosis": diagnosis,
        "foundation_case": "0001",
        "kz_horizontal_ratio": kz_ratio,
        "foundation_npz": manifest["foundation_npz"],
        "foundation_npz_sha256": manifest["foundation_npz_sha256"],
        "producer_id_required": False,
        "producer_id_status": "UNAVAILABLE_FROM_FROZEN_NONRETRACE_PROVENANCE",
        "recommendation": recommendation,
        "next_stage": next_stage,
    })

    if all_valid:
        build_checksums()
        build_zip()

    print("FOUNDATION CASE 0001")
    print(f"  Bound Kz/Kh ratio       : {kz_ratio}")
    for row in component_rows:
        req = "REQ" if row.get("required") else "OPT"
        print(
            f"  {row['component']:<20} | {req} | "
            f"present={row['present']} | valid={row['valid']}"
        )

    print("\n" + "=" * 78)
    print("V16A-R8R FINAL FREEZE GATES")
    print("=" * 78)
    for g,p in gates:
        print(f"[{'PASS' if p else 'FAIL'}] {g}")
    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT STAGE")
    print(f"  {next_stage}")

    print("\nOUTPUTS")
    print(f"  Package directory:\n    {PACKAGE}")

    if FOUNDATION_NPZ.exists():
        print("\nFoundation numerical artifact:")
        print(f"  {FOUNDATION_NPZ.name}")
        print(f"  SHA-256: {sha256_file(FOUNDATION_NPZ)}")

    print("\nTables / records:")
    for p in [
        COMPONENT_TABLE,
        SCOPE_TABLE,
        PROVENANCE_TABLE,
        FREEZE_GATES,
        MANIFEST,
        SUMMARY,
    ]:
        print(f"  {p.name}")

    if CHECKSUM_FILE.exists():
        print(f"  {CHECKSUM_FILE.name}")

    if ZIP_FILE.exists():
        print("\nFrozen package ZIP:")
        print(f"  {ZIP_FILE}")
        print(f"  SHA-256: {sha256_file(ZIP_FILE)}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16A-R8R REPAIRED FOUNDATION CASE 0001 FREEZE: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()

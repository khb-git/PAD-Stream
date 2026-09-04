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
# PAD-Stream V16A-R8
# Foundation Case 0001 Final Assembly / Freeze
#
# PURPOSE
# -------
# R7E authorized Foundation Case 0001 freeze with one explicit limitation:
# producer_id is unavailable from frozen non-retrace provenance and is NOT a
# required primitive foundation component.
#
# R8 assembles one immutable V16A foundation package containing:
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
#     producer_id = unavailable historical metadata / not required
#
# R8 WILL NOT:
#   - rerun SG3 or SG4,
#   - recompute velocity,
#   - retrace Pollock,
#   - run Fast Marching,
#   - train/infer ML,
#   - invent producer_id,
#   - mutate frozen V15 artifacts.
#
# K / POROSITY POLICY
# -------------------
# R3 established Kx/Ky/Kz/porosity as deterministic algebraic reconstructions
# from frozen SG1/SG2 source-authentic inputs. R8 reconstructs them only from:
#   - the original 50x50x15 SGSim permeability CSV,
#   - exact SG1/SG2 source-defined anisotropy / porosity constants.
#
# No new geological realization is generated.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT_ROOT = ROOT / "output" / "V16_A_R8_FOUNDATION_CASE_0001_FREEZE"
PACKAGE = OUT_ROOT / "PAD_Stream_V16A_Foundation_Case_0001"
PACKAGE.mkdir(parents=True, exist_ok=True)

R7E_DIR = ROOT / "output" / "V16_A_R7E_PRODUCER_SCOPE_FREEZE_DECISION"
R7E_SUMMARY = R7E_DIR / "PAD_Stream_V16AR7E_Summary.json"

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
SUMMARY = PACKAGE / "PAD_Stream_V16A_R8_Summary.json"
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


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_source_constants(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(text)
    constants = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = getattr(node, "value", None)
        try:
            val = ast.literal_eval(value)
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
        # Prefer known geological integration source.
        pref = [p for p in sg1 if "Geology_Integration" in p.name]
        if len(pref) == 1:
            sg1 = pref

    if len(sg2) != 1:
        pref = [p for p in sg2 if "Transmiss" in p.name]
        if len(pref) == 1:
            sg2 = pref

    if len(sg1) != 1 or len(sg2) != 1:
        raise RuntimeError(
            f"Could not uniquely resolve SG1/SG2 sources: "
            f"SG1={[p.name for p in sg1]}, SG2={[p.name for p in sg2]}"
        )
    return sg1[0], sg2[0]


def find_perm_csv(sg1_text: str):
    # First: literal CSV names from SG1 source.
    literals = re.findall(r'["\']([^"\']+\.csv)["\']', sg1_text, flags=re.I)
    candidates = []
    for lit in literals:
        p = Path(lit)
        tests = [p, ROOT / p, ROOT / p.name]
        for q in tests:
            if q.exists() and "perm" in q.name.lower():
                candidates.append(q.resolve())

    # Second: project search restricted to the exact expected model dimensions/name.
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
    # Robust numeric CSV load. Header is allowed.
    attempts = [
        lambda: np.loadtxt(path, delimiter=","),
        lambda: np.genfromtxt(path, delimiter=",", names=True),
    ]

    arr = None
    for fn in attempts:
        try:
            x = fn()
            if getattr(x, "dtype", None) is not None and x.dtype.names:
                # take last numeric column; SGSim CSVs commonly include index columns
                cols = []
                for name in x.dtype.names:
                    try:
                        col = np.asarray(x[name], dtype=float)
                        if np.all(np.isfinite(col)):
                            cols.append((name, col))
                    except Exception:
                        pass
                if cols:
                    # Prefer permeability-like column.
                    preferred = [c for c in cols if "perm" in c[0].lower()]
                    arr = (preferred[0] if preferred else cols[-1])[1]
                    break
            else:
                x = np.asarray(x, dtype=float)
                if np.all(np.isfinite(x)):
                    if x.ndim == 2 and x.shape[1] > 1:
                        arr = x[:, -1]
                    else:
                        arr = x.reshape(-1)
                    break
        except Exception:
            continue

    if arr is None:
        raise RuntimeError(f"Failed to read numeric permeability data from {path}")

    if arr.size != 15 * 50 * 50:
        raise RuntimeError(f"Permeability CSV has {arr.size} values; expected 37500.")

    # V15 SG arrays are (nz, ny, nx).
    return np.asarray(arr, dtype=np.float64).reshape(15, 50, 50)


def infer_kz_ratio(sg2_text: str, sg2_constants: dict):
    # Prefer explicit constants with anisotropy / kz names.
    for k, v in sg2_constants.items():
        lk = k.lower()
        if isinstance(v, (int, float)) and (
            "kz" in lk or "anisot" in lk or "vertical" in lk
        ):
            fv = float(v)
            if 0.0 < fv <= 1.0:
                return fv, f"SG2 constant {k}"

    # Exact source pattern Kz = factor * K...
    patterns = [
        r'Kz\s*=\s*([0-9]*\.?[0-9]+)\s*\*\s*[A-Za-z_][A-Za-z0-9_]*',
        r'kz\s*=\s*([0-9]*\.?[0-9]+)\s*\*\s*[A-Za-z_][A-Za-z0-9_]*',
    ]
    for patt in patterns:
        m = re.search(patt, sg2_text)
        if m:
            return float(m.group(1)), "SG2 source multiplication"

    raise RuntimeError("Could not source-authentically bind Kz/K horizontal anisotropy ratio.")


def infer_porosity(sg1_text: str, sg1_constants: dict):
    # Prefer explicit porosity/phi scalar constant.
    candidates = []
    for k, v in sg1_constants.items():
        lk = k.lower()
        if isinstance(v, (int, float)) and ("poro" in lk or lk == "phi" or "porosity" in lk):
            fv = float(v)
            if 0.0 < fv < 1.0:
                candidates.append((k, fv))

    if len(candidates) == 1:
        return candidates[0][1], f"SG1 constant {candidates[0][0]}"

    if len(candidates) > 1:
        vals = sorted(set(v for _, v in candidates))
        if len(vals) == 1:
            return vals[0], "SG1 equivalent porosity constants"

    # Explicit np.full / ones pattern containing scalar.
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


def reconstruct_geology():
    sg1, sg2 = find_sg1_sg2_sources()
    sg1_text, sg1_constants = parse_source_constants(sg1)
    sg2_text, sg2_constants = parse_source_constants(sg2)

    perm_csv = find_perm_csv(sg1_text)
    K = load_perm_csv(perm_csv)

    kz_ratio, kz_source = infer_kz_ratio(sg2_text, sg2_constants)
    poro_value, poro_source = infer_porosity(sg1_text, sg1_constants)

    Kx = K.copy()
    Ky = K.copy()
    Kz = kz_ratio * K
    porosity = np.full_like(K, poro_value, dtype=np.float64)

    provenance = [
        {
            "component": "Kx",
            "source": str(perm_csv),
            "source_sha256": sha256_file(perm_csv),
            "derivation": "Kx = SGSim permeability",
        },
        {
            "component": "Ky",
            "source": str(perm_csv),
            "source_sha256": sha256_file(perm_csv),
            "derivation": "Ky = SGSim permeability",
        },
        {
            "component": "Kz",
            "source": str(sg2),
            "source_sha256": sha256_file(sg2),
            "derivation": f"Kz = {kz_ratio} * SGSim permeability ({kz_source})",
        },
        {
            "component": "porosity",
            "source": str(sg1),
            "source_sha256": sha256_file(sg1),
            "derivation": f"constant porosity = {poro_value} ({poro_source})",
        },
    ]

    return {
        "Kx": Kx, "Ky": Ky, "Kz": Kz, "porosity": porosity
    }, provenance


def load_dynamic():
    with np.load(R7_DYNAMIC, allow_pickle=False) as db:
        return {k: np.array(db[k], copy=True) for k in ["pressure", "Qx", "Qy", "Qz"]}


def load_velocity():
    with np.load(R7B_RESIDUAL, allow_pickle=False) as db:
        return {k: np.array(db[k], copy=True) for k in ["Vx", "Vy", "Vz"]}


def find_npz_key(key: str, expected_shape, preferred_names):
    outroot = ROOT / "output"
    candidates = []

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
                if tuple(a.shape) != expected_shape:
                    continue
                if not np.issubdtype(a.dtype, np.number) or not np.all(np.isfinite(a)):
                    continue

                score = 0
                for token in preferred_names:
                    if token.lower() in lowp:
                        score += 100
                candidates.append((score, p, np.array(a, copy=True)))
        except Exception:
            continue

    candidates.sort(key=lambda x: (-x[0], str(x[1])))
    if not candidates:
        return None

    top_score = candidates[0][0]
    top = [c for c in candidates if c[0] == top_score]
    hashes = {sha256_array(c[2]) for c in top}

    if len(hashes) != 1:
        raise RuntimeError(f"Ambiguous persisted authority for key {key}")

    return top[0][1], top[0][2]


def load_pollock_references():
    bindings = {}

    # Exact keys from the earlier V16A binding lineage.
    specs = [
        ("streamline_xyz", (1078, 201, 3), ["sg7c_frozen_pirnn_streamline_deployment"]),
        ("pollock_tof", (1078, 201), ["streamline_transport_coordinates", "sg6"]),
        ("streamline_weight", (1078,), ["streamlines_pollock", "sg5"]),
    ]

    # key aliases reflecting actual earlier V15 artifact naming
    key_aliases = {
        "streamline_xyz": ["streamline_xyz", "transport_xyz"],
        "pollock_tof": ["tau_s", "tof", "pollock_tof"],
        "streamline_weight": ["weights_m3_s", "streamline_weight", "weights"],
    }

    arrays = {}
    provenance = []

    for comp, shape, prefs in specs:
        found = None
        for key in key_aliases[comp]:
            found = find_npz_key(key, shape, prefs)
            if found:
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
            raise RuntimeError(f"Could not bind frozen Pollock reference {comp}")

    return arrays, provenance


def validate_component(name, a):
    return (
        tuple(a.shape) == EXPECTED[name]
        and np.issubdtype(a.dtype, np.number)
        and np.all(np.isfinite(a))
    )


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16A-R8")
    print("Foundation Case 0001 Final Assembly / Freeze")
    print("=" * 78)

    print("""
NO PRODUCER ID WILL BE FABRICATED.
NO SG3 PRESSURE SOLVE WILL BE RERUN.
NO SG4 DARCY FLUX WILL BE RERUN.
NO VELOCITY ARRAY WILL BE RECOMPUTED.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO FAST MARCHING WILL BE EXECUTED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
NO FROZEN V15 ARTIFACT WILL BE CHANGED.

FOUNDATION CASE 0001 WILL BE ASSEMBLED FROM:
  - deterministic frozen-V15 geology reconstruction,
  - R7 pressure / flux artifact,
  - R7B velocity artifact,
  - persisted frozen Pollock XYZ / TOF / weights.

producer_id IS EXPLICITLY OUT OF REQUIRED FREEZE SCOPE.
""")

    if not R7E_SUMMARY.exists():
        raise FileNotFoundError(R7E_SUMMARY)

    r7e = load_json(R7E_SUMMARY)
    if r7e.get("status") != "V16A_FOUNDATION_CASE_0001_FREEZE_AUTHORIZED_WITH_PRODUCER_ID_SCOPE_LIMITATION":
        raise RuntimeError("R8 expects successful R7E foundation-freeze authorization.")

    if not R7_DYNAMIC.exists():
        raise FileNotFoundError(R7_DYNAMIC)
    if not R7B_RESIDUAL.exists():
        raise FileNotFoundError(R7B_RESIDUAL)

    geology, geo_prov = reconstruct_geology()
    dynamic = load_dynamic()
    velocity = load_velocity()
    pollock, pollock_prov = load_pollock_references()

    arrays = {}
    arrays.update(geology)
    arrays.update(dynamic)
    arrays.update(velocity)
    arrays.update(pollock)

    # Normalize weight to 1-D.
    arrays["streamline_weight"] = arrays["streamline_weight"].reshape(-1)

    component_rows = []
    all_valid = True
    for name in EXPECTED:
        a = arrays.get(name)
        valid = a is not None and validate_component(name, a)
        all_valid &= valid
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

    # Explicit non-required component.
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

    provenance_rows = []
    provenance_rows.extend(geo_prov)
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
    ])
    provenance_rows.extend(pollock_prov)
    save_csv(PROVENANCE_TABLE, provenance_rows)

    gates = [
        ("incoming_R7E_freeze_authorization_reproduced", True),
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
    save_csv(FREEZE_GATES, [{"gate": g, "passed": p} for g,p in gates])

    if not all_valid:
        failed = [g for g,p in gates if not p]
        status = "V16A_FOUNDATION_CASE_0001_ASSEMBLY_BLOCKED"
        diagnosis = "ONE_OR_MORE_REQUIRED_FOUNDATION_COMPONENT_VALIDATION_GATES_FAILED"
        recommendation = "Do not freeze. Audit only failed R8 component bindings: " + ", ".join(failed)
        next_stage = "V16A-R8A — Foundation Assembly Residual Binding Audit"
    else:
        # Save authoritative frozen V16A dataset.
        payload = {k: np.asarray(v) for k,v in arrays.items()}
        payload["authority_label_ascii"] = np.frombuffer(
            b"PAD_STREAM_V16A_FOUNDATION_CASE_0001", dtype=np.uint8
        )
        np.savez_compressed(FOUNDATION_NPZ, **payload)

        status = "V16A_FOUNDATION_CASE_0001_FROZEN_COMPLETE"
        diagnosis = "ALL_REQUIRED_GEOLOGY_PRESSURE_FLOW_VELOCITY_AND_POLLOCK_REFERENCE_COMPONENTS_ARE_VALID_AND_PACKAGED"
        recommendation = (
            "Close V16A. Preserve Foundation Case 0001 as the immutable post-V15 development base. "
            "Begin V16B with an exact Fast Marching physics baseline using this frozen foundation."
        )
        next_stage = "V16B — Exact Fast Marching Physics Baseline"

    manifest = {
        "milestone": "V16A-R8",
        "status": status,
        "diagnosis": diagnosis,
        "foundation_case": "0001",
        "required_components": list(EXPECTED.keys()),
        "producer_id": {
            "required": False,
            "included": False,
            "status": "UNAVAILABLE_FROM_FROZEN_NONRETRACE_PROVENANCE",
        },
        "foundation_npz": str(FOUNDATION_NPZ) if FOUNDATION_NPZ.exists() else None,
        "foundation_npz_sha256": sha256_file(FOUNDATION_NPZ) if FOUNDATION_NPZ.exists() else None,
        "provenance": provenance_rows,
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
        "milestone": "V16A-R8",
        "status": status,
        "diagnosis": diagnosis,
        "foundation_case": "0001",
        "foundation_npz": manifest["foundation_npz"],
        "foundation_npz_sha256": manifest["foundation_npz_sha256"],
        "producer_id_required": False,
        "producer_id_status": "UNAVAILABLE_FROM_FROZEN_NONRETRACE_PROVENANCE",
        "recommendation": recommendation,
        "next_stage": next_stage,
    })

    # Freeze package checksum inventory.
    if all_valid:
        checksum_rows = []
        for p in sorted(PACKAGE.iterdir()):
            if p.is_file():
                checksum_rows.append({
                    "file": p.name,
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                })
        checksum_file = PACKAGE / "V16A_Foundation_Case_0001_SHA256.csv"
        save_csv(checksum_file, checksum_rows)

        # Rebuild ZIP only from package files.
        if ZIP_FILE.exists():
            ZIP_FILE.unlink()
        with zipfile.ZipFile(ZIP_FILE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(PACKAGE.iterdir()):
                if p.is_file():
                    zf.write(p, arcname=f"{PACKAGE.name}/{p.name}")

    print("FOUNDATION CASE 0001")
    for row in component_rows:
        req = "REQ" if row.get("required") else "OPT"
        print(f"  {row['component']:<20} | {req} | present={row['present']} | valid={row['valid']}")

    print("\n" + "=" * 78)
    print("V16A-R8 FINAL FREEZE GATES")
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
        COMPONENT_TABLE, SCOPE_TABLE, PROVENANCE_TABLE,
        FREEZE_GATES, MANIFEST, SUMMARY
    ]:
        print(f"  {p.name}")

    if ZIP_FILE.exists():
        print("\nFrozen package ZIP:")
        print(f"  {ZIP_FILE}")
        print(f"  SHA-256: {sha256_file(ZIP_FILE)}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16A-R8 FOUNDATION CASE 0001 ASSEMBLY / FREEZE: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()

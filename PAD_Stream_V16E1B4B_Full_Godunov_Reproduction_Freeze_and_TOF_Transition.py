#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, os, re

MILESTONE = "V16E-1B4B"
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")
RUN = DRIVE / "runs" / "V16E-BLREP-FULL-GODUNOV-CUDA-001"
SOURCE = Path("/content/PAD-Stream/pi_rnn_stage4_full_godunov.py")
EXPECTED_SOURCE_SHA = "165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"

B4A = DRIVE / "provenance" / "stage4_full" / "V16E1B4A_SOURCE_AUTHORITY_AND_PHYSICS_PREFLIGHT"
AUTH = {
    B4A / "V16E1B4A_Source_Authority_and_Physics_Preflight.json":
        "8c9d460a079db6caf3a31c15305f70bc1557e46099c5b60b3d1619b86ceb29a7",
    B4A / "PAD_Stream_V16E1B4A_Summary.json":
        "6017ddacc2dbbf1c6436732c1b4f0bf174b7aa1c70ea900c33fff670ff02027e",
    B4A / "V16E1B4A_Handoff.md":
        "23502655a58623af795ee49900bc24faf57580565bffa7e593c20c469d9b38bd",
}
EXPECTED = {
    "stage4_godunov_dataset.npz":
        "dac15962c4f26c2956b1bed2b7e102e6544e165e0824611ecaf7874a1ca37b80",
    "pi_rnn_stage4_full_godunov.weights.h5":
        "143ce31a72cb19c3550d54811d8aca6ed08ea2417fe606e6ef20350aef39d4a2",
    "pi_rnn_stage4_full_godunov_config.json":
        "ae764534b14b634ca74ae0065f75862a94fb9367423ce3fc40258b5845e29110",
    "training_convergence_stage4_full_godunov.png":
        "e431ff440165de2b6fb5a024f21c7f97f2858a2ecbce268e9b7b429511684458",
    "training_convergence_stage4_full_godunov.pdf":
        "5787d45c72f4aefd792662b3ef22bb8d29ac0c1b56882a912a906786197b625b",
    "diagnostic_case1_full_pec22_nc01.png":
        "16356483dafa393e45559d27e0d003e875fecdce398be42b4b1395fd423f1ca5",
    "diagnostic_case1_full_pec22_nc01.pdf":
        "ba0d193eee24fbda3759be55b69be8cf70592e61df382564480519118aa54159",
    "diagnostic_case2_nesting_pec100_nc0.png":
        "dafcd7756fb826d1c30be848700f1751cd9cdcd9671ac0ae7284bf86da840417",
    "diagnostic_case2_nesting_pec100_nc0.pdf":
        "cc66db7f0660a0a638349a62a65eff31ab646c3e64ab81bc3ddb97a571d4b939",
    "stage4_full_godunov_run.log":
        "c7ede70e4c2d7bae36f219577efce9eca5bb7d89aa0cc086a86c9a485840247e",
}
SLAB = RUN / "stage4_godunov_slab.npz"
OUT = DRIVE / "provenance" / "stage4_full" / "V16E1B4B_REPRODUCTION_FREEZE"
OUT.mkdir(parents=True, exist_ok=True)
RESULTS = OUT / "V16E1B4B_Full_Godunov_Reproduction_Results.json"
SUMMARY = OUT / "PAD_Stream_V16E1B4B_Summary.json"
HANDOFF = OUT / "V16E1B4B_Handoff.md"

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

def gate(name, ok):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        raise RuntimeError(name)

def dump(path, obj):
    tmp = Path(str(path)+".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")
    os.replace(tmp, path)

print("="*110)
print("PAD-Stream V16E-1B4B — Full Godunov Reproduction Freeze / TOF Transition")
print("="*110)
print("NO TRAINING. NO RETUNING. NO DATASET REBUILD. NO NEW B4 BRANCH.")

gate("source_exists", SOURCE.exists())
gate("source_SHA_exact", sha(SOURCE) == EXPECTED_SOURCE_SHA)

for p, expected in AUTH.items():
    gate(f"{p.name}_exists", p.exists())
    gate(f"{p.name}_SHA_exact", sha(p) == expected)

artifact_hashes = {}
for name, expected in EXPECTED.items():
    p = RUN / name
    gate(f"{name}_exists", p.exists())
    actual = sha(p)
    artifact_hashes[name] = actual
    gate(f"{name}_SHA_exact", actual == expected)

gate("supplemental_slab_absent_as_observed", not SLAB.exists())

log = (RUN / "stage4_full_godunov_run.log").read_text(encoding="utf-8", errors="replace")

m = re.search(
    r"\[Stage 3\] Epoch 1000 \| Data ([0-9.eE+-]+) \| PDE ([0-9.eE+-]+) \(w=([0-9.eE+-]+)\) "
    r"\| BC_inj ([0-9.eE+-]+) \| BC_out ([0-9.eE+-]+) \| Anchor ([0-9.eE+-]+) "
    r"\| Mono ([0-9.eE+-]+) \| Mass ([0-9.eE+-]+) \| Curv ([0-9.eE+-]+)",
    log,
)
gate("epoch_1000_present_and_parseable", m is not None)
train = {
    "data": float(m.group(1)), "pde": float(m.group(2)), "pde_weight": float(m.group(3)),
    "bc_inj": float(m.group(4)), "bc_out": float(m.group(5)), "anchor": float(m.group(6)),
    "mono": float(m.group(7)), "mass": float(m.group(8)), "curv": float(m.group(9)),
}

pe_sweep = {}
for pe in (10, 22, 50, 100):
    x = re.search(rf"Pe_c =\s*{pe}\s*\| MAE = ([0-9.eE+-]+) \| max = ([0-9.eE+-]+)", log)
    gate(f"Pe_c_sweep_{pe}", x is not None)
    pe_sweep[str(pe)] = {"mae": float(x.group(1)), "max_abs": float(x.group(2))}

nc_sweep = {}
for nc in ("0.00", "0.05", "0.10", "0.20"):
    x = re.search(
        rf"Nc =\s*{re.escape(nc)}\s*\| MAE = ([0-9.eE+-]+) \| mean res = ([+-]?[0-9.eE+-]+) "
        r"\| t_BT = ([0-9]+) d \(x Y_L = ([0-9.]+)\)", log
    )
    gate(f"Nc_sweep_{nc}", x is not None)
    nc_sweep[nc] = {
        "mae": float(x.group(1)), "mean_residual": float(x.group(2)),
        "t_BT_days": int(x.group(3)), "Y_L": float(x.group(4)),
    }

gate(
    "breakthrough_shifts_earlier_with_Nc",
    nc_sweep["0.20"]["t_BT_days"] < nc_sweep["0.10"]["t_BT_days"] <
    nc_sweep["0.05"]["t_BT_days"] < nc_sweep["0.00"]["t_BT_days"],
)

r2s = [float(v) for v in re.findall(r"R²:\s*([0-9.]+)", log)]
means = [float(v) for v in re.findall(r"Mean residual:\s*([0-9.eE+-]+)", log)]
stds = [float(v) for v in re.findall(r"Std residual:\s*([0-9.eE+-]+)", log)]
maxres = [float(v) for v in re.findall(r"Max \|residual\|:\s*([0-9.eE+-]+)", log)]
gate("two_final_diagnostics", min(len(r2s),len(means),len(stds),len(maxres)) >= 2)

fan = re.search(
    r"Fan-region max\|dSw\| at inv_Pec = 0 vs Stage 1 analytical:\s*([0-9.eE+-]+)", log
)
gate("sharp_limit_metric", fan is not None)

limitations = [
    "The clean first B4 run omitted stage4_godunov_slab.npz because supplemental-slab generation sits in the dataset-reload branch.",
    "Localized high-Pe_c / early-time errors are much larger than profile-average MAE on the fixed 64-node interface.",
    "The inv_Pec -> 0 sharp-limit extrapolation does not monotonically sharpen; this remains an extrapolation limitation.",
    "Nc=0 physically nests Stage 3 but shows a modest surrogate-accuracy regression relative to the dedicated B3 model.",
]

results = {
    "milestone": MILESTONE,
    "status": "B4_FULL_GODUNOV_REPRODUCTION_COMPLETE_FROZEN_WITH_LIMITATIONS_TOF_BRIDGE_AUTHORIZED",
    "source_sha256": EXPECTED_SOURCE_SHA,
    "artifact_hashes": artifact_hashes,
    "supplemental_slab_present": SLAB.exists(),
    "final_epoch": 1000,
    "final_training_metrics": train,
    "Pe_c_sweep": pe_sweep,
    "Nc_sweep": nc_sweep,
    "diagnostics": {
        "case1_full_Pe22_Nc0p1": {"R2": r2s[-2], "mean_residual": means[-2], "std_residual": stds[-2], "max_abs_residual": maxres[-2]},
        "case2_nesting_Pe100_Nc0": {"R2": r2s[-1], "mean_residual": means[-1], "std_residual": stds[-1], "max_abs_residual": maxres[-1]},
    },
    "sharp_limit_fan_max_abs_dSw": float(fan.group(1)),
    "limitations": limitations,
    "B4_reproduction_complete": True,
    "B4_retraining_authorized": False,
    "B4_frozen_for_forward_progress": True,
    "native_BL_ladder_closed": True,
    "TOF_deployment_bridge_authorized": True,
    "next": "Physical-distance -> Pollock/time-of-flight deployment bridge.",
}
dump(RESULTS, results)
results_sha = sha(RESULTS)

summary = {
    "milestone": MILESTONE,
    "results_sha256": results_sha,
    "B4_reproduction_complete": True,
    "B4_frozen_for_forward_progress": True,
    "native_BL_ladder_closed": True,
    "TOF_deployment_bridge_authorized": True,
    "next": results["next"],
}
dump(SUMMARY, summary)
summary_sha = sha(SUMMARY)

handoff = f"""# PAD-Stream V16E-1B4B

## Status
B4 full compressible-capillary Godunov reproduction completed and frozen with documented limitations.

## Headline results
- Epochs: 1000
- Final data loss: {train["data"]:.6e}
- Final PDE loss: {train["pde"]:.6e}
- Full-physics diagnostic R² (Pe_c=22, Nc=0.1): {r2s[-2]:.6f}
- Stage-3 nesting diagnostic R² (Pe_c=100, Nc=0): {r2s[-1]:.6f}

## Forward decision
No B4 retraining or new B4 branch is authorized by this freeze.
The native 1-D BL ladder is closed for forward progress.
The physical-distance -> Pollock/time-of-flight deployment bridge is authorized.

## Documented limitations
1. Supplemental B4 slab absent from the clean first execution.
2. Localized high-Pe_c / early-time errors exceed profile-average MAE.
3. Sharp-limit extrapolation remains unresolved.
4. Nc=0 nesting has a modest accuracy regression versus the dedicated B3 surrogate.

Results SHA-256: {results_sha}
Summary SHA-256: {summary_sha}
"""
HANDOFF.write_text(handoff, encoding="utf-8")
handoff_sha = sha(HANDOFF)

print()
print("="*110)
print("B4B FREEZE RESULT")
print("="*110)
print("B4 reproduction complete         : YES")
print("Supplemental slab included       :", "YES" if SLAB.exists() else "NO")
print("Limitations documented           : YES")
print("B4 retraining authorized         : NO")
print("B4 frozen for forward progress   : YES")
print("Native BL ladder closed          : YES")
print("TOF deployment bridge authorized : YES")
print("Results SHA                      :", results_sha)
print("Summary SHA                      :", summary_sha)
print("Handoff SHA                      :", handoff_sha)
print("NEXT: physical-distance -> Pollock/time-of-flight deployment bridge.")

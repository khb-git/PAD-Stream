#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, os, re

MILESTONE = "V16E-1B3B"
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")
RUN = DRIVE / "runs" / "V16E-BLREP-CAP-CUDA-001"
SOURCE = Path("/content/PAD-Stream/pi_rnn_stage3_capillary.py")
EXPECTED_SOURCE_SHA = "980dc6eb51c894bcdbc5bce277bfaa7d24d26b7aec194fa1034005888c2b1845"

files = {
    "dataset": RUN / "stage3_capillary_dataset.npz",
    "weights": RUN / "pi_rnn_stage3_capillary_v9.weights.h5",
    "config": RUN / "pi_rnn_stage3_capillary_v9_config.json",
    "log": RUN / "stage3_capillary_v9_run.log",
    "conv_png": RUN / "training_convergence_stage3_capillary_v9.png",
    "conv_pdf": RUN / "training_convergence_stage3_capillary_v9.pdf",
    "diag1_png": RUN / "diagnostic_case1_symmetric_pec22.png",
    "diag1_pdf": RUN / "diagnostic_case1_symmetric_pec22.pdf",
    "diag2_png": RUN / "diagnostic_case2_asymmetric_pec100.png",
    "diag2_pdf": RUN / "diagnostic_case2_asymmetric_pec100.pdf",
}
slab = RUN / "stage3_slab.npz"

OUT = DRIVE / "provenance" / "stage3_capillary" / "V16E1B3B_REPRODUCTION_FREEZE"
OUT.mkdir(parents=True, exist_ok=True)
RESULTS = OUT / "V16E1B3B_Capillary_Reproduction_Results.json"
SUMMARY = OUT / "PAD_Stream_V16E1B3B_Summary.json"
HANDOFF = OUT / "V16E1B3B_Handoff.md"

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

def gate(name, ok):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        raise RuntimeError(name)

def atomic_json(path, obj):
    tmp = Path(str(path)+".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")
    os.replace(tmp, path)

print("="*110)
print("PAD-Stream V16E-1B3B — Capillary Reproduction Freeze / B4 Transition")
print("="*110)
print("NO TRAINING. NO RETUNING. NO DATASET REBUILD.")

gate("source_exists", SOURCE.exists())
gate("source_SHA_exact", sha256(SOURCE) == EXPECTED_SOURCE_SHA)

for k,p in files.items():
    gate(f"{k}_exists", p.exists())

log = files["log"].read_text(encoding="utf-8", errors="replace")
gate("epoch_2000_present", "[Stage 3] Epoch 2000" in log)

epoch = re.search(
    r"\[Stage 3\] Epoch 2000 \| Data ([0-9.eE+-]+) \| PDE ([0-9.eE+-]+).*?"
    r"BC_inj ([0-9.eE+-]+) \| BC_out ([0-9.eE+-]+) \| Anchor ([0-9.eE+-]+) "
    r"\| Mono ([0-9.eE+-]+) \| Mass ([0-9.eE+-]+) \| Curv ([0-9.eE+-]+)",
    log
)
gate("epoch_2000_metrics_parse", epoch is not None)

final_train = {
    "data": float(epoch.group(1)),
    "pde": float(epoch.group(2)),
    "bc_inj": float(epoch.group(3)),
    "bc_out": float(epoch.group(4)),
    "anchor": float(epoch.group(5)),
    "mono": float(epoch.group(6)),
    "mass": float(epoch.group(7)),
    "curv": float(epoch.group(8)),
}

sweep = {}
for pe in (10,22,50,100):
    m = re.search(rf"Pe_c =\s*{pe}\s*\| MAE = ([0-9.eE+-]+) \| max = ([0-9.eE+-]+)", log)
    gate(f"sweep_{pe}_present", m is not None)
    sweep[str(pe)] = {"mae": float(m.group(1)), "max_abs": float(m.group(2))}

r2s = [float(v) for v in re.findall(r"R²:\s*([0-9.]+)", log)]
gate("diagnostic_R2s_present", len(r2s) >= 2)

fan = re.search(r"Fan-region max\|dSw\| at inv_Pec = 0 vs Stage 1 analytical:\s*([0-9.eE+-]+)", log)
gate("sharp_limit_metric_present", fan is not None)

widths = {}
for inv in ("0.1000","0.0455","0.0200","0.0100","0.0050","0.0000"):
    m = re.search(rf"^\s*{re.escape(inv)}\s+([0-9.]+)\s*$", log, re.MULTILINE)
    if m:
        widths[inv] = float(m.group(1))

artifact_hashes = {k: sha256(p) for k,p in files.items()}

limitations = [
    "The clean first run did not contain stage3_slab.npz. In the final source, supplemental-slab generation/concatenation occurs only in the branch entered when stage3_capillary_dataset.npz already exists. This first source-faithful run therefore trained on the main dataset without the supplemental slab.",
    "The sharp-limit extrapolation did not monotonically sharpen toward inv_Pec=0; the 10–90 width increased toward the zero limit. This is documented and not repaired in B3B.",
    "High-Pe_c maximum pointwise errors are larger than the corresponding mean errors, although the Pe_c sweep MAE remains approximately 0.007–0.008."
]

results = {
    "milestone": MILESTONE,
    "status": "B3_CAPILLARY_REPRODUCTION_COMPLETE_WITH_DOCUMENTED_LIMITATIONS_B4_AUTHORIZED",
    "source_sha256": EXPECTED_SOURCE_SHA,
    "artifacts_sha256": artifact_hashes,
    "final_training_metrics": final_train,
    "Pe_c_accuracy_sweep": sweep,
    "diagnostic_R2": {
        "case1_symmetric_Pe22": r2s[-2],
        "case2_asymmetric_Pe100": r2s[-1],
    },
    "sharp_limit": {
        "width_10_90_by_inv_Pec": widths,
        "fan_region_max_abs_dSw_vs_stage1": float(fan.group(1)),
    },
    "supplemental_slab_present": slab.exists(),
    "limitations": limitations,
    "reproduction_complete": True,
    "B3_retraining_authorized": False,
    "B3_frozen_for_forward_progress": True,
    "B4_authorized": True,
    "next": "V16E-1B4 — full Buckley-Leverett solver reproduction/integration",
}
atomic_json(RESULTS, results)
results_sha = sha256(RESULTS)

summary = {
    "milestone": MILESTONE,
    "results_sha256": results_sha,
    "reproduction_complete": True,
    "B3_frozen_for_forward_progress": True,
    "B4_authorized": True,
    "next": results["next"],
}
atomic_json(SUMMARY, summary)
summary_sha = sha256(SUMMARY)

handoff = f'''# PAD-Stream V16E-1B3B

## Status
B3 capillary source-faithful reproduction completed and frozen for forward progress.

## Headline results
- 2000 training epochs completed.
- Final data loss: {final_train["data"]:.6e}
- Final PDE loss: {final_train["pde"]:.6e}
- Case 1 symmetric Pe_c=22 R²: {r2s[-2]:.6f}
- Case 2 asymmetric Pe_c=100 R²: {r2s[-1]:.6f}
- Pe_c sweep MAE: 10={sweep["10"]["mae"]:.6e}, 22={sweep["22"]["mae"]:.6e}, 50={sweep["50"]["mae"]:.6e}, 100={sweep["100"]["mae"]:.6e}

## Documented limitations
1. Supplemental V7 slab was absent in the clean first-run execution because of the final source's control-flow ordering.
2. The sharp-limit extrapolation did not show monotonic sharpening toward inv_Pec=0.
3. High-Pe_c pointwise maximum errors remain larger than mean errors.

## Forward decision
No B3 retraining or new B3 branch is authorized here.
B3 is frozen as a completed reproduction with documented limitations.
B4 full Buckley-Leverett work is authorized.

Results SHA-256: {results_sha}
Summary SHA-256: {summary_sha}

## Next
V16E-1B4 — full Buckley-Leverett solver reproduction/integration
'''
HANDOFF.write_text(handoff, encoding="utf-8")
handoff_sha = sha256(HANDOFF)

print()
print("="*110)
print("B3B FREEZE COMPLETE")
print("="*110)
print("Reproduction complete          : YES")
print("Supplemental slab included     :", "YES" if slab.exists() else "NO")
print("Limitations documented         : YES")
print("B3 retraining authorized       : NO")
print("B3 frozen for forward progress : YES")
print("B4 authorized                  : YES")
print("Results SHA                    :", results_sha)
print("Summary SHA                    :", summary_sha)
print("Handoff SHA                    :", handoff_sha)
print("NEXT: V16E-1B4 — full Buckley-Leverett solver reproduction/integration")

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import subprocess
from pathlib import Path
from typing import Any

M = "POSTV16-AV4-PIVOT-P3-R1-R7-R10"
BRANCH = "postv16-av4-pivot"
PARENT = "fad8dde93d6418c9e9fd09ec942bde394b0f6916"

R9 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R9_Day395_to_Day400_SeventhObservation_Pilot.py"
R9_BLOB = "0e50a7aa55881ae10dec22182d4b6a2698c88a48"

DAY385_TOPOLOGY_SOURCE_SHA = "18a98bd27661fd1f2464f5e46e74389c794e2bdfc58a68541ee381a526d29988"
DAY400_STATE_SHA = "9630449981429d90f3265dad60875217873000061a294b2bf60bbe806cb5c5d4"
DAY400_DIAGNOSTIC_SHA = "2e772ca70526a2c64bc0a84f3fbc42c2540593e6b7d79dc74787e33b52c0ac42"
DAY400_ACCEPTED_STEPS = 951

SOURCE_STATUS = "AV4PIVOTP3R1R7R9_XY2_DAY395_TO_DAY400_SEVENTH_OBSERVATION_PILOT_EXACT_FLOW_DIAGNOSTIC_PASS"
SOURCE_CLASS = "P3R1_R7_XY2_DAY395_TO_DAY400_SEVENTH_OBSERVATION_TRANSPORT_AND_EXACT_FLOW_DIAGNOSTIC_CERTIFIED_NO_GENERIC_STAGE2_FALLBACK_DAY405_PILOT_AUTHORIZED"


class TransformError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    actual = text.count(old)
    if actual != expected:
        raise TransformError(f"replacement_count:{old[:120]!r}:expected={expected}:actual={actual}")
    return text.replace(old, new)


def load_r9_module(root: Path):
    p = root / R9
    if not p.is_file():
        raise TransformError(f"R9_runner_missing:{p}")
    blob = gt(root, "hash-object", str(p))
    if blob != R9_BLOB:
        raise TransformError(f"R9_runner_blob:{blob}:{R9_BLOB}")
    spec = importlib.util.spec_from_file_location("pad_stream_r7r9_authority", p)
    if spec is None or spec.loader is None:
        raise TransformError("R9_import_spec_failed")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def advance_source(src: str) -> str:
    # src is the already-certified R7-R9 generated physical runner.
    replacements = [
        ('M = "POSTV16-AV4-PIVOT-P3-R1-R7-R9"',
         'M = "POSTV16-AV4-PIVOT-P3-R1-R7-R10"'),
        ('NAME = "Restart-Safe XY2 Day395-to-Day400 Seventh-Observation Pilot + Exact Flow Diagnostic"',
         'NAME = "Restart-Safe XY2 Day400-to-Day405 Eighth-Observation Pilot + Exact Flow Diagnostic"'),
        ('PASS = "AV4PIVOTP3R1R7R9_XY2_DAY395_TO_DAY400_SEVENTH_OBSERVATION_PILOT_EXACT_FLOW_DIAGNOSTIC_PASS"',
         'PASS = "AV4PIVOTP3R1R7R10_XY2_DAY400_TO_DAY405_EIGHTH_OBSERVATION_PILOT_EXACT_FLOW_DIAGNOSTIC_PASS"'),
        ('BLOCK = "AV4PIVOTP3R1R7R9_TECHNICAL_OR_AUTHORITY_BLOCK"',
         'BLOCK = "AV4PIVOTP3R1R7R10_TECHNICAL_OR_AUTHORITY_BLOCK"'),
        ('PARENT = "ad803a56bfb4b5871b75eefdfea0f9dd6e19a517"',
         f'PARENT = "{PARENT}"'),

        # Immediate source becomes certified R7-R9 Day400.
        ('R7R6 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R8_R3_Corrected_CheckpointLineage_and_Day390_to_Day395_SixthObservation_Pilot.py"',
         f'R7R6 = "{R9}"'),
        ('R7R6_BLOB = "99d309be8e06afcfdf9fd146d478afab56c97fa2"',
         f'R7R6_BLOB = "{R9_BLOB}"'),
        ('R7R6_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R7_R8_R3_XY2_Day390_to_Day395_SixthObservation_Pilot_and_Exact_Flow_Diagnostic"',
         'R7R6_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R7_R9_XY2_Day395_to_Day400_SeventhObservation_Pilot_and_Exact_Flow_Diagnostic"'),
        ('R7R6_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R8_R3_Summary.json"',
         'R7R6_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R9_Summary.json"'),
        ('R7R6_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R7_R8_R3_Decision_Contract.json"',
         'R7R6_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R7_R9_Decision_Contract.json"'),
        ('R7R6_STATE = "POSTV16_AV4_PIVOT_P3_R1_R7_R8_R3_Day0395_Accepted_Dense_State.npz"',
         'R7R6_STATE = "POSTV16_AV4_PIVOT_P3_R1_R7_R9_Day0400_Accepted_Dense_State.npz"'),
        ('R7R6_DIAGNOSTIC = "POSTV16_AV4_PIVOT_P3_R1_R7_R8_R3_Day0395_Exact_Flow_Diagnostic.npz"',
         'R7R6_DIAGNOSTIC = "POSTV16_AV4_PIVOT_P3_R1_R7_R9_Day0400_Exact_Flow_Diagnostic.npz"'),
        ('R7R6_AUDIT = "POSTV16_AV4_PIVOT_P3_R1_R7_R8_R3_Atomic_Step_Audit.csv"',
         'R7R6_AUDIT = "POSTV16_AV4_PIVOT_P3_R1_R7_R9_Atomic_Step_Audit.csv"'),
        ('R7R6_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R7_R8_R3_Artifact_Manifest.csv"',
         'R7R6_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R7_R9_Artifact_Manifest.csv"'),
        ('R7R6_STATUS = "AV4PIVOTP3R1R7R8R3_XY2_DAY390_TO_DAY395_SIXTH_OBSERVATION_PILOT_EXACT_FLOW_DIAGNOSTIC_PASS"',
         f'R7R6_STATUS = "{SOURCE_STATUS}"'),
        ('R7R6_CLASS = "P3R1_R7_XY2_DAY390_TO_DAY395_SIXTH_OBSERVATION_TRANSPORT_AND_EXACT_FLOW_DIAGNOSTIC_CERTIFIED_NO_GENERIC_STAGE2_FALLBACK_DAY400_PILOT_AUTHORIZED"',
         f'R7R6_CLASS = "{SOURCE_CLASS}"'),
        ('R7R6_STATE_SHA = "15a59e11db310a0eadc628dc8075d3bf58b19b97bf0648f94566682bb25f77e5"',
         f'R7R6_STATE_SHA = "{DAY400_STATE_SHA}"'),
        ('R7R6_DIAGNOSTIC_SHA = "83a4911575266aa8380a33c94849061b91aa055da203f35455b0566fff8413a8"',
         f'R7R6_DIAGNOSTIC_SHA = "{DAY400_DIAGNOSTIC_SHA}"'),
        ('R7R6_SOURCE_DAY = 395.0', 'R7R6_SOURCE_DAY = 400.0'),
        ('R7R6_ACCEPTED_STEPS = 816', f'R7R6_ACCEPTED_STEPS = {DAY400_ACCEPTED_STEPS}'),

        # New formal output.
        ('OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R7_R9"',
         'OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R7_R10"'),
        ('OUT_REL = BASE_AV4 / (OUT_TOKEN + "_XY2_Day395_to_Day400_SeventhObservation_Pilot_and_Exact_Flow_Diagnostic")',
         'OUT_REL = BASE_AV4 / (OUT_TOKEN + "_XY2_Day400_to_Day405_EighthObservation_Pilot_and_Exact_Flow_Diagnostic")'),
        ('FINAL_STATE = f"{OUT_TOKEN}_Day0400_Accepted_Dense_State.npz"',
         'FINAL_STATE = f"{OUT_TOKEN}_Day0405_Accepted_Dense_State.npz"'),
        ('FLOW_DIAGNOSTIC = f"{OUT_TOKEN}_Day0400_Exact_Flow_Diagnostic.npz"',
         'FLOW_DIAGNOSTIC = f"{OUT_TOKEN}_Day0405_Exact_Flow_Diagnostic.npz"'),
        ('DIAGNOSTIC_METRICS = f"{OUT_TOKEN}_Day0400_Exact_Flow_Diagnostic_Metrics.json"',
         'DIAGNOSTIC_METRICS = f"{OUT_TOKEN}_Day0405_Exact_Flow_Diagnostic_Metrics.json"'),
        ('TARGET_DAY = 400.0', 'TARGET_DAY = 405.0'),

        # Immediate-source summary / decision bindings now point to R7-R9 Day400.
        ('r7r6sum.get("Day395_positive_XY1_terminal_edge_count")',
         'r7r6sum.get("Day400_positive_XY1_terminal_edge_count")'),
        ('r7r6sum.get("Day395_positive_XY2_terminal_edge_count")',
         'r7r6sum.get("Day400_positive_XY2_terminal_edge_count")'),
        ('r7r6sum.get("Day395_state_sha256")',
         'r7r6sum.get("Day400_state_sha256")'),
        ('r7r6sum.get("Day395_diagnostic_sha256")',
         'r7r6sum.get("Day400_diagnostic_sha256")'),
        ('r7r6dec.get("Day395_to_Day395_repaired_pilot_authorized")',
         'r7r6dec.get("Day400_to_Day405_repaired_pilot_authorized")'),
        ('r7r6dec.get("Day395_exact_diagnostic_is_one_shot_no_feedback")',
         'r7r6dec.get("Day400_exact_diagnostic_is_one_shot_no_feedback")'),
    ]

    out = src
    for old, new in replacements:
        if old in {
            'r7r6sum.get("Day395_state_sha256")',
            'r7r6sum.get("Day395_diagnostic_sha256")',
        }:
            out = replace_exact(out, old, new, expected=2)
        else:
            out = replace_exact(out, old, new, expected=1)

    # Dynamic checkpoint lineage follows the immediate physical source Day400.
    old_key = '"source_R7R8R3_Day395_state_sha256"'
    if old_key not in out:
        raise TransformError("missing_Day395_checkpoint_source_key")
    out = out.replace(old_key, '"source_R7R9_Day400_state_sha256"')

    # Rebuild classification cleanly: R7-R10 certifies Day405 and authorizes only Day405->410.
    classify_start = out.index("def classify(")
    selftest_start = out.index("def selftest()", classify_start)
    new_classify = """def classify(day405_reached: bool, diagnostic_passed: bool, generic_fallback_count: int) -> tuple[str, str, bool]:
    if day405_reached and diagnostic_passed and generic_fallback_count == 0:
        return (
            "P3R1_R7_XY2_DAY400_TO_DAY405_EIGHTH_OBSERVATION_TRANSPORT_AND_EXACT_FLOW_DIAGNOSTIC_CERTIFIED_NO_GENERIC_STAGE2_FALLBACK_DAY410_PILOT_AUTHORIZED",
            "Day405 is certified. Preserve this state for the read-only 3D visualization milestone. The next transport extension, if resumed, is Day405-to-Day410 under the same frozen exact+XY1+XY2 recurrent semantics and one-shot exact diagnostic; keep the full Day365-to500 sweep and P4 locked.",
            True,
        )
    if day405_reached and diagnostic_passed:
        return (
            "P3R1_R7_XY2_DAY400_TO_DAY405_EIGHTH_OBSERVATION_CERTIFIED_BUT_GENERIC_STAGE2_FALLBACK_USED_RUNTIME_PATH_REQUIRES_LOCALIZATION_BEFORE_EXTENSION",
            "Localize generic exact+XY1+XY2 Stage2 fallback usage before extending beyond Day405; keep the full Day365-to500 sweep and P4 locked.",
            False,
        )
    return (
        "P3R1_R7_XY2_DAY400_TO_DAY405_EIGHTH_OBSERVATION_PILOT_NOT_CERTIFIED_NO_EXTENSION_AUTHORIZED",
        "Use the restart-safe externalized-topology checkpoint, atomic-step, and diagnostic evidence to diagnose the first unresolved condition; do not extend beyond Day405.",
        False,
    )

"""
    out = out[:classify_start] + new_classify + out[selftest_start:]

    # Rebuild structural self-test for this target.
    selftest_start = out.index("def selftest()")
    main_start = out.index("def main(", selftest_start)
    new_selftest = f"""def selftest() -> None:
    c, _, ok = classify(True, True, 0)
    assert "DAY410_PILOT_AUTHORIZED" in c and ok
    c, _, ok = classify(True, True, 1)
    assert "GENERIC_STAGE2_FALLBACK_USED" in c and not ok
    assert TARGET_DAY == 405.0
    assert MAX_RETRIES == 8 and RETRY_FACTOR == 0.5
    assert PARENT == "{PARENT}"
    assert R7R6_STATE_SHA == "{DAY400_STATE_SHA}"
    print("POSTV16 AV4 PIVOT P3-R1-R7-R10 structural self-test: PASS")


"""
    out = out[:selftest_start] + new_selftest + out[main_start:]

    # Banner / repository authority labels.
    out = replace_exact(
        out,
        'print("POSTV16-AV4-PIVOT-P3-R1-R7-R9 — XY2 DAY395-TO-DAY400 SEVENTH-OBSERVATION PILOT + EXACT FLOW DIAGNOSTIC", flush=True)',
        'print("POSTV16-AV4-PIVOT-P3-R1-R7-R10 — XY2 DAY400-TO-DAY405 EIGHTH-OBSERVATION PILOT + EXACT FLOW DIAGNOSTIC", flush=True)',
    )
    out = replace_exact(
        out,
        'print("START FROM THE FORMAL R7-R8-R3 DAY395 SCHEMA-V2 ACCEPTED STATE. CONTINUE TO DAY400 ONLY. PRESERVE THE CANONICAL SCIPY SOLVER AND THE O1-R2-CERTIFIED EXTERNALIZED-TOPOLOGY CHECKPOINT OPTIMIZATION.", flush=True)',
        'print("START FROM THE FORMAL R7-R9 DAY400 SCHEMA-V2 ACCEPTED STATE. CONTINUE TO DAY405 ONLY. PRESERVE THE CANONICAL SCIPY SOLVER AND THE O1-R2-CERTIFIED EXTERNALIZED-TOPOLOGY CHECKPOINT OPTIMIZATION.", flush=True)',
    )
    out = replace_exact(out, 'gate("parent_is_R7R8R3_commit"', 'gate("parent_is_R7R9_commit"')

    # Authority stage/gate labels.
    out = out.replace('stage = "R7R8R3_Day395_authority"', 'stage = "R7R9_Day400_authority"', 1)
    out = out.replace("R7R8R3_Day395_state_SHA_exact", "R7R9_Day400_state_SHA_exact", 1)
    out = out.replace("R7R8R3_Day395_diagnostic_SHA_exact", "R7R9_Day400_diagnostic_SHA_exact", 1)
    out = out.replace("R7R8R3_Day395_state_summary_SHA_exact", "R7R9_Day400_state_summary_SHA_exact", 1)
    out = out.replace("R7R8R3_Day395_diagnostic_summary_SHA_exact", "R7R9_Day400_diagnostic_summary_SHA_exact", 1)
    out = out.replace("R7R8R3_Day400_authorized", "R7R9_Day405_authorized", 1)
    out = out.replace("R7R8R3_diagnostic_one_shot_no_feedback", "R7R9_diagnostic_one_shot_no_feedback", 1)
    out = out.replace("R7R8R3_source_state_schema2", "R7R9_source_state_schema2", 1)
    out = out.replace("R7R8R3_source_root_checkpoint_exact", "R7R9_source_root_checkpoint_exact", 1)
    out = out.replace("physical_day_Day395_exact", "physical_day_Day400_exact", 1)
    out = out.replace("accepted_steps_Day395_exact", "accepted_steps_Day400_exact", 1)
    out = out.replace("source_Day395_positive_XY1_count_exact", "source_Day400_positive_XY1_count_exact", 1)
    out = out.replace("source_Day395_positive_XY2_count_exact", "source_Day400_positive_XY2_count_exact", 1)
    out = out.replace("Day395_source_mass_ledger_closes", "Day400_source_mass_ledger_closes", 1)
    out = out.replace("# R7-R8-R3 Day395 state is authoritative schema-v2 support.",
                      "# R7-R9 Day400 state is authoritative schema-v2 support.", 1)

    # Exact Day405 diagnostic labels only.
    d0 = out.index("        def run_exact_diagnostic")
    d1 = out.index("        # Resume an R7-R9 dynamic checkpoint", d0)
    diag = out[d0:d1].replace("Day400", "Day405").replace("day400", "day405")
    out = out[:d0] + diag + out[d1:]

    # Resume/seed from Day400; topology remains Day385.
    r0 = out.index("        # Resume an R7-R9 dynamic checkpoint")
    r1 = out.index("        while current_time < TARGET_DAY", r0)
    resume = out[r0:r1]
    resume = resume.replace("Resume an R7-R9 dynamic checkpoint", "Resume an R7-R10 dynamic checkpoint")
    resume = resume.replace("[R7-R9 RESUME]", "[R7-R10 RESUME]")
    resume = resume.replace("resume_checkpoint_Day395_source_exact", "resume_checkpoint_Day400_source_exact")
    resume = resume.replace("Day395_schema2_seed_time_exact", "Day400_schema2_seed_time_exact")
    resume = resume.replace("Day395_schema2_seed_steps_exact", "Day400_schema2_seed_steps_exact")
    resume = resume.replace("[DAY395 SCHEMA-V2 STATE SEED]", "[DAY400 SCHEMA-V2 STATE SEED]")
    out = out[:r0] + resume + out[r1:]

    # Publication: old destination Day400 -> Day405; old source Day395 -> Day400.
    c0 = out.index('        stage = "Day400_pilot_closure"')
    c1 = out.index("    except Exception as exc:", c0)
    closure = out[c0:c1]
    closure = closure.replace("Day400", "Day405").replace("day400", "day405")
    closure = closure.replace("Day395", "Day400").replace("day395", "day400")

    # Undo source-lineage over-renaming caused by destination replacement.
    closure = closure.replace('"source_R7R9_Day405_state_sha256"',
                              '"source_R7R9_Day400_state_sha256"')
    closure = closure.replace('"Day405_to_Day405_repaired_pilot_authorized"',
                              '"Day405_to_Day410_repaired_pilot_authorized"')

    # Make immediate-source naming explicit.
    closure = closure.replace('"R7R8R3_status_bound"', '"R7R9_status_bound"')
    closure = closure.replace('"R7R8R3_classification_bound"', '"R7R9_classification_bound"')
    closure = closure.replace('"R7R8R3_Day400_state_must_be_preserved"', '"R7R9_Day400_state_must_be_preserved"')
    closure = closure.replace('"R7R8R3_Day400_state_sha256"', '"R7R9_Day400_state_sha256"')
    closure = closure.replace('"R7R8R3_Day400_accepted_state_is_segment_start_authority"',
                              '"R7R9_Day400_accepted_state_is_segment_start_authority"')
    closure = closure.replace('"canonical_R7R8R3_SciPy_solver_preserved"',
                              '"canonical_R7R9_SciPy_solver_preserved"')
    closure = closure.replace('"repository_parent_R7R8R3_commit"',
                              '"repository_parent_R7R9_commit"')

    out = out[:c0] + closure + out[c1:]

    # BLOCK forward authority must advance correctly.
    out = out.replace('"Day400_to_Day405_repaired_pilot_authorized": False',
                      '"Day405_to_Day410_repaired_pilot_authorized": False', 1)

    # Semantic firewall: source physical state = Day400; topology source remains Day385.
    forbidden = [
        'r7r6sum.get("Day395_state_sha256")',
        'r7r6sum.get("Day395_diagnostic_sha256")',
        'r7r6dec.get("Day395_to_Day395_repaired_pilot_authorized")',
        'r7r6dec.get("Day395_exact_diagnostic_is_one_shot_no_feedback")',
        '"source_R7R9_Day405_state_sha256"',
        '"Day405_to_Day405_repaired_pilot_authorized"',
    ]
    for stale in forbidden:
        if stale in out:
            raise TransformError(f"stale_or_mislabeled_binding:{stale}")

    required = [
        f'R7R6_STATE_SHA = "{DAY400_STATE_SHA}"',
        f'R7R6_DIAGNOSTIC_SHA = "{DAY400_DIAGNOSTIC_SHA}"',
        'r7r6sum.get("Day400_state_sha256")',
        'r7r6sum.get("Day400_diagnostic_sha256")',
        'r7r6dec.get("Day400_to_Day405_repaired_pilot_authorized")',
        'r7r6dec.get("Day400_exact_diagnostic_is_one_shot_no_feedback")',
        '"source_R7R9_Day400_state_sha256"',
        f'"support_topology_source_state_sha256": np.asarray("{DAY385_TOPOLOGY_SOURCE_SHA}")',
        f'meta.get("support_topology_source_state_sha256") == "{DAY385_TOPOLOGY_SOURCE_SHA}"',
        'OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R7_R10"',
        'TARGET_DAY = 405.0',
        '"Day405_to_Day410_repaired_pilot_authorized"',
    ]
    for expected in required:
        if expected not in out:
            raise TransformError(f"missing_R7R10_semantic_binding:{expected}")

    return out


def build_source(root: Path) -> str:
    r9 = load_r9_module(root)
    if not hasattr(r9, "build_source"):
        raise TransformError("R9_build_source_missing")
    r9_source = r9.build_source(root)
    compile(r9_source, "<R7-R9-derived-authority>", "exec")
    return advance_source(r9_source)


def load_advanced(root: Path) -> dict[str, Any]:
    src = build_source(root)
    code = compile(src, f"<derived:{M}>", "exec")
    ns: dict[str, Any] = {"__name__": "pad_stream_r7r10_derived", "__file__": str(root / R9)}
    exec(code, ns, ns)
    return ns


def selftest(root: Path | None = None) -> None:
    assert PARENT == "fad8dde93d6418c9e9fd09ec942bde394b0f6916"
    assert R9_BLOB == "0e50a7aa55881ae10dec22182d4b6a2698c88a48"
    assert DAY400_STATE_SHA == "9630449981429d90f3265dad60875217873000061a294b2bf60bbe806cb5c5d4"
    assert DAY400_DIAGNOSTIC_SHA == "2e772ca70526a2c64bc0a84f3fbc42c2540593e6b7d79dc74787e33b52c0ac42"
    assert DAY400_ACCEPTED_STEPS == 951
    if root is not None and (root / R9).is_file():
        ns = load_advanced(root)
        ns["selftest"]()
    print("POSTV16 AV4 P3-R1-R7-R10 derived-runner self-test: PASS")


def main(project_root: Path, drive_root: Path, time_limit_seconds: float) -> int:
    root = project_root.resolve()
    if gt(root, "branch", "--show-current") != BRANCH:
        raise SystemExit(f"wrong_branch:{gt(root, 'branch', '--show-current')}")
    if gt(root, "rev-parse", "HEAD^") != PARENT:
        raise SystemExit(f"wrong_parent:{gt(root, 'rev-parse', 'HEAD^')}:{PARENT}")
    ns = load_advanced(root)
    return int(ns["main"](root, drive_root.resolve(), float(time_limit_seconds)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--time-limit-seconds", type=float, default=300.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest(args.project_root.resolve())
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root, args.time_limit_seconds))

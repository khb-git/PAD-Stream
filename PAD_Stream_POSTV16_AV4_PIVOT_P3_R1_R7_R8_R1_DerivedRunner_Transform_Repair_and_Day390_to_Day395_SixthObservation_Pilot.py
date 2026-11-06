#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

M = "POSTV16-AV4-PIVOT-P3-R1-R7-R8-R1"
BRANCH = "postv16-av4-pivot"
PARENT = "1bd95433fe9c5959b9d8428fa1ef72c5c2dee640"

TEMPLATE = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R7_Day385_to_Day390_FifthObservation_Pilot.py"
TEMPLATE_BLOB = "1e5548ae40edeeaeac142dce42a02c764ed0216d"

DAY385_TOPOLOGY_SOURCE_SHA = "18a98bd27661fd1f2464f5e46e74389c794e2bdfc58a68541ee381a526d29988"
DAY390_STATE_SHA = "83e26d77f5f853412b817c37dcd4d3958ba4469bbd14c10a8467a256b52c33ee"
DAY390_DIAGNOSTIC_SHA = "a5e2271830649b37e0de38459a9ead58fb79d4c20c185fee1d3390e9e749c9dc"

SOURCE_R7R7_STATUS = "AV4PIVOTP3R1R7R7_XY2_DAY385_TO_DAY390_FIFTH_OBSERVATION_PILOT_EXACT_FLOW_DIAGNOSTIC_PASS"
SOURCE_R7R7_CLASS = "P3R1_R7_XY2_DAY385_TO_DAY390_FIFTH_OBSERVATION_TRANSPORT_AND_EXACT_FLOW_DIAGNOSTIC_CERTIFIED_NO_GENERIC_STAGE2_FALLBACK_DAY395_PILOT_AUTHORIZED"
ORIGINAL_R7R8_WRAPPER = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R8_Day390_to_Day395_SixthObservation_Pilot.py"
ORIGINAL_R7R8_WRAPPER_BLOB = "d3c149abb08af49e4a96e1b8599f4618b97583c4"

class TransformError(RuntimeError):
    pass

def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def replace_exact(text: str, old: str, new: str, count: int = 1) -> str:
    actual = text.count(old)
    if actual != count:
        raise TransformError(f"replacement_count:{old[:100]!r}:expected={count}:actual={actual}")
    return text.replace(old, new, count)

def transform_template(src: str) -> str:
    replacements = [
        ('M = "POSTV16-AV4-PIVOT-P3-R1-R7-R7"', 'M = "POSTV16-AV4-PIVOT-P3-R1-R7-R8"'),
        ('NAME = "Restart-Safe XY2 Day385-to-Day390 Fifth-Observation Pilot + Exact Flow Diagnostic"',
         'NAME = "Restart-Safe XY2 Day390-to-Day395 Sixth-Observation Pilot + Exact Flow Diagnostic"'),
        ('PASS = "AV4PIVOTP3R1R7R7_XY2_DAY385_TO_DAY390_FIFTH_OBSERVATION_PILOT_EXACT_FLOW_DIAGNOSTIC_PASS"',
         'PASS = "AV4PIVOTP3R1R7R8_XY2_DAY390_TO_DAY395_SIXTH_OBSERVATION_PILOT_EXACT_FLOW_DIAGNOSTIC_PASS"'),
        ('BLOCK = "AV4PIVOTP3R1R7R7_TECHNICAL_OR_AUTHORITY_BLOCK"',
         'BLOCK = "AV4PIVOTP3R1R7R8_TECHNICAL_OR_AUTHORITY_BLOCK"'),
        ('PARENT = "0180d56dbe5801b7a95aa548bd9551f6b22669ba"', f'PARENT = "{PARENT}"'),

        ('R7R6 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R6_Day380_to_Day385_FourthObservation_Pilot.py"',
         f'R7R6 = "{TEMPLATE}"'),
        ('R7R6_BLOB = "5f77419b363f885f012b9195cc49f041282c211b"', f'R7R6_BLOB = "{TEMPLATE_BLOB}"'),
        ('R7R6_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R7_R6_XY2_Day380_to_Day385_FourthObservation_Pilot_and_Exact_Flow_Diagnostic"',
         'R7R6_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R7_R7_XY2_Day385_to_Day390_FifthObservation_Pilot_and_Exact_Flow_Diagnostic"'),
        ('R7R6_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R6_Summary.json"',
         'R7R6_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R7_Summary.json"'),
        ('R7R6_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R7_R6_Decision_Contract.json"',
         'R7R6_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R7_R7_Decision_Contract.json"'),
        ('R7R6_STATE = "POSTV16_AV4_PIVOT_P3_R1_R7_R6_Day0385_Accepted_Dense_State.npz"',
         'R7R6_STATE = "POSTV16_AV4_PIVOT_P3_R1_R7_R7_Day0390_Accepted_Dense_State.npz"'),
        ('R7R6_DIAGNOSTIC = "POSTV16_AV4_PIVOT_P3_R1_R7_R6_Day0385_Exact_Flow_Diagnostic.npz"',
         'R7R6_DIAGNOSTIC = "POSTV16_AV4_PIVOT_P3_R1_R7_R7_Day0390_Exact_Flow_Diagnostic.npz"'),
        ('R7R6_AUDIT = "POSTV16_AV4_PIVOT_P3_R1_R7_R6_Atomic_Step_Audit.csv"',
         'R7R6_AUDIT = "POSTV16_AV4_PIVOT_P3_R1_R7_R7_Atomic_Step_Audit.csv"'),
        ('R7R6_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R7_R6_Artifact_Manifest.csv"',
         'R7R6_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R7_R7_Artifact_Manifest.csv"'),
        ('R7R6_STATUS = "AV4PIVOTP3R1R7R6_XY2_DAY380_TO_DAY385_FOURTH_OBSERVATION_PILOT_EXACT_FLOW_DIAGNOSTIC_PASS"',
         f'R7R6_STATUS = "{SOURCE_R7R7_STATUS}"'),
        ('R7R6_CLASS = "P3R1_R7_XY2_DAY380_TO_DAY385_FOURTH_OBSERVATION_TRANSPORT_AND_EXACT_FLOW_DIAGNOSTIC_CERTIFIED_NO_GENERIC_STAGE2_FALLBACK_DAY390_PILOT_AUTHORIZED"',
         f'R7R6_CLASS = "{SOURCE_R7R7_CLASS}"'),
        ('R7R6_STATE_SHA = "18a98bd27661fd1f2464f5e46e74389c794e2bdfc58a68541ee381a526d29988"',
         f'R7R6_STATE_SHA = "{DAY390_STATE_SHA}"'),
        ('R7R6_DIAGNOSTIC_SHA = "3ec8d7b6a7877847501396478d5757761ed54a33de1358a2cc157859daba1c7d"',
         f'R7R6_DIAGNOSTIC_SHA = "{DAY390_DIAGNOSTIC_SHA}"'),
        ('R7R6_SOURCE_DAY = 385.0', 'R7R6_SOURCE_DAY = 390.0'),
        ('R7R6_ACCEPTED_STEPS = 546', 'R7R6_ACCEPTED_STEPS = 681'),

        ('OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R7_R7"', 'OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R7_R8"'),
        ('OUT_REL = BASE_AV4 / (OUT_TOKEN + "_XY2_Day385_to_Day390_FifthObservation_Pilot_and_Exact_Flow_Diagnostic")',
         'OUT_REL = BASE_AV4 / (OUT_TOKEN + "_XY2_Day390_to_Day395_SixthObservation_Pilot_and_Exact_Flow_Diagnostic")'),
        ('FINAL_STATE = f"{OUT_TOKEN}_Day0390_Accepted_Dense_State.npz"',
         'FINAL_STATE = f"{OUT_TOKEN}_Day0395_Accepted_Dense_State.npz"'),
        ('FLOW_DIAGNOSTIC = f"{OUT_TOKEN}_Day0390_Exact_Flow_Diagnostic.npz"',
         'FLOW_DIAGNOSTIC = f"{OUT_TOKEN}_Day0395_Exact_Flow_Diagnostic.npz"'),
        ('DIAGNOSTIC_METRICS = f"{OUT_TOKEN}_Day0390_Exact_Flow_Diagnostic_Metrics.json"',
         'DIAGNOSTIC_METRICS = f"{OUT_TOKEN}_Day0395_Exact_Flow_Diagnostic_Metrics.json"'),
        ('TARGET_DAY = 390.0', 'TARGET_DAY = 395.0'),

        ('r7r6sum.get("Day385_positive_XY1_terminal_edge_count")',
         'r7r6sum.get("Day390_positive_XY1_terminal_edge_count")'),
        ('r7r6sum.get("Day385_positive_XY2_terminal_edge_count")',
         'r7r6sum.get("Day390_positive_XY2_terminal_edge_count")'),

        ('o1r2cp.get("topology_source_state_sha256") == R7R6_STATE_SHA',
         f'o1r2cp.get("topology_source_state_sha256") == "{DAY385_TOPOLOGY_SOURCE_SHA}"'),

        ('"source_R7R6_Day385_state_sha256"', '"source_R7R7_Day390_state_sha256"'),
        ('resume_checkpoint_Day385_source_exact', 'resume_checkpoint_Day390_source_exact'),
        ('Day385_schema2_seed_time_exact', 'Day390_schema2_seed_time_exact'),
        ('Day385_schema2_seed_steps_exact', 'Day390_schema2_seed_steps_exact'),
        ('[DAY385 SCHEMA-V2 STATE SEED]', '[DAY390 SCHEMA-V2 STATE SEED]'),
    ]
    out = src
    for old, new in replacements:
        if old == '"source_R7R6_Day385_state_sha256"':
            actual = out.count(old)
            if actual != 5:
                raise TransformError(f"checkpoint_source_key_count:expected=5:actual={actual}")
            out = out.replace(old, new)
        else:
            out = replace_exact(out, old, new, 1)

    classify_start = out.index("def classify(")
    selftest_start = out.index("def selftest()", classify_start)
    new_classify = """def classify(day395_reached: bool, diagnostic_passed: bool, generic_fallback_count: int) -> tuple[str, str, bool]:
    if day395_reached and diagnostic_passed and generic_fallback_count == 0:
        return (
            "P3R1_R7_XY2_DAY390_TO_DAY395_SIXTH_OBSERVATION_TRANSPORT_AND_EXACT_FLOW_DIAGNOSTIC_CERTIFIED_NO_GENERIC_STAGE2_FALLBACK_DAY400_PILOT_AUTHORIZED",
            "Execute a Day395-to-Day400 seventh-observation pilot from the certified Day395 schema-v2 state using the same frozen exact+XY1+XY2 recurrent semantics and one-shot exact diagnostic; preserve the certified externalized-topology checkpoint format and keep the full Day365-to500 sweep and P4 locked.",
            True,
        )
    if day395_reached and diagnostic_passed:
        return (
            "P3R1_R7_XY2_DAY390_TO_DAY395_SIXTH_OBSERVATION_CERTIFIED_BUT_GENERIC_STAGE2_FALLBACK_USED_RUNTIME_PATH_REQUIRES_LOCALIZATION_BEFORE_EXTENSION",
            "Localize the generic exact+XY1+XY2 Stage2 fallback usage before extending beyond Day395; keep the full Day365-to500 sweep and P4 locked.",
            False,
        )
    return (
        "P3R1_R7_XY2_DAY390_TO_DAY395_SIXTH_OBSERVATION_PILOT_NOT_CERTIFIED_NO_EXTENSION_AUTHORIZED",
        "Use the restart-safe externalized-topology checkpoint, atomic-step, and diagnostic evidence to diagnose the first unresolved condition; do not extend beyond Day395.",
        False,
    )

"""
    out = out[:classify_start] + new_classify + out[selftest_start:]

    selftest_start = out.index("def selftest()")
    main_start = out.index("def main(", selftest_start)
    new_selftest = f"""def selftest() -> None:
    c, _, ok = classify(True, True, 0)
    assert "DAY400_PILOT_AUTHORIZED" in c and ok
    c, _, ok = classify(True, True, 1)
    assert "GENERIC_STAGE2_FALLBACK_USED" in c and not ok
    assert TARGET_DAY == 395.0
    assert MAX_RETRIES == 8 and RETRY_FACTOR == 0.5
    assert PARENT == "{PARENT}"
    assert R7R6_STATE_SHA == "{DAY390_STATE_SHA}"
    print("POSTV16 AV4 PIVOT P3-R1-R7-R8 structural self-test: PASS")


"""
    out = out[:selftest_start] + new_selftest + out[main_start:]

    out = replace_exact(
        out,
        'print("POSTV16-AV4-PIVOT-P3-R1-R7-R7 — XY2 DAY385-TO-DAY390 FIFTH-OBSERVATION PILOT + EXACT FLOW DIAGNOSTIC", flush=True)',
        'print("POSTV16-AV4-PIVOT-P3-R1-R7-R8 — XY2 DAY390-TO-DAY395 SIXTH-OBSERVATION PILOT + EXACT FLOW DIAGNOSTIC", flush=True)',
        1,
    )
    out = replace_exact(
        out,
        'print("START FROM THE FORMAL R7-R6 DAY385 SCHEMA-V2 ACCEPTED STATE. CONTINUE TO DAY390 ONLY. PRESERVE THE CANONICAL SCIPY SOLVER AND USE ONLY THE O1-R2-CERTIFIED EXTERNALIZED-TOPOLOGY CHECKPOINT OPTIMIZATION.", flush=True)',
        'print("START FROM THE FORMAL R7-R7 DAY390 SCHEMA-V2 ACCEPTED STATE. CONTINUE TO DAY395 ONLY. PRESERVE THE CANONICAL SCIPY SOLVER AND THE O1-R2-CERTIFIED EXTERNALIZED-TOPOLOGY CHECKPOINT OPTIMIZATION.", flush=True)',
        1,
    )
    out = replace_exact(out, 'gate("parent_is_O1R2_commit"', 'gate("parent_is_R7R8_wrapper_commit"', 1)

    # Preserve the O1-R2-certified immutable topology source at Day385,
    # while the recurrent physical source is the Day390 R7-R7 state.
    topology_sha = DAY385_TOPOLOGY_SOURCE_SHA
    out = out.replace('"support_topology_source_state_sha256": np.asarray(R7R6_STATE_SHA)',
                      f'"support_topology_source_state_sha256": np.asarray("{topology_sha}")')
    out = out.replace('"support_topology_source_state_sha256": R7R6_STATE_SHA',
                      f'"support_topology_source_state_sha256": "{topology_sha}"')
    out = out.replace('meta.get("support_topology_source_state_sha256") == R7R6_STATE_SHA',
                      f'meta.get("support_topology_source_state_sha256") == "{topology_sha}"')
    out = out.replace('str(np.asarray(z["support_topology_source_state_sha256"]).reshape(())) == R7R6_STATE_SHA',
                      f'str(np.asarray(z["support_topology_source_state_sha256"]).reshape(())) == "{topology_sha}"')

    d0 = out.index("        def run_exact_diagnostic")
    d1 = out.index("        # Resume an R7-R7 dynamic checkpoint", d0)
    out = out[:d0] + out[d0:d1].replace("Day390", "Day395") + out[d1:]

    r0 = out.index("        # Resume an R7-R7 dynamic checkpoint")
    r1 = out.index("        while current_time < TARGET_DAY", r0)
    resume = out[r0:r1]
    resume = resume.replace("Resume an R7-R7 dynamic checkpoint", "Resume an R7-R8 dynamic checkpoint")
    resume = resume.replace("[R7-R7 RESUME]", "[R7-R8 RESUME]")
    resume = resume.replace("Day385", "Day390")
    out = out[:r0] + resume + out[r1:]

    c0 = out.index('        stage = "Day390_pilot_closure"')
    c1 = out.index("    except Exception as exc:", c0)
    closure = out[c0:c1]
    closure = closure.replace("Day390", "Day395").replace("day390", "day395")
    closure = closure.replace("Day385", "Day390")
    closure = closure.replace('"R7R6_status_bound"', '"R7R7_status_bound"')
    closure = closure.replace('"R7R6_classification_bound"', '"R7R7_classification_bound"')
    closure = closure.replace('"R7R6_Day390_state_must_be_preserved"', '"R7R7_Day390_state_must_be_preserved"')
    closure = closure.replace('"R7R6_Day390_state_sha256"', '"R7R7_Day390_state_sha256"')
    closure = closure.replace('"R7R6_Day390_accepted_state_is_segment_start_authority"', '"R7R7_Day390_accepted_state_is_segment_start_authority"')
    closure = closure.replace('"canonical_R7R6_SciPy_solver_preserved"', '"canonical_R7R7_SciPy_solver_preserved"')
    closure = closure.replace('"repository_parent_O1R2_commit"', '"repository_parent_R7R8_wrapper_commit"')
    closure = closure.replace('"checkpoint_topology_source_state_sha256": R7R6_STATE_SHA',
                              f'"checkpoint_topology_source_state_sha256": "{DAY385_TOPOLOGY_SOURCE_SHA}"')
    out = out[:c0] + closure + out[c1:]

    out = out.replace('"Day390_to_Day395_repaired_pilot_authorized": False',
                      '"Day395_to_Day400_repaired_pilot_authorized": False', 1)

    out = out.replace("# R7-R6 Day385 state is authoritative schema-v2 support.",
                      "# R7-R7 Day390 state is authoritative schema-v2 support.", 1)
    out = out.replace("R7R6_source_state_schema2", "R7R7_source_state_schema2", 1)
    out = out.replace("R7R6_source_root_checkpoint_exact", "R7R7_source_root_checkpoint_exact", 1)
    out = out.replace("physical_day_Day385_exact", "physical_day_Day390_exact", 1)
    out = out.replace("accepted_steps_Day385_exact", "accepted_steps_Day390_exact", 1)
    out = out.replace("source_Day385_positive_XY1_count_exact", "source_Day390_positive_XY1_count_exact", 1)
    out = out.replace("source_Day385_positive_XY2_count_exact", "source_Day390_positive_XY2_count_exact", 1)
    out = out.replace("Day385_source_mass_ledger_closes", "Day390_source_mass_ledger_closes", 1)

    return out

def load_transformed(root: Path) -> dict[str, Any]:
    template = root / TEMPLATE
    if not template.is_file():
        raise TransformError(f"template_missing:{template}")
    blob = gt(root, "hash-object", str(template))
    if blob != TEMPLATE_BLOB:
        raise TransformError(f"template_blob:{blob}:{TEMPLATE_BLOB}")
    transformed = transform_template(template.read_text(encoding="utf-8"))
    code = compile(transformed, f"<derived:{M}>", "exec")
    ns: dict[str, Any] = {"__name__": "pad_stream_r7r8_derived", "__file__": str(template)}
    exec(code, ns, ns)
    return ns

def selftest(root: Path | None = None) -> None:
    assert BRANCH == "postv16-av4-pivot"
    assert PARENT == "1bd95433fe9c5959b9d8428fa1ef72c5c2dee640"
    assert DAY390_STATE_SHA == "83e26d77f5f853412b817c37dcd4d3958ba4469bbd14c10a8467a256b52c33ee"
    if root is not None and (root / TEMPLATE).is_file():
        ns = load_transformed(root)
        ns["selftest"]()
    print("POSTV16 AV4 P3-R1-R7-R8-R1 derived-runner transform repair self-test: PASS")

def main(project_root: Path, drive_root: Path, time_limit_seconds: float) -> int:
    root = project_root.resolve()
    if gt(root, "branch", "--show-current") != BRANCH:
        raise SystemExit(f"wrong_branch:{gt(root, 'branch', '--show-current')}")
    if gt(root, "rev-parse", "HEAD^") != PARENT:
        raise SystemExit(f"wrong_parent:{gt(root, 'rev-parse', 'HEAD^')}:{PARENT}")
    original = root / ORIGINAL_R7R8_WRAPPER
    if not original.is_file():
        raise SystemExit(f"original_R7R8_wrapper_missing:{original}")
    if gt(root, "hash-object", str(original)) != ORIGINAL_R7R8_WRAPPER_BLOB:
        raise SystemExit(f"original_R7R8_wrapper_blob_mismatch:{gt(root, 'hash-object', str(original))}")
    ns = load_transformed(root)
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

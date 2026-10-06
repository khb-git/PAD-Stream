#!/usr/bin/env python3
"""PAD-Stream V16E-7: Hybrid10/Hybrid12 evidence synthesis and deployment-role freeze.

No training, inference, checkpoint change, test re-evaluation, or OOD access occurs.
The sealed internal-test results are bound and summarized descriptively only. They
are not used to choose a model. Deployment routing is frozen prospectively from
the already-frozen physics/feature contracts:

* Hybrid10: fixed relative-permeability endpoints krw_max=kro_max=0.8 only.
* Hybrid12: layer-specific relative-permeability endpoints within frozen bounds.
* Otherwise: no neural proposal; use the exact-physics/fallback branch.

Both learned models remain pre-breakthrough incompressible immiscible BL fan
proposals, subject to exact physics/inventory/conservative-map-back authority.
"""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, sys, tempfile
from pathlib import Path

MILESTONE = "V16E-7"
REVISION = "R1_HYBRID10_HYBRID12_EVIDENCE_AND_DEPLOYMENT_ROLE_FREEZE"
STATUS = "V16E7_HYBRID_EVIDENCE_SYNTHESIZED_DEPLOYMENT_ROLES_FROZEN_NO_TEST_INFORMED_SELECTION"
NEXT = "V16E-8 — Hybrid BL-DP PAD-Stream Transport Adapter and Identical-State Integration Protocol Freeze"

E3_REL = Path("provenance/hybrid_dp/V16E3_R1_HYBRID_PROTOCOL_FREEZE")
E5_REL = Path("provenance/hybrid_dp/V16E5_PRETRAINING_MANIFEST_FREEZE")
E6A_REL = Path("models/hybrid_dp/V16E6A_HYBRID10_CONTROLLED_R1")
E6AT_REL = Path("evaluations/hybrid_dp/V16E6AT_HYBRID10_SEALED_INTERNAL_TEST_R1")
E6B_REL = Path("models/hybrid_dp/V16E6B_HYBRID12_CONTROLLED_R1")
E6BT_REL = Path("evaluations/hybrid_dp/V16E6BT_HYBRID12_SEALED_INTERNAL_TEST_R1")
E6AT_LOCK_REL = Path("provenance/hybrid_dp/V16E6AT_INTERNAL_TEST_OPEN_LOCK")
E6BT_LOCK_REL = Path("provenance/hybrid_dp/V16E6BT_INTERNAL_TEST_OPEN_LOCK")
OUT_REL = Path("provenance/hybrid_dp/V16E7_HYBRID_EVIDENCE_AND_DEPLOYMENT_ROLE_FREEZE")

E3 = {"protocol": ("V16E3_R1_Hybrid_BL_DP_Protocol.json", "57bcb2e74c68eb77ed8de69d75ddafc00b38d2f3c4e9b884bfc87676160db4a1")}
E5 = {
    "manifest": ("V16E5_PreTraining_Manifest.json", "c197dae32d01a1f083f7ad414e601eac1f44d7405b6087c7c7db8a6c28c5c808"),
    "results": ("V16E5_PreTraining_Manifest_Freeze_Results.json", "3f605784f41f4cec2637887d4678d217a651b2f5b5fff0f1b9f659857dde4d84"),
    "summary": ("PAD_Stream_V16E5_Summary.json", "9736d303c5388f5cca87616583a6b5e692738fdd1e912b372c372c889abfdebd"),
    "handoff": ("V16E5_Handoff.md", "caf53b0dccf696c604e248688a30d81dac1a100afd8ff5eefbe601c8bb44e44a"),
}
RUNNERS = {
    "E5": ("PAD_Stream_V16E5_PreTraining_Manifest_Freeze.py", "38849300cb611511575fc0dc4c023758a3d61462d31c0aa82fe863989e54f56e"),
    "E6A": ("PAD_Stream_V16E6A_Hybrid10_Controlled_Training_and_Validation.py", "c48a1d8f185bb4576af7e255a5cf190fc47d2fa5360f526e2254d831254994ad"),
    "E6AT": ("PAD_Stream_V16E6AT_Hybrid10_Sealed_Internal_Test_Evaluation.py", "6cad3a01c5c05ce7488956cfe358294eef41af5ffa79876d08d19312f39b660f"),
    "E6B": ("PAD_Stream_V16E6B_Hybrid12_Controlled_Training_and_Validation.py", "79cffcf527d20a8f036f561a5a5372f9858f47f91eb08dd34dc0069d6229dcf0"),
    "E6BT": ("PAD_Stream_V16E6BT_Hybrid12_Sealed_Internal_Test_Evaluation.py", "8b09a92f021d765ed35c28131e2351a58481058cdb1a3b8cae256ea9d39a5c82"),
}
E6A = {
    "checkpoint": ("V16E6A_Hybrid10_Accepted.weights.h5", "0b7be119dfc14c08bd8f7bb3c84c64b8d425e0176cddebf952687a49c05402a9"),
    "validation": ("V16E6A_Validation_Metrics.json", "235c41ed2e6bbf63a242cf5a8d6386802e752705dafee9705e8d09453a9589f0"),
    "summary": ("PAD_Stream_V16E6A_Summary.json", "3a737b4c8a15e30fcc5a2acf9a94a6e7af5f26a3158c99f6207e78986c0a60ea"),
    "handoff": ("V16E6A_Handoff.md", "c3ba1b3ffb4439d616f9420542e9bfc1f42b4e47467d324f075d924f78467586"),
}
E6AT = {
    "metrics": ("V16E6AT_Hybrid10_Internal_Test_Metrics.json", "35c48d2e2e01c8c4efc2d1594970c929f1d87cfd93066f242dd306ad863fe218"),
    "results": ("V16E6AT_Sealed_Internal_Test_Evaluation_Results.json", "0343911f35329309ae88a0431de38f1b448b940559b5582d1ed57064d3cc2e7f"),
    "summary": ("PAD_Stream_V16E6AT_Summary.json", "c1f72fbce37fa5e7b5346c9cf36a55452ba454ccd0580fb8469b85bba4e516db"),
    "handoff": ("V16E6AT_Handoff.md", "384c93e2d431501d4b20351b2c6069b70d59acf91822dc3a29ad3c6522ba56d3"),
}
E6B = {
    "checkpoint": ("V16E6B_Hybrid12_Accepted.weights.h5", "1321008f1127ae48fa3d230b89759337779a9db83819ae8a73719ed3dfec12d8"),
    "validation": ("V16E6B_Validation_Metrics.json", "3739954f7d6ee0157660f17b080379cacdb998f75f5cb1bca5f1df3141e87a59"),
    "summary": ("PAD_Stream_V16E6B_Summary.json", "ecb0cca6ff9b5c1a7c9131e92897ad80008a552e27ee1f456341683935b2ee4f"),
    "handoff": ("V16E6B_Handoff.md", "2bbfcb6549ac225410ad94501cf823943e405599a634f4ba7713f406349b5c12"),
}
E6BT = {
    "metrics": ("V16E6BT_Hybrid12_Internal_Test_Metrics.json", "28d39bf059b02a0410457f997e406dc753ac0c7756fde5387083e6e4d06d9e52"),
    "results": ("V16E6BT_Sealed_Internal_Test_Evaluation_Results.json", "85dd305452f3c6dc2de7d71fe8f9b98383bf2a1d89e3f2473d6cab3e1428eabb"),
    "summary": ("PAD_Stream_V16E6BT_Summary.json", "d582c4b0e5f64bfb14f518783f99508dc69297e6ae1079e1c18e0703475ee3d0"),
    "handoff": ("V16E6BT_Handoff.md", "0b0b6a284ea14cb1430b7b9181762a3a27272204e7052922f8996e9a39ff44d2"),
}
FEATURES10 = ["no", "nw", "swc", "sor", "mu_w", "mu_o", "phi", "tD", "xD_star", "Sw_star"]
FEATURES12 = ["no", "nw", "swc", "sor", "mu_w", "mu_o", "phi", "krw_max", "kro_max", "tD", "xD_star", "Sw_star"]
PROHIBITIONS = [
    "NO TRAINING, GRADIENT UPDATE, OR CHECKPOINT CREATION.",
    "NO CHECKPOINT SELECTION, REPLACEMENT, OR RETRAINING.",
    "NO INTERNAL-TEST RE-EVALUATION.",
    "NO CROSS-MODEL RANKING OR WINNER SELECTION FROM SEALED TEST METRICS.",
    "NO HYPERPARAMETER OR ACCEPTANCE-THRESHOLD TUNING.",
    "NO OOD REOPENING.",
    "NO SGSim MODIFICATION OR DEPLOYMENT IN THIS MILESTONE.",
    "NO POLLOCK/TOF RECOMPUTATION.",
    "NO B4 RETRAINING.",
    "NO ASSUMPTION OF FIXED 0.8 ENDPOINTS WHEN UPSTREAM METADATA DOES NOT EXPLICITLY GUARANTEE THEM.",
]

class GateError(RuntimeError):
    pass

class Gates:
    def __init__(self):
        self.items = {}
    def check(self, name, condition, detail=""):
        ok = bool(condition)
        self.items[name] = {"passed": ok, "detail": detail}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""), flush=True)
        if not ok:
            raise GateError(name + ((": " + detail) if detail else ""))

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def encoded(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False, ensure_ascii=False) + "\n").encode("utf-8")

def read_json(path: Path):
    def reject(value):
        raise ValueError("non-finite JSON constant " + value)
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)

def bind(gates, label, path, expected):
    gates.check(label + "_exists", path.is_file(), str(path))
    gates.check(label + "_SHA_exact", sha(path) == expected)

def bind_set(gates, prefix, base, spec):
    for key, (name, expected) in spec.items():
        bind(gates, prefix + "_" + key, base / name, expected)

def publish(stage: Path, out: Path):
    if out.exists():
        current = {p.relative_to(out).as_posix(): sha(p) for p in out.rglob("*") if p.is_file()}
        staged = {p.relative_to(stage).as_posix(): sha(p) for p in stage.rglob("*") if p.is_file()}
        if current == staged:
            print("Existing identical V16E-7 freeze reused.", flush=True)
            return
        raise GateError("Existing V16E-7 output differs; nothing overwritten.")
    out.parent.mkdir(parents=True, exist_ok=True)
    sibling = Path(tempfile.mkdtemp(prefix=".v16e7-", dir=out.parent))
    try:
        for src in sorted(stage.rglob("*")):
            if src.is_file():
                dst = sibling / src.relative_to(stage)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
        sibling.rename(out)
    finally:
        if sibling.exists():
            shutil.rmtree(sibling)

def identity_from_handoff(gates, label, base, handoff_name, identity_name):
    text = (base / handoff_name).read_text(encoding="utf-8")
    match = re.search(r"Checkpoint identity SHA:\s*([0-9a-f]{64})", text)
    gates.check(label + "_handoff_identity_SHA_present", match is not None)
    path = base / identity_name
    bind(gates, label + "_checkpoint_identity", path, match.group(1))
    return read_json(path), match.group(1)

def metric_view(payload):
    metrics = payload["metrics"]
    keys = ["Sw_RMSE", "Sw_MAE", "profile_RMSE_p95", "BC_RMSE", "front_RMSE",
            "physics_characteristic_RMSE", "monotonic_violation_fraction", "nonfinite_predictions"]
    return {key: metrics[key] for key in keys}

def run(project: Path, drive: Path, out: Path):
    print("=" * 118 + "\nPAD-Stream V16E-7\nHybrid10 / Hybrid12 Evidence Synthesis and Deployment-Role Freeze\n" + "=" * 118, flush=True)
    print("\n".join(PROHIBITIONS), flush=True)
    gates = Gates()

    print("\nREPOSITORY RUNNER AUTHORITY", flush=True)
    for label, (name, expected) in RUNNERS.items():
        bind(gates, label + "_runner", project / name, expected)

    print("\nFROZEN SCIENTIFIC / PRE-TRAINING CONTRACTS", flush=True)
    bind_set(gates, "E5", drive / E5_REL, E5)
    bind_set(gates, "E3", drive / E3_REL, E3)
    e3 = read_json(drive / E3_REL / E3["protocol"][0])
    e5 = read_json(drive / E5_REL / E5["manifest"][0])
    gates.check("Hybrid10_features_exact", e5["experiments"]["Hybrid10"]["feature_order"] == FEATURES10)
    gates.check("Hybrid12_features_exact", e5["experiments"]["Hybrid12"]["feature_order"] == FEATURES12)
    gates.check("Hybrid10_fixed_endpoint_contract_exact", e3["experiments"]["Hybrid10"]["fixed_endpoints"] == {"krw_max": 0.8, "kro_max": 0.8})
    bounds = e3["dataset_design"]["bounds"]
    gates.check("Hybrid12_krw_bounds_exact", bounds["krw_max_Hybrid12"] == [0.05, 0.80])
    gates.check("Hybrid12_kro_bounds_exact", bounds["kro_max_Hybrid12"] == [0.30, 0.80])
    gates.check("learned_role_is_proposal", "proposal" in e3["scope"]["learned_transport_role"].lower())
    gates.check("full_physics_equivalence_false", e3["scope"]["full_physics_equivalence_claimed"] is False)

    print("\nHYBRID10 FINAL EVIDENCE AUTHORITY", flush=True)
    bind_set(gates, "E6A", drive / E6A_REL, E6A)
    bind_set(gates, "E6AT", drive / E6AT_REL, E6AT)
    a_val = read_json(drive / E6A_REL / E6A["validation"][0])
    a_sum = read_json(drive / E6A_REL / E6A["summary"][0])
    a_test = read_json(drive / E6AT_REL / E6AT["metrics"][0])
    a_tres = read_json(drive / E6AT_REL / E6AT["results"][0])
    a_tsum = read_json(drive / E6AT_REL / E6AT["summary"][0])
    a_id, a_idsha = identity_from_handoff(gates, "E6A", drive / E6A_REL, E6A["handoff"][0], "V16E6A_Checkpoint_Identity.json")
    gates.check("E6A_validation_accepted", a_val["all_gates_passed"] is True and a_sum["validation_all_gates_passed"] is True)
    gates.check("E6A_checkpoint_identity_exact", a_id["checkpoint_sha256"] == E6A["checkpoint"][1])
    gates.check("E6AT_one_time_complete", a_tsum["internal_test_evaluation_count"] == 1 and a_tres["evaluation_completed"] is True)
    gates.check("E6AT_no_model_selection", a_tres["model_selection_performed"] is False and a_tres["training_performed"] is False)
    gates.check("E6AT_OOD_closed", a_tres["OOD_opened"] is False)
    gates.check("E6AT_metrics_checkpoint_link", a_test["checkpoint_sha256"] == E6A["checkpoint"][1])
    lock_a = drive / E6AT_LOCK_REL / "V16E6AT_Internal_Test_Open_Lock.json"
    gates.check("E6AT_open_lock_exists", lock_a.is_file(), str(lock_a))
    gates.check("E6AT_results_lock_link", a_tres["internal_test_open_lock_sha256"] == sha(lock_a))

    print("\nHYBRID12 FINAL EVIDENCE AUTHORITY", flush=True)
    bind_set(gates, "E6B", drive / E6B_REL, E6B)
    bind_set(gates, "E6BT", drive / E6BT_REL, E6BT)
    b_val = read_json(drive / E6B_REL / E6B["validation"][0])
    b_sum = read_json(drive / E6B_REL / E6B["summary"][0])
    b_test = read_json(drive / E6BT_REL / E6BT["metrics"][0])
    b_tres = read_json(drive / E6BT_REL / E6BT["results"][0])
    b_tsum = read_json(drive / E6BT_REL / E6BT["summary"][0])
    b_id, b_idsha = identity_from_handoff(gates, "E6B", drive / E6B_REL, E6B["handoff"][0], "V16E6B_Checkpoint_Identity.json")
    gates.check("E6B_validation_accepted", b_val["all_gates_passed"] is True and b_sum["validation_all_gates_passed"] is True)
    gates.check("E6B_checkpoint_identity_exact", b_id["checkpoint_sha256"] == E6B["checkpoint"][1])
    gates.check("E6BT_one_time_complete", b_tsum["internal_test_evaluation_count"] == 1 and b_tres["evaluation_completed"] is True)
    gates.check("E6BT_no_model_selection", b_tres["model_selection_performed"] is False and b_tres["training_performed"] is False)
    gates.check("E6BT_OOD_closed", b_tres["OOD_opened"] is False)
    gates.check("E6BT_metrics_checkpoint_link", b_test["checkpoint_sha256"] == E6B["checkpoint"][1])
    lock_b = drive / E6BT_LOCK_REL / "V16E6BT_Internal_Test_Open_Lock.json"
    gates.check("E6BT_open_lock_exists", lock_b.is_file(), str(lock_b))
    gates.check("E6BT_results_lock_link", b_tres["internal_test_open_lock_sha256"] == sha(lock_b))

    print("\nNO TEST-INFORMED SELECTION FIREWALL", flush=True)
    gates.check("both_test_sets_already_single_use", a_tsum["internal_test_evaluation_count"] == 1 and b_tsum["internal_test_evaluation_count"] == 1)
    gates.check("both_test_artifacts_mark_no_selection", a_test["model_selection_performed"] is False and b_test["model_selection_performed"] is False)
    gates.check("cross_model_test_ranking_prohibited", True, "E7 records test metrics descriptively but does not rank or select checkpoints from them")
    gates.check("checkpoint_changes_prohibited", a_test["checkpoint_changed"] is False and b_test["checkpoint_changed"] is False)

    evidence = {
        "milestone": MILESTONE,
        "revision": REVISION,
        "selection_policy": "NO cross-model winner is selected from sealed internal-test evidence.",
        "Hybrid10": {
            "checkpoint_sha256": E6A["checkpoint"][1],
            "checkpoint_identity_sha256": a_idsha,
            "validation_metrics_sha256": E6A["validation"][1],
            "validation": metric_view(a_val),
            "sealed_internal_test_metrics_sha256": E6AT["metrics"][1],
            "sealed_internal_test": metric_view(a_test),
            "test_use": "descriptive final generalization evidence only; not deployment selection",
        },
        "Hybrid12": {
            "checkpoint_sha256": E6B["checkpoint"][1],
            "checkpoint_identity_sha256": b_idsha,
            "validation_metrics_sha256": E6B["validation"][1],
            "validation": metric_view(b_val),
            "sealed_internal_test_metrics_sha256": E6BT["metrics"][1],
            "sealed_internal_test": metric_view(b_test),
            "test_use": "descriptive final generalization evidence only; not deployment selection",
        },
        "cross_model_test_ranking_performed": False,
        "test_informed_checkpoint_selection_performed": False,
        "OOD_opened": False,
    }

    routing = {
        "milestone": MILESTONE,
        "revision": REVISION,
        "scope": {
            "transport_regime": "incompressible immiscible Corey/Welge BL; positive pre-breakthrough fan only",
            "full_compressible_capillary_equivalence_claimed": False,
            "learned_output_role": "transport proposal, not final conservation authority",
            "DP_role": "absolute permeability, thickness, kh/kh_mob allocation and aggregation remain outside the PI-RNN",
            "exact_authorities": [
                "upstream pressure/Darcy/Pollock state",
                "shock inputs xD_star and Sw_star",
                "inventory/conservation screen",
                "conservative grid map-back",
            ],
        },
        "models": {
            "Hybrid10": {
                "checkpoint_sha256": E6A["checkpoint"][1],
                "feature_order": FEATURES10,
                "eligible_only_if": "upstream metadata explicitly declares fixed_endpoint_mode with krw_max=0.8 and kro_max=0.8",
                "endpoint_policy": "never infer fixed 0.8 from missing endpoint data or numerical closeness",
                "role": "canonical fixed-endpoint Hybrid BL-DP proposal branch",
            },
            "Hybrid12": {
                "checkpoint_sha256": E6B["checkpoint"][1],
                "feature_order": FEATURES12,
                "eligible_only_if": "layer-specific krw_max and kro_max are explicitly supplied and all conditioning is within the frozen prospective domain",
                "endpoint_bounds": {"krw_max": [0.05, 0.80], "kro_max": [0.30, 0.80]},
                "role": "canonical variable-endpoint Hybrid BL-DP proposal branch",
            },
        },
        "routing_rules": [
            {"priority": 1, "condition": "upstream explicitly declares fixed_endpoint_mode and krw_max=0.8 and kro_max=0.8", "action": "HYBRID10"},
            {"priority": 2, "condition": "explicit layer-specific endpoints are supplied within frozen Hybrid12 bounds and the complete conditioning vector is in-domain", "action": "HYBRID12"},
            {"priority": 3, "condition": "endpoint semantics are missing, ambiguous, outside frozen bounds, or other conditioning is outside the frozen prospective domain", "action": "EXACT_PHYSICS_OR_SCREENED_FALLBACK"},
        ],
        "forbidden_routing": [
            "choose Hybrid10 because its sealed-test metric is numerically lower",
            "choose Hybrid12 because it has more features",
            "assume missing endpoints equal 0.8",
            "use either branch outside the frozen pre-BT incompressible scope without a new protocol",
        ],
        "SGSim_deployment_authorized_here": False,
        "adapter_implementation_authorized_next": True,
    }
    gates.check("Hybrid10_role_fixed_endpoint_only", "fixed_endpoint_mode" in routing["models"]["Hybrid10"]["eligible_only_if"])
    gates.check("Hybrid12_role_variable_endpoint", routing["models"]["Hybrid12"]["endpoint_bounds"] == {"krw_max": [0.05, 0.80], "kro_max": [0.30, 0.80]})
    gates.check("ambiguous_endpoint_fallback_exact", routing["routing_rules"][2]["action"] == "EXACT_PHYSICS_OR_SCREENED_FALLBACK")
    gates.check("SGSim_not_deployed_in_E7", routing["SGSim_deployment_authorized_here"] is False)

    results = {
        "milestone": MILESTONE,
        "revision": REVISION,
        "status": STATUS,
        "runner_sha256": sha(Path(__file__)),
        "Hybrid10_checkpoint_sha256": E6A["checkpoint"][1],
        "Hybrid12_checkpoint_sha256": E6B["checkpoint"][1],
        "Hybrid10_internal_test_metrics_sha256": E6AT["metrics"][1],
        "Hybrid12_internal_test_metrics_sha256": E6BT["metrics"][1],
        "cross_model_test_ranking_performed": False,
        "test_informed_model_selection_performed": False,
        "training_performed": False,
        "inference_performed": False,
        "checkpoint_changed": False,
        "OOD_opened": False,
        "SGSim_modified_or_deployed": False,
        "deployment_roles_frozen": True,
        "next_milestone": NEXT,
        "acceptance_gates": gates.items,
    }
    summary = {
        "milestone": MILESTONE,
        "revision": REVISION,
        "status": STATUS,
        "Hybrid10_checkpoint_unchanged": True,
        "Hybrid12_checkpoint_unchanged": True,
        "sealed_tests_reopened": False,
        "test_informed_selection_performed": False,
        "deployment_role_Hybrid10": "fixed-endpoint 0.8/0.8 proposal branch",
        "deployment_role_Hybrid12": "explicit variable-endpoint proposal branch",
        "ambiguous_or_out_of_domain_policy": "exact physics or screened fallback",
        "SGSim_deployment_authorized": False,
        "adapter_protocol_authorized_next": True,
        "next_milestone": NEXT,
    }

    print("\nFREEZE EVIDENCE AND DEPLOYMENT ROLES", flush=True)
    with tempfile.TemporaryDirectory(prefix="v16e7-out-") as tmp:
        stage = Path(tmp)
        (stage / "V16E7_Hybrid10_Hybrid12_Evidence_Synthesis.json").write_bytes(encoded(evidence))
        (stage / "V16E7_Deployment_Routing_Contract.json").write_bytes(encoded(routing))
        (stage / "V16E7_Evidence_Synthesis_and_Deployment_Role_Results.json").write_bytes(encoded(results))
        (stage / "PAD_Stream_V16E7_Summary.json").write_bytes(encoded(summary))
        evidence_sha = sha(stage / "V16E7_Hybrid10_Hybrid12_Evidence_Synthesis.json")
        routing_sha = sha(stage / "V16E7_Deployment_Routing_Contract.json")
        handoff = f"""# PAD-Stream V16E-7 — Hybrid evidence synthesis and deployment-role freeze

Both prospective Hybrid checkpoints are now complete through validation and one-time sealed internal-test evaluation. Their sealed-test metrics are retained as descriptive final generalization evidence only. V16E-7 does not rank the checkpoints or choose a winner from the test results.

Deployment is frozen by physics semantics instead. Hybrid10 is the fixed-endpoint branch and is eligible only when upstream metadata explicitly guarantees krw_max=kro_max=0.8. Hybrid12 is the variable-endpoint branch and is eligible when layer-specific endpoints are explicitly supplied within the frozen domain. Missing/ambiguous/out-of-domain endpoint semantics trigger exact-physics or screened fallback; they never silently map to Hybrid10.

Both models remain incompressible immiscible pre-breakthrough BL fan proposals. Absolute permeability and thickness remain in Dykstra-Parsons allocation/aggregation, not neural conditioning. Exact pressure/Darcy/Pollock state, shock inputs, inventory/conservation screening and conservative map-back retain authority. No SGSim deployment occurs here.

Hybrid10 checkpoint SHA: {E6A['checkpoint'][1]}
Hybrid12 checkpoint SHA: {E6B['checkpoint'][1]}
Evidence synthesis SHA: {evidence_sha}
Routing contract SHA: {routing_sha}

NEXT: {NEXT}
"""
        (stage / "V16E7_Handoff.md").write_text(handoff, encoding="utf-8")
        publish(stage, out)

    print("\n" + "=" * 118 + "\nV16E-7 RESULT: PASS\n" + "=" * 118, flush=True)
    print(f"{'Hybrid10 checkpoint unchanged':48}: YES", flush=True)
    print(f"{'Hybrid12 checkpoint unchanged':48}: YES", flush=True)
    print(f"{'Sealed tests reopened':48}: NO", flush=True)
    print(f"{'Test-informed model selection performed':48}: NO", flush=True)
    print(f"{'Hybrid10 deployment role':48}: FIXED 0.8/0.8 ENDPOINT BRANCH", flush=True)
    print(f"{'Hybrid12 deployment role':48}: EXPLICIT VARIABLE-ENDPOINT BRANCH", flush=True)
    print(f"{'Ambiguous / OOD endpoint policy':48}: EXACT PHYSICS / SCREENED FALLBACK", flush=True)
    print(f"{'SGSim deployment performed / authorized here':48}: NO / NO", flush=True)
    print("Output:", out, flush=True)
    for name in [
        "V16E7_Hybrid10_Hybrid12_Evidence_Synthesis.json",
        "V16E7_Deployment_Routing_Contract.json",
        "V16E7_Evidence_Synthesis_and_Deployment_Role_Results.json",
        "PAD_Stream_V16E7_Summary.json",
        "V16E7_Handoff.md",
    ]:
        print(name, "SHA:", sha(out / name), flush=True)
    print("NEXT:", NEXT, flush=True)
    return 0

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        return run(args.project_root.resolve(), args.drive_root.resolve(), (args.output_dir or args.drive_root / OUT_REL).resolve())
    except (GateError, OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        print("\n[FAIL] V16E-7 did not close:", exc, file=sys.stderr, flush=True)
        print("No deployment-role freeze or new integration authority was published.", file=sys.stderr, flush=True)
        return 2

if __name__ == "__main__":
    sys.exit(main())

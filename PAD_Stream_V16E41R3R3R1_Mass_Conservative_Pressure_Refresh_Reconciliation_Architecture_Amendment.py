from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import io
import json
import subprocess
from typing import Any


MILESTONE = "V16E-41-R3-R3-R1"
STATUS = "MASS_CONSERVATIVE_PRESSURE_REFRESH_RECONCILIATION_ARCHITECTURE_FROZEN"
NEXT = (
    "V16E-41-R3-R4 - Controlled Same-Parent Mass-Conservative "
    "Saturation-Updated Flow-Refresh Transition Validation"
)

R3R3_RUNNER = (
    "PAD_Stream_V16E41R3R3_Saturation_Updated_Flow_Refresh_"
    "Runtime_Architecture_Freeze.py"
)
R3R3_GIT_BLOB = "8d72895d023fe6c2d7d3c9752698a557747117a8"

R3R3_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R3_SATURATION_UPDATED_FLOW_REFRESH_RUNTIME_ARCHITECTURE_FREEZE"
)
R3R3_CONTRACT = "PAD_Stream_V16E41R3R3_Architecture_Contract.json"
R3R3_CLOSURE = "V16E41R3R3_Final_Closure.json"
EXPECTED_R3R3_STATUS = "SATURATION_UPDATED_FLOW_REFRESH_RUNTIME_ARCHITECTURE_FROZEN"

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R3R1_MASS_CONSERVATIVE_PRESSURE_REFRESH_RECONCILIATION_ARCHITECTURE_AMENDMENT"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R3R1_BLOCKED_MASS_CONSERVATIVE_PRESSURE_REFRESH_RECONCILIATION_ARCHITECTURE_AMENDMENT"
)


class GateError(RuntimeError):
    pass


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path: Path, repo_root: Path) -> str:
    p = subprocess.run(
        ["git", "-C", str(repo_root), "hash-object", str(path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists():
            if p.read_bytes() != data:
                raise GateError(f"existing_output_differs:{name}")
        else:
            p.write_bytes(data)


def self_test() -> None:
    # Toy EOS representation: fixed mass M = PV*rho(p)*S.
    # Changing pressure while keeping both M and S fixed is impossible
    # unless rho is unchanged.
    pv = 2.0
    rho0 = 10.0
    rho1 = 12.0
    s0 = 0.25
    mass = pv * rho0 * s0
    unchanged_s_mass = pv * rho1 * s0
    reconciled_s = mass / (pv * rho1)

    if abs(unchanged_s_mass - mass) <= 1.0e-12:
        raise RuntimeError("self_test_failed_to_expose_pressure_mass_coupling")
    if abs(pv * rho1 * reconciled_s - mass) > 1.0e-12:
        raise RuntimeError("self_test_mass_reconciliation_failed")
    if abs(reconciled_s - s0) <= 1.0e-12:
        raise RuntimeError("self_test_saturation_should_change")

    print(
        "PAD-Stream V16E-41-R3-R3-R1 mass-conservative pressure-refresh "
        "reconciliation architecture amendment self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}
    failed_stage: str | None = None

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {"passed": bool(passed), "detail": str(detail)}
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "=" * 154)
        print(
            "PAD-Stream V16E-41-R3-R3-R1 — Mass-Conservative Pressure-Refresh "
            "Thermodynamic Reconciliation Architecture Amendment"
        )
        print("=" * 154)
        print("ROLE       : architecture amendment only")
        print("SOLVER RUN : none")
        print("STATE MOVE : none")
        print("PURPOSE    : remove pressure/EOS inconsistency before R3-R4")

        failed_stage = "R3R3_predecessor_binding"

        pred = root / R3R3_RUNNER
        gate("R3R3_runner_exists", pred.is_file(), pred)
        blob = git_blob_sha(pred, root)
        gate("R3R3_runner_git_blob_exact", blob == R3R3_GIT_BLOB, blob)

        contract_path = drive / R3R3_REL / R3R3_CONTRACT
        closure_path = drive / R3R3_REL / R3R3_CLOSURE
        gate("R3R3_contract_exists", contract_path.is_file(), contract_path)
        gate("R3R3_closure_exists", closure_path.is_file(), closure_path)

        old = load_json(contract_path)
        old_closure = load_json(closure_path)

        gate(
            "R3R3_status_exact",
            old.get("status") == EXPECTED_R3R3_STATUS,
            old.get("status"),
        )
        gate(
            "R3R3_closure_all_gates_passed",
            old_closure.get("all_gates_passed") is True,
            old_closure.get("all_gates_passed"),
        )
        gate(
            "R3R3_refresh_preserved_grid_inventory",
            old.get("rollback_semantics", {}).get(
                "refresh_does_not_change_grid_inventory"
            ) is True,
        )

        failed_stage = "reconciliation_contract_freeze"

        amendment = {
            "milestone": MILESTONE,
            "status": STATUS,
            "architecture_amendment_only": True,
            "solver_execution_performed": False,
            "canonical_state_created": False,
            "physical_time_advanced": False,
            "accepted_step_index_advanced": False,
            "predecessor_status": EXPECTED_R3R3_STATUS,
            "amends": {
                "R3R3_rule_retained": (
                    "A refresh is not a physical transport transition and must "
                    "not change component inventory, physical time, accepted step, "
                    "or cumulative injection/production ledgers."
                ),
                "R3R3_rule_replaced": (
                    "The accepted Cartesian saturation array is NOT required to "
                    "remain numerically unchanged during a compressible pressure refresh."
                ),
                "reason": (
                    "Stored CO2 mass depends on pressure through the accepted gas-density EOS. "
                    "Holding both pressure-updated density and saturation fixed would change "
                    "component inventory without a source or sink."
                ),
            },
            "primary_conserved_refresh_quantity": (
                "cellwise Cartesian CO2 component mass array"
            ),
            "refresh_reference_mass_definition": {
                "source": (
                    "Exact accepted parent saturation + exact accepted parent pressure + "
                    "frozen p_ref/EOS + cell pore volume."
                ),
                "formula": (
                    "M_i^parent = PV_i * rho_g(S_i^parent,p_i^parent,p_ref) * "
                    "(S_i^parent-S_background)"
                ),
                "must_match_parent_ledger": True,
                "cellwise_mass_array_frozen_during_refresh": True,
            },
            "same_time_pressure_saturation_fixed_point": {
                "iteration": [
                    "Start S^(0) from exact accepted parent saturation.",
                    "Compute total mobility lambda_t(S^(n)).",
                    "Solve finite-volume pressure p^(n+1).",
                    "Invert the frozen parent cellwise component mass array under p^(n+1) "
                    "to obtain S^(n+1), using the existing nonlinear EOS inversion.",
                    "Recompute mobility from S^(n+1).",
                    "Repeat until both pressure and saturation convergence gates pass.",
                ],
                "direct_Picard_first": True,
                "hidden_damping_or_relaxation_authorized": False,
                "convergence_required_before_flow_epoch_commit": True,
                "maximum_iteration_count_must_be_explicit_in_R3R4": True,
                "tolerances_must_be_explicit_in_R3R4": True,
            },
            "reconciliation_invariants": {
                "physical_time_days_unchanged": True,
                "accepted_step_index_unchanged": True,
                "cumulative_injected_co2_mass_kg_unchanged": True,
                "cumulative_produced_co2_mass_kg_unchanged": True,
                "cumulative_boundary_co2_mass_kg_unchanged": True,
                "cellwise_component_mass_unchanged_within_numeric_tolerance": True,
                "global_component_mass_unchanged_within_numeric_tolerance": True,
                "p_ref_gas_pa_unchanged": True,
                "external_mass_source_zero": True,
                "external_mass_sink_zero": True,
            },
            "saturation_semantics": {
                "reconciled_saturation_may_differ_from_parent": True,
                "difference_is_not_advective_transport": True,
                "difference_is_not_capillary_transport": True,
                "difference_is_thermodynamic_representation_of_same_component_mass": True,
                "reconciled_saturation_used_for_final_mobility": True,
                "reconciled_saturation_used_as_transport_parent_after_flow_epoch_commit": True,
                "historical_parent_state_remains_immutable": True,
            },
            "capacity_policy_during_reconciliation": {
                "same_Sg_increment_max_0p60": True,
                "if_any_cell_mass_exceeds_reconciled_pressure_capacity": "BLOCK",
                "clipping_authorized": False,
                "mass_redistribution_authorized": False,
                "saturation_ceiling_relaxation_authorized": False,
            },
            "flow_epoch_commit_after_reconciliation": [
                "converged reconciled saturation",
                "converged pressure",
                "conservative Darcy face fluxes",
                "exact Pollock streamline geometry",
                "streamline weights",
                "TOF coordinates",
                "SG7D overlap operator",
                "E37A control-volume geometry",
                "streamline face pressure",
            ],
            "R3R4_acceptance_requirements": [
                "Bind exact R3-R1 step-3975 parent and mass ledger.",
                "Construct fixed parent cellwise component mass using parent accepted pressure.",
                "Converge same-time pressure/saturation fixed point with no mass source/sink.",
                "Prove reconciled cellwise/global mass closure.",
                "Build conservative Darcy fluxes and exact Pollock/TOF/overlap from converged state.",
                "Retry the original stale-flow nominal candidate dt unchanged.",
                "Require updated-flow CFL to admit that candidate dt.",
                "Require raw map-back capacity preflight to pass without R2 capacity timestep reduction.",
                "Apply existing no-flow conservative capillary operator.",
                "Require exact transition component-mass closure.",
                "Commit exactly one child: step 3976, time parent_time + candidate_dt.",
                "Do not authorize 100-day rollout or cadence selection.",
            ],
            "no_go": [
                "Do not preserve saturation numerically at the cost of changing component mass.",
                "Do not alter p_ref to hide pressure-refresh inventory mismatch.",
                "Do not clip cell mass or saturation during reconciliation.",
                "Do not redistribute mass between cells during same-time pressure reconciliation.",
                "Do not count thermodynamic saturation reconciliation as a transport transition.",
                "Do not update time, accepted step, cumulative injection, or cumulative production during refresh.",
                "Do not use hidden under-relaxation if direct Picard fails; block and audit first.",
                "Do not proceed to long-horizon rollout before the one-transition R3-R4 validation passes.",
            ],
            "next_milestone": NEXT,
        }

        gate(
            "amendment_cellwise_mass_primary",
            amendment["primary_conserved_refresh_quantity"]
            == "cellwise Cartesian CO2 component mass array",
        )
        gate(
            "amendment_allows_same_time_saturation_change",
            amendment["saturation_semantics"][
                "reconciled_saturation_may_differ_from_parent"
            ] is True,
        )
        gate(
            "amendment_forbids_refresh_mass_redistribution",
            amendment["capacity_policy_during_reconciliation"][
                "mass_redistribution_authorized"
            ] is False,
        )
        gate(
            "amendment_preserves_time_and_step",
            amendment["reconciliation_invariants"][
                "physical_time_days_unchanged"
            ] is True
            and amendment["reconciliation_invariants"][
                "accepted_step_index_unchanged"
            ] is True,
        )
        gate(
            "amendment_requires_fixed_point",
            amendment["same_time_pressure_saturation_fixed_point"][
                "convergence_required_before_flow_epoch_commit"
            ] is True,
        )

        workflow_rows = [
            {
                "order": 1,
                "stage": "FREEZE_PARENT_CELLWISE_COMPONENT_MASS",
                "time_advance": False,
                "mass_change": False,
            },
            {
                "order": 2,
                "stage": "TOTAL_MOBILITY_FROM_WORKING_SATURATION",
                "time_advance": False,
                "mass_change": False,
            },
            {
                "order": 3,
                "stage": "FINITE_VOLUME_PRESSURE_SOLVE",
                "time_advance": False,
                "mass_change": False,
            },
            {
                "order": 4,
                "stage": "EOS_INVERT_FIXED_MASS_TO_RECONCILED_SATURATION",
                "time_advance": False,
                "mass_change": False,
            },
            {
                "order": 5,
                "stage": "PRESSURE_SATURATION_CONVERGENCE_CHECK",
                "time_advance": False,
                "mass_change": False,
            },
            {
                "order": 6,
                "stage": "CONSERVATIVE_DARCY_FLUX_POLLOCK_TOF_OVERLAP",
                "time_advance": False,
                "mass_change": False,
            },
            {
                "order": 7,
                "stage": "FLOW_EPOCH_COMMIT",
                "time_advance": False,
                "mass_change": False,
            },
            {
                "order": 8,
                "stage": "R3R4_SAME_DT_TRANSPORT_TRIAL",
                "time_advance": "ONLY_IF_ACCEPTED",
                "mass_change": "ONLY_FROM_PHYSICAL_INJECTION_MINUS_PRODUCTION",
            },
        ]

        closure = {
            "milestone": MILESTONE,
            "status": STATUS,
            "all_gates_passed": all(v["passed"] for v in gates.values()),
            "gate_count": len(gates),
            "architecture_amendment_only": True,
            "solver_execution_performed": False,
            "canonical_state_created": False,
            "physical_time_advanced": False,
            "accepted_step_index_advanced": False,
            "R3R3_predecessor_remains_immutable": True,
            "R3R3_pressure_refresh_semantics_amended": True,
            "next_milestone": NEXT,
        }

        files = {
            "PAD_Stream_V16E41R3R3R1_Reconciliation_Architecture_Amendment.json":
                json_bytes(amendment),
            "V16E41R3R3R1_Reconciliation_Workflow.csv": csv_bytes(workflow_rows),
            "V16E41R3R3R1_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
            "V16E41R3R3R1_Final_Closure.json": json_bytes(closure),
        }

        immutable_publish(out, files)

        manifest = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "V16E41R3R3R1_Artifact_Manifest.csv":
                manifest.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_publish(
            out,
            {"V16E41R3R3R1_Artifact_Manifest.csv": csv_bytes(manifest)},
        )

        print("\n" + "=" * 154)
        print("PAD-Stream V16E-41-R3-R3-R1: PASS")
        print("=" * 154)
        print(f"{'Status':66}: {STATUS}")
        print(
            f"{'Primary conserved refresh quantity':66}: "
            "cellwise Cartesian CO2 component mass"
        )
        print(
            f"{'Same-time saturation may change':66}: True"
        )
        print(
            f"{'Pressure/saturation fixed point required':66}: True"
        )
        print(
            f"{'Refresh advances physical time':66}: False"
        )
        print(
            f"{'Refresh changes injection/production ledgers':66}: False"
        )
        print(
            f"{'Mass redistribution during refresh authorized':66}: False"
        )
        print(f"{'Next':66}: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "MASS_CONSERVATIVE_PRESSURE_REFRESH_RECONCILIATION_ARCHITECTURE_BLOCKED",
            "failed_stage": failed_stage,
            "exception": repr(exc),
            "gates": gates,
        }
        data = json_bytes(report)
        p = blocked / "V16E41R3R3R1_Blocked_Architecture_Amendment.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "V16E41R3R3R1_Blocked_Architecture_Amendment_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        p.write_bytes(data)
        print("\n" + "=" * 154)
        print("PAD-Stream V16E-41-R3-R3-R1: BLOCKED")
        print("=" * 154)
        print("Report      :", p)
        print("Failed stage:", failed_stage)
        print("Exception   :", repr(exc))
        return 2


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))

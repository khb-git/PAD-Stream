from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

DEVELOPMENT_FLOW_REFRESH_REFERENCE_DAYS = 5.0
PRESSURE_SEED_PRODUCTION_POLICY = "TEMPORAL_SEED_EXACT_FV_CORRECTION"
LEARNED_PRESSURE_CHECKPOINT_POLICY = "RESEARCH_REFERENCE_ONLY_NOT_PRODUCTION_AUTHORIZED"

HARD_REFRESH_TRIGGERS = (
    "RESTART_OR_INITIALIZATION",
    "WELL_OR_CONTROL_CHANGE",
    "POST_OBSERVATION_CHECKPOINT",
    "CAPACITY_PREFLIGHT_REJECTION",
)

@dataclass(frozen=True)
class RuntimeDecision:
    action: str
    reason: str
    flow_epoch_age_days: float
    refresh_reference_days: float
    pressure_seed_policy: str
    learned_pressure_checkpoint_policy: str

def decide_runtime_action(
    current_time_days: float,
    flow_epoch_origin_day: float,
    *,
    hard_triggers: Iterable[str] = (),
    refresh_reference_days: float = DEVELOPMENT_FLOW_REFRESH_REFERENCE_DAYS,
) -> RuntimeDecision:
    age = float(current_time_days) - float(flow_epoch_origin_day)
    if age < -1.0e-12:
        raise ValueError("flow_epoch_origin_after_current_time")
    active = tuple(str(x) for x in hard_triggers)
    unknown = [x for x in active if x not in HARD_REFRESH_TRIGGERS]
    if unknown:
        raise ValueError(f"unknown_hard_refresh_trigger:{unknown}")

    if active:
        return RuntimeDecision(
            action="FULL_FLOW_REFRESH",
            reason="HARD_TRIGGER:" + ",".join(active),
            flow_epoch_age_days=age,
            refresh_reference_days=float(refresh_reference_days),
            pressure_seed_policy=PRESSURE_SEED_PRODUCTION_POLICY,
            learned_pressure_checkpoint_policy=LEARNED_PRESSURE_CHECKPOINT_POLICY,
        )

    if age >= float(refresh_reference_days) - 1.0e-12:
        return RuntimeDecision(
            action="FULL_FLOW_REFRESH",
            reason="DEVELOPMENT_FLOW_EPOCH_AGE_REFERENCE_REACHED",
            flow_epoch_age_days=age,
            refresh_reference_days=float(refresh_reference_days),
            pressure_seed_policy=PRESSURE_SEED_PRODUCTION_POLICY,
            learned_pressure_checkpoint_policy=LEARNED_PRESSURE_CHECKPOINT_POLICY,
        )

    return RuntimeDecision(
        action="REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT",
        reason="FLOW_EPOCH_FRESH",
        flow_epoch_age_days=age,
        refresh_reference_days=float(refresh_reference_days),
        pressure_seed_policy=PRESSURE_SEED_PRODUCTION_POLICY,
        learned_pressure_checkpoint_policy=LEARNED_PRESSURE_CHECKPOINT_POLICY,
    )

def production_refresh_sequence() -> tuple[str, ...]:
    return (
        "PRESERVE_CELLWISE_CARTESIAN_CO2_COMPONENT_MASS",
        "TEMPORAL_PRESSURE_SEED",
        "EXACT_FINITE_VOLUME_PRESSURE_CORRECTION",
        "DIRECT_SPSOLVE_REFERENCE_OR_FALLBACK_IF_REQUIRED",
        "CONSERVATIVE_DARCY_FACE_FLUXES",
        "EXACT_POLLOCK_STREAMLINES",
        "EXACT_TIME_OF_FLIGHT_WEIGHTS_CONNECTIVITY",
        "REFRESHED_FLOW_CFL",
    )

def transport_reuse_sequence() -> tuple[str, ...]:
    return (
        "SAMPLE_CURRENT_CARTESIAN_STATE_TO_E37A_COMPONENT_MASS_CVS",
        "HYBRID10_PARENT_ANCHORED_INCREMENT_ON_ELIGIBLE_ROUTES",
        "EXACT_E37A_FALLBACK_ON_ALL_OTHER_ROUTES",
        "EXACT_PARENT_PLUS_INLET_MINUS_OUTLET_COMPONENT_MASS_BUDGET",
        "BOX_CONSTRAINED_CONSERVATIVE_MASS_PROJECTION",
        "SINGLE_COMMON_E37A_CV_TO_CARTESIAN_MAPBACK",
        "CONSERVATIVE_CARTESIAN_CAPILLARY_REDISTRIBUTION",
        "CREATE_NEXT_RECURRENT_STATE",
    )

def self_test() -> None:
    a=decide_runtime_action(75.1828299829973,75.0)
    assert a.action=="REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT"
    b=decide_runtime_action(80.0,75.0)
    assert b.action=="FULL_FLOW_REFRESH"
    c=decide_runtime_action(75.2,75.0,hard_triggers=("WELL_OR_CONTROL_CHANGE",))
    assert c.action=="FULL_FLOW_REFRESH"
    assert "TEMPORAL_PRESSURE_SEED" in production_refresh_sequence()
    assert "HYBRID10_PARENT_ANCHORED_INCREMENT_ON_ELIGIBLE_ROUTES" in transport_reuse_sequence()

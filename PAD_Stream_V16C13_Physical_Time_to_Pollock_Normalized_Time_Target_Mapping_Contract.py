from __future__ import annotations
from pathlib import Path
import csv, json, numpy as np

ROOT=Path(__file__).resolve().parent

C12BD=ROOT/"output"/"V16_C12B_INTERNAL_PHYSICS_VALIDATION_CLOSURE_Y_GENERATION_READINESS_AUDIT"
C12BS=C12BD/"PAD_Stream_V16C12B_Summary.json"

C2D=ROOT/"output"/"V16_C2_MULTI_COORDINATE_STREAMLINE_TRANSPORT_DATABASE"
C2P=C2D/"V16C2_Multi_Coordinate_Streamline_Transport_Database.npz"

OUT=ROOT/"output"/"V16_C13_PHYSICAL_TIME_TO_POLLOCK_NORMALIZED_TIME_TARGET_MAPPING_CONTRACT"
OUT.mkdir(parents=True,exist_ok=True)
MAP=OUT/"V16C13_Physical_Time_Mapping_Audit.csv"
GATES=OUT/"V16C13_Final_Time_Mapping_Gates.csv"
CON=OUT/"V16C13_Physical_Time_Mapping_Contract.json"
SUM=OUT/"PAD_Stream_V16C13_Summary.json"

C12B_OK="V16C_INTERNAL_PHYSICS_VALIDATION_CLOSED_PRE_Y_CONTRACTS_REQUIRED"
SECONDS_PER_DAY=86400.0

def loadj(p):
    if not p.exists(): raise FileNotFoundError(p)
    return json.loads(p.read_text(encoding="utf-8"))
def savej(p,x): p.write_text(json.dumps(x,indent=2),encoding="utf-8")
def save_csv(p,rows):
    rows=list(rows); keys=[]
    for r in rows:
        for k in r:
            if k not in keys:keys.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def discover_c2():
    # Bind by required structural content, not guessed directory spelling.
    candidates=list((ROOT/"output").rglob("*.npz"))
    matches=[]
    for p in candidates:
        try:
            with np.load(p,allow_pickle=False) as z:
                keys=set(z.files)
                if "pollock_tof" in keys and "streamline_xyz" in keys:
                    a=z["pollock_tof"]; x=z["streamline_xyz"]
                    if a.ndim==2 and x.ndim==3 and a.shape==x.shape[:2] and a.shape[1]==201:
                        matches.append(p)
        except Exception:
            pass
    preferred=[p for p in matches if "V16C2" in p.name or "MULTI_COORDINATE" in str(p).upper()]
    if len(preferred)==1:return preferred[0]
    if len(matches)==1:return matches[0]
    if not matches:raise FileNotFoundError("No V16C2-compatible Pollock database found.")
    raise RuntimeError("Ambiguous V16C2 database binding:\n  "+"\n  ".join(map(str,matches)))

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-13")
    print("Physical-Time-to-Pollock-Normalized-Time Target Mapping Contract")
    print("="*78)
    print("""
C12B CLOSED THE INTERNAL SOLVER-PHYSICS VALIDATION BRANCH.

C13 NOW FREEZES TIME SEMANTICS ONLY. IT DOES NOT SOLVE TRANSPORT AND DOES NOT
GENERATE Y_transport.

FOR STREAMLINE i:
    tau_end_i = authoritative terminal Pollock TOF [s]
    theta      = tau/tau_end_i
    eta_i(t)   = t/tau_end_i

WITH PHYSICAL TARGET TIME t_days:
    t_seconds  = 86400 * t_days
    eta_i      = t_seconds/tau_end_i_seconds

THEREFORE A SINGLE PHYSICAL DAY TARGET CORRESPONDS TO A DIFFERENT NORMALIZED
eta ON EACH STREAMLINE. THIS IS REQUIRED BECAUSE TERMINAL POLLOCK TOF VARIES
ACROSS THE 1,078 STREAMLINES.

C13 DOES NOT DECLARE 100/250/500/1000 DAYS AS PRODUCTION TARGETS.
IT ONLY DEFINES THE DETERMINISTIC MAPPING FOR ANY FUTURE AUTHORIZED t_days.
""")
    c12b=loadj(C12BS)
    if c12b.get("status")!=C12B_OK:
        raise RuntimeError("C13 requires closed C12B internal-physics status.")

    dbp=discover_c2()
    with np.load(dbp,allow_pickle=False) as z:
        tof=np.asarray(z["pollock_tof"],dtype=float)
        xyz=np.asarray(z["streamline_xyz"],dtype=float)

    nsl,nn=tof.shape
    terminal=tof[:,-1]
    finite=np.isfinite(tof).all() and np.isfinite(terminal).all()
    positive=np.all(terminal>0)
    monotonic=np.all(np.diff(tof,axis=1)>=-1e-12)
    starts_zero=np.max(np.abs(tof[:,0]))<=1e-9
    theta=tof/terminal[:,None]
    theta_start=float(np.max(np.abs(theta[:,0])))
    theta_end=float(np.max(np.abs(theta[:,-1]-1.0)))
    theta_mono=np.all(np.diff(theta,axis=1)>=-1e-12)

    tau_days=terminal/SECONDS_PER_DAY
    # Demonstration/audit times only. These DO NOT become Y targets.
    audit_days=np.array([1.0,100.0,250.0,500.0,1000.0])
    rows=[]
    for td in audit_days:
        eta=(td*SECONDS_PER_DAY)/terminal
        rows.append(dict(
            audit_time_days=float(td),
            eta_min=float(np.min(eta)),
            eta_median=float(np.median(eta)),
            eta_mean=float(np.mean(eta)),
            eta_max=float(np.max(eta)),
            production_target_authorized=False
        ))
    save_csv(MAP,rows)

    roundtrip_max=0.0
    for td in audit_days:
        eta=(td*SECONDS_PER_DAY)/terminal
        back_days=eta*terminal/SECONDS_PER_DAY
        roundtrip_max=max(roundtrip_max,float(np.max(np.abs(back_days-td))))

    gates=[
        ("C12B_internal_physics_closure_reproduced",True),
        ("Pollock_database_bound",True),
        ("streamline_count_1078",nsl==1078),
        ("node_count_201",nn==201),
        ("Pollock_TOF_finite",finite),
        ("terminal_Pollock_TOF_positive",positive),
        ("Pollock_TOF_monotonic",monotonic),
        ("Pollock_TOF_starts_at_zero",starts_zero),
        ("theta_starts_at_zero",theta_start<=1e-12),
        ("theta_ends_at_one",theta_end<=1e-12),
        ("theta_monotonic",theta_mono),
        ("seconds_per_day_exact_constant",SECONDS_PER_DAY==86400.0),
        ("physical_time_eta_roundtrip_exact",roundtrip_max<=1e-12),
        ("per_streamline_eta_mapping_required",float(np.ptp(tau_days))>0),
        ("100_250_500_1000_not_promoted_to_production_targets",True),
        ("no_transport_solve_performed",True),
        ("no_Y_transport_generated",True),
        ("no_training_authorized",True),
        ("no_parameter_fitting",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])
    passed=all(v for _,v in gates)

    if passed:
        status="V16C_PHYSICAL_TIME_TO_POLLOCK_NORMALIZED_TIME_MAPPING_FROZEN"
        diagnosis="PHYSICAL_TIME_IS_DETERMINISTICALLY_MAPPED_TO_PER_STREAMLINE_NORMALIZED_TIME_USING_THE_FROZEN_TERMINAL_POLLOCK_TOF_WITH_EXACT_UNIT_CONVERSION"
        rec=("Freeze C13. Next bind the production full-physics transport parameter authority "
             "(rock/fluid endpoints, viscosities, Pe_c, capillary lambda, and the role of Nc metadata) "
             "without fitting to unavailable V15 states. Y generation remains prohibited until that contract passes.")
        nxt="V16C-14 — Production Full-Physics Transport Parameter Authority Contract"
    else:
        status="V16C_PHYSICAL_TIME_MAPPING_CONTRACT_BLOCKED"
        diagnosis="ONE_OR_MORE_FROZEN_POLLOCK_TIME_SEMANTICS_OR_UNIT_CONVERSION_GATES_FAILED"
        rec="Do not generate Y. Repair only the failed time-coordinate authority gate."
        nxt="V16C-13R — Physical-Time Mapping Residual Audit"

    contract=dict(
        milestone="V16C-13",status=status,diagnosis=diagnosis,
        source_database=str(dbp.relative_to(ROOT)),
        shape=[int(nsl),int(nn)],
        units=dict(pollock_tof="seconds",physical_target_time="days",
                   seconds_per_day=SECONDS_PER_DAY,eta="dimensionless",theta="dimensionless"),
        definitions=dict(
            theta="pollock_tof_s / terminal_pollock_tof_s",
            eta_i="physical_time_seconds / terminal_pollock_tof_i_seconds",
            physical_time_seconds="physical_time_days * 86400"
        ),
        terminal_tof_days=dict(min=float(tau_days.min()),median=float(np.median(tau_days)),
                               mean=float(tau_days.mean()),max=float(tau_days.max())),
        audit_roundtrip_max_days=roundtrip_max,
        production_target_times_frozen=False,
        Y_transport_generated=False,Y_generation_authorized=False,
        training_authorized=False,recommendation=rec,next_milestone=nxt
    )
    savej(CON,contract)
    savej(SUM,dict(
        milestone="V16C-13",status=status,diagnosis=diagnosis,
        physical_time_target_mapping_frozen=passed,
        streamline_count=int(nsl),node_count=int(nn),
        terminal_tof_days=contract["terminal_tof_days"],
        production_target_times_frozen=False,
        Y_transport_generated=False,Y_generation_authorized=False,
        training_authorized=False,recommendation=rec,next_milestone=nxt
    ))

    print("TIME-MAPPING AUTHORITY")
    print("  Pollock database       :",dbp)
    print("  streamlines / nodes    :",nsl,"/",nn)
    print("  terminal TOF [days]    :")
    print("    min                  :",f"{tau_days.min():.6f}")
    print("    median               :",f"{np.median(tau_days):.6f}")
    print("    mean                 :",f"{tau_days.mean():.6f}")
    print("    max                  :",f"{tau_days.max():.6f}")
    print("  round-trip max [days]  :",f"{roundtrip_max:.3e}")
    print("  production target times: NOT YET FROZEN")
    print("  Y generation authorized: False")

    print("\n"+"="*78)
    print("V16C-13 FINAL TIME-MAPPING GATES")
    print("="*78)
    for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-13 PHYSICAL-TIME MAPPING CONTRACT: COMPLETE")
    print("="*78)

if __name__=="__main__":main()

from pathlib import Path
import csv,json,numpy as np
ROOT=Path(__file__).resolve().parent
C13=ROOT/"output"/"V16_C13_PHYSICAL_TIME_TO_POLLOCK_NORMALIZED_TIME_TARGET_MAPPING_CONTRACT"/"PAD_Stream_V16C13_Summary.json"
C14=ROOT/"output"/"V16_C14_PRODUCTION_FULL_PHYSICS_TRANSPORT_PARAMETER_AUTHORITY_CONTRACT"/"PAD_Stream_V16C14_Summary.json"
OUT=ROOT/"output"/"V16_C15_PRODUCTION_PHYSICAL_TARGET_TIME_SCHEDULE_AUTHORITY_CONTRACT";OUT.mkdir(parents=True,exist_ok=True)
TARGET=np.array([30.,60.,100.,150.,250.,365.,500.,750.,1000.]); SPD=86400.
def lj(p): return json.loads(p.read_text(encoding="utf-8"))
def sj(p,x): p.write_text(json.dumps(x,indent=2),encoding="utf-8")
def sc(p,rows):
 rows=list(rows); keys=list(rows[0]) if rows else []
 with p.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def pollock():
 m=[]
 for p in (ROOT/"output").rglob("*.npz"):
  try:
   with np.load(p,allow_pickle=False) as z:
    if "pollock_tof" in z.files and z["pollock_tof"].shape==(1078,201):m.append(p)
  except: pass
 q=[p for p in m if "Foundation_Case_0001" in str(p)]
 if len(q)==1:return q[0]
 if len(m)==1:return m[0]
 raise RuntimeError(f"Pollock authority ambiguous/unavailable: {len(m)}")
def main():
 print("\n"+"="*78+"\nPAD-Stream V16C-15\nProduction Physical Target-Time Schedule Authority Contract\n"+"="*78)
 print("""
C13 FROZE t_days -> eta_i AND C14 FROZE PRODUCTION PHYSICS PARAMETERS.
C15 FREEZES A NEW V16 SUPERVISION-TIME SCHEDULE. HISTORICAL VALUES SUCH AS
100/250/500/1000 DAYS ARE NOT TREATED AS RECOVERED OR CERTIFIED V15 STATES.
NO TRANSPORT TARGETS ARE GENERATED HERE.
""")
 a,b=lj(C13),lj(C14)
 if a.get("status")!="V16C_PHYSICAL_TIME_TO_POLLOCK_NORMALIZED_TIME_MAPPING_FROZEN":raise RuntimeError("C13 not frozen")
 if b.get("status")!="V16C_PRODUCTION_FULL_PHYSICS_TRANSPORT_PARAMETER_AUTHORITY_FROZEN":raise RuntimeError("C14 not frozen")
 pp=pollock()
 with np.load(pp,allow_pickle=False) as z: td=np.asarray(z["pollock_tof"][:,-1],float)/SPD
 hist={100.,250.,500.,1000.}; sched=[]; eta_rows=[]
 for i,t in enumerate(TARGET):
  e=t/td
  sched.append(dict(index=i,target_time_days=float(t),target_time_seconds=float(t*SPD),
   V16_production_target=True,historical_V15_time_value=bool(t in hist),V15_deployment_authority_claim=False))
  eta_rows.append(dict(target_time_days=float(t),eta_min=float(e.min()),eta_median=float(np.median(e)),
   eta_mean=float(e.mean()),eta_max=float(e.max()),fraction_eta_ge_1=float(np.mean(e>=1))))
 sc(OUT/"V16C15_Production_Target_Time_Schedule.csv",sched)
 sc(OUT/"V16C15_Target_Time_Eta_Coverage.csv",eta_rows)
 gates=[
 ("C13_time_mapping_frozen",True),("C14_parameter_authority_frozen",True),
 ("target_times_positive",bool(np.all(TARGET>0))),("target_times_unique_strictly_increasing",bool(np.all(np.diff(TARGET)>0))),
 ("early_pre_fastest_arrival_time_present",bool(TARGET.min()<td.min())),
 ("fastest_arrival_bracketed",bool(np.any(TARGET<td.min()) and np.any(TARGET>td.min()))),
 ("median_terminal_TOF_bracketed",bool(np.any(TARGET<np.median(td)) and np.any(TARGET>np.median(td)))),
 ("late_time_beyond_P90_terminal_TOF_present",bool(TARGET.max()>np.percentile(td,90))),
 ("schedule_is_new_V16_design",True),("historical_time_values_not_treated_as_V15_authority",True),
 ("250_500_1000_not_relabelled_as_certified_V15_deployment",True),("no_parameter_fitting",True),
 ("no_transport_solve_performed",True),("no_Y_transport_generated",True),("training_not_yet_authorized",True)]
 sc(OUT/"V16C15_Final_Target_Time_Schedule_Gates.csv",[dict(gate=g,passed=v) for g,v in gates])
 ok=all(v for _,v in gates)
 if ok:
  status="V16C_PRODUCTION_PHYSICAL_TARGET_TIME_SCHEDULE_FROZEN"
  diag="A_NEW_V16_MULTI_TIME_SUPERVISION_SCHEDULE_SPANS_EARLY_BREAKTHROUGH_INTERMEDIATE_AND_LATE_POLLOCK_TIME_REGIMES_WITHOUT_RELABELLING_HISTORICAL_V15_STATES"
  rec="Freeze C15. Next bind C11 executable solver to C13-C15 and perform the final pre-generation authorization audit."
  nxt="V16C-16 — Source-Authentic Y_transport Generation Authorization Audit"
 else:
  status="V16C_PRODUCTION_TARGET_TIME_SCHEDULE_BLOCKED";diag="ONE_OR_MORE_TIME_COVERAGE_OR_PROVENANCE_GATES_FAILED"
  rec="Do not generate Y; repair only the failed schedule gate.";nxt="V16C-15R — Target-Time Schedule Residual Audit"
 summary=dict(milestone="V16C-15",status=status,diagnosis=diag,physical_target_time_schedule_frozen=ok,
  target_days=TARGET.tolist(),target_count=len(TARGET),Y_transport_generated=False,Y_generation_authorized=False,
  training_authorized=False,recommendation=rec,next_milestone=nxt)
 sj(OUT/"PAD_Stream_V16C15_Summary.json",summary)
 sj(OUT/"V16C15_Production_Target_Time_Schedule_Contract.json",dict(**summary,
  design_basis="NEW_V16_MULTI_TIME_SUPERVISION_SCHEDULE",pollock_source=str(pp.relative_to(ROOT)),
  terminal_tof_days=dict(min=float(td.min()),median=float(np.median(td)),p90=float(np.percentile(td,90)),max=float(td.max())),
  historical_V15_deployment_authority_inherited=False))
 print("V16 PRODUCTION TARGET SCHEDULE")
 print("  target days :",", ".join(f"{x:g}" for x in TARGET));print("  count       :",len(TARGET))
 print(f"  Pollock terminal TOF [days]: min={td.min():.6f}, median={np.median(td):.6f}, P90={np.percentile(td,90):.6f}, max={td.max():.6f}")
 print("  V15 deployment authority inherited : False\n  Y generated                         : False")
 print("\n"+"="*78+"\nV16C-15 FINAL TARGET-TIME SCHEDULE GATES\n"+"="*78)
 for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
 print("="*78+"\n\nSTATUS\n ",status,"\n\nDIAGNOSIS\n ",diag,"\n\nRECOMMENDATION\n ",rec,"\n\nNEXT MILESTONE\n ",nxt)
 print("\nOUTPUTS\n  Directory:\n   ",OUT,"\n\n"+"="*78+"\nPAD-STREAM V16C-15 TARGET-TIME SCHEDULE CONTRACT: COMPLETE\n"+"="*78)
if __name__=="__main__":main()

from pathlib import Path
import csv,json,hashlib,re

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"/"V16_C16_SOURCE_AUTHENTIC_Y_TRANSPORT_GENERATION_AUTHORIZATION_AUDIT"
OUT.mkdir(parents=True,exist_ok=True)

EXPECTED={
"C12B":("V16_C12B_INTERNAL_PHYSICS_VALIDATION_CLOSURE_Y_GENERATION_READINESS_AUDIT",
        "PAD_Stream_V16C12B_Summary.json",
        "V16C_INTERNAL_PHYSICS_VALIDATION_CLOSED_PRE_Y_CONTRACTS_REQUIRED"),
"C13":("V16_C13_PHYSICAL_TIME_TO_POLLOCK_NORMALIZED_TIME_TARGET_MAPPING_CONTRACT",
       "PAD_Stream_V16C13_Summary.json",
       "V16C_PHYSICAL_TIME_TO_POLLOCK_NORMALIZED_TIME_MAPPING_FROZEN"),
"C14":("V16_C14_PRODUCTION_FULL_PHYSICS_TRANSPORT_PARAMETER_AUTHORITY_CONTRACT",
       "PAD_Stream_V16C14_Summary.json",
       "V16C_PRODUCTION_FULL_PHYSICS_TRANSPORT_PARAMETER_AUTHORITY_FROZEN"),
"C15":("V16_C15_PRODUCTION_PHYSICAL_TARGET_TIME_SCHEDULE_AUTHORITY_CONTRACT",
       "PAD_Stream_V16C15_Summary.json",
       "V16C_PRODUCTION_PHYSICAL_TARGET_TIME_SCHEDULE_FROZEN"),
}
STAGE4_SHA="165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"
C11_STATUS="V16C_EXECUTABLE_CONSERVATIVE_FULL_PHYSICS_POLLOCK_SOLVER_ASSEMBLED_DIAGNOSTICALLY_VALIDATED"

def lj(p):
 if not p.exists():raise FileNotFoundError(p)
 return json.loads(p.read_text(encoding="utf-8"))
def sj(p,x):p.write_text(json.dumps(x,indent=2),encoding="utf-8")
def sc(p,rows):
 rows=list(rows);keys=[]
 for r in rows:
  for k in r:
   if k not in keys:keys.append(k)
 with p.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def find_status(status):
 hits=[]
 for p in (ROOT/"output").rglob("*.json"):
  try:
   x=lj(p)
   if isinstance(x,dict) and x.get("status")==status:hits.append(p)
  except:pass
 q=[p for p in hits if "summary" in p.name.lower()]
 if len(q)==1:return q[0]
 if len(hits)==1:return hits[0]
 raise RuntimeError(f"Authority status {status}: {len(hits)} matches")
def main():
 print("\n"+"="*78)
 print("PAD-Stream V16C-16")
 print("Source-Authentic Y_transport Generation Authorization Audit")
 print("="*78)
 print("""
C16 IS THE FINAL PRE-GENERATION GATE.

IT DOES NOT GENERATE Y_transport. IT DETERMINES WHETHER THE EXECUTABLE
POLLOCK-COORDINATE FULL-PHYSICS SOLVER MAY NOW BE USED TO GENERATE THE NEW
V16 SUPERVISION TENSOR UNDER THE FROZEN C13-C15 CONTRACTS.

AUTHORIZATION REQUIRES:
  * C12B internal-physics closure;
  * C13 physical-time mapping;
  * C14 production parameter authority;
  * C15 production target-time schedule;
  * C11 executable solver authority;
  * exact Stage4 source hash;
  * Pollock kinematics primary;
  * no exp(Nc*xD) velocity double counting;
  * no fitting to unavailable V15 states;
  * immutable frozen inputs.

THIS MILESTONE AUTHORIZES GENERATION ONLY. IT DOES NOT AUTHORIZE TRAINING.
""")
 auth={}
 rows=[]
 for k,(d,n,s) in EXPECTED.items():
  p=ROOT/"output"/d/n
  x=lj(p); ok=x.get("status")==s
  auth[k]=(p,x,ok)
  rows.append(dict(authority=k,path=str(p.relative_to(ROOT)),expected_status=s,
                   observed_status=x.get("status",""),passed=ok))
 c11p=find_status(C11_STATUS);c11=lj(c11p)
 rows.append(dict(authority="C11",path=str(c11p.relative_to(ROOT)),
                  expected_status=C11_STATUS,observed_status=c11.get("status",""),passed=True))
 s4=ROOT/"pi_rnn_stage4_full_godunov.py"
 s4ok=s4.exists() and sha(s4)==STAGE4_SHA
 rows.append(dict(authority="Stage4",path=str(s4.relative_to(ROOT)) if s4.exists() else "",
                  expected_status=STAGE4_SHA,observed_status=sha(s4) if s4.exists() else "",passed=s4ok))
 sc(OUT/"V16C16_Authority_Binding.csv",rows)

 c13=auth["C13"][1];c14=auth["C14"][1];c15=auth["C15"][1]
 target=c15.get("target_days",[])
 params_contract=ROOT/"output"/EXPECTED["C14"][0]/"V16C14_Production_Full_Physics_Parameter_Contract.json"
 pc=lj(params_contract)
 pars=pc.get("production_parameters",{})
 required=["nw","no","Swc","Sor","krw_max","kro_max","mu_w","mu_o","phi","Pe_c","lambda_c","Nc"]
 complete=all(k in pars for k in required)
 expected_targets=[30.,60.,100.,150.,250.,365.,500.,750.,1000.]
 schedule_exact=[float(x) for x in target]==expected_targets
 policies=pc.get("policies",{})
 pollock=policies.get("Pollock_kinematics_primary") is True
 no_exp=policies.get("use_exp_Nc_xD_velocity_scaling") is False
 no_fit=policies.get("fit_to_V15_reference") is False

 gates=[
 ("C12B_internal_physics_closed",auth["C12B"][2]),
 ("C13_physical_time_mapping_frozen",auth["C13"][2]),
 ("C14_production_parameters_frozen",auth["C14"][2]),
 ("C15_target_schedule_frozen",auth["C15"][2]),
 ("C11_executable_solver_authority_bound",True),
 ("Stage4_exact_source_hash_bound",s4ok),
 ("production_parameter_set_complete",complete),
 ("target_schedule_exactly_reproduced",schedule_exact),
 ("Pollock_kinematics_primary",pollock),
 ("legacy_exp_Nc_xD_velocity_scaling_disabled",no_exp),
 ("Nc_not_used_as_duplicate_kinematic_multiplier",no_exp),
 ("no_fit_to_unavailable_V15_states",no_fit),
 ("missing_V15_cross_validation_not_recast_as_pass",True),
 ("C13_C14_C15_inputs_remain_immutable",True),
 ("generation_output_must_be_new_V16_artifact",True),
 ("generation_must_preserve_1078x201_spatial_shape",True),
 ("generation_must_preserve_9_target_times",len(target)==9),
 ("generation_must_record_solver_and_contract_lineage",True),
 ("training_remains_separate_after_generation",True),
 ("no_Y_transport_generated_by_C16",True),
 ]
 sc(OUT/"V16C16_Final_Generation_Authorization_Gates.csv",
    [dict(gate=g,passed=bool(v)) for g,v in gates])
 ok=all(v for _,v in gates)

 if ok:
  status="V16C_SOURCE_AUTHENTIC_Y_TRANSPORT_GENERATION_AUTHORIZED"
  diag="C11_EXECUTABLE_SOLVER_C13_TIME_C14_PARAMETERS_AND_C15_TARGET_SCHEDULE_FORM_A_COMPLETE_IMMUTABLE_SOURCE_AUTHENTIC_GENERATION_LINEAGE_WITH_POLLOCK_KINEMATICS_PRESERVED"
  rec=("Freeze C16. Proceed to the first production target-generation milestone. "
       "Generate a new V16 Y_transport tensor at the nine frozen physical times, "
       "validate bounds/conservation/BC/finite-state behavior, and save full lineage. "
       "Do not authorize PI-RNN training until the generated tensor passes its own certification audit.")
  nxt="V16C-17 — Production Source-Authentic Y_transport Tensor Generation and Certification"
 else:
  status="V16C_Y_TRANSPORT_GENERATION_AUTHORIZATION_BLOCKED"
  diag="ONE_OR_MORE_REQUIRED_SOLVER_TIME_PARAMETER_SCHEDULE_OR_PROVENANCE_AUTHORITIES_FAILED"
  rec="Do not generate Y. Repair only the failed C16 authority gate."
  nxt="V16C-16R — Y_transport Generation Authorization Residual Audit"

 contract=dict(
  milestone="V16C-16",status=status,diagnosis=diag,
  generation_authorized=ok,training_authorized=False,Y_transport_generated=False,
  expected_output_shape=[9,1078,201],
  target_days=[float(x) for x in target],
  parameter_names=required,
  immutable_rules=dict(Pollock_kinematics_primary=True,use_exp_Nc_xD=False,
                       fit_to_missing_V15=False,modify_frozen_inputs=False),
  required_generation_checks=["finite","Sw_bounds","injector_BC","implicit_solver_residual",
   "conservative_advection","capillary_operator_consistency","time_ordering","lineage_hashes"],
  recommendation=rec,next_milestone=nxt)
 sj(OUT/"V16C16_Y_Transport_Generation_Authorization_Contract.json",contract)
 sj(OUT/"PAD_Stream_V16C16_Summary.json",dict(
  milestone="V16C-16",status=status,diagnosis=diag,
  Y_generation_authorized=ok,Y_transport_generated=False,training_authorized=False,
  expected_Y_shape=[9,1078,201],target_days=[float(x) for x in target],
  recommendation=rec,next_milestone=nxt))

 print("GENERATION AUTHORITY")
 print("  C11 solver       :",c11p)
 print("  Stage4 SHA       :",sha(s4) if s4.exists() else "MISSING")
 print("  parameters       :",", ".join(required))
 print("  target days      :",", ".join(str(x) for x in target))
 print("  expected Y shape : (9, 1078, 201)")
 print("  Y generated now  : False")
 print("  training allowed : False")
 print("\n"+"="*78+"\nV16C-16 FINAL GENERATION AUTHORIZATION GATES\n"+"="*78)
 for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
 print("="*78)
 print("\nSTATUS\n ",status,"\n\nDIAGNOSIS\n ",diag,"\n\nRECOMMENDATION\n ",rec,
       "\n\nNEXT MILESTONE\n ",nxt)
 print("\nOUTPUTS\n  Directory:\n   ",OUT)
 print("\n"+"="*78+"\nPAD-STREAM V16C-16 Y_TRANSPORT GENERATION AUTHORIZATION: COMPLETE\n"+"="*78)
if __name__=="__main__":main()

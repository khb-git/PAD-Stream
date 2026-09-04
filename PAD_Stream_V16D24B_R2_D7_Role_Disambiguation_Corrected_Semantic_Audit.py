#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,sys
R=Path(__file__).resolve().parent
S=R/"output"/"V16_D24B_R1_D7_RUNNER_ROLE_DISAMBIGUATION"/"PAD_Stream_V16D24B_R1_Summary.json"
SSHA="c01360838c3327e3418f204d6d295b2c8670caaf80cca4e7d8b6f40bf6218b11"
D7A=R/"PAD_Stream_V16D7A_SourceBound_SG2_SG3_SG4_Adapter_and_Case0002_Pilot.py"
D7B=R/"PAD_Stream_V16D7B_Full_Frozen_Case0002_0025_SourceBound_SG2_SG3_SG4_Flow_Ensemble_Execution.py"
A_SHA="3bdb11fe60703c05ffd27ea2eab122badcf2894406ff7399f9f55af261038452"
B_SHA="d2a736039bd34ec5bc3272ebf0ab9908f47c28cdc1bd91ca74d8d76ec366922b"
O=R/"output"/"V16_D24B_R2_CORRECTED_D7_ROLE_AUDIT";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-24B-R2")
 print("Corrected Semantic D7A/D7B Role Audit");print("="*78)
 if sha(S)!=SSHA:raise RuntimeError("R1 summary SHA mismatch")
 if sha(D7A)!=A_SHA or sha(D7B)!=B_SHA:raise RuntimeError("D7 source SHA mismatch")
 a=D7A.read_text(encoding="utf-8",errors="replace")
 b=D7B.read_text(encoding="utf-8",errors="replace")
 # Correct semantic criterion: D7A may mention the ensemble range as provenance.
 # Its execution role is established by its actual CASE binding, artifact, and explicit
 # "RUNS ONLY CASE 0002" assertion—not by absence of the token 0025.
 a_evidence={
 "explicit_runs_only_case0002":bool(re.search(r"D7A\s+RUNS\s+ONLY\s+CASE\s+0002",a,re.I)),
 "single_CASE_binding":bool(re.search(r"\bCASE\s*=.*Case_0002_Geology\.npz",a,re.I)),
 "single_pilot_artifact":bool(re.search(r"Case0002_SG2_SG3_SG4_Pilot\.npz",a,re.I)),
 "authorizes_full24_after_pilot":bool(re.search(r"PILOT_CERTIFIED_FULL_24CASE_FLOW_EXECUTION_AUTHORIZED",a))}
 b_evidence={
 "requires_D7A_certified_status":bool(re.search(r"if\s+a\[.?[\"']status[\"'].*PILOT_CERTIFIED_FULL_24CASE_FLOW_EXECUTION_AUTHORIZED",b,re.I)),
 "cases_directory_bound":bool(re.search(r"\bCASES\s*=.*CASE0002_0025",b,re.I)),
 "ensemble_manifest":bool(re.search(r"Flow_Ensemble_Manifest\.csv",b,re.I)),
 "ensemble_certification_status":bool(re.search(r"CASE0002_0025_SOURCEBOUND_FLOW_ENSEMBLE_CERTIFIED",b))}
 gates={"R1_SHA_exact":True,"D7A_SHA_exact":True,"D7B_SHA_exact":True,
 "D7A_execution_role_single_case_pilot":all(a_evidence.values()),
 "D7B_execution_role_full_ensemble":all(b_evidence.values()),
 "D7B_is_downstream_of_D7A":b_evidence["requires_D7A_certified_status"],
 "token_0025_in_D7A_not_used_as_negative_role_test":True,
 "roles_complementary_and_sequential":all(a_evidence.values()) and all(b_evidence.values())}
 authority={"D7A":"authoritative prior source-bound single-case pilot adapter/execution pattern",
 "D7B":"authoritative downstream full-ensemble execution pattern",
 "D24C":"must derive reference-equivalence + one TRAIN pilot from D7A mechanics",
 "later_batch":"may derive 36-case batch mechanics from D7B only after D24C passes",
 "correction":"R1 false-negative arose because it incorrectly required token 0025 to be absent from D7A; D7A legitimately mentions 0002-0025 in upstream D6 provenance/status text."}
 ap=O/"V16D24B_R2_Corrected_D7_Execution_Authority.json";ap.write_text(json.dumps(
 {"authority":authority,"D7A_evidence":a_evidence,"D7B_evidence":b_evidence,"gates":gates},indent=2))
 if all(gates.values()):
  status="V16D_D7A_SINGLE_PILOT_D7B_FULL_ENSEMBLE_ROLES_CORRECTLY_BOUND_D24C_EXECUTION_AUTHORIZED"
  nxt="V16D-24C — Derive D7A Mechanics for 500/2000 Adapter Equivalence + Geology0026 TRAIN New-Control Pilot"
 else:
  status="V16D_D7_ROLE_BINDING_STILL_BLOCKED"
  nxt="Do not execute new-control flow."
 sp=O/"PAD_Stream_V16D24B_R2_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-24B-R2","status":status,
 "authority_sha256":sha(ap),"gates":gates,"next_milestone":nxt},indent=2))
 print("\nD7A EXECUTION EVIDENCE")
 for k,v in a_evidence.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nD7B EXECUTION EVIDENCE")
 for k,v in b_evidence.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not all(gates.values()):sys.exit(2)
if __name__=="__main__":main()

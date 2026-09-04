#!/usr/bin/env python3
from pathlib import Path
import ast,hashlib,json,re,sys
R=Path(__file__).resolve().parent
D24B=R/"output"/"V16_D24B_EXACTVARIABLE_ADAPTER_REFERENCE_AND_TRAIN_PILOT"
S24B=D24B/"PAD_Stream_V16D24B_Summary.json"
S24BSHA="434a4bebf2e2385c9ba605cd5850263b8b47830ff1de03964663a379b59046b0"
CANDS={
"D7A":(R/"PAD_Stream_V16D7A_SourceBound_SG2_SG3_SG4_Adapter_and_Case0002_Pilot.py",
"3bdb11fe60703c05ffd27ea2eab122badcf2894406ff7399f9f55af261038452"),
"D7B":(R/"PAD_Stream_V16D7B_Full_Frozen_Case0002_0025_SourceBound_SG2_SG3_SG4_Flow_Ensemble_Execution.py",
"d2a736039bd34ec5bc3272ebf0ab9908f47c28cdc1bd91ca74d8d76ec366922b")}
O=R/"output"/"V16_D24B_R1_D7_RUNNER_ROLE_DISAMBIGUATION";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def analyze(tag,p):
 t=p.read_text(encoding="utf-8",errors="replace")
 facts={"tag":tag,"path":str(p),"sha256":sha(p)}
 facts["mentions_case0002"]=bool(re.search(r"Case\s*0002|CASE0002|case_id.*0002",t,re.I))
 facts["mentions_0025"]=bool(re.search(r"0025",t))
 facts["has_loop"]=bool(re.search(r"\bfor\b.+\bin\b",t))
 facts["mentions_manifest"]=bool(re.search(r"manifest",t,re.I))
 facts["mentions_full_ensemble"]=bool(re.search(r"full.*ensemble|ensemble.*execution|0002.*0025",t,re.I|re.S))
 facts["source_names"]={x: x in t for x in ["PAD_Stream_V15SG2_Anisotropic_Transmissibility.py","PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py","PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"]}
 # Extract status/next literals for role evidence.
 facts["status_lines"]=[l.strip() for l in t.splitlines() if "STATUS" in l or "status" in l.lower() and ("V16D" in l or "CERT" in l)]
 facts["case_range_lines"]=[l.strip() for l in t.splitlines() if re.search(r"0002|0025|pilot|ensemble",l,re.I)][:80]
 return facts
def main():
 print("="*78);print("PAD-Stream V16D-24B-R1")
 print("D7 Flow-Runner Role Disambiguation + Execution Authority Binding");print("="*78)
 if sha(S24B)!=S24BSHA:raise RuntimeError("D24B summary SHA mismatch")
 facts=[];gates={"D24B_SHA_exact":True}
 for tag,(p,w) in CANDS.items():
  ok=p.exists() and sha(p)==w;gates[f"{tag}_SHA_exact"]=ok
  if not ok:continue
  f=analyze(tag,p);facts.append(f)
  print(f"\n{tag}: {p.name}")
  print("  SHA:",f["sha256"])
  print("  Case0002:",f["mentions_case0002"],"0025:",f["mentions_0025"],
        "manifest:",f["mentions_manifest"],"full ensemble evidence:",f["mentions_full_ensemble"])
  for l in f["case_range_lines"][:12]:print("   ",l[:220])
 # Role is determined semantically from filenames + source evidence, not numerical closeness.
 d={x["tag"]:x for x in facts}
 gates["D7A_is_single_case_pilot_role"]=("D7A" in d and d["D7A"]["mentions_case0002"] and not d["D7A"]["mentions_0025"])
 gates["D7B_is_full_ensemble_role"]=("D7B" in d and d["D7B"]["mentions_case0002"] and d["D7B"]["mentions_0025"] and d["D7B"]["mentions_manifest"])
 gates["roles_are_complementary_not_ambiguous"]=gates["D7A_is_single_case_pilot_role"] and gates["D7B_is_full_ensemble_role"]
 # Freeze authority: D7A for reference/single-pilot adapter mechanics; D7B only after pilot for batch ensemble mechanics.
 authority={"reference_and_single_train_pilot_runner":"D7A",
 "future_36case_batch_runner":"D7B",
 "reason":"D7A is the prior source-bound single-Case0002 pilot adapter; D7B is the subsequent full Case0002–0025 ensemble execution. They are sequential roles, not competing alternatives.",
 "prohibitions":["do not choose by numerical closeness","do not rewrite SG2/SG3/SG4 physics",
 "do not use D7B batch execution before D24C reference+TRAIN pilot certification"]}
 ap=O/"V16D24B_R1_D7_Execution_Authority.json";ap.write_text(json.dumps({"authority":authority,"evidence":facts},indent=2))
 gates["execution_authority_frozen"]=all(gates.values())
 if all(gates.values()):
  status="V16D_D7_RUNNER_ROLES_DISAMBIGUATED_D7A_REFERENCE_PILOT_D7B_FUTURE_BATCH_D24C_EXECUTION_AUTHORIZED"
  nxt="V16D-24C — Source-Preserving 500/2000 Reference Reproduction + Geology0026 TRAIN New-Control Pilot"
 else:
  status="V16D_D7_RUNNER_ROLE_DISAMBIGUATION_BLOCKED"
  nxt="Inspect D7A/D7B role evidence; do not execute new-control flow."
 sp=O/"PAD_Stream_V16D24B_R1_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-24B-R1","status":status,
 "authority_sha256":sha(ap),"gates":gates,"next_milestone":nxt},indent=2))
 print("\nAUTHORITY")
 print("  D7A -> reference reproduction + single TRAIN pilot")
 print("  D7B -> future 36-case batch execution after pilot certification")
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not all(gates.values()):sys.exit(2)
if __name__=="__main__":main()

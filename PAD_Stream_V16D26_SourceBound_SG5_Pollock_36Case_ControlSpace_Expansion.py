#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,sys

R=Path(__file__).resolve().parent
D25=R/"output"/"V16_D25_36CASE_CONTROLSPACE_SG2_SG3_SG4_FLOW_ENSEMBLE"/"PAD_Stream_V16D25_Summary.json"
D25SHA="55c5831bf0f0166355ec3542a221280bededf08004700ffedf13a7ae56538e45"
SG5=R/"PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
# Historical frozen SG5 SHA is deliberately discovered/bound from prior certified V16D runner,
# not guessed here.
CANDS=[
 R/"PAD_Stream_V16D8B_Full_Case0002_0025_SourceBound_SG5_Pollock_Ensemble_Execution.py",
 R/"PAD_Stream_V16D8R1_Case0002_SourceBound_SG5_Pollock_Pilot.py",
]
OUT=R/"output"/"V16_D26_SOURCEBOUND_SG5_36CASE_CONTROLSPACE_EXPANSION";OUT.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-26")
 print("Source-Bound SG5 Pollock 36-Case Control-Space Expansion — Execution Binding");print("="*78)
 gates={"D25_SHA_exact":D25.exists() and sha(D25)==D25SHA,"SG5_exists":SG5.exists()}
 d25=json.loads(D25.read_text()) if gates["D25_SHA_exact"] else {}
 gates["D25_status_authorizes_Pollock"]=d25.get("status")=="V16D_36CASE_CONTROLSPACE_SG2_SG3_SG4_FLOW_ENSEMBLE_GENERATED_CERTIFIED_POLLOCK_EXPANSION_AUTHORIZED"
 found=[]
 for c in CANDS:
  if c.exists():
   t=c.read_text(encoding="utf-8",errors="replace")
   evidence=[x.strip() for x in t.splitlines() if any(k in x for k in ("construct_face_pore_velocities","build_seeds","trace_streamlines","validate_streamlines","SG5"))]
   found.append({"path":str(c),"sha256":sha(c),"evidence":evidence[:100]})
 print("\nPRIOR SOURCE-BOUND SG5 RUNNER CANDIDATES")
 for x in found:
  print(" ",Path(x["path"]).name,x["sha256"])
  for e in x["evidence"][:12]:print("    ",e[:220])
 gates["prior_SG5_runner_found"]=bool(found)
 # Extract an explicit 64-hex SG5 hash associated with SG5 from source if available.
 hashes=[]
 for x in found:
  text=Path(x["path"]).read_text(encoding="utf-8",errors="replace")
  for line in text.splitlines():
   if "SG5" in line.upper():
    hashes += re.findall(r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])',line,re.I)
 hashes=list(dict.fromkeys(hashes))
 actual=sha(SG5) if SG5.exists() else None
 gates["SG5_hash_source_bound"]=actual in hashes
 print("\nSG5 BINDING")
 print("  actual SG5 SHA-256 :",actual)
 print("  source-evidenced hashes:",hashes)
 # D25 artifact census only; locked artifacts may exist but are not interpreted.
 case_dir=R/"output"/"V16_D25_36CASE_CONTROLSPACE_SG2_SG3_SG4_FLOW_ENSEMBLE"/"cases"
 arts=sorted(case_dir.glob("*_Flow.npz")) if case_dir.exists() else []
 gates["D25_36_flow_artifacts_exist"]=len(arts)==36
 ids=[a.stem for a in arts]
 gates["36_unique_flow_artifacts"]=len(set(ids))==36
 gates["no_transport_executed_in_D26_binding"]=True
 gates["no_training"]=True
 ok=all(gates.values())
 status="V16D_SG5_EXACT_SOURCE_AND_36CASE_FLOW_INPUTS_BOUND_D26R1_POLLOCK_EXECUTION_AUTHORIZED" if ok else "V16D_D26_SG5_BINDING_BLOCKED"
 nxt="V16D-26R1 — Execute exact source-bound SG5 Pollock streamline/TOF pipeline across all 36 Foundation Cases" if ok else "Resolve SG5 source/hash or D25 artifact binding; do not execute Pollock."
 summary={"milestone":"V16D-26","status":status,"D25_sha256":D25SHA,"SG5":{"path":str(SG5),"sha256":actual,"source_evidenced_hashes":hashes},
 "prior_runner_candidates":found,"flow_artifact_count":len(arts),"gates":gates,"next_milestone":nxt}
 sp=OUT/"PAD_Stream_V16D26_Summary.json";sp.write_text(json.dumps(summary,indent=2))
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

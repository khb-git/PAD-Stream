#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parent
D26=ROOT/"output"/"V16_D26_SOURCEBOUND_SG5_36CASE_CONTROLSPACE_EXPANSION"/"PAD_Stream_V16D26_Summary.json"
D26SHA="3fd0ad787c54b2702a8c13739a5ea8bb476c309bfff9663f4b473a68685af455"
D8B=ROOT/"PAD_Stream_V16D8B_Full_Case0002_0025_SourceBound_SG5_Pollock_Ensemble_Execution.py"
D8BSHA="f8669eb3dd9f5b886dc7cde5e4c26b0c85c1a1967386901a76d51301ed9a32ec"
SG5=ROOT/"PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
R1=ROOT/"output"/"V16_D8R1_EXACT_SG5_SEED_CONTAINER_ADAPTER_REPAIR_CASE0002_POLLOCK_PILOT"/"PAD_Stream_V16D8R1_Summary.json"
OUT=ROOT/"output"/"V16_D26_R1_R1_SG5_RUNTIME_HASH_PROVENANCE_REPAIR";OUT.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-26-R1-R1")
 print("SG5 Runtime Hash Provenance Repair — Resolve D26 False-Negative Binding");print("="*78)
 gates={"D26_blocked_summary_SHA_exact":D26.exists() and sha(D26)==D26SHA,
        "D8B_SHA_exact":D8B.exists() and sha(D8B)==D8BSHA,
        "SG5_exists":SG5.exists(),"D8R1_summary_exists":R1.exists()}
 if not all(gates.values()):
  print(gates);raise RuntimeError("authority pre-gate failure")
 d8=D8B.read_text(encoding="utf-8",errors="replace")
 # Prove D8B does runtime binding rather than embedding a literal hash.
 runtime_expr=bool(re.search(r'if\s+sha\(SG5\)\s*!=\s*r\["SG5_sha256"\]',d8))
 gates["D8B_runtime_SG5_hash_binding_expression_found"]=runtime_expr
 r=json.loads(R1.read_text())
 print("\nD8R1 STATUS:",r.get("status"))
 print("D8R1 SG5_sha256:",r.get("SG5_sha256"))
 actual=sha(SG5)
 print("Actual SG5 SHA-256:",actual)
 gates["D8R1_status_certified"]=r.get("status")=="V16D_CASE0002_SOURCEBOUND_SG5_POLLOCK_PILOT_CERTIFIED_FULL_24CASE_POLLOCK_EXECUTION_AUTHORIZED"
 gates["SG5_SHA_matches_D8R1_runtime_authority"]=r.get("SG5_sha256")==actual
 # D8B downstream lineage must be consistent with same R1 summary and source-native path.
 for token in ("construct_face_pore_velocities","build_seeds","trace_streamlines","validate_streamlines"):
  gates["D8B_has_"+token]=token in d8
 # Confirm D26 failure cause: parser searched only same lines as token SG5 for literal 64-hex.
 d26=json.loads(D26.read_text())
 gates["D26_failed_only_hash_binding_among_core_bindings"]=(
  d26.get("gates",{}).get("SG5_hash_source_bound") is False and
  all(v for k,v in d26.get("gates",{}).items() if k!="SG5_hash_source_bound"))
 report={"milestone":"V16D-26-R1-R1",
 "diagnosis":"D26 was a conservative audit false-negative. D8B does not embed the SG5 SHA literal on an SG5 line; it reads D8R1 summary at runtime and enforces sha(SG5) == r['SG5_sha256']. Therefore the authoritative hash must be recovered from the exact D8R1 summary, not regex-extracted from D8B source.",
 "D8B_sha256":sha(D8B),"D8R1_summary_sha256":sha(R1),"SG5_actual_sha256":actual,
 "D8R1_recorded_SG5_sha256":r.get("SG5_sha256"),"gates":gates}
 rp=OUT/"V16D26_R1_SG5_Runtime_Hash_Provenance_Report.json";rp.write_text(json.dumps(report,indent=2))
 ok=all(gates.values())
 status="V16D_SG5_RUNTIME_HASH_PROVENANCE_REPAIRED_EXACT_SOURCE_BOUND_D26R2_EXECUTOR_GENERATION_AUTHORIZED" if ok else "V16D_D26_R1_SG5_PROVENANCE_REPAIR_BLOCKED"
 nxt="V16D-26-R2 — Generate exact D8B-derived 36-case SG5 Pollock executor" if ok else "Inspect D8R1/D8B lineage; do not execute Pollock."
 sp=OUT/"PAD_Stream_V16D26_R1_R1_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-26-R1-R1","status":status,"report_sha256":sha(rp),"gates":gates,"next_milestone":nxt},indent=2))
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

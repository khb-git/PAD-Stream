#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, io, json, subprocess, sys
from pathlib import Path
from typing import Any

M="POSTV16-AV4-PIVOT-P3-R1-R6-R1"
NAME="Day375 Publication-Only Technical Closure Audit"
PASS="AV4PIVOTP3R1R6R1_DAY375_PUBLICATION_ONLY_TECHNICAL_CLOSURE_PASS_NO_STATE_MUTATION"
BLOCK="AV4PIVOTP3R1R6R1_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="1bb53810a39a7f250eef4cd9ec56ad96f12be226"
R6="PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R6_Day370_to_Day375_SecondObservation_Pilot.py"
R6_BLOB="e89eb57b753ba546b0ca8ec948042c7cab3537f6"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
R6_REL=BASE/"POSTV16_AV4_PIVOT_P3_R1_R6_Day370_to_Day375_SecondObservation_Pilot_and_Exact_Flow_Diagnostic"
R6_BLOCK_REL=BASE/"POSTV16_AV4_PIVOT_P3_R1_R6_BLOCKED"
R6_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R6_Summary.json"
R6_DECISION="POSTV16_AV4_PIVOT_P3_R1_R6_Decision_Contract.json"
R6_STATE="POSTV16_AV4_PIVOT_P3_R1_R6_Day0375_Accepted_Dense_State.npz"
R6_DIAG="POSTV16_AV4_PIVOT_P3_R1_R6_Day0375_Exact_Flow_Diagnostic.npz"
R6_METRICS="POSTV16_AV4_PIVOT_P3_R1_R6_Day0375_Exact_Flow_Diagnostic_Metrics.json"
R6_AUDIT="POSTV16_AV4_PIVOT_P3_R1_R6_Atomic_Step_Audit.csv"
R6_GATES="POSTV16_AV4_PIVOT_P3_R1_R6_Final_Gate_Matrix.csv"
R6_MANIFEST="POSTV16_AV4_PIVOT_P3_R1_R6_Artifact_Manifest.csv"
R6_BLOCK="POSTV16_AV4_PIVOT_P3_R1_R6_Blocked_Report.json"
R6_STATUS="AV4PIVOTP3R1R6_DAY370_TO_DAY375_SECOND_OBSERVATION_PILOT_EXACT_FLOW_DIAGNOSTIC_PASS"
R6_CLASS="P3R1_REPAIRED_DAY370_TO_DAY375_SECOND_OBSERVATION_TRANSPORT_AND_EXACT_FLOW_DIAGNOSTIC_CERTIFIED_RESTART_SAFE_CARRY_FORWARD_NO_GENERIC_STAGE2_FALLBACK_DAY380_PILOT_AUTHORIZED"
R6_BLOCK_STATUS="AV4PIVOTP3R1R6_TECHNICAL_OR_AUTHORITY_BLOCK"
R6_STATE_SHA="89b69ed69ef2c67babcf1e52ead0add950f366379c849f23645be5b18dc5d7ac"
R6_DIAG_SHA="43957d890246452bcfc78467f19aba4f48feaaf9a0ffa58aababe7e7189e9c31"

OUT_TOKEN="POSTV16_AV4_PIVOT_P3_R1_R6_R1"
OUT_REL=BASE/(OUT_TOKEN+"_Day375_Publication_Only_Technical_Closure_Audit")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
AUDIT=f"{OUT_TOKEN}_Closure_Audit.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"
MASS_TOL=1e-6

class GateError(RuntimeError): pass

def gt(root,*args): return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()
def js(path): return json.loads(path.read_text(encoding="utf-8"))
def csvr(path):
    with path.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))
def csvb(rows):
    if not rows: return b""
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    s=io.StringIO(newline=""); w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(rows)
    return s.getvalue().encode()
def jb(o): return (json.dumps(o,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()

def verify_manifest(directory,filename):
    out={}
    for row in csvr(directory/filename):
        p=directory/row["file"]
        if not p.is_file(): raise GateError(f"manifest_missing:{p.name}")
        actual=sha(p)
        if actual!=row["sha256"]: raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size!=int(row["bytes"]): raise GateError(f"manifest_bytes:{p.name}")
        out[p.name]=actual
    if not out: raise GateError("manifest_empty")
    return out

def selftest():
    assert PARENT=="1bb53810a39a7f250eef4cd9ec56ad96f12be226"
    assert "DAY380_PILOT_AUTHORIZED" in R6_CLASS
    assert len(R6_STATE_SHA)==64 and len(R6_DIAG_SHA)==64
    print("POSTV16 AV4 PIVOT P3-R1-R6-R1 structural self-test: PASS")

def main(project_root:Path,drive_root:Path)->int:
    root=project_root.resolve(); drive=drive_root.resolve()
    r6dir=drive/R6_REL; r6blockdir=drive/R6_BLOCK_REL; out=drive/OUT_REL; blocked=drive/BLOCK_REL
    stage="preflight"; gates=[]
    def gate(name,cond,detail=None):
        ok=bool(cond); gates.append({"stage":stage,"gate":name,"pass":ok,"detail":"" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+("" if detail is None else f" -- {detail}"),flush=True)
        if not ok: raise GateError(name)
    try:
        print("="*180)
        print("POSTV16-AV4-PIVOT-P3-R1-R6-R1 — DAY375 PUBLICATION-ONLY TECHNICAL CLOSURE AUDIT")
        print("READ-ONLY. NO TRANSPORT OR FLOW-DIAGNOSTIC RERUN.")
        print("="*180)

        stage="preexisting_state_firewall"
        gate("no_preexisting_R6R1_PASS",not (out/SUMMARY).exists())
        gate("no_preexisting_R6R1_BLOCK",not (blocked/f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage="repository_authority"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_R6_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        src=root/R6
        gate("R6_source_present",src.is_file(),str(src))
        gate("R6_source_blob_exact",gt(root,"hash-object",str(src))==R6_BLOB,gt(root,"hash-object",str(src)))

        stage="R6_artifact_authority"
        gate("R6_output_dir_exists",r6dir.is_dir(),str(r6dir))
        for fn in [R6_SUMMARY,R6_DECISION,R6_STATE,R6_DIAG,R6_METRICS,R6_AUDIT,R6_GATES,R6_MANIFEST]:
            gate(f"R6_artifact_present:{fn}",(r6dir/fn).is_file())
        mm=verify_manifest(r6dir,R6_MANIFEST)
        gate("manifest_state_SHA_exact",mm.get(R6_STATE)==R6_STATE_SHA,mm.get(R6_STATE))
        gate("manifest_diagnostic_SHA_exact",mm.get(R6_DIAG)==R6_DIAG_SHA,mm.get(R6_DIAG))

        s=js(r6dir/R6_SUMMARY); d=js(r6dir/R6_DECISION); m=js(r6dir/R6_METRICS)
        gate("R6_status_exact",s.get("status")==R6_STATUS,s.get("status"))
        gate("R6_classification_exact",s.get("classification")==R6_CLASS,s.get("classification"))
        gate("summary_state_SHA_exact",s.get("Day375_state_sha256")==R6_STATE_SHA,s.get("Day375_state_sha256"))
        gate("summary_diagnostic_SHA_exact",s.get("Day375_diagnostic_sha256")==R6_DIAG_SHA,s.get("Day375_diagnostic_sha256"))
        gate("state_file_SHA_exact",sha(r6dir/R6_STATE)==R6_STATE_SHA,sha(r6dir/R6_STATE))
        gate("diagnostic_file_SHA_exact",sha(r6dir/R6_DIAG)==R6_DIAG_SHA,sha(r6dir/R6_DIAG))
        gate("final_day_375_exact",abs(float(s["pilot_final_day"])-375.0)<=1e-12,s["pilot_final_day"])
        gate("start_day_370_exact",abs(float(s["pilot_start_day"])-370.0)<=1e-12,s["pilot_start_day"])
        gate("frozen_transport_epoch_365",abs(float(s["frozen_transport_flow_epoch_day"])-365.0)<=1e-12,s["frozen_transport_flow_epoch_day"])
        gate("no_generic_fallback",int(s["generic_XY1_fallback_step_count"])==0,s["generic_XY1_fallback_step_count"])
        gate("global_source_sink",abs(float(s["Day375_global_source_sink_residual_kg"]))<=MASS_TOL,s["Day375_global_source_sink_residual_kg"])
        gate("split_identity",float(s["Day375_split_identity_max_abs_error_kg"])<=MASS_TOL,s["Day375_split_identity_max_abs_error_kg"])
        gate("CV_edge_equality",float(s["Day375_CV_edge_equality_max_abs_error_kg"])<=MASS_TOL,s["Day375_CV_edge_equality_max_abs_error_kg"])

        gate("metrics_day_375",abs(float(m["diagnostic_day"])-375.0)<=1e-12,m["diagnostic_day"])
        gate("metrics_no_fixed_point",m["diagnostic_same_time_fixed_point_executed"] is False)
        gate("metrics_no_transport_feedback",m["diagnostic_transport_feedback_executed"] is False)
        gate("pressure_residual_small",float(m["pressure_linear_relative_residual"])<=1e-10,m["pressure_linear_relative_residual"])
        gate("flow_local_error_small",float(m["flow_local_relative_L2_error"])<=1e-10,m["flow_local_relative_L2_error"])
        gate("flow_global_mismatch_small",float(m["flow_global_relative_mismatch"])<=1e-10,m["flow_global_relative_mismatch"])
        gate("streamline_count_exact",int(m["streamline_count"])==1078,m["streamline_count"])
        gate("nodes_per_streamline_exact",int(m["nodes_per_streamline"])==201,m["nodes_per_streamline"])

        gate_rows=csvr(r6dir/R6_GATES)
        bad=[r for r in gate_rows if str(r.get("pass","")).strip().lower() not in ("true","1")]
        gate("R6_gate_matrix_all_pass",len(bad)==0,bad[:2])

        stage="R6_decision_authority"
        gate("decision_status_exact",d.get("status")==R6_STATUS,d.get("status"))
        gate("decision_classification_exact",d.get("classification")==R6_CLASS,d.get("classification"))
        gate("Day380_authorized",d.get("Day375_to_Day380_repaired_pilot_authorized") is True)
        gate("full_rerun_locked",d.get("P3_R1_full_rerun_authorized") is False)
        gate("P4_locked",d.get("P4_authorized") is False)
        gate("scientific_failure_false",d.get("scientific_failure_declared") is False)
        gate("one_shot_no_feedback",d.get("Day375_exact_diagnostic_is_one_shot_no_feedback") is True)
        gate("carry_forward_preserved",d.get("positive_halo_carry_forward_prior_accepted_shell_support_seed_preserved") is True)

        stage="R6_publication_BLOCK_closure"
        bp=r6blockdir/R6_BLOCK
        gate("R6_BLOCK_exists",bp.is_file(),str(bp))
        b=js(bp)
        gate("R6_BLOCK_status_exact",b.get("status")==R6_BLOCK_STATUS,b.get("status"))
        gate("R6_BLOCK_failed_stage_publication",b.get("failed_stage")=="publication",b.get("failed_stage"))
        gate("R6_BLOCK_exception_exact",b.get("exception")=='NameError("name \'day370_state_sha\' is not defined")',b.get("exception"))
        gate("R6_BLOCK_no_authoritative_mutation",b.get("authoritative_physics_state_mutated") is False and b.get("authoritative_physical_time_advanced") is False)

        st=src.read_text(encoding="utf-8")
        gate("source_defines_day375_state_sha","day375_state_sha = sha(staging / FINAL_STATE)" in st)
        gate("summary_uses_day375_state_sha",'"Day375_state_sha256": day375_state_sha' in st)
        bad_print='print("Day370 state SHA256                    :", day370_state_sha, flush=True)'
        gate("source_contains_bad_final_print",bad_print in st)
        gate("final_rename_precedes_bad_print",st.find("staging.rename(out)") < st.find(bad_print),[st.find("staging.rename(out)"),st.find(bad_print)])

        stage="publication"
        out.mkdir(parents=True,exist_ok=False)
        closure_class="P3R1_R6_DAY375_SCIENCE_ARTIFACTS_AND_DECISION_CERTIFIED_PUBLICATION_PRINT_NAMEERROR_CLOSED_DAY380_PILOT_AUTHORITY_PRESERVED"
        recommendation=("Execute the authorized Day375-to-Day380 third-observation pilot from the certified R6 Day375 accepted state, "
                        "using the same restart-safe carry-forward fast paths and one-shot exact diagnostic semantics; "
                        "do not rerun Day370-toDay375, and keep the full Day365-to500 sweep and P4 locked.")
        rows=gates+[{"stage":"closure","gate":"R6_publication_print_NameError_closed_without_science_rerun","pass":True,
                     "detail":repr("final console print typo only; published R6 science artifacts remain authoritative")}]
        (out/AUDIT).write_bytes(csvb(rows))
        summary={"milestone":M,"name":NAME,"status":PASS,"classification":closure_class,
                 "repository_parent_R6_commit":PARENT,"R6_source_blob":R6_BLOB,"R6_status_bound":R6_STATUS,
                 "R6_classification_bound":R6_CLASS,"R6_prior_BLOCK_status":R6_BLOCK_STATUS,
                 "R6_prior_BLOCK_closed_as_publication_only_console_print_NameError":True,
                 "R6_transport_rerun_executed":False,"R6_flow_diagnostic_rerun_executed":False,
                 "authoritative_physics_state_mutated":False,"authoritative_physical_time_advanced":False,
                 "Day375_state_sha256":R6_STATE_SHA,"Day375_diagnostic_sha256":R6_DIAG_SHA,
                 "Day375_global_source_sink_residual_kg":float(s["Day375_global_source_sink_residual_kg"]),
                 "Day375_split_identity_max_abs_error_kg":float(s["Day375_split_identity_max_abs_error_kg"]),
                 "Day375_CV_edge_equality_max_abs_error_kg":float(s["Day375_CV_edge_equality_max_abs_error_kg"]),
                 "generic_XY1_fallback_step_count":int(s["generic_XY1_fallback_step_count"]),
                 "accepted_atomic_steps":int(s["accepted_atomic_steps"]),
                 "Day375_to_Day380_repaired_pilot_authorized":True,
                 "P3_R1_full_rerun_authorized":False,"P4_authorized":False,
                 "recommended_next_action":recommendation}
        decision={"milestone":M,"status":PASS,"classification":closure_class,
                  "R6_science_PASS_remains_authoritative":True,
                  "R6_Day375_state_remains_authoritative":True,
                  "R6_Day375_diagnostic_remains_authoritative":True,
                  "R6_prior_BLOCK_is_scientific_failure":False,
                  "R6_prior_BLOCK_closed_as_publication_only_console_print_NameError":True,
                  "R6_transport_rerun_required":False,"R32_recurrent_semantics_remain_authoritative":True,
                  "frozen_transport_flow_epoch_day":365.0,
                  "positive_halo_carry_forward_prior_accepted_shell_support_seed_preserved":True,
                  "dual_pricing_global_closure_required_for_positive_halo":True,
                  "frozen_generic_XY1_lexicographic_fallback_must_be_preserved":True,
                  "Day375_exact_diagnostic_is_one_shot_no_feedback":True,
                  "Day375_to_Day380_repaired_pilot_authorized":True,
                  "P3_R1_full_rerun_authorized":False,"P4_authorized":False,
                  "recommended_next_action":recommendation}
        (out/SUMMARY).write_bytes(jb(summary)); (out/DECISION).write_bytes(jb(decision))
        mr=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!=MANIFEST: mr.append({"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size})
        (out/MANIFEST).write_bytes(csvb(mr))
        print("="*180); print(M,"PASS"); print("Classification:",closure_class)
        print("R6 transport rerun executed: False"); print("R6 publication BLOCK closed: True")
        print("Day375->Day380 authorized: True"); print("Full P3-R1 rerun authorized: False"); print("P4 authorized: False")
        print("="*180)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        rp=blocked/f"{OUT_TOKEN}_Blocked_Report.json"
        if not rp.exists():
            rp.write_bytes(jb({"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),
                               "authoritative_physics_state_mutated":False,"authoritative_physical_time_advanced":False,
                               "Day375_to_Day380_repaired_pilot_authorized":False,
                               "P3_R1_full_rerun_authorized":False,"P4_authorized":False,"gates_completed":gates}))
        print(M,"TECHNICAL / AUTHORITY BLOCK"); print("Stage:",stage); print("Exception:",repr(exc)); return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test: selftest(); raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))

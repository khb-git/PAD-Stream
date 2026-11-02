#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,inspect,io,json,subprocess,sys
from pathlib import Path
from typing import Any

M="POSTV16-AV4-PIVOT-P2-R6-R29-R2-R1-R1-R1"
NAME="False-Absence Assertion Technical Closure + Direct R29-R1-R1 Authority Recovery"
PASS="AV4PIVOTP2R6R29R2R1R1R1_FALSE_ABSENCE_ASSERTION_TECHNICAL_CLOSURE_PASS_DIRECT_R29R1R1_AUTHORITY_RECOVERED_R29R3_NEXT"
BLOCK="AV4PIVOTP2R6R29R2R1R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="8c2b5419283ed440b0d68d38bd33e931ceec01d7"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3=Path("post_v16")/RID/"POSTV16_AV3_Corey_Relperm_Heterogeneity"

DT_DAYS=0.03721673128859954
TARGET_DAY=375.0372167312886

R29R2R1R1_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R29_R2_R1_R1_BLOCKED"
R29R2R1R1_BLOCK="POSTV16_AV4_PIVOT_P2_R6_R29_R2_R1_R1_Blocked_Report.json"
R29R2R1R1_BLOCK_STATUS="AV4PIVOTP2R6R29R2R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"
R29R2R1R1_BLOCK_STAGE="real_drive_authority"
R29R2R1R1_BLOCK_EXCEPTION="GateError('original_R29R1R1_summary_absent_on_authoritative_drive')"

R29R1R1_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_Comprehensive_Technical_Closure_PoreVolume_Diagnostic"
R29R1R1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_Summary.json"
R29R1R1_CLOSURE="POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_Comprehensive_Technical_Closure_Contract.json"
R29R1R1_DECISION="POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_Decision_Contract.json"
R29R1R1_GATES="POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_Final_Gate_Matrix.csv"
R29R1R1_MANIFEST="POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_Artifact_Manifest.csv"
R29R1R1_STATUS="AV4PIVOTP2R6R29R1R1_COMPREHENSIVE_TECHNICAL_CLOSURE_PASS_R29R1_DIAGNOSTIC_RECOVERED_NO_SCIENCE_STATE_MUTATION"
R29R1R1_CLASSIFICATION="R6R29R1R1_TECHNICAL_CLOSURE_RECOVERS_R29R1_DIAGNOSTIC_EXACT_STRING_FLOAT_FORMAT_GATE_ONLY_AV4_HETEROGENEOUS_PARENT_VALID_R29R2_REPAIR_DESIGN_NEXT"
R29R1_BLOCK_SHA256="cde61dec85e1d183ee07329ce30329e9f7e9c88d62ee798ac648cec129933ab5"
R29_FAIL_SHA256="1522b39b9e2c89cacf8899c07bcedf61a841a57ca61cc47bd41fbcd818b02209"

R28_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R28_FrozenFlow_Transport_DeltaMapback_ResidualWell_Coupling_Protocol_Freeze"
R28_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R28_Summary.json"
R28_DECISION="POSTV16_AV4_PIVOT_P2_R6_R28_Decision_Contract.json"
R28_MANIFEST="POSTV16_AV4_PIVOT_P2_R6_R28_Artifact_Manifest.csv"

A6E_REL=BASE_AV3/"POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE="POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_STATE_SHA256="f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

R29R2R1R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R2_R1_R1_Authoritative_Drive_Artifact_Recovery_and_Design_Closure.py"
R29R2R1R1_RUNNER_BLOB="e0cfa467dbc680e9820b9dca3bbaf65eb62de5f1"
E37A="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
A2E="PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB="79a8969233b72b4543edd382a0c3d1028c6dca09"
SOURCE_BLOBS={R29R2R1R1_RUNNER:R29R2R1R1_RUNNER_BLOB,E37A:E37A_BLOB,A2E:A2E_BLOB}

OUT_TOKEN="POSTV16_AV4_PIVOT_P2_R6_R29_R2_R1_R1_R1"
OUT_REL=BASE/(OUT_TOKEN+"_False_Absence_Assertion_Technical_Closure")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")

class GateError(RuntimeError): pass

def gt(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def sha(path:Path)->str:
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def js(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def csvr(path:Path)->list[dict[str,str]]:
    with open(path,newline="",encoding="utf-8") as f: return list(csv.DictReader(f))

def csvb(rows:list[dict[str,Any]])->bytes:
    if not rows:return b""
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)
    return s.getvalue().encode()

def jb(obj:Any)->bytes:
    return (json.dumps(obj,indent=2,sort_keys=True)+"\n").encode()

def manifest(directory:Path,filename:str)->dict[str,str]:
    out={}
    for row in csvr(directory/filename):
        p=directory/row["file"]
        if not p.is_file(): raise GateError(f"manifest_missing:{p.name}")
        if sha(p)!=row["sha256"]: raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size!=int(row["bytes"]): raise GateError(f"manifest_bytes:{p.name}")
        out[p.name]=row["sha256"]
    return out

def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise GateError(f"cannot_load:{path}")
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def selftest():
    assert R29R2R1R1_BLOCK_STAGE=="real_drive_authority"
    assert TARGET_DAY>375.0
    print("POSTV16 AV4 PIVOT P2-R6-R29-R2-R1-R1-R1 structural self-test: PASS")

def main(project_root:Path,drive_root:Path)->int:
    root=project_root.resolve();drive=drive_root.resolve()
    out=drive/OUT_REL;block_dir=drive/BLOCK_REL;stage="preflight";gates=[]
    def gate(name,cond,detail=None):
        ok=bool(cond)
        gates.append({"stage":stage,"gate":name,"pass":ok,"detail":"" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+("" if detail is None else f" -- {detail}"))
        if not ok: raise GateError(name)
    try:
        stage="real_drive_authority"
        r1=drive/R29R1R1_REL
        bpath=drive/R29R2R1R1_REL/R29R2R1R1_BLOCK
        gate("drive_root_exists",drive.is_dir(),str(drive))
        gate("R29R1R1_directory_exists",r1.is_dir(),str(r1))
        gate("R29R1R1_summary_exists",(r1/R29R1R1_SUMMARY).is_file())
        gate("R29R1R1_manifest_exists",(r1/R29R1R1_MANIFEST).is_file())
        gate("R29R2R1R1_BLOCK_exists",bpath.is_file(),str(bpath))

        stage="preexisting_state_firewall"
        gate("no_preexisting_child_PASS",not (out/f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_child_BLOCK",not (block_dir/f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage="repository_authority"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH)
        gate("parent_exact",gt(root,"rev-parse","HEAD^")==PARENT)
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            gate(f"{Path(fn).stem}_present",p.is_file(),str(p))
            actual=gt(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact",actual==expected,actual)

        stage="immutable_R29R2R1R1_BLOCK_authority"
        b=js(bpath);bsha=sha(bpath)
        gate("BLOCK_status_exact",b.get("status")==R29R2R1R1_BLOCK_STATUS,b.get("status"))
        gate("BLOCK_stage_exact",b.get("failed_stage")==R29R2R1R1_BLOCK_STAGE,b.get("failed_stage"))
        gate("BLOCK_exception_exact",b.get("exception")==R29R2R1R1_BLOCK_EXCEPTION,b.get("exception"))
        gate("BLOCK_no_transport",b.get("transport_execution_executed") is False)
        gate("BLOCK_no_state_mutation",b.get("state_mutation_executed") is False)
        gate("BLOCK_no_time_advance",b.get("physical_time_advance_executed") is False)

        stage="direct_R29R1R1_artifact_authority"
        mm=manifest(r1,R29R1R1_MANIFEST)
        s=js(r1/R29R1R1_SUMMARY);c=js(r1/R29R1R1_CLOSURE);d=js(r1/R29R1R1_DECISION);g=csvr(r1/R29R1R1_GATES)
        for fn in (R29R1R1_SUMMARY,R29R1R1_CLOSURE,R29R1R1_DECISION,R29R1R1_GATES):
            gate(f"{Path(fn).stem}_in_manifest",fn in mm)
        gate("R29R1R1_status_exact",s.get("status")==R29R1R1_STATUS,s.get("status"))
        gate("R29R1R1_classification_exact",s.get("classification")==R29R1R1_CLASSIFICATION,s.get("classification"))
        gate("R29R1_BLOCK_SHA_exact",s.get("source_R29R1_BLOCK_sha256")==R29R1_BLOCK_SHA256)
        gate("R29_FAIL_SHA_exact",s.get("source_R29_SCIENTIFIC_FAIL_sha256")==R29_FAIL_SHA256)
        gate("accepted_parent_valid",s.get("accepted_parent_capacity_valid_under_AV4_authority") is True)
        gate("heterogeneous_zero_violations",int(s.get("heterogeneous_PV_violating_cell_count"))==0)
        gate("saturation_reproduction_exact",float(s.get("heterogeneous_inversion_saturation_max_abs_error"))==0.0)
        gate("wrapper_audit_complete",s.get("technical_wrapper_full_audit_completed") is True)
        gate("no_transport_rerun",s.get("transport_science_rerun") is False)
        gate("gate_matrix_all_pass",all(str(row.get("pass")).lower()=="true" for row in g),len(g))
        repair=c.get("repair_boundary",{})
        gate("CV_transport_change_forbidden",repair.get("CV_transport_operator_change_authorized") is False)
        gate("delta_formula_change_forbidden",repair.get("subsegment_delta_formula_change_authorized") is False)
        gate("SG7D_deposition_change_forbidden",repair.get("SG7D_cell_deposition_change_authorized") is False)
        gate("heterogeneous_PV_required",repair.get("heterogeneous_cartesian_pore_volume_required") is True)
        gate("uniform_PV_forbidden",repair.get("uniform_phi_0p20_cartesian_PV_authorized") is False)
        gate("direct_parent_mass_required",repair.get("direct_accepted_parent_cartesian_mass_required") is True)
        gate("R29R2_originally_authorized",d.get("P2_R6_R29_R2_authorized") is True)

        stage="R28_and_porosity_continuity"
        r28=drive/R28_REL;manifest(r28,R28_MANIFEST);s28=js(r28/R28_SUMMARY);d28=js(r28/R28_DECISION)
        gate("R28_dt_exact",float(s28["nominal_dt_days"])==DT_DAYS)
        gate("R28_target_day_exact",float(s28["candidate_target_day"])==TARGET_DAY)
        gate("R28_delta_mapback_required",s28.get("delta_mapback_required") is True)
        gate("R28_absolute_mapback_forbidden",s28.get("absolute_mapback_forbidden") is True)
        gate("R28_residual_mutation_forbidden",d28.get("residual_sidecar_mutation_authorized") is False)
        gate("R28_auto_dt_reduction_forbidden",d28.get("automatic_dt_reduction_authorized") is False)
        a6e=drive/A6E_REL/A6E_STATE
        gate("A6E_porosity_SHA_exact",a6e.is_file() and sha(a6e)==A6E_STATE_SHA256)

        stage="repair_boundary_source_audit"
        e37a=load_module(root/E37A,"r29r2r1r1r1_e37a")
        a2e=load_module(root/A2E,"r29r2r1r1r1_a2e")
        adv=inspect.getsource(e37a.advance_component_mass_control_volumes)
        mp=inspect.getsource(e37a.map_control_volume_increment_to_grid)
        inv=inspect.getsource(a2e.invert_local_mass)
        gate("CV_transport_closure_present","component_mass_FV_global_closure" in adv)
        gate("subsegment_delta_present","sub_delta_mass" in mp)
        gate("flat_cell_deposition_present","np.bincount" in mp and "deposited_delta_mass" in mp)
        gate("legacy_scalar_parent_identified","float(cell_pore_volume_m3) * parent_rho * parent_sg" in mp)
        gate("legacy_scalar_inversion_identified","_invert_incremental_sg_from_mass" in mp and "cell_pore_volume_m3" in mp)
        gate("A2E_array_PV_inversion","pore_volume_m3" in inspect.signature(a2e.invert_local_mass).parameters)
        gate("A2E_capacity_gate","same_time_local_cell_mass_capacity" in inv)

        stage="technical_closure_publication"
        classification="R6R29R2R1R1R1_FALSE_ABSENCE_ASSERTION_CLOSED_ORIGINAL_R29R1R1_PASS_ARTIFACTS_VALIDATED_ON_REAL_DRIVE_HETEROGENEOUS_PV_DESIGN_FROZEN_R29R3_NEXT"
        closure={
            "milestone":M,"status":PASS,"classification":classification,
            "source_R29R2R1R1_BLOCK":{"sha256":bsha,"status":R29R2R1R1_BLOCK_STATUS,"failed_stage":R29R2R1R1_BLOCK_STAGE,"exception":R29R2R1R1_BLOCK_EXCEPTION,"immutable":True},
            "root_cause":{"classification":"false absence assertion against genuinely authoritative Drive","original_R29R1R1_artifacts_actually_present":True,"artifact_reconstruction_required":False,"artifact_rewrite_required":False},
            "direct_R29R1R1_authority":{"summary_sha256":mm[R29R1R1_SUMMARY],"closure_sha256":mm[R29R1R1_CLOSURE],"decision_sha256":mm[R29R1R1_DECISION],"gate_matrix_sha256":mm[R29R1R1_GATES],"manifest_sha256":sha(r1/R29R1R1_MANIFEST)},
            "recovered_design":{"dt_days":DT_DAYS,"candidate_target_day":TARGET_DAY,"CV_transport_operator":"E37A.advance_component_mass_control_volumes","CV_transport_operator_changed":False,"subsegment_delta_formula_changed":False,"SG7D_cell_deposition_changed":False,"uniform_cartesian_PV_authorized":False,"heterogeneous_cartesian_PV":"paired_porosity * A2E.BULK_VOLUME_M3","accepted_parent_cartesian_mass_used_directly":True,"candidate_mass_identity":"M_grid_candidate = accepted_M_grid_parent + Delta_M_grid","residual_candidate_identity":"M_residual_candidate = M_residual_parent exactly","absolute_mapback_authorized":False,"automatic_dt_reduction_authorized":False,"support_growth_authorized":False,"physical_time_commit_authorized":False}
        }
        summary={"milestone":M,"name":NAME,"status":PASS,"classification":classification,"source_R29R2R1R1_BLOCK_sha256":bsha,"false_absence_assertion_closed":True,"original_R29R1R1_artifacts_present_on_authoritative_drive":True,"R29R1R1_manifest_validated":True,"R29R1R1_status":s["status"],"R29R1R1_summary_sha256":mm[R29R1R1_SUMMARY],"R29R1R1_manifest_sha256":sha(r1/R29R1R1_MANIFEST),"accepted_parent_capacity_valid_under_AV4_authority":True,"heterogeneous_AV4_design_recovered":True,"transport_execution_performed":False,"state_mutation_executed":False,"physical_time_advance_executed":False,"P3_authorized":False}
        decision={"milestone":M,"status":PASS,"classification":classification,"P2_R6_R29_R3_authorized":True,"P2_R6_R29_R3_name":"Controlled Post-Day375 Frozen-Flow Transport Candidate Execution — Heterogeneous Cartesian PV Repair — No Time Commit","P2_R6_R29_R3_execution_authorized":True,"P2_R6_R29_R3_candidate_only":True,"P2_R6_R29_R3_must_bind_this_closure":True,"P2_R6_R29_R3_dt_days":DT_DAYS,"P2_R6_R29_R3_candidate_target_day":TARGET_DAY,"uniform_cartesian_PV_authorized":False,"heterogeneous_AV4_cartesian_PV_required":True,"CV_transport_operator_change_authorized":False,"subsegment_delta_formula_change_authorized":False,"absolute_mapback_authorized":False,"residual_sidecar_mutation_authorized":False,"automatic_dt_reduction_authorized":False,"support_growth_authorized":False,"physical_time_advance_authorized":False,"pressure_refresh_authorized":False,"P3_authorized":False}

        out.mkdir(parents=True,exist_ok=False)
        (out/f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out/f"{OUT_TOKEN}_False_Absence_Technical_Closure_Contract.json").write_bytes(jb(closure))
        (out/f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out/f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))
        rows=[]
        for p in sorted(out.iterdir()):
            if p.is_file(): rows.append({"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size})
        (out/f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("="*180)
        print(M,"PASS")
        print("R29-R2-R1-R1 BLOCK SHA256           :",bsha)
        print("Original R29-R1-R1 artifacts present: True")
        print("Original R29-R1-R1 manifest valid   : True")
        print("False absence assertion closed      : True")
        print("Artifact reconstruction/rewrite     : False / False")
        print("R29-R3 execution authorized         : True")
        print("Transport / state / time / P3       : False / False / False / False")
        print("="*180)
        return 0
    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"R29R2R1R1_BLOCK_preserved":True,"R29R1R1_artifacts_preserved":True,"transport_execution_executed":False,"state_mutation_executed":False,"physical_time_advance_executed":False,"P3_authorized":False,"automatic_rerun_authorized":False,"gates_completed":gates}))
        print(M,"TECHNICAL / AUTHORITY BLOCK")
        print("Stage:",stage);print("Exception:",repr(exc))
        return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:selftest();raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))

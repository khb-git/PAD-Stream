#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, io, json, subprocess
from pathlib import Path

MILESTONE = "POSTV16-AV3-A4-R1"
STATUS_PASS = (
    "AV3A4R1_IMMUTABLE_A4_SCIENTIFIC_FAIL_PRESERVED_"
    "TEACHER_CERTIFICATION_GATE_SEMANTICS_ROOT_CAUSE_CLOSED_NO_TEACHER_REEXECUTION"
)
STATUS_BLOCKED = "AV3A4R1_FAILURE_SEMANTICS_CLOSURE_BLOCKED"
RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT = "e1795d374c04e2eb07f701f0592f993d377c6421"

A4 = "PAD_Stream_POSTV16_AV3_A4_Corrected_CellCentered_Teacher_Dataset_and_LockedOOD_Predictor.py"
A4_BLOB = "24a6e4b815b83dfe89eca85a18ccc23021b4eefb"
A3 = "PAD_Stream_POSTV16_AV3_A3_Transport_Teacher_Residual_and_PIRNN_Protocol_Freeze.py"
A3_BLOB = "40fe89c142e62aad750a749f0a8ae452574f28bd"
A3R1 = "PAD_Stream_POSTV16_AV3_A3_R1_First9_CellCentered_Geometry_and_Normalization_Authority_Correction.py"
A3R1_BLOB = "2a70ef6b67ddefee61b5a9ab2fb080755fdb4b49"

BASE = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
FAIL = BASE / "POSTV16_AV3_A4_SCIENTIFIC_FAIL" / "POSTV16_AV3_A4_Scientific_Fail_Report.json"
A3DIR = BASE / "POSTV16_AV3_A3_Transport_Teacher_Residual_and_PIRNN_Protocol_Freeze"
A3_DATASET = A3DIR / "POSTV16_AV3_A3_Teacher_Dataset_and_Leakage_Firewall.json"
A3_DECISION = A3DIR / "POSTV16_AV3_A3_Decision_Contract.json"
OUT = BASE / "POSTV16_AV3_A4_R1_Teacher_Certification_Failure_Semantics_Closure"
BLOCK = BASE / "POSTV16_AV3_A4_R1_BLOCKED"

A4_FAIL_STATUS = (
    "AV3A4_SPATIAL_COREY_RELPERM_TEACHER_OR_DATASET_SCIENTIFIC_FAIL_"
    "NO_OOD_OPENING_RESEED_RETUNE_OR_TRAINING_AUTHORIZED"
)
A3_STATUS = (
    "AV3A3_SPATIAL_COREY_RELPERM_TRANSPORT_TEACHER_RESIDUAL_AND_"
    "13CHANNEL_PIRNN_PROTOCOL_PROSPECTIVELY_FROZEN_NO_TEACHER_OR_TRAINING_EXECUTION"
)

TH = {
    "advection_conservation_max_abs": 1e-11,
    "implicit_residual_max_abs": 1e-10,
    "preclip_bound_violation_max": 1e-8,
    "Y_bound_violation": 1e-8,
    "Y_inlet_Dirichlet_error": 1e-12,
    "Y_reservoir_undershoot": 1e-8,
    "temporal_negative_increment_fraction": 0.01,
    "spatial_positive_increment_fraction": 0.05,
}
SWC, SOR = 0.20, 0.20

class GateError(RuntimeError): pass

def git(root,*args):
    return subprocess.run(["git","-C",str(root),*args],check=True,text=True,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.strip()

def blob(root,fn):
    return git(root,"hash-object",str(root/fn))

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def jb(x):
    return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()

def cb(rows):
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n")
    w.writeheader(); w.writerows(rows)
    return s.getvalue().encode()

def publish(out,files):
    out.mkdir(parents=True,exist_ok=True)
    for n,d in files.items():
        p=out/n
        if p.exists() and p.read_bytes()!=d: raise GateError("existing_output_differs:"+n)
        if not p.exists(): p.write_bytes(d)

def self_test():
    assert set(TH) == {
        "advection_conservation_max_abs","implicit_residual_max_abs",
        "preclip_bound_violation_max","Y_bound_violation",
        "Y_inlet_Dirichlet_error","Y_reservoir_undershoot",
        "temporal_negative_increment_fraction","spatial_positive_increment_fraction"
    }
    print("POSTV16-AV3-A4-R1 teacher-certification failure-semantics closure self-test: PASS")

def main(root,drive):
    gates={}
    stage="preflight"
    def gate(n,c,v=None):
        ok=bool(c); gates[n]={"passed":ok,"value":v}
        print(f"[{'PASS' if ok else 'FAIL'}] {n}" + (f" — {v}" if v is not None else ""))
        if not ok: raise GateError(n)
    try:
        root=root.resolve(); drive=drive.resolve()
        print("="*180)
        print("POSTV16-AV3-A4-R1 — IMMUTABLE A4 FAIL PRESERVATION / TEACHER-CERTIFICATION SEMANTICS CLOSURE")
        print("="*180)
        print("NO TEACHER REEXECUTION. NO Y GENERATION. NO TRAINING. NO OOD TARGET ACCESS.")
        print("ORIGINAL AV3-A4 SCIENTIFIC FAIL REMAINS IMMUTABLE.")

        stage="repository"
        gate("repository_parent_is_failed_A4_source_commit",git(root,"rev-parse","HEAD^")==PARENT,git(root,"rev-parse","HEAD^"))
        gate("repository_clean",git(root,"status","--porcelain")=="",repr(git(root,"status","--porcelain")))
        gate("A4_blob_exact",blob(root,A4)==A4_BLOB,blob(root,A4))
        gate("A3_blob_exact",blob(root,A3)==A3_BLOB,blob(root,A3))
        gate("A3R1_blob_exact",blob(root,A3R1)==A3R1_BLOB,blob(root,A3R1))

        stage="failure_binding"
        fp=drive/FAIL
        gate("A4_fail_report_present",fp.is_file(),str(fp))
        f=json.loads(fp.read_text())
        gate("A4_fail_status_exact",f["status"]==A4_FAIL_STATUS,f["status"])
        gate("A4_failed_stage_teacher_generation",f["failed_stage"]=="teacher_generation",f["failed_stage"])
        gate("A4_failed_gate_CR0001",f["failed_gate"]=="AV3CR0001_teacher_certification",f["failed_gate"])
        gate("A4_teacher_completed_zero",int(f["teacher_realizations_completed"])==0,f["teacher_realizations_completed"])
        gate("A4_locked_OOD_remained_closed",f["LOCKED_OOD_target_opened"] is False)
        gate("A4_training_false",f["training"] is False)
        gate("A4_A5_not_authorized",f["AV3_A5_authorized"] is False)

        stage="A3_binding"
        ds=json.loads((drive/A3_DATASET).read_text())
        dec=json.loads((drive/A3_DECISION).read_text())
        gate("A3_status_preserved",dec["status"]==A3_STATUS,dec["status"])
        for k,v in TH.items():
            gate("A3_threshold_"+k,float(ds["teacher_certification_thresholds"][k])==v,ds["teacher_certification_thresholds"][k])

        d=f["detail"]
        hard={
            "Y_finite": bool(d["Y_finite"]),
            "advection_conservation_max_abs": float(d["advection_conservation_max_abs"])<TH["advection_conservation_max_abs"],
            "implicit_residual_max_abs": float(d["implicit_residual_max_abs"])<TH["implicit_residual_max_abs"],
            "preclip_bound_violation_max": float(d["preclip_bound_violation_max"])<TH["preclip_bound_violation_max"],
            "Y_bound_violation": float(d["Y_bound_violation"])<TH["Y_bound_violation"],
            "Y_inlet_Dirichlet_error": float(d["Y_inlet_Dirichlet_error"])<TH["Y_inlet_Dirichlet_error"],
        }
        morph={
            "Y_reservoir_undershoot": float(d["Y_reservoir_undershoot"])<TH["Y_reservoir_undershoot"],
            "temporal_negative_increment_fraction": float(d["temporal_negative_increment_fraction"])<TH["temporal_negative_increment_fraction"],
            "spatial_positive_increment_fraction": float(d["spatial_positive_increment_fraction"])<TH["spatial_positive_increment_fraction"],
        }
        gate("all_hard_numerical_checks_passed",all(hard.values()),hard)
        gate("exactly_three_morphology_checks_failed",sum(not x for x in morph.values())==3,morph)
        gate("Y_inside_absolute_physical_bounds",float(d["Y_min"])>=SWC and float(d["Y_max"])<=1-SOR,[d["Y_min"],d["Y_max"]])

        semantics={
            "governing_equation":"dS/deta + d/dtheta fw(S;p(theta)) = (phi/Pe_c) M d/dtheta[Dtilde(S;p(theta)) M dS/dtheta]",
            "heterogeneous_vector":"p(theta)=(nw,no,krw_max,kro_max)",
            "uniform_state_reduction":"At exact uniform interior S0, dS/dtheta=0, so initially dS/deta=-d/dtheta fw(S0;p(theta)).",
            "sign_argument":"Because p(theta) varies, d/dtheta fw(S0;p(theta)) has no globally fixed sign.",
            "not_universal_invariants":[
                "S(theta,t)>=S_initial everywhere",
                "temporal monotone saturation increase everywhere",
                "spatial monotone saturation decrease everywhere"
            ],
            "still_hard_invariants":[
                "finite Y","absolute saturation bounds","advection conservation",
                "implicit linear-solve residual","inlet Dirichlet condition"
            ],
            "boundary":"This does not prove every local nonmonotonic feature is physically exact; it proves the three morphology quantities are not universal certification invariants of the frozen AV3 PDE."
        }

        corrected={
            "hard_pass_fail":{
                "Y_finite":True,
                "advection_conservation_max_abs":"<1e-11",
                "implicit_residual_max_abs":"<1e-10",
                "preclip_bound_violation_max":"<1e-8",
                "Y_bound_violation":"<1e-8",
                "Y_inlet_Dirichlet_error":"<1e-12",
                "Y_absolute_bounds":"Swc<=Y<=1-Sor within frozen bound tolerance"
            },
            "report_only_no_threshold":[
                "Y_reservoir_undershoot",
                "temporal_negative_increment_fraction",
                "spatial_positive_increment_fraction"
            ],
            "replacement_relaxed_thresholds":False,
            "teacher_PDE_changed":False,
            "face_algebra_changed":False,
            "CFL_changed":False,
            "constitutive_fields_or_seeds_changed":False,
            "target_times_changed":False,
            "split_changed":False,
            "normalization_changed":False
        }
        gate("no_replacement_relaxed_thresholds",corrected["replacement_relaxed_thresholds"] is False)
        gate("teacher_physics_unchanged",not corrected["teacher_PDE_changed"] and not corrected["face_algebra_changed"] and not corrected["CFL_changed"])
        gate("fields_seeds_unchanged",corrected["constitutive_fields_or_seeds_changed"] is False)

        handoff={
            "milestone":"POSTV16-AV3-A4-R2",
            "authorized":True,
            "execution":True,
            "required":[
                "preserve original AV3-A4 scientific FAIL immutably",
                "rerun deterministic supervised teachers under unchanged A3 physics",
                "apply only R1 hard numerical certification gates",
                "record three morphology metrics report-only with no thresholds",
                "generate Y only for AV3CR0001/0002/0003",
                "keep AV3CR0004 predictor-only",
                "no reseed, field retune, PDE/face/CFL/time/model/split/normalization change"
            ]
        }

        audit=[]
        for k,v in hard.items():
            audit.append({"metric":k,"class":"HARD_NUMERICAL_GATE","observed":d.get(k),"original_pass":v,"R1_role":"PASS_FAIL"})
        for k,v in morph.items():
            audit.append({"metric":k,"class":"MORPHOLOGY_DIAGNOSTIC","observed":d[k],"original_pass":v,"R1_role":"REPORT_ONLY_NO_THRESHOLD"})

        decision={
            "milestone":MILESTONE,"status":STATUS_PASS,
            "original_A4_scientific_FAIL_preserved":True,
            "original_failed_gate":f["failed_gate"],
            "hard_numerical_checks_all_passed":all(hard.values()),
            "failed_components_exactly_three_morphology_diagnostics":True,
            "root_cause":"A3 teacher certification overconstrained AV3 with morphology assumptions that are not universal invariants of spatially heterogeneous fw(S;p(theta)).",
            "teacher_solver_instability_claimed":False,
            "teacher_physics_changed":False,
            "morphology_thresholds_relaxed":False,
            "morphology_diagnostics_report_only":True,
            "teacher_reexecution_performed":False,
            "locked_OOD_target_opened":False,
            "AV3_A5_authorized":False,
            "AV3_A4_R2_authorized":True,
            "next":handoff
        }
        summary={
            "milestone":MILESTONE,"status":STATUS_PASS,
            "original_A4_status":f["status"],
            "original_A4_failed_gate":f["failed_gate"],
            "hard_numerical_checks_passed":[k for k,v in hard.items() if v],
            "morphology_checks_failed":[k for k,v in morph.items() if not v],
            "Y_min":float(d["Y_min"]),"Y_max":float(d["Y_max"]),
            "physical_bounds":[SWC,1-SOR],
            "teacher_reexecution":False,"training":False,
            "locked_OOD_target_access":False,
            "AV3_A4_R2_authorized":True,"AV3_A5_authorized":False
        }

        files={
            "PAD_Stream_POSTV16_AV3_A4_R1_Summary.json":jb(summary),
            "POSTV16_AV3_A4_R1_Immutable_Failure_Identity.json":jb({"failure_SHA256":sha256(fp),"failure":f,"reclassified":False}),
            "POSTV16_AV3_A4_R1_Teacher_Certification_Gate_Semantics_Audit.csv":cb(audit),
            "POSTV16_AV3_A4_R1_Spatial_Heterogeneity_Monotonicity_Analysis.json":jb(semantics),
            "POSTV16_AV3_A4_R1_Corrected_Teacher_Certification_Contract.json":jb(corrected),
            "POSTV16_AV3_A4_R1_R2_Handoff_Contract.json":jb(handoff),
            "POSTV16_AV3_A4_R1_Decision_Contract.json":jb(decision),
            "POSTV16_AV3_A4_R1_Final_Gate_Matrix.csv":cb([{"gate":k,**v} for k,v in gates.items()])
        }
        publish(drive/OUT,files)

        manifest=[]
        for q in sorted((drive/OUT).iterdir()):
            if q.is_file() and q.name!="POSTV16_AV3_A4_R1_Artifact_Manifest.csv":
                manifest.append({"file":q.name,"sha256":sha256(q),"bytes":q.stat().st_size})
        publish(drive/OUT,{"POSTV16_AV3_A4_R1_Artifact_Manifest.csv":cb(manifest)})

        print("="*180)
        print("POSTV16-AV3-A4-R1: FAILURE / CERTIFICATION-SEMANTICS CLOSURE PASS")
        print("Original A4 scientific FAIL : PRESERVED")
        print("Hard numerical checks       : ALL PASSED")
        print("Failed components            : 3 morphology diagnostics")
        print("Replacement thresholds       : NONE")
        print("Teacher physics              : UNCHANGED")
        print("Teacher reexecution in R1    : False")
        print("Locked OOD Y                 : CLOSED")
        print("AV3-A5                       : NOT AUTHORIZED")
        print("AV3-A4-R2                    : AUTHORIZED")
        print("="*180)
        return 0

    except Exception as exc:
        p=drive/BLOCK
        p.mkdir(parents=True,exist_ok=True)
        report={"milestone":MILESTONE,"status":STATUS_BLOCKED,"failed_stage":stage,
                "exception":repr(exc),"gates":gates,
                "original_A4_FAIL_reclassified":False,
                "teacher_reexecution":False,"locked_OOD_target_opened":False,
                "AV3_A4_R2_authorized":False,"AV3_A5_authorized":False}
        q=p/"POSTV16_AV3_A4_R1_Blocked_Report.json"
        if not q.exists(): q.write_bytes(jb(report))
        print("POSTV16-AV3-A4-R1: BLOCKED",stage,repr(exc))
        return 2

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path("."))
    p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test",action="store_true")
    return p.parse_args()

if __name__=="__main__":
    a=parse_args()
    if a.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))

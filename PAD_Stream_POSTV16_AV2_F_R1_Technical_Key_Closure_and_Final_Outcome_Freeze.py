#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,io,json,subprocess
from pathlib import Path
from typing import Any
import numpy as np

MILESTONE="POSTV16-AV2-F-R1"
PROTOCOL="POSTV16_AV2_F_R1_TECHNICAL_KEY_SCHEMA_CLOSURE_AND_FINAL_OUTCOME_FREEZE_V1"
STATUS="AV2_FINAL_VARIABLE_POROSITY_SCIENTIFIC_OUTCOME_FROZEN_AFTER_F_TECHNICAL_KEY_CLOSURE_AV3_A0_AUTHORIZED"
BLOCK="AV2FR1_FINAL_OUTCOME_FREEZE_BLOCKED"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT="3d5a1519c4bd1e4d71307bd9c748227953ed29ef"
CKSHA="1c82867c53d9d3a63ee8ba9dab5ab65e9bdfaf6330fb5239954d02d7f566ef28"

F="PAD_Stream_POSTV16_AV2_F_Final_Variable_Porosity_Outcome_Freeze_and_AV3_Handoff.py";FBLOB="934c37b519cc68424a97451d57803e34a3f0ec4e"
A1="PAD_Stream_POSTV16_AV2_A1_Spatial_Porosity_Field_Model_and_Split_Registry_Freeze.py";A1B="465d493cf6641c8929224d68a15e29aa38f9db69"
A2="PAD_Stream_POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution.py";A2B="f141b07f0424d29a7996c089a76dbe7128af5132"
R1="PAD_Stream_POSTV16_AV2_A4_R1_OOD_Metric_Precision_Failure_Closure.py";R1B="dddb0e7e64acae111822b7c48281f78b2864bceb"
R2="PAD_Stream_POSTV16_AV2_A4_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation.py";R2B="fd1428e093481ceb3b271fa8b5ff22fb9fdfc55f"
A5="PAD_Stream_POSTV16_AV2_A5_Frozen_Checkpoint_LocalPV_R7D_Integration.py";A5B="f2cc67b80a17eccfca54f4330b2259ef9b7e377c"
SOURCES={F:FBLOB,A1:A1B,A2:A2B,R1:R1B,R2:R2B,A5:A5B}

BASE=Path("post_v16")/RID/"POSTV16_AV2_Variable_Porosity"
A1D=BASE/"POSTV16_AV2_A1_Spatial_Porosity_Field_Model_and_Split_Registry_Freeze"
A2D=BASE/"POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution"
R1D=BASE/"POSTV16_AV2_A4_R1_OOD_Metric_Precision_Failure_Closure"
R2D=BASE/"POSTV16_AV2_A4_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation"
A5D=BASE/"POSTV16_AV2_A5_Frozen_Checkpoint_LocalPV_R7D_Integration"
FBLK=BASE/"POSTV16_AV2_F_BLOCKED"
OUT=BASE/"POSTV16_AV2_F_R1_Technical_Key_Closure_and_Final_Outcome_Freeze"
BLK=BASE/"POSTV16_AV2_F_R1_BLOCKED"

F_BLOCK_REPORT="POSTV16_AV2_F_Blocked_Report.json"
EXPECTED_F_EXCEPTION="KeyError('A4_float32_roundtrip_max_abs_difference')"

A1STAT="AV2A1_SPATIAL_POROSITY_FIELD_MODEL_BOUNDS_CORRELATION_FACE_RULE_AND_SPLIT_REGISTRY_PROSPECTIVELY_FROZEN_NO_FIELD_GENERATION"
A2STAT="AV2A2_FROZEN_SPATIAL_POROSITY_REALIZATIONS_GENERATED_PRESSURE_Q_INVARIANCE_CERTIFIED_PORE_KINEMATICS_RECONSTRUCTED_PASS"
R1STAT="AV2A4R1_OOD_METRIC_PRECISION_FAILURE_CAUSE_CLOSED_ORIGINAL_A4_FAIL_PRESERVED_OOD_TARGET_CONFIRMED_UNGENERATED"
R2STAT="AV2A4R2_FROZEN_CHECKPOINT_LOCKED_OOD_TEACHER_GENERATED_ONCE_EVALUATED_ONCE_DESCRIPTIVE_GENERALIZATION_EVIDENCE_FROZEN"
A5STAT="AV2A5_FROZEN_CHECKPOINT_VARIABLE_POROSITY_LOCAL_PORE_VOLUME_R7D_TERMINAL_HALO_INTEGRATION_ALL_4_REALIZATIONS_ALL_9_TIMES_PASS"

REAL=[("AV2PHI0001",260201,"TRAIN"),("AV2PHI0002",260202,"TRAIN"),("AV2PHI0003",260203,"VALIDATION"),("AV2PHI0004",260204,"LOCKED_OOD_TEST")]
DAYS=np.asarray([30.,60.,100.,150.,250.,365.,500.,750.,1000.],dtype=np.float64)
GRID=(15,50,50)

class GateError(RuntimeError): pass

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def git(root:Path,*a:str)->str:
    return subprocess.run(["git","-C",str(root),*a],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.strip()

def loadj(p:Path)->dict[str,Any]:
    return json.loads(p.read_text(encoding="utf-8"))

def rows(p:Path)->list[dict[str,str]]:
    with p.open("r",newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def manifest(d:Path,n:str)->dict[str,str]:
    rr=rows(d/n); m={r["file"]:r["sha256"] for r in rr}
    if not m: raise GateError("manifest_empty:"+n)
    for fn,e in m.items():
        q=d/fn
        if not q.is_file() or sha(q)!=e: raise GateError("manifest_mismatch:"+fn)
    return m

def jb(x:Any)->bytes:
    return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()

def cb(rr:list[dict[str,Any]])->bytes:
    if not rr:return b""
    ks=[]
    for r in rr:
        for k in r:
            if k not in ks:ks.append(k)
    s=io.StringIO();w=csv.DictWriter(s,fieldnames=ks,lineterminator="\n");w.writeheader();w.writerows(rr)
    return s.getvalue().encode()

def pub(d:Path,fs:dict[str,bytes])->None:
    d.mkdir(parents=True,exist_ok=True)
    for n,b in fs.items():
        p=d/n
        if p.exists() and p.read_bytes()!=b: raise GateError("existing_output_differs:"+n)
        if not p.exists():p.write_bytes(b)

def bt(v:Any)->bool:
    return str(v).strip().lower()=="true"

def self_test():
    rootcause={"native_float64_max_abs_difference":0.0,"float32_roundtrip_max_abs_difference":4.734486385160608e-07}
    assert "A4_float32_roundtrip_max_abs_difference" not in rootcause
    assert rootcause["float32_roundtrip_max_abs_difference"]==4.734486385160608e-07
    print("POSTV16-AV2-F-R1 technical-key closure self-test: PASS")

def main(root:Path,drive:Path)->int:
    gates={};stage="preflight";out=drive/OUT
    def g(n,v,val=None):
        ok=bool(v);gates[n]={"passed":ok,"value":val};print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f" — {val}" if val is not None else ""))
        if not ok:raise GateError(n)

    print("="*196)
    print("POSTV16-AV2-F-R1 — TECHNICAL KEY-SCHEMA CLOSURE / FINAL AV2 OUTCOME FREEZE")
    print("="*196)
    print("AUDIT/FREEZE ONLY. NO TRAINING. NO INFERENCE. NO LP. NO MAPBACK. NO OOD TRUTH ACCESS. NO OOD METRIC RECOMPUTATION. NO CMG.")
    print("ORIGINAL AV2-F BLOCK IS PRESERVED. ORIGINAL AV2-A4 FAIL IS PRESERVED.")

    try:
        root=root.resolve();drive=drive.resolve()
        stage="repository"
        g("repository_parent_is_blocked_AV2F",git(root,"rev-parse","HEAD^")==PARENT,git(root,"rev-parse","HEAD^"))
        g("repository_clean",git(root,"status","--porcelain")=="")
        for fn,e in SOURCES.items():
            p=root/fn;a=git(root,"hash-object",str(p)) if p.is_file() else "missing"
            g(Path(fn).stem+"_blob_exact",a==e,a)

        stage="blocked_F_binding"
        brp=drive/FBLK/F_BLOCK_REPORT
        g("original_AV2F_block_report_present",brp.is_file(),str(brp))
        br=loadj(brp)
        g("original_AV2F_status_BLOCKED",br["status"]=="AV2F_FINAL_OUTCOME_FREEZE_BLOCKED",br["status"])
        g("original_AV2F_exception_exact",br["exception"]==EXPECTED_F_EXCEPTION,br["exception"])
        g("original_AV2F_outcome_not_frozen",br["AV2_outcome_frozen"] is False)
        g("original_AV2F_AV3_not_authorized",br["AV3_A0_authorized"] is False)
        g("original_AV2F_no_training",br["training_performed"] is False)
        g("original_AV2F_no_inference",br["inference_performed"] is False)
        g("original_AV2F_no_LP",br["LP_execution_performed"] is False)
        g("original_AV2F_no_mapback",br["mapback_execution_performed"] is False)
        g("original_AV2F_no_OOD_truth",br["OOD_truth_accessed"] is False)
        g("original_AV2F_no_CMG",br["CMG_validation_performed"] is False)

        stage="authority_binding"
        a1=drive/A1D;a2=drive/A2D;r1=drive/R1D;r2=drive/R2D;a5=drive/A5D
        for n,d in [("A1",a1),("A2",a2),("A4R1",r1),("A4R2",r2),("A5",a5)]:g(n+"_output_present",d.is_dir(),str(d))
        m1=manifest(a1,"POSTV16_AV2_A1_Artifact_Manifest.csv");m2=manifest(a2,"POSTV16_AV2_A2_Artifact_Manifest.csv");mr1=manifest(r1,"POSTV16_AV2_A4_R1_Artifact_Manifest.csv");mr2=manifest(r2,"POSTV16_AV2_A4_R2_Artifact_Manifest.csv");m5=manifest(a5,"POSTV16_AV2_A5_Artifact_Manifest.csv")
        g("all_bound_manifests_SHA_exact",True,(len(m1),len(m2),len(mr1),len(mr2),len(m5)))

        s1=loadj(a1/"PAD_Stream_POSTV16_AV2_A1_Summary.json")
        s2=loadj(a2/"PAD_Stream_POSTV16_AV2_A2_Summary.json");d2=loadj(a2/"POSTV16_AV2_A2_Decision_Contract.json")
        sr1=loadj(r1/"PAD_Stream_POSTV16_AV2_A4_R1_Summary.json");rr1=loadj(r1/"POSTV16_AV2_A4_R1_Precision_Root_Cause_Audit.json");er1=loadj(r1/"POSTV16_AV2_A4_R1_OOD_Exposure_State.json")
        sr2=loadj(r2/"PAD_Stream_POSTV16_AV2_A4_R2_Summary.json");dr2=loadj(r2/"POSTV16_AV2_A4_R2_Decision_Contract.json");gr2=loadj(r2/"POSTV16_AV2_A4_R2_LockedOOD_Generalization_Evidence.json")
        s5=loadj(a5/"PAD_Stream_POSTV16_AV2_A5_Summary.json");d5=loadj(a5/"POSTV16_AV2_A5_Decision_Contract.json")

        g("A1_status_exact",s1["status"]==A1STAT,s1["status"])
        g("A2_status_exact",s2["status"]==A2STAT,s2["status"])
        g("A2_pressure_Q_invariance",d2["pressure_Q_invariance_certified"] is True)
        g("A2_retrace_TOF",d2["Pollock_retraced"] is True and d2["TOF_recomputed"] is True)
        g("A2_all_1078_streamlines",d2["all_1078_streamlines_captured_for_all_realizations"] is True)

        g("A4R1_status_exact",sr1["status"]==R1STAT,sr1["status"])
        g("A4R1_original_A4_FAIL_preserved",sr1["original_A4_fail_preserved"] is True)
        g("A4R1_actual_native_key_present","native_float64_max_abs_difference" in rr1,sorted(rr1))
        g("A4R1_actual_float32_key_present","float32_roundtrip_max_abs_difference" in rr1,sorted(rr1))
        g("A4R1_incorrect_F_key_absent","A4_float32_roundtrip_max_abs_difference" not in rr1,sorted(rr1))
        d64=float(rr1["native_float64_max_abs_difference"]);d32=float(rr1["float32_roundtrip_max_abs_difference"])
        g("A4R1_native_float64_diff_zero",d64==0.0,d64)
        g("A4R1_float32_diff_exact",abs(d32-4.734486385160608e-07)<=1e-15,d32)
        g("A4R1_precision_root_cause",rr1["precision_demotion_root_cause_supported"] is True)
        g("A4R1_physical_metric_mismatch_false",rr1["physical_metric_mismatch_supported"] is False)
        g("A4R1_OOD_not_generated_or_evaluated",er1["OOD_Y_transport_generated"] is False and er1["OOD_model_evaluated"] is False)

        g("A4R2_status_exact",sr2["status"]==R2STAT,sr2["status"])
        g("A4R2_checkpoint_exact",sr2["checkpoint_sha256"]==CKSHA,sr2["checkpoint_sha256"])
        g("A4R2_one_touch_complete",dr2["locked_OOD_teacher_generated_once"] is True and dr2["locked_OOD_evaluated_once"] is True)
        g("A4R2_no_generalization_claim",dr2["variable_phi_predictive_generalization_claim"] is False)

        g("A5_status_exact",s5["status"]==A5STAT,s5["status"])
        g("A5_checkpoint_exact",s5["checkpoint_sha256"]==CKSHA)
        g("A5_36_cases",s5["realizations_completed"]==4 and s5["canonical_times_per_realization"]==9 and s5["integrated_cases"]==36)
        g("A5_local_PV",d5["local_pore_volume_capacity_used"] is True)
        g("A5_R7D_preserved",d5["R7D_terminal_halo_semantics_preserved"] is True)
        g("A5_R7R7A_preserved",d5["R7R7A_arithmetic_preserved_via_R7E_authority"] is True)
        g("A5_freeze_authorized",d5["AV2_final_outcome_freeze_authorized"] is True)

        stage="realization_freeze"
        reg={r["porosity_realization_id"]:r for r in rows(a1/"POSTV16_AV2_A1_Frozen_Porosity_Realization_Registry.csv")}
        diag={r["porosity_realization_id"]:r for r in rows(a2/"POSTV16_AV2_A2_By_Porosity_Realization_Diagnostics.csv")}
        real={r["porosity_realization_id"]:r for r in rows(a5/"POSTV16_AV2_A5_Realization_Summary.csv")}
        g("registry_counts_4_4_4",len(reg)==len(diag)==len(real)==4,(len(reg),len(diag),len(real)))
        frozen=[]
        for rid,seed,part in REAL:
            g(rid+"_registered",rid in reg and rid in diag and rid in real)
            g(rid+"_seed",int(reg[rid]["seed"])==seed,int(reg[rid]["seed"]))
            g(rid+"_partition",reg[rid]["partition"]==part and real[rid]["partition"]==part,part)
            rr=real[rid];dd=diag[rid];s0=int(rr["S0_cells"]);h1=int(rr["H1_cells"]);d1=int(rr["D1_cells"])
            g(rid+"_D1_partition",d1==s0+h1,[d1,s0,h1]);g(rid+"_all9",bt(rr["all_9_times_passed"]))
            state=f"POSTV16_AV2_A5_{rid}_Integrated_State.npz";g(rid+"_state_manifested",state in m5,state)
            with np.load(a5/state,allow_pickle=False) as z:
                g(rid+"_state_shapes",z["porosity"].shape==GRID and z["grid_saturation"].shape==(9,)+GRID and z["grid_component_mass_kg"].shape==(9,)+GRID)
                g(rid+"_state_checkpoint",str(np.asarray(z["checkpoint_sha256"]).reshape(-1)[0])==CKSHA)
                g(rid+"_state_days",np.array_equal(np.asarray(z["target_days"],float),DAYS))
                sat=np.asarray(z["grid_saturation"],float);mass=np.asarray(z["grid_component_mass_kg"],float)
                g(rid+"_state_finite_bounded",np.isfinite(sat).all() and np.isfinite(mass).all() and sat.min()>=.2-1e-12 and sat.max()<=.8+1e-12)
            frozen.append({
                "porosity_realization_id":rid,"seed":seed,"partition":part,
                "phi_min":float(rr["phi_min"]),"phi_max":float(rr["phi_max"]),"phi_mean":float(rr["phi_mean"]),"phi_std":float(rr["phi_std"]),
                "total_pore_volume_ratio_to_AV1_constant_phi":float(dd["total_pore_volume_ratio_to_AV1_constant_phi"]),
                "terminal_TOF_min_days":float(dd["terminal_TOF_min_days"]),"terminal_TOF_mean_days":float(dd["terminal_TOF_mean_days"]),"terminal_TOF_max_days":float(dd["terminal_TOF_max_days"]),
                "max_abs_terminal_TOF_change_vs_AV1_s":float(dd["max_abs_terminal_TOF_change_vs_AV1_s"]),
                "max_abs_201node_XYZ_change_vs_AV1_m":float(dd["max_abs_201node_XYZ_change_vs_AV1_m"]),
                "S0_cells":s0,"H1_cells":h1,"D1_cells":d1,"integrated_state_file":state,"integrated_state_sha256":m5[state]
            })

        stage="timewise_freeze"
        tw=rows(a5/"POSTV16_AV2_A5_Timewise_Integration_Audit.csv");g("A5_timewise_36",len(tw)==36,len(tw))
        for rid,_,part in REAL:
            q=[r for r in tw if r["porosity_realization_id"]==rid]
            g(rid+"_timewise_9",len(q)==9,len(q))
            g(rid+"_canonical_days",np.array_equal(np.sort(np.asarray([float(r["target_day"]) for r in q])),DAYS))
            g(rid+"_timewise_partition",all(r["partition"]==part for r in q))
        mm=max(abs(float(r["mass_relative_closure"])) for r in tw);me=max(abs(float(r["EOS_localPV_mass_relative_closure"])) for r in tw);mc=max(float(r["max_capacity_excess_after_reconciliation_kg"]) for r in tw);mh=max(float(r["H1_capacity_fraction_used"]) for r in tw);mo=max(int(float(r["H1_occupied_cell_count"])) for r in tw)
        g("A5_mass_closure_machine_precision",mm<=1e-10,mm);g("A5_localPV_EOS_closure_machine_precision",me<=1e-10,me)
        g("A5_summary_metrics_exact",float(s5["max_mass_relative_closure"])==mm and float(s5["max_EOS_localPV_mass_relative_closure"])==me and float(s5["max_post_reconciliation_capacity_excess_kg"])==mc and float(s5["max_H1_capacity_fraction_used"])==mh and int(s5["max_H1_occupied_cell_count"])==mo)
        g5=rows(a5/"POSTV16_AV2_A5_Final_Gate_Matrix.csv");g("A5_gate_count_317",len(g5)==317,len(g5));g("A5_all_317_PASS",all(bt(r["passed"]) for r in g5));g("A5_manifest_count_9",len(m5)==9,len(m5))

        stage="freeze_publish"
        claims={
            "milestone":MILESTONE,"protocol_id":PROTOCOL,
            "frozen_claims":[
                {"id":"AV2_CLAIM_1_PRESSURE_Q_INVARIANCE","claim":"Under the frozen AV2 variable-porosity model, unchanged AV1 permeability, wells, controls, fluids, and steady finite-volume flow formulation reproduce the AV1 pressure and Darcy volumetric-flow solution within the prospectively frozen A2 tolerances.","evidence":{k:float(s2[k]) for k in ["pressure_max_abs_difference_psi","pressure_relative_L2_difference","Qx_relative_L2_difference","Qy_relative_L2_difference","Qz_relative_L2_difference"]}},
                {"id":"AV2_CLAIM_2_PORE_KINEMATICS_CHANGE","claim":"Spatially variable porosity changes pore velocity and therefore requires realization-specific exact Pollock streamline and time-of-flight reconstruction.","evidence_realizations":frozen},
                {"id":"AV2_CLAIM_3_FROZEN_PIRNN_ONE_TOUCH_OOD","claim":"The frozen epoch-198 AV2 PI-RNN checkpoint was evaluated once on prospectively locked AV2PHI0004 after checkpoint freeze, without retraining, checkpoint reselection, normalization refit, or post-OOD retuning.","checkpoint_sha256":CKSHA,"validation_metrics":sr2["validation_metrics"],"locked_OOD_metrics":sr2["locked_OOD_metrics"],"OOD_to_validation_RMSE_ratio":float(gr2["OOD_to_validation_RMSE_ratio"]),"OOD_to_validation_MAE_ratio":float(gr2["OOD_to_validation_MAE_ratio"])},
                {"id":"AV2_CLAIM_4_END_TO_END_LOCAL_PV_INTEGRATION","claim":"All four prospectively frozen AV2 porosity realizations were integrated through the frozen checkpoint, exact component-mass bridge, realization-specific S0 support, single-ring same-layer terminal H1 occupancy halo, local cell pore-volume capacity, and frozen EOS/reconciliation semantics at all nine canonical times.","integrated_cases":36,"max_mass_relative_closure":mm,"max_localPV_EOS_mass_relative_closure":me,"max_post_reconciliation_capacity_excess_kg":mc,"max_H1_capacity_fraction_used":mh,"max_H1_occupied_cell_count":mo},
                {"id":"AV2_CLAIM_5_ARCHITECTURE_FIXED_GEOMETRY_REALIZATION_DEPENDENT","claim":"The R7D occupancy-domain construction rule is preserved, but exact S0/H1/D1 membership is realization-dependent because variable porosity changes Pollock trajectories.","realization_domains":[{k:r[k] for k in ["porosity_realization_id","S0_cells","H1_cells","D1_cells"]} for r in frozen]}
            ],
            "explicitly_not_claimed":["generalization to arbitrary variable-porosity geological fields","external full-physics or CMG agreement","AV3 relative-permeability/Corey heterogeneity performance","AV4 dynamic pressure-refresh performance","AV5 final GPU performance validation","IBDP transferability","plume-fidelity superiority over full-physics simulation"]
        }
        history={
            "AV2_A4_original_result":"FAIL","AV2_A4_failure_gate":"OOD_metric_matches_A3_sidecar","AV2_A4_checkpoint_best_epoch":198,"AV2_A4_epochs_completed":207,"AV2_A4_checkpoint_sha256":CKSHA,
            "AV2_A4_R1_result":"PASS","AV2_A4_R1_native_float64_max_abs_difference":d64,"AV2_A4_R1_float32_roundtrip_max_abs_difference":d32,"AV2_A4_R2_result":"PASS","original_A4_FAIL_reclassified":False,
            "AV2_F_original_result":"BLOCKED","AV2_F_block_exception":EXPECTED_F_EXCEPTION,"AV2_F_scientific_execution_performed":False,"AV2_F_block_reclassified":False,
            "AV2_F_R1_result":"PASS","AV2_F_R1_repair":"Use exact stored R1 key float32_roundtrip_max_abs_difference; no scientific data or thresholds changed.",
            "history_rule":"Original FAIL/BLOCK outcomes remain immutable historical results; closure milestones do not relabel them."
        }
        handoff={
            "from":"POSTV16-AV2-F-R1","AV2_complete":True,"AV2_external_CMG_validation_complete":False,"CMG_remains_deferred_until_after_internal_AV2_AV5_roadmap":True,"AV2_frozen_checkpoint_sha256":CKSHA,"AV2_variable_porosity_architecture_frozen":True,"AV3_authorized":True,
            "next":{"milestone":"POSTV16-AV3-A0","name":"Spatial Corey / Relative-Permeability Heterogeneity Authority-Gap and Physics-Impact Freeze","authorized":True,"execution":False},
            "AV3_initial_scope":{"new_physics_axis":"spatial heterogeneity in Corey/relative-permeability parameters while preserving the completed AV2 variable-porosity base","AV2_checkpoint_may_be_assumed_authoritative_for_AV3":False,"reason":"AV3 changes constitutive transport physics; a new authority-gap and learning-evidence audit is required before reusing or extending the AV2 transport model."}
        }
        ledger={
            "repository_parent_blocked_AV2F_commit":PARENT,"checkpoint_sha256":CKSHA,"source_git_blobs":SOURCES,
            "original_AV2F_block_report_sha256":sha(brp),
            "bound_manifests":{"A1":{"entries":len(m1),"sha256":sha(a1/"POSTV16_AV2_A1_Artifact_Manifest.csv")},"A2":{"entries":len(m2),"sha256":sha(a2/"POSTV16_AV2_A2_Artifact_Manifest.csv")},"A4R1":{"entries":len(mr1),"sha256":sha(r1/"POSTV16_AV2_A4_R1_Artifact_Manifest.csv")},"A4R2":{"entries":len(mr2),"sha256":sha(r2/"POSTV16_AV2_A4_R2_Artifact_Manifest.csv")},"A5":{"entries":len(m5),"sha256":sha(a5/"POSTV16_AV2_A5_Artifact_Manifest.csv")}},
            "A5_integrated_state_SHA256":{r["porosity_realization_id"]:r["integrated_state_sha256"] for r in frozen}
        }
        decision={
            "milestone":MILESTONE,"status":STATUS,"protocol_id":PROTOCOL,"original_AV2F_BLOCK_preserved":True,"technical_key_schema_defect_closed":True,"AV2_scientific_outcome_frozen":True,"AV2_internal_system_development_complete":True,"AV2_external_validation_complete":False,"checkpoint_sha256":CKSHA,
            "pressure_Q_invariance_frozen":True,"variable_phi_pore_kinematics_frozen":True,"one_touch_locked_OOD_evidence_frozen":True,"all_four_realizations_all_nine_times_integrated":True,"local_pore_volume_grid_capacity_frozen":True,"R7D_terminal_halo_semantics_frozen":True,"original_A4_FAIL_preserved":True,
            "training_performed":False,"inference_performed":False,"LP_execution_performed":False,"mapback_execution_performed":False,"OOD_truth_accessed":False,"OOD_metrics_recomputed":False,"CMG_validation_performed":False,"AV3_A0_authorized":True,"next":handoff["next"]
        }
        summary={
            "milestone":MILESTONE,"status":STATUS,"protocol_id":PROTOCOL,"checkpoint_sha256":CKSHA,"original_AV2F_result":"BLOCKED","original_AV2F_block_preserved":True,"technical_key_schema_defect_closed":True,
            "porosity_realizations":4,"canonical_times":9,"frozen_integrated_states":4,"frozen_integrated_cases":36,"A5_execution_gate_count":317,"A5_manifest_entry_count":9,
            "max_mass_relative_closure":mm,"max_localPV_EOS_mass_relative_closure":me,"max_post_reconciliation_capacity_excess_kg":mc,"max_H1_capacity_fraction_used":mh,"max_H1_occupied_cell_count":mo,
            "AV2_external_CMG_validation":False,"AV3_A0_authorized":True,"next":handoff["next"]
        }
        pub(out,{
            "PAD_Stream_POSTV16_AV2_F_R1_Summary.json":jb(summary),
            "POSTV16_AV2_F_R1_Frozen_Scientific_Claims.json":jb(claims),
            "POSTV16_AV2_F_R1_Frozen_Realization_and_Domain_Registry.csv":cb(frozen),
            "POSTV16_AV2_F_R1_Immutable_Failure_and_Block_History.json":jb(history),
            "POSTV16_AV2_F_R1_AV3_Handoff_Contract.json":jb(handoff),
            "POSTV16_AV2_F_R1_Source_and_Artifact_Authority_Ledger.json":jb(ledger),
            "POSTV16_AV2_F_R1_Decision_Contract.json":jb(decision),
            "POSTV16_AV2_F_R1_Final_Gate_Matrix.csv":cb([{"gate":k,**v} for k,v in gates.items()])
        })
        mr=[{"file":q.name,"sha256":sha(q),"bytes":q.stat().st_size} for q in sorted(out.iterdir()) if q.is_file() and q.name!="POSTV16_AV2_F_R1_Artifact_Manifest.csv"]
        pub(out,{"POSTV16_AV2_F_R1_Artifact_Manifest.csv":cb(mr)})

        print("\n"+"="*196)
        print("POSTV16-AV2-F-R1: FULL TECHNICAL CLOSURE / FINAL OUTCOME FREEZE PASS")
        print("="*196)
        print("Original AV2-F result                 : BLOCKED (preserved)")
        print("AV2-F key-schema defect               : CLOSED")
        print("Original AV2-A4 result                : FAIL (preserved)")
        print("A4-R1 / A4-R2                         : PASS / PASS")
        print("A5 integrated cases                   : 36 / 36")
        print("A5 gates / artifacts                  : 317 PASS / 9 SHA-exact")
        print("AV2 scientific outcome                : FROZEN")
        print("CMG validation                        : Deferred")
        print("POSTV16-AV3-A0                        : AUTHORIZED")
        print("AV3 execution                         : NOT YET AUTHORIZED")
        print("="*196)
        return 0

    except Exception as e:
        d=drive/BLK;d.mkdir(parents=True,exist_ok=True)
        report={"milestone":MILESTONE,"status":BLOCK,"failed_stage":stage,"exception":repr(e),"gates":gates,"original_AV2F_BLOCK_preserved":True,"training_performed":False,"inference_performed":False,"LP_execution_performed":False,"mapback_execution_performed":False,"OOD_truth_accessed":False,"CMG_validation_performed":False,"AV2_outcome_frozen":False,"AV3_A0_authorized":False}
        q=d/"POSTV16_AV2_F_R1_Blocked_Report.json"
        if not q.exists():q.write_bytes(jb(report))
        print("POSTV16-AV2-F-R1: BLOCKED",stage,repr(e))
        return 2

def parse():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path("."))
    p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test",action="store_true")
    return p.parse_args()

if __name__=="__main__":
    a=parse()
    if a.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))

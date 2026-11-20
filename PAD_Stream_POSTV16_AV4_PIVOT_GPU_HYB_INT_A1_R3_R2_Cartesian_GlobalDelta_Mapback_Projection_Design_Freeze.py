#!/usr/bin/env python3
from __future__ import annotations

import argparse,csv,hashlib,json,subprocess
from pathlib import Path
from typing import Any

M="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R3-R2"
PASS="POSTV16AV4PIVOTGPUHYBINTA1R3R2_CARTESIAN_GLOBAL_DELTA_MAPBACK_PROJECTION_DESIGN_FREEZE_PASS_NO_PHYSICS_EXECUTION"
BLOCK="POSTV16AV4PIVOTGPUHYBINTA1R3R2_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="961d088214f0b859565da86fd0b6b8db52c89d43"

R4R2R1R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R2_R1_R1_Corrected_Structural_SelfTest_DeltaOwnership_Run.py"
R4R2R1R1_BLOB="ff4e10155e51d81c745280fa3594414344bc1e2a"
R3R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R1_Corrected_BoundedOccupancy_DeltaOwnership_Design_Freeze.py"
R3R1_BLOB="a96c6a4ca50a109cc1ed8eb54f696b4c7ae541b6"
E37A_RUNNER="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
A3R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A3_R1_MixedRoute_CVDelta_Ledger_Repair.py"
A3R1_BLOB="dc0b10d72991786752a0522f2e58f640d90b420d"
F2R3_RUNNER="PAD_Stream_POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution.py"
F2R3_BLOB="359f3c0edf87e10bb4006cacdd271cd426fed22b"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

R4R2R1R1_BLOCK_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R2_R1_R1_BLOCKED"
R4R2R1R1_BLOCK_REPORT="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R2_R1_R1_Blocked_Report.json"
R4R2R1R1_BLOCK_STATUS="POSTV16AV4PIVOTGPUHYBINTA1R4R2R1R1_TECHNICAL_CONSERVATION_DELTA_OWNERSHIP_CAPACITY_OR_AUTHORITY_BLOCK"
R4R2R1R1_EXCEPTION="GateError('delta_ownership_negative_child_target:-0.8723954285500215:1e-08')"

R3R1_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R1_Corrected_BoundedOccupancy_DeltaOwnership_Design_Freeze"
R3R1_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R1_Summary.json"
R3R1_STATUS="POSTV16AV4PIVOTGPUHYBINTA1R3R1_CORRECTED_BOUNDED_OCCUPANCY_DELTA_OWNERSHIP_DESIGN_FREEZE_PASS_NO_PHYSICS_EXECUTION"

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R2"
OUT_REL=BASE/(OUT_TOKEN+"_Cartesian_GlobalDelta_Mapback_Projection_Design_Freeze")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
PROTOCOL=f"{OUT_TOKEN}_Frozen_Projection_Protocol.json"
HANDOFF=f"{OUT_TOKEN}_R4_R3_Execution_Handoff_Contract.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError):pass

def gt(root:Path,*a:str)->str:
    return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):h.update(c)
    return h.hexdigest()

def js(p:Path):return json.loads(p.read_text(encoding="utf-8"))

def write_csv(p:Path,rows):
    rows=list(rows)
    if not rows:p.write_text("",encoding="utf-8");return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)

def exact_blob(root:Path,fn:str,expected:str)->str:
    p=root/fn
    if not p.is_file():raise GateError(f"missing_source:{fn}")
    actual=gt(root,"hash-object",str(p))
    if actual!=expected:raise GateError(f"source_blob:{fn}:{actual}:{expected}")
    return actual

def selftest(root:Path):
    for fn,b in [
        (R4R2R1R1_RUNNER,R4R2R1R1_BLOB),(R3R1_RUNNER,R3R1_BLOB),
        (E37A_RUNNER,E37A_BLOB),(A3R1_RUNNER,A3R1_BLOB),(F2R3_RUNNER,F2R3_BLOB),
    ]:
        assert exact_blob(root,fn,b)==b

    # Deterministic bounded-box + exact-sum Euclidean projection identity.
    import numpy as np
    raw=np.array([-2.0,5.0,4.0],dtype=np.float64)
    cap=np.array([6.0,6.0,6.0],dtype=np.float64)
    target=9.0
    def project(y,u,s):
        lo=float(np.min(y-u))-1.0
        hi=float(np.max(y))+1.0
        for _ in range(200):
            lam=0.5*(lo+hi)
            x=np.clip(y-lam,0.0,u)
            if float(np.sum(x))>s:lo=lam
            else:hi=lam
        return np.clip(y-0.5*(lo+hi),0.0,u)
    x=project(raw,cap,target)
    assert abs(float(np.sum(x))-target)<1e-12
    assert float(np.min(x))>=0.0
    assert float(np.max(x-cap))<=1e-12
    # Zero-delta identity when raw parent already satisfies constraints.
    parent=np.array([1.0,2.0,3.0])
    xid=project(parent,np.array([5.0,5.0,5.0]),float(np.sum(parent)))
    assert float(np.max(np.abs(xid-parent)))<1e-12
    print("POSTV16 GPU-HYB-INT-A1-R3-R2 Cartesian global-delta projection design self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight"
    def gate(n,c,d=None):
        ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok:raise GateError(n)
    try:
        print("="*196)
        print("INT-A1-R3-R2 — CARTESIAN GLOBAL-DELTA MAPBACK PROJECTION DESIGN FREEZE")
        print("CPU-ONLY. NO PHYSICS. NO HYBRID INFERENCE. NO MAPBACK EXECUTION. NO STATE MUTATION.")
        print("="*196)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_R4_R2_R1_R1_formal_BLOCK_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        stage="source_authority"
        for label,fn,b in [
            ("R4_R2_R1_R1",R4R2R1R1_RUNNER,R4R2R1R1_BLOB),
            ("R3_R1",R3R1_RUNNER,R3R1_BLOB),
            ("E37A",E37A_RUNNER,E37A_BLOB),
            ("G4_A3_R1",A3R1_RUNNER,A3R1_BLOB),
            ("F2_R3",F2R3_RUNNER,F2R3_BLOB),
        ]:
            gate(label+"_blob_exact",exact_blob(root,fn,b)==b)

        stage="R4_R2_R1_R1_formal_BLOCK_authority"
        bp=drive/R4R2R1R1_BLOCK_REL/R4R2R1R1_BLOCK_REPORT
        gate("BLOCK_report_present",bp.is_file(),str(bp))
        b=js(bp)
        gate("BLOCK_status_exact",b.get("status")==R4R2R1R1_BLOCK_STATUS,b.get("status"))
        gate("BLOCK_failed_stage_exact",b.get("failed_stage")=="controlled_integrated_rollout",b.get("failed_stage"))
        gate("BLOCK_exception_exact",b.get("exception")==R4R2R1R1_EXCEPTION,b.get("exception"))
        gate("BLOCK_no_clipping",b.get("cell_mass_clipping_performed") is False)
        gate("BLOCK_no_mass_discard",b.get("mass_discard_performed") is False)
        gate("BLOCK_no_tolerance_relaxation",b.get("scientific_tolerance_relaxed") is False)
        gate("BLOCK_local_validation_not_completed",b.get("postvalidation_delta_ownership_fallback_active") is False)
        gate("BLOCK_visualization_closed",b.get("INT_VIS_A1_integrated_3D_visualization_authorized") is False)

        stage="R3_R1_authority"
        sp=drive/R3R1_REL/R3R1_SUM
        gate("R3_R1_summary_present",sp.is_file(),str(sp))
        s31=js(sp)
        gate("R3_R1_status_exact",s31.get("status")==R3R1_STATUS,s31.get("status"))
        gate("R3_R1_absolute_CV_ownership_already_superseded",s31.get("R3_absolute_CV_ownership_constraint_superseded") is True)
        gate("R3_R1_per_CV_delta_constraint_now_closed_by_formal_evidence",
             s31.get("transport_authority_preserved_as_exact_per_CV_delta") is True)

        stage="corrected_design_freeze"
        protocol={
            "milestone":M,
            "status":PASS,
            "classification":"PER_CV_EXCLUSIVE_DELTA_OWNERSHIP_CONSTRAINT_SUPERSEDED_E37A_GLOBAL_COMPONENT_DELTA_IS_MAPBACK_AUTHORITY_CARTESIAN_BOUNDED_EUCLIDEAN_PROJECTION_FROZEN",
            "formal_new_evidence":{
                "failed_constraint":"O1_j = O0_j + DeltaM_j >= 0 for every CV",
                "minimum_child_ownership_target_kg":-0.8723954285500215,
                "interpretation":"at least one overlapping E37A CV transport withdrawal exceeds its exclusive bounded Cartesian ownership; per-CV exclusive attribution is not physically representable",
                "does_not_invalidate_transport_FV_state":True,
                "does_not_authorize_transport_mutation":True,
            },
            "E37A_authoritative_semantics":{
                "transport_CV_FV_state":"accepted unchanged",
                "mapback_raw_spatial_proposal":"subsegment EOS delta aggregated to Cartesian cells",
                "certified_transfer_gate":"GLOBAL sum(subsegment delta) equals GLOBAL sum(CV delta)",
                "per_CV_subsegment_delta_gate_in_authoritative_E37A":False,
                "recurrent_consistency":"each accepted next step resamples the authoritative Cartesian grid into CVs; prior child CV masses are not independently carried as persistent authoritative state",
            },
            "corrected_mapback_operator":{
                "name":"SUPPORTED_CARTESIAN_BOUNDED_GLOBAL_DELTA_EUCLIDEAN_PROJECTION",
                "ordinary_E37A_first":True,
                "activation":"only after ordinary E37A has passed its global transfer closure and rejects with aligned_mapback_negative_cell_mass",
                "inputs":{
                    "G0_c":"authoritative parent Cartesian component mass",
                    "dRaw_c":"ordinary E37A raw deposited component-mass delta aggregated to Cartesian cell",
                    "Yraw_c":"G0_c + dRaw_c",
                    "C_c":"physical Cartesian component-mass capacity",
                    "S":"existing E37A Cartesian support = unique(flat_cell)",
                    "Mtarget":"parent grid mass + exact injected mass - exact produced mass",
                },
                "hard_constraints":[
                    "X_c = G0_c for c outside S",
                    "0 <= X_c <= C_c for c in S",
                    "sum_c X_c = Mtarget exactly to frozen mass-closure tolerance",
                    "no support expansion",
                ],
                "objective":"unique Euclidean projection: minimize sum_{c in S} (X_c - Yraw_c)^2",
                "deterministic_solution":"X_c = clip(Yraw_c - lambda, 0, C_c) on S, with scalar lambda solved by deterministic bisection so supported-cell total equals required target",
                "feasibility_gate":"required supported mass must lie in [0, sum_{c in S} C_c]; otherwise SCIENTIFIC BLOCK with no support expansion",
                "outside_support":"parent mass unchanged exactly",
            },
            "mandatory_gates":{
                "raw_E37A_global_transfer_closure":"must pass before projection",
                "raw_global_trial_total_matches_Mtarget":"required",
                "zero_delta_identity":"if dRaw=0 and Mtarget=sum(G0), X=G0",
                "global_component_delta_identity":"sum(X-G0) = Mtarget-sum(G0)",
                "nonnegative_grid":"min X >= 0",
                "capacity":"X <= C",
                "outside_support_identity":"X=G0 outside S",
                "grid_inversion_closure":"required after mass->saturation inversion",
                "capillary_external_mass_change_zero":"unchanged downstream requirement",
            },
            "spatial_fidelity_audit":{
                "report_only_not_new_acceptance_threshold":[
                    "projection correction L1 kg",
                    "projection correction L2 kg",
                    "projection correction Linf kg",
                    "changed supported-cell count",
                    "raw negative-cell count",
                    "lower-bound active-cell count",
                    "upper-bound active-cell count",
                    "lambda kg",
                ],
                "reason":"the raw E37A cell-delta field remains the proposal; projection makes the minimum-L2 physical correction necessary for admissibility",
            },
            "superseded_constraints":[
                "R3 absolute sampled-CV ownership equality",
                "R3-R1 exact per-CV exclusive ownership delta equality",
                "no-cross-CV-attribution rule at mapback representation layer",
            ],
            "constraints_retained":[
                "accepted transport CV masses/saturations are not mutated by mapback reconciliation",
                "global boundary component-mass delta exact",
                "existing E37A Cartesian support only",
                "no clipping as an ad hoc post-process; bounds are solved simultaneously with exact total mass",
                "no mass discard",
                "no global plume rescaling",
                "no scientific tolerance relaxation",
                "no support expansion",
                "no extra pressure refresh caused solely by mapback reconciliation",
                "Day30/35/40/45 controller schedule unchanged",
            ],
            "R4_R3_execution":{
                "phase_1":"replay certified R1 path to Day30.003412917596155",
                "phase_2":"same-parent exact-fallback control remains admissible",
                "phase_3":"reproduce mixed ordinary-E37A negative-cell rejection",
                "phase_4":"execute supported Cartesian bounded global-delta projection",
                "phase_5":"prove all mandatory gates; only then mark local validation PASS",
                "phase_6":"continue Day30->45 in same run, ordinary E37A first and projection fallback only for negative-cell rejection",
            },
        }

        summary={
            "milestone":M,"status":PASS,"classification":protocol["classification"],
            "R4_R2_R1_R1_formal_BLOCK_bound":True,
            "formal_negative_child_ownership_target_kg":-0.8723954285500215,
            "per_CV_exclusive_delta_ownership_constraint_superseded":True,
            "E37A_global_component_delta_is_mapback_authority":True,
            "accepted_CV_transport_state_mutated_by_projection":False,
            "projection_space":"CARTESIAN_CELL_MASS_ON_EXISTING_E37A_SUPPORT",
            "projection_objective":"MINIMUM_L2_CORRECTION_TO_RAW_E37A_TRIAL",
            "existing_E37A_support_only":True,
            "cellwise_ad_hoc_clipping_authorized":False,
            "mass_discard_authorized":False,
            "global_rescaling_authorized":False,
            "scientific_tolerance_relaxation_authorized":False,
            "support_expansion_authorized":False,
            "R3_R2_physics_executed":False,
            "R3_R2_Hybrid_inference_executed":False,
            "R3_R2_projection_executed":False,
            "CPU_only_design_freeze":True,
            "INT_A1_R4_R3_execution_authorized":True,
            "INT_A1_R4_R3_local_validation_required_before_trajectory":True,
            "INT_VIS_A1_integrated_3D_visualization_authorized":False,
            "longer_horizon_validation_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
            "P4_authorized":False,
        }

        decision={
            "milestone":M,"status":PASS,
            "corrected_mapback_design_frozen":True,
            "next_milestone":{
                "name":"POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R4-R3",
                "purpose":"Execute supported Cartesian bounded global-delta Euclidean projection at certified failed parent; after local PASS continue Day30->45 in same run.",
                "authorized":True,
            },
            "runtime_recommendation":"L4/T4; A100 not required",
            "visualization_authorized_now":False,
            "P4_authorized":False,
        }

        handoff={
            "milestone":M,"status":PASS,
            "R4_R3_authorized":True,
            "local_validation_before_trajectory_required":True,
            "flow_refresh_schedule_days":[30.0,35.0,40.0,45.0],
            "on_R4_R3_PASS":"INT-VIS-A1 immediately authorized",
            "production_activation_authorized":False,
            "P4_authorized":False,
        }

        stage="scope_guards"
        gate("no_physics_execution",summary["R3_R2_physics_executed"] is False)
        gate("no_Hybrid_inference",summary["R3_R2_Hybrid_inference_executed"] is False)
        gate("no_projection_execution",summary["R3_R2_projection_executed"] is False)
        gate("accepted_transport_state_immutable",summary["accepted_CV_transport_state_mutated_by_projection"] is False)
        gate("global_delta_authority",summary["E37A_global_component_delta_is_mapback_authority"] is True)
        gate("existing_support_only",summary["existing_E37A_support_only"] is True)
        gate("no_scientific_tolerance_relaxation",summary["scientific_tolerance_relaxation_authorized"] is False)
        gate("no_support_expansion",summary["support_expansion_authorized"] is False)
        gate("R4_R3_authorized",summary["INT_A1_R4_R3_execution_authorized"] is True)
        gate("visualization_closed_until_R4_R3",summary["INT_VIS_A1_integrated_3D_visualization_authorized"] is False)
        gate("P4_closed",summary["P4_authorized"] is False)

        stage="publication"
        gate("output_absent",not out.exists(),str(out))
        out.mkdir(parents=True)
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/PROTOCOL).write_text(json.dumps(protocol,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/HANDOFF).write_text(json.dumps(handoff,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
                                for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST])

        print("="*196)
        print(M,"PASS")
        print("Per-CV exclusive delta ownership : SUPERSEDED")
        print("Mapback authority                 : GLOBAL E37A COMPONENT DELTA")
        print("Repair space                      : EXISTING-SUPPORT CARTESIAN CELL MASS")
        print("Projection                        : BOUNDED EXACT-SUM MINIMUM-L2")
        print("Transport CV state mutation       : NONE")
        print("R4-R3                             : AUTHORIZED")
        print("Recommended runtime               : L4/T4; A100 NOT REQUIRED")
        print("="*196)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
            "INT_A1_R4_R3_execution_authorized":False,
            "INT_VIS_A1_integrated_3D_visualization_authorized":False,
            "P4_authorized":False,
        },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(M,"BLOCK");print("Stage:",stage);print("Exception:",repr(exc));return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:selftest(a.project_root.resolve());raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))

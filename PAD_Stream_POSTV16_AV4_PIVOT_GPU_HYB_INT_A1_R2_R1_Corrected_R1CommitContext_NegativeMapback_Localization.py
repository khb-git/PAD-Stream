#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math, re, shutil, subprocess, sys
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R2-R1"
PASS="POSTV16AV4PIVOTGPUHYBINTA1R2R1_CORRECTED_R1_COMMIT_CONTEXT_NEGATIVE_MAPBACK_LOCALIZATION_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBINTA1R2R1_DIAGNOSTIC_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="ab4146abfbc308b6cab600c196383c104b95a4b1"

R2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R2_NegativeMapback_DTRefinement_Failure_Localization.py"
R2_BLOB="f41344280f3693c573453da53fb06551bf9524d6"
R2_BLOCK_STATUS="POSTV16AV4PIVOTGPUHYBINTA1R2_DIAGNOSTIC_BLOCK"
R2_EXPECTED_FAILED_STAGE="R1_instrumented_reproduction"
R2_EXPECTED_EXCEPTION="GateError('sandbox_failure_is_negative_retry_exhaustion')"
R1_COMMIT="b866afb1b54e646a739c4f62148f21b3642fe200"
R1_PARENT="e80dd6bf78c727daed33d8c6c8819b2952f5e8a8"

R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R1_NegativeMapback_TimestepRetry_Repair_and_WholeSystem_Run.py"
R1_BLOB="4070629c1a863d1504094c51246f3adc647edfaf"
E37A_RUNNER="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
A3R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A3_R1_MixedRoute_CVDelta_Ledger_Repair.py"
A3R1_BLOB="dc0b10d72991786752a0522f2e58f640d90b420d"
F4LOC_RUNNER="PAD_Stream_POSTV16_AV4_F4_R3_R3_R1_Event_MapBack_Negative_Cell_Localization.py"
F4LOC_BLOB="347ba736f4a0f7e56de37365bbc9dcbf623cc860"
F4FREEZE_RUNNER="PAD_Stream_POSTV16_AV4_F4_R3_R3_R2_Bounded_Parent_Ownership_Event_MapBack_Reconciliation_Freeze.py"
F4FREEZE_BLOB="247e1e5b6d3fc83bd81d3dd84f0bbeb88c5280c0"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
R1_BLOCK_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R1_BLOCKED"
R1_BLOCK_REPORT="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R1_Blocked_Report.json"
R1_BLOCK_STATUS="POSTV16AV4PIVOTGPUHYBINTA1R1_TECHNICAL_CONSERVATION_MAPBACK_CAPACITY_OR_AUTHORITY_BLOCK"
R1_EXCEPTION_PREFIX="GateError('negative_mapback_retry_budget_exhausted:"
R2_BLOCK_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R2_BLOCKED"
R2_BLOCK_REPORT="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R2_Blocked_Report.json"

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R2_R1"
OUT_REL=BASE/(OUT_TOKEN+"_Corrected_R1CommitContext_NegativeMapback_Localization")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SANDBOX_REL=BASE/(OUT_TOKEN+"_R1_Reproduction_Sandbox")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
ATTEMPTS=f"{OUT_TOKEN}_Mapback_Attempt_Localization.csv"
WORST=f"{OUT_TOKEN}_Worst_Cell_Contribution_Audit.csv"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError): pass

def gt(root:Path,*a:str)->str:
    return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def exact_mod(root:Path,fn:str,blob_expected:str,name:str):
    p=root/fn
    if not p.is_file(): raise GateError(f"missing_source:{fn}")
    actual=gt(root,"hash-object",str(p))
    if actual!=blob_expected: raise GateError(f"source_blob:{fn}:{actual}:{blob_expected}")
    s=importlib.util.spec_from_file_location(name,p)
    if s is None or s.loader is None: raise GateError(f"import_spec:{fn}")
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def js(p:Path): return json.loads(p.read_text(encoding="utf-8"))

def write_csv(p:Path,rows):
    rows=list(rows)
    if not rows:
        p.write_text("",encoding="utf-8");return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)

def arrhash(*arrays)->str:
    h=hashlib.sha256()
    for a in arrays:
        x=np.ascontiguousarray(np.asarray(a))
        h.update(str(x.shape).encode());h.update(str(x.dtype).encode());h.update(x.tobytes())
    return h.hexdigest()

def selftest(root:Path):
    r2=exact_mod(root,R2_RUNNER,R2_BLOB,"inta1r2r1_r2_selftest")
    r1=exact_mod(root,R1_RUNNER,R1_BLOB,"inta1r2r1_r1_selftest")
    e37=exact_mod(root,E37A_RUNNER,E37A_BLOB,"inta1r2r1_e37a_selftest")
    exact_mod(root,A3R1_RUNNER,A3R1_BLOB,"inta1r2r1_a3r1_selftest")
    exact_mod(root,F4LOC_RUNNER,F4LOC_BLOB,"inta1r2r1_f4loc_selftest")
    exact_mod(root,F4FREEZE_RUNNER,F4FREEZE_BLOB,"inta1r2r1_f4freeze_selftest")
    assert r2.M=="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R2"
    assert r1.NEGATIVE_MAPBACK_RETRY_FACTOR==0.5
    assert r1.MAX_NEGATIVE_MAPBACK_RETRIES==12
    assert hasattr(e37,"map_control_volume_increment_to_grid")
    assert hasattr(e37,"advance_component_mass_control_volumes")
    print("POSTV16 GPU-HYB-INT-A1-R2-R1 corrected R1-commit-context diagnostic self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve()
    out=drive/OUT_REL;blocked=drive/BLOCK_REL;sandbox=drive/SANDBOX_REL
    gates=[];stage="preflight"
    def gate(n,c,d=None):
        ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok: raise GateError(n)
    try:
        print("="*190)
        print("INT-A1-R2-R1 — CORRECTED R1-COMMIT-CONTEXT NEGATIVE MAPBACK LOCALIZATION")
        print("READ-ONLY DIAGNOSTIC REPRODUCTION. R1 IS REPLAYED IN A LOCAL CLONE PINNED TO ITS IMMUTABLE COMMIT.")
        print("="*190)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_immutable_R2_BLOCK_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        stage="source_authority"
        r2=exact_mod(root,R2_RUNNER,R2_BLOB,"inta1r2r1_r2")
        r1=exact_mod(root,R1_RUNNER,R1_BLOB,"inta1r2r1_r1")
        exact_mod(root,E37A_RUNNER,E37A_BLOB,"inta1r2r1_e37a_reference")
        exact_mod(root,A3R1_RUNNER,A3R1_BLOB,"inta1r2r1_a3r1")
        exact_mod(root,F4LOC_RUNNER,F4LOC_BLOB,"inta1r2r1_f4loc")
        exact_mod(root,F4FREEZE_RUNNER,F4FREEZE_BLOB,"inta1r2r1_f4freeze")

        stage="R2_immutable_BLOCK_authority"
        r2bp=drive/R2_BLOCK_REL/R2_BLOCK_REPORT
        gate("R2_BLOCK_report_present",r2bp.is_file(),str(r2bp))
        r2b=js(r2bp)
        gate("R2_BLOCK_status_exact",r2b.get("status")==R2_BLOCK_STATUS,r2b.get("status"))
        gate("R2_BLOCK_failed_stage_exact",r2b.get("failed_stage")==R2_EXPECTED_FAILED_STAGE,r2b.get("failed_stage"))
        gate("R2_BLOCK_exception_exact",r2b.get("exception")==R2_EXPECTED_EXCEPTION,r2b.get("exception"))
        gate("R2_R3_design_not_authorized",r2b.get("INT_A1_R3_parent_ownership_mapback_reconciliation_design_freeze_authorized") is False)
        gate("R2_visualization_closed",r2b.get("INT_VIS_A1_integrated_3D_visualization_authorized") is False)
        gate("R2_P4_closed",r2b.get("P4_authorized") is False)

        stage="R1_block_authority"
        bp=drive/R1_BLOCK_REL/R1_BLOCK_REPORT
        gate("R1_BLOCK_report_present",bp.is_file(),str(bp))
        b=js(bp)
        gate("R1_BLOCK_status_exact",b.get("status")==R1_BLOCK_STATUS,b.get("status"))
        gate("R1_BLOCK_failed_stage",b.get("failed_stage")=="controlled_integrated_rollout",b.get("failed_stage"))
        gate("R1_BLOCK_exception_prefix",str(b.get("exception","")).startswith(R1_EXCEPTION_PREFIX),b.get("exception"))
        gate("R1_no_clipping",b.get("cell_mass_clipping_performed") is False)
        gate("R1_no_mass_discard",b.get("mass_discard_performed") is False)
        gate("R1_no_tolerance_relaxation",b.get("scientific_tolerance_relaxed") is False)
        gate("R1_visualization_closed",b.get("INT_VIS_A1_integrated_3D_visualization_authorized") is False)

        stage="sandbox_reproduction_setup"
        if sandbox.exists(): shutil.rmtree(sandbox)
        sandbox.mkdir(parents=True)

        # R2 originally called r1.main() against the R2 checkout. That correctly
        # failed R1's immutable repository-parent gate before the diagnostic was reached.
        # Corrected method: make an isolated local clone and pin its branch to the
        # immutable R1 commit so R1 sees exactly the repository identity it was built for.
        replay_repo=root.parent/"PAD-Stream-INT-A1-R1-Diagnostic-Replay"
        if replay_repo.exists(): shutil.rmtree(replay_repo)
        subprocess.check_call(["git","clone","--no-local",str(root),str(replay_repo)])
        subprocess.check_call(["git","-C",str(replay_repo),"checkout","-B",BRANCH,R1_COMMIT])
        gate("replay_repo_branch_exact",gt(replay_repo,"branch","--show-current")==BRANCH,gt(replay_repo,"branch","--show-current"))
        gate("replay_repo_HEAD_is_R1_commit",gt(replay_repo,"rev-parse","HEAD")==R1_COMMIT,gt(replay_repo,"rev-parse","HEAD"))
        gate("replay_repo_parent_is_original_INT_A1_BLOCK",gt(replay_repo,"rev-parse","HEAD^")==R1_PARENT,gt(replay_repo,"rev-parse","HEAD^"))
        gate("replay_repo_clean",gt(replay_repo,"status","--porcelain")=="")

        # Redirect only R1 publication/block paths. All authority artifacts remain read-only in Drive.
        r1.OUT_REL=SANDBOX_REL/"R1_OUT"
        r1.BLOCK_REL=SANDBOX_REL/"R1_BLOCK"
        attempts=[]
        last_exact={}
        wrapped_modules=set()
        orig_mod=r1.mod

        def instrument_module(m,fn):
            if not (hasattr(m,"advance_component_mass_control_volumes")
                    and hasattr(m,"map_control_volume_increment_to_grid")
                    and hasattr(m,"TrialReject")):
                return m
            if id(m) in wrapped_modules: return m
            wrapped_modules.add(id(m))
            orig_adv=m.advance_component_mass_control_volumes
            orig_map=m.map_control_volume_increment_to_grid

            def adv(*args,**kwargs):
                res=orig_adv(*args,**kwargs)
                dt=float(args[-1] if args else kwargs["dt_days"])
                last_exact.clear()
                last_exact.update({
                    "dt_days":dt,
                    "new_mass":np.asarray(res["new_mass"],float).copy(),
                    "new_sat":np.asarray(res["new_saturation"],float).copy(),
                })
                return res

            def mapwrap(*args,**kwargs):
                # Frozen E37A signature:
                # r2,parent_grid_sat,old_cv_sat,new_cv_sat,old_cv_mass,new_cv_mass,
                # geometry,pressure,pref,cell_pv,target_final
                r2=args[0];parent_sat=np.asarray(args[1],float)
                old_sat=np.asarray(args[2],float);mixed_sat=np.asarray(args[3],float)
                old_mass=np.asarray(args[4],float);mixed_mass=np.asarray(args[5],float)
                geom=args[6];pressure=np.asarray(args[7],float);pref=float(args[8])
                cellpv=float(args[9]);target=float(args[10])
                dt=float(last_exact.get("dt_days",float("nan")))
                exact_mass=np.asarray(last_exact["new_mass"],float)
                exact_sat=np.asarray(last_exact["new_sat"],float)

                cv_id=np.asarray(geom["cv_id"],int)
                flat=np.asarray(geom["flat_cell"],int)
                pv=np.asarray(geom["pv_m3"],float)
                pseg=np.asarray(geom["pseg_psi"],float)

                def subdelta(newsat):
                    of=old_sat.reshape(-1)[cv_id];nf=np.asarray(newsat,float).reshape(-1)[cv_id]
                    osg=np.clip(of-m.BACKGROUND_SATURATION,0.0,m.MAX_INCREMENTAL_CO2_SATURATION)
                    nsg=np.clip(nf-m.BACKGROUND_SATURATION,0.0,m.MAX_INCREMENTAL_CO2_SATURATION)
                    ro=np.asarray(r2.gas_density_from_state(of,pseg,pref),float)
                    rn=np.asarray(r2.gas_density_from_state(nf,pseg,pref),float)
                    oldsub=pv*ro*osg
                    newsub=pv*rn*nsg
                    dep=np.bincount(flat,weights=newsub-oldsub,minlength=int(np.prod(m.EXPECTED_GRID))).reshape(m.EXPECTED_GRID)
                    oldcell=np.bincount(flat,weights=oldsub,minlength=int(np.prod(m.EXPECTED_GRID))).reshape(m.EXPECTED_GRID)
                    return dep,oldcell

                parent_sg=np.clip(parent_sat-m.BACKGROUND_SATURATION,0.0,m.MAX_INCREMENTAL_CO2_SATURATION)
                parent_rho=np.asarray(r2.gas_density_from_state(parent_sat,pressure,pref),float)
                parent_mass=cellpv*parent_rho*parent_sg
                dep_mixed,raw_old_cell=subdelta(mixed_sat)
                dep_exact,_=subdelta(exact_sat)
                trial_mixed=parent_mass+dep_mixed
                trial_exact=parent_mass+dep_exact
                worst=np.unravel_index(int(np.argmin(trial_mixed)),trial_mixed.shape)
                flatworst=np.ravel_multi_index(worst,trial_mixed.shape)
                coverage_pv=float(np.sum(pv[flat==flatworst]))/cellpv
                route_change=np.max(np.abs(mixed_mass-exact_mass),axis=1)
                changed=int(np.sum(route_change>1e-8))
                parent_fp=arrhash(parent_sat,pressure)

                exact_pass=True;exact_reason=""
                try:
                    orig_map(r2,parent_sat,old_sat,exact_sat,old_mass,exact_mass,geom,pressure,pref,cellpv,target)
                except Exception as ex:
                    exact_pass=False;exact_reason=repr(ex)

                row={
                    "attempt_index":len(attempts)+1,
                    "parent_fingerprint":parent_fp,
                    "dt_days":dt,
                    "hybrid_changed_route_count":changed,
                    "mixed_min_trial_cell_mass_kg":float(np.min(trial_mixed)),
                    "mixed_negative_cell_count":int(np.sum(trial_mixed < -max(1e-6,1e-10*max(abs(target),1.0)))),
                    "exact_min_trial_cell_mass_kg":float(np.min(trial_exact)),
                    "exact_negative_cell_count":int(np.sum(trial_exact < -max(1e-6,1e-10*max(abs(target),1.0)))),
                    "exact_mapback_pass":exact_pass,
                    "exact_mapback_reason":exact_reason,
                    "worst_k":int(worst[0]),"worst_j":int(worst[1]),"worst_i":int(worst[2]),
                    "worst_parent_cell_mass_kg":float(parent_mass[worst]),
                    "worst_raw_old_subsegment_mass_kg":float(raw_old_cell[worst]),
                    "worst_raw_old_minus_parent_cell_mass_kg":float(raw_old_cell[worst]-parent_mass[worst]),
                    "worst_mixed_deposited_delta_kg":float(dep_mixed[worst]),
                    "worst_exact_deposited_delta_kg":float(dep_exact[worst]),
                    "worst_hybrid_minus_exact_delta_kg":float(dep_mixed[worst]-dep_exact[worst]),
                    "worst_coverage_pv_over_cell_pv":coverage_pv,
                }
                try:
                    outm=orig_map(*args,**kwargs)
                    row["mixed_mapback_pass"]=True;row["mixed_mapback_reason"]=""
                    attempts.append(row);return outm
                except Exception as ex:
                    row["mixed_mapback_pass"]=False;row["mixed_mapback_reason"]=repr(ex)
                    attempts.append(row);raise

            m.advance_component_mass_control_volumes=adv
            m.map_control_volume_increment_to_grid=mapwrap
            return m

        def patched_mod(rootp,fn,expected,name):
            m=orig_mod(rootp,fn,expected,name)
            return instrument_module(m,fn)
        r1.mod=patched_mod

        stage="R1_instrumented_reproduction"
        rc=r1.main(replay_repo,drive)
        gate("instrumented_R1_reproduces_BLOCK",rc==2,rc)
        gate("instrumented_reproduction_did_not_fail_repository_identity",len(attempts)>0,len(attempts))
        sb=drive/r1.BLOCK_REL/f"{r1.OUT_TOKEN}_Blocked_Report.json"
        gate("sandbox_BLOCK_report_present",sb.is_file(),str(sb))
        sbj=js(sb)
        gate("sandbox_failure_is_negative_retry_exhaustion",
             str(sbj.get("exception","")).startswith(R1_EXCEPTION_PREFIX),sbj.get("exception"))
        gate("mapback_attempts_captured",len(attempts)>0,len(attempts))

        stage="failure_localization"
        # Last parent fingerprint is the retry-exhaustion parent.
        last_fp=attempts[-1]["parent_fingerprint"]
        failed=[r for r in attempts if r["parent_fingerprint"]==last_fp]
        gate("failed_parent_attempt_count_at_least_13",len(failed)>=13,len(failed))
        failed=failed[-13:]
        dts=[float(r["dt_days"]) for r in failed]
        mixedmins=[float(r["mixed_min_trial_cell_mass_kg"]) for r in failed]
        exactmins=[float(r["exact_min_trial_cell_mass_kg"]) for r in failed]
        gate("retry_dt_halving_exact",
             all(abs(dts[i+1]/dts[i]-0.5)<=1e-12 for i in range(len(dts)-1)),
             dts)
        gate("dt_refined_at_least_4096x",dts[-1] <= dts[0]/4096.0*(1+1e-12),(dts[0],dts[-1]))
        gate("all_failed_parent_mixed_mapbacks_rejected",
             all(not bool(r["mixed_mapback_pass"]) for r in failed))
        gate("all_failed_parent_exact_fallback_mapbacks_admissible",
             all(bool(r["exact_mapback_pass"]) for r in failed),
             [(r["dt_days"],r["exact_mapback_reason"]) for r in failed if not r["exact_mapback_pass"]])
        gate("mixed_negative_persists_at_smallest_dt",mixedmins[-1] < -1e-3,mixedmins[-1])
        gate("exact_smallest_dt_nonnegative",exactmins[-1] >= -1e-6,exactmins[-1])
        gate("mixed_failure_nonvanishing_under_refinement",
             abs(mixedmins[-1]) >= 0.25*abs(mixedmins[0]),(mixedmins[0],mixedmins[-1]))

        worstrow=min(failed,key=lambda r:r["mixed_min_trial_cell_mass_kg"])
        lastrow=failed[-1]
        gate("Hybrid_delta_is_local_difference_vs_exact_at_smallest_dt",
             float(lastrow["worst_hybrid_minus_exact_delta_kg"]) < -1e-3,
             lastrow["worst_hybrid_minus_exact_delta_kg"])
        gate("same_worst_cell_persists",
             len({(r["worst_k"],r["worst_j"],r["worst_i"]) for r in failed})==1,
             [(r["worst_k"],r["worst_j"],r["worst_i"]) for r in failed])
        gate("parent_raw_subsegment_ownership_exceeds_cartesian_cell_at_worst",
             float(lastrow["worst_raw_old_minus_parent_cell_mass_kg"])>0.0,
             lastrow["worst_raw_old_minus_parent_cell_mass_kg"])

        classification=(
            "MIXED_HYBRID_CV_DELTA_TO_CARTESIAN_REPRESENTATION_DISAGGREGATION_"
            "INCOMPATIBILITY_PERSISTENT_UNDER_DT_REFINEMENT_EXACT_FALLBACK_"
            "MAPBACK_ADMISSIBLE_PARENT_OWNERSHIP_RECONCILIATION_DESIGN_REQUIRED"
        )

        stage="publication"
        gate("output_absent",not out.exists(),str(out))
        out.mkdir(parents=True)
        write_csv(out/ATTEMPTS,attempts)
        write_csv(out/WORST,[{
            "failed_parent_fingerprint":last_fp,
            "retry_attempt_count":len(failed),
            "first_dt_days":dts[0],
            "last_dt_days":dts[-1],
            "dt_refinement_factor":dts[0]/dts[-1],
            "first_mixed_min_cell_mass_kg":mixedmins[0],
            "last_mixed_min_cell_mass_kg":mixedmins[-1],
            "first_exact_min_cell_mass_kg":exactmins[0],
            "last_exact_min_cell_mass_kg":exactmins[-1],
            "worst_cell_kji":f"({lastrow['worst_k']},{lastrow['worst_j']},{lastrow['worst_i']})",
            "last_parent_cell_mass_kg":lastrow["worst_parent_cell_mass_kg"],
            "last_raw_old_subsegment_mass_kg":lastrow["worst_raw_old_subsegment_mass_kg"],
            "last_raw_old_minus_parent_cell_mass_kg":lastrow["worst_raw_old_minus_parent_cell_mass_kg"],
            "last_mixed_deposited_delta_kg":lastrow["worst_mixed_deposited_delta_kg"],
            "last_exact_deposited_delta_kg":lastrow["worst_exact_deposited_delta_kg"],
            "last_Hybrid_minus_exact_delta_kg":lastrow["worst_hybrid_minus_exact_delta_kg"],
            "coverage_pv_over_cell_pv":lastrow["worst_coverage_pv_over_cell_pv"],
            "Hybrid_changed_route_count":lastrow["hybrid_changed_route_count"],
        }])

        summary={
            "milestone":M,"status":PASS,"classification":classification,
            "immutable_INT_A1_R2_BLOCK_bound":True,
            "R2_block_classification":"TECHNICAL_DIAGNOSTIC_HARNESS_CONTEXT_ERROR_NO_SCIENTIFIC_CONCLUSION",
            "corrected_R1_commit_context_replay":True,
            "immutable_INT_A1_R1_BLOCK_bound":True,
            "instrumented_R1_reproduction_exit_code":rc,
            "failed_parent_retry_attempt_count":len(failed),
            "first_failed_parent_trial_dt_days":dts[0],
            "smallest_failed_parent_trial_dt_days":dts[-1],
            "dt_refinement_factor":dts[0]/dts[-1],
            "first_mixed_min_trial_cell_mass_kg":mixedmins[0],
            "smallest_dt_mixed_min_trial_cell_mass_kg":mixedmins[-1],
            "smallest_dt_exact_min_trial_cell_mass_kg":exactmins[-1],
            "exact_fallback_mapback_admissible_for_all_failed_parent_retries":True,
            "mixed_mapback_rejected_for_all_failed_parent_retries":True,
            "negative_failure_nonvanishing_under_dt_refinement":True,
            "worst_cell_kji":[lastrow["worst_k"],lastrow["worst_j"],lastrow["worst_i"]],
            "worst_cell_parent_raw_subsegment_ownership_excess_kg":lastrow["worst_raw_old_minus_parent_cell_mass_kg"],
            "worst_cell_Hybrid_minus_exact_delta_kg":lastrow["worst_hybrid_minus_exact_delta_kg"],
            "timestep_only_repair_rejected":True,
            "cell_mass_clipping_authorized":False,
            "mass_discard_authorized":False,
            "tolerance_relaxation_authorized":False,
            "support_expansion_authorized":False,
            "INT_A1_R3_parent_ownership_mapback_reconciliation_design_freeze_authorized":True,
            "INT_A1_R3_execution_authorized":False,
            "INT_VIS_A1_integrated_3D_visualization_authorized":False,
            "longer_horizon_validation_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
            "P4_authorized":False,
        }
        decision={
            "milestone":M,"status":PASS,
            "immutable_R2_BLOCK_preserved":True,
            "R2_harness_error_corrected":True,
            "timestep_refinement_repair_closed_as_insufficient":True,
            "repair_family_selected":"BOUNDED_PARENT_OWNERSHIP_PRESERVING_MIXED_CV_TO_CARTESIAN_RECONCILIATION",
            "reason":"exact fallback mapback remains admissible while mixed Hybrid mapback retains a nonvanishing local negative cell under >4096x dt refinement; parent raw subsegment inventory exceeds Cartesian ownership at the persistent worst cell",
            "next_milestone":{
                "name":"POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R3",
                "purpose":"Design/freeze a mixed-route parent-ownership-preserving CV-to-Cartesian mapback reconciliation on existing E37A support, preserving each transported CV mass exactly and the immutable residual Cartesian inventory.",
                "authorized":True,
                "execution_authorized":False,
            },
            "prohibitions":["cellwise_clipping","mass_discard","global_rescaling","scientific_tolerance_relaxation","automatic_support_expansion"],
            "P4_authorized":False,
        }
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
                                for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST])

        print("="*190)
        print(M,"PASS")
        print("Classification:",classification)
        print("Failed-parent retry attempts               :",len(failed))
        print("dt first / smallest                       :",dts[0],"/",dts[-1])
        print("dt refinement factor                      :",dts[0]/dts[-1])
        print("Mixed min cell mass first / smallest kg   :",mixedmins[0],"/",mixedmins[-1])
        print("Exact min cell mass at smallest dt kg     :",exactmins[-1])
        print("Persistent worst cell kji                 :",(lastrow["worst_k"],lastrow["worst_j"],lastrow["worst_i"]))
        print("Raw old subsegment ownership excess kg    :",lastrow["worst_raw_old_minus_parent_cell_mass_kg"])
        print("Hybrid-minus-exact delta at worst cell kg :",lastrow["worst_hybrid_minus_exact_delta_kg"])
        print("Timestep-only repair                      : CLOSED / INSUFFICIENT")
        print("INT-A1-R3 design freeze                   : AUTHORIZED")
        print("INT-A1-R3 execution                       : NOT AUTHORIZED")
        print("="*190)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
            "immutable_INT_A1_R2_BLOCK_preserved":True,
            "INT_A1_R3_parent_ownership_mapback_reconciliation_design_freeze_authorized":False,
            "INT_VIS_A1_integrated_3D_visualization_authorized":False,
            "production_pressure_refresh_cadence_selected":False,"P4_authorized":False,
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

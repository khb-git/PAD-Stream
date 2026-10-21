#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, io, json, subprocess
from pathlib import Path
from typing import Any
import numpy as np

MILESTONE="POSTV16-AV3-A6"
STATUS_PASS=(
"AV3A6_FROZEN_EPOCH92_CHECKPOINT_LOCAL_PV_R7D_TERMINAL_HALO_"
"DEPLOYMENT_AND_INTEGRATION_CONTRACT_PROSPECTIVELY_FROZEN_NO_EXECUTION"
)
STATUS_BLOCKED="AV3A6_DEPLOYMENT_INTEGRATION_CONTRACT_FREEZE_BLOCKED"
RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT="6560d21f0c145dacd03da8fbc04d31b89377e7fd"
CKSHA="17b188494e0452570d43e868c20c4c814e6a1f0b493329d0e40849c4c5ec6d4e"
BEST_EPOCH=92
EPOCHS=122
BEST_VAL=0.002138707781058555

SOURCES={
"PAD_Stream_POSTV16_AV3_A5_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation.py":"b2dd3fb27966a51e6a6057e444dfdb617976b36f",
"PAD_Stream_POSTV16_AV3_A5_R1_PreOOD_Technical_Block_Closure.py":"1710ddffc2cb74ce171010ea55011b6c31ccad83",
"PAD_Stream_POSTV16_AV3_A4_R2_Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py":"289901331e835afb44ff2f665fe9a6bbea2eac19",
"PAD_Stream_POSTV16_AV3_A2_Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling.py":"e7d4f1b1e69ea3e756c4f41d7edb57e2ffd87d7b",
"PAD_Stream_POSTV16_AV2_A5_Frozen_Checkpoint_LocalPV_R7D_Integration.py":"f2cc67b80a17eccfca54f4330b2259ef9b7e377c",
"PAD_Stream_POSTV16_AV1_D_R7_R7E_Frozen_Horizontal_Face_Halo_Occupancy_Domain_Execution.py":"9f99d9dcab649ba7ac911ad09ad79b4e0eb2ecc8",
"PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py":"8d9561d7c85805b82dedc26073c4633f90eeeab6",
"PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py":"0bbf98ed89cee9128ef1d313c321f9a401b4e9f0",
"PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py":"890088c0c0fcab415a2c7351c5079ca8ee12bf82",
"PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py":"a127f8730a16e150713420ea547a8de6255550ef",
}

BASE=Path("post_v16")/RID/"POSTV16_AV3_Corey_Relperm_Heterogeneity"
A5R2D=BASE/"POSTV16_AV3_A5_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation"
A5R2SUM="PAD_Stream_POSTV16_AV3_A5_R2_Summary.json"
A5R2DEC="POSTV16_AV3_A5_R2_Decision_Contract.json"
A5R2AUTH="POSTV16_AV3_A5_R2_Frozen_Checkpoint_Continuation_Authority.json"
A5R2OOD="POSTV16_AV3_A5_R2_LockedOOD_Truth_and_Predictions.npz"
A5R2MAN="POSTV16_AV3_A5_R2_Artifact_Manifest.csv"
A5R2STATUS=(
"AV3A5R2_FROZEN_EPOCH92_CHECKPOINT_PRE_OOD_INTEGRITY_CORRECTED_"
"LOCKED_OOD_TEACHER_GENERATED_ONCE_EVALUATED_ONCE_PASS"
)

A4R2D=BASE/"POSTV16_AV3_A4_R2_Corrected_Teacher_Dataset_and_LockedOOD_Predictor"
A4TV="POSTV16_AV3_A4_R2_TrainValidation_13Channel_Transport_Dataset.npz"
A4MAN="POSTV16_AV3_A4_R2_Artifact_Manifest.csv"
A2D=BASE/"POSTV16_AV3_A2_Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling"
A2MAN="POSTV16_AV3_A2_Artifact_Manifest.csv"
CKREL=BASE/"POSTV16_AV3_A5_PIRNN_Training_Checkpoint_and_OneTouch_OOD"/"POSTV16_AV3_A5_Best_Validation_Model.keras"
OUTD=BASE/"POSTV16_AV3_A6_Deployment_Integration_Contract_Freeze"
BLOCKD=BASE/"POSTV16_AV3_A6_BLOCKED"

REAL=[
("AV3CR0001",0,"AV2PHI0001","TRAIN","A6_CHECKPOINT_INFERENCE_FROM_FROZEN_A4R2_X13"),
("AV3CR0002",1,"AV2PHI0002","TRAIN","A6_CHECKPOINT_INFERENCE_FROM_FROZEN_A4R2_X13"),
("AV3CR0003",2,"AV2PHI0003","VALIDATION","A6_CHECKPOINT_INFERENCE_FROM_FROZEN_A4R2_X13"),
("AV3CR0004",3,"AV2PHI0004","LOCKED_OOD_TEST","FROZEN_A5R2_Y_PRED_ONLY_NO_REINFERENCE"),
]
DAYS=[30.,60.,100.,150.,250.,365.,500.,750.,1000.]
GRID=(15,50,50); NSL=1078; NN=201; NCV=200
DX=6.096; DY=6.096; DZ=1.2192
BULK=DX*DY*DZ

class GateError(RuntimeError): pass

def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def git(root,*a):
    return subprocess.run(["git","-C",str(root),*a],check=True,text=True,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.strip()

def blob(p,root): return git(root,"hash-object",str(p))
def lj(p): return json.loads(Path(p).read_text(encoding="utf-8"))

def rcsv(p):
    with open(p,newline="",encoding="utf-8") as f: return list(csv.DictReader(f))

def man(d,n):
    m={r["file"]:r["sha256"] for r in rcsv(d/n)}
    if not m: raise GateError("manifest_empty:"+n)
    for fn,e in m.items():
        p=d/fn
        if not p.is_file() or sha(p)!=e: raise GateError("manifest_mismatch:"+fn)
    return m

def jb(x): return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()

def cb(rows):
    rows=list(rows)
    if not rows: return b""
    ks=[]
    for r in rows:
        for k in r:
            if k not in ks: ks.append(k)
    s=io.StringIO(); w=csv.DictWriter(s,fieldnames=ks,lineterminator="\n")
    w.writeheader(); w.writerows(rows); return s.getvalue().encode()

def pub(d,files):
    d.mkdir(parents=True,exist_ok=True)
    for n,b in files.items():
        p=d/n
        if p.exists() and p.read_bytes()!=b: raise GateError("existing_output_differs:"+n)
        if not p.exists(): p.write_bytes(b)

def self_test():
    assert len(REAL)==4 and len(DAYS)==9
    assert GRID==(15,50,50) and NSL==1078 and NN==201 and NCV==200
    assert REAL[-1][-1]=="FROZEN_A5R2_Y_PRED_ONLY_NO_REINFERENCE"
    print("POSTV16-AV3-A6 deployment/integration contract-freeze self-test: PASS")

def main(root,drive):
    gates={}; stage="preflight"
    out=drive/OUTD
    def g(n,v,val=None):
        ok=bool(v); gates[n]={"passed":ok,"value":val}
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f" — {val}" if val is not None else ""))
        if not ok: raise GateError(n)

    print("="*210)
    print("POSTV16-AV3-A6 — FROZEN CHECKPOINT / LOCAL-PV / R7D TERMINAL-HALO DEPLOYMENT CONTRACT FREEZE")
    print("="*210)
    print("DESIGN/FREEZE ONLY. NO INFERENCE. NO MAPBACK. NO LP. NO EOS INVERSION.")
    print("NO OOD Y ACCESS/METRIC RECOMPUTE/REINFERENCE. NO PRESSURE SOLVE/POLLOCK RETRACE. NO CMG.")
    try:
        root=root.resolve(); drive=drive.resolve()
        stage="repository_authority"
        g("repository_parent_is_A5R2_commit",git(root,"rev-parse","HEAD^")==PARENT,git(root,"rev-parse","HEAD^"))
        g("repository_clean",git(root,"status","--porcelain")=="")
        for fn,e in SOURCES.items():
            a=blob(root/fn,root) if (root/fn).is_file() else "missing"
            g(Path(fn).stem+"_blob_exact",a==e,a)

        stage="A5R2_binding"
        a5=drive/A5R2D; m5=man(a5,A5R2MAN)
        g("A5R2_manifest_exact_8",len(m5)==8,len(m5))
        s5=lj(a5/A5R2SUM); d5=lj(a5/A5R2DEC); a5a=lj(a5/A5R2AUTH)
        g("A5R2_status_exact",s5["status"]==A5R2STATUS,s5["status"])
        g("checkpoint_identity_exact",
          s5["frozen_checkpoint_sha256"]==CKSHA and int(s5["best_epoch"])==BEST_EPOCH
          and int(s5["epochs_completed"])==EPOCHS
          and abs(float(s5["best_validation_total_objective"])-BEST_VAL)<=1e-15)
        g("A5R2_one_touch_complete",
          int(a5a["OOD_teacher_generation_count"])==1 and int(a5a["OOD_evaluation_count"])==1)
        g("A5R2_second_OOD_forbidden",
          d5["second_OOD_generation_authorized"] is False and d5["second_OOD_evaluation_authorized"] is False)
        g("A5R2_A6_freeze_authorized",
          d5["AV3_A6_authorized"] is True and d5["next"]["milestone"]==MILESTONE
          and d5["next"]["authorized"] is True and d5["next"]["execution"] is False)
        ck=drive/CKREL
        g("checkpoint_SHA_exact",ck.is_file() and sha(ck)==CKSHA,sha(ck) if ck.is_file() else "missing")

        stage="predictor_authorities"
        a4=drive/A4R2D; m4=man(a4,A4MAN); tv=a4/A4TV
        g("A4R2_trainval_manifested",A4TV in m4 and sha(tv)==m4[A4TV])
        with np.load(tv,allow_pickle=False) as z:
            g("A4R2_X13_shape_exact",np.asarray(z["X_required_13"]).shape==(29106,201,13),
              np.asarray(z["X_required_13"]).shape)
            ri=np.asarray(z["realization_index"],int); pc=np.asarray(z["partition_code"],int)
            g("nonOOD_registry_exact",set(np.unique(ri).tolist())=={0,1,2})
            g("train_val_counts_exact",int(np.sum(pc==0))==19404 and int(np.sum(pc==1))==9702)
        ood=a5/A5R2OOD
        g("A5R2_OOD_result_manifested",A5R2OOD in m5 and sha(ood)==m5[A5R2OOD])
        with np.load(ood,allow_pickle=False) as z:
            g("OOD_prediction_shape_exact",np.asarray(z["Y_pred"]).shape==(9702,201),
              np.asarray(z["Y_pred"]).shape)
            g("OOD_prediction_checkpoint_exact",
              str(np.asarray(z["checkpoint_sha256"]).reshape(-1)[0])==CKSHA)

        stage="A2_realization_authority"
        a2=drive/A2D; m2=man(a2,A2MAN)
        for rid,idx,phi_rid,part,pred in REAL:
            n=f"POSTV16_AV3_A2_{rid}_Corey_Relperm_Field_and_Streamline_Sampling.npz"
            p=a2/n
            g(rid+"_A2_artifact_manifested",n in m2 and p.is_file() and sha(p)==m2[n])
            with np.load(p,allow_pickle=False) as z:
                req={"paired_porosity","streamline_xyz_m","pollock_tof_s","streamline_weight_m3_s",
                     "nw","no","krw_max","kro_max","corey_realization_id",
                     "paired_porosity_realization_id","partition"}
                g(rid+"_required_arrays",req.issubset(set(z.files)))
                g(rid+"_geometry_shapes",
                  np.asarray(z["paired_porosity"]).shape==GRID
                  and np.asarray(z["streamline_xyz_m"]).shape==(NSL,NN,3)
                  and np.asarray(z["pollock_tof_s"]).shape==(NSL,NN)
                  and np.asarray(z["streamline_weight_m3_s"]).shape==(NSL,))

        stage="contract_freeze"
        registry=[
            {"corey_realization_id":r,"corey_index":i,"paired_porosity_realization_id":p,
             "partition":q,"prediction_authority":a}
            for r,i,p,q,a in REAL
        ]
        prediction={
            "checkpoint_sha256":CKSHA,"best_epoch":BEST_EPOCH,"model_nodes":201,
            "input_channels":13,"model_parameters":53057,
            "AV3CR0001_0003":{
                "source":A4TV,"inference":"exact epoch-92 checkpoint, batch_size=64",
                "Y_transport_access":False
            },
            "AV3CR0004":{
                "source":A5R2OOD,"use_arrays":["Y_pred","realization_index","time_index",
                "streamline_index","target_time_days","checkpoint_sha256"],
                "Y_true_access":False,"metric_recompute":False,"model_reinference":False,
                "teacher_regeneration":False
            }
        }
        transfer={
            "sequence":[
                "201-node frozen PI-RNN saturation prediction",
                "B1 exact 201-to-200 component-mass bridge",
                "SG7D/E37A conservative subsegment deposition on S0",
                "R7D H1 = one non-recursive same-layer x/y face-neighbor ring around S0",
                "D1=S0 union H1 conservative reconciliation",
                "local paired-porosity PV capacity",
                "frozen R2 EOS local-PV inversion",
                "bounded grid saturation/component mass"
            ],
            "raw_deposition_support":"S0 only","H1_terminal_occupancy_only":True,
            "H1_transit":False,"S0_to_H1_entry_cost":5.0,"adaptive_halo":False,
            "local_PV":"paired_porosity * cell_bulk_volume","cell_bulk_volume_m3":BULK,
            "capacity":"local_PV * rho_g(Sw=0.80,pressure,pref) * 0.60",
            "global_rescale":False,"mass_clipping_or_discard":False,
            "saturation_bounds":[0.20,0.80],"outside_D1_saturation":0.20,
            "outside_D1_component_mass_kg":0.0
        }
        exec_gates={
            "realizations":4,"times_each":9,"integrated_states":36,
            "B1_projection_relative_closure_max":1e-12,
            "mass_relative_closure_max":1e-10,"EOS_localPV_mass_relative_closure_max":1e-10,
            "raw_outside_S0":"exact zero","local_PV":"finite positive",
            "capacity":"finite positive","grid_saturation":"finite in [0.20,0.80]",
            "outside_D1":"Sw=0.20 exact; component mass=0 exact"
        }
        forbidden=[
            "training","checkpoint reselection","normalization refit","hyperparameter retuning",
            "AV3CR0004 Y_true access","AV3CR0004 metric recomputation","AV3CR0004 reinference",
            "AV3CR0004 teacher regeneration","second OOD exposure","pressure re-solve",
            "Darcy-Q recomputation","Pollock retrace","TOF recomputation","constitutive reseeding",
            "direct saturation averaging for B1","adaptive/recursive/vertical/diagonal halo growth",
            "H1 transit","global mass rescale","mass clipping/discard","mapback retuning","CMG"
        ]
        handoff={
            "milestone":"POSTV16-AV3-A6-E",
            "name":"Frozen AV3 checkpoint / Local-PV / R7D terminal-halo integration execution",
            "authorized":True,"execution":True,
            "required":[
                "infer AV3CR0001/0002/0003 from frozen A4-R2 X13 with epoch-92 checkpoint",
                "reuse AV3CR0004 frozen A5-R2 Y_pred without Y_true access or reinference",
                "use paired AV3-A2 porosity/kinematics for each realization",
                "use exact B1 bridge, SG7D/E37A deposition, R7D terminal halo, and local-PV EOS inversion",
                "execute all 4 realizations at all 9 canonical times"
            ],
            "AV3_final_outcome_freeze_authorized":False
        }
        decision={
            "milestone":MILESTONE,"status":STATUS_PASS,"checkpoint_sha256":CKSHA,
            "all_four_realizations_frozen":True,"all_nine_times_frozen":True,
            "prediction_authority_split_frozen":True,"local_PV_semantics_frozen":True,
            "B1_bridge_frozen":True,"R7D_terminal_halo_frozen":True,
            "training":False,"inference":False,"mapback_execution":False,"LP_execution":False,
            "OOD_truth_or_metrics_reopened":False,"OOD_reinference":False,
            "pressure_resolve":False,"Pollock_retrace":False,"CMG_validation":False,
            "A6_execution_authorized":True,"AV3_final_outcome_freeze_authorized":False,
            "next":handoff
        }
        summary={
            "milestone":MILESTONE,"status":STATUS_PASS,"checkpoint_sha256":CKSHA,
            "best_epoch":BEST_EPOCH,"realizations_frozen":4,"times_each":9,
            "prospective_integrated_states":36,"OOD_prediction_authority":"FROZEN_A5R2_Y_PRED_ONLY",
            "training":False,"inference":False,"mapback_execution":False,
            "A6_execution_authorized":True,"AV3_final_outcome_freeze_authorized":False,
            "next":handoff
        }
        files={
            "PAD_Stream_POSTV16_AV3_A6_Summary.json":jb(summary),
            "POSTV16_AV3_A6_Realization_Registry.json":jb({"realizations":registry,"canonical_times_days":DAYS}),
            "POSTV16_AV3_A6_Prediction_Authority_Contract.json":jb(prediction),
            "POSTV16_AV3_A6_B1_R7D_Transfer_Integration_Contract.json":jb(transfer),
            "POSTV16_AV3_A6_Execution_Gates.json":jb(exec_gates),
            "POSTV16_AV3_A6_Forbidden_Adaptations.json":jb({"forbidden":forbidden}),
            "POSTV16_AV3_A6_A6E_Handoff_Contract.json":jb(handoff),
            "POSTV16_AV3_A6_Decision_Contract.json":jb(decision),
            "POSTV16_AV3_A6_Final_Gate_Matrix.csv":cb([{"gate":k,**v} for k,v in gates.items()])
        }
        pub(out,files)
        mr=[{"file":q.name,"sha256":sha(q),"bytes":q.stat().st_size}
            for q in sorted(out.iterdir()) if q.is_file() and q.name!="POSTV16_AV3_A6_Artifact_Manifest.csv"]
        pub(out,{"POSTV16_AV3_A6_Artifact_Manifest.csv":cb(mr)})
        print("\n"+"="*210)
        print("POSTV16-AV3-A6: DEPLOYMENT / INTEGRATION CONTRACT FREEZE PASS")
        print("="*210)
        print("Checkpoint:",CKSHA,"epoch",BEST_EPOCH)
        print("Prospective states: 4 x 9 = 36")
        print("CR0001/2/3: frozen checkpoint inference on A4-R2 X13")
        print("CR0004: frozen A5-R2 Y_pred only; no Y_true/metric reopen/reinference")
        print("Local-PV + B1 + R7D terminal halo: FROZEN")
        print("POSTV16-AV3-A6-E execution: AUTHORIZED")
        print("AV3 final outcome freeze: NOT YET AUTHORIZED")
        print("="*210)
        return 0

    except Exception as e:
        d=drive/BLOCKD; d.mkdir(parents=True,exist_ok=True)
        r={"milestone":MILESTONE,"status":STATUS_BLOCKED,"failed_stage":stage,
           "exception":repr(e),"gates":gates,"inference":False,"mapback_execution":False,
           "OOD_truth_or_metrics_reopened":False,"A6_execution_authorized":False}
        p=d/"POSTV16_AV3_A6_Blocked_Report.json"
        if not p.exists(): p.write_bytes(jb(r))
        print("POSTV16-AV3-A6: BLOCKED",stage,repr(e))
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

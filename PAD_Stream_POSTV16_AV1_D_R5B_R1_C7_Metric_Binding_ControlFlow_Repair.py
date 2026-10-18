#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, io, json, shutil, subprocess, sys, tempfile
from pathlib import Path
from typing import Any
import numpy as np

MILESTONE="POSTV16-AV1-D-R5B-R1"
STATUS_PASS="AV1DR5BR1_C7_METRIC_BINDING_CONTROLFLOW_REPAIRED_SINGLE_PRODUCER_BALANCED_TRAIN_VALIDATION_REPAIR_EXECUTED_SELECTED_CHECKPOINT_FROZEN_GEOLOGY0031_REMAINS_SEALED"
STATUS_BLOCKED="AV1DR5BR1_PRODUCER_BALANCED_REPAIR_EXECUTION_BLOCKED"
RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT="a06ca12eb64e324acfbf07d920faa061ec8ef2c4"

R5B_ORIG="PAD_Stream_POSTV16_AV1_D_R5B_Producer_Balanced_TrainValidation_Repair.py"
R5B_ORIG_BLOB="d02acc4c18caf46d299afdf7cf01c9b5500b3046"
R5A="PAD_Stream_POSTV16_AV1_D_R5A_Producer_Labels_and_Geology0031_Sealed_Authority.py"
R5A_BLOB="740c4862e934c2b05b2eaa63c4136110c01866e9"
R5="PAD_Stream_POSTV16_AV1_D_R5_Prospective_Producer_Resolved_Repair_and_Geology0031_Freeze.py"
R5_BLOB="c5d2f64f124153b4e352f302302e0558a31c5c58"
R3B="PAD_Stream_POSTV16_AV1_D_R3B_Frozen_TrainValidation_Outlet_Response_Repair_Execution.py"
R3B_BLOB="787fe69e6631a1d294c17e791ab82aa4ab963c10"
C25="PAD_Stream_V16C25_Differentiable_Pollock_Full_Physics_Residual_Boundary_Mask_and_Physics_Loss_Weight_Authority_Contract.py"
C25_BLOB="0a4740b95c2b5e5d15db3137414e663e1e9b6282"
C26="PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
C26_BLOB="62e19e6b502fb3ab101a2589251c26b5f9ad9031"
BLOBS={R5B_ORIG:R5B_ORIG_BLOB,R5A:R5A_BLOB,R5:R5_BLOB,R3B:R3B_BLOB,C25:C25_BLOB,C26:C26_BLOB}

BASE=Path("post_v16")/RID/"POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
R5D=BASE/"POSTV16_AV1_D_R5_Prospective_Producer_Resolved_Repair_and_Geology0031_Freeze"
R5AD=BASE/"POSTV16_AV1_D_R5A_Producer_Labels_and_Geology0031_Sealed_Authority"
R3BD=BASE/"POSTV16_AV1_D_R3B_Frozen_TrainValidation_Repair_Execution"
OUTD=BASE/"POSTV16_AV1_D_R5B_R1_Producer_Balanced_TrainValidation_Repair_Execution"
BLOCKD=BASE/"POSTV16_AV1_D_R5B_R1_BLOCKED"

R5_REPAIR="POSTV16_AV1_D_R5_Producer_Resolved_Repair_Protocol.json"
R5_ACCEPT="POSTV16_AV1_D_R5_Geology0031_Independent_Acceptance_Authority.json"
R5_MANIFEST="POSTV16_AV1_D_R5_Artifact_Manifest.csv"
R5A_SUMMARY="PAD_Stream_POSTV16_AV1_D_R5A_Summary.json"
R5A_AUTH="POSTV16_AV1_D_R5A_Sealed_Acceptance_Authority.json"
R5A_DEC="POSTV16_AV1_D_R5A_Decision_Contract.json"
R5A_MANIFEST="POSTV16_AV1_D_R5A_Artifact_Manifest.csv"
LABEL_FILE="POSTV16_AV1_D_R5A_Derived_V16_Producer_Labels.npz"
LABEL_SHA="d87ca79290852d8a4cf2c7707be28869930a918802476c26fd261136309e62a2"
TARGET_FILE="POSTV16_AV1_D_R5A_Geology0031_R500_B2000_SEALED_Stage4_Target.npz"
TARGET_SHA="cef2647c394909fb268b621a5e6074b49c3aa41a285c75082d7d976f48e62afc"
R5A_STATUS="AV1DR5A_DERIVED_V16_PRODUCER_LABELS_CERTIFIED_AND_GEOLOGY0031_SOURCE_AUTHENTIC_ACCEPTANCE_AUTHORITY_GENERATED_SHA_SEALED"

R3B_SUMMARY="PAD_Stream_POSTV16_AV1_D_R3B_Summary.json"
R3B_SEL="POSTV16_AV1_D_R3B_Selected_Checkpoint_Contract.json"
R3B_MANIFEST="POSTV16_AV1_D_R3B_Artifact_Manifest.csv"
R3B_WEIGHTS="POSTV16_AV1_D_R3B_SELECTED_FROZEN.weights.h5"
R3B_STATUS="AV1DR3B_THREE_CANDIDATE_TRAIN_VALIDATION_REPAIR_EXECUTED_SELECTED_CHECKPOINT_FROZEN_GEOLOGY0030_REMAINS_SEALED"
START_ID="R3B_RESPONSE"
START_SHA="8207f17f35c354a3396525ed3ba8de88c923f7b55351f7cc58a9000268a26364"

C18R_NAME="V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz"
C18R_SHA="1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"
C19_NAME="V16C19_Leakage_Safe_Split_Assignment.npz"
C19_SHA="399815504f5ba3a900c02f24e4f9496b3a93c2e472a5faea593507cf9174638a"
C4_NAME="V16C4_Model_Ready_Conditioning_Tensors.npz"
C4_SHA="98a0b65a221433877f3d6d6e8b65b3c4028925cf0dc5304d42421707a33d5b9c"
C7_NAME="V16C7_Pollock_TOF_Streamline_Metric_Contract.npz"
C7_SHA="5a47ef2a4154291b424e43d1b0e21e30baa0c805c846e9943f62f8b389289e6d"

NS,NL,NN,NCH=9702,1078,201,9
NTR,NVA,NTE=755,162,161
PRODS=["PROD_SW","PROD_SE","PROD_NW","PROD_NE"]
BATCH=64; MAXEP=300; PAT=30; MINDELTA=1e-6; LRPAT=10; MINLR=1e-6; LR=1e-3; SEED=16021
LPHYS=.01; LGLOBAL=1.; LPROD=1.

class GateError(RuntimeError): pass
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def git(root,*args):
    return subprocess.run(["git","-C",str(root),*args],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.strip()
def loadj(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def readcsv(p):
    with Path(p).open("r",newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def verify_manifest(d,n):
    m={r["file"]:r["sha256"] for r in readcsv(d/n)}
    for fn,e in m.items():
        p=d/fn
        if not p.is_file() or sha(p)!=e: raise GateError(f"manifest_SHA:{fn}")
    return m
def jbytes(x): return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()
def cbytes(rows):
    if not rows:return b""
    fs=[]
    for r in rows:
        for k in r:
            if k not in fs:fs.append(k)
    s=io.StringIO(newline="");w=csv.DictWriter(s,fieldnames=fs,lineterminator="\n");w.writeheader();w.writerows(rows);return s.getvalue().encode()
def publish(d,files):
    d.mkdir(parents=True,exist_ok=True)
    for n,b in files.items():
        p=d/n
        if p.exists() and p.read_bytes()!=b:raise GateError(f"existing_output_differs:{n}")
        if not p.exists():p.write_bytes(b)
def mod(path,name):
    s=importlib.util.spec_from_file_location(name,path)
    if s is None or s.loader is None:raise GateError(f"load_module:{path}")
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def findexact(roots,name,expected):
    hits=[]
    for r in roots:
        if not r.exists():continue
        for p in r.rglob(name):
            try:
                if p.is_file() and sha(p)==expected:hits.append(p.resolve())
            except OSError:pass
    if not hits:raise GateError(f"exact_authority_not_found:{name}:{expected}")
    return sorted(set(hits),key=lambda p:(len(str(p)),str(p)))[0]
def pairs(ids,sl,ti):
    allowed=set(map(int,ids));A=[];B=[]
    for g in np.unique(sl[ids]):
        q=ids[sl[ids]==g];q=q[np.argsort(ti[q])]
        for a,b in zip(q[:-1],q[1:]):
            if int(a) in allowed and int(b) in allowed:A.append(int(a));B.append(int(b))
    return np.asarray(A,np.int64),np.asarray(B,np.int64)
def beta_coeff(train,a,b,sl,labels,w):
    P=len(a);occ=np.bincount(np.r_[a,b],minlength=NS).astype(np.int64);beta=np.zeros(NS,float);qs={}
    tl=labels[sl[train]];tq=w[sl[train]]
    for p in PRODS:
        m=tl==p
        if not np.any(m):raise GateError(f"TRAIN_missing:{p}")
        qs[p]=float(np.sum(tq[m]));ids=train[m]
        beta[ids]=(P/2.)*w[sl[ids]]/(occ[ids]*qs[p])
    return beta,qs,occ

def self_test():
    sl=np.tile(np.arange(4),3);ti=np.repeat(np.arange(3),4);train=np.arange(12)
    labels=np.asarray(PRODS);w=np.asarray([1.,2.,3.,4.]);a,b=pairs(train,sl,ti);beta,qs,occ=beta_coeff(train,a,b,sl,labels,w)
    e2=np.linspace(.1,1.2,12)**2
    want=0.
    for p in PRODS:
        m=labels[sl[train]]==p;want+=.25*np.sum(w[sl[train[m]]]*e2[train[m]])/qs[p]
    got=.5*(np.mean(beta[a]*e2[a])+np.mean(beta[b]*e2[b]))
    if abs(want-got)>1e-14:raise RuntimeError((want,got))
    if set(np.unique(occ[train]))!={1,2}:raise RuntimeError("occ")
    print("POSTV16-AV1-D-R5B-R1 self-test: PASS")

def main(root,drive):
    import tensorflow as tf
    gates={};stage="preflight";root=root.resolve();drive=drive.resolve();out=drive/OUTD;blocked=drive/BLOCKD
    def gate(n,v,x=None):
        ok=bool(v);gates[n]={"passed":ok,"value":x};print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f" — {x}" if x is not None else ""))
        if not ok:raise GateError(n)
    print("="*170);print("POSTV16-AV1-D-R5B-R1 — C7 METRIC-BINDING CONTROL-FLOW REPAIR + SINGLE PRODUCER-BALANCED TRAIN/VALIDATION REPAIR");print("="*170)
    print("ONE CANDIDATE. R3B_RESPONSE START. C19 TRAIN GRADIENTS / VALIDATION SELECTION ONLY.")
    print("NO RETIRED TEST. NO GEOLOGY0030. GEOLOGY0031 TARGET HASH-ONLY. NO BREAKTHROUGH THRESHOLD.\n")
    try:
        out.mkdir(parents=True,exist_ok=True)
        head=git(root,"rev-parse","HEAD");parent=git(root,"rev-parse","HEAD^");stat=git(root,"status","--porcelain")
        gate("repository_parent_is_R5A_commit",parent==PARENT,parent);gate("repository_clean",stat=="",repr(stat))
        for fn,e in BLOBS.items():
            a=git(root,"hash-object",str(root/fn)) if (root/fn).is_file() else "missing";gate(f"{Path(fn).stem}_git_blob_exact",a==e,a)

        stage="contract_binding";r5=drive/R5D;r5a=drive/R5AD;r3b=drive/R3BD
        for n,d in [("R5",r5),("R5A",r5a),("R3B",r3b)]:gate(f"{n}_output_present",d.is_dir(),str(d))
        m5=verify_manifest(r5,R5_MANIFEST);m5a=verify_manifest(r5a,R5A_MANIFEST);m3=verify_manifest(r3b,R3B_MANIFEST)
        gate("R5_manifest_SHA_closure",True,len(m5));gate("R5A_manifest_SHA_closure",True,len(m5a));gate("R3B_manifest_SHA_closure",True,len(m3))

        repair=loadj(r5/R5_REPAIR);accept=loadj(r5/R5_ACCEPT);s5a=loadj(r5a/R5A_SUMMARY);a5a=loadj(r5a/R5A_AUTH);d5a=loadj(r5a/R5A_DEC)
        s3=loadj(r3b/R3B_SUMMARY);sel3=loadj(r3b/R3B_SEL)
        gate("R5A_status_exact",s5a["status"]==R5A_STATUS,s5a["status"])
        gate("R5A_training_false",d5a["repair_training_performed"] is False);gate("R5A_inference_false",d5a["model_inference_performed"] is False)
        gate("R5A_target_unopened",d5a["target_performance_opened"] is False);gate("R5A_geology0030_unused",d5a["geology0030_reused"] is False)
        gate("R5_single_candidate",repair["single_candidate_policy"]["candidate_count"]==1)
        gate("R5_lambda_phys",float(repair["base_objective"]["lambda_phys"])==LPHYS)
        gate("R5_lambda_global",float(repair["base_objective"]["lambda_global_response"])==LGLOBAL)
        gate("R5_lambda_producer",float(repair["new_repair_term"]["lambda_producer_balanced_response"])==LPROD)
        gate("R5_no_PROD_SW_weighting",repair["new_repair_term"]["PROD_SW_specific_weighting"] is False)
        gate("R5_no_threshold",repair["single_candidate_policy"]["no_threshold_in_training"] is True and repair["validation_checkpoint_selection"]["breakthrough_threshold_used"] is False)
        gate("R5_no_search",repair["single_candidate_policy"]["no_posthoc_lambda_search"] and repair["single_candidate_policy"]["no_architecture_search"] and repair["single_candidate_policy"]["no_feature_search"])
        gate("R5_no_test_selection",repair["validation_checkpoint_selection"]["retired_C19_TEST_used"] is False)
        gate("R5_no_geology0030_selection",repair["validation_checkpoint_selection"]["geology0030_used"] is False)
        gate("R5_freeze_before_0031_open",repair["post_selection"]["selected_checkpoint_frozen_before_geology0031_target_opening"] is True)
        gate("R5_acceptance_0031",accept["geology_id"]=="0031" and int(accept["seed"])==390051)
        gate("R5_target_forbidden_training",accept["generation_order"]["target_may_not_be_opened_for_training_or_selection"] is True)

        gate("R3B_status_exact",s3["status"]==R3B_STATUS,s3["status"]);gate("R3B_winner_exact",s3["winner_candidate_id"]==START_ID)
        gate("R3B_selected_SHA_exact",s3["selected_frozen_weights_sha256"]==START_SHA and sel3["winner"]["candidate_id"]==START_ID)
        gate("R3B_0030_unopened_for_selection",sel3["geology0030_opened_for_selection"] is False)
        start=r3b/R3B_WEIGHTS;gate("starting_weights_SHA_exact",start.is_file() and sha(start)==START_SHA,sha(start) if start.is_file() else "missing")

        lab=r5a/LABEL_FILE;targ=r5a/TARGET_FILE
        gate("label_manifest_SHA_exact",m5a.get(LABEL_FILE)==LABEL_SHA,m5a.get(LABEL_FILE));gate("label_file_SHA_exact",lab.is_file() and sha(lab)==LABEL_SHA)
        gate("target_manifest_SHA_exact",m5a.get(TARGET_FILE)==TARGET_SHA,m5a.get(TARGET_FILE));gate("target_SHA_verified_without_opening",targ.is_file() and sha(targ)==TARGET_SHA)
        gate("authority_target_SHA_exact",a5a["acceptance_authority"]["sealed_target_sha256"]==TARGET_SHA)
        gate("authority_target_performance_unopened",a5a["acceptance_authority"]["firewall"]["model_performance_computed"] is False)

        stage="training_authorities"
        c18=findexact([root,drive],C18R_NAME,C18R_SHA);c19=findexact([root,drive],C19_NAME,C19_SHA);c4=findexact([root,drive],C4_NAME,C4_SHA);c7=findexact([root,drive],C7_NAME,C7_SHA)
        for n,p,e in [("C18R",c18,C18R_SHA),("C19",c19,C19_SHA),("C4",c4,C4_SHA),("C7",c7,C7_SHA)]:gate(f"{n}_exact_SHA",sha(p)==e,str(p))
        c26=mod(root/C26,"r5b_c26")
        with np.load(c18,allow_pickle=False) as z:d={k:z[k].copy() for k in z.files}
        with np.load(c19,allow_pickle=False) as z:s={k:z[k].copy() for k in z.files}
        with np.load(c4,allow_pickle=False) as z:c4x={k:z[k].copy() for k in z.files}
        with np.load(c7,allow_pickle=False) as z:
            mk=next((k for k in ("metric_M_dtheta_dxD","metric_M","M_dtheta_dxD") if k in z.files),None)
            if mk is None:
                raise GateError("C7_metric_key")
            Mall=np.asarray(z[mk],np.float32)
        with np.load(lab,allow_pickle=False) as z:
            labels=np.asarray(z["producer_label"]).astype(str);rule=str(np.asarray(z["rule_id"]).item());hist=bool(np.asarray(z["historical_V15_producer_id_claim"]).item())
        X7=np.asarray(d["X_sequence_required"],np.float32);Y=np.asarray(d["Y_transport"],np.float32);th=np.asarray(d["target_time_hat"],np.float32)
        eta=np.asarray(d["target_eta_sequence"],np.float32);sl=np.asarray(d["streamline_index"],np.int64);ti=np.asarray(d["time_index"],np.int64);part=np.asarray(s["sample_partition_code"],np.int8)
        static=np.asarray(c4x["X_static_required"],np.float32);w=np.asarray(c4x["streamline_weight_m3_s"],float)
        gate("X7_shape",X7.shape==(NS,NN,7),X7.shape);gate("Y_shape",Y.shape==(NS,NN),Y.shape);gate("metric_shape",Mall.shape==(NL,NN),Mall.shape)
        gate("labels_shape",labels.shape==(NL,),labels.shape);gate("labels_four",set(labels)==set(PRODS),sorted(set(labels)));gate("label_rule_exact",rule=="POSTV16_DERIVED_V16_TERMINAL_XY_NEAREST_PRODUCER_COLUMN_V1");gate("historical_claim_false",hist is False)
        gate("weights_positive",w.shape==(NL,) and np.isfinite(w).all() and np.all(w>0))
        xr=np.asarray(d["X_static_required"],np.float32).reshape(9,NL,1);gate("C18R_C4_order_exact",np.array_equal(xr,np.broadcast_to(static[None,:,:],xr.shape)))
        T=np.broadcast_to(th[:,None,None],(NS,NN,1)).astype(np.float32);X=np.concatenate([X7,T,eta[:,:,None]],axis=2);gate("C26_X_shape",X.shape==(NS,NN,NCH),X.shape)
        train=np.flatnonzero(part==0);val=np.flatnonzero(part==1);test=np.flatnonzero(part==2);trs=np.unique(sl[train]);vas=np.unique(sl[val]);tes=np.unique(sl[test])
        gate("split_counts",len(trs)==NTR and len(vas)==NVA and len(tes)==NTE,(len(trs),len(vas),len(tes)))
        gate("split_disjoint",not(set(trs)&set(vas) or set(trs)&set(tes) or set(vas)&set(tes)))
        gate("four_producers_TRAIN",set(labels[trs])==set(PRODS),{p:int(np.sum(labels[trs]==p)) for p in PRODS})
        gate("four_producers_VALIDATION",set(labels[vas])==set(PRODS),{p:int(np.sum(labels[vas]==p)) for p in PRODS})
        a,b=pairs(train,sl,ti);va,vb=pairs(val,sl,ti);gate("pair_counts",len(a)==6040 and len(va)==1296,(len(a),len(va)))
        gate("test_not_in_pairs",not np.isin(np.r_[a,b,va,vb],test).any())
        meanw=float(np.mean(w[trs]));beta,qs,occ=beta_coeff(train,a,b,sl,labels,w);gate("pair_occurrence_1_2",set(np.unique(occ[train]))=={1,2})
        shares={}
        for p in PRODS:
            ids=train[labels[sl[train]]==p];shares[p]=float(np.sum(occ[ids]*beta[ids])/(2*len(a)));gate(f"equal_quarter_{p}",abs(shares[p]-.25)<=1e-12,shares[p])

        def valmetrics(model):
            pp=[]
            for st in range(0,len(val),BATCH):q=val[st:st+BATCH];pp.append(model(X[q],training=False).numpy().astype(float))
            P=np.concatenate(pp);TT=Y[val].astype(float);te=P[:,-1]-TT[:,-1]
            fwp=c26.fw(tf.convert_to_tensor(P[:,-1],tf.float32)).numpy().astype(float);fwt=c26.fw(tf.convert_to_tensor(TT[:,-1],tf.float32)).numpy().astype(float)
            e2=(fwp-fwt)**2;vl=labels[sl[val]];wv=w[sl[val]];per={}
            for p in PRODS:
                m=vl==p;per[p]=float(np.sqrt(np.sum(wv[m]*e2[m])/np.sum(wv[m])))
            vd=[];vp=[];vt=[]
            for st in range(0,len(va),BATCH):
                aa=va[st:st+BATCH];bb=vb[st:st+BATCH];Sa=model(X[aa],training=False);Sb=model(X[bb],training=False)
                ld=.5*(tf.reduce_mean((Sa-Y[aa])**2)+tf.reduce_mean((Sb-Y[bb])**2));ea=tf.reduce_mean(eta[aa],1);eb=tf.reduce_mean(eta[bb],1)
                lp=c26.phys_pair_loss(Sa,Sb,ea,eb,tf.gather(Mall,sl[aa]));vd.append(float(ld));vp.append(float(lp));vt.append(float(ld+LPHYS*lp))
            return {"worst":max(per.values()),"equal":float(np.mean(list(per.values()))),"global":float(np.sqrt(np.sum(wv*e2)/np.sum(wv))),
                    "terminal":float(np.sqrt(np.mean(te**2))),"profile":float(np.sqrt(np.mean((P-TT)**2))),
                    "base_data":float(np.mean(vd)),"base_phys":float(np.mean(vp)),"base_total":float(np.mean(vt)),"per_producer":per}
        def key(m):return tuple(float(m[k]) for k in ("worst","equal","global","terminal","profile","base_total"))

        stage="baseline";tf.keras.utils.set_random_seed(SEED);bm=c26.model();bm.load_weights(start);gate("model_params_52033",bm.count_params()==52033,bm.count_params());base=valmetrics(bm);del bm;tf.keras.backend.clear_session()
        stage="training";tf.keras.utils.set_random_seed(SEED);model=c26.model();model.load_weights(start);opt=tf.keras.optimizers.Adam(LR);rng=np.random.default_rng(SEED)
        best=None;bestep=None;bestm=None;es=np.inf;lrb=np.inf;wait=0;lrwait=0;histrows=[]
        with tempfile.TemporaryDirectory(prefix="R5B_") as td:
            temp=Path(td)/"best.weights.h5"
            for ep in range(1,MAXEP+1):
                order=rng.permutation(len(a));trp=[];trph=[];trg=[];trpb=[];trt=[]
                for st in range(0,len(order),BATCH):
                    z=order[st:st+BATCH];aa=a[z];bb=b[z]
                    with tf.GradientTape() as tape:
                        Sa=model(X[aa],training=True);Sb=model(X[bb],training=True)
                        lp=.5*(tf.reduce_mean((Sa-Y[aa])**2)+tf.reduce_mean((Sb-Y[bb])**2))
                        ea=tf.reduce_mean(eta[aa],1);eb=tf.reduce_mean(eta[bb],1);lphys=c26.phys_pair_loss(Sa,Sb,ea,eb,tf.gather(Mall,sl[aa]))
                        fpa=c26.fw(Sa[:,-1]);fta=c26.fw(Y[aa,-1]);fpb=c26.fw(Sb[:,-1]);ftb=c26.fw(Y[bb,-1])
                        wa=tf.convert_to_tensor(w[sl[aa]]/meanw,tf.float32);wb=tf.convert_to_tensor(w[sl[bb]]/meanw,tf.float32)
                        lg=.5*(tf.reduce_mean(wa*(fpa-fta)**2)+tf.reduce_mean(wb*(fpb-ftb)**2))
                        ba=tf.convert_to_tensor(beta[aa],tf.float32);bc=tf.convert_to_tensor(beta[bb],tf.float32)
                        lpb=.5*(tf.reduce_mean(ba*(fpa-fta)**2)+tf.reduce_mean(bc*(fpb-ftb)**2))
                        loss=lp+LPHYS*lphys+LGLOBAL*lg+LPROD*lpb
                    grads=tape.gradient(loss,model.trainable_variables);opt.apply_gradients(zip(grads,model.trainable_variables))
                    trp.append(float(lp));trph.append(float(lphys));trg.append(float(lg));trpb.append(float(lpb));trt.append(float(loss))
                vm=valmetrics(model);k=key(vm);primary=vm["worst"]
                if best is None or k<best:best=k;bestep=ep;bestm=json.loads(json.dumps(vm));model.save_weights(temp)
                if primary<lrb:lrb=primary;lrwait=0
                else:lrwait+=1
                if primary<es-MINDELTA:es=primary;wait=0
                else:wait+=1
                if lrwait>=LRPAT:opt.learning_rate.assign(max(float(opt.learning_rate.numpy())*.5,MINLR));lrwait=0
                row={"epoch":ep,"train_profile":np.mean(trp),"train_phys":np.mean(trph),"train_global_response":np.mean(trg),"train_producer_balanced_response":np.mean(trpb),"train_total":np.mean(trt),
                     "val_worst_producer_response_RMSE":vm["worst"],"val_equal_producer_mean_response_RMSE":vm["equal"],"val_global_response_RMSE":vm["global"],"val_terminal_RMSE":vm["terminal"],"val_profile_RMSE":vm["profile"],"val_base_total":vm["base_total"],
                     **{f"val_{p}_response_RMSE":vm["per_producer"][p] for p in PRODS},"learning_rate":float(opt.learning_rate.numpy()),"best_epoch_so_far":bestep}
                histrows.append(row);print(f"R5B epoch {ep:03d}: train={row['train_total']:.6e} val_worst={vm['worst']:.6e} val_equal={vm['equal']:.6e} val_global={vm['global']:.6e} lr={row['learning_rate']:.3e}")
                if wait>=PAT:print(f"R5B early stop epoch {ep}; best={bestep}");break
            if not temp.is_file() or best is None:raise GateError("no_best_checkpoint")
            chk=c26.model();chk.load_weights(temp);cm=valmetrics(chk);ck=key(cm);gate("best_recompute_match",np.allclose(ck,best,rtol=1e-7,atol=1e-10),ck)
            selected=out/"POSTV16_AV1_D_R5B_R1_SELECTED_FROZEN.weights.h5"
            if selected.exists() and sha(selected)!=sha(temp):raise GateError("selected_weights_conflict")
            if not selected.exists():shutil.copyfile(temp,selected)
        selected_sha=sha(selected);gate("selected_weights_new_SHA",len(selected_sha)==64 and selected_sha!=START_SHA,selected_sha)
        gate("retired_test_predictions_false",True);gate("geology0031_target_opened_false",True);gate("geology0031_inference_false",True);gate("geology0030_used_false",True);gate("threshold_used_false",True);gate("alternate_candidate_false",True)

        hp=out/"POSTV16_AV1_D_R5B_R1_Training_History.csv";hb=cbytes(histrows)
        if hp.exists() and hp.read_bytes()!=hb:raise GateError("history_conflict")
        if not hp.exists():hp.write_bytes(hb)
        audit=[]
        trcounts={p:int(np.sum(labels[trs]==p)) for p in PRODS};vacounts={p:int(np.sum(labels[vas]==p)) for p in PRODS}
        for p in PRODS:audit.append({"producer":p,"train_streamlines":trcounts[p],"validation_streamlines":vacounts[p],"train_sample_weight_sum":qs[p],"pair_estimator_mass_share":shares[p],"starting_validation_response_RMSE":base["per_producer"][p],"selected_validation_response_RMSE":cm["per_producer"][p]})
        selection={"milestone":MILESTONE,"status":STATUS_PASS,"candidate_id":"R5B_PRODUCER_BALANCED_RESPONSE","starting_checkpoint":START_ID,"starting_weights_sha256":START_SHA,
                   "selected_frozen_weights_sha256":selected_sha,"best_epoch":int(bestep),"epochs_completed":len(histrows),
                   "objective":{"lambda_phys":LPHYS,"lambda_global_response":LGLOBAL,"lambda_producer_balanced_response":LPROD,"equal_producer_mass_shares":shares,"pair_multiplicity_corrected":True},
                   "selection_rule":["worst-producer response RMSE","equal-producer mean response RMSE","global response RMSE","terminal saturation RMSE","full-profile RMSE","base total objective"],
                   "selected_validation_metrics":cm,"starting_validation_metrics_descriptive_only":base,
                   "retired_test_used":False,"geology0031_target_opened":False,"geology0031_model_inference":False,"geology0030_used":False,"breakthrough_threshold_used":False,"alternate_candidate_trained":False}
        summary={"milestone":MILESTONE,"status":STATUS_PASS,"repository_head":head,"repository_parent":parent,"candidate_count":1,"candidate_id":"R5B_PRODUCER_BALANCED_RESPONSE",
                 "starting_weights_sha256":START_SHA,"selected_frozen_weights_sha256":selected_sha,"selected_best_epoch":int(bestep),
                 "selected_validation_tuple":{"worst":ck[0],"equal":ck[1],"global":ck[2],"terminal":ck[3],"profile":ck[4],"base_total":ck[5]},
                 "producer_label_sha256":LABEL_SHA,"geology0031_target_sha256":TARGET_SHA,"retired_test_predicted_or_scored":False,"geology0031_target_opened":False,"geology0031_model_inference":False,
                 "geology0030_used":False,"breakthrough_threshold_used":False,"next":"POSTV16-AV1-D-R5C — build geology0031 C26 deployment conditioning while target remains sealed."}
        cert={"milestone":MILESTONE,"status":STATUS_PASS,"selected_weights_sha256":selected_sha,"producer_label_sha256":LABEL_SHA,"geology0031_target_sha256":TARGET_SHA,
              "training_partition":"C19 TRAIN only","selection_partition":"C19 VALIDATION only","retired_test_role":"NOT PREDICTED OR SCORED","geology0031_status":"SHA-SEALED AND UNOPENED","geology0030_status":"CONSUMED; NOT USED",
              "threshold_role":"NOT USED","next":summary["next"]}
        publish(out,{"PAD_Stream_POSTV16_AV1_D_R5B_R1_Summary.json":jbytes(summary),"POSTV16_AV1_D_R5B_R1_Selected_Checkpoint_Contract.json":jbytes(selection),
                     "POSTV16_AV1_D_R5B_R1_Certification.json":jbytes(cert),"POSTV16_AV1_D_R5B_R1_Producer_Balance_Audit.csv":cbytes(audit),
                     "POSTV16_AV1_D_R5B_R1_Final_Gate_Matrix.csv":cbytes([{"gate":k,**v} for k,v in gates.items()])})
        manifest=[]
        for p in sorted(out.rglob("*")):
            if p.is_file() and p.name!="POSTV16_AV1_D_R5B_R1_Artifact_Manifest.csv":manifest.append({"file":str(p.relative_to(out)),"sha256":sha(p),"bytes":p.stat().st_size})
        publish(out,{"POSTV16_AV1_D_R5B_R1_Artifact_Manifest.csv":cbytes(manifest)})

        print("\n"+"="*170);print("POSTV16-AV1-D-R5B-R1: PASS");print("="*170)
        print(f"Status{'':70}: {STATUS_PASS}");print(f"Selected best epoch{'':57}: {bestep}");print(f"Selected weights SHA256{'':53}: {selected_sha}")
        print(f"Validation worst-producer response RMSE{'':36}: {ck[0]:.12e}");print(f"Validation equal-producer mean response RMSE{'':30}: {ck[1]:.12e}")
        print(f"Validation global response RMSE{'':44}: {ck[2]:.12e}");print(f"Validation terminal saturation RMSE{'':37}: {ck[3]:.12e}");print(f"Validation full-profile RMSE{'':45}: {ck[4]:.12e}")
        for p in PRODS:print(f"  {p} response RMSE{'':53}: {cm['per_producer'][p]:.12e}")
        print(f"Retired C19 test predicted/scored{'':42}: False / False");print(f"Geology0031 target opened / inference{'':37}: False / False");print(f"Geology0030 used / threshold used{'':43}: False / False")
        print(f"NEXT{'':72}: R5C — geology0031 deployment conditioning authority");print("="*170);return 0
    except Exception as e:
        blocked.mkdir(parents=True,exist_ok=True)
        rep={"milestone":MILESTONE,"status":STATUS_BLOCKED,"failed_stage":stage,"exception":repr(e),"gates":gates,"retired_test_predictions":False,"geology0031_target_opened":False,"geology0031_model_inference":False,"geology0030_used":False,
             "next_action":"Audit only this R5B technical/training gate. Do not open geology0031 or alter the frozen R5 repair."}
        p=blocked/"POSTV16_AV1_D_R5B_R1_Blocked_Report.json";data=jbytes(rep)
        if p.exists() and p.read_bytes()!=data:p=blocked/f"POSTV16_AV1_D_R5B_R1_Blocked_Report_{hashlib.sha256(data).hexdigest()[:12]}.json"
        if not p.exists():p.write_bytes(data)
        print("\nPOSTV16-AV1-D-R5B-R1: BLOCKED\nStage:",stage,"\nException:",repr(e),"\nReport:",p);return 2

def args():
    p=argparse.ArgumentParser();p.add_argument("--project-root",type=Path,default=Path("."));p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"));p.add_argument("--self-test",action="store_true");return p.parse_args()
if __name__=="__main__":
    a=args()
    if a.self_test:self_test();raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))

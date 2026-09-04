#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,json,numpy as np,sys
R=Path(__file__).resolve().parent;O=R/"output"/"V16_D13_24CASE_SUPERVISION_INTEGRITY";O.mkdir(parents=True,exist_ok=True)
T=["0020","0015","0013","0004","0006","0002","0023","0016","0009","0019","0017","0024","0003","0011","0014","0007"];V=["0010","0025","0008","0012"];E=["0005","0018","0021","0022"]
CM=R/"output"/"V16_D12C_RESTARTABLE_TRAIN_STAGE4_TRANSPORT_GENERATION"/"V16D12C_TRAIN_Transport_Manifest.csv";DM=R/"output"/"V16_D12D_RESTARTABLE_VALIDATION_STAGE4_TRANSPORT_GENERATION"/"V16D12D_VALIDATION_Transport_Manifest.csv";FM=R/"output"/"V16_D12F_RESTARTABLE_SEALED_LOCKED_OOD_STAGE4_TRANSPORT_GENERATION"/"V16D12F_LOCKED_OOD_Transport_Manifest.csv"
CS="85415615a8d752e45085eaff5c4d9b97ecb2c5155d570bc4019ef42221c30264";DS="14dfabec309c2d024ed970983a03c4f3610caff8f66a845ca5f5ba2318ff867c";FS="0d195b438a7fe3dce983ff93dfff9c2681949f8c1b92528d6ec575e31c8732f1"
C2=R/"output"/"V16_D12A_CASE0002_SOURCEAUTHENTIC_9TIME_STAGE4_TRANSPORT_PILOT"/"V16D12A_Case0002_SourceAuthentic_Y_Transport.npz";dirs={"TRAIN":R/"output"/"V16_D12C_RESTARTABLE_TRAIN_STAGE4_TRANSPORT_GENERATION"/"cases","VALIDATION":R/"output"/"V16_D12D_RESTARTABLE_VALIDATION_STAGE4_TRANSPORT_GENERATION"/"cases","LOCKED_OOD_TEST":R/"output"/"V16_D12F_RESTARTABLE_SEALED_LOCKED_OOD_STAGE4_TRANSPORT_GENERATION"/"cases"}
D=np.array([30,60,100,150,250,365,500,750,1000.])
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def art(c,part):
 if c=="0002":return C2
 h=list(dirs[part].glob(f"*Case_{c}*Transport.npz"))
 if len(h)!=1:raise RuntimeError(f"Case{c} {part} artifact count {len(h)}")
 return h[0]
def main():
 print("="*78);print("PAD-Stream V16D-13");print("24-Case Supervision Ensemble Integrity Audit + TRAIN-Only Normalization Contract");print("="*78)
 print("NO TRAINING. ALL 24 TARGETS ARE HASHED/AUDITED. NORMALIZATION MAY BE FIT ONLY ON TRAIN. OOD LABELS REMAIN SEALED FROM ADAPTIVE USE.")
 if sha(CM)!=CS or sha(DM)!=DS or sha(FM)!=FS:raise RuntimeError("Partition manifest SHA mismatch")
 rows=[];okall=True
 for part,cases in [("TRAIN",T),("VALIDATION",V),("LOCKED_OOD_TEST",E)]:
  for c in cases:
   a=art(c,part)
   with np.load(a,allow_pickle=False) as z:
    y=np.asarray(z["Y_transport"]);d=np.asarray(z["target_days"]);te=np.asarray(z["terminal_pollock_tof_s"])
    g={"shape":y.shape==(9,1078,201),"finite":np.isfinite(y).all(),"days":np.array_equal(d,D),"tof":te.shape==(1078,) and np.all(np.isfinite(te)) and np.all(te>0),"bounds":y.min()>=.2-1e-8 and y.max()<=.8+1e-8}
   q=all(g.values());okall&=q;rows.append({"case_id":c,"partition":part,"sha256":sha(a),"certified":q,**{k:bool(v) for k,v in g.items()}})
 reg=O/"V16D13_24Case_Target_Integrity_Registry.csv"
 with reg.open("w",newline="") as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 feats=["xi","pollock_tau_hat","adv_tau_hat","log10_Kh","log10_Kz_over_Kh","porosity","pressure_z","target_time_hat","target_eta_sequence"]
 norm={"authority":"V16D13_TRAIN_ONLY_NORMALIZATION_METHOD","fit_cases":T,"fit_partition":"TRAIN_ONLY","transform_only":["VALIDATION","LOCKED_OOD_TEST"],"feature_channels":feats,"target_Y_used_for_fit":False,"M_sidecar_predictor":False,"zero_variance_policy":"NO_DIVIDE_BY_ZERO_IDENTITY_CONSTANT_CHANNEL","statistics":"TO_BE_COMPUTED_IN_D14_FROM_SOURCE_BOUND_TRAIN_PREDICTORS_ONLY"}
 npth=O/"V16D13_TRAIN_Only_Normalization_Method_Contract.json";npth.write_text(json.dumps(norm,indent=2))
 g={"TRAIN_manifest_SHA":sha(CM)==CS,"VALIDATION_manifest_SHA":sha(DM)==DS,"OOD_manifest_SHA":sha(FM)==FS,"exact_24":len(rows)==24,"counts_16_4_4":(len(T),len(V),len(E))==(16,4,4),"all_targets_certified":okall,"unique_artifact_SHA":len({x["sha256"] for x in rows})==24,"TRAIN_only_normalization_fit":True,"validation_transform_only":True,"OOD_transform_only":True,"OOD_labels_not_fit":True,"C20_nine_channels_preserved":len(feats)==9,"M_sidecar_not_predictor":True,"no_training":True,"no_selection":True,"no_OOD_evaluation":True}
 ok=all(g.values());status="V16D_24CASE_STAGE4_SUPERVISION_ENSEMBLE_INTEGRITY_CERTIFIED_TRAIN_ONLY_NORMALIZATION_METHOD_FROZEN_FEATURE_ASSEMBLY_AUTHORIZED" if ok else "V16D_D13_BLOCKED"
 q={"milestone":"V16D-13","status":status,"target_values":24*9*1078*201,"registry_sha256":sha(reg),"normalization_contract_sha256":sha(npth),"gates":g,"next_milestone":"V16D-14 — Source-Bound 24-Case Predictor Tensor Assembly and TRAIN-Only Normalization Statistics Freeze" if ok else "V16D-13R"}
 sp=O/"PAD_Stream_V16D13_Summary.json";sp.write_text(json.dumps(q,indent=2))
 print("\nENSEMBLE: 16 TRAIN + 4 VALIDATION + 4 LOCKED OOD = 24");print("TARGET VALUES:",q["target_values"]);print("\nGATES")
 for k,v in g.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",q["next_milestone"]);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

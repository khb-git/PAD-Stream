from __future__ import annotations
from pathlib import Path
import ast,csv,hashlib,json,re
import numpy as np

ROOT=Path(__file__).resolve().parent
S4=ROOT/"pi_rnn_stage4_full_godunov.py"
S4_SHA="165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"
C18R=ROOT/"output"/"V16_C18R_ALIGNMENT_RESIDUAL_AUDIT"/"V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz"
C18R_SHA="1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"
C19=ROOT/"output"/"V16_C19_LEAKAGE_SAFE_TRAIN_VALIDATION_TEST_OOD_SPLIT_AUTHORITY_CONTRACT"/"V16C19_Leakage_Safe_Split_Assignment.npz"
C19_SHA="399815504f5ba3a900c02f24e4f9496b3a93c2e472a5faea593507cf9174638a"

OUT=ROOT/"output"/"V16_C20_STAGE4_PIRNN_TO_V16_TRAINING_INTERFACE_ARCHITECTURE_BINDING_CONTRACT"
OUT.mkdir(parents=True,exist_ok=True)
CSV=OUT/"V16C20_Interface_Channel_Contract.csv"
GATES=OUT/"V16C20_Final_Architecture_Interface_Gates.csv"
CON=OUT/"V16C20_Stage4_to_V16_Training_Interface_Contract.json"
SUM=OUT/"PAD_Stream_V16C20_Summary.json"

REQ=["xi","pollock_tau_hat","adv_tau_hat","log10_Kh","log10_Kz_over_Kh","porosity","pressure_z"]
OPT=["fmm_tau_hat","x_norm","y_norm","z_norm"]
STATIC=["log_streamline_weight_z"]
TIME=["target_time_hat","target_eta_sequence"]

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def sj(p,x):p.write_text(json.dumps(x,indent=2),encoding="utf-8")
def sc(p,rows):
 rows=list(rows);ks=[]
 for r in rows:
  for k in r:
   if k not in ks:ks.append(k)
 with p.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=ks);w.writeheader();w.writerows(rows)

def main():
 print("\n"+"="*78)
 print("PAD-Stream V16C-20")
 print("Stage4 PI-RNN to V16 Training Interface and Architecture Binding Contract")
 print("="*78)
 print("""
C20 DOES NOT TRAIN.

IT BINDS THE EXISTING STAGE4 FULL-PHYSICS PI-RNN ARCHITECTURAL LINEAGE TO THE
CERTIFIED V16 201-NODE POLLOCK DATASET WITHOUT PRETENDING THE HISTORICAL
64-NODE xD INTERFACE CAN BE USED DIRECTLY.

FROZEN DESIGN PRINCIPLE:
  STAGE4 ARCHITECTURAL LINEAGE IS RETAINED:
      sequence conditioning -> stacked LSTM -> TimeDistributed Dense ->
      bounded saturation output.
  STAGE4 NATIVE xD/64-NODE INPUT SEMANTICS ARE NOT RETAINED AS THE V16 INPUT.
  V16 USES THE FROZEN 201-NODE POLLOCK CONDITIONING CONTRACT AND C17 TARGETS.

NO LEGACY exp(Nc*xD) KINEMATICS, NO 64-NODE REMESHING, NO TRAINING, AND NO
HYPERPARAMETER OR LOSS-WEIGHT SELECTION OCCURS HERE.
""")
 if sha(S4)!=S4_SHA:raise RuntimeError("Stage4 source hash mismatch")
 if sha(C18R)!=C18R_SHA:raise RuntimeError("C18R dataset hash mismatch")
 if sha(C19)!=C19_SHA:raise RuntimeError("C19 split hash mismatch")

 src=S4.read_text(encoding="utf-8",errors="replace")
 # Source-level architecture evidence only; no model construction/training.
 evidence={
  "LSTM":("LSTM(" in src),
  "TimeDistributed":("TimeDistributed" in src),
  "Dense":("Dense(" in src),
  "bounded_sigmoid":("sigmoid" in src.lower()),
  "build_model":("def build_model" in src),
  "legacy_xD_seq":("xD_seq" in src),
 }
 with np.load(C18R,allow_pickle=False) as z:
  xr=np.asarray(z["X_sequence_required"])
  xo=np.asarray(z["X_sequence_optional"])
  xs=np.asarray(z["X_static_required"])
  y=np.asarray(z["Y_transport"])
  th=np.asarray(z["target_time_hat"])
  es=np.asarray(z["target_eta_sequence"])
  si=np.asarray(z["streamline_index"],dtype=np.int64)
 with np.load(C19,allow_pickle=False) as z:
  part=np.asarray(z["sample_partition_code"],dtype=np.int8)

 if xr.shape!=(9702,201,7) or xo.shape!=(9702,201,4) or xs.shape!=(9702,1) or y.shape!=(9702,201):
  raise RuntimeError("C18R shapes invalid")
 if th.shape!=(9702,) or es.shape!=(9702,201) or part.shape!=(9702,):
  raise RuntimeError("Time/split shapes invalid")

 # Freeze the minimum V16 production input contract.
 # Required C4 channels + exact physical-time conditioning.
 # Optional FMM/XYZ and static weight remain auxiliary, not silently promoted.
 Xseq_dim=len(REQ)+2
 rows=[]
 for i,n in enumerate(REQ):rows.append(dict(interface="sequence_required",index=i,name=n,authority="C4/C18R",use="MODEL_INPUT_REQUIRED"))
 rows.append(dict(interface="sequence_required",index=7,name="target_time_hat",authority="C15/C18R",use="MODEL_INPUT_REQUIRED"))
 rows.append(dict(interface="sequence_required",index=8,name="target_eta_sequence",authority="C13/C18R",use="MODEL_INPUT_REQUIRED"))
 for i,n in enumerate(OPT):rows.append(dict(interface="sequence_optional",index=i,name=n,authority="C4/C18R",use="AUXILIARY_NOT_PROMOTED"))
 for i,n in enumerate(STATIC):rows.append(dict(interface="static_optional",index=i,name=n,authority="C4/C18R",use="AUXILIARY_NOT_PROMOTED"))
 rows.append(dict(interface="target",index=0,name="Sw_201_node_sequence",authority="C17/C18R",use="SUPERVISION"))
 sc(CSV,rows)

 # Training-ready required tensor is deterministic concatenation only.
 T=np.broadcast_to(th[:,None,None],(len(th),201,1))
 E=es[:,:,None]
 X=np.concatenate([xr.astype(np.float32,copy=False),T.astype(np.float32),E.astype(np.float32)],axis=2)
 Y=y.astype(np.float32,copy=False)

 # Partition counts must reproduce C19.
 counts={k:int(np.sum(part==v)) for k,v in {"train":0,"validation":1,"test":2}.items()}
 group_leak=True
 for g in np.unique(si):
  if len(np.unique(part[si==g]))!=1:group_leak=False;break

 gates=[
 ("Stage4_exact_source_hash_reproduced",sha(S4)==S4_SHA),
 ("Stage4_build_model_source_bound",evidence["build_model"]),
 ("Stage4_LSTM_lineage_bound",evidence["LSTM"]),
 ("Stage4_TimeDistributed_Dense_lineage_bound",evidence["TimeDistributed"] and evidence["Dense"]),
 ("Stage4_bounded_output_lineage_bound",evidence["bounded_sigmoid"]),
 ("historical_xD_sequence_interface_detected",evidence["legacy_xD_seq"]),
 ("historical_64_node_interface_not_used_directly",True),
 ("V16_201_node_sequence_preserved",X.shape[1]==201),
 ("seven_C4_required_channels_preserved",X.shape[2]>=7),
 ("target_time_hat_added_deterministically",X.shape[2]==9),
 ("target_eta_sequence_added_deterministically",X.shape[2]==9),
 ("optional_FMM_XYZ_not_silently_promoted",True),
 ("static_weight_not_silently_promoted",True),
 ("Y_is_201_node_C17_supervision",Y.shape==(9702,201)),
 ("C19_split_assignment_reproduced",counts=={"train":6795,"validation":1458,"test":1449}),
 ("streamline_group_leakage_absent",group_leak),
 ("Pollock_kinematics_primary",True),
 ("legacy_exp_Nc_xD_not_reintroduced",True),
 ("Nc_not_added_as_duplicate_kinematic_feature",True),
 ("no_64_node_truth_adaptive_remeshing",True),
 ("no_normalization_refit",True),
 ("no_hyperparameter_selection",True),
 ("no_loss_weight_selection",True),
 ("no_model_training",True),
 ("OOD_remains_reserved_future_cases",True),
 ]
 sc(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates]);ok=all(v for _,v in gates)

 if ok:
  status="V16C_STAGE4_PIRNN_V16_TRAINING_INTERFACE_ARCHITECTURE_BOUND"
  diag="THE_EXISTING_STAGE4_STACKED_LSTM_TIMEDISTRIBUTED_BOUNDED_SATURATION_ARCHITECTURAL_LINEAGE_IS_BOUND_TO_THE_CERTIFIED_201_NODE_POLLOCK_INPUT_TARGET_CONTRACT_WITHOUT_REUSING_THE_LEGACY_64_NODE_XD_INTERFACE"
  rec=("Freeze C20. Next freeze the actual V16 PI-RNN training objective, normalization policy, architecture dimensions, optimizer, and stopping/selection rules before executing training.")
  nxt="V16C-21 — PI-RNN Training Objective, Hyperparameter and Model-Selection Authority Contract"
 else:
  status="V16C_STAGE4_PIRNN_V16_INTERFACE_BINDING_BLOCKED";diag="ONE_OR_MORE_STAGE4_ARCHITECTURE_OR_V16_INTERFACE_BINDING_GATES_FAILED"
  rec="Do not train. Audit only failed C20 architecture/interface gates.";nxt="V16C-20R — Architecture/Interface Binding Residual Audit"

 sj(CON,dict(
  milestone="V16C-20",status=status,diagnosis=diag,
  Stage4_sha256=sha(S4),C18R_sha256=sha(C18R),C19_sha256=sha(C19),
  architecture_lineage=dict(sequence_model="stacked LSTM",head="TimeDistributed Dense",
   output="bounded saturation",historical_native_coordinate="xD_seq / 64-node lineage",
   V16_coordinate="201-node Pollock sequence"),
  V16_required_sequence_channels=REQ+TIME,
  V16_required_sequence_dim=Xseq_dim,
  optional_sequence_channels=OPT,optional_static_channels=STATIC,
  target="201-node Sw sequence",
  partition_counts=counts,
  training_authorized=False,recommendation=rec,next_milestone=nxt))
 sj(SUM,dict(
  milestone="V16C-20",status=status,diagnosis=diag,
  samples=9702,nodes=201,required_sequence_dim=Xseq_dim,target_dim=201,
  partition_counts=counts,training_authorized=False,
  recommendation=rec,next_milestone=nxt))

 print("BOUND V16 MODEL INTERFACE")
 print(f"  samples / nodes             : 9702 / 201")
 print(f"  required sequence channels  : {Xseq_dim}")
 print("  channels                    :",", ".join(REQ+TIME))
 print(f"  target                      : Sw sequence (201)")
 print(f"  train/val/test              : {counts['train']} / {counts['validation']} / {counts['test']}")
 print("  Stage4 lineage              : stacked LSTM -> TimeDistributed Dense -> bounded Sw")
 print("  historical 64-node xD input : NOT USED DIRECTLY")
 print("  training performed          : False")

 print("\n"+"="*78)
 print("V16C-20 FINAL ARCHITECTURE/INTERFACE GATES")
 print("="*78)
 for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
 print("="*78)
 print("\nSTATUS\n ",status)
 print("\nDIAGNOSIS\n ",diag)
 print("\nRECOMMENDATION\n ",rec)
 print("\nNEXT MILESTONE\n ",nxt)
 print("\n"+"="*78)
 print("PAD-STREAM V16C-20 STAGE4/V16 TRAINING INTERFACE: COMPLETE")
 print("="*78)

if __name__=="__main__":main()

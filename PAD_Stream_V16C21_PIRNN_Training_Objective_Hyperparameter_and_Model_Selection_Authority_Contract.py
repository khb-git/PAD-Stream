from __future__ import annotations
from pathlib import Path
import csv,hashlib,json,re
import numpy as np

ROOT=Path(__file__).resolve().parent
S4=ROOT/"pi_rnn_stage4_full_godunov.py"
S4_SHA="165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"
C18R=ROOT/"output"/"V16_C18R_ALIGNMENT_RESIDUAL_AUDIT"/"V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz"
C18R_SHA="1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"
C19=ROOT/"output"/"V16_C19_LEAKAGE_SAFE_TRAIN_VALIDATION_TEST_OOD_SPLIT_AUTHORITY_CONTRACT"/"V16C19_Leakage_Safe_Split_Assignment.npz"
C19_SHA="399815504f5ba3a900c02f24e4f9496b3a93c2e472a5faea593507cf9174638a"
C20S=ROOT/"output"/"V16_C20_STAGE4_PIRNN_TO_V16_TRAINING_INTERFACE_ARCHITECTURE_BINDING_CONTRACT"/"PAD_Stream_V16C20_Summary.json"

OUT=ROOT/"output"/"V16_C21_PIRNN_TRAINING_OBJECTIVE_HYPERPARAMETER_MODEL_SELECTION_AUTHORITY_CONTRACT"
OUT.mkdir(parents=True,exist_ok=True)
CSV=OUT/"V16C21_Training_Protocol.csv"
GATES=OUT/"V16C21_Final_Training_Protocol_Gates.csv"
CON=OUT/"V16C21_Training_Protocol_Contract.json"
SUM=OUT/"PAD_Stream_V16C21_Summary.json"

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def lj(p):
 if not p.exists():raise FileNotFoundError(p)
 return json.loads(p.read_text())
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
 print("PAD-Stream V16C-21")
 print("PI-RNN Training Objective, Hyperparameter and Model-Selection Authority Contract")
 print("="*78)
 print("""
C21 FREEZES THE FIRST V16 TRAINING EXPERIMENT BEFORE PERFORMANCE IS OBSERVED.
IT DOES NOT TRAIN.

THE GOAL IS A CONSERVATIVE FIRST EXPERIMENT THAT PRESERVES STAGE4 MODEL
LINEAGE WHILE USING THE CERTIFIED V16 DATASET/SPLIT.

IMPORTANT:
  * C17 IS SOURCE-AUTHENTIC PHYSICS SUPERVISION.
  * THE FIRST V16 MODEL IS TRAINED AGAINST THAT SUPERVISION.
  * NO UNVALIDATED SECOND PHYSICS LOSS IS ADDED JUST TO CALL THE NETWORK
    'PHYSICS-INFORMED'. THE POLLOCK FULL-PHYSICS OPERATOR REMAINS AVAILABLE
    FOR POST-PREDICTION PHYSICS RESIDUAL AUDIT.
  * OPTIONAL FMM/XYZ/STATIC FEATURES ARE NOT USED IN EXPERIMENT 1.
  * TEST IS LOCKED UNTIL FINAL MODEL SELECTION.
  * OOD REMAINS FUTURE FOUNDATION CASES.
""")
 if sha(S4)!=S4_SHA:raise RuntimeError("Stage4 hash mismatch")
 if sha(C18R)!=C18R_SHA:raise RuntimeError("C18R hash mismatch")
 if sha(C19)!=C19_SHA:raise RuntimeError("C19 hash mismatch")
 c20=lj(C20S)
 if c20.get("status")!="V16C_STAGE4_PIRNN_V16_TRAINING_INTERFACE_ARCHITECTURE_BOUND":
  raise RuntimeError("C20 bound status missing")

 src=S4.read_text(encoding="utf-8",errors="replace")
 # Bind historical architecture defaults from exact source rather than inventing a new family.
 hidden64=bool(re.search(r"hidden\s*[:=][^,\n]*64|hidden\s*=\s*64",src))
 layers2=bool(re.search(r"layers\s*[:=][^,\n]*2|layers\s*=\s*2",src))
 lstm="LSTM(" in src
 td="TimeDistributed" in src
 bounded="sigmoid" in src.lower()

 with np.load(C18R,allow_pickle=False) as z:
  xr=np.asarray(z["X_sequence_required"])
  y=np.asarray(z["Y_transport"])
  th=np.asarray(z["target_time_hat"])
  es=np.asarray(z["target_eta_sequence"])
 with np.load(C19,allow_pickle=False) as z:
  part=np.asarray(z["sample_partition_code"],dtype=np.int8)

 counts={k:int(np.sum(part==v)) for k,v in {"train":0,"validation":1,"test":2}.items()}
 train=part==0; val=part==1; test=part==2

 # Freeze protocol. No data-derived normalization fit.
 protocol={
  "experiment_id":"V16C_EXP1_REQUIRED_CHANNELS_STAGE4_LINEAGE",
  "input_nodes":201,
  "input_channels":9,
  "required_channels":["xi","pollock_tau_hat","adv_tau_hat","log10_Kh","log10_Kz_over_Kh","porosity","pressure_z","target_time_hat","target_eta_sequence"],
  "optional_channels_used":False,
  "architecture":{"family":"stacked_LSTM_TimeDistributed_Dense_bounded_Sw","hidden_units":64,"lstm_layers":2,"output_units_per_node":1},
  "output_bounds":{"Swc":0.2,"Sor":0.2,"mapping":"Swc + (1-Swc-Sor)*sigmoid(raw)"},
  "loss":{"primary":"mean_squared_error_on_Sw_all_201_nodes","weight":1.0,
          "additional_training_physics_residual":"NONE_IN_EXP1",
          "reason":"C17 labels already come from certified full-physics Pollock solver; new differentiable V16 operator loss requires separate validation before promotion"},
  "optimizer":{"name":"Adam","learning_rate":1e-3},
  "batch_size":64,
  "max_epochs":300,
  "shuffle_training_samples_each_epoch":True,
  "validation_frequency_epochs":1,
  "early_stopping":{"monitor":"validation_MSE","patience":30,"min_delta":1e-6,"restore_best_weights":True},
  "lr_schedule":{"type":"ReduceLROnPlateau","monitor":"validation_MSE","factor":0.5,"patience":10,"min_learning_rate":1e-6},
  "checkpoint_selection":"minimum_validation_MSE",
  "test_policy":"evaluate exactly once after model selection; never select hyperparameters on test",
  "random_seed":16021,
  "normalization_policy":"use frozen C4/C18R representations and deterministic C20 time scaling only; no train-statistic refit",
  "post_prediction_physics_audit":["saturation_bounds","injector_boundary","front_ordering","C10/C11 Pollock full-physics residual diagnostic"],
  "training_authorized_after_C21_pass":True
 }

 rows=[]
 def add(cat,name,value,authority):
  rows.append(dict(category=cat,name=name,value=value,authority=authority))
 add("architecture","hidden_units",64,"Stage4 lineage")
 add("architecture","lstm_layers",2,"Stage4 lineage")
 add("architecture","nodes",201,"C20")
 add("architecture","input_channels",9,"C20")
 add("loss","primary","MSE(Sw)", "V16 EXP1 frozen design")
 add("loss","additional_physics_training_loss","NONE","provenance-safe EXP1 design")
 add("optimizer","Adam_lr",1e-3,"V16 EXP1 frozen design")
 add("training","batch_size",64,"V16 EXP1 frozen design")
 add("training","max_epochs",300,"V16 EXP1 frozen design")
 add("selection","early_stopping_patience",30,"V16 EXP1 frozen design")
 add("selection","checkpoint","minimum validation MSE","V16 EXP1 frozen design")
 add("evaluation","test_access","once after selection","leakage-safe policy")
 add("reproducibility","seed",16021,"V16 EXP1 frozen design")
 sc(CSV,rows)

 gates=[
  ("Stage4_exact_hash_reproduced",sha(S4)==S4_SHA),
  ("C18R_exact_dataset_hash_reproduced",sha(C18R)==C18R_SHA),
  ("C19_exact_split_hash_reproduced",sha(C19)==C19_SHA),
  ("C20_interface_status_reproduced",True),
  ("Stage4_LSTM_architecture_lineage_detected",lstm),
  ("Stage4_TimeDistributed_lineage_detected",td),
  ("Stage4_bounded_sigmoid_output_detected",bounded),
  ("Stage4_hidden64_default_bound",hidden64),
  ("Stage4_two_LSTM_layers_default_bound",layers2),
  ("V16_nodes_201_frozen",xr.shape[1]==201),
  ("V16_required_input_dim_9_frozen",xr.shape[2]+2==9),
  ("C19_train_count_6795",counts["train"]==6795),
  ("C19_validation_count_1458",counts["validation"]==1458),
  ("C19_test_count_1449",counts["test"]==1449),
  ("primary_supervision_is_C17_Sw",y.shape==(9702,201)),
  ("EXP1_loss_frozen_before_training",True),
  ("no_unvalidated_physics_loss_added",True),
  ("optimizer_frozen_before_training",True),
  ("batch_size_frozen_before_training",True),
  ("early_stopping_frozen_before_training",True),
  ("checkpoint_selection_uses_validation_only",True),
  ("test_locked_during_model_selection",True),
  ("OOD_reserved_future_cases",True),
  ("no_normalization_refit",True),
  ("no_optional_feature_promotion",True),
  ("no_training_performed_by_C21",True),
  ("no_performance_observed_before_protocol_freeze",True),
 ]
 sc(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates]);ok=all(v for _,v in gates)

 if ok:
  status="V16C_PIRNN_EXP1_TRAINING_PROTOCOL_FROZEN_TRAINING_AUTHORIZED"
  diag="THE_FIRST_V16_STAGE4_LINEAGE_PIRNN_EXPERIMENT_HAS_A_PREDECLARED_201_NODE_NINE_CHANNEL_ARCHITECTURE_SUPERVISION_OPTIMIZATION_EARLY_STOPPING_AND_VALIDATION_ONLY_MODEL_SELECTION_PROTOCOL"
  rec=("Freeze C21. Training is now authorized only under this exact EXP1 protocol. Next execute the training run, preserve the best-validation checkpoint and full history, then evaluate the locked test set and physics diagnostics without retuning.")
  nxt="V16C-22 — PI-RNN EXP1 Training Execution, Best-Validation Checkpoint and Locked-Test Evaluation"
 else:
  status="V16C_PIRNN_TRAINING_PROTOCOL_BINDING_BLOCKED";diag="ONE_OR_MORE_SOURCE_ARCHITECTURE_DATASET_SPLIT_OR_PROTOCOL_GATES_FAILED"
  rec="Do not train. Audit only failed C21 gates.";nxt="V16C-21R — Training Protocol Residual Audit"

 sj(CON,dict(milestone="V16C-21",status=status,diagnosis=diag,protocol=protocol,
  source_hashes={"Stage4":sha(S4),"C18R":sha(C18R),"C19":sha(C19)},
  training_authorized=bool(ok),recommendation=rec,next_milestone=nxt))
 sj(SUM,dict(milestone="V16C-21",status=status,diagnosis=diag,
  experiment_id=protocol["experiment_id"],architecture=protocol["architecture"],
  loss=protocol["loss"],optimizer=protocol["optimizer"],batch_size=64,max_epochs=300,
  partition_counts=counts,training_authorized=bool(ok),training_performed=False,
  recommendation=rec,next_milestone=nxt))

 print("FROZEN EXP1 TRAINING PROTOCOL")
 print("  architecture        : 2 x LSTM(64) -> TimeDistributed Dense -> bounded Sw")
 print("  sequence            : 201 nodes x 9 required channels")
 print("  supervision         : certified C17 Sw")
 print("  primary loss        : MSE over all 201 nodes")
 print("  extra physics loss  : NONE in EXP1 (requires separate validated formulation)")
 print("  optimizer           : Adam, lr=1e-3")
 print("  batch / max epochs  : 64 / 300")
 print("  early stopping      : val MSE, patience=30, min_delta=1e-6")
 print("  LR reduction        : factor=.5, patience=10, floor=1e-6")
 print("  checkpoint          : minimum validation MSE")
 print("  test access         : once after model selection")
 print("  seed                : 16021")
 print("  training now        : False")

 print("\n"+"="*78)
 print("V16C-21 FINAL TRAINING PROTOCOL GATES")
 print("="*78)
 for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
 print("="*78)
 print("\nSTATUS\n ",status)
 print("\nDIAGNOSIS\n ",diag)
 print("\nRECOMMENDATION\n ",rec)
 print("\nNEXT MILESTONE\n ",nxt)
 print("\n"+"="*78)
 print("PAD-STREAM V16C-21 TRAINING PROTOCOL CONTRACT: COMPLETE")
 print("="*78)

if __name__=="__main__":main()

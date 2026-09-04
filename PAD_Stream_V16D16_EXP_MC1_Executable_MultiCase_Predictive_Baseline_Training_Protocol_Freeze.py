#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
R=Path(__file__).resolve().parent
D15=R/"output"/"V16_D15R1_MULTIFOUNDATIONCASE_LEARNING_DATASET_FREEZE"
SUM=D15/"PAD_Stream_V16D15R1_Summary.json"
REG=D15/"V16D15R1_Frozen_MultiFoundationCase_Learning_Dataset_Registry.json"
AUTH=D15/"V16D15R1_EXP_MC1_Training_Protocol_Authority.json"
SUMSHA="a32ca6e51bfbd5596d592b0474467e2e852a5eabe6a651a4b4bb68dbe18bb7e2"
REGSHA="7e3e885a1219bf72f89dd759df7043fe2bd6e9a718d418edbe8db3e2afce6266"
AUTHSHA="b8987bfddefcdb890b99bbb0de9d8c7f6ad29c4332082c16c06a4beab0f3f65e"
O=R/"output"/"V16_D16_EXP_MC1_EXECUTABLE_TRAINING_PROTOCOL_FREEZE";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-16")
 print("EXP-MC1 Executable Multi-Case Predictive Baseline Training Protocol Freeze");print("="*78)
 print("""D16 FREEZES ALL REMAINING EXECUTABLE CHOICES BEFORE THE FIRST
MULTI-FOUNDATION-CASE TRAINING RUN. IT DOES NOT OPEN Y, TRAIN A MODEL,
SELECT A CHECKPOINT, OR TOUCH LOCKED OOD VALUES.
""")
 if sha(SUM)!=SUMSHA or sha(REG)!=REGSHA or sha(AUTH)!=AUTHSHA:raise RuntimeError("D15R1 authority SHA mismatch")
 d=json.loads(REG.read_text()); a=json.loads(AUTH.read_text())
 protocol={
 "name":"V16D_EXP_MC1_EXECUTABLE_PROTOCOL_1.0",
 "dataset_registry_sha256":REGSHA,
 "training_authority_sha256":AUTHSHA,
 "seed":161501,
 "model":{
   "input_shape":[201,9],
   "architecture":[
    {"layer":"LSTM","units":64,"return_sequences":True},
    {"layer":"LSTM","units":64,"return_sequences":True},
    {"layer":"TimeDistributed(Dense)","units":1,"activation":"sigmoid_affine_to_[0.2,0.8]"}
   ],
   "lineage":"C20 / Case0001 EXP1 predictive baseline",
   "output_shape":[201,1],
   "bounded_output":{"Sw_min":0.2,"Sw_max":0.8}
 },
 "objective":{"training_loss":"MSE","physics_loss":"NONE","metrics":["MSE","MAE"]},
 "optimizer":{"name":"Adam","learning_rate":1e-3},
 "sampling":{
   "sample_unit":"one (FoundationCase,target_time,streamline) sequence",
   "sequence_shape":[201,9],
   "target_shape":[201,1],
   "TRAIN_samples":16*9*1078,
   "VALIDATION_samples":4*9*1078,
   "case_weighting":"equal per sequence; every case has identical 9x1078 sample count",
   "shuffle":"TRAIN only, deterministic from seed each epoch",
   "batch_size":64
 },
 "loading":{
   "strategy":"streaming/memory-safe per-case NPZ loading through deterministic generator or tf.data",
   "do_not_materialize_all_24_cases_in_RAM":True,
   "TRAIN_cases_only_for_gradient_updates":True,
   "VALIDATION_cases_read_for_validation_only":True,
   "LOCKED_OOD_cases_not_opened_during_training":True
 },
 "epochs":{"max":300,"early_stopping":{"monitor":"val_loss","mode":"min","patience":25,"min_delta":0.0,"restore_best_weights":False}},
 "checkpoint":{"monitor":"val_loss","mode":"min","save_best_only":True,"format":"weights_only_HDF5_or_Keras_weights","selection_authority":"minimum raw validation MSE"},
 "postfit":{"reload_best_checkpoint_before_any_test":True,"validation_diagnostics_allowed":True,"locked_OOD_evaluation":"separate later milestone, once only"},
 "prohibited":["physics loss","OOD-informed tuning","OOD normalization","OOD checkpoint selection","architecture changes after training starts","retraining merely to repair serialization"],
 "failure_policy":{"serialization_failure":"repair/recover frozen best weights; do not retrain","OOM":"repair loading/batch execution without changing model/objective; if batch size must change, freeze a protocol revision before retry","interruption":"resume only from an explicitly persisted training-state/checkpoint contract; never silently restart and call it same run"},
 "scientific_scope":{"geology":"Recipe1.1 spectral GRF Cases0002-0025","controls":"fixed","generalization":"case-level geology OOD","foundation_model_claim":"NOT YET AUTHORIZED"}
 }
 pp=O/"V16D16_EXP_MC1_Executable_Training_Protocol_1.0.json";pp.write_text(json.dumps(protocol,indent=2))
 gates={"D15R1_summary_SHA_exact":sha(SUM)==SUMSHA,"dataset_registry_SHA_exact":sha(REG)==REGSHA,
 "training_authority_SHA_exact":sha(AUTH)==AUTHSHA,"architecture_frozen_2xLSTM64":True,"batch_size_frozen_64":True,
 "early_stopping_frozen":True,"checkpoint_rule_frozen":True,"MSE_only_no_physics_loss":True,
 "memory_safe_loading_frozen":True,"equal_sequence_weighting_frozen":True,"TRAIN_gradient_only":True,
 "validation_selection_only":True,"locked_OOD_not_opened":True,"serialization_no_retrain_policy_frozen":True,
 "no_Y_opened":True,"no_training":True,"no_model_selection":True,"no_OOD_evaluation":True}
 ok=all(gates.values())
 status="V16D_EXP_MC1_EXECUTABLE_TRAINING_PROTOCOL_1_0_FROZEN_FIRST_MULTICASE_TRAINING_RUN_AUTHORIZED" if ok else "V16D_D16_BLOCKED"
 nxt="V16D-17 — EXP-MC1 First Multi-Foundation-Case Predictive Baseline Training Run" if ok else "V16D-16R — Executable Protocol Repair"
 sp=O/"PAD_Stream_V16D16_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-16","status":status,"protocol_sha256":sha(pp),"gates":gates,"next_milestone":nxt},indent=2))
 print("TRAIN samples:",protocol["sampling"]["TRAIN_samples"]);print("VALIDATION samples:",protocol["sampling"]["VALIDATION_samples"])
 print("architecture: LSTM64 -> LSTM64 -> TD Dense bounded Sw");print("batch size: 64 | max epochs: 300 | patience: 25")
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

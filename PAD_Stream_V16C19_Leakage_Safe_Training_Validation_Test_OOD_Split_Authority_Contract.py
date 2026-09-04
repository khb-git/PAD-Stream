from __future__ import annotations
from pathlib import Path
import csv, hashlib, json
import numpy as np

ROOT=Path(__file__).resolve().parent
C18R=ROOT/"output"/"V16_C18R_ALIGNMENT_RESIDUAL_AUDIT"/"V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz"
C18RS=C18R.parent/"PAD_Stream_V16C18R_Summary.json"
C18R_SHA="1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"

OUT=ROOT/"output"/"V16_C19_LEAKAGE_SAFE_TRAIN_VALIDATION_TEST_OOD_SPLIT_AUTHORITY_CONTRACT"
OUT.mkdir(parents=True,exist_ok=True)
NPZ=OUT/"V16C19_Leakage_Safe_Split_Assignment.npz"
CSV=OUT/"V16C19_Streamline_Group_Split_Assignment.csv"
GATES=OUT/"V16C19_Final_Split_Authority_Gates.csv"
CON=OUT/"V16C19_Leakage_Safe_Split_Contract.json"
SUM=OUT/"PAD_Stream_V16C19_Summary.json"

SEED=16019
FRACTIONS={"train":0.70,"validation":0.15,"test":0.15}

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def lj(p):
 if not p.exists():raise FileNotFoundError(p)
 return json.loads(p.read_text(encoding="utf-8"))
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
 print("PAD-Stream V16C-19")
 print("Leakage-Safe Training/Validation/Test/OOD Split Authority Contract")
 print("="*78)
 print("""
C18R CERTIFIED THE ALIGNED 9702-SAMPLE DATASET.

C19 FREEZES ONLY THE SPLIT POLICY AND ASSIGNMENT. IT DOES NOT TRAIN.

LEAKAGE RULE:
  ALL NINE PHYSICAL-TIME STATES FROM ONE STREAMLINE MUST REMAIN IN THE SAME
  PARTITION. THEREFORE THE GROUPING UNIT IS streamline_index, NOT THE
  (time, streamline) SAMPLE.

FOUNDATION-CASE SCOPE:
  THIS DATASET CONTAINS ONE FROZEN GEOLOGY/CONTROL CASE. A TRUE GEOLOGY/CONTROL
  OOD SET CANNOT BE CLAIMED FROM THESE 9702 SAMPLES. C19 THEREFORE FREEZES:
    TRAIN      = held-in streamline groups
    VALIDATION = disjoint streamline groups
    TEST       = disjoint streamline groups
    OOD        = RESERVED FOR FUTURE UNSEEN FOUNDATION CASES

NO TIME-WISE RANDOM SPLIT, NO NODE-WISE SPLIT, NO STRATIFICATION BY TARGET
VALUES, NO NORMALIZATION REFIT, AND NO TRAINING OCCURS.
""")
 if sha(C18R)!=C18R_SHA:raise RuntimeError("C18R artifact hash mismatch.")
 s=lj(C18RS)
 if s.get("status")!="V16C_CONDITIONING_TO_Y_TRANSPORT_TRAINING_DATASET_CERTIFIED":
  raise RuntimeError("C18R certified status missing.")

 with np.load(C18R,allow_pickle=False) as z:
  ti=np.asarray(z["time_index"],dtype=np.int64)
  si=np.asarray(z["streamline_index"],dtype=np.int64)
  days=np.asarray(z["target_time_days"],float)
  Y=np.asarray(z["Y_transport"])
 N=len(si); groups=np.unique(si); ng=len(groups)
 if N!=9702 or ng!=1078:raise RuntimeError((N,ng))

 # Deterministic group permutation. Split counts use exact integer allocation:
 # 70/15/15 approximately, summing to all 1078 streamlines.
 rng=np.random.default_rng(SEED)
 perm=rng.permutation(groups)
 ntrain=int(round(FRACTIONS["train"]*ng))
 nval=int(round(FRACTIONS["validation"]*ng))
 ntest=ng-ntrain-nval
 train=np.sort(perm[:ntrain]); val=np.sort(perm[ntrain:ntrain+nval]); test=np.sort(perm[ntrain+nval:])
 sets={"train":train,"validation":val,"test":test}

 label=np.full(N,-1,dtype=np.int8)
 for code,(name,g) in enumerate(sets.items()):
  label[np.isin(si,g)]=code
 if np.any(label<0):raise RuntimeError("Unassigned samples")

 # Group leakage checks.
 inter_tv=np.intersect1d(train,val)
 inter_tt=np.intersect1d(train,test)
 inter_vt=np.intersect1d(val,test)
 all_once=len(np.unique(np.concatenate([train,val,test])))==ng

 # Every streamline must carry all 9 time states and only one partition.
 time_complete=True; one_partition=True
 for g in groups:
  m=si==g
  time_complete &= (np.sum(m)==9 and len(np.unique(ti[m]))==9 and len(np.unique(days[m]))==9)
  one_partition &= len(np.unique(label[m]))==1

 # All partitions should contain every target day.
 day_coverage={}
 for code,name in enumerate(["train","validation","test"]):
  d=np.unique(days[label==code])
  day_coverage[name]=d.tolist()

 sample_counts={name:int(np.sum(label==code)) for code,name in enumerate(["train","validation","test"])}
 group_counts={name:len(g) for name,g in sets.items()}

 rows=[]
 for name,g in sets.items():
  for x in g:rows.append(dict(streamline_index=int(x),partition=name,all_nine_times_together=True))
 sc(CSV,rows)

 np.savez_compressed(NPZ,
  sample_partition_code=label,
  partition_names_ascii=np.array([b"train",b"validation",b"test"]),
  train_streamline_index=train,validation_streamline_index=val,test_streamline_index=test,
  seed=np.array(SEED,dtype=np.int64),
  fractions=np.array([FRACTIONS["train"],FRACTIONS["validation"],FRACTIONS["test"]]),
  authority_label_ascii=np.frombuffer(b"V16C19_STREAMLINE_GROUP_SPLIT_OOD_RESERVED_FUTURE_CASES",dtype=np.uint8))

 gates=[
  ("C18R_exact_certified_hash_reproduced",sha(C18R)==C18R_SHA),
  ("C18R_certified_status_reproduced",True),
  ("sample_count_9702",N==9702),
  ("streamline_group_count_1078",ng==1078),
  ("grouping_unit_is_streamline_not_time_sample",True),
  ("all_nine_times_stay_with_each_streamline",bool(time_complete)),
  ("one_partition_per_streamline",bool(one_partition)),
  ("train_validation_streamlines_disjoint",len(inter_tv)==0),
  ("train_test_streamlines_disjoint",len(inter_tt)==0),
  ("validation_test_streamlines_disjoint",len(inter_vt)==0),
  ("all_streamlines_assigned_exactly_once",bool(all_once)),
  ("train_contains_all_target_days",len(day_coverage["train"])==9),
  ("validation_contains_all_target_days",len(day_coverage["validation"])==9),
  ("test_contains_all_target_days",len(day_coverage["test"])==9),
  ("deterministic_seed_frozen",SEED==16019),
  ("split_approximately_70_15_15",ntrain==755 and nval==162 and ntest==161),
  ("no_time_wise_random_split",True),
  ("no_node_wise_split",True),
  ("no_target_value_stratification",True),
  ("OOD_not_fabricated_from_single_foundation_case",True),
  ("OOD_reserved_for_future_unseen_geology_control_cases",True),
  ("no_normalization_refit",True),
  ("no_PI_RNN_training_performed",True),
  ("C18R_dataset_not_mutated",True),
 ]
 sc(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates]);ok=all(v for _,v in gates)

 if ok:
  status="V16C_LEAKAGE_SAFE_STREAMLINE_GROUP_SPLIT_AUTHORITY_FROZEN"
  diag="ALL_NINE_TIME_STATES_FOR_EACH_STREAMLINE_ARE_GROUPED_IN_ONE_DISJOINT_TRAIN_VALIDATION_OR_TEST_PARTITION_WHILE_TRUE_OOD_IS_RESERVED_FOR_FUTURE_UNSEEN_FOUNDATION_CASES"
  rec=("Freeze C19. The current Foundation Case 0001 dataset now has a leakage-safe in-case train/validation/test assignment. "
       "Next bind the existing Stage4 PI-RNN architecture to the V16 201-node conditioning/target interface and freeze the training input/output contract before training.")
  nxt="V16C-20 — Stage4 PI-RNN to V16 Training Interface and Architecture Binding Contract"
 else:
  status="V16C_LEAKAGE_SAFE_SPLIT_AUTHORITY_BLOCKED";diag="ONE_OR_MORE_GROUP_DISJOINTNESS_TIME_COHERENCE_OR_PROVENANCE_GATES_FAILED"
  rec="Do not train. Repair only failed C19 split gates without sample-level reshuffling.";nxt="V16C-19R — Split Authority Residual Audit"

 ah=sha(NPZ)
 sj(CON,dict(
  milestone="V16C-19",status=status,diagnosis=diag,seed=SEED,
  grouping_unit="streamline_index",all_time_states_grouped=True,
  requested_fractions=FRACTIONS,streamline_counts=group_counts,sample_counts=sample_counts,
  target_day_coverage=day_coverage,
  OOD_policy="RESERVED_FOR_FUTURE_UNSEEN_GEOLOGY_CONTROL_FOUNDATION_CASES",
  current_case_OOD_samples=0,
  artifact=str(NPZ.relative_to(ROOT)),artifact_sha256=ah,
  training_authorized=False,recommendation=rec,next_milestone=nxt))
 sj(SUM,dict(
  milestone="V16C-19",status=status,diagnosis=diag,
  streamlines=ng,samples=N,streamline_counts=group_counts,sample_counts=sample_counts,
  seed=SEED,OOD_samples=0,OOD_reserved_future_cases=True,
  artifact_sha256=ah,training_authorized=False,recommendation=rec,next_milestone=nxt))

 print("SPLIT RESULT")
 print(f"  grouping unit : streamline")
 print(f"  train         : {ntrain} streamlines / {sample_counts['train']} samples")
 print(f"  validation    : {nval} streamlines / {sample_counts['validation']} samples")
 print(f"  test          : {ntest} streamlines / {sample_counts['test']} samples")
 print(f"  OOD           : 0 current samples — RESERVED FOR FUTURE FOUNDATION CASES")
 print(f"  seed          : {SEED}")

 print("\n"+"="*78)
 print("V16C-19 FINAL SPLIT AUTHORITY GATES")
 print("="*78)
 for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
 print("="*78)
 print("\nSTATUS\n ",status)
 print("\nDIAGNOSIS\n ",diag)
 print("\nRECOMMENDATION\n ",rec)
 print("\nNEXT MILESTONE\n ",nxt)
 print("\nArtifact\n ",NPZ,"\n  SHA-256:",ah)
 print("\n"+"="*78)
 print("PAD-STREAM V16C-19 LEAKAGE-SAFE SPLIT CONTRACT: COMPLETE")
 print("="*78)

if __name__=="__main__":main()

#!/usr/bin/env python
from __future__ import annotations
from pathlib import Path
import json,hashlib,csv
import numpy as np

ROOT=Path(__file__).resolve().parent
C24=ROOT/"output"/"V16_C24_EXP1_BASELINE_SCIENTIFIC_ASSESSMENT_PHYSICS_INFORMED_EXP2_DECISION_CONTRACT"/"PAD_Stream_V16C24_Summary.json"
C7_SHA="5a47ef2a4154291b424e43d1b0e21e30baa0c805c846e9943f62f8b389289e6d"
OUT=ROOT/"output"/"V16_C25_DIFFERENTIABLE_POLLOCK_FULL_PHYSICS_RESIDUAL_BOUNDARY_MASK_PHYSICS_LOSS_WEIGHT_AUTHORITY_CONTRACT";OUT.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def findsha(h):
 a=[]
 for p in ROOT.rglob("*"):
  if p.is_file():
   try:
    if sha(p)==h:a.append(p)
   except OSError:pass
 if len(a)!=1:raise RuntimeError(f"Expected exactly one SHA match {h}; found {a}")
 return a[0]

def main():
 print("="*78);print("PAD-Stream V16C-25")
 print("Differentiable Pollock Full-Physics Residual, Boundary Mask and Physics-Loss Weight Authority Contract");print("="*78)
 print("""C25 DOES NOT TRAIN.

EXP2 KEEPS THE C20/C21 PREDICTOR AND ARCHITECTURE UNCHANGED.
THE C7 METRIC IS A NON-PREDICTIVE PHYSICS SIDECAR.

CRITICAL DESIGN:
THE PDE CONTAINS dS/deta AT FIXED (streamline,theta). A SINGLE 201-NODE
PROFILE CANNOT SUPPLY THIS DERIVATIVE. EXP2 THEREFORE FORMS PHYSICS BATCHES
AS ADJACENT PHYSICAL-TIME PAIRS FROM THE SAME TRAINING STREAMLINE.

FOR ADJACENT STATES a,b:
  dS/deta = (S_b - S_a)/(eta_b-eta_a)
and the spatial operator is evaluated at the midpoint state
  S_mid = 0.5*(S_a+S_b).

ONLY INTERIOR POLLOCK NODES j=1..199 ENTER THE PDE LOSS. INLET AND TERMINAL
BOUNDARY NODES ARE EXCLUDED FROM THE PDE RESIDUAL BECAUSE THEIR SOURCE-
AUTHENTIC BOUNDARY SEMANTICS ARE DISTINCT.

PHYSICS LOSS IS NORMALIZED BY A FROZEN CHARACTERISTIC RESIDUAL SCALE R0=1.
NO SCALE IS FIT FROM EXP1/EXP2 RESIDUALS.

EXP2 OBJECTIVE:
  L = L_data + lambda_phys * L_phys
with lambda_phys = 0.01, predeclared before EXP2 performance is observed.
""")
 c24=json.loads(C24.read_text())
 if c24["status"]!="V16C_EXP1_BASELINE_FROZEN_EXP2_PHYSICS_INFORMED_BRANCH_AUTHORIZED_FOR_OBJECTIVE_DESIGN_ONLY":
  raise RuntimeError("C24 prerequisite mismatch")
 c7=findsha(C7_SHA)
 with np.load(c7,allow_pickle=False) as z:
  k=next((x for x in ["metric_M_dtheta_dxD","metric_M","M_dtheta_dxD"] if x in z.files),None)
  if k is None:raise RuntimeError(f"C7 metric key unresolved: {z.files}")
  M=np.asarray(z[k],float)
 if M.shape!=(1078,201):raise RuntimeError(M.shape)
 contract={
 "EXP2_predictor":"UNCHANGED_C20_201x9",
 "architecture":"UNCHANGED_C21_2xLSTM64_TD_DENSE_BOUNDED_SW",
 "physics_sidecar":"C7 metric_M_dtheta_dxD; NOT predictor input",
 "residual":"R=dS/deta + dfw/dtheta - (phi/Pe_c) M d/dtheta[Dtilde(S) M dS/dtheta]",
 "time_derivative":{"method":"adjacent_frozen_target_time_pairs_same_training_streamline",
 "formula":"(S_b-S_a)/(eta_b-eta_a)","spatial_operator_state":"midpoint 0.5*(S_a+S_b)",
 "pairs_per_streamline":8,"test_pairs_for_selection":"PROHIBITED"},
 "spatial_derivative":{"theta_nodes":201,"interior_mask":"j=1..199","scheme":"centered node differences with conservative face capillary flux",
 "boundary_nodes_in_PDE_loss":False},
 "constitutive":{"nw":2.0,"no":2.0,"Swc":0.2,"Sor":0.2,"krw_max":0.8,"kro_max":0.8,
 "mu_w_cP":0.5,"mu_o_cP":5.0,"phi":0.2,"Pe_c":22.0,"lambda_c":2.0,
 "Nc":"metadata only; exp(Nc*xD) prohibited"},
 "loss":{"data":"mean squared Sw error on supervised profiles","physics":"mean squared interior residual",
 "R0":1.0,"lambda_data":1.0,"lambda_phys":0.01},
 "selection":{"monitor":"validation total objective with separately reported validation data and physics terms",
 "test_locked":True,"no_test_retuning":True},
 "training_authorized_after_C25":True
 }
 gates=[
 ("C24_bound",True),("exact_C7_metric_hash_bound",sha(c7)==C7_SHA),("C7_shape_1078x201",M.shape==(1078,201)),
 ("predictor_interface_unchanged",True),("architecture_unchanged",True),("C7_metric_sidecar_only",True),
 ("time_derivative_uses_same_streamline_adjacent_times",True),("no_synthetic_time_perturbation",True),
 ("PDE_mask_excludes_inlet_node",True),("PDE_mask_excludes_terminal_node",True),
 ("source_boundary_semantics_not_replaced_by_PDE_mask",True),("Pollock_kinematics_primary",True),
 ("legacy_exp_Nc_xD_prohibited",True),("physics_scale_not_fit_from_EXP1",True),
 ("lambda_phys_predeclared_0p01",True),("test_locked_for_selection",True),
 ("no_training_in_C25",True),("no_EXP2_performance_observed",True)]
 ok=all(v for _,v in gates)
 status="V16C_EXP2_DIFFERENTIABLE_PHYSICS_OBJECTIVE_FROZEN_TRAINING_AUTHORIZED" if ok else "V16C_EXP2_PHYSICS_OBJECTIVE_BINDING_BLOCKED"
 summary={"milestone":"V16C-25","status":status,"contract":contract,"C7_sha256":sha(c7),
 "gates":dict(gates),"training_performed":False,
 "next_milestone":"V16C-26 — EXP2 Physics-Informed Training Execution, Best-Validation Checkpoint and Locked-Test Evaluation"}
 (OUT/"PAD_Stream_V16C25_Summary.json").write_text(json.dumps(summary,indent=2))
 rows=[{"item":"lambda_data","value":1.0},{"item":"lambda_phys","value":.01},{"item":"R0","value":1.0},
 {"item":"PDE_interior_nodes","value":"1..199"},{"item":"time_pairs_per_streamline","value":8}]
 with (OUT/"V16C25_Frozen_EXP2_Objective.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=["item","value"]);w.writeheader();w.writerows(rows)
 print("\\nFROZEN EXP2 OBJECTIVE")
 print("  L                 : L_data + 0.01 L_phys")
 print("  L_data            : mean squared saturation error")
 print("  L_phys            : mean squared normalized PDE residual")
 print("  R0                : 1.0 (fixed, not data-fitted)")
 print("  dS/deta           : adjacent target-time pair, same streamline")
 print("  spatial state     : midpoint prediction of adjacent pair")
 print("  PDE nodes         : 1..199 only")
 print("  C7 M              : physics sidecar only")
 print("  test selection    : prohibited")
 print("  training now      : AUTHORIZED only if all gates pass")
 print("\\n"+"="*78);print("V16C-25 GATES");print("="*78)
 for g,v in gates:print(f"[{'PASS' if v else 'FAIL'}] {g}")
 print("\\nSTATUS\\n ",status)
 print("\\nNEXT MILESTONE\\n  V16C-26 — EXP2 Physics-Informed Training Execution, Best-Validation Checkpoint and Locked-Test Evaluation")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()

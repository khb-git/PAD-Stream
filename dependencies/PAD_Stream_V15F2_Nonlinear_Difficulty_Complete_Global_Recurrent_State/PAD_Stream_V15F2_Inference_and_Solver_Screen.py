#!/usr/bin/env python3
"""Inference interface for PAD-Stream Version 15F-2.

The returned budgets are initial allocations only. Exact nonlinear and pressure
residual checks must continue and must escalate any budget miss.
"""
from pathlib import Path
import numpy as np

def _sigmoid(x):
    return 1.0/(1.0+np.exp(-np.clip(x,-40.0,40.0)))

def load_bundle(path):
    with np.load(Path(path),allow_pickle=True) as z:
        return {k:z[k].copy() for k in z.files}

def predict(bundle, feature_raw, f1_control_preflight=False):
    x=np.asarray(feature_raw,np.float64)
    single=x.ndim==1
    if single:x=x[None,:]
    z=(x-bundle["feature_mean"])/bundle["feature_std"]
    nl=np.clip(z@bundle["nonlinear_coef"]+float(bundle["nonlinear_intercept"][0]),1.0,int(bundle["full_nonlinear_budget"][0]))
    fp=np.clip(z@bundle["pressure_coef"]+float(bundle["pressure_intercept"][0]),3.0,int(bundle["full_pressure_fp_budget"][0]))
    retry=_sigmoid(z@bundle["retry_coef"]+float(bundle["retry_intercept"][0]))
    dist=np.sqrt(np.mean(z*z,axis=1))
    difficulty=np.clip(.35*(nl-1)/4+.35*(fp-3)/21+.30*retry,0,1)
    control=np.broadcast_to(np.asarray(f1_control_preflight,bool),retry.shape)
    full=(retry>=float(bundle["retry_threshold"][0]))|(dist>float(bundle["state_distance_threshold"][0]))|control|(difficulty>=float(bundle["full_difficulty_threshold"][0]))
    nb=np.clip(np.ceil(nl+float(bundle["nonlinear_margin"][0])),int(bundle["minimum_nonlinear_budget"][0]),int(bundle["full_nonlinear_budget"][0])).astype(int)
    pb=np.clip(np.ceil(fp+float(bundle["pressure_margin"][0])),int(bundle["minimum_pressure_fp_budget"][0]),int(bundle["full_pressure_fp_budget"][0])).astype(int)
    nb[full]=int(bundle["full_nonlinear_budget"][0]);pb[full]=int(bundle["full_pressure_fp_budget"][0])
    tier=np.full(len(z),"light",dtype="<U8")
    standard=(~full)&((difficulty>=float(bundle["warning_difficulty_threshold"][0]))|(nb>=4)|(pb>=15))
    tier[standard]="standard";tier[full]="full"
    result={"predicted_nonlinear_iterations":nl,"predicted_pressure_fixed_point_iterations_total":fp,"retry_probability":retry,"difficulty_score":difficulty,"preflight_tier":tier,"initial_nonlinear_budget":nb,"initial_pressure_fixed_point_budget":pb,"exact_escalation_required_on_residual_miss":np.ones(len(z),bool)}
    if single:return {k:(v[0] if np.asarray(v).ndim else v) for k,v in result.items()}
    return result

if __name__=="__main__":
    root=Path(__file__).resolve().parent
    b=load_bundle(root/"PAD_Stream_V15F2_Nonlinear_Difficulty_Heads.npz")
    d=np.load(root/"PAD_Stream_V15F2_Nonlinear_Difficulty_Dataset.npz",allow_pickle=True)
    print(predict(b,d["features_raw"][0],False))

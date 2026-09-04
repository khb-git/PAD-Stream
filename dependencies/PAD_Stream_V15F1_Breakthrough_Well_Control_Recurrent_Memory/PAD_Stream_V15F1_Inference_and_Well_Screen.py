#!/usr/bin/env python3
"""Pure-NumPy well-memory heads for PAD-Stream Version 15F-1.

The caller supplies the current frozen 15F-0 hidden vector and the 11 current
well-memory features defined in PAD_Stream_V15F1_Feature_Target_Schema.json.
Exact Peaceman well equations remain mandatory after this warm-start proposal.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np


def load_bundle(path: Path):
    z=np.load(path,allow_pickle=False)
    return {k:z[k].copy() for k in z.files}


def _linear(x,coef,intercept):
    return float(np.dot(x,coef)+intercept)


def predict(bundle, f0_hidden, well_features, current_gas_cut,
            current_mode_mass_rate, current_bhp_mpa, current_mass_rate_kg_s,
            previous_monotone_hazard=0.0):
    raw=np.concatenate([np.asarray(f0_hidden,np.float64).reshape(-1),np.asarray(well_features,np.float64).reshape(-1)])
    x=(raw-bundle["feature_mean"])/bundle["feature_std"]
    distance=float(np.sqrt(np.mean(x*x)))
    raw_gas=float(current_gas_cut+_linear(x,bundle["gas_coef"],bundle["gas_intercept"][0]))
    raw_hazard=float(np.clip(_linear(x,bundle["hazard_coef"],bundle["hazard_intercept"][0]),0,1))
    logit=_linear(x,bundle["mode_coef"],bundle["mode_intercept"][0])
    probability=float(1/(1+np.exp(-np.clip(logit,-60,60))))
    gas_candidate=float(np.clip(raw_gas,current_gas_cut-bundle["gas_max_decrease"][0],current_gas_cut+bundle["gas_max_increase"][0]))
    gas_candidate=float(np.clip(gas_candidate,0,1))
    selected=bool(raw_hazard>=bundle["gas_select_hazard_threshold"][0] and current_gas_cut<bundle["gas_select_max_current_cut"][0] and distance<=bundle["state_distance_threshold"][0])
    screened_gas=gas_candidate if selected else float(current_gas_cut)
    monotone_hazard=float(max(previous_monotone_hazard,raw_hazard))
    raw_mode=int(probability>=0.5)
    confident=bool(probability<=bundle["mode_confidence_low"][0] or probability>=bundle["mode_confidence_high"][0])
    screened_mode=raw_mode if confident else int(current_mode_mass_rate)
    boundary=bool((not current_mode_mass_rate and current_mass_rate_kg_s>=bundle["mass_rate_boundary_kg_s"][0]) or (current_mode_mass_rate and current_bhp_mpa>=bundle["bhp_boundary_mpa"][0]))
    preflight=bool(boundary or not confident or screened_mode!=int(current_mode_mass_rate) or distance>bundle["state_distance_threshold"][0])
    warm_bhp=float(bundle["bhp_limit_mpa"][0] if screened_mode==0 else current_bhp_mpa)
    warm_rate=float(bundle["mass_rate_limit_kg_s"][0] if screened_mode==1 else current_mass_rate_kg_s)
    return {"raw_gas_cut":raw_gas,"screened_gas_cut":screened_gas,"gas_head_selected":selected,"raw_breakthrough_hazard":raw_hazard,"monotone_breakthrough_hazard":monotone_hazard,"breakthrough_warning":bool(monotone_hazard>=bundle["gas_select_hazard_threshold"][0]),"proposed_breakthrough":bool(monotone_hazard>=0.5),"mode_mass_rate_probability":probability,"screened_mode_mass_rate":screened_mode,"control_preflight":preflight,"warm_start_bhp_mpa":warm_bhp,"warm_start_mass_rate_kg_s":warm_rate,"state_distance":distance}

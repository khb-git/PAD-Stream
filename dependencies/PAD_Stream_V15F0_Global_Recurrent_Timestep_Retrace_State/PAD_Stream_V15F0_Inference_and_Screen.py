#!/usr/bin/env python3
"""Inference and confidence screen for PAD-Stream Version 15F-0."""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path
from typing import Mapping, Any
import numpy as np
import torch


def _load_module(path: Path):
    spec=importlib.util.spec_from_file_location("pad_stream_v15f0_trainer",path)
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module
    assert spec.loader is not None; spec.loader.exec_module(module); return module


def load_model(checkpoint_path: Path, trainer_path: Path):
    trainer=_load_module(Path(trainer_path))
    try: ckpt=torch.load(checkpoint_path,map_location="cpu",weights_only=False)
    except TypeError: ckpt=torch.load(checkpoint_path,map_location="cpu")
    model=trainer.model_from_config(ckpt["model_config"])
    model.load_state_dict(ckpt["model_state_dict"]); model.eval()
    return model,ckpt,trainer


def initial_hidden(checkpoint: Mapping[str,Any]):
    return np.zeros((1,1,int(checkpoint["model_config"]["hidden_dim"])),np.float32)


def step(model, checkpoint, dense_feature_raw, current_dt_days, hidden=None,
         snapshot_feature_raw=None):
    dm=np.asarray(checkpoint["normalization"]["dense_mean"],np.float64)
    ds=np.asarray(checkpoint["normalization"]["dense_std"],np.float64)
    x=((np.asarray(dense_feature_raw,np.float64)-dm)/ds).astype(np.float32)
    xt=torch.tensor(x.reshape(1,1,-1))
    ht=None if hidden is None else torch.tensor(np.asarray(hidden,np.float32))
    model.eval()
    with torch.no_grad():
        hs,hnew=model.encode(xt,ht); logdt,_=model.heads(hs)
    raw=float(np.exp(float(logdt[0,0])))
    dist=float(np.sqrt(np.mean(x.astype(np.float64)**2)))
    cal=checkpoint["calibration"]
    selected=dist<=float(cal["dense_state_distance_threshold"])
    alpha=float(cal["timestep_blend_alpha"])
    proposal=(1-alpha)*float(current_dt_days)+alpha*raw if selected else float(current_dt_days)
    cfg=checkpoint["training_config"]
    proposal=float(np.clip(proposal,max(float(cfg["minimum_dt_days"]),float(cfg["minimum_dt_factor"])*current_dt_days),min(float(cfg["maximum_dt_days"]),float(cfg["maximum_dt_factor"])*current_dt_days)))
    out={"raw_timestep_days":raw,"screened_timestep_days":proposal,"timestep_selected":bool(selected),"dense_state_distance":dist,"hidden":hnew.cpu().numpy()}
    if snapshot_feature_raw is not None:
        sm=np.asarray(checkpoint["normalization"]["snapshot_mean"],np.float64)
        ss=np.asarray(checkpoint["normalization"]["snapshot_std"],np.float64)
        s=((np.asarray(snapshot_feature_raw,np.float64)-sm)/ss).astype(np.float32)
        with torch.no_grad():
            pred=model.retrace_head(torch.cat([hs[:,0,:],torch.tensor(s.reshape(1,-1))],dim=1))[0].cpu().numpy()
        risk=float(np.max(pred)); sdist=float(np.sqrt(np.mean(s.astype(np.float64)**2)))
        upper=float(np.clip(risk+float(cal["retrace_conservative_margin"]),0,1))
        ood=sdist>float(cal["snapshot_state_distance_threshold"])
        full=bool(upper>=float(cal["retrace_risk_threshold"]) or ood)
        out.update({"predicted_retrace_fractions":pred,"predicted_combined_retrace_risk":risk,"upper_combined_retrace_risk":upper,"snapshot_state_distance":sdist,"snapshot_ood":bool(ood),"full_family_retrace":full,"cache_only_update":not full})
    return out

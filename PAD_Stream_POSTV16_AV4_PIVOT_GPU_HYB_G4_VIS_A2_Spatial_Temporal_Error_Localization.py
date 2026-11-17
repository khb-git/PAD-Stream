#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors

M="POSTV16-AV4-PIVOT-GPU-HYB-G4-VIS-A2"
PASS="POSTV16AV4PIVOTGPUHYBG4VISA2_SPATIAL_TEMPORAL_ERROR_LOCALIZATION_PASS_NO_PHYSICS_MUTATION"
BLOCK="POSTV16AV4PIVOTGPUHYBG4VISA2_TECHNICAL_OR_AUTHORITY_BLOCK_NO_PHYSICS_MUTATION"
BRANCH="postv16-av4-pivot"
PARENT="6650bffc652caa2ae3f225e1c7f9c3649ec7ec26"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

A8_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A8"
A8_REL=BASE/(A8_TOKEN+"_Day100_Production_Trajectory_Validation")
A8_SUMMARY=f"PAD_Stream_{A8_TOKEN}_Summary.json"
A8_MANIFEST=f"{A8_TOKEN}_Artifact_Manifest.csv"
A8_SNAPS=f"{A8_TOKEN}_Refresh_Snapshots.npz"
A8_STATUS="POSTV16AV4PIVOTGPUHYBG4A8_DAY100_PRODUCTION_TRAJECTORY_VALIDATION_COMPLETE"

VIS1_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_VIS_A1"
VIS1_REL=BASE/(VIS1_TOKEN+"_Day100_DecisionSupport_3D")
VIS1_SUMMARY=f"PAD_Stream_{VIS1_TOKEN}_Summary.json"
VIS1_MANIFEST=f"{VIS1_TOKEN}_Artifact_Manifest.csv"
VIS1_STATUS="POSTV16AV4PIVOTGPUHYBG4VISA1_DAY100_DECISION_SUPPORT_3D_VISUALIZATION_PASS_NO_PHYSICS_MUTATION"

GRID=(15,50,50)
NZ,NY,NX=GRID
DX_FT=20.0
DY_FT=20.0
DZ_FT=4.0
BACKGROUND=0.20
INJ_I=24
INJ_J=24
INJ_X=(INJ_I+0.5)*DX_FT
INJ_Y=(INJ_J+0.5)*DY_FT

RADIAL_EDGES=np.asarray([0,100,200,300,400,500,600,800],dtype=float)
RADIAL_LABELS=["0-100","100-200","200-300","300-400","400-500","500-600","600-800"]
REGIME_EDGES=np.asarray([0.0,0.25,0.35,0.45,0.55,0.65,1.01],dtype=float)
REGIME_LABELS=["<0.25","0.25-0.35","0.35-0.45","0.45-0.55","0.55-0.65",">=0.65"]
CORE_R_FT=150.0
MID_R_FT=300.0
VISIBLE_SG=0.25

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_VIS_A2"
OUT_REL=BASE/(OUT_TOKEN+"_Spatial_Temporal_Error_Localization")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
RADIAL=f"{OUT_TOKEN}_Day100_Radial_Error.csv"
LAYERS=f"{OUT_TOKEN}_Day100_Layer_Error.csv"
QUADS=f"{OUT_TOKEN}_Day100_Quadrant_Error.csv"
REGIMES=f"{OUT_TOKEN}_Day100_ExactSaturation_Regime_Error.csv"
TEMPORAL=f"{OUT_TOKEN}_Mixed_Temporal_Evolution.csv"
INDEX=f"{OUT_TOKEN}_Visualization_Index.csv"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError):
    pass

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):
            h.update(c)
    return h.hexdigest()

def gt(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def js(p:Path):
    return json.loads(p.read_text(encoding="utf-8"))

def csv_rows(p:Path):
    with p.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_csv(p:Path,rows:list[dict[str,Any]]):
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def verify_manifest(directory:Path,name:str)->dict[str,str]:
    p=directory/name
    if not p.is_file():
        raise GateError(f"manifest_missing:{p}")
    result={}
    for row in csv_rows(p):
        fp=directory/row["file"]
        if not fp.is_file():
            raise GateError(f"manifest_artifact_missing:{fp.name}")
        actual=sha(fp)
        if actual!=row["sha256"]:
            raise GateError(f"manifest_sha:{fp.name}:{actual}:{row['sha256']}")
        if fp.stat().st_size!=int(row["bytes"]):
            raise GateError(f"manifest_bytes:{fp.name}")
        result[fp.name]=actual
    if not result:
        raise GateError(f"manifest_empty:{p}")
    return result

def rel_l2(a:np.ndarray,b:np.ndarray)->float:
    den=float(np.linalg.norm(np.asarray(b,float).ravel()))
    return float(np.linalg.norm((np.asarray(a,float)-np.asarray(b,float)).ravel())/max(den,1e-30))

def subset_metrics(mixed:np.ndarray,exact:np.ndarray,mask:np.ndarray)->dict[str,float]:
    m=np.asarray(mixed,float)[mask]
    e=np.asarray(exact,float)[mask]
    if m.size==0:
        return {
            "cell_count":0,"bias":float("nan"),"MAE":float("nan"),"RMSE":float("nan"),
            "relative_L2":float("nan"),"Linf":float("nan"),
            "mixed_mean":float("nan"),"exact_mean":float("nan")
        }
    d=m-e
    return {
        "cell_count":int(m.size),
        "bias":float(np.mean(d)),
        "MAE":float(np.mean(np.abs(d))),
        "RMSE":float(np.sqrt(np.mean(d*d))),
        "relative_L2":rel_l2(m,e),
        "Linf":float(np.max(np.abs(d))),
        "mixed_mean":float(np.mean(m)),
        "exact_mean":float(np.mean(e)),
    }

def grid_geometry():
    xc=(np.arange(NX,dtype=float)+0.5)*DX_FT
    yc=(np.arange(NY,dtype=float)+0.5)*DY_FT
    zc=(np.arange(NZ,dtype=float)+0.5)*DZ_FT
    X,Y=np.meshgrid(xc,yc,indexing="xy")
    R=np.sqrt((X-INJ_X)**2+(Y-INJ_Y)**2)
    R3=np.broadcast_to(R,(NZ,NY,NX))
    K=np.broadcast_to(np.arange(NZ)[:,None,None],GRID)
    X3=np.broadcast_to(X,(NZ,NY,NX))
    Y3=np.broadcast_to(Y,(NZ,NY,NX))
    return xc,yc,zc,R3,K,X3,Y3

def savefig(fig:plt.Figure,out:Path,name:str,index:list[dict[str,Any]],kind:str):
    p=out/name
    fig.savefig(p,dpi=220,bbox_inches="tight")
    plt.close(fig)
    index.append({"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size,"kind":kind})
    return p

def selftest():
    assert GRID==(15,50,50)
    assert RADIAL_EDGES[0]==0 and RADIAL_EDGES[-1]==800
    assert CORE_R_FT<MID_R_FT
    print("POSTV16 GPU-HYB-G4-VIS-A2 structural self-test: PASS")

def main(project_root:Path,drive_root:Path)->int:
    root=project_root.resolve()
    drive=drive_root.resolve()
    out=drive/OUT_REL
    blocked=drive/BLOCK_REL
    gates=[]
    stage="preflight"

    def gate(name:str,passed:bool,detail:Any=None):
        ok=bool(passed)
        gates.append({"stage":stage,"gate":name,"pass":ok,"detail":"" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+("" if detail is None else f" -- {detail}"),flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("="*198)
        print("G4-VIS-A2 — SPATIAL / TEMPORAL HYBRID ERROR LOCALIZATION")
        print("READ-ONLY A8/VIS-A1 POST-PROCESSING. DAY100 EXACT ERROR LOCALIZATION + MIXED-ONLY REFRESH EVOLUTION.")
        print("NO PHYSICS EXECUTION. NO MODEL INFERENCE. NO STATE MUTATION. NO NEW SCIENTIFIC THRESHOLD.")
        print("="*198)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_VIS_A1",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        stage="A8_authority"
        a8d=drive/A8_REL
        a8=js(a8d/A8_SUMMARY)
        gate("A8_status_exact",a8.get("status")==A8_STATUS,a8.get("status"))
        gate("A8_validation_complete",a8.get("trajectory_validation_complete") is True)
        gate("A8_production_locked",a8.get("integrated_GPU_runtime_production_authorized") is False)
        a8manifest=verify_manifest(a8d,A8_MANIFEST)
        gate("A8_snapshots_manifested",A8_SNAPS in a8manifest)
        with np.load(a8d/A8_SNAPS,allow_pickle=False) as z:
            times=np.asarray(z["refresh_time_days"],float)
            mixed_refresh_sat=np.asarray(z["mixed_refresh_saturation"],float)
            mixed_refresh_pressure=np.asarray(z["mixed_refresh_pressure_psi"],float)
            exact100=np.asarray(z["exact_100d_saturation"],float)
            exact100r=np.asarray(z["exact_100d_refreshed_saturation"],float)
            exactp100=np.asarray(z["exact_100d_refreshed_pressure_psi"],float)
        gate("refresh_snapshot_shapes",
             mixed_refresh_sat.shape[1:]==GRID and mixed_refresh_pressure.shape==mixed_refresh_sat.shape and
             times.shape==(mixed_refresh_sat.shape[0],),
             (times.shape,mixed_refresh_sat.shape,mixed_refresh_pressure.shape))
        gate("Day100_exact_shapes",exact100.shape==GRID and exact100r.shape==GRID and exactp100.shape==GRID)
        gate("final_refresh_day_100",abs(float(times[-1])-100.0)<=1e-12,times[-1])

        mixed_obs_file=a8["mixed_100d_observation_state_file"]
        gate("mixed_100d_observation_manifested",mixed_obs_file in a8manifest,mixed_obs_file)
        with np.load(a8d/mixed_obs_file,allow_pickle=False) as z:
            mixed100=np.asarray(z["transport_saturation"],float)
        gate("mixed100_shape",mixed100.shape==GRID,mixed100.shape)

        stage="VIS_A1_authority"
        v1d=drive/VIS1_REL
        v1=js(v1d/VIS1_SUMMARY)
        gate("VIS_A1_status_exact",v1.get("status")==VIS1_STATUS,v1.get("status"))
        gate("VIS_A1_no_physics_mutation",v1.get("physics_mutation_performed") is False)
        gate("VIS_A1_no_state_mutation",v1.get("state_mutation_performed") is False)
        verify_manifest(v1d,VIS1_MANIFEST)

        stage="geometry"
        xc,yc,zc,R3,K,X3,Y3=grid_geometry()
        gate("geometry_shape",R3.shape==GRID,R3.shape)

        stage="Day100_spatial_localization"
        radial_rows=[]
        for i,label in enumerate(RADIAL_LABELS):
            lo=float(RADIAL_EDGES[i]);hi=float(RADIAL_EDGES[i+1])
            mask=(R3>=lo)&(R3<hi)
            row={"radial_bin_ft":label,"r_min_ft":lo,"r_max_ft":hi,**subset_metrics(mixed100,exact100,mask)}
            radial_rows.append(row)

        layer_rows=[]
        for k in range(NZ):
            mask=(K==k)
            row={"k_zero_based":k,"physical_layer":k+1,"z_center_ft":float(zc[k]),**subset_metrics(mixed100,exact100,mask)}
            layer_rows.append(row)

        quad_defs={
            "SW":(X3<INJ_X)&(Y3<INJ_Y),
            "SE":(X3>=INJ_X)&(Y3<INJ_Y),
            "NW":(X3<INJ_X)&(Y3>=INJ_Y),
            "NE":(X3>=INJ_X)&(Y3>=INJ_Y),
        }
        quad_rows=[]
        for name,mask in quad_defs.items():
            quad_rows.append({"quadrant":name,**subset_metrics(mixed100,exact100,mask)})

        regime_rows=[]
        for i,label in enumerate(REGIME_LABELS):
            lo=float(REGIME_EDGES[i]);hi=float(REGIME_EDGES[i+1])
            mask=(exact100>=lo)&(exact100<hi)
            regime_rows.append({
                "exact_saturation_regime":label,"exact_sg_min":lo,"exact_sg_max":hi,
                **subset_metrics(mixed100,exact100,mask)
            })

        day100_delta=mixed100-exact100
        core_mask=R3<CORE_R_FT
        mid_mask=(R3>=CORE_R_FT)&(R3<MID_R_FT)
        fringe_mask=R3>=MID_R_FT
        core=subset_metrics(mixed100,exact100,core_mask)
        mid=subset_metrics(mixed100,exact100,mid_mask)
        fringe=subset_metrics(mixed100,exact100,fringe_mask)

        stage="mixed_temporal_evolution"
        temporal_rows=[]
        for n,day in enumerate(times.tolist()):
            s=np.asarray(mixed_refresh_sat[n],float)
            p=np.asarray(mixed_refresh_pressure[n],float)
            temporal_rows.append({
                "day":float(day),
                "core_mean_Sg_r_lt_150ft":float(np.mean(s[core_mask])),
                "mid_mean_Sg_150_to_300ft":float(np.mean(s[mid_mask])),
                "fringe_mean_Sg_r_ge_300ft":float(np.mean(s[fringe_mask])),
                "core_mean_pressure_psi":float(np.mean(p[core_mask])),
                "mid_mean_pressure_psi":float(np.mean(p[mid_mask])),
                "fringe_mean_pressure_psi":float(np.mean(p[fringe_mask])),
                "visible_cell_count_Sg_ge_0p25":int(np.sum(s>=VISIBLE_SG)),
                "mean_Sg":float(np.mean(s)),
                "max_Sg":float(np.max(s)),
            })

        stage="render"
        gate("output_absent",not out.exists(),str(out))
        out.mkdir(parents=True)
        index=[]

        # Day100 radial bias / MAE
        x=np.arange(len(radial_rows))
        fig,ax=plt.subplots(figsize=(9.5,5.8))
        bias=np.asarray([r["bias"] for r in radial_rows],float)
        mae=np.asarray([r["MAE"] for r in radial_rows],float)
        ax.plot(x,bias,marker="o",label="Signed bias")
        ax.plot(x,mae,marker="s",label="MAE")
        ax.axhline(0,linewidth=0.8,color="black")
        ax.set_xticks(x,[r["radial_bin_ft"] for r in radial_rows],rotation=30)
        ax.set_xlabel("Distance from injector (ft)")
        ax.set_ylabel("Saturation difference")
        ax.set_title("Day100 Mixed − Exact saturation error by radial distance")
        ax.legend()
        ax.grid(alpha=0.25)
        savefig(fig,out,"Day0100_Radial_Saturation_Error_Profile.png",index,"DAY100_RADIAL_ERROR")

        # Layer profile
        fig,ax=plt.subplots(figsize=(9.2,5.8))
        lay=np.arange(1,NZ+1)
        ax.plot(lay,[r["bias"] for r in layer_rows],marker="o",label="Signed bias")
        ax.plot(lay,[r["MAE"] for r in layer_rows],marker="s",label="MAE")
        ax.axhline(0,linewidth=0.8,color="black")
        ax.set_xlabel("Physical layer")
        ax.set_ylabel("Saturation difference")
        ax.set_xticks(lay)
        ax.set_title("Day100 Mixed − Exact saturation error by vertical layer")
        ax.legend()
        ax.grid(alpha=0.25)
        savefig(fig,out,"Day0100_Layer_Saturation_Error_Profile.png",index,"DAY100_LAYER_ERROR")

        # Quadrants
        fig,ax=plt.subplots(figsize=(7.8,5.8))
        qnames=[r["quadrant"] for r in quad_rows]
        qbias=[r["bias"] for r in quad_rows]
        qmae=[r["MAE"] for r in quad_rows]
        xx=np.arange(len(qnames));w=.36
        ax.bar(xx-w/2,qbias,w,label="Signed bias")
        ax.bar(xx+w/2,qmae,w,label="MAE")
        ax.axhline(0,linewidth=0.8,color="black")
        ax.set_xticks(xx,qnames)
        ax.set_ylabel("Saturation difference")
        ax.set_title("Day100 Mixed − Exact saturation error by injector quadrant")
        ax.legend()
        savefig(fig,out,"Day0100_Quadrant_Saturation_Error.png",index,"DAY100_QUADRANT_ERROR")

        # Exact saturation regime
        fig,ax=plt.subplots(figsize=(9.0,5.8))
        rx=np.arange(len(regime_rows))
        ax.plot(rx,[r["bias"] for r in regime_rows],marker="o",label="Signed bias")
        ax.plot(rx,[r["MAE"] for r in regime_rows],marker="s",label="MAE")
        ax.axhline(0,linewidth=0.8,color="black")
        ax.set_xticks(rx,[r["exact_saturation_regime"] for r in regime_rows],rotation=25)
        ax.set_xlabel("Exact Day100 saturation regime")
        ax.set_ylabel("Saturation difference")
        ax.set_title("Day100 Hybrid error versus exact saturation regime")
        ax.legend()
        ax.grid(alpha=0.25)
        savefig(fig,out,"Day0100_ExactSaturation_Regime_Error.png",index,"DAY100_SATURATION_REGIME_ERROR")

        # Temporal mixed saturation evolution by radial zone.
        fig,ax=plt.subplots(figsize=(9.4,5.8))
        d=np.asarray([r["day"] for r in temporal_rows],float)
        ax.plot(d,[r["core_mean_Sg_r_lt_150ft"] for r in temporal_rows],marker="o",label="Core r<150 ft")
        ax.plot(d,[r["mid_mean_Sg_150_to_300ft"] for r in temporal_rows],marker="s",label="Mid 150–300 ft")
        ax.plot(d,[r["fringe_mean_Sg_r_ge_300ft"] for r in temporal_rows],marker="^",label="Fringe ≥300 ft")
        ax.set_xlabel("Day")
        ax.set_ylabel("Mean mixed saturation")
        ax.set_title("Mixed trajectory saturation evolution by radial zone")
        ax.legend()
        ax.grid(alpha=0.25)
        savefig(fig,out,"Mixed_Temporal_Saturation_By_Radial_Zone.png",index,"MIXED_TEMPORAL_RADIAL_SATURATION")

        # Temporal mixed pressure evolution by radial zone.
        fig,ax=plt.subplots(figsize=(9.4,5.8))
        ax.plot(d,[r["core_mean_pressure_psi"] for r in temporal_rows],marker="o",label="Core r<150 ft")
        ax.plot(d,[r["mid_mean_pressure_psi"] for r in temporal_rows],marker="s",label="Mid 150–300 ft")
        ax.plot(d,[r["fringe_mean_pressure_psi"] for r in temporal_rows],marker="^",label="Fringe ≥300 ft")
        ax.set_xlabel("Day")
        ax.set_ylabel("Mean mixed refreshed pressure (psi)")
        ax.set_title("Mixed trajectory refreshed pressure evolution by radial zone")
        ax.legend()
        ax.grid(alpha=0.25)
        savefig(fig,out,"Mixed_Temporal_Pressure_By_Radial_Zone.png",index,"MIXED_TEMPORAL_RADIAL_PRESSURE")

        # Day100 layer-8 saturation-delta heatmap for spatial localization.
        delta8=day100_delta[7]
        dmax=max(float(np.max(np.abs(delta8))),1e-12)
        norm=colors.TwoSlopeNorm(vmin=-dmax,vcenter=0.0,vmax=dmax)
        fig,ax=plt.subplots(figsize=(7.8,6.7))
        im=ax.imshow(delta8,origin="lower",extent=[0,1000,0,1000],cmap="coolwarm",norm=norm,interpolation="nearest")
        ax.scatter([INJ_X],[INJ_Y],marker="*",s=150,c="black")
        ax.set_xlabel("X (ft)");ax.set_ylabel("Y (ft)")
        ax.set_title("Day100 Mixed − Exact saturation, physical layer 8")
        cb=fig.colorbar(im,ax=ax,pad=.02);cb.set_label("ΔSg")
        savefig(fig,out,"Day0100_SaturationDelta_Layer8_Localization.png",index,"DAY100_LAYER8_DELTA")

        # Compact localization summary.
        fig,ax=plt.subplots(figsize=(10.5,6.0))
        ax.axis("off")
        text_lines=[
            "PAD-Stream VIS-A2 — Day100 error localization",
            "",
            f"Global saturation relL2: {float(a8['mixed_100d_vs_exact_saturation_relative_L2'])*100:.2f}%",
            f"Core r<150 ft bias / MAE: {core['bias']:+.4f} / {core['MAE']:.4f}",
            f"Mid 150–300 ft bias / MAE: {mid['bias']:+.4f} / {mid['MAE']:.4f}",
            f"Fringe ≥300 ft bias / MAE: {fringe['bias']:+.4f} / {fringe['MAE']:.4f}",
            "",
            "Temporal truth limitation:",
            "Exact fields exist only at Day100 in the saved A8 snapshot artifact.",
            "Earlier refresh plots therefore describe mixed-state evolution, not Mixed−Exact error growth.",
            "",
            "Route attribution limitation:",
            "A8 saved per-step Hybrid/exact route counts, not per-route spatial identities/timings.",
            "B1 must instrument route-level cost and spatial provenance before route-economics optimization.",
        ]
        ax.text(.03,.96,"\n".join(text_lines),va="top",ha="left",fontsize=11,family="monospace")
        savefig(fig,out,"VIS_A2_Localization_Summary.png",index,"LOCALIZATION_SUMMARY")

        stage="publication"
        write_csv(out/RADIAL,radial_rows)
        write_csv(out/LAYERS,layer_rows)
        write_csv(out/QUADS,quad_rows)
        write_csv(out/REGIMES,regime_rows)
        write_csv(out/TEMPORAL,temporal_rows)
        write_csv(out/INDEX,index)

        # Find dominant regions descriptively; these are rankings, not thresholds.
        radial_valid=[r for r in radial_rows if np.isfinite(float(r["MAE"]))]
        layer_valid=[r for r in layer_rows if np.isfinite(float(r["MAE"]))]
        regime_valid=[r for r in regime_rows if np.isfinite(float(r["MAE"]))]
        quad_valid=[r for r in quad_rows if np.isfinite(float(r["MAE"]))]
        dominant_radial=max(radial_valid,key=lambda r:float(r["MAE"]))
        dominant_layer=max(layer_valid,key=lambda r:float(r["MAE"]))
        dominant_regime=max(regime_valid,key=lambda r:float(r["MAE"]))
        dominant_quad=max(quad_valid,key=lambda r:float(r["MAE"]))

        summary={
            "milestone":M,
            "status":PASS,
            "classification":"READ_ONLY_DAY100_SPATIAL_ERROR_LOCALIZATION_AND_MIXED_REFRESH_EVOLUTION_COMPLETE_B1_ROUTE_ECONOMICS_INSTRUMENTATION_AUTHORIZED",
            "refresh_snapshot_count":int(len(times)),
            "refresh_days":[float(x) for x in times],
            "Day100_global_saturation_relative_L2":float(a8["mixed_100d_vs_exact_saturation_relative_L2"]),
            "Day100_core_r_lt_150ft_bias":float(core["bias"]),
            "Day100_core_r_lt_150ft_MAE":float(core["MAE"]),
            "Day100_mid_150_to_300ft_bias":float(mid["bias"]),
            "Day100_mid_150_to_300ft_MAE":float(mid["MAE"]),
            "Day100_fringe_r_ge_300ft_bias":float(fringe["bias"]),
            "Day100_fringe_r_ge_300ft_MAE":float(fringe["MAE"]),
            "dominant_radial_MAE_bin_ft":dominant_radial["radial_bin_ft"],
            "dominant_radial_MAE":float(dominant_radial["MAE"]),
            "dominant_vertical_layer_by_MAE":int(dominant_layer["physical_layer"]),
            "dominant_vertical_layer_MAE":float(dominant_layer["MAE"]),
            "dominant_exact_saturation_regime_by_MAE":dominant_regime["exact_saturation_regime"],
            "dominant_exact_saturation_regime_MAE":float(dominant_regime["MAE"]),
            "dominant_quadrant_by_MAE":dominant_quad["quadrant"],
            "dominant_quadrant_MAE":float(dominant_quad["MAE"]),
            "exact_temporal_refresh_truth_available":False,
            "exact_temporal_truth_limitation":"A8_SAVED_EXACT_FIELD_ONLY_AT_DAY100",
            "earlier_refresh_error_growth_claim_authorized":False,
            "mixed_temporal_evolution_characterized":True,
            "route_spatial_attribution_available_from_A8":False,
            "route_timing_attribution_available_from_A8":False,
            "B1_route_economics_instrumentation_required":True,
            "B1_route_economics_audit_authorized":True,
            "new_scientific_threshold_defined":False,
            "physics_mutation_performed":False,
            "state_mutation_performed":False,
            "production_authorization_changed":False,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        }
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[
            {"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
            for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST
        ])

        print("="*198)
        print(M,"PASS")
        print("Day100 core bias / MAE                       :",core["bias"],"/",core["MAE"])
        print("Day100 mid bias / MAE                        :",mid["bias"],"/",mid["MAE"])
        print("Day100 fringe bias / MAE                     :",fringe["bias"],"/",fringe["MAE"])
        print("Dominant radial MAE bin                      :",dominant_radial["radial_bin_ft"])
        print("Dominant physical layer by MAE               :",dominant_layer["physical_layer"])
        print("Dominant exact-Sg regime by MAE              :",dominant_regime["exact_saturation_regime"])
        print("Dominant quadrant by MAE                     :",dominant_quad["quadrant"])
        print("Earlier exact refresh truth available        : False")
        print("B1 route-economics instrumentation           : AUTHORIZED")
        print("Physics/state mutation                       : NONE")
        print("="*198)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,
            "status":BLOCK,
            "failed_stage":stage,
            "exception":repr(exc),
            "gates":gates,
            "physics_mutation_performed":False,
            "state_mutation_performed":False,
            "B1_route_economics_audit_authorized":False,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(M,"BLOCK")
        print("Stage:",stage)
        print("Exception:",repr(exc))
        return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))

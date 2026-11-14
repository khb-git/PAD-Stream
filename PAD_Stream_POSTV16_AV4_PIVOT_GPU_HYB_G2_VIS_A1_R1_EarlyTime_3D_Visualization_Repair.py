#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,math,shutil,subprocess,sys,tempfile
from pathlib import Path
from typing import Any

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
from PIL import Image

M="POSTV16-AV4-PIVOT-GPU-HYB-G2-VIS-A1-R1"
PASS="POSTV16AV4PIVOTGPUHYBG2VISA1R1_CERTIFIED_EARLYTIME_3D_VISUALIZATION_REPAIR_PASS_NO_PHYSICS_MUTATION"
BLOCK="POSTV16AV4PIVOTGPUHYBG2VISA1R1_TECHNICAL_OR_AUTHORITY_BLOCK_NO_PHYSICS_MUTATION"
BRANCH="postv16-av4-pivot"
PARENT="1fda1877340f34996e136ea2025ac6b19602e7c8"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

FAILED_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_VIS_A1_Certified_EarlyTime_3D_Visualization.py"
FAILED_BLOB="8a401e06d1fa5c3ed4fbca10419c78b9ebeabc68"
FAILED_BLOCK_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_VIS_A1_BLOCKED"
FAILED_BLOCK="POSTV16_AV4_PIVOT_GPU_HYB_G2_VIS_A1_Blocked_Report.json"

VIS_A3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_VIS_A3_Industry_Style_Reservoir_PostProcessing.py"
VIS_A3_BLOB="270def5961bf5a434564b77fe365c6c1c50c2e46"

R3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Rank3_Day40_45_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
R3_BLOB="b06a18d93e68dca2c3d7326cc8b76e4116999117"
R3_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Rank3_Day40_Day45_ExactFlow_and_Hybrid_Endpoint_Diagnostic"
R3_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Summary.json"

R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Rank1_Day75_80_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
R1_BLOB="04c3940a7c736b1d210376113e48bab6111fc173"
R1_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Rank1_Day75_Day80_ExactFlow_and_Hybrid_Endpoint_Diagnostic"
R1_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Summary.json"

R2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Rank2_Day120_125_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
R2_BLOB="1d08f9b2d7c2e38c69862028a731f695811e3cf8"
R2_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Rank2_Day120_Day125_ExactFlow_and_Hybrid_Endpoint_Diagnostic"
R2_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Summary.json"

R3R5_REL=Path("provenance/hybrid_dp/V16E41R3R5_MULTI_REFRESH_CADENCE_SENSITIVITY_RUNTIME_POLICY_CALIBRATION")
R3R5_DAY80="V16E41R3R5_Selected_Calibration_State_80d.npz"

DAYS=[40,45,75,80,120,125]
PAIRS=[(40,45),(75,80),(120,125)]
GRID=(15,50,50)
NZ,NY,NX=GRID
DX_FT=20.0;DY_FT=20.0;DZ_FT=4.0
LX_FT=1000.0;LY_FT=1000.0;LZ_FT=60.0
FT_TO_M=0.3048
VERTICAL_EXAGGERATION=5.0
POROSITY=0.20
BACKGROUND=0.20
CELL_BULK_FT3=DX_FT*DY_FT*DZ_FT
CELL_PV_FT3=POROSITY*CELL_BULK_FT3
THRESHOLDS=(0.25,0.30,0.40,0.50,0.60)
DELTA_FILTER=0.02

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G2_VIS_A1_R1"
OUT_REL=BASE/(OUT_TOKEN+"_Certified_EarlyTime_3D_Visualization_Repair")
STAGE_REL=BASE/(OUT_TOKEN+"_STAGING")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
METRICS=f"{OUT_TOKEN}_Volumetric_Occupancy_Metrics.csv"
PAIR=f"{OUT_TOKEN}_Pairwise_Change_Metrics.csv"
INDEX=f"{OUT_TOKEN}_Visualization_Index.csv"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError): pass

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def gt(root:Path,*a:str)->str:
    return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()

def mod(root:Path,fn:str,blob:str,name:str):
    p=root/fn
    if not p.is_file(): raise GateError(f"missing_source:{fn}")
    actual=gt(root,"hash-object",str(p))
    if actual!=blob: raise GateError(f"source_blob:{fn}:{actual}:{blob}")
    s=importlib.util.spec_from_file_location(name,p)
    if s is None or s.loader is None: raise GateError(f"cannot_import:{fn}")
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def js(p:Path): return json.loads(p.read_text(encoding="utf-8"))

def write_csv(p:Path,rows:list[dict[str,Any]]):
    if not rows:
        p.write_text("",encoding="utf-8");return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)

def load_state(p:Path):
    with np.load(p,allow_pickle=False) as z:
        return np.asarray(z["transport_saturation"],dtype=np.float64),float(np.asarray(z["physical_time_days"]).reshape(()))

def load_diag(p:Path):
    with np.load(p,allow_pickle=False) as z:
        needed=["pressure_psi","xyz_m","tau_end_s","weights_m3_s","producer"]
        for k in needed:
            if k not in z.files: raise GateError(f"diag_missing:{p.name}:{k}")
        return {"pressure":np.asarray(z["pressure_psi"],dtype=np.float64),
                "xyz_m":np.asarray(z["xyz_m"],dtype=np.float64),
                "tau_end_s":np.asarray(z["tau_end_s"],dtype=np.float64),
                "weights_m3_s":np.asarray(z["weights_m3_s"],dtype=np.float64),
                "producer_labels":np.asarray(z["producer"]).astype("U64")}

def records(drive:Path):
    r3=js(drive/R3_REL/R3_SUM);r1=js(drive/R1_REL/R1_SUM);r2=js(drive/R2_REL/R2_SUM)
    if not r3.get("early_3D_visualization_sequence_authorized"): raise GateError("R3_3D_not_authorized")
    specs={
      40:(drive/R3_REL/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Exact_Day40_State.npz",
          drive/R3_REL/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Day40_ExactFlow_and_Hybrid_Diagnostic.npz",r3["Day40_state_sha256"]),
      45:(drive/R3_REL/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Exact_Day45_State.npz",
          drive/R3_REL/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Day45_ExactFlow_and_Hybrid_Diagnostic.npz",r3["Day45_state_sha256"]),
      75:(drive/R1_REL/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Exact_Day75_SelectedPolicy_State.npz",
          drive/R1_REL/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Day75_ExactFlow_and_Hybrid_Diagnostic.npz",r1["Day75_exact_state_sha256"]),
      80:(drive/R3R5_REL/R3R5_DAY80,
          drive/R1_REL/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Day80_ExactFlow_and_Hybrid_Diagnostic.npz",r1["Day80_state_sha256"]),
      120:(drive/R2_REL/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Exact_Day120_State.npz",
           drive/R2_REL/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Day120_ExactFlow_and_Hybrid_Diagnostic.npz",r2["Day120_state_sha256"]),
      125:(drive/R2_REL/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Exact_Day125_State.npz",
           drive/R2_REL/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Day125_ExactFlow_and_Hybrid_Diagnostic.npz",r2["Day125_state_sha256"])}
    out=[]
    for d in DAYS:
        sp,dp,expected=specs[d]
        if not sp.is_file() or not dp.is_file(): raise GateError(f"missing_Day{d}")
        if sha(sp)!=expected: raise GateError(f"Day{d}_state_sha:{sha(sp)}:{expected}")
        sat,t=load_state(sp);dg=load_diag(dp)
        if abs(t-d)>1e-10: raise GateError(f"Day{d}_time:{t}")
        if sat.shape!=GRID or dg["pressure"].shape!=GRID: raise GateError(f"Day{d}_grid_shape")
        if dg["xyz_m"].ndim!=3 or dg["xyz_m"].shape[1:]!=(201,3): raise GateError(f"Day{d}_streamline_shape:{dg['xyz_m'].shape}")
        n=dg["xyz_m"].shape[0]
        if dg["tau_end_s"].shape!=(n,) or dg["weights_m3_s"].shape!=(n,) or dg["producer_labels"].shape!=(n,):
            raise GateError(f"Day{d}_streamline_metadata_shape")
        if not np.all(np.isfinite(sat)) or not np.all(np.isfinite(dg["pressure"])): raise GateError(f"Day{d}_nonfinite")
        out.append({"day":d,"saturation":sat,"state_sha":expected,"diag_sha":sha(dp),
                    "state_file":sp,"diag_file":dp,**dg})
    return out

def make_early_contact_sheet(vis,paths,labels,output):
    if len(paths)!=6 or len(labels)!=6: raise GateError("early_contact_sheet_requires_six_frames")
    tw,th=vis.CONTACT_TILE;m=vis.CONTACT_MARGIN
    sheet=Image.new("RGB",(3*tw+4*m,2*th+3*m),(242,242,242))
    for n,(path,label) in enumerate(zip(paths,labels)):
        with Image.open(path) as im:
            tile=vis.centered_canvas(im,vis.CONTACT_TILE)
        tile=vis.label_tile(tile,label)
        row,col=divmod(n,3)
        sheet.paste(tile,(m+col*(tw+m),m+row*(th+m)))
    sheet.save(output,format="PNG",optimize=False)

def plot_delta_pressure(a,b,out,vis):
    data=(np.asarray(b["pressure"])-np.asarray(a["pressure"]))[vis.MID_COMPLETION_K]
    _,_,_,xe,ye,_=vis.centers_and_edges()
    vmax=max(float(np.max(np.abs(data))),1e-6)
    fig,ax=plt.subplots(figsize=(8.4,7.2))
    pc=ax.pcolormesh(xe,ye,data,cmap="coolwarm",
                     norm=colors.TwoSlopeNorm(vmin=-vmax,vcenter=0.0,vmax=vmax),shading="flat")
    if float(np.min(data))<0<float(np.max(data)):
        xc,yc,_,_,_,_=vis.centers_and_edges()
        ax.contour(xc,yc,data,levels=[0],colors="black",linewidths=0.8)
    vis.add_map_wells(ax);ax.set_aspect("equal");ax.set_xlim(0,LX_FT);ax.set_ylim(0,LY_FT)
    ax.set_xlabel("X (ft)");ax.set_ylabel("Y (ft)")
    ax.set_title(f"Day {a['day']} → {b['day']}: exact pressure change — physical layer {vis.MID_COMPLETION_K+1}")
    fig.colorbar(pc,ax=ax,pad=0.02).set_label("ΔP (psi)");ax.legend(loc="upper right",fontsize=8)
    fig.tight_layout();p=out/f"Day{a['day']:04d}_to_Day{b['day']:04d}_DeltaP_Layer_Map.png"
    fig.savefig(p,dpi=200,bbox_inches="tight");plt.close(fig);return p

def delta3d(a,b,out):
    ds=np.asarray(b["saturation"])-np.asarray(a["saturation"])
    k,j,i=np.indices(GRID);x=(i+.5)*DX_FT;y=(j+.5)*DY_FT;z=(k+.5)*DZ_FT
    m=np.abs(ds)>=DELTA_FILTER
    if not np.any(m): m=np.abs(ds)>0
    vmax=max(float(np.max(np.abs(ds[m]))) if np.any(m) else 1e-6,1e-6)
    fig=plt.figure(figsize=(10.5,8.2));ax=fig.add_subplot(111,projection="3d")
    sc=ax.scatter(x[m],y[m],z[m],c=ds[m],cmap="coolwarm",
                  norm=colors.TwoSlopeNorm(vmin=-vmax,vcenter=0,vmax=vmax),s=8,alpha=.72,linewidths=0)
    ax.set_xlim(0,LX_FT);ax.set_ylim(0,LY_FT);ax.set_zlim(0,LZ_FT)
    ax.set_box_aspect((1,1,(LZ_FT/LX_FT)*VERTICAL_EXAGGERATION));ax.view_init(elev=24,azim=-58)
    ax.set_xlabel("X (ft)");ax.set_ylabel("Y (ft)");ax.set_zlabel("Z (ft)")
    ax.set_title(f"Day {a['day']} → {b['day']}: 3D saturation redistribution\nvisualization filter |ΔSg| ≥ {DELTA_FILTER:.2f}; 5× vertical exaggeration")
    fig.colorbar(sc,ax=ax,pad=.08,shrink=.72).set_label("ΔSg");fig.tight_layout()
    p=out/f"Day{a['day']:04d}_to_Day{b['day']:04d}_DeltaSg_3D.png";fig.savefig(p,dpi=200,bbox_inches="tight");plt.close(fig);return p

def occupancy(r):
    sat=np.asarray(r["saturation"],dtype=np.float64);n=sat.size
    total_bulk=n*CELL_BULK_FT3;total_pv=n*CELL_PV_FT3
    total_sgpv=float(np.sum(sat)*CELL_PV_FT3)
    excess=np.clip(sat-BACKGROUND,0,None)
    total_excess_pv=float(np.sum(excess)*CELL_PV_FT3)
    row={"day":r["day"],"state_sha256":r["state_sha"],"diagnostic_sha256":r["diag_sha"],
         "saturation_min":float(np.min(sat)),"saturation_mean":float(np.mean(sat)),"saturation_max":float(np.max(sat)),
         "total_cell_count":n,"total_bulk_volume_ft3":total_bulk,"total_pore_volume_ft3":total_pv,
         "gas_saturation_weighted_pore_volume_ft3":total_sgpv,
         "excess_saturation_above_background_weighted_pore_volume_ft3":total_excess_pv}
    for th in THRESHOLDS:
        mask=sat>=th;tag=str(th).replace(".","p");q=int(np.count_nonzero(mask))
        sgpv=float(np.sum(sat[mask])*CELL_PV_FT3)
        expv=float(np.sum(excess[mask])*CELL_PV_FT3)
        row[f"cell_volume_fraction_Sg_ge_{tag}"]=q/n
        row[f"pore_volume_fraction_Sg_ge_{tag}"]=q/n
        row[f"gas_saturation_PV_fraction_in_cells_Sg_ge_{tag}"]=sgpv/total_sgpv if total_sgpv>0 else 0.0
        row[f"excess_saturation_PV_fraction_in_cells_Sg_ge_{tag}"]=expv/total_excess_pv if total_excess_pv>0 else 0.0
    return row

def pairmetric(a,b):
    ds=b["saturation"]-a["saturation"];dp=b["pressure"]-a["pressure"]
    return {"day_start":a["day"],"day_end":b["day"],
            "saturation_relative_L2":float(np.linalg.norm(ds.ravel())/max(np.linalg.norm(a["saturation"].ravel()),1e-30)),
            "saturation_Linf":float(np.max(np.abs(ds))),
            "pressure_relative_L2":float(np.linalg.norm(dp.ravel())/max(np.linalg.norm(a["pressure"].ravel()),1e-30)),
            "pressure_max_abs_psi":float(np.max(np.abs(dp))),
            "cells_abs_DeltaSg_ge_0p02":int(np.count_nonzero(np.abs(ds)>=DELTA_FILTER))}

def selftest():
    assert DAYS==[40,45,75,80,120,125] and GRID==(15,50,50)
    assert THRESHOLDS==(0.25,0.30,0.40,0.50,0.60)
    assert abs(CELL_PV_FT3-320.0)<1e-12
    # Prove the repaired six-frame layout is independent of VIS-A3's nine-frame helper.
    with tempfile.TemporaryDirectory() as td:
        td=Path(td);paths=[]
        for i in range(6):
            p=td/f"{i}.png";Image.new("RGB",(50,40),(255,255,255)).save(p);paths.append(p)
        class V:
            CONTACT_TILE=(50,40);CONTACT_MARGIN=2
            @staticmethod
            def centered_canvas(im,size): return im.convert("RGB").resize(size)
            @staticmethod
            def label_tile(tile,label): return tile
        out=td/"sheet.png";make_early_contact_sheet(V,paths,[str(i) for i in range(6)],out)
        assert out.is_file()
    print("POSTV16 GPU-HYB-G2-VIS-A1-R1 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;staging=drive/STAGE_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight"
    def gate(n,c,d=None):
        ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok: raise GateError(n)
    try:
        print("="*180)
        print("G2-VIS-A1-R1 — SIX-FRAME EARLY-TIME 3D VISUALIZATION REPAIR")
        print("READ ONLY — NO PHYSICS OR STATE MUTATION.")
        print("="*180)
        stage="repo"
        gate("branch",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_failed_VIS_A1",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("clean",gt(root,"status","--porcelain")=="")
        mod(root,FAILED_RUNNER,FAILED_BLOB,"g2_vis_failed")
        vis=mod(root,VIS_A3_RUNNER,VIS_A3_BLOB,"g2_vis_a3")
        mod(root,R3_RUNNER,R3_BLOB,"g2_vis_r3")
        mod(root,R1_RUNNER,R1_BLOB,"g2_vis_r1")
        mod(root,R2_RUNNER,R2_BLOB,"g2_vis_r2")

        stage="prior_block_audit"
        prior=drive/FAILED_BLOCK_REL/FAILED_BLOCK
        gate("prior_VIS_A1_block_report_present",prior.is_file(),str(prior))
        pb=js(prior)
        gate("prior_VIS_A1_was_block",str(pb.get("status","")).endswith("BLOCK_NO_PHYSICS_MUTATION"),pb.get("status"))
        prior_exception=str(pb.get("exception",""))
        # The known first harness defect should be recorded; if the old wrapper failed earlier for another reason, stop here.
        gate("prior_block_is_nine_frame_contact_sheet_bug","contact_sheet_requires_nine_frames" in prior_exception,prior_exception)

        stage="source_records"
        recs=records(drive);gate("six_certified_records",len(recs)==6,len(recs))
        gate("record_days_exact",[r["day"] for r in recs]==DAYS,[r["day"] for r in recs])

        stage="output_firewall"
        gate("R1_output_absent",not out.exists(),str(out))
        if staging.exists(): shutil.rmtree(staging)
        staging.mkdir(parents=True)

        pmin=min(float(r["pressure"].min()) for r in recs);pmax=max(float(r["pressure"].max()) for r in recs)
        ta=np.concatenate([r["tau_end_s"]/vis.DAY_TO_S for r in recs]);pos=ta[ta>0]
        gate("positive_TOF_exists",pos.size>0,pos.size)
        tof=colors.LogNorm(vmin=max(float(pos.min()),1e-6),vmax=float(pos.max()))

        stage="individual_renders"
        geos=[];overs=[];pollock=[];press=[]
        for r in recs:
            geos.append(vis.plot_geocellular_saturation(r,staging))
            overs.append(vis.plot_plume_streamline_overlay(r,staging,tof))
            pollock.append(vis.plot_pollock_weighted(r,staging,tof))
            press.append(vis.plot_pressure_layer(r,staging,pmin,pmax))
        gate("six_geocellular",len(geos)==6);gate("six_overlays",len(overs)==6);gate("six_pollock",len(pollock)==6);gate("six_pressure",len(press)==6)

        stage="six_frame_progression"
        labels=[f"Day {d}" for d in DAYS]
        make_early_contact_sheet(vis,geos,labels,staging/f"{OUT_TOKEN}_Saturation_3D_ContactSheet.png")
        make_early_contact_sheet(vis,overs,labels,staging/f"{OUT_TOKEN}_Streamline_Overlay_3D_ContactSheet.png")
        make_early_contact_sheet(vis,pollock,labels,staging/f"{OUT_TOKEN}_Pollock_TOF_3D_ContactSheet.png")
        make_early_contact_sheet(vis,press,labels,staging/f"{OUT_TOKEN}_Pressure_ContactSheet.png")
        # VIS-A3 GIF helper is frame-count agnostic.
        vis.make_gif(geos,labels,staging/f"{OUT_TOKEN}_Saturation_3D_Progression.gif")
        vis.make_gif(overs,labels,staging/f"{OUT_TOKEN}_Streamline_Overlay_3D_Progression.gif")

        stage="pairwise_change_renders"
        by={r["day"]:r for r in recs}
        for a,b in PAIRS:
            delta3d(by[a],by[b],staging)
            plot_delta_pressure(by[a],by[b],staging,vis)

        stage="metrics"
        write_csv(staging/METRICS,[occupancy(r) for r in recs])
        write_csv(staging/PAIR,[pairmetric(by[a],by[b]) for a,b in PAIRS])

        idx=[{"file":p.name,"type":"GIF" if p.suffix.lower()==".gif" else "PNG"}
             for p in sorted(staging.iterdir()) if p.suffix.lower() in {".png",".gif"}]
        write_csv(staging/INDEX,idx)
        gate("visual_file_count_exact",len(idx)==36,len(idx))

        summary={"milestone":M,"status":PASS,
                 "classification":"SIX_FRAME_CONTACT_SHEET_REPAIRED_CERTIFIED_EARLY_DAY40_45_75_80_120_125_3D_VISUALIZATION_COMPLETE_NO_PHYSICS_MUTATION",
                 "prior_failure":"VIS-A3 contact-sheet helper required 9 frames; early authority has 6 frames",
                 "days":DAYS,"pairwise_change_windows":[list(x) for x in PAIRS],
                 "individual_3D_saturation_count":6,"individual_3D_streamline_overlay_count":6,
                 "individual_3D_pollock_TOF_count":6,"individual_pressure_map_count":6,
                 "pairwise_3D_DeltaSg_count":3,"pairwise_DeltaP_map_count":3,
                 "contact_sheet_count":4,"GIF_count":2,"visual_file_count":len(idx),
                 "volumetric_thresholds":list(THRESHOLDS),
                 "raw_cell_volume_and_PV_fraction_equal_due_uniform_phi_and_cell_size":True,
                 "excess_saturation_PV_fraction_metric_added":True,
                 "physics_mutation":False,"production_pressure_refresh_cadence_selected":False,"P4_authorized":False}
        (staging/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(staging/GATES,gates)
        manifest=[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
                  for p in sorted(staging.iterdir()) if p.is_file() and p.name!=MANIFEST]
        write_csv(staging/MANIFEST,manifest)

        staging.rename(out)
        print("="*180);print(M,"PASS")
        print("Visual files:",len(idx))
        print("Six-frame contact sheets: 4")
        print("GIFs: 2")
        print("Pairwise DeltaSg 3D: 3")
        print("Pairwise DeltaP maps: 3")
        print("Physics mutation: False")
        print("Output:",out);print("="*180)
        return 0
    except Exception as e:
        if staging.exists(): shutil.rmtree(staging)
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps(
            {"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(e),
             "gates":gates,"physics_mutation":False},indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(M,"BLOCK");print("Stage:",stage);print("Exception:",repr(e));return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:selftest();raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))

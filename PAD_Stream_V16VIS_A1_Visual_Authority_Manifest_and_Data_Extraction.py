
from __future__ import annotations
from pathlib import Path
import argparse, csv, hashlib, io, json, math, subprocess, zipfile
from typing import Any
import numpy as np

MILESTONE="V16VIS-A1"
STATUS="V16_VISUAL_AUTHORITY_MANIFEST_AND_DATA_EXTRACTION_VALIDATED"
NEXT="V16VIS-B1 - Frozen SGSim Geology and Reservoir Geometry Visuals"

RELEASE_ID="PAD-STREAM-V16-RC1-B92D52088D01078A"
RELEASE_PATH_ID="PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_E49_STATUS="FINAL_V16_FREEZE_AND_RELEASE_CANDIDATE_ASSEMBLED"
EXPECTED_E48_STATUS="LONG_HORIZON_RUNTIME_CLOSURE_AND_V16_INTEGRATION_AUDIT_VALIDATED"

GRID_SHAPE=(15,50,50); NX=50; NY=50; NZ=15
DX_FT=20.0; DY_FT=20.0; DZ_FT=4.0
LX_FT=1000.0; LY_FT=1000.0; LZ_FT=60.0
POROSITY=0.20
OBSERVATION_DAYS=[30.0,60.0,100.0,150.0,250.0,365.0,500.0,750.0,1000.0]
OBSERVATION_STEPS=[611,1222,4640,5747,7931,10400,13259,18490,23668]
FLOW_DIAGNOSTIC_DAYS=[100.0,150.0,250.0,365.0,500.0,750.0,1000.0]
TERMINAL_RESTART_SHA256="af0097b5e7befc7417286fbb90cc2139a3dab583cb3cce972c9293c7b7fe0a7e"

DISPLAY_X_LABEL="X, ft"
DISPLAY_Y_LABEL="Y, ft"
DISPLAY_Z_LABEL="Depth below reservoir top, ft (+z downward)"
DISPLAY_Z_POSITIVE_DIRECTION="DOWNWARD_DEPTH"
LAYER_1_POSITION="SHALLOWEST"
LAYER_15_POSITION="DEEPEST"
ARRAY_LAYOUT="[k,j,i] = [z,y,x]"
VERTICAL_DISPLAY_POLICY=(
    "Display depth is indexed by k: depth_center_ft=(k+0.5)*DZ_FT. "
    "Layer 1 (k=0) is shallowest and Layer 15 (k=14) is deepest. "
    "For legacy flow outputs, preserve raw arrays and define vertical "
    "direction from array adjacency k->k+1; do not reuse legacy TOP/BOTTOM "
    "word labels in publication graphics."
)
LEGACY_SOLVER_NOTE=(
    "Frozen SG3/SG4 comments use an internal +z-upward gravity convention "
    "and describe Layer 1 as bottom. V16VIS does not modify or re-solve "
    "that physics. Reservoir graphics use the locked display convention: "
    "Layer 1 shallowest, Layer 15 deepest, +z downward."
)

SOURCE_BINDINGS={
"E49":("PAD_Stream_V16E49_Final_V16_Freeze_and_Release_Candidate_Assembly.py","15c7f9c749ba41f62f42003a3a12defcda7451d7"),
"R3R4R1":("PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py","5f8433437ce111533338ceada922f51abb2edefe"),
"SG1":("PAD_Stream_V15SG1_SGSim_Geology_Integration.py","07e0f9ee0a2d21baeb0de311bdc556b0fc81846e"),
"SG2":("PAD_Stream_V15SG2_Anisotropic_Transmissibility.py","7242012d3e758472abc3ee7f543831b92d2cf419"),
"SG3":("PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py","66a379cd97ee9120f69e7e7e949171541e4918c3"),
"SG4":("PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py","8d49f88bdf55b0da087af2bed04e69967740e695"),
"SG5":("PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py","9a0b64ea7e669904d0d9855ade1c6b052f05ecea"),
"SG6":("PAD_Stream_V15SG6_TOF_Transport_Coordinates.py","70ceda68e02894167958d753d88b4dbd694731ab"),
"SG7A":("PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py","a4dd47338e7a85f130a6a70d0a41211e38c655f8"),
"SG7D":("PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py","890088c0c0fcab415a2c7351c5079ca8ee12bf82"),
"PERM":("SGSIM_50x50x15_PERM_MD.csv","317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"),
}

E49_REL=Path("provenance/hybrid_dp/V16E49_FINAL_V16_FREEZE_AND_RELEASE_CANDIDATE")
E49_SUMMARY="PAD_Stream_V16E49_Summary.json"; E49_CLOSURE="V16E49_Final_Closure.json"
E49_FREEZE="PAD_Stream_V16_Final_Freeze_Contract.json"; E49_CERT="PAD_Stream_V16_Release_Certificate.json"
E49_MANIFEST="V16E49_Artifact_Manifest.csv"

E48_REL=Path("provenance/hybrid_dp/V16E48_LONG_HORIZON_RUNTIME_CLOSURE_AND_V16_INTEGRATION_AUDIT")
E48_SUMMARY="PAD_Stream_V16E48_Summary.json"; E48_CLOSURE="V16E48_Final_Closure.json"
E48_OBS_AUDIT="V16E48_Observation_Lineage_and_Mass_Audit.csv"
E48_CAPACITY_AUDIT="V16E48_Capacity_Safety_Audit.csv"; E48_MANIFEST="V16E48_Artifact_Manifest.csv"

OUT_REL=Path("visuals")/RELEASE_PATH_ID/"Phase_A_Authority_and_Data_Extraction"
BLOCKED_REL=Path("visuals")/RELEASE_PATH_ID/"Phase_A_BLOCKED"

OBS_SPECS=[
(30.0,611,"E39","V16E39_POST_BREAKTHROUGH_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT","PAD_Stream_V16E39_Summary.json","V16E39_Canonical_PostBreakthrough_SGSim_Runtime_State_Observation_0030d.npz",None,None),
(60.0,1222,"E40","V16E40_POST_BREAKTHROUGH_SECOND_FIXED_OBSERVATION_60D_CHECKPOINT","PAD_Stream_V16E40_Summary.json","V16E40_Canonical_PostBreakthrough_SGSim_Runtime_State_Observation_0060d.npz",None,None),
(100.0,4640,"R3R7","V16E41R3R7_REPAIRED_PRODUCTION_EXACT_100D_OBSERVATION","PAD_Stream_V16E41R3R7_Summary.json","V16E41R3R7_Canonical_Exact_100d_Observation_State_PreRefresh.npz","exact_100d_observation","V16E41R3R7_Authoritative_100d_PostObservation_Refreshed_Restart.npz"),
(150.0,5747,"E42","V16E42_REPAIRED_PRODUCTION_EXACT_150D_OBSERVATION","PAD_Stream_V16E42_Summary.json","V16E42_Canonical_Exact_150d_Observation_State_PreRefresh.npz","exact_150d_observation","V16E42_Authoritative_150d_PostObservation_Refreshed_Restart.npz"),
(250.0,7931,"E43","V16E43_REPAIRED_PRODUCTION_EXACT_250D_OBSERVATION","PAD_Stream_V16E43_Summary.json","V16E43_Canonical_Exact_250d_Observation_State_PreRefresh.npz","exact_250d_observation","V16E43_Authoritative_250d_PostObservation_Refreshed_Restart.npz"),
(365.0,10400,"E44R1","V16E44R1_PREDECESSOR_BINDING_REPAIR_EXACT_365D_OBSERVATION","PAD_Stream_V16E44R1_Summary.json","V16E44R1_Canonical_Exact_365d_Observation_State_PreRefresh.npz","exact_365d_observation","V16E44R1_Authoritative_365d_PostObservation_Refreshed_Restart.npz"),
(500.0,13259,"E45","V16E45_REPAIRED_PRODUCTION_EXACT_500D_OBSERVATION","PAD_Stream_V16E45_Summary.json","V16E45_Canonical_Exact_500d_Observation_State_PreRefresh.npz","exact_500d_observation","V16E45_Authoritative_500d_PostObservation_Refreshed_Restart.npz"),
(750.0,18490,"E46","V16E46_REPAIRED_PRODUCTION_EXACT_750D_OBSERVATION","PAD_Stream_V16E46_Summary.json","V16E46_Canonical_Exact_750d_Observation_State_PreRefresh.npz","exact_750d_observation","V16E46_Authoritative_750d_PostObservation_Refreshed_Restart.npz"),
(1000.0,23668,"E47","V16E47_REPAIRED_PRODUCTION_EXACT_1000D_OBSERVATION","PAD_Stream_V16E47_Summary.json","V16E47_Canonical_Exact_1000d_Observation_State_PreRefresh.npz","exact_1000d_observation","V16E47_Authoritative_1000d_PostObservation_Refreshed_Restart.npz"),
]

FIGURES=[
("G01","3D SGSim permeability model","Geology","Core","DIRECT_FROZEN_STATIC","PERM",None),
("G02","Representative horizontal permeability slices","Geology","Core","DERIVED_FROM_DIRECT","PERM",None),
("G03","X-Z and Y-Z permeability cross-sections","Geology","Core","DERIVED_FROM_DIRECT","PERM",None),
("G04","Permeability distribution / histogram","Geology","Supporting","DERIVED_FROM_DIRECT","PERM",None),
("G05","Five-spot wells over SGSim geology","Geology","Core","DERIVED_FROM_DIRECT","PERM + SG1",None),
("F01","Initial/reference pressure field","Flow","Core","READ_ONLY_DIAGNOSTIC_RECONSTRUCTION","SG2+SG3+PERM","initial"),
("F02","Terminal V16 evolved pressure field","Flow","Core","DIRECT_FROZEN_RUNTIME_FIELD","E47 post-refresh restart",1000.0),
("F03","Terminal pressure cross-section with wells","Flow","Supporting","DERIVED_FROM_DIRECT","E47 post-refresh restart",1000.0),
("F04","Terminal Darcy flux magnitude field","Flow","Core","READ_ONLY_DIAGNOSTIC_RECONSTRUCTION","Frozen V16 flow-epoch build",1000.0),
("F05","Terminal pressure + Darcy flow overlay","Flow","Core","READ_ONLY_DIAGNOSTIC_RECONSTRUCTION","Frozen V16 flow-epoch build",1000.0),
("S01","Full 3D V16 Pollock streamline field","Streamlines","Core","READ_ONLY_DIAGNOSTIC_RECONSTRUCTION","Frozen V16 flow-epoch build",1000.0),
("S02","V16 streamlines colored by producer","Streamlines","Core","READ_ONLY_DIAGNOSTIC_RECONSTRUCTION","Frozen V16 flow-epoch build",1000.0),
("S03","V16 streamlines colored by terminal TOF","Streamlines","Core","READ_ONLY_DIAGNOSTIC_RECONSTRUCTION","Frozen V16 flow-epoch build",1000.0),
("S04","Representative streamline anatomy","Streamlines","Core","DERIVED_FROM_DIAGNOSTIC","V16 Pollock + SG6",1000.0),
("T01","V16 reservoir TOF distribution","TOF","Core","READ_ONLY_DIAGNOSTIC_RECONSTRUCTION","Frozen V16 flow-epoch build",1000.0),
("T02","Distance vs TOF on selected streamlines","TOF","Supporting","DERIVED_FROM_DIAGNOSTIC","V16 Pollock + SG6",1000.0),
("T03","Xi-TOF transport-coordinate schematic","TOF","Core","SCHEMATIC_FROM_FROZEN_CONTRACT","SG6",None),
("P01","Full nine-checkpoint plume set","Plume","Core","DIRECT_FROZEN_OBSERVATION","Exact pre-refresh observation states","30-1000"),
("P02","Six-panel plume evolution composite","Plume","Core","DIRECT_FROZEN_OBSERVATION","30,100,250,500,750,1000 d","selected"),
("P03","Plan-view saturation evolution","Plume","Core","DERIVED_FROM_DIRECT","Exact pre-refresh observation states","30-1000"),
("P04","Vertical plume evolution","Plume","Core","DERIVED_FROM_DIRECT","Exact pre-refresh observation states","30-1000"),
("P05","Final 1000-day 3D plume","Plume","Core","DIRECT_FROZEN_OBSERVATION","E47 exact pre-refresh observation",1000.0),
("R01","Injected / produced / stored CO2 vs time","Runtime","Core","DERIVED_FROM_FROZEN_AUDIT","E48 observation audit","30-1000"),
("R02","Producer CO2 gas cut vs time","Runtime","Core","DERIVED_FROM_FROZEN_AUDIT","E48 observation audit","30-1000"),
("R03","Component-mass residual vs time","Runtime","Core","DERIVED_FROM_FROZEN_AUDIT","E48 observation audit","30-1000"),
("R04","Minimum capacity margin vs time","Runtime","Supporting","DERIVED_FROM_FROZEN_AUDIT","E48 capacity audit","100-1000"),
("A01","Full PAD-Stream V16 scientific architecture","Architecture","Core","SCHEMATIC_FROM_FROZEN_CONTRACT","E49 freeze + R3R6",None),
("A02","Frozen V16 production runtime loop","Architecture","Core","SCHEMATIC_FROM_FROZEN_CONTRACT","R3R6 + E49",None),
("A03","Physics vs recurrent-ML responsibilities","Architecture","Core","SCHEMATIC_FROM_FROZEN_CONTRACT","V16 frozen design",None),
("A04","V14 to V15-SG to V16 development evolution","Architecture","Supporting","SCHEMATIC_FROM_PROVENANCE","Frozen provenance lineage",None),
("A05","V16 freeze / release-candidate summary","Architecture","Core","SCHEMATIC_FROM_FROZEN_CONTRACT","E49 release certificate",None),
]

class GateError(RuntimeError): pass

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def git_blob_sha(p:Path,root:Path)->str:
    x=subprocess.run(["git","-C",str(root),"hash-object",str(p)],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return x.stdout.strip()

def json_bytes(o:Any)->bytes:
    return (json.dumps(o,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()

def csv_bytes(rows:list[dict[str,Any]])->bytes:
    if not rows: return b""
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(rows)
    return s.getvalue().encode()

def deterministic_npz_bytes(arrays:dict[str,Any])->bytes:
    outer=io.BytesIO()
    with zipfile.ZipFile(outer,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for key in sorted(arrays):
            b=io.BytesIO(); np.save(b,np.asarray(arrays[key]),allow_pickle=False)
            info=zipfile.ZipInfo(f"{key}.npy",date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o600<<16
            zf.writestr(info,b.getvalue())
    return outer.getvalue()

def load_json(p:Path): return json.loads(p.read_text(encoding="utf-8"))
def load_csv(p:Path):
    with p.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))
def load_npz(p:Path):
    with np.load(p,allow_pickle=False) as z: return {k:z[k].copy() for k in z.files}
def scalar(v): return float(np.asarray(v).reshape(()))
def int_scalar(v): return int(np.asarray(v).reshape(()))

def immutable_publish(out:Path,files:dict[str,bytes]):
    out.mkdir(parents=True,exist_ok=True)
    for n,d in files.items():
        p=out/n
        if p.exists() and p.read_bytes()!=d: raise GateError(f"existing_output_differs:{n}")
        if not p.exists(): p.write_bytes(d)

def self_test():
    if RELEASE_ID!="PAD-STREAM-V16-RC1-B92D52088D01078A": raise RuntimeError("release_identity")
    if GRID_SHAPE!=(15,50,50): raise RuntimeError("grid_identity")
    if DISPLAY_Z_POSITIVE_DIRECTION!="DOWNWARD_DEPTH": raise RuntimeError("z_direction")
    if LAYER_1_POSITION!="SHALLOWEST" or LAYER_15_POSITION!="DEEPEST": raise RuntimeError("layer_order")
    if (0.5*DZ_FT)!=2.0 or ((NZ-0.5)*DZ_FT)!=58.0: raise RuntimeError("depth_centers")
    if len(FIGURES)!=31: raise RuntimeError(f"figure_count:{len(FIGURES)}")
    if len(OBS_SPECS)!=9: raise RuntimeError("observation_count")
    if [x[0] for x in OBS_SPECS if x[7] is not None] != FLOW_DIAGNOSTIC_DAYS: raise RuntimeError("flow_days")
    print("PAD-Stream V16VIS-A1 visual authority / extraction self-test: PASS")

def main(project_root:Path,drive_root:Path)->int:
    root=Path(project_root).resolve(); drive=Path(drive_root).resolve()
    out=drive/OUT_REL; blocked=drive/BLOCKED_REL
    gates={}; failed_stage=None
    def gate(name,passed,detail=""):
        gates[name]={"passed":bool(passed),"detail":str(detail)}
        if not passed: raise GateError(name)
    try:
        print("\n"+"="*164)
        print("PAD-Stream V16VIS-A1 — Visual Authority Manifest and Data Extraction")
        print("="*164)
        print("Release                         :",RELEASE_ID)
        print("Simulation                      : none")
        print("Accepted-state mutation         : none")
        print("Display vertical axis           : +z downward / increasing depth")
        print("Layer ordering                  : Layer 1 shallowest -> Layer 15 deepest")

        failed_stage="repository_source_binding"
        source_rows=[]
        for role,(fn,expected) in SOURCE_BINDINGS.items():
            p=root/fn; gate(f"{role}_exists",p.is_file(),p)
            actual=git_blob_sha(p,root); gate(f"{role}_git_blob_exact",actual==expected,actual)
            source_rows.append({"role":role,"filename":fn,"expected_git_blob":expected,"actual_git_blob":actual})

        failed_stage="E49_release_identity"
        e49=drive/E49_REL
        for n in [E49_SUMMARY,E49_CLOSURE,E49_FREEZE,E49_CERT,E49_MANIFEST]:
            gate(f"E49_exists_{n}",(e49/n).is_file(),e49/n)
        s49=load_json(e49/E49_SUMMARY); c49=load_json(e49/E49_CLOSURE)
        f49=load_json(e49/E49_FREEZE); cert49=load_json(e49/E49_CERT)
        gate("E49_status_exact",s49.get("status")==EXPECTED_E49_STATUS,s49.get("status"))
        gate("E49_release_id_exact",s49.get("release_id")==RELEASE_ID,s49.get("release_id"))
        gate("E49_V16_frozen",s49.get("V16_frozen") is True)
        gate("E49_closure_passed",c49.get("all_gates_passed") is True)
        gate("E49_no_new_V16_development",c49.get("new_V16_simulation_development_authorized") is False)
        gate("E49_freeze_contract",f49.get("V16_frozen") is True)
        gate("E49_certificate",cert49.get("V16_frozen") is True)
        gate("E49_terminal_SHA",s49.get("terminal_restart_sha256")==TERMINAL_RESTART_SHA256,s49.get("terminal_restart_sha256"))
        for r in load_csv(e49/E49_MANIFEST):
            p=e49/r["file"]; gate(f"E49_manifest_exists_{r['file']}",p.is_file(),p)
            gate(f"E49_manifest_SHA_{r['file']}",sha256_file(p)==r["sha256"],sha256_file(p))

        failed_stage="E48_visual_audit_authority"
        e48=drive/E48_REL
        for n in [E48_SUMMARY,E48_CLOSURE,E48_OBS_AUDIT,E48_CAPACITY_AUDIT,E48_MANIFEST]:
            gate(f"E48_exists_{n}",(e48/n).is_file(),e48/n)
        s48=load_json(e48/E48_SUMMARY); c48=load_json(e48/E48_CLOSURE)
        gate("E48_status_exact",s48.get("status")==EXPECTED_E48_STATUS,s48.get("status"))
        gate("E48_closure_passed",c48.get("all_gates_passed") is True)
        gate("E48_schedule_complete",c48.get("observation_schedule_complete") is True)
        gate("E48_terminal_SHA",c48.get("terminal_restart_sha256")==TERMINAL_RESTART_SHA256)
        obs_audit=load_csv(e48/E48_OBS_AUDIT); obs_by_day={float(r["day"]):r for r in obs_audit}
        gate("E48_nine_observations",sorted(obs_by_day)==OBSERVATION_DAYS,sorted(obs_by_day))
        cap_audit=load_csv(e48/E48_CAPACITY_AUDIT)

        failed_stage="coordinate_and_geology_extraction"
        perm_path=root/SOURCE_BINDINGS["PERM"][0]
        vals=np.loadtxt(perm_path,skiprows=1,dtype=np.float64)
        gate("PERM_count",vals.size==np.prod(GRID_SHAPE),vals.size)
        perm=vals.reshape(GRID_SHAPE,order="C")
        gate("PERM_finite",bool(np.all(np.isfinite(perm))))
        gate("PERM_positive",float(np.min(perm))>0,float(np.min(perm)))
        x=(np.arange(NX,dtype=np.float64)+0.5)*DX_FT
        y=(np.arange(NY,dtype=np.float64)+0.5)*DY_FT
        depth=(np.arange(NZ,dtype=np.float64)+0.5)*DZ_FT
        depth_edges=np.arange(NZ+1,dtype=np.float64)*DZ_FT
        gate("depth_layer1_center",depth[0]==2.0,depth[0])
        gate("depth_layer15_center",depth[-1]==58.0,depth[-1])
        gate("depth_base",depth_edges[-1]==60.0,depth_edges[-1])

        failed_stage="frozen_observation_state_extraction"
        plume_sats=[]; plume_shas=[]; plume_rows=[]
        flow_sats=[]; flow_press=[]; flow_shas=[]; flow_rows=[]
        for day,step,label,rel,summary_name,plume_file,obs_key,restart_file in OBS_SPECS:
            base=drive/"provenance/hybrid_dp"/rel
            sp=base/summary_name; pp=base/plume_file
            gate(f"{label}_summary_exists",sp.is_file(),sp); gate(f"{label}_plume_exists",pp.is_file(),pp)
            sm=load_json(sp); psha=sha256_file(pp)
            if day in (30.0,60.0):
                gate(f"{label}_plume_SHA_E48",psha==obs_by_day[day]["state_sha256"],psha)
            else:
                ob=sm[obs_key]
                gate(f"{label}_plume_filename",ob["state_filename"]==plume_file,ob["state_filename"])
                gate(f"{label}_plume_SHA",ob["state_sha256"]==psha,psha)
                gate(f"{label}_plume_time_summary",float(ob["time_days"])==day,ob["time_days"])
                gate(f"{label}_plume_step_summary",int(ob["step"])==step,ob["step"])
            st=load_npz(pp); sat=np.asarray(st["transport_saturation"],dtype=np.float64)
            gate(f"{label}_plume_shape",sat.shape==GRID_SHAPE,sat.shape)
            gate(f"{label}_plume_time_state",scalar(st["physical_time_days"])==day,scalar(st["physical_time_days"]))
            gate(f"{label}_plume_step_state",int_scalar(st["accepted_step_index"])==step,int_scalar(st["accepted_step_index"]))
            plume_sats.append(sat); plume_shas.append(psha)
            plume_rows.append({"day":day,"step":step,"milestone":label,"authority_class":"DIRECT_FROZEN_OBSERVATION_PRE_REFRESH","source_relpath":str(Path("provenance/hybrid_dp")/rel/plume_file),"source_sha256":psha,"array_key":"transport_saturation","display_z_convention":DISPLAY_Z_POSITIVE_DIRECTION})
            if restart_file:
                rp=base/restart_file; gate(f"{label}_restart_exists",rp.is_file(),rp)
                rsha=sha256_file(rp); post=sm["post_observation_restart"]
                gate(f"{label}_restart_SHA",post["state_sha256"]==rsha,rsha)
                rst=load_npz(rp); fs=np.asarray(rst["transport_saturation"],dtype=np.float64); pr=np.asarray(rst["accepted_pressure_psi"],dtype=np.float64)
                gate(f"{label}_flow_sat_shape",fs.shape==GRID_SHAPE,fs.shape)
                gate(f"{label}_flow_pressure_shape",pr.shape==GRID_SHAPE,pr.shape)
                gate(f"{label}_flow_time",scalar(rst["physical_time_days"])==day,scalar(rst["physical_time_days"]))
                gate(f"{label}_flow_step",int_scalar(rst["accepted_step_index"])==step,int_scalar(rst["accepted_step_index"]))
                flow_sats.append(fs); flow_press.append(pr); flow_shas.append(rsha)
                flow_rows.append({"day":day,"step":step,"milestone":label,"authority_class":"DIRECT_FROZEN_POST_REFRESH_FLOW_STATE","source_relpath":str(Path("provenance/hybrid_dp")/rel/restart_file),"source_sha256":rsha,"direct_fields":"transport_saturation;accepted_pressure_psi","diagnostic_permission":"read-only pressure/flux/Pollock/TOF reconstruction using frozen V16 modules","display_z_convention":DISPLAY_Z_POSITIVE_DIRECTION})
        gate("plume_count_9",len(plume_sats)==9,len(plume_sats))
        gate("flow_count_7",len(flow_sats)==7,len(flow_sats))
        gate("terminal_flow_SHA",flow_shas[-1]==TERMINAL_RESTART_SHA256,flow_shas[-1])

        failed_stage="runtime_metric_extraction"
        rows=sorted(obs_audit,key=lambda r:float(r["day"]))
        md=np.asarray([float(r["day"]) for r in rows]); ms=np.asarray([int(r["step"]) for r in rows],dtype=np.int64)
        inj=np.asarray([float(r["cumulative_injected_co2_mass_kg"]) for r in rows])
        prod=np.asarray([float(r["cumulative_produced_co2_mass_kg"]) for r in rows])
        stored=np.asarray([float(r["stored_co2_mass_kg"]) for r in rows])
        resid=np.asarray([float(r["recomputed_cumulative_mass_residual_kg"]) for r in rows])
        gas=np.asarray([float(r["producer_co2_gas_cut"]) for r in rows])
        gate("metric_days",md.tolist()==OBSERVATION_DAYS,md.tolist())
        gate("metric_steps",ms.tolist()==OBSERVATION_STEPS,ms.tolist())
        caprows=sorted(cap_audit,key=lambda r:float(r["day"]))
        cd=np.asarray([float(r["day"]) for r in caprows])
        cm=np.asarray([float(r["minimum_raw_capacity_margin_kg"]) for r in caprows])
        cr=np.asarray([int(r["capacity_refresh_count"]) for r in caprows],dtype=np.int64)
        ca=np.asarray([int(r["capacity_controller_adjustments_total"]) for r in caprows],dtype=np.int64)
        gate("capacity_margin_positive",float(np.min(cm))>0,float(np.min(cm)))
        gate("capacity_refresh_zero",int(np.sum(cr))==0,int(np.sum(cr)))
        gate("capacity_adjust_zero",int(np.sum(ca))==0,int(np.sum(ca)))

        figure_rows=[]
        for fid,title,family,priority,authority,source,time in FIGURES:
            figure_rows.append({"figure_id":fid,"title":title,"family":family,"priority":priority,"authority_class":authority,"primary_authority":source,"state_time_days":time,"release_id":RELEASE_ID,"display_vertical_axis":DISPLAY_Z_LABEL if family in {"Geology","Flow","Streamlines","TOF","Plume"} else "N/A","accepted_state_mutation_authorized":False})

        coordinate_contract={
            "release_id":RELEASE_ID,"array_layout":ARRAY_LAYOUT,
            "grid":{"nx":NX,"ny":NY,"nz":NZ,"dx_ft":DX_FT,"dy_ft":DY_FT,"dz_ft":DZ_FT,"lx_ft":LX_FT,"ly_ft":LY_FT,"lz_ft":LZ_FT},
            "display_axes":{"x":DISPLAY_X_LABEL,"y":DISPLAY_Y_LABEL,"z":DISPLAY_Z_LABEL,"positive_z_direction":DISPLAY_Z_POSITIVE_DIRECTION},
            "layer_order":{"layer_1":LAYER_1_POSITION,"layer_15":LAYER_15_POSITION,"layer_1_center_depth_ft":2.0,"layer_15_center_depth_ft":58.0,"reservoir_top_depth_ft":0.0,"reservoir_base_depth_ft":60.0},
            "plotting_rules":{"3D":"Use depth values increasing with k and invert the graphical z-axis so larger depth is drawn lower.","vertical_cross_sections":"Depth increases downward; 0 ft at top, 60 ft at bottom.","horizontal_slices":"Layer 1 shallowest through Layer 15 deepest.","vertical_flux":"Use array adjacency k->k+1 as increasing depth; do not publish legacy TOP/BOTTOM labels.","streamlines":"Use stored z/index coordinate as depth-index coordinate for display; preserve point ordering and trajectory values."},
            "legacy_solver_note":LEGACY_SOLVER_NOTE,"vertical_display_policy":VERTICAL_DISPLAY_POLICY,"physics_mutation":False
        }
        extraction_contract={
            "release_id":RELEASE_ID,
            "plume_visual_authority":"pre-refresh exact observation state",
            "flow_visual_authority":"post-refresh authoritative restart at same physical time",
            "diagnostic_reconstruction_authorized":{"pressure":True,"Darcy_flux":True,"Pollock_streamlines":True,"time_of_flight":True,"primary_checkpoint_day":1000.0,"conditions":["Read frozen state only.","Use exact frozen Git-bound V16 modules.","No physical-time advance.","No accepted-step advance.","No ledger change.","No transport update.","No parameter modification.","No calibration.","No replacement of frozen state."]},
            "coordinate_contract_file":"V16VIS_A1_Coordinate_Convention.json"
        }
        arrays={
            "permeability_md":perm,"x_center_ft":x,"y_center_ft":y,"depth_center_ft":depth,"depth_edges_ft":depth_edges,
            "plume_days":np.asarray(OBSERVATION_DAYS),"plume_steps":np.asarray(OBSERVATION_STEPS,dtype=np.int64),"plume_saturation":np.stack(plume_sats),"plume_state_sha256":np.asarray(plume_shas,dtype="U64"),
            "flow_days":np.asarray(FLOW_DIAGNOSTIC_DAYS),"flow_saturation":np.stack(flow_sats),"flow_pressure_psi":np.stack(flow_press),"flow_restart_sha256":np.asarray(flow_shas,dtype="U64"),
            "metric_days":md,"metric_steps":ms,"cumulative_injected_co2_mass_kg":inj,"cumulative_produced_co2_mass_kg":prod,"stored_co2_mass_kg":stored,"cumulative_mass_residual_kg":resid,"producer_co2_gas_cut":gas,
            "capacity_days":cd,"minimum_raw_capacity_margin_kg":cm,"capacity_refresh_count":cr,"capacity_controller_adjustments_total":ca,"porosity":np.asarray(POROSITY)
        }
        cache=deterministic_npz_bytes(arrays); cache_sha=hashlib.sha256(cache).hexdigest()
        core=sum(1 for f in FIGURES if f[3]=="Core"); support=sum(1 for f in FIGURES if f[3]=="Supporting")
        summary={"milestone":MILESTONE,"status":STATUS,"release_id":RELEASE_ID,"V16_frozen":True,"simulation_executed":False,"accepted_state_mutation":False,"figure_count":len(FIGURES),"core_figure_count":core,"supporting_figure_count":support,"plume_observation_states_extracted":len(plume_sats),"flow_consistent_states_extracted":len(flow_sats),"primary_flow_diagnostic_day":1000.0,"visual_cache_sha256":cache_sha,"coordinate_convention":DISPLAY_Z_POSITIVE_DIRECTION,"layer_1_position":LAYER_1_POSITION,"layer_15_position":LAYER_15_POSITION,"next":NEXT}
        closure={"milestone":MILESTONE,"status":STATUS,"all_gates_passed":all(v["passed"] for v in gates.values()),"gate_count":len(gates),"visual_authority_manifest_frozen":True,"coordinate_convention_frozen":True,"z_positive_downward":True,"layer_1_shallowest":True,"layer_15_deepest":True,"nine_plume_states_extracted":True,"seven_flow_states_extracted":True,"runtime_metrics_extracted":True,"visual_cache_sha256":cache_sha,"simulation_state_modified":False,"phase_B_authorized":True,"next":NEXT}
        files={
            "V16VIS_A1_Authoritative_Visual_Data.npz":cache,
            "V16VIS_A1_Visual_Authority_Manifest.csv":csv_bytes(figure_rows),
            "V16VIS_A1_Observation_State_Manifest.csv":csv_bytes(plume_rows),
            "V16VIS_A1_Flow_State_Manifest.csv":csv_bytes(flow_rows),
            "V16VIS_A1_Source_Bindings.csv":csv_bytes(source_rows),
            "V16VIS_A1_Coordinate_Convention.json":json_bytes(coordinate_contract),
            "V16VIS_A1_Extraction_Contract.json":json_bytes(extraction_contract),
            "PAD_Stream_V16VIS_A1_Summary.json":json_bytes(summary),
            "V16VIS_A1_Final_Gate_Matrix.csv":csv_bytes([{"gate":k,**v} for k,v in gates.items()]),
            "V16VIS_A1_Final_Closure.json":json_bytes(closure)
        }
        immutable_publish(out,files)
        manifest=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="V16VIS_A1_Artifact_Manifest.csv":
                manifest.append({"file":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size})
        immutable_publish(out,{"V16VIS_A1_Artifact_Manifest.csv":csv_bytes(manifest)})
        print("\n"+"="*164); print("PAD-Stream V16VIS-A1: PASS"); print("="*164)
        print("Status                              :",STATUS)
        print("Release ID                          :",RELEASE_ID)
        print("Figures registered                  :",len(FIGURES))
        print("Core / supporting figures           :",core,"/",support)
        print("Exact plume states extracted        :",len(plume_sats))
        print("Post-refresh flow states extracted  :",len(flow_sats))
        print("Visual cache SHA                    :",cache_sha)
        print("Vertical display convention         : +z downward / increasing depth")
        print("Layer ordering                      : Layer 1 shallowest -> Layer 15 deepest")
        print("Accepted simulation state modified  : False")
        print("Phase B authorized                  : True")
        print("Next                                :",NEXT)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report={"milestone":MILESTONE,"status":"V16_VISUAL_AUTHORITY_MANIFEST_AND_DATA_EXTRACTION_BLOCKED","failed_stage":failed_stage,"exception":repr(exc),"gates":gates}
        data=json_bytes(report); p=blocked/"V16VIS_A1_Blocked_Report.json"
        if p.exists() and p.read_bytes()!=data:
            p=blocked/("V16VIS_A1_Blocked_Report_"+hashlib.sha256(data).hexdigest()[:12]+".json")
        p.write_bytes(data)
        print("\n"+"="*164); print("PAD-Stream V16VIS-A1: BLOCKED"); print("="*164)
        print("Report      :",p); print("Failed stage:",failed_stage); print("Exception   :",repr(exc))
        return 2

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path("."))
    p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test",action="store_true")
    return p.parse_args()

if __name__=="__main__":
    a=parse_args()
    if a.self_test: self_test(); raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))

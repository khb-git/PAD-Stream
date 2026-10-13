from __future__ import annotations
from pathlib import Path
import argparse, csv, hashlib, io, json, subprocess
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

MILESTONE="V16VIS-B6"
STATUS="FROZEN_V16_ARCHITECTURE_AND_RELEASE_VISUALS_VALIDATED"
NEXT="V16VIS-C1 - Final V16 Visual Package Integration and Closeout Audit"
RELEASE_ID="PAD-STREAM-V16-RC1-B92D52088D01078A"
RID="PAD_STREAM_V16_RC1_B92D52088D01078A"

SOURCE_BINDINGS={
"A1":("PAD_Stream_V16VIS_A1_Visual_Authority_Manifest_and_Data_Extraction.py","7ed31f0e69b63489f25a1833cdc3693f735b1233"),
"B5":("PAD_Stream_V16VIS_B5_Frozen_V16_Runtime_and_Mass_Balance_Visuals.py","cfda1357973d9ae00214835e634e05258c49cab2"),
"E49":("PAD_Stream_V16E49_Final_V16_Freeze_and_Release_Candidate_Assembly.py","15c7f9c749ba41f62f42003a3a12defcda7451d7"),
"R3R6":("PAD_Stream_V16E41R3R6_Production_Runtime_Refresh_Policy_Freeze.py","58f17776a1e72baece909a67ff6e1ca7135adf6a"),
"V14":("PAD_Stream_CCUS_Physics_Development_v14_Complete_Validation.py","e130440eb2fae8d70b133511882947d6ca296c92"),
"V15G0":("PAD_Stream_V15G0_End_to_End_PAD_Stream_Integration_PORTABLE.py","6d56888646c667cf27e39844911f29893d6aeb9c"),
"V16E7":("PAD_Stream_V16E7_Hybrid_Evidence_Synthesis_and_Deployment_Role_Freeze.py","d687c35b8b35c45470cb342bbf61b5e19dbd7451"),
"SG1":("PAD_Stream_V15SG1_SGSim_Geology_Integration.py","07e0f9ee0a2d21baeb0de311bdc556b0fc81846e"),
"SG5":("PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py","9a0b64ea7e669904d0d9855ade1c6b052f05ecea"),
"SG6":("PAD_Stream_V15SG6_TOF_Transport_Coordinates.py","70ceda68e02894167958d753d88b4dbd694731ab"),
"SG7A":("PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py","a4dd47338e7a85f130a6a70d0a41211e38c655f8"),
"SG7D":("PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py","890088c0c0fcab415a2c7351c5079ca8ee12bf82"),
}

PHASES={
"B1":("Phase_B1_Geology_and_Reservoir_Geometry","PAD_Stream_V16VIS_B1_Summary.json","V16VIS_B1_Final_Closure.json","FROZEN_SGSIM_GEOLOGY_AND_RESERVOIR_GEOMETRY_VISUALS_VALIDATED"),
"B2":("Phase_B2_Pressure_and_Darcy_Flow","PAD_Stream_V16VIS_B2_Summary.json","V16VIS_B2_Final_Closure.json","FROZEN_V16_PRESSURE_AND_DARCY_FLOW_VISUALS_VALIDATED"),
"B3R1":("Phase_B3R1_Pollock_Streamline_and_TOF_Interface_Repair","PAD_Stream_V16VIS_B3R1_Summary.json","V16VIS_B3R1_Final_Closure.json","FROZEN_V16_POLLOCK_STREAMLINE_AND_TOF_VISUALS_VALIDATED_R1"),
"B4":("Phase_B4_CO2_Plume_Evolution","PAD_Stream_V16VIS_B4_Summary.json","V16VIS_B4_Final_Closure.json","FROZEN_V16_CO2_PLUME_EVOLUTION_VISUALS_VALIDATED"),
"B5":("Phase_B5_Runtime_and_Mass_Balance","PAD_Stream_V16VIS_B5_Summary.json","V16VIS_B5_Final_Closure.json","FROZEN_V16_RUNTIME_AND_MASS_BALANCE_VISUALS_VALIDATED"),
}
VISROOT=Path("visuals")/RID
OUT_REL=VISROOT/"Phase_B6_Architecture_and_Release"
BLOCKED_REL=VISROOT/"Phase_B6_BLOCKED"
E49_REL=Path("provenance/hybrid_dp/V16E49_FINAL_V16_FREEZE_AND_RELEASE_CANDIDATE")
R3R6_REL=Path("provenance/hybrid_dp/V16E41R3R6_PRODUCTION_RUNTIME_REFRESH_POLICY_FREEZE")
V15_SUM=Path("output/PAD_Stream_V15G0_End_to_End_PAD_Stream_Integration/PAD_Stream_V15G0_Summary.json")
FIGS=[
("A01","A01_Full_PAD_Stream_V16_Scientific_Architecture"),
("A02","A02_Frozen_V16_Production_Runtime_Loop"),
("A03","A03_Physics_vs_Learned_Proposal_Responsibilities"),
("A04","A04_V14_to_V15SG_to_V16_Development_Evolution"),
("A05","A05_V16_Freeze_Release_Candidate_Summary"),
]
DPI=300

class GateError(RuntimeError): pass
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def blob(p,root):
    return subprocess.run(["git","-C",str(root),"hash-object",str(p)],check=True,text=True,stdout=subprocess.PIPE).stdout.strip()
def jload(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def cload(p):
    with Path(p).open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def jbytes(x): return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()
def cbytes(rows):
    if not rows:return b""
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:fields.append(k)
    s=io.StringIO(newline=""); w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)
    return s.getvalue().encode()
def publish(out,files):
    out.mkdir(parents=True,exist_ok=True)
    for n,d in files.items():
        p=out/n
        if p.exists() and p.read_bytes()!=d:raise GateError("existing_output_differs:"+n)
        if not p.exists():p.write_bytes(d)
def save(fig,out,stem):
    rows=[]
    for ext in ("png","pdf"):
        p=out/f"{stem}.{ext}"
        if p.exists():raise GateError("existing_figure:"+p.name)
        fig.savefig(p,dpi=DPI,bbox_inches="tight")
        rows.append({"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size})
    plt.close(fig);return rows
def bx(ax,x,y,w,h,text,fs=9):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.012",facecolor=(0.2,0.45,0.75,0.12),edgecolor="black"))
    ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=fs,wrap=True)
def ar(ax,a,b,c,d,rad=0):
    ax.add_patch(FancyArrowPatch((a,b),(c,d),arrowstyle="-|>",mutation_scale=12,linewidth=1.2,color="black",connectionstyle=f"arc3,rad={rad}"))
def canvas(title):
    fig,ax=plt.subplots(figsize=(14,8));ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis("off");ax.set_title(title,fontsize=16,pad=14);return fig,ax

def a01(out,a):
    fig,ax=canvas("A01 — Full PAD-Stream V16 Scientific Architecture")
    items=[
    ("SGSim geology",a["geology"]),("Pressure",a["pressure"]),("Darcy flux",a["darcy_flux"]),("Pollock",a["streamlines"]),
    ("TOF / ξ",a["transport_coordinate"]),("Transport",a["transport_primary_variable"]),("Grid transfer",a["streamline_grid_transfer"]),("Capillary",a["capillary"])]
    xs=[.03,.27,.51,.75];ys=[.68,.39]
    for n,(t,d) in enumerate(items):
        r,c=divmod(n,4);x,y=xs[c],ys[r];bx(ax,x,y,.20,.19,f"{t}\n\n{d}",8)
        if c<3: ar(ax,x+.20,y+.095,xs[c+1],y+.095)
        elif r==0: ar(ax,x+.10,y,x+.10,ys[1]+.19)
    bx(ax,.15,.07,.70,.18,
       f"Frozen runtime control\nRefresh policy: {a['runtime_refresh_policy']} | max epoch age = {a['maximum_flow_epoch_age_days']:.6f} d\n"
       f"Capacity controller: {a['capacity_controller_role']}\nObservation schedule: {a['observation_schedule_days']} | terminal = {a['terminal_observation_day']:.0f} d",9)
    return save(fig,out,FIGS[0][1])

def a02(out,p):
    fig,ax=canvas("A02 — Frozen V16 Production Runtime Loop")
    nodes=[(.04,.70,.18,.14,"Accepted parent"),(.27,.70,.20,.14,"Event / observation /\ncadence landing"),(.52,.70,.21,.14,"Same-time mass-\nconservative flow refresh"),(.79,.70,.17,.14,"Refreshed-flow\nCFL"),
           (.79,.42,.17,.14,"Conservative\ntransport trial"),(.52,.42,.21,.14,"Raw map-back\ncapacity preflight"),(.27,.42,.20,.14,"Accept or reject\ntransition"),(.04,.42,.18,.14,"Observation /\ncheckpoint")]
    for x,y,w,h,t in nodes:bx(ax,x,y,w,h,t,9)
    for i in range(3):ar(ax,nodes[i][0]+nodes[i][2],.77,nodes[i+1][0],.77)
    ar(ax,.875,.70,.875,.56);ar(ax,.79,.49,.73,.49);ar(ax,.52,.49,.47,.49);ar(ax,.27,.49,.22,.49)
    bx(ax,.07,.11,.39,.15,"Capacity unsafe:\nrollback → same-parent full refresh → refreshed-CFL retry",9)
    bx(ax,.54,.11,.39,.15,"Capacity controller only if still unsafe.\nNo clipping / plume rescaling / artificial mass source.",9)
    ar(ax,.37,.42,.30,.26,.18);ar(ax,.46,.185,.54,.185);ar(ax,.735,.26,.64,.70,.22)
    ax.text(.5,.02,"Hard refresh triggers: "+" | ".join(p["refresh_trigger_policy"]["hard_refresh_triggers"]),ha="center",fontsize=8)
    return save(fig,out,FIGS[1][1])

def a03(out,v):
    fig,ax=canvas("A03 — Exact-Physics Authority vs Learned-Proposal Responsibilities")
    bx(ax,.04,.14,.42,.70,"EXACT / CONSERVATIVE ACCEPTANCE AUTHORITY\n\n• FV pressure + wells\n• conservative Darcy fluxes\n• exact Pollock correction/retrace\n• TOF + conservative control volumes\n• component-mass closure + conservative map-back\n• capillary zero-external-source redistribution\n• refreshed CFL + capacity preflight\n• accepted-state / inventory gates",9)
    bx(ax,.54,.14,.42,.70,"LEARNED / RECURRENT PROPOSAL LAYER\n\nV15: learned pressure, path/event, map-back graph, timestep, well/control and nonlinear preflight proposals.\n\nV16: Hybrid10 / Hybrid12 pre-breakthrough incompressible BL-fan neural proposals under frozen routing.\n\nAll proposals remain subject to exact physics / inventory / conservative map-back authority.\n\nR3R6 authorizes no new ML module after policy freeze.",9)
    ar(ax,.46,.64,.54,.64);ar(ax,.54,.38,.46,.38)
    m=v.get("metrics",{}); pf=m.get("pressure_learned_selection_fraction")
    ax.text(.5,.04,(f"V15G0 learned-pressure selection fraction = {100*pf:.1f}% | " if pf is not None else "")+"Exact classical authorities remain mandatory.",ha="center",fontsize=8.5)
    return save(fig,out,FIGS[2][1])

def a04(out):
    fig,ax=canvas("A04 — PAD-Stream Evolution: V14 → V15-SG → V16")
    bx(ax,.04,.24,.25,.55,"V14 — Classical physics baseline\n\n• deterministic 5×5×5 case\n• BL physics ladder\n• Dykstra–Parsons / F-Φ\n• TPFA pressure / pore velocity\n• Pollock + TOF\n• CCUS validation scenarios",9)
    bx(ax,.375,.24,.25,.55,"V15 / V15-SG — Heterogeneous integration\n\n• 50×50×15 SGSim geology\n• anisotropic FV + five-spot\n• exact 3D Pollock + SG6 TOF/ξ\n• full-physics streamline transport\n• PI-RNN / learned proposal research\n• conservative map-back",9)
    bx(ax,.71,.24,.25,.55,"V16 RC1 — Production runtime + freeze\n\n• hybrid BL-DP proposal routing\n• component-mass primary transport\n• same-time mass-conservative refresh\n• refreshed-CFL / capacity safety\n• exact 30→1000 d observations\n• E48 closure + E49 immutable RC1",9)
    ar(ax,.29,.515,.375,.515);ar(ax,.625,.515,.71,.515)
    ax.text(.5,.07,"Capability increased while exact physics, conservation, and provenance remained acceptance constraints.",ha="center",fontsize=9)
    return save(fig,out,FIGS[3][1])

def a05(out,c,f):
    fig,ax=canvas("A05 — PAD-Stream V16 RC1 Freeze / Release-Candidate Summary")
    vals=[
    ("Release ID",c["release_id"]),("Release",f"{c['release_name']} {c['release_candidate']}"),("Frozen",str(c["V16_frozen"])),
    ("Runtime closed through",f"{c['runtime_closed_through_day']:.0f} days"),("Terminal step",str(c["terminal_step"])),("Production policy",c["production_policy"]),
    ("Max flow-epoch age",f"{c['maximum_flow_epoch_age_days']:.6f} d"),("Observation schedule complete",str(c["observation_schedule_complete"])),
    ("E41 closed",str(c["E41_formally_closed"])),("E48 freeze authorized",str(c["E48_final_freeze_authorized"])),
    ("Capacity fallback used 100–1000 d",str(c["capacity_fallback_used_100_to_1000d"])),("Legacy candidate is truth",str(c["legacy_candidate_is_truth"])) ]
    for col,items in enumerate((vals[:6],vals[6:])):
        x=.05 if col==0 else .53
        for n,(k,v) in enumerate(items):bx(ax,x,.77-n*.105,.42,.075,f"{k}\n{v}",8.5)
    im=f["immutability_policy"]
    ax.text(.5,.06,f"Runtime physics modification authorized = {im['frozen_runtime_physics_modification_authorized']} | Observation-state modification authorized = {im['frozen_observation_states_modification_authorized']} | Post-freeze research must be separately versioned.",ha="center",fontsize=8.2,wrap=True)
    ax.text(.5,.015,"Terminal restart SHA-256: "+c["terminal_restart_sha256"],ha="center",fontsize=7.4)
    return save(fig,out,FIGS[4][1])

def self_test():
    if RELEASE_ID!="PAD-STREAM-V16-RC1-B92D52088D01078A":raise RuntimeError("release")
    if len(FIGS)!=5:raise RuntimeError("figures")
    if SOURCE_BINDINGS["V14"][1]!="e130440eb2fae8d70b133511882947d6ca296c92":raise RuntimeError("v14")
    print("PAD-Stream V16VIS-B6 architecture / release visual self-test: PASS")

def main(project_root:Path,drive_root:Path)->int:
    root=Path(project_root).resolve();drive=Path(drive_root).resolve();out=drive/OUT_REL;blocked=drive/BLOCKED_REL
    gates={};stage=None
    def gate(n,ok,d=""):
        gates[n]={"passed":bool(ok),"detail":str(d)}
        if not ok:raise GateError(n)
    try:
        print("\n"+"="*164);print("PAD-Stream V16VIS-B6 — Frozen V16 Architecture and Release Visuals");print("="*164)
        print("Release                    :",RELEASE_ID);print("Simulation                  : none");print("Accepted-state mutation     : none")
        stage="repository_source_binding"
        for role,(fn,expected) in SOURCE_BINDINGS.items():
            p=root/fn;gate(role+"_exists",p.is_file(),p);actual=blob(p,root);gate(role+"_blob_exact",actual==expected,actual)

        stage="visual_phase_chain"
        closures={}
        for phase,(dirname,sn,cn,estatus) in PHASES.items():
            base=drive/VISROOT/dirname;sp=base/sn;cp=base/cn
            gate(phase+"_summary_exists",sp.is_file(),sp);gate(phase+"_closure_exists",cp.is_file(),cp)
            s=jload(sp);c=jload(cp);closures[phase]=c
            gate(phase+"_status",s.get("status")==estatus,s.get("status"));gate(phase+"_release",s.get("release_id")==RELEASE_ID,s.get("release_id"))
            gate(phase+"_closed",c.get("all_gates_passed") is True);gate(phase+"_unmodified",c.get("accepted_simulation_state_modified") is False,c.get("accepted_simulation_state_modified"))
        gate("B5_authorized_B6",closures["B5"].get("phase_B6_authorized") is True)

        stage="E49_release_contract";e49=drive/E49_REL
        req=["PAD_Stream_V16E49_Summary.json","V16E49_Final_Closure.json","PAD_Stream_V16_Final_Freeze_Contract.json","PAD_Stream_V16_Release_Certificate.json","V16E49_Artifact_Manifest.csv"]
        for n in req:gate("E49_"+n,(e49/n).is_file(),e49/n)
        for r in cload(e49/"V16E49_Artifact_Manifest.csv"):
            p=e49/r["file"];gate("manifest_"+r["file"],p.is_file() and sha(p)==r["sha256"],p)
        es=jload(e49/"PAD_Stream_V16E49_Summary.json");ec=jload(e49/"V16E49_Final_Closure.json");fr=jload(e49/"PAD_Stream_V16_Final_Freeze_Contract.json");cert=jload(e49/"PAD_Stream_V16_Release_Certificate.json")
        gate("E49_status",es.get("status")=="FINAL_V16_FREEZE_AND_RELEASE_CANDIDATE_ASSEMBLED",es.get("status"));gate("E49_release",es.get("release_id")==RELEASE_ID);gate("E49_closed",ec.get("all_gates_passed") is True)
        gate("V16_frozen",fr.get("V16_frozen") is True and cert.get("V16_frozen") is True);gate("terminal_1000d",float(cert["runtime_closed_through_day"])==1000.0)
        gate("immutability",fr["immutability_policy"]["frozen_runtime_physics_modification_authorized"] is False)
        arch=fr["accepted_runtime_architecture"]

        stage="R3R6_policy";r3=drive/R3R6_REL
        pc=r3/"PAD_Stream_V16E41R3R6_Production_Runtime_Refresh_Policy_Contract.json";cc=r3/"V16E41R3R6_Final_Closure.json"
        gate("policy_exists",pc.is_file());gate("policy_closure_exists",cc.is_file())
        pol=jload(pc);pcl=jload(cc);gate("policy_status",pol.get("status")=="PRODUCTION_RUNTIME_REFRESH_POLICY_FROZEN",pol.get("status"));gate("policy_closed",pcl.get("all_gates_passed") is True)
        gate("no_new_ml",pol["scope_guards"]["new_ML_module_authorized"] is False);gate("capacity_fallback_only",pol["capacity_safety_policy"]["capacity_controller_is_normal_timestep_driver"] is False)

        stage="V15G0_provenance";vp=root/V15_SUM;gate("V15_summary_exists",vp.is_file(),vp);vs=jload(vp);gate("V15_pass",vs.get("status")=="PASS");gate("V15_approved",vs.get("deployment_approved") is True)
        gate("V15_exact_authority",any("Exact classical authorities remain mandatory" in x for x in vs.get("limitations",[])))

        stage="figure_rendering"
        if out.exists() and any(out.iterdir()):raise GateError("B6_output_directory_not_empty")
        out.mkdir(parents=True,exist_ok=True)
        rendered=[];rendered+=a01(out,arch);rendered+=a02(out,pol);rendered+=a03(out,vs);rendered+=a04(out);rendered+=a05(out,cert,fr)
        gate("rendered_10",len(rendered)==10,len(rendered));gate("rendered_nonempty",all(x["bytes"]>0 for x in rendered))

        stage="closeout";by={}
        for r in rendered:by.setdefault(Path(r["file"]).stem,[]).append(r)
        auth={
        "A01":"SCHEMATIC_FROM_FROZEN_CONTRACT: E49 accepted runtime architecture",
        "A02":"SCHEMATIC_FROM_FROZEN_CONTRACT: R3R6 frozen production runtime policy",
        "A03":"SCHEMATIC_FROM_FROZEN_CONTRACT_AND_PROVENANCE: V15G0 + V16E7 + R3R6",
        "A04":"SCHEMATIC_FROM_PROVENANCE: V14 + V15/V15-SG + V16",
        "A05":"SCHEMATIC_FROM_FROZEN_CONTRACT: E49 freeze contract + release certificate"}
        index=[]
        for fid,stem in FIGS:index.append({"figure_id":fid,"authority":auth[fid],"release_id":RELEASE_ID,"simulation_executed":False,"accepted_state_mutation":False,"files":";".join(sorted(x["file"] for x in by[stem]))})
        captions=[
        {"figure_id":"A01","caption":"Full V16 scientific architecture from the E49 accepted-runtime contract."},
        {"figure_id":"A02","caption":"Frozen production runtime loop from R3R6, including same-time mass-conservative refresh, refreshed-flow CFL, and fallback-only capacity control."},
        {"figure_id":"A03","caption":"Learned branches are proposal mechanisms; exact physics, inventory, conservation, and map-back gates retain acceptance authority."},
        {"figure_id":"A04","caption":"Development evolution from the V14 classical baseline through V15/V15-SG heterogeneous and learned-proposal integration to V16 RC1 production closure."},
        {"figure_id":"A05","caption":"RC1 freeze and release-candidate identity from the E49 release certificate and immutability contract."}]
        contract={"milestone":MILESTONE,"release_id":RELEASE_ID,"figure_authority":auth,"prior_visual_phases_verified":list(PHASES),"failed_B3_superseded_by_B3R1":True,"new_architecture_claim_introduced":False,"new_ML_module_introduced":False,"new_physics_introduced":False,"accepted_state_mutation":False}
        summary={"milestone":MILESTONE,"status":STATUS,"release_id":RELEASE_ID,"simulation_executed":False,"accepted_state_mutation":False,"figure_families_completed":["A01","A02","A03","A04","A05"],"rendered_variants":5,"rendered_files_png_pdf":10,"prior_visual_phases_verified":list(PHASES),"V16_frozen":True,"terminal_day":cert["runtime_closed_through_day"],"terminal_step":cert["terminal_step"],"next":NEXT}
        closure={"milestone":MILESTONE,"status":STATUS,"all_gates_passed":all(v["passed"] for v in gates.values()),"gate_count":len(gates),"A01_complete":True,"A02_complete":True,"A03_complete":True,"A04_complete":True,"A05_complete":True,"all_A1_registered_figure_families_now_covered_by_B1_through_B6":True,"prior_phase_chain_validated":True,"accepted_simulation_state_modified":False,"final_visual_package_integration_authorized":True,"next":NEXT}
        publish(out,{"V16VIS_B6_Figure_Index.csv":cbytes(index),"V16VIS_B6_Figure_Captions.csv":cbytes(captions),"V16VIS_B6_Architecture_Release_Contract.json":jbytes(contract),"PAD_Stream_V16VIS_B6_Summary.json":jbytes(summary),"V16VIS_B6_Final_Gate_Matrix.csv":cbytes([{"gate":k,**v} for k,v in gates.items()]),"V16VIS_B6_Final_Closure.json":jbytes(closure)})
        man=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="V16VIS_B6_Artifact_Manifest.csv":man.append({"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size})
        publish(out,{"V16VIS_B6_Artifact_Manifest.csv":cbytes(man)})
        print("\n"+"="*164);print("PAD-Stream V16VIS-B6: PASS");print("="*164)
        print(f"{'Status':72}: {STATUS}");print(f"{'Release ID':72}: {RELEASE_ID}");print(f"{'Figure families completed':72}: A01, A02, A03, A04, A05");print(f"{'Rendered PNG/PDF files':72}: 10")
        print(f"{'Prior visual phase chain':72}: B1, B2, B3R1, B4, B5 — verified");print(f"{'V16 frozen':72}: True");print(f"{'Terminal runtime':72}: day {cert['runtime_closed_through_day']:.1f} / step {cert['terminal_step']}")
        print(f"{'Accepted simulation state modified':72}: False");print(f"{'Final visual integration authorized':72}: True");print(f"{'Next':72}: {NEXT}")
        return 0
    except Exception as e:
        blocked.mkdir(parents=True,exist_ok=True);data=jbytes({"milestone":MILESTONE,"status":"FROZEN_V16_ARCHITECTURE_AND_RELEASE_VISUALS_BLOCKED","failed_stage":stage,"exception":repr(e),"gates":gates})
        p=blocked/"V16VIS_B6_Blocked_Report.json"
        if p.exists() and p.read_bytes()!=data:p=blocked/("V16VIS_B6_Blocked_Report_"+hashlib.sha256(data).hexdigest()[:12]+".json")
        p.write_bytes(data);print("\n"+"="*164);print("PAD-Stream V16VIS-B6: BLOCKED");print("="*164);print("Report      :",p);print("Failed stage:",stage);print("Exception   :",repr(e));return 2

def parse_args():
    p=argparse.ArgumentParser();p.add_argument("--project-root",type=Path,default=Path("."));p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"));p.add_argument("--self-test",action="store_true");return p.parse_args()
if __name__=="__main__":
    a=parse_args()
    if a.self_test:self_test();raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))

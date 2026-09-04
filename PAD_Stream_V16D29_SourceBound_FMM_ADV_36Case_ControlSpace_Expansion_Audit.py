#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,sys
R=Path(__file__).resolve().parent
D28=R/"output"/"V16_D28_R1_36CASE_D9R1_CONSERVATIVE_FACE_METRIC_EXPANSION"/"PAD_Stream_V16D28_R1_Summary.json"
D28SHA="3f7664b8b9b2d5a11dc24e1d3528d9a373a606295c7ef39937aff35a4c071f4c"
D10C=R/"PAD_Stream_V16D10C_Full_Case0002_0025_SourceBound_FMM_ADV_TravelTime_Hierarchy_Execution.py"
FMM=R/"PAD_Stream_V16B2_Exact_3D_Fast_Marching_Arrival_Time_Baseline.py"
B7=R/"PAD_Stream_V16B7_Controlled_Directional_Advective_Travel_Time_Solve.py"
SG5=R/"PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
HASH={"FMM":"0b26e3cdbc41276c53f4778e7eddcddd0cc8ef081ffb495b71df548152e8f049",
"B7":"2355f3eecd41bb6571f7ead3ebb1c5d90a1907ae681826159e79463166994c56",
"SG5":"2989fe58d1fd78fe9f9c03176dbb3ff066faf359f7edaf028cbdc0fea85135f2"}
OUT=R/"output"/"V16_D29_SOURCEBOUND_FMM_ADV_36CASE_CONTROLSPACE_EXPANSION_AUDIT";OUT.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-29")
 print("Source-Bound FMM/ADV 36-Case Control-Space Expansion Audit");print("="*78)
 gates={"D28R1_SHA_exact":D28.exists() and sha(D28)==D28SHA,"D10C_exists":D10C.exists(),
        "FMM_source_SHA_exact":FMM.exists() and sha(FMM)==HASH["FMM"],
        "B7_source_SHA_exact":B7.exists() and sha(B7)==HASH["B7"],
        "SG5_source_SHA_exact":SG5.exists() and sha(SG5)==HASH["SG5"]}
 if not all(gates.values()):print(gates);raise RuntimeError("authority pre-gate failure")
 d=json.loads(D28.read_text());gates["D28R1_status_authorizes_FMM_ADV"]=d.get("status")=="V16D_36CASE_D9R1_CONSERVATIVE_C7_FACE_METRIC_ENSEMBLE_CERTIFIED_FMM_ADV_CONTROLSPACE_EXPANSION_AUTHORIZED"
 t=D10C.read_text(encoding="utf-8",errors="replace")
 required=[
 "construct_face_pore_velocities(qx,qy,qz)",
 "cx,cy,cz=cv(vx,vy,vz)",
 "speed=np.sqrt(cx*cx+cy*cy+cz*cz)",
 "bind_injector_sources(qx,qy,qz)",
 "fast_marching_3d(speed,sm,6.096,6.096,1.2192)",
 "aW=np.maximum(cx,0)/dx",
 "aE=np.maximum(-cx,0)/dx",
 "aS=np.maximum(cy,0)/dy",
 "aN=np.maximum(-cy,0)/dy",
 "aB=np.maximum(cz,0)/dz",
 "aT=np.maximum(-cz,0)/dz",
 "runpy.run_path(str(B7_SRC),run_name=\"__main__\")"
 ]
 for x in required:gates["D10C_has_"+re.sub(r'[^A-Za-z0-9]+','_',x)[:50]]=x in t
 gates["D10C_binds_exact_source_hashes"]=all(HASH[k] in t for k in HASH)
 gates["Pollock_remains_authoritative_reference"]="Pollock_remains_authoritative_reference" in t
 gates["FMM_auxiliary_scalar_role"]="FMM_role_auxiliary_scalar_control" in t
 gates["ADV_auxiliary_directional_role"]="ADV_role_auxiliary_directional_field" in t
 gates["no_execution_in_D29"]=True;gates["no_transport"]=True;gates["no_training"]=True
 report={"milestone":"V16D-29","D28R1_sha256":sha(D28),"D10C_source":D10C.name,"D10C_sha256":sha(D10C),
 "frozen_sources":{"FMM":{"path":FMM.name,"sha256":sha(FMM)},"B7":{"path":B7.name,"sha256":sha(B7)},"SG5":{"path":SG5.name,"sha256":sha(SG5)}},
 "execution_contract":{"cell_velocity":"D10C cv(face velocities)","FMM_speed":"sqrt(cx^2+cy^2+cz^2)",
 "FMM_sources":"frozen FMM bind_injector_sources(qx,qy,qz)","FMM_spacing_m":[6.096,6.096,1.2192],
 "ADV":"D10C frozen closed-boundary projected upwind coefficients -> exact B7 runner",
 "roles":{"Pollock":"authoritative trajectory TOF","FMM":"auxiliary scalar connectivity control","ADV":"auxiliary directional Eulerian travel time"}},
 "gates":gates}
 rp=OUT/"V16D29_Source_Binding_Report.json";rp.write_text(json.dumps(report,indent=2))
 ok=all(gates.values())
 status="V16D_D10C_FMM_ADV_EXACT_EXECUTION_LINEAGE_BOUND_36CASE_D29R1_EXECUTION_AUTHORIZED" if ok else "V16D_D29_FMM_ADV_SOURCE_BINDING_BLOCKED"
 nxt="V16D-29-R1 — Execute exact D10C-derived FMM/ADV hierarchy across all 36 control-space Foundation Cases" if ok else "Resolve FMM/ADV execution lineage; do not execute."
 sp=OUT/"PAD_Stream_V16D29_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-29","status":status,"report_sha256":sha(rp),"gates":gates,"next_milestone":nxt},indent=2))
 print("\nBOUND SOURCES")
 print("  D10C:",sha(D10C));print("  FMM :",sha(FMM));print("  B7  :",sha(B7));print("  SG5 :",sha(SG5))
 print("\nGATES");[print(f"[{'PASS' if v else 'FAIL'}] {k}") for k,v in gates.items()]
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

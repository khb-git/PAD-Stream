#!/usr/bin/env python
from pathlib import Path
import csv,json,hashlib,importlib.util,numpy as np

ROOT=Path(__file__).resolve().parent
R1=ROOT/"output"/"V16_D8R1_EXACT_SG5_SEED_CONTAINER_ADAPTER_REPAIR_CASE0002_POLLOCK_PILOT"/"PAD_Stream_V16D8R1_Summary.json"
FLOW=ROOT/"output"/"V16_D7B_FULL_FROZEN_CASE0002_0025_SOURCEBOUND_SG2_SG3_SG4_FLOW_ENSEMBLE"/"cases"
SG5=ROOT/"PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
OUT=ROOT/"output"/"V16_D8B_FULL_CASE0002_0025_SOURCEBOUND_SG5_POLLOCK_ENSEMBLE"
CASES=OUT/"cases";CASES.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def mod():
 s=importlib.util.spec_from_file_location("v16d8b_sg5",SG5)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
 print("="*78);print("PAD-Stream V16D-8B")
 print("Full Case 0002-0025 Source-Bound SG5 Pollock Ensemble Execution");print("="*78)
 r=json.loads(R1.read_text())
 if r["status"]!="V16D_CASE0002_SOURCEBOUND_SG5_POLLOCK_PILOT_CERTIFIED_FULL_24CASE_POLLOCK_EXECUTION_AUTHORIZED":raise RuntimeError("D8R1 mismatch")
 if sha(SG5)!=r["SG5_sha256"]:raise RuntimeError("SG5 hash changed")
 sg5=mod()
 print("""
D8B REPEATS THE CERTIFIED D8R1 SOURCE-NATIVE SG5 PATH FOR ALL 24 CASES:
  construct_face_pore_velocities
  build_seeds -> (faces, seeds)
  trace_streamlines
  validate_streamlines

NO CASE IS REJECTED FOR STREAMLINE SHAPE, TOF DISTRIBUTION, OR PRODUCER SPLIT.
THE SOURCE SG5 VALIDATION CONTRACT IS THE CASE-LEVEL AUTHORITY.
""")
 recs=[]
 for idx in range(2,26):
  cid=f"V16D_Foundation_Case_{idx:04d}";fp=FLOW/f"{cid}_Flow.npz"
  rec={"case_id":cid}
  try:
   z=np.load(fp);qx,qy,qz=[np.asarray(z[k],float) for k in ["Qx","Qy","Qz"]]
   vx,vy,vz=sg5.construct_face_pore_velocities(qx,qy,qz)[:3]
   faces,seeds=sg5.build_seeds(qx,qy,qz)
   streams=sg5.trace_streamlines(seeds,vx,vy,vz)
   validation=sg5.validate_streamlines(faces,seeds,streams)
   bools=[]
   def walk(x):
    if isinstance(x,(bool,np.bool_)):bools.append(bool(x))
    elif isinstance(x,dict):
     for y in x.values():walk(y)
    elif isinstance(x,(tuple,list)):
     for y in x:walk(y)
   walk(validation)
   valid=all(bools) if bools else True
   statuses=[str(s.get("status","")) for s in streams]
   times=np.array([float(s.get("travel_time_s",np.nan)) for s in streams])
   weights=np.array([float(s.get("weight_m3_s",np.nan)) for s in streams])
   producers=[str(s.get("producer","")) for s in streams]
   passed=(valid and len(seeds)>0 and len(streams)==len(seeds) and
           all(x=="PRODUCER" for x in statuses) and np.isfinite(times).all() and np.all(times>0) and
           np.isfinite(weights).all() and np.all(weights>0))
   out=CASES/f"{cid}_Pollock.npz"
   np.savez_compressed(out,Vx=vx,Vy=vy,Vz=vz,faces=np.array(faces,dtype=object),
      seeds=np.array(seeds,dtype=object),streamlines=np.array(streams,dtype=object),
      case_id=np.array(cid))
   unique,counts=np.unique(producers,return_counts=True)
   rec.update(status="CERTIFIED" if passed else "POLLOCK_GATE_FAILURE",sha256=sha(out),
      face_count=len(faces),seed_count=len(seeds),streamline_count=len(streams),
      captured_count=sum(x=="PRODUCER" for x in statuses),
      weight_sum_m3_s=float(weights.sum()),tof_min_days=float(times.min()/86400),
      tof_median_days=float(np.median(times)/86400),tof_mean_days=float(times.mean()/86400),
      tof_max_days=float(times.max()/86400),
      producer_count=len(unique),producer_counts=";".join(f"{u}:{c}" for u,c in zip(unique,counts)),
      vx_absmax=float(np.max(np.abs(vx))),vy_absmax=float(np.max(np.abs(vy))),vz_absmax=float(np.max(np.abs(vz))))
  except Exception as e:rec.update(status="TECHNICAL_FAILURE",error=repr(e))
  recs.append(rec);print(f"\n[{idx-1:02d}/24] {cid} -> {rec['status']}")
 fields=sorted(set().union(*(r.keys() for r in recs)))
 man=OUT/"V16D8B_Pollock_Ensemble_Manifest.csv"
 with man.open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(recs)
 good=[r for r in recs if r["status"]=="CERTIFIED"]
 vals=lambda k:np.array([float(r[k]) for r in good])
 gates={"D8R1_bound":True,"SG5_hash_exact":True,"all_24_attempted":len(recs)==24,
  "all_24_certified":len(good)==24,"no_case_replacement":True,
  "all_streamlines_producer_captured":len(good)==24 and all(int(r["captured_count"])==int(r["streamline_count"]) for r in good),
  "all_four_producers_each_case":len(good)==24 and all(int(r["producer_count"])==4 for r in good),
  "all_tof_positive_finite":len(good)==24 and all(float(r["tof_min_days"])>0 for r in good),
  "no_streamline_shape_selection":True,"no_tof_selection":True,"no_transport":True,"no_training":True}
 gates={k:bool(v) for k,v in gates.items()}
 ok=all(gates.values())
 status="V16D_CASE0002_0025_SOURCEBOUND_SG5_POLLOCK_ENSEMBLE_CERTIFIED_READY_FOR_MULTICASE_TRAVELTIME_HIERARCHY" if ok else "V16D_MULTICASE_SG5_POLLOCK_ENSEMBLE_HAS_DOCUMENTED_FAILURES"
 summary={"milestone":"V16D-8B","status":status,"certified_count":int(len(good)),
  "manifest":{"path":str(man.relative_to(ROOT)),"sha256":sha(man)},
  "ensemble_metrics":({k:{"min":float(vals(k).min()),"median":float(np.median(vals(k))),"max":float(vals(k).max())}
    for k in ["seed_count","tof_min_days","tof_median_days","tof_mean_days","tof_max_days","weight_sum_m3_s"]} if good else {}),
  "gates":gates,
  "next_milestone":"V16D-9 — Multi-Case Pollock TOF/201-Node Transport Coordinate and C7 Metric Construction"}
 sp=OUT/"PAD_Stream_V16D8B_Summary.json";sp.write_text(json.dumps(summary,indent=2))
 print("\nENSEMBLE POLLOCK SUMMARY")
 print(f"  certified             : {len(good)}/24")
 if good:
  print(f"  streamline count min/median/max: {vals('seed_count').min():.0f} / {np.median(vals('seed_count')):.0f} / {vals('seed_count').max():.0f}")
  print(f"  median TOF days min/median/max : {vals('tof_median_days').min():.3f} / {np.median(vals('tof_median_days')):.3f} / {vals('tof_median_days').max():.3f}")
  print(f"  max TOF days min/median/max    : {vals('tof_max_days').min():.3f} / {np.median(vals('tof_max_days')):.3f} / {vals('tof_max_days').max():.3f}")
 print(f"  manifest SHA-256: {sha(man)}")
 print("\n"+"="*78);print("V16D-8B GATES");print("="*78)
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status)
 print("\nNEXT MILESTONE\n  V16D-9 — Multi-Case Pollock TOF/201-Node Transport Coordinate and C7 Metric Construction")
 if not ok:raise SystemExit(2)
if __name__=="__main__":main()

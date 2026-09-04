#!/usr/bin/env python3
from pathlib import Path
import ast,hashlib,json,re,sys
R=Path(__file__).resolve().parent
S=R/"output"/"V16_D24C_R3_SOURCEPATCH_SG4_CONTROL_DIAGNOSTIC"/"PAD_Stream_V16D24C_R3_Summary.json"
SSHA="a72ee2d47e702bcfd51091f1d372866d79b05f146e9e8261e03e3d2a82661d47"
SG3=R/"PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG4=R/"PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SHA3="d3ba7b7be45636f6d3ee254fd6cb95268cef9e6f35e85d53b5793596cb22b14d"
SHA4="86a1c88ffc35033314ae6598ade23f0bebfa709f62cbe2cbef1830cd607e0af9"
O=R/"output"/"V16_D24C_R4_SG4_CONTROL_DEPENDENCY_BINDING";O.mkdir(parents=True,exist_ok=True)
CONTROLS=("CO2_MASS_RATE_TONNES_DAY","PRODUCER_BHP_PSI")
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def funcs_using(tree,names):
 out={}
 for n in ast.walk(tree):
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
   used=sorted({x.id for x in ast.walk(n) if isinstance(x,ast.Name) and x.id in names})
   if used:out[n.name]={"line":n.lineno,"controls":used}
 return out
def assignments(tree,names):
 out={}
 for n in ast.walk(tree):
  if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in names:
   try:v=ast.literal_eval(n.value)
   except:v=ast.unparse(n.value)
   out[n.targets[0].id]={"line":n.lineno,"value":v}
 return out
def main():
 print("="*78);print("PAD-Stream V16D-24C-R4")
 print("SG4 Well-Source Control Dependency Binding + Cross-Module Adapter Contract");print("="*78)
 gates={"R3_SHA_exact":sha(S)==SSHA,"SG3_SHA_exact":sha(SG3)==SHA3,"SG4_SHA_exact":sha(SG4)==SHA4}
 if not all(gates.values()):raise RuntimeError("authority SHA failure")
 t3=SG3.read_text(encoding="utf-8");t4=SG4.read_text(encoding="utf-8")
 tr3=ast.parse(t3);tr4=ast.parse(t4)
 a3=assignments(tr3,CONTROLS);a4=assignments(tr4,CONTROLS)
 # Include derived controls that SG4 well-source function actually reads.
 derived=("CO2_MASS_RATE_KG_S","CO2_RESERVOIR_RATE_M3_S","CO2_RESERVOIR_RATE_M3_DAY","PRODUCER_BHP_PA")
 f4=funcs_using(tr4,set(CONTROLS+derived))
 print("\nSG3 base assignments:",a3);print("SG4 base assignments:",a4)
 print("\nSG4 functions consuming control/derived-control globals:")
 for k,v in f4.items():print(" ",k,v)
 gates["SG3_two_base_controls_bound"]=set(a3)==set(CONTROLS)
 gates["SG4_two_base_controls_bound"]=set(a4)==set(CONTROLS)
 gates["SG4_reference_values_match_SG3"]=(a4["CO2_MASS_RATE_TONNES_DAY"]["value"]==a3["CO2_MASS_RATE_TONNES_DAY"]["value"]==500.0 and a4["PRODUCER_BHP_PSI"]["value"]==a3["PRODUCER_BHP_PSI"]["value"]==2000.0)
 gates["construct_expected_well_rates_consumes_control_chain"]="construct_expected_well_rates" in f4
 # Determine exact semantic patch lines for both modules, preserving newline style.
 def patch(text,rate,bhp):
  lines=text.splitlines(keepends=True);changed=[]
  for idx,line in enumerate(lines):
   for name,old,new in (("PRODUCER_BHP_PSI","2000.0",f"{bhp:.1f}"),("CO2_MASS_RATE_TONNES_DAY","500.0",f"{rate:.1f}")):
    m=re.match(rf"^({name}\s*=\s*){re.escape(old)}(\s*(?:#.*)?)(\r?\n)?$",line)
    if m:
     lines[idx]=m.group(1)+new+m.group(2)+(m.group(3) or "");changed.append(idx+1)
  return "".join(lines),changed
 _,c3=patch(t3,350,1800);_,c4=patch(t4,350,1800)
 print("\nAuthorized semantic patch lines")
 print("  SG3:",c3);print("  SG4:",c4)
 gates["SG3_exact_two_patch_lines"]=c3==[122,132]
 gates["SG4_exact_two_patch_lines"]=len(c4)==2 and set(c4)=={a4["CO2_MASS_RATE_TONNES_DAY"]["line"],a4["PRODUCER_BHP_PSI"]["line"]}
 contract={"id":"V16D_SG3_SG4_CROSSMODULE_CONTROL_ADAPTER_1.0",
 "controls":{"CO2_MASS_RATE_TONNES_DAY":[350.0,500.0,650.0],"PRODUCER_BHP_PSI":[1800.0,2000.0,2200.0]},
 "rule":"For every non-reference control execution, derive BOTH SG3 and SG4 source copies from their SHA-bound frozen sources and alter only each module's exact two base-control assignment lines. Derived rate/BHP quantities remain source-computed.",
 "reference_rule":"500/2000 must reproduce unmodified SG3+SG4 path exactly on identical geology.",
 "validation_rule":"Conservation compares SG4 divergence against SG4 expected well source generated under the SAME rate/BHP controls used by SG3 pressure assembly.",
 "immutable":["frozen SG3","frozen SG4","SG2","matrix assembly","pressure solve","gravity","fluid properties","well geometry/completions","well-index algebra","flux reconstruction equations","conservation thresholds"],
 "prohibited":["patch derived quantities directly","relax conservation gates","use locked geology0029 during pilot","execute 36-case batch before R5 pilot passes"]}
 cp=O/"V16D24C_R4_CrossModule_Control_Adapter_Contract.json";cp.write_text(json.dumps({"contract":contract,"SG3_assignments":a3,"SG4_assignments":a4,"SG4_consumers":f4,"gates":gates},indent=2))
 ok=all(gates.values())
 status="V16D_SG3_SG4_CROSSMODULE_CONTROL_ADAPTER_1_0_FROZEN_MATCHED_CONTROL_R5_PILOT_AUTHORIZED" if ok else "V16D_D24C_R4_BLOCKED"
 nxt="V16D-24C-R5 — Re-run geology0026 350/1800 TRAIN pilot with matched SG3+SG4 source-preserving controls"
 sp=O/"PAD_Stream_V16D24C_R4_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-24C-R4","status":status,"contract_sha256":sha(cp),"gates":gates,"next_milestone":nxt},indent=2))
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()

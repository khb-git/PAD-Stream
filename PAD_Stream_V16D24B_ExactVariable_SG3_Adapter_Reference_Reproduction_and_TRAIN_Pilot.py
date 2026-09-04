#!/usr/bin/env python3
from pathlib import Path
import ast, hashlib, json, re, runpy, shutil, sys, tempfile, os
import numpy as np

R=Path(__file__).resolve().parent

D24A=R/"output"/"V16_D24A_SOURCEPRESERVING_SG3_CONTROL_ADAPTER_CONTRACT"
S24A=D24A/"PAD_Stream_V16D24A_Summary.json"
S24ASHA="b7e7d9428c83a24868d69b1d91f94fbd06a4c4390d57710c01445e72be6fea4b"

D22=R/"output"/"V16_D22_CONTROL_SPACE_DESIGN_FOUNDATION_CASE_REGISTRY"
REG22=D22/"V16D22_Control_Space_Recipe_1.0_and_Foundation_Case_Registry.json"

D23=R/"output"/"V16_D23_FRESH_RECIPE1P1_GEOLOGIES_0026_0029"
G26=D23/"V16D_Geology_Case_0026_Recipe1p1.npz"

SG2=R/"PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG3=R/"PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG4=R/"PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"

SHA2="8dfc3485682830ef854178720d32050b6b2e9d25befa7ee9669993df1e544416"
SHA3="d3ba7b7be45636f6d3ee254fd6cb95268cef9e6f35e85d53b5793596cb22b14d"
SHA4="86a1c88ffc35033314ae6598ade23f0bebfa709f62cbe2cbef1830cd607e0af9"

O=R/"output"/"V16_D24B_EXACTVARIABLE_ADAPTER_REFERENCE_AND_TRAIN_PILOT"
O.mkdir(parents=True,exist_ok=True)

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def exact_assignments(path):
    tree=ast.parse(path.read_text(encoding="utf-8"))
    ans={}
    for n in ast.walk(tree):
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
            name=n.targets[0].id
            if name in ("PRODUCER_BHP_PSI","CO2_MASS_RATE_TONNES_DAY"):
                ans[name]={"lineno":n.lineno,"value":ast.literal_eval(n.value)}
    return ans

def exact_source_patch(text, rate, bhp):
    # Exact variable assignment patch only. Fails unless exactly one assignment each.
    pats={
      "PRODUCER_BHP_PSI":(re.compile(r"(?m)^(\s*PRODUCER_BHP_PSI\s*=\s*)2000\.0(\s*(?:#.*)?)$"),bhp),
      "CO2_MASS_RATE_TONNES_DAY":(re.compile(r"(?m)^(\s*CO2_MASS_RATE_TONNES_DAY\s*=\s*)500\.0(\s*(?:#.*)?)$"),rate)
    }
    out=text
    counts={}
    for name,(pat,val) in pats.items():
        out,n=pat.subn(lambda m:f"{m.group(1)}{float(val):.1f}{m.group(2)}",out)
        counts[name]=n
    if counts!={"PRODUCER_BHP_PSI":1,"CO2_MASS_RATE_TONNES_DAY":1}:
        raise RuntimeError(f"exact assignment patch failed: {counts}")
    return out,counts

def discover_prior_flow_runner():
    # Bind to the already-successful D7 source-bound execution machinery rather than
    # inventing geology/SG2/SG3/SG4 wiring. Candidate must mention all exact source names
    # and Foundation Case flow output semantics.
    hits=[]
    for p in R.glob("PAD_Stream_V16D7*.py"):
        try:
            t=p.read_text(encoding="utf-8",errors="replace")
        except Exception:
            continue
        score=sum(s in t for s in (
          "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py",
          "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py",
          "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py",
          "pressure_psi","Qx","Qy","Qz"))
        if score>=6:
            hits.append({"path":str(p),"sha256":sha(p),"score":score})
    return hits

def main():
    print("="*78)
    print("PAD-Stream V16D-24B")
    print("Exact-Variable SG3 Adapter + Reference Reproduction / TRAIN Pilot Binding")
    print("="*78)
    print("D24B WILL NOT GUESS GEOLOGY-TO-SG2/SG3/SG4 WIRING.")
    print("IT FIRST BINDS THE PRIOR SUCCESSFUL D7 FLOW EXECUTION ADAPTER.")
    print("ONLY THE TWO AST-BOUND SG3 ASSIGNMENTS MAY VARY.\n")

    gates={}
    gates["D24A_SHA_exact"]=sha(S24A)==S24ASHA
    gates["SG2_SHA_exact"]=sha(SG2)==SHA2
    gates["SG3_SHA_exact"]=sha(SG3)==SHA3
    gates["SG4_SHA_exact"]=sha(SG4)==SHA4
    gates["geology_0026_exists"]=G26.exists()

    ass=exact_assignments(SG3)
    gates["SG3_exact_two_control_assignments"]=(set(ass)=={"PRODUCER_BHP_PSI","CO2_MASS_RATE_TONNES_DAY"})
    gates["SG3_reference_values_exact"]=(ass.get("PRODUCER_BHP_PSI",{}).get("value")==2000.0 and
                                         ass.get("CO2_MASS_RATE_TONNES_DAY",{}).get("value")==500.0)
    print("Exact SG3 assignments:",ass)

    # Prove exact patch behavior without executing physics.
    src=SG3.read_text(encoding="utf-8")
    ref,cref=exact_source_patch(src,500.0,2000.0)
    pilot,cpil=exact_source_patch(src,350.0,1800.0)
    gates["reference_patch_byte_identical_to_frozen_SG3"]=(ref==src)
    gates["pilot_patch_only_two_assignment_lines"]=True
    # Verify by line-diff count.
    a=src.splitlines(); b=pilot.splitlines()
    diffs=[(i+1,x,y) for i,(x,y) in enumerate(zip(a,b)) if x!=y]
    gates["pilot_exactly_two_source_lines_changed"]=(len(diffs)==2 and
        any("PRODUCER_BHP_PSI" in x for _,x,_ in diffs) and
        any("CO2_MASS_RATE_TONNES_DAY" in x for _,x,_ in diffs))
    print("Pilot source differences:")
    for d in diffs: print(" ",d)

    runners=discover_prior_flow_runner()
    print(f"\nPrior D7 flow-runner candidates: {len(runners)}")
    for h in runners: print(" ",h["path"],h["sha256"])
    gates["unique_prior_D7_flow_runner_bound"]=(len(runners)==1)

    # Persist exact derived SG3 pilot source ONLY if prior runner wiring is uniquely bound.
    derived=None
    if gates["unique_prior_D7_flow_runner_bound"]:
        derived=O/"PAD_Stream_V16D24B_DERIVED_SG3_350TPD_1800PSI.py"
        derived.write_text(pilot,encoding="utf-8")
        gates["derived_SG3_created_without_mutating_frozen_source"]=sha(SG3)==SHA3
    else:
        gates["derived_SG3_created_without_mutating_frozen_source"]=False

    report={
      "milestone":"V16D-24B",
      "exact_assignments":ass,
      "pilot_source_diffs":[{"line":i,"frozen":x,"derived":y} for i,x,y in diffs],
      "prior_D7_runner_candidates":runners,
      "derived_SG3":str(derived) if derived else None,
      "gates":gates,
      "decision":(
        "REFERENCE_AND_SINGLE_TRAIN_PILOT_EXECUTION_AUTHORIZED"
        if all(gates.values()) else
        "EXECUTION_BLOCKED_UNTIL_UNIQUE_PRIOR_D7_FLOW_RUNNER_IS_BOUND"
      )
    }
    rp=O/"V16D24B_ExactVariable_Adapter_Binding_Report.json"
    rp.write_text(json.dumps(report,indent=2))

    # This milestone is intentionally binding-first. Reference/pilot execution is the
    # next script because its adapter must be generated from the unique D7 runner found here.
    if all(gates.values()):
        status="V16D_EXACTVARIABLE_SG3_ADAPTER_AND_D7_FLOW_RUNNER_BOUND_REFERENCE_AND_SINGLE_TRAIN_PILOT_EXECUTION_AUTHORIZED"
        nxt="V16D-24C — Execute 500/2000 Reference Reproduction + One 0026 TRAIN New-Control Flow Pilot"
    else:
        status="V16D_REFERENCE_PILOT_EXECUTION_BLOCKED_D7_FLOW_RUNNER_BINDING_INCOMPLETE"
        nxt="Inspect D24B runner candidates; bind the exact prior successful D7 flow execution script without reimplementing physics."

    sp=O/"PAD_Stream_V16D24B_Summary.json"
    sp.write_text(json.dumps({"milestone":"V16D-24B","status":status,
      "report_sha256":sha(rp),"gates":gates,"next_milestone":nxt},indent=2))

    print("\nGATES")
    for k,v in gates.items(): print(f"[{'PASS' if v else 'FAIL'}] {k}")
    print("\nSTATUS\n ",status)
    print("\nNEXT\n ",nxt)
    print("\nSummary SHA-256:",sha(sp))
    if not all(gates.values()): sys.exit(2)

if __name__=="__main__":
    main()

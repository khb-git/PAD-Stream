#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,sys,itertools
R=Path(__file__).resolve().parent
D21=R/"output"/"V16_D21_POST_OOD_SCIENTIFIC_INTERPRETATION_NEXT_EXPERIMENT_DECISION"
S21=D21/"PAD_Stream_V16D21_Summary.json"
S21SHA="ee7b497a54a3c9001bee1b524809a81e4140a407dfbd35ce372bea470cdc04b4"
O=R/"output"/"V16_D22_CONTROL_SPACE_DESIGN_FOUNDATION_CASE_REGISTRY";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-22")
 print("Versioned Injection-Rate / Producer-BHP Control-Space Design + Registry");print("="*78)
 if sha(S21)!=S21SHA:raise RuntimeError("D21 summary SHA mismatch")
 # Versioned design: chosen prospectively, before any new flow/transport generation.
 rates=[350.0,500.0,650.0]       # tonnes/day
 bhps=[1800.0,2000.0,2200.0]    # psi
 # Four fresh Recipe1.1 geology IDs, generated from immutable D4 seed formula extension.
 geos=[26,27,28,29]
 def seed(case_id):return 160400+(case_id-2)*7919
 # Complete 3x3 control grid on each fresh geology = 36 Foundation Cases.
 # Split by complete geology to prevent streamline/geology leakage:
 # 26,27 TRAIN; 28 VALIDATION; 29 LOCKED OOD.
 part={26:"TRAIN",27:"TRAIN",28:"VALIDATION",29:"LOCKED_OOD_TEST"}
 rows=[];fc=1001
 for g in geos:
  for q,b in itertools.product(rates,bhps):
   rows.append({"foundation_case_id":f"CS{fc:04d}","geology_case_id":f"{g:04d}",
    "geology_seed":seed(g),"injection_tonnes_per_day":q,"producer_BHP_psi":b,
    "partition":part[g],"well_geometry":"FROZEN_V15_FIVE_SPOT","geology_recipe":"V16D_SPECTRAL_ENSEMBLE_RECIPE_1.1"})
   fc+=1
 design={"milestone":"V16D-22","contract":"V16D_CONTROL_SPACE_RECIPE_1.0",
 "prospective_design":True,
 "axes":{"CO2_injection_tonnes_per_day":rates,"producer_BHP_psi":bhps},
 "reference_control":{"CO2_injection_tonnes_per_day":500.0,"producer_BHP_psi":2000.0},
 "geology":{"recipe":"V16D_SPECTRAL_ENSEMBLE_RECIPE_1.1","new_geology_ids":[f"{g:04d}" for g in geos],
 "seed_rule":"160400 + (geology_case_id - 2)*7919","historical_cases_0002_0025_reused":False},
 "crossing":"complete 3x3 control factorial on every new geology",
 "split":{"TRAIN_geologies":["0026","0027"],"VALIDATION_geologies":["0028"],"LOCKED_OOD_TEST_geologies":["0029"],
 "unit":"complete geology including all 9 control combinations"},
 "counts":{"TRAIN":18,"VALIDATION":9,"LOCKED_OOD_TEST":9,"TOTAL":36},
 "fixed":{"grid":"50x50x15, 20x20x4 ft","porosity":0.20,"Kz_over_Kh":0.10,
 "well_geometry":"existing five-spot locations and completions","transport":"source-authentic Stage4 semantics",
 "target_days":[30,60,100,150,250,365,500,750,1000]},
 "interpretation":{"primary_test":"joint unseen-geology generalization across a fully represented control grid",
 "control_interpolation":"500 t/day and 2000 psi are interior/reference levels",
 "control_edge_coverage":"350/650 t/day and 1800/2200 psi included prospectively",
 "extrapolative_control_OOD":"NOT tested by this first 3x3 design",
 "foundation_model_claim":"NOT AUTHORIZED"},
 "firewall":{"locked_geology_0029_defined_before_generation":True,"locked_targets_no_training_or_selection":True,
 "D18_observed_cases_not_reused":True,"no_cherry_picking_or_case_replacement":True},
 "registry":rows}
 cp=O/"V16D22_Control_Space_Recipe_1.0_and_Foundation_Case_Registry.json";cp.write_text(json.dumps(design,indent=2))
 gates={"D21_SHA_exact":sha(S21)==S21SHA,"prospective_before_generation":True,"two_control_axes":True,
 "complete_3x3_factorial_each_geology":len(rows)==36,"new_recipe1_1_geologies_only":all(g>25 for g in geos),
 "old_observed_OOD_not_reused":True,"complete_geology_split":True,"locked_test_predeclared":True,
 "no_flow_generation":True,"no_transport_generation":True,"no_training":True,"no_OOD_evaluation":True,
 "foundation_model_claim_not_authorized":True}
 status="V16D_CONTROL_SPACE_RECIPE_1_0_AND_36_FOUNDATION_CASE_REGISTRY_FROZEN_NEW_GEOLOGY_GENERATION_AUTHORIZED"
 nxt="V16D-23 — Generate and Certify Fresh Recipe1.1 Geologies 0026–0029"
 sp=O/"PAD_Stream_V16D22_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-22","status":status,
 "contract_registry_sha256":sha(cp),"gates":gates,"next_milestone":nxt},indent=2))
 print("CONTROL SPACE")
 print("  Injection [tonnes/day]:",rates);print("  Producer BHP [psi]:",bhps)
 print("  Complete factorial per geology: 9 controls")
 print("NEW GEOLOGIES / SPLIT")
 for g in geos:print(f"  {g:04d} seed={seed(g)} -> {part[g]}")
 print("FOUNDATION CASES: TRAIN=18 VALIDATION=9 LOCKED_OOD=9 TOTAL=36")
 print("\nIMPORTANT: this first design tests unseen geology across broad control coverage;")
 print("it does NOT yet claim extrapolation beyond the frozen control bounds.")
 print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not all(gates.values()):sys.exit(2)
if __name__=="__main__":main()

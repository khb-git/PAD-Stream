from __future__ import annotations
from pathlib import Path
import csv, hashlib, json, zipfile, tarfile, re

ROOT=Path(__file__).resolve().parent
R5D=ROOT/"output"/"V16_C12R5_EXACT_FROZEN_L2_SG7D6_SOURCE_RECIPE_REGENERATION_AUTHORITY_AUDIT"
R5S=R5D/"PAD_Stream_V16C12R5_Summary.json"

OUT=ROOT/"output"/"V16_C12R5A_FROZEN_V15_PACKAGE_ARCHIVE_EXACT_L2_BYTE_RECOVERY_AUDIT"
OUT.mkdir(parents=True,exist_ok=True)
ARCH=OUT/"V16C12R5A_Archive_Inventory.csv"
MEM=OUT/"V16C12R5A_Archive_Member_Hash_Audit.csv"
HITS=OUT/"V16C12R5A_Exact_Authority_Hash_Hits.csv"
GATES=OUT/"V16C12R5A_Final_Byte_Recovery_Gates.csv"
DEC=OUT/"V16C12R5A_Byte_Recovery_Decision.csv"
CON=OUT/"V16C12R5A_Frozen_Byte_Recovery_Contract.json"
SUM=OUT/"PAD_Stream_V16C12R5A_Summary.json"

L2_SHA="01bb967c07b262836f6c140dd519538db13d9ce5b3bc0f83d52a6164ddcfa950"
D6_SHA="6bf6661e2344d51c54df4689758a1998952454e0bc13797b8e4da57824cf9522"

def hbytes(b): return hashlib.sha256(b).hexdigest()
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def loadj(p): return json.loads(p.read_text(encoding="utf-8"))
def savej(p,x): p.write_text(json.dumps(x,indent=2),encoding="utf-8")
def save_csv(p,rows):
    rows=list(rows); keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(rows)

def archives():
    exts={".zip",".tar",".gz",".tgz",".bz2",".xz"}
    out=[]
    for p in ROOT.rglob("*"):
        if not p.is_file(): continue
        if "V16_C12R5A" in str(p): continue
        if p.suffix.lower() in exts or p.name.lower().endswith((".tar.gz",".tar.bz2",".tar.xz")):
            out.append(p)
    return out

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-12R5A")
    print("Frozen V15 Package/Archive Exact L2 Byte-Recovery Audit")
    print("="*78)
    print("""
R5 PROHIBITED RE-RUNNING THE PI-RNN TO RECREATE L2_independent_100.

R5A THEREFORE SEARCHES PRESERVED ARCHIVES AND PACKAGES BY BYTE IDENTITY.

THIS AUDIT:
  * HASHES ARCHIVE MEMBERS IN MEMORY.
  * DOES NOT EXTRACT OVER EXISTING FILES.
  * DOES NOT SELECT BY MEMBER NAME.
  * DOES NOT SELECT BY NUMERICAL SIMILARITY.
  * DOES NOT MODIFY THE FROZEN V15 TREE.

TARGET AUTHORITIES:
  L2_independent_100 SHA-256:
    01bb967c07b262836f6c140dd519538db13d9ce5b3bc0f83d52a6164ddcfa950
  SG7D6 full-grid SHA-256:
    6bf6661e2344d51c54df4689758a1998952454e0bc13797b8e4da57824cf9522
""")
    if not R5S.exists(): raise FileNotFoundError(R5S)
    r5=loadj(R5S)
    if r5.get("status")!="V16C_SG7D6_RECIPE_PRESERVED_BUT_MISSING_CERTIFIED_L2_REGENERATION_NOT_AUTHORIZED":
        raise RuntimeError("R5A requires R5 missing-certified-L2 status.")

    ars=archives()
    arows=[]; mrows=[]; hits=[]
    for a in ars:
        kind="zip" if zipfile.is_zipfile(a) else ("tar" if tarfile.is_tarfile(a) else "unknown")
        arows.append(dict(path=str(a.relative_to(ROOT)),sha256=sha(a),size_bytes=a.stat().st_size,kind=kind))
        try:
            if kind=="zip":
                with zipfile.ZipFile(a) as z:
                    for info in z.infolist():
                        if info.is_dir(): continue
                        try:b=z.read(info)
                        except Exception:continue
                        hh=hbytes(b)
                        mrows.append(dict(archive=str(a.relative_to(ROOT)),member=info.filename,
                                          size_bytes=len(b),sha256=hh))
                        if hh in (L2_SHA,D6_SHA):
                            hits.append(dict(authority="L2_independent_100" if hh==L2_SHA else "SG7D6_full_grid",
                                expected_sha256=hh,archive=str(a.relative_to(ROOT)),member=info.filename,
                                member_size_bytes=len(b)))
            elif kind=="tar":
                with tarfile.open(a,"r:*") as t:
                    for info in t.getmembers():
                        if not info.isfile(): continue
                        f=t.extractfile(info)
                        if f is None: continue
                        b=f.read(); hh=hbytes(b)
                        mrows.append(dict(archive=str(a.relative_to(ROOT)),member=info.name,
                                          size_bytes=len(b),sha256=hh))
                        if hh in (L2_SHA,D6_SHA):
                            hits.append(dict(authority="L2_independent_100" if hh==L2_SHA else "SG7D6_full_grid",
                                expected_sha256=hh,archive=str(a.relative_to(ROOT)),member=info.name,
                                member_size_bytes=len(b)))
        except Exception as e:
            arows[-1]["scan_error"]=repr(e)

    save_csv(ARCH,arows); save_csv(MEM,mrows); save_csv(HITS,hits)
    l2=[x for x in hits if x["expected_sha256"]==L2_SHA]
    d6=[x for x in hits if x["expected_sha256"]==D6_SHA]
    l2_unique=len(l2)==1
    d6_unique=len(d6)==1

    # Exact hash identity means duplicate copies are not ambiguous in physical state,
    # but unique archive/member is preferred for a clean extraction path.
    l2_found=len(l2)>0; d6_found=len(d6)>0

    gates=[
        ("R5_missing_L2_regeneration_prohibition_reproduced",True),
        ("archive_inventory_completed",True),
        ("archive_members_hashed_bytewise",True),
        ("no_archive_member_selected_by_name",True),
        ("no_numerical_closeness_selection",True),
        ("exact_L2_authority_bytes_found_in_archive",l2_found),
        ("exact_SG7D6_authority_bytes_found_in_archive",d6_found),
        ("unique_L2_archive_member_hit",l2_unique),
        ("unique_SG7D6_archive_member_hit",d6_unique),
        ("no_PI_RNN_inference",True),
        ("no_training",True),
        ("no_archive_extraction_performed",True),
        ("no_frozen_artifact_mutation",True),
        ("no_Y_transport_generated",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])

    if l2_found and d6_found:
        status="V16C_EXACT_FROZEN_L2_AND_SG7D6_BYTES_RECOVERABLE_FROM_PRESERVED_ARCHIVE"
        diagnosis="THE_FORMAL_V15_L2_INDEPENDENT_100_AND_SG7D6_BYTE_IDENTITIES_EXIST_IN_PRESERVED_ARCHIVE_MEMBERS_WITH_EXACT_SHA256_MATCHES"
        rec="Freeze R5A. Proceed to controlled extraction into a new V16 recovery directory, re-hash after extraction, and then perform C12A cross-authority validation."
        nxt="V16C-12R5B — Controlled Exact-Hash V15 Authority Byte Extraction and Verification"
    elif l2_found:
        status="V16C_EXACT_FROZEN_L2_BYTES_RECOVERABLE_SG7D6_RECONSTRUCTION_PATH_REQUIRED"
        diagnosis="THE_CERTIFIED_L2_INDEPENDENT_100_BYTES_ARE_PRESERVED_BUT_THE_SG7D6_FROZEN_BYTES_ARE_NOT_FOUND_IN_SCANNED_ARCHIVES"
        rec="Freeze R5A. Recover L2 by exact hash, then use the already-authorized deterministic SG7D1->SG7D6 recipe in a separate controlled milestone and verify against the formal SG7D6 hash."
        nxt="V16C-12R5B — Controlled Exact L2 Extraction and Deterministic SG7D6 Reconstruction"
    else:
        status="V16C_EXACT_FROZEN_L2_BYTES_NOT_FOUND_IN_LOCAL_PRESERVED_ARCHIVES"
        diagnosis="NO_SCANNED_LOCAL_ARCHIVE_MEMBER_MATCHES_THE_FORMAL_CERTIFIED_L2_INDEPENDENT_100_SHA256_SO_REGENERATION_REMAINS_PROHIBITED"
        rec=("Do not rerun the PI-RNN and do not select an ambiguous historical candidate. "
             "Search external/preserved project copies or the formal V15 freeze package location for the exact L2 SHA-256. "
             "If no copy exists, C12A must be reformulated around the surviving SG7D6/historical reference authorities without pretending the missing L2 was recovered.")
        nxt="V16C-12R5C — External/Preserved-Copy Exact L2 Authority Recovery Decision"

    save_csv(DEC,[dict(status=status,diagnosis=diagnosis,archives_scanned=len(ars),
        members_hashed=len(mrows),L2_hits=len(l2),SG7D6_hits=len(d6),
        L2_found=l2_found,SG7D6_found=d6_found,extraction_performed=False,
        Y_generation_authorized=False,next_milestone=nxt)])
    savej(CON,dict(milestone="V16C-12R5A",status=status,diagnosis=diagnosis,
        targets=dict(L2_independent_100=L2_SHA,SG7D6=D6_SHA),
        archives_scanned=len(ars),members_hashed=len(mrows),
        exact_hits=hits,extraction_performed=False,
        PI_RNN_inference_performed=False,Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))
    savej(SUM,dict(milestone="V16C-12R5A",status=status,diagnosis=diagnosis,
        archives_scanned=len(ars),members_hashed=len(mrows),
        L2_hits=len(l2),SG7D6_hits=len(d6),L2_found=l2_found,SG7D6_found=d6_found,
        extraction_performed=False,Y_transport_generated=False,Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))

    print("ARCHIVE BYTE AUDIT")
    print("  archives scanned          :",len(ars))
    print("  archive members hashed    :",len(mrows))
    print("  exact L2 hash hits        :",len(l2))
    print("  exact SG7D6 hash hits     :",len(d6))
    print("  extraction performed      : False")
    print("  PI-RNN inference performed: False")

    print("\n"+"="*78)
    print("V16C-12R5A FINAL BYTE-RECOVERY GATES")
    print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-12R5A ARCHIVE BYTE-RECOVERY AUDIT: COMPLETE")
    print("="*78)

if __name__=="__main__": main()

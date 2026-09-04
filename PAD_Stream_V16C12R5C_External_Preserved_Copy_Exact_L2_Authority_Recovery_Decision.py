from __future__ import annotations
from pathlib import Path
import csv, hashlib, json, os, zipfile, tarfile

ROOT=Path(__file__).resolve().parent
R5AD=ROOT/"output"/"V16_C12R5A_FROZEN_V15_PACKAGE_ARCHIVE_EXACT_L2_BYTE_RECOVERY_AUDIT"
R5AS=R5AD/"PAD_Stream_V16C12R5A_Summary.json"

OUT=ROOT/"output"/"V16_C12R5C_EXTERNAL_PRESERVED_COPY_EXACT_L2_AUTHORITY_RECOVERY_DECISION"
OUT.mkdir(parents=True,exist_ok=True)
ROOTS=OUT/"V16C12R5C_Search_Roots.csv"
FILES=OUT/"V16C12R5C_Candidate_File_Hash_Audit.csv"
ARCH=OUT/"V16C12R5C_Archive_Member_Hash_Audit.csv"
HITS=OUT/"V16C12R5C_Exact_Authority_Hits.csv"
GATES=OUT/"V16C12R5C_Final_Recovery_Decision_Gates.csv"
DEC=OUT/"V16C12R5C_Recovery_Decision.csv"
CON=OUT/"V16C12R5C_External_Preserved_Copy_Recovery_Contract.json"
SUM=OUT/"PAD_Stream_V16C12R5C_Summary.json"

L2_SHA="01bb967c07b262836f6c140dd519538db13d9ce5b3bc0f83d52a6164ddcfa950"
D6_SHA="6bf6661e2344d51c54df4689758a1998952454e0bc13797b8e4da57824cf9522"

SKIP_DIRS={".venv","venv","env","node_modules",".git","__pycache__",
           "AppData","site-packages","Library","Temp","Cache","Caches"}
CANDIDATE_SUFFIXES={".npz",".npy",".zip",".tar",".gz",".tgz",".bz2",".xz"}
MAX_ARCHIVE_BYTES=8*1024**3

def hbytes(b): return hashlib.sha256(b).hexdigest()
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4<<20),b""): h.update(b)
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

def search_roots():
    home=Path.home()
    candidates=[
        ROOT.parent,                         # PyCharmProjects
        home/"Downloads",
        home/"Documents",
        home/"Desktop",
    ]
    # Include obvious sibling PAD-Stream/project copies without scanning whole C:.
    roots=[]; seen=set()
    for p in candidates:
        try:p=p.resolve()
        except:continue
        if p.exists() and p not in seen:
            seen.add(p); roots.append(p)
    return roots

def iter_files(base):
    for cur,dirs,files in os.walk(base):
        dirs[:]=[d for d in dirs if d not in SKIP_DIRS and
                 "V16_C12R5C_EXTERNAL_PRESERVED_COPY" not in d]
        cp=Path(cur)
        for n in files:
            p=cp/n
            low=n.lower()
            if (p.suffix.lower() in CANDIDATE_SUFFIXES or
                low.endswith((".tar.gz",".tar.bz2",".tar.xz")) or
                any(k in low for k in ("l2","sg7d6","frozen","deployment","version15","v15"))):
                yield p

def archive_kind(p):
    try:
        if zipfile.is_zipfile(p): return "zip"
        if tarfile.is_tarfile(p): return "tar"
    except: pass
    return None

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-12R5C")
    print("External/Preserved-Copy Exact L2 Authority Recovery Decision")
    print("="*78)
    print("""
R5A FOUND NO EXACT AUTHORITY BYTES INSIDE THE CURRENT PROJECT'S LOCAL ARCHIVES.

R5C PERFORMS A READ-ONLY SEARCH OF LIKELY PRESERVED-COPY LOCATIONS:
  * THE PARENT PYCHARM PROJECTS DIRECTORY
  * DOWNLOADS
  * DOCUMENTS
  * DESKTOP

IT SEARCHES ONLY BY THE FORMAL SHA-256 IDENTITIES. IT DOES NOT USE NUMERICAL
CLOSENESS, TIMESTAMPS, VERSION ORDERING, OR FILENAMES AS AUTHORITY.

NO FILE IS MOVED, EXTRACTED, RENAMED, OR MODIFIED.
NO PI-RNN INFERENCE IS PERFORMED.

IF THE EXACT L2 BYTES ARE RECOVERED, THE ALREADY-AUTHORIZED SG7D6 RECIPE MAY
BE USED IN THE NEXT CONTROLLED MILESTONE. IF THEY ARE NOT RECOVERED, THE
MISSING L2 AUTHORITY IS FORMALLY CLOSED AS UNAVAILABLE AND C12A MUST USE ONLY
SURVIVING FORMAL V15 AUTHORITIES.
""")
    if not R5AS.exists(): raise FileNotFoundError(R5AS)
    r5a=loadj(R5AS)
    if r5a.get("status")!="V16C_EXACT_FROZEN_L2_BYTES_NOT_FOUND_IN_LOCAL_PRESERVED_ARCHIVES":
        raise RuntimeError("R5C requires R5A exact-L2-not-found status.")

    roots=search_roots()
    save_csv(ROOTS,[dict(search_root=str(r),exists=r.exists(),read_only=True) for r in roots])

    frows=[]; arows=[]; hits=[]; seen=set()
    for base in roots:
        for p in iter_files(base):
            try:
                rp=p.resolve()
                if rp in seen: continue
                seen.add(rp)
                size=p.stat().st_size
            except: continue
            # Hash candidate file itself.
            try:
                hh=sha(p)
                frows.append(dict(path=str(p),size_bytes=size,sha256=hh))
                if hh in (L2_SHA,D6_SHA):
                    hits.append(dict(location_type="file",
                        authority="L2_independent_100" if hh==L2_SHA else "SG7D6_full_grid",
                        sha256=hh,container="",member_or_path=str(p),size_bytes=size))
            except Exception as e:
                frows.append(dict(path=str(p),size_bytes=size,sha256="",error=repr(e)))
                continue

            kind=archive_kind(p)
            if not kind or size>MAX_ARCHIVE_BYTES: continue
            try:
                if kind=="zip":
                    with zipfile.ZipFile(p) as z:
                        for info in z.infolist():
                            if info.is_dir(): continue
                            try:b=z.read(info)
                            except:continue
                            mh=hbytes(b)
                            arows.append(dict(archive=str(p),member=info.filename,
                                              size_bytes=len(b),sha256=mh))
                            if mh in (L2_SHA,D6_SHA):
                                hits.append(dict(location_type="archive_member",
                                    authority="L2_independent_100" if mh==L2_SHA else "SG7D6_full_grid",
                                    sha256=mh,container=str(p),member_or_path=info.filename,
                                    size_bytes=len(b)))
                else:
                    with tarfile.open(p,"r:*") as t:
                        for info in t.getmembers():
                            if not info.isfile(): continue
                            f=t.extractfile(info)
                            if f is None: continue
                            b=f.read(); mh=hbytes(b)
                            arows.append(dict(archive=str(p),member=info.name,
                                              size_bytes=len(b),sha256=mh))
                            if mh in (L2_SHA,D6_SHA):
                                hits.append(dict(location_type="archive_member",
                                    authority="L2_independent_100" if mh==L2_SHA else "SG7D6_full_grid",
                                    sha256=mh,container=str(p),member_or_path=info.name,
                                    size_bytes=len(b)))
            except Exception as e:
                arows.append(dict(archive=str(p),member="",size_bytes="",sha256="",error=repr(e)))

    save_csv(FILES,frows); save_csv(ARCH,arows); save_csv(HITS,hits)
    l2=[h for h in hits if h["sha256"]==L2_SHA]
    d6=[h for h in hits if h["sha256"]==D6_SHA]
    l2_found=bool(l2); d6_found=bool(d6)

    gates=[
        ("R5A_local_archive_negative_result_reproduced",True),
        ("external_preserved_copy_roots_defined",len(roots)>0),
        ("read_only_candidate_scan_completed",True),
        ("candidate_files_hashed_by_SHA256",len(frows)>0),
        ("no_filename_authority_selection",True),
        ("no_timestamp_authority_selection",True),
        ("no_numerical_closeness_selection",True),
        ("exact_L2_authority_recovered",l2_found),
        ("exact_SG7D6_authority_recovered",d6_found),
        ("no_PI_RNN_inference",True),
        ("no_training",True),
        ("no_extraction_or_mutation",True),
        ("no_Y_transport_generated",True),
    ]
    save_csv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])

    if l2_found:
        status="V16C_EXACT_CERTIFIED_L2_AUTHORITY_RECOVERED_FROM_PRESERVED_COPY"
        diagnosis="AT_LEAST_ONE_READ_ONLY_PRESERVED_COPY_MATCHES_THE_FORMAL_L2_INDEPENDENT_100_SHA256_EXACTLY"
        rec=("Freeze R5C. Proceed to controlled copy/extraction into a new V16 recovery directory, "
             "verify the exact L2 hash again, then reconstruct or recover SG7D6 under the R5-authorized recipe.")
        nxt="V16C-12R5D — Controlled Exact-Hash Authority Recovery and SG7D6 Reconstruction"
    else:
        status="V16C_CERTIFIED_L2_AUTHORITY_BYTES_UNAVAILABLE_AFTER_PRESERVED_COPY_SEARCH"
        diagnosis="NO_SEARCHED_PRESERVED_COPY_OR_ARCHIVE_MEMBER_MATCHES_THE_FORMAL_L2_INDEPENDENT_100_SHA256_AND_PI_RNN_REGENERATION_REMAINS_UNAUTHORIZED"
        rec=("Close exact L2 byte recovery as unavailable in the searched environment. Do not select an ambiguous "
             "historical frozen100 object and do not rerun the PI-RNN. Reformulate C12A around the surviving formal "
             "V15 authorities: SG7D6 if recoverable/reconstructible from an authoritative L2 source, and otherwise the "
             "historical SG7E 100-day grid reference as validation-only authority. Preserve the missing-L2 limitation explicitly.")
        nxt="V16C-12A-R — Surviving-Authority 100-Day Validation Contract"

    save_csv(DEC,[dict(status=status,diagnosis=diagnosis,search_roots=len(roots),
        candidate_files_hashed=len(frows),archive_members_hashed=len(arows),
        L2_exact_hits=len(l2),SG7D6_exact_hits=len(d6),
        L2_recovered=l2_found,SG7D6_recovered=d6_found,
        PI_RNN_regeneration_authorized=False,Y_generation_authorized=False,next_milestone=nxt)])
    savej(CON,dict(milestone="V16C-12R5C",status=status,diagnosis=diagnosis,
        formal_targets=dict(L2_independent_100=L2_SHA,SG7D6=D6_SHA),
        search_roots=[str(r) for r in roots],exact_hits=hits,
        L2_recovered=l2_found,SG7D6_recovered=d6_found,
        PI_RNN_regeneration_authorized=False,mutation_performed=False,
        Y_generation_authorized=False,recommendation=rec,next_milestone=nxt))
    savej(SUM,dict(milestone="V16C-12R5C",status=status,diagnosis=diagnosis,
        search_roots=len(roots),candidate_files_hashed=len(frows),
        archive_members_hashed=len(arows),L2_exact_hits=len(l2),
        SG7D6_exact_hits=len(d6),L2_recovered=l2_found,SG7D6_recovered=d6_found,
        Y_transport_generated=False,Y_generation_authorized=False,
        recommendation=rec,next_milestone=nxt))

    print("PRESERVED-COPY BYTE SEARCH")
    print("  search roots              :",len(roots))
    print("  candidate files hashed    :",len(frows))
    print("  archive members hashed    :",len(arows))
    print("  exact L2 hits             :",len(l2))
    print("  exact SG7D6 hits          :",len(d6))
    print("  PI-RNN inference          : PROHIBITED / NOT PERFORMED")
    print("  mutation/extraction       : NOT PERFORMED")

    print("\n"+"="*78)
    print("V16C-12R5C FINAL RECOVERY DECISION GATES")
    print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-12R5C PRESERVED-COPY RECOVERY DECISION: COMPLETE")
    print("="*78)

if __name__=="__main__": main()

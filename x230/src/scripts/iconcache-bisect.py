#!/usr/bin/env python3
import os, sys, shutil, subprocess, tempfile, pathlib

THEME = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
if not THEME or not THEME.is_dir():
    print("Usage: iconcache-bisect.py THEME_DIR", file=sys.stderr); sys.exit(2)

# Candidates: png/svg/xpm (skip dotdirs and anything already quarantined)
def list_candidates():
    exts = {'.png', '.svg', '.xpm'}
    for p in THEME.rglob('*'):
        if p.is_dir():
            parts = p.relative_to(THEME).parts
            if any(part.startswith('.') for part in parts):  # skip .git, .off, etc.
                continue
        if p.is_file() and p.suffix.lower() in exts:
            rel = p.relative_to(THEME)
            if any(part.startswith('.') for part in rel.parts):
                continue
            yield rel

def make_subset(subset):
    """Create a minimal temp theme containing only files from subset."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="iconbisect-"))
    # build minimal index.theme
    dirs = sorted({str(p.parent).replace('\\','/') for p in subset})
    with (tmp / "index.theme").open("w", encoding="utf-8") as f:
        f.write("[Icon Theme]\nName=tmp\nComment=tmp\nExample=folder\n")
        f.write("Directories=" + ",".join(dirs) + "\n")
        for d in dirs:
            f.write(f"\n[{d}]\nSize=48\nType=Scalable\nMinSize=1\nMaxSize=512\n")
    # copy files
    for rel in subset:
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(THEME / rel, dst)
    return tmp

def ok_cache(tmpdir):
    # Try gtk3 and gtk4 tools if available
    cmds = [
        ["gtk-update-icon-cache", "-f", "-i", str(tmpdir)],
        ["gtk4-update-icon-cache", "-f", "-i", str(tmpdir)],
    ]
    for cmd in cmds:
        try:
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if r.returncode == 0:
                return True
        except FileNotFoundError:
            continue
    return False

def find_one_offender(files):
    """Binary search for one offending file; return its relative path or None if OK."""
    # Quick pass: anything with spaces or uppercase (violates spec) – test those first
    suspicious = [f for f in files if (" " in f.name) or (f.stem != f.stem.lower())]
    for cand in suspicious:
        tmp = make_subset([cand])
        bad = not ok_cache(tmp)
        shutil.rmtree(tmp, ignore_errors=True)
        if bad:
            return cand

    # If whole set passes, nothing to find
    tmp = make_subset(files)
    whole_ok = ok_cache(tmp)
    shutil.rmtree(tmp, ignore_errors=True)
    if whole_ok:
        return None

    lo = 0; hi = len(files)
    idx = list(files)
    while hi - lo > 1:
        mid = (lo + hi) // 2
        tmp = make_subset(idx[lo:mid])
        bad = not ok_cache(tmp)
        shutil.rmtree(tmp, ignore_errors=True)
        if bad:
            hi = mid
        else:
            lo = mid
    return idx[lo]

def mv_to_off(relpath):
    src = THEME / relpath
    dst = THEME / ".off" / relpath
    dst.parent.mkdir(parents=True, exist_ok=True)
    # Keep original around but out of the tree
    src.rename(dst)
    print(f"  quarantined -> {dst}")

all_files = sorted(list(list_candidates()))
if not all_files:
    print("No candidate images found."); sys.exit(1)

rounds = 0
while True:
    rounds += 1
    print(f"\nRound {rounds}: testing {len(all_files)} files…")
    culprit = find_one_offender(all_files)
    if not culprit:
        print("\n✅ Cache builds successfully with remaining files.")
        break
    print(f"OFFENDER: {THEME / culprit}")
    # Quarantine it and continue
    mv_to_off(culprit)
    all_files.remove(culprit)

print("\nDone. You can inspect ~/.local/share/icons/BeOS-r5-Icons/.off for quarantined files.")
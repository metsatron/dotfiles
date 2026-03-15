#!/usr/bin/env python3
import os, sys, collections, time, shlex

# Usage:
#   ~/.scripts/rename-dupes.py [THEME_DIR] [--apply]
# Dry-run by default. Use --apply to actually rename.
#
# What it does:
# - Finds files that collide by lowercased basename within the same directory
#   (e.g. Terminal.png vs terminal.png, or png.png vs png.xpm).
# - Chooses one "keeper" (prefer all-lowercase stem, then .svg, then shortest).
# - Renames the rest to "<keeper_stem>_1.ext", "<keeper_stem>_2.ext", ...
# - Never overwrites; increments suffix until a free name exists.
# - Skips .git, backup-like folders.

def main():
    args = sys.argv[1:]
    apply = False
    root = os.environ.get("THEME", ".")
    for a in list(args):
        if a == "--apply":
            apply = True
            args.remove(a)
    if args:
        root = args[0]

    if not os.path.isdir(root):
        print(f"ERROR: theme dir not found: {root}", file=sys.stderr)
        sys.exit(1)

    exts = (".png",".svg",".xpm")
    skip_dirs = {".git", "_OFF", "broken-symlinks_backup", "backup"}

    def is_skipped(relpath):
        parts = [p for p in relpath.split(os.sep) if p]
        return any(p in skip_dirs for p in parts)

    def keeper_key(fname):
        stem, ext = os.path.splitext(fname)
        # lower is better; svg is better; shorter is better; then lexicographic
        return (
            0 if stem == stem.lower() else 1,
            0 if ext.lower() == ".svg" else 1,
            len(fname),
            fname.lower()
        )

    changes = []
    for dirpath, dirnames, files in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        if is_skipped(rel):
            continue
        # consider only icon-ish files
        bybase = collections.defaultdict(list)
        for f in files:
            if f.lower().endswith(exts):
                bybase[os.path.splitext(f)[0].lower()].append(f)
        for base_lower, lst in bybase.items():
            if len(lst) <= 1:
                continue
            keeper = sorted(lst, key=keeper_key)[0]
            keeper_stem, _ = os.path.splitext(keeper)
            # avoid reusing existing names (case-insensitively)
            used = set(x.lower() for x in files)
            idx = 1
            for f in sorted(lst, key=str.lower):
                if f == keeper:
                    continue
                _, ext = os.path.splitext(f)
                # make a target that won't collide
                while True:
                    target = f"{keeper_stem}_{idx}{ext.lower()}"
                    if target.lower() not in used and not os.path.exists(os.path.join(dirpath, target)):
                        break
                    idx += 1
                src = os.path.join(dirpath, f)
                dst = os.path.join(dirpath, target)
                changes.append((src, dst))
                used.add(target.lower())
                idx += 1

    if not changes:
        print("No case/extension duplicates found. Nothing to do.")
        return 0

    print(f"Planned renames: {len(changes)}")
    for s,d in changes:
        print("  mv --", shlex.quote(s), shlex.quote(d))

    if not apply:
        print("\n(DRY RUN) Nothing changed.")
        print("Apply with:\n  ~/.scripts/rename-dupes.py", shlex.quote(root), "--apply")
        return 0

    undo = os.path.expanduser(f"~/.scripts/rename_dupes_undo-{int(time.time())}.sh")
    os.makedirs(os.path.dirname(undo), exist_ok=True)
    with open(undo, "w") as fh:
        fh.write("#!/usr/bin/env bash\nset -euo pipefail\n\n")
        for s,d in changes:
            os.rename(s, d)
            fh.write(f"mv -i -- {shlex.quote(d)} {shlex.quote(s)}\n")
    os.chmod(undo, 0o755)
    print(f"\nAPPLIED {len(changes)} renames.")
    print(f"Undo script: {undo}")
    return 0

if __name__ == "__main__":
    sys.exit(main())

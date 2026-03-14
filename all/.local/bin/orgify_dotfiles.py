#!/usr/bin/env python3
"""
Non-destructive org-ify: wrap each existing config file in an Org source block
that tangles back to the same path. Generated 2025-08-21 19:11:55 .

- Creates files under ./orgsrc/ mirroring the original path with '.org' appended.
- Skips obvious binaries (by extension) and existing .org files.
- Won't overwrite Org files unless --force is used.
"""
import argparse, os, pathlib, sys

SKIP_EXT = {".png",".jpg",".jpeg",".gif",".webp",".pdf",".zip",".tar",".gz",".xz",
            ".7z",".iso",".mp3",".ogg",".flac",".mp4",".mkv",".webm",".bin",".otf",".ttf"}

def guess_lang(path: pathlib.Path) -> str:
    n = path.name.lower()
    if n.endswith((".bashrc",".bash_aliases",".bash_profile",".bash_functions",".bash_exports",".bash_env",".bash_options",".bash_prompt")):
        return "sh"
    if n.endswith((".zshrc",".zsh_aliases",".zsh_profile",".zsh_functions",".zsh_exports",".zsh_env",".zsh_options",".zsh_plugins",".zsh_keybinds",".p10k.zsh")):
        return "sh"
    if n.endswith((".tmux.conf",)) or path.suffix in {".tmux"}:
        return "conf"
    if path.suffix in {".el"}:
        return "emacs-lisp"
    if path.suffix in {".vim",".vimrc"} or n == ".vimrc":
        return "viml"
    if path.suffix in {".lua"}:
        return "lua"
    if path.suffix in {".conf",".cfg",".ini"}:
        return "conf"
    if path.suffix in {".xinitrc",".xprofile",".xresources",".Xresources",".Xdefaults",".Xdefault"}:
        return "conf"
    if path.suffix in {".json"}:
        return "json"
    if path.suffix in {".yml",".yaml"}:
        return "yaml"
    if path.suffix in {".py"}:
        return "python"
    if path.suffix in {".sh",".bash"}:
        return "sh"
    return "text"

def should_skip(p: pathlib.Path) -> bool:
    if p.is_dir(): return True
    if p.suffix.lower() in SKIP_EXT: return True
    if p.name.endswith(".org"): return True
    if any(part in {".git","backups","json.data"} for part in p.parts): return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=os.getcwd(), help="dotfiles repo root (defaults to cwd)")
    ap.add_argument("--force", action="store_true", help="overwrite existing org files")
    args = ap.parse_args()
    root = pathlib.Path(args.root).resolve()
    outroot = root / "orgsrc"

    created = 0
    for p in root.rglob("*"):
        if should_skip(p): 
            continue
        try:
            data = p.read_text(encoding="utf-8")
        except Exception:
            # binary or unreadable
            continue

        rel = p.relative_to(root)
        out = outroot / (str(rel) + ".org")
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists() and not args.force:
            continue

        lang = guess_lang(p)
        header = f"""#+TITLE: {rel}
#+OPTIONS: toc:2
#+PROPERTY: header-args :mkdirp yes :results silent :comments both

* Source
This file tangles to ~{rel}~. You can start adding commentary above and split blocks as you migrate.
#+BEGIN: toc :depth 2
#+END:

* Code
#+BEGIN_SRC {lang} :tangle {rel}
"""
        footer = "\n#+END_SRC\n"
        out.write_text(header + data + footer, encoding="utf-8")
        created += 1

    print(f"Created {created} org files under {outroot}")

if __name__ == "__main__":
    main()

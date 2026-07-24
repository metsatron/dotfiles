---
name: redstone-9x-theme-pixels
description: Pixel-accurate forensics methodology for the Redstone 9X IceWM BeOS-tab themes. Load BEFORE editing any IceWM titlebar, tab, corner, or caption-button pixmap (frameATL, title*, close*/minimize*/maximize*/restore*). Covers capturing the live :93 guest as the only ground truth, numeric pixel probing, the marker experiment for learning the real pixmap-to-screen mapping, and the refresh gap-fill trap that silently drops edits to existing theme dirs. Includes a ready-to-run live probe harness.
---

# Redstone 9X IceWM Tab Theme — Pixel Forensics Methodology

Use this BEFORE editing any IceWM titlebar / tab / corner / caption-button pixmap in the Redstone 9X BeOS-tab themes (`frameATL`, `title*`, `close*`/`minimize*`/`maximize*`/`restore*`, `frame*`). It exists because pixel work on these themes has repeatedly gone in circles — the failures were always the same, and they are all avoidable. Read the laws, run the harness, measure the live guest. Do not eyeball, do not theorise, do not trust an isolated render.

## Law 0 — The live `:93` guest is the ONLY ground truth

An isolated Xvfb/host render — even with the guest's exact `icewm-gradients` binary and the guest's `prefoverride` — STILL diverges from the live guest in geometry. Real window sizes, `CornerSizeX/Y` placement, the shaped-tab corner clip, and caption-button offsets all differ from a tiny test window. A source column that lands on the visible tab edge in Xvfb lands 6px inside on the live guest. **Never verify tab pixel-positioning against an isolated render.** The isolated render is a detector, and detectors lie (covenant, 2026-07-14). Every positional claim is made against a live `:93` capture or it is not made at all.

## Law 1 — The refresh gap-fill silently drops edits to EXISTING theme dirs

`loom redstone:refresh` projects theme dirs the guest is **missing**. It does **not** re-project a theme dir that already exists in the guest home. So: you edit `linux/.icewm/themes/<Theme>/frameATL.xpm`, run refresh, capture — and the guest still has the OLD pixmap. You then "verify" a change that never shipped and conclude the edit did nothing (or that some unrelated thing regressed). This has burned multiple sessions.

Before testing ANY edit to an existing theme dir:
1. `GH=/home/metsatron/.local/share/dotcortex/guests/sanctuary-redstone-9x/home`
2. `rm -rf "$GH/.icewm/themes/<Theme>"`  (guest copy only — never the DotCortex source)
3. `cd ~/DotCortex && loom redstone:refresh`
4. **Confirm deployment** by grepping the guest file for your exact edit BEFORE you capture: `grep -m1 'yourEditPattern' "$GH/.icewm/themes/<Theme>/frameATL.xpm"`. If it is not there, nothing you capture is about your change.

## Law 2 — Numeric probe, never eyeball

Small screenshots and detector summaries lie. Crop the corner region, dump it as a text pixel map (`convert … txt:`), map each hex to the theme's letter code, and print a per-row grid indexed by `(x − frameX, y − frameY)`. Read the grid, not the picture. Only use a zoomed PNG to sanity-check a grid you already trust.

## Law 3 — Find the real frame origin; never assume it

`xdotool`/`xwininfo` on `:93` give the exact frame X,Y,W,H and the child `TitleBar`/`Close` window offsets (which reveal where icewm actually places the leftmost button — usually several px right of the frame corner). Probe at the measured origin. The ACTIVE window is the one with the coloured tab (`ColorActiveTitleBar`, `#feca00` for Max-Tab) and uses `frameA*`/`title*A*`; the INACTIVE window is grey and uses `frameI*`/`title*I*`; dialogs use `dframe*`. Edit the variant that matches the window you are fixing, and probe BOTH active and inactive before claiming a fix — an active-corner edit must not regress the inactive corner.

## Law 4 — Learn the pixmap→screen mapping empirically (marker experiment)

Do NOT assume which source column/row of a pixmap lands on which screen pixel — icewm scales, clips, and shapes the corner, and the mapping is non-1:1, non-obvious, and different per environment. To learn it: paint the candidate pixmap's first columns with a distinct colour gradient (col0=red, col1=green, …), DEPLOY TO THE GUEST (Law 1), capture live, and read which source column shows up at which screen `x`. Only then edit the real colours at the proven source coordinates. This is the controlled-marker method the covenant demands over squinting at 16px features.

## Law 5 — The override outranks the theme

`scheme-apply` injects `ColorActiveTitleBar` into `$GH/.icewm/prefoverride`, which OUTRANKS the theme's `Color*` keys. It is real on the live guest, so live captures already include it. (Any hypothetical render that omits it is wrong by construction.)

## Law 6 — Do not thrash the user's room

The refresh reloads the WM visibly and the guest is often on the user's screen. Batch edits, deploy once, capture once. If the user is actively watching/using the room, say what a live experiment will do and get a go-ahead before repeatedly reloading it. A read-only `import -window root` capture does not disturb anything; a `refresh` (WM reload) does.

## Theme dirs are vendored payload

`linux/.icewm/themes/<Theme>/` is edited **directly** (git-tracked), unlike everything else under `linux/` which is tangled. Provenance is documented in `sanctuary-redstone-9x-schemes.org`. Pixmap taxonomy: `title{A,I}{L,M,T,P,S,J,B,Q,R}` = titlebar background tiles; `frame{A,I}{TL,T,TR,L,R,BL,B,BR}` = border + corners; `close/minimize/maximize/restore{A,I}` = caption buttons (16×48 = two 24px frames). `A`=active, `I`=inactive, `d`-prefix=dialog.

## The probe harness (copy to scratchpad, run against live `:93`)

```bash
#!/usr/bin/env bash
# redstone-tabprobe TITLE [cropW cropH dx dy]
# Captures the LIVE :93 root and prints a numeric pixel grid of a window's
# top-left corner, indexed by (x-frameX, y-frameY). Read-only — safe while the
# user is in the room. Requires the room running on :93.
set -u
TITLE="${1:?window title, e.g. metsatron}"
CW="${2:-26}"; CH="${3:-30}"; DX="${4:--6}"; DY="${5:--8}"
XA=/home/metsatron/.Xauthority
IMPORT=$(ls -d ~/.guix-extra-profiles/*/*/bin/import 2>/dev/null | head -1)
CV=$(ls -d ~/.guix-extra-profiles/*/*/bin/convert 2>/dev/null | head -1)
XD=/usr/bin/xdotool; XW=/usr/bin/xwininfo
OUT=$(mktemp -d)/live.png
XAUTHORITY=$XA DISPLAY=:93 "$IMPORT" -window root "$OUT"
WID=$(XAUTHORITY=$XA DISPLAY=:93 $XD search --onlyvisible --name "$TITLE" | tail -1)
eval "$(XAUTHORITY=$XA DISPLAY=:93 $XW -id "$WID" | awk \
  '/Absolute upper-left X/{print "FX="$NF}/Absolute upper-left Y/{print "FY="$NF}')"
echo "win '$TITLE' id=$WID frame origin: FX=$FX FY=$FY"
TLX=$((FX+DX)); TLY=$((FY+DY))
"$CV" "$OUT" -crop ${CW}x${CH}+${TLX}+${TLY} +repage txt: > "$OUT.txt"
python3 - "$OUT.txt" "$TLX" "$TLY" "$FX" "$FY" <<'PY'
import sys,re,collections
rows=collections.defaultdict(dict); tlx,tly,fx,fy=map(int,sys.argv[2:6])
for ln in open(sys.argv[1]):
    m=re.match(r'(\d+),(\d+):.*?(#[0-9A-Fa-f]{6})',ln)
    if not m: continue
    x,y,h=int(m.group(1)),int(m.group(2)),m.group(3).upper(); rows[y][x]=h
t={'606060':'a','898989':'b','999999':'c','9C9C9C':'c','D9D9D9':'d','D8D8D8':'d',
   'F8FC4F':'e','FECA00':'f','F8FCF8':'F','000000':'K','FFFFFF':'W','FFCB00':'j',
   'EDC4AB':'e','C69B84':'f'}  # last two = Personal-Tab warm highlight/body
nm=lambda h:t.get(h[1:],h[:4])
xs=sorted(next(iter(rows.values())).keys())
print("      "+"".join(f"{tlx+i-fx:>4}" for i in range(len(xs)))+"  (x-frameX)")
for y in sorted(rows):
    print(f"y{y-fy:>+4} "+"".join(f"{nm(rows[y][x]):>4}" for x in xs))
PY
```

Letter codes: `a`=#606060 `b`=#898989 `c`=#999999 `d`=#D9D9D9 `e`=highlight (#F8FC4F yellow / #EDC4AB terracotta) `f`=body (#FECA00 / #C69B84) `F`=#F8FCF8 `j`=#FFCB00 button face `K`=#000000 `W`=client.

## Canonical Owners

- Theme payload: `linux/.icewm/themes/` (vendored, provenance in `sanctuary-redstone-9x-schemes.org`)
- Deploy/refresh: `sanctuary-redstone-9x-refresh.org` (see the `redstone-9x-refresh` skill)
- This skill: `agents-skills-dotcortex.org`

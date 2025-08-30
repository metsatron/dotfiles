#!/usr/bin/env bash
# org2obsidian.sh — Org → Obsidian MD (split by top-level *), with:
# - deterministic conversion (no pandoc),
# - tasks preserved as Obsidian Tasks (- [ ] …) with SCHEDULED/DEADLINE/CLOSED/CREATED chips,
# - deep non-TODO subheads → bullets (configurable),
# - YAML frontmatter with Org metadata (+ raw OPTIONS),
# - optional TOC insertion honoring #+toc: unless OPTIONS toc:nil.
#
# Env knobs:
#   OUT_DIR=/path/to/output
#   OVERWRITE=1                 # 0 = skip existing
#   EXTRA_TAGS="tag1,tag2"
#   FILE_PREFIX=""
#   TASKS_GLOBAL_FILTER="#task"
#   NON_TASK_SUBHEADS_AS_LIST=1 # 1=convert non-TODO headings with depth>=LIST_MIN_DEPTH to bullets
#   LIST_MIN_DEPTH=5            # default: ***** and deeper become bullets
#   BULLET_INDENT=2             # spaces per nesting level for bullets
#   TOC_BEHAVIOR=auto           # auto|always|never (auto = insert [[toc]] if #+toc: and not toc:nil)
#   KEEP_PLANNING_LINES=0       # 1 = keep raw planning lines in body too
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 file1.org [file2.org ...]" >&2
  exit 1
fi

python3 - "$@" <<'PYCODE'
import sys, os, re, unicodedata, uuid, json
from datetime import datetime

# ---------- Config from ENV ----------
ENV = os.environ
OUT_DIR  = ENV.get("OUT_DIR")
OVERWRITE = ENV.get("OVERWRITE","1") != "0"
EXTRA_TAGS = [t.strip() for t in ENV.get("EXTRA_TAGS","").split(",") if t.strip()]
FILE_PREFIX = ENV.get("FILE_PREFIX","")
TASKS_GLOBAL_FILTER = ENV.get("TASKS_GLOBAL_FILTER","").strip()
NON_TASK_AS_LIST = ENV.get("NON_TASK_SUBHEADS_AS_LIST","1") == "1"
LIST_MIN_DEPTH = int(ENV.get("LIST_MIN_DEPTH","5"))
BULLET_INDENT  = int(ENV.get("BULLET_INDENT","2"))
TOC_BEHAVIOR   = ENV.get("TOC_BEHAVIOR","auto")
KEEP_PLANNING  = ENV.get("KEEP_PLANNING_LINES","0") == "1"

TODO_KEYWORDS = {"TODO","DONE","NEXT","WAIT","WAITING","CANCELLED","CANCELED","KILLED","ARCHIVED","RESOLVED","HOLD","BACKLOG","INPROGRESS","IN-PROGRESS","WIP","STARTED"}

ZERO_WIDTHS = ("\u200b","\uFEFF")
NBSP = "\u00A0"

def clean(s:str)->str:
    if not s: return s
    for z in ZERO_WIDTHS: s=s.replace(z,"")
    return s.replace(NBSP," ").rstrip()

def slugify(title: str) -> str:
    t = unicodedata.normalize('NFKD', title).encode('ascii','ignore').decode('ascii')
    t = re.sub(r'[^A-Za-z0-9]+','-',t).strip('-').lower()
    return t or "section"

def parse_org_timestamp(ts: str) -> str:
    if not ts: return ""
    s = ts.strip().lstrip("<[").rstrip(">]")
    # yyyy-mm-dd or yy-mm-dd or yyyy/mm/dd or dd.mm.yyyy
    m = (re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})(?:\s+\w{2,12})?(?:\s+(\d{1,2}:\d{2}))?', s)
         or re.search(r'(\d{2})[./-](\d{1,2})[./-](\d{1,2})(?:\s+\w{2,12})?(?:\s+(\d{1,2}:\d{2}))?', s))
    if not m: return ""
    y, mo, d = m.group(1), m.group(2), m.group(3); t = m.group(4) or ""
    if len(y)==2:
        yi=int(y); y=f"20{yi:02d}" if yi<=68 else f"19{yi:02d}"
    return f"{y}-{int(mo):02d}-{int(d):02d} {t}".strip()

def parse_meta(lines):
    meta = {
        "title": None, "date": None, "author": None, "email": None, "language": None,
        "filetags": [], "select_tags": None, "exclude_tags": None, "creator": None,
        "options": [], "toc_request": None
    }
    for line in lines:
        if line.startswith("*"): break
        line = line.strip()
        m = re.match(r"^#\+([A-Za-z_]+):\s*(.*)$", line)
        if not m:
            continue
        key = m.group(1).upper()
        val = m.group(2).strip()
        if key == "TITLE": meta["title"]=val
        elif key == "DATE": meta["date"]=parse_org_timestamp(val) or val
        elif key == "AUTHOR": meta["author"]=val
        elif key == "EMAIL": meta["email"]=val
        elif key == "LANGUAGE": meta["language"]=val
        elif key == "FILETAGS":
            tags = [t for t in val.strip(":").split(":") if t]
            meta["filetags"].extend(tags)
        elif key == "SELECT_TAGS": meta["select_tags"]=val
        elif key == "EXCLUDE_TAGS": meta["exclude_tags"]=val
        elif key == "CREATOR": meta["creator"]=val
        elif key == "OPTIONS":
            meta["options"].append(val)
            # detect toc:nil
            if re.search(r'\btoc:nil\b', val): meta["toc_request"]="off"
        elif key == "TOC":
            # org has both #+TOC: and #+toc: forms; capture common "headlines 3"
            meta["toc_request"]=val
    return meta

def split_sections(lines):
    sections=[]
    idxs=[i for i,l in enumerate(lines) if l.startswith("* ")]
    if not idxs:
        sections.append({"heading":"preface","body":lines[:]})
        return sections
    if idxs[0]>0 and any(lines[i].strip() for i in range(idxs[0])):
        sections.append({"heading":"preface","body":lines[:idxs[0]]})
    idxs.append(len(lines))
    for i in range(len(idxs)-1):
        block=lines[idxs[i]:idxs[i+1]]
        head=block[0].strip()
        # strip TODO token & priority from top heading title for display; preserve TODO for task
        m=re.match(r"^\*+\s+([A-Z][A-Z0-9_-]+)?\s*(.*)$", head)
        todo=""; title=""
        if m:
            tok=(m.group(1) or "")
            title=m.group(2)
            if tok and tok.upper() in TODO_KEYWORDS:
                todo=tok; # leave title as rest
            else:
                title=(tok+" "+title).strip()
        title=re.sub(r"\[#([A-Z])\]\s*","",title).strip()
        title=re.sub(r":([A-Za-z0-9_@#%./+-:]+):\s*$","",title).strip()
        sections.append({"heading":title or "section","head_raw":head,"todo":todo,"body":block[1:]})
    return sections

def emit_yaml(meta, section_title, orgfile_base, todo_info):
    tags = []
    seen=set()
    for t in (meta.get("filetags", []) + EXTRA_TAGS):
        if t not in seen:
            seen.add(t); tags.append(t)
    yaml = {
        "title": section_title,
        "source_org_file": orgfile_base,
        "tags": tags or None,
        "author": meta.get("author") or None,
        "email": meta.get("email") or None,
        "language": meta.get("language") or None,
        "date": meta.get("date") or None,
        "org": {
            "select_tags": meta.get("select_tags") or None,
            "exclude_tags": meta.get("exclude_tags") or None,
            "creator": meta.get("creator") or None,
            "options_raw": meta.get("options") or None,
            "toc_request": meta.get("toc_request") or None,
            "heading_todo": todo_info or None
        }
    }
    # prune nulls
    def prune(v):
        if isinstance(v, dict):
            return {k: prune(x) for k,x in v.items() if x is not None}
        return v
    yaml = prune(yaml)

    # dump simple YAML without PyYAML to keep it portable
    out=["---"]
    def emit(k,v,indent=""):
        if isinstance(v, dict):
            out.append(f"{indent}{k}:")
            for kk,vv in v.items(): emit(kk,vv,indent+"  ")
        elif isinstance(v, list):
            out.append(f"{indent}{k}:")
            for item in v:
                out.append(f"{indent}- {item}")
        else:
            if isinstance(v, str) and (":" in v or v.strip()!=v):
                out.append(f'{indent}{k}: "{v}"')
            else:
                out.append(f"{indent}{k}: {v}")
    for k,v in yaml.items(): emit(k,v)
    out.append("---\n")
    return "\n".join(out)

def convert_section(section, meta):
    """
    Convert one top-level section's body.
    - Tasks from subhead TODOs become '- [ ] ...' lines (flush-left).
    - Non-TODO subheads at depth >= LIST_MIN_DEPTH become '- ...' bullets with indentation.
    - Other subheads become markdown headings ###..######.
    - Planning lines under a heading are consumed for chips unless KEEP_PLANNING.
    """
    lines = section["body"][:]
    out=[]
    tasks=[]
    i=0

    def parse_heading(line):
        m = re.match(r"^(\*+)\s+(.+?)\s*$", line)
        if not m: return None
        stars=m.group(1); rest=m.group(2)
        depth=len(stars)
        # Extract leading TODO token, priority, tags
        todo=""; prio=""
        m2=re.match(r"^([A-Z][A-Z0-9_-]+)\s+(.*)$", rest)
        if m2 and m2.group(1).upper() in TODO_KEYWORDS:
            todo=m2.group(1); rest=m2.group(2)
        # priority
        rest=re.sub(r"\[#([A-Z])\]\s*","",rest)
        # tags (ignore for display)
        rest=re.sub(r":([A-Za-z0-9_@#%./+-:]+):\s*$","",rest)
        title=rest.strip()
        return {"depth":depth,"todo":todo,"prio":prio,"title":title}

    def gather_planning(start_idx):
        sched=deadline=closed=created=""
        j=start_idx+1
        while j<len(lines):
            nxt=lines[j]
            if nxt.startswith("*"): break
            if not nxt.strip(): 
                j+=1
                continue
            # planning lines (case-insensitive)
            m=re.search(r"\bSCHEDULED:\s*([<\[].*[>\]])", nxt, re.I)
            if m and not sched: sched=parse_org_timestamp(m.group(1)); 
            m=re.search(r"\bDEADLINE:\s*([<\[].*[>\]])", nxt, re.I)
            if m and not deadline: deadline=parse_org_timestamp(m.group(1));
            m=re.search(r"\bCLOSED:\s*([<\[].*[>\]])", nxt, re.I)
            if m and not closed: closed=parse_org_timestamp(m.group(1));
            m=re.search(r"\bCREATED:\s*([<\[].*[>\]])", nxt, re.I)
            if m and not created: created=parse_org_timestamp(m.group(1));
            # unless keeping, drop planning lines
            if KEEP_PLANNING:
                j+=1
            else:
                # skip this line
                del lines[j]
                continue
            j+=1
        return sched, deadline, closed, created

    while i<len(lines):
        L = clean(lines[i])
        if not L:
            # collapse multiple blank lines aggressively later; for now keep one
            out.append("\n")
            i+=1; continue

        if L.startswith("*"):
            h = parse_heading(L)
            if not h:
                out.append(L+"\n"); i+=1; continue

            sched,deadline,closed,created = gather_planning(i)

            if h["todo"]:
                # subheading task → tasks line
                chips=[]
                if sched:    chips.append(f"⏳ {sched}")
                if deadline: chips.append(f"📅 {deadline}")
                if closed:   chips.append(f"✅ {closed}")
                if created:  chips.append(f"➕ {created}")
                chip_str = (" " + " ".join(chips)) if chips else ""
                tail = (" " + TASKS_GLOBAL_FILTER) if TASKS_GLOBAL_FILTER else ""
                done = h["todo"].upper() in {"DONE","CANCELLED","CANCELED","KILLED","ARCHIVED","RESOLVED"}
                tasks.append(f"- [{'x' if done else ' '}] {h['title']}{chip_str}{tail}\n")
                # do not emit the heading itself
                i+=1; continue

            # non-TODO heading
            if NON_TASK_AS_LIST and h["depth"]>=LIST_MIN_DEPTH:
                indent = " " * (BULLET_INDENT*(h["depth"]-LIST_MIN_DEPTH))
                out.append(f"{indent}- {h['title']}\n")
                i+=1; continue
            else:
                # markdown heading
                level = min(6, h["depth"])  # map **..****** → ##..######
                out.append("#"*level + " " + h["title"] + "\n")
                # ensure exactly one blank line after heading
                out.append("\n")
                i+=1; continue

        else:
            # plain content
            out.append(L+"\n")
            i+=1

    # Build final: tasks first (if any), then body
    body = []

    # If the top-level heading itself had TODO, inject a main task at top of section
    if section.get("todo"):
        # No chips for top heading (could be added similarly by parsing)
        tail = (" " + TASKS_GLOBAL_FILTER) if TASKS_GLOBAL_FILTER else ""
        done = section["todo"].upper() in {"DONE","CANCELLED","CANCELED","KILLED","ARCHIVED","RESOLVED"}
        body.append(f"- [{'x' if done else ' '}] {section['heading']}{tail}\n")

    if tasks:
        body.extend(tasks)
        # add a single blank line before body content if there is content following
        if out and out[0].strip(): body.append("\n")

    body.extend(out)

    # whitespace normalization:
    txt = "".join(body)

    # collapse 3+ blank lines → 2, and then 2→1 after headings & list items
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    # after headings, ensure exactly one blank line
    txt = re.sub(r"^(#{1,6}\s+.*\n)\n+", r"\1\n", txt, flags=re.M)
    # between list items (bullets or tasks), remove blank lines
    txt = re.sub(r"(^\s*-\s.*\n)\n(?=\s*-\s)", r"\1", txt, flags=re.M)
    # after a list item, collapse multiple newlines to one
    txt = re.sub(r"(^\s*-\s.*\n)\n+", r"\1", txt, flags=re.M)

    return txt

def main():
    for inpath in sys.argv[1:]:
        if not inpath.lower().endswith(".org"): continue
        abspath = os.path.abspath(inpath)
        base_dir = os.path.dirname(abspath)
        out_dir = OUT_DIR or base_dir
        with open(abspath,"r",encoding="utf-8") as f:
            raw = f.read()
        raw = clean(raw)
        lines = raw.splitlines(True)

        meta = parse_meta(lines)
        sections = split_sections(lines)
        base_noext = os.path.splitext(os.path.basename(abspath))[0]

        for s in sections:
            heading = s["heading"]
            content_md = convert_section(s, meta)

            # Insert H1 title at top (Markdown)
            h1 = "# " + heading + "\n\n"

            # TOC decision
            toc_on = False
            if TOC_BEHAVIOR == "always":
                toc_on = True
            elif TOC_BEHAVIOR == "never":
                toc_on = False
            else: # auto
                if (meta.get("toc_request") and "nil" not in str(meta["toc_request"]).lower()):
                    toc_on = True
                # OPTIONS toc:nil overrides
                if any("toc:nil" in opt for opt in (meta.get("options") or [])):
                    toc_on = False

            toc_block = "[[toc]]\n\n" if toc_on else ""

            yaml = emit_yaml(meta, heading, os.path.basename(abspath), s.get("todo"))
            final = yaml + h1 + toc_block + content_md.lstrip()

            # filename
            slug = "preface" if heading.lower()=="preface" else slugify(heading)
            outname = f"{FILE_PREFIX}{base_noext}-{slug}.md"
            os.makedirs(out_dir, exist_ok=True)
            outpath = os.path.join(out_dir, outname)
            if os.path.exists(outpath) and not OVERWRITE:
                print(f"SKIP (exists): {outpath}")
            else:
                with open(outpath,"w",encoding="utf-8") as f:
                    f.write(final)
                print(f"WROTE: {outpath}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", e, file=sys.stderr); sys.exit(3)
PYCODE


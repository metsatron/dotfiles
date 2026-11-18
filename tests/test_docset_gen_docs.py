"""Tests for dotcortex-docset-gen's org and md modes and their hand-off to the corpus builder.

Hermetic: every fixture lives in a temp dir. Org tests need Emacs and are skipped, with the
reason printed, when it is absent. Run: python3 -m unittest tests/test_docset_gen_docs.py
"""
import importlib.machinery
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "all/.local/bin"
GEN = BIN / "dotcortex-docset-gen"
CORPUS = BIN / "dotcortex-help-corpus-build"
QUERY = BIN / "dotcortex-help-query"


def load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


gen = load(GEN, "docset_gen")
corpus = load(CORPUS, "corpus_build")
EMACS = gen.find_emacs()
try:
    import markdown  # noqa: F401
    HAVE_MD = True
except ImportError:
    HAVE_MD = False

ORG = """#+TITLE: Probe Guide
Preamble mentioning my_var_name and nothing else.

* Top One
alpha body text
** Sub A
sub body =code= with zebrafish
#+BEGIN_SRC bash
echo hi
#+END_SRC
* Top Two :tag:
second body
* Top One
duplicate heading body
"""
MD = """# Top One

alpha body text

## Sub A

sub body `code` with zebrafish

# Top Two

second body

# Top One

duplicate heading body
"""


def run_gen(mode, out, base, extra=(), roots=None):
    cmd = [sys.executable, str(GEN), mode, "--name", "Probe Docs", "--keyword", "probe",
           "--out", str(out), "--base", str(base), *extra, *(roots or [str(base)])]
    return subprocess.run(cmd, capture_output=True, text=True)


def docs_dir(out):
    return Path(out) / "Contents/Resources/Documents"


class Common:
    suffix = ""
    text = ""
    mode = ""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / "src"
        (self.base / "sub").mkdir(parents=True)
        (self.base / f"Probe{self.suffix}").write_text(self.text)
        (self.base / "sub" / f"Nested{self.suffix}").write_text(self.text)
        self.out = Path(self.tmp.name) / "Probe.docset"

    def test_sections_follow_the_chunker_contract(self):
        r = run_gen(self.mode, self.out, self.base)
        self.assertEqual(r.returncode, 0, r.stderr)
        html = (docs_dir(self.out) / f"Probe{self.suffix}.html").read_text()
        chunks = corpus.chunk_html(html)
        anchors = [a for a, _, _ in chunks]
        self.assertEqual(len(anchors), len(set(anchors)), "anchors must be unique")
        by_heading = {h: (a, b) for a, h, b in chunks}
        self.assertIn("Top One", by_heading)
        self.assertIn("Sub A", by_heading)
        self.assertIn("zebrafish", by_heading["Sub A"][1])
        self.assertNotIn("zebrafish", by_heading["Top One"][1], "child text must not leak into the parent chunk")
        dup = [a for a, h, _ in chunks if h == "Top One"]
        self.assertEqual(len(dup), 2)
        self.assertNotEqual(dup[0], dup[1], "duplicate headings get distinct anchors")

    def test_preamble_is_not_dropped(self):
        if self.mode == "md":
            (self.base / "Pre.md").write_text("intro paragraph kept\n\n# H\n\nbody\n")
            rel = "Pre.md"
        else:
            rel = f"Probe{self.suffix}"
        run_gen(self.mode, self.out, self.base)
        chunks = corpus.chunk_html((docs_dir(self.out) / f"{rel}.html").read_text())
        joined = " ".join(b for _, _, b in chunks)
        self.assertTrue("intro paragraph kept" in joined or "my_var_name" in joined)

    def test_incremental_second_run_renders_nothing(self):
        run_gen(self.mode, self.out, self.base)
        r = run_gen(self.mode, self.out, self.base)
        self.assertIn("0 rendered, 2 cached", r.stdout)

    def test_changed_file_is_rerendered_and_deleted_file_pruned(self):
        run_gen(self.mode, self.out, self.base)
        (self.base / "sub" / f"Nested{self.suffix}").unlink()
        (self.base / f"Probe{self.suffix}").write_text(self.text + "\nextra\n")
        r = run_gen(self.mode, self.out, self.base)
        self.assertIn("1 rendered, 0 cached", r.stdout)
        self.assertFalse((docs_dir(self.out) / f"sub__Nested{self.suffix}.html").exists())

    def test_symlinks_hidden_dirs_and_excludes_are_skipped_and_reported(self):
        (self.base / ".hidden").mkdir()
        (self.base / ".hidden" / f"x{self.suffix}").write_text(self.text)
        (self.base / "secret").mkdir()
        (self.base / "secret" / f"s{self.suffix}").write_text(self.text)
        os.symlink(self.base / f"Probe{self.suffix}", self.base / f"Link{self.suffix}")
        r = run_gen(self.mode, self.out, self.base, ["--exclude", "secret"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1 symlink", r.stdout)
        self.assertIn("1 excluded", r.stdout)
        names = {p.name for p in docs_dir(self.out).glob("*.html")}
        self.assertNotIn(f"Link{self.suffix}.html", names)
        self.assertFalse(any(n.startswith(".hidden") or n.startswith("secret") for n in names))

    def test_oversize_file_is_reported_not_silent(self):
        r = run_gen(self.mode, self.out, self.base, ["--max-bytes", "10"])
        self.assertIn("oversize", r.stdout + r.stderr)
        self.assertIn("0 entries", r.stdout)

    def test_end_to_end_query_finds_the_heading_chunk_with_anchor(self):
        shelf = Path(self.tmp.name) / "shelf"
        shelf.mkdir()
        os.symlink(self.out, shelf / "Probe.docset")
        self.assertEqual(run_gen(self.mode, self.out, self.base).returncode, 0)
        db = Path(self.tmp.name) / "corpus.sqlite"
        r = subprocess.run([sys.executable, str(CORPUS), "--docsets-dir", str(shelf), "--out", str(db)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = subprocess.run([sys.executable, str(QUERY), "--corpus", str(db), "search", "zebrafish"],
                           capture_output=True, text=True)
        hits = json.loads(r.stdout)
        self.assertTrue(hits, r.stdout)
        top = hits[0]
        self.assertEqual(top["heading"], "Sub A")
        self.assertTrue(top["anchor"])
        self.assertTrue(top["path"].endswith(".html"))


@unittest.skipUnless(EMACS, "emacs not found: org mode untested here")
class OrgMode(Common, unittest.TestCase):
    suffix, text, mode = ".org", ORG, "org"

    def test_underscores_are_not_subscripts(self):
        run_gen("org", self.out, self.base)
        html = (docs_dir(self.out) / "Probe.org.html").read_text()
        self.assertIn("my_var_name", html)
        self.assertNotIn("<sub>", html)

    def test_a_failing_file_fails_the_run_loudly(self):
        # An unterminated source block with a broken include still exports; a binary file does not.
        (self.base / "Bad.org").write_bytes(b"\xff\xfe\x00\x00" * 4)
        (self.base / "Bad.org").chmod(0o000)
        try:
            r = run_gen("org", self.out, self.base)
        finally:
            (self.base / "Bad.org").chmod(0o644)
        if os.access(self.base / "Bad.org", os.R_OK) and r.returncode == 0:
            self.skipTest("cannot make a file unreadable here (running as root?)")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Bad.org", r.stderr)


@unittest.skipUnless(HAVE_MD, "python markdown module not importable: md mode untested here")
class MarkdownMode(Common, unittest.TestCase):
    suffix, text, mode = ".md", MD, "md"


@unittest.skipUnless(HAVE_MD, "python markdown module not importable")
class QueryRobustness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name) / "src"
        base.mkdir()
        (base / "Guide.md").write_text("# Build\n\nRun dotcortex-help-corpus-build to index chmod 2755 setgid modes.\n")
        out = Path(self.tmp.name) / "G.docset"
        shelf = Path(self.tmp.name) / "shelf"
        shelf.mkdir()
        os.symlink(out, shelf / "G.docset")
        assert run_gen("md", out, base).returncode == 0
        self.db = Path(self.tmp.name) / "c.sqlite"
        subprocess.run([sys.executable, str(CORPUS), "--docsets-dir", str(shelf), "--out", str(self.db)],
                       check=True, capture_output=True)

    def search(self, q):
        r = subprocess.run([sys.executable, str(QUERY), "--corpus", str(self.db), "search", q],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_hyphenated_command_name(self):
        self.assertTrue(self.search("dotcortex-help-corpus-build"))

    def test_natural_language_question(self):
        self.assertTrue(self.search("Why use chmod 2755?"))

    def test_valid_fts_syntax_is_unchanged(self):
        self.assertTrue(self.search("chmod AND setgid"))
        self.assertEqual(self.search("chmod AND nonexistentword"), [])

    def test_question_words_do_not_outrank_the_real_match(self):
        base = Path(self.tmp.name) / "src"
        (base / "Noise.md").write_text("# Noise\n\nhow do i get started with the calendar\n")
        (base / "Export.md").write_text("# Export\n\nexport a conversation from the browser\n")
        out = Path(self.tmp.name) / "G.docset"
        self.assertEqual(run_gen("md", out, base).returncode, 0)
        subprocess.run([sys.executable, str(CORPUS), "--docsets-dir", str(Path(self.tmp.name) / "shelf"),
                        "--out", str(self.db)], check=True, capture_output=True)
        hits = self.search("How do I export a conversation?")
        self.assertTrue(hits[0]["path"].startswith("Export.md"), [h["path"] for h in hits])

    def test_punctuation_only_returns_empty_not_error(self):
        self.assertEqual(self.search("?!"), [])


class Shared(unittest.TestCase):
    def test_name_collision_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t) / "src"
            (base / "a").mkdir(parents=True)
            (base / "a__b.md").write_text("# x\n")
            (base / "a" / "b.md").write_text("# y\n")
            r = run_gen("md", Path(t) / "o.docset", base)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("collision", r.stderr)

    def test_root_outside_base_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t) / "a"
            other = Path(t) / "b"
            base.mkdir()
            other.mkdir()
            r = run_gen("md", Path(t) / "o.docset", base, roots=[str(other)])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("outside --base", r.stderr)

    def test_man_mode_still_accepted(self):
        r = subprocess.run([sys.executable, str(GEN), "man", "--help"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("{man,org,md}", r.stdout)

    def test_man_page_heading_id_becomes_the_chunk_anchor(self):
        # mandoc output: id on the heading, none on the section.
        html = ('<section class="Sh"><h1 class="Sh" id="SYNOPSIS"><a href="#SYNOPSIS">SYNOPSIS</a></h1>'
                '<p>chmod OPTION</p></section>'
                '<section class="Sh" id="own"><h1 class="Sh" id="ignored">OWN</h1><p>x</p></section>')
        got = {h: a for a, h, _ in corpus.chunk_html(html)}
        self.assertEqual(got["SYNOPSIS"], "SYNOPSIS")
        self.assertEqual(got["OWN"], "own", "a section id outranks the heading id")

    def test_sectionize_flat_nests_by_level(self):
        body = "<h1>A</h1><p>a</p><h2>B</h2><p>b</p><h2>C</h2><p>c</p><h1>D</h1><p>d</p>"
        html = gen.sectionize_flat(body, "T")
        chunks = {h: b for _, h, b in corpus.chunk_html(html)}
        self.assertEqual(set(chunks), {"A", "B", "C", "D"})
        self.assertEqual(chunks["B"].strip(), "b")


if __name__ == "__main__":
    unittest.main()

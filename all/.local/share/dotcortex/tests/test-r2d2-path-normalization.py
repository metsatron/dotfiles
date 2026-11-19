#!/usr/bin/env python3
"""Synthetic tests of the generated hook, without live R2D2 state or calls."""
import ast
import json
import os
import subprocess
import sys
import tempfile
import types
from pathlib import Path

HOOK = Path(__file__).resolve().parents[4] / ".hermes/r2d2/hook_tool.py"
PATHFIX = Path.home() / ".hermes/r2d2/pathfix.py"


class Directive(Exception):
    def __init__(self, value):
        self.value = value


def main():
    source = HOOK.read_text()
    wanted = {"path_form_class", "log_path_diagnostic", "check_paths"}
    nodes = [n for n in ast.parse(source).body
             if isinstance(n, ast.FunctionDef) and n.name in wanted]
    assert len(nodes) == len(wanted)
    ns = {"os": os, "re": __import__("re")}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<isolated-hook>", "exec"), ns)
    pf_ns = {"__name__": "isolated_pathfix"}
    exec(compile(ast.parse(PATHFIX.read_text()), "<isolated-pathfix>", "exec"), pf_ns)
    results = []

    with tempfile.TemporaryDirectory(prefix="r2d2-path-check-") as td:
        root = Path(td)
        target = root / "fixture with spaces.pdf"
        target.write_text("NONCLINICAL_FIXTURE")
        fake_vault = root / "fake-vault"
        fake_vault.mkdir()
        pf = types.SimpleNamespace(**{k: v for k, v in pf_ns.items()
                                     if not k.startswith("__")})
        pf.find_match = lambda p, sid: pf_ns["find_match"](
            p, sid, attach_root=str(root / "attachments"), vault=str(fake_vault))
        pf.suggestions = lambda p: pf_ns["suggestions"](p, vault=str(fake_vault))
        pf.close_matches = lambda p: pf_ns["close_matches"](p, vault=str(fake_vault))

        def run(raw, mode="active", tool="read_file"):
            events = []
            r = types.SimpleNamespace(
                mode=lambda feature: mode if feature == "path_fixer" else "off",
                log=lambda kind, **fields: events.append((kind, fields)),
                mark_steer=lambda *args: None)

            def out(value=None):
                raise Directive(value or {})

            def block(feature, message, **fields):
                out({"action": "block"} if mode == "active" else {})

            ns.update(R=r, pathfix=pf, out=out, block=block)
            try:
                ns["check_paths"]("synthetic", tool, {pf.PATH_ARGS[tool]: raw}, None)
                value = {}
            except Directive as exc:
                value = exc.value
            diags = [fields for kind, fields in events if kind == "path_diagnostic"]
            if mode == "off":
                assert not diags
            else:
                assert len(diags) == 1
                assert set(diags[0]) == {
                    "tool", "form_class", "directive", "normalized_exists"}
                assert diags[0]["directive"] == value.get("action", "none")
                assert isinstance(diags[0]["normalized_exists"], bool)
                # Every string is a known enum; no value can contain a path.
                assert diags[0]["form_class"] in {
                    "bare_absolute", "quoted", "file_uri", "percent_encoded",
                    "relative", "unsupported_url", "invalid"}
                assert diags[0]["tool"] in pf.PATH_ARGS
                assert diags[0]["directive"] in {"none", "modify", "block"}
            return value

        for tool in pf.PATH_ARGS:
            for raw in (json.dumps(str(target)), "file://" + str(target)):
                value = run(raw, tool=tool)
                assert value == {"action": "modify", "args": {pf.PATH_ARGS[tool]: str(target)}}
                assert Path(value["args"][pf.PATH_ARGS[tool]]).read_text() == "NONCLINICAL_FIXTURE"
                results.append(True)
        assert run(str(target)) == {}
        assert run(json.dumps(str(target)), "shadow") == {}
        assert run(json.dumps(str(target)), "off") == {}
        assert run("relative.pdf") == {}
        assert run("https://example.invalid/a%20b") == {}
        assert run(str(root / "missing-directory" / "absent.pdf")).get("action") == "block"
        results.extend([True] * 6)

        (root / "real" / "deep").mkdir(parents=True)
        (root / "alias").symlink_to(root / "real" / "deep", target_is_directory=True)
        (root / "target").write_text("LEXICAL")
        (root / "real" / "target").write_text("SEMANTIC")
        traversal = str(root / "alias" / ".." / "target")
        for raw in (traversal, json.dumps(traversal), "file://" + traversal):
            assert run(raw) == {}
            results.append(True)
        assert Path(traversal).resolve().read_text() == "SEMANTIC"

        (root / "ambig-one.pdf").write_text("ONE")
        (root / "ambig-two.pdf").write_text("TWO")
        assert run(str(root / "ambig.pdf"))["action"] == "block"
        assert run(str(root / "ambig.pdf"), "shadow") == {}
        results.extend([True] * 2)

        # Exercise the complete hook subprocess through its symlink, with fake
        # sibling modules. No live library, log, database or model is imported.
        launch = root / "launch"
        launch.mkdir()
        (launch / "hook_tool.py").symlink_to(HOOK)
        (launch / "pathfix.py").write_text(PATHFIX.read_text())
        stub = """import json,sys
from pathlib import Path
HOME=Path(__file__).parent
SECRET_VAULT=HOME/'fake-vault'
STATE_DIR=HOME/'state'
def read_payload(): return json.load(sys.stdin)
def who(*args): return 'gillean'
def mode(feature): return 'active' if feature=='path_fixer' else 'off'
def log(kind,**fields): pass
"""
        (launch / "r2d2lib.py").write_text(stub)
        payload = {
            "hook_event_name": "pre_tool_call", "tool_name": "read_file",
            "tool_input": {"path": json.dumps(str(target))}}
        completed = subprocess.run(
            [sys.executable, "-B", str(launch / "hook_tool.py")],
            input=json.dumps(payload), text=True, capture_output=True,
            timeout=15, env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"})
        assert completed.returncode == 0 and not completed.stderr
        value = json.loads(completed.stdout)
        assert value == {"action": "modify", "args": {"path": str(target)}}
        assert Path(value["args"]["path"]).read_text() == "NONCLINICAL_FIXTURE"
        results.append(True)

    print(json.dumps({"status": "PASS", "checks": len(results),
                      "live_state_or_model_used": False,
                      "diagnostic_privacy": "enum_fields_only"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

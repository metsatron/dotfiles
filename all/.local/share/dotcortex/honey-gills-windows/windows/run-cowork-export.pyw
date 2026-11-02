# run-cowork-export.pyw: windowless runner for the Cowork -> Obsidian export. It replaces run-cowork-export.bat as
# the Task Scheduler action, so no console window opens. It writes the same export.log, in the same format, and
# exits with the exporter's own exit code. Any console program the exporter starts (icacls) is also kept hidden.
import datetime, os, runpy, subprocess, sys, traceback

EXPORTER = os.environ.get("COWORK_EXPORT_DIR", r"C:\Users\gille\Obsidian Vault\Scripts\cowork-export")
NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW

_popen_init = subprocess.Popen.__init__


def _quiet(self, *args, **kwargs):
    kwargs["creationflags"] = kwargs.get("creationflags", 0) | NO_WINDOW
    _popen_init(self, *args, **kwargs)


subprocess.Popen.__init__ = _quiet
os.environ["PYTHONIOENCODING"] = "utf-8"
log = open(os.path.join(EXPORTER, "export.log"), "a", encoding="utf-8", buffering=1)
sys.stdout = sys.stderr = log
now = datetime.datetime.now()
log.write("\n===== run %s %s.%02d =====\n" % (now.strftime("%a %d/%m/%Y"), now.strftime("%H:%M:%S"), now.microsecond // 10000))
code = 0
try:
    script = os.path.join(EXPORTER, "cowork_to_md.py")
    sys.path.insert(0, EXPORTER)
    os.chdir(EXPORTER)
    sys.argv = [script] + sys.argv[1:]
    runpy.run_path(script, run_name="__main__")
except SystemExit as e:
    code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
except BaseException:
    traceback.print_exc()
    code = 1
log.flush()
sys.exit(code)

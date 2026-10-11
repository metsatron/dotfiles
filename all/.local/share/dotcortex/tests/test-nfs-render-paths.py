"""NFS home rendering: different local/remote accounts and fail-closed inputs."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[5]
RENDER = ROOT / "all/.local/bin/nfs-render-paths"

class NfsHomeTests(unittest.TestCase):
    def render(self, text, *args):
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "map"
            template.write_text(text)
            return subprocess.run([str(RENDER), *args, str(template)],
                                  capture_output=True, text=True, env=dict(os.environ, HOME="/srv/YOUR_LOCAL_USERNAME"))

    def test_distinct_local_and_remote_accounts(self):
        result = self.render("/home/YOUR_USERNAME/mnt/peer -fstype=nfs4 peer:/home/YOUR_USERNAME\n",
                             "--kind", "client", "--remote-home", "/srv/YOUR_REMOTE_USERNAME")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "/srv/YOUR_LOCAL_USERNAME/mnt/peer  -fstype=nfs4  peer:/srv/YOUR_REMOTE_USERNAME\n")

    def test_export_home_override(self):
        result = self.render("/home/YOUR_USERNAME peer(ro)\n", "--kind", "server", "--local-home", "/srv/YOUR_EXPORT_USERNAME")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "/srv/YOUR_EXPORT_USERNAME  peer(ro)\n")

    def test_invalid_homes_emit_no_partial_fragment(self):
        for home in ("relative", "/", "/srv/space name", "/srv/name:other", "/srv/name#other"):
            with self.subTest(home=home):
                result = self.render("/home/YOUR_USERNAME peer(ro)\n", "--kind", "server", "--local-home", home)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")

    def test_bad_later_row_emits_no_partial_fragment(self):
        result = self.render("/home/YOUR_USERNAME peer(ro)\nbad\n", "--kind", "server")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

if __name__ == "__main__":
    unittest.main()

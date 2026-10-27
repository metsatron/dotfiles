import importlib.machinery
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
m = importlib.machinery.SourceFileLoader('commons', str(ROOT / 'all/.local/bin/dotcortex-code-commons')).load_module()


class CommonsTests(unittest.TestCase):
    def test_external_links_and_existing_hardlinks_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);source=root/'source';source.mkdir()
            (source/'external').symlink_to('/etc/passwd')
            with self.assertRaises(m.Refused):m.scan(source)
            (source/'external').unlink()
            (root/'outside').write_text('mutable outside')
            os.link(root/'outside',source/'linked')
            with self.assertRaises(m.Refused):m.scan(source)

    @unittest.skipUnless(os.geteuid() == 0, 'root needed for immutable publisher custody fixture')
    def test_sharing_preserves_abi_layout_and_refuses_drift_and_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);a=root/'a';b=root/'b';a.mkdir();b.mkdir()
            for source in [a,b]:(source/'shared').write_bytes(b'identical public bytes')
            (a/'native.so').write_bytes(b'ABI-A');(b/'native.so').write_bytes(b'ABI-B')
            (a/'alias').symlink_to('shared')
            def fixture_store(path):path.mkdir(parents=True,exist_ok=True);path.chmod(0o755)
            with patch.object(m,'trusted_directory',side_effect=fixture_store):
                one=m.publish(m.scan(a),'abi-a',root/'store')
                two=m.publish(m.scan(b),'abi-b',root/'store')
                x=Path(one['tree']);y=Path(two['tree'])
                self.assertEqual((x/'shared').stat().st_ino,(y/'shared').stat().st_ino)
                self.assertNotEqual((x/'native.so').stat().st_ino,(y/'native.so').stat().st_ino)
                self.assertEqual((x/'shared').stat().st_mode & 0o222,0)
                self.assertEqual((x/'alias').read_bytes(),b'identical public bytes')
                with self.assertRaises(m.Refused):m.publish(m.scan(a),'abi-a',root/'store')
                plan=m.scan(a);(a/'shared').write_bytes(b'new source')
                with self.assertRaises(m.Refused):m.publish(plan,'drift',root/'store')


if __name__ == '__main__':unittest.main()

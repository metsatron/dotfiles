import argparse
import fcntl
import importlib.machinery
import io
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
m = importlib.machinery.SourceFileLoader('pip_hygiene', str(ROOT / 'all/.local/bin/dotcortex-pip-cache-maintenance')).load_module()


class PipHygieneTests(unittest.TestCase):
    def fixture(self, root):
        home = root / 'selected';cache = home / '.cache/pip'
        cache.mkdir(parents=True)
        (cache / 'download').write_bytes(b'x' * 128)
        other = root / 'unselected/.cache/pip';other.mkdir(parents=True)
        (other / 'keeper').write_text('preserve')
        account = argparse.Namespace(pw_dir=str(home),pw_uid=os.getuid(),pw_gid=os.getgid(),pw_name='selected')
        return account, cache, other

    def test_allowlist_selects_only_named_accounts(self):
        account = argparse.Namespace(pw_uid=1234,pw_name='selected')
        config = dict(accounts=['selected'],max_bytes=1,quiet_hours=24)
        with patch.object(m,'config_read',return_value=(io.StringIO(),config)),patch.object(m.pwd,'getpwnam',return_value=account) as passwd,patch.object(m,'run_account',return_value=0) as run,patch.object(m.sys,'argv',['helper','--dry-run']):
            self.assertEqual(m.main(),0)
            passwd.assert_called_once_with('selected')
            run.assert_called_once_with(account,config,True)

    def test_threshold_quiet_dry_run_and_native_purge(self):
        with tempfile.TemporaryDirectory() as tmp:
            account,cache,other = self.fixture(Path(tmp))
            def native(python,home,args):
                return argparse.Namespace(returncode=0,stdout=str(cache))
            with patch.object(m,'active_installer',return_value=False),patch.object(m,'pip_run',side_effect=native) as run:
                self.assertIn('below size cap',m.maintain(account,dict(max_bytes=1024,quiet_hours=24),True))
                self.assertIn('not quiet',m.maintain(account,dict(max_bytes=1,quiet_hours=24),True))
                with patch.object(m.time,'time',return_value=time.time()+48*3600):
                    self.assertIn('would purge',m.maintain(account,dict(max_bytes=1,quiet_hours=24),True))
                    self.assertFalse((Path(account.pw_dir)/'.local').exists())
                    self.assertTrue(all('purge' not in call.args[2] for call in run.call_args_list))
                    self.assertIn('purged',m.maintain(account,dict(max_bytes=1,quiet_hours=24),False))
                self.assertEqual(run.call_args.args[2],['--cache-dir',str(cache),'cache','purge'])
                self.assertEqual((other/'keeper').read_text(),'preserve')
                self.assertTrue((cache/'download').exists())  # mocked native command only

    def test_active_installer_and_busy_managed_lock_skip_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            account,cache,_ = self.fixture(Path(tmp))
            with patch.object(m,'active_installer',return_value=True),patch.object(m,'pip_run') as run:
                self.assertIn('active pip installer',m.maintain(account,dict(max_bytes=1,quiet_hours=24),True))
                run.assert_not_called()
            with m.installer_lock(Path(account.pw_dir),account.pw_uid,False):
                with self.assertRaises(BlockingIOError):
                    with m.installer_lock(Path(account.pw_dir),account.pw_uid,True):pass
            proc=Path(tmp)/'proc';(proc/'123').mkdir(parents=True)
            (proc/'123/cmdline').write_bytes(b'python3\0-m\0pip\0download\0package\0')
            self.assertTrue(m.active_installer(account.pw_uid,proc))
            (proc/'123/cmdline').write_bytes(b'python3\0application.py\0')
            self.assertFalse(m.active_installer(account.pw_uid,proc))

    def test_redirects_wrong_owners_and_custom_destinations_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            account,cache,_ = self.fixture(Path(tmp))
            with patch.object(m,'active_installer',return_value=False),patch.object(m,'pip_run',return_value=argparse.Namespace(returncode=0,stdout='/different/cache')):
                with self.assertRaises(m.Refused):m.maintain(account,dict(max_bytes=1,quiet_hours=24),True)
            (cache/'external').symlink_to('/etc/passwd')
            with self.assertRaises(m.Refused):m.measure(cache,account.pw_uid)
            (cache/'external').unlink()
            (cache/'download').unlink();cache.rmdir();cache.symlink_to(Path(tmp)/'unselected/.cache/pip')
            with self.assertRaises(m.Refused):m.cache_root(account)
            account.pw_uid += 10000
            with self.assertRaises(m.Refused):m.cache_root(account)
            account.pw_uid=0
            with self.assertRaises(m.Refused):m.cache_root(account)


if __name__ == '__main__':unittest.main()

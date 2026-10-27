import argparse
import importlib.machinery
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
loader = importlib.machinery.SourceFileLoader('deps', str(ROOT / 'all/.local/bin/dotcortex-deps'))
d = loader.load_module()
POLICY = {'schema': 1, 'user_site': {'forbidden': ['torch', 'triton', 'nvidia-*', 'cuda-*', 'openai-whisper', 'faster-whisper']}}


class DependencyTests(unittest.TestCase):
    def test_frozen_user_site_stops_before_resolver(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);site=home/'.local/lib/python3.13/site-packages'
            site.parent.mkdir(parents=True);site.symlink_to(home/'frozen')
            args=argparse.Namespace(python='python3',manifest=None,apply=True)
            with patch.object(d.Path,'home',return_value=home), patch.object(d,'python_identity',return_value={'version':[3,13,0]}), patch.object(d.subprocess,'run') as run:
                with self.assertRaises(d.Refused):d.pip_apply(args,POLICY,home)
                run.assert_not_called()

    def test_transitive_gpu_rejected_before_install(self):
        for name in ['torch', 'NVIDIA_CUBLAS_CU13', 'cuda-toolkit', 'triton']:
            with self.subTest(name=name), self.assertRaises(d.Refused):
                d.locked_report({'version': '1', 'install': [{'metadata': {'name': name}}]}, POLICY)

    def test_wheel_plan_pins_artifact_and_rejects_unlocked_sources(self):
        item = {'metadata': {'name': 'Example_Pkg'}, 'download_info': {
            'url': 'https://example.invalid/pkg.whl', 'archive_info': {'hashes': {'sha256': 'a' * 64}}}}
        lock = d.locked_report({'version': '1', 'install': [item]}, POLICY)
        self.assertEqual(lock, ['example-pkg @ https://example.invalid/pkg.whl --hash=sha256:' + 'a' * 64])
        for url in ['https://example.invalid/pkg.tar.gz', 'https://user:secret@example.invalid/pkg.whl', 'file:///tmp/pkg.whl']:
            item['download_info']['url'] = url
            with self.assertRaises(d.Refused):
                d.locked_report({'version': '1', 'install': [item]}, POLICY)

    def test_inventory_is_bounded_and_reports_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'user';home.mkdir()
            for version in ['3.12', '3.13']:
                path = home / '.local/lib' / ('python' + version) / 'site-packages/example-1.dist-info'
                path.mkdir(parents=True);(path / 'METADATA').write_text('Name: example\nVersion: 1\n')
            # A link outside the home is never followed.
            (home / '.local/lib/python3.14').symlink_to('/unreachable-fleet-path')
            result = d.inventory([str(home)], POLICY)
            self.assertEqual(len(result['packages']), 2)
            self.assertEqual(len(result['repeated']), 1)
            self.assertTrue(result['complete'])
        with self.assertRaises(d.Refused):
            d.local_home('/home')

    def test_permission_gap_is_not_clean_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'user';(home / '.local/lib').mkdir(parents=True)
            original = Path.iterdir
            def denied(path):
                if path == home / '.local/lib':raise PermissionError('fixture')
                return original(path)
            with patch.object(Path, 'iterdir', denied):
                self.assertFalse(d.inventory([str(home)], POLICY)['complete'])

    def test_changed_or_failed_interpreter_receipt_stops_before_resolver(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp);manifest=tmp/'manifest.ssv';manifest.write_text('example "" ""\n')
            state = tmp / 'dotcortex/dependencies';state.mkdir(parents=True)
            args = argparse.Namespace(python='python3',manifest=manifest,apply=True)
            for status, identity in [('incomplete', {'version': [3,13,0]}), ('complete', {'version': [3,12,0]})]:
                (state/'user-site.json').write_text(json.dumps({'status': status, 'python': identity}))
                with patch.dict(d.os.environ, {'XDG_STATE_HOME':str(tmp)}), patch.object(d,'python_identity',return_value={'executable':'/usr/bin/python3','version':[3,13,0]}), patch.object(d.subprocess,'run',return_value=argparse.Namespace(stdout='{}')) as run:
                    with self.assertRaises(d.Refused):d.pip_apply(args,POLICY,tmp)
                    self.assertEqual(run.call_count,1)
                    self.assertIn('-c',run.call_args.args[0])

    def test_backend_conflict_rejected_before_runtime_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);(tmp/'lock.txt').write_text('nvidia-cublas-cu13==1 --hash=sha256:'+'a'*64+'\n')
            policy={**POLICY,'runtimes':{'speech':{'python':'python3','backend':'cpu','lock':'lock.txt'}}}
            with self.assertRaises(d.Refused):d.runtime_spec(policy,'speech',tmp)
            policy['runtimes']['speech']['lock']='../escape.txt'
            with self.assertRaises(d.Refused):d.runtime_spec(policy,'speech',tmp)

    def test_runtime_build_reuses_generation_and_keeps_permanent_shebang(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'lock.txt').write_text('example==1 --hash=sha256:'+'a'*64+'\n')
            policy={**POLICY,'runtimes':{'speech':{'python':'python3','backend':'none','lock':'lock.txt'}}}
            args=argparse.Namespace(name='speech',store=root/'store')
            def fake_run(argv, **kwargs):
                if 'venv' in argv:
                    target=Path(argv[-1]);(target/'bin').mkdir();(target/'bin/python').symlink_to('/usr/bin/python3')
                    (target/'bin/example').write_text('#!'+str(target/'bin/python')+'\n')
                return None
            # Test directories sit under /tmp; production deliberately refuses world-writable ancestry.
            def local_store(path):path.mkdir(parents=True,exist_ok=True)
            with patch.object(d,'trusted_store',side_effect=local_store),patch.object(d,'python_identity',return_value={'executable':'/usr/bin/python3','version':[3,13,0]}),patch.object(d.shutil,'which',return_value='/usr/bin/uv'),patch.object(d.subprocess,'run',side_effect=fake_run) as run:
                d.runtime_build(args,policy,root)
                target=(args.store/'speech/current').resolve()
                self.assertIn(str(target/'bin/python'),(target/'bin/example').read_text())
                self.assertEqual(target.stat().st_mode & 0o222,0)
                self.assertEqual(run.call_count,2)
                d.runtime_build(args,policy,root)
                self.assertEqual(run.call_count,2)
                self.assertIn('--require-hashes',run.call_args_list[1].args[0])
                self.assertIn('--strict',run.call_args_list[1].args[0])

    def test_source_build_is_never_executed_during_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'manifest.ssv';path.write_text('example "" "git+https://example.invalid/repo"\n')
            with self.assertRaises(d.Refused):d.manifest_requirements(path,POLICY)
            self.assertEqual(d.manifest_requirements(path,POLICY,{'example':'1'}),['example==1'])

    def test_full_pip_gate_installs_only_the_accepted_wheel_lock(self):
        for package in ['example', 'nvidia-cublas-cu13']:
            with self.subTest(package=package),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);manifest=root/'manifest.ssv';manifest.write_text('example "" ""\n')
                args=argparse.Namespace(python='python3',manifest=manifest,apply=True)
                commands=[]
                def run(argv,**kwargs):
                    commands.append(argv)
                    if '--report' in argv:
                        Path(argv[argv.index('--report')+1]).write_text(json.dumps({'version':'1','install':[{'metadata':{'name':package},'download_info':{'url':'https://example.invalid/example.whl','archive_info':{'hashes':{'sha256':'a'*64}}}}]}))
                    if '--require-hashes' in argv:
                        self.assertIn('--no-deps',argv)
                        lock=Path(argv[-1]).read_text();self.assertIn('--hash=sha256:',lock)
                    return argparse.Namespace(stdout='{}')
                with patch.dict(d.os.environ,{'XDG_STATE_HOME':str(root)}),patch.object(d,'python_identity',return_value={'executable':'/usr/bin/python3','version':[3,13,0]}),patch.object(d.subprocess,'run',side_effect=run):
                    if package.startswith('nvidia'):
                        with self.assertRaises(d.Refused):d.pip_apply(args,POLICY,root)
                        self.assertFalse(any('--require-hashes' in c for c in commands))
                    else:
                        d.pip_apply(args,POLICY,root)
                        receipt=json.loads((root/'dotcortex/dependencies/user-site.json').read_text())
                        self.assertEqual(receipt['status'],'complete')
                        self.assertEqual(sum('--report' in c for c in commands),1)

    def test_untrusted_shared_store_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(d.Refused):d.trusted_store(Path(tmp)/'shared')

    def test_loom_canonical_apply_uses_guarded_lane(self):
        source=(ROOT/'loom.org').read_text()
        segment=source.split("(task 'pip:apply",1)[1].split("(task 'pip:health",1)[0]
        self.assertIn('dotcortex-deps',segment)
        self.assertIn('pip-apply --apply',segment)
        for verb in ['deps:report','pip:plan','deps:test']:
            self.assertIn("(task '"+verb,source)


if __name__ == '__main__':unittest.main()

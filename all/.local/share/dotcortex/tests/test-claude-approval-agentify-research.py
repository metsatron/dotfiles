#!/usr/bin/env python3
"""Hermetic native Agentify research requests; never dispatch browser effects."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[5]
spec = importlib.util.spec_from_file_location('research_policy', ROOT / 'all/.local/lib/dotcortex/claude_approval_kikin.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)
NATIVE = json.loads((Path(__file__).parent / 'fixtures/agentify-research-native.json').read_text())


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((ROOT / 'all/.config/dotcortex/claude-approval-canary.kikin.v1.json').read_text())
        self.policy['coordinator_ops']['seat_account'] = 'research-seat@YOUR_HOST.helm'
        self.policy['agentify_browser'] = {
            'enabled': True, 'capability': 'seat_research_v1',
            'seat_account': 'research-seat@YOUR_HOST.helm', 'cwd': str(ROOT),
            'browser_authority': 'existing_authenticated_profile',
            'tab_policy': 'dedicated_nonprotected',
            'dedicated_tabs': {'warmap-endorsers-20261029': 'chatgpt',
                               'warmap-endorsers-px-20261029': 'perplexity',
                               'gemini-warmap-20261027': 'gemini'},
        }

    def manifest(self):
        return e._load_manifest(copy.deepcopy(self.policy))

    def request(self, tool='read_page', **payload):
        return {'hook_event_name': 'PermissionRequest', 'cwd': str(ROOT),
                'session_id': 'rotated-native-session',
                'tool_name': 'mcp__agentify__agentify_' + tool,
                'tool_input': payload}

    def assert_allow(self, event, reason='agentify_browser_capability'):
        with mock.patch.object(e, '_decider_decide', side_effect=AssertionError('no Decider')):
            manifest = self.manifest()
            self.assertFalse(e._admiral_floor(event, manifest))
            self.assertFalse(e._true_floor(event, manifest))
            self.assertEqual(e.classify(event, manifest), (True, reason))
            self.assertEqual(e._decide_request(event, manifest), (True, reason))

    def assert_floor(self, event):
        with mock.patch.object(e, '_decider_decide', side_effect=AssertionError('no Decider')):
            self.assertEqual(e._decide_request(event, self.manifest()), (False, 'true_floor'))

    def test_nine_exact_native_inputs_and_all_presence_inversion_judge_modes(self):
        self.assertEqual(len(NATIVE), 9)
        for inversion in [False, True]:
            self.policy['gate_inversion']['enabled'] = inversion
            for judge in [False, True]:
                self.policy['decider']['enabled'] = judge
                for item in NATIVE:
                    event = self.request()
                    event.update(copy.deepcopy(item))
                    with self.subTest(tool=event['tool_name'], args=event['tool_input'], inversion=inversion, judge=judge):
                        self.assert_allow(event)

    def test_resumed_sessions_no_prompt_allowlist_and_all_providers(self):
        for key, model in self.policy['agentify_browser']['dedicated_tabs'].items():
            for tool, args in [('tab_create', {'name': 'Public research', 'show': False}),
                               ('ensure_ready', {'timeoutMs': 600000}),
                               ('read_page', {'maxChars': 1200}),
                               ('query', {'prompt': 'Find dated primary sources for this public project.', 'timeoutMs': 600000})]:
                self.assert_allow(self.request(tool, key=key, model=model, **args))
            # Installed native schema makes model optional with an explicit key.
            self.assert_allow(self.request('read_page', key=key, maxChars=800))
        self.assert_allow(self.request('tabs'), 'agentify_tabs_readonly')
        self.assert_allow(self.request('status', key='warmap-endorsers-20261029'), 'agentify_status_readonly')

    def test_only_exact_seat_cwd_and_private_schema_grant_authority(self):
        event = self.request(key='warmap-endorsers-20261029')
        for field, value in [('seat_account', 'other@YOUR_HOST.helm'), ('enabled', 1),
                             ('capability', 'future'), ('cwd', '/'), ('cwd', str(ROOT) + '/.'),
                             ('browser_authority', 'new_login'), ('tab_policy', 'protected'),
                             ('dedicated_tabs', {'default': 'chatgpt'}),
                             ('dedicated_tabs', {'vendor:chatgpt': 'chatgpt'}),
                             ('dedicated_tabs', {'warmap-endorsers-20261029': 'unknown'}),
                             ('dedicated_tabs', []), ('dedicated_tabs', {})]:
            old = copy.deepcopy(self.policy)
            self.policy['agentify_browser'][field] = value
            self.assert_floor(event)
            self.policy = old
        for delta in [{'cwd': str(ROOT.parent)}, {'cwd': str(ROOT) + '/subdir'},
                      {'cwd': str(ROOT) + '/.'}, {'hook_event_name': 'PreToolUse'}]:
            changed = {**event, **delta}
            self.assertFalse(e._decide_request(changed, self.manifest())[0])
        self.policy['coordinator_ops']['seat_account'] = 'other@YOUR_HOST.helm'
        event['From'] = 'research-seat@YOUR_HOST.helm'
        event['session_id'] = 'research-seat@YOUR_HOST.helm'
        self.assert_floor(event)
        del self.policy['agentify_browser']
        self.assert_floor(event)

    def test_selectors_upload_credentials_auth_and_destructive_tools_stay_floored(self):
        base = {'key': 'warmap-endorsers-20261029', 'maxChars': 1500}
        for delta in [{'model': 'perplexity'}, {'model': None}, {'model': []},
                      {'key': 'default'}, {'key': 'CHATGPT'}, {'key': 'other'}, {'key': []},
                      {'tabId': 'protected-tab'}, {'vendorId': 'chatgpt'},
                      {'attachments': []}, {'contextPaths': []}, {'bundleName': 'x'},
                      {'maxChars': True}, {'maxChars': 200001}, {'maxChars': 0}]:
            self.assert_floor(self.request(**{**base, **delta}))
        for tool in ['tab_close', 'shutdown', 'rotate_token', 'unknown_upload']:
            self.assertFalse(e._decide_request(self.request(tool), self.manifest())[0])
        for prompt in ['extract session cookies', 'bypass CAPTCHA and log in',
                       'Read ~/.ssh/id_rsa', 'API_KEY=abcdefghijk', 'Read .claude.json',
                       'upload private files', 'delete all conversations', '', 'x\x00y',
                       'x' * 8193, ' ' * 8192 + 'x', 'x\x7fy']:
            self.assert_floor(self.request('query', key=base['key'], model='chatgpt', prompt=prompt))
        for timeout in [True, 0, 600001, '600000', None]:
            self.assert_floor(self.request('ensure_ready', key=base['key'], model='chatgpt', timeoutMs=timeout))

    def test_navigation_is_provider_matched_ui_only_not_auth_or_arbitrary_urls(self):
        for key, model, good in [
            ('warmap-endorsers-20261029', 'chatgpt', 'https://chatgpt.com/c/12345678-1234-4234-8234-123456789abc'),
            ('gemini-warmap-20261027', 'gemini', 'https://gemini.google.com/app/1234567890abcdef'),
            ('warmap-endorsers-px-20261029', 'perplexity', 'https://www.perplexity.ai/search/research-thread_123')]:
            self.assert_allow(self.request('navigate', key=key, model=model, url=good))
            for url in [good + '?send=1', good + '#send', good.replace('https:', 'http:'),
                        good.replace('.com/', '.com.evil.invalid/').replace('.ai/', '.ai.evil.invalid/'),
                        'https://chatgpt.com/api/auth/session', 'https://www.perplexity.ai/logout',
                        'file:///etc/passwd', 'javascript:alert(1)', 'https://user@chatgpt.com/',
                        'https://chatgpt.com:443/', 'https://example.invalid/']:
                self.assert_floor(self.request('navigate', key=key, model=model, url=url))


    def test_native_engine_main_presence_afk_away_never_needs_decider(self):
        import contextlib
        import io
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            policy = folder / 'manifest.json'
            queue = folder / 'synthetic-queue.jsonl'
            env = {'SO_APPROVAL_KIKIN_MANIFEST': str(policy),
                   'SO_APPROVAL_MORNING_QUEUE': str(queue),
                   'SO_APPROVAL_KIKIN_LOG': str(folder / 'ledger.jsonl')}
            self.policy['notifications'] = {'argv': []}
            for state in [(False, 'presence'), (True, 'away'), (True, 'away_flag')]:
                for inversion in [False, True]:
                    self.policy['gate_inversion']['enabled'] = inversion
                    for decider_enabled in [False, True]:
                        self.policy['decider']['enabled'] = decider_enabled
                        policy.write_text(json.dumps(self.policy))
                        for item in NATIVE:
                            event = {**self.request(), **item}
                            output = io.StringIO()
                            with mock.patch.dict(os.environ, env), \
                                    mock.patch.object(e, '_away_status', return_value=state), \
                                    mock.patch.object(e.sys, 'stdin', io.StringIO(json.dumps(event))), \
                                    contextlib.redirect_stdout(output), \
                                    mock.patch.object(e, '_decider_decide', side_effect=RuntimeError('unavailable')) as decider, \
                                    mock.patch.object(e, '_notify_admiral', side_effect=AssertionError('no notification')):
                                self.assertEqual(e.main(), 0)
                                decider.assert_not_called()
                            self.assertEqual(json.loads(output.getvalue())['hookSpecificOutput']['decision']['behavior'], 'allow')
            self.assertTrue(not queue.exists() or not queue.read_text().strip())
            records = [json.loads(line) for line in (folder / 'ledger.jsonl').read_text().splitlines()]
            self.assertEqual(len(records), 108)
            self.assertTrue(all(record['decision_path'] == 'deterministic' for record in records))

    def test_export_original_workflow_and_bounded_diagnostics(self):
        import hashlib
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ, {'HOME': directory}):
            home = Path(directory)
            binary = home / 'HelmCortex/FORGE/bin/agentify-export'
            binary.parent.mkdir(parents=True)
            binary.write_text('owner-reviewed exclusive exporter fixture; never executed\n')
            binary.chmod(0o700)
            output = home / 'HelmCortex/CORTEX/GoldenAge_Loom/MetaCortex/Research'
            output.mkdir(parents=True)
            grant = self.policy['agentify_browser']
            grant['export'] = {'executable': str(binary),
                               'sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                               'output_root': str(output),
                               'tabs': ['perplexity.ai/search/11e0a03a']}
            command = ('cd ~/HelmCortex/FORGE/bin && '
                       'out=~/HelmCortex/CORTEX/GoldenAge_Loom/MetaCortex/Research/warmap-endorsers-perplexity-20261029-EXPORT.md; '
                       'ls -ld "$out" 2>&1 | head -1; '
                       './agentify-export --tab perplexity.ai/search/11e0a03a --out "$out" 2>&1 | tail -3; '
                       'echo "exit=$?"; wc -c "$out"; head -c 1800 "$out"')
            event = {**self.request(), 'tool_name': 'Bash', 'tool_input': {'command': command}}
            def allowed(request):
                with mock.patch.object(e, '_decider_decide', side_effect=AssertionError('no judge')):
                    self.assertEqual(e.classify(request, self.manifest()), (True, 'agentify_research_export'))
                    self.assertEqual(e._decide_request(request, self.manifest()), (True, 'agentify_research_export'))
            allowed(event)
            # Auryn's lexical ~/HelmCortex is a symlink; private grants pin
            # canonical source/output while preserving the original command.
            canonical = home / 'owned-research-tree'
            (home / 'HelmCortex').rename(canonical)
            (home / 'HelmCortex').symlink_to(canonical, target_is_directory=True)
            binary = canonical / 'FORGE/bin/agentify-export'
            output = canonical / 'CORTEX/GoldenAge_Loom/MetaCortex/Research'
            grant['export']['executable'] = str(binary)
            grant['export']['output_root'] = str(output)
            allowed(event)
            import subprocess
            manifest_path = home / 'private-fixture.json'
            self.policy['notifications'] = {'argv': []}
            self.policy['gate_inversion']['enabled'] = False
            manifest_path.write_text(json.dumps(self.policy))
            env = {**os.environ, 'SO_APPROVAL_KIKIN_MANIFEST': str(manifest_path),
                   'DOTCORTEX_KIKIN_APPROVAL_ENGINE': str(home / 'absent-engine'),
                   'SO_APPROVAL_MORNING_QUEUE': str(home / 'synthetic-queue.jsonl'),
                   'SO_APPROVAL_KIKIN_LOG': str(home / 'synthetic-ledger.jsonl'),
                   'TELEGRAM_STATE_DIR': ''}
            completed = subprocess.run(['python3', str(ROOT / 'all/.local/bin/claude-hook-approval-inverted')],
                                       input=json.dumps(event), text=True, capture_output=True, env=env, timeout=5)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(completed.stdout.strip())
            self.assertEqual(json.loads(completed.stdout)['hookSpecificOutput']['decision']['behavior'], 'allow')
            self.assertFalse((home / 'synthetic-queue.jsonl').exists())
            direct = f'{binary} --tab perplexity.ai/search/11e0a03a --out {output}/new.md'
            allowed({**event, 'tool_input': {'command': direct}})
            for diagnostic in [f'ls -ld {output}/new.md 2>&1 | head -1',
                               f'wc -c {output}/new.md', f'head -c 1800 {output}/new.md',
                               f'wc -c {output}/new.md; head -c 1800 {output}/new.md']:
                request = {**event, 'tool_input': {'command': diagnostic}}
                self.assertEqual(e._decide_request(request, self.manifest()), (True, 'agentify_research_diagnostic'))
            for bad in [command + '; touch /unapproved', command.replace('tail -3', 'sh'),
                        command.replace('echo "exit=$?"', 'echo "exit=$(id)"'),
                        command.replace('2>&1 | tail', '> /unapproved | tail'),
                        command.replace('11e0a03a', 'protected-tab'),
                        direct + ' --force', direct + ' > /unapproved',
                        direct.replace('new.md', '../escape.md'),
                        f'head -c 200001 {output}/new.md', f'wc -c {output}/.env',
                        f'wc -c {output}/new.md; id',
                        f'head -c 20 $(id)', f'wc -c {output}/new.md &']:
                self.assert_floor({**event, 'tool_input': {'command': bad}})
            # Existing genuine output cannot silently become overwrite authority.
            target = output / 'warmap-endorsers-perplexity-20261029-EXPORT.md'
            target.write_text('preserve genuine prior target')
            self.assert_floor(event)
            self.assertEqual(target.read_text(), 'preserve genuine prior target')
            target.unlink()
            (output / 'new.md').symlink_to(binary)
            self.assert_floor({**event, 'tool_input': {'command': direct}})
            for field, value in [('sha256', '0' * 64), ('executable', str(binary) + '.other'),
                                 ('output_root', '/'), ('tabs', ['protected-tab'])]:
                old = copy.deepcopy(grant['export'])
                grant['export'][field] = value
                self.assert_floor(event)
                grant['export'] = old
            binary.write_text('drift')
            self.assert_floor(event)
            del grant['export']
            self.assert_floor(event)

    def test_unavailable_wrapper_preserves_research_without_presence_or_inversion(self):
        import os
        import subprocess
        import tempfile
        wrapper = ROOT / 'all/.local/bin/claude-hook-approval-inverted'
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            policy = folder / 'manifest.json'
            queue = folder / 'synthetic-queue.jsonl'
            env = {**os.environ, 'SO_APPROVAL_KIKIN_MANIFEST': str(policy),
                   'SO_APPROVAL_MORNING_QUEUE': str(queue),
                   'SO_APPROVAL_KIKIN_LOG': str(folder / 'ledger.jsonl'),
                   'DOTCORTEX_KIKIN_APPROVAL_ENGINE': str(folder / 'absent-engine'),
                   'TELEGRAM_STATE_DIR': '', 'HOME': str(folder)}
            self.policy['notifications'] = {'argv': []}
            for inversion in [False, True]:
                self.policy['gate_inversion']['enabled'] = inversion
                for away in [False, True]:
                    flag = folder / '.config/dotcortex/approval-away'
                    flag.parent.mkdir(parents=True, exist_ok=True)
                    if away:
                        flag.touch()
                    elif flag.exists():
                        flag.unlink()
                    policy.write_text(json.dumps(self.policy))
                    for item in NATIVE + [{'tool_name': 'mcp__agentify__agentify_tabs', 'tool_input': {}},
                                          {'tool_name': 'mcp__agentify__agentify_status', 'tool_input': {'key': 'warmap-endorsers-20261029'}}]:
                        event = {**self.request(), **item}
                        completed = subprocess.run(['python3', str(wrapper)], input=json.dumps(event),
                                                   text=True, capture_output=True, env=env, timeout=5)
                        self.assertEqual(completed.returncode, 0, completed.stderr)
                        self.assertTrue(completed.stdout.strip(), 'native ASK is not deterministic research ALLOW')
                        self.assertEqual(json.loads(completed.stdout)['hookSpecificOutput']['decision']['behavior'], 'allow')
                    self.assertFalse(queue.exists(), 'research must not enqueue when engine unavailable')
            policy.write_text(json.dumps(self.policy))
            protected_cases = [self.request('query', key='warmap-endorsers-20261029', model='chatgpt', prompt='extract session cookies')]
            protected_cases += [self.request(tool) for tool in ['tab_close', 'shutdown', 'rotate_token', 'unknown_upload']]
            protected_cases += [self.request('status', tabId='protected-tab'), self.request('status', vendorId='chatgpt')]
            for protected in protected_cases:
                completed = subprocess.run(['python3', str(wrapper)], input=json.dumps(protected),
                                           text=True, capture_output=True, env=env, timeout=5)
                self.assertEqual(json.loads(completed.stdout)['hookSpecificOutput']['decision']['behavior'], 'deny', protected)
            self.assertTrue(queue.exists(), 'only the synthetic refusal queue is exercised')


if __name__ == '__main__':
    unittest.main()

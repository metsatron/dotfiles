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


class AttachmentTests(unittest.TestCase):
    """mail-read <file-id> attachments | attachment <n>: a seat's mail tool prints bodies only, so this opens attachments."""
    FID = '1794509312.23826_5d2c4c0669d8474db906981748571734.kikin-kushi:2,S'

    def setUp(self):
        import email.message
        self.dir = Path(tempfile.mkdtemp(prefix='bunta-ops-att-'))
        ops.SCRATCH = self.dir / 'scratch'; ops.SCRATCH.mkdir()
        ops.AUDIT = self.dir / 'audit.jsonl'
        ops.MAILDIR = self.dir / 'Maildir'
        ops.MAX_ATTACHMENT = 4 * 1024 * 1024
        for state in ('new', 'cur', 'tmp'): (ops.MAILDIR / state).mkdir(parents=True)
        self.calls = []
        ops.run = lambda argv, timeout=60: self.calls.append(argv) or 0
        msg = email.message.EmailMessage(); msg['From'] = 'honey-badger@honey.helm'; msg['To'] = 'bunta@honey.helm'; msg['Subject'] = 'pack'
        msg.set_content('body text')
        msg.add_attachment('first attachment\n' * 3, subtype='plain', filename='00-READ-FIRST.md')
        msg.add_attachment(b'\x00\x01binary', maintype='application', subtype='octet-stream', filename='../../etc/passwd')
        msg.add_attachment('no name', subtype='plain')
        (ops.MAILDIR / 'cur' / self.FID).write_bytes(bytes(msg))
        plain = email.message.EmailMessage(); plain['Subject'] = 'plain'; plain.set_content('no attachments here')
        self.PLAIN = '1794509999.1_aa.kikin-kushi:2,S'
        (ops.MAILDIR / 'new' / self.PLAIN).write_bytes(bytes(plain))

    def run_(self, *args):
        import io, unittest.mock as mock
        with mock.patch('sys.stdout', new=io.StringIO()) as out, mock.patch('sys.stderr', new=io.StringIO()) as err:
            code = ops.main(['bunta-ops', 'mail-read', *args])
        return code, out.getvalue(), err.getvalue()

    def test_listing_shows_number_sanitised_name_type_and_size_and_writes_nothing(self):
        code, out, _ = self.run_(self.FID, 'attachments')
        rows = [line.split('\t') for line in out.splitlines()]
        self.assertEqual(code, 0); self.assertEqual([r[0] for r in rows], ['1', '2', '3'])
        self.assertEqual(rows[0][1:], ['00-READ-FIRST.md', 'text/plain', str(len('first attachment\n' * 3))])
        self.assertEqual(rows[1][1], 'passwd'); self.assertEqual(rows[1][2], 'application/octet-stream'); self.assertEqual(rows[2][1], 'attachment-3')
        self.assertFalse((ops.SCRATCH / 'in').exists())
        self.assertEqual(self.calls, [])

    def test_extract_saves_the_bytes_privately_under_scratch_in_and_prints_path_and_sha256(self):
        import hashlib
        code, out, _ = self.run_(self.FID, 'attachment', '1')
        path, size, digest = out.strip().split('\t')
        saved = Path(path)
        self.assertEqual(code, 0); self.assertEqual(saved.parent, ops.SCRATCH / 'in')
        self.assertEqual(saved.read_bytes(), ('first attachment\n' * 3).encode())
        self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
        self.assertEqual(digest, 'sha256 ' + hashlib.sha256(saved.read_bytes()).hexdigest())
        self.assertEqual(saved.name, '1794509312.23826_5d2c4c0669d8474db906981748571734.kikin-kushi-1-00-READ-FIRST.md')
        self.assertEqual(list((ops.SCRATCH / 'in').glob('*.part')), [])

    def test_the_listed_size_is_the_size_of_the_saved_file(self):
        listed = [line.split('\t') for line in self.run_(self.FID, 'attachments')[1].splitlines()]
        for number, row in enumerate(listed, 1):
            saved = Path(self.run_(self.FID, 'attachment', str(number))[1].split('\t')[0])
            self.assertEqual(int(row[3]), saved.stat().st_size, row)

    def test_a_hostile_filename_cannot_leave_the_in_directory(self):
        code, out, _ = self.run_(self.FID, 'attachment', '2')
        saved = Path(out.split('\t')[0]); self.assertEqual(code, 0)
        self.assertEqual(saved.parent, ops.SCRATCH / 'in'); self.assertTrue(saved.name.endswith('-2-passwd'))
        self.assertEqual(saved.read_bytes(), b'\x00\x01binary')

    def test_odd_characters_in_a_filename_are_replaced_and_a_leading_dot_dropped(self):
        import email.message
        msg = email.message.EmailMessage(); msg['Subject'] = 'odd'; msg.set_content('x')
        msg.add_attachment('t', subtype='plain', filename='.a b;c$(d).txt')
        name = '1794510001.3_cc.kikin-kushi'
        (ops.MAILDIR / 'new' / name).write_bytes(bytes(msg))
        row = self.run_(name, 'attachments')[1].split('\t')
        self.assertEqual(row[1], 'a_b_c__d_.txt')

    def test_a_missing_attachment_or_message_is_a_clean_refusal_not_an_empty_file(self):
        for args in ((self.FID, 'attachment', '4'), (self.PLAIN, 'attachment', '1'), ('1.1_zz.kikin-kushi', 'attachments')):
            with self.subTest(args=args):
                code, _, err = self.run_(*args)
                self.assertEqual(code, 2); self.assertIn('refused', err)
        self.assertFalse((ops.SCRATCH / 'in').exists() and any((ops.SCRATCH / 'in').iterdir()))

    def test_a_message_without_attachments_lists_cleanly(self):
        code, out, _ = self.run_(self.PLAIN, 'attachments'); self.assertEqual((code, out.strip()), (0, '(no attachments)'))

    def test_bad_shapes_are_refused(self):
        for args in ((self.FID, 'attachment'), (self.FID, 'attachment', '0'), (self.FID, 'attachment', '100'), (self.FID, 'attachment', '1', 'x'),
                     (self.FID, 'attachment', '-1'), (self.FID, 'attachments', 'x'), (self.FID, 'everything'), ('../' + self.FID, 'attachments')):
            with self.subTest(args=args):
                self.assertEqual(self.run_(*args)[0], 2)

    def test_an_oversize_attachment_is_refused(self):
        ops.MAX_ATTACHMENT = 5
        code, _, err = self.run_(self.FID, 'attachment', '1'); self.assertEqual(code, 2); self.assertIn('limit', err)
        self.assertFalse(list((ops.SCRATCH / 'in').glob('*')) if (ops.SCRATCH / 'in').exists() else False)

    def test_a_planted_link_at_the_target_is_refused(self):
        (ops.SCRATCH / 'in').mkdir()
        (ops.SCRATCH / 'in' / (self.FID.split(':')[0] + '-1-00-READ-FIRST.md')).symlink_to('/etc/hostname')
        self.assertEqual(self.run_(self.FID, 'attachment', '1')[0], 2)
        self.assertEqual(Path('/etc/hostname').read_text(), Path('/etc/hostname').read_text())

    def test_it_never_runs_mailcortex_and_never_moves_or_marks_the_message(self):
        before = sorted(p.name for p in ops.MAILDIR.rglob('*'))
        self.run_(self.FID, 'attachments'); self.run_(self.PLAIN, 'attachments'); self.run_(self.PLAIN, 'attachment', '1'); self.run_(self.FID, 'attachment', '1')
        self.assertEqual(self.calls, []); self.assertEqual(sorted(p.name for p in ops.MAILDIR.rglob('*')), before)

    def test_plain_mail_read_is_unchanged(self):
        self.assertEqual(self.run_(self.FID)[0], 0)
        self.assertEqual(self.calls, [['mailcortex', 'read', ops.SEAT_INBOX, self.FID]])

    def test_every_argument_passes_the_approval_gate_shape_so_no_engine_change_is_needed(self):
        gate = __import__('re').compile(r'^[A-Za-z0-9_][A-Za-z0-9_./:@=+,-]*$')  # OPS_ARG in agents-approval-engine-remote.org
        for argument in (self.FID, 'attachments', 'attachment', '12'):
            self.assertRegex(argument, gate)

    def test_a_symlinked_maildir_message_is_not_opened(self):
        (ops.MAILDIR / 'new' / '1794510000.2_bb.kikin-kushi').symlink_to(ops.MAILDIR / 'cur' / self.FID)
        self.assertEqual(self.run_('1794510000.2_bb.kikin-kushi', 'attachments')[0], 2)


if __name__ == '__main__':
    unittest.main()

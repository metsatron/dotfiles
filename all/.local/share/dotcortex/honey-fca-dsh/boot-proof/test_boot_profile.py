#!/usr/bin/python3
"""Real-boot and telemetry-off tests for the sterile FCA DSH worker lane (revision 7, SOURCE candidate; nothing is provisioned).
Runs the REAL launcher as the real worker uid 2012 (NO supplementary groups) in the real bwrap sandbox, on a throwaway copy of the lane
under /tmp whose closure pin is filled in; the production launcher keeps REVIEW_REQUIRED and is never executed. No network, no model,
no credential. Needs passwordless sudo for setpriv and the staged runtime under /home/agent-deepseek. Usage: test_boot_profile.py [LANE_DIR]
LANE_DIR is a tangled lane tree (bin/, fca-synthetic-fixture/); by default the tree is assembled from the files next to this one, with the
two unchanged fixture files taken from DotCortex at the frozen preimage 7fe4080df8."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PREIMAGE = '7fe4080df8'
DOT = '/home/gille/DotCortex'
LANE_REL = 'all/.local/share/dotcortex/honey-fca-dsh/'
STAGE = '/home/agent-deepseek/.local/share/fca-dsh-runtime'
WORKER_HOME = '/home/agent-deepseek'
WORK = tempfile.mkdtemp(prefix='fca-boot-')
os.chmod(WORK, 0o755)

TELEMETRY_ROW = 'session-telemetry-otel'
BOOT_CLOSURE = {  # row id -> package name that reports "pending" when the row is left enabled
    'session-title-llm': '@deepseek-ai/dsh-session-title-first-prompt-llm',
    'plugin-package-inventory-deepseek': '@deepseek-ai/dsh-plugin-package-inventory-deepseek',
    'permission': '@deepseek-ai/dsh-permission-presets',
    'plan-mode': '@deepseek-ai/dsh-plan-mode',
    'compaction-basic': '@deepseek-ai/dsh-compaction-basic',
    'command-compact': '@deepseek-ai/dsh-command-compact',
    'timeout-policy': '@deepseek-ai/dsh-tool-call-timeout-policy',
    'spill-policy': '@deepseek-ai/dsh-spill-policy',
    'session-checkpoint-policy': '@deepseek-ai/dsh-session-checkpoint-policy',
}
# Everything a boot may create under the sterile DSH_HOME (the module farm under node_modules is links only and is not listed).
EXPECTED_DSH_HOME = {
    'profiles/', 'profiles/fca-synthetic/', 'profiles/fca-synthetic/.dsh-module-fallback/',
    'profiles/fca-synthetic/.dsh-module-fallback/node_modules/', 'profiles/fca-synthetic/cordis.patch.yml',
    'profiles/fca-synthetic/cordis.yml', 'profiles/fca-synthetic/node_modules/', 'profiles/fca-synthetic/package.json',
    'profiles/fca-synthetic/pnpm-workspace.yaml', 'profiles/node_modules/', 'storages/',
}
SECRETISH = re.compile(r'credential|setting|spill|token|secret|\.env|key|auth', re.I)
HAVE_RUNTIME = subprocess.run(['sudo', '-n', 'test', '-x', STAGE + '/node/bin/node']).returncode == 0


def read(path):
    with open(path) as handle:
        return handle.read()


def write(path, text):
    with open(path, 'w') as handle:
        handle.write(text)


def git_show(path):
    return subprocess.run(['git', '-C', DOT, 'show', '%s:%s%s' % (PREIMAGE, LANE_REL, path)], capture_output=True, text=True, check=True).stdout


def assemble(dest):
    """Copy a lane tree to dest (bin/, fca-synthetic-fixture/, SOURCE.md)."""
    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        shutil.copytree(sys.argv[1], dest, ignore=shutil.ignore_patterns('__pycache__', 'egress', 'boot-proof'))
    else:
        os.makedirs(dest + '/bin')
        os.makedirs(dest + '/fca-synthetic-fixture/fixtures')
        for src, dst in (('honey-fca-dsh', 'bin/honey-fca-dsh'), ('cordis.patch.yml', 'fca-synthetic-fixture/cordis.patch.yml'),
                         ('boot_check.mjs', 'fca-synthetic-fixture/boot_check.mjs'), ('SOURCE.md', 'SOURCE.md')):
            shutil.copy(os.path.join(HERE, src), os.path.join(dest, dst))
        for rel in ('fca-synthetic-fixture/offline_fixture.py', 'fca-synthetic-fixture/fixtures/offline.json'):
            write(os.path.join(dest, rel), git_show(rel))
    for root, dirs, files in os.walk(dest):
        os.chmod(root, 0o755)
        for name in files:
            full = os.path.join(root, name)
            os.chmod(full, 0o755 if name == 'honey-fca-dsh' else 0o644)


def pin(lane):
    manifest = subprocess.run(['sudo', '-n', 'sha256sum', STAGE + '/dsh/REVIEWED-CLOSURE.sha256'], capture_output=True, text=True, check=True)
    digest = manifest.stdout.split()[0]
    path = lane + '/bin/honey-fca-dsh'
    text = read(path)
    assert 'REVIEWED_CLOSURE_MANIFEST_SHA256=REVIEW_REQUIRED' in text
    write(path, text.replace('REVIEWED_CLOSURE_MANIFEST_SHA256=REVIEW_REQUIRED', 'REVIEWED_CLOSURE_MANIFEST_SHA256=' + digest))


def make_lane(name, overlay=None, launcher=None, boot_check=None):
    """A pinned throwaway lane; overlay/launcher/boot_check are optional functions text -> text (sabotage or the old preimage)."""
    lane = '%s/%s' % (WORK, name)
    assemble(lane)
    for rel, edit in (('fca-synthetic-fixture/cordis.patch.yml', overlay), ('bin/honey-fca-dsh', launcher),
                      ('fca-synthetic-fixture/boot_check.mjs', boot_check)):
        if edit is not None:
            text = read(os.path.join(lane, rel))
            new = edit(text)
            assert new != text, 'edit did not change %s for %s' % (rel, name)
            write(os.path.join(lane, rel), new)
    pin(lane)
    return lane


def as_worker(argv, env=(), timeout=120):
    cmd = ['sudo', '-n', 'setpriv', '--reuid=2012', '--regid=2012', '--clear-groups', '/usr/bin/env', '-i',
           'HOME=' + WORKER_HOME, 'PATH=/usr/bin:/bin'] + list(env) + list(argv)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def boot(lane, env=()):
    result = as_worker([lane + '/bin/honey-fca-dsh', 'boot-check'], env)
    report = None
    for line in result.stdout.splitlines():
        if line.startswith('{'):
            report = json.loads(line)
    return result, report


def overlay_rows(text):
    rows, current = [], None
    for line in text.splitlines():
        match = re.match(r'- id: (\S+)\s*$', line)
        if match:
            current = {'id': match.group(1), 'disabled': False}
            rows.append(current)
        elif current is not None and re.match(r'  disabled: true\s*$', line):
            current['disabled'] = True
    return rows


def dump_rows(lane):
    result = as_worker([lane + '/bin/honey-fca-dsh', 'dsh-config'])
    assert result.returncode == 0 and not result.stderr, (result.returncode, result.stderr[:300])
    return {row['id']: row['disabled'] for row in overlay_rows(result.stdout)}


def drop_row(row_id):
    def edit(text):
        return re.sub(r'- id: %s\n  disabled: true\n' % re.escape(row_id), '', text)
    return edit


def drop_telemetry_env(text):
    return text.replace(' DSH_TELEMETRY_DISABLED=1', '')


@unittest.skipUnless(HAVE_RUNTIME, 'staged worker runtime or sudo not available')
class BootProfile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.good = make_lane('good')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(WORK, ignore_errors=True)

    # ---- static: the two telemetry layers and the closure rows must be present (these fail if either layer is missing) ----
    def test_01_overlay_disables_telemetry_row_and_never_enables_anything(self):
        rows = overlay_rows(read(self.good + '/fca-synthetic-fixture/cordis.patch.yml'))
        by_id = {row['id']: row['disabled'] for row in rows}
        self.assertEqual(by_id.get(TELEMETRY_ROW), True, 'session-telemetry-otel must be disabled in the overlay')
        for row_id in BOOT_CLOSURE:
            self.assertEqual(by_id.get(row_id), True, row_id)
        self.assertEqual([row['id'] for row in rows if not row['disabled']], [], 'the overlay must only disable')
        self.assertEqual(len(by_id), len(rows), 'duplicate row ids')

    def test_02_launcher_sets_telemetry_env_for_every_mode_and_has_no_other_environment(self):
        text = read(self.good + '/bin/honey-fca-dsh')
        block = re.search(r'^WORKER_ENV=\((.*?)^\)', text, re.S | re.M)
        self.assertIsNotNone(block)
        self.assertIn('DSH_TELEMETRY_DISABLED=1', block.group(1).split())
        execs = [line for line in text.splitlines() if 'exec "$BWRAP"' in line]
        self.assertEqual(len(execs), 3, 'probe, boot-check and dsh-config are the only sandbox entries')
        for line in execs:
            self.assertIn('/usr/bin/env -i "${WORKER_ENV[@]}"', line)
        self.assertEqual(len(re.findall(r'/usr/bin/env -i', text)), 3, 'every sandbox entry must use the one fixed environment')

    # ---- real boot ----
    def test_03_real_boot_succeeds_offline_with_clean_shutdown_and_no_stderr(self):
        result, report = boot(self.good)
        self.assertEqual(result.returncode, 0, (result.stdout[-400:], result.stderr[-400:]))
        self.assertEqual(report['boot'], 'ok')
        self.assertEqual(result.stderr, '')

    def test_04_boot_writes_only_the_expected_sterile_paths_and_no_telemetry_identity(self):
        _, report = boot(self.good)
        self.assertEqual(report['home'], [], 'nothing may be written to HOME')
        self.assertEqual(set(report['dsh_home']), EXPECTED_DSH_HOME)
        self.assertNotIn('.anonymous-user-id', report['dsh_home'])
        self.assertEqual([name for name in report['dsh_home'] if SECRETISH.search(name)], [], 'credential/settings/spill file appeared')

    def test_05_the_witness_is_real_when_both_telemetry_layers_are_missing(self):
        lane = make_lane('both-missing', overlay=drop_row(TELEMETRY_ROW), launcher=drop_telemetry_env)
        result, report = boot(lane)
        self.assertEqual(result.returncode, 0, result.stdout[-300:])
        self.assertIn('.anonymous-user-id', report['dsh_home'], 'telemetry constructs its exporter and identity when nothing disables it')

    def test_06_each_telemetry_layer_alone_is_sufficient(self):
        for name, kwargs in (('row-only', {'launcher': drop_telemetry_env}), ('env-only', {'overlay': drop_row(TELEMETRY_ROW)})):
            with self.subTest(name):
                result, report = boot(make_lane(name, **kwargs))
                self.assertEqual(result.returncode, 0, result.stdout[-300:])
                self.assertNotIn('.anonymous-user-id', report['dsh_home'])

    def test_07_caller_environment_cannot_turn_telemetry_on_or_move_the_home(self):
        hostile = ['DSH_TELEMETRY_DISABLED=', 'DSH_TELEMETRY_MODE=FEEDBACK_ONLY', 'DSH_TELEMETRY_OTLP_URL=https://telemetry.invalid/v1/logs',
                   'OTEL_EXPORTER_OTLP_ENDPOINT=https://telemetry.invalid', 'DSH_HOME=/tmp/not-the-sandbox', 'NEURALWATT_API_KEY=x']
        result, report = boot(self.good, env=hostile)
        self.assertEqual(result.returncode, 0, result.stdout[-300:])
        self.assertNotIn('.anonymous-user-id', report['dsh_home'])
        self.assertEqual(set(report['dsh_home']), EXPECTED_DSH_HOME)

    # ---- the finding: the revision-5 composition does not boot, and boot_check can fail ----
    def test_08_the_revision5_overlay_fails_boot_naming_exactly_the_nine_pending_entries(self):
        old = git_show('fca-synthetic-fixture/cordis.patch.yml')
        lane = make_lane('rev5', overlay=lambda _text: old)
        result, report = boot(lane)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report['boot'], 'failed')
        pending = [line.split(': pending')[0] for line in report['detail'] if ': pending' in line]
        self.assertEqual(pending[0], '@deepseek-ai/dsh-session-title-first-prompt-llm', 'first rejected entry')
        self.assertEqual(sorted(pending), sorted(BOOT_CLOSURE.values()))

    def test_09_every_boot_closure_row_is_necessary(self):
        for row_id, package in BOOT_CLOSURE.items():
            with self.subTest(row_id):
                result, report = boot(make_lane('no-' + row_id, overlay=drop_row(row_id)))
                self.assertEqual(result.returncode, 1, row_id)
                self.assertIn(package + ': pending', '\n'.join(report['detail']))

    # ---- offline modes: unchanged behaviour except the ten rows ----
    def test_10_dsh_config_differs_from_revision5_by_exactly_the_ten_disabled_rows(self):
        old = make_lane('rev5-cfg', overlay=lambda _text: git_show('fca-synthetic-fixture/cordis.patch.yml'))
        before, after = dump_rows(old), dump_rows(self.good)
        self.assertEqual(set(before), set(after))
        flipped = {row for row in after if before[row] != after[row]}
        self.assertEqual(flipped, set(BOOT_CLOSURE) | {TELEMETRY_ROW})
        self.assertTrue(all(after[row] for row in flipped), 'a row went from disabled to enabled')
        self.assertTrue(after[TELEMETRY_ROW])

    def test_11_probe_is_unchanged_and_boot_check_keeps_the_launcher_refusals(self):
        probe = as_worker([self.good + '/bin/honey-fca-dsh', 'probe'])
        self.assertEqual(json.loads(probe.stdout), {'fixture_read': True, 'network_policy': 'none', 'worker_uid': 2012})
        extra = as_worker([self.good + '/bin/honey-fca-dsh', 'boot-check', '--profile', 'x'])
        self.assertEqual(extra.returncode, 2)
        self.assertIn('arbitrary arguments are disabled', extra.stderr)
        operator = subprocess.run([self.good + '/bin/honey-fca-dsh', 'boot-check'], capture_output=True, text=True)
        self.assertEqual(operator.returncode, 2)
        self.assertIn('must run as agent-deepseek', operator.stderr)

    def test_12_boot_check_run_through_bash_dash_p_refusal_is_kept(self):
        result = as_worker(['/usr/bin/bash', self.good + '/bin/honey-fca-dsh', 'boot-check'])
        self.assertEqual(result.returncode, 2)
        self.assertIn('start through the executable', result.stderr)


if __name__ == '__main__':
    args = [sys.argv[0]] + [a for a in sys.argv[1:] if not os.path.isdir(a)]
    unittest.main(argv=args, verbosity=2)

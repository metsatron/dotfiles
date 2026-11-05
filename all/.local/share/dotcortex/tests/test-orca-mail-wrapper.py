import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(os.environ.get('ORCA_MAIL_WRAPPER', Path(__file__).resolve().parents[4] / '.bots/templates/orca-mailcortex'))
REAL = '/home/agent-deepseek/.local/bin/mailcortex-real'

class OrcaMailWrapperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='orca-mail-wrapper-')
        self.base = Path(self.temp.name)
        self.stub = self.base / 'receiver'
        self.stub.write_text('#!/usr/bin/python3\nimport json,os,sys\nprint(json.dumps({"argv":sys.argv[1:],"root":os.environ.get("MAILCORTEX_ROOT")}))\n')
        self.stub.chmod(0o755)
        if os.access(SOURCE, os.R_OK):
            source = SOURCE.read_text()
        else:
            source = subprocess.check_output(['sudo','-n','-u','agent-deepseek','python3','-c','from pathlib import Path; print(Path.home().joinpath(".local/bin/mailcortex").read_text(), end="")'],text=True)
        self.wrapper = self.base / 'wrapper'
        self.wrapper.write_text(source.replace(REAL, str(self.stub)))
    def tearDown(self):
        self.temp.cleanup()
    def run_wrapper(self, *args):
        x = subprocess.run(['bash',str(self.wrapper),*args],capture_output=True,text=True,check=True)
        d=json.loads(x.stdout); self.assertEqual(d['root'],'/home/metsatron/Mail'); return d['argv']
    def test_hermes_uses_receiver_shared_delivery(self):
        a=['send','--from','orcinus-orca@kikin.helm','--to','hermes@kikin.helm','--body','literal']; self.assertEqual(self.run_wrapper(*a),a+['--shared-delivery'])
    def test_other_recipient_private_semantics_unchanged(self):
        a=['send','--to','other@kikin.helm']; self.assertEqual(self.run_wrapper(*a),a)
    def test_inbox_unchanged(self):
        a=['inbox','orcinus-orca@kikin.helm']; self.assertEqual(self.run_wrapper(*a),a)
    def test_explicit_flag_not_duplicated(self):
        a=['send','--shared-delivery','--to','hermes@kikin.helm']; self.assertEqual(self.run_wrapper(*a),a)
    def test_equal_option_and_literal_subject_preserved(self):
        a=['send','--to=hermes@kikin.helm','--subject','--to is literal text']; self.assertEqual(self.run_wrapper(*a),a+['--shared-delivery'])
    def test_last_recipient_wins_like_argparse(self):
        a=['send','--to','hermes@kikin.helm','--to','other@kikin.helm']; self.assertEqual(self.run_wrapper(*a),a)

if __name__ == '__main__':
    unittest.main()

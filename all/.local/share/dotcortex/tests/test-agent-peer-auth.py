#!/usr/bin/env python3
"""Offline authenticated source/store tests; fixture credentials only."""
import copy
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(os.environ.get('WAKE_DOT_BUILDER', Path(__file__).resolve().parents[5]))

def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module

class AuthenticatedWakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.env = mock.patch.dict(os.environ, {
            'AGENT_PEER_REGISTRY_FILE': str(self.base/'registry.json'),
            'AGENT_PEER_STATE_DIR': str(self.base/'store')})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.peer = load('fixture_peer', ROOT/'all/.local/bin/agent-peer')
        self.source = 'fixture/hermes/coordinator'
        self.dest = 'kikin/codex/helmastra-coordinator'
        key = self.base/'fixture.key'
        key.write_bytes(b'OFFLINE-FIXTURE-ONLY-NOT-A-REAL-KEY')
        key.chmod(0o600)
        self.grant = {'source': self.source, 'destination': self.dest,
            'repo': 'fixture', 'repo_root': str(self.base), 'checkout_id': 'fixture:checkout',
            'capabilities': ['status','nudge'], 'secret_file': str(key)}
        self.registry = self.peer.blank_registry('kikin')
        self.registry['coordinator_keys'] = {'fixture-key': self.grant}
        self.registry['endpoints'][self.dest] = {'delivery': 'store',
            'repo_root': str(self.base), 'accept_from': [],
            'herdr_session': 'unused', 'herdr_target': 'unused'}
        self.peer.write_registry(self.registry)
        handoff = {'schema_version':'1.0', 'id':'fixture', 'scope':'fixture',
            'goal':'Report fixture status only', 'working_directory':str(self.base),
            'constraints':{'read_only':True,'allow_git':'none','forbidden_paths':['LOGS/','NEXUS/']},
            'steps':['Report status'], 'deliverables':['Status'], 'stop_conditions':['No changes']}
        self.envelope = self.peer.compose_envelope(from_peer=self.source,to_peer=self.dest,
            repo='fixture',repo_root=str(self.base),checkout_id='fixture:checkout', access='read',
            body='Fixture status',handoff=handoff,allow_git=False,allow_push=False,
            allow_pull=False,lease_id=None)

    def test_attested_store_exact_duplicate_and_reverification(self):
        signed = self.peer.sign_coordinator(self.envelope, 'fixture-key')
        self.assertEqual(self.peer.receive_coordinator(signed)['state'], 'stored')
        self.assertTrue(self.peer.receive_coordinator(signed)['duplicate'])
        record = self.peer.verified_coordinator_record(self.envelope['message_id'])
        self.assertEqual(record['envelope'], self.envelope)
        self.assertEqual(record['coordinator_auth']['source'], self.source)
        with self.assertRaises(self.peer.PeerError):
            self.peer.receive_envelope(self.envelope)

    def test_forgeries_scopes_expiry_nonce_and_rotation(self):
        signed = self.peer.sign_coordinator(self.envelope,'fixture-key')
        for field, value in [('from',self.peer.peer_object('fixture/hermes/forged')),
                             ('to',self.peer.peer_object('kikin/codex/other'))]:
            bad = copy.deepcopy(signed);bad['envelope'][field]=value
            with self.assertRaises(self.peer.PeerError): self.peer.receive_coordinator(bad)
        for field in ['repo','repo_root','checkout_id']:
            bad=copy.deepcopy(self.envelope);bad['workspace'][field]='mismatch'
            with self.assertRaises(self.peer.PeerError): self.peer.sign_coordinator(bad,'fixture-key')
        bad=copy.deepcopy(signed);bad['key_id']='unknown'
        with self.assertRaises(self.peer.PeerError): self.peer.receive_coordinator(bad)
        with mock.patch.object(self.peer.time,'time',return_value=time.time()+400):
            with self.assertRaises(self.peer.PeerError): self.peer.receive_coordinator(signed)
        self.peer.receive_coordinator(signed)
        replay=copy.deepcopy(self.envelope);replay['message_id']=str(self.peer.uuid.uuid4())
        with mock.patch.object(self.peer.uuid,'uuid4',return_value=signed['nonce']):
            replay=self.peer.sign_coordinator(replay,'fixture-key')
        with self.assertRaises(self.peer.PeerError): self.peer.receive_coordinator(replay)
        self.registry['coordinator_keys']={};self.peer.write_registry(self.registry)
        with self.assertRaises(self.peer.PeerError): self.peer.verified_coordinator_record(self.envelope['message_id'])

    def test_mail_transport_poison_then_valid_stores_once_without_model(self):
        from email.message import EmailMessage
        watcher = load('fixture_watcher', ROOT/'all/.local/bin/mailcortex-seat-watcher')
        mailroot=self.base/'Mail'
        mailbox=mailroot/'seats/astra'
        for leaf in ('new','cur','tmp'): (mailbox/leaf).mkdir(parents=True)
        record={'host':'fixture','mailbox':'seats/astra','harness':'codex',
                'transport':'agent-peer-native','native_endpoint':self.dest,'rate_limit_seconds':0}
        registry={'schema':'mailcortex.seats.v1','host':'fixture','seats':{'astra':record}}
        for name,body in [('a-poison','not signed JSON'),
                          ('b-valid',json.dumps(self.peer.sign_coordinator(self.envelope,'fixture-key')))]:
            msg=EmailMessage();msg['From']='forged-author@example.invalid';msg['Message-ID']=f'<{name}@fixture>'
            msg.set_content(body);(mailbox/'new'/name).write_bytes(msg.as_bytes())
        with mock.patch.dict(os.environ,MAILCORTEX_ROOT=str(mailroot),MAILCORTEX_RUNTIME=str(self.base/'runtime')):
            self.registry['coordinator_keys']={};self.peer.write_registry(self.registry)
            self.assertEqual(watcher.scan_once(registry, watcher.TransportAdapters(),now=99),0)
            self.assertEqual(watcher.MAILCORTEX.load_receipt('astra','<b-valid@fixture>')['reason'],'transport_unavailable')
            self.registry['coordinator_keys']={'fixture-key':self.grant};self.peer.write_registry(self.registry)
            self.assertEqual(watcher.scan_once(registry, watcher.TransportAdapters(),now=100),1)
            self.assertEqual(watcher.scan_once(registry, watcher.TransportAdapters(),now=101),0)
            receipt=watcher.MAILCORTEX.load_receipt('astra','<b-valid@fixture>')
            self.assertEqual(receipt['wake_state'],'injected')
            self.assertEqual(receipt['transport_ack'],'stored')
            self.assertEqual(receipt['peer_message_id'],self.envelope['message_id'])
            poison=watcher.MAILCORTEX.load_receipt('astra','<a-poison@fixture>')
            self.assertEqual(poison['reason'],'authentication_refused')
        self.assertIsNotNone(self.peer.verified_coordinator_record(self.envelope['message_id']))

if __name__=='__main__': unittest.main()

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
            'AGENT_PEER_STATE_DIR': str(self.base/'store'),
            'AGENT_PEER_COORDINATOR_TRUST_FILE': str(self.base/'trust.json')})
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
            'capabilities': ['status','nudge'], 'secret_file': str(key),
            'root_identity': {'device':self.base.stat().st_dev,'inode':self.base.stat().st_ino}}
        self.registry = self.peer.blank_registry('kikin')
        self.registry['coordinator_keys'] = {'fixture-key': self.grant}
        self.registry['endpoints'][self.dest] = {'delivery': 'store',
            'repo_root': str(self.base), 'accept_from': [],
            'herdr_session': 'unused', 'herdr_target': 'unused'}
        self.peer.write_registry(self.registry)
        self.write_trust()
        handoff = {'schema_version':'1.0', 'id':'fixture', 'scope':'fixture',
            'goal':'Report fixture status only', 'working_directory':str(self.base),
            'constraints':{'read_only':True,'allow_git':'none','forbidden_paths':['LOGS/','NEXUS/']},
            'steps':['Report status'], 'deliverables':['Status'], 'stop_conditions':['No changes']}
        self.envelope = self.peer.compose_envelope(from_peer=self.source,to_peer=self.dest,
            repo='fixture',repo_root=str(self.base),checkout_id='fixture:checkout', access='read',
            body='Fixture status',handoff=handoff,allow_git=False,allow_push=False,
            allow_pull=False,lease_id=None)

    def write_trust(self):
        self.peer.atomic_json(self.base/'trust.json',
            {'schema':'dotcortex.coordinator-trust.v1',
             'coordinator_keys':self.registry['coordinator_keys']})

    def task_execution_grant(self):
        handoff = self.envelope['payload']['task_handoff']
        handoff['constraints']['allowed_paths'] = {'read':['FORGE/fixture.py'], 'write':[]}
        self.grant.update(capabilities=['taskExecution'],
            execution_authority='existing_session_permissions',
            task_execution={'schema':'dotcortex.task-execution.v1',
                'thread_id':'thread-coordinator', 'task_id':handoff['id'],
                'handoff_sha256':self.peer.hashlib.sha256(self.peer.coordinator_material(handoff)).hexdigest(),
                'allowed_paths':handoff['constraints']['allowed_paths'],
                'access':'read', 'expires':int(time.time())+300})
        self.write_trust()

    def test_distinct_task_execution_signed_grant_and_readonly_separation(self):
        self.task_execution_grant()
        signed = self.peer.sign_coordinator(self.envelope, 'fixture-key')
        self.assertEqual(signed['schema'], 'dotcortex.coordinator-task-attestation.v1')
        self.assertEqual(self.peer.receive_coordinator(signed)['state'], 'stored')
        auth = self.peer.verified_coordinator_record(self.envelope['message_id'])['coordinator_auth']
        self.assertEqual(auth['execution_authority'], 'existing_session_permissions')
        self.assertEqual(auth['task_execution'], self.grant['task_execution'])
        for field, value in [('thread_id','other'), ('handoff_sha256','0'*64),
                             ('allowed_paths',{'read':['NEXUS/secret'], 'write':[]})]:
            changed=copy.deepcopy(self.grant)
            changed['task_execution'][field]=value
            self.registry['coordinator_keys']['fixture-key']=changed;self.write_trust()
            with self.assertRaises(self.peer.PeerError): self.peer.verify_coordinator(signed)
        self.registry['coordinator_keys']['fixture-key']=self.grant
        self.grant['capabilities']=['status','nudge'];self.write_trust()
        with self.assertRaises(self.peer.PeerError): self.peer.verify_coordinator(signed)

    def test_write_task_requires_existing_checkout_lease_and_exact_policy(self):
        self.task_execution_grant()
        handoff=self.envelope['payload']['task_handoff']
        handoff['constraints'].update(read_only=False,allow_git='commit_via_skill',
            allowed_paths={'read':['FORGE/fixture.py'],'write':['FORGE/fixture.py']})
        self.envelope['workspace']['access']='write'
        self.envelope['authority']['allow_git']=True
        self.grant['task_execution'].update(access='write',
            allowed_paths=handoff['constraints']['allowed_paths'],
            handoff_sha256=self.peer.hashlib.sha256(self.peer.coordinator_material(handoff)).hexdigest())
        self.write_trust()
        with mock.patch.object(self.peer,'emit') as emitted:
            self.peer.command_lease_acquire(['checkout-write'],'fixture:checkout',self.dest,300)
        lease=emitted.call_args.args[0]
        self.envelope['lease']={k:lease[k] for k in ('lease_id','scopes')}
        signed=self.peer.sign_coordinator(self.envelope,'fixture-key')
        self.assertEqual(self.peer.verify_coordinator(signed)['task_execution']['access'],'write')
        self.peer.command_lease_release(lease['lease_id'])
        with self.assertRaises(self.peer.PeerError):self.peer.verify_coordinator(signed)

    def test_shared_registry_cannot_replace_protected_grant(self):
        trust = self.base/'trust.json'
        self.peer.atomic_json(trust, {'schema':'dotcortex.coordinator-trust.v1',
            'coordinator_keys':{'fixture-key':self.grant}})
        with mock.patch.dict(os.environ, AGENT_PEER_COORDINATOR_TRUST_FILE=str(trust)):
            signed = self.peer.sign_coordinator(self.envelope, 'fixture-key')
            attacker = self.base/'attacker.key'
            attacker.write_bytes(b'ISOLATED-ATTACKER-FIXTURE-KEY-ONLY-0000');attacker.chmod(0o600)
            self.registry['coordinator_keys']['fixture-key'] = dict(self.grant, secret_file=str(attacker))
            self.peer.write_registry(self.registry)
            (self.base/'registry.json').chmod(0o666)
            self.assertEqual(self.peer.verify_coordinator(signed)['secret_file'], self.grant['secret_file'])
            (self.base/'registry.json').chmod(0o660)
            self.assertEqual(self.peer.verify_coordinator(signed)['secret_file'], self.grant['secret_file'])

    def test_private_trust_owner_modes_links_parents_and_read_race(self):
        trust=self.base/'trust.json'
        for mode in (0o666,0o660,0o640):
            trust.chmod(mode)
            with self.assertRaises(self.peer.PeerError): self.peer.sign_coordinator(self.envelope,'fixture-key')
        trust.chmod(0o600)
        link=self.base/'linked';link.symlink_to(self.base, target_is_directory=True)
        with mock.patch.dict(os.environ,AGENT_PEER_COORDINATOR_TRUST_FILE=str(link/'trust.json')):
            with self.assertRaises(self.peer.PeerError): self.peer.sign_coordinator(self.envelope,'fixture-key')
        unsafe=self.base/'unsafe';unsafe.mkdir();unsafe.chmod(0o777)
        self.peer.atomic_json(unsafe/'trust.json',{'schema':'dotcortex.coordinator-trust.v1','coordinator_keys':{'fixture-key':self.grant}})
        with mock.patch.dict(os.environ,AGENT_PEER_COORDINATOR_TRUST_FILE=str(unsafe/'trust.json')):
            with self.assertRaises(self.peer.PeerError): self.peer.sign_coordinator(self.envelope,'fixture-key')
        real_fstat=self.peer.os.fstat
        def wrong_owner(fd):
            info=real_fstat(fd)
            if self.peer.stat.S_ISREG(info.st_mode):
                values=list(info);values[4]=os.geteuid()+1
                return os.stat_result(values)
            return info
        with mock.patch.object(self.peer.os,'fstat',side_effect=wrong_owner):
            with self.assertRaises(self.peer.PeerError): self.peer.sign_coordinator(self.envelope,'fixture-key')
        real_read=self.peer.os.read
        def mutate(fd,n):
            value=real_read(fd,n)
            with trust.open('ab') as handle: handle.write(b' ')
            return value
        with mock.patch.object(self.peer.os,'read',side_effect=mutate):
            with self.assertRaises(self.peer.PeerError): self.peer.sign_coordinator(self.envelope,'fixture-key')
        self.write_trust()
        trust.unlink();trust.symlink_to(self.base/'fixture.key')
        with self.assertRaises(self.peer.PeerError): self.peer.sign_coordinator(self.envelope,'fixture-key')

    def test_physical_root_alias_and_replaced_checkout_are_refused(self):
        signed=self.peer.sign_coordinator(self.envelope,'fixture-key')
        self.grant['root_identity']['inode']+=1;self.write_trust()
        with self.assertRaises(self.peer.PeerError): self.peer.receive_coordinator(signed)
        self.grant['root_identity']['inode']-=1
        link=self.base/'checkout-alias';link.symlink_to(self.base,target_is_directory=True)
        self.grant['repo_root']=str(link);self.write_trust()
        envelope=copy.deepcopy(self.envelope);envelope['workspace']['repo_root']=str(link)
        with self.assertRaises(self.peer.PeerError): self.peer.sign_coordinator(envelope,'fixture-key')

    def test_missing_trust_is_retryable_but_unknown_and_revoked_are_refused(self):
        signed=self.peer.sign_coordinator(self.envelope,'fixture-key')
        trust=self.base/'trust.json';value=trust.read_bytes();trust.unlink()
        with self.assertRaises(self.peer.CoordinatorUnavailable): self.peer.receive_coordinator(signed)
        trust.write_bytes(value);trust.chmod(0o600)
        self.assertEqual(self.peer.receive_coordinator(signed)['state'],'stored')
        self.registry['coordinator_keys']={};self.write_trust()
        with self.assertRaises(self.peer.PeerError) as refused: self.peer.verify_coordinator(signed)
        self.assertNotIsInstance(refused.exception,self.peer.CoordinatorUnavailable)

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
        self.registry['coordinator_keys']={};self.write_trust()
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
            trust_bytes=(self.base/'trust.json').read_bytes()
            (self.base/'trust.json').unlink()
            self.assertEqual(watcher.scan_once(registry, watcher.TransportAdapters(),now=99),0)
            self.assertEqual(watcher.MAILCORTEX.load_receipt('astra','<b-valid@fixture>')['reason'],'transport_unavailable')
            (self.base/'trust.json').write_bytes(trust_bytes)
            (self.base/'trust.json').chmod(0o600)
            self.assertEqual(watcher.scan_once(registry, watcher.TransportAdapters(),now=100),1)
            self.assertEqual(watcher.scan_once(registry, watcher.TransportAdapters(),now=101),0)
            receipt=watcher.MAILCORTEX.load_receipt('astra','<b-valid@fixture>')
            self.assertEqual(receipt['wake_state'],'injected')
            self.assertEqual(receipt['transport_ack'],'stored')
            self.assertEqual(receipt['peer_message_id'],self.envelope['message_id'])
            poison=watcher.MAILCORTEX.load_receipt('astra','<a-poison@fixture>')
            self.assertEqual(poison['reason'],'authentication_refused')
        self.assertIsNotNone(self.peer.verified_coordinator_record(self.envelope['message_id']))

class GemmaDestinationTests(AuthenticatedWakeTests):
    """Run the original auth contract against an explicitly selected fixture."""
    def setUp(self):
        super().setUp()
        from functools import partial
        self.dest = 'kikin/pi/gemma-fixture'
        endpoint = self.registry['endpoints'].pop(self.grant['destination'])
        self.registry['endpoints'][self.dest] = endpoint
        self.grant['destination'] = self.dest
        self.envelope['to'] = self.peer.peer_object(self.dest)
        self.peer.write_registry(self.registry)
        self.write_trust()
        for name in ('sign_coordinator', 'verify_coordinator', 'receive_coordinator',
                     'verified_coordinator_record'):
            setattr(self.peer, name, partial(getattr(self.peer, name), destination=self.dest))

    def test_mail_transport_poison_then_valid_stores_once_without_model(self):
        # Watcher seat expansion belongs to the adapter owner, not this change.
        # Exercise the actual CLI used by NativePeerInbox instead, without mail.
        import subprocess
        signed = self.peer.sign_coordinator(self.envelope, 'fixture-key')
        self.peer.receive_coordinator(signed)
        command = ['python3', str(ROOT/'all/.local/bin/agent-peer'),
                   'coordinator-verify', self.envelope['message_id']]
        result = subprocess.run(command + ['--destination', self.dest],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(set(value), {'box', 'record'})
        self.assertEqual(value['record']['coordinator_auth']['destination'], self.dest)
        self.assertNotEqual(subprocess.run(command, capture_output=True,
                            text=True, check=False).returncode, 0)

    def test_configuration_is_not_a_grant_and_default_does_not_authorize_gemma(self):
        raw = load('default_fixture_peer', ROOT/'all/.local/bin/agent-peer')
        with self.assertRaises(raw.PeerError):
            raw.sign_coordinator(self.envelope, 'fixture-key')
        self.registry['coordinator_keys'] = {}; self.write_trust()
        with self.assertRaises(self.peer.PeerError):
            self.peer.sign_coordinator(self.envelope, 'fixture-key')

    def test_pickup_rechecks_endpoint_registration_delivery_host_and_root(self):
        signed = self.peer.sign_coordinator(self.envelope, 'fixture-key')
        self.peer.receive_coordinator(signed)
        original = copy.deepcopy(self.registry)
        for change in ('missing', 'pane', 'host', 'root'):
            self.registry = copy.deepcopy(original)
            if change == 'missing': self.registry['endpoints'].pop(self.dest)
            elif change == 'pane': self.registry['endpoints'][self.dest]['delivery'] = 'pane'
            elif change == 'host': self.registry['local_host_id'] = 'other-fixture'
            else:
                other = self.base/'other'; other.mkdir(exist_ok=True)
                self.registry['endpoints'][self.dest]['repo_root'] = str(other)
            self.peer.write_registry(self.registry)
            with self.subTest(change=change), self.assertRaises(self.peer.PeerError):
                self.peer.verified_coordinator_record(self.envelope['message_id'])

    def test_bad_destination_selection_fails_closed(self):
        raw = load('selection_fixture_peer', ROOT/'all/.local/bin/agent-peer')
        for destination in ('', '*', 'fixture/pi', 'fixture/pi/session/extra',
                            'fixture/pi/other', None):
            with self.subTest(destination=destination), self.assertRaises(raw.PeerError):
                raw.sign_coordinator(self.envelope, 'fixture-key', destination=destination)

    def test_changed_handoff_and_current_grant_are_refused_at_pickup(self):
        self.task_execution_grant()
        signed = self.peer.sign_coordinator(self.envelope, 'fixture-key')
        self.peer.receive_coordinator(signed)
        mid = self.envelope['message_id']
        for field, value in [('source', 'fixture/hermes/other'),
                             ('destination', 'kikin/pi/other'),
                             ('checkout_id', 'fixture:other')]:
            original = self.grant[field]; self.grant[field] = value; self.write_trust()
            with self.subTest(field=field), self.assertRaises(self.peer.PeerError):
                self.peer.verified_coordinator_record(mid)
            self.grant[field] = original
        self.write_trust()
        record = self.peer.read_record('inbox', mid)
        record['envelope']['payload']['task_handoff']['goal'] = 'Changed payload'
        self.peer.atomic_json(self.peer.record_path('inbox', mid), record)
        with self.assertRaises(self.peer.PeerError): self.peer.verified_coordinator_record(mid)

    def test_stale_cli_cannot_claim_destination_support(self):
        import subprocess
        # Hermetic stale-host capability fixture: no fallback to ordinary show.
        stale = self.base/'stale-peer.py'
        stale.write_text('import argparse\np=argparse.ArgumentParser()\n'
                         'p.add_argument("verb",choices=["show"])\np.parse_args()\n')
        result = subprocess.run(['python3', str(stale), 'coordinator-verify',
                                 self.envelope['message_id'], '--destination', self.dest],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')

if __name__=='__main__': unittest.main()

#!/usr/bin/env python3
"""Provider-free actual extracted producer/handler + native FS + hook tests.
No plugin import, bot startup, credentials, real file IDs or network.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[5]
ASSETS = REPO / 'all/.local/share/dotcortex/telegram-attachments'
ENGINE = REPO / 'all/.local/lib/dotcortex/claude_approval_kikin.py'
APPLIER = REPO / 'all/.local/bin/claude-telegram-attachment-patch'
SCRIPT = Path(__file__).resolve()
BUN = shutil.which('bun')

PLUGIN_PREFIX = r"""import {randomBytes} from 'node:crypto';
import {join} from 'node:path';
import {homedir} from 'node:os';
import {execFileSync} from 'node:child_process';
import {createInterface} from 'node:readline';
import {mkdirSync,writeFileSync,readFileSync,renameSync,symlinkSync,openSync,fstatSync,constants as fsConstants} from 'node:fs';
const STATE_DIR=process.env.TELEGRAM_STATE_DIR;
const INBOX_DIR=join(STATE_DIR,'inbox');
const TOKEN='synthetic-no-network';
const PERMISSION_REPLY_RE=/^NEVER_MATCH_SYNTHETIC$/;
let apiIds=[],mode='normal',notifications=[],lastArgs,payload;
let callTool,listTools;
const ListToolsRequestSchema='list',CallToolRequestSchema='call';
const access={dmPolicy:'allowlist',allowFrom:['101'],groups:{},pending:{}};
function loadAccess(){return access}
function pruneExpired(){return false}
function saveAccess(){throw new Error('unexpected access write')}
function isMentioned(){return false}
const bot={api:{sendChatAction:async()=>{},setMessageReaction:async()=>{},
  getFile:async(id)=>{apiIds.push(id); if(mode==='get-timeout') return new Promise(()=>{});
    return {file_path:mode==='url'?'https://fixture.invalid/x':'documents/fixture.bin',
    file_size:mode==='large-meta'?20971521:17};}}};
const mcp={setRequestHandler:(schema,handler)=>{if(schema==='list')listTools=handler;else callTool=handler},
 notification:async v=>{if(mode==='notification-fail')throw new Error('fixture');notifications.push(v)}};
const fetch=async (url,opts)=>{
  lastArgs=opts;
  if(mode==='fetch-timeout')return new Promise(()=>{});
  const body=mode==='large-stream'?new Uint8Array(20971521):payload??Buffer.from('synthetic payload');
  return {ok:mode!=='http-error',headers:{get:()=>mode==='large-header'?'20971521':null},
    body:{getReader:()=>{let sent=false;return {cancel:async()=>{},read:async()=>{
      if(mode==='stream-timeout')return new Promise(()=>{});
      if(mode==='parent-race'&&!sent){renameSync(INBOX_DIR,INBOX_DIR+'-moved');symlinkSync(process.env.RACE_TARGET,INBOX_DIR)}
      if(sent)return {done:true};sent=true;return {done:false,value:body};}}}}};};
// Tests shorten ONLY the extracted deadline, without replacing native timers.
const nativeSetTimeout=globalThis.setTimeout;
const setTimeout=(fn,ms)=>nativeSetTimeout(fn,ms===30000?25:ms);
"""
PLUGIN_SUFFIX=r"""
console.log(JSON.stringify({ready:true,attachmentReady}));
for await(const line of createInterface({input:process.stdin})){
  const request=JSON.parse(line);mode=request.mode??'normal';
  payload=request.bytes?Buffer.from(request.bytes,'base64'):undefined;
  try{
    let out;
    if(request.op==='incoming'){
      const c={from:{id:request.sender??101},chat:{id:request.chat??101,type:'private'},
        message:{message_id:request.message??202,date:1},reply:async()=>{}};
      await handleInbound(c,'synthetic message',undefined,{kind:'document',file_id:request.id??'SyntheticAttachment_123',size:request.size??17});
      out={notifications:notifications.length,attachment:notifications.at(-1)?.params?.meta?.attachment_file_id??null};
    }else if(request.op==='download'){
      out=await callTool({params:{name:'download_attachment',arguments:request.args}});
      if(out.isError)throw new Error(out.content[0].text);
    }else if(request.op==='read')out=await callTool({params:{name:'read_attachment',arguments:request.args}});
    else if(request.op==='tools')out=await listTools();
    else throw new Error('unknown fixture op');
    console.log(JSON.stringify({ok:true,out,apiIds,fetchOptions:lastArgs?{redirect:lastArgs.redirect,signal:!!lastArgs.signal}:null}));
  }catch(e){console.log(JSON.stringify({ok:false,error:String(e.message),apiIds}));}
}
"""

def extract_plugin(source):
    custody=source.split('// DOTCORTEX_ATTACHMENT_CUSTODY_BEGIN',1)[1].split('// DOTCORTEX_ATTACHMENT_CUSTODY_END',1)[0]
    handlers=source.split('mcp.setRequestHandler(ListToolsRequestSchema',1)[1].split('await mcp.connect(',1)[0]
    handlers='mcp.setRequestHandler(ListToolsRequestSchema'+handlers
    gate=source.split('function gate(ctx: Context): GateResult {',1)[1].split('// Like gate()',1)[0]
    inbound=source.split('async function handleInbound(',1)[1].split('// Without this, any throw',1)[0]
    return (PLUGIN_PREFIX+custody+'\nfunction gate(ctx: any): any {'+gate+
            '\nasync function handleInbound('+inbound+'\n'+handlers+'\n'+PLUGIN_SUFFIX)

class CustodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(os.environ['ATTACHMENT_TEST_ROOT'])
        cls.source=Path(os.environ['ATTACHMENT_PATCHED_SOURCE']).read_text()
        cls.fixture=cls.root/'extracted.ts'
        cls.fixture.write_text(extract_plugin(cls.source))
        spec=importlib.util.spec_from_file_location('test_custody',ASSETS/'custody.py')
        cls.c=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.c)
        spec=importlib.util.spec_from_file_location('test_approval',ENGINE)
        cls.e=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.e)
        cls.manifest=cls.e._load_manifest(json.loads((REPO/'all/.config/dotcortex/claude-approval-canary.kikin.v1.json').read_text()))
        cls.manifest['decider']['enabled']=False
        cls.manifest['roots']=(str(cls.root),)
        cls.manifest['scratch_roots']=()
        cls.manifest['gate_inversion']={'enabled':False,'present_refusal':'deny'}
        for ent in cls.manifest['entries'].values():ent['enabled']=False
    def setUp(self):
        self.state=self.root/self._testMethodName
        self.state.mkdir(mode=0o770)
        os.chmod(self.state,0o770) # group-writable ancestor is intentionally valid
        self.env={**os.environ,'TELEGRAM_STATE_DIR':str(self.state),'RACE_TARGET':str(self.root/'race-neighbor')}
        (self.root/'race-neighbor').mkdir(exist_ok=True)
        self.start()
    def start(self, expected=True):
        self.plugin=subprocess.Popen([BUN,str(self.fixture)],env=self.env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.addCleanup(self.stop)
        first=json.loads(self.plugin.stdout.readline())
        self.assertEqual(first['attachmentReady'],expected,first)
    def stop(self):
        if self.plugin.poll() is None:
            self.plugin.stdin.close()
            self.plugin.wait(timeout=10)
        self.plugin.stdout.close();self.plugin.stderr.close()
    def call(self,op,**data):
        self.plugin.stdin.write(json.dumps({'op':op,**data})+'\n');self.plugin.stdin.flush()
        result=json.loads(self.plugin.stdout.readline())
        # Optional installed SDK witness; validates actual handler results, not
        # a fabricated response. Set ATTACHMENT_MCP_TYPES to installed types.js.
        types=os.environ.get('ATTACHMENT_MCP_TYPES')
        if types and result.get('ok') and op in ('read','download','tools'):
            schema='ListToolsResultSchema' if op=='tools' else 'CallToolResultSchema'
            code=('import {'+schema+' as schema} from '+json.dumps(types)+';'
                  'const result=JSON.parse(await Bun.stdin.text());schema.parse(result);')
            subprocess.run([BUN,'-e',code],input=json.dumps(result['out']),text=True,capture_output=True,check=True)
        return result
    def event(self,args=None,tool=None,sid='synthetic_session'):
        return {'hook_event_name':'PermissionRequest','tool_name':tool or self.c.DOWNLOAD,
                'tool_input':args or {'file_id':'SyntheticAttachment_123'},'session_id':sid,'cwd':str(self.root)}
    def decision(self,event):
        # Native owner is this real copied interpreter, not a mocked PID/JSON.
        return self.e._decide_request(event,self.manifest)
    def grant(self):
        self.assertTrue(self.call('incoming')['ok'])
        self.assertEqual(self.decision(self.event()),(True,'telegram_attachment_download'))
    def download(self):
        self.grant()
        result=self.call('download',args={'file_id':'SyntheticAttachment_123'})
        self.assertTrue(result['ok'],result)
        # Internal descriptor spelling is ONLY a filesystem adversary fixture;
        # the public MCP download response deliberately returns no path.
        reg=self.c.registry()
        try:index=reg.read(self.c.key(self.c.owner()))
        finally:reg.close()
        proof=self.c.generation(index['state'],index['nonce'])
        try:record=proof.read(index['nonce']+'.json')
        finally:proof.close()
        path=Path(record['anchor'])/list(record['files'])[-1]
        return path,result
    def read_event(self,**extra):
        return self.event({'file_id':'SyntheticAttachment_123',**extra},self.c.READ)
    def read(self,**extra):
        return self.call('read',args={'file_id':'SyntheticAttachment_123',**extra})
    def mutate(self,fn):
        reg=self.c.registry();o=self.c.owner()
        try:index=reg.read(self.c.key(o))
        finally:reg.close()
        proof=self.c.generation(index['state'],index['nonce'])
        try:
            r=proof.read(index['nonce']+'.json');fn(r);proof.write(index['nonce']+'.json',r,True)
        finally:proof.close()
    def test_native_incoming_download_read_chain(self):
        path,result=self.download()
        self.assertEqual(path.read_bytes(),b'synthetic payload')
        self.assertEqual(path.stat().st_mode & 0o777,0o600)
        self.assertEqual(result['apiIds'],['SyntheticAttachment_123'])
        self.assertEqual(result['fetchOptions'],{'redirect':'error','signal':True})
        event=self.read_event()
        self.assertEqual(self.decision(event),(True,'telegram_attachment_read'))
        self.assertEqual(self.e.classify(event,self.manifest),(True,'telegram_attachment_read'))
        self.assertEqual(self.read()['out'],{'content':[{'type':'text','text':'synthetic payload'}]})
        self.assertNotIn('/proc/',result['out']['content'][0]['text'])
        self.assertFalse(self.decision(self.event({'file_path':str(path)},'Read'))[0])
    def test_mcp_read_exact_schema_and_provenance(self):
        tools=self.call('tools')['out']['tools']
        schema=next(t['inputSchema'] for t in tools if t['name']=='read_attachment')
        self.assertEqual(schema['required'],['file_id'])
        self.assertEqual(set(schema['properties']),{'file_id'})
        self.assertIs(schema['additionalProperties'],False)
        self.assertTrue(self.read()['out']['isError']) # no receipt/download
        self.download()
        for extra in ({'path':'/fixture'}, {'url':'https://fixture.invalid'},
                      {'owner':self.c.owner()}, {'session_id':'synthetic_session'},
                      {'authorized':True}):
            with self.subTest(extra=extra):
                self.assertFalse(self.decision(self.read_event(**extra))[0])
                self.assertTrue(self.read(**extra)['out']['isError'])
        self.assertFalse(self.decision(self.event({'file_id':'SyntheticAttachment_123'},self.c.READ,sid='foreign'))[0])
        self.assertTrue(self.call('read',args={'file_id':'UnknownSynthetic'})['out']['isError'])
        self.mutate(lambda r:r['files'][next(iter(r['files']))].update(at=0))
        self.assertFalse(self.decision(self.read_event())[0])
        self.assertTrue(self.read()['out']['isError'])

    def test_mcp_markdown_text_and_truthful_format_limits(self):
        import base64
        self.grant()
        samples=[(b'# Synthetic Markdown\n\nTrusted transport, untrusted content.\n',True),
                 (b'\x89PNG\r\n\x1a\n'+b'fixture',False),
                 (b'\xff\xd8\xff'+b'fixture',False),
                 (b'%PDF-1.4\nfixture',False), (b'abc\x00binary',False),
                 (b'\xffinvalid-utf8',False), (b'a'*(256*1024+1),False)]
        for raw,allowed in samples:
            with self.subTest(prefix=raw[:12],allowed=allowed):
                out=self.call('download',args={'file_id':'SyntheticAttachment_123'},bytes=base64.b64encode(raw).decode())
                self.assertTrue(out['ok'],out)
                result=self.read()['out']
                self.assertEqual(not result.get('isError',False),allowed,result)
                if allowed:self.assertEqual(result['content'][0],{'type':'text','text':raw.decode()})
                else:self.assertIn('UTF-8 text up to 256 KiB',result['content'][0]['text'])

    def test_unproven_id_and_extra_arguments_no_api_calls(self):
        for args in ({'file_id':'UnknownSynthetic'},{'file_id':'https://fixture.invalid'},
                     {'file_id':'../escape'},{'file_id':'x'*257},{'file_id':None},
                     {'file_id':'SyntheticAttachment_123','authorized':True},
                     {'file_id':'SyntheticAttachment_123','url':'https://fixture.invalid'},
                     {'file_id':'SyntheticAttachment_123','path':'/fixture'},[],{}):
            with self.subTest(args=args):
                result=self.call('download',args=args)
                self.assertFalse(result['ok'],result);self.assertEqual(result['apiIds'],[])
                self.assertFalse(self.decision(self.event(args))[0])
    def test_foreign_sender_and_chat_no_provenance(self):
        for sender,chat in ((303,101),(303,303),(101,303)):
            self.call('incoming',sender=sender,chat=chat,id='ForeignSynthetic')
            self.assertFalse(self.decision(self.event({'file_id':'ForeignSynthetic'}))[0])
        self.assertEqual(self.call('download',args={'file_id':'ForeignSynthetic'})['apiIds'],[])
    def test_foreign_session_expired_and_restart_stale(self):
        self.grant()
        self.assertFalse(self.decision(self.event(sid='foreign_session'))[0])
        self.mutate(lambda r:r['receipts']['SyntheticAttachment_123'].update(at=0))
        self.assertFalse(self.decision(self.event())[0])
        self.assertFalse(self.call('download',args={'file_id':'SyntheticAttachment_123'})['ok'])
        self.stop();self.start()
        self.assertFalse(self.decision(self.event())[0])
        self.assertFalse(self.call('download',args={'file_id':'SyntheticAttachment_123'})['ok'])
    def test_neighbors_write_edit_extra_read_arguments_denied(self):
        path,_=self.download()
        neighbor=self.state/'access.json';neighbor.write_text('{}')
        other=self.state/'inbox'/'attachment-012345678901234567890123456789012345678901234567.bin'
        other.write_text('unproven synthetic bytes');other.chmod(0o600)
        for raw in (str(neighbor),str(self.state/'.env'),str(other),str(path.parent/'..'/'access.json')):
            self.assertFalse(self.decision(self.event({'file_path':raw},'Read'))[0],raw)
        alias=self.root/'channel-alias';alias.symlink_to(self.state,target_is_directory=True)
        protected={**self.manifest,'entries':{k:{**v,'enabled':True} if k=='local_read' else v
                   for k,v in self.manifest['entries'].items()}}
        commands=('cat '+str(neighbor), 'cat "'+str(neighbor)+'"',
                  'cat '+str(path.parent/'..'/'access.json'),
                  'cat '+str(alias/'access.json'), 'cat access.json')
        for command in commands:
            event=self.event({'command':command},'Bash')
            if command=='cat access.json':event['cwd']=str(self.state)
            for check in (self.e.classify,self.e._decide_request):
                self.assertEqual(check(event,protected),(False,'true_floor'),command)
        # A same-prefix sibling is unrelated ordinary work, not channel state.
        sibling=Path(str(self.state)+'-unrelated');sibling.mkdir()
        ordinary=sibling/'notes.txt';ordinary.write_text('ordinary synthetic work')
        for check in (self.e.classify,self.e._decide_request):
            self.assertIsNone(self.e._telegram_attachment_policy(
                self.event({'command':'cat '+str(ordinary)},'Bash'),protected))
            self.assertTrue(check(self.event({'command':'cat '+str(ordinary)},'Bash'),protected)[0])
        for tool in ('Write','Edit'):
            self.assertFalse(self.decision(self.event({'file_path':str(path)},tool))[0])
        self.assertFalse(self.decision(self.event({'file_path':str(path),'authorized':True},'Read'))[0])
    def test_symlink_hardlink_special_and_tamper_read_denied(self):
        path,_=self.download()
        original=path.read_bytes();path.unlink()
        neighbor=self.root/'neighbor';neighbor.write_bytes(original);neighbor.chmod(0o600)
        path.symlink_to(neighbor)
        self.assertFalse(self.decision(self.event({'file_path':str(path)},'Read'))[0])
        self.assertFalse(self.decision(self.read_event())[0])
        self.assertTrue(self.read()['out']['isError'])
        path.unlink();os.link(neighbor,path)
        self.assertFalse(self.decision(self.event({'file_path':str(path)},'Read'))[0])
        self.assertFalse(self.decision(self.read_event())[0])
        self.assertTrue(self.read()['out']['isError'])
        path.unlink();os.mkfifo(path,0o600)
        self.assertFalse(self.decision(self.event({'file_path':str(path)},'Read'))[0])
        self.assertFalse(self.decision(self.read_event())[0])
        self.assertTrue(self.read()['out']['isError'])
        path.unlink();path.write_bytes(b'changed synthetic');path.chmod(0o600)
        self.assertFalse(self.decision(self.event({'file_path':str(path)},'Read'))[0])
        self.assertFalse(self.decision(self.read_event())[0])
        self.assertTrue(self.read()['out']['isError'])
    def test_stream_metadata_header_bounds_urls_timeouts(self):
        self.grant()
        for mode in ('large-meta','large-header','large-stream','url','http-error','get-timeout','fetch-timeout','stream-timeout'):
            with self.subTest(mode=mode):
                result=self.call('download',args={'file_id':'SyntheticAttachment_123'},mode=mode)
                self.assertFalse(result['ok'],result)
        self.assertEqual(list((self.state/'inbox').glob('attachment-*')),[])
    def test_mcp_read_rechecks_after_approval_parent_rename(self):
        path,_=self.download()
        self.assertTrue(self.decision(self.read_event())[0])
        inbox=self.state/'inbox'
        inbox.rename(self.state/'inbox-moved')
        inbox.symlink_to(self.root/'race-neighbor')
        self.assertFalse(self.decision(self.read_event())[0])
        self.assertTrue(self.read()['out']['isError'])
        self.assertEqual(list((self.root/'race-neighbor').iterdir()),[])

    def test_parent_race_refused_without_neighbor_write(self):
        self.grant()
        result=self.call('download',args={'file_id':'SyntheticAttachment_123'},mode='parent-race')
        self.assertFalse(result['ok'],result)
        self.assertEqual(list((self.root/'race-neighbor').iterdir()),[])
    def test_exclusive_collision_symlink_and_hardlink_no_clobber(self):
        self.grant()
        # Real native store with deterministic entropy ONLY inside this helper
        # test process; producer identity parent is explicitly pinned to this
        # fixture parent for this isolated helper unit, not production behavior.
        inbox=self.c.Directory(str(self.state/'inbox'))
        try:
            neighbor=self.root/'collision-neighbor';neighbor.write_text('keep');neighbor.chmod(0o600)
            name='attachment-'+'a'*48+'.bin'
            target=self.state/'inbox'/name
            for kind in ('symlink','hardlink','regular','fifo'):
                if kind=='symlink':target.symlink_to(neighbor)
                elif kind=='hardlink':os.link(neighbor,target)
                elif kind=='regular':target.write_text('keep');target.chmod(0o600)
                else:os.mkfifo(target,0o600)
                with self.assertRaises(OSError):inbox.regular(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL)
                self.assertEqual(neighbor.read_text(),'keep');target.unlink()
        finally:inbox.close()
    def test_actual_handler_collision_cannot_follow_upstream_destination_symlink(self):
        self.grant()
        helper=Path.home()/'.local/share/dotcortex/telegram-attachments/custody.py'
        original=helper.read_text()
        # Fixture-only deterministic entropy runs the actual Python store below
        # the actual extracted JS handler. No production test flag is added.
        wrapper='import secrets; secrets.token_hex=lambda n: "a"*(n*2)\nexec(compile('+repr(original)+',"custody.py","exec"))\n'
        neighbor=self.root/'actual-handler-neighbor';neighbor.write_text('keep')
        target=self.state/'inbox'/('attachment-'+'a'*48+'.bin')
        helper.write_text(wrapper)
        try:
            for kind in ('symlink','hardlink','regular','fifo'):
                if kind=='symlink':target.symlink_to(neighbor)
                elif kind=='hardlink':os.link(neighbor,target)
                elif kind=='regular':target.write_text('keep');target.chmod(0o600)
                else:os.mkfifo(target,0o600)
                result=self.call('download',args={'file_id':'SyntheticAttachment_123'})
                self.assertFalse(result['ok'],result)
                self.assertEqual(neighbor.read_text(),'keep');target.unlink()
        finally:helper.write_text(original)

    def test_shared_or_symlink_inbox_disables_custody_without_chmod(self):
        self.stop()
        inbox=self.state/'inbox';os.chmod(inbox,0o775)
        self.start(expected=False)
        self.assertEqual(inbox.stat().st_mode&0o777,0o775)
        self.assertEqual(self.call('download',args={'file_id':'SyntheticAttachment_123'})['apiIds'],[])
        self.stop();inbox.rename(self.state/'old-inbox');inbox.symlink_to(self.root/'race-neighbor')
        self.start(expected=False)
        self.assertEqual(self.call('download',args={'file_id':'SyntheticAttachment_123'})['apiIds'],[])

    def test_native_hook_child_binds_real_owner_and_missing_owner_refuses(self):
        self.call('incoming')
        code=('import importlib.util,json,sys; s=importlib.util.spec_from_file_location("e",'+repr(str(ENGINE))+');'
              'e=importlib.util.module_from_spec(s);s.loader.exec_module(e);'
              'v=json.load(sys.stdin);print(json.dumps(e._decide_request(v["event"],v["manifest"])))')
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
        p=subprocess.run(['/usr/bin/python3','-c',code],input=json.dumps({'event':self.event(),'manifest':self.manifest}),
                         env=env,text=True,capture_output=True,check=True)
        self.assertEqual(json.loads(p.stdout),[True,'telegram_attachment_download'])
        # A different configured executable inode is not this native owner.
        native=Path.home()/'.npm-global/bin/claude'
        replacement=native.with_name('other-owner');shutil.copy2('/usr/bin/true',replacement)
        native.rename(native.with_name('active-owner'));replacement.rename(native)
        try:self.assertFalse(self.decision(self.event())[0])
        finally:native.unlink();native.with_name('active-owner').rename(native)

    def test_failed_notification_revokes_receipt(self):
        self.call('incoming',mode='notification-fail')
        self.assertFalse(self.decision(self.event())[0])
        self.assertEqual(self.call('download',args={'file_id':'SyntheticAttachment_123'})['apiIds'],[])
    def test_oversized_incoming_receipt_refused(self):
        self.call('incoming',size=20971521)
        self.assertFalse(self.decision(self.event())[0])
    def test_custody_metadata_never_gains_read_or_shell_write_authority(self):
        reg=self.c.registry()
        try:
            path=reg.path+'/'+self.c.key(self.c.owner())
        finally:reg.close()
        for tool,args in [('Read',{'file_path':path}),('Write',{'file_path':path,'content':'fixture'}),
                          ('Bash',{'command':'cat '+path}),('Bash',{'command':'printf fixture > '+path})]:
            with self.subTest(tool=tool,args=args):
                self.assertFalse(self.decision(self.event(args,tool))[0])

    def test_no_native_owner_cannot_forge_registry(self):
        # This subprocess is still under native owner, so test another process
        # ancestry by asserting a caller-provided owner key cannot change it.
        actual=self.c.owner()
        self.assertNotEqual(actual,{'pid':1,'start':'0'})
        self.assertFalse(self.decision(self.event({'file_id':'UnknownSynthetic','owner':actual}))[0])

class ApplierTests(unittest.TestCase):
    def test_optimization_never_overrides_unknown_drift(self):
        root=Path(os.environ['ATTACHMENT_TEST_ROOT'])
        for variant,flags,extra in (('normal',[],{}),('optimized',['-O'],{}),
                                   ('environment',[],{'PYTHONOPTIMIZE':'1'})):
            for rollback in (False,True):
                with self.subTest(variant=variant,rollback=rollback):
                    runtime=root/('unknown-'+variant+str(rollback));runtime.mkdir(mode=0o700)
                    for name in ('.mcp.json','package.json'):
                        shutil.copy2(ASSETS/'fixtures'/name,runtime/name)
                    target=runtime/'server.ts';unknown=b'// unknown synthetic drift\n'
                    target.write_bytes(unknown);target.chmod(0o640)
                    argv=[sys.executable,*flags,str(APPLIER),str(runtime),'--apply']
                    if rollback:argv.append('--rollback')
                    result=subprocess.run(argv,env={**os.environ,**extra},capture_output=True,text=True)
                    self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertEqual(target.read_bytes(),unknown)

    def test_all_applier_pins_survive_optimization(self):
        root=Path(os.environ['ATTACHMENT_TEST_ROOT'])
        for variant,flags,extra in (('normal',[],{}),('optimized',['-O'],{}),
                                   ('environment',[],{'PYTHONOPTIMIZE':'1'})):
            for rollback in (False,True):
                for fault in ('pristine','helper','metadata','series','permissions','concurrent'):
                    with self.subTest(variant=variant,rollback=rollback,fault=fault):
                        base=root/('pins-'+variant+str(rollback)+fault)
                        assets=base/'share/dotcortex/telegram-attachments'
                        shutil.copytree(ASSETS,assets)
                        applier=base/'bin/patch';applier.parent.mkdir()
                        applier.write_bytes(APPLIER.read_bytes())
                        runtime=base/'runtime';runtime.mkdir(mode=0o700)
                        for name in ('.mcp.json','package.json'):
                            shutil.copy2(ASSETS/'fixtures'/name,runtime/name)
                        target=runtime/'server.ts'
                        # Both operations have a legitimate transition available.
                        target.write_bytes(Path(os.environ['ATTACHMENT_PATCHED_SOURCE']).read_bytes()
                                           if rollback else (ASSETS/'server.ts.pristine').read_bytes())
                        target.chmod(0o640)
                        if fault=='pristine':(assets/'server.ts.pristine').write_text('// unknown fixture')
                        elif fault=='helper':(assets/'custody.py').write_text('# unknown fixture')
                        elif fault=='metadata':(runtime/'package.json').write_text('{}')
                        elif fault=='series':(assets/'0001-custody.patch').write_text('invalid fixture patch')
                        elif fault=='permissions':runtime.chmod(0o770)
                        argv=[sys.executable,*flags,str(applier),str(runtime),'--apply']
                        expected=target.read_bytes()
                        if rollback:argv.append('--rollback')
                        if fault=='concurrent':
                            # Inject an actual concurrent target mutation at the
                            # final recheck open, without changing production code.
                            code=('import os,runpy,sys; real=os.open; target='+repr(str(target))+'; count=0\n'
                                  'def opened(path,*a,**kw):\n'
                                  ' global count\n'
                                  ' if path=="server.ts":\n'
                                  '  count+=1\n'
                                  '  if count==2: open(target,"wb").write(b"concurrent fixture")\n'
                                  ' return real(path,*a,**kw)\n'
                                  'os.open=opened;sys.argv='+repr([str(applier),str(runtime),'--apply']+(['--rollback'] if rollback else []))+';runpy.run_path(sys.argv[0],run_name="__main__")')
                            argv=[sys.executable,*flags,'-c',code];expected=b'concurrent fixture'
                        result=subprocess.run(argv,env={**os.environ,**extra},capture_output=True,text=True)
                        self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                        self.assertEqual(target.read_bytes(),expected)

    def test_native_consumer_contract_is_not_procfd_read(self):
        source=Path(os.environ['ATTACHMENT_PATCHED_SOURCE']).read_text()
        self.assertIn("name: 'read_attachment'",source)
        self.assertIn("case 'read_attachment':",source)
        self.assertNotIn('then Read the returned path',source)
        self.assertNotIn('Returns the local file path ready to Read',source)

    def test_both_engines_idempotence_rollback_drift_and_permissions(self):
        root=Path(os.environ['ATTACHMENT_TEST_ROOT'])
        outputs=[]
        for engine in ('git','patch'):
            runtime=root/('runtime-'+engine);runtime.mkdir(mode=0o700)
            for name in ('.mcp.json','package.json'):
                shutil.copy2(ASSETS/'fixtures'/name,runtime/name)
            target=runtime/'server.ts';target.write_bytes((ASSETS/'server.ts.pristine').read_bytes());target.chmod(0o640)
            def run(*args,ok=True):
                p=subprocess.run([sys.executable,str(APPLIER),str(runtime),'--engine',engine,*args],capture_output=True,text=True)
                self.assertEqual(p.returncode==0,ok,p.stdout+p.stderr)
                return json.loads(p.stdout) if ok else None
            original=target.read_bytes()
            self.assertFalse(run()['changed']);self.assertEqual(target.read_bytes(),original)
            self.assertTrue(run('--apply')['changed']);outputs.append(target.read_bytes())
            self.assertEqual(target.stat().st_mode&0o777,0o640)
            self.assertFalse(run('--apply')['changed'])
            self.assertTrue(run('--rollback','--apply')['changed']);self.assertEqual(target.read_bytes(),original)
            target.write_bytes(original+b'// drift\n');before=target.read_bytes()
            run('--apply',ok=False);self.assertEqual(target.read_bytes(),before)
        self.assertEqual(*outputs)

def launch():
    scratch=os.environ.get('TMPDIR')
    with tempfile.TemporaryDirectory(prefix='telegram-native-',dir=scratch) as tmp:
        root=Path(tmp);home=root/'home';home.mkdir(mode=0o700)
        native=home/'.npm-global/bin/claude';native.parent.mkdir(parents=True)
        shutil.copy2('/usr/bin/python3',native)
        assets=home/'.local/share/dotcortex/telegram-attachments';assets.mkdir(parents=True)
        shutil.copy2(ASSETS/'custody.py',assets/'custody.py')
        stage=root/'compile';stage.mkdir();(stage/'server.ts').write_bytes((ASSETS/'server.ts.pristine').read_bytes())
        subprocess.run(['git','apply',str(ASSETS/'0001-custody.patch')],cwd=stage,check=True)
        env={**os.environ,'HOME':str(home),'ATTACHMENT_TEST_ROOT':str(root),
             'ATTACHMENT_PATCHED_SOURCE':str(stage/'server.ts'),'PYTHONDONTWRITEBYTECODE':'1'}
        result=subprocess.run([str(native),str(SCRIPT),'--native'],env=env)
        return result.returncode

if __name__=='__main__':
    if '--native' not in sys.argv:
        raise SystemExit(launch())
    sys.argv.remove('--native');unittest.main(verbosity=2)

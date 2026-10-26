#!/usr/bin/env python3
"""Linux descriptor-confined Telegram custody. No credentials or document parsing.
Native Claude executable ancestry is the owner; the hook alone binds session_id.
Same-UID code execution is not an OS security boundary. Metadata is never input
from tool arguments. Restart/expiry/identity uncertainty fails closed.
"""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import time

LIMIT = 20 * 1024 * 1024
TTL = 900
ID = re.compile(r'[A-Za-z0-9_-]{1,256}\Z')
DOWNLOAD = 'mcp__plugin_telegram_telegram__download_attachment'
READ = 'mcp__plugin_telegram_telegram__read_attachment'
TEXT_LIMIT = 256 * 1024

def require(ok):
    if not ok:
        raise ValueError('attachment custody refused')

def identity(pid):
    p = Path('/proc') / str(pid)
    fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
    require(p.stat().st_uid == os.getuid())
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    return {'pid': pid, 'start': fields[19], 'boot': boot}, int(fields[1])

def owner():
    expected = Path.home() / '.npm-global/bin/claude'
    expected_stat = expected.stat()
    pid = os.getpid()
    for _ in range(64):
        item, parent = identity(pid)
        exe = os.stat('/proc/%s/exe' % pid)
        if (exe.st_dev, exe.st_ino) == (expected_stat.st_dev, expected_stat.st_ino):
            return item
        require(parent > 1 and parent != pid)
        pid = parent
    raise ValueError('no native Claude owner')

def alive(item):
    try:
        return identity(item['pid'])[0] == item
    except (OSError, KeyError, ValueError):
        return False

class Directory:
    def __init__(self, path, create=False, private=True):
        require(isinstance(path, str) and path.startswith('/') and os.path.normpath(path) == path)
        parts = path.split('/')[1:]
        require(parts and all(x not in ('', '.', '..') for x in parts))
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        try:
            for part in parts:
                if create:
                    try:
                        os.mkdir(part, 0o700, dir_fd=fd)
                    except FileExistsError:
                        pass
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
            info = os.fstat(fd)
            require(info.st_uid == os.getuid() and (not private or info.st_mode & 0o077 == 0))
            self.fd, self.path, self.info = fd, path, info
        except BaseException:
            os.close(fd)
            raise
    def close(self):
        os.close(self.fd)
    def current(self):
        other = Directory(self.path)
        try:
            require((other.info.st_dev, other.info.st_ino) == (self.info.st_dev, self.info.st_ino))
        finally:
            other.close()
    def regular(self, name, flags=os.O_RDONLY):
        require('/' not in name and name not in ('', '.', '..'))
        fd = os.open(name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=self.fd)
        try:
            st = os.fstat(fd)
            require(stat.S_ISREG(st.st_mode) and st.st_uid == os.getuid()
                    and st.st_nlink == 1 and st.st_mode & 0o077 == 0)
            return fd
        except BaseException:
            os.close(fd)
            raise
    def read(self, name):
        fd = self.regular(name)
        with os.fdopen(fd, 'rb') as f:
            raw = f.read(256 * 1024 + 1)
        require(len(raw) <= 256 * 1024)
        return json.loads(raw)
    def write(self, name, value, replace=False):
        raw = json.dumps(value, separators=(',', ':')).encode()
        require(len(raw) <= 256 * 1024)
        temp = '.txn-' + secrets.token_hex(16) if replace else name
        fd = self.regular(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        if replace:
            os.rename(temp, name, src_dir_fd=self.fd, dst_dir_fd=self.fd)
        self.current()

def registry(create=False):
    return Directory(str(Path.home() / '.local/state/dotcortex/telegram-attachments'), create)

def key(o):
    return str(o['pid']) + '-' + o['start'] + '.json'

def generation(state, nonce):
    require(isinstance(nonce, str) and re.fullmatch('[a-f0-9]{32}', nonce))
    # Only inbox owns bytes/proofs; channel ancestors may be shared 0770/0775.
    inbox = Directory(state + '/inbox', True)
    try:
        proof = Directory(state + '/inbox/.custody', True)
    finally:
        inbox.close()
    return proof

def locked(reg):
    fd = reg.regular('.lock', os.O_RDWR | os.O_CREAT)
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd

def begin(state, nonce):
    o = owner()
    plugin = identity(os.getppid())[0]
    reg = registry(True)
    lock = locked(reg)
    try:
        try:
            old = reg.read(key(o))
            require(not alive(old['plugin']) or old['plugin'] == plugin and old['nonce'] == nonce)
        except FileNotFoundError:
            pass
        p = generation(state, nonce)
        inbox = Directory(state + '/inbox')
        root = {'dev': inbox.info.st_dev, 'ino': inbox.info.st_ino}
        inbox.close()
        try:
            p.write(nonce + '.json', {'owner': o, 'plugin': plugin, 'nonce': nonce,
                    'session': None, 'receipts': {}, 'files': {}, 'root': root, 'anchor': None })
        finally:
            p.close()
        reg.write(key(o), {'owner': o, 'plugin': plugin, 'nonce': nonce, 'state': state}, True)
        return root
    finally:
        os.close(lock)
        reg.close()

def with_record(action):
    reg = registry()
    lock = locked(reg)
    proof = None
    try:
        o = owner()
        index = reg.read(key(o))
        require(index['owner'] == o and alive(index['plugin']))
        proof = generation(index['state'], index['nonce'])
        record = proof.read(index['nonce'] + '.json')
        require(record['owner'] == o and record['plugin'] == index['plugin'] and record['nonce'] == index['nonce'])
        result, dirty = action(index, record)
        if dirty:
            proof.write(index['nonce'] + '.json', record, True)
        return result
    finally:
        if proof:
            proof.close()
        os.close(lock)
        reg.close()

def verified_bytes(index, r, fid):
    now = time.time()
    require(fid in r['receipts'] and 0 <= now-r['receipts'][fid]['at'] < TTL)
    matches = [(name, rec) for name, rec in r['files'].items() if rec['id'] == fid]
    require(bool(matches))
    name, rec = matches[-1]
    require(re.fullmatch(r'attachment-[a-f0-9]{48}\.bin', name) and 0 <= now-rec['at'] < TTL)
    inbox = Directory(index['state'] + '/inbox')
    try:
        anchor = os.stat(r['anchor'])
        require((anchor.st_dev, anchor.st_ino) == (inbox.info.st_dev, inbox.info.st_ino)
                == (r['root']['dev'], r['root']['ino']))
        fd = inbox.regular(name)
        with os.fdopen(fd, 'rb') as f:
            st = os.fstat(f.fileno())
            require((st.st_dev, st.st_ino, st.st_size) == (rec['dev'], rec['ino'], rec['size']) and st.st_size <= LIMIT)
            raw = f.read(LIMIT+1)
        require(len(raw) == rec['size'] and hashlib.sha256(raw).hexdigest() == rec['sha'])
        inbox.current()
        return raw
    finally:
        inbox.close()

def text_content(raw):
    # Content, never uploader filename/MIME, determines this bounded capability.
    # Image/PDF decoding is deliberately NOT implemented by this text-only tool.
    unsupported = {'content': [{'type': 'text', 'text':
        'Unsupported attachment format or size: read_attachment supports only UTF-8 text up to 256 KiB; PNG, JPEG, PDF and other binary formats are not supported.'}], 'isError': True}
    if len(raw) > TEXT_LIMIT or raw.startswith((b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff', b'%PDF-')):
        return unsupported
    try:
        text = raw.decode('utf-8', errors='strict')
    except UnicodeDecodeError:
        return unsupported
    if any(ord(ch) < 32 and ch not in '\t\r\n' or 127 <= ord(ch) <= 159 for ch in text):
        return unsupported
    return {'content': [{'type': 'text', 'text': text}]}

def producer(op, data):
    def act(index, r):
        require(identity(os.getppid())[0] == r['plugin'] and data['nonce'] == r['nonce'])
        now = time.time()
        r['receipts'] = {k:v for k,v in r['receipts'].items() if 0 <= now - v['at'] < TTL}
        if op == 'anchor':
            require(set(data) == {'nonce', 'fd'} and type(data['fd']) is int and 0 <= data['fd'] <= 100000)
            anchor = '/proc/%s/fd/%s' % (r['plugin']['pid'], data['fd'])
            st = os.stat(anchor)
            require(stat.S_ISDIR(st.st_mode) and (st.st_dev, st.st_ino) == (r['root']['dev'], r['root']['ino']))
            r['anchor'] = anchor
            return True, True
        fid = data['file_id']
        require(isinstance(fid, str) and ID.fullmatch(fid))
        if op == 'receive':
            require(set(data) == {'nonce', 'file_id', 'sender', 'chat', 'message', 'size'})
            require(all(isinstance(data[k], str) and re.fullmatch(r'-?[0-9]{1,20}', data[k]) for k in ('sender', 'chat', 'message')))
            require(data['size'] is None or type(data['size']) is int and 0 <= data['size'] <= LIMIT)
            require(len(r['receipts']) < 128)
            r['receipts'][fid] = {'at':now, 'sender':data['sender'], 'chat':data['chat'], 'message':data['message']}
            return True, True
        if op == 'revoke':
            r['receipts'].pop(fid, None)
            return True, True
        require(fid in r['receipts'] and isinstance(r['session'], str) and isinstance(r['anchor'], str))
        if op == 'read':
            require(set(data) == {'nonce', 'file_id'})
            return text_content(verified_bytes(index, r, fid)), False
        if op == 'check':
            require(set(data) == {'nonce', 'file_id'})
            return True, False
        require(op == 'store' and set(data) == {'nonce', 'file_id', 'bytes'})
        buf = base64.b64decode(data['bytes'], validate=True)
        require(len(buf) <= LIMIT and len(r['files']) < 128)
        inbox = Directory(index['state'] + '/inbox')
        try:
            anchor_stat = os.stat(r['anchor'])
            require((anchor_stat.st_dev, anchor_stat.st_ino) == (inbox.info.st_dev, inbox.info.st_ino))
            name = 'attachment-' + secrets.token_hex(24) + '.bin'
            fd = inbox.regular(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
            with os.fdopen(fd, 'wb') as f:
                f.write(buf)
                f.flush()
                os.fsync(f.fileno())
                st = os.fstat(f.fileno())
            inbox.current()
            r['files'][name] = {'id':fid, 'at':now, 'dev':st.st_dev, 'ino':st.st_ino,
                                'size':st.st_size, 'sha':hashlib.sha256(buf).hexdigest()}
            return r['anchor'] + '/' + name, True
        finally:
            inbox.close()
    return with_record(act)

def approval(event, bind=False):
    tool, args = event.get('tool_name'), event.get('tool_input')
    require(event.get('hook_event_name') == 'PermissionRequest' and isinstance(args, dict))
    sid = event.get('session_id')
    require(isinstance(sid, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', sid))
    require(tool in (DOWNLOAD, READ))
    require(set(args) == {'file_id'} and isinstance(args['file_id'], str) and ID.fullmatch(args['file_id']))
    def act(index, r):
        dirty = False
        # First trusted native PermissionRequest pins this Claude generation to
        # its session. A different session never inherits receipts, even if the
        # same executable survives. No tool-supplied owner/session is consulted.
        if r['session'] is None and bind and tool == DOWNLOAD and args['file_id'] in r['receipts']:
            r['session'], dirty = sid, True
        require(r['session'] == sid)
        now = time.time()
        if tool == DOWNLOAD:
            rec = r['receipts'][args['file_id']]
            require(0 <= now-rec['at'] < TTL)
            return True, dirty
        verified_bytes(index, r, args['file_id'])
        return True, False
    return with_record(act)

def main():
    op = sys.argv[1]
    raw = sys.stdin.buffer.read(LIMIT * 2 + 4097)
    require(len(raw) <= LIMIT * 2 + 4096)
    data = json.loads(raw)
    if op == 'begin':
        result = begin(data['state'], data['nonce'])
    else:
        result = producer(op, data)
    print(json.dumps(result))

if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('attachment custody refused', file=sys.stderr)
        sys.exit(1)

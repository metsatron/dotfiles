import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, rmSync, symlinkSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { prepareRoots, extendConfinement, checkedScopedTarget, apply } from '../../../../.bots/templates/orca-seat-scope.mjs';

const base = mkdtempSync(join(dirname(fileURLToPath(import.meta.url)), 'fixtures-'));
const allowed = join(base, 'allowed');
const outside = join(base, 'outside');
mkdirSync(allowed); mkdirSync(outside);
const roots = prepareRoots([allowed]);
const wrapped = () => ({ argv: ['bwrap', '--ro-bind', '/', '/', '--tmpfs', '/tmp', '--bind', '/workspace', '/workspace', '--', 'bash', '-c', 'true'], enforcement: 'full', denialSignatures: ['Read-only file system'], runnerFailureRules: [] });
const denied = Object.assign(new Error('denied'), { code: 'FS_SANDBOX_DENIED' });
const fs = { resolve: async p => ({ displayPath: p, targetKey: p }) };

process.on('exit', () => rmSync(base, { recursive: true, force: true }));
test('canonicalizes and deduplicates roots', () => assert.deepEqual(prepareRoots([allowed, allowed]), [allowed]));
test('rejects root and missing grants', () => { assert.throws(() => prepareRoots(['/'])); assert.throws(() => prepareRoots([join(base, 'missing')])); });
test('only workspace-write receives extra binds', () => {
  const x = extendConfinement(wrapped(), { mode: 'workspace-write' }, roots, '/node24/bin', '/usr/bin');
  assert.ok(x.argv.join(' ').includes(`--bind ${allowed} ${allowed}`));
  assert.ok(x.argv.join(' ').includes('--setenv PATH /node24/bin:/usr/bin'));
  assert.equal(x.enforcement, 'full'); assert.deepEqual(x.denialSignatures, ['Read-only file system']);
});
test('read-only stays read-only but receives correct node', () => {
  const x = extendConfinement(wrapped(), { mode: 'read-only' }, roots, '/node24/bin', '/usr/bin');
  assert.ok(!x.argv.includes(allowed)); assert.ok(x.argv.includes('/node24/bin:/usr/bin'));
});
test('unconfined policy receives no fabricated enforcement', () => {
  const x = wrapped(); assert.equal(extendConfinement(x, { mode: 'danger-full-access' }, roots, '/node24/bin', ''), x);
});
test('unknown confinement backend fails closed', () => assert.throws(() => extendConfinement({ ...wrapped(), argv: ['unknown', '--', 'true'] }, { mode: 'workspace-write' }, roots, '/node24/bin', '')));
test('missing command separator fails closed', () => assert.throws(() => extendConfinement({ ...wrapped(), argv: ['bwrap'] }, { mode: 'workspace-write' }, roots, '/node24/bin', '')));
test('allowed fs target uses fresh resolution', async () => {
  const p = join(allowed, 'file'); const fresh = await checkedScopedTarget(fs, async () => { throw denied; }, { displayPath: p, targetKey: '/stale' }, { mode: 'workspace-write' }, roots);
  assert.equal(fresh.targetKey, p);
});
test('sibling prefix is not a grant', async () => assert.rejects(checkedScopedTarget(fs, async () => { throw denied; }, { displayPath: `${allowed}-sibling/file` }, { mode: 'workspace-write' }, roots), e => e === denied));
test('fs read-only is not bypassed', async () => assert.rejects(checkedScopedTarget(fs, async () => { throw denied; }, { displayPath: join(allowed, 'file') }, { mode: 'read-only' }, roots), e => e === denied));
test('non-policy error is preserved', async () => { const e = new Error('disk failure'); await assert.rejects(checkedScopedTarget(fs, async () => { throw e; }, { displayPath: allowed }, { mode: 'workspace-write' }, roots), x => x === e); });
test('existing successful checks are preserved exactly', async () => { const x = {}; assert.equal(await checkedScopedTarget(fs, async () => x, {}, { mode: 'workspace-write' }, roots), x); });
test('resolved symlink escape is denied', async () => {
  symlinkSync(outside, join(allowed, 'escape'));
  const resolvingFs = { resolve: async p => ({ displayPath: p, targetKey: join(outside, 'file') }) };
  await assert.rejects(checkedScopedTarget(resolvingFs, async () => { throw denied; }, { displayPath: join(allowed, 'escape/file') }, { mode: 'workspace-write' }, roots), e => e === denied);
});
test('plugin mounts and restores only this context', async () => {
  let dispose;
  const confine = () => wrapped(); const checkedTarget = async () => { throw denied; };
  const ctx = { sandbox: { confine }, fs: { ...fs, checkedTarget }, sandboxPolicy: { resolve: () => ({ mode: 'workspace-write' }) }, effect: f => { dispose = f(); }, logger: { info: () => {} } };
  apply(ctx, { roots: [allowed] }); assert.notEqual(ctx.sandbox.confine, confine); assert.notEqual(ctx.fs.checkedTarget, checkedTarget);
  assert.ok(ctx.sandbox.confine(['true'], { mode: 'workspace-write' }).argv.includes(allowed));
  dispose(); assert.equal(ctx.sandbox.confine, confine); assert.equal(ctx.fs.checkedTarget, checkedTarget);
});

// Orca's operator-authorized, multi-root workspace extension.
// No global mode change, permission bypass, upstream edit or unconfined fallback.
import { realpathSync, statSync } from 'node:fs';
import { basename, dirname, relative, isAbsolute, sep } from 'node:path';

export const name = 'helmcortex-orca-seat-scope';
export const inject = ['sandbox', 'fs', 'sandboxPolicy'];

export function prepareRoots(configured) {
  if (!Array.isArray(configured) || configured.length === 0) throw new Error('orca-seat-scope: explicit roots required');
  return [...new Set(configured.map(p => {
    if (typeof p !== 'string' || !isAbsolute(p)) throw new Error('orca-seat-scope: roots must be absolute');
    const root = realpathSync(p);
    if (root === sep || !statSync(root).isDirectory()) throw new Error('orca-seat-scope: unsafe or non-directory root');
    return root;
  }))];
}

export function extendConfinement(wrapped, policy, roots, nodeBin, inheritedPath) {
  if (policy.mode !== 'workspace-write' && policy.mode !== 'read-only') return wrapped;
  const argv = wrapped.argv;
  if (basename(argv[0] ?? '') !== 'bwrap' || !argv.includes('--ro-bind')) throw new Error('orca-seat-scope: bwrap confinement required; refusing unsupported backend');
  const split = argv.indexOf('--');
  if (split < 0) throw new Error('orca-seat-scope: missing confinement command boundary');
  const extra = ['--setenv', 'PATH', `${nodeBin}:${inheritedPath ?? ''}`];
  if (policy.mode === 'workspace-write') for (const root of roots) extra.push('--bind', root, root);
  return { ...wrapped, argv: [...argv.slice(0, split), ...extra, ...argv.slice(split)] };
}

function contained(target, root) {
  const suffix = relative(root, target);
  return suffix === '' || (suffix !== '..' && !suffix.startsWith(`..${sep}`) && !isAbsolute(suffix));
}

export async function checkedScopedTarget(fs, original, target, policy, roots) {
  try { return await original(target, policy); }
  catch (error) {
    if (policy.mode !== 'workspace-write' || error.code !== 'FS_SANDBOX_DENIED') throw error;
    // Re-resolve using the native backend, preserving canonical/symlink safety.
    const fresh = await fs.resolve(target.displayPath);
    if (!roots.some(root => contained(fresh.targetKey, root))) throw error;
    return fresh;
  }
}

export function apply(ctx, config) {
  const roots = prepareRoots(config.roots);
  const nodeBin = dirname(process.execPath);
  if (Number(process.versions.node.split('.')[0]) < 24) throw new Error('orca-seat-scope: Node 24+ required');
  ctx.effect(() => {
    const sandbox = ctx.sandbox;
    const fs = ctx.fs;
    if (typeof sandbox.confine !== 'function' || typeof fs.checkedTarget !== 'function') throw new Error('orca-seat-scope: incompatible capability seam');
    const originalConfine = sandbox.confine;
    const originalChecked = fs.checkedTarget;
    function confined(argv, policy) {
      return extendConfinement(originalConfine.call(sandbox, argv, policy), policy, roots, nodeBin, process.env.PATH);
    }
    function checked(target, policy) {
      const effective = policy ?? ctx.sandboxPolicy.resolve();
      return checkedScopedTarget(fs, (t, p) => originalChecked.call(fs, t, p), target, effective, roots);
    }
    sandbox.confine = confined;
    fs.checkedTarget = checked;
    ctx.logger.info(`Orca scoped workspace extension mounted (${roots.length} canonical roots; Node ${process.versions.node}; confinement retained)`);
    return () => {
      if (sandbox.confine === confined) sandbox.confine = originalConfine;
      if (fs.checkedTarget === checked) fs.checkedTarget = originalChecked;
    };
  });
}

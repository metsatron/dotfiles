// Offline boot proof for the sterile FCA DSH worker (SOURCE candidate). Boots the real headless profile with the reviewed overlay inside
// the launcher's sandbox (no network), then reports names only: the boot verdict, any entry that did not activate, and the paths
// (never contents) the boot created under the sterile home. It performs no model, tool or network action. Exit 0 = booted, 1 = failed.
import { readdirSync } from 'node:fs';
import { join } from 'node:path';
import { runCli } from '/opt/dsh/node_modules/@deepseek-ai/dsh/lib/bin.js';

const argv = ['--from-default-profile', 'headless', '--patch', '/workspace/fca-synthetic/cordis.patch.yml', '--profile', 'fca-synthetic'];
process.argv = [process.argv[0], process.argv[1], ...argv];

function walk(root, rel = '') {
  let names = [];
  for (const entry of readdirSync(join(root, rel), { withFileTypes: true })) {
    const path = join(rel, entry.name);
    names.push(entry.isDirectory() ? `${path}/` : path);
    if (entry.isDirectory() && entry.name !== 'node_modules') names = names.concat(walk(root, path)); // the module farm is links only
  }
  return names.sort();
}
const files = (root) => { try { return walk(root); } catch { return []; } };
const report = (verdict, extra) => process.stdout.write(`${JSON.stringify({ boot: verdict, ...extra })}\n`);

const deadline = setTimeout(() => { report('failed', { reason: 'boot deadline exceeded' }); process.exit(1); }, 30000);
try {
  await runCli();
} catch (error) {
  const detail = String(error?.message ?? error).split('\n').filter((line) => !line.startsWith('    at ')).slice(0, 40);
  report('failed', { detail });
  process.exit(1);
}
clearTimeout(deadline);
report('ok', { dsh_home: files(process.env.DSH_HOME), home: files(process.env.HOME) });
process.kill(process.pid, 'SIGTERM'); // the launcher's own signal handler disposes the tree and exits 0

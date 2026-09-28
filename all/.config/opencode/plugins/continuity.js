import { chmod, mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { execFile } from "node:child_process";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { promisify } from "node:util";

const SESSION = /^[A-Za-z0-9._:-]{1,240}$/;
const REFERENCE = /^continuity:\/\/[A-Za-z0-9._:/-]{1,150}$/;
const execute = promisify(execFile);
const RECEIPT_MAX_AGE_MS = 1800 * 1000;
const CLOCK_SKEW_MS = 10 * 1000;
const idleTimers = new Map();

const idleDelayMs = () => {
  const value = Number(process.env.OPENCODE_WARM_IDLE_DELAY_SECONDS ?? 900);
  if (!Number.isFinite(value) || value < 0) return 900 * 1000;
  return Math.min(value, 24 * 60 * 60) * 1000;
};

const stateRoot = () => {
  if (process.env.OPENCODE_WARM_STATE_DIR) return process.env.OPENCODE_WARM_STATE_DIR;
  const stateHome = process.env.XDG_STATE_HOME || join(homedir(), ".local", "state");
  return join(stateHome, "opencode-idle-continuity");
};

const writeEvent = async (sessionID) => {
  if (!SESSION.test(sessionID)) return;
  const target = join(stateRoot(), "events", `${sessionID}.json`);
  const directory = dirname(target);
  await mkdir(directory, { recursive: true, mode: 0o700 });
  await chmod(directory, 0o700);
  const temporary = `${target}.tmp-${process.pid}-${Date.now()}`;
  const payload = JSON.stringify({
    schema: "dotcortex.opencode-continuity-event.v1",
    type: "session.compacted",
    session_id: sessionID,
    observed_at: Date.now() / 1000,
  }) + "\n";
  await writeFile(temporary, payload, { encoding: "utf8", mode: 0o600 });
  await rename(temporary, target);
};

const handoffFor = async (sessionID) => {
  try {
    const raw = await readFile(join(stateRoot(), "handoff.json"), "utf8");
    const value = JSON.parse(raw);
    if (value?.schema !== "dotcortex.opencode-continuity-receipt.v1") return null;
    if (value?.kind !== "handoff" || value?.session_id !== sessionID) return null;
    if (typeof value?.reference !== "string" || !REFERENCE.test(value.reference)) return null;
    if (typeof value?.created_at !== "number" || !Number.isFinite(value.created_at)) return null;
    const age = Date.now() - value.created_at * 1000;
    if (age < -CLOCK_SKEW_MS || age > RECEIPT_MAX_AGE_MS) return null;
    const critical = value?.critical;
    if (critical !== undefined && (critical === null || typeof critical !== "object" || Array.isArray(critical))) return null;
    const clean = {};
    for (const key of ["objective", "next", "prohibition"]) {
      const item = critical?.[key];
      if (typeof item === "string" && item.length > 0 && item.length <= 500) clean[key] = item;
    }
    return {
      reference: value.reference,
      checkpoint: typeof value.checkpoint_id === "string" ? value.checkpoint_id : "unknown",
      sourceMessage: typeof value.message_id === "string" ? value.message_id : "unknown",
      critical: clean,
    };
  } catch {
    return null;
  }
};

const dispatchController = async (sessionID, eventType) => {
  if (!SESSION.test(sessionID)) return;
  const binary = process.env.OPENCODE_WARM_EVENT_BIN || join(homedir(), ".local", "bin", "opencode-warm-event");
  try {
    await execute(binary, [
      "--session", sessionID,
      "--event", eventType,
      "--observed-at", String(Date.now() / 1000),
    ], { timeout: 30000, maxBuffer: 65536 });
  } catch {
    // The controller is fail-closed and writes its own bounded state. A refusal
    // must never destabilize OpenCode's event loop.
  }
};

const dispatchAfterQuietPeriod = async (sessionID) => {
  const previous = idleTimers.get(sessionID);
  if (previous) clearTimeout(previous);
  const delay = idleDelayMs();
  if (delay === 0) {
    await dispatchController(sessionID, "session.idle");
    return;
  }
  const timer = setTimeout(() => {
    idleTimers.delete(sessionID);
    void dispatchController(sessionID, "session.idle");
  }, delay);
  timer.unref?.();
  idleTimers.set(sessionID, timer);
};

export const OpenCodeContinuityPlugin = async () => ({
  event: async ({ event }) => {
    const sessionID = event?.properties?.sessionID;
    if (typeof sessionID !== "string") return;
    if (event?.type === "session.compacted") {
      const pending = idleTimers.get(sessionID);
      if (pending) clearTimeout(pending);
      idleTimers.delete(sessionID);
      await writeEvent(sessionID);
      await dispatchController(sessionID, "session.compacted");
    } else if (event?.type === "session.idle") {
      await dispatchAfterQuietPeriod(sessionID);
    }
  },
  "experimental.session.compacting": async ({ sessionID }, output) => {
    const handoff = await handoffFor(sessionID);
    if (!handoff) return;
    output.context.push(`HelmCortex continuity handoff: ${JSON.stringify(handoff)}`);
  },
  "experimental.compaction.autocontinue": async ({ sessionID }, output) => {
    if (await handoffFor(sessionID)) output.enabled = false;
  },
});

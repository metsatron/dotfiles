const SUMMARY_URL = "http://127.0.0.1:8098/v1/summary";
// The backend reserves 256 output tokens and 128 prompt-margin tokens from a
// 2048-token context.  This conservative wire cap keeps each client job well
// below the remaining tokenizer budget even for byte-heavy JSON/Unicode.
const MAX_CHUNK_BYTES = 1_200;
const MAX_RECENT_ROWS = 12;
const MODEL = "decider-2b-v11-Q4_K_M";
const MODEL_SHA256 = "b7c132a67934d51c81abc96bb7724800f965ff5a288aed3e1ca7d8bc349c1386";

let testTransport = null;
export function setSummaryTransportForTest(transport) { testTransport = transport; }

function canonical(value) {
  if (value === null || typeof value === "string" || typeof value === "boolean") return JSON.stringify(value);
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("non-finite number");
    return JSON.stringify(Object.is(value, -0) ? 0 : value);
  }
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  }
  throw new Error("non-JSON value");
}

async function digest(value) {
  const bytes = new TextEncoder().encode(canonical(value));
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(hash)].map((x) => x.toString(16).padStart(2, "0")).join("");
}

function normalizeRow(row) {
  if (!row || !["user", "assistant"].includes(row.role) || typeof row.text !== "string") throw new Error("invalid native message");
  const copy = { ...row, toolUses: Array.isArray(row.toolUses) ? row.toolUses.map((x) => ({ ...x })) : [] };
  if (row.toolResults !== undefined) copy.toolResults = row.toolResults.map((x) => ({ ...x }));
  else copy.toolResults = [];
  return copy;
}

function validateRows(rows) {
  if (!Array.isArray(rows) || rows.length === 0) throw new Error("empty native message set");
  const uses = new Set();
  const results = new Set();
  const normalized = rows.map(normalizeRow);
  for (const row of normalized) {
    for (const use of row.toolUses) {
      if (typeof use.tool_use_id !== "string" || typeof use.tool !== "string" || !use.input || typeof use.input !== "object" || uses.has(use.tool_use_id)) throw new Error("invalid or duplicate tool use");
      uses.add(use.tool_use_id);
    }
    for (const result of row.toolResults) {
      if (typeof result.tool_use_id !== "string" || typeof result.text !== "string" || typeof result.isError !== "boolean" || results.has(result.tool_use_id)) throw new Error("invalid or duplicate tool result");
      results.add(result.tool_use_id);
    }
  }
  if (uses.size !== results.size || [...uses].some((id) => !results.has(id))) throw new Error("unmatched tool pair");
  return normalized;
}

function groups(rows) {
  const result = [];
  for (let index = 0; index < rows.length;) {
    const group = [rows[index++]];
    const pending = new Set(group[0].toolUses.map((x) => x.tool_use_id));
    while (pending.size && index < rows.length) {
      group.push(rows[index]);
      for (const item of rows[index].toolResults) pending.delete(item.tool_use_id);
      index += 1;
    }
    if (pending.size) throw new Error("tool pair crosses chunk boundary");
    result.push(group);
  }
  return result;
}

function chunkRows(rows) {
  const summaryRows = segmentRows(rows);
  const chunks = [];
  let current = [];
  let bytes = 2;
  for (const group of groups(summaryRows)) {
    const size = new TextEncoder().encode(canonical(group)).length;
    if (size > MAX_CHUNK_BYTES) throw new Error("exchange exceeds bounded transport");
    if (current.length && bytes + size > MAX_CHUNK_BYTES) {
      chunks.push(current);
      current = [];
      bytes = 2;
    }
    current.push(...group);
    bytes += size;
  }
  if (current.length) chunks.push(current);
  return chunks;
}

function segmentRows(rows) {
  const output = [];
  for (const [exchangeIndex, exchange] of groups(rows).entries()) {
    const payloads = exchange.map((row) => canonical(row));
    const exchangeBytes = payloads.reduce((sum, text) => sum + new TextEncoder().encode(text).length, 0);
    if (exchangeBytes <= MAX_CHUNK_BYTES) {
      output.push(...exchange);
      continue;
    }
    const exchangeHandles = exchange.map((row, rowIndex) => row.handle || row.uuid || `exchange-${exchangeIndex}-row-${rowIndex}`);
    const exchangeToolIds = exchange.flatMap((row) => row.toolUses.map((use) => use.tool_use_id));
    for (let rowIndex = 0; rowIndex < exchange.length; rowIndex += 1) {
      const row = exchange[rowIndex];
      const payload = payloads[rowIndex];
      const characters = Math.max(1, Math.floor(MAX_CHUNK_BYTES / 2));
      const codepoints = Array.from(payload);
      const total = codepoints.length;
      for (let offset = 0, order = 0; offset < total; offset += characters, order += 1) {
        const end = Math.min(total, offset + characters);
        output.push({
          role: row.role, text: codepoints.slice(offset, end).join(""), toolUses: [], toolResults: [],
          source_fragment: {
            source_handle: exchangeHandles[rowIndex],
            source_role: row.role, field: "canonical-row", offset, end, total, order,
            exchange_order: rowIndex, exchange_handles: exchangeHandles,
            tool_use_ids: exchangeToolIds,
          },
        });
      }
    }
  }
  return output;
}

function recentCompleteRows(rows) {
  const all = groups(rows);
  const selected = [];
  let count = 0;
  for (let index = all.length - 1; index >= 0 && count < MAX_RECENT_ROWS; index -= 1) {
    selected.unshift(...all[index]);
    count += all[index].length;
  }
  return selected;
}

async function summaryRequest($, rows, sourceEpoch, phase) {
  const normalized = validateRows(rows);
  const session = await $.session.id();
  const canonicalMessages = canonical(normalized);
  const sourceHash = await digest(normalized);
  return {
    operation: "summary.v1", model: MODEL, model_sha256: MODEL_SHA256,
    request_id: `${session}:${sourceEpoch}:${phase}:${sourceHash.slice(0, 16)}:${Date.now()}`,
    source_session_id: session, source_epoch: sourceEpoch,
    source_hash: sourceHash, canonical_messages: canonicalMessages, messages: normalized,
    max_output_tokens: 256, phase, async: true, limits: { deadline_ms: 120000 },
  };
}

async function requestSummary($, rows, sourceEpoch, phase) {
  const payload = await summaryRequest($, rows, sourceEpoch, phase);
  let response = testTransport ? await testTransport(payload) : await $.http.fetch(SUMMARY_URL, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload),
  });
  if (!testTransport && response.status === 202) {
    const ticket = JSON.parse(response.text);
    if (ticket.request_id !== payload.request_id || typeof ticket.poll_path !== "string" ||
        !/^\/v1\/summary\/jobs\/[a-f0-9]{32}$/.test(ticket.poll_path)) {
      throw new Error("invalid local summary ticket");
    }
    const origin = new URL(SUMMARY_URL).origin;
    const deadline = Date.now() + 120000;
    let polls = 0;
    do {
      if (Date.now() >= deadline || ++polls > 25) throw new Error("local summary deadline exceeded");
      response = await $.http.fetch(origin + ticket.poll_path);
      if (response.status === 202) {
        const pending = JSON.parse(response.text);
        if (pending.poll_path !== ticket.poll_path || pending.request_id !== payload.request_id) {
          throw new Error("stale local summary ticket");
        }
      }
    } while (response.status === 202);
  }
  const body = testTransport ? response : JSON.parse(response.text);
  if ((!testTransport && response.status !== 200) || body.operation !== "summary.v1" || body.request_id !== payload.request_id ||
      body.source_session_id !== payload.source_session_id || body.source_epoch !== payload.source_epoch ||
      body.source_hash !== payload.source_hash || body.truncated !== false || typeof body.summary !== "string" || !body.summary.trim()) {
    throw new Error("invalid or stale summary checkpoint");
  }
  return body.summary.trim();
}

async function tailFingerprint($) {
  const rows = await $.session.messages({ last: 1 });
  if (!Array.isArray(rows) || rows.length !== 1) throw new Error("current session tail unavailable");
  const row = normalizeRow(rows[0]);
  delete row.handle;
  delete row.uuid;
  return digest([row]);
}

export function register(on) {
  let armed = null;

  on("session.start", async ($, event, next) => {
    const result = await next(event);
    const path = await $.env.get("CLAUDE_WARM_DECIDER_READY");
    if (path) {
      await $.fs.write(path, JSON.stringify({
        protocol: "decider-summary.v1", session_id: await $.session.id(),
        channel: await $.env.get("CLAUDE_IDLE_CHANNEL"),
      }));
    }
    return result;
  });

  on("session.compact", async ($, event, next) => {
    if (event.trigger !== "manual" || event.instructions !== "decider-local-only") return next(event);
    if (armed) return { skip: "local summary already running" };
    armed = true;
    try {
      const snapshot = validateRows(event.messages);
      const sourceEpoch = snapshot.length;
      const snapshotHash = await digest(snapshot);
      const tailBefore = await tailFingerprint($);
      const recent = recentCompleteRows(snapshot);
      const older = snapshot.slice(0, snapshot.length - recent.length);
      const summarySource = older.length ? older : snapshot;
      const summaries = [];
      for (const chunk of chunkRows(summarySource)) summaries.push(await requestSummary($, chunk, sourceEpoch, "chunk"));
      let reduced = summaries;
      let rounds = 0;
      while (reduced.length > 1) {
        if (++rounds > 8) throw new Error("summary reduction did not converge");
        const rowsForReduce = reduced.map((text) => ({ role: "assistant", text, toolUses: [], toolResults: [] }));
        const reducedNext = [];
        for (const chunk of chunkRows(rowsForReduce)) reducedNext.push(await requestSummary($, chunk, sourceEpoch, "reduce"));
        if (reducedNext.length >= reduced.length) throw new Error("summary reduction made no progress");
        reduced = reducedNext;
      }
      if (await digest(validateRows(event.messages)) !== snapshotHash || await tailFingerprint($) !== tailBefore) return { skip: "session changed during summary" };
      if (await digest(validateRows(event.messages)) !== snapshotHash || await tailFingerprint($) !== tailBefore) return { skip: "session changed before checkpoint" };
      return { messages: [{ role: "assistant", text: reduced[0], toolUses: [] }, ...recent] };
    } catch (_error) {
      return { skip: "local Decider summary unavailable or incomplete; original context preserved" };
    } finally {
      armed = null;
    }
  });
}

export { canonical, chunkRows, normalizeRow, recentCompleteRows, segmentRows, validateRows };

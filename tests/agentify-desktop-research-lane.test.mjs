import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { pathToFileURL } from 'node:url';
const { ChatGPTController } = await import(pathToFileURL(process.env.AGENTIFY_CONTROLLER).href);

function harness(overrides = {}, changeAfterTyping = false) {
  const state = { host: 'chatgpt.com', chat: true, work: false, effort: 'high', model: 'GPT-6', expanded: false, ...overrides };
  const effects = [];
  const node = (text, attrs = {}) => ({ innerText: text, textContent: text,
    getAttribute: k => attrs[k] ?? null, hasAttribute: k => k in attrs, getBoundingClientRect: () => ({ width: 100, height: 30 }),
    click: () => { state.expanded = true; } });
  const page = {
    async evaluate(js) {
      if (js.includes('HELMCORTEX_AGENTIFY_RESEARCH_LANE_PROBE_V1')) {
        let buttons = [node('Chat', { 'aria-pressed': String(state.chat) }), node('Work', { 'aria-pressed': String(state.work) }),
          node('High', { 'aria-label': 'Select ChatGPT model', 'data-selected-reasoning-effort': state.effort, 'aria-expanded': String(state.expanded) })];
        if (state.thread) buttons = buttons.slice(2).concat(node('ChatGPT', { 'aria-label': 'Switch mode, current mode: ChatGPT' }));
        const rows = state.expanded ? [node(state.model), node('GPT-6.1')] : [];
        return vm.runInNewContext(js, {
          location: { hostname: state.host }, getComputedStyle: () => ({ visibility: 'visible', display: 'block' }),
          document: { querySelectorAll: sel => sel === 'button' ? buttons : rows.slice(0, 1) }
        });
      }
      if (js.includes('HELMCORTEX_AGENTIFY_RESEARCH_LANE_OPEN_V1')) { state.expanded = true; return; }
      if (js.includes('const hasTurnstile')) return { blocked: false, promptVisible: true, indicators: {} };
      if (js.includes('selectNodeContents')) return { ok: true, promptLen: 0 };
      if (js.includes('missing_prompt_textarea')) return { ok: true, rect: { x: 1, y: 1, w: 100, h: 30 } };
      throw new Error('unexpected browser operation: ' + js.slice(0, 80));
    },
    async getUrl() { return 'https://chatgpt.com/'; },
    async sendKey(key) { effects.push(key); if (key === 'Escape') state.expanded = false; },
    async insertText(text) { effects.push({ text }); if (changeAfterTyping) { state.chat = false; state.work = true; } },
    async moveMouse() {}, async mouseDown() {}, async mouseUp() {}
  };
  return { controller: new ChatGPTController({ page, selectors: { promptTextarea: '#prompt-textarea' } }), effects, state };
}

for (const [name, state] of [
  ['Work', { chat: false, work: true }],
  ['ambiguous Chat and Work', { chat: true, work: true }],
  ['unknown mode', { chat: false }],
  ['extra high', { effort: 'xhigh' }],
  ['missing effort', { effort: null }],
  ['lower effort', { effort: 'medium' }],
  ['GPT-6.1 even with GPT-6 listed', { model: 'GPT-6.1' }],
  ['unknown model', { model: '' }],
]) {
  test(`${name} blocks send without typing or submission`, async () => {
    const h = harness(state);
    await assert.rejects(h.controller.send({ text: 'do not spend', timeoutMs: 3000 }), /research_lane_blocked/);
    assert.equal(h.effects.some(e => typeof e === 'object'), false);
    assert.equal(h.effects.includes('Enter'), false);
  });
}
test('query shares the same policy boundary', async () => {
  const h = harness({ model: 'GPT-6.1' });
  await assert.rejects(h.controller.query({ prompt: 'do not spend', timeoutMs: 3000 }), /research_lane_blocked/);
  assert.equal(h.effects.some(e => typeof e === 'object'), false);
});
test('switch to Work after typing is rejected by final send guard', async () => {
  const h = harness({}, true);
  await assert.rejects(h.controller.send({ text: 'safe draft', timeoutMs: 3000 }), /research_lane_blocked/);
  assert.equal(h.effects.some(e => typeof e === 'object'), true);
  assert.equal(h.effects.includes('Enter'), false);
});

test('read-only verification supports a resumed ordinary Chat conversation', async () => {
  const h = harness({ thread: true });
  const receipt = await h.controller.verifyResearchLane();
  assert.equal(receipt.ok, true);
  assert.equal(h.effects.some(e => typeof e === 'object'), false);
  assert.equal(h.effects.includes('Enter'), false);
});

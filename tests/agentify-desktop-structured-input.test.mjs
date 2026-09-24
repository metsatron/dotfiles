import test from 'node:test';
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';

const controllerPath = process.env.AGENTIFY_CONTROLLER;
if (!controllerPath) throw new Error('AGENTIFY_CONTROLLER is required');
const { ChatGPTController } = await import(pathToFileURL(controllerPath).href);

function readyState() {
  return {
    url: 'https://chatgpt.com/',
    title: 'ChatGPT',
    readyState: 'complete',
    blocked: false,
    promptVisible: true,
    kind: null,
    indicators: {
      hasTurnstile: false,
      hasArkose: false,
      hasVerifyButton: false,
      looks403: false,
      loginLike: false,
      rawPromptVisible: true,
      sendVisible: true
    }
  };
}

test('structured prompts use Shift+Enter and submit exactly once', async () => {
  const events = [];
  let waitForSendChecks = 0;
  let clearChecks = 0;
  const page = {
    async navigate() {},
    async evaluate(js) {
      if (js.includes('const hasTurnstile')) return readyState();
      if (js.includes('selectNodeContents')) {
        clearChecks += 1;
        return { ok: true, promptLen: 9 };
      }
      if (js.includes('const text = el.matches')) {
        clearChecks += 1;
        return { ok: true, promptLen: 0 };
      }
      if (js.includes('missing_prompt_textarea')) return { ok: true, rect: { x: 10, y: 10, w: 200, h: 40 } };
      if (js.includes('form.requestSubmit')) {
        events.push({ type: 'submit' });
        return true;
      }
      if (js.includes('already_generating')) return { ok: true, requestSubmit: true, host: 'chatgpt.com' };
      if (js.includes('promptLen')) {
        waitForSendChecks += 1;
        return waitForSendChecks >= 2
          ? { stopVisible: false, sendDisabled: true, promptLen: 0 }
          : { stopVisible: false, sendDisabled: false, promptLen: 32 };
      }
      throw new Error(`unexpected_eval:${js.slice(0, 80)}`);
    },
    async getUrl() { return 'https://chatgpt.com/'; },
    async sendKey(key, options = {}) {
      events.push({ type: 'key', key, modifiers: options.modifiers || [] });
    },
    async insertText(text) { events.push({ type: 'text', text }); },
    async moveMouse() {},
    async mouseDown() {},
    async mouseUp() {},
    async setFileInputFiles() {}
  };

  const controller = new ChatGPTController({
    page,
    selectors: {
      promptTextarea: '#prompt-textarea',
      sendButton: 'button[data-testid="send-button"]',
      stopButton: 'button[data-testid="stop-button"]',
      assistantMessage: '[data-message-author-role="assistant"]'
    }
  });

  const longLine = 'x'.repeat(5000);
  const prompt = `# Heading\r\n\r\n- first\u2028- second\u2029\`\`\`js\ncode();\n${longLine}\n\`\`\``;
  await controller.send({ text: prompt, timeoutMs: 5_000 });

  const clearAt = events.findLastIndex((event) => event.type === 'key' && event.key === 'Backspace');
  const submitAt = events.findIndex((event) => event.type === 'submit');
  const typing = events.slice(clearAt + 1, submitAt);
  assert.ok(clearAt >= 0);
  assert.ok(submitAt >= 0);
  assert.equal(clearChecks, 2);
  assert.equal(events.filter((event) => event.type === 'key' && event.key === 'Backspace').length, 2);
  assert.equal(events.filter((event) => event.type === 'submit').length, 1);
  assert.equal(typing.some((event) => event.type === 'text' && /[\r\n\u2028\u2029]/u.test(event.text)), false);
  assert.equal(typing.some((event) => event.type === 'key' && event.key === 'Enter' && event.modifiers.length === 0), false);
  assert.ok(typing.filter((event) => event.type === 'text').every((event) => event.text.length <= 2048));
  assert.ok(typing.filter((event) => event.type === 'text').length < 16);

  const reconstructed = typing.map((event) => {
    if (event.type === 'text') return event.text;
    if (event.type === 'key' && event.key === 'Enter' && event.modifiers.includes('shift')) return '\n';
    return '';
  }).join('');
  assert.equal(reconstructed, `# Heading\n\n- first\n- second\n\`\`\`js\ncode();\n${longLine}\n\`\`\``);
});

test('a composer that cannot be emptied fails before typing or submitting', async () => {
  const events = [];
  const page = {
    async navigate() {},
    async evaluate(js) {
      if (js.includes('const hasTurnstile')) return readyState();
      if (js.includes('selectNodeContents')) return { ok: true, promptLen: 7 };
      if (js.includes('const text = el.matches')) return { ok: true, promptLen: 7 };
      if (js.includes('missing_prompt_textarea')) return { ok: true, rect: { x: 10, y: 10, w: 200, h: 40 } };
      if (js.includes('form.requestSubmit')) {
        events.push({ type: 'submit' });
        return true;
      }
      throw new Error(`unexpected_eval:${js.slice(0, 80)}`);
    },
    async getUrl() { return 'https://chatgpt.com/'; },
    async sendKey(key, options = {}) {
      events.push({ type: 'key', key, modifiers: options.modifiers || [] });
    },
    async insertText(text) { events.push({ type: 'text', text }); },
    async moveMouse() {},
    async mouseDown() {},
    async mouseUp() {},
    async setFileInputFiles() {}
  };

  const controller = new ChatGPTController({
    page,
    selectors: {
      promptTextarea: '#prompt-textarea',
      sendButton: 'button[data-testid="send-button"]',
      stopButton: 'button[data-testid="stop-button"]',
      assistantMessage: '[data-message-author-role="assistant"]'
    }
  });

  await assert.rejects(controller.send({ text: 'must not append', timeoutMs: 5_000 }), /prompt_clear_failed/);
  assert.equal(events.some((event) => event.type === 'text'), false);
  assert.equal(events.some((event) => event.type === 'submit'), false);
});

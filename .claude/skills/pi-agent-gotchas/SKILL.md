---
name: pi-agent-gotchas
description: Troubleshooting pi-coding-agent config — DeepInfra provider, openai-completions api type, models.json, auth.json, DEEPINFRA_TOKEN, deepseek provider
model: claude-haiku-4-5-20251001
---

# Pi Agent (pi-coding-agent) Gotchas

## Custom provider `api` field must be `"openai-completions"` not `"openai"`

In `~/.pi/agent/models.json`, custom OpenAI-compatible providers (e.g. DeepInfra, NeuralWatt) must declare `"api": "openai-completions"`, NOT `"api": "openai"`.

The bare `"openai"` type is the built-in OpenAI.com provider backend and only registers when `OPENAI_API_KEY` is present. Without it, any custom provider that sets `"api": "openai"` silently fails to register, and selecting any of its models produces:

```
Error: No API provider registered for api: openai
```

Fix — change every custom OpenAI-compatible provider entry:

```json
"DeepInfra": {
  "baseUrl": "https://api.deepinfra.com/v1/openai",
  "api": "openai-completions",
  "apiKey": "DEEPINFRA_TOKEN",
  ...
}
```

`"openai-completions"` is the generic OpenAI-wire-format backend. `"openai"` is exclusively the upstream openai.com provider.

## Built-in `deepseek` provider (v0.80.2+) vs custom DeepInfra entry

Pi-agent 0.80.2 added a built-in `deepseek` provider using `DEEPSEEK_API_KEY`, with models `deepseek-v4-flash` and `deepseek-v4-pro` (lowercase hyphenated — not the DeepInfra `deepseek-ai/DeepSeek-V4-Pro` style ID). To use DeepSeek through DeepSeek's own API: provider `deepseek`, model `deepseek-v4-pro`. To use it via DeepInfra: use the custom `DeepInfra` entry with model `deepseek-ai/DeepSeek-V4-Pro` and fix the `api` field as above.

## `apiKey` references an env var by name, not by value

`"apiKey": "DEEPINFRA_TOKEN"` in `models.json` is an env var name — pi-agent resolves `process.env["DEEPINFRA_TOKEN"]` at startup. On this machine `DEEPINFRA_TOKEN` is in `~/.env`, sourced by `.zshrc` (interactive shells only, not `.zshenv`). It is NOT available when pi-agent is invoked non-interactively or via `agent pi` (which runs under `env -i`).

To avoid env-dependency entirely, store credentials in `~/.pi/agent/auth.json` (mode 0600):

```json
{
  "DeepInfra": { "type": "api_key", "key": "actual-token-here" }
}
```

Auth file credentials take priority over env vars and survive `env -i` launchers.

## The binary is `pi`, not `pi-agent`

The npm package `@earendil-works/pi-coding-agent` installs its binary as `pi` (from `package.json` `bin.pi`). The DotCortex agent registry lists the command as `pi-agent` (a wrapper stub not yet written). Run it directly as `pi` from your shell.

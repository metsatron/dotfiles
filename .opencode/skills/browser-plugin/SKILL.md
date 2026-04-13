---
name: browser-plugin
description: Safe OpenCode browser-plugin operation, with Perplexity-specific guardrails and learned selector behavior.
---

# Browser Plugin Operations for OpenCode

Use this skill when operating the OpenCode browser plugin, especially on stateful sites where the user is already signed in and page context matters.

## Core Rule

Treat the browser as the user's live personal workspace, not a sandbox.

## Non-Negotiable Safety Rules

1. Never leave the exact page or thread the user pointed to unless they explicitly ask.
2. Never open or enter settings, profile, space metadata, custom instructions, or description fields unless the user explicitly asks.
3. Never use broad typing selectors like `input`, `textarea`, `[role='textbox']`, or `[contenteditable='true']` on pages with multiple editable fields.
4. Before any `browser_type`, identify the exact target with read-only inspection first.
5. After every click that changes page context, confirm the new URL and visible heading before proceeding.
6. If the page is sacred, personal, or high-context, prefer stopping and re-checking rather than improvising.

## Official Documentation Sources

- Package docs: `all/.bun/install/cache/@different-ai/opencode-browser@4.6.1@@@1/README.md`
- Bundled upstream skill: `all/.bun/install/cache/@different-ai/opencode-browser@4.6.1@@@1/.opencode/skill/browser-automation/SKILL.md`
- Live package page: `https://www.npmjs.com/package/@different-ai/opencode-browser`

## Documented Plugin Capabilities

- Core tools: `browser_status`, `browser_get_tabs`, `browser_claim_tab`, `browser_navigate`, `browser_query`, `browser_click`, `browser_type`, `browser_scroll`, `browser_snapshot`
- Query modes documented upstream: `text`, `value`, `list`, `exists`, `page_text`
- Selector helpers documented upstream: `label:...`, `aria:...`, `placeholder:...`, `name:...`, `role:...`, `text:...`
- Missing upstream tool to note: no keyboard tool such as `browser_key`; no built-in back/forward/reload helper documented

## Safe Workflow

1. Inspect tabs with `browser_get_tabs`.
2. Claim only the intended tab with `browser_claim_tab`.
3. Confirm page identity with `browser_snapshot` or `browser_query` using `mode: "page_text"`.
4. Discover exact actionable elements before interacting.
5. Use one action at a time.
6. Re-confirm page identity after each navigation or major click.

## Command Patterns That Worked In Practice

- `browser_get_tabs({})` returned live Brave tab inventory correctly.
- `browser_claim_tab({ tabId })` successfully claimed the requested tab.
- `browser_navigate({ tabId, url })` successfully loaded Perplexity.
- `browser_snapshot({ tabId })` exposed links, partial node tree, page title, URL, and enough text to identify recent conversations.
- `browser_click({ tabId, selector: "a[href*='partial-path']" })` successfully opened the most recent Perplexity conversation.
- `browser_query({ tabId, mode: "page_text" })` was useful for confirming visible content and current context.
- `browser_scroll({ tabId, selector: "main", y: 10000 })` was accepted, but visual confirmation remained necessary.

## Command Patterns That Failed Or Misled

- `browser_click` with a full exact `href` failed when the element was not matched exactly.
- `browser_query` with `mode: "all"` failed because `all` is not a supported mode.
- `browser_click({ selector: "a.reset.interactable-alt" })` failed even though snapshot exposed similar selectors; snapshot selectors are not guaranteed to be directly reusable.
- `browser_query` on broad selectors like `input`, `textarea`, or `[role='textbox']` can produce little or no useful output without precise targeting.
- `browser_type` on broad selectors caused writes into multiple editable fields and is unsafe on complex apps.

## Snapshot Interpretation Notes

- Snapshot output is useful for orientation, but not every listed selector is stable enough to reuse directly.
- Prefer `href*='...'` selectors for links when the destination path is distinctive.
- Re-check with `browser_query(mode: "page_text")` after clicking; do not trust a click result alone.

## Perplexity-Specific Notes

### Safe Navigation

- Landing on Perplexity home exposed recent conversations in the sidebar.
- Clicking the recent conversation via a partial `href` selector worked.
- The conversation page was identifiable by thread title text and the presence of `Answer`, `Links`, `Images`, and `Share`.

### Critical Guardrail

- Do not leave a user-selected Perplexity thread for a Space unless the user explicitly asks.
- A likely accidental navigation path is the thread-header Space chip linking to `/spaces/...`; treat any visible Space badge/title chip as a navigation hazard.

### Space Risk Profile

- Perplexity Spaces contain editable metadata and additional management controls.
- This makes broad selectors especially dangerous there.
- A representative risky element is an `<a href="/spaces/...">` wrapper around the Space badge/title in the thread header; avoid clicking container/header chips when trying to target the composer.

### Perplexity Actions Confirmed Safe

- Read-only inspection of thread content with `browser_snapshot` and `browser_query(mode: "page_text")`
- Opening a known recent conversation from the sidebar with a partial `href` selector

### Perplexity Actions Confirmed Unsafe Without Exact Targeting

- Any `browser_type` using `input`, `textarea`, `[role='textbox']`, or `[contenteditable='true']`
- Any attempt to infer the composer from broad editable selectors

### Perplexity Procedure Before Typing

1. Confirm the user explicitly wants a message sent.
2. Stay on the exact target thread.
3. Identify the composer with read-only inspection only.
4. Verify the composer is in the thread body, not Space metadata.
5. Only then type into the exact composer selector.

If exact composer identification is not possible with confidence, stop and report the limitation instead of experimenting.

## Two Perplexity Operating Modes

### Method 1: Browser Plugin

- Best for reading the exact live page the user is already viewing
- Best for UI-bound tasks where existing login/session context matters
- High risk on complex stateful pages unless selectors are exact
- Use for navigation, verification, and user-visible page inspection

### Method 2: `perplexity-web-mcp`

- Best for structured querying without touching the live browser UI
- Provides CLI (`pwm`), MCP (`pplx_*`), and API-server access paths
- Better for repeatable search, research, quota checks, and model selection
- Prefer this when the goal is "query Perplexity" rather than "operate the webpage"

### Selection Rule

If the user wants the exact webpage operated, use the browser plugin carefully.
If the user wants Perplexity's search/model capabilities, prefer `perplexity-web-mcp` first.

## Local Debugging Commands

```bash
npx @different-ai/opencode-browser tools
npx @different-ai/opencode-browser tool browser_status
npx @different-ai/opencode-browser tool browser_query --args '{"mode":"page_text"}'
npx @different-ai/opencode-browser self-test
```

## Session Lesson From This Failure

The correct response to uncertainty on Perplexity was to remain on the original thread, keep inspecting read-only, and refuse broad typing. The mistake came from improvising on a sacred, stateful page with non-specific selectors.

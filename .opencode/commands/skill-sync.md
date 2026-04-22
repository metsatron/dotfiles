# skill-sync - OpenCode Layer Sync Audit

OpenCode workflow reference for checking whether DotCortex's local `.opencode`
layer is missing commands, skills, memory notes, workflows, or operating
guidance that already exists in `.claude`, `.agents`, `.codex`, or adjacent
repos, then adapting only the useful pieces for OpenCode on this platform.

This is a repo-local workflow doc, not proof of slash-command registration.

## Purpose

Use this when Mètsàtron asks to sync the OpenCode layer with the other agent
overlays, or when `.opencode/` feels stale relative to `.claude/`, `.agents/`,
or `.codex/`.

The goal is not parity for its own sake. The goal is an OpenCode-aware local
layer that reflects:

- OpenCode's real capabilities
- DotCortex doctrine and local workflow
- the actual differences between this client and Claude or Codex

Use the Bruce Lee filter: take what works, leave what does not, and make it
uniquely ours.

## Source Priority

When sources disagree, prefer:

1. `AGENTS.md`
2. `.opencode/AGENTS.md`
3. `README.org` and current repo state
4. `.claude/` and `CLAUDE.md` as read-only reference material
5. `.agents/`, `.codex/`, and adjacent repos as mirrors, adapters, and delta sources

Treat Claude hooks, Codex-only docs, installers, and other client-specific
behavior as source material, not automatic OpenCode features.

## Audit Scope

Check all of these against the current `.opencode` layer:

- `.claude/commands/`
- `.claude/skills/`
- `.claude/contexts/`
- `.claude/settings.local.json`
- `.agents/workflows/`
- `.agents/skills/`
- `.codex/commands/`
- `.codex/skills/`
- `.codex/modules/`
- `.codex/README.md`
- `.opencode/commands/`
- `.opencode/skills/`
- `.opencode/memory/`
- `.opencode/workflows/`
- `.opencode/AGENTS.md`
- `.opencode/README.md`

## Steps

1. Inventory the current `.opencode` commands, skills, memory notes,
   workflows, and root guidance files.
2. Inventory relevant docs under `.claude`, `.agents`, and `.codex`.
3. Identify gaps in five buckets:
   - missing command workflows
   - missing skills
   - missing memory or durable guidance
   - missing workflow docs
   - useful deltas that should change existing OpenCode wording
4. Classify each gap:
   - `port` for near-direct OpenCode adaptation
   - `adapt` for source material that needs OpenCode-specific rewriting
   - `skip` for client-specific behavior that should not be mirrored
5. Implement the `port` and `adapt` items:
   - add command docs to `.opencode/commands/`
   - add skill docs to `.opencode/skills/`
   - add memory docs to `.opencode/memory/` when the content is durable
   - add workflows to `.opencode/workflows/` when they help repeated tasks
   - update `.opencode/AGENTS.md` and `.opencode/README.md` so the new
     material is discoverable
6. Rewrite imported material for OpenCode reality:
    - no fabricated hook support
    - no fabricated command discovery
    - no Claude-only UI or settings presented as active here
    - no Codex-only module semantics presented as OpenCode-native
    - mention manual workflow use unless OpenCode truly exposes discovery
    - never write back into `.claude` or `CLAUDE.md`
7. Verify the result by listing `.opencode/commands/`, `.opencode/skills/`,
   `.opencode/memory/`, and relevant README pointers.
8. Report:
   - what was added
   - what was intentionally skipped
   - what still looks stale or uncertain

## Adaptation Rules

- Do not copy source text blindly.
- Keep the result concise and OpenCode-aware.
- Prefer the current repo state and safe OpenCode-owned targets over any
  client-specific source layout.
- Use `.agents` and `.codex` to find missing concepts, simplifications, and
  useful deltas.
- If a source depends on a feature OpenCode lacks, convert it into a manual
  workflow doc or skip it.
- Do not mirror secrets, auth material, local tokens, or machine-local state.
- Do not fabricate hooks, command registration, or automatic skill discovery.
- Do not modify any `.claude` path or `CLAUDE.md` while syncing `.opencode`.

## Typical Outputs

- new `.opencode/commands/*.md`
- new `.opencode/skills/*/SKILL.md`
- new `.opencode/memory/*.md`
- selective updates to `.opencode/AGENTS.md`
- selective updates to `.opencode/README.md`

## Skip Conditions

Skip or leave as reference-only when the source is:

- pure Claude hook configuration
- Claude plugin installers or settings merge logic
- Codex-only runtime behavior
- something `.opencode` already has in equivalent or better form
- stale duplication with no OpenCode-specific value

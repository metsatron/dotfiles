# Policy A (Tiago, 2026-11-06)

Aura's wake route is the target's NATIVE idle-prompt seam (POST /api/gateway/idle-prompt[/status], Telegram session keys only).
The model-callable `send_message` registration, the final-tool-list safety net and the earlier "B" egress branch are
INTENTIONALLY NOT CARRIED: model_tools.py and toolsets.py local patches of the 0.20.5 install are dropped on purpose.
Upstream cron / CLI / opt-in-MCP send paths and addressed owning-adapter replies are preserved untouched.
Do not reintroduce a send_message carry without a new ruling.

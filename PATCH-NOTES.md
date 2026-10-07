# Telegram wake-lane patch notes

No live service, private registry, secret file, harness checkout, stow target, or
running session was changed.  These artifacts are review inputs; crossing the
live apply/restart gate still requires the Admiral's explicit approval.

## Hermes finding

`gateway/platforms/api_server.py::_handle_session_chat` ordinarily executes a
turn and returns the assistant content to the HTTP caller.  Its sole mirroring
exception is `_answer_through_live_bot_chat`, which is restricted by
`_admit_to_live_bot_chat` to the canonical Desktop Bot Chat lineage held by a
live Desktop owner.  Naming a Telegram transcript or supplying a continuation
header does not turn that ordinary API response into Telegram output.

Hermes does have the correct internal route:
`hermes_cli/plugins.py::PluginContext.inject_message` schedules
`gateway/run_inbound.py::_dispatch_plugin_message_injection`, which restores the
durable session origin, resolves its authorized delivery adapter, and calls
`BasePlatformAdapter.handle_message`.  The managed patch
`all/.bots/patches/hermes-mailcortex-idle-prompt.patch` exposes a narrow,
authenticated conditional endpoint around that platform path.  It accepts only
an existing Telegram DM key, refuses any observed work or pending adapter input,
and returns `accepted` only after the adapter's real session guard accepts the
event.  Therefore the injected turn and its adapter-delivered reply occupy the
Telegram lane the Admiral watches.

## Exact private-registry migration

Apply this field-shape change in the private `mailcortex.seats.v1` registry.
Retain each seat's existing URL and private token/key-file path; replace only the
target fields shown here.  Every uppercase value is a placeholder.

```diff
@@ YOUR_HERMES_SEAT @@
   "hermes_url": "http://YOUR_LOOPBACK_HOST:YOUR_HERMES_PORT",
   "hermes_api_key_file": "YOUR_HERMES_API_KEY_FILE",
-  "hermes_session": "YOUR_HIDDEN_API_SESSION",
-  "hermes_session_key": "YOUR_HIDDEN_API_SESSION_KEY",
+  "hermes_target": {
+    "mode": "gateway_platform_session",
+    "session_key": "agent:YOUR_PROFILE:telegram:dm:YOUR_CHAT_ID"
+  },

@@ YOUR_NANOBOT_SEAT @@
   "nanobot_url": "http://YOUR_LOOPBACK_HOST:YOUR_NANOBOT_PORT",
   "nanobot_api_token_file": "YOUR_NANOBOT_API_TOKEN_FILE",
-  "nanobot_session": "YOUR_NANOBOT_API_SESSION",
+  "nanobot_target": {
+    "mode": "telegram_gateway",
+    "channel": "telegram",
+    "chat_id": "YOUR_CHAT_ID",
+    "session_key": "telegram:YOUR_CHAT_ID"
+  },
```

The Nano gateway process must receive this private environment setting, pointing
to the same mode-0600 bearer-token file read by the watcher:

```text
NANOBOT_MAILCORTEX_TOKEN_FILE=YOUR_NANOBOT_API_TOKEN_FILE
```

Do not put the token, chat identity, session identity, listener address, or port
in DotCortex.  The Hermes seam continues to use the already-configured Hermes
API authentication.  The Nano seam creates no listener; it adds authenticated
routes to Nano's existing health listener.

## Review and activation order

1. Review and apply the Hermes patch to the pinned private Hermes checkout, then
   run the disposable seam test with `HERMES_AGENT_SOURCE=YOUR_HERMES_CHECKOUT`.
2. Review the Nano ordered patch series through `nanobot-apply`'s pristine staged
   preflight.  The complete series must patch and compile before live mutation.
3. Provision the private Nano token-file environment and make the registry
   field-shape changes above.
4. With explicit approval, restart one harness at a time and verify its status
   endpoint before allowing the watcher to admit real mail.

Busy or unavailable status leaves mail queued.  An exact negative admission ACK
also leaves it queued.  Once an admission request may have crossed the harness
boundary, a missing or malformed acknowledgement becomes `delivery_unknown`;
the persisted receipt prevents automatic resend.

## Verification ledger

- RED before implementation: watcher suite, 38 tests, 6 errors (new target
  schema and conditional endpoints absent).
- GREEN after implementation: watcher 38/38; Hermes disposable seam 4/4; Nano
  disposable seam 5/5; MailCortex command fixtures 9/9; watcher lifecycle 7/7;
  Syncthing prerequisite fixtures 7/7; Nano cache-policy 2/2, search-isolation
  5/5, and voice-reply 6/6.  Total: 83/83 relevant tests.
- Syntax checks: the watcher and Python fixtures compile; `nanobot-apply` and
  `nanobot-health` pass `bash -n`; both managed runtime patches apply with
  `--fuzz=0` to disposable copies; Nano's complete ordered patch series applies
  with zero fuzz to a pristine pinned package tree; all patched modules compile.

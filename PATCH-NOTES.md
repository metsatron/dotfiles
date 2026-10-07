# Kikin web UI ownership and private provisioning

This patch adds `hermes-dashboard` to the existing `telegram-agent-host` boot
and watchdog lane, and teaches the DeepSeek Harness launch to pass dsh one
operator-provisioned `--trusted-host` authority. It does not alter live config,
stow files, or restart anything.

## Coordinator apply

1. Integrate the committed patch into the canonical checkout, then regenerate
   and deploy from canonical source:

   ```sh
   tangle-one agents-bots.org
   tangle-one agents-watchdog.org
   loom stow:t1700
   ```

2. Install the dashboard placeholder file without overwriting any existing
   private file:

   ```sh
   telegram-agent-host sync hermes-dashboard
   ```

3. If the old hand-started dashboard is still running, inspect its exact PID
   and command line and stop that one process first. The new owner deliberately
   refuses to start while any unowned Hermes dashboard process exists.

4. After the Admiral provisions both private files below, start the dashboard
   through its only owner and restart the DeepSeek Harness through its existing
   owner:

   ```sh
   telegram-agent-host start hermes-dashboard
   telegram-agent-host stop deepseek-harness
   telegram-agent-host start deepseek-harness
   ```

5. Verify ownership and watchdog-visible status:

   ```sh
   telegram-agent-host status hermes-dashboard
   telegram-agent-host status deepseek-harness
   telegram-agent-host status
   ```

The host inventory now enables `hermes-dashboard`, so the established boot
owner and watchdog will start it automatically. A successful operator stop
creates its own intentional-stop marker, and the watchdog leaves it stopped.

## Admiral: Hermes dashboard private env

The private file is `~/.hermes/dashboard.env`, mode `0600`. Start from the
tracked `~/.bots/templates/hermes-dashboard.env` template and replace every
placeholder privately:

```text
HERMES_DASHBOARD_PUBLIC_URL=https://YOUR_TAILNET_HOST:YOUR_HERMES_DASHBOARD_PORT
HERMES_DASHBOARD_BASIC_AUTH_USERNAME=YOUR_HERMES_DASHBOARD_BASIC_AUTH_USERNAME
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH=YOUR_HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH
HERMES_DASHBOARD_BASIC_AUTH_SECRET=YOUR_HERMES_DASHBOARD_BASIC_AUTH_SECRET
```

`HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH` must be the scrypt hash returned by
Hermes's bundled `plugins.dashboard_auth.basic.hash_password`; never put the
plaintext password in the file, shell history, process arguments, or this repo.
Generate it from an interactive `getpass` prompt inside Hermes's own Python
environment and move only the resulting hash from KeePass into the file. The
secret is optional but recommended for stable signed sessions.

If the file is missing, not mode `0600`, contains a placeholder, lacks the URL,
username, or hash, or has an invalid URL/hash shape, the owner masks any ambient
or Hermes-configured public URL with `http://localhost`. The dashboard still
starts on Hermes's loopback default, without public-host trust or dashboard
authentication being armed.

## Admiral: dsh trusted host and one-time auth URL

In the private agent file
`/home/agent-deepseek/.config/deepseek-harness-telegram/env` (mode `0600`), add:

```text
DSH_WEB_TRUSTED_HOST=YOUR_TAILNET_HOST:YOUR_DSH_WEB_PORT
```

The value is one bare authority: no scheme, path, query, credentials, or
whitespace. The manager omits `--trusted-host` while the value is blank or still
a `YOUR_*` placeholder, and rejects malformed provisioned values.

After the managed dsh process has started, retrieve its current one-time browser
URL directly as the owning user:

```sh
sudo -u agent-deepseek -H "$(readlink -f "$HOME/.local/bin/deepseek-harness-web-url")" show
```

Open the printed URL directly. Do not redirect it, paste it into chat, or copy it
into a ticket or log. The launch filter stores only the loopback URL's root path
and token in agent-owned mode-`0600` state, substitutes the private HTTPS
authority only on this explicit command, and redacts the token from service
logs. Restarting or stopping the harness removes the stale captured path.

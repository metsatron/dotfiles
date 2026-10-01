-- MailCortex private XMPP server. Public layer, tangled from DotCortex
-- services-mailcortex-xmpp.org. Site values live in local.cfg.lua.
local home = Lua.os.getenv("HOME")
local site = home .. "/.config/mailcortex/xmpp-private"
local state = home .. "/.local/share/mailcortex/xmpp"

pidfile = state .. "/prosody.pid"
data_path = state .. "/data"
certificates = site .. "/certs"
log = {
  info = state .. "/prosody.log";
  error = state .. "/prosody.err";
}

-- Closed, unfederated, encrypted.
allow_registration = false
c2s_require_encryption = true
authentication = "internal_hashed"
storage = "internal"
modules_disabled = { "s2s" }
s2s_ports = {}

-- Loopback by default; local.cfg.lua adds the tailnet interface for clients.
interfaces = { "127.0.0.1" }
c2s_ports = { 5222 }
component_interfaces = { "127.0.0.1" }
component_ports = { 5347 }

modules_enabled = {
  "roster"; "saslauth"; "tls"; "disco"; "carbons"; "pep"; "private";
  "blocklist"; "vcard4"; "vcard_legacy"; "version"; "uptime"; "time";
  "ping"; "smacks"; "csi_simple"; "mam"; "bookmarks";
  -- Local unix socket for prosodyctl adduser/passwd/shell; no network listener.
  "admin_shell"; "admin_socket";
}
archive_expires_after = "never"

Include(site .. "/local.cfg.lua")

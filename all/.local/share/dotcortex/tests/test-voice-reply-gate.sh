#!/usr/bin/env bash
# Refusal gate test (NO_REPLY / mail envelope / normal paragraph)

# The refusal gate above (2026-11-19) must suppress the NO_REPLY sentinel and mail-turn envelopes while still speaking a normal reply. This test drives the real =claude-hook-voice-reply= with the normalizer and synthesizer stubbed out (a pass-through normalizer, a fake =pvox= that writes a WAV, and a fake =ssh= that drains it and succeeds), feeds the three canonical fixtures, and asserts **2 refusals + 1 spoken** by reading the per-fixture =pvox-reply.log=. Synthesis is fully stubbed, so the test never touches pvox, the fleet, or the phone.


# [[file:../../../../../agents-hooks.org::*Refusal gate test (NO_REPLY / mail envelope / normal paragraph)][Refusal gate test (NO_REPLY / mail envelope / normal paragraph):1]]
# ~/DotCortex/all/.local/share/dotcortex/tests/test-voice-reply-gate.sh
# Failing-first test for the claude-hook-voice-reply refusal gate.
# Feeds three fixtures (NO_REPLY, a mail envelope, a normal paragraph) with
# synthesis stubbed out and asserts 2 refusals + 1 spoken, by reading the
# per-fixture pvox-reply.log. No real pvox / ssh / phone is touched.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="${VOICE_REPLY_HOOK:-$HERE/../../../bin/claude-hook-voice-reply}"
if [ ! -x "$HOOK" ]; then
    echo "FAIL: hook not found/executable at $HOOK" >&2
    exit 1
fi

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/voice-gate-test-XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT

# Stub normalizer: emit stdin verbatim (ignore --hook-json), so TEXT == fixture.
NORM="$SANDBOX/voice-text-normalize"
cat > "$NORM" <<'EOF'
#!/usr/bin/env bash
cat
EOF
chmod +x "$NORM"

# Fake HOME carrying a fake pvox: voicespec prints nothing (skips the on-device
# lane), render writes a stub WAV to its output path and succeeds.
FAKEHOME="$SANDBOX/home"
mkdir -p "$FAKEHOME/.local/share/pvox-clone/client/bin"
PVOX="$FAKEHOME/.local/share/pvox-clone/client/bin/pvox"
cat > "$PVOX" <<'EOF'
#!/usr/bin/env bash
case "${1:-}" in
    voicespec) exit 0 ;;                 # empty spec -> ship lane, not on-device
    render)    out="${@: -1}"; printf 'RIFFstub' > "$out"; exit 0 ;;
    *)         exit 0 ;;
esac
EOF
chmod +x "$PVOX"

# Fake ssh: drain the shipped WAV from stdin and succeed (delivery OK).
BIN="$SANDBOX/bin"
mkdir -p "$BIN"
cat > "$BIN/ssh" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null 2>&1 || true
exit 0
EOF
chmod +x "$BIN/ssh"

run_fixture() {
    # run_fixture <name> <fixture-file>
    local name="$1" fixture="$2"
    local cache="$SANDBOX/cache-$name"
    mkdir -p "$cache"
    env -i \
        PATH="$BIN:/usr/bin:/bin" \
        HOME="$FAKEHOME" \
        XDG_CACHE_HOME="$cache" \
        VOICE_TEXT_NORMALIZER="$NORM" \
        CLAUDE_WARM_HERDR_AGENT="hermes" \
        "$HOOK" < "$fixture" >/dev/null 2>&1 || true
    # The spoken lane synthesizes in a detached worker; poll its log briefly.
    local log="$cache/pvox-reply.log" i
    for i in $(seq 1 50); do
        if [ -s "$log" ]; then break; fi
        sleep 0.1
    done
    cat "$log" 2>/dev/null || true
}

# Fixtures ------------------------------------------------------------------
F_NOREPLY="$SANDBOX/fx-noreply"
printf 'NO_REPLY' > "$F_NOREPLY"

F_ENVELOPE="$SANDBOX/fx-envelope"
cat > "$F_ENVELOPE" <<'EOF'
MailCortex delivery for honey-badger@honey.helm
From: operator
Subject: nightly rollup
The backup stratum rotated cleanly and the health check is green across all seats this evening.
EOF

F_NORMAL="$SANDBOX/fx-normal"
printf '%s' "Yes, I restarted the gateway and confirmed the web UI came back up on its port. Everything looks healthy now." > "$F_NORMAL"

# Run ----------------------------------------------------------------------
OUT_NOREPLY="$(run_fixture noreply "$F_NOREPLY")"
OUT_ENVELOPE="$(run_fixture envelope "$F_ENVELOPE")"
OUT_NORMAL="$(run_fixture normal "$F_NORMAL")"

echo "---- NO_REPLY ----";        echo "${OUT_NOREPLY:-<empty>}"
echo "---- mail envelope ----";   echo "${OUT_ENVELOPE:-<empty>}"
echo "---- normal paragraph ----"; echo "${OUT_NORMAL:-<empty>}"
echo "--------------------------"

fail=0
assert_refused() {
    local name="$1" out="$2" rule="$3"
    if printf '%s' "$out" | grep -q "refused=$rule"; then
        echo "PASS: $name refused ($rule)"
    else
        echo "FAIL: $name should have been refused with $rule; got: ${out:-<empty>}"
        fail=1
    fi
}
assert_spoken() {
    local name="$1" out="$2"
    if printf '%s' "$out" | grep -q 'refused='; then
        echo "FAIL: $name was refused but should have been spoken; got: $out"
        fail=1
    elif printf '%s' "$out" | grep -Eq 'delivered=|rendered=on-device|RENDER-FAIL'; then
        echo "PASS: $name spoken (reached synthesis)"
    else
        echo "FAIL: $name produced no synthesis evidence; got: ${out:-<empty>}"
        fail=1
    fi
}

assert_refused "NO_REPLY"      "$OUT_NOREPLY"  "no-reply-or-empty"
assert_refused "mail envelope" "$OUT_ENVELOPE" "mail-envelope"
assert_spoken  "normal paragraph" "$OUT_NORMAL"

refusals=0
printf '%s' "$OUT_NOREPLY"  | grep -q 'refused=' && refusals=$((refusals+1)) || true
printf '%s' "$OUT_ENVELOPE" | grep -q 'refused=' && refusals=$((refusals+1)) || true
printf '%s' "$OUT_NORMAL"   | grep -q 'refused=' && refusals=$((refusals+1)) || true
echo "SUMMARY: refusals=$refusals (expected 2)"

if [ "$refusals" -ne 2 ]; then
    echo "FAIL: expected exactly 2 refusals, got $refusals"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "RESULT: FAIL"
    exit 1
fi
echo "RESULT: PASS (2 refusals + 1 spoken)"
# Refusal gate test (NO_REPLY / mail envelope / normal paragraph):1 ends here

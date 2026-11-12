#!/usr/bin/env bash
# Mutation proof: each sabotaged copy of the relay MUST fail the named suite. Disposable space only; the candidate is not modified.
set -uo pipefail
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail=0
mutate() { # name suite sed-expression. A KILL needs a real unittest failure (named below); a crash, stall or skip is an infrastructure problem and fails the run.
  local name="$1" suite="$2" expr="$3" d="$TMP/$1-$2" out rc names
  if [ "$suite" = test_egress_sandbox.py ] && [ "${HONEY_LIVE:-1}" != 1 ]; then echo "skipped (Honey-only, HONEY_LIVE=0): $name [$suite]"; return; fi
  mkdir -p "$d"; cp "$HERE"/fca_egress_*.py "$d"/
  sed -i "$expr" "$d/fca_egress_relay.py"
  if cmp -s "$HERE/fca_egress_relay.py" "$d/fca_egress_relay.py"; then echo "MUTATION NOT APPLIED: $name"; fail=1; return; fi
  out="$(timeout 300 python3 "$HERE/$suite" "$d" 2>&1)"; rc=$?
  if [ "$rc" = 0 ]; then echo "SURVIVED (tests too weak, or the suite skipped): $name [$suite]"; fail=1
  elif [ "$rc" = 124 ]; then echo "TIMEOUT (infrastructure, NOT a kill): $name [$suite]"; fail=1
  elif printf '%s\n' "$out" | grep -qE '^FAILED \('; then
    names="$(printf '%s\n' "$out" | grep -E '^(FAIL|ERROR):' | sed 's/^[A-Z]*: //; s/ (.*//' | head -3 | tr '\n' ' ')"
    echo "killed: $name [$suite] by: $names"
  else echo "INFRASTRUCTURE ERROR (not a kill): $name [$suite]"; printf '%s\n' "$out" | tail -8 | sed 's/^/    | /'; fail=1; fi
}
mutate sni-check-removed          test_egress_relay.py   "s/if parse_client_hello_sni(record) != UPSTREAM_HOST:/if False:/"
mutate address-policy-open        test_egress_relay.py   "s/^    if not isinstance(text, str) or '%' in text:/    return True\n    if not isinstance(text, str) or '%' in text:/"
mutate one-bad-answer-tolerated   test_egress_relay.py   "s/                raise Reject('dnsaddr')  # one bad answer.*/                continue/"
mutate ech-allowed                test_egress_relay.py   "s/if etype in seen or etype in BANNED_EXTENSIONS:/if etype in seen:/"
# (dropping the 'len(record) != 5 + length' clause is an equivalent mutant: the exact-consumption checks reject the same inputs)
mutate fractured-hello-allowed    test_egress_relay.py   "s/ or len(record) != 5 + length:/:/; s/    if not r.done():/    if False:/"
mutate peername-unchecked         test_egress_relay.py   "s/if ipaddress.ip_address(peer) != ipaddress.ip_address(address):/if False:/"
mutate hello-deadline-unbounded   test_egress_relay.py   "s/deadline = time.monotonic() + self.hello_deadline/deadline = time.monotonic() + 5000/"
mutate concurrency-unbounded      test_egress_relay.py   "s/if not self.slots.acquire(blocking=False):/if False:/"
mutate peer-uid-unchecked         test_egress_relay.py   "s/if self.peer_uid is not None and struct.unpack('3i', cred)\[1\] != self.peer_uid:/if False:/"
mutate sni-duplicate-allowed      test_egress_relay.py   "s/if etype in seen or etype in BANNED_EXTENSIONS:/if etype in BANNED_EXTENSIONS:/"
mutate argv-accepted              test_egress_relay.py   "s/if len(argv) != 1:/if False:/"
mutate upstream-fin-not-forwarded   test_egress_relay.py   "s/                        peer\[s\].shutdown(socket.SHUT_WR)/                        pass/"
mutate resolver-lock-nonblocking    test_egress_relay.py   "s/self.resolving.acquire(timeout=self.connect_deadline)/self.resolving.acquire(blocking=False)/"
mutate resolver-lock-removed        test_egress_relay.py   "s/self.resolving = threading.Lock()/self.resolving = threading.BoundedSemaphore(1000)/"
mutate last-byte-dropped            test_egress_relay.py   "s/                    peer\[s\].sendall(chunk)/                    peer[s].sendall(chunk[:-1])/"
mutate supplementary-groups-ok    test_egress_sandbox.py "s/if set(os.getgroups()) - {os.getegid()}:/if False:/"
mutate cortex-not-forbidden       test_egress_sandbox.py "s/FORBIDDEN_IDS = frozenset({0, 1000, 2000, 2012})/FORBIDDEN_IDS = frozenset({0, 1000, 2012})/; s/if set(os.getgroups()) - {os.getegid()}:/if False:/"
mutate peer-uid-unchecked         test_egress_sandbox.py "s/if self.peer_uid is not None and struct.unpack('3i', cred)\[1\] != self.peer_uid:/if False:/"
exit $fail

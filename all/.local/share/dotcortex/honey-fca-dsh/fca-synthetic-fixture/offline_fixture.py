#!/usr/bin/env python3
"""Offline-only fixture probe; the fixture and this script are one source closure."""
from pathlib import Path
import json, os
fixture = json.loads(Path('/workspace/fca-synthetic/fixtures/offline.json').read_text())
result = {'fixture_read': fixture.get('fixture_id') == 'fca-synthetic-001', 'worker_uid': os.getuid(), 'network_policy': 'none'}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result['fixture_read'] else 1)

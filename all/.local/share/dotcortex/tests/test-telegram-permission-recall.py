#!/usr/bin/env python3
"""Recall deletes only windowed permission prompts, against a loopback fake Telegram."""
import datetime
import http.server
import importlib.util
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

LIB = Path(__file__).resolve().parents[3] / 'lib/dotcortex/telegram_permission_recall.py'
spec = importlib.util.spec_from_file_location('recall', LIB)
recall = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recall)

CHAT = '111'
PERM = '\U0001f510 Permission: Bash'


class FakeTelegram:
    """Messages: id -> dict(kind=user|bot, text, buttons, date)."""

    def __init__(self, messages):
        self.messages = messages
        self.deleted = []
        self.stripped = []
        self.edited = []
        fake = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))) or b'{}')
                method = self.path.rsplit('/', 1)[-1]
                reply = fake.handle(method, body)
                data = json.dumps(reply).encode()
                self.send_response(200 if reply.get('ok') else 400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.server.server_address[1]}'

    def handle(self, method, body):
        self.calls = getattr(self, 'calls', []) + [(method, body.get('message_id'))]
        if body.get('message_id') in getattr(self, 'limited', ()):
            return {'ok': False, 'description': 'Too Many Requests: retry after 30', 'parameters': {'retry_after': 30}}
        message = self.messages.get(body.get('message_id'))
        if str(body.get('chat_id')) != CHAT:
            return {'ok': False, 'description': 'Bad Request: chat not found'}
        if message is None:
            return {'ok': False, 'description': 'Bad Request: message to edit not found'}
        if method == 'editMessageReplyMarkup':
            if message['kind'] == 'user':
                return {'ok': False, 'description': "Bad Request: message can't be edited"}
            if not message['buttons']:
                return {'ok': False, 'description': 'Bad Request: message is not modified'}
            message['buttons'] = False
            self.stripped.append(body['message_id'])
            return {'ok': True, 'result': {'message_id': body['message_id'], 'text': message['text'], 'date': message['date']}}
        if method == 'editMessageText':
            if message['kind'] == 'user':
                return {'ok': False, 'description': "Bad Request: message can't be edited"}
            message['buttons'] = False
            message['text'] = body['text']
            self.edited.append((body['message_id'], body['text']))
            return {'ok': True, 'result': True}
        if method == 'deleteMessage':
            self.deleted.append(body['message_id'])
            del self.messages[body['message_id']]
            return {'ok': True, 'result': True}
        return {'ok': False, 'description': 'unknown method'}


class RecallTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix='recall-test-'))
        self.state = self.dir / 'state'
        self.state.mkdir()
        (self.state / '.env').write_text('TELEGRAM_BOT_TOKEN=123:abc\n')
        (self.state / 'access.json').write_text(json.dumps({'allowFrom': [CHAT]}))
        self.now = int(time.time())
        recall.LOG = self.dir / 'recall.jsonl'  # never write the live log
        self.sweep_args = {}

    def transcript(self, *, anchor=100, tools=('Bash',), extra=()):
        # The shapes Claude Code writes: a channel-origin user row for the
        # inbound message, then the reply tool's call and its result.
        rows = [{'type': 'user', 'isMeta': True, 'origin': {'kind': 'channel', 'server': 'plugin:telegram:telegram'},
                 'message': {'role': 'user', 'content': f'<channel source="plugin:telegram:telegram" chat_id="{CHAT}" message_id="{anchor - 1}" user="op">\nhi\n</channel>'}},
                {'type': 'assistant', 'message': {'id': 'reply-turn', 'role': 'assistant', 'content': [
                    {'type': 'tool_use', 'id': 'old', 'name': 'mcp__plugin_telegram_telegram__reply', 'input': {}}]}},
                {'type': 'user', 'message': {'role': 'user', 'content': [
                    {'type': 'tool_result', 'tool_use_id': 'old', 'content': [{'type': 'text', 'text': f'sent (id: {anchor})'}]}]}},
                *extra]
        for index, name in enumerate(tools):
            rows.append({'message': {'content': [{'type': 'tool_use', 'id': f'open{index}', 'name': name, 'input': {}}]}})
        path = self.dir / 'transcript.jsonl'
        path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n')
        return str(path)

    def run_sweep(self, fake, tool='Bash', **kwargs):
        event = {'session_id': 's', 'tool_name': tool, 'transcript_path': self.transcript(**kwargs)}
        return recall.sweep(event, self.now, state_dir=self.state, base=fake.base, sweep_seconds=2.2, **self.sweep_args)  # self.now is truncated to the second

    def test_deletes_only_the_windowed_permission_prompt(self):
        fake = FakeTelegram({
            101: {'kind': 'user', 'text': 'Admiral words', 'buttons': False, 'date': self.now},
            102: {'kind': 'bot', 'text': 'my plain reply', 'buttons': False, 'date': self.now},
            103: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now},
        })
        self.assertEqual(self.run_sweep(fake), [103])
        self.assertEqual(sorted(fake.messages), [101, 102])
        self.assertEqual(fake.stripped, [103])

    def test_never_touches_messages_at_or_below_the_anchor(self):
        fake = FakeTelegram({100: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now}})
        self.assertEqual(self.run_sweep(fake), [])
        self.assertEqual(fake.stripped, [])

    def test_older_dead_permission_card_is_deleted_and_the_sweep_reaches_its_own_card(self):
        # A sweep that missed leaves a card behind. The next sweep used to stop at it,
        # strip its buttons and leave both cards in the chat.
        fake = FakeTelegram({
            101: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now - 600},
            102: {'kind': 'bot', 'text': PERM.replace('Bash', 'Write'), 'buttons': True, 'date': self.now - 300},
            103: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now},
        })
        self.assertEqual(self.run_sweep(fake), [103])
        self.assertEqual(sorted(fake.messages), [])
        self.assertEqual(fake.deleted, [101, 102, 103])
        rows = [json.loads(line) for line in recall.LOG.read_text().splitlines()]
        self.assertEqual([row['message_id'] for row in rows if row.get('action') == 'deleted_stale'], [101, 102])

    def test_older_permission_card_is_kept_while_a_sibling_request_waits(self):
        # With another request pending in the same batch the older card may be its live ask.
        fake = FakeTelegram({101: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now - 600}})
        self.assertEqual(self.run_sweep(fake, tools=('Bash', 'Write')), [])
        self.assertIn(101, fake.messages)
        self.assertEqual(fake.deleted, [])

    def test_older_card_is_kept_when_settling_an_outcome(self):
        self.sweep_args = {'outcome': 'denied'}
        fake = FakeTelegram({101: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now - 600}})
        self.assertEqual(self.run_sweep(fake), [])
        self.assertIn(101, fake.messages)

    def test_buttoned_non_permission_message_is_kept(self):
        fake = FakeTelegram({101: {'kind': 'bot', 'text': 'something else', 'buttons': True, 'date': self.now}})
        self.assertEqual(self.run_sweep(fake), [])
        self.assertIn(101, fake.messages)

    def test_a_long_dead_unresolved_call_does_not_block_the_sweep(self):
        # Admiral 7409: an interrupted call from an earlier turn never gets a
        # tool_result; only the newest message's batch can hold a live request.
        path = self.transcript()
        rows = [json.loads(line) for line in Path(path).read_text().splitlines()]
        rows.insert(0, {'message': {'id': 'old-turn', 'content': [{'type': 'tool_use', 'id': 'dead', 'name': 'Bash', 'input': {}}]}})
        Path(path).write_text('\n'.join(json.dumps(row) for row in rows) + '\n')
        fake = FakeTelegram({101: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now}})
        event = {'session_id': 's', 'tool_name': 'Bash', 'transcript_path': path}
        self.assertEqual(recall.sweep(event, self.now, state_dir=self.state, base=fake.base, sweep_seconds=2.2), [101])

    def test_two_same_tool_calls_pending_at_once_are_never_touched(self):
        # Two Bash calls unresolved in one batch: either card could be the
        # other request's live floor ask, so the sweep refuses to guess.
        fake = FakeTelegram({101: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now}})
        self.assertEqual(self.run_sweep(fake, tools=('Bash', 'Bash')), [])
        self.assertEqual(fake.stripped, [])

    def test_parallel_prompts_of_different_tools_are_each_cleaned_by_their_own_sweep(self):
        # Telegram 7862/7865: Bash and WebFetch asked at once, both allowed;
        # the old blanket guard skipped both sweeps and a card stayed live.
        fake = FakeTelegram({
            101: {'kind': 'bot', 'text': '\U0001f510 Permission: Bash', 'buttons': True, 'date': self.now},
            102: {'kind': 'bot', 'text': '\U0001f510 Permission: WebFetch', 'buttons': True, 'date': self.now},
        })
        self.assertEqual(self.run_sweep(fake, tool='Bash', tools=('Bash', 'WebFetch')), [101])
        self.assertEqual(self.run_sweep(fake, tool='WebFetch', tools=('Bash', 'WebFetch')), [102])
        self.assertEqual(sorted(fake.messages), [])

    def test_sibling_pending_prompt_survives_an_allowed_sweep(self):
        # The allowed Bash request must not strip the still-pending WebFetch
        # card while its sibling is waiting for the Admiral.
        fake = FakeTelegram({
            101: {'kind': 'bot', 'text': '\U0001f510 Permission: Bash', 'buttons': True, 'date': self.now},
            102: {'kind': 'bot', 'text': '\U0001f510 Permission: WebFetch', 'buttons': True, 'date': self.now},
        })
        self.assertEqual(self.run_sweep(fake, tool='Bash', tools=('Bash', 'WebFetch')), [101])
        self.assertIn(102, fake.messages)
        self.assertEqual(fake.stripped, [101])

    def test_prompt_that_arrives_late_is_still_caught(self):
        fake = FakeTelegram({})
        timer = threading.Timer(0.4, lambda: fake.messages.__setitem__(101, {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now}))
        timer.start()
        self.assertEqual(self.run_sweep(fake), [101])

    def test_two_same_tool_prompts_in_one_window_are_never_touched(self):
        # The old sweep deleted the first of two same-tool prompts; two prompts
        # this close cannot be told apart, so now neither is touched.
        fake = FakeTelegram({
            101: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now},
            102: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now},
        })
        self.assertEqual(self.run_sweep(fake, tools=('Bash', 'Bash')), [])
        self.assertIn(101, fake.messages)
        self.assertIn(102, fake.messages)

    def test_next_request_prompt_after_the_decision_is_never_touched(self):
        # Telegram 7224: the next request's live floor prompt arrived seconds
        # after this allow and was deleted. Now the sweep has ended by then.
        self.sweep_args = {'settle_seconds': 0.3}
        fake = FakeTelegram({})
        timer = threading.Timer(0.7, lambda: fake.messages.__setitem__(101, {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now}))
        timer.start()
        self.assertEqual(self.run_sweep(fake), [])
        timer.join()
        self.assertEqual(fake.stripped, [])
        self.assertIn(101, fake.messages)

    def test_prompt_dated_after_the_decision_stops_the_sweep(self):
        fake = FakeTelegram({
            101: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now + 30},
            102: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now + 30},
        })
        self.assertEqual(self.run_sweep(fake), [])
        self.assertEqual(sorted(fake.stripped), [101])
        self.assertIn(101, fake.messages)
        self.assertIn(102, fake.messages)

    def test_earlier_sweeps_move_the_anchor_past_a_long_run_of_prompts(self):
        # Admiral 7316: with no new chat text the transcript anchor stayed at
        # 100 while prompts climbed past 112, out of probe range.
        recall.LOG.write_text(json.dumps({'session': 's', 'action': 'swept', 'anchor': 100, 'deleted': [], 'seen': 140}) + '\n')
        fake = FakeTelegram({141: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now}})
        self.assertEqual(self.run_sweep(fake), [141])
        rows = [json.loads(line) for line in recall.LOG.read_text().splitlines()]
        self.assertEqual(rows[-1]['seen'], 141)

    def test_another_sessions_log_never_moves_the_anchor(self):
        recall.LOG.write_text(json.dumps({'session': 'other', 'action': 'swept', 'anchor': 100, 'deleted': [], 'seen': 140}) + '\n')
        fake = FakeTelegram({141: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now}})
        self.assertEqual(self.run_sweep(fake), [])

    def test_no_state_or_ambiguous_chat_does_nothing(self):
        fake = FakeTelegram({101: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now}})
        (self.state / 'access.json').write_text(json.dumps({'allowFrom': [CHAT, '222']}))
        self.assertEqual(self.run_sweep(fake), [])
        self.assertEqual(fake.stripped, [])

    def test_settle_uses_first_seen_when_no_hold_window_and_edits_the_desk_outcome(self):
        # A Desk approval settles a hook-queued item long after the request; the
        # card was posted when the request first hit the gate, so first_seen
        # bounds the window and the outcome names the Desk.
        first = datetime.datetime.now(datetime.timezone.utc)
        item = {'session': 's', 'first_seen': first.isoformat(),
                'request': {'tool_name': 'Bash', 'session_id': 's', 'transcript_path': self.transcript(),
                            'tool_input': {'command': 'printf hello'}}}
        fake = FakeTelegram({101: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': int(first.timestamp())}})
        os.environ['TELEGRAM_STATE_DIR'] = str(self.state)
        os.environ['TELEGRAM_API_BASE'] = fake.base
        try:
            self.assertTrue(recall.settle(item, 'desk_approved'))
        finally:
            del os.environ['TELEGRAM_STATE_DIR']
            del os.environ['TELEGRAM_API_BASE']
        self.assertEqual(fake.edited, [(101, '✅ Approved from the Desk')])

    def test_settle_never_touches_another_tools_card(self):
        first = datetime.datetime.now(datetime.timezone.utc)
        item = {'session': 's', 'first_seen': first.isoformat(),
                'request': {'tool_name': 'Bash', 'session_id': 's', 'transcript_path': self.transcript(tools=('Bash', 'WebFetch')),
                            'tool_input': {'command': 'printf hello'}}}
        fake = FakeTelegram({
            101: {'kind': 'bot', 'text': '\U0001f510 Permission: WebFetch', 'buttons': True, 'date': int(first.timestamp())},
        })
        os.environ['TELEGRAM_STATE_DIR'] = str(self.state)
        os.environ['TELEGRAM_API_BASE'] = fake.base
        try:
            self.assertFalse(recall.settle(item, 'desk_approved'))
        finally:
            del os.environ['TELEGRAM_STATE_DIR']
            del os.environ['TELEGRAM_API_BASE']
        self.assertEqual(fake.edited, [])
        self.assertIn(101, fake.messages)


class ClearOpenTests(unittest.TestCase):
    """Mètsàtron's rule (Telegram 12310, 12313): every open card up to this request goes; a later live ask stays."""

    transcript = RecallTests.transcript

    def setUp(self):
        RecallTests.setUp(self)
        recall.CLEAR_STATE = self.dir / 'clear.json'  # never write the live mark

    def chat(self):
        return FakeTelegram({
            90: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now - 3600},
            91: {'kind': 'user', 'text': 'Admiral words', 'buttons': False, 'date': self.now - 3000},
            92: {'kind': 'bot', 'text': '\U0001f510 Permission: Edit', 'buttons': True, 'date': self.now - 2000},
            93: {'kind': 'bot', 'text': 'my plain reply', 'buttons': False, 'date': self.now - 1000},
            99: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now - 10},
            100: {'kind': 'bot', 'text': 'sent reply', 'buttons': False, 'date': self.now - 5},
            103: {'kind': 'bot', 'text': PERM, 'buttons': True, 'date': self.now},
            104: {'kind': 'bot', 'text': '\U0001f510 Permission: Write', 'buttons': True, 'date': self.now + 1},
        })

    def test_every_open_card_up_to_the_ceiling_goes_and_the_newer_one_stays(self):
        fake = self.chat()
        self.assertEqual(recall.clear_open('s', 103, state_dir=self.state, base=fake.base, start=85), [90, 92, 99, 103])
        self.assertEqual(sorted(fake.messages), [91, 93, 100, 104])
        self.assertTrue(fake.messages[104]['buttons'])  # the live ask keeps its buttons
        self.assertNotIn(104, [mid for _, mid in fake.calls])

    def test_the_mark_moves_on_so_the_next_clear_starts_after_the_ceiling(self):
        fake = self.chat()
        recall.clear_open('s', 99, state_dir=self.state, base=fake.base, start=85)
        fake.calls = []
        self.assertEqual(recall.clear_open('s', 104, state_dir=self.state, base=fake.base), [103, 104])
        self.assertEqual([mid for _, mid in fake.calls if mid is not None and mid < 100], [])

    def test_first_clear_for_a_bot_reaches_back_a_fixed_distance(self):
        fake = self.chat()
        saved = recall.CLEAR_BACKFILL
        recall.CLEAR_BACKFILL = 10
        try:
            self.assertEqual(recall.clear_open('s', 103, state_dir=self.state, base=fake.base), [99, 103])
        finally:
            recall.CLEAR_BACKFILL = saved
        self.assertIn(90, fake.messages)

    def test_a_long_rate_limit_stops_and_keeps_the_mark_at_that_id(self):
        fake = self.chat()
        fake.limited = {92}
        self.assertEqual(recall.clear_open('s', 103, state_dir=self.state, base=fake.base, start=85, sleep=lambda s: None), [90])
        fake.limited = set()
        self.assertEqual(recall.clear_open('s', 103, state_dir=self.state, base=fake.base), [92, 99, 103])

    def test_after_an_allow_the_ceiling_is_this_requests_own_card(self):
        fake = self.chat()
        recall.LOG.write_text(json.dumps({'session': 's', 'action': 'swept', 'seen': 103}) + '\n')
        event = {'session_id': 's', 'tool_name': 'Bash', 'transcript_path': self.transcript(anchor=100)}
        recall._save_mark(hashlib_key(), 85)
        self.assertEqual(recall.clear_after_allow(event, state_dir=self.state, base=fake.base), [90, 92, 99, 103])
        self.assertTrue(fake.messages[104]['buttons'])

    def test_a_waiting_parallel_sibling_keeps_the_batch_cards(self):
        fake = self.chat()
        recall.LOG.write_text(json.dumps({'session': 's', 'action': 'swept', 'seen': 103}) + '\n')
        event = {'session_id': 's', 'tool_name': 'Bash', 'transcript_path': self.transcript(anchor=100, tools=('Bash', 'Write'))}
        recall._save_mark(hashlib_key(), 85)
        self.assertEqual(recall.clear_after_allow(event, state_dir=self.state, base=fake.base), [90, 92, 99])
        self.assertTrue(fake.messages[103]['buttons'] and fake.messages[104]['buttons'])

    def test_mark_reset_lowers_a_mark_that_ran_past_the_chat(self):
        recall._save_mark(hashlib_key(), 12172)
        recall._save_mark(hashlib_key(), 85)  # the ordinary path only raises
        self.assertEqual(recall._marks()[hashlib_key()], 12172)
        self.assertEqual(recall.reset_mark(self.state, 85), 12172)
        self.assertEqual(recall._marks()[hashlib_key()], 85)
        fake = self.chat()
        event = {'session_id': 's', 'tool_name': 'Bash', 'transcript_path': self.transcript(anchor=100)}
        self.assertEqual(recall.clear_after_allow(event, state_dir=self.state, base=fake.base), [90, 92, 99])


class AnchorProvenanceTests(unittest.TestCase):
    """2026-11-18: an id quoted in a file read became Auryn's anchor and stalled the janitor."""

    def setUp(self):
        RecallTests.setUp(self)

    transcript = RecallTests.transcript

    def anchor(self, *extra, anchor=100):
        return recall._anchor(Path(self.transcript(anchor=anchor, tools=(), extra=extra)).read_text())

    @staticmethod
    def result(use_id, name, text):
        return [{'type': 'assistant', 'message': {'id': 'm-' + use_id, 'role': 'assistant', 'content': [
                    {'type': 'tool_use', 'id': use_id, 'name': name, 'input': {}}]}},
                {'type': 'user', 'message': {'role': 'user', 'content': [
                    {'type': 'tool_result', 'tool_use_id': use_id, 'content': [{'type': 'text', 'text': text}]}]}}]

    def test_own_inbound_and_reply_set_the_anchor(self):
        self.assertEqual(self.anchor(), 100)

    def test_enqueued_channel_message_moves_the_anchor(self):
        row = {'type': 'queue-operation', 'operation': 'enqueue',
               'content': f'<channel source="plugin:telegram:telegram" chat_id="{CHAT}" message_id="104" user="op">\nyo'}
        self.assertEqual(self.anchor(row), 104)

    def test_multi_part_reply_moves_the_anchor_to_its_last_part(self):
        self.assertEqual(self.anchor(*self.result('r2', recall.REPLY_TOOL, 'sent 3 parts (ids: 101, 102, 103)')), 103)

    def test_quoted_sent_id_in_a_file_read_never_moves_the_anchor(self):
        quoted = 'Telegram reply 12171 (result `sent (id: 12171)`) and Telegram (12155 and 12171)'
        self.assertEqual(self.anchor(*self.result('x1', 'Read', quoted), *self.result('x2', 'Read', 'sent (id: 12171)')), 100)

    def test_quoted_channel_tag_in_a_tool_result_never_moves_the_anchor(self):
        tag = f'<channel source="plugin:telegram:telegram" chat_id="{CHAT}" message_id="12171">'
        self.assertEqual(self.anchor(*self.result('x1', 'Bash', tag)), 100)

    def test_quoted_ids_in_typed_text_or_a_summary_never_move_the_anchor(self):
        typed = {'type': 'user', 'message': {'role': 'user', 'content':
                 f'look: <channel source="plugin:telegram:telegram" chat_id="{CHAT}" message_id="12171"> and sent (id: 12350)'}}
        self.assertEqual(self.anchor(typed), 100)

    def test_no_telegram_traffic_means_no_anchor(self):
        path = self.dir / 'bare.jsonl'
        path.write_text('\n'.join(json.dumps(row) for row in self.result('x', 'Read', 'sent (id: 9)')) + '\n')
        self.assertIsNone(recall._anchor(path.read_text()))


def hashlib_key():
    import hashlib
    return hashlib.sha256(('123:abc:' + CHAT).encode()).hexdigest()[:16]


if __name__ == '__main__':
    unittest.main()

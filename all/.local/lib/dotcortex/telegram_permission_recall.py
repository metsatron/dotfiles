#!/usr/bin/env python3
"""Delete Telegram permission prompts for requests the approval gate allowed.

Usage: telegram_permission_recall.py <hook-start-epoch>   (hook event JSON on stdin)
See agents-approval-telegram-recall.org for the identification rules.
"""
import json
import datetime
import hashlib
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PREFIX = '\U0001f510 Permission: '
SWEEP_SECONDS = 8.0
SETTLE_SECONDS = 3.0  # our prompt is posted while the hook runs; the next request comes later
PROBE_AHEAD = 12  # buttonless gaps only; a buttoned message ends the sweep
TAIL_BYTES = 4 * 1024 * 1024
# The anchor is read by provenance, never by matching numbers anywhere in the
# transcript: on 2026-11-18 Auryn read a Fable handoff quoting
# "sent (id: 12171)", the regex took Fable's chat id as Auryn's newest message,
# and every later sweep and clear looked above 12171 in a chat whose ids were
# near 5600. Chat id cannot separate the two chats either: every bot DMs the
# same operator, so every seat's chat has the same chat_id.
REPLY_TOOL = 'mcp__plugin_telegram_telegram__reply'
CHANNEL_SERVERS = ('plugin:telegram:telegram',)
CHANNEL_TAG_RE = re.compile(r'\A\s*<channel source="(?:plugin:telegram:)?telegram"[^>]*\smessage_id="(\d+)"')
SENT_RE = re.compile(r'\Asent (?:\(id: (\d+)\)|\d+ parts \(ids: ([\d, ]+)\))\s*\Z')
LOG = Path(os.path.expanduser('~/.local/state/dotcortex/telegram-permission-recall.jsonl'))
# Per bot and chat: the lowest message id not yet checked for an open card.
CLEAR_STATE = Path(os.path.expanduser('~/.local/state/dotcortex/telegram-permission-clear.json'))
CLEAR_BACKFILL = 300  # first run for a bot: how far below the ceiling to start
CLEAR_LIMIT = 400  # Telegram calls per clear; the mark keeps the rest for the next run


def _log(**row):
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%S%z'), **row}) + '\n')
    except OSError:
        pass


def _token(state_dir):
    try:
        text = (state_dir / '.env').read_text(encoding='utf-8')
    except OSError:
        return None
    for line in text.splitlines():
        match = re.fullmatch(r'\s*TELEGRAM_BOT_TOKEN\s*=\s*(\S+)\s*', line)
        if match:
            return match.group(1)
    return None


def _chat(state_dir):
    try:
        access = json.loads((state_dir / 'access.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    chats = access.get('allowFrom') if isinstance(access, dict) else None
    if not isinstance(chats, list) or len(chats) != 1 or not re.fullmatch(r'-?\d+', str(chats[0])):
        return None
    return str(chats[0])


def _transcript_tail(path):
    try:
        with open(path, 'rb') as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - TAIL_BYTES))
            data = handle.read().decode('utf-8', errors='replace')
    except (OSError, TypeError):
        return None
    return data if size <= TAIL_BYTES else data.split('\n', 1)[-1]


def _texts(content):
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [block.get('text', '') for block in content
                if isinstance(block, dict) and block.get('type') == 'text' and isinstance(block.get('text'), str)]
    return []


def _anchor(tail):
    """Newest Telegram message id this session's own chat produced.

    Inbound: a channel-origin user row, or a queue-operation enqueue, whose
    content opens with the channel tag. Outbound: a tool_result answering a
    tool_use of the Telegram reply tool. Ids quoted anywhere else (a file
    read, a mail, a log, a compaction summary) are ignored."""
    ids, reply_uses = [], set()
    for line in (tail or '').splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict):
            continue
        if row.get('type') == 'queue-operation' and row.get('operation') == 'enqueue':
            content = row.get('content')
            match = CHANNEL_TAG_RE.match(content) if isinstance(content, str) else None
            if match:
                ids.append(int(match.group(1)))
            continue
        message = row.get('message') if isinstance(row.get('message'), dict) else {}
        content = message.get('content')
        origin = row.get('origin') if isinstance(row.get('origin'), dict) else {}
        if row.get('type') == 'user' and origin.get('kind') == 'channel' and origin.get('server') in CHANNEL_SERVERS:
            for text in _texts(content):
                match = CHANNEL_TAG_RE.match(text)
                if match:
                    ids.append(int(match.group(1)))
            continue
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'tool_use' and block.get('name') == REPLY_TOOL:
                reply_uses.add(block.get('id'))
            elif block.get('type') == 'tool_result' and block.get('tool_use_id') in reply_uses:
                for text in _texts(block.get('content')):
                    match = SENT_RE.match(text.strip())
                    if match:
                        ids.extend(int(part) for part in (match.group(1) or match.group(2)).replace(' ', '').split(',') if part)
    return max(ids) if ids else None


def _logged_floor(session):
    """Highest message id this session's earlier sweeps saw or deleted.

    The transcript anchor only moves when a Telegram message enters the
    session; prompts alone keep raising the chat's ids, so after twelve
    unanswered-by-text prompts they ran past the probe range and were never
    seen (Admiral 7316). Earlier sweeps record how far the chat has got."""
    try:
        with LOG.open('rb') as handle:
            handle.seek(0, os.SEEK_END)
            handle.seek(max(0, handle.tell() - 262144))
            lines = handle.read().decode('utf-8', 'replace').splitlines()
    except OSError:
        return None
    best = None
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict) or row.get('session') != session:
            continue
        for key in ('seen', 'message_id'):
            if key == 'message_id' and row.get('action') != 'deleted':
                continue  # an anomaly row may name a later request's prompt
            value = row.get(key)
            if type(value) is int and (best is None or value > best):
                best = value
    return best


def _unresolved(tail):
    """Unresolved tool calls in the newest assistant message only, with tools.

    Parallel tool calls share one assistant message id, so that batch is the
    only place another live request can be waiting. A call interrupted or
    refused long ago never gets a tool_result in the transcript; counting it
    stalled every later sweep (Admiral 7409). The tool names let an allow
    match its own card while a parallel request of a different tool is also
    waiting (2026-10-17, Telegram 7862/7865)."""
    uses, results, last_group = {}, set(), None
    for line in tail.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        message = row.get('message') if isinstance(row, dict) else None
        content = message.get('content') if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        group = message.get('id') or row.get('uuid')
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'tool_use' and block.get('id'):
                uses[block['id']] = (group, block.get('name'))
                last_group = group
            elif block.get('type') == 'tool_result' and block.get('tool_use_id'):
                results.add(block['tool_use_id'])
    return {use: name for use, (group, name) in uses.items()
            if group == last_group and use not in results}


def _request_slot(unresolved, event):
    """Return this request's zero-based prompt slot in the live batch.

    Claude normally supplies the tool-use id in the hook event. Older hook
    payloads do not, so a uniquely named unresolved tool is the safe fallback.
    A missing or ambiguous slot is never guessed when another request is live.
    """
    if not isinstance(event, dict):
        return None
    request_id = event.get('tool_use_id') or event.get('request_id')
    ids = list(unresolved)
    if isinstance(request_id, str) and request_id in unresolved:
        return ids.index(request_id)
    tool = event.get('tool_name')
    matches = [index for index, name in enumerate(unresolved.values()) if name == tool]
    return matches[0] if len(matches) == 1 else None


def _explicit_message_id(event):
    """Read an exact native-plugin prompt id when a caller has one."""
    if not isinstance(event, dict):
        return None
    for key in ('permission_message_id', 'telegram_message_id', 'prompt_message_id'):
        value = event.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
        if isinstance(value, str) and value.isdecimal() and int(value) > 0:
            return int(value)
    telegram = event.get('telegram')
    if isinstance(telegram, dict):
        value = telegram.get('message_id')
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
        if isinstance(value, str) and value.isdecimal() and int(value) > 0:
            return int(value)
    return None


def _call(base, token, method, payload):
    request = urllib.request.Request(
        f'{base}/bot{token}/{method}', data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.loads(response.read() or b'{}')
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read() or b'{}')
        except ValueError:
            return {'ok': False, 'description': f'http {exc.code}'}
    except (OSError, ValueError):
        return {'ok': False, 'description': 'transport'}



OUTCOMES = {
    'hold_timeout': '⏱️ Denied on idle, queued for the Desk',
    'timeout': '⏱️ Denied on idle, queued for the Desk',
    'away_flag': '⏸️ Denied while away, queued for the Desk',
    'unavailable': '⚠️ Delivery unavailable, queued for the Desk',
    'hold_unavailable': '⚠️ Delivery unavailable, queued for the Desk',
    'done_by_another_route': '✅ Done by another route',
    'resolved': '✅ Resolved on the Desk',
    'desk_approved': '✅ Approved from the Desk',
    'desk_declined': '❌ Declined from the Desk',
    'denied': '⏸️ Denied, queued for the Desk',
    'human_denied': '⛔ Denied, queued for the Desk',
}


def markdown_text(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])',r'\\\1',text)


def edit_outcome(base, token, chat, message_id, outcome):
    return _call(base,token,'editMessageText',{
        'chat_id':chat,'message_id':message_id,
        'text':markdown_text(OUTCOMES.get(outcome,OUTCOMES['denied'])),
        'parse_mode':'MarkdownV2','reply_markup':{'inline_keyboard':[]}}).get('ok') is True


def settle(item, outcome):
    request=item.get('request',{})
    session=item.get('session','')
    state=os.environ.get('TELEGRAM_STATE_DIR')
    token=os.environ.get('APPROVAL_TELEGRAM_BOT_TOKEN')
    chat=os.environ.get('APPROVAL_TELEGRAM_CHAT_ID')
    base=os.environ.get('APPROVAL_TELEGRAM_API_BASE')
    if not (token and chat and base) and state:
        token,chat=_token(Path(state)),_chat(Path(state))
        base=os.environ.get('TELEGRAM_API_BASE','https://api.telegram.org')
    if not token or not chat or not base:
        _log(session=session,action='cleanup_failed',why='credentials_unavailable');return False
    digest=item.get('notification_sha')
    bot_key=hashlib.sha256((token+':'+chat).encode()).hexdigest()
    ids=set()
    receipts=Path.home()/'.local/state/dotcortex/approval-telegram-receipts.jsonl'
    try:
        for line in receipts.read_text().splitlines():
            row=json.loads(line)
            if digest and row.get('request_sha')==digest and row.get('bot_key')==bot_key and type(row.get('message_id')) is int:ids.add(row['message_id'])
    except FileNotFoundError:pass
    except (OSError,ValueError):
        _log(session=session,action='cleanup_failed',why='receipts_unreadable');return False
    ok=True
    for message_id in ids:
        edited=edit_outcome(base,token,chat,message_id,outcome);ok=ok and edited
        _log(session=session,action='outcome_edited' if edited else 'cleanup_failed',message_id=message_id)
    # Native plugin sends bypass approval-telegram-notify. Use the existing
    # bounded recall lane only when the original prompt window is known: the
    # PTY captured its hold window, or a hook-queued item carries first_seen,
    # the moment the request first hit the gate and the card was posted.
    started=request.get('hold_started') or item.get('hold_started')
    if started is None and isinstance(item.get('first_seen'), str):
        try:
            started = datetime.datetime.fromisoformat(item['first_seen']).timestamp()
        except ValueError:
            started = None
    if state and isinstance(started,(int,float)) and request.get('transcript_path'):
        native=sweep(request,started,state_dir=Path(state),base=base,outcome=outcome)
        ok=bool(native) and ok
    elif not ids:
        _log(session=session,action='cleanup_failed',why='no_bound_message_or_hold_window');return False
    return ok


def sweep(event, started, *, state_dir, base, now=time.time, sleep=time.sleep, sweep_seconds=SWEEP_SECONDS,
          settle_seconds=SETTLE_SECONDS, outcome=None):
    """Return the deleted message id as a one-item list (empty when nothing qualifies)."""
    decided = now()  # the wrapper starts this right after the gate allowed
    session = event.get('session_id', '') if isinstance(event, dict) else ''
    tool = event.get('tool_name') if isinstance(event, dict) else None
    if not isinstance(tool, str) or not tool:
        _log(session=session, action='skip', why='no_tool')
        return []
    wanted = PREFIX + tool  # the card names its tool; parallel prompts do not share it
    token, chat = _token(state_dir), _chat(state_dir)
    if not token or not chat:
        _log(session=session, action='skip', why='no_token' if not token else 'chat_not_single')
        return []
    tail = _transcript_tail(event.get('transcript_path')) if isinstance(event, dict) else None
    if tail is None:
        _log(session=session, action='skip', why='no_transcript')
        return []
    unresolved = _unresolved(tail)
    if sum(1 for name in unresolved.values() if name == tool) > 1:
        # Two same-tool calls pending at once: either card could be the other
        # request's live floor ask, and nothing in the window tells them apart.
        _log(session=session, action='skip', why='same_tool_parallel')
        return []
    slot = _request_slot(unresolved, event)
    explicit = _explicit_message_id(event)
    if slot is None and explicit is None:
        # An outcome settled after the transcript moved on may have no live
        # call, but it must not probe a sibling that is still waiting.
        _log(session=session, action='skip', why='request_slot_unknown')
        return []
    anchor = _anchor(tail)
    floor = _logged_floor(session) if session else None
    if anchor is not None and floor is not None:
        anchor = max(anchor, floor)
    if anchor is None:
        _log(session=session, action='skip', why='no_anchor')
        return []
    parallel = len(unresolved) > 1 and explicit is None
    if explicit is not None:
        candidates = [explicit]
    else:
        # A logged floor already names every safe id before it. For a new
        # parallel batch, use the request's ordered slot and probe exactly one
        # id; for a single request, buttonless Telegram messages may occupy a
        # gap, so only those are scanned ahead.
        start = anchor + 1 if floor is not None else anchor + (slot or 0) + 1
        candidates = [start] if parallel else list(range(start, start + PROBE_AHEAD))
    done, deleted, seen = set(), [], None
    deadline = decided + settle_seconds if outcome else min(started + sweep_seconds, decided + settle_seconds)
    while now() < deadline:
        for message_id in candidates:
            if message_id in done:
                continue
            if message_id <= anchor:
                _log(session=session, action='skip', why='message_at_or_below_anchor', message_id=message_id)
                done.add(message_id)
                continue
            reply = _call(base, token, 'editMessageReplyMarkup', {'chat_id': chat, 'message_id': message_id})
            if not reply.get('ok'):
                if 'not found' in str(reply.get('description', '')):
                    continue  # not sent yet; retried on the next pass
                done.add(message_id)
                # User messages and buttonless bot replies are safe gaps. In a
                # parallel batch there is no safe adjacent-id inference.
                seen = message_id if seen is None else max(seen, message_id)
                if parallel:
                    deadline = 0
                    break
                continue
            done.add(message_id)
            message = reply.get('result') if isinstance(reply.get('result'), dict) else {}
            text, date = message.get('text', ''), message.get('date')
            in_window = isinstance(date, int) and int(started) - 1 <= date <= (int(started + SETTLE_SECONDS) + 1 if outcome else int(decided) + 1)
            if not (isinstance(text, str) and text.startswith(PREFIX)):
                _log(session=session, action='anomaly', message_id=message_id, why='buttoned_non_permission')
                seen = message_id if seen is None else max(seen, message_id)
                deadline = 0
                break
            if not in_window:
                if (not outcome and not parallel and isinstance(date, int)
                        and date < int(started) - 1):
                    # A permission card older than this request, with no sibling
                    # request waiting. The probe above has already removed its
                    # buttons, so it is dead either way: it is the leftover of a
                    # sweep that missed. Left in place it stopped this sweep and
                    # every later one at the same card (71 dead cards on
                    # 2026-11-17). Delete it and go on to this request's own card.
                    gone = _call(base, token, 'deleteMessage', {'chat_id': chat, 'message_id': message_id}).get('ok')
                    _log(session=session, action='deleted_stale' if gone else 'cleanup_failed', message_id=message_id)
                    seen = message_id if seen is None else max(seen, message_id)
                    continue
                _log(session=session, action='skip', message_id=message_id, why='prompt_outside_window')
                deadline = 0
                break
            if not text.startswith(wanted):
                _log(session=session, action='skip', message_id=message_id, why='prompt_not_owned')
                deadline = 0
                break
            seen = message_id if seen is None else max(seen, message_id)
            if (edit_outcome(base,token,chat,message_id,outcome) if outcome else
                    _call(base,token,'deleteMessage',{'chat_id':chat,'message_id':message_id}).get('ok')):
                deleted.append(message_id)
                _log(session=session,action='outcome_edited' if outcome else 'deleted',message_id=message_id)
            else:_log(session=session,action='cleanup_failed',message_id=message_id)
            deadline = 0  # one request, one prompt
            break
        sleep(0.5)
    _log(session=session, action='swept', anchor=anchor, deleted=deleted, **({'seen': seen} if seen is not None else {}))
    return deleted


def _marks():
    try:
        data = json.loads(CLEAR_STATE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_mark(key, value):
    try:
        marks = _marks()  # re-read: a parallel clear may have moved it further
        if type(marks.get(key)) is int and marks[key] >= value:
            return
        marks[key] = value
        CLEAR_STATE.parent.mkdir(parents=True, exist_ok=True)
        temp = CLEAR_STATE.with_name(CLEAR_STATE.name + f'.{os.getpid()}.tmp')
        temp.write_text(json.dumps(marks, sort_keys=True) + '\n', encoding='utf-8')
        os.replace(temp, CLEAR_STATE)
    except OSError:
        pass


def reset_mark(state_dir, value):
    """Set a bot's clear mark to value, lower or higher. Operator-run only.

    _save_mark only raises a mark, so a mark pushed too far (2026-11-18:
    Auryn's bot at 12172 after a quoted id became its anchor) could never come
    back down by itself and every later clear checked nothing."""
    token, chat = _token(state_dir), _chat(state_dir)
    if not token or not chat or type(value) is not int or value < 1:
        raise ValueError('state dir has no bot token or single chat, or the id is not positive')
    key = hashlib.sha256((token + ':' + chat).encode()).hexdigest()[:16]
    marks = _marks()
    before = marks.get(key)
    marks[key] = value
    CLEAR_STATE.parent.mkdir(parents=True, exist_ok=True)
    temp = CLEAR_STATE.with_name(CLEAR_STATE.name + f'.{os.getpid()}.tmp')
    temp.write_text(json.dumps(marks, sort_keys=True) + '\n', encoding='utf-8')
    os.replace(temp, CLEAR_STATE)
    _log(session='manual', action='mark_reset', before=before, after=value)
    return before


def clear_open(session, ceiling, *, state_dir, base, sleep=time.sleep, start=None, limit=CLEAR_LIMIT):
    """Delete every permission card that still has buttons, up to ceiling.

    Mètsàtron's rule (Telegram 12310, 12313, 2026-11-18; first stated
    2026-11-17 03:23): once a request is approved, every card still showing
    its buttons is already settled, so the chat keeps at most one open card,
    the live ask. The ceiling is this request's own card or the newest message
    the session knows, so a card newer than it, a later request's live ask,
    is never touched. The plugin keeps no record of its card ids, so each id
    from the stored mark up to the ceiling is checked once; the mark then
    moves past it and the next clear starts there."""
    token, chat = _token(state_dir), _chat(state_dir)
    if not token or not chat or type(ceiling) is not int or ceiling < 1:
        _log(session=session, action='skip', why='clear_unbounded')
        return []
    key = hashlib.sha256((token + ':' + chat).encode()).hexdigest()[:16]
    low = start if type(start) is int else _marks().get(key)
    if type(low) is not int:
        low = max(1, ceiling - CLEAR_BACKFILL)
    message_id, calls, deleted, failures, stopped = max(1, low), 0, [], 0, None
    while message_id <= ceiling:
        if calls >= limit:
            stopped = 'call_limit'
            break
        reply = _call(base, token, 'editMessageReplyMarkup', {'chat_id': chat, 'message_id': message_id})
        calls += 1
        if not reply.get('ok'):
            params = reply.get('parameters') if isinstance(reply.get('parameters'), dict) else {}
            retry = params.get('retry_after')
            if type(retry) is int and retry <= 5:
                sleep(retry)
                continue  # same id again
            if retry is not None:
                stopped = f'rate_limited_{retry}s'
                break  # keep the mark here; the next clear resumes at this id
            if reply.get('description') in ('transport', None) or str(reply.get('description', '')).startswith('http '):
                failures += 1
                if failures <= 2:
                    sleep(1)
                    continue
                stopped = 'transport'
                break
            message_id += 1  # a user message, a buttonless reply, or a deleted id
            continue
        message = reply.get('result') if isinstance(reply.get('result'), dict) else {}
        text = message.get('text', '')
        if isinstance(text, str) and text.startswith(PREFIX):
            gone = _call(base, token, 'deleteMessage', {'chat_id': chat, 'message_id': message_id}).get('ok')
            calls += 1
            _log(session=session, action='deleted_open' if gone else 'cleanup_failed', message_id=message_id)
            if gone:
                deleted.append(message_id)
        else:
            _log(session=session, action='anomaly', message_id=message_id, why='buttoned_non_permission')
        message_id += 1
    _save_mark(key, message_id)
    _log(session=session, action='cleared', low=low, ceiling=ceiling, next=message_id, deleted=deleted,
         calls=calls, **({'stopped': stopped} if stopped else {}))
    return deleted


def clear_after_allow(event, *, state_dir, base, sleep=time.sleep):
    """After an allow: clear every open card up to this request's own card.

    The ceiling is the highest id this session's sweeps have seen (its own
    card when the sweep found it) or the newest Telegram message in the
    transcript. While a parallel sibling is still waiting, the ceiling drops
    to the transcript's newest message, so the batch's live cards stay; the
    last allow in the batch clears them."""
    session = event.get('session_id', '') if isinstance(event, dict) else ''
    tail = _transcript_tail(event.get('transcript_path')) if isinstance(event, dict) else None
    if tail is None:
        _log(session=session, action='skip', why='clear_no_transcript')
        return []
    anchor = _anchor(tail)
    floor = _logged_floor(session) if session else None
    if len(_unresolved(tail)) > 1:
        ceiling = anchor
    else:
        ceiling = max((value for value in (anchor, floor) if value is not None), default=None)
    return clear_open(session, ceiling, state_dir=state_dir, base=base, sleep=sleep)


def main(argv):
    if len(argv)==3 and argv[1]=='--reset-mark':
        # Manual repair: --reset-mark <next-id>, TELEGRAM_STATE_DIR set.
        state = os.environ.get('TELEGRAM_STATE_DIR')
        if not state or not argv[2].isdecimal():
            print('usage: TELEGRAM_STATE_DIR=<dir> telegram_permission_recall.py --reset-mark <next-id>', file=sys.stderr)
            return 2
        try:
            before = reset_mark(Path(state), int(argv[2]))
        except (OSError, ValueError) as error:
            print(f'reset-mark refused: {error}', file=sys.stderr)
            return 1
        print(json.dumps({'before': before, 'after': int(argv[2])}))
        return 0
    if len(argv)==4 and argv[1]=='--clear':
        # Manual backlog clear: --clear <first-id> <ceiling-id>, TELEGRAM_STATE_DIR set.
        state = os.environ.get('TELEGRAM_STATE_DIR')
        if not state or not argv[2].isdecimal() or not argv[3].isdecimal():
            print('usage: TELEGRAM_STATE_DIR=<dir> telegram_permission_recall.py --clear <first-id> <ceiling-id>', file=sys.stderr)
            return 2
        base = os.environ.get('TELEGRAM_API_BASE', 'https://api.telegram.org').rstrip('/')
        gone = clear_open('manual', int(argv[3]), state_dir=Path(state), base=base, start=int(argv[2]),
                          limit=4 * (int(argv[3]) - int(argv[2]) + 1) + 20)
        print(json.dumps({'deleted': gone}))
        return 0
    if len(argv)==2 and argv[1]=='--outcome':
        try:
            value=json.loads(sys.stdin.read(1024*1024));return 0 if settle(value['item'],value['outcome']) else 1
        except (OSError,ValueError,KeyError,TypeError):
            _log(action='cleanup_failed',why='invalid_outcome_request');return 1
    state = os.environ.get('TELEGRAM_STATE_DIR')
    if not state or len(argv) not in (2,3):
        _log(action='skip', why='no_state_dir' if not state else 'bad_argv')
        return 0
    try:
        started = float(argv[1])
        event = json.loads(sys.stdin.read(1024 * 1024))
    except ValueError:
        _log(action='skip', why='bad_input')
        return 0
    base = os.environ.get('TELEGRAM_API_BASE', 'https://api.telegram.org').rstrip('/')
    outcome = argv[2] if len(argv)==3 else None
    sweep(event, started, state_dir=Path(state), base=base,outcome=outcome)
    if outcome is None:
        clear_after_allow(event, state_dir=Path(state), base=base)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))

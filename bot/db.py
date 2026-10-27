from __future__ import annotations

import os
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import aiosqlite

from bot.services.statuses import CLOSED, OPEN

Row = Dict[str, Any]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL DEFAULT '',
    username TEXT,
    is_banned INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    last_seen_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS operators (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL DEFAULT '',
    username TEXT,
    last_seen_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL,
    description TEXT NOT NULL,
    operator_id INTEGER,
    thread_id INTEGER,
    created_at INTEGER NOT NULL,
    taken_at INTEGER,
    first_reply_at INTEGER,
    closed_at INTEGER,
    reopened_at INTEGER,
    last_client_at INTEGER,
    last_operator_at INTEGER,
    awaiting_since INTEGER,
    reminded_at INTEGER
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    sender TEXT NOT NULL,
    sender_id INTEGER,
    text TEXT,
    media_type TEXT,
    file_id TEXT,
    file_name TEXT,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    comment TEXT,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS relays (
    chat_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    ticket_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    PRIMARY KEY (chat_id, message_id)
);
CREATE INDEX IF NOT EXISTS idx_tickets_user ON tickets (user_id, status);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets (status, category);
CREATE INDEX IF NOT EXISTS idx_tickets_thread ON tickets (thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_ticket ON messages (ticket_id, id);
CREATE INDEX IF NOT EXISTS idx_relays_ticket ON relays (ticket_id, kind);
"""


def now_ts() -> int:
    return int(time.time())


class Database:
    def __init__(self, path: str, first_ticket_number: int = 1001) -> None:
        self.path = path
        self.first_ticket_number = first_ticket_number
        self._conn: Optional[aiosqlite.Connection] = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("database is not connected")
        return self._conn

    async def connect(self) -> None:
        if self.path != ":memory:":
            directory = os.path.dirname(self.path)
            if directory:
                os.makedirs(directory, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        if self.path != ":memory:":
            await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def _one(self, sql: str, params: Iterable[Any] = ()) -> Optional[Row]:
        async with self.conn.execute(sql, tuple(params)) as cursor:
            row = await cursor.fetchone()
        return dict(row) if row is not None else None

    async def _all(self, sql: str, params: Iterable[Any] = ()) -> List[Row]:
        async with self.conn.execute(sql, tuple(params)) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def _run(self, sql: str, params: Iterable[Any] = ()) -> Optional[int]:
        cursor = await self.conn.execute(sql, tuple(params))
        await self.conn.commit()
        return cursor.lastrowid

    async def upsert_user(self, user_id: int, full_name: str, username: Optional[str]) -> Row:
        ts = now_ts()
        await self._run(
            "INSERT INTO users (id, full_name, username, created_at, last_seen_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET full_name = excluded.full_name, "
            "username = excluded.username, last_seen_at = excluded.last_seen_at",
            (user_id, full_name or "", username, ts, ts),
        )
        user = await self.get_user(user_id)
        assert user is not None
        return user

    async def get_user(self, user_id: int) -> Optional[Row]:
        return await self._one("SELECT * FROM users WHERE id = ?", (user_id,))

    async def users_map(self, user_ids: Iterable[int]) -> Dict[int, Row]:
        ids = sorted(set(user_ids))
        if not ids:
            return {}
        placeholders = ", ".join("?" for _ in ids)
        rows = await self._all(f"SELECT * FROM users WHERE id IN ({placeholders})", ids)
        return {row["id"]: row for row in rows}

    async def set_banned(self, user_id: int, banned: bool) -> Optional[Row]:
        user = await self.get_user(user_id)
        if user is None:
            ts = now_ts()
            await self._run(
                "INSERT INTO users (id, full_name, username, is_banned, created_at, last_seen_at) VALUES (?, '', NULL, ?, ?, ?)",
                (user_id, int(banned), ts, ts),
            )
        else:
            await self._run("UPDATE users SET is_banned = ? WHERE id = ?", (int(banned), user_id))
        return await self.get_user(user_id)

    async def upsert_operator(self, operator_id: int, full_name: str, username: Optional[str]) -> None:
        await self._run(
            "INSERT INTO operators (id, full_name, username, last_seen_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET full_name = excluded.full_name, "
            "username = excluded.username, last_seen_at = excluded.last_seen_at",
            (operator_id, full_name or "", username, now_ts()),
        )

    async def get_operator(self, operator_id: int) -> Optional[Row]:
        return await self._one("SELECT * FROM operators WHERE id = ?", (operator_id,))

    async def operators_map(self) -> Dict[int, str]:
        rows = await self._all("SELECT id, full_name FROM operators")
        return {row["id"]: row["full_name"] or str(row["id"]) for row in rows}

    async def create_ticket(self, user_id: int, category: str, description: str, ts: Optional[int] = None) -> Row:
        ts = ts or now_ts()
        ticket_id = await self._run(
            "INSERT INTO tickets (id, user_id, category, status, description, created_at, last_client_at, awaiting_since) "
            "VALUES ((SELECT COALESCE(MAX(id), ?) + 1 FROM tickets), ?, ?, ?, ?, ?, ?, ?)",
            (self.first_ticket_number - 1, user_id, category, OPEN, description, ts, ts, ts),
        )
        ticket = await self.get_ticket(ticket_id)
        assert ticket is not None
        return ticket

    async def get_ticket(self, ticket_id: int) -> Optional[Row]:
        return await self._one("SELECT * FROM tickets WHERE id = ?", (ticket_id,))

    async def update_ticket(self, ticket_id: int, **fields: Any) -> Row:
        if fields:
            assignments = ", ".join(f"{key} = ?" for key in fields)
            await self._run(f"UPDATE tickets SET {assignments} WHERE id = ?", (*fields.values(), ticket_id))
        ticket = await self.get_ticket(ticket_id)
        assert ticket is not None
        return ticket

    @staticmethod
    def _ticket_filters(status: Optional[str], category: Optional[str]) -> Tuple[str, List[Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if category:
            clauses.append("category = ?")
            params.append(category)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        return where, params

    async def list_tickets(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Row]:
        where, params = self._ticket_filters(status, category)
        return await self._all(
            f"SELECT * FROM tickets{where} ORDER BY id DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )

    async def count_tickets(self, status: Optional[str] = None, category: Optional[str] = None) -> int:
        where, params = self._ticket_filters(status, category)
        row = await self._one(f"SELECT COUNT(*) AS total FROM tickets{where}", params)
        return int(row["total"]) if row else 0

    async def user_tickets(self, user_id: int, limit: int = 10) -> List[Row]:
        return await self._all(
            "SELECT * FROM tickets WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )

    async def active_ticket_for_user(self, user_id: int) -> Optional[Row]:
        return await self._one(
            "SELECT * FROM tickets WHERE user_id = ? AND status != ? ORDER BY id DESC LIMIT 1",
            (user_id, CLOSED),
        )

    async def latest_ticket_for_user(self, user_id: int) -> Optional[Row]:
        return await self._one("SELECT * FROM tickets WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))

    async def ticket_by_thread(self, thread_id: int) -> Optional[Row]:
        return await self._one("SELECT * FROM tickets WHERE thread_id = ? ORDER BY id DESC LIMIT 1", (thread_id,))

    async def tickets_for_stats(self, since_ts: int) -> List[Row]:
        return await self._all(
            "SELECT * FROM tickets WHERE created_at >= ? OR closed_at >= ? OR first_reply_at >= ? OR status != ?",
            (since_ts, since_ts, since_ts, CLOSED),
        )

    async def tickets_awaiting(self, older_than_ts: int, reminded_before_ts: int) -> List[Row]:
        return await self._all(
            "SELECT * FROM tickets WHERE status != ? AND awaiting_since IS NOT NULL AND awaiting_since <= ? "
            "AND (reminded_at IS NULL OR reminded_at <= ?) ORDER BY awaiting_since",
            (CLOSED, older_than_ts, reminded_before_ts),
        )

    async def mark_reminded(self, ticket_ids: Iterable[int], ts: int) -> None:
        ids = list(ticket_ids)
        if not ids:
            return
        placeholders = ", ".join("?" for _ in ids)
        await self._run(f"UPDATE tickets SET reminded_at = ? WHERE id IN ({placeholders})", (ts, *ids))

    async def add_message(
        self,
        ticket_id: int,
        sender: str,
        sender_id: Optional[int],
        text: Optional[str],
        media_type: Optional[str] = None,
        file_id: Optional[str] = None,
        file_name: Optional[str] = None,
        ts: Optional[int] = None,
    ) -> int:
        message_id = await self._run(
            "INSERT INTO messages (ticket_id, sender, sender_id, text, media_type, file_id, file_name, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, sender, sender_id, text, media_type, file_id, file_name, ts or now_ts()),
        )
        return int(message_id or 0)

    async def ticket_messages(self, ticket_id: int, limit: Optional[int] = None) -> List[Row]:
        if limit is None:
            return await self._all("SELECT * FROM messages WHERE ticket_id = ? ORDER BY id", (ticket_id,))
        rows = await self._all(
            "SELECT * FROM messages WHERE ticket_id = ? ORDER BY id DESC LIMIT ?",
            (ticket_id, limit),
        )
        return list(reversed(rows))

    async def count_attachments(self, ticket_id: int) -> int:
        row = await self._one(
            "SELECT COUNT(*) AS total FROM messages WHERE ticket_id = ? AND media_type IS NOT NULL",
            (ticket_id,),
        )
        return int(row["total"]) if row else 0

    async def add_rating(self, ticket_id: int, user_id: int, score: int, ts: Optional[int] = None) -> None:
        await self._run(
            "INSERT INTO ratings (ticket_id, user_id, score, created_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(ticket_id) DO UPDATE SET score = excluded.score, created_at = excluded.created_at",
            (ticket_id, user_id, score, ts or now_ts()),
        )

    async def set_rating_comment(self, ticket_id: int, comment: str) -> None:
        await self._run("UPDATE ratings SET comment = ? WHERE ticket_id = ?", (comment, ticket_id))

    async def get_rating(self, ticket_id: int) -> Optional[Row]:
        return await self._one("SELECT * FROM ratings WHERE ticket_id = ?", (ticket_id,))

    async def ratings_since(self, since_ts: int) -> List[Row]:
        return await self._all("SELECT * FROM ratings WHERE created_at >= ?", (since_ts,))

    async def add_relay(self, chat_id: int, message_id: int, ticket_id: int, kind: str) -> None:
        await self._run(
            "INSERT OR REPLACE INTO relays (chat_id, message_id, ticket_id, kind) VALUES (?, ?, ?, ?)",
            (chat_id, message_id, ticket_id, kind),
        )

    async def find_relay(self, chat_id: int, message_id: int) -> Optional[Row]:
        return await self._one(
            "SELECT * FROM relays WHERE chat_id = ? AND message_id = ?",
            (chat_id, message_id),
        )

    async def latest_cards(self, ticket_id: int) -> List[Row]:
        return await self._all(
            "SELECT chat_id, MAX(message_id) AS message_id FROM relays WHERE ticket_id = ? AND kind = 'card' GROUP BY chat_id",
            (ticket_id,),
        )

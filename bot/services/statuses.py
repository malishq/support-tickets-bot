from __future__ import annotations

from typing import Dict, Optional, Set

OPEN = "open"
IN_PROGRESS = "in_progress"
WAITING_CLIENT = "waiting_client"
CLOSED = "closed"

ALL = (OPEN, IN_PROGRESS, WAITING_CLIENT, CLOSED)
ACTIVE = (OPEN, IN_PROGRESS, WAITING_CLIENT)

LABELS: Dict[str, str] = {
    OPEN: "открыт",
    IN_PROGRESS: "в работе",
    WAITING_CLIENT: "ждём ответа клиента",
    CLOSED: "закрыт",
}

CLIENT_LABELS: Dict[str, str] = {
    OPEN: "открыт, ждёт оператора",
    IN_PROGRESS: "в работе",
    WAITING_CLIENT: "ждём вашего ответа",
    CLOSED: "закрыт",
}

ICONS: Dict[str, str] = {
    OPEN: "🟢",
    IN_PROGRESS: "🔵",
    WAITING_CLIENT: "🟡",
    CLOSED: "⚪️",
}

TRANSITIONS: Dict[str, Set[str]] = {
    OPEN: {IN_PROGRESS, WAITING_CLIENT, CLOSED},
    IN_PROGRESS: {WAITING_CLIENT, CLOSED},
    WAITING_CLIENT: {IN_PROGRESS, CLOSED},
    CLOSED: {OPEN, IN_PROGRESS},
}

ALIASES: Dict[str, str] = {
    "open": OPEN,
    "new": OPEN,
    "открыт": OPEN,
    "открытые": OPEN,
    "новые": OPEN,
    "in_progress": IN_PROGRESS,
    "progress": IN_PROGRESS,
    "work": IN_PROGRESS,
    "в работе": IN_PROGRESS,
    "работа": IN_PROGRESS,
    "waiting": WAITING_CLIENT,
    "waiting_client": WAITING_CLIENT,
    "ждем": WAITING_CLIENT,
    "ждем клиента": WAITING_CLIENT,
    "closed": CLOSED,
    "close": CLOSED,
    "закрыт": CLOSED,
    "закрытые": CLOSED,
}


class InvalidTransition(ValueError):
    pass


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())


def transition(current: str, target: str) -> str:
    if not can_transition(current, target):
        raise InvalidTransition(f"{current} -> {target}")
    return target


def on_client_message(status: str) -> str:
    if status == CLOSED:
        raise InvalidTransition("closed ticket does not accept messages")
    if status == WAITING_CLIENT:
        return IN_PROGRESS
    return status


def on_operator_reply(status: str) -> str:
    if status == CLOSED:
        raise InvalidTransition("closed ticket does not accept replies")
    return WAITING_CLIENT


def on_take(status: str) -> str:
    if status != OPEN:
        raise InvalidTransition(f"only open tickets can be taken, got {status}")
    return IN_PROGRESS


def on_close(status: str) -> str:
    return transition(status, CLOSED)


def on_reopen(status: str, has_operator: bool) -> str:
    if status != CLOSED:
        raise InvalidTransition("only closed tickets can be reopened")
    return IN_PROGRESS if has_operator else OPEN


def can_reopen(closed_at: Optional[int], now: int, reopen_hours: int) -> bool:
    if closed_at is None:
        return False
    return 0 <= now - closed_at <= reopen_hours * 3600


def label(status: str) -> str:
    return LABELS.get(status, status)


def client_label(status: str) -> str:
    return CLIENT_LABELS.get(status, label(status))


def icon(status: str) -> str:
    return ICONS.get(status, "⚪️")


def parse_status(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    return ALIASES.get(text.strip().lower().replace("ё", "е"))

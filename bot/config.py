from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv


def parse_ids(value: str) -> List[int]:
    ids: List[int] = []
    for part in value.replace(";", ",").split(","):
        part = part.strip()
        if part:
            ids.append(int(part))
    return ids


def parse_optional_int(value: str) -> Optional[int]:
    value = value.strip()
    return int(value) if value else None


def env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    return int(value) if value else default


@dataclass
class Config:
    bot_token: str
    operator_ids: List[int]
    admin_ids: List[int]
    support_chat_id: Optional[int]
    db_path: str
    faq_path: str
    templates_path: str
    reminder_minutes: int
    reminder_check_seconds: int
    reopen_hours: int
    tz_offset_hours: int
    first_ticket_number: int


def load_config(env_file: str = ".env") -> Config:
    load_dotenv(env_file)
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN не задан: создайте .env по образцу .env.example")
    operator_ids = parse_ids(os.getenv("OPERATOR_IDS", ""))
    admin_ids = parse_ids(os.getenv("ADMIN_IDS", "")) or list(operator_ids)
    return Config(
        bot_token=token,
        operator_ids=operator_ids,
        admin_ids=admin_ids,
        support_chat_id=parse_optional_int(os.getenv("SUPPORT_CHAT_ID", "")),
        db_path=os.getenv("DB_PATH", "data/support.db").strip() or "data/support.db",
        faq_path=os.getenv("FAQ_PATH", "data/faq.json").strip() or "data/faq.json",
        templates_path=os.getenv("TEMPLATES_PATH", "data/templates.json").strip() or "data/templates.json",
        reminder_minutes=env_int("REMINDER_MINUTES", 15),
        reminder_check_seconds=env_int("REMINDER_CHECK_SECONDS", 60),
        reopen_hours=env_int("REOPEN_HOURS", 24),
        tz_offset_hours=env_int("TZ_OFFSET_HOURS", 3),
        first_ticket_number=env_int("FIRST_TICKET_NUMBER", 1001),
    )

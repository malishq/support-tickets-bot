from __future__ import annotations

import re
from typing import Any, Optional, Tuple

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message

TICKET_RE = re.compile(r"#?(\d{1,10})")


def extract_content(message: Message) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    if message.photo:
        return message.caption, "photo", message.photo[-1].file_id, None
    if message.document:
        return message.caption, "document", message.document.file_id, message.document.file_name
    return message.text, None, None, None


def parse_ticket_number(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    match = TICKET_RE.search(text.strip())
    return int(match.group(1)) if match else None


async def safe_edit(message: Any, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None) -> None:
    if not isinstance(message, Message):
        return
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as error:
        description = str(error)
        if "message is not modified" in description:
            return
        if "no text in the message" in description or "can't be edited" in description:
            await message.answer(text, reply_markup=reply_markup)
            return
        raise


async def safe_edit_markup(message: Any, reply_markup: Optional[InlineKeyboardMarkup]) -> None:
    if not isinstance(message, Message):
        return
    try:
        await message.edit_reply_markup(reply_markup=reply_markup)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot import texts
from bot.config import Config
from bot.db import Database


class AccessMiddleware(BaseMiddleware):
    def __init__(self, db: Database, config: Config) -> None:
        self.db = db
        self.config = config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        chat = data.get("event_chat")
        if user is None or user.is_bot or chat is None or chat.type != "private":
            return await handler(event, data)
        record = await self.db.upsert_user(user.id, user.full_name, user.username)
        privileged = user.id in self.config.admin_ids or user.id in self.config.operator_ids
        if record["is_banned"] and not privileged:
            if isinstance(event, Message):
                await event.answer(texts.BANNED)
            elif isinstance(event, CallbackQuery):
                await event.answer(texts.BANNED, show_alert=True)
            return None
        data["user_record"] = record
        return await handler(event, data)

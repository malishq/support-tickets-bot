from __future__ import annotations

import logging
from typing import Awaitable

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat

from bot import texts
from bot.config import Config

logger = logging.getLogger(__name__)

CLIENT_COMMANDS = [
    BotCommand(command="start", description="Начать"),
    BotCommand(command="new", description="Новое обращение"),
    BotCommand(command="my", description="Мои обращения"),
    BotCommand(command="faq", description="Частые вопросы"),
    BotCommand(command="help", description="Помощь"),
    BotCommand(command="cancel", description="Отменить текущее действие"),
]

OPERATOR_COMMANDS = [
    BotCommand(command="tickets", description="Список обращений"),
    BotCommand(command="ticket", description="Карточка обращения: /ticket 1001"),
    BotCommand(command="stats", description="Статистика"),
    BotCommand(command="ban", description="Заблокировать пользователя"),
    BotCommand(command="unban", description="Разблокировать пользователя"),
    BotCommand(command="chatid", description="Показать id этого чата"),
]


async def _attempt(label: str, call: Awaitable[object]) -> None:
    try:
        await call
    except TelegramAPIError as error:
        logger.warning("%s: %s", label, error)


async def register_bot_meta(bot: Bot, config: Config) -> None:
    await _attempt(
        "Команды для клиентов не обновлены",
        bot.set_my_commands(CLIENT_COMMANDS, scope=BotCommandScopeAllPrivateChats()),
    )
    for operator_id in config.operator_ids:
        await _attempt(
            f"Команды для оператора {operator_id} не обновлены (он ещё не открывал чат с ботом?)",
            bot.set_my_commands(OPERATOR_COMMANDS + CLIENT_COMMANDS, scope=BotCommandScopeChat(chat_id=operator_id)),
        )
    if config.support_chat_id is not None:
        await _attempt(
            "Команды для группы операторов не обновлены",
            bot.set_my_commands(OPERATOR_COMMANDS, scope=BotCommandScopeChat(chat_id=config.support_chat_id)),
        )
    await _attempt("Описание бота не обновлено", bot.set_my_description(description=texts.BOT_DESCRIPTION))
    await _attempt(
        "Короткое описание не обновлено",
        bot.set_my_short_description(short_description=texts.BOT_SHORT_DESCRIPTION),
    )

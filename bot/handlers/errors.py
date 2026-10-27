from __future__ import annotations

import logging

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ErrorEvent

from bot import texts

logger = logging.getLogger(__name__)

router = Router(name="errors")


@router.errors()
async def on_error(event: ErrorEvent) -> bool:
    exception = event.exception
    if isinstance(exception, TelegramBadRequest) and "message is not modified" in str(exception):
        return True
    logger.error("Ошибка при обработке обновления %s", event.update.update_id, exc_info=exception)
    try:
        if event.update.message is not None:
            await event.update.message.answer(texts.ERROR)
        elif event.update.callback_query is not None:
            await event.update.callback_query.answer(texts.ERROR, show_alert=True)
    except Exception:
        logger.debug("Не удалось сообщить пользователю об ошибке")
    return True

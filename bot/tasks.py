from __future__ import annotations

import asyncio
import logging

from bot.db import now_ts
from bot.services.formatting import format_reminder
from bot.support import Support

logger = logging.getLogger(__name__)


async def check_unanswered(support: Support) -> int:
    minutes = support.config.reminder_minutes
    if minutes <= 0:
        return 0
    now = now_ts()
    threshold = now - minutes * 60
    tickets = await support.db.tickets_awaiting(threshold, threshold)
    if not tickets:
        return 0
    users = await support.db.users_map(ticket["user_id"] for ticket in tickets)
    await support.broadcast(format_reminder(tickets, users, now, minutes))
    await support.db.mark_reminded([ticket["id"] for ticket in tickets], now)
    return len(tickets)


async def reminder_loop(support: Support) -> None:
    interval = max(support.config.reminder_check_seconds, 5)
    logger.info(
        "Напоминания операторам: проверка каждые %s с, порог %s мин", interval, support.config.reminder_minutes
    )
    while True:
        await asyncio.sleep(interval)
        try:
            count = await check_unanswered(support)
            if count:
                logger.info("Напоминание отправлено: %d обращений без ответа", count)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Ошибка в задаче напоминаний")

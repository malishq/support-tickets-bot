from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import Config, load_config
from bot.db import Database
from bot.handlers import client, errors, operator, operator_commands
from bot.middlewares import AccessMiddleware
from bot.setup import register_bot_meta
from bot.support import Support
from bot.tasks import reminder_loop

logger = logging.getLogger("support-bot")


async def on_startup(bot: Bot, dispatcher: Dispatcher, support: Support, config: Config) -> None:
    await register_bot_meta(bot, config)
    dispatcher["reminder_task"] = asyncio.create_task(reminder_loop(support))
    me = await bot.get_me()
    logger.info("Бот @%s запущен, операторов: %d", me.username, len(config.operator_ids))


async def on_shutdown(dispatcher: Dispatcher, db: Database) -> None:
    task = dispatcher.workflow_data.get("reminder_task")
    if task is not None:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    await db.close()
    logger.info("Бот остановлен")


def build_dispatcher(config: Config, db: Database, bot: Bot) -> Dispatcher:
    support = Support(bot, db, config)
    dp = Dispatcher(storage=MemoryStorage())
    dp["config"] = config
    dp["db"] = db
    dp["support"] = support
    dp.message.outer_middleware(AccessMiddleware(db, config))
    dp.callback_query.outer_middleware(AccessMiddleware(db, config))
    dp.include_routers(errors.router, operator_commands.router, operator.router, client.router)
    return dp


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config()
    db = Database(config.db_path, config.first_ticket_number)
    await db.connect()
    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher(config, db, bot)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass

# main.py
# Точка входа: БД → бот → диспетчер → роутеры → polling.

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import Config
from database import init_db
from handlers import start as start_handlers
from handlers import common as common_handlers
from games import GAMES


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()

    bot = Bot(
        token=Config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Порядок важен: common ловит "Меню" и заглушки игр.
    # Роутеры конкретных игр регистрируются раньше — если они есть.
    for game in GAMES:
        if game.router is not None:
            dp.include_router(game.router)
            logger.info("Игра подключена: %s", game.id)

    dp.include_router(common_handlers.router)
    dp.include_router(start_handlers.router)

    logger.info("Бот запущен. Polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен") 
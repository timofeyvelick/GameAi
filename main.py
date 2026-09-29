# main.py
# Точка входа. Здесь мы:
#   1) инициализируем БД
#   2) поднимаем бота и диспетчер
#   3) регистрируем все роутеры (общие + игры)
#   4) запускаем long-polling

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


# Логи в stdout — увидим, что происходит в консоли.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    # 1. База данных
    await init_db()

    # 2. Бот и диспетчер
    bot = Bot(
        token=Config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # 3. Регистрируем общие обработчики.
    # ВАЖНО: порядок важен — common (кнопки «Меню») должен ловить раньше игр.
    dp.include_router(common_handlers.router)
    dp.include_router(start_handlers.router)

    # 4. Регистрируем роутеры игр (пока у всех router=None).
    for game in GAMES:
        if game.router is not None:
            dp.include_router(game.router)
            logger.info("Игра подключена: %s", game.id)

    # 5. Запуск. Пропускаем накопившиеся апдейты — чтобы бот не отвечал
    # на старое, пока мы спали.
    logger.info("Бот запущен. Polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
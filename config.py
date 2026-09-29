# config.py
# Здесь мы читаем настройки из файла .env и делаем их доступными всему проекту.

import os
from dotenv import load_dotenv

# Загружаем переменные из .env в окружение процесса.
# После этой строки os.getenv("BOT_TOKEN") вернёт значение из .env.
load_dotenv()


class Config:
    """Простой контейнер для настроек. Обращаться будем как Config.BOT_TOKEN."""

    # --- Telegram ---
    # Токен бота от @BotFather. Если пусто — бот не запустится.
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # --- LLM (LLM7.io) ---
    # Ключ можно оставить "unused" — LLM7 не проверяет его для бесплатного тарифа.
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "unused")
    # Адрес OpenAI-совместимого API. Меняешь только если переедешь на другой провайдер.
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.llm7.io/v1")
    # Модель. "fast" — самая шустрая бесплатная у LLM7.
    MODEL: str = os.getenv("MODEL", "fast")

    # --- База данных ---
    # Файл SQLite будет лежать рядом с main.py.
    DB_PATH: str = os.getenv("DB_PATH", "gamebot.db")


# Небольшая проверка: если токена нет — сразу говорим об этом,
# чтобы не искать ошибку в дебрях aiogram.
if not Config.BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не задан. Открой .env и впиши токен от @BotFather."
    )
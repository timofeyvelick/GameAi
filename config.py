# config.py
# Читаем настройки из .env и делаем их доступными всему проекту.

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Контейнер настроек. Использовать как Config.BOT_TOKEN."""

    # --- Telegram ---
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # --- LLM (LLM7.io) ---
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "unused")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.llm7.io/v1")
    MODEL: str = os.getenv("MODEL", "fast")

    # --- База данных ---
    DB_PATH: str = os.getenv("DB_PATH", "gamebot.db")


if not Config.BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не задан. Открой .env и впиши токен от @BotFather."
    )
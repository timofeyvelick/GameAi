# database.py
# Слой работы с SQLite. Все обращения к БД идут через этот файл.

import json
import logging
from typing import Optional

import aiosqlite

from config import Config

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Создать таблицы, если их ещё нет. Вызывается один раз при старте бота."""
    async with aiosqlite.connect(Config.DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id       INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                tg_id       INTEGER NOT NULL,
                game        TEXT    NOT NULL,
                wins        INTEGER NOT NULL DEFAULT 0,
                losses      INTEGER NOT NULL DEFAULT 0,
                draws       INTEGER NOT NULL DEFAULT 0,
                played      INTEGER NOT NULL DEFAULT 0,
                last_played TEXT,
                PRIMARY KEY (tg_id, game)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                tg_id       INTEGER PRIMARY KEY,
                game        TEXT    NOT NULL,
                state_json  TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)

        await db.commit()
        logger.info("БД инициализирована: %s", Config.DB_PATH)


async def get_or_create_user(tg_id: int, username: str = "", first_name: str = "") -> None:
    """Если юзера нет — создать. Если есть — обновить имя/username."""
    async with aiosqlite.connect(Config.DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (tg_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(tg_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name
        """, (tg_id, username or "", first_name or ""))
        await db.commit()


async def record_result(tg_id: int, game: str, result: str) -> None:
    """result: 'win' | 'loss' | 'draw'"""
    if result not in ("win", "loss", "draw"):
        raise ValueError(f"Неизвестный результат: {result}")

    column = {"win": "wins", "loss": "losses", "draw": "draws"}[result]

    async with aiosqlite.connect(Config.DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO stats (tg_id, game) VALUES (?, ?)
        """, (tg_id, game))

        await db.execute(f"""
            UPDATE stats
               SET {column}    = {column} + 1,
                   played      = played + 1,
                   last_played = datetime('now')
             WHERE tg_id = ? AND game = ?
        """, (tg_id, game))

        await db.commit()


async def get_stats(tg_id: int) -> list[dict]:
    """Вернуть список словарей со статистикой по всем играм юзера."""
    async with aiosqlite.connect(Config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT game, wins, losses, draws, played, last_played
              FROM stats
             WHERE tg_id = ?
             ORDER BY played DESC
        """, (tg_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def set_session(tg_id: int, game: str, state: dict) -> None:
    """Сохранить (или перезаписать) состояние активной игры."""
    async with aiosqlite.connect(Config.DB_PATH) as db:
        await db.execute("""
            INSERT INTO sessions (tg_id, game, state_json, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(tg_id) DO UPDATE SET
                game       = excluded.game,
                state_json = excluded.state_json,
                updated_at = datetime('now')
        """, (tg_id, game, json.dumps(state, ensure_ascii=False)))
        await db.commit()


async def get_session(tg_id: int) -> Optional[dict]:
    """Вернуть {'game': ..., 'state': {...}} или None."""
    async with aiosqlite.connect(Config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT game, state_json FROM sessions WHERE tg_id = ?", (tg_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return {"game": row["game"], "state": json.loads(row["state_json"])}


async def clear_session(tg_id: int) -> None:
    """Удалить активную сессию."""
    async with aiosqlite.connect(Config.DB_PATH) as db:
        await db.execute("DELETE FROM sessions WHERE tg_id = ?", (tg_id,))
        await db.commit()
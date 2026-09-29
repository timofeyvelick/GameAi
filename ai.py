# ai.py
# Единая точка вызова ИИ. Все игры дёргают только эту функцию.
# Так мы гарантируем: один клиент, один формат, одна обработка ошибок.

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from config import Config

logger = logging.getLogger(__name__)

# Создаём клиент один раз при импорте модуля.
# AsyncOpenAI — асинхронный клиент, чтобы не блокировать бота, пока ИИ думает.
client = AsyncOpenAI(
    api_key=Config.OPENAI_API_KEY,
    base_url=Config.OPENAI_BASE_URL,
)


class AIError(Exception):
    """Своя ошибка, чтобы ловить её в играх одним except."""


def _clean_json(text: str) -> str:
    """Убирает ```json ... ``` обёртку, если модель её добавила."""
    text = text.strip()
    if text.startswith("```"):
        # Отрезаем первую строку (```json или ```) и последние ```.
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


async def ask_ai(
    system: str,
    user: str,
    *,
    json_mode: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> Any:
    """
    Отправить один запрос в LLM.

    :param system: системный промпт — кто такой ИИ (характер, роль, правила).
    :param user:   пользовательский промпт — что именно надо сделать сейчас.
    :param json_mode: если True — распарсит ответ как JSON и вернёт dict/list.
    :param temperature: 0 = скучно и предсказуемо, 1 = креативно и рандомно.
    :param max_tokens: лимит длины ответа.

    Возвращает: строку (обычный режим) или dict/list (json_mode=True).

    Ошибки: если что-то не так с API или JSON — поднимет AIError.
    """
    try:
        resp = await client.chat.completions.create(
            model=Config.MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        logger.exception("LLM запрос упал")
        raise AIError(f"Ошибка при обращении к ИИ: {e}") from e

    text = resp.choices[0].message.content or ""

    if json_mode:
        try:
            return json.loads(_clean_json(text))
        except json.JSONDecodeError as e:
            logger.warning("ИИ вернул не-JSON: %s", text[:300])
            raise AIError("ИИ вернул некорректный JSON") from e

    return text.strip()


async def ask_ai_json(system: str, user: str, **kwargs) -> dict:
    """
    Удобная обёртка: всегда ждём dict.
    Если ИИ вернул не-dict — кидаем AIError.
    """
    data = await ask_ai(system, user, json_mode=True, **kwargs)
    if not isinstance(data, dict):
        raise AIError("Ожидался JSON-объект, пришёл другой тип")
    return data
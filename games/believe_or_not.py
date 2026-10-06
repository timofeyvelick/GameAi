# games/believe_or_not.py
# Игра «Верю / не верю»: ИИ придумывает факт — правдивый или ложный.
# Игрок решает, верить или нет.

import logging
import random

from aiogram import Router, F
from aiogram.types import CallbackQuery

from ai import ask_ai_json, AIError

logger = logging.getLogger(__name__)

router = Router(name="believe")

GAME_ID = "believe_or_not"
ROUNDS = 7

# Темы, чтобы факты не повторялись и были разнообразными
TOPICS = [
    "животные", "история", "космос", "география", "наука",
    "спорт", "искусство", "кулинария", "изобретения", "океаны",
]


async def ai_generate_fact(topic: str) -> dict:
    """
    Сгенерировать факт — правдивый или ложный (50/50).
    Возвращаем {'text': '...', 'is_true': True/False, 'explanation': '...'}
    """
    make_true = random.choice([True, False])

    system = (
        "Ты ведущий игры «Верю / не верю». Генерируешь короткие факты — "
        "на русском. Отвечай СТРОГО валидным JSON без markdown-обёртки."
    )
    user = (
        f"Тема: {topic}.\n"
        f"Тип факта: {'ПРАВДИВЫЙ' if make_true else 'ЛОЖНЫЙ'}.\n\n"
        f"Правила:\n"
        f"- Одно предложение, до 180 символов.\n"
        f"- Без эмодзи, без вступлений «а вы знали».\n"
        f"{'- Факт должен быть реальным и проверяемым.' if make_true else '- Факт должен быть правдоподобной выдумкой, но НЕ реальным.'}\n"
        f"- В поле explanation коротко объясни, правда это или выдумка и почему.\n\n"
        f'Формат: {{"text": "факт", "is_true": {str(make_true).lower()}, "explanation": "объяснение"}}'
    )

    try:
        data = await ask_ai_json(system, user, temperature=0.9, max_tokens=250)
        return {
            "text": str(data.get("text", "")).strip()[:250],
            "is_true": bool(data.get("is_true", False)),
            "explanation": str(data.get("explanation", "")).strip()[:220],
        }
    except AIError as e:
        logger.warning("BELIEVE: ИИ упал, fallback. %s", e)
        # Фолбэк — простой реальный факт
        return {
            "text": "У осьминога три сердца.",
            "is_true": True,
            "explanation": "Это реальный факт из биологии.",
        }


def header_text(round_no: int, score: int) -> str:
    return (
        f"<b>Верю / не верю</b>\n"
        f"Раунд {round_no} / {ROUNDS} · угадано: {score}\n\n"
    )


def fact_text(fact: dict) -> str:
    return f"📢 <b>Факт:</b>\n\n<i>{fact['text']}</i>\n\nВеришь?"


@router.callback_query(F.data == f"start_game:{GAME_ID}")
async def start_believe(call: CallbackQuery) -> None:
    from keyboards import yes_no_kb
    from database import set_session

    topic = random.choice(TOPICS)
    fact = await ai_generate_fact(topic)

    await set_session(call.from_user.id, GAME_ID, {
        "round": 1,
        "score": 0,
        "fact": fact,
        "used_topics": [topic],
    })

    await call.message.edit_text(
        header_text(1, 0) + fact_text(fact),
        reply_markup=yes_no_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("believe:"))
async def handle_answer(call: CallbackQuery) -> None:
    from keyboards import yes_no_kb, next_round_kb, back_to_menu_kb
    from database import get_session, set_session, clear_session, record_result

    answer = call.data.split(":", 1)[1]  # "yes" | "no"
    user_believes = (answer == "yes")

    sess = await get_session(call.from_user.id)
    if not sess or sess["game"] != GAME_ID:
        await call.message.edit_text(
            "Сессия потерялась. Начни игру заново из меню.",
            reply_markup=back_to_menu_kb(),
        )
        await call.answer()
        return

    state = sess["state"]
    fact = state["fact"]
    round_no = state["round"]
    score = state["score"]
    used_topics = state["used_topics"]

    # Игрок угадал, если его ответ совпал с реальностью факта
    correct = (user_believes == fact["is_true"])
    if correct:
        score += 1

    mark = "🎯" if correct else "💀"
    truth_label = "правда" if fact["is_true"] else "выдумка"

    result_text = (
        header_text(round_no, score)
        + fact_text(fact)
        + f"\n\n{mark} <b>{'Верно!' if correct else 'Мимо.'}</b> "
          f"Это была <b>{truth_label}</b>.\n"
        f"<i>{fact['explanation']}</i>\n\n"
        f"Счёт: <b>{score}</b> из {round_no}"
    )

    # Финал
    if round_no >= ROUNDS:
        await clear_session(call.from_user.id)
        if score >= 6:
            medal = "🏆 Отличная интуиция."
            await record_result(call.from_user.id, GAME_ID, "win")
        elif score >= 4:
            medal = "👍 Неплохо."
            await record_result(call.from_user.id, GAME_ID, "draw")
        else:
            medal = "🙃 Слабовато, тренируйся."
            await record_result(call.from_user.id, GAME_ID, "loss")

        await call.message.edit_text(
            f"{result_text}\n\n{medal}\nИтог: <b>{score} / {ROUNDS}</b>.",
            reply_markup=next_round_kb(GAME_ID),
        )
        await call.answer()
        return

    # Следующий раунд — новая тема
    available = [t for t in TOPICS if t not in used_topics] or TOPICS
    topic = random.choice(available)
    new_fact = await ai_generate_fact(topic)
    used_topics.append(topic)

    state["round"] = round_no + 1
    state["score"] = score
    state["fact"] = new_fact
    state["used_topics"] = used_topics
    await set_session(call.from_user.id, GAME_ID, state)

    # Сначала показываем результат прошлого раунда
    await call.message.edit_text(result_text, reply_markup=None)
    # Затем присылаем новый факт НОВЫМ сообщением
    await call.message.answer(
        header_text(round_no + 1, score) + fact_text(new_fact),
        reply_markup=yes_no_kb(),
    )
    await call.answer()

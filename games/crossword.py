# games/crossword.py
# Игра «Кроссворд»: ИИ генерирует мини-кроссворд по теме.

import logging
import random

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from ai import ask_ai_json, AIError
from states import CrosswordStates

logger = logging.getLogger(__name__)

router = Router(name="crossword")

GAME_ID = "crossword"
ROUNDS = 5

TOPICS = ["космос", "животные", "еда", "спорт", "история", "музыка"]

FALLBACK_QUESTIONS = [
    {"q": "Спутник Земли", "a": "луна"},
    {"q": "Красная планета", "a": "марс"},
    {"q": "Король зверей", "a": "лев"},
    {"q": "Столица России", "a": "москва"},
    {"q": "Кислый жёлтый фрукт", "a": "лимон"},
]


async def ai_questions(topic: str, count: int) -> list:
    system = (
        "Ты составляешь кроссворд. Отвечай СТРОГО валидным JSON без "
        "markdown-обёртки, на русском."
    )
    user = (
        f"Тема: {topic}. Придумай {count} вопросов для кроссворда. "
        f"Ответы — существительные в именительном падеже, единственном числе, "
        f"без пробелов (одно слово).\n\n"
        f'Формат: {{"items": [{{"q": "вопрос", "a": "ответ"}}, ...]}}'
    )
    try:
        data = await ask_ai_json(system, user, temperature=0.8, max_tokens=500)
        items = data.get("items", [])
        if not isinstance(items, list) or len(items) < 2:
            raise AIError("Мало вопросов")
        cleaned = []
        for it in items[:count]:
            q = str(it.get("q", "")).strip()
            a = str(it.get("a", "")).strip().lower().replace(" ", "")
            if q and a:
                cleaned.append({"q": q, "a": a})
        if len(cleaned) < 2:
            raise AIError("После очистки мало вопросов")
        return cleaned
    except AIError as e:
        logger.warning("CROSSWORD: ИИ упал, fallback. %s", e)
        return random.sample(FALLBACK_QUESTIONS, min(count, len(FALLBACK_QUESTIONS)))


@router.callback_query(F.data == f"start_game:{GAME_ID}")
async def start_crossword(call: CallbackQuery, state: FSMContext) -> None:
    from keyboards import back_to_menu_kb
    from database import set_session

    topic = random.choice(TOPICS)
    items = await ai_questions(topic, ROUNDS)

    await set_session(call.from_user.id, GAME_ID, {
        "topic": topic,
        "items": items,
        "index": 0,
        "score": 0,
    })
    await state.set_state(CrosswordStates.answering)

    first = items[0]
    await call.message.edit_text(
        f"<b>Кроссворд</b> · тема: <i>{topic}</i>\n"
        f"Вопрос 1 / {len(items)} · угадано: 0\n\n"
        f"❓ <b>{first['q']}</b>\n"
        f"({len(first['a'])} букв)\n\n"
        f"Напиши ответ.",
        reply_markup=back_to_menu_kb(),
    )
    await call.answer()


@router.message(CrosswordStates.answering, F.text)
async def handle_crossword(message: Message, state: FSMContext) -> None:
    from keyboards import next_round_kb, back_to_menu_kb
    from database import get_session, set_session, clear_session, record_result

    answer = (message.text or "").strip().lower().replace(" ", "")
    if not answer:
        return

    sess = await get_session(message.from_user.id)
    if not sess or sess["game"] != GAME_ID:
        await state.clear()
        await message.answer("Сессия потерялась.", reply_markup=back_to_menu_kb())
        return

    st = sess["state"]
    items = st["items"]
    index = st["index"]
    score = st["score"]
    topic = st["topic"]

    current = items[index]
    correct = answer == current["a"]
    if correct:
        score += 1

    mark = "✅" if correct else "❌"
    result = f"{mark} <b>{'Верно!' if correct else 'Неверно.'}</b> Ответ: <b>{current['a']}</b>"

    if index + 1 >= len(items):
        await clear_session(message.from_user.id)
        await state.clear()
        if score >= 4:
            medal = "🏆 Отлично!"
            await record_result(message.from_user.id, GAME_ID, "win")
        elif score >= 2:
            medal = "👍 Средне."
            await record_result(message.from_user.id, GAME_ID, "draw")
        else:
            medal = "🙃 Слабовато."
            await record_result(message.from_user.id, GAME_ID, "loss")
        await message.answer(
            f"{result}\n\n{medal}\nИтог: <b>{score} / {len(items)}</b>",
            reply_markup=next_round_kb(GAME_ID),
        )
        return

    next_item = items[index + 1]
    st["index"] = index + 1
    st["score"] = score
    await set_session(message.from_user.id, GAME_ID, st)

    await message.answer(result, reply_markup=back_to_menu_kb())
    await message.answer(
        f"<b>Кроссворд</b> · тема: <i>{topic}</i>\n"
        f"Вопрос {index + 2} / {len(items)} · угадано: {score}\n\n"
        f"❓ <b>{next_item['q']}</b>\n"
        f"({len(next_item['a'])} букв)",
        reply_markup=back_to_menu_kb(),
    )

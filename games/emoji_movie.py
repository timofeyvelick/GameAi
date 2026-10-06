# games/emoji_movie.py
# Игра «Фильм по эмодзи»: ИИ шифрует фильм эмодзи, игрок угадывает.

import logging
import random

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from ai import ask_ai_json, AIError
from states import EmojiMovieStates

logger = logging.getLogger(__name__)

router = Router(name="emoji_movie")

GAME_ID = "emoji_movie"
ROUNDS = 5

FALLBACK_MOVIES = [
    {"emoji": "🦁👑🌍", "title": "Король Лев", "fact": "Мультфильм 1994 года, один из самых кассовых в истории Disney."},
    {"emoji": "🚢❄️💔", "title": "Титаник", "fact": "Фильм получил 11 «Оскаров», включая «Лучший фильм»."},
    {"emoji": "🕷️🧑‍🦱🏙️", "title": "Человек-паук", "fact": "Первый фильм вышел в 2002 году с Тоби Магуайром в главной роли."},
    {"emoji": "🔴🔵💊🕶️", "title": "Матрица", "fact": "Сцена с красной и синей таблеткой стала культурным мемом."},
    {"emoji": "🧙‍♂️💍🌋", "title": "Властелин колец", "fact": "Трилогия снималась в Новой Зеландии почти 8 лет."},
]


async def ai_new_round(used_titles: list) -> dict:
    system = (
        "Ты ведущий игры «Угадай фильм по эмодзи». Отвечай СТРОГО "
        "валидным JSON без markdown-обёртки, на русском."
    )
    user = (
        f"Зашифруй известный фильм 3-5 эмодзи и придумай короткий факт о нём. "
        f"Не используй фильмы: {', '.join(used_titles) if used_titles else '—'}.\n\n"
        f'Формат: {{"emoji": "🔴🔵💊", "title": "Матрица", "fact": "короткий факт"}}'
    )
    try:
        data = await ask_ai_json(system, user, temperature=0.9, max_tokens=180)
        return {
            "emoji": str(data.get("emoji", "")).strip()[:60],
            "title": str(data.get("title", "")).strip()[:80],
            "fact": str(data.get("fact", "")).strip()[:220],
        }
    except AIError as e:
        logger.warning("EMOJI: ИИ упал, fallback. %s", e)
        available = [m for m in FALLBACK_MOVIES if m["title"] not in used_titles] or FALLBACK_MOVIES
        return random.choice(available)


@router.callback_query(F.data == f"start_game:{GAME_ID}")
async def start_emoji(call: CallbackQuery, state: FSMContext) -> None:
    from keyboards import back_to_menu_kb
    from database import set_session

    round_data = await ai_new_round([])

    await set_session(call.from_user.id, GAME_ID, {
        "round": 1,
        "score": 0,
        "current": round_data,
        "used_titles": [round_data["title"]],
    })
    await state.set_state(EmojiMovieStates.guessing)

    await call.message.edit_text(
        f"<b>Фильм по эмодзи</b>\nРаунд 1 / {ROUNDS}\n\n"
        f"<b>{round_data['emoji']}</b>\n\n"
        f"Что это за фильм? Напиши название.",
        reply_markup=back_to_menu_kb(),
    )
    await call.answer()


@router.message(EmojiMovieStates.guessing, F.text)
async def handle_guess(message: Message, state: FSMContext) -> None:
    from keyboards import next_round_kb, back_to_menu_kb
    from database import get_session, set_session, clear_session, record_result

    guess = (message.text or "").strip().lower()
    if not guess or len(guess) > 80:
        return

    sess = await get_session(message.from_user.id)
    if not sess or sess["game"] != GAME_ID:
        await state.clear()
        await message.answer("Сессия потерялась. Начни игру заново из меню.", reply_markup=back_to_menu_kb())
        return

    st = sess["state"]
    current = st["current"]
    round_no = st["round"]
    score = st["score"]
    used_titles = st["used_titles"]

    real = current["title"].lower()
    correct = guess == real or guess in real or real in guess
    if correct:
        score += 1

    mark = "🎯" if correct else "❌"
    result = (
        f"{mark} <b>{'Верно!' if correct else 'Не угадал.'}</b>\n"
        f"Ответ: <b>{current['title']}</b>\n"
        f"<i>{current['fact']}</i>\n"
    )

    if round_no >= ROUNDS:
        await clear_session(message.from_user.id)
        await state.clear()
        if score >= 4:
            medal = "🏆 Отличный результат."
            await record_result(message.from_user.id, GAME_ID, "win")
        elif score >= 2:
            medal = "👍 Средне."
            await record_result(message.from_user.id, GAME_ID, "draw")
        else:
            medal = "🙃 Слабовато."
            await record_result(message.from_user.id, GAME_ID, "loss")
        await message.answer(
            f"{result}\n{medal}\nИтог: <b>{score} / {ROUNDS}</b>",
            reply_markup=next_round_kb(GAME_ID),
        )
        return

    next_round = await ai_new_round(used_titles)
    used_titles.append(next_round["title"])

    st["round"] = round_no + 1
    st["score"] = score
    st["current"] = next_round
    st["used_titles"] = used_titles
    await set_session(message.from_user.id, GAME_ID, st)

    await message.answer(result, reply_markup=back_to_menu_kb())
    await message.answer(
        f"<b>Фильм по эмодзи</b>\nРаунд {round_no + 1} / {ROUNDS}\n\n"
        f"<b>{next_round['emoji']}</b>\n\n"
        f"Что это за фильм?",
        reply_markup=back_to_menu_kb(),
    )

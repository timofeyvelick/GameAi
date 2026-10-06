# games/guess_word.py
# Игра «Угадай слово по буквам»: ИИ загадывает слово, игрок открывает буквы.

import logging
import random

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from ai import ask_ai_json, AIError
from states import GuessWordStates

logger = logging.getLogger(__name__)

router = Router(name="guess_word")

GAME_ID = "guess_word"
MAX_MISTAKES = 6

FALLBACK_WORDS = [
    {"word": "космос", "hint": "там летают ракеты"},
    {"word": "ёжик", "hint": "колючий зверёк"},
    {"word": "пират", "hint": "ищет клады"},
    {"word": "море", "hint": "большое и солёное"},
    {"word": "книга", "hint": "источник знаний"},
]


async def ai_new_word(used: list) -> dict:
    system = (
        "Ты ведущий игры «Угадай слово по буквам». Отвечай СТРОГО "
        "валидным JSON без markdown-обёртки, на русском."
    )
    user = (
        f"Загадай русское существительное (4-8 букв, без дефиса). "
        f"Не используй: {', '.join(used) if used else '—'}.\n"
        f"Дай короткую подсказку одним предложением.\n\n"
        f'Формат: {{"word": "космос", "hint": "там летают ракеты"}}'
    )
    try:
        data = await ask_ai_json(system, user, temperature=0.9, max_tokens=120)
        word = str(data.get("word", "")).strip().lower()
        hint = str(data.get("hint", "")).strip()[:180]
        if not word or not word.isalpha() or word in used:
            raise AIError("Некорректное слово")
        return {"word": word, "hint": hint}
    except AIError as e:
        logger.warning("GUESS: ИИ упал, fallback. %s", e)
        available = [w for w in FALLBACK_WORDS if w["word"] not in used] or FALLBACK_WORDS
        return random.choice(available)


def render_word(word: str, opened: set) -> str:
    return " ".join(c if c in opened else "•" for c in word)


@router.callback_query(F.data == f"start_game:{GAME_ID}")
async def start_guess(call: CallbackQuery, state: FSMContext) -> None:
    from keyboards import back_to_menu_kb
    from database import set_session

    data = await ai_new_word([])

    await set_session(call.from_user.id, GAME_ID, {
        "word": data["word"],
        "hint": data["hint"],
        "opened": [],
        "mistakes": 0,
        "used_words": [data["word"]],
    })
    await state.set_state(GuessWordStates.waiting_letter)

    await call.message.edit_text(
        f"<b>Угадай слово</b>\n\n"
        f"Подсказка: <i>{data['hint']}</i>\n\n"
        f"<code>{render_word(data['word'], set())}</code>\n"
        f"Букв: {len(data['word'])} · Ошибок: 0 / {MAX_MISTAKES}\n\n"
        f"Напиши букву или слово целиком.",
        reply_markup=back_to_menu_kb(),
    )
    await call.answer()


@router.message(GuessWordStates.waiting_letter, F.text)
async def handle_letter(message: Message, state: FSMContext) -> None:
    from keyboards import next_round_kb, back_to_menu_kb
    from database import get_session, set_session, clear_session, record_result

    text = (message.text or "").strip().lower()
    if not text:
        return

    sess = await get_session(message.from_user.id)
    if not sess or sess["game"] != GAME_ID:
        await state.clear()
        await message.answer("Сессия потерялась.", reply_markup=back_to_menu_kb())
        return

    st = sess["state"]
    word = st["word"]
    opened = set(st["opened"])
    mistakes = st["mistakes"]
    used_words = st["used_words"]

    # Полное слово
    if len(text) > 1:
        if text == word:
            await clear_session(message.from_user.id)
            await state.clear()
            await record_result(message.from_user.id, GAME_ID, "win")
            await message.answer(
                f"🏆 <b>Угадал!</b>\n\nСлово: <b>{word}</b>",
                reply_markup=next_round_kb(GAME_ID),
            )
            return
        mistakes += 1
        if mistakes >= MAX_MISTAKES:
            await clear_session(message.from_user.id)
            await state.clear()
            await record_result(message.from_user.id, GAME_ID, "loss")
            await message.answer(
                f"💀 <b>Попытки кончились.</b>\n\nСлово было: <b>{word}</b>",
                reply_markup=next_round_kb(GAME_ID),
            )
            return
        await message.answer(f"❌ Не то слово. Ошибок: {mistakes} / {MAX_MISTAKES}")
        st["mistakes"] = mistakes
        await set_session(message.from_user.id, GAME_ID, st)
        return

    # Одна буква
    letter = text[0]
    if letter in opened:
        await message.answer("Эту букву ты уже открывал.")
        return
    if letter in word:
        opened.update(i for i, c in enumerate(word) if c == letter)
        # Проверка на победу
        if all(i in opened for i in range(len(word))):
            await clear_session(message.from_user.id)
            await state.clear()
            await record_result(message.from_user.id, GAME_ID, "win")
            await message.answer(
                f"🏆 <b>Угадал!</b>\n\nСлово: <b>{word}</b>",
                reply_markup=next_round_kb(GAME_ID),
            )
            return
    else:
        mistakes += 1
        if mistakes >= MAX_MISTAKES:
            await clear_session(message.from_user.id)
            await state.clear()
            await record_result(message.from_user.id, GAME_ID, "loss")
            await message.answer(
                f"💀 <b>Попытки кончились.</b>\n\nСлово было: <b>{word}</b>",
                reply_markup=next_round_kb(GAME_ID),
            )
            return

    st["opened"] = list(opened)
    st["mistakes"] = mistakes
    await set_session(message.from_user.id, GAME_ID, st)

    await message.answer(
        f"<code>{render_word(word, opened)}</code>\n"
        f"Ошибок: {mistakes} / {MAX_MISTAKES}",
    )

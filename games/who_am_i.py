# games/who_am_i.py
# Игра «Кто я?»: ИИ загадывает персонажа, игрок задаёт вопросы и угадывает.

import logging
import random

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from ai import ask_ai_json, AIError
from states import WhoAmIStates

logger = logging.getLogger(__name__)

router = Router(name="who_am_i")

GAME_ID = "who_am_i"
MAX_QUESTIONS = 15

FALLBACK_CHARACTERS = ["Гарри Поттер", "Клеопатра", "Альберт Эйнштейн", "Наполеон", "Мона Лиза"]


async def ai_pick_character() -> dict:
    system = (
        "Ты ведущий игры «Кто я?». Отвечай СТРОГО валидным JSON без "
        "markdown-обёртки, на русском."
    )
    user = (
        f"Загадай известного персонажа или личность. Дай только категорию "
        f"(одно слово: актёр, учёный, персонаж книги, историческая личность и т.п.).\n\n"
        f'Формат: {{"character": "Альберт Эйнштейн", "category": "учёный"}}'
    )
    try:
        data = await ask_ai_json(system, user, temperature=0.9, max_tokens=100)
        return {
            "character": str(data.get("character", "")).strip()[:80],
            "category": str(data.get("category", "")).strip()[:60],
        }
    except AIError as e:
        logger.warning("WHOAMI: ИИ упал, fallback. %s", e)
        return {"character": random.choice(FALLBACK_CHARACTERS), "category": "персонаж"}


async def ai_answer(character: str, question: str) -> str:
    system = (
        "Ты отвечаешь на вопросы игрока в игре «Кто я?». "
        "Отвечай одним словом: да, нет или возможно. JSON без markdown."
    )
    user = (
        f"Загаданный персонаж: «{character}».\n"
        f"Вопрос: «{question}».\n\n"
        f'Формат: {{"answer": "да"}}'
    )
    try:
        data = await ask_ai_json(system, user, temperature=0.3, max_tokens=30)
        ans = str(data.get("answer", "возможно")).strip().lower()
        if ans not in ("да", "нет", "возможно"):
            ans = "возможно"
        return ans
    except AIError as e:
        logger.warning("WHOAMI: ИИ упал на ответе, fallback. %s", e)
        return "возможно"


@router.callback_query(F.data == f"start_game:{GAME_ID}")
async def start_whoami(call: CallbackQuery, state: FSMContext) -> None:
    from keyboards import back_to_menu_kb
    from database import set_session

    data = await ai_pick_character()

    await set_session(call.from_user.id, GAME_ID, {
        "character": data["character"],
        "category": data["category"],
        "asked": 0,
    })
    await state.set_state(WhoAmIStates.asking)

    await call.message.edit_text(
        f"<b>Кто я?</b>\n\n"
        f"Представь, что тебе на лоб наклеили стикер с именем персонажа.\n"
        f"Я знаю, кто это. Категория: <i>{data['category']}</i>.\n\n"
        f"Задавай вопросы («Я реальный человек?», «Я женщина?»), "
        f"я отвечу Да / Нет / Возможно.\n"
        f"Или назови персонажа — если угадаешь, победа.\n\n"
        f"Вопросов осталось: {MAX_QUESTIONS}",
        reply_markup=back_to_menu_kb(),
    )
    await call.answer()


@router.message(WhoAmIStates.asking, F.text)
async def handle_whoami(message: Message, state: FSMContext) -> None:
    from keyboards import next_round_kb, back_to_menu_kb
    from database import get_session, set_session, clear_session, record_result

    text = (message.text or "").strip()
    if not text or len(text) > 200:
        return

    sess = await get_session(message.from_user.id)
    if not sess or sess["game"] != GAME_ID:
        await state.clear()
        await message.answer("Сессия потерялась.", reply_markup=back_to_menu_kb())
        return

    st = sess["state"]
    character = st["character"]
    asked = st["asked"]

    if character.lower() in text.lower():
        await clear_session(message.from_user.id)
        await state.clear()
        await record_result(message.from_user.id, GAME_ID, "win")
        await message.answer(
            f"🏆 <b>Угадал!</b>\n\nЭто был <b>{character}</b>.\nВопросов: {asked}.",
            reply_markup=next_round_kb(GAME_ID),
        )
        return

    await message.answer("Думаю...")
    answer = await ai_answer(character, text)
    asked += 1

    if asked >= MAX_QUESTIONS:
        await clear_session(message.from_user.id)
        await state.clear()
        await record_result(message.from_user.id, GAME_ID, "loss")
        await message.answer(
            f"💀 <b>Вопросы кончились.</b>\n\nЯ загадал: <b>{character}</b>.",
            reply_markup=next_round_kb(GAME_ID),
        )
        return

    st["asked"] = asked
    await set_session(message.from_user.id, GAME_ID, st)

    emoji = {"да": "✅", "нет": "❌", "возможно": "🤔"}.get(answer, "❓")
    await message.answer(
        f"{emoji} <b>{answer.capitalize()}</b>\n\n"
        f"Вопросов осталось: {MAX_QUESTIONS - asked}",
    )

# games/twenty_questions.py
# Игра «20 вопросов»: ИИ загадывает персонажа, игрок угадывает через Да/Нет.

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from ai import ask_ai_json, AIError
from states import TwentyQuestionsStates

logger = logging.getLogger(__name__)

router = Router(name="twenty_questions")

GAME_ID = "twenty_questions"
MAX_QUESTIONS = 20

FALLBACK_CHARACTERS = ["Пушкин", "Юрий Гагарин", "Мерилин Монро", "Леонардо да Винчи", "Шерлок Холмс"]


async def ai_pick_character() -> dict:
    import random
    system = (
        "Ты ведущий игры «20 вопросов». Отвечай СТРОГО валидным JSON "
        "без markdown-обёртки, на русском."
    )
    user = (
        f"Загадай известного персонажа (историческая личность, персонаж книги "
        f"или фильма, учёный, артист). Ответь коротким описанием категории, "
        f"но НЕ называй персонажа.\n\n"
        f'Формат: {{"character": "имя", "category": "реальный человек / персонаж книги / ..."}}'
    )
    try:
        data = await ask_ai_json(system, user, temperature=0.9, max_tokens=120)
        return {
            "character": str(data.get("character", "")).strip()[:80],
            "category": str(data.get("category", "")).strip()[:80],
        }
    except AIError as e:
        logger.warning("20Q: ИИ упал на выборе, fallback. %s", e)
        name = random.choice(FALLBACK_CHARACTERS)
        return {"character": name, "category": "реальный человек"}


async def ai_answer(character: str, question: str) -> str:
    """Ответить на вопрос игрока: 'да' / 'нет' / 'не знаю'."""
    system = (
        "Ты отвечаешь на вопросы в игре «20 вопросов» про загаданного персонажа. "
        "Отвечай СТРОГО одним словом: да, нет или не знаю. "
        "Отвечай валидным JSON без markdown-обёртки."
    )
    user = (
        f"Загаданный персонаж: «{character}».\n"
        f"Вопрос игрока: «{question}».\n\n"
        f'Формат: {{"answer": "да"}}'
    )
    try:
        data = await ask_ai_json(system, user, temperature=0.3, max_tokens=30)
        ans = str(data.get("answer", "не знаю")).strip().lower()
        if ans not in ("да", "нет", "не знаю"):
            ans = "не знаю"
        return ans
    except AIError as e:
        logger.warning("20Q: ИИ упал на ответе, fallback. %s", e)
        return "не знаю"


@router.callback_query(F.data == f"start_game:{GAME_ID}")
async def start_20q(call: CallbackQuery, state: FSMContext) -> None:
    from keyboards import back_to_menu_kb
    from database import set_session

    data = await ai_pick_character()

    await set_session(call.from_user.id, GAME_ID, {
        "character": data["character"],
        "category": data["category"],
        "asked": 0,
        "history": [],
    })
    await state.set_state(TwentyQuestionsStates.asking)

    await call.message.edit_text(
        f"<b>20 вопросов</b>\n\n"
        f"Я загадал персонажа. Категория: <i>{data['category']}</i>.\n\n"
        f"Задавай вопросы, на которые можно ответить «Да / Нет / Не знаю».\n"
        f"Или сразу назови персонажа — если угадаешь, победа.\n\n"
        f"Вопросов осталось: {MAX_QUESTIONS}",
        reply_markup=back_to_menu_kb(),
    )
    await call.answer()


@router.message(TwentyQuestionsStates.asking, F.text)
async def handle_question(message: Message, state: FSMContext) -> None:
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
    history = st["history"]

    # Проверяем, не назвал ли игрок персонажа напрямую
    if character.lower() in text.lower():
        await clear_session(message.from_user.id)
        await state.clear()
        await record_result(message.from_user.id, GAME_ID, "win")
        await message.answer(
            f"🏆 <b>Угадал!</b>\n\nЭто был <b>{character}</b>.\n"
            f"Вопросов задано: {asked}.",
            reply_markup=next_round_kb(GAME_ID),
        )
        return

    await message.answer("Думаю...")
    answer = await ai_answer(character, text)
    asked += 1
    history.append({"q": text, "a": answer})

    if asked >= MAX_QUESTIONS:
        await clear_session(message.from_user.id)
        await state.clear()
        await record_result(message.from_user.id, GAME_ID, "loss")
        await message.answer(
            f"💀 <b>20 вопросов исчерпаны.</b>\n\n"
            f"Я загадал: <b>{character}</b>.",
            reply_markup=next_round_kb(GAME_ID),
        )
        return

    st["asked"] = asked
    st["history"] = history
    await set_session(message.from_user.id, GAME_ID, st)

    emoji = {"да": "✅", "нет": "❌", "не знаю": "🤷"}.get(answer, "❓")
    await message.answer(
        f"{emoji} <b>{answer.capitalize()}</b>\n\n"
        f"Вопросов осталось: {MAX_QUESTIONS - asked}",
    )

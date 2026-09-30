# games/mine_number.py
# Игра «Мина из цифр»: ИИ загадывает число 1–10,
# игрок называет числа, стараясь не попасть в мину.

import logging
import random

from aiogram import Router, F
from aiogram.types import CallbackQuery

from ai import ask_ai, AIError

logger = logging.getLogger(__name__)

router = Router(name="mine")

GAME_ID = "mine_number"
MAX_ATTEMPTS = 5  # если не попал в мину за 5 попыток — победа

PERSONAS = [
    {
        "name": "Спокойный",
        "trait": (
            "Ты спокойный и сдержанный. Подсказки даёшь коротко и по делу: "
            "в какую сторону двигаться, ближе или дальше от мины. "
            "Без пафоса и восклицаний."
        ),
    },
    {
        "name": "Игривый",
        "trait": (
            "Ты с лёгкой усмешкой наблюдаешь за попытками игрока. "
            "Подсказки даёшь коротко, но с ноткой иронии. "
            "Без издёвки и без грубости."
        ),
    },
    {
        "name": "Мрачный",
        "trait": (
            "Ты мрачный и немногословный. Одно короткое предложение с "
            "подсказкой. Не сочувствуешь, но и не издеваешься."
        ),
    },
]


def hint_text(mine: int, guess: int) -> str:
    """
    Детерминированная подсказка: точно говорим, куда двигаться.
    Если игрок угадал — не подсказываем (это конец).
    """
    if guess == mine:
        return ""
    diff = abs(guess - mine)
    if diff == 1:
        return "Огонь рядом."
    if diff <= 3:
        return f"Близко. Мина {('выше' if mine > guess else 'ниже')} {guess}."
    return f"Холодно. Мина {('выше' if mine > guess else 'ниже')} {guess}."


async def ai_comment(persona: dict, mine: int, guess: int, attempts: int) -> str:
    """Просим ИИ прокомментировать ход в характере. Если упал — берём детерминированную подсказку."""
    hint = hint_text(mine, guess)
    if not hint:
        return ""

    system = (
        f"Ты ведёшь игру «Мина из цифр» и общаешься с игроком. "
        f"Твой характер: {persona['trait']} "
        f"Одно короткое предложение до 120 символов, без эмодзи. "
        f"На русском."
    )
    user = (
        f"Игрок назвал число {guess}. Попытка номер {attempts}. "
        f"Мина от него {hint}. "
        f"Скажи ему коротко и в своём характере, куда двигаться дальше. "
        f"Не называй мину."
    )

    try:
        text = await ask_ai(system, user, temperature=0.8, max_tokens=100)
        return text.strip()
    except AIError as e:
        logger.warning("MINE: ИИ упал, fallback hint. %s", e)
        return hint


def header(persona: dict, attempts: int, tried: list) -> str:
    tried_text = ", ".join(str(n) for n in tried) if tried else "—"
    return (
        f"<b>Мина из цифр</b>\n"
        f"Характер ведущего: {persona['name']}\n"
        f"Попыток: {attempts} / {MAX_ATTEMPTS}\n"
        f"Уже называл: {tried_text}\n\n"
        f"Назови число:"
    )


@router.callback_query(F.data == f"start_game:{GAME_ID}")
async def start_mine(call: CallbackQuery) -> None:
    from keyboards import numbers_kb
    from database import set_session

    persona = random.choice(PERSONAS)
    mine = random.randint(1, 10)

    await set_session(call.from_user.id, GAME_ID, {
        "persona": persona,
        "mine": mine,
        "attempts": 0,
        "tried": [],
    })

    await call.message.edit_text(
        f"<b>Мина из цифр</b>\n"
        f"Характер ведущего: {persona['name']}\n\n"
        f"Я загадал число от 1 до 10.\n"
        f"Называй числа — не попади в мину.\n"
        f"У тебя {MAX_ATTEMPTS} попыток.",
        reply_markup=numbers_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("num:"))
async def handle_number(call: CallbackQuery) -> None:
    from keyboards import numbers_kb, next_round_kb, back_to_menu_kb
    from database import get_session, set_session, clear_session, record_result

    guess = int(call.data.split(":", 1)[1])

    sess = await get_session(call.from_user.id)
    if not sess or sess["game"] != GAME_ID:
        await call.message.edit_text(
            "Сессия потерялась. Начни игру заново из меню.",
            reply_markup=back_to_menu_kb(),
        )
        await call.answer()
        return

    state = sess["state"]
    persona = state["persona"]
    mine = state["mine"]
    attempts = state["attempts"]
    tried = state["tried"]

    if guess in tried:
        await call.answer("Это число ты уже называл", show_alert=True)
        return

    tried.append(guess)
    attempts += 1

    # Попал в мину
    if guess == mine:
        await record_result(call.from_user.id, GAME_ID, "loss")
        await clear_session(call.from_user.id)
        await call.message.edit_text(
            f"💣 <b>Бум. Это была мина.</b>\n\n"
            f"Загаданное число: <b>{mine}</b>\n"
            f"Попыток: {attempts}",
            reply_markup=next_round_kb(GAME_ID),
        )
        await call.answer()
        return

    # Попытки кончились — победа игрока
    if attempts >= MAX_ATTEMPTS:
        await record_result(call.from_user.id, GAME_ID, "win")
        await clear_session(call.from_user.id)
        await call.message.edit_text(
            f"🏆 <b>Ты уцелел.</b>\n\n"
            f"Загаданное число: <b>{mine}</b>\n"
            f"Ты не попал в мину за {attempts} попыток.",
            reply_markup=next_round_kb(GAME_ID),
        )
        await call.answer()
        return

    # Играем дальше — ИИ комментирует
    await call.answer("Ведущий думает...")
    comment = await ai_comment(persona, mine, guess, attempts)

    state["attempts"] = attempts
    state["tried"] = tried
    await set_session(call.from_user.id, GAME_ID, state)

    # Новое сообщение с подсказкой
    await call.message.answer(
        f"{comment}\n\n"
        f"Попыток: {attempts} / {MAX_ATTEMPTS}\n"
        f"Уже называл: {', '.join(str(n) for n in tried)}",
        reply_markup=numbers_kb(),
    )
    # В старом сообщении убираем кнопки
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
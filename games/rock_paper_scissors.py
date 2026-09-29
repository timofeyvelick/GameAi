# games/rock_paper_scissors.py
# Игра «Камень-ножницы-бумага» с ИИ-соперником.
#
# ВАЖНО про импорты: keyboards.py импортирует games/__init__.py,
# а games/__init__.py импортирует этот файл. Если импортировать keyboards
# на верхнем уровне — получится циклический импорт.
# Поэтому keyboards и database импортируются ЛОКАЛЬНО внутри функций.

import logging
import random

from aiogram import Router, F
from aiogram.types import CallbackQuery

from ai import ask_ai_json, AIError
from database import record_result

logger = logging.getLogger(__name__)

router = Router(name="rps")

GAME_ID = "rock_paper_scissors"
WINS_NEEDED = 3

BEATS = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
MOVES_RU = {"rock": "камень 🪨", "scissors": "ножницы ✂️", "paper": "бумага 📄"}

PERSONAS = [
    {
        "name": "Злопамятный Гоблин",
        "trait": (
            "ты злопамятный и мстительный. Если игрок тебя обыграл, "
            "ты обязательно упомянешь это в следующем комментарии. "
            "Любишь считать, сколько раз ты проиграл."
        ),
    },
    {
        "name": "Блефующий Барон",
        "trait": (
            "ты блефуешь и запугиваешь. Говоришь, что видишь мысли игрока, "
            "что следующий ход будет решающим, что у тебя есть тайная стратегия."
        ),
    },
    {
        "name": "Ироничный Сфинкс",
        "trait": (
            "ты ироничный и сдержанно-насмешливый. Комментируешь ходы игрока "
            "с лёгкой издёвкой, будто тебе всё равно, но ты явно наслаждаешься процессом."
        ),
    },
]


def who_wins(player: str, ai: str) -> str:
    """Возвращает 'player' | 'ai' | 'draw'."""
    if player == ai:
        return "draw"
    return "player" if BEATS[player] == ai else "ai"


async def ai_pick_move(persona: dict, history: list, score: dict) -> dict:
    """
    Спросить у ИИ ход и комментарий.
    history — список кортежей (ход игрока, ход ИИ).
    Возвращает {'move': ..., 'comment': ...}. Если ИИ упал — fallback на random.
    """
    history_text = "\n".join(
        f"  раунд {i + 1}: игрок — {MOVES_RU[p]}, ты — {MOVES_RU[a]} ({who_wins(p, a)})"
        for i, (p, a) in enumerate(history)
    ) or "  (пока пусто)"

    system = (
        f"Ты играешь в «Камень-ножницы-бумага» против человека. "
        f"Твой характер: {persona['trait']} "
        f"Отвечай СТРОГО валидным JSON без markdown-обёртки, на русском."
    )
    user = (
        f"История партий:\n{history_text}\n\n"
        f"Счёт (победы игрока / твои): {score['player']} / {score['ai']}\n\n"
        f"Сделай свой ход и прокомментируй его в своём характере. "
        f"Ход — строго одно из: rock, scissors, paper.\n\n"
        f"Формат ответа:\n"
        f'{{"move": "rock|scissors|paper", "comment": "короткая фраза, до 200 символов"}}'
    )

    try:
        data = await ask_ai_json(system, user, temperature=0.9, max_tokens=200)
        if data.get("move") not in BEATS:
            raise AIError(f"ИИ прислал недопустимый ход: {data.get('move')}")
        return {"move": data["move"], "comment": data.get("comment", "")[:300]}
    except AIError as e:
        logger.warning("RPS: ИИ упал, fallback random. %s", e)
        return {"move": random.choice(list(BEATS)), "comment": "…"}


def persona_header(persona: dict) -> str:
    return (
        f"🎭 Твой соперник: <b>{persona['name']}</b>\n"
        f"<i>Играем до {WINS_NEEDED} побед.</i>\n\n"
        f"Твой ход?"
    )


@router.callback_query(F.data == f"start_game:{GAME_ID}")
async def start_rps(call: CallbackQuery) -> None:
    # Локальные импорты — чтобы не было циклической зависимости
    from keyboards import rps_kb
    from database import set_session

    persona = random.choice(PERSONAS)

    await set_session(call.from_user.id, GAME_ID, {
        "persona": persona,
        "history": [],
        "score": {"player": 0, "ai": 0},
    })

    await call.message.edit_text(persona_header(persona), reply_markup=rps_kb())
    await call.answer()


@router.callback_query(F.data.startswith("rps:"))
async def handle_move(call: CallbackQuery) -> None:
    # Локальные импорты
    from keyboards import rps_kb, next_round_kb, back_to_menu_kb
    from database import get_session, set_session, clear_session

    player_move = call.data.split(":", 1)[1]
    if player_move not in BEATS:
        await call.answer("Некорректный ход", show_alert=True)
        return

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
    history = state["history"]
    score = state["score"]

    await call.answer("ИИ думает...")

    ai_data = await ai_pick_move(persona, [(h[0], h[1]) for h in history], score)
    ai_move = ai_data["move"]
    comment = ai_data["comment"]

    result = who_wins(player_move, ai_move)
    if result == "player":
        score["player"] += 1
    elif result == "ai":
        score["ai"] += 1

    history.append((player_move, ai_move))

    if result == "player":
        outcome = "🎉 Ты выиграл раунд!"
    elif result == "ai":
        outcome = "💀 ИИ выиграл раунд."
    else:
        outcome = "🤝 Ничья."

    text = (
        f"Ты: {MOVES_RU[player_move]}\n"
        f"ИИ: {MOVES_RU[ai_move]}\n\n"
        f"{outcome}\n"
        f"💬 <i>{comment}</i>\n\n"
        f"Счёт: <b>{score['player']} : {score['ai']}</b> (ты : ИИ)"
    )

    # Финал партии
    if score["player"] >= WINS_NEEDED or score["ai"] >= WINS_NEEDED:
        if score["player"] > score["ai"]:
            final = f"🏆 <b>Ты победил {score['player']}:{score['ai']}!</b>"
            await record_result(call.from_user.id, GAME_ID, "win")
        else:
            final = f"😈 <b>ИИ победил {score['ai']}:{score['player']}.</b>"
            await record_result(call.from_user.id, GAME_ID, "loss")

        text += f"\n\n{final}"
        await call.message.edit_text(text, reply_markup=next_round_kb(GAME_ID))
        await clear_session(call.from_user.id)
        return

    # Играем дальше — сохраняем состояние
    state["history"] = history
    state["score"] = score
    await set_session(call.from_user.id, GAME_ID, state)

    await call.message.edit_text(text + "\n\nТвой ход?", reply_markup=rps_kb())
# games/rock_paper_scissors.py
# Игра «Камень-ножницы-бумага» с ИИ-соперником.

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
        "name": "Злопамятный",
        "trait": (
            "Ты ведёшь счёт проигрышам и всегда помнишь, кто кому проиграл. "
            "Если игрок тебя только что обыграл — напомни об этом в следующей "
            "реплике, коротко и с холодком. Если ты ведёшь — не хвались, "
            "просто дай понять, что заметил."
        ),
    },
    {
        "name": "Блефующий",
        "trait": (
            "Ты любишь делать вид, что просчитал ходы игрока на два шага вперёд. "
            "Иногда угадываешь, иногда откровенно блефуешь — но всегда "
            "уверенным тоном. Если попал — сдержанное «как я и думал», если "
            "нет — «по плану»."
        ),
    },
    {
        "name": "Ироничный",
        "trait": (
            "Ты наблюдаешь за игроком с лёгкой усмешкой. Замечаешь паттерны "
            "в его ходах и комментируешь коротко, с сухим юмором. Без издёвки, "
            "без грубости, но с ощущением, что ты видишь его насквозь."
        ),
    },
]


def who_wins(player: str, ai: str) -> str:
    """Возвращает 'player' | 'ai' | 'draw'."""
    if player == ai:
        return "draw"
    return "player" if BEATS[player] == ai else "ai"


async def ai_pick_move(
    persona: dict,
    last_player_move: str | None,
    history: list,
    score: dict,
) -> dict:
    """
    Спросить у ИИ ход и комментарий.
    last_player_move — ход игрока, на который ИИ сейчас реагирует (или None в самом начале).
    """
    history_text = "\n".join(
        f"  раунд {i + 1}: игрок — {MOVES_RU[p]}, ты — {MOVES_RU[a]} ({who_wins(p, a)})"
        for i, (p, a) in enumerate(history)
    ) or "  (пока пусто)"

    if last_player_move is None:
        last_move_line = "Игрок делает первый ход в этой партии."
    else:
        last_move_line = (
            f"Только что игрок сыграл: {MOVES_RU[last_player_move]}."
        )

    system = (
        f"Ты играешь в «Камень-ножницы-бумага» против человека. "
        f"Твой характер: {persona['trait']} "
        f"Комментарий — 1 или 2 коротких предложения, до 180 символов. "
        f"Без восклицаний, без пафоса, без эмодзи, без обращения на «вы». "
        f"Отвечай СТРОГО валидным JSON без markdown-обёртки, на русском."
    )
    user = (
        f"История раундов:\n{history_text}\n\n"
        f"{last_move_line}\n"
        f"Счёт (ты / игрок): {score['ai']} / {score['player']}\n\n"
        f"Выбери свой ход и дай короткий комментарий, который опирается на "
        f"конкретный последний ход игрока. Не выдумывай ходы, которых не было. "
        f"Ход — строго одно из: rock, scissors, paper.\n\n"
        f"Формат ответа:\n"
        f'{{"move": "rock|scissors|paper", "comment": "короткая фраза"}}'
    )

    try:
        data = await ask_ai_json(system, user, temperature=0.9, max_tokens=220)
        if data.get("move") not in BEATS:
            raise AIError(f"ИИ прислал недопустимый ход: {data.get('move')}")
        return {"move": data["move"], "comment": data.get("comment", "")[:280]}
    except AIError as e:
        logger.warning("RPS: ИИ упал, fallback random. %s", e)
        return {"move": random.choice(list(BEATS)), "comment": "…"}


def persona_header(persona: dict) -> str:
    return (
        f"<b>{persona['name']}</b>\n"
        f"До {WINS_NEEDED} побед.\n\n"
        f"Твой ход:"
    )


@router.callback_query(F.data == f"start_game:{GAME_ID}")
async def start_rps(call: CallbackQuery) -> None:
    from keyboards import rps_kb
    from database import set_session

    persona = random.choice(PERSONAS)

    await set_session(call.from_user.id, GAME_ID, {
        "persona": persona,
        "history": [],
        "score": {"player": 0, "ai": 0},
        "last_player_move": None,
    })

    await call.message.edit_text(persona_header(persona), reply_markup=rps_kb())
    await call.answer()


@router.callback_query(F.data.startswith("rps:"))
async def handle_move(call: CallbackQuery) -> None:
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
    last_player_move = state.get("last_player_move")

    await call.answer("ИИ думает...")

    ai_data = await ai_pick_move(persona, last_player_move, history, score)
    ai_move = ai_data["move"]
    comment = ai_data["comment"]

    result = who_wins(player_move, ai_move)
    if result == "player":
        score["player"] += 1
    elif result == "ai":
        score["ai"] += 1

    history.append((player_move, ai_move))

    if result == "player":
        outcome = "Раунд за тобой."
    elif result == "ai":
        outcome = "Раунд за ИИ."
    else:
        outcome = "Ничья."

    text = (
        f"Ты: {MOVES_RU[player_move]}\n"
        f"ИИ: {MOVES_RU[ai_move]}\n\n"
        f"<b>{outcome}</b>\n"
        f"<i>{comment}</i>\n\n"
        f"Счёт: <b>{score['player']} : {score['ai']}</b>"
    )

    if score["player"] >= WINS_NEEDED or score["ai"] >= WINS_NEEDED:
        if score["player"] > score["ai"]:
            final = f"<b>Ты победил {score['player']}:{score['ai']}.</b>"
            await record_result(call.from_user.id, GAME_ID, "win")
        else:
            final = f"<b>ИИ победил {score['ai']}:{score['player']}.</b>"
            await record_result(call.from_user.id, GAME_ID, "loss")

        text += f"\n\n{final}"
        await call.message.edit_text(text, reply_markup=next_round_kb(GAME_ID))
        await clear_session(call.from_user.id)
        return

    # Сохраняем состояние, включая последний ход игрока для следующего раунда
    state["history"] = history
    state["score"] = score
    state["last_player_move"] = player_move
    await set_session(call.from_user.id, GAME_ID, state)

    await call.message.edit_text(text + "\n\nТвой ход:", reply_markup=rps_kb())
# games/antonyms.py
# Игра «Антонимы»: ИИ даёт слово, игрок пишет максимально не связанное.
# ИИ оценивает антисвязность от 0 до 10.

import logging
import random

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from ai import ask_ai_json, AIError
from states import AntonymsStates

logger = logging.getLogger(__name__)

router = Router(name="antonyms")

GAME_ID = "antonyms"
ROUNDS = 5

PERSONAS = [
    {
        "name": "Строгий",
        "trait": (
            "Ты оцениваешь строго и без скидок. Если слова хоть как-то "
            "пересекаются по смыслу, категории или контексту — снижай балл. "
            "Комментарий короткий, по делу."
        ),
    },
    {
        "name": "Ироничный",
        "trait": (
            "Ты комментируешь с лёгкой иронией, но оценку ставишь честно. "
            "Если игрок придумал банальное слово — подколи, но не грубо. "
            "Если красиво — коротко похвали."
        ),
    },
    {
        "name": "Щедрый",
        "trait": (
            "Ты склонен засчитывать неожиданные ассоциации и давать балл выше, "
            "если слово действительно уводит в другую категорию. "
            "Комментарий доброжелательный, короткий."
        ),
    },
]


async def ai_new_word(persona: dict, used: list) -> str:
    """Попросить у ИИ стартовое слово. Если упал — берём из локального списка."""
    system = (
        "Ты ведущий игры «Антонимы». Отвечай СТРОГО валидным JSON без "
        "markdown-обёртки, на русском."
    )
    user = (
        f"Придумай одно нарицательное существительное на русском — "
        f"конкретное, понятное (не абстрактное). Одно слово. "
        f"Не используй слова: {', '.join(used) if used else '—'}.\n\n"
        f'Формат: {{"word": "твоё_слово"}}'
    )
    try:
        data = await ask_ai_json(system, user, temperature=0.9, max_tokens=60)
        word = str(data.get("word", "")).strip().lower()
        if not word or word in used:
            raise AIError("ИИ вернул пустое или повторяющееся слово")
        return word
    except AIError as e:
        logger.warning("ANTONYMS: ИИ упал на новом слове, fallback. %s", e)
        pool = ["море", "стол", "лампа", "город", "книга", "зонт", "лёд", "поле"]
        return random.choice([w for w in pool if w not in used] or pool)


async def ai_score(persona: dict, base: str, answer: str) -> dict:
    """
    Оценить антисвязность от 0 до 10 + короткий комментарий.
    Формат ответа: {'score': int, 'comment': str}
    """
    system = (
        f"Ты оцениваешь антисвязность пары слов в игре «Антонимы». "
        f"Твой характер: {persona['trait']} "
        f"Оценка — целое число от 0 до 10 (0 — слова связаны, 10 — максимально "
        f"далеко друг от друга). Комментарий — 1 короткое предложение, "
        f"до 120 символов, без эмодзи. "
        f"Отвечай СТРОГО валидным JSON без markdown-обёртки, на русском."
    )
    user = (
        f"Исходное слово: «{base}».\n"
        f"Ответ игрока: «{answer}».\n\n"
        f"Насколько слова далеки друг от друга по смыслу, категории, контексту? "
        f"Оцени от 0 до 10 и дай короткий комментарий в своём характере.\n\n"
        f'Формат: {{"score": 7, "comment": "короткая фраза"}}'
    )
    try:
        data = await ask_ai_json(system, user, temperature=0.7, max_tokens=150)
        score = int(data.get("score", 0))
        score = max(0, min(10, score))
        comment = str(data.get("comment", "")).strip()[:160]
        return {"score": score, "comment": comment or "…"}
    except AIError as e:
        logger.warning("ANTONYMS: ИИ упал на оценке, fallback. %s", e)
        return {"score": 5, "comment": "Оценка недоступна."}


def header_text(persona: dict, base: str, round_no: int) -> str:
    return (
        f"<b>Антонимы</b> · ведущий: {persona['name']}\n"
        f"Раунд {round_no} / {ROUNDS}\n\n"
        f"Слово: <b>{base}</b>\n"
        f"Напиши максимально не связанное слово."
    )


@router.callback_query(F.data == f"start_game:{GAME_ID}")
async def start_antonyms(call: CallbackQuery, state: FSMContext) -> None:
    from keyboards import back_to_menu_kb
    from database import set_session

    persona = random.choice(PERSONAS)
    base = await ai_new_word(persona, [])

    await set_session(call.from_user.id, GAME_ID, {
        "persona": persona,
        "round": 1,
        "total": 0,
        "used_base": [base],
        "base": base,
    })

    await state.set_state(AntonymsStates.waiting_word)

    await call.message.edit_text(
        header_text(persona, base, 1),
        reply_markup=back_to_menu_kb(),
    )
    await call.answer()


@router.message(AntonymsStates.waiting_word, F.text)
async def handle_answer(message: Message, state: FSMContext) -> None:
    from keyboards import back_to_menu_kb, next_round_kb
    from database import get_session, set_session, clear_session, record_result

    answer = (message.text or "").strip().lower()
    if not answer:
        return
    if len(answer) > 50:
        await message.answer("Слишком длинно. Одно слово, до 50 символов.")
        return

    sess = await get_session(message.from_user.id)
    if not sess or sess["game"] != GAME_ID:
        await state.clear()
        await message.answer(
            "Сессия потерялась. Начни игру заново из меню.",
            reply_markup=back_to_menu_kb(),
        )
        return

    st = sess["state"]
    persona = st["persona"]
    base = st["base"]
    round_no = st["round"]
    total = st["total"]
    used_base = st["used_base"]

    await message.answer("Оцениваю…")
    result = await ai_score(persona, base, answer)
    score = result["score"]
    comment = result["comment"]
    total += score

    text = (
        f"«{base}» ↔ «{answer}»\n\n"
        f"<b>{score} / 10</b>\n"
        f"<i>{comment}</i>\n\n"
        f"Всего: <b>{total}</b>"
    )

    # Финал партии
    if round_no >= ROUNDS:
        await clear_session(message.from_user.id)
        await state.clear()
        if total >= 31:
            medal = "🏆 Отличный результат."
            await record_result(message.from_user.id, GAME_ID, "win")
        elif total >= 15:
            medal = "👍 Средний результат."
            await record_result(message.from_user.id, GAME_ID, "draw")
        else:
            medal = "🙃 Слабовато."
            await record_result(message.from_user.id, GAME_ID, "loss")

        await message.answer(
            f"{text}\n\n{medal}\nСумма за {ROUNDS} раундов: <b>{total}</b>.",
            reply_markup=next_round_kb(GAME_ID),
        )
        return

    # Следующий раунд
    next_base = await ai_new_word(persona, used_base)
    used_base.append(next_base)

    st["round"] = round_no + 1
    st["total"] = total
    st["base"] = next_base
    st["used_base"] = used_base
    await set_session(message.from_user.id, GAME_ID, st)

    await message.answer(text, reply_markup=back_to_menu_kb())
    await message.answer(
        header_text(persona, next_base, round_no + 1),
        reply_markup=back_to_menu_kb(),
    )
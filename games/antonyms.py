# games/antonyms.py
# Игра «Антонимы»: ИИ даёт слово, игрок подбирает настоящий антоним.
# ИИ проверяет: правильный антоним или нет.

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
            "Ты строгий ведущий. Засчитываешь только точные антонимы. "
            "Если слово — не антоним, а просто связанное или синоним — "
            "честно говоришь, что не засчитано, и коротко объясняешь почему."
        ),
    },
    {
        "name": "Дружелюбный",
        "trait": (
            "Ты дружелюбный ведущий. Засчитываешь точные антонимы, а если "
            "игрок ошибся — мягко поправляешь и подсказываешь правильный вариант."
        ),
    },
    {
        "name": "Ироничный",
        "trait": (
            "Ты с лёгкой иронией. Засчитываешь правильные ответы, но не "
            "упускаешь случая подколоть за промах — коротко и без грубости."
        ),
    },
]


async def ai_new_word(persona: dict, used: list) -> dict:
    """
    Попросить у ИИ слово и его правильный антоним (эталон).
    Возвращаем {'word': 'тёплый', 'antonym': 'холодный'}.
    """
    system = (
        "Ты ведущий игры «Антонимы». Отвечай СТРОГО валидным JSON без "
        "markdown-обёртки, на русском."
    )
    user = (
        f"Придумай одно прилагательное или наречие на русском, у которого "
        f"есть общепризнанный антоним (например: тёплый→холодный, "
        f"быстро→медленно, высокий→низкий). "
        f"Не используй слова: {', '.join(used) if used else '—'}.\n\n"
        f'Формат: {{"word": "тёплый", "antonym": "холодный"}}'
    )
    try:
        data = await ask_ai_json(system, user, temperature=0.8, max_tokens=80)
        word = str(data.get("word", "")).strip().lower()
        antonym = str(data.get("antonym", "")).strip().lower()
        if not word or not antonym or word in used:
            raise AIError("ИИ вернул пустое или повторяющееся слово")
        return {"word": word, "antonym": antonym}
    except AIError as e:
        logger.warning("ANTONYMS: ИИ упал на новом слове, fallback. %s", e)
        pool = [
            {"word": "тёплый", "antonym": "холодный"},
            {"word": "быстро", "antonym": "медленно"},
            {"word": "высокий", "antonym": "низкий"},
            {"word": "день", "antonym": "ночь"},
            {"word": "добрый", "antonym": "злой"},
            {"word": "светлый", "antonym": "тёмный"},
        ]
        return random.choice([p for p in pool if p["word"] not in used] or pool)


async def ai_check(persona: dict, base: str, antonym: str, answer: str) -> dict:
    """
    Проверить, является ли ответ антонимом слова.
    Возвращаем {'correct': bool, 'comment': str}.
    """
    system = (
        f"Ты проверяешь ответ в игре «Антонимы». "
        f"Твой характер: {persona['trait']} "
        f"Комментарий — 1 короткое предложение, до 120 символов, без эмодзи. "
        f"Отвечай СТРОГО валидным JSON без markdown-обёртки, на русском."
    )
    user = (
        f"Слово: «{base}».\n"
        f"Эталонный антоним: «{antonym}».\n"
        f"Ответ игрока: «{answer}».\n\n"
        f"Считается ли ответ правильным антонимом? Учти синонимы и близкие "
        f"варианты (например «холодный» и «студёный» — оба верны для «тёплого»). "
        f"Если игрок написал синоним исходного слова или просто связанное — "
        f"не засчитывай.\n\n"
        f'Формат: {{"correct": true, "comment": "короткая фраза"}}'
    )
    try:
        data = await ask_ai_json(system, user, temperature=0.5, max_tokens=150)
        correct = bool(data.get("correct", False))
        comment = str(data.get("comment", "")).strip()[:160]
        return {"correct": correct, "comment": comment or "…"}
    except AIError as e:
        logger.warning("ANTONYMS: ИИ упал на проверке, fallback. %s", e)
        # Простой фолбэк: точное совпадение с эталоном
        return {
            "correct": answer.strip().lower() == antonym,
            "comment": "Проверка недоступна, зачёл по точному совпадению.",
        }


def header_text(persona: dict, word: str, round_no: int) -> str:
    return (
        f"<b>Антонимы</b> · ведущий: {persona['name']}\n"
        f"Раунд {round_no} / {ROUNDS}\n\n"
        f"Слово: <b>{word}</b>\n"
        f"Напиши антоним — слово с противоположным значением."
    )


@router.callback_query(F.data == f"start_game:{GAME_ID}")
async def start_antonyms(call: CallbackQuery, state: FSMContext) -> None:
    from keyboards import back_to_menu_kb
    from database import set_session

    persona = random.choice(PERSONAS)
    pair = await ai_new_word(persona, [])

    await set_session(call.from_user.id, GAME_ID, {
        "persona": persona,
        "round": 1,
        "score": 0,
        "used_words": [pair["word"]],
        "word": pair["word"],
        "antonym": pair["antonym"],
    })

    await state.set_state(AntonymsStates.waiting_word)

    await call.message.edit_text(
        header_text(persona, pair["word"], 1),
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
    if len(answer) > 40:
        await message.answer("Слишком длинно. Одно слово, до 40 символов.")
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
    word = st["word"]
    antonym = st["antonym"]
    round_no = st["round"]
    score = st["score"]
    used_words = st["used_words"]

    await message.answer("Проверяю…")
    result = await ai_check(persona, word, antonym, answer)
    correct = result["correct"]
    comment = result["comment"]
    if correct:
        score += 1

    mark = "✅" if correct else "❌"
    text = (
        f"«{word}» → «{answer}»\n\n"
        f"{mark} <b>{'Засчитано' if correct else 'Не засчитано'}</b>\n"
        f"<i>{comment}</i>\n"
    )
    if not correct:
        text += f"\nЭталонный антоним: <b>{antonym}</b>"

    # Финал партии
    if round_no >= ROUNDS:
        await clear_session(message.from_user.id)
        await state.clear()
        if score >= 4:
            medal = "🏆 Отличный результат."
            await record_result(message.from_user.id, GAME_ID, "win")
        elif score >= 2:
            medal = "👍 Средний результат."
            await record_result(message.from_user.id, GAME_ID, "draw")
        else:
            medal = "🙃 Слабовато."
            await record_result(message.from_user.id, GAME_ID, "loss")

        await message.answer(
            f"{text}\n\n{medal}\nСчёт: <b>{score} / {ROUNDS}</b>.",
            reply_markup=next_round_kb(GAME_ID),
        )
        return

    # Следующий раунд
    pair = await ai_new_word(persona, used_words)
    used_words.append(pair["word"])

    st["round"] = round_no + 1
    st["score"] = score
    st["word"] = pair["word"]
    st["antonym"] = pair["antonym"]
    st["used_words"] = used_words
    await set_session(message.from_user.id, GAME_ID, st)

    await message.answer(text, reply_markup=back_to_menu_kb())
    await message.answer(
        header_text(persona, pair["word"], round_no + 1),
        reply_markup=back_to_menu_kb(),
    )

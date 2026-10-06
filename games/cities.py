# games/cities.py
# Игра «Города»: игрок и ИИ по очереди называют города.

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from ai import ask_ai_json, AIError
from states import CitiesStates

logger = logging.getLogger(__name__)

router = Router(name="cities")

GAME_ID = "cities"

# Русские города для фолбэка
FALLBACK_CITIES = [
    "Москва", "Астрахань", "Новгород", "Дербент", "Тула",
    "Архангельск", "Курск", "Красноярск", "Казань", "Новосибирск",
]

# Буквы, на которые городов мало — заменяем на предыдущую
HARD_LETTERS = "ъьы"


def last_letter(city: str) -> str:
    """Последняя значимая буква (без ь, ъ, ы)."""
    s = city.strip().lower()
    while s and s[-1] in HARD_LETTERS:
        s = s[:-1]
    return s[-1] if s else ""


async def ai_pick_city(used: list, letter: str) -> dict:
    """ИИ называет город на нужную букву + короткий факт."""
    system = (
        "Ты играешь в «Города» против человека. Отвечай СТРОГО валидным "
        "JSON без markdown-обёртки, на русском."
    )
    user = (
        f"Назови российский или зарубежный город на букву «{letter.upper()}». "
        f"Не используй: {', '.join(used) if used else '—'}.\n"
        f"Добавь короткий факт (1 предложение) об этом городе.\n\n"
        f'Формат: {{"city": "Москва", "fact": "Столица России, крупнейший город Европы."}}'
    )
    try:
        data = await ask_ai_json(system, user, temperature=0.8, max_tokens=180)
        city = str(data.get("city", "")).strip()
        fact = str(data.get("fact", "")).strip()[:220]
        if not city or city.lower() in [c.lower() for c in used]:
            raise AIError("Город пуст или уже назван")
        return {"city": city, "fact": fact}
    except AIError as e:
        logger.warning("CITIES: ИИ упал, fallback. %s", e)
        for c in FALLBACK_CITIES:
            if c.lower() not in [u.lower() for u in used] and c[0].lower() == letter.lower():
                return {"city": c, "fact": "Город из моего резерва."}
        # Если на букву нет — отдаём первый из списка
        return {"city": "Новгород", "fact": "Один из древнейших городов России."}


@router.callback_query(F.data == f"start_game:{GAME_ID}")
async def start_cities(call: CallbackQuery, state: FSMContext) -> None:
    from keyboards import back_to_menu_kb
    from database import set_session

    # ИИ начинает первым
    first = await ai_pick_city([], "м")

    await set_session(call.from_user.id, GAME_ID, {
        "used": [first["city"]],
        "player_turn": True,
        "letter": last_letter(first["city"]),
    })
    await state.set_state(CitiesStates.waiting_city)

    await call.message.edit_text(
        f"<b>Города</b>\n\n"
        f"Я начну: <b>{first['city']}</b>\n"
        f"<i>{first['fact']}</i>\n\n"
        f"Твой город на букву <b>{last_letter(first['city']).upper()}</b>:",
        reply_markup=back_to_menu_kb(),
    )
    await call.answer()


@router.message(CitiesStates.waiting_city, F.text)
async def handle_city(message: Message, state: FSMContext) -> None:
    from keyboards import next_round_kb, back_to_menu_kb
    from database import get_session, set_session, clear_session, record_result

    city = (message.text or "").strip()
    if not city or len(city) > 60:
        return

    sess = await get_session(message.from_user.id)
    if not sess or sess["game"] != GAME_ID:
        await state.clear()
        await message.answer("Сессия потерялась.", reply_markup=back_to_menu_kb())
        return

    st = sess["state"]
    used = st["used"]
    letter = st["letter"]

    # Проверка буквы
    if last_letter(city) == "" or city[0].lower() != letter.lower():
        await message.answer(
            f"❌ Город должен начинаться на <b>{letter.upper()}</b>. Попробуй ещё.",
        )
        return
    if city.lower() in [u.lower() for u in used]:
        await message.answer("❌ Этот город уже был. Назови другой.")
        return

    used.append(city)
    new_letter = last_letter(city)

    if new_letter == "":
        await message.answer("❌ Странный город. Попробуй другой.")
        return

    await message.answer("Ищу город...")

    ai_data = await ai_pick_city(used, new_letter)
    ai_city = ai_data["city"]
    ai_fact = ai_data["fact"]

    # Проверяем, что ИИ не сдался
    if last_letter(ai_city) == "":
        # Игра окончена — ИИ не нашёл город
        await clear_session(message.from_user.id)
        await state.clear()
        await record_result(message.from_user.id, GAME_ID, "win")
        await message.answer(
            f"🏆 <b>Ты победил!</b>\n\n"
            f"Я не смог найти город на букву <b>{new_letter.upper()}</b>.\n"
            f"Всего городов в партии: {len(used)}.",
            reply_markup=next_round_kb(GAME_ID),
        )
        return

    used.append(ai_city)
    st["used"] = used
    st["letter"] = last_letter(ai_city)
    await set_session(message.from_user.id, GAME_ID, st)

    await message.answer(
        f"✅ Принято: <b>{city}</b>\n\n"
        f"Мой ответ: <b>{ai_city}</b>\n"
        f"<i>{ai_fact}</i>\n\n"
        f"Твой город на букву <b>{last_letter(ai_city).upper()}</b>:",
        reply_markup=back_to_menu_kb(),
    )

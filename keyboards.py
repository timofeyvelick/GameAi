# keyboards.py
# Все общие клавиатуры бота.

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from games import GAMES


def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню: сетка из игр по 2 кнопки в ряд + статистика и помощь."""
    kb = InlineKeyboardBuilder()

    for game in GAMES:
        # Обращаемся через ТОЧКУ, потому что game — объект GameInfo
        kb.button(
            text=f"{game.emoji} {game.title}",
            callback_data=f"start_game:{game.id}",
        )

    kb.button(text="📊 Моя статистика", callback_data="stats")
    kb.button(text="ℹ️ Помощь",         callback_data="help")

    kb.adjust(2)
    return kb.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Меню", callback_data="menu")
    return kb.as_markup()


def next_round_kb(game_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Ещё раунд", callback_data=f"start_game:{game_id}")
    kb.button(text="🏠 Меню",      callback_data="menu")
    kb.adjust(2)
    return kb.as_markup()


def yes_no_unknown_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да",      callback_data="ans:yes")
    kb.button(text="❌ Нет",     callback_data="ans:no")
    kb.button(text="🤷 Не знаю", callback_data="ans:unknown")
    kb.button(text="🏠 Меню",    callback_data="menu")
    kb.adjust(3, 1)
    return kb.as_markup()


def yes_no_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Верю",    callback_data="believe:yes")
    kb.button(text="❌ Не верю", callback_data="believe:no")
    kb.adjust(2)
    return kb.as_markup()


def numbers_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for n in range(1, 11):
        kb.button(text=str(n), callback_data=f"num:{n}")
    kb.button(text="🏠 Меню", callback_data="menu")
    kb.adjust(5, 5, 1)
    return kb.as_markup()


def rps_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🪨 Камень",  callback_data="rps:rock")
    kb.button(text="✂️ Ножницы", callback_data="rps:scissors")
    kb.button(text="📄 Бумага",  callback_data="rps:paper")
    kb.button(text="🏠 Меню",    callback_data="menu")
    kb.adjust(3, 1)
    return kb.as_markup()
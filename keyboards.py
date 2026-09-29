# keyboards.py
# Все общие клавиатуры бота. Каждая игра использует эти же функции —
# так у пользователя везде единый вид кнопок.

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Импортируем список игр из games/__init__.py
# (мы его создадим на следующем этапе — если пока нет, закомментируй импорт и словарь)
from games import GAMES


# ============================================
# ГЛАВНОЕ МЕНЮ
# ============================================
def main_menu_kb() -> InlineKeyboardMarkup:
    """
    Главное меню: сетка из игр по 2 кнопки в ряд.
    callback_data для каждой игры — 'start_game:<game_id>'.
    """
    kb = InlineKeyboardBuilder()

    for game in GAMES:
        kb.button(
            text=f"{game['emoji']} {game['title']}",
            callback_data=f"start_game:{game['id']}",
        )

    kb.button(text="📊 Моя статистика", callback_data="stats")
    kb.button(text="ℹ️ Помощь", callback_data="help")

    # 2 кнопки в ряд, последний ряд растянется как получится
    kb.adjust(2)
    return kb.as_markup()


# ============================================
# КНОПКА «В МЕНЮ»
# ============================================
def back_to_menu_kb() -> InlineKeyboardMarkup:
    """Одна кнопка — вернуться в главное меню. Используется внутри игр."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Меню", callback_data="menu")
    return kb.as_markup()


# ============================================
# «ЕЩЁ РАУНД / МЕНЮ»
# ============================================
def next_round_kb(game_id: str) -> InlineKeyboardMarkup:
    """
    Кнопки после партии: сыграть ещё раз или выйти в меню.
    game_id — id текущей игры, чтобы запустить её же заново.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Ещё раунд", callback_data=f"start_game:{game_id}")
    kb.button(text="🏠 Меню", callback_data="menu")
    kb.adjust(2)
    return kb.as_markup()


# ============================================
# «ДА / НЕТ / НЕ ЗНАЮ»
# ============================================
def yes_no_unknown_kb() -> InlineKeyboardMarkup:
    """Для игры «20 вопросов» и «Кто я?» — ответы на вопросы игрока."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да",      callback_data="ans:yes")
    kb.button(text="❌ Нет",     callback_data="ans:no")
    kb.button(text="🤷 Не знаю", callback_data="ans:unknown")
    kb.button(text="🏠 Меню",    callback_data="menu")
    kb.adjust(3, 1)
    return kb.as_markup()


# ============================================
# ТОЛЬКО «ДА / НЕТ»
# ============================================
def yes_no_kb() -> InlineKeyboardMarkup:
    """Для игры «Верю / не верю»."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Верю",     callback_data="believe:yes")
    kb.button(text="❌ Не верю",  callback_data="believe:no")
    kb.adjust(2)
    return kb.as_markup()


# ============================================
# ИГРА «МИНА ИЗ ЦИФР» — быстрые кнопки 1..10
# ============================================
def numbers_kb() -> InlineKeyboardMarkup:
    """Кнопки с числами 1..10 для игры «Мина»."""
    kb = InlineKeyboardBuilder()
    for n in range(1, 11):
        kb.button(text=str(n), callback_data=f"num:{n}")
    kb.button(text="🏠 Меню", callback_data="menu")
    kb.adjust(5, 5, 1)
    return kb.as_markup()


# ============================================
# КАМЕНЬ-НОЖНИЦЫ-БУМАГА — три кнопки хода
# ============================================
def rps_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🪨 Камень",   callback_data="rps:rock")
    kb.button(text="✂️ Ножницы",  callback_data="rps:scissors")
    kb.button(text="📄 Бумага",   callback_data="rps:paper")
    kb.button(text="🏠 Меню",     callback_data="menu")
    kb.adjust(3, 1)
    return kb.as_markup()
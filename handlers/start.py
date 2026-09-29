# handlers/start.py
# Обработчики команд /start, /help, /stats и кнопок главного меню.

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from keyboards import main_menu_kb, back_to_menu_kb
from database import get_or_create_user, get_stats
from games import GAMES

router = Router(name="start")


HELLO = (
    "👋 Привет! Я <b>игровой бот с ИИ</b>.\n\n"
    "Выбери игру — и ИИ станет твоим соперником или ведущим:\n\n"
    "<i>Каждая игра — отдельный характер, стратегия и чувство юмора.</i>"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    u = message.from_user
    await get_or_create_user(u.id, u.username or "", u.first_name or "")
    await message.answer(HELLO, reply_markup=main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    lines = ["<b>Доступные игры:</b>\n"]
    for g in GAMES:
        lines.append(f"{g.emoji} <b>{g.title}</b> — {g.description}")
    lines.append("\nКоманды: /start — меню, /stats — статистика, /help — эта справка")
    await message.answer("\n".join(lines), reply_markup=back_to_menu_kb())


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    rows = await get_stats(message.from_user.id)
    if not rows:
        await message.answer(
            "Ты ещё не играл. Жми «Меню» и выбери игру 👇",
            reply_markup=main_menu_kb(),
        )
        return

    lines = ["<b>📊 Твоя статистика</b>\n"]
    for r in rows:
        # Название игры по id — из реестра
        from games import GAMES_BY_ID
        g = GAMES_BY_ID.get(r["game"])
        title = f"{g.emoji} {g.title}" if g else r["game"]
        lines.append(
            f"{title}: "
            f"<b>{r['wins']}</b>П / {r['losses']}Пр / {r['draws']}Н "
            f"(всего {r['played']})"
        )
    await message.answer("\n".join(lines), reply_markup=back_to_menu_kb())


@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery) -> None:
    """Любая кнопка «🏠 Меню» возвращает в главное меню."""
    await call.message.edit_text(HELLO, reply_markup=main_menu_kb())
    await call.answer()


@router.callback_query(F.data == "help")
async def cb_help(call: CallbackQuery) -> None:
    lines = ["<b>Доступные игры:</b>\n"]
    for g in GAMES:
        lines.append(f"{g.emoji} <b>{g.title}</b> — {g.description}")
    await call.message.edit_text("\n".join(lines), reply_markup=back_to_menu_kb())
    await call.answer()


@router.callback_query(F.data == "stats")
async def cb_stats(call: CallbackQuery) -> None:
    rows = await get_stats(call.from_user.id)
    if not rows:
        await call.message.edit_text(
            "Ты ещё не играл. Выбери игру 👇",
            reply_markup=main_menu_kb(),
        )
        await call.answer()
        return

    lines = ["<b>📊 Твоя статистика</b>\n"]
    for r in rows:
        from games import GAMES_BY_ID
        g = GAMES_BY_ID.get(r["game"])
        title = f"{g.emoji} {g.title}" if g else r["game"]
        lines.append(
            f"{title}: "
            f"<b>{r['wins']}</b>П / {r['losses']}Пр / {r['draws']}Н "
            f"(всего {r['played']})"
        )
    await call.message.edit_text("\n".join(lines), reply_markup=back_to_menu_kb())
    await call.answer()
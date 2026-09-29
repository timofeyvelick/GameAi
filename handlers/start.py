# handlers/start.py
# /start, /help, /stats и кнопки главного меню.

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from keyboards import main_menu_kb, back_to_menu_kb
from database import get_or_create_user, get_stats
from games import GAMES, GAMES_BY_ID

router = Router(name="start")


HELLO = (
    "👋 Привет! Я <b>игровой бот с ИИ</b>.\n\n"
    "Выбери игру — и ИИ станет твоим соперником или ведущим:\n\n"
    "<i>Каждая игра — отдельный характер, стратегия и чувство юмора.</i>"
)


def _help_text() -> str:
    lines = ["<b>Доступные игры:</b>\n"]
    for g in GAMES:
        lines.append(f"{g.emoji} <b>{g.title}</b> — {g.description}")
    lines.append("\nКоманды: /start — меню, /stats — статистика, /help — справка")
    return "\n".join(lines)


def _stats_text(rows: list[dict]) -> str:
    lines = ["<b>📊 Твоя статистика</b>\n"]
    for r in rows:
        g = GAMES_BY_ID.get(r["game"])
        title = f"{g.emoji} {g.title}" if g else r["game"]
        lines.append(
            f"{title}: "
            f"<b>{r['wins']}</b>П / {r['losses']}Пр / {r['draws']}Н "
            f"(всего {r['played']})"
        )
    return "\n".join(lines)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    u = message.from_user
    await get_or_create_user(u.id, u.username or "", u.first_name or "")
    await message.answer(HELLO, reply_markup=main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(_help_text(), reply_markup=back_to_menu_kb())


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    rows = await get_stats(message.from_user.id)
    if not rows:
        await message.answer(
            "Ты ещё не играл. Жми «Меню» и выбери игру 👇",
            reply_markup=main_menu_kb(),
        )
        return
    await message.answer(_stats_text(rows), reply_markup=back_to_menu_kb())


@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery) -> None:
    await call.message.edit_text(HELLO, reply_markup=main_menu_kb())
    await call.answer()


@router.callback_query(F.data == "help")
async def cb_help(call: CallbackQuery) -> None:
    await call.message.edit_text(_help_text(), reply_markup=back_to_menu_kb())
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
    await call.message.edit_text(_stats_text(rows), reply_markup=back_to_menu_kb())
    await call.answer()
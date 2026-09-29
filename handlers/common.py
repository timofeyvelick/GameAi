# handlers/common.py
# Пока игры не реализованы — ловим нажатие "start_game:<id>" и отвечаем заглушкой.
# Когда напишем игру — её роутер будет зарегистрирован РАНЬШЕ этого,
# и хендлер здесь перестанет срабатывать (aiogram берёт первый подходящий).

from aiogram import Router, F
from aiogram.types import CallbackQuery

from games import GAMES_BY_ID
from keyboards import back_to_menu_kb

router = Router(name="common")


@router.callback_query(F.data.startswith("start_game:"))
async def start_game_stub(call: CallbackQuery) -> None:
    game_id = call.data.split(":", 1)[1]
    g = GAMES_BY_ID.get(game_id)
    if not g:
        await call.answer("Такой игры нет", show_alert=True)
        return

    text = (
        f"{g.emoji} <b>{g.title}</b>\n\n"
        f"<i>{g.description}</i>\n\n"
        "🚧 Игра пока в разработке. Совсем скоро! 🚧"
    )
    await call.message.edit_text(text, reply_markup=back_to_menu_kb())
    await call.answer()
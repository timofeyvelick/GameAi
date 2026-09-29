# games/__init__.py
# Реестр всех игр. Пока роутеров нет — игры просто объявлены в списке.
# Когда напишем игру, поменяем 'router': None на реальный роутер.

from dataclasses import dataclass
from typing import Optional
from aiogram import Router


@dataclass
class GameInfo:
    """Описание одной игры для меню."""
    id: str           # технический id (латиницей), для callback_data
    title: str        # название на кнопке
    emoji: str        # эмодзи на кнопке
    description: str  # подсказка в /help
    router: Optional[Router] = None  # aiogram-роутер игры (заполним позже)


# Список всех игр. Порядок = порядок кнопок в меню.
GAMES: list[GameInfo] = [
    GameInfo("rock_paper_scissors", "Камень-ножницы-бумага", "🪨",
             "Соперник со стратегиями: злопамятный, блефующий, ироничный"),
    GameInfo("crossword",            "Кроссворд",              "🧩",
             "ИИ генерирует сетку и загадки под тему"),
    GameInfo("guess_word",           "Угадай слово по буквам", "🔤",
             "Ведущий загадывает слово, следит за буквами, даёт хитрые подсказки"),
    GameInfo("twenty_questions",     "20 вопросов",            "🎩",
             "ИИ загадывает персонажа, ты отгадываешь через Да/Нет"),
    GameInfo("who_am_i",             "Кто я?",                 "🤔",
             "ИИ клеит тебе персонажа на лоб, ты задаёшь вопросы"),
    GameInfo("emoji_movie",          "Фильм по эмодзи",        "🍿",
             "Угадай фильм по эмодзи и получи смешной факт"),
    GameInfo("believe_or_not",       "Верю / Не верю",         "🤨",
             "Реальные факты и правдоподобная нейро-чушь вперемешку"),
    GameInfo("cities",               "Города",                 "🌍",
             "Соперник + интересный факт про каждый город"),
    GameInfo("antonyms",             "Антонимы",               "🔀",
             "Даётся слово — подбери максимально не связанное"),
    GameInfo("mine_number",          "Мина из цифр",           "💣",
             "Загадано число 1–10. Называй любые, кроме него"),
]


# Быстрый доступ по id: GAMES_BY_ID['cities'] → GameInfo
GAMES_BY_ID: dict[str, GameInfo] = {g.id: g for g in GAMES}
# games/__init__.py
# Реестр всех игр.

from dataclasses import dataclass
from typing import Optional
from aiogram import Router


@dataclass
class GameInfo:
    id: str
    title: str
    emoji: str
    description: str
    router: Optional[Router] = None


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


GAMES_BY_ID: dict[str, GameInfo] = {g.id: g for g in GAMES}

# Подключаем роутеры реализованных игр
from games.rock_paper_scissors import router as rps_router
GAMES_BY_ID["rock_paper_scissors"].router = rps_router

from games.mine_number import router as mine_router
GAMES_BY_ID["mine_number"].router = mine_router

from games.antonyms import router as antonyms_router
GAMES_BY_ID["antonyms"].router = antonyms_router

from games.believe_or_not import router as believe_router
GAMES_BY_ID["believe_or_not"].router = believe_router

from games.emoji_movie import router as emoji_router
GAMES_BY_ID["emoji_movie"].router = emoji_router

from games.cities import router as cities_router
GAMES_BY_ID["cities"].router = cities_router

from games.guess_word import router as guess_router
GAMES_BY_ID["guess_word"].router = guess_router

from games.twenty_questions import router as tq_router
GAMES_BY_ID["twenty_questions"].router = tq_router

from games.who_am_i import router as whoami_router
GAMES_BY_ID["who_am_i"].router = whoami_router

from games.crossword import router as crossword_router
GAMES_BY_ID["crossword"].router = crossword_router

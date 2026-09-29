# states.py
# FSM-состояния для игр, где игрок пишет текст или ждёт ответа.

from aiogram.fsm.state import State, StatesGroup


class RPSStates(StatesGroup):
    waiting_move = State()


class GuessWordStates(StatesGroup):
    waiting_letter = State()


class TwentyQuestionsStates(StatesGroup):
    asking = State()


class WhoAmIStates(StatesGroup):
    asking = State()


class EmojiMovieStates(StatesGroup):
    guessing = State()


class BelieveStates(StatesGroup):
    answering = State()


class CitiesStates(StatesGroup):
    waiting_city = State()


class AntonymsStates(StatesGroup):
    waiting_word = State()


class MineStates(StatesGroup):
    waiting_number = State()


class CrosswordStates(StatesGroup):
    answering = State()
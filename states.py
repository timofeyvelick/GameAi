# states.py
# FSM-состояния (finite state machine — конечный автомат).
# Используются там, где игра идёт пошагово: бот должен знать,
# какого следующего сообщения ждать от игрока.

from aiogram.fsm.state import State, StatesGroup


class RPSStates(StatesGroup):
    """Камень-ножницы-бумага: ждём ход игрока."""
    waiting_move = State()


class GuessWordStates(StatesGroup):
    """Угадай слово: ждём букву или слово целиком."""
    waiting_letter = State()


class TwentyQuestionsStates(StatesGroup):
    """20 вопросов: игрок задаёт вопрос — ИИ отвечает."""
    asking = State()


class WhoAmIStates(StatesGroup):
    """Кто я: игрок задаёт вопросы про своего персонажа."""
    asking = State()


class EmojiMovieStates(StatesGroup):
    """Фильм по эмодзи: ждём догадку игрока."""
    guessing = State()


class BelieveStates(StatesGroup):
    """Верю / не верю: ждём реакцию на факт."""
    answering = State()


class CitiesStates(StatesGroup):
    """Города: ждём город от игрока."""
    waiting_city = State()


class AntonymsStates(StatesGroup):
    """Антонимы: ждём слово-антипод."""
    waiting_word = State()


class MineStates(StatesGroup):
    """Мина из цифр: ждём число."""
    waiting_number = State()


class CrosswordStates(StatesGroup):
    """Кроссворд: ждём ответ на текущий вопрос."""
    answering = State()
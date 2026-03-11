import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from aiogram_calendar import simple_cal_callback, SimpleCalendar

API_TOKEN = os.getenv("API_TOKEN")  # токен бота в переменных окружения

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Федеральные земли
lands = [
    "Баден-Вюртемберг","Бавария","Берлин","Бранденбург","Бремен","Гамбург",
    "Гессен","Мекленбург-Передняя Померания","Нижняя Саксония",
    "Северный Рейн-Вестфалия","Рейнланд-Пфальц","Саар","Саксония",
    "Саксония-Анхальт","Шлезвиг-Гольштейн","Тюрингия"
]

# Профессии
professions = [
    ("Инженер","Техническая профессия"),
    ("Врач","Медицинская профессия"),
    ("Учитель","Фиксированный доход"),
    ("Рабочий","Промышленная или строительная работа"),
    ("Программист","IT-профессия"),
    ("Менеджер","Управленческая должность")
]

user_data = {}

def create_inline_kb(options, prefix):
    kb = InlineKeyboardMarkup(row_width=1)
    for opt in options:
        kb.insert(InlineKeyboardButton(text=opt, callback_data=f"{prefix}:{opt}"))
    return kb

def create_inline_kb_with_desc(options, prefix):
    kb = InlineKeyboardMarkup(row_width=1)
    for opt, desc in options:
        text = f"{opt} — {desc}"
        kb.insert(InlineKeyboardButton(text=text, callback_data=f"{prefix}:{opt}"))
    return kb

# Параметры 2026
AVERAGE_INCOME_2026 = 51944
PENSION_POINT_VALUE_2026 = 42.52
MAX_POINTS_PER_YEAR = 1.95

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_data[message.from_user.id] = {}
    await message.answer(
        "Привет! Я помогу рассчитать вашу пенсию в Германии.\n"
        "Выберите федеральную землю:",
        reply_markup=create_inline_kb(lands, "land")
    )

@dp.callback_query_handler(lambda c: c.data.startswith("land:"))
async def land_chosen(cb: types.CallbackQuery):
    land = cb.data.split(":")[1]
    user_data[cb.from_user.id]["land"] = land
    await bot.send_message(cb.from_user.id, "Выберите профессию:", reply_markup=create_inline_kb_with_desc(professions, "prof"))

@dp.callback_query_handler(lambda c: c.data.startswith("prof:"))
async def prof_chosen(cb: types.CallbackQuery):
    prof = cb.data.split(":")[1]
    user_data[cb.from_user.id]["profession"] = prof
    await bot.send_message(cb.from_user.id, "Выберите год начала стажа:", reply_markup=await SimpleCalendar().start_calendar())

@dp.callback_query_handler(simple_cal_callback.filter())
async def calendar_handler(cb: types.CallbackQuery, callback_data: dict):
    selected, date = await SimpleCalendar().process_selection(cb, callback_data)
    if not selected:
        return
    uid = cb.from_user.id
    if "start_year" not in user_data[uid]:
        user_data[uid]["start_year"] = date.year
        await bot.send_message(uid, f"Начало стажа: {date.year}\nТеперь выберите год окончания:", reply_markup=await SimpleCalendar().start_calendar())
    else:
        user_data[uid]["end_year"] = date.year
        await bot.send_message(uid, "Введите ваш средний годовой доход в €:")

@dp.message_handler(lambda m: m.text.replace('.', '', 1).isdigit())
async def process_income(message: types.Message):
    uid = message.from_user.id
    data = user_data[uid]
    data["income"] = float(message.text)
    years = data["end_year"] - data["start_year"]
    points = (data["income"] / AVERAGE_INCOME_2026) * years
    points = min(points, years * MAX_POINTS_PER_YEAR)
    pension_amount = points * PENSION_POINT_VALUE_2026
    await message.answer(
        f"📌 Результаты:\n"
        f"Земля: {data['land']}\n"
        f"Профессия: {data['profession']}\n"
        f"Стаж: {years} лет\n"
        f"Баллы: {points:.2f}\n"
        f"Пенсия (брутто): {pension_amount:.2f} €\n\n"
        f"ℹ️ Брутто — без вычетов налогов и страховок.\n"
        f"Средний доход 2026: {AVERAGE_INCOME_2026} €/год."
    )

if __name__ == "__main__":
    from web import keep_alive
    keep_alive()  # запускаем веб-сервер для 24/7
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, LabeledPrice, PreCheckoutQuery

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8986640844:AAFOHa9fJ94aKibOV-cqczm0zGlXMjxHCwo"
WEBAPP_URL = "https://ai-school-4kxl.onrender.com"  # <--- ЗАМЕНИ НА СВОЙ АДРЕС С RENDER
ADMIN_ID = 7088034758  # <--- ТВОЙ TELEGRAM ID (узнать можно у @userinfobot)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_premium INTEGER DEFAULT 0,
            last_lesson_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def set_premium(user_id, status=1):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    cursor.execute('UPDATE users SET is_premium = ? WHERE user_id = ?', (status, user_id))
    conn.commit()
    conn.close()

def get_user_status(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT is_premium FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

# ==================== ОБРАБОТЧИКИ ====================

@dp.message(CommandStart())
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "друг"
    
    # Создаем запись в базе, если её нет
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

    # Проверяем статус
    is_premium = get_user_status(user_id)
    status_text = "💎 Premium" if is_premium else "🆓 Базовый"

    # Кнопка для входа в Mini App
    web_app = WebAppInfo(url=WEBAPP_URL)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть AI Школу", web_app=web_app)]
    ])
    
    # Кнопка для оплаты
    pay_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Купить Premium за 49 ⭐️", callback_data="buy_premium")]
    ])

    await message.answer(
        f"Привет, {username}!\n\n"
        f"Твой текущий тариф: {status_text}\n\n"
        f"Нажми кнопку ниже, чтобы открыть приложение и начать учиться!",
        reply_markup=keyboard
    )
    
    if not is_premium:
        await message.answer(
            "🔥 Хочешь открыть все 50 уроков и 4 теста?\n"
            "Оформи Premium за 49 звезд!",
            reply_markup=pay_keyboard
        )

# ==================== ОПЛАТА ====================

@dp.callback_query(F.data == "buy_premium")
async def send_invoice(callback: types.CallbackQuery):
    await callback.message.answer_invoice(
        title="AI Школа Premium",
        description="Полный доступ ко всем 50 урокам и 4 тестам на 30 дней.",
        payload="premium_subscription_30d",
        provider_token="",  # Пусто, так как это Stars
        currency="XTR",  # XTR = Telegram Stars
        prices=[LabeledPrice(label="Premium на 30 дней", amount=49)]
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    user_id = message.from_user.id
    set_premium(user_id, 1)
    
    await message.answer(
        "✅ Оплата прошла успешно!\n\n"
        "Твой тариф: 💎 Premium\n"
        "Теперь тебе доступны все 50 уроков и 4 теста. Открой Mini App, чтобы начать!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Открыть AI Школу", web_app=WebAppInfo(url=WEBAPP_URL))]
        ])
    )

# ==================== АДМИН-ПАНЕЛЬ ====================

@dp.message(F.text == "/admin")
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У тебя нет прав для этой команды.")
        return
    
    await message.answer(
        "👑 Админ-панель\n\n"
        "/stats - Статистика\n"
        "/give_premium <user_id> - Выдать Premium\n"
        "/take_premium <user_id> - Забрать Premium"
    )

@dp.message(F.text == "/stats")
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_premium = 1')
    premium = cursor.fetchone()[0]
    conn.close()
    
    await message.answer(f"📊 Всего пользователей: {total}\n💎 Premium: {premium}")

@dp.message(F.text.startswith("/give_premium"))
async def give_premium(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        user_id = int(message.text.split()[1])
        set_premium(user_id, 1)
        await message.answer(f"✅ Пользователь {user_id} теперь Premium!")
    except:
        await message.answer("Ошибка. Используй: /give_premium 123456789")

# ==================== ЗАПУСК ====================

async def main():
    init_db()
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
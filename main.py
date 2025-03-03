import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import config  # Файл с TOKEN и ADMIN_ID

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем бота и диспетчер
bot = Bot(token=config.TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# Хранилище заблокированных пользователей
banned_users = set()


# Состояния FSM для обработки доната
class DonationState(StatesGroup):
    waiting_for_id_and_diamonds = State()
    waiting_for_receipt = State()


# Главное меню
async def main_menu():
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📜 Прайс")],
            [types.KeyboardButton(text="💎 Донат"), types.KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )
    return keyboard


# Кнопки для пользователя после отправки чека
async def user_receipt_menu():
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Готово", callback_data="submit_receipt"),
         types.InlineKeyboardButton(text="🔄 Изменить", callback_data="redo_donation")]
    ])
    return keyboard


# Кнопки администратора (в 2 строки)
async def admin_buttons(user_id):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{user_id}"),
         types.InlineKeyboardButton(text="⏳ Ожидание", callback_data=f"waiting_{user_id}"),
         types.InlineKeyboardButton(text="❌ Отказано", callback_data=f"decline_{user_id}")],
        [types.InlineKeyboardButton(text="🚫 Бан", callback_data=f"ban_{user_id}"),
         types.InlineKeyboardButton(text="🔓 Разбан", callback_data=f"unban_{user_id}"),
         types.InlineKeyboardButton(text="✉ Связаться", url=f"tg://user?id={user_id}")]
    ])
    return keyboard


# Команда /start
@router.message(Command("start"))
async def send_welcome(message: types.Message):
    if message.from_user.id in banned_users:
        return
    await message.answer("Привет! Я чем могу помочь? ", reply_markup=await main_menu())



@router.message(F.text == "📜 Прайс")
async def send_price(message: types.Message):
    price_list = """Прайс-лист на алмазы валюта Кыргызский сом:

🌟Специальное предложение:
• Алмазный Пропуск 🌟 — 180🇰🇬
• Сумеречный Пропуск ⭐️ — 900 🇰🇬
•  78 + 8 💎 — 150 🇰🇬
•  156 + 16 💎 — 285 🇰🇬
•  234 + 23 💎 — 400 🇰🇬
•  390 + 39 💎 — 660 🇰🇬
•  625 + 81 💎 — 1050 🇰🇬
•  781 + 97 💎 — 1350 🇰🇬
•  1050 +121 💎 — 1670 🇰🇬
•  1250 + 162 💎 — 2150 🇰🇬
•  1406 + 178 💎 — 2400 🇰🇬
•  1860 + 335 💎 — 3320 🇰🇬
•  3099 + 589 💎 — 5575🇰🇬
•  4649 + 883 💎 — 8300 🇰🇬
•  7740 + 1548 💎 — 13800 🇰🇬
Если нужно еще больше алмазов 💎  пишите администраторам!!!  """
    await message.answer(price_list)

    # Обработка кнопки "❓ Помощь"
    @router.message(F.text == "❓ Помощь")
    async def send_help(message: types.Message):
        help_text = "Обратитесь к администратору @Rikokml для получения помощи."
        await message.answer(help_text)


# Кнопка "Донат"
@router.message(F.text == "💎 Донат")
async def handle_donate(message: types.Message, state: FSMContext):
    if message.from_user.id in banned_users:
        return
    await message.answer(
        "️️️❗❗❗Важно ❗❗❗\n C начало ознакомтесь с прайсом и потом \nВведите ваш ID(Server ID) \nПример: 472387(4353) количество алмазов\n(❗❗Не забудьте про пробел )")
    await state.set_state(DonationState.waiting_for_id_and_diamonds)


# Обработка ID, зоны айди и количества алмазов
@router.message(DonationState.waiting_for_id_and_diamonds, lambda message: re.match(r"^\d+\(\d+\) \d+$", message.text))
async def process_donation(message: types.Message, state: FSMContext):
    user_id_zone, diamonds = message.text.split()
    user_id = user_id_zone.split('(')[0]  # ID пользователя
    zone_id = user_id_zone.split('(')[1][:-1]  # Зона айди (удаляем закрывающую скобку)

    # Обновляем данные в состоянии
    await state.update_data(user_id=user_id, zone_id=zone_id, diamonds=diamonds)

    # Отправляем сообщение с просьбой прислать чек
    await message.answer("MBank:+996998202990 Ринат.К\nBakaiBank +996998202990  \nОтправьте доказательствавашего пополнение чека")
    await state.set_state(DonationState.waiting_for_receipt)


# Обработка чека
@router.message(DonationState.waiting_for_receipt, F.photo)
async def process_receipt(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(receipt=file_id)
    await message.answer(
        "Чтобы мы начали вашим донатом . Нажмите \"Готово\", если все верно, или \"Изменить\", чтобы ввести данные заново.",
        reply_markup=await user_receipt_menu())


# Обработка инлайн-кнопок "Отправить" и "Изменить"
@router.callback_query(F.data == "redo_donation")
async def redo_donation(call: types.CallbackQuery, state: FSMContext):
    await handle_donate(call.message, state)
    await call.answer()


@router.callback_query(F.data == "submit_receipt")
async def submit_receipt(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = call.from_user.id
    await bot.send_photo(chat_id=config.ADMIN_ID, photo=data['receipt'],
                         caption=f"Новый чек\nID: {data['user_id']}\nЗона ID: {data['zone_id']}\nАлмазов: {data['diamonds']}",
                         reply_markup=await admin_buttons(user_id))
    await call.message.answer("Чек отправлен администратору.")
    await state.clear()
    await call.answer()

# Обработка ID, зоны айди и количества алмазов
@router.message(DonationState.waiting_for_id_and_diamonds)
async def process_donation(message: types.Message, state: FSMContext):
    if not re.match(r"^\d+\(\d+\) \d+$", message.text):
        await message.answer("❌ Ошибка! Введите данные в формате:\n\n"
                             "472387(4353) 100\n(Где 472387 - ваш ID, 4353 - Server ID, 100 - количество алмазов)")
        return

    user_id_zone, diamonds = message.text.split()
    user_id = user_id_zone.split('(')[0]  # ID пользователя
    zone_id = user_id_zone.split('(')[1][:-1]  # Зона ID (удаляем закрывающую скобку)

    # Обновляем данные в состоянии
    await state.update_data(user_id=user_id, zone_id=zone_id, diamonds=diamonds)

    # Отправляем сообщение с просьбой прислать чек
    await message.answer("MBank:+996998202990 Ринат.К\nBakaiBank +996998202990  \nОтправьте доказательство вашего пополнения (чек).")
    await state.set_state(DonationState.waiting_for_receipt)

# Обработка кнопок администратора
@router.callback_query()
async def admin_callback(call: types.CallbackQuery):
    user_id = int(call.data.split('_')[1])
    if call.data.startswith("approve"):
        await bot.send_message(user_id, "✅ Ваша пополнение поступило поверьте внутриигровой аккаунт")
    elif call.data.startswith("decline"):
        await bot.send_message(user_id, "❌ Ваша пополнение не поступило свяжитесь с Администратором")
    elif call.data.startswith("ban"):
        banned_users.add(user_id)
        await bot.send_message(user_id, "🚫 Ваш аккаунт заблокирован. Обратитесь к администратору.")
    elif call.data.startswith("unban"):
        banned_users.discard(user_id)
        await bot.send_message(user_id, "🔓 Вы были разблокировали. Теперь можете пользоваться ботом.")
    elif call.data.startswith("waiting"):
        await bot.send_message(user_id, "⏳ Администратор принял ваше пополнение. Скоро вы получите ответ.")
    await call.answer()


# Запуск бота
async def main():
    dp.include_router(router)
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка запуска бота: {e}")


if __name__ == "__main__":
    asyncio.run(main())

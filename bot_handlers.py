from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import config, db, api_handlers
import datetime
import json

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Состояния для FSM (например, для ввода данных)
class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_days = State()

# Декоратор проверки подписки
def subscription_required(func):
    async def wrapper(message: Message, *args, **kwargs):
        user_id = message.from_user.id
        if db.is_admin(user_id) or db.is_subscribed(user_id):
            return await func(message, *args, **kwargs)
        else:
            await message.answer("❌ Доступ только по подписке. Обратитесь к администратору.")
    return wrapper

# Декоратор проверки админа
def admin_required(func):
    async def wrapper(message: Message, *args, **kwargs):
        if db.is_admin(message.from_user.id):
            return await func(message, *args, **kwargs)
        else:
            await message.answer("⛔ Только для администратора.")
    return wrapper

@dp.message(Command("start"))
async def start_cmd(message: Message):
    user = message.from_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    # Если это админ, даём права
    if user.id == config.ADMIN_ID:
        db.set_admin(user.id, 1)
    await message.answer("Добро пожаловать в hsCmd beta!\nИспользуйте /help для списка команд.")

@dp.message(Command("help"))
async def help_cmd(message: Message):
    text = (
        "🔍 Команды:\n"
        "/search_vk <имя> – поиск в ВК\n"
        "/search_ip <IP> – геолокация и провайдер\n"
        "/search_domain <домен> – whois\n"
        "/search_nick <ник> – проверка наличия на платформах\n"
        "/log – сделать фото через камеру (подписка)\n"
        "Админ-команды:\n"
        "/admin – панель управления\n"
        "/give_access <user_id> <дней>\n"
        "/revoke_access <user_id>\n"
        "/list_users\n"
        "/get_logs <user_id>"
    )
    await message.answer(text)

@dp.message(Command("search_vk"))
@subscription_required
async def search_vk(message: Message, command: CommandObject):
    query = command.args
    if not query:
        await message.answer("Укажите имя для поиска, например: /search_vk Иван")
        return
    data = await api_handlers.search_vk_by_name(query)
    result_text = json.dumps(data, ensure_ascii=False, indent=2)[:4000]
    db.add_log(message.from_user.id, "vk_search", query, result_text)
    await message.answer(f"Результаты поиска VK:\n{result_text}")

@dp.message(Command("search_ip"))
@subscription_required
async def search_ip(message: Message, command: CommandObject):
    ip = command.args
    if not ip:
        await message.answer("Укажите IP, например: /search_ip 8.8.8.8")
        return
    data = await api_handlers.search_by_ip(ip)
    result_text = json.dumps(data, ensure_ascii=False, indent=2)
    db.add_log(message.from_user.id, "ip_search", ip, result_text)
    await message.answer(f"Информация по IP:\n{result_text}")

@dp.message(Command("search_domain"))
@subscription_required
async def search_domain(message: Message, command: CommandObject):
    domain = command.args
    if not domain:
        await message.answer("Укажите домен, например: /search_domain example.com")
        return
    data = await api_handlers.search_by_domain(domain)
    result_text = json.dumps(data, ensure_ascii=False, indent=2)
    db.add_log(message.from_user.id, "domain_search", domain, result_text)
    await message.answer(f"Whois информация:\n{result_text}")

@dp.message(Command("search_nick"))
@subscription_required
async def search_nick(message: Message, command: CommandObject):
    nick = command.args
    if not nick:
        await message.answer("Укажите никнейм, например: /search_nick john_doe")
        return
    data = await api_handlers.search_by_nick(nick)
    result_text = json.dumps(data, ensure_ascii=False, indent=2)
    db.add_log(message.from_user.id, "nick_search", nick, result_text)
    await message.answer(f"Результаты по нику:\n{result_text}")

# -------- ЛОГГЕР (веб-приложение) ---------
@dp.message(Command("log"))
@subscription_required
async def log_cmd(message: Message):
    # Отправляем кнопку с веб-приложением (Mini App)
    web_app_url = "https://ваш-домен-на-render.com/camera"  # замените на реальный URL
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📸 Сделать снимок", web_app=types.WebAppInfo(url=web_app_url))]
        ]
    )
    await message.answer("Нажмите кнопку, чтобы открыть камеру и отправить фото.", reply_markup=keyboard)

# Обработчик получения фото из веб-приложения (через callback или напрямую)
@dp.message(F.photo)
async def handle_photo(message: Message):
    # Проверяем, что это от логгера (можно по контексту)
    user_id = message.from_user.id
    if not db.is_subscribed(user_id) and not db.is_admin(user_id):
        await message.answer("Доступ запрещён.")
        return
    # Скачиваем фото
    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    downloaded = await bot.download_file(file_path)
    # Сохраняем в папку logs
    import os, time
    os.makedirs("faces", exist_ok=True)
    filename = f"faces/{user_id}_{int(time.time())}.jpg"
    with open(filename, "wb") as f:
        f.write(downloaded.getvalue())
    # Сохраняем в лог БД
    db.add_log(user_id, "face_capture", "camera", filename)
    await message.answer("✅ Фото сохранено в лог.")

# -------- АДМИН-ПАНЕЛЬ ---------
@dp.message(Command("admin"))
@admin_required
async def admin_panel(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_list")],
        [InlineKeyboardButton(text="➕ Выдать доступ", callback_data="admin_give")],
        [InlineKeyboardButton(text="➖ Отозвать доступ", callback_data="admin_revoke")],
        [InlineKeyboardButton(text="📜 Логи пользователя", callback_data="admin_logs")]
    ])
    await message.answer("Админ-панель:", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("admin_"))
async def admin_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = callback.data
    if data == "admin_list":
        users = db.get_all_users()  # напишем функцию
        text = "Список пользователей:\n"
        for u in users:
            sub_until = datetime.datetime.fromtimestamp(u[4]).strftime("%Y-%m-%d %H:%M") if u[4] else "нет"
            admin = "✅" if u[5] else "❌"
            text += f"ID: {u[0]}, @{u[1]}, подписка до: {sub_until}, админ: {admin}\n"
        await callback.message.answer(text[:4000])
    elif data == "admin_give":
        await callback.message.answer("Введите ID пользователя и количество дней через пробел, например: 123456 30")
        await state.set_state(AdminStates.waiting_for_user_id)
    elif data == "admin_revoke":
        await callback.message.answer("Введите ID пользователя для отзыва подписки:")
        await state.set_state(AdminStates.waiting_for_user_id)  # можно отдельное состояние
    elif data == "admin_logs":
        await callback.message.answer("Введите ID пользователя для просмотра логов:")
        await state.set_state(AdminStates.waiting_for_user_id)  # будем различать по контексту

# FSM для ввода данных админом
@dp.message(AdminStates.waiting_for_user_id)
async def admin_input_user(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split()
    if len(parts) == 2 and parts[1].isdigit():
        # Даём доступ
        user_id = int(parts[0])
        days = int(parts[1])
        until = int(datetime.datetime.now().timestamp()) + days*86400
        db.update_subscription(user_id, until)
        await message.answer(f"✅ Пользователю {user_id} выдан доступ на {days} дней.")
        await state.clear()
    elif len(parts) == 1 and parts[0].isdigit():
        # Отзыв или логи – определяем по состоянию (можно сохранить в state)
        # Используем переменную в state
        data = await state.get_data()
        action = data.get("admin_action", "revoke")
        user_id = int(parts[0])
        if action == "revoke":
            db.update_subscription(user_id, 0)
            await message.answer(f"✅ Подписка пользователя {user_id} отозвана.")
        elif action == "logs":
            logs = db.get_user_logs(user_id)
            text_log = "\n".join([f"{l[1]} - {l[2]} - {l[3][:100]}" for l in logs]) if logs else "нет логов"
            await message.answer(f"Логи пользователя {user_id}:\n{text_log[:4000]}")
        await state.clear()
    else:
        await message.answer("Неверный формат. Введите ID и (если даёте доступ) количество дней.")

# Добавим обработчики для команд give_access, revoke_access, list_users, get_logs как альтернативу
@dp.message(Command("give_access"))
@admin_required
async def give_access(message: Message, command: CommandObject):
    args = command.args
    if not args:
        await message.answer("Использование: /give_access <user_id> <дней>")
        return
    parts = args.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Неверный формат.")
        return
    user_id = int(parts[0])
    days = int(parts[1])
    until = int(datetime.datetime.now().timestamp()) + days*86400
    db.update_subscription(user_id, until)
    await message.answer(f"✅ Доступ выдан.")

@dp.message(Command("revoke_access"))
@admin_required
async def revoke_access(message: Message, command: CommandObject):
    user_id = int(command.args) if command.args and command.args.isdigit() else None
    if not user_id:
        await message.answer("Укажите ID пользователя.")
        return
    db.update_subscription(user_id, 0)
    await message.answer(f"✅ Подписка отозвана.")

@dp.message(Command("list_users"))
@admin_required
async def list_users(message: Message):
    users = db.get_all_users()
    text = "Список пользователей:\n"
    for u in users:
        sub = datetime.datetime.fromtimestamp(u[4]).strftime("%Y-%m-%d %H:%M") if u[4] else "нет"
        admin = "админ" if u[5] else "пользователь"
        text += f"{u[0]} @{u[1]} – подписка до {sub} – {admin}\n"
    await message.answer(text[:4000])

@dp.message(Command("get_logs"))
@admin_required
async def get_logs(message: Message, command: CommandObject):
    user_id = int(command.args) if command.args and command.args.isdigit() else None
    if not user_id:
        await message.answer("Укажите ID пользователя.")
        return
    logs = db.get_user_logs(user_id)
    if not logs:
        await message.answer("Логов нет.")
        return
    text = "\n".join([f"{l[1]} – {l[2]} – {l[3][:200]}" for l in logs])
    await message.answer(f"Логи пользователя {user_id}:\n{text[:4000]}")

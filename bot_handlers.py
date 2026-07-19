from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import config, db, api_handlers
import datetime
import json
import os

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Состояния для FSM (админские вводы)
class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_days = State()
    waiting_for_logs_user = State()

# ---------- ДЕКОРАТОРЫ ----------
def subscription_required(func):
    async def wrapper(message: Message, *args, **kwargs):
        user_id = message.from_user.id
        if db.is_admin(user_id) or db.is_subscribed(user_id):
            return await func(message, *args, **kwargs)
        else:
            await message.answer("❌ Доступ только по подписке. Обратитесь к администратору.")
    return wrapper

def admin_required(func):
    async def wrapper(message: Message, *args, **kwargs):
        if db.is_admin(message.from_user.id):
            return await func(message, *args, **kwargs)
        else:
            await message.answer("⛔ Только для администратора.")
    return wrapper

# ---------- КОМАНДЫ ----------
@dp.message(Command("start"))
async def start_cmd(message: Message, *args, **kwargs):
    user = message.from_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    if user.id == config.ADMIN_ID:
        db.set_admin(user.id, 1)
    # Главное меню с инлайн-кнопками
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Поиск по VK", callback_data="search_vk")],
        [InlineKeyboardButton(text="🌐 Поиск по IP", callback_data="search_ip")],
        [InlineKeyboardButton(text="🏠 Поиск по домену", callback_data="search_domain")],
        [InlineKeyboardButton(text="👤 Поиск по нику", callback_data="search_nick")],
        [InlineKeyboardButton(text="📸 Логгер (фото)", callback_data="log")],
        [InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")]
    ])
    await message.answer("Добро пожаловать в hsCmd beta!\nВыберите действие:", reply_markup=kb)

@dp.message(Command("help"))
async def help_cmd(message: Message, *args, **kwargs):
    await message.answer(
        "🔍 Команды:\n"
        "/start – главное меню\n"
        "/search_vk <имя> – поиск в ВК\n"
        "/search_ip <IP> – геолокация и провайдер\n"
        "/search_domain <домен> – whois\n"
        "/search_nick <ник> – проверка наличия на платформах\n"
        "/log – сделать фото через камеру (подписка)\n"
        "Админ-команды:\n"
        "/admin – панель управления"
    )

# -------- ОБРАБОТЧИКИ ИНЛАЙН-КНОПОК (колбэки) ----------
@dp.callback_query(lambda c: c.data in ["search_vk", "search_ip", "search_domain", "search_nick", "log", "admin_panel"])
async def main_menu_callback(callback: CallbackQuery, *args, **kwargs):
    await callback.answer()
    data = callback.data
    if data == "search_vk":
        await callback.message.answer("Введите имя для поиска в ВК (например: Иван Петров)")
    elif data == "search_ip":
        await callback.message.answer("Введите IP-адрес (например: 8.8.8.8)")
    elif data == "search_domain":
        await callback.message.answer("Введите домен (например: example.com)")
    elif data == "search_nick":
        await callback.message.answer("Введите никнейм (например: john_doe)")
    elif data == "log":
        # Проверка подписки
        if not db.is_subscribed(callback.from_user.id) and not db.is_admin(callback.from_user.id):
            await callback.message.answer("❌ Требуется подписка.")
            return
        web_app_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/camera?user_id={callback.from_user.id}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📸 Сделать снимок", web_app=WebAppInfo(url=web_app_url))]
        ])
        await callback.message.answer("Нажмите кнопку, чтобы открыть камеру.", reply_markup=kb)
    elif data == "admin_panel":
        if not db.is_admin(callback.from_user.id):
            await callback.message.answer("⛔ Нет прав.")
            return
        await admin_panel_show(callback.message)

# -------- ОСНОВНЫЕ КОМАНДЫ (текстовые) ----------
@dp.message(Command("search_vk"))
@subscription_required
async def search_vk(message: Message, command: CommandObject, *args, **kwargs):
    query = command.args
    if not query:
        await message.answer("Укажите имя, например: /search_vk Иван")
        return
    data = await api_handlers.search_vk_by_name(query)
    result_text = json.dumps(data, ensure_ascii=False, indent=2)[:4000]
    db.add_log(message.from_user.id, "vk_search", query, result_text)
    await message.answer(f"Результаты поиска VK:\n{result_text}")

@dp.message(Command("search_ip"))
@subscription_required
async def search_ip(message: Message, command: CommandObject, *args, **kwargs):
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
async def search_domain(message: Message, command: CommandObject, *args, **kwargs):
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
async def search_nick(message: Message, command: CommandObject, *args, **kwargs):
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
async def log_cmd(message: Message, *args, **kwargs):
    web_app_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/camera?user_id={message.from_user.id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Сделать снимок", web_app=WebAppInfo(url=web_app_url))]
    ])
    await message.answer("Нажмите кнопку, чтобы открыть камеру.", reply_markup=kb)

# Обработчик фото (присылаемых через веб-приложение или напрямую)
@dp.message(F.photo)
async def handle_photo(message: Message, *args, **kwargs):
    user_id = message.from_user.id
    if not db.is_subscribed(user_id) and not db.is_admin(user_id):
        await message.answer("Доступ запрещён.")
        return
    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    downloaded = await bot.download_file(file_path)
    os.makedirs("faces", exist_ok=True)
    filename = f"faces/{user_id}_{int(datetime.datetime.now().timestamp())}.jpg"
    with open(filename, "wb") as f:
        f.write(downloaded.getvalue())
    db.add_log(user_id, "face_capture", "camera", filename)
    await message.answer("✅ Фото сохранено в лог.")

# -------- АДМИН-ПАНЕЛЬ ---------
@dp.message(Command("admin"))
@admin_required
async def admin_cmd(message: Message, *args, **kwargs):
    await admin_panel_show(message)

async def admin_panel_show(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_list")],
        [InlineKeyboardButton(text="➕ Выдать доступ", callback_data="admin_give")],
        [InlineKeyboardButton(text="➖ Отозвать доступ", callback_data="admin_revoke")],
        [InlineKeyboardButton(text="📜 Логи пользователя", callback_data="admin_logs")]
    ])
    await message.answer("Админ-панель:", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("admin_"))
async def admin_callback(callback: CallbackQuery, state: FSMContext, *args, **kwargs):
    await callback.answer()
    data = callback.data
    if data == "admin_list":
        users = db.get_all_users()
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
        await state.set_state(AdminStates.waiting_for_days)  # используем другое состояние
    elif data == "admin_logs":
        await callback.message.answer("Введите ID пользователя для просмотра логов:")
        await state.set_state(AdminStates.waiting_for_logs_user)

# FSM для ввода данных админом
@dp.message(StateFilter(AdminStates.waiting_for_user_id))
async def admin_input_give(message: Message, state: FSMContext, *args, **kwargs):
    text = message.text.strip()
    parts = text.split()
    if len(parts) == 2 and parts[1].isdigit():
        user_id = int(parts[0])
        days = int(parts[1])
        until = int(datetime.datetime.now().timestamp()) + days*86400
        db.update_subscription(user_id, until)
        await message.answer(f"✅ Пользователю {user_id} выдан доступ на {days} дней.")
    else:
        await message.answer("Неверный формат. Используйте: ID пробел количество дней")
    await state.clear()

@dp.message(StateFilter(AdminStates.waiting_for_days))
async def admin_input_revoke(message: Message, state: FSMContext, *args, **kwargs):
    user_id = int(message.text.strip()) if message.text.strip().isdigit() else None
    if user_id:
        db.update_subscription(user_id, 0)
        await message.answer(f"✅ Подписка пользователя {user_id} отозвана.")
    else:
        await message.answer("Введите корректный ID.")
    await state.clear()

@dp.message(StateFilter(AdminStates.waiting_for_logs_user))
async def admin_input_logs(message: Message, state: FSMContext, *args, **kwargs):
    user_id = int(message.text.strip()) if message.text.strip().isdigit() else None
    if user_id:
        logs = db.get_user_logs(user_id)
        if not logs:
            await message.answer("Логов нет.")
        else:
            text = "\n".join([f"{l[1]} – {l[2]} – {l[3][:200]}" for l in logs])
            await message.answer(f"Логи пользователя {user_id}:\n{text[:4000]}")
    else:
        await message.answer("Введите корректный ID.")
    await state.clear()

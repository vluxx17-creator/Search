from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import config, db, api_handlers
import datetime
import json
import os

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

class AdminStates(StatesGroup):
    waiting_user_id = State()
    waiting_days = State()

# ---------- ДЕКОРАТОР АДМИНА (только для админ-панели) ----------
def admin_required(func):
    async def wrapper(message: Message, *args, **kwargs):
        if db.is_admin(message.from_user.id):
            return await func(message, *args, **kwargs)
        else:
            await message.answer("⛔ <b>Только для администратора.</b>", parse_mode="HTML")
    return wrapper

# ---------- МЕНЮ ----------
def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="menu_search")],
        [InlineKeyboardButton(text="📡 Мой IP / Логер", callback_data="menu_logger")],
        [InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="menu_admin")]
    ])
    return kb

def search_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 ВК по имени", callback_data="search_vk")],
        [InlineKeyboardButton(text="🌐 IP-адрес", callback_data="search_ip")],
        [InlineKeyboardButton(text="🏠 Домен (whois)", callback_data="search_domain")],
        [InlineKeyboardButton(text="🔎 Никнейм", callback_data="search_nick")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
    ])
    return kb

def admin_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_list")],
        [InlineKeyboardButton(text="➕ Выдать подписку", callback_data="admin_give")],
        [InlineKeyboardButton(text="➖ Отозвать подписку", callback_data="admin_revoke")],
        [InlineKeyboardButton(text="📜 Логи пользователя", callback_data="admin_logs")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
    ])
    return kb

# ---------- КОМАНДЫ ----------
@dp.message(Command("start"))
async def start_cmd(message: Message):
    user = message.from_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    if user.id == config.ADMIN_ID:
        db.set_admin(user.id, 1)
    await message.answer(
        "<b>🔍 hsCmd beta — поиск по открытым источникам</b>\n\n"
        "Я умею искать:\n"
        "• 👤 Людей в ВКонтакте по имени\n"
        "• 🌐 Геолокацию и провайдера по IP\n"
        "• 🏠 Информацию о домене (whois)\n"
        "• 🔎 Никнеймы на разных платформах\n\n"
        "Также я покажу ваш IP и другую техническую информацию по команде /log.\n\n"
        "Выберите действие в меню или используйте команды:\n"
        "/search_vk <имя>\n"
        "/search_ip <IP>\n"
        "/search_domain <домен>\n"
        "/search_nick <ник>\n"
        "/log — получить отчёт о вашем подключении",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "<b>📖 Справка</b>\n\n"
        "/start – главное меню\n"
        "/search_vk <имя> – поиск людей в ВК\n"
        "/search_ip <IP> – геолокация и провайдер\n"
        "/search_domain <домен> – whois-информация\n"
        "/search_nick <ник> – поиск на платформах\n"
        "/log – показать ваш IP и данные о подключении\n\n"
        "Администратор имеет доступ к панели управления.",
        parse_mode="HTML"
    )

# ---------- ПОИСКОВЫЕ КОМАНДЫ (без подписки) ----------
@dp.message(Command("search_vk"))
async def cmd_search_vk(message: Message, command: CommandObject):
    query = command.args
    if not query:
        await message.answer("Укажите имя, например: /search_vk Иван", parse_mode="HTML")
        return
    data = await api_handlers.search_vk_by_name(query)
    await send_search_result(message, data, "VK", query)

@dp.message(Command("search_ip"))
async def cmd_search_ip(message: Message, command: CommandObject):
    query = command.args
    if not query:
        await message.answer("Укажите IP, например: /search_ip 8.8.8.8", parse_mode="HTML")
        return
    data = await api_handlers.search_by_ip(query)
    await send_search_result(message, data, "IP", query)

@dp.message(Command("search_domain"))
async def cmd_search_domain(message: Message, command: CommandObject):
    query = command.args
    if not query:
        await message.answer("Укажите домен, например: /search_domain example.com", parse_mode="HTML")
        return
    data = await api_handlers.search_by_domain(query)
    await send_search_result(message, data, "домен", query)

@dp.message(Command("search_nick"))
async def cmd_search_nick(message: Message, command: CommandObject):
    query = command.args
    if not query:
        await message.answer("Укажите никнейм, например: /search_nick john_doe", parse_mode="HTML")
        return
    data = await api_handlers.search_by_nick(query)
    await send_search_result(message, data, "никнейм", query)

@dp.message(Command("log"))
async def cmd_log(message: Message):
    await send_logger_link(message)

# ---------- ОБЩАЯ ФУНКЦИЯ ВЫВОДА РЕЗУЛЬТАТОВ ----------
async def send_search_result(message, data, search_type, query):
    if isinstance(data, dict) and "error" in data:
        output = f"<b>❌ Ошибка:</b> <code>{data['error']}</code>"
    else:
        output = f"<b>✅ Результаты поиска ({search_type}):</b>\n<pre>{json.dumps(data, ensure_ascii=False, indent=2)[:3000]}</pre>"
    output += "\n\n<blockquote>Данные получены из открытых источников.</blockquote>"
    await message.answer(output, parse_mode="HTML")
    db.add_log(message.from_user.id, f"search_{search_type}", query, output[:500])

# ---------- ЛОГЕР (ссылка на отчёт) ----------
async def send_logger_link(message):
    host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "localhost")
    link = f"https://{host}/log"
    db.add_log(message.from_user.id, "logger_link_request", link, "")
    await message.answer(
        f"<b>📡 Ваш персональный отчёт</b>\n\n"
        f"Перейдите по ссылке, чтобы увидеть ваш IP, страну, город, провайдера и другую информацию:\n"
        f"<code>{link}</code>\n\n"
        "<i>Данные будут сохранены в лог-файл.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Открыть отчёт", url=link)],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
        ]),
        parse_mode="HTML"
    )

# ---------- ОБРАБОТЧИКИ МЕНЮ (callbacks) ----------
@dp.callback_query(lambda c: c.data.startswith("menu_"))
async def menu_callback(callback: CallbackQuery):
    await callback.answer()
    data = callback.data
    if data == "menu_main":
        await callback.message.edit_text(
            "<b>🔍 hsCmd beta — главное меню</b>",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
    elif data == "menu_search":
        await callback.message.edit_text(
            "<b>🔍 Выберите тип поиска:</b>",
            reply_markup=search_menu(),
            parse_mode="HTML"
        )
    elif data == "menu_logger":
        await send_logger_link(callback.message)
    elif data == "menu_admin":
        if not db.is_admin(callback.from_user.id):
            await callback.message.answer("⛔ <b>Нет прав.</b>", parse_mode="HTML")
            return
        await callback.message.edit_text(
            "<b>⚙️ Админ-панель</b>",
            reply_markup=admin_menu(),
            parse_mode="HTML"
        )

@dp.callback_query(lambda c: c.data.startswith("search_"))
async def search_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    search_type = callback.data.replace("search_", "")
    await state.set_data({"search_type": search_type})
    prompts = {
        "vk": "Введите <b>имя</b> для поиска в ВК (например: <i>Иван Петров</i>):",
        "ip": "Введите <b>IP-адрес</b> (например: <code>8.8.8.8</code>):",
        "domain": "Введите <b>домен</b> (например: <code>example.com</code>):",
        "nick": "Введите <b>никнейм</b> (например: <i>john_doe</i>):"
    }
    await callback.message.answer(prompts.get(search_type, "Введите данные:"), parse_mode="HTML")

# ---------- ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ (для поиска после выбора типа) ----------
@dp.message(lambda message: True)
async def handle_search_input(message: Message, state: FSMContext):
    data = await state.get_data()
    search_type = data.get("search_type")
    if not search_type:
        # Если нет состояния – игнорируем (пользователь просто пишет текст)
        return
    query = message.text.strip()
    if not query:
        await message.answer("Введите непустое значение.", parse_mode="HTML")
        return

    # Выполняем поиск (без проверки подписки)
    func_map = {
        "vk": api_handlers.search_vk_by_name,
        "ip": api_handlers.search_by_ip,
        "domain": api_handlers.search_by_domain,
        "nick": api_handlers.search_by_nick
    }
    func = func_map.get(search_type)
    if not func:
        await message.answer("Неизвестный тип поиска.", parse_mode="HTML")
        await state.clear()
        return

    result = await func(query)
    await send_search_result(message, result, search_type, query)
    await state.clear()

# ---------- АДМИН-КОЛБЭКИ (с проверкой прав) ----------
@dp.callback_query(lambda c: c.data.startswith("admin_"))
async def admin_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if not db.is_admin(callback.from_user.id):
        await callback.message.answer("⛔ <b>Нет прав.</b>", parse_mode="HTML")
        return
    data = callback.data
    if data == "admin_list":
        users = db.get_all_users()
        text = "<b>Список пользователей:</b>\n"
        for u in users:
            sub = datetime.datetime.fromtimestamp(u[4]).strftime("%Y-%m-%d %H:%M") if u[4] else "нет"
            admin = "✅" if u[5] else "❌"
            text += f"<code>{u[0]}</code> @{u[1]} – подписка до {sub} – админ {admin}\n"
        await callback.message.answer(text[:4000], parse_mode="HTML")
    elif data == "admin_give":
        await callback.message.answer("Введите <b>ID пользователя</b> и <b>количество дней</b> через пробел:\n<code>123456 30</code>", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_user_id)
    elif data == "admin_revoke":
        await callback.message.answer("Введите <b>ID пользователя</b> для отзыва подписки:", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_days)
    elif data == "admin_logs":
        await callback.message.answer("Введите <b>ID пользователя</b> для просмотра логов:", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_days)

# FSM для админа
@dp.message(AdminStates.waiting_user_id)
async def admin_give_access(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) == 2 and parts[1].isdigit():
        user_id = int(parts[0])
        days = int(parts[1])
        until = int(datetime.datetime.now().timestamp()) + days*86400
        db.update_subscription(user_id, until)
        await message.answer(f"✅ <b>Пользователю {user_id} выдан доступ на {days} дней.</b>", parse_mode="HTML")
    else:
        await message.answer("Неверный формат. Используйте: <code>ID пробел количество_дней</code>", parse_mode="HTML")
    await state.clear()

@dp.message(AdminStates.waiting_days)
async def admin_revoke_or_logs(message: Message, state: FSMContext):
    user_id = int(message.text.strip()) if message.text.strip().isdigit() else None
    if not user_id:
        await message.answer("Введите корректный <b>ID</b>", parse_mode="HTML")
        return
    await message.answer("Что сделать? Напишите <b>revoke</b> для отзыва или <b>logs</b> для просмотра логов.", parse_mode="HTML")
    await state.update_data(user_id=user_id)

@dp.message(lambda message: message.text.lower() in ["revoke", "logs"])
async def admin_action_confirm(message: Message, state: FSMContext):
    action = message.text.lower()
    data = await state.get_data()
    user_id = data.get("user_id")
    if not user_id:
        await message.answer("Сначала введите ID.")
        return
    if action == "revoke":
        db.update_subscription(user_id, 0)
        await message.answer(f"✅ <b>Подписка пользователя {user_id} отозвана.</b>", parse_mode="HTML")
    elif action == "logs":
        logs = db.get_user_logs(user_id)
        if not logs:
            await message.answer("Логов нет.")
        else:
            text = "<b>Логи пользователя</b>\n"
            for l in logs[:10]:
                text += f"<code>{l[1]}</code> – {l[2]} – {l[3][:100]}\n"
            await message.answer(text[:4000], parse_mode="HTML")
    await state.clear()

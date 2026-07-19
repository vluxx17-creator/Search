import asyncio
import threading
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
import config
from bot_handlers import dp, bot
from web_app import app
import db

async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск"),
        BotCommand(command="help", description="Справка"),
        BotCommand(command="search_vk", description="Поиск в ВК"),
        BotCommand(command="search_ip", description="Поиск по IP"),
        BotCommand(command="search_domain", description="Поиск по домену"),
        BotCommand(command="search_nick", description="Поиск по нику"),
        BotCommand(command="log", description="Фото логгер"),
        BotCommand(command="admin", description="Админ-панель"),
        BotCommand(command="give_access", description="Выдать доступ"),
        BotCommand(command="revoke_access", description="Отозвать доступ"),
        BotCommand(command="list_users", description="Список пользователей"),
        BotCommand(command="get_logs", description="Логи пользователя")
    ])

async def bot_polling():
    await set_commands()
    await dp.start_polling(bot, skip_updates=True)

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    db.init_db()
    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    # Запускаем бота
    asyncio.run(bot_polling())

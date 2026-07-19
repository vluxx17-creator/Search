import asyncio
import threading
import uvicorn
import os
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
import config
from bot_handlers import dp, bot
from web_app import app
import db

async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="help", description="Справка"),
        BotCommand(command="search_vk", description="Поиск в ВК"),
        BotCommand(command="search_ip", description="Поиск по IP"),
        BotCommand(command="search_domain", description="Поиск по домену"),
        BotCommand(command="search_nick", description="Поиск по нику"),
        BotCommand(command="log", description="Мой IP / отчёт")
    ])

async def bot_polling():
    await set_commands()
    # Удаляем вебхук, чтобы избежать конфликтов
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, skip_updates=True)

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    db.init_db()
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    asyncio.run(bot_polling())

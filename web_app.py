from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import aiofiles
from aiogram import Bot
import config

app = FastAPI()
bot = Bot(token=config.BOT_TOKEN)

# Папка для статики (HTML)
app.mount("/static", StaticFiles(directory="templates"), name="static")

@app.get("/camera")
async def camera_page():
    # Возвращаем HTML с камерой
    with open("templates/camera.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html, status_code=200)

@app.post("/upload_photo")
async def upload_photo(user_id: int = Form(...), photo: UploadFile = File(...)):
    # Сохраняем фото на диск
    os.makedirs("faces", exist_ok=True)
    filename = f"faces/{user_id}_{int(time.time())}.jpg"
    async with aiofiles.open(filename, "wb") as out_file:
        content = await photo.read()
        await out_file.write(content)
    # Отправляем пользователю через бота
    try:
        await bot.send_photo(chat_id=user_id, photo=open(filename, "rb"), caption="📸 Ваше фото сохранено в логах.")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    return JSONResponse({"status": "ok", "filename": filename})

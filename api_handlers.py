import aiohttp
import asyncio
import whois
import vk_api
from vk_api import VkApi
from vk_api.exceptions import ApiError

async def search_vk_by_name(name):
    """Поиск пользователей VK по имени/фамилии"""
    try:
        vk_session = vk_api.VkApi(token=config.VK_API_TOKEN)
        vk = vk_session.get_api()
        users = vk.users.search(q=name, count=10, fields="city,country,bdate,photo_max,sex,last_seen")
        return users
    except Exception as e:
        return {"error": str(e)}

async def search_by_ip(ip):
    """Получение информации по IP через ip-api.com"""
    url = f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

async def search_by_domain(domain):
    """Whois информация о домене"""
    try:
        w = whois.whois(domain)
        return {
            "domain_name": w.domain_name,
            "registrar": w.registrar,
            "creation_date": str(w.creation_date),
            "expiration_date": str(w.expiration_date),
            "name_servers": w.name_servers,
            "emails": w.emails
        }
    except Exception as e:
        return {"error": str(e)}

async def search_by_nick(nick):
    """Поиск никнейма на популярных площадках (заглушка, можно расширить)"""
    # Используем публичный API whatsmyname.app или парсим
    # Здесь реализуем простой вариант – проверяем наличие на GitHub, Twitter, Instagram (имитация)
    results = {}
    # GitHub
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.github.com/users/{nick}") as resp:
            if resp.status == 200:
                data = await resp.json()
                results["github"] = data.get("html_url")
            else:
                results["github"] = None
        # Twitter (через v1.1 – требует OAuth, делаем заглушку)
        # Instagram – аналогично
    # Добавим VK поиск по нику
    vk_result = await search_vk_by_name(nick)
    results["vk"] = vk_result
    return results

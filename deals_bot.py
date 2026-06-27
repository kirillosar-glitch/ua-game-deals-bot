import requests
import os
import json
import base64
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHANNEL = "@ua_game_deals"
ITAD_API_KEY = os.environ["ITAD_API_KEY"]
GH_TOKEN = os.environ["GH_TOKEN"]
GH_REPO = "kirillosar-glitch/ua-game-deals-bot"
HISTORY_FILE = "published.json"

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHANNEL,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    r = requests.post(url, data=data)
    print(r.status_code, r.text[:200])

def load_history():
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{HISTORY_FILE}"
    headers = {"Authorization": f"token {GH_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        data = json.loads(content)
        sha = r.json()["sha"]
        return data, sha
    return {"published": [], "free_dates": []}, None

def save_history(history, sha):
    content = base64.b64encode(json.dumps(history, ensure_ascii=False, indent=2).encode()).decode()
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{HISTORY_FILE}"
    headers = {"Authorization": f"token {GH_TOKEN}"}
    payload = {
        "message": "Update published history",
        "content": content
    }
    if sha:
        payload["sha"] = sha
    requests.put(url, headers=headers, json=payload)

def get_candidates():
    """Отримуємо великий пул кандидатів, відсортований по популярності"""
    url = "https://api.isthereanydeal.com/deals/v2"
    params = {
        "key": ITAD_API_KEY,
        "country": "UA",
        "shops": "61",
        "limit": 100,
        "sort": "-popularity",
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        data = r.json()
        return data.get("list", [])
    except Exception as e:
        print(f"Error fetching candidates: {e}")
        return []

def get_game_info(game_id):
    """Отримуємо деталі гри: тип, metacritic, теги"""
    url = "https://api.isthereanydeal.com/games/info/v2"
    params = {"key": ITAD_API_KEY, "id": game_id}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"Error fetching game info {game_id}: {e}")
    return None

if __name__ == "__main__":
    history, sha = load_history()
    published = history.get("published", [])
    free_dates = history.get("free_dates", [])

    today = datetime.utcnow().strftime("%Y-%m-%d")
    cutoff_30 = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")

    # Очищуємо стару історію (>30 днів)
    published = [e for e in published if e["date"] >= cutoff_30]
    free_dates = [d for d in free_dates if d >= cutoff_30]
    recent_slugs = {e["slug"] for e in published}

    # Чи можна публікувати безкоштовну гру цього тижня (не більше 1-2 за 7 днів)
    cutoff_7 = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    free_count_week = len([d for d in free_dates if d >= cutoff_7])
    can_add_free = free_count_week < 2

    candidates = get_candidates()
    print(f"Got {len(candidates)} candidates")

    selected = []
    free_in_this_post = 0

    for item in candidates:
        if len(selected) >= 5:
            break

        slug = item.get("slug", "")
        if not slug or slug in recent_slugs:
            continue

        deal = item.get("deal", {})
        cut = deal.get("cut", 0)
        price = deal.get("price", {}).get("amount", 0)
        is_free = (cut == 100 or price == 0)

        # Безкоштовні - обмежуємо 1 на пост, і тільки якщо не перевищили тижневий ліміт
        if is_free:
            if free_in_this_post >= 1 or not can_add_free:
                continue

        # Перевіряємо тип гри та якість через games/info
        game_id = item.get("id", "")
        info = get_game_info(game_id)
        if not info:
            continue

        game_type = info.get("type", "game")
        if game_type != "game":
            continue  # пропускаємо DLC, soundtracks, packages

        # Перевіряємо якість: Metacritic OR хороший reception
        reviews = info.get("reviews", []) or []
        metacritic_score = None
        steam_positive = None
        for rev in reviews:
            if rev.get("source") == "metacritic":
                metacritic_score = rev.get("score")
            if rev.get("source") == "steam":
                steam_positive = rev.get("score")

        # Прохідний бал: Metacritic 70+ ИЛИ Steam reviews 75%+ ИЛИ скидка дуже висока (потенційний хайп)
        passes_quality = False
        if metacritic_score and metacritic_score >= 70:
            passes_quality = True
        elif steam_positive and steam_positive >= 75:
            passes_quality = True
        elif cut >= 60 and not is_free:
            # Високі знижки на популярні (вже відфільтровано по popularity) теж проходять
            passes_quality = True

        if not passes_quality and not is_free:
            continue
        if is_free and not (metacritic_score or steam_positive):
            # Для безкоштовних теж бажано мати хоч якийсь reception, інакше пропускаємо
            if cut == 100 and price == 0:
                pass  # дозволяємо роздачі навіть без оцінок, це рідкість і цінно
            else:
                continue

        title = item.get("title", "Невідома гра")
        currency = deal.get("price", {}).get("currency", "")
        regular = deal.get("regular", {}).get("amount", 0)
        store_url = deal.get("url", "")

        selected.append({
            "slug": slug,
            "title": title,
            "cut": cut,
            "price": price,
            "currency": currency,
            "regular": regular,
            "url": store_url,
            "is_free": is_free,
            "metacritic": metacritic_score,
            "steam_score": steam_positive
        })

        if is_free:
            free_in_this_post += 1

    print(f"Selected {len(selected)} games")

    if not selected:
        print("Нічого підходящого не знайдено, пост не публікуємо")
    else:
        lines = ["🎮 <b>Steam — топові знижки та роздачі (UA)</b>\n"]
        for g in selected:
            if g["is_free"]:
                price_str = "🆓 Безкоштовно"
            else:
                price_str = f"💰 {g['price']:.0f} {g['currency']} (було {g['regular']:.0f} {g['currency']})"

            quality_badge = ""
            if g["metacritic"]:
                quality_badge = f" | ⭐ Metacritic {g['metacritic']}"
            elif g["steam_score"]:
                quality_badge = f" | ⭐ Steam {g['steam_score']}%"

            lines.append(f"<b>{g['title']}</b>")
            lines.append(f"🔥 -{g['cut']}% | {price_str}{quality_badge}")
            lines.append(f"🔗 <a href='{g['url']}'>Отримати в Steam</a>\n")

        post = "\n".join(lines)
        send_telegram(post)

        # Зберігаємо в історію
        for g in selected:
            published.append({"slug": g["slug"], "date": today})
            if g["is_free"]:
                free_dates.append(today)

        history["published"] = published
        history["free_dates"] = free_dates
        save_history(history, sha)

    print("Готово!")

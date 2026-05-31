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
        data["_sha"] = r.json()["sha"]
        return data
    return {"published": [], "_sha": None}

def save_history(history):
    sha = history.pop("_sha", None)
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

def get_steam_deals(exclude_ids, min_cut=50, limit=20):
    url = "https://api.isthereanydeal.com/deals/v2"
    params = {
        "key": ITAD_API_KEY,
        "country": "UA",
        "shops": "61",
        "limit": limit,
        "sort": "-cut"
    }
    try:
        r = requests.get(url, params=params)
        data = r.json()
        items = data.get("list", [])

        # Фільтруємо по порогу та виключаємо вже опубліковані
        filtered = []
        for item in items:
            deal = item.get("deal", {})
            cut = deal.get("cut", 0)
            slug = item.get("slug", "")
            if cut >= min_cut and slug not in exclude_ids:
                filtered.append(item)

        # Якщо менше 5 — знижуємо поріг
        if len(filtered) < 5 and min_cut > 20:
            return get_steam_deals(exclude_ids, min_cut=min_cut-10, limit=limit)

        return filtered[:5]
    except Exception as e:
        print(f"Steam error: {e}")
        return []

def format_steam_post(items):
    if not items:
        return "🎮 <b>Steam — знижки та роздачі (UA)</b>\n\nНа жаль, зараз немає актуальних пропозицій."
    lines = ["🎮 <b>Steam — знижки та роздачі (UA)</b>\n"]
    for item in items:
        title = item.get("title", "Невідома гра")
        deal = item.get("deal", {})
        cut = deal.get("cut", 0)
        price = deal.get("price", {}).get("amount", 0)
        currency = deal.get("price", {}).get("currency", "")
        regular = deal.get("regular", {}).get("amount", 0)
        store_url = deal.get("url", "")
        if cut == 100 or price == 0:
            price_str = "🆓 Безкоштовно"
        else:
            price_str = f"💰 {price:.0f} {currency} (було {regular:.0f} {currency})"
        lines.append(f"<b>{title}</b>")
        lines.append(f"🔥 -{cut}% | {price_str}")
        lines.append(f"🔗 <a href='{store_url}'>Отримати в Steam</a>\n")
    return "\n".join(lines)

if __name__ == "__main__":
    # Завантажуємо історію
    history = load_history()
    published = history.get("published", [])

    # Визначаємо що виключити
    # Сьогодні і вчора — повний виняток
    today = datetime.utcnow().strftime("%Y-%m-%d")
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    exclude_today = set()
    exclude_yesterday = set()
    week_slugs = {}

    for entry in published:
        if entry["date"] == today:
            exclude_today.add(entry["slug"])
        if entry["date"] == yesterday:
            exclude_yesterday.add(entry["slug"])
        # Рахуємо частоту за тиждень
        entry_date = datetime.strptime(entry["date"], "%Y-%m-%d")
        if (datetime.utcnow() - entry_date).days <= 7:
            week_slugs[entry["slug"]] = week_slugs.get(entry["slug"], 0) + 1

    # Виключаємо: сьогоднішні + вчорашні
    exclude_ids = exclude_today | exclude_yesterday

    # Серед тижневих — намагаємось виключити ті що вже були більше 1 разу
    frequent = {s for s, c in week_slugs.items() if c >= 2}
    exclude_with_frequent = exclude_ids | frequent

    print(f"Excluded today: {len(exclude_today)}, yesterday: {len(exclude_yesterday)}, frequent: {len(frequent)}")

    # Отримуємо deals
    items = get_steam_deals(exclude_with_frequent)
    # Якщо після виключення частих мало — пробуємо без них
    if len(items) < 5:
        items = get_steam_deals(exclude_ids)

    # Публікуємо
    post = format_steam_post(items)
    send_telegram(post)

    # Зберігаємо в історію
    for item in items:
        slug = item.get("slug", "")
        if slug:
            published.append({"slug": slug, "date": today})

    # Чистимо старі записи (старше 14 днів)
    cutoff = (datetime.utcnow() - timedelta(days=14)).strftime("%Y-%m-%d")
    published = [e for e in published if e["date"] >= cutoff]

    history["published"] = published
    history["_sha"] = load_history().get("_sha")
    save_history(history)

    print("Готово!")

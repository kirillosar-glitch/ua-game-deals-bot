import requests
import os

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHANNEL = "@ua_game_deals"
ITAD_API_KEY = os.environ["ITAD_API_KEY"]

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

def get_steam_deals():
    url = "https://api.isthereanydeal.com/deals/v2"
    params = {
        "key": ITAD_API_KEY,
        "country": "UA",
        "shops": "61",
        "limit": 5,
        "sort": "-cut"
    }
    try:
        r = requests.get(url, params=params)
        data = r.json()
        items = data.get("list", [])
        if not items:
            return "🎮 <b>Steam — знижки та роздачі</b>\n\nНа жаль, зараз немає актуальних пропозицій."
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
    except Exception as e:
        return f"Steam: помилка ({e})"

def get_ps_deals():
    try:
        url = "https://store.playstation.com/store/api/chihiro/00_09_000/tumbler/UA/uk/999/STORE-MSF75508-PRICEDROPSCHI/1/24/az/0/PRICE/fl=withRatings/start=0/grid=true"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        print(f"PSN status: {r.status_code}")
        print(f"PSN response: {r.text[:1000]}")
        data = r.json()
        items = data.get("links", [])[:5]
        if not items:
            return "🎮 <b>PS Store — знижки та роздачі</b>\n\nНа жаль, зараз немає актуальних пропозицій."
        lines = ["🎮 <b>PS Store — знижки та роздачі (UA)</b>\n"]
        for item in items:
            title = item.get("name", "Невідома гра")
            rewards = item.get("default_sku", {}).get("rewards", [{}])
            cut = rewards[0].get("discount", 0) if rewards else 0
            price = item.get("default_sku", {}).get("display_price", "0")
            url_item = "https://store.playstation.com/uk-ua/product/" + item.get("id", "")
            if cut == 100:
                price_str = "🆓 Безкоштовно"
            else:
                price_str = f"💰 {price}"
            lines.append(f"<b>{title}</b>")
            lines.append(f"🔥 -{cut}% | {price_str}")
            lines.append(f"🔗 <a href='{url_item}'>Отримати в PS Store</a>\n")
        return "\n".join(lines)
    except Exception as e:
        return f"PS Store: помилка ({e})"

if __name__ == "__main__":
    print("Steam...")
    send_telegram(get_steam_deals())
    print("PS Store...")
    send_telegram(get_ps_deals())
    print("Готово!")

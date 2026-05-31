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

def get_deals(shop_ids, shop_name, link_text):
    url = "https://api.isthereanydeal.com/deals/v2"
    params = {
        "key": ITAD_API_KEY,
        "country": "UA",
        "shops": ",".join(str(s) for s in shop_ids),
        "limit": 5,
        "sort": "-cut"
    }
    try:
        r = requests.get(url, params=params)
        print(f"{shop_name} status: {r.status_code}")
        print(f"{shop_name} response: {r.text[:500]}")
        data = r.json()
        items = data.get("list", [])

        if not items:
            # Спробуємо без фільтра по країні
            params2 = {
                "key": ITAD_API_KEY,
                "shops": ",".join(str(s) for s in shop_ids),
                "limit": 5,
                "sort": "-cut"
            }
            r2 = requests.get(url, params=params2)
            print(f"{shop_name} fallback response: {r2.text[:500]}")
            data2 = r2.json()
            items = data2.get("list", [])

        if not items:
            return f"🎮 <b>{shop_name} — знижки та роздачі</b>\n\nНа жаль, зараз немає актуальних пропозицій."

        lines = [f"🎮 <b>{shop_name} — знижки та роздачі (UA)</b>\n"]
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
            lines.append(f"🔗 <a href='{store_url}'>{link_text}</a>\n")

        return "\n".join(lines)
    except Exception as e:
        return f"{shop_name}: помилка ({e})"

if __name__ == "__main__":
    # Steam ID = 61, PlayStation = 16
    print("Steam...")
    send_telegram(get_deals([61], "Steam", "Отримати в Steam"))
    print("PS Store...")
    send_telegram(get_deals([16], "PS Store", "Отримати в PS Store"))
    print("Готово!")

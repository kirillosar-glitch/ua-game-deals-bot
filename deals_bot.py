import requests
import os
import time

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHANNEL = "@ua_game_deals"
ITAD_API_KEY = os.environ["ITAD_API_KEY"]
APIFY_TOKEN = os.environ["APIFY_TOKEN"]

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
        # Запускаємо Apify актор
        run_url = "https://api.apify.com/v2/acts/apify~playstation-store-scraper/runs"
        headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
        payload = {
            "countryCode": "UA",
            "includeDiscounts": True,
            "sortBy": "discount",
            "maxItems": 5,
            "categoryUrl": "https://store.playstation.com/uk-ua/category/deals"
        }
        r = requests.post(run_url, json=payload, headers=headers)
        print(f"Apify start: {r.status_code} {r.text[:300]}")
        run_id = r.json().get("data", {}).get("id")
        if not run_id:
            return "PS Store: не вдалось запустити скрапер"

        # Чекаємо завершення (до 60 секунд)
        for i in range(12):
            time.sleep(5)
            status_r = requests.get(
                f"https://api.apify.com/v2/acts/apify~playstation-store-scraper/runs/{run_id}",
                headers=headers
            )
            status = status_r.json().get("data", {}).get("status")
            print(f"Apify status: {status}")
            if status == "SUCCEEDED":
                break

        # Отримуємо результати
        dataset_id = status_r.json().get("data", {}).get("defaultDatasetId")
        items_r = requests.get(
            f"https://api.apify.com/v2/datasets/{dataset_id}/items?limit=5",
            headers=headers
        )
        print(f"Apify items: {items_r.text[:500]}")
        items = items_r.json()

        if not items:
            return "🎮 <b>PS Store — знижки та роздачі</b>\n\nНа жаль, зараз немає актуальних пропозицій."

        lines = ["🎮 <b>PS Store — знижки та роздачі (UA)</b>\n"]
        for item in items:
            title = item.get("name", item.get("title", "Невідома гра"))
            cut = item.get("discountPercentage", item.get("discount", 0))
            price = item.get("price", "0")
            regular = item.get("originalPrice", item.get("basePrice", "0"))
            store_url = item.get("url", "")
            if str(cut) == "100" or str(price) in ["0", "0.00", "Free"]:
                price_str = "🆓 Безкоштовно"
            else:
                price_str = f"💰 {price} (було {regular})"
            lines.append(f"<b>{title}</b>")
            lines.append(f"🔥 -{cut}% | {price_str}")
            lines.append(f"🔗 <a href='{store_url}'>Отримати в PS Store</a>\n")
        return "\n".join(lines)
    except Exception as e:
        return f"PS Store: помилка ({e})"

if __name__ == "__main__":
    print("Steam...")
    send_telegram(get_steam_deals())
    print("PS Store...")
    send_telegram(get_ps_deals())
    print("Готово!")

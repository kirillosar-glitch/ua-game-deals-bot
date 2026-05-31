import requests
import os

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
        url = "https://web.np.playstation.com/api/graphql/v1/op"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Origin": "https://store.playstation.com",
            "Referer": "https://store.playstation.com/",
            "x-psn-store-locale-override": "ru-UA"
        }
        params = {
            "operationName": "categoryGridRetrieve",
            "variables": '{"id":"3f772501-f6f8-49b7-abac-874a88ca4897","pageArgs":{"size":5,"offset":0},"sortBy":null,"filterBy":[],"facetOptions":[]}',
            "extensions": '{"persistedQuery":{"version":1,"sha256Hash":"4e41660b6732f35c99fc5541926b7502a09557924e8c2cfebd1beb1a5c8c8f81"}}'
        }
        r = requests.get(url, headers=headers, params=params, timeout=15)
        print(f"PSN status: {r.status_code}")
        print(f"PSN response: {r.text[:2000]}")

        if r.status_code != 200:
            return "PS Store: помилка запиту"

        data = r.json()
        products = data.get("data", {}).get("categoryGridRetrieve", {}).get("products", [])

        if not products:
            return "🎮 <b>PS Store — знижки та роздачі</b>\n\nНа жаль, зараз немає актуальних пропозицій."

        lines = ["🎮 <b>PS Store — знижки та роздачі (UA)</b>\n"]
        for item in products[:5]:
            title = item.get("name", "Невідома гра")
            price_obj = item.get("price", {})
            cut = price_obj.get("discountedPrice", {}).get("discountPercentage", 0)
            price = price_obj.get("discountedPrice", {}).get("price", "0")
            regular = price_obj.get("basePrice", "0")
            product_id = item.get("id", "")
            store_url = f"https://store.playstation.com/ru-ua/product/{product_id}"

            if str(cut) == "100" or str(price) in ["0", "0.00"]:
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

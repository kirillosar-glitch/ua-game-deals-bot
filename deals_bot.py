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
        url = "https://web.np.playstation.com/api/graphql/v1/op"
        params = {
            "operationName": "categoryGridRetrieve",
            "variables": '{"id":"STORE-MSF75508-PRICEDROPSCHI","pageArgs":{"size":5,"offset":0},"sortBy":{"name":"DISCOUNT","isAscending":false},"filterBy":[],"facetOptions":[],"country":"UA","language":"uk"}',
            "extensions": '{"persistedQuery":{"version":1,"sha256Hash":"4ce7d410a4db2c8b635a48c1dcdc30c2b0b4a4a3e8e5e5e5e5e5e5e5e5e5e5e5"}}'
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "x-psn-store-locale-override": "uk-UA"
        }
        r = requests.get(url, params=params, headers=headers, timeout=15)
        print(f"PSN status: {r.status_code}")
        print(f"PSN response: {r.text[:1000]}")
        return "PS Store: тест"
    except Exception as e:
        return f"PS Store: помилка ({e})"

if __name__ == "__main__":
    print("Steam...")
    send_telegram(get_steam_deals())
    print("PS Store...")
    send_telegram(get_ps_deals())
    print("Готово!")

import requests
import os
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PRICE_FILE = "last_price.txt"

def get_hyderabad_rates():
    headers = {'User-Agent': 'Mozilla/5.0'}
    data = {"24K": "N/A", "22K": "N/A", "Silver": "N/A"}
    
    try:
        # 1. Fetch Gold Prices
        gold_url = "https://www.goodreturns.in/gold-rates/hyderabad.html"
        g_res = requests.get(gold_url, headers=headers)
        g_soup = BeautifulSoup(g_res.text, 'html.parser')
        rows = g_soup.find_all("tr")
        
        for row in rows:
            text = row.get_text()
            if "24 Carat" in text and data["24K"] == "N/A":
                data["24K"] = row.find_all("td")[1].get_text().strip()
            if "22 Carat" in text and data["22K"] == "N/A":
                data["22K"] = row.find_all("td")[1].get_text().strip()

        # 2. Fetch Silver Price
        silver_url = "https://www.goodreturns.in/silver-rates/hyderabad.html"
        s_res = requests.get(silver_url, headers=headers)
        s_soup = BeautifulSoup(s_res.text, 'html.parser')
        # Selecting the first price entry in the Hyderabad silver table
        data["Silver"] = s_soup.find("div", class_="gold_silver_table").find_all("td")[1].get_text().strip()

        return data
    except Exception as e:
        print(f"Scraping Error: {e}")
        return None

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

if __name__ == "__main__":
    current_data = get_hyderabad_rates()
    
    if current_data:
        # Create a unique string to check for changes
        current_state = f"{current_data['24K']}-{current_data['22K']}-{current_data['Silver']}"
        
        last_state = ""
        if os.path.exists(PRICE_FILE):
            with open(PRICE_FILE, "r") as f:
                last_state = f.read().strip()
        
        # Only message if prices have changed
        if current_state != last_state:
            msg = (f"💰 *Hyderabad Price Update*\n\n"
                   f"🟡 *24K Gold:* {current_data['24K']}/gm\n"
                   f"🟠 *22K Gold:* {current_data['22K']}/gm\n"
                   f"⚪ *Silver:* {current_data['Silver']}/gm\n\n"
                   f"📈 _Price updated on website._")
            send_telegram(msg)
            
            # Save new state
            with open(PRICE_FILE, "w") as f:
                f.write(current_state)
        else:
            print("No price change detected.")
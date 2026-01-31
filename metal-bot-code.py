import cloudscraper
import os
import re
import requests
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PRICE_FILE = "last_price.txt"

# Defined constants to avoid repetition
GOLD_URL = "https://www.goodreturns.in/gold-rates/hyderabad.html"
SILVER_URL = "https://www.goodreturns.in/silver-rates/hyderabad.html"

def clean_price(price_str):
    """Removes '₹', commas, and extra text. Returns clean number string."""
    if not price_str:
        return "N/A"
    match = re.search(r"[\d,]+", price_str)
    if match:
        return match.group(0)
    return price_str

def get_price_from_header(soup, header_pattern):
    """Finds a header matching the pattern, gets the next table, and finds the 1g row."""
    try:
        # Find header (h2-h4) containing the pattern
        header = soup.find(lambda tag: tag.name in ["h2", "h3", "h4"] and header_pattern.lower() in tag.get_text().lower())
        
        if header:
            table = header.find_next("table")
            if table:
                for row in table.find_all("tr"):
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        col0 = cols[0].get_text().strip().lower()
                        if col0 in ["1", "1g", "1 gram", "1 gm"]:
                            return clean_price(cols[1].get_text())
    except Exception as e:
        print(f"Error extracting {header_pattern}: {e}")
    
    return "N/A"

def get_hyderabad_rates():
    scraper = cloudscraper.create_scraper()
    data = {"24K": "N/A", "22K": "N/A", "Silver": "N/A"}

    # --- 1. FETCH GOLD ---
    try:
        print(f"📡 Fetching Gold from {GOLD_URL}...")
        res = scraper.get(GOLD_URL)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            data["24K"] = get_price_from_header(soup, "24 Carat")
            data["22K"] = get_price_from_header(soup, "22 Carat")
        else:
            print(f"❌ Gold Request Failed: {res.status_code}")
    except Exception as e:
        print(f"❌ Gold Error: {e}")

    # --- 2. FETCH SILVER ---
    try:
        print(f"📡 Fetching Silver from {SILVER_URL}...")
        res = scraper.get(SILVER_URL)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            data["Silver"] = get_price_from_header(soup, "Silver")
        else:
            print(f"❌ Silver Request Failed: {res.status_code}")
    except Exception as e:
        print(f"❌ Silver Error: {e}")

    return data

def send_telegram(message):
    if not TOKEN or not CHAT_ID:
        print("ℹ️ Telegram skipped: Missing keys.")
        return
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ Telegram Send Error: {e}")
        
def get_price_diff(current_str, last_str):
    """Calculates difference and returns formatted string with emoji."""
    try:
        curr = float(current_str.replace(",", ""))
        last = float(last_str.replace(",", ""))
        diff = curr - last
        
        if diff > 0:
            return f" (₹{int(diff)} 🔺)"
        elif diff < 0:
            return f" (₹{int(abs(diff))} 🔻)"
        return ""
    except (ValueError, AttributeError):
        return ""

if __name__ == "__main__":
    current_data = get_hyderabad_rates()
    print(f"🔎 Extracted Data: {current_data}")
    
    if current_data["24K"] != "N/A":
        current_state = f"{current_data['24K']}-{current_data['22K']}-{current_data['Silver']}"
        
        # Load last prices
        last_prices = {"24K": "N/A", "22K": "N/A", "Silver": "N/A"}
        last_state = ""
        
        if os.path.exists(PRICE_FILE):
            with open(PRICE_FILE, "r") as f:
                last_state = f.read().strip()
                parts = last_state.split("-")
                if len(parts) == 3:
                    last_prices = {"24K": parts[0], "22K": parts[1], "Silver": parts[2]}
        
        if current_state != last_state:
            # Calculate differences
            diff_24k = get_price_diff(current_data["24K"], last_prices["24K"])
            diff_22k = get_price_diff(current_data["22K"], last_prices["22K"])
            diff_silver = get_price_diff(current_data["Silver"], last_prices["Silver"])
            
            # Clean clickable links
            msg = (f"💰 *Hyderabad Price Update*\n\n"
                   f"🟡 *[24K Gold]({GOLD_URL}):* ₹{current_data['24K']}/gm{diff_24k}\n"
                   f"🟠 *[22K Gold]({GOLD_URL}):* ₹{current_data['22K']}/gm{diff_22k}\n"
                   f"⚪ *[Silver]({SILVER_URL}):* ₹{current_data['Silver']}/gm{diff_silver}\n\n"
                   f"📈 [Check Source on Website]({GOLD_URL})")
            
            print(msg) 
            send_telegram(msg)
            
            with open(PRICE_FILE, "w") as f:
                f.write(current_state)
            print("✅ Update sent to Telegram.")
        else:
            print("ℹ️ Prices unchanged.")
    else:
        print("❌ Failed to scrape valid data. Check website layout.")

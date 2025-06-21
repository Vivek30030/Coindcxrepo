
import requests
import pandas as pd
import ta
import time
import datetime
import platform
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Telegram Bot ===
BOT_TOKEN = "8148338157:AAFsiUOy9sJ9eTseiq8h_pbVamyp9wniE0s"
CHAT_ID = "819307069"

# === Google Sheets Setup ===
SHEET_NAME = "Altcoin Alerts Log"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)
client = gspread.authorize(credentials)
sheet = client.open(SHEET_NAME).sheet1

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data)
        print("📲 Telegram sent!" if response.ok else "❌ Telegram failed:", response.text)
    except Exception as e:
        print("❌ Telegram error:", e)

def alert_sound():
    if platform.system() == 'Windows':
        import winsound
        winsound.Beep(1000, 500)

def get_coindcx_usdt_pairs():
    url = "https://api.coindcx.com/exchange/v1/markets_details"
    data = requests.get(url).json()
    return [item['symbol'] for item in data if item.get('symbol', '').lower().endswith('usdt')]

def fetch_ohlcv(symbol, interval):
    url = f"https://public.coindcx.com/market_data/candles?pair={symbol}&interval={interval}&limit=200"
    data = requests.get(url).json()
    if not data: return None
    df = pd.DataFrame(data, columns=['timestamp','open','high','low','close','volume']).sort_values('timestamp')
    return df

def log_to_gsheet(timeframe, coin):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        sheet.append_row([timestamp, timeframe, coin])
        print(f"📝 Logged to Google Sheet: {coin} [{timeframe}]")
    except Exception as e:
        print("❌ Google Sheets logging error:", e)

def analyze(df):
    df['ema9'] = ta.trend.EMAIndicator(df['close'], 9).ema_indicator()
    df['ema15'] = ta.trend.EMAIndicator(df['close'], 15).ema_indicator()
    df['ema50'] = ta.trend.EMAIndicator(df['close'], 50).ema_indicator()
    df['ema200'] = ta.trend.EMAIndicator(df['close'], 200).ema_indicator()
    latest = df.iloc[-1]
    price = latest['close']
    intersects = latest['ema9'] > price > latest['ema15'] and latest['ema15'] > latest['ema50']
    supports_200 = abs(price - latest['ema200']) / latest['ema200'] < 0.01
    return intersects and supports_200

def run_scan():
    timeframes = ['5m', '15m', '30m', '1h']
    print("🚀 Starting live scan...")
    while True:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"🔁 Scan at {timestamp}")
        all_matches = []
        for tf in timeframes:
            print(f"⏱️ Timeframe: {tf}")
            matches = []
            for coin in get_coindcx_usdt_pairs():
                df = fetch_ohlcv(coin, tf)
                if df is None or len(df) < 200: continue
                df[['open','high','low','close','volume']] = df[['open','high','low','close','volume']].astype(float)
                try:
                    if analyze(df):
                        matches.append(coin)
                        log_to_gsheet(tf, coin)
                except: continue
                time.sleep(0.05)
            if matches:
                all_matches.append((tf, matches))
                print("✅ Matches:", matches)
        if all_matches:
            msg = "🚨 Alert from CoinDCX Bot:
"
            for tf, coins in all_matches:
                msg += f"
📊 {tf}:
" + "
".join([f"• {c}" for c in coins])
            send_telegram_message(msg)
            alert_sound()
        print("⏳ Waiting 90 seconds...
")
        time.sleep(90)

run_scan()

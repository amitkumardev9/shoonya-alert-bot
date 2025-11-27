import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import pytz
import os

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
TIMEFRAME = '1m' # We check 1-minute candles for precision

# --- WATCHLIST (Indices + Stocks Under ₹30) ---
WATCHLIST = [
    '^NSEI', '^NSEBANK',
    'YESBANK.NS', 'UCOBANK.NS', 'IOB.NS', 'MAHABANK.NS', 
    'CENTRALBK.NS', 'SOUTHBANK.NS', 'UJJIVANSFB.NS',
    'RPOWER.NS', 'JPPOWER.NS', 'GMRINFRA.NS', 'SUZLON.NS',
    'RTNPOWER.NS', 'SJVN.NS', 'NHPC.NS', 'IRFC.NS', 'RVNL.NS',
    'IDEA.NS', 'MTNL.NS', 'HFCL.NS', 'TRIDENT.NS',
    'BCG.NS', 'INFIBEAM.NS',
    'SAIL.NS', 'NATIONALUM.NS', 'HINDCOPPER.NS',
    'RENUKA.NS', 'BAJAJHIND.NS', 'MMTC.NS', 'NBCC.NS',
    'EASEMYTRIP.NS', 'ZOMATO.NS' 
]

# --- HOLIDAY LIST ---
NSE_HOLIDAYS = [
    '2024-12-25', '2025-01-26', '2025-03-14', '2025-03-31'
]

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.get(url, params=params)
    except Exception:
        pass

def get_ist_time():
    return datetime.now(pytz.timezone('Asia/Kolkata'))

def scan_market():
    print(f"Scanning at {get_ist_time().strftime('%H:%M:%S')}")
    try:
        # Download last 1 day of data (enough for indicators)
        data = yf.download(WATCHLIST, period='1d', interval=TIMEFRAME, group_by='ticker', progress=False)
        
        for ticker in WATCHLIST:
            try:
                if len(WATCHLIST) == 1: df = data
                else: df = data[ticker]
                
                if df.empty or len(df) < 200: continue

                # Calculate EMAs
                df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
                df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
                
                # --- CCTV LOGIC (Check Last 5 Candles) ---
                # This catches any signal that happened while the bot was sleeping
                last_5_candles = df.iloc[-6:-1] 

                for i in range(len(last_5_candles) - 1):
                    prev = last_5_candles.iloc[i]
                    curr = last_5_candles.iloc[i+1]
                    
                    p_ema9 = float(prev['EMA9'])
                    p_ema21 = float(prev['EMA21'])
                    c_ema9 = float(curr['EMA9'])
                    c_ema21 = float(curr['EMA21'])
                    price = round(float(curr['Close']), 2)
                    
                    # Filter: Only alert if price < 30 (Indices ignored)
                    if not ticker.startswith('^') and price > 30: continue

                    ticker_clean = ticker.replace('.NS', '').replace('^', '')
                    candle_time = curr.name.strftime('%H:%M')

                    # BUY SIGNAL
                    if p_ema9 < p_ema21 and c_ema9 > c_ema21:
                        msg = f"🚀 <b>BUY ALERT: {ticker_clean}</b>\nPrice: ₹{price}\nTime: {candle_time}\nLogic: EMA 9 Cross UP"
                        send_telegram(msg)
                        break # Stop checking this stock to avoid duplicate spam

                    # SELL SIGNAL
                    elif p_ema9 > p_ema21 and c_ema9 < c_ema21:
                        msg = f"🔻 <b>SELL ALERT: {ticker_clean}</b>\nPrice: ₹{price}\nTime: {candle_time}\nLogic: EMA 9 Cross DOWN"
                        send_telegram(msg)
                        break

            except Exception: continue
    except Exception: pass

if __name__ == "__main__":
    now = get_ist_time()
    today = now.strftime('%Y-%m-%d')
    
    # Check Holiday
    if today in NSE_HOLIDAYS:
        print("Holiday. Exiting.")
        exit()

    # Check Market Hours (9:00 AM to 3:30 PM)
    # We start at 9:00 to catch the opening bell
    if 9 <= now.hour <= 15:
        # If it's 3:30 PM+, don't run
        if now.hour == 15 and now.minute > 30:
            print("Market Closed.")
        else:
            scan_market()
    else:
        print("Outside Market Hours.")

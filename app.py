import os
import time
from datetime import datetime, timedelta
from flask import Flask, render_template_string, redirect, url_for
import requests

app = Flask(__name__)

HISTORY_FILE = "signals_history.txt"
SYMBOL = "BTCUSDT"
LIMIT = 100

def get_binance_klines(interval, limit=LIMIT):
    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={interval}&limit={limit}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

@app.route('/')
def home():
    return "Crypto Trading Bot is Running 24/7!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
  

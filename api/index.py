import time
from datetime import datetime
from flask import Flask, render_template_string, request
import urllib.request
import json
import xml.etree.ElementTree as ET

app = Flask(__name__)

SYMBOL = "BTCUSDT"
LIMIT = 100

def get_binance_klines(interval, limit=LIMIT):
    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={interval}&limit={limit}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching klines: {e}")
    return None

def get_market_data():
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={SYMBOL}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                change_pct = float(data.get('priceChangePercent', 0))
                current_price = float(data.get('lastPrice', 0))
                return change_pct, current_price
    except Exception as e:
        print(f"Error fetching market data: {e}")
    return 0.0, 0.0

def fetch_latest_crypto_news():
    rss_url = "https://cointelegraph.com/rss"
    req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                root = ET.fromstring(response.read())
                items = root.findall('.//item')
                if items:
                    return items[0].find('title').text
    except Exception as e:
        print(f"Error fetching news: {e}")
    return "لا توجد أخبار جديدة حالياً"

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(closes):
    if len(closes) < 35:
        return 0, 0, 0
    e12 = sum(closes[:12]) / 12
    e26 = sum(closes[:26]) / 26
    mult12 = 2 / 13
    mult26 = 2 / 27
    mult9 = 2 / 10
    
    ema12, ema26 = [], []
    for i, p in enumerate(closes):
        if i >= 12:
            e12 = (p - e12) * mult12 + e12
        if i >= 26:
            e26 = (p - e26) * mult26 + e26
        if i >= 25:
            ema12.append(e12)
            ema26.append(e26)
            
    dif_list = [a - b for a, b in zip(ema12, ema26)]
    if not dif_list:
        return 0, 0, 0
    dea = sum(dif_list[:9]) / min(9, len(dif_list))
    for val in dif_list[9:]:
        dea = (val - dea) * mult9 + dea
    dif = dif_list[-1]
    return round(dif, 2), round(dea, 2), round(dif - dea, 2)

@app.route("/")
def index():
    tf = request.args.get("tf", "15m")
    klines = get_binance_klines(tf, limit=100)
    change_24h, current_price = get_market_data()
    news_title = fetch_latest_crypto_news()
    
    rsi = 50.0
    macd_hist = 0.0
    support_val, resistance_val = 0.0, 0.0
    has_signal = "false"

    if klines and len(klines) > 30:
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines[-20:]]
        lows = [float(k[3]) for k in klines[-20:]]
        rsi = round(calculate_rsi(closes), 2)
        _, _, macd_hist = calculate_macd(closes)
        support_val, resistance_val = min(lows), max(highs)
        
        if rsi > 70 or rsi < 30:
            has_signal = "true"

    rsi_pct = min(max(rsi, 0), 100)

    return render_template_string(HTML_TEMPLATE, 
                                 price=current_price, 
                                 change_24h=change_24h,
                                 rsi=rsi,
                                 rsi_pct=rsi_pct,
                                 macd_hist=macd_hist,
                                 support_val=support_val,
                                 resistance_val=resistance_val,
                                 latest_news=news_title,
                                 current_tf=tf,
                                 has_signal=has_signal)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>منصة سكالبينج الثنائية</title>
    <style>
        body { background-color: #121212; color: #e0e0e0; font-family: Tahoma, sans-serif; padding: 10px; margin: 0; }
        .card { background: #1e1e1e; padding: 12px; border-radius: 10px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .price { font-size: 20px; font-weight: bold; color: #4CAF50; text-align: center; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .box { background: #2a2a2a; padding: 10px; border-radius: 8px; text-align: center; font-size: 13px; }
        .news-box { background: #1a2634; padding: 10px; border-radius: 8px; font-size: 12px; color: #64B5F6; margin-bottom: 12px; border: 1px solid #1E88E5; }
        .tf-select { background: #2a2a2a; color: #fff; padding: 6px; border-radius: 6px; border: 1px solid #444; font-size: 13px; }
        .alert-btn { background: #ff9800; color: #000; border: none; padding: 6px 10px; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 12px; }
        .progress-bar { background: #333; border-radius: 4px; height: 6px; width: 100%; margin-top: 6px; overflow: hidden; }
        .progress-fill { background: #ff9800; height: 100%; width: {{ rsi_pct }}%; }
    </style>
    <meta http-equiv="refresh" content="15">
    <script>
        function playBeep() {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(880, ctx.currentTime);
                gain.gain.setValueAtTime(0.1, ctx.currentTime);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.4);
            } catch(e) {}
        }
        window.onload = function() {
            if("{{ has_signal }}" === "true") { playBeep(); }
        };
    </script>
</head>
<body>
    <div class="card" style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <div style="font-size: 10px; color: #aaa;">الفريم الزمني:</div>
            <select class="tf-select" onchange="location.href='/?tf='+this.value">
                <option value="1m" {% if current_tf == '1m' %}selected{% endif %}>1 دقيقة</option>
                <option value="5m" {% if current_tf == '5m' %}selected{% endif %}>5 دقائق</option>
                <option value="15m" {% if current_tf == '15m' %}selected{% endif %}>15 دقيقة</option>
                <option value="1h" {% if current_tf == '1h' %}selected{% endif %}>ساعة (1h)</option>
            </select>
        </div>
        <div><button class="alert-btn" onclick="playBeep()">🔊 اختبار الصوت</button></div>
        <div style="text-align: left;">
            <div style="font-size: 11px; color: #aaa;">BTC/USDT <span style="color: {{ 'green' if change_24h >= 0 else 'red' }};">({{ '+' if change_24h >= 0 else '' }}{{ change_24h }}%)</span></div>
            <div class="price">${{ price }}</div>
        </div>
    </div>

    <div class="news-box">
        <b>📰 آخر خبر:</b><br><span>{{ latest_news }}</span>
    </div>

    <div class="grid">
        <div class="box">
            <div>مؤشر RSI</div>
            <div style="font-size: 16px; font-weight: bold; color: #ff9800; margin-top: 4px;">{{ rsi }}</div>
            <div class="progress-bar"><div class="progress-fill"></div></div>
        </div>
        <div class="box">
            <div>مؤشر MACD Hist</div>
            <div style="font-size: 14px; font-weight: bold; color: {{ 'green' if macd_hist > 0 else 'red' }}; margin-top: 4px;">{{ macd_hist }}</div>
        </div>
        <div class="box" style="grid-column: span 2;">
            <div>الدعم والمقاومة</div>
            <div style="display: flex; justify-content: space-around; margin-top: 5px;">
                <span style="color: #4CAF50;">دعم: ${{ support_val }}</span>
                <span style="color: #f44336;">مقاومة: ${{ resistance_val }}</span>
            </div>
        </div>
    </div>
</body>
</html>
"""

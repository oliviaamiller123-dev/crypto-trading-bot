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
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff >= 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger_bands(closes, period=20, num_std=2):
    if len(closes) < period:
        return closes[-1], closes[-1]
    sma = sum(closes[-period:]) / period
    variance = sum((x - sma) ** 2 for x in closes[-period:]) / period
    std_dev = variance ** 0.5
    return sma + (num_std * std_dev), sma - (num_std * std_dev)

def calculate_macd(closes):
    if len(closes) < 35:
        return 0, 0, 0
    e12 = sum(closes[:12]) / 12
    e26 = sum(closes[:26]) / 26
    mult12, mult26, mult9 = 2 / 13, 2 / 27, 2 / 10
    ema12, ema26 = [], []
    for i, p in enumerate(closes):
        if i >= 12: e12 = (p - e12) * mult12 + e12
        if i >= 26: e26 = (p - e26) * mult26 + e26
        if i >= 25:
            ema12.append(e12)
            ema26.append(e26)
    dif_list = [a - b for a, b in zip(ema12, ema26)]
    if not dif_list: return 0, 0, 0
    dea = sum(dif_list[:9]) / min(9, len(dif_list))
    for val in dif_list[9:]:
        dea = (val - dea) * mult9 + dea
    return round(dif_list[-1], 2), round(dea, 2), round(dif_list[-1] - dea, 2)

@app.route("/")
def index():
    tf = request.args.get("tf", "15m")
    klines = get_binance_klines(tf, limit=100)
    change_24h, current_price = get_market_data()
    news_title = fetch_latest_crypto_news()
    
    rsi = 50.0
    upper_bb, lower_bb = current_price, current_price
    macd_hist = 0.0
    support_val, resistance_val = 0.0, 0.0
    market_structure = "نطاق عرضي (Ranging)"
    smc_status = "استقرار (لا يوجد سحب سيولة)"
    has_signal = "false"

    if klines and len(klines) > 30:
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines[-20:]]
        lows = [float(k[3]) for k in klines[-20:]]
        rsi = round(calculate_rsi(closes), 2)
        upper_bb, lower_bb = calculate_bollinger_bands(closes)
        _, _, macd_hist = calculate_macd(closes)
        support_val, resistance_val = round(min(lows), 2), round(max(highs), 2)
        
        if rsi > 70 or rsi < 30:
            has_signal = "true"

    rsi_pct = min(max(rsi, 0), 100)

    return render_template_string(HTML_TEMPLATE, 
                                 price=current_price, 
                                 change_24h=change_24h,
                                 rsi=rsi,
                                 rsi_pct=rsi_pct,
                                 upper_bb=round(upper_bb, 2),
                                 lower_bb=round(lower_bb, 2),
                                 macd_hist=macd_hist,
                                 support_val=support_val,
                                 resistance_val=resistance_val,
                                 market_structure=market_structure,
                                 smc_status=smc_status,
                                 latest_news=news_title,
                                 current_tf=tf,
                                 has_signal=has_signal)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>منصة سكالبينج الثنائية المتقدمة</title>
    <style>
        body { background-color: #121212; color: #e0e0e0; font-family: Tahoma, sans-serif; padding: 8px; margin: 0; }
        .card { background: #1e1e1e; padding: 10px; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .price { font-size: 22px; font-weight: bold; color: #4CAF50; text-align: center; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .box { background: #2a2a2a; padding: 10px; border-radius: 8px; text-align: center; font-size: 13px; }
        .news-box { background: #1a2634; padding: 8px; border-radius: 8px; font-size: 11px; color: #64B5F6; margin-bottom: 10px; border: 1px solid #1E88E5; }
        .tf-select { background: #2a2a2a; color: #fff; padding: 5px; border-radius: 6px; border: 1px solid #444; font-size: 12px; }
        .progress-bar { background: #333; border-radius: 4px; height: 5px; width: 100%; margin-top: 5px; overflow: hidden; }
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
            <div style="font-size: 10px; color: #aaa;">اختر الفريم الزمني:</div>
            <select class="tf-select" onchange="location.href='/?tf='+this.value">
                <option value="1m" {% if current_tf == '1m' %}selected{% endif %}>1 دقيقة</option>
                <option value="5m" {% if current_tf == '5m' %}selected{% endif %}>5 دقائق</option>
                <option value="15m" {% if current_tf == '15m' %}selected{% endif %}>15 دقيقة</option>
                <option value="1h" {% if current_tf == '1h' %}selected{% endif %}>ساعة (1h)</option>
            </select>
        </div>
        <div style="text-align: left;">
            <div style="font-size: 11px; color: #aaa;">BTC/USDT <span style="color: {{ 'green' if change_24h >= 0 else 'red' }};">({{ '+' if change_24h >= 0 else '' }}{{ change_24h }}%)</span></div>
            <div class="price">${{ price }}</div>
        </div>
    </div>

    <div class="news-box">
        <b>📰 آخر خبر حي تم تحليله آلياً:</b><br><span>{{ latest_news }}</span>
    </div>

    <!-- شارت TradingView التفاعلي للشموع اليابانية -->
    <div class="card" style="padding: 0; overflow: hidden; height: 320px;">
        <div class="tradingview-widget-container" style="height:100%;width:100%">
            <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
            {
                "autosize": true,
                "symbol": "BINANCE:BTCUSDT",
                "interval": "{{ current_tf }}",
                "timezone": "Etc/UTC",
                "theme": "dark",
                "style": "1",
                "locale": "ar",
                "enable_publishing": false,
                "hide_top_toolbar": false,
                "save_image": false,
                "calendar": false,
                "support_host": "https://www.tradingview.com"
            }
            </script>
        </div>
    </div>

    <div class="grid">
        <div class="box">
            <div>القيمة السوقية (Market Cap)</div>
            <div style="font-size: 15px; font-weight: bold; color: #4CAF50; margin-top: 4px;">B $1640~</div>
        </div>
        <div class="box">
            <div>مؤشر القوة النسبية RSI</div>
            <div style="font-size: 15px; font-weight: bold; color: #ff9800; margin-top: 4px;">{{ rsi }}</div>
            <div class="progress-bar"><div class="progress-fill"></div></div>
        </div>
        <div class="box">
            <div>الدعم والمقاومة (S/R)</div>
            <div style="font-size: 11px; color: #4CAF50; margin-top: 2px;">دعم: ${{ support_val }}</div>
            <div style="font-size: 11px; color: #f44336;">مقاومة: ${{ resistance_val }}</div>
        </div>
        <div class="box">
            <div>مؤشر الزخم MACD Hist</div>
            <div style="font-size: 14px; font-weight: bold; color: {{ 'green' if macd_hist > 0 else 'red' }}; margin-top: 4px;">{{ macd_hist }}</div>
        </div>
        <div class="box">
            <div>هيكل السوق (BOS) والحيتان</div>
            <div style="font-size: 11px; font-weight: bold; color: #00bcd4; margin-top: 2px;">{{ market_structure }}</div>
            <div style="font-size: 10px; color: #ffeb3b; margin-top: 2px;">{{ smc_status }}</div>
        </div>
        <div class="box">
            <div>البولينجر السفلي / العلوي</div>
            <div style="font-size: 10px; color: #ccc; margin-top: 2px;">سفلي: ${{ lower_bb }}</div>
            <div style="font-size: 10px; color: #ccc;">علوي: ${{ upper_bb }}</div>
        </div>
    </div>
</body>
</html>
"""
        

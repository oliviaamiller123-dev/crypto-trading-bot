import os
import time
from datetime import datetime
from flask import Flask, render_template_string, request
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

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

def get_market_data():
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={SYMBOL}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            change_pct = float(data.get('priceChangePercent', 0))
            current_price = float(data.get('lastPrice', 0))
            return change_pct, current_price
    except Exception:
        pass
    return 0.0, 0.0

def fetch_latest_crypto_news():
    rss_url = "https://cointelegraph.com/rss"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(rss_url, headers=headers, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            if items:
                latest_title = items[0].find('title').text
                return latest_title
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

def calculate_bollinger_bands(closes, period=20, num_std=2):
    if len(closes) < period:
        return closes[-1], closes[-1]
    sma = sum(closes[-period:]) / period
    variance = sum((x - sma) ** 2 for x in closes[-period:]) / period
    std_dev = variance ** 0.5
    upper_band = sma + (num_std * std_dev)
    lower_band = sma - (num_std * std_dev)
    return upper_band, lower_band

def calculate_macd(closes):
    if len(closes) < 35:
        return 0, 0, 0
    
    ema12_list = []
    ema26_list = []
    multiplier12 = 2 / (12 + 1)
    multiplier26 = 2 / (26 + 1)
    
    e12 = sum(closes[:12]) / 12
    e26 = sum(closes[:26]) / 26
    
    for i, price in enumerate(closes):
        if i >= 12:
            e12 = (price - e12) * multiplier12 + e12
        if i >= 26:
            e26 = (price - e26) * multiplier26 + e26
        if i >= 25:
            ema12_list.append(e12)
            ema26_list.append(e26)
            
    dif_list = [e12 - e26 for e12, e26 in zip(ema12_list, ema26_list)]
    if len(dif_list) < 9:
        return dif_list[-1], 0, 0
        
    multiplier9 = 2 / (9 + 1)
    dea = sum(dif_list[:9]) / 9
    for val in dif_list[9:]:
        dea = (val - dea) * multiplier9 + dea
        
    dif = dif_list[-1]
    macd_hist = dif - dea
    return round(dif, 2), round(dea, 2), round(macd_hist, 2)

def calculate_support_resistance(klines):
    if len(klines) < 20:
        return 0, 0
    highs = [float(k[2]) for k in klines[-20:]]
    lows = [float(k[3]) for k in klines[-20:]]
    return min(lows), max(highs)

def analyze_market_structure(closes):
    if len(closes) < 20:
        return "نطاق عرضي (Ranging)"
    recent_high = max(closes[-20:])
    recent_low = min(closes[-20:])
    current_close = closes[-1]
    if current_close >= recent_high * 0.998:
        return "كسر صاعد (BOS) 🟢"
    elif current_close <= recent_low * 1.002:
        return "كسر هابط (BOS) 🔴"
    return "نطاق عرضي (Ranging)"

def analyze_smart_money_concepts(klines):
    if len(klines) < 25:
        return "ترصد مناطق السيولة", False
    highs = [float(k[2]) for k in klines[-25:-1]]
    lows = [float(k[3]) for k in klines[-25:-1]]
    prev_high = max(highs)
    prev_low = min(lows)
    
    curr_low = float(klines[-1][3])
    curr_high = float(klines[-1][2])
    curr_close = float(klines[-1][4])
    
    if curr_low < prev_low and curr_close > prev_low:
        return "SM_SWEEP_LONG (اختراق وهمي للدعم - فرصة صعود) 🚀", True
    elif curr_high > prev_high and curr_close < prev_high:
        return "SM_SWEEP_SHORT (اختراق وهمي للمقاومة - فرصة هبوط) 🩸", True
    return "استقرار (لا يوجد سحب سيولة)", False

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
    market_structure = "جاري التحليل..."
    smc_status = "جاري الفحص..."
    has_signal = "false"

    if klines and len(klines) > 30:
        closes = [float(k[4]) for k in klines]
        rsi = round(calculate_rsi(closes, period=14), 2)
        upper_bb, lower_bb = calculate_bollinger_bands(closes, period=20, num_std=2)
        upper_bb = round(upper_bb, 2)
        lower_bb = round(lower_bb, 2)
        _, _, macd_hist = calculate_macd(closes)
        support_val, resistance_val = calculate_support_resistance(klines)
        market_structure = analyze_market_structure(closes)
        smc_status, is_smc_triggered = analyze_smart_money_concepts(klines)
        
        if "كسر" in market_structure or is_smc_triggered or rsi > 70 or rsi < 30:
            has_signal = "true"

    rsi_pct = min(max(rsi, 0), 100)
    
    history = [
        {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "type": "التنبيهات الصوتية", "details": "النظام الصوتي مفعل وجاهز لإطلاق صافرة التنبيه عند صفقات الصعود والهبوط", "status": "نشط 🔔"}
    ]

    return render_template_string(HTML_TEMPLATE, 
                                 price=current_price, 
                                 change_24h=change_24h,
                                 rsi=rsi,
                                 rsi_pct=rsi_pct,
                                 macd_hist=macd_hist,
                                 support_val=support_val,
                                 resistance_val=resistance_val,
                                 lower_bb=lower_bb,
                                 upper_bb=upper_bb,
                                 market_structure=market_structure,
                                 smc_status=smc_status,
                                 latest_news=news_title,
                                 history=history,
                                 current_tf=tf,
                                 has_signal=has_signal)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>منصة سكالبينج الثنائية مع التنبيه الصوتي</title>
    <style>
        body { background-color: #121212; color: #e0e0e0; font-family: Tahoma, sans-serif; padding: 10px; margin: 0; }
        .card { background: #1e1e1e; padding: 12px; border-radius: 10px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .price { font-size: 24px; font-weight: bold; color: #4CAF50; text-align: center; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .box { background: #2a2a2a; padding: 10px; border-radius: 8px; text-align: center; font-size: 13px; }
        .news-box { background: #1a2634; padding: 10px; border-radius: 8px; text-align: right; font-size: 12px; color: #64B5F6; margin-bottom: 12px; border: 1px solid #1E88E5; }
        .history-item { background: #252525; padding: 8px; margin-bottom: 8px; border-radius: 6px; font-size: 12px; border-right: 4px solid #2196F3; }
        .tf-select { background: #2a2a2a; color: #fff; padding: 6px 10px; border-radius: 6px; border: 1px solid #444; font-size: 13px; cursor: pointer; }
        .alert-btn { background: #ff9800; color: #000; border: none; padding: 6px 12px; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 12px; }
        .progress-bar-container { background: #333; border-radius: 4px; height: 6px; width: 100%; margin-top: 6px; overflow: hidden; }
        .progress-bar-fill { background: #ff9800; height: 100%; width: {{ rsi_pct }}%; }
    </style>
    <meta http-equiv="refresh" content="15">
    <script>
        function playBeep() {
            try {
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();
                
                oscillator.type = 'sine';
                oscillator.frequency.setValueAtTime(880, audioCtx.currentTime);
                gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
                
                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);
                
                oscillator.start();
                oscillator.stop(audioCtx.currentTime + 0.4);
            } catch(e) {
                console.log("Audio not allowed yet");
            }
        }

        window.onload = function() {
            var signalDetected = "{{ has_signal }}";
            if(signalDetected === "true") {
                playBeep();
            }
        };
    </script>
</head>
<body>
    <div class="card" style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <div style="font-size: 10px; color: #aaa; margin-bottom: 3px;">الفريم الزمني:</div>
            <select class="tf-select" id="timeframeSelect" onchange="location.href='/?tf='+this.value">
                <option value="1m" {% if current_tf == '1m' %}selected{% endif %}>1 دقيقة</option>
                <option value="5m" {% if current_tf == '5m' %}selected{% endif %}>5 دقائق</option>
                <option value="15m" {% if current_tf == '15m' %}selected{% endif %}>15 دقيقة</option>
                <option value="30m" {% if current_tf == '30m' %}selected{% endif %}>30 دقيقة</option>
                <option value="1h" {% if current_tf == '1h' %}selected{% endif %}>ساعة (1h)</option>
                <option value="4h" {% if current_tf == '4h' %}selected{% endif %}>4 ساعات</option>
            </select>
        </div>
        <div>
            <button class="alert-btn" onclick="playBeep()">🔊 اختبار التنبيه الصوتي</button>
        </div>
        <div style="text-align: left;">
            <div style="font-size: 11px; color: #aaa;">BTC/USDT <span style="color: {{ 'green' if change_24h >= 0 else 'red' }};">({{ '+' if change_24h >= 0 else '' }}{{ change_24h }}%)</span></div>
            <div class="price" style="font-size: 18px;">${{ price }}</div>
        </div>
    </div>

    <div class="news-box">
        <b>📰 آخر خبر تم تحليله:</b><br>
        <span>{{ latest_news }}</span>
    </div>

    <div class="grid">
        <div class="box">
            <div>مؤشر القوة النسبية RSI</div>
            <div style="font-size: 17px; font-weight: bold; color: #ff9800; margin-top: 4px;">{{ rsi }}</div>
            <div class="progress-bar-container"><div class="progress-bar-fill"></div></div>
        </div>
        <div class="box">
            <div>مؤشر الزخم MACD Hist</div>
            <div style="font-size: 15px; font-weight: bold; color: {{ 'green' if macd_hist > 0 else 'red' }}; margin-top: 4px;">{{ macd_hist }}</div>
        </div>
        <div class="box">
            <div>الدعم والمقاومة</div>
            <div style="font-size: 11px; color: #4CAF50; margin-top: 2px;">دعم: ${{ support_val }}</div>
            <div style="font-size: 11px; color: #f44336;">مقاومة: ${{ resistance_val }}</div>
        </div>
        <div class="box">
            <div>هيكل السوق والسيولة</div>
            <div style="font-size: 11px; font-weight: bold; color: #00bcd4; margin-top: 2px;">{{ market_structure }}</div>
            <div style="font-size: 10px; color: #ffeb3b; margin-top: 2px;">{{ smc_status }}</div>
        </div>
    </div>

    <div class="card">
        <div style="font-size: 13px; font-weight: bold; margin-bottom: 6px; color: #ff9800;">📋 السجل وحالة التنبيهات:</div>
        {% for item in history %}
        <div class="history-item">
            <div style="display: flex; justify-content: space-between; color: #aaa; font-size: 10px;">
                <span>{{ item.time }}</span>
                <span style="color: #4CAF50; font-weight: bold;">{{ item.status }}</span>
            </div>
            <div style="margin-top: 4px; font-weight: bold;">{{ item.type }}</div>
            <div style="font-size: 11px; color: #ccc; margin-top: 2px;">{{ item.details }}</div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""
    

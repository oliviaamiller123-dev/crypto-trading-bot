import os
import time
from datetime import datetime, timedelta
from flask import Flask, render_template_string, redirect, url_for, request
import requests
import xml.etree.ElementTree as ET

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

def analyze_news_sentiment(title):
    bullish_keywords = ['bullish', 'surge', 'breakout', 'approval', 'partnership', 'pump', 'high', 'gain', 'rally', 'adoption']
    bearish_keywords = ['crash', 'drop', 'ban', 'hack', 'lawsuit', 'bearish', 'fall', 'loss', 'dump', 'slump']
    
    title_lower = title.lower()
    score = 0
    for word in bullish_keywords:
        if word in title_lower:
            score += 1
    for word in bearish_keywords:
        if word in title_lower:
            score -= 1
            
    if score > 0:
        return "BULLISH", title
    elif score < 0:
        return "BEARISH", title
    return "NEUTRAL", title

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

def calculate_ema(closes, period=50):
    if len(closes) < period:
        return closes[-1]
    multiplier = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

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
        return "SM_SWEEP_LONG (اختراق وهمي للدعم المؤكد بإغلاق) 🚀", True
    elif curr_high > prev_high and curr_close < prev_high:
        return "SM_SWEEP_SHORT (اختراق وهمي للمقاومة المؤكد بإغلاق) 🩸", True
    return "استقرار (لا يوجد سحب سيولة)", False

def check_multi_timeframe_trend(current_tf):
    higher_tf = "4h"
    if current_tf == "4h":
        higher_tf = "1d"
    elif current_tf == "1h":
        higher_tf = "4h"
    
    klines_htf = get_binance_klines(higher_tf, limit=50)
    if not klines_htf:
        return "NEUTRAL"
    
    closes_htf = [float(k[4]) for k in klines_htf]
    ema_htf = calculate_ema(closes_htf, period=50)
    current_htf_price = closes_htf[-1]
    
    if current_htf_price > ema_htf:
        return "BULLISH"
    elif current_htf_price < ema_htf:
        return "BEARISH"
    return "NEUTRAL"

def check_fair_value_gap(klines):
    if len(klines) < 3:
        return "لا يوجد FVG"
    curr_low = float(klines[-1][3])
    prev_prev_high = float(klines[-3][2])
    curr_high = float(klines[-1][2])
    prev_prev_low = float(klines[-3][3])
    if curr_low > prev_prev_high:
        return "Bullish FVG نشط 🟢"
    elif curr_high < prev_prev_low:
        return "Bearish FVG نشط 🔴"
    return "استقرار (لا يوجد FVG)"

def has_active_signal():
    if not os.path.exists(HISTORY_FILE):
        return False
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "قيد التتبع ⏳" in line or "محمية 🛡️" in line:
                    return True
    except Exception:
        pass
    return False

def save_signal(signal_type, entry_price, target_price, stop_loss):
    if has_active_signal():
        return False 
        
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{now} | {signal_type} | الدخول: ${entry_price:.2f} | الهدف: ${target_price:.2f} | الوقف: ${stop_loss:.2f} | قيد التتبع ⏳\n"
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(line)
        return True 
    except Exception:
        pass
    return False

def update_signals_status(current_price):
    if not os.path.exists(HISTORY_FILE) or current_price <= 0:
        return
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        updated = False
        new_lines = []
        for line in lines:
            parts = line.strip().split(" | ")
            if len(parts) >= 6 and ("قيد التتبع ⏳" in parts[5] or "محمية 🛡️" in parts[5]):
                sig_type = parts[1]
                try:
                    entry = float(parts[2].split("$")[1])
                    target = float(parts[3].split("$")[1])
                    stop_part = parts[4]
                    
                    stop_val_str = stop_part.split("$")[1].split(" ")[0]
                    stop = float(stop_val_str)
                    
                    if "LONG" in sig_type or "NEWS" in sig_type:
                        distance_to_target = target - entry
                        current_profit_progress = current_price - entry
                        
                        if distance_to_target > 0 and current_profit_progress >= (distance_to_target * 0.5):
                            if stop < entry:
                                stop = entry
                                parts[4] = f"الوقف: ${stop:.2f} (محمي 🛡️)"
                                parts[5] = "محمية 🛡️"
                                updated = True

                        if current_price >= target:
                            parts[5] = "حقق الهدف ✅"
                            updated = True
                        elif current_price <= stop:
                            parts[5] = "ضرب الوقف ❌" if stop < entry else "خروج محمي بربح 🛡️✅"
                            updated = True
                            
                    elif "SHORT" in sig_type or "بيع" in sig_type:
                        distance_to_target = entry - target
                        current_profit_progress = entry - current_price
                        
                        if distance_to_target > 0 and current_profit_progress >= (distance_to_target * 0.5):
                            if stop > entry:
                                stop = entry
                                parts[4] = f"الوقف: ${stop:.2f} (محمي 🛡️)"
                                parts[5] = "محمية 🛡️"
                                updated = True

                        if current_price <= target:
                            parts[5] = "حقق الهدف ✅"
                            updated = True
                        elif current_price >= stop:
                            parts[5] = "ضرب الوقف ❌" if stop > entry else "خروج محمي بربح 🛡️✅"
                            updated = True
                except Exception as e:
                    print(f"Error updating signal: {e}")
                new_lines.append(" | ".join(parts) + "\n")
            else:
                new_lines.append(line)
                
        if updated:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
    except Exception as e:
        print(f"Error reading/writing history: {e}")

def load_history():
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    parts = line.strip().split(" | ")
                    if len(parts) >= 6:
                        history.append({
                            "time": parts[0],
                            "type": parts[1],
                            "details": f"{parts[2]} | {parts[3]} | {parts[4]}",
                            "status": parts[5]
                        })
        except Exception:
            pass
    return history

@app.route("/")
def index():
    tf = request.args.get("tf", "15m")
    klines = get_binance_klines(tf, limit=100)
    change_24h, current_price = get_market_data()
    
    update_signals_status(current_price)
    
    news_title = fetch_latest_crypto_news()
    news_sentiment, _ = analyze_news_sentiment(news_title)
    
    rsi = 50.0
    upper_bb, lower_bb = current_price, current_price
    macd_hist = 0.0
    support_val, resistance_val = 0.0, 0.0
    market_structure = "جاري التحليل..."
    smc_status = "جاري الفحص..."
    fvg_status = "جاري الفحص..."
    htf_trend = "NEUTRAL"
    market_status = "المحرك ينتظر إغلاق الشمعة وتأكيد الشروط الفنية بدقة..."
    play_sound = False

    if klines and len(klines) > 30:
        closes = [float(k[4]) for k in klines]
        rsi = round(calculate_rsi(closes, period=14), 2)
        upper_bb, lower_bb = calculate_bollinger_bands(closes, period=20, num_std=2)
        upper_bb = round(upper_bb, 2)
        lower_bb = round(lower_bb, 2)
        _, _, macd_hist = calculate_macd(closes)
        support_val, resistance_val = calculate_support_resistance(klines)
        market_structure = analyze_market_structure(closes)
        smc_status, smc_triggered = analyze_smart_money_concepts(klines)
        fvg_status = check_fair_value_gap(klines)
        htf_trend = check_multi_timeframe_trend(tf)
        
        if not has_active_signal():
            if rsi < 35 and current_price <= lower_bb * 1.003:
                target = round(current_price * 1.01, 2)
                stop = round(current_price * 0.994, 2)
                if save_signal("شراء LONG - ذكي مؤكد", current_price, target, stop):
                    play_sound = True
            
            elif rsi > 65 and current_price >= upper_bb * 0.997:
                target = round(current_price * 0.99, 2)
                stop = round(current_price * 1.006, 2)
                if save_signal("بيع SHORT - نزول مؤكد", current_price, target, stop):
                    play_sound = True

    history = load_history()
    rsi_pct = min(max(rsi, 0), 100)

    return render_template_string(HTML_TEMPLATE, 
                                 price=current_price, 
                                 change_24h=change_24h,
                                 rsi=rsi,
                                 rsi_pct=rsi_pct,
                                 market_cap=1640,
                                 macd_hist=macd_hist,
                                 support_val=support_val,
                                 resistance_val=resistance_val,
                                 lower_bb=lower_bb,
                                 upper_bb=upper_bb,
                                 market_structure=market_structure,
                                 smc_status=smc_status,
                                 fvg_status=fvg_status,
                                 htf_trend=htf_trend,
                                 market_status=market_status,
                                 latest_news=news_title,
                                 history=history,
                                 current_tf=tf,
                                 play_sound=play_sound)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>منصة سكالبينج الثنائية وتحليل الأخبار الآلي (Long & Short)</title>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <style>
        body { background-color: #121212; color: #e0e0e0; font-family: Tahoma, sans-serif; padding: 10px; margin: 0; }
        .card { background: #1e1e1e; padding: 12px; border-radius: 10px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .price { font-size: 24px; font-weight: bold; color: #4CAF50; text-align: center; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .box { background: #2a2a2a; padding: 10px; border-radius: 8px; text-align: center; font-size: 13px; }
        .alert-box { background: #2a2a2a; padding: 10px; border-radius: 8px; text-align: center; font-size: 14px; color: #ffeb3b; margin-bottom: 12px; border: 1px dashed #ff9800; }
        .news-box { background: #1a2634; padding: 10px; border-radius: 8px; text-align: right; font-size: 12px; color: #64B5F6; margin-bottom: 12px; border: 1px solid #1E88E5; }
        .history-item { background: #252525; padding: 8px; margin-bottom: 8px; border-radius: 6px; font-size: 12px; border-right: 4px solid #2196F3; }
        .status-success { color: #4CAF50; font-weight: bold; }
        .status-fail { color: #f44336; font-weight: bold; }
        .status-pending { color: #ff9800; font-weight: bold; }
        .status-protected { color: #00bcd4; font-weight: bold; }
        .tf-select { background: #2a2a2a; color: #fff; padding: 6px 10px; border-radius: 6px; border: 1px solid #444; font-size: 13px; cursor: pointer; }
        .progress-bar-container { background: #333; border-radius: 4px; height: 6px; width: 100%; margin-top: 6px; overflow: hidden; }
        .progress-bar-fill { background: #ff9800; height: 100%; width: {{ rsi_pct }}%; }
    </style>
    <meta http-equiv="refresh" content="15">
</head>
<body>
    <div class="card" style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <div style="font-size: 10px; color: #aaa; margin-bottom: 3px;">اختر الفريم الزمني:</div>
            <select class="tf-select" id="timeframeSelect" onchange="changeTimeframe()">
                <option value="1m" {% if current_tf == '1m' %}selected{% endif %}>1 دقيقة</option>
                <option value="5m" {% if current_tf == '5m' %}selected{% endif %}>5 دقائق</option>
                <option value="15m" {% if current_tf == '15m' %}selected{% endif %}>15 دقيقة</option>
                <option value="30m" {% if current_tf == '30m' %}selected{% endif %}>30 دقيقة</option>
                <option value="1h" {% if current_tf == '1h' %}selected{% endif %}>ساعة (1h)</option>
                <option value="4h" {% if current_tf == '4h' %}selected{% endif %}>4 ساعات</option>
            </select>
        </div>
        <div style="text-align: left;">
            <div style="font-size: 11px; color: #aaa;">BTC/USDT <span style="color: {{ 'green' if change_24h >= 0 else 'red' }};">({{ '+' if change_24h >= 0 else '' }}{{ change_24h }}%)</span></div>
            <div class="price" style="font-size: 20px;">${{ price }}</div>
        </div>
    </div>

    <div class="news-box">
        <b>📰 آخر خبر حي تم تحليله آلياً:</b><br>
        <span>{{ latest_news }}</span>
    </div>

    <div class="card" style="padding: 5px;">
        <div id="tradingview_chart" style="height: 260px; width: 100%;"></div>
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
            <div>الدعم والمقاومة (S/R)</div>
            <div style="font-size: 11px; color: #4CAF50; margin-top: 2px;">دعم: ${{ support_val }}</div>
            <div style="font-size: 11px; color: #f44336;">مقاومة: ${{ resistance_val }}</div>
        </div>
        <div class="box">
            <div>هيكل السوق (BOS)</div>
            <div style="font-size: 12px; font-weight: bold; color: #00bcd4; margin-top: 4px;">{{ market_structure }}</div>
        </div>
    </div>

    <div class="card">
        <div style="font-size: 13px; font-weight: bold; margin-bottom: 6px; color: #ff9800;">📋 سجل الصفقات والتتبع الآلي:</div>
        {% if history %}
            {% for item in history %}
            <div class="history-item">
                <div style="display: flex; justify-content: space-between; color: #aaa; font-size: 10px;">
                    <span>{{ item.time }}</

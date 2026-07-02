import streamlit as st
import streamlit.components.v1 as components
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
import json
import os
from datetime import datetime
import requests
import plotly.graph_objects as go

# ==========================================
# ⚙️ 1. ตั้งค่าหน้าเว็บ 
# ==========================================
st.set_page_config(page_title="SMC AI Trading Bot", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

# 🚑 [สคริปต์รักษาตัวเอง] ล้างความจำเบราว์เซอร์และบังคับกางแถบออโต้!
components.html(
    """
    <script>
        setTimeout(function() {
            // ล้างค่าในเบราว์เซอร์ที่จำว่า "พับแถบไว้"
            try { window.parent.localStorage.removeItem('stActiveSidebarState'); } catch(e) {}
            
            // สั่งกดปุ่มกางแถบอัตโนมัติ (ถ้ามันถูกพับอยู่)
            var expandBtn = window.parent.document.querySelector('[data-testid="collapsedControl"]');
            if (expandBtn) { expandBtn.click(); }
        }, 100);
    </script>
    """,
    height=0, width=0
)

# ==========================================
# 🎨 CSS ตกแต่ง
# ==========================================
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap');
    
    html, body, p, div, h1, h2, h3, h4, h5, h6, label, input, button {
        font-family: 'Prompt', sans-serif;
    }
    
    /* 🔴 ซ่อนปุ่ม X หรือ ยุบ ที่อยู่ด้านใน Sidebar (ไม่ให้กดยุบได้อีก) */
    [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }
    
    /* ซ่อมปุ่ม Icon ของระบบ */
    span[class*="material"], 
    i[class*="material"] {
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
    }
    
    /* 🎨 พื้นหลัง Gradient โทนสว่าง-เหลืองอ่อนแบบในรูป */
    .stApp {
        background: radial-gradient(circle at top left, #f8fafc 0%, #fef3c7 100%) !important;
    }
    
    /* 🔥 เอาแถบสีขาวด้านบน และซ่อนปุ่ม Deploy/Stop ออก */
    [data-testid="stHeader"] {
        background-color: transparent !important;
    }
    [data-testid="stToolbar"] {
        display: none !important;
    }
    .stDeployButton {
        display: none !important;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 96%;
    }

    /* 🎨 สไตล์การ์ดตัวเลขด้านบน */
    .dash-card {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border-radius: 24px;
        padding: 24px 30px;
        box-shadow: 0px 10px 40px rgba(0, 0, 0, 0.03); 
        border: 1px solid rgba(255, 255, 255, 0.8);
    }

    /* 🎨 เสกให้พื้นที่ด้านในของ "คอลัมน์" ซ้าย-ขวา กลายเป็นการ์ด */
    [data-testid="column"] > div {
        background: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border-radius: 28px !important;
        padding: 28px !important;
        box-shadow: 0px 10px 40px rgba(0, 0, 0, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.8) !important;
    }

    /* Sidebar แบบโปร่งแสงนิดๆ ให้เข้ากับธีม */
    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.6) !important;
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255, 255, 255, 0.6);
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# ⚙️ 2. การตั้งค่าระบบ & Telegram
# ==========================================
TELEGRAM_TOKEN = "8875944703:AAEKAkYJJ_1iz7o8KHHrO_5pXBaS6B4LKM4"
TELEGRAM_CHAT_ID = "8784481128"

MAGIC_NUMBER = 999111    
SL_BUFFER = 0.00020      
CHECK_INTERVAL = 5 

if 'bot_state' not in st.session_state:
    st.session_state.bot_state = {'last_progress': 0, 'has_order': False}

if 'last_update_id' not in st.session_state:
    st.session_state.last_update_id = 0
    try:
        res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates", timeout=2).json()
        if res.get("ok") and len(res["result"]) > 0:
            st.session_state.last_update_id = res["result"][-1]["update_id"]
    except: pass

def notify_telegram(message, chat_id=TELEGRAM_CHAT_ID):
    if TELEGRAM_TOKEN == "YOUR_TELEGRAM_TOKEN": return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=2)
    except: pass

def check_telegram_commands(current_symbol, balance, profit, step1, step2, step3, action):
    if TELEGRAM_TOKEN == "YOUR_TELEGRAM_TOKEN": return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": st.session_state.last_update_id + 1, "timeout": 1}
    try:
        res = requests.get(url, params=params, timeout=2).json()
        if res.get("ok"):
            for update in res["result"]:
                st.session_state.last_update_id = update["update_id"]
                if "message" in update and "text" in update["message"]:
                    chat_id = update["message"]["chat"]["id"]
                    text = update["message"]["text"].strip().lower()
                    if text in ["status", "สถานะ", "ทำอะไรอยู่", "รายงาน", "อัพเดท"]:
                        reply_msg = (
                            f"🤖 **รายงานสถานะบอท SMC**\n"
                            f"🔹 คู่เงิน: {current_symbol}\n"
                            f"💰 Balance: {balance:,.2f} USD\n"
                            f"💵 P/L ปัจจุบัน: {profit:,.2f} USD\n\n"
                            f"📊 **สถานะการวิเคราะห์:**\n"
                            f"1️⃣ โซนใหญ่: {step1}\n"
                            f"2️⃣ โครงสร้างรอง: {step2}\n"
                            f"3️⃣ จุดเข้า: {step3}\n\n"
                            f"🎯 **บอทกำลังทำ:** {action}"
                        )
                        notify_telegram(reply_msg, chat_id)
    except: pass

# ==========================================
# 🛠️ 3. ฟังก์ชัน MT5 & SMC 
# ==========================================
def check_mt5_connection():
    if not mt5.initialize(): return False, "เชื่อมต่อไม่ได้"
    acc = mt5.account_info()
    return (True, acc.login) if acc else (False, "ไม่พบข้อมูลบัญชี")

def has_open_orders(symbol):
    pos = mt5.positions_get(symbol=symbol)
    ords = mt5.orders_get(symbol=symbol)
    return (pos is not None and len(pos) > 0) or (ords is not None and len(ords) > 0)

def force_test_buy(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None: return False, "ไม่สามารถดึงราคากระดานได้"
    req = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": 0.01,
        "type": mt5.ORDER_TYPE_BUY, "price": tick.ask, "deviation": 20,
        "magic": MAGIC_NUMBER, "comment": "Test API MT5",
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(req)
    if result.retcode == mt5.TRADE_RETCODE_DONE: return True, "✅ ยิงออเดอร์ทดสอบ (Buy 0.01) สำเร็จ!"
    else: return False, "❌ ส่งคำสั่งไม่สำเร็จ กรุณาตรวจสอบปุ่ม 'Algo Trading' ใน MT5"

def get_market_structure(symbol, timeframe, num_candles=500): 
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
    if rates is None: return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    swing_len = 10 
    window_size = (swing_len * 2) + 1 
    
    df['is_sh'] = (df['high'] == df['high'].rolling(window=window_size, center=True).max())
    df['is_sl'] = (df['low'] == df['low'].rolling(window=window_size, center=True).min())
    
    trend, breaks = 0, []
    last_sh_val, last_sh_idx = None, None
    last_sl_val, last_sl_idx = None, None
    range_high, range_low = df['high'].iloc[0], df['low'].iloc[0]

    for i in range(window_size, len(df)):
        check_idx = i - swing_len
        
        if df['is_sh'].iloc[check_idx]: 
            last_sh_val, last_sh_idx = df['high'].iloc[check_idx], check_idx
        if df['is_sl'].iloc[check_idx]: 
            last_sl_val, last_sl_idx = df['low'].iloc[check_idx], check_idx
            
        current_close, current_time = df['close'].iloc[i], df['time'].iloc[i]

        if last_sh_val is not None and current_close > last_sh_val:
            breaks.append({'type': 'CHoCH' if trend <= 0 else 'BOS', 'dir': 'bullish', 'y': last_sh_val, 'x0': df['time'].iloc[last_sh_idx], 'x1': current_time})
            trend = 1
            if last_sh_idx is not None and last_sh_idx <= i:
                new_low = df['low'].iloc[last_sh_idx:i+1].min()
                if pd.notna(new_low): range_low = new_low
            range_high = current_close 
            last_sh_val = None 
            
        elif last_sl_val is not None and current_close < last_sl_val:
            breaks.append({'type': 'CHoCH' if trend >= 0 else 'BOS', 'dir': 'bearish', 'y': last_sl_val, 'x0': df['time'].iloc[last_sl_idx], 'x1': current_time})
            trend = -1
            if last_sl_idx is not None and last_sl_idx <= i:
                new_high = df['high'].iloc[last_sl_idx:i+1].max()
                if pd.notna(new_high): range_high = new_high
            range_low = current_close 
            last_sl_val = None

        if trend == 1 and df['high'].iloc[i] > range_high: 
            range_high = df['high'].iloc[i]
        elif trend == -1 and df['low'].iloc[i] < range_low: 
            range_low = df['low'].iloc[i]

    df.attrs['structure_breaks'] = breaks
    eq_50 = (range_high + range_low) / 2
    sz_top, sz_bottom = (range_high, range_high - ((range_high - eq_50) * 0.25)) if trend == -1 else (df['high'].max(), df['high'].max())
    dz_top, dz_bottom = (range_low + ((eq_50 - range_low) * 0.25), range_low) if trend == 1 else (df['low'].min(), df['low'].min())
    df['SZ_Top'], df['SZ_Bottom'], df['DZ_Top'], df['DZ_Bottom'] = sz_top, sz_bottom, dz_top, dz_bottom
    return df

def calculate_lot_size(symbol, sl_dist, risk_pct):
    acc, sym = mt5.account_info(), mt5.symbol_info(symbol)
    if not acc or not sym or sl_dist <= 0: return 0.01
    risk_money = acc.balance * risk_pct
    ticks = sl_dist / sym.trade_tick_size
    raw_lot = risk_money / (ticks * sym.trade_tick_value)
    lot = round(raw_lot / sym.volume_step) * sym.volume_step
    return max(sym.volume_min, min(lot, sym.volume_max))

def place_pending_order(symbol, order_type, lot, price, sl, tp):
    req = {
        "action": mt5.TRADE_ACTION_PENDING, "symbol": symbol, "volume": float(lot),
        "type": order_type, "price": float(price), "sl": float(sl), "tp": float(tp),
        "deviation": 20, "magic": MAGIC_NUMBER, "type_time": mt5.ORDER_TIME_GTC,
    }
    return mt5.order_send(req).retcode == mt5.TRADE_RETCODE_DONE

def plot_market_chart(df, symbol, timeframe_name):
    fig = go.Figure()
    df['time_str'] = df['time'].dt.strftime('%Y-%m-%d %H:%M')

    fig.add_trace(go.Candlestick(
        x=df['time_str'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#10b981', increasing_fillcolor='#10b981', 
        decreasing_line_color='#ef4444', decreasing_fillcolor='#ef4444', name='Price'
    ))

    latest = df.iloc[-1]
    
    try:
        if not pd.isna(latest['SZ_Top']) and not pd.isna(latest['SZ_Bottom']):
            fig.add_hrect(y0=latest['SZ_Bottom'], y1=latest['SZ_Top'], line_width=0, fillcolor="rgba(239, 68, 68, 0.08)", annotation_text="Supply Zone", annotation_font_color="#ef4444", annotation_position="top left")
        if not pd.isna(latest['DZ_Top']) and not pd.isna(latest['DZ_Bottom']):
            fig.add_hrect(y0=latest['DZ_Bottom'], y1=latest['DZ_Top'], line_width=0, fillcolor="rgba(16, 185, 129, 0.08)", annotation_text="Demand Zone", annotation_font_color="#10b981", annotation_position="bottom left")
        if not pd.isna(latest['Equilibrium_50']):
            fig.add_hline(y=latest['Equilibrium_50'], line_dash="dash", line_color="#cbd5e1", opacity=0.8, annotation_text="EQ 50%", annotation_font_color="#94a3b8", annotation_position="right")
    except: pass

    if hasattr(df, 'attrs') and 'structure_breaks' in df.attrs:
        for b in df.attrs['structure_breaks'][-5:]:
            try:
                if pd.isna(b['y']) or pd.isna(b['x0']) or pd.isna(b['x1']): continue
                color = "#10b981" if b['dir'] == 'bullish' else "#ef4444"
                x0_str, x1_str = b['x0'].strftime('%Y-%m-%d %H:%M'), b['x1'].strftime('%Y-%m-%d %H:%M')
                idx0_list = df.index[df['time'] == b['x0']].tolist()
                idx1_list = df.index[df['time'] == b['x1']].tolist()
                if idx0_list and idx1_list:
                    mid_idx = (idx0_list[0] + idx1_list[0]) // 2
                    x_mid_str = df.iloc[mid_idx]['time_str']
                else: x_mid_str = x1_str 
                y_anchor, y_shift = ("bottom", 5) if b['dir'] == 'bullish' else ("top", -5)
                fig.add_shape(type="line", x0=x0_str, y0=b['y'], x1=x1_str, y1=b['y'], line=dict(color=color, width=2, dash="dot"))
                fig.add_annotation(x=x_mid_str, y=b['y'], text=b['type'], showarrow=False, xanchor="center", yanchor=y_anchor, yshift=y_shift, font=dict(color=color, size=11, weight="bold", family="Prompt"))
            except: pass

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
        font=dict(color='#475569', family='Prompt, sans-serif', size=12),
        height=480, margin=dict(l=0, r=50, t=10, b=0), xaxis_rangeslider_visible=False, hovermode='x unified'
    )
    fig.update_xaxes(type='category', nticks=10, showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.03)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.03)', side="right", tickformat=".5f")
    return fig

# ==========================================
# 🎨 4. Sidebar 
# ==========================================
is_connected, conn_text = check_mt5_connection()
TF_DICT = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}
CONFIG_FILE = "bot_settings.json"
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f: cfg = json.load(f)
    except: cfg = {"sym": "XAUUSD", "tf1": 2, "tf2": 1, "tf3": 0, "risk": 1.0}
else: cfg = {"sym": "XAUUSD", "tf1": 2, "tf2": 1, "tf3": 0, "risk": 1.0}

with st.sidebar:
    st.markdown("<h2 style='color:#18181b; font-weight:700; margin-top:-10px; font-size: 26px;'>phonlaws Bot</h2>", unsafe_allow_html=True)
    st.markdown(f"<div style='color:{'#10b981' if is_connected else '#ef4444'}; font-weight:500; font-size:14px; margin-bottom:20px;'>● {conn_text}</div>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color: rgba(0,0,0,0.05); margin-top:0; margin-bottom:20px;'>", unsafe_allow_html=True)
    
    input_symbol = st.text_input("🔹 คู่เงิน (Symbol):", value=cfg["sym"]).upper()
    tf_main_name = st.selectbox("⏱️ TF โซนหลัก:", list(TF_DICT.keys()), index=cfg["tf1"]) 
    tf_sub_name = st.selectbox("⏱️ TF ยืนยัน:", list(TF_DICT.keys()), index=cfg["tf2"])   
    tf_entry_name = st.selectbox("⏱️ TF จุดเข้า:", list(TF_DICT.keys()), index=cfg["tf3"]) 
    input_risk = st.number_input("🔹 ความเสี่ยง (%):", value=cfg["risk"], step=0.1, min_value=0.1, max_value=10.0)
    
    st.markdown("<br>", unsafe_allow_html=True)
    is_bot_running = st.toggle("🚀 เปิดระบบ Auto-Refresh", value=True)

    st.markdown("<hr style='border-color: rgba(0,0,0,0.05); margin-top:10px; margin-bottom:20px;'>", unsafe_allow_html=True)
    if st.button("🧪 ทดสอบยิงออเดอร์ (0.01)", use_container_width=True):
        if is_connected:
            success, msg = force_test_buy(input_symbol)
            st.success(msg) if success else st.error(msg)
        else: st.error("❌ MT5 ยังไม่เชื่อมต่อ")

    new_cfg = {"sym": input_symbol, "tf1": list(TF_DICT.keys()).index(tf_main_name), "tf2": list(TF_DICT.keys()).index(tf_sub_name), "tf3": list(TF_DICT.keys()).index(tf_entry_name), "risk": float(input_risk)}
    if new_cfg != cfg:
        try:
            with open(CONFIG_FILE, "w") as f: json.dump(new_cfg, f)
        except: pass

active_sym, TF_MAIN, TF_SUB, TF_ENTRY, active_risk = input_symbol, TF_DICT[tf_main_name], TF_DICT[tf_sub_name], TF_DICT[tf_entry_name], float(input_risk)

# ==========================================
# 🧠 5. กระบวนการทำงานของบอท 
# ==========================================
step1_msg = step2_msg = step3_msg = action_msg = ""
progress_pct = 0
has_order = has_open_orders(active_sym)

# ดึงข้อมูลมาเตรียมไว้ล่วงหน้า
df_main = get_market_structure(active_sym, TF_MAIN)
df_sub = get_market_structure(active_sym, TF_SUB)
df_entry = get_market_structure(active_sym, TF_ENTRY)

if has_order:
    step1_msg = step2_msg = step3_msg = "ถือออเดอร์แล้ว"
    action_msg, progress_pct = f"⏳ Tracking {active_sym}...", 100
else:
    if df_main is not None and df_sub is not None:
        latest_main = df_main.iloc[-1]
        c_price = latest_main['close']

        # 🚀 [ระบบความจำ]: ดูย้อนหลัง 30 แท่งของ TF_SUB ว่า "เพิ่งลงไปแตะโซนมาไหม"
        lookback = 30
        recent_low_sub = df_sub['low'].tail(lookback).min()
        recent_high_sub = df_sub['high'].tail(lookback).max()

        # เช็คว่าเคยแตะโซน และโซนนั้นต้องยังไม่ถูกทะลุจนพัง (Invalidated)
        tapped_dz = (recent_low_sub <= latest_main['DZ_Top'] + 0.0005) and (c_price > latest_main['DZ_Bottom'])
        tapped_sz = (recent_high_sub >= latest_main['SZ_Bottom'] - 0.0005) and (c_price < latest_main['SZ_Top'])

        if not tapped_dz and not tapped_sz:
            step1_msg, step2_msg, step3_msg = f"รอราคาเข้าโซน", "Skip", "Skip"
            action_msg, progress_pct = f"🔎 Scanning Zone...", 15
            
        elif tapped_dz:
            step1_msg, progress_pct = f"🟢 Tapped DZ", 45
            
            # บอทจำได้ว่าแตะโซนแล้ว ให้มารอเช็ค MSS ได้เลย แม้ตอนราคานี้จะลอยอยู่นอกโซน
            if df_sub['close'].iloc[-1] > df_sub['SZ_Top'].iloc[-3]: 
                step2_msg, progress_pct = f"🔥 Bullish MSS", 75
                
                if df_entry is not None:
                    entry = (df_entry['DZ_Top'].iloc[-1] + df_entry['DZ_Bottom'].iloc[-1])/2
                    sl = df_entry['DZ_Bottom'].iloc[-1] - SL_BUFFER
                    tp = entry + (entry - sl)*3
                    lot = calculate_lot_size(active_sym, entry - sl, active_risk)
                    step3_msg, action_msg = f"🎯 Buy Limit {lot}L", "🚀 Placing BUY!"
                    if is_bot_running and place_pending_order(active_sym, mt5.ORDER_TYPE_BUY_LIMIT, lot, entry, sl, tp): progress_pct = 100
            else: 
                step2_msg, step3_msg = f"⏳ Wait MSS", "รอคำนวณ Lot"
                action_msg = "รอกราฟเสียทรงเป็นขาขึ้น"
                
        elif tapped_sz:
            step1_msg, progress_pct = f"🔴 Tapped SZ", 45
            
            # บอทจำได้ว่าแตะโซนแล้ว ให้มารอเช็ค MSS ขาลง
            if df_sub['close'].iloc[-1] < df_sub['DZ_Bottom'].iloc[-3]: 
                step2_msg, progress_pct = f"🔥 Bearish MSS", 75
                
                if df_entry is not None:
                    entry = (df_entry['SZ_Top'].iloc[-1] + df_entry['SZ_Bottom'].iloc[-1])/2
                    sl = df_entry['SZ_Top'].iloc[-1] + SL_BUFFER
                    tp = entry - (sl - entry)*3
                    lot = calculate_lot_size(active_sym, sl - entry, active_risk)
                    step3_msg, action_msg = f"🎯 Sell Limit {lot}L", "🚀 Placing SELL!"
                    if is_bot_running and place_pending_order(active_sym, mt5.ORDER_TYPE_SELL_LIMIT, lot, entry, sl, tp): progress_pct = 100
            else: 
                step2_msg, step3_msg = f"⏳ Wait MSS", "รอคำนวณ Lot"
                action_msg = "รอกราฟเสียทรงเป็นขาลง"

# ==========================================
# 📊 6. การแสดงผลหน้าหลัก (UI ตามภาพอ้างอิง)
# ==========================================
st.markdown("<h1 style='color:#18181b; font-weight:500; font-size: 32px; margin-bottom:24px;'>Welcome in, <span style='font-weight:700;'>Trader</span></h1>", unsafe_allow_html=True)

# ----- ส่วนบน: Metrics -----
acc_info = mt5.account_info()
bal = acc_info.balance if acc_info else 0.0
eq = acc_info.equity if acc_info else 0.0
pl = acc_info.profit if acc_info else 0.0
pl_color = "#10b981" if pl >= 0 else "#ef4444"

html_metrics = f"""<div style="display: flex; gap: 24px; margin-bottom: 24px;">
<div class="dash-card" style="flex: 1;">
<div style="color: #71717a; font-weight: 400; font-size: 14px;">Balance</div>
<div style="color: #18181b; font-size: 32px; font-weight: 700; margin-top: 4px;">${bal:,.2f}</div>
</div>
<div class="dash-card" style="flex: 1;">
<div style="color: #71717a; font-weight: 400; font-size: 14px;">Equity</div>
<div style="color: #18181b; font-size: 32px; font-weight: 700; margin-top: 4px;">${eq:,.2f}</div>
</div>
<div class="dash-card" style="flex: 1;">
<div style="color: #71717a; font-weight: 400; font-size: 14px;">Floating P/L</div>
<div style="color: {pl_color}; font-size: 32px; font-weight: 700; margin-top: 4px;">${pl:,.2f}</div>
</div>
</div>"""
st.markdown(html_metrics, unsafe_allow_html=True)

# ----- ส่วนล่าง: แบ่งจอ ซ้าย (Chart) ขวา (Checklist) -----
colL, colR = st.columns([6.2, 3.8])

with colL:
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 10px;">
        <div style="font-size: 20px; font-weight: 600; color: #18181b;">Live Chart</div>
        <div style="display:flex; gap:8px;">
            <div style="background: #18181b; color: #fbbf24; padding: 4px 14px; border-radius: 20px; font-weight: 600; font-size: 14px;">{active_sym}</div>
            <div style="background: #f4f4f5; color: #52525b; padding: 4px 14px; border-radius: 20px; font-weight: 600; font-size: 14px;">{tf_main_name}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if df_main is not None: st.plotly_chart(plot_market_chart(df_main, active_sym, tf_main_name), use_container_width=True)

with colR:
    st.markdown('<div style="font-size: 20px; font-weight: 600; color: #18181b; margin-bottom: 20px;">Task Progress</div>', unsafe_allow_html=True)
    
    def render_process_item(step_num, tf, title, desc, status, active_state):
        if active_state == "active":
            icon_bg, icon_color, shadow = "#18181b", "#fbbf24", "box-shadow: 0 8px 20px rgba(0,0,0,0.15);"
            title_color, status_color = "#18181b", "#18181b"
        elif active_state == "done":
            icon_bg, icon_color, shadow = "#fbbf24", "#18181b", ""
            title_color, status_color = "#18181b", "#d97706"
        else:
            icon_bg, icon_color, shadow = "#f4f4f5", "#a1a1aa", ""
            title_color, status_color = "#a1a1aa", "#a1a1aa"
            
        return f"""<div style="display: flex; align-items: center; padding: 16px 0; border-bottom: 1px dashed rgba(0,0,0,0.05);">
<div style="min-width: 44px; height: 44px; border-radius: 50%; background: {icon_bg}; color: {icon_color}; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 16px; margin-right: 16px; {shadow} transition: 0.3s;">{step_num}</div>
<div style="flex-grow: 1;">
<div style="display:flex; align-items:center; gap:8px;">
    <div style="color: {title_color}; font-weight: 600; font-size: 15px;">{title}</div>
    <span style="background:#fef08a; color:#854d0e; font-size:10px; padding:2px 8px; border-radius:12px; font-weight:600;">{tf}</span>
</div>
<div style="color: #71717a; font-size: 12px; margin-top: 2px;">{desc}</div>
</div>
<div style="color: {status_color}; font-weight: 600; font-size: 14px; text-align: right;">{status}</div>
</div>"""
        
    s1 = "active" if progress_pct <= 15 else "done"
    s2 = "waiting" if progress_pct <= 15 else ("active" if progress_pct == 45 else "done")
    s3 = "waiting" if progress_pct <= 45 else ("active" if progress_pct == 75 else "done")
    if progress_pct == 100: s1 = s2 = s3 = "done"

    html_list = render_process_item("1", tf_main_name, "Main Zone", "เช็คราคาเข้าโซน", step1_msg, s1)
    html_list += render_process_item("2", tf_sub_name, "Confirm MSS", "รอกราฟเสียทรง", step2_msg, s2)
    html_list += render_process_item("3", tf_entry_name, "Entry Point", "คำนวณ Lot", step3_msg, s3)
    
    html_list += f"""<div style="margin-top: 30px; background: rgba(255,255,255,0.5); padding: 20px; border-radius: 20px;">
<div style="display:flex; justify-content:space-between; margin-bottom:10px;">
<span style="color:#18181b; font-weight:600; font-size:14px;">Onboarding Status</span>
<span style="color:#d97706; font-weight:700; font-size:14px;">{progress_pct}%</span>
</div>
<div style="width:100%; background:#f4f4f5; border-radius:20px; height:8px;">
<div style="width:{progress_pct}%; background: linear-gradient(90deg, #facc15, #f59e0b); height:8px; border-radius:20px; transition: 0.5s;"></div>
</div>
<div style="color:#52525b; font-size:13px; font-weight: 500; margin-top:16px; text-align:center;">Action: <span style="color:#18181b; font-weight:700;">{action_msg}</span></div>
</div>"""
    
    st.markdown(html_list, unsafe_allow_html=True)

# ==========================================
# 📞 7. Refresh Loop
# ==========================================
if is_bot_running:
    check_telegram_commands(active_sym, bal, pl, step1_msg, step2_msg, step3_msg, action_msg)
    time.sleep(CHECK_INTERVAL)
    st.rerun()
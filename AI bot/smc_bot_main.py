import streamlit as st
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
from datetime import datetime
import requests

# 🌟 นำเข้าไลบรารีกราฟ TradingView สำหรับ Streamlit โดยเฉพาะ
from lightweight_charts.widgets import StreamlitChart

# ==========================================
# ⚙️ 1. ตั้งค่าหน้าเว็บ (ต้องอยู่บรรทัดแรก)
# ==========================================
st.set_page_config(
    page_title="SMC AI Trading Bot", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🎨 2. โค้ด CSS
# ==========================================
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap');
    html, body, p, div, h1, h2, h3, h4, h5, h6, span, li, a, button, label, input {
        font-family: 'Prompt', sans-serif;
    }
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 20px 25px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: all 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    @media (prefers-color-scheme: dark) {
        div[data-testid="metric-container"] {
            background-color: #1e1e2e;
            border: 1px solid #2b2b40;
        }
    }
    div[data-testid="stAlert"] {
        border-radius: 12px;
        padding: 15px 20px;
        border: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    h1 {
        font-weight: 700 !important;
        background: -webkit-linear-gradient(45deg, #2563eb, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 10px;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# ⚙️ 3. ตั้งค่าพารามิเตอร์การเทรด & Telegram
# ==========================================
TELEGRAM_TOKEN = "8875944703:AAEKAkYJJ_1iz7o8KHHrO_5pXBaS6B4LKM4"
TELEGRAM_CHAT_ID = "8784481128"

SYMBOL = "EURUSD"        
RISK_PCT = 0.01          
MAGIC_NUMBER = 999111    
SL_BUFFER = 0.00020      
CHECK_INTERVAL = 5 

def notify_telegram(message):
    if TELEGRAM_TOKEN == "YOUR_TELEGRAM_TOKEN": return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try: requests.post(url, json=payload)
    except: pass

if 'bot_state' not in st.session_state:
    st.session_state.bot_state = {'last_progress': 0, 'has_order': False}

# ==========================================
# 🛠️ 4. ฟังก์ชัน MT5 & วิเคราะห์ SMC แบบใหม่ (แม่นยำขึ้น)
# ==========================================
def check_mt5_connection():
    if not mt5.initialize(): return False, "เชื่อมต่อไม่ได้"
    acc = mt5.account_info()
    return (True, acc.login) if acc else (False, "ไม่พบข้อมูลบัญชี")

def has_open_orders(symbol):
    pos = mt5.positions_get(symbol=symbol)
    ords = mt5.orders_get(symbol=symbol)
    return (pos is not None and len(pos) > 0) or (ords is not None and len(ords) > 0)

def get_last_close_reason(symbol):
    try:
        deals = mt5.history_deals_get(datetime.now() - pd.Timedelta(days=1), datetime.now() + pd.Timedelta(days=1))
        if deals and len(deals) > 0:
            sym_deals = [d for d in deals if d.symbol == symbol and d.entry == 1]
            if sym_deals:
                profit = sym_deals[-1].profit
                if profit > 0: return f"🎯 ชนเป้าทำกำไร (TP)\nกำไร: +{profit:.2f} USD"
                elif profit < 0: return f"🛑 ชนจุดตัดขาดทุน (SL)\nขาดทุน: {profit:.2f} USD"
    except: pass
    return "ออเดอร์ถูกปิดแล้ว"

def get_market_structure(symbol, timeframe, num_candles=500): 
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
    if rates is None: return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    swing_len = 10 
    window_size = (swing_len * 2) + 1 
    
    df['is_sh'] = (df['high'] == df['high'].rolling(window=window_size, center=True).max())
    df['is_sl'] = (df['low'] == df['low'].rolling(window=window_size, center=True).min())
    
    trend = 0  
    breaks = [] 

    last_sh_val, last_sh_time = None, None
    last_sl_val, last_sl_time = None, None

    range_high = df['high'].iloc[0]
    range_low = df['low'].iloc[0]

    for i in range(window_size, len(df)):
        check_idx = i - swing_len
        
        if df['is_sh'].iloc[check_idx]:
            last_sh_val = df['high'].iloc[check_idx]
            last_sh_time = df['time'].iloc[check_idx]
        if df['is_sl'].iloc[check_idx]:
            last_sl_val = df['low'].iloc[check_idx]
            last_sl_time = df['time'].iloc[check_idx]

        current_close = df['close'].iloc[i]
        current_time = df['time'].iloc[i]

        if last_sh_val is not None and current_close > last_sh_val:
            break_type = 'CHoCH' if trend <= 0 else 'BOS'
            trend = 1
            breaks.append({'type': break_type, 'dir': 'bullish', 'y': last_sh_val, 'x0': last_sh_time, 'x1': current_time})
            last_sh_val = None 
            range_low = last_sl_val if last_sl_val else range_low 

        elif last_sl_val is not None and current_close < last_sl_val:
            break_type = 'CHoCH' if trend >= 0 else 'BOS'
            trend = -1
            breaks.append({'type': break_type, 'dir': 'bearish', 'y': last_sl_val, 'x0': last_sl_time, 'x1': current_time})
            last_sl_val = None 
            range_high = last_sh_val if last_sh_val else range_high 

        if trend == 1 and df['high'].iloc[i] > range_high:
            range_high = df['high'].iloc[i]
        elif trend == -1 and df['low'].iloc[i] < range_low:
            range_low = df['low'].iloc[i]

    df.attrs['structure_breaks'] = breaks

    eq_50 = (range_high + range_low) / 2
    df['Equilibrium_50'] = eq_50
    df['Dealing_Range_High'] = range_high
    df['Dealing_Range_Low'] = range_low
    
    sz_top, sz_bottom = range_high, range_high
    dz_top, dz_bottom = range_low, range_low

    if trend == -1:
        sz_top = range_high
        sz_bottom = range_high - ((range_high - eq_50) * 0.25)
        dz_top, dz_bottom = df['low'].min(), df['low'].min() 
    elif trend == 1:
        dz_bottom = range_low
        dz_top = range_low + ((eq_50 - range_low) * 0.25) 
        sz_top, sz_bottom = df['high'].max(), df['high'].max()

    df['SZ_Top'] = sz_top
    df['SZ_Bottom'] = sz_bottom
    df['DZ_Top'] = dz_top
    df['DZ_Bottom'] = dz_bottom
    
    return df

def calculate_lot_size(symbol, sl_dist, risk_pct):
    acc, sym = mt5.account_info(), mt5.symbol_info(symbol)
    if not acc or not sym or sl_dist <= 0: return 0.01
    risk_money = acc.balance * risk_pct
    ticks = sl_dist / sym.trade_tick_size
    if ticks <= 0: return 0.01
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

# 📈 5. ฟังก์ชันวาดกราฟแบบ TradingView 
def render_tradingview_chart(df):
    # กำหนดขนาดให้อิงตามหน้าจอ Streamlit (ปรับ height ได้ตามต้องการ)
    chart = StreamlitChart(height=500)
    
    # ธีม TradingView Dark Mode
    chart.layout(background_color='#131722', text_color='#d1d4dc')
    chart.grid(vert_enabled=True, horz_enabled=True, color='#363c4e')
    chart.candle_style(up_color='#26a69a', down_color='#ef5350', 
                       border_up_color='#26a69a', border_down_color='#ef5350',
                       wick_up_color='#26a69a', wick_down_color='#ef5350')

    # โหลดแท่งเทียน
    df_chart = df[['time', 'open', 'high', 'low', 'close']].copy()
    chart.set(df_chart)

    latest = df.iloc[-1]
    
    # ตีเส้นแนวนอน (Equilibrium และขอบเขต Dealing Range)
    if 'Equilibrium_50' in df.columns:
        chart.horizontal_line(latest['Equilibrium_50'], color='#2962FF', width=2, style='dashed', text='EQ 50%')
        chart.horizontal_line(latest['Dealing_Range_High'], color='#B2B5BE', width=1, text='Range High')
        chart.horizontal_line(latest['Dealing_Range_Low'], color='#B2B5BE', width=1, text='Range Low')
        
        # สำหรับ Zone เนื่องจากไม่มี Fill Color เราจะตีเส้นบอกขอบเขตแทนครับ
        if latest['SZ_Bottom'] != latest['SZ_Top']:
            chart.horizontal_line(latest['SZ_Bottom'], color='#ef5350', width=2, text='Supply Zone')
        if latest['DZ_Top'] != latest['DZ_Bottom']:
            chart.horizontal_line(latest['DZ_Top'], color='#26a69a', width=2, text='Demand Zone')

    # วาดเส้น BOS / CHoCH
    if hasattr(df, 'attrs') and 'structure_breaks' in df.attrs:
        for b in df.attrs['structure_breaks'][-5:]:
            color = "#26a69a" if b['dir'] == 'bullish' else "#ef5350"
            chart.trend_line(
                start_time=b['x0'], start_value=b['y'], 
                end_time=b['x1'], end_value=b['y'], 
                color=color, width=2
            )

    # โหลดเข้า Streamlit
    chart.load()

# ==========================================
# 🎨 6. วาด UI
# ==========================================
is_connected, conn_text = check_mt5_connection()

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/6122/6122849.png", width=100)
    st.markdown("### 🤖 SMC System")
    st.markdown("---")
    if is_connected: st.success(f"🟢 **เชื่อมต่อสำเร็จ**\n\nบัญชี: {conn_text}")
    else: st.error(f"🔴 **ขาดการเชื่อมต่อ**\n\n{conn_text}")
    st.markdown("---")
    st.write(f"🔹 **คู่เงิน:** `{SYMBOL}`")
    st.write(f"🔹 **ความเสี่ยง:** `{RISK_PCT*100}%`")

st.title(f"SMC AI Trading Dashboard 📈")
if not is_connected: st.stop()

acc_info = mt5.account_info()
balance, equity, profit = acc_info.balance, acc_info.equity, acc_info.profit

col1, col2, col3 = st.columns(3)
col1.metric("💰 Balance", f"{balance:,.2f} USD")
col2.metric("📊 Equity", f"{equity:,.2f} USD")
col3.metric("💵 Floating P/L", f"{profit:,.2f} USD", delta=f"{profit:,.2f}", delta_color="normal" if profit >= 0 else "inverse")
st.markdown("<br>", unsafe_allow_html=True)

h1_th = m5_th = m1_th = action_msg = ""
progress_pct = 0
has_order = has_open_orders(SYMBOL)

if st.session_state.bot_state['has_order'] and not has_order:
    notify_telegram(f"🔔 แจ้งเตือน: ออเดอร์ปิดแล้ว!\n{get_last_close_reason(SYMBOL)}\n💰 ยอด: {balance:.2f} USD")
st.session_state.bot_state['has_order'] = has_order

df_h1 = get_market_structure(SYMBOL, mt5.TIMEFRAME_H1)

if has_order:
    h1_th = m5_th = m1_th = "ออเดอร์กำลังทำงาน"
    action_msg = "⏳ ระบบกำลังถือออเดอร์..."
    progress_pct = 100
else:
    if df_h1 is not None:
        latest = df_h1.iloc[-1]
        c_price, eq_50 = latest['close'], latest['Equilibrium_50']
        
        is_dz = c_price <= latest['DZ_Top'] + 0.0005
        is_sz = c_price >= latest['SZ_Bottom'] - 0.0005

        if not is_dz and not is_sz:
            h1_th, m5_th, m1_th = f"ราคาอยู่กลางทาง ({c_price:.5f})", "ข้าม", "ข้าม"
            action_msg, progress_pct = "🔎 สแกนหาโซนได้เปรียบ...", 10
        elif is_dz:
            h1_th, progress_pct = "🟢 เข้า Demand Zone (รอ BUY)", 40
            df_m5 = get_market_structure(SYMBOL, mt5.TIMEFRAME_M5)
            if df_m5['close'].iloc[-1] > df_m5['SZ_Top'].iloc[-3]: 
                m5_th, progress_pct = "🔥 เกิด Bullish MSS (M5)", 70
                df_m1 = get_market_structure(SYMBOL, mt5.TIMEFRAME_M1)
                entry, sl = (df_m1['DZ_Top'].iloc[-1] + df_m1['DZ_Bottom'].iloc[-1])/2, df_m1['DZ_Bottom'].iloc[-1] - SL_BUFFER
                tp, lot = entry + (entry - sl)*3, calculate_lot_size(SYMBOL, entry - sl, RISK_PCT)
                m1_th, action_msg = f"🎯 Buy Limit Lot {lot}", "🚀 ส่งออเดอร์ BUY LIMIT!"
                if place_pending_order(SYMBOL, mt5.ORDER_TYPE_BUY_LIMIT, lot, entry, sl, tp): progress_pct = 100
            else: m5_th, action_msg = "⏳ รอยืนยัน Bullish MSS", "เฝ้ารอจุดกลับตัว"
        elif is_sz:
            h1_th, progress_pct = "🔴 เข้า Supply Zone (รอ SELL)", 40
            df_m5 = get_market_structure(SYMBOL, mt5.TIMEFRAME_M5)
            if df_m5['close'].iloc[-1] < df_m5['DZ_Bottom'].iloc[-3]: 
                m5_th, progress_pct = "🔥 เกิด Bearish MSS (M5)", 70
                df_m1 = get_market_structure(SYMBOL, mt5.TIMEFRAME_M1)
                entry, sl = (df_m1['SZ_Top'].iloc[-1] + df_m1['SZ_Bottom'].iloc[-1])/2, df_m1['SZ_Top'].iloc[-1] + SL_BUFFER
                tp, lot = entry - (sl - entry)*3, calculate_lot_size(SYMBOL, sl - entry, RISK_PCT)
                m1_th, action_msg = f"🎯 Sell Limit Lot {lot}", "🚀 ส่งออเดอร์ SELL LIMIT!"
                if place_pending_order(SYMBOL, mt5.ORDER_TYPE_SELL_LIMIT, lot, entry, sl, tp): progress_pct = 100
            else: m5_th, action_msg = "⏳ รอยืนยัน Bearish MSS", "เฝ้ารอจุดกลับตัว"

if progress_pct > st.session_state.bot_state['last_progress']:
    if progress_pct == 40: notify_telegram(f"👀 [STEP 1] {SYMBOL}\n{h1_th}\nซูมเข้า M5...")
    elif progress_pct == 70: notify_telegram(f"🔥 [STEP 2] เจอสัญญาณกลับตัว\nกำลังยิงออเดอร์...")
    elif progress_pct == 100: notify_telegram(f"✅ [STEP 3] ทำรายการสำเร็จ!\n{action_msg}\n{m1_th}")
st.session_state.bot_state['last_progress'] = max(10, progress_pct)

# ==========================================
# โหลดกราฟ TradingView ลงใน Streamlit
# ==========================================
st.markdown("### 👁️ มุมมองของบอท (Market View)")
if df_h1 is not None:
    render_tradingview_chart(df_h1)

st.markdown("---")
st.markdown("### 🔍 กระบวนการวิเคราะห์ตลาด (SMC)")
c1, c2, c3 = st.columns(3)
with c1: st.info(f"**[Step 1] H1 โซนใหญ่:**\n\n{h1_th}")
with c2: st.warning(f"**[Step 2] M5 โครงสร้างรอง:**\n\n{m5_th}")
with c3: st.success(f"**[Step 3] M1 จุดเข้า:**\n\n{m1_th}")
st.markdown("<br>", unsafe_allow_html=True)

if progress_pct == 100: st.success(f"🎯 **สถานะปัจจุบัน:** {action_msg}")
else: st.info(f"🔄 **สถานะปัจจุบัน:** {action_msg}")
st.progress(progress_pct / 100, text=f"กระบวนการทำงาน: {progress_pct}%")

time.sleep(CHECK_INTERVAL)
st.rerun()
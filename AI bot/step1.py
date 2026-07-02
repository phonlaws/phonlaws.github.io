import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def connect_mt5():
    if not mt5.initialize():
        print("❌ ไม่สามารถเชื่อมต่อ MT5 ได้")
        return False
    return True

def get_market_structure(symbol, timeframe, num_candles):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
    if rates is None: return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    df['Swing_High'] = np.where((df['high'] > df['high'].shift(1)) & (df['high'] > df['high'].shift(2)) & (df['high'] > df['high'].shift(-1)) & (df['high'] > df['high'].shift(-2)), df['high'], np.nan)
    df['Swing_Low'] = np.where((df['low'] < df['low'].shift(1)) & (df['low'] < df['low'].shift(2)) & (df['low'] < df['low'].shift(-1)) & (df['low'] < df['low'].shift(-2)), df['low'], np.nan)
        
    df['Last_Swing_High'] = df['Swing_High'].ffill()
    df['Last_Swing_Low'] = df['Swing_Low'].ffill()
    
    df['Zone_Top'] = np.where(df['Swing_High'].notna(), df['high'], np.where(df['Swing_Low'].notna(), df['high'], np.nan))
    df['Zone_Bottom'] = np.where(df['Swing_High'].notna(), df['low'], np.where(df['Swing_Low'].notna(), df['low'], np.nan))
    df['Zone_Top'] = df['Zone_Top'].ffill()
    df['Zone_Bottom'] = df['Zone_Bottom'].ffill()
    
    df['Equilibrium_50'] = (df['high'].rolling(50).max() + df['low'].rolling(50).min()) / 2
    return df

def calculate_lot_size(symbol, sl_distance_price, risk_pct=0.01):
    # คำนวณ Lot 1% ของพอร์ต
    account = mt5.account_info()
    sym_info = mt5.symbol_info(symbol)
    if account is None or sym_info is None: return 0.01
    
    balance = account.balance
    risk_money = balance * risk_pct # เงิน 1% ที่ยอมเสียได้
    
    tick_size = sym_info.trade_tick_size
    tick_value = sym_info.trade_tick_value
    
    ticks_at_risk = sl_distance_price / tick_size
    if ticks_at_risk <= 0: return 0.01
    
    raw_lot = risk_money / (ticks_at_risk * tick_value)
    
    # ปัดเศษ Lot ให้ตรงกับที่โบรกเกอร์รองรับ
    step = sym_info.volume_step
    lot = round(raw_lot / step) * step
    
    if lot < sym_info.volume_min: lot = sym_info.volume_min
    if lot > sym_info.volume_max: lot = sym_info.volume_max
    
    return lot, risk_money, balance

if __name__ == "__main__":
    SYMBOL = "EURUSD" 
    
    if connect_mt5():
        print(f"\n✅ เริ่มวิเคราะห์ระบบเทรด SMC เต็มรูปแบบ (H1 -> M5 -> M1) | คู่เงิน: {SYMBOL}\n")
        
        # --- สมมติว่า H1 แตะ DZ และ M5 เกิด Bullish MSS แล้ว ---
        print("🔎 [3] ซูมเข้า Timeframe M1 เพื่อหา Flip Zone และเตรียมยิงออเดอร์:")
        
        df_m1 = get_market_structure(SYMBOL, mt5.TIMEFRAME_M1, 100)
        
        if df_m1 is not None:
            # หา Flip Zone (ใช้แท่งเทียนที่ทำจุด Swing Low ล่าสุดเป็นฐาน)
            last_low_val = df_m1['Last_Swing_Low'].iloc[-1]
            
            # ดึงข้อมูลแท่งที่เป็น Swing Low นั้นมาสร้างกรอบ Flip Zone
            swing_candle = df_m1[df_m1['low'] == last_low_val].iloc[-1]
            
            fz_bottom = swing_candle['low']
            fz_top = swing_candle['high']
            
            # คำนวณจุดเข้า 50% ของ Flip Zone
            entry_price = (fz_top + fz_bottom) / 2
            
            # คำนวณ SL (เผื่อระยะจากตูด Flip Zone ลงมานิดหน่อย)
            sl_price = fz_bottom - 0.00020 
            
            # คำนวณ TP (RR 1:3)
            risk_distance = entry_price - sl_price
            tp_price = entry_price + (risk_distance * 3)
            
            # คำนวณ Lot Size 1%
            lot_size, risk_money, balance = calculate_lot_size(SYMBOL, risk_distance, risk_pct=0.01)
            
            print(f"   🟩 พบ Flip Zone (M1): {fz_bottom:.5f} - {fz_top:.5f}")
            print(f"   🎯 จุดเข้าออเดอร์ (50% ของ FZ): {entry_price:.5f}")
            print(f"   🛡️ จุดตัดขาดทุน (SL): {sl_price:.5f} (ระยะ {risk_distance:.5f})")
            print(f"   💰 จุดทำกำไร (TP) [RR 1:3]: {tp_price:.5f}")
            print("\n📊 การจัดการความเสี่ยง (Risk Management):")
            print(f"   - ยอดเงินในพอร์ต (Balance): {balance:.2f} USD")
            print(f"   - ความเสี่ยง 1% (ยอมเสียได้): {risk_money:.2f} USD")
            print(f"   - 🚀 ขนาด Lot ที่ต้องออก: {lot_size:.2f} Lot")
            
            print("\n💡 บอทพร้อมที่จะส่งคำสั่ง BUY LIMIT (Pending Order) เข้าตลาดแล้ว!")

        mt5.shutdown()
        print("\n-------------------------------------------------")
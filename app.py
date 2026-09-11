import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="GTF Eye-Style Stock Scanner", layout="wide")
st.title("👁️ Custom 'GTF Eye' Demand & Supply Scanner")
st.caption("Advanced Multi-Timeframe Institutional Zone Analysis Framework for NSE Cash Markets")

# --- SIDEBAR: GTF Eye Control Controls ---
st.sidebar.header("🎛️ GTF Eye Controls")

# 1. Criteria Selector
criteria = st.sidebar.radio("Select Criteria:", ["In Zone / Reacting", "Approaching Zone"])

# 2. Zone Type Selector
zone_type = st.sidebar.radio("Select Zone Type:", ["Demand (Buy)", "Supply (Sell)"])

# 3. Time Frame Selector
timeframe = st.sidebar.selectbox("Select Timeframe:", ["Daily", "Weekly", "Monthly"])

# 4. Mode Selection
mode = st.sidebar.selectbox("Select Mode:", ["Standard Mode", "GTF Mode (Trend Aligned)"])

# 5. Core Price Filter
min_price = st.sidebar.number_input("Minimum Stock Price (₹)", value=200)

# Full Nifty 50 List
watchlist = [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS",
    "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BEL.NS", "BPCL.NS",
    "BHARTIARTL.NS", "BRITANNIA.NS", "CIPLA.NS", "COALINDIA.NS", "DIVISLAB.NS",
    "DRREDDY.NS", "EICHERMOT.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS",
    "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS",
    "ITC.NS", "INDUSINDBK.NS", "INFY.NS", "JSWSTEEL.NS", "KOTAKBANK.NS",
    "LT.NS", "LTIM.NS", "M&M.NS", "MARUTI.NS", "NTPC.NS", "NESTLEIND.NS",
    "ONGC.NS", "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS", "SHRIRAMFIN.NS",
    "SBIN.NS", "SUNPHARMA.NS", "TCS.NS", "TATACONSUM.NS", "TATAMOTORS.NS",
    "TATASTEEL.NS", "TECHM.NS", "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS"
]

def get_history_by_tf(ticker_obj, tf):
    if tf == "Weekly":
        df = ticker_obj.history(period="1y", interval="1wk")
    elif tf == "Monthly":
        df = ticker_obj.history(period="3y", interval="1mo")
    else: # Daily
        df = ticker_obj.history(period="6mo", interval="1d")
    return df

@st.cache_data(ttl=600)
def scan_gtf_eye(ticker_list, tf, zone_req, crit_req, mode_req, prc_flt):
    scanned_list = []
    
    for ticker in ticker_list:
        try:
            stock = yf.Ticker(ticker)
            df = get_history_by_tf(stock, tf)
            df = df.dropna()
            
            if len(df) < 25 or df['Close'].iloc[-1] < prc_flt:
                continue
                
            # Base Calculations
            df['Range'] = df['High'] - df['Low']
            df['Body'] = (df['Close'] - df['Open']).abs()
            df['Body_Pct'] = df['Body'] / np.where(df['Range'] == 0, 1, df['Range'])
            df['Is_Green'] = df['Close'] > df['Open']
            
            # Trend calculation (GTF Mode uses 50 SMA for primary trend alignment)
            df['SMA50'] = df['Close'].rolling(window=min(50, len(df))).mean()
            current_trend = "Bullish" if df['Close'].iloc[-1] > df['SMA50'].iloc[-1] else "Bearish"
            
            # Check last few candles to isolate an S&D footprint block
            p_leg_in = df.iloc[-4]
            p_base = df.iloc[-3]
            p_leg_out = df.iloc[-2]
            current_candle = df.iloc[-1]
            
            # Structural Validations (Base candle must be tight consolidation)
            if p_base['Body_Pct'] > 0.50 or p_leg_out['Body_Pct'] <= 0.40:
                continue
                
            is_demand_zone = False
            is_supply_zone = False
            zone_high, zone_low = 0.0, 0.0
            pattern = ""
            
            # Identify Structure Type
            if not p_leg_in['Is_Green'] and p_leg_out['Is_Green']:
                pattern = "DBR (Drop-Base-Rally)"
                zone_high, zone_low = p_base['High'], min(p_base['Low'], p_leg_out['Low'])
                is_demand_zone = True
            elif p_leg_in['Is_Green'] and p_leg_out['Is_Green']:
                pattern = "RBR (Rally-Base-Rally)"
                zone_high, zone_low = p_base['High'], min(p_base['Low'], p_leg_out['Low'])
                is_demand_zone = True
            elif p_leg_in['Is_Green'] and not p_leg_out['Is_Green']:
                pattern = "RBD (Rally-Base-Drop)"
                zone_high, zone_low = max(p_base['High'], p_leg_out['High']), p_base['Low']
                is_supply_zone = True
            elif not p_leg_in['Is_Green'] and not p_leg_out['Is_Green']:
                pattern = "DBD (Drop-Base-Drop)"
                zone_high, zone_low = max(p_base['High'], p_leg_out['High']), p_base['Low']
                is_supply_zone = True

            # Match filters selected on UI
            if zone_req == "Demand (Buy)" and not is_demand_zone: continue
            if zone_req == "Supply (Sell)" and not is_supply_zone: continue
            
            # GTF Mode Filter: Only allow demand setups in structural uptrends & supply setups in downtrends
            if mode_req == "GTF Mode (Trend Aligned)":
                if zone_req == "Demand (Buy)" and current_trend != "Bullish": continue
                if zone_req == "Supply (Sell)" and current_trend != "Bearish": continue
                
            curr_price = current_candle['Close']
            status = "Mismatch"
            
            # Evaluate Criteria (Approaching vs Reacting/In Zone)
            if is_demand_zone:
                buffer = (zone_high - zone_low) * 0.20
                if zone_low <= curr_price <= zone_high:
                    status = "In Zone / Reacting"
                elif zone_high < curr_price <= (zone_high + buffer):
                    status = "Approaching Zone"
            elif is_supply_zone:
                buffer = (zone_high - zone_low) * 0.20
                if zone_low <= curr_price <= zone_high:
                    status = "In Zone / Reacting"
                elif (zone_low - buffer) <= curr_price < zone_low:
                    status = "Approaching Zone"
                    
            if status != crit_req:
                continue
                
            scanned_list.append({
                "Ticker": ticker.replace(".NS", ""),
                "Full_Ticker": ticker,
                "Price": round(curr_price, 2),
                "Pattern": pattern,
                "Trend": current_trend,
                "Zone High (Proximal)": round(zone_high, 2),
                "Zone Low (Distal)": round(zone_low, 2),
                "Base_Date": df.index[-3],
                "Current_Date": df.index[-1],
                "Is_Demand": is_demand_zone
            })
        except Exception:
            continue
            
    return pd.DataFrame(scanned_list)

# --- SCANNING EXECUTION KEYWAY ---
if st.button("🔥 Scan Market in GTF Eye Mode"):
    with st.spinner(f"Scanning Nifty 50 for {timeframe} {zone_type} setups..."):
        results_df = scan_gtf_eye(watchlist, timeframe, zone_type, criteria, mode, min_price)
        st.session_state['gtf_data'] = results_df

# --- GRID VISUAL ENGINE ---
if 'gtf_data' in st.session_state and not st.session_state['gtf_data'].empty:
    display_df = st.session_state['gtf_data']
    st.subheader(f"🎯 Matched Setups ({len(display_df)} Found)")
    
    clean_view = display_df.drop(columns=['Full_Ticker', 'Base_Date', 'Current_Date', 'Is_Demand'])
    st.dataframe(clean_view.style.map(
        lambda v: 'background-color: #1e4620; color: white;' if v == "Bullish" else 'background-color: #5c1d1d; color: white;', 
        subset=["Trend"]
    ), use_container_width=True)
    
    # Chart Integration
    st.markdown("---")
    st.subheader("📊 Chart Scanner Verification")
    selected_stock = st.selectbox("Select stock to check institutional borders:", display_df["Ticker"].unique())
    
    if selected_stock:
        row = display_df[display_df["Ticker"] == selected_stock].iloc[0]
        stock_obj = yf.Ticker(row['Full_Ticker'])
        chart_history = get_history_by_tf(stock_obj, timeframe).tail(40)
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=chart_history.index, open=chart_history['Open'], high=chart_history['High'],
            low=chart_history['Low'], close=chart_history['Close'], name=selected_stock
        ))
        
        # Color layout configuration based on strategy conditions
        box_fill = "rgba(46, 125, 50, 0.2)" if row['Is_Demand'] else "rgba(198, 40, 40, 0.2)"
        border_line = "#2e7d32" if row['Is_Demand'] else "#c62828"
        
        fig.add_shape(
            type="rect", x0=row['Base_Date'], x1=row['Current_Date'],
            y0=row['Zone Low (Distal)'], y1=row['Zone High (Proximal)'],
            fillcolor=box_fill, line=dict(color=border_line, width=2, dash="dot"),
            layer="below"
        )
        
        fig.update_layout(
            title=f"{selected_stock} - {row['Pattern']} ({timeframe} View)",
            yaxis_title="Price (₹)", xaxis_rangeslider_visible=False,
            height=600, template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)
        
elif 'gtf_data' in st.session_state:
    st.info(f"No stocks currently match the specific filters: [{timeframe} | {zone_type} | {criteria} | {mode}]. Try changing parameters in the sidebar!")

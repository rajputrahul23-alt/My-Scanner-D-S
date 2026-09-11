import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="🇮🇳 Advanced S&D Institutional Scanner", layout="wide")
st.title("📦 Institutional Supply & Demand Zone Scanner + Visualizer")
st.caption("Scanning NSE Cash Market for DBR, RBR, RBD, DBD Structures with A/A+ Quality Filters")

# 1. Sidebar Parameter Controls
st.sidebar.header("Strategy Settings")
base_body_threshold = st.sidebar.slider("Max Base Candle Body/Range %", 10, 60, 50, step=5) / 100.0
min_price_filter = st.sidebar.number_input("Minimum Stock Price (₹)", value=200)
vol_ma_length = st.sidebar.number_input("Volume MA Length", value=20)

# Full Nifty 50 List
watchlist = [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS",
    "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BEL.NS", "BPCL.NS",
    "BHARTIARTL.NS", "BRITANNIA.NS", "CIPLA.NS", "COALINDIA.NS", "DIVISLAB.NS",
    "DRREDDY.NS", "EICHERMOT.NS", "GRASIM.NS", "HCLTECH.TH", "HDFCBANK.NS",
    "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS",
    "ITC.NS", "INDUSINDBK.NS", "INFY.NS", "JSWSTEEL.NS", "KOTAKBANK.NS",
    "LT.NS", "LTIM.NS", "M&M.NS", "MARUTI.NS", "NTPC.NS", "NESTLEIND.NS",
    "ONGC.NS", "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS", "SHRIRAMFIN.NS",
    "SBIN.NS", "SUNPHARMA.NS", "TCS.NS", "TATACONSUM.NS", "TATAMOTORS.NS",
    "TATASTEEL.NS", "TECHM.NS", "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS"
]

def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_cp = np.abs(df['High'] - df['Close'].shift())
    low_cp = np.abs(df['Low'] - df['Close'].shift())
    df_tr = pd.concat([high_low, high_cp, low_cp], axis=1)
    true_range = df_tr.max(axis=1)
    return true_range.rolling(period).mean()

def process_sd_scan(ticker_list):
    results = []
    
    for ticker in ticker_list:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="100d")
            if len(df) < 30 or df['Close'].iloc[-1] < min_price_filter:
                continue
            
            df['ATR'] = calculate_atr(df)
            df['Range'] = df['High'] - df['Low']
            df['Body'] = (df['Close'] - df['Open']).abs()
            df['Body_Pct'] = df['Body'] / np.where(df['Range'] == 0, 1, df['Range'])
            df['Is_Green'] = df['Close'] > df['Open']
            df['Vol_MA'] = df['Volume'].rolling(vol_ma_length).mean()
            
            p_leg_in = df.iloc[-4]
            p_base = df.iloc[-3]
            p_leg_out = df.iloc[-2]
            current_day = df.iloc[-1]
            
            if p_base['Body_Pct'] > base_body_threshold:
                continue
            if p_leg_in['Body_Pct'] <= base_body_threshold or p_leg_out['Body_Pct'] <= base_body_threshold:
                continue
                
            structure_type = "None"
            zone_high, zone_low = 0.0, 0.0
            is_demand = False
            
            if not p_leg_in['Is_Green'] and p_leg_out['Is_Green']:
                structure_type = "DBR"
                zone_high = p_base['High']
                zone_low = min(p_base['Low'], p_leg_out['Low'])
                is_demand = True
            elif p_leg_in['Is_Green'] and p_leg_out['Is_Green']:
                structure_type = "RBR"
                zone_high = p_base['High']
                zone_low = min(p_base['Low'], p_leg_out['Low'])
                is_demand = True
            elif p_leg_in['Is_Green'] and not p_leg_out['Is_Green']:
                structure_type = "RBD"
                zone_high = max(p_base['High'], p_leg_out['High'])
                zone_low = p_base['Low']
            elif not p_leg_in['Is_Green'] and not p_leg_out['Is_Green']:
                structure_type = "DBD"
                zone_high = max(p_base['High'], p_leg_out['High'])
                zone_low = p_base['Low']
                
            if structure_type == "None":
                continue
                
            leg_out_atr_ratio = p_leg_out['Body'] / p_leg_out['ATR']
            quality_score = "B"
            if leg_out_atr_ratio >= 2.5:
                quality_score = "A+"
            elif leg_out_atr_ratio >= 1.5:
                quality_score = "A"
                
            volume_confirmed = "Yes" if p_leg_out['Volume'] > p_leg_out['Vol_MA'] else "No"
            
            is_testing_zone = "No"
            curr_price = current_day['Close']
            if is_demand:
                if zone_low <= curr_price <= zone_high:
                    is_testing_zone = "🎯 Inside Demand Zone"
            else:
                if zone_low <= curr_price <= zone_high:
                    is_testing_zone = "⚠️ Inside Supply Zone"
                    
            results.append({
                "Ticker": ticker.replace(".NS", ""),
                "Full_Ticker": ticker,
                "Current Price": round(curr_price, 2),
                "Structure": structure_type,
                "Quality": quality_score,
                "Vol Confirmed": volume_confirmed,
                "Zone High": round(zone_high, 2),
                "Zone Low": round(zone_low, 2),
                "Zone Status": is_testing_zone,
                "Is_Demand": is_demand,
                "Base_Index": df.index[-3],
                "Current_Index": df.index[-1]
            })
            
        except Exception:
            continue
            
    return pd.DataFrame(results)

# 2. Main Scan Trigger Execution
if st.button("Run Market Structure Scan"):
    with st.spinner("Analyzing institutional setups..."):
        scan_results = process_sd_scan(watchlist)
        st.session_state['scan_data'] = scan_results

# 3. Handle Visualizations if Results Exist
if 'scan_data' in st.session_state and not st.session_state['scan_data'].empty:
    df_display = st.session_state['scan_data']
    st.subheader("🎯 Identified S&D Footprints")
    
    st.dataframe(df_display.drop(columns=['Full_Ticker', 'Base_Index', 'Current_Index', 'Is_Demand']).style.map(
        lambda v: 'background-color: #2e7d32; color: white;' if v in ["A+", "A"] else '', subset=["Quality"]
    ).map(
        lambda v: 'background-color: #1565c0; color: white;' if "Inside" in str(v) else '', subset=["Zone Status"]
    ), use_container_width=True)
    
    st.markdown("---")
    st.subheader("📈 S&D Structural Candlestick Visualizer")
    selected_symbol = st.selectbox("Select a scanned stock to visualize its structural zone boundaries:", df_display["Ticker"].unique())
    
    if selected_symbol:
        row = df_display[df_display["Ticker"] == selected_symbol].iloc[0]
        
        chart_stock = yf.Ticker(row['Full_Ticker'])
        chart_df = chart_stock.history(period="45d")
        
        fig = go.Figure()
        
        fig.add_trace(go.Candlestick(
            x=chart_df.index, open=chart_df['Open'], high=chart_df['High'],
            low=chart_df['Low'], close=chart_df['Close'], name=selected_symbol
        ))
        
        box_color = "rgba(46, 125, 50, 0.25)" if row['Is_Demand'] else "rgba(198, 40, 40, 0.25)"
        line_color = "#2e7d32" if row['Is_Demand'] else "#c62828"
        
        fig.add_shape(
            type="rect", x0=row['Base_Index'], x1=row['Current_Index'],
            y0=row['Zone Low'], y1=row['Zone High'],
            fillcolor=box_color, line=dict(color=line_color, width=1.5, dash="dash"),
            layer="below"
        )
        
        fig.update_layout(
            title=f"{selected_symbol} - {row['Structure']} Zone Configuration ({row['Quality']} Rating)",
            yaxis_title="Stock Price (₹)", xaxis_title="Trading Session Date",
            xaxis_rangeslider_visible=False, height=550, template="plotly_dark"
        )
        
        st.plotly_chart(fig, use_container_width=True)
elif 'scan_data' in st.session_state:
    st.info("No matching S&D structural sequences were identified on this scan run.")

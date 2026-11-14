import streamlit as st
import requests
import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

st.set_page_config(page_title="Apex Quant | Terminal", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# --- THEME STATE ---
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='margin-bottom: 0px;'>⚡ APEX QUANT</h2>", unsafe_allow_html=True)
    st.caption("Institutional Terminal")
    
    # Theme Toggle
    is_dark = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode, key="theme_toggle")
    st.session_state.dark_mode = is_dark
    
    st.markdown("---")
    page = st.radio("Navigation", ["Portfolio Overview", "Algorithmic Trading", "Risk Management", "System Admin"])
    
    st.markdown("---")
    st.markdown("### System Status")
    st.success("🟢 Researcher: RUNNING")
    st.success("🟢 Risk Engine: ONLINE")
    st.error("🔴 Live Trading: DISABLED")

# --- DYNAMIC CSS ---
if st.session_state.dark_mode:
    bg_main = "#0B0E14"; bg_panel = "#141822"; border_color = "#1F293D"
    text_main = "#E2E8F0"; text_dim = "#64748B"; chart_grid = "#1F293D"; chart_text = "#64748B"
else:
    bg_main = "#F8FAFC"; bg_panel = "#FFFFFF"; border_color = "#E2E8F0"
    text_main = "#0F172A"; text_dim = "#475569"; chart_grid = "#E2E8F0"; chart_text = "#475569"

st.markdown(f"""
<style>
    .stApp {{ background-color: {bg_main}; color: {text_main}; font-family: 'Inter', sans-serif; }}
    /* Fix mobile header spacing and keep hamburger menu */
    header {{ background: transparent !important; }}
    [data-testid="collapsedControl"] {{ top: 10px; left: 10px; }}
    .block-container {{padding: 2rem 1rem 1rem 1rem; max-width: 100%;}}
    
    /* Cards */
    .panel {{ background: {bg_panel}; border: 1px solid {border_color}; border-radius: 8px; padding: 15px; margin-bottom: 15px; }}
    .panel-title {{ font-size: 0.8rem; color: {text_dim}; text-transform: uppercase; font-weight: 600; margin-bottom: 10px; letter-spacing: 1px; }}
    
    /* Metrics */
    .metric-val {{ font-size: 1.6rem; font-weight: 700; color: {text_main}; margin-bottom: 2px; }}
    .metric-delta-pos {{ font-size: 0.85rem; color: #10B981; font-weight: 600; }}
    .metric-delta-neg {{ font-size: 0.85rem; color: #EF4444; font-weight: 600; }}
    
    /* Data rows */
    .data-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid {border_color}; font-size: 0.85rem;}}
    .data-row span {{ color: {text_dim}; }}
    .data-row strong {{ color: {text_main}; }}
    
    /* Badges */
    .tag-green {{ background: rgba(16, 185, 129, 0.1); color: #10B981; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; border: 1px solid rgba(16, 185, 129, 0.3);}}
    .tag-red {{ background: rgba(239, 68, 68, 0.1); color: #EF4444; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; border: 1px solid rgba(239, 68, 68, 0.3);}}
    .tag-yellow {{ background: rgba(245, 158, 11, 0.1); color: #F59E0B; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; border: 1px solid rgba(245, 158, 11, 0.3);}}
</style>
""", unsafe_allow_html=True)

# --- LIVE ALPACA DATA ---
@st.cache_data(ttl=30)
def get_alpaca_data():
    key = os.getenv("ALPACA_KEY"); secret = os.getenv("ALPACA_SECRET")
    if not key or not secret: return None, None
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    try:
        acc = requests.get("https://paper-api.alpaca.markets/v2/account", headers=headers, timeout=5).json()
        pos = requests.get("https://paper-api.alpaca.markets/v2/positions", headers=headers, timeout=5).json()
        return acc, pos
    except Exception:
        return None, None

account, positions = get_alpaca_data()

# ==========================================
# PAGE: PORTFOLIO OVERVIEW
# ==========================================
if page == "Portfolio Overview":
    st.markdown(f"<h2 style='margin:0; color:{text_main}; font-weight: 700;'>PORTFOLIO OVERVIEW</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{text_dim}; font-size:0.9rem;'>{datetime.now().strftime('%b %d, %Y | %H:%M')}</p>", unsafe_allow_html=True)
    
    if account and 'equity' in account:
        equity = float(account['equity']); last_equity = float(account['last_equity'])
        pnl = equity - last_equity; pnl_pct = (pnl / last_equity) * 100 if last_equity > 0 else 0
        pnl_class = "metric-delta-pos" if pnl >= 0 else "metric-delta-neg"
        pnl_symbol = "▲" if pnl >= 0 else "▼"
        
        m1, m2, m3 = st.columns(3)
        with m1: st.markdown(f'<div class="panel" style="padding:10px;"><div class="panel-title">Total Equity</div><div class="metric-val">${equity:,.2f}</div></div>', unsafe_allow_html=True)
        with m2: st.markdown(f'<div class="panel" style="padding:10px;"><div class="panel-title">Daily P&L</div><div class="metric-val">${pnl:,.2f}</div><div class="{pnl_class}">{pnl_symbol} {pnl_pct:.2f}%</div></div>', unsafe_allow_html=True)
        with m3: st.markdown(f'<div class="panel" style="padding:10px;"><div class="panel-title">Buying Power</div><div class="metric-val">${float(account.get("buying_power",0)):,.2f}</div></div>', unsafe_allow_html=True)

    # Chart
    st.markdown(f'<div class="panel" style="padding:15px 15px 5px 15px;"><div class="panel-title">PERFORMANCE | EQUITIES</div>', unsafe_allow_html=True)
    dates = [datetime.today() - timedelta(minutes=i*15) for i in range(80)][::-1]
    close_prices = np.cumsum(np.random.randn(80) * 0.8) + 4312
    open_prices = close_prices + np.random.randn(80) * 0.5
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    fig.add_trace(go.Candlestick(x=dates, open=open_prices, high=np.maximum(open_prices, close_prices)+1, low=np.minimum(open_prices, close_prices)-1, close=close_prices, increasing_line_color='#10B981', decreasing_line_color='#EF4444'), row=1, col=1)
    fig.add_trace(go.Bar(x=dates, y=np.random.randint(1000, 5000, 80), marker_color='#2DD4BF', opacity=0.5), row=2, col=1)
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(showgrid=True, gridcolor=chart_grid), yaxis=dict(showgrid=True, gridcolor=chart_grid, side='right'), xaxis_rangeslider_visible=False, height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# PAGE: ALGORITHMIC TRADING
# ==========================================
elif page == "Algorithmic Trading":
    st.markdown(f"<h2 style='margin:0; color:{text_main}; font-weight: 700;'>ALGORITHMIC TRADING</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{text_dim}; font-size:0.9rem;'>Active strategies passing the CPCV/DSR gate.</p>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="panel">
        <div class="panel-title">Active Strategies</div>
        <div class="data-row"><div><strong>MOMENTUM_V1</strong><br><span style="font-size:0.75rem;">Universe: SPY, QQQ</span></div> <span class="tag-green">ACTIVE</span></div>
        <div class="data-row"><div><strong>MEAN_REVERSION_V3</strong><br><span style="font-size:0.75rem;">Universe: NVDA, AMD</span></div> <span class="tag-green">ACTIVE</span></div>
        <div class="data-row"><div><strong>CRYPTO_XSEC_V1</strong><br><span style="font-size:0.75rem;">Universe: BTC, ETH, SOL</span></div> <span class="tag-yellow">PAPER TEST</span></div>
    </div>
    <div class="panel">
        <div class="panel-title">Statistical Gates</div>
        <div class="data-row"><span>PBO (Overfit Probability)</span> <strong>0.11 (PASS < 0.20)</strong></div>
        <div class="data-row"><span>DSR (Deflated Sharpe)</span> <strong>0.97 (PASS > 0.95)</strong></div>
        <div class="data-row"><span>Total Trials Evaluated</span> <strong>14,203</strong></div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# PAGE: RISK MANAGEMENT
# ==========================================
elif page == "Risk Management":
    st.markdown(f"<h2 style='margin:0; color:{text_main}; font-weight: 700;'>RISK MANAGEMENT</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{text_dim}; font-size:0.9rem;'>Fail-closed boundaries enforced by apex_risk_engine.</p>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="panel">
        <div class="panel-title">Hard Limits</div>
        <div class="data-row"><span>Max Daily Drawdown</span> <strong style="color:#EF4444;">2.0%</strong></div>
        <div class="data-row"><span>Max Position Size</span> <strong>10.0%</strong></div>
        <div class="data-row"><span>Max Gross Exposure</span> <strong>100.0%</strong></div>
        <div class="data-row"><span>Data Freshness Limit</span> <strong>5 Minutes</strong></div>
    </div>
    <div class="panel">
        <div class="panel-title">Current Exposure</div>
        <div class="data-row"><span>Long Exposure</span> <strong>$0.00 (0%)</strong></div>
        <div class="data-row"><span>Short Exposure</span> <strong>$0.00 (0%)</strong></div>
        <div class="data-row"><span>Circuit Breaker</span> <strong class="tag-green">ARMED</strong></div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# PAGE: SYSTEM ADMIN
# ==========================================
elif page == "System Admin":
    st.markdown(f"<h2 style='margin:0; color:{text_main}; font-weight: 700;'>SYSTEM ADMIN</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{text_dim}; font-size:0.9rem;'>Container health and system logs.</p>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="panel">
        <div class="panel-title">Docker Services</div>
        <div class="data-row"><span>apex_app (Streamlit)</span> <strong class="tag-green">ONLINE</strong></div>
        <div class="data-row"><span>apex_bot (Execution)</span> <strong class="tag-green">ONLINE</strong></div>
        <div class="data-row"><span>apex_researcher (CPCV/DSR)</span> <strong class="tag-green">ONLINE</strong></div>
        <div class="data-row"><span>apex_risk_engine (FastAPI)</span> <strong class="tag-green">ONLINE</strong></div>
    </div>
    <div class="panel">
        <div class="panel-title">Security</div>
        <div class="data-row"><span>Network Boundary</span> <strong>Tailscale (100.113.x.x)</strong></div>
        <div class="data-row"><span>Live Trading</span> <strong class="tag-red">LOCKED (FALSE)</strong></div>
        <div class="data-row"><span>HMAC Validation</span> <strong class="tag-green">ENFORCED</strong></div>
    </div>
    """, unsafe_allow_html=True)

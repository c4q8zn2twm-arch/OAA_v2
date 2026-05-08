import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="Trading Replay",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# CUSTOM CSS (BASELINE — DO NOT REMOVE)
# -------------------------------------------------
st.markdown("""
<style>
body {
    background-color: #0e1117;
}
.card {
    background: #161b22;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 16px;
    border: 1px solid #30363d;
}
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
}
.initiative { background: #1f6feb; color: white; }
.rotational { background: #8b949e; color: black; }
.long { background: #2ea043; color: white; }
.short { background: #da3633; color: white; }
.rr-good { color: #2ea043; font-weight: bold; }
.rr-bad { color: #da3633; font-weight: bold; }
.asset-box {
    background: #111827;
    border: 1px solid #374151;
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# SESSION STATE INIT
# -------------------------------------------------
state_defaults = {
    "df": None,
    "index": 0,
    "position": None,
    "manual_trades": [],
    "auto_trades": [],
    "confirm_delete": None,
}

for k, v in state_defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
with st.sidebar:
    st.markdown("## 🔍 Market Context")

    symbol = st.text_input("Symbol", value="AAPL")

    st.caption("Examples:")
    st.caption("• Stocks: AAPL, MSFT, TSLA")
    st.caption("• FX: EURUSD=X, GBPJPY=X")
    st.caption("• Crypto: BTC-USD, ETH-USD")
    st.caption("• Futures: ES=F, NQ=F")

    # ---------------------------------------------
    # TIMEFRAME SELECTOR
    # ---------------------------------------------
    timeframe = st.selectbox(
        "Timeframe",
        [
            "1M",
            "5M",
            "15M",
            "30M",
            "1Hr",
            "4Hr",
            "1Week",
            "1 Month"
        ],
        index=1
    )

    interval_map = {
        "1M": ("1m", "7d"),
        "5M": ("5m", "30d"),
        "15M": ("15m", "60d"),
        "30M": ("30m", "60d"),
        "1Hr": ("60m", "730d"),
        "4Hr": ("1h", "730d"),
        "1Week": ("1wk", "10y"),
        "1 Month": ("1mo", "max"),
    }

    interval, period = interval_map[timeframe]

    now = datetime.now()

    st.markdown("### ⏱ Current Time")
    st.write(now.strftime("%Y-%m-%d %H:%M:%S"))

    st.markdown("### 📊 Day Type")

    day_type = st.selectbox(
        "Override Day Type",
        ["Initiative", "Rotational", "Neutral"]
    )

    badge_class = (
        "initiative" if day_type == "Initiative"
        else "rotational" if day_type == "Rotational"
        else ""
    )

    if badge_class:
        st.markdown(
            f'<span class="badge {badge_class}">{day_type}</span>',
            unsafe_allow_html=True
        )

# -------------------------------------------------
# LOAD ASSET
# -------------------------------------------------
try:
    ticker = yf.Ticker(symbol)

    info = ticker.info

    asset_name = info.get("longName") or info.get("shortName") or "Unknown Asset"
    exchange = info.get("exchange", "Unknown Exchange")
    quote_type = info.get("quoteType", "Unknown Type")
    currency = info.get("currency", "Unknown Currency")

    df = ticker.history(
        period=period,
        interval=interval
    )

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()

    if "Datetime" in df.columns:
        df.rename(columns={"Datetime": "Date"}, inplace=True)

    if "Date" not in df.columns:
        df.rename(columns={"index": "Date"}, inplace=True)

    df["time"] = df["Date"]

    for col in ["Open", "High", "Low", "Close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna()

    if len(df) == 0:
        st.error("No market data returned for this symbol.")
        st.stop()

    st.session_state.df = df

except Exception as e:
    st.error(f"Failed to load market data: {e}")
    st.stop()

# -------------------------------------------------
# MARKET LEVELS
# -------------------------------------------------
opening_range = df.iloc[:6]
premarket = df.iloc[:24]

OH = float(opening_range["High"].max())
OL = float(opening_range["Low"].min())

PMH = float(premarket["High"].max())
PML = float(premarket["Low"].min())

PDH = float(df["High"].max())
PDL = float(df["Low"].min())

# -------------------------------------------------
# HEADER
# -------------------------------------------------
st.markdown(f"## 📈 {asset_name}")
st.caption("Unified Manual & Automated Trading Replay")

# -------------------------------------------------
# VERIFIED ASSET INFO
# -------------------------------------------------
st.markdown(f"""
<div class="asset-box">
<b>Verified Instrument</b><br><br>

Ticker:
<b>{symbol}</b><br>

Resolved Name:
<b>{asset_name}</b><br>

Exchange:
<b>{exchange}</b><br>

Asset Type:
<b>{quote_type}</b><br>

Currency:
<b>{currency}</b><br>

Timeframe:
<b>{timeframe}</b>
</div>
""", unsafe_allow_html=True)

if asset_name == "Unknown Asset":
    st.warning(
        "Unable to fully verify instrument identity. "
        "Double-check the symbol before trading."
    )

# -------------------------------------------------
# CHART
# -------------------------------------------------
st.markdown("## Price Chart")

fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=df["time"],
    open=df["Open"],
    high=df["High"],
    low=df["Low"],
    close=df["Close"],
    name=f"{asset_name} ({symbol})"
))

def add_level(price, label):
    if price is not None:
        fig.add_hline(
            y=float(price),
            line_dash="dash",
            annotation_text=label
        )

add_level(OH, "OH")
add_level(OL, "OL")
add_level(PMH, "PMH")
add_level(PML, "PML")
add_level(PDH, "PDH")
add_level(PDL, "PDL")

fig.update_layout(
    title=f"{asset_name} ({symbol}) - {timeframe}",
    height=520,
    dragmode="zoom",
    xaxis=dict(
        rangeslider=dict(visible=True),
        fixedrange=False
    ),
    yaxis=dict(
        fixedrange=False
    )
)

st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------
# TABS
# -------------------------------------------------
tab_auto, tab_manual, tab_both = st.tabs(
    ["🤖 Automatic", "🎮 Manual", "🧠 Combined"]
)

# =================================================
# AUTOMATIC TAB
# =================================================
with tab_auto:
    st.markdown("### 🤖 Automated Suggestions")

    rr = round(np.random.uniform(0.5, 3.0), 2)
    direction = np.random.choice(["Long", "Short"])

    if rr >= 1:
        rr_class = "rr-good" if rr >= 2 else "rr-bad"
        dir_class = "long" if direction == "Long" else "short"

        st.markdown(f"""
        <div class="card">
            <span class="badge {dir_class}">{direction}</span><br><br>
            Risk:Reward →
            <span class="{rr_class}">{rr}</span>
        </div>
        """, unsafe_allow_html=True)

# =================================================
# MANUAL TAB
# =================================================
with tab_manual:
    st.markdown("### 🎮 Manual Replay")

    idx = min(st.session_state.index, len(df) - 1)
    row = df.iloc[idx]

    st.markdown(f"""
    <div class="card">
    <b>{row.Date}</b><br>
    O: {row.Open:.2f} |
    H: {row.High:.2f} |
    L: {row.Low:.2f} |
    C: {row.Close:.2f}
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("⬅ Previous") and idx > 0:
            st.session_state.index -= 1

    with col2:
        if st.button("Next ➡") and idx < len(df) - 1:
            st.session_state.index += 1

    with col3:
        if st.button("🔄 Reset"):
            st.session_state.index = 0
            st.session_state.position = None

# =================================================
# COMBINED TAB
# =================================================
with tab_both:
    st.markdown("### 🧠 Price Overview")

    chart_df = df.set_index("Date")[["Close"]]
    st.line_chart(chart_df)

# -------------------------------------------------
# JOURNALS
# -------------------------------------------------
st.markdown("## 📒 Trade Journals")

def render_journal(title, trades, key_prefix):
    st.markdown(f"### {title}")

    if not trades:
        st.info("No trades yet.")
        return

    df_trades = pd.DataFrame(trades)

    st.dataframe(df_trades, use_container_width=True)

    for i in range(len(trades)):
        if st.button(f"🗑 Delete Trade {i+1}", key=f"{key_prefix}_del_{i}"):
            st.session_state.confirm_delete = (key_prefix, i)

    if st.session_state.confirm_delete:
        k, i = st.session_state.confirm_delete

        if k == key_prefix:
            st.warning("Confirm deletion?")

            c1, c2 = st.columns(2)

            if c1.button("Yes, delete"):
                trades.pop(i)
                st.session_state.confirm_delete = None

            if c2.button("Cancel"):
                st.session_state.confirm_delete = None

render_journal(
    "Manual Trades",
    st.session_state.manual_trades,
    "manual"
)

render_journal(
    "Automated Trades",
    st.session_state.auto_trades,
    "auto"
)

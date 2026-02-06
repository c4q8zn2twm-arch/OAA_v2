import streamlit as st
import pandas as pd
import numpy as np
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
# DEMO DATA (SAFE, NO API)
# -------------------------------------------------
dates = pd.date_range(
    start=now.replace(hour=4, minute=0),
    periods=300,
    freq="1min"
)

price = 100 + np.cumsum(np.random.normal(0, 0.05, size=len(dates)))

df = pd.DataFrame({
    "Date": dates,
    "Open": price,
    "High": price + 0.15,
    "Low": price - 0.15,
    "Close": price,
    "Volume": 1000
})

st.session_state.df = df

# -------------------------------------------------
# HEADER
# -------------------------------------------------
st.markdown(f"## 📈 {symbol}")
st.caption("Unified Manual & Automated Trading Replay")

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

    idx = st.session_state.index
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

render_journal("Manual Trades", st.session_state.manual_trades, "manual")
render_journal("Automated Trades", st.session_state.auto_trades, "auto")

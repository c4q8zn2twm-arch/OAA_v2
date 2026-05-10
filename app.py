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

    symbol = st.text_input(
        "Symbol",
        value="AAPL"
    )

    st.caption("Examples:")
    st.caption("• Stocks: AAPL, MSFT, TSLA")
    st.caption("• FX: EURUSD=X, GBPJPY=X")
    st.caption("• Crypto: BTC-USD, ETH-USD")
    st.caption("• Futures: ES=F, NQ=F")

    # ---------------------------------------------
    # ASSET CLASS DETECTION
    # ---------------------------------------------
    upper_symbol = symbol.upper()

    if "=F" in upper_symbol:
        asset_class = "Futures"

    elif "-USD" in upper_symbol:
        asset_class = "Crypto"

    elif "=X" in upper_symbol:
        asset_class = "Forex"

    else:
        asset_class = "Equity"

    # ---------------------------------------------
    # TIMEFRAME OPTIONS
    # ---------------------------------------------
    timeframe_options = {
        "Futures": [
            "1M",
            "5M",
            "15M",
            "30M",
            "1Hr",
            "4Hr",
            "1Day",
            "1Week"
        ],

        "Equity": [
            "1M",
            "5M",
            "15M",
            "30M",
            "1Hr",
            "4Hr",
            "1Day",
            "1Week",
            "1 Month"
        ],

        "Forex": [
            "1M",
            "5M",
            "15M",
            "30M",
            "1Hr",
            "4Hr",
            "1Day",
            "1Week"
        ],

        "Crypto": [
            "1M",
            "5M",
            "15M",
            "30M",
            "1Hr",
            "4Hr",
            "1Day",
            "1Week",
            "1 Month"
        ]
    }

    timeframe = st.selectbox(
        "Timeframe",
        timeframe_options[asset_class],
        index=1
    )

    # ---------------------------------------------
    # INTERVAL MAP
    # ---------------------------------------------
    interval_map = {
        "1M": ("1m", "7d"),
        "5M": ("5m", "30d"),
        "15M": ("15m", "60d"),
        "30M": ("30m", "60d"),
        "1Hr": ("60m", "730d"),
        "4Hr": ("1h", "730d"),
        "1Day": ("1d", "10y"),
        "1Week": ("1wk", "10y"),
        "1 Month": ("1mo", "max"),
    }

    interval, period = interval_map[timeframe]

    # ---------------------------------------------
    # SESSION FILTERS
    # ---------------------------------------------
    st.markdown("### 🕒 Session Filters")

    if asset_class == "Futures":

        rth_only = st.checkbox(
            "RTH Only",
            value=True
        )

        exclude_lunch = st.checkbox(
            "Exclude Lunch Session",
            value=True
        )

        exclude_overnight = st.checkbox(
            "Exclude Overnight",
            value=True
        )

        show_low_quality_tfs = st.checkbox(
            "Show Excluded Futures Timeframes",
            value=False
        )

    elif asset_class == "Equity":

        rth_only = st.checkbox(
            "RTH Only",
            value=True
        )

        exclude_lunch = st.checkbox(
            "Exclude Lunch Session",
            value=False
        )

        exclude_overnight = True
        show_low_quality_tfs = True

    elif asset_class == "Forex":

        rth_only = False

        exclude_lunch = st.checkbox(
            "Exclude Midday Session",
            value=False
        )

        exclude_overnight = False
        show_low_quality_tfs = True

    else:
        # Crypto
        rth_only = False
        exclude_lunch = False
        exclude_overnight = False
        show_low_quality_tfs = True

    # ---------------------------------------------
    # FUTURES TIMEFRAME FILTERING
    # ---------------------------------------------
    if asset_class == "Futures":

        excluded_futures_tfs = [
            "1M"
        ]

        if (
            not show_low_quality_tfs and
            timeframe in excluded_futures_tfs
        ):
            st.warning(
                f"{timeframe} is commonly excluded "
                f"by futures traders due to noise."
            )

    now = datetime.now()

    st.markdown("### ⏱ Current Time")
    st.write(
        now.strftime("%Y-%m-%d %H:%M:%S")
    )

    st.markdown("### 📊 Day Type")

    day_type = st.selectbox(
        "Override Day Type",
        [
            "Initiative",
            "Rotational",
            "Neutral"
        ]
    )

    badge_class = (
        "initiative"
        if day_type == "Initiative"
        else "rotational"
        if day_type == "Rotational"
        else ""
    )

    if badge_class:
        st.markdown(
            f'<span class="badge {badge_class}">{day_type}</span>',
            unsafe_allow_html=True
        )
# -------------------------------------------------
# CACHED MARKET DATA
# -------------------------------------------------
@st.cache_data(ttl=600)
def load_market_data(symbol, period, interval):

    ticker = yf.Ticker(symbol)

    info = ticker.info

    df = ticker.history(
        period=period,
        interval=interval
    )

    return info, df

# -------------------------------------------------
# LOAD ASSET
# -------------------------------------------------
try:

    info, df = load_market_data(
        symbol,
        period,
        interval
    )

    asset_name = (
        info.get("longName")
        or info.get("shortName")
        or "Unknown Asset"
    )

    exchange = info.get(
        "exchange",
        "Unknown Exchange"
    )

    quote_type = info.get(
        "quoteType",
        "Unknown Type"
    )

    currency = info.get(
        "currency",
        "Unknown Currency"
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
# LEVEL CALCULATIONS
# -------------------------------------------------
df["date"] = pd.to_datetime(df["Date"]).dt.date
df["session"] = pd.to_datetime(df["Date"]).dt.time

def opening_range(df):
    or_df = df[
        (df["session"] >= datetime.strptime("09:30", "%H:%M").time()) &
        (df["session"] <= datetime.strptime("09:35", "%H:%M").time())
    ]

    if or_df.empty:
        return None, None

    return (
        float(or_df["High"].max()),
        float(or_df["Low"].min())
    )

def premarket_levels(df):
    pm = df[
        df["session"] < datetime.strptime("09:30", "%H:%M").time()
    ]

    if pm.empty:
        return None, None

    return (
        float(pm["High"].max()),
        float(pm["Low"].min())
    )

def prior_day_levels(df):
    dates = sorted(df["date"].unique())

    if len(dates) < 2:
        return None, None, None

    prior = df[df["date"] == dates[-2]]

    return (
        float(prior["High"].max()),
        float(prior["Low"].min()),
        float(prior["Open"].iloc[0])
    )

OH, OL = opening_range(df)

PMH, PML = premarket_levels(df)

PDH, PDL, PDO = prior_day_levels(df)

# -------------------------------------------------
# HEADER
# -------------------------------------------------
st.markdown(f"## 📈 {asset_name}")
st.caption("Unified Manual & Automated Trading Replay")

# -------------------------------------------------
# KEY LEVELS DISPLAY
# -------------------------------------------------
st.markdown(f"## 📊 {symbol.upper()} Key Levels")

level_col1, level_col2, level_col3 = st.columns(3)

with level_col1:
    st.markdown(f"""
    <div class="card">
    <b>5 Min Opening Range</b><br><br>

    OH:
    <b>{f"{OH:.2f}" if OH is not None else "N/A"}</b><br>

    OL:
    <b>{f"{OL:.2f}" if OL is not None else "N/A"}</b>
    </div>
    """, unsafe_allow_html=True)

with level_col2:
    st.markdown(f"""
    <div class="card">
    <b>Premarket</b><br><br>

    PMH:
    <b>{f"{PMH:.2f}" if PMH is not None else "N/A"}</b><br>

    PML:
    <b>{f"{PML:.2f}" if PML is not None else "N/A"}</b>
    </div>
    """, unsafe_allow_html=True)

with level_col3:
    st.markdown(f"""
    <div class="card">
    <b>Prior Day</b><br><br>

    PDH:
    <b>{f"{PDH:.2f}" if PDH is not None else "N/A"}</b><br>

    PDL:
    <b>{f"{PDL:.2f}" if PDL is not None else "N/A"}</b><br>

    PDO:
    <b>{f"{PDO:.2f}" if PDO is not None else "N/A"}</b>
    </div>
    """, unsafe_allow_html=True)
    
# -------------------------------------------------
# VERIFIED ASSET INFO (SIDEBAR)
# -------------------------------------------------
with st.sidebar:
    st.markdown("### ✅ Verified Instrument")

    st.markdown(f"""
    <div class="asset-box">

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
# DYNAMIC SESSION WINDOWS
# -------------------------------------------------
valid_trade_windows = []

if asset_class in ["Equity", "Futures"]:

    if exclude_lunch:

        valid_trade_windows = [
            (
                datetime.strptime("09:30", "%H:%M").time(),
                datetime.strptime("11:30", "%H:%M").time()
            ),
            (
                datetime.strptime("13:00", "%H:%M").time(),
                datetime.strptime("16:00", "%H:%M").time()
            )
        ]

    else:

        valid_trade_windows = [
            (
                datetime.strptime("09:30", "%H:%M").time(),
                datetime.strptime("16:00", "%H:%M").time()
            )
        ]

elif asset_class == "Forex":

    valid_trade_windows = [
        (
            datetime.strptime("03:00", "%H:%M").time(),
            datetime.strptime("17:00", "%H:%M").time()
        )
    ]

else:
    # Crypto
    valid_trade_windows = [
        (
            datetime.strptime("00:00", "%H:%M").time(),
            datetime.strptime("23:59", "%H:%M").time()
        )
    ]
# -------------------------------------------------
# TRADE SIGNAL ENGINE
# -------------------------------------------------
def rr(entry, stop, target):
    risk = abs(entry - stop)
    reward = abs(target - entry)

    return round(reward / risk, 2) if risk else 0

signals = []

def in_valid_window(t):
    return any(
        start <= t <= end
        for start, end in valid_trade_windows
    )

# -------------------------------------------------
# TRADE OUTCOME ENGINE
# -------------------------------------------------
def evaluate_trade_outcome(
    df,
    start_index,
    side,
    entry,
    stop,
    target
):
    outcome = "OPEN"
    exit_price = None
    exit_time = None

    for j in range(start_index + 1, len(df)):

        future_candle = df.iloc[j]

        high = future_candle["High"]
        low = future_candle["Low"]

        # -----------------------------------------
        # LONG TRADES
        # -----------------------------------------
        if side == "LONG":

            # Stop hit first
            if low <= stop:
                outcome = "STOPPED"
                exit_price = stop
                exit_time = future_candle["time"]
                break

            # Target hit
            if high >= target:
                outcome = "TARGET HIT"
                exit_price = target
                exit_time = future_candle["time"]
                break

        # -----------------------------------------
        # SHORT TRADES
        # -----------------------------------------
        elif side == "SHORT":

            # Stop hit first
            if high >= stop:
                outcome = "STOPPED"
                exit_price = stop
                exit_time = future_candle["time"]
                break

            # Target hit
            if low <= target:
                outcome = "TARGET HIT"
                exit_price = target
                exit_time = future_candle["time"]
                break

    return (
        outcome,
        exit_price,
        exit_time
    )

for i in range(5, len(df)):

    candle = df.iloc[i]
    prev = df.iloc[i - 1]

    candle_time = pd.to_datetime(
        candle["time"]
    ).time()

    # ---------------------------------------------
    # IGNORE INVALID TIMES
    # ---------------------------------------------
    if not in_valid_window(candle_time):
        continue

    # Initiative LONG
    if (
        OH is not None and
        PDH is not None and
        OL is not None
    ):
        if (
            candle["Close"] > OH and
            candle["Close"] > prev["High"]
        ):
            entry = candle["Close"]
            stop = OL
            target = PDH

            rr_val = rr(entry, stop, target)

            if rr_val >= 1:
                outcome, exit_price, exit_time = evaluate_trade_outcome(
    df=df,
    start_index=i,
    side="LONG",
    entry=entry,
    stop=stop,
    target=target
)

signals.append({
    "Type": "OAA-I",
    "Side": "LONG",
    "Time": candle["time"],
    "Entry": round(entry, 2),
    "Stop": round(stop, 2),
    "Target": round(target, 2),
    "RR": rr_val,
    "Quality": "A+" if rr_val >= 2 else "B",
    "Outcome": outcome,
    "Exit Price": (
        round(exit_price, 2)
        if exit_price is not None
        else None
    ),
    "Exit Time": exit_time
})

    # Rotational SHORT
if (
        OH is not None and
        PDO is not None
    ):
        if (
            candle["High"] > OH and
            candle["Close"] < OH
        ):
            entry = candle["Close"]
            stop = candle["High"]
            target = PDO

            rr_val = rr(entry, stop, target)

            if rr_val >= 1:
               outcome, exit_price, exit_time = evaluate_trade_outcome(
    df=df,
    start_index=i,
    side="SHORT",
    entry=entry,
    stop=stop,
    target=target
)

signals.append({
    "Type": "OAA-R",
    "Side": "SHORT",
    "Time": candle["time"],
    "Entry": round(entry, 2),
    "Stop": round(stop, 2),
    "Target": round(target, 2),
    "RR": rr_val,
    "Quality": "A+" if rr_val >= 2 else "B",
    "Outcome": outcome,
    "Exit Price": (
        round(exit_price, 2)
        if exit_price is not None
        else None
    ),
    "Exit Time": exit_time
})

signals_df = pd.DataFrame(signals)

# -------------------------------------------------
# SIGNAL TABLE STYLING
# -------------------------------------------------
def highlight_rr(row):

    if row["Outcome"] == "TARGET HIT":
        return [
            "background-color: #0f5132; color: white"
        ] * len(row)

    if row["Outcome"] == "STOPPED":
        return [
            "background-color: #5a1a1a; color: white"
        ] * len(row)

    if row["RR"] >= 2:
        return [
            "background-color: #1f3b63; color: white"
        ] * len(row)

    return [""] * len(row)

# -------------------------------------------------
# AUTOMATED TRADE SUGGESTIONS
# -------------------------------------------------
st.markdown("## 📡 Automated Trade Suggestions")

if signals_df.empty:
    st.info("No valid setups detected.")
else:

    # ---------------------------------------------
    # DATE FILTER
    # ---------------------------------------------
    signals_df["Signal Date"] = pd.to_datetime(
        signals_df["Time"]
    ).dt.date

    available_dates = sorted(
        signals_df["Signal Date"].unique(),
        reverse=True
    )

    selected_date = st.selectbox(
        "View Signal History",
        available_dates,
        format_func=lambda x: x.strftime("%Y-%m-%d")
    )

    filtered_signals = signals_df[
        signals_df["Signal Date"] == selected_date
    ].copy()

    filtered_signals = filtered_signals.drop(
        columns=["Signal Date"]
    )

    st.dataframe(
        filtered_signals.style.apply(
            highlight_rr,
            axis=1
        ),
        use_container_width=True
    )


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

#render_journal(
#    "Manual Trades",
 #   st.session_state.manual_trades,
  #  "manual"
#)

render_journal(
    "Automated Trades",
    st.session_state.auto_trades,
    "auto"
)

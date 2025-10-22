import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# ---------------------
# CONFIG
# ---------------------
API_BASE = "http://localhost:5000/api/v1"

# CSS for a clean, modern UI
st.markdown("""
<style>
    /* Sidebar & main layout polish */
    .css-1d391kg { background: linear-gradient(to bottom right, #f0f4f8, #d9e2ec); padding: 1rem; }
    .css-1dcb7u2 { padding-top: 1rem; padding-bottom: 1rem; }
    .stHeader { padding: 1rem 0; }
    .main-content { padding: 1rem 1.5rem; border-left: 0; }
    /* KPI cards */
    .metric-card {
        background: #eef6ff;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        text-align: center;
        box-shadow: 0 2px 6px rgb(0 0 0 / 0.08);
        color: #0b6efd;
        font-weight: 600;
    }
    .metric-value { font-size: 2.2rem; margin-top: 0.25rem; }
    .date-text { font-size: 0.95rem; color: #4b5a66; }
</style>
""", unsafe_allow_html=True)

# Utility: ordinal date (1st, 2nd, 3rd, 4th)
def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

def format_date(dt: datetime):
    return f"{ordinal(dt.day)} {dt.strftime('%b %Y')}"

# ---------------------
# Helpers
# ---------------------
def fetch_api(path, params=None):
    url = f"{API_BASE}/{path}"
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def parse_predictions(payload):
    if not payload or (isinstance(payload, dict) and 'error' in payload):
        return None, payload.get('error') if isinstance(payload, dict) else "No data"

    preds = None
    if isinstance(payload, dict) and 'data' in payload and 'predictions' in payload['data']:
        preds = payload['data']['predictions']
    elif isinstance(payload, dict) and 'predictions' in payload:
        preds = payload['predictions']
    else:
        preds = payload

    if isinstance(preds, dict):
        df = pd.DataFrame(list(preds.items()), columns=['date', 'value'])
        df['date'] = pd.to_datetime(df['date'])
        df['value'] = df['value'].round().astype(int)
        return df.sort_values('date'), None

    if isinstance(preds, list):
        if len(preds) > 0 and isinstance(preds[0], dict):
            date_key = None
            value_key = None
            candidates = preds[0].keys()
            for k in candidates:
                lk = k.lower()
                if lk in ("date", "ds", "day"):
                    date_key = k
                if lk in ("value", "y", "tickets", "count", "volume"):
                    value_key = k
            if not date_key and len(candidates) >= 1:
                date_key = list(candidates)[0]
            if not value_key and len(candidates) >= 2:
                value_key = list(candidates)[1]

            rows = []
            for item in preds:
                try:
                    d = item.get(date_key) if date_key in item else None
                    v = item.get(value_key) if value_key in item else None
                    rows.append((d, v))
                except Exception:
                    continue
            df = pd.DataFrame(rows, columns=['date', 'value'])
            try:
                df['date'] = pd.to_datetime(df['date'])
                df['value'] = df['value'].round().astype(int)
            except Exception:
                pass
            return df.sort_values('date'), None

        if all(isinstance(x, (int, float)) for x in preds):
            today = datetime.now().date()
            rows = [(today + timedelta(days=i), round(preds[i])) for i in range(len(preds))]
            df = pd.DataFrame(rows, columns=['date', 'value'])
            df['date'] = pd.to_datetime(df['date'])
            return df, None

    return None, "Unable to parse prediction payload"

# Plot with Plotly (interactive hover)
def plot_predictions(df, title="Ticket Volume Predictions"):
    if df is None or df.empty:
        st.warning("No prediction data to plot")
        return

    df['date_str'] = df['date'].dt.day.map(ordinal) + df['date'].dt.strftime(" %b %Y")

    max_idx = df['value'].idxmax()
    min_idx = df['value'].idxmin()

    fig = px.bar(
        df,
        x='date',
        y='value',
        labels={'date': 'Date', 'value': 'Ticket Volume'},
        title=title,
        color=df.index.map(lambda i: 'max' if i==max_idx else ('min' if i==min_idx else 'normal')),
        color_discrete_map={'max':'#ff4d4d','min':'#2ca02c','normal':'#0b6efd'},
        hover_data={'date_str': True, 'date': False, 'value': True}
    )
    fig.update_traces(hovertemplate="<b>%{x|%d %B %Y}</b><br>Tickets: %{y}<extra></extra>",
                      marker=dict(line=dict(width=0)))
    fig.update_layout(
        plot_bgcolor='white',
        hoverlabel_bgcolor="#0b6efd",
        hoverlabel_font_color="white",
        hoverlabel_font_size=12,
        margin=dict(t=80, b=60),
        xaxis_tickformat="%d %b",
        xaxis_title_font=dict(size=14),
        yaxis_title_font=dict(size=14),
        font=dict(color="#334e68")
    )
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, use_container_width=True)

    total = int(df['value'].sum())
    max_v = int(df.loc[max_idx, 'value'])
    min_v = int(df.loc[min_idx, 'value'])
    max_date = df.loc[max_idx, 'date']
    min_date = df.loc[min_idx, 'date']

    st.markdown("---")
    st.markdown("### Summary")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            Total Tickets
            <div class="metric-value">{total:,}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card" style="background-color:#ffe6e6; color:#b30000;">
            Max Tickets
            <div class="metric-value">{max_v:,}</div>
            <div class="date-text">{format_date(max_date)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card" style="background-color:#e6ffe6; color:#237a27;">
            Min Tickets
            <div class="metric-value">{min_v:,}</div>
            <div class="date-text">{format_date(min_date)}</div>
        </div>
        """, unsafe_allow_html=True)

# ---------------------
# UI Layout
# ---------------------
st.markdown("<h1 style='color:#0b6efd; text-align:center;'> Ticket Prediction Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#334e68;'>Hit the API with startdate and enddate for every prediction</p>", unsafe_allow_html=True)
st.write("---")

# Left sidebar: two collapsible sections
with st.sidebar.expander("Predict", expanded=True):
    option = st.selectbox("Predict by:", [
        "Tomorrow",
        "Next 2 Days",
        "Next 7 Days",
        "This Week",
        "This Month",
        "Next 30 Days",
    ])
    go_btn_quick = st.button("Get Predictions (Quick)")

with st.sidebar.expander("Alternative (Manual Days)"):
    # Manual days input for alternative; user enters a number of days
    manual_days = st.number_input("Manual days (enter N to predict today + N days):", min_value=1, max_value=365, value=7)
    go_btn_alt = st.button("Predict by Manual Days")

with st.sidebar.expander("Predict by Range"):
    start_date = st.date_input("Custom Start Date", value=datetime.now().date())
    end_date = st.date_input("Custom End Date", value=datetime.now().date() + timedelta(days=7))
    go_btn_range = st.button("Get Predictions (Range)")

# Helper: map quick option to date range
def map_quick_to_dates(option_str):
    today = datetime.now().date()
    if option_str == "Tomorrow":
        s = today + timedelta(days=1)
        e = s
    elif option_str == "Next 2 Days":
        s = today + timedelta(days=1)
        e = today + timedelta(days=2)
    elif option_str == "Next 7 Days":
        s = today + timedelta(days=1)
        e = today + timedelta(days=7)
    elif option_str == "This Week":
        s = today
        end_of_week = today + timedelta(days=(6 - today.weekday()))
        e = end_of_week
    elif option_str == "This Month":
        s = today.replace(day=1)
        next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
        e = next_month - timedelta(days=1)
    elif option_str == "Next 30 Days":
        s = today
        e = today + timedelta(days=30)
    else:
        s, e = today, today
    return s, e

# Action handlers
def trigger_quick_prediction(option_str):
    s, e = map_quick_to_dates(option_str)
    start_str = s.strftime("%Y-%m-%d")
    end_str = e.strftime("%Y-%m-%d")
    payload = fetch_api("predictions", params={"startdate": start_str, "enddate": end_str})
    df, err = parse_predictions(payload)
    if err:
        st.error(f"Error: {err}")
    else:
        st.success(f"Predictions for {start_str} to {end_str}")
        plot_predictions(df, title=f"{option_str} — Ticket Volumes")

def trigger_alt_prediction():
    # Manual Days: compute end date from today + N days, start today
    s = datetime.now().date()
    e = s + timedelta(days=int(manual_days))
    start_str = s.strftime("%Y-%m-%d")
    end_str = e.strftime("%Y-%m-%d")
    payload = fetch_api("predictions", params={"startdate": start_str, "enddate": end_str})
    df, err = parse_predictions(payload)
    if err:
        st.error(f"Error: {err}")
    else:
        st.success(f"Predictions for {start_str} to {end_str} (Manual Days)")
        plot_predictions(df, title=f"Manual Days: {start_str} — {end_str}")

def trigger_range_prediction():
    if end_date < start_date:
        st.error("End date must be after start date")
        return
    payload = fetch_api("predictions", params={
        "startdate": start_date.strftime("%Y-%m-%d"),
        "enddate": end_date.strftime("%Y-%m-%d")
    })
    df, err = parse_predictions(payload)
    if err:
        st.error(f"Error: {err}")
    else:
        st.success(f"Predictions for range {start_date} to {end_date}")
        plot_predictions(df, title=f"Range: {format_date(pd.to_datetime(start_date))} — {format_date(pd.to_datetime(end_date))}")

# Button actions
if go_btn_quick:
    trigger_quick_prediction(option)
if go_btn_alt:
    trigger_alt_prediction()
if go_btn_range:
    trigger_range_prediction()

# Optional: show a sample data fetch status or help
st.write("---")
st.caption("Backend expects startdate and enddate in YYYY-MM-DD. End date can be the same as start date for single-day predictions.")
st.caption("Run this UI with: streamlit run streamlit_ticket_dashboard.py --server.port 8501")

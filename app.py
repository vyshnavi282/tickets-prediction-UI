import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ---------------------
# CONFIG
# ---------------------
API_BASE = "http://localhost:5000/api/v1"  # change if your Flask API runs on another host/port

# Set attractive background and style using markdown
st.markdown("""
<style>
    .reportview-container {
        background: linear-gradient(to bottom right, #f0f4f8, #d9e2ec);
    }
    .stHeader h1 {
        color: #0b6efd;
    }
    .stMarkdown p {
        color: #334e68;
        font-size:16px;
    }
</style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="🎟️ Ticket Prediction Dashboard", layout="wide")

# ---------------------
# Helper functions
# ---------------------

def fetch_api(path, params=None):
    url = f"{API_BASE}/{path}"
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def parse_predictions(payload):
    if not payload or (isinstance(payload, dict) and 'error' in payload):
        return None, payload.get('error') if isinstance(payload, dict) else "No data"

    if isinstance(payload, dict) and 'data' in payload and 'predictions' in payload['data']:
        preds = payload['data']['predictions']
    elif isinstance(payload, dict) and 'predictions' in payload:
        preds = payload['predictions']
    else:
        preds = payload

    if isinstance(preds, dict):
        df = pd.DataFrame(list(preds.items()), columns=['date', 'value'])
        df['date'] = pd.to_datetime(df['date'])
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
            except Exception:
                pass
            return df.sort_values('date'), None

        if all(isinstance(x, (int, float)) for x in preds):
            today = datetime.now().date()
            rows = [(today + timedelta(days=i), preds[i]) for i in range(len(preds))]
            df = pd.DataFrame(rows, columns=['date', 'value'])
            df['date'] = pd.to_datetime(df['date'])
            return df, None

    return None, "Unable to parse prediction payload"


def plot_predictions(df, title="Ticket Volume Predictions"):
    if df is None or df.empty:
        st.warning("No prediction data to plot")
        return

    # Colors for bars
    colors = ['#0b6efd'] * len(df)  # default blue
    max_idx = df['value'].idxmax()
    min_idx = df['value'].idxmin()
    colors[max_idx] = '#ff4d4d'  # red for max
    colors[min_idx] = '#2ca02c'  # green for min

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(df['date'], df['value'], color=colors)

    ax.set_title(title, fontsize=16, color="#0b6efd")
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Ticket Volume', fontsize=12)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)

    # Summary metrics
    st.subheader("Summary")
    total_tickets = df['value'].sum()
    max_tickets = df['value'].max()
    min_tickets = df['value'].min()
    max_date = df['date'][max_idx].date()
    min_date = df['date'][min_idx].date()

    summary_df = pd.DataFrame({
        "Metric": ["Total Tickets", "Max Tickets", "Max Tickets Date", "Min Tickets", "Min Tickets Date"],
        "Value": [total_tickets, max_tickets, max_date, min_tickets, min_date]
    })

    st.table(summary_df)

    # Color legend for bars
    st.markdown("**Color Legend:**")
    st.markdown("<span style='color:#ff4d4d;'>■ Max Tickets</span>  <span style='color:#2ca02c;'>■ Min Tickets</span>  <span style='color:#0b6efd;'>■ Others</span>", unsafe_allow_html=True)

# ---------------------
# UI
# ---------------------

st.markdown("<h1 style='color:#0b6efd; text-align:center;'>😎 Ticket Prediction Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#334e68;'>☕ Connects to your Flask predictions API and visualizes ticket volumes.</p>", unsafe_allow_html=True)
st.write("---")

# Two tabs
tab1, tab2 = st.tabs(["Predict by Quick Options ⚡", "Predict by Date Range ⚡"])

with tab1:
    st.header("Quick prediction")
    col1, col2 = st.columns([3, 1])
    with col1:
        option = st.selectbox("Predict by:", [
            "Tomorrow",
            "Next 2 Days",
            "Next 7 Days",
            "This Week",
            "This Month",
            "Next 30 Days",
        ])
    with col2:
        go_btn = st.button("Get Predictions")

    if go_btn:
        with st.spinner("Fetching predictions..."):
            if option == "Tomorrow":
                path = "predictions/next/1"
            elif option == "Next 2 Days":
                path = "predictions/next_2_days"
            elif option == "Next 7 Days":
                path = "predictions/next_week"
            elif option == "This Week":
                path = "predictions/this_week"
            elif option == "This Month":
                path = "predictions/this_month"
            elif option == "Next 30 Days":
                path = "predictions/next_month"
            else:
                path = "predictions/next_week"

            payload = fetch_api(path)
            df, err = parse_predictions(payload)
            if err:
                st.error(f"Error: {err}")
            else:
                st.success("Predictions fetched")
                plot_predictions(df, title=f"{option} — Ticket Volumes")

with tab2:
    st.header("Custom Date Range Prediction")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        start_date = st.date_input("Start Date")
    with c2:
        end_date = st.date_input("End Date")
    with c3:
        go_range = st.button("Get Range Predictions")

    if go_range:
        if end_date < start_date:
            st.error("End date must be after start date")
        else:
            params = {"startdate": start_date.strftime("%Y-%m-%d"), "enddate": end_date.strftime("%Y-%m-%d")}
            with st.spinner("Fetching predictions for range..."):
                payload = fetch_api("predictions", params=params)
                df, err = parse_predictions(payload)
                if err:
                    st.error(f"Error: {err}")
                else:
                    st.success("Predictions fetched for range")
                    plot_predictions(df, title=f"Range: {start_date} — {end_date}")

st.write("---")
st.caption("Make sure your Flask API is running and accessible at the API_BASE URL set in the script.")
st.caption("Run this UI with: `streamlit run streamlit_ticket_dashboard.py --server.port 8501`")
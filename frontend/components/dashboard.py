import streamlit as st
import requests
import pandas as pd

def show_dashboard(BACKEND_URL):
    st.title("📊 Crypto Market Dashboard")

    coin = st.selectbox("Choose a cryptocurrency:", ["bitcoin", "ethereum", "solana"])
    vs_currency = st.selectbox("Currency", ["usd", "inr", "eur"])
    days = st.slider("Select number of days", 1, 30, 7)

    if st.button("Get Data"):
        try:
            res = requests.get(f"{BACKEND_URL}/history/{coin}?vs_currency={vs_currency}&days={days}")
            res.raise_for_status()
            data = res.json()

            if "prices" not in data or not data["prices"]:
                st.warning("No data available for this coin.")
                return

            df = pd.DataFrame(data["prices"])
            df["ts"] = pd.to_datetime(df["ts"])
            st.subheader("Price Over Time")
            st.line_chart(df, x="ts", y="price")

            # --- New Technical Indicators ---
            df["return"] = df["price"].pct_change()
            df["volatility"] = df["return"].rolling(5).std() * 100  # rolling std in %
            df["SMA7"] = df["price"].rolling(7).mean()
            df["SMA14"] = df["price"].rolling(14).mean()

            # Trend detection
            first = df["price"].iloc[0]
            last = df["price"].iloc[-1]

            pct_change = (last - first) / first * 100

            if pct_change > 0:
                trend = "↑ UP"
            elif pct_change < 0:
                trend = "↓ DOWN"
            else:
                trend = " -> SIDEWAYS"


            # --- Main Price Chart with SMA Overlay ---
            st.subheader("Price Chart with Moving Averages")
            st.line_chart(df[["price", "SMA7", "SMA14"]])

            # --- Secondary Chart: Volatility ---
            st.subheader("Volatility (%)")
            st.line_chart(df["volatility"])

            # --- Secondary Chart: Returns ---
            st.subheader("Daily Returns")
            st.line_chart(df["return"])

            analysis = data.get("analysis", {})
            if analysis:
                st.subheader(" Market Summary")
                st.write("---")
                col1, col2 = st.columns(2)
                col3, col4 = st.columns(2)
                col5, _ = st.columns(2)

                col1.metric("First Price", f"{float(analysis['first_price']):,.2f} {vs_currency.upper()}")
                col2.metric("Last Price", f"{float(analysis['last_price']):,.2f} {vs_currency.upper()}")
                col3.metric("Change (%)", f"{float(analysis['pct_change']):.2f}%")
                col4.metric("Volatility (5-period)", f"{float(df['volatility'].iloc[-1]):.2f}%")
                # trend_display = " UP" if trend == "UP" else "📉 DOWN"
                col5.metric("Trend", trend)
            else:
                st.info("No analysis available.")
        except Exception as e:
            st.error(f"Error fetching data: {e}")

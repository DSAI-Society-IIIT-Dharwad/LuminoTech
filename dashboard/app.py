import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models import get_session, engine

st.set_page_config(
    page_title="SKF Bearing Price Monitor",
    page_icon="🔩",
    layout="wide",
)

st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #1f77b4;
    }
    .buy-box-badge {
        background: #28a745;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def load_data():
    with engine.connect() as conn:
        df = pd.read_sql(
            "SELECT * FROM price_snapshots ORDER BY scraped_at DESC",
            conn
        )
    return df


def main():
    st.title("🔩 SKF Bearing Price Monitor")
    st.caption("Amazon.in · Tamil Nadu (PIN 600001) · Real-time competitor tracking")

    df = load_data()

    if df.empty:
        st.warning("No data found. Run the spider first: `py run.py`")
        return

    df["scraped_at"] = pd.to_datetime(df["scraped_at"])
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df[df["price"] > 0]

    # ── Sidebar filters ──────────────────────────────────────
    st.sidebar.title("Filters")

    models = ["All"] + sorted(df["model"].dropna().unique().tolist())
    selected_model = st.sidebar.selectbox("Bearing Model", models)

    sellers = ["All"] + sorted(df["seller_name"].dropna().unique().tolist())
    selected_seller = st.sidebar.selectbox("Seller", sellers)

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # Apply filters
    filtered = df.copy()
    if selected_model != "All":
        filtered = filtered[filtered["model"] == selected_model]
    if selected_seller != "All":
        filtered = filtered[filtered["seller_name"] == selected_seller]

    # ── Metric Cards ─────────────────────────────────────────
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Records", len(filtered))
    with col2:
        st.metric("Unique ASINs", filtered["asin"].nunique())
    with col3:
        st.metric("Active Sellers", filtered["seller_name"].nunique())
    with col4:
        avg = filtered["price"].mean()
        st.metric("Avg Price", f"₹{avg:.0f}" if not pd.isna(avg) else "N/A")

    st.markdown("---")

    # ── Row 1: Price Trend + Seller Comparison ────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📈 Price Trend Over Time")
        trend_df = filtered.groupby(
            [pd.Grouper(key="scraped_at", freq="10min"), "seller_name"]
        )["price"].mean().reset_index()

        if not trend_df.empty:
            fig_trend = px.line(
                trend_df,
                x="scraped_at",
                y="price",
                color="seller_name",
                title="Price trend by seller",
                labels={"scraped_at": "Time", "price": "Price (₹)", "seller_name": "Seller"},
            )
            fig_trend.update_layout(height=350, showlegend=True)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Not enough data for trend chart.")

    with col_right:
        st.subheader("💰 Current Price Comparison")
        latest = filtered.sort_values("scraped_at").groupby(
            "seller_name"
        ).last().reset_index()

        if not latest.empty:
            fig_bar = px.bar(
                latest.sort_values("price"),
                x="seller_name",
                y="price",
                color="price",
                color_continuous_scale="RdYlGn_r",
                title="Latest price per seller",
                labels={"seller_name": "Seller", "price": "Price (₹)"},
            )
            fig_bar.update_layout(height=350, showlegend=False)
            fig_bar.update_xaxes(tickangle=30)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No seller data available.")

    # ── Row 2: Buy Box + Price Distribution ──────────────────
    col_left2, col_right2 = st.columns(2)

    with col_left2:
        st.subheader("🏆 Buy Box Winners")
        buy_box = filtered[filtered["is_buy_box_winner"] == True]
        if not buy_box.empty:
            bb_count = buy_box["seller_name"].value_counts().reset_index()
            bb_count.columns = ["seller_name", "wins"]
            fig_pie = px.pie(
                bb_count,
                names="seller_name",
                values="wins",
                title="Buy Box distribution",
                hole=0.4,
            )
            fig_pie.update_layout(height=350)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No Buy Box data available.")

    with col_right2:
        st.subheader("📊 Price Distribution")
        if not filtered.empty:
            fig_hist = px.histogram(
                filtered,
                x="price",
                nbins=30,
                color="model",
                title="Price distribution by model",
                labels={"price": "Price (₹)", "count": "Count"},
            )
            fig_hist.update_layout(height=350)
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("No data available.")

    # ── Seller Table ──────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 All Sellers — Latest Prices")

    table_df = filtered.sort_values("scraped_at", ascending=False).groupby(
        ["asin", "seller_name"]
    ).first().reset_index()

    display_df = table_df[[
        "asin", "model", "seller_name", "price",
        "mrp", "is_buy_box_winner", "fba_status",
        "availability", "pincode", "scraped_at"
    ]].copy()

    display_df["price"] = display_df["price"].apply(lambda x: f"₹{x:.0f}")
    display_df["is_buy_box_winner"] = display_df["is_buy_box_winner"].apply(
        lambda x: "✅ Yes" if x else "No"
    )
    display_df.columns = [
        "ASIN", "Model", "Seller", "Price", "MRP",
        "Buy Box", "Fulfillment", "Availability", "PIN", "Last Seen"
    ]

    st.dataframe(display_df, use_container_width=True, height=400)

    # ── Price Alerts ──────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔔 Price Alerts")

    alert_df = filtered[filtered["price"] > 0].copy()
    if len(alert_df) > 0:
        model_min = alert_df.groupby("model")["price"].min()
        model_max = alert_df.groupby("model")["price"].max()

        for model in alert_df["model"].unique():
            min_p = model_min[model]
            max_p = model_max[model]
            spread = max_p - min_p
            pct = (spread / min_p * 100) if min_p > 0 else 0

            if pct > 20:
                st.error(
                    f"🚨 SKF {model}: Price spread is ₹{spread:.0f} "
                    f"({pct:.1f}%) — from ₹{min_p:.0f} to ₹{max_p:.0f}"
                )
            elif pct > 10:
                st.warning(
                    f"⚠️ SKF {model}: Price spread is ₹{spread:.0f} "
                    f"({pct:.1f}%) — from ₹{min_p:.0f} to ₹{max_p:.0f}"
                )
            else:
                st.success(
                    f"✅ SKF {model}: Prices stable — "
                    f"₹{min_p:.0f} to ₹{max_p:.0f}"
                )

    st.markdown("---")
    st.caption(
        f"Last refreshed: {df['scraped_at'].max()} · "
        f"Total records in DB: {len(df)}"
    )


if __name__ == "__main__":
    main()
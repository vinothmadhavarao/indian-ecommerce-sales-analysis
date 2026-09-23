import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------------
# Page settings
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Indian E-Commerce Sales Dashboard",
    page_icon="🛒",
    layout="wide",
)

MAIN = "#1B4F72"      # deep blue for main bars/lines
ACCENT = "#E67E22"    # saffron for comparison bars
px.defaults.template = "simple_white"


# ------------------------------------------------------------------
# Load data (cached so it loads only once)
# ------------------------------------------------------------------
@st.cache_data
def load_data():
    sales = pd.read_parquet("data/dashboard/sales_dashboard.parquet")
    rfm = pd.read_parquet("data/dashboard/rfm.parquet")
    return sales, rfm


df, rfm = load_data()


# ------------------------------------------------------------------
# Sidebar filters
# ------------------------------------------------------------------
st.sidebar.header("Filters")
st.sidebar.caption("All values are selected by default. Remove items to narrow the view.")

min_date = df["Order_Date"].min().date()
max_date = df["Order_Date"].max().date()
dates = st.sidebar.date_input(
    "Order date range", (min_date, max_date), min_value=min_date, max_value=max_date
)
if len(dates) != 2:
    st.info("Pick an end date in the sidebar to update the dashboard.")
    st.stop()
start, end = pd.Timestamp(dates[0]), pd.Timestamp(dates[1])


def multiselect(label, column):
    options = sorted(df[column].dropna().unique().tolist())
    return st.sidebar.multiselect(label, options, default=options)


states = multiselect("State", "State")
categories = multiselect("Category", "Category")
payments = multiselect("Payment mode", "Payment_Mode")

mask = (
    df["Order_Date"].between(start, end)
    & df["State"].isin(states)
    & df["Category"].isin(categories)
    & df["Payment_Mode"].isin(payments)
)
f = df[mask]  # all orders after filters

if f.empty:
    st.warning("No orders match these filters. Add at least one state, category and payment mode.")
    st.stop()

d = f[f["Status_Group"] == "Completed"]  # delivered orders after filters


# ------------------------------------------------------------------
# Header and KPI cards
# ------------------------------------------------------------------
st.title("🛒 Indian E-Commerce Sales Dashboard")
st.caption(
    "250,000 orders from June 2024 to June 2026. Simulated Kaggle dataset. "
    "Net Revenue counts delivered orders only."
)

gmv = f["Total_Amount"].sum()
net_revenue = d["Total_Amount"].sum()
median_order = d["Total_Amount"].median() if len(d) else 0
lost_rate = (f["Status_Group"] == "Lost").mean() * 100

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("GMV (all orders)", f"₹{gmv / 1e7:,.1f} Cr")
k2.metric("Net Revenue (delivered)", f"₹{net_revenue / 1e7:,.1f} Cr")
k3.metric("Orders", f"{len(f):,}")
k4.metric("Median order value", f"₹{median_order:,.0f}")
k5.metric("Cancelled or returned", f"{lost_rate:.1f}%")

st.divider()

tab_trend, tab_products, tab_geo, tab_customers, tab_coupons, tab_payments, tab_about = st.tabs(
    ["📈 Trend", "📦 Products", "🗺️ Geography", "👥 Customers", "🎟️ Coupons", "💳 Payments", "ℹ️ About"]
)


# ------------------------------------------------------------------
# Trend
# ------------------------------------------------------------------
with tab_trend:
    monthly = (
        d.groupby("Year_Month")
        .agg(Revenue=("Total_Amount", "sum"), Orders=("Order_ID", "count"))
        .reset_index()
        .sort_values("Year_Month")
    )
    monthly["Net Revenue (₹ Cr)"] = monthly["Revenue"] / 1e7

    fig = px.line(
        monthly, x="Year_Month", y="Net Revenue (₹ Cr)", markers=True,
        title="Monthly Net Revenue", color_discrete_sequence=[MAIN],
    )
    fig.update_yaxes(rangemode="tozero")
    fig.update_xaxes(title="Month")
    st.plotly_chart(fig)
    st.caption(
        "Revenue is flat across the period, with no Diwali uplift. "
        "Lower February totals come from February having 28 days; revenue per day is stable."
    )


# ------------------------------------------------------------------
# Products
# ------------------------------------------------------------------
with tab_products:
    left, right = st.columns(2)

    cat = d.groupby("Category", observed=True).agg(
        Revenue=("Total_Amount", "sum"), Orders=("Order_ID", "count")
    )
    cat["Share of revenue (%)"] = cat["Revenue"] / cat["Revenue"].sum() * 100
    cat["Share of orders (%)"] = cat["Orders"] / cat["Orders"].sum() * 100
    cat = cat.sort_values("Share of revenue (%)")
    cat_long = (
        cat[["Share of revenue (%)", "Share of orders (%)"]]
        .reset_index()
        .melt(id_vars="Category", var_name="Measure", value_name="Share (%)")
    )
    fig = px.bar(
        cat_long, x="Share (%)", y="Category", color="Measure", barmode="group",
        orientation="h", title="Revenue share vs order share by category",
        color_discrete_sequence=[MAIN, ACCENT],
    )
    fig.update_layout(legend_title_text="")
    left.plotly_chart(fig)

    brands = (
        d.groupby("Brand", observed=True)["Total_Amount"].sum()
        .sort_values(ascending=False).head(10) / 1e7
    ).reset_index(name="Net Revenue (₹ Cr)").sort_values("Net Revenue (₹ Cr)")
    fig = px.bar(
        brands, x="Net Revenue (₹ Cr)", y="Brand", orientation="h",
        title="Top 10 brands by Net Revenue", color_discrete_sequence=[MAIN],
    )
    right.plotly_chart(fig)

    st.caption(
        "Electronics earns most of the revenue from a minority of orders. "
        "Across the full data, 379 products (18.9%) generate 80% of revenue."
    )


# ------------------------------------------------------------------
# Geography
# ------------------------------------------------------------------
with tab_geo:
    geo = d.groupby("State", observed=True).agg(
        Revenue=("Total_Amount", "sum"), Cities=("City", "nunique")
    )
    geo["Net Revenue (₹ Cr)"] = geo["Revenue"] / 1e7
    geo["Revenue per city (₹ Cr)"] = geo["Net Revenue (₹ Cr)"] / geo["Cities"]
    geo = geo.reset_index()

    left, right = st.columns(2)
    fig = px.bar(
        geo.sort_values("Net Revenue (₹ Cr)"), x="Net Revenue (₹ Cr)", y="State",
        orientation="h", title="Net Revenue by state", hover_data=["Cities"],
        color_discrete_sequence=[MAIN],
    )
    left.plotly_chart(fig)

    fig = px.bar(
        geo.sort_values("Revenue per city (₹ Cr)"), x="Revenue per city (₹ Cr)", y="State",
        orientation="h", title="Net Revenue per city", hover_data=["Cities"],
        color_discrete_sequence=[ACCENT],
    )
    right.plotly_chart(fig)

    st.caption(
        "States with more cities in the data rank higher by total revenue. "
        "Per city, every state earns a similar amount, so the ranking reflects coverage, not market strength."
    )


# ------------------------------------------------------------------
# Customers
# ------------------------------------------------------------------
with tab_customers:
    left, right = st.columns(2)

    cust = d.groupby("Customer_ID").agg(
        Revenue=("Total_Amount", "sum"), Tier=("Customer_Tier", "first")
    )
    tier = cust.groupby("Tier", observed=True).agg(
        Customers=("Revenue", "count"), Revenue=("Revenue", "sum")
    )
    tier["Share of customers (%)"] = tier["Customers"] / tier["Customers"].sum() * 100
    tier["Share of revenue (%)"] = tier["Revenue"] / tier["Revenue"].sum() * 100
    tier_long = (
        tier[["Share of customers (%)", "Share of revenue (%)"]]
        .reset_index()
        .melt(id_vars="Tier", var_name="Measure", value_name="Share (%)")
    )
    fig = px.bar(
        tier_long, x="Tier", y="Share (%)", color="Measure", barmode="group",
        title="Customer tiers: share of customers vs revenue",
        color_discrete_sequence=[ACCENT, MAIN],
    )
    fig.update_layout(legend_title_text="")
    left.plotly_chart(fig)

    seg = rfm.groupby("Segment").agg(
        Customers=("Monetary", "count"),
        Avg_recency_days=("Recency", "mean"),
        Avg_orders=("Frequency", "mean"),
        Avg_spend=("Monetary", "mean"),
        Revenue=("Monetary", "sum"),
    )
    seg["Share of revenue (%)"] = seg["Revenue"] / seg["Revenue"].sum() * 100
    seg = seg.sort_values("Share of revenue (%)")
    fig = px.bar(
        seg.reset_index(), x="Share of revenue (%)", y="Segment", orientation="h",
        title="RFM segments: share of revenue", hover_data=["Customers"],
        color_discrete_sequence=[MAIN],
    )
    right.plotly_chart(fig)

    st.markdown("**RFM segment details** (all delivered orders; not affected by filters)")
    st.dataframe(
        seg.sort_values("Share of revenue (%)", ascending=False)
        .drop(columns="Revenue")
        .round(1),
    )
    st.caption(
        "At Risk customers spent as much as Loyal customers but have not ordered in about 8 months. "
        "They are the clearest win-back target."
    )


# ------------------------------------------------------------------
# Coupons
# ------------------------------------------------------------------
with tab_coupons:
    used = d[d["Coupon_Code"] != "No Coupon"]
    total_discount = used["Coupon_Discount"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Orders using a coupon", f"{len(used) / len(d) * 100:.1f}%" if len(d) else "0%")
    c2.metric("Total discount given", f"₹{total_discount / 1e7:,.2f} Cr")
    c3.metric("Discount as % of Net Revenue",
              f"{total_discount / net_revenue * 100:.2f}%" if net_revenue else "0%")

    left, right = st.columns(2)

    cost = (
        used.groupby("Coupon_Code", observed=True)["Coupon_Discount"].sum() / 1e5
    ).reset_index(name="Discount (₹ lakh)").sort_values("Discount (₹ lakh)")
    fig = px.bar(
        cost, x="Discount (₹ lakh)", y="Coupon_Code", orientation="h",
        title="Discount cost by coupon", color_discrete_sequence=[ACCENT],
    )
    fig.update_yaxes(title="")
    left.plotly_chart(fig)

    usage = pd.crosstab(f["Year_Month"], f["Coupon_Code"], normalize="index") * 100
    usage = usage[[c for c in ["SAVE10", "DIWALI100", "FLAT50"] if c in usage.columns]]
    fig = px.line(
        usage.reset_index().melt(id_vars="Year_Month", var_name="Coupon", value_name="% of orders"),
        x="Year_Month", y="% of orders", color="Coupon", markers=True,
        title="Coupon usage by month",
    )
    fig.update_yaxes(rangemode="tozero")
    fig.update_xaxes(title="Month")
    right.plotly_chart(fig)

    st.subheader("What if SAVE10 had a maximum discount?")
    save10 = used.loc[used["Coupon_Code"] == "SAVE10", "Coupon_Discount"]
    cap = st.slider("Maximum SAVE10 discount per order (₹)", 250, 10000, 2000, step=250)
    if len(save10):
        savings = (save10 - cap).clip(lower=0).sum()
        affected = (save10 > cap).mean() * 100
        s1, s2, s3 = st.columns(3)
        s1.metric("Estimated saving", f"₹{savings / 1e7:,.2f} Cr")
        s2.metric("Share of SAVE10 cost saved", f"{savings / save10.sum() * 100:.0f}%")
        s3.metric("SAVE10 orders affected", f"{affected:.0f}%")
        st.caption("Upper-bound estimate: some customers may not buy without the full discount.")
    else:
        st.info("No SAVE10 orders match the current filters.")


# ------------------------------------------------------------------
# Payments
# ------------------------------------------------------------------
with tab_payments:
    pay = f.assign(Lost=f["Status_Group"] == "Lost").groupby("Payment_Mode", observed=True).agg(
        Orders=("Order_ID", "count"), Lost_rate=("Lost", "mean")
    )
    pay["Cancelled or returned (%)"] = pay["Lost_rate"] * 100
    pay["Share of orders (%)"] = pay["Orders"] / pay["Orders"].sum() * 100
    pay = pay.reset_index().sort_values("Orders", ascending=False)

    left, right = st.columns(2)
    fig = px.bar(
        pay, x="Payment_Mode", y="Share of orders (%)", title="Share of orders by payment mode",
        color_discrete_sequence=[MAIN],
    )
    fig.update_xaxes(title="")
    left.plotly_chart(fig)

    fig = px.bar(
        pay, x="Payment_Mode", y="Cancelled or returned (%)",
        title="Cancelled or returned by payment mode", color_discrete_sequence=[ACCENT],
    )
    fig.add_hline(y=lost_rate, line_dash="dash", line_color="gray",
                  annotation_text="Average", annotation_position="top left")
    fig.update_yaxes(range=[0, 20])
    fig.update_xaxes(title="")
    right.plotly_chart(fig)

    st.caption(
        "Cash on Delivery is not riskier than prepaid orders in this data "
        "(chi-square test on the full data, p = 0.96)."
    )


# ------------------------------------------------------------------
# About
# ------------------------------------------------------------------
with tab_about:
    st.markdown(
        """
### About this project

This dashboard summarises an end-to-end analysis of 250,000 orders from a multi-table
Indian e-commerce dataset: data validation, cleaning, exploratory analysis, statistical
testing, Pareto analysis and RFM customer segmentation.

**Key recommendations**
- Cap SAVE10: it causes 97% of coupon cost and has no maximum discount.
- Win back At Risk customers: about 7,000 high-value customers who stopped ordering.
- Protect stock of the 379 products that generate 80% of revenue.
- Add a minimum order value to flat coupons and limit DIWALI100 to the festive season.
- Use the ₹500 free-shipping threshold to raise basket sizes in Books, Grocery and Beauty.

**Limitations.** The dataset is simulated. Order statuses, ratings, delivery times and
review texts follow artificial patterns, so the findings demonstrate analytical methods
rather than real market behaviour.

**Full analysis and code:**
[github.com/vinothmadhavarao/indian-ecommerce-sales-analysis](https://github.com/vinothmadhavarao/indian-ecommerce-sales-analysis)

Built by Vinoth with Python, Pandas, Plotly and Streamlit.
"""
    )

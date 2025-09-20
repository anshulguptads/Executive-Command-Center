# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import date, datetime

st.set_page_config(page_title="Lulu Executive Command Center", layout="wide")

# -----------------------------
# Data Loaders (with hardening)
# -----------------------------
@st.cache_data
def load_data():
    # Read CSVs without assuming correct types
    sales = pd.read_csv("lulu_sales_ops.csv")
    persona = pd.read_csv("lulu_persona.csv")

    # Coerce datetimes and sanitize columns
    if "Date" in sales.columns:
        sales["Date"] = pd.to_datetime(sales["Date"], errors="coerce")
    else:
        sales["Date"] = pd.NaT

    if "Last_Visit_Date" in persona.columns:
        persona["Last_Visit_Date"] = pd.to_datetime(persona["Last_Visit_Date"], errors="coerce")

    # Ensure expected numeric columns exist to avoid lookup errors
    for col in [
        "Sales_Revenue","Units_Sold","Basket_Size","Unit_Price","Footfall",
        "Web_Orders","Mobile_Orders","Stock_On_Hand","Staff_Count","Discount",
        "Competitor_Price"
    ]:
        if col not in sales.columns:
            sales[col] = 0

    # Ensure expected categorical columns exist
    for col in ["Region","Store_ID","SKU_Category","SKU","Promo_Flag"]:
        if col not in sales.columns:
            sales[col] = "Unknown"

    for col in ["Loyalty_Segment","App_Engagement","Preferred_Visit_Day","City","Avg_Spend_AED",
                "Visit_Frequency","Typical_Basket_Size","Category_Preference","Name","Customer_ID"]:
        if col not in persona.columns:
            persona[col] = np.nan

    return sales, persona


sales, persona = load_data()

st.title("🛒 Lulu Executive Command Center – Data-Driven Decisions")

# Guard against empty/invalid date column
if sales.empty or sales["Date"].dropna().empty:
    st.error("Sales dataset is empty or has invalid 'Date' values. Please verify lulu_sales_ops.csv.")
    st.stop()

# ---------------------------------
# Sidebar: Global Filters (hardened)
# ---------------------------------
with st.sidebar:
    st.header("🔎 Global Filters")

    # Safe min/max dates
    min_ts = sales["Date"].min()
    max_ts = sales["Date"].max()

    # Fallbacks if NaT
    if pd.isna(min_ts) or pd.isna(max_ts):
        min_d, max_d = date(2022, 1, 1), date.today()
    else:
        # Convert safely to Python date
        min_d = pd.to_datetime(min_ts).to_pydatetime().date()
        max_d = pd.to_datetime(max_ts).to_pydatetime().date()

    # Streamlit date_input expects date/datetime, not pandas Timestamp
    date_range = st.date_input(
        "Date Range",
        (min_d, max_d),
        min_value=min_d,
        max_value=max_d,
        key="date_range_picker"
    )

    # If user selects a single date, convert to a range of the same day
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_d, end_d = date_range
    else:
        start_d = end_d = date_range

    region_opts = sorted(sales["Region"].dropna().unique().tolist())
    store_opts = sorted(sales["Store_ID"].dropna().unique().tolist())
    cat_opts   = sorted(sales["SKU_Category"].dropna().unique().tolist())
    loy_opts   = sorted(persona["Loyalty_Segment"].dropna().unique().tolist())

    region = st.multiselect("Region", region_opts, default=region_opts or [])
    stores = st.multiselect("Store", store_opts, default=store_opts or [])
    categories = st.multiselect("Category", cat_opts, default=cat_opts or [])
    loyalty_filter = st.multiselect("Loyalty (Persona)", loy_opts, default=loy_opts or [])

# -----------------------------
# Apply Filters (null-safe)
# -----------------------------
mask = (
    (sales["Date"] >= pd.to_datetime(start_d)) &
    (sales["Date"] <= pd.to_datetime(end_d))
)
if region:
    mask &= sales["Region"].isin(region)
if stores:
    mask &= sales["Store_ID"].isin(stores)
if categories:
    mask &= sales["SKU_Category"].isin(categories)

sales_f = sales.loc[mask].copy()
persona_f = persona.copy()
if loyalty_filter:
    persona_f = persona_f[persona_f["Loyalty_Segment"].isin(loyalty_filter)]

# -----------------------------
# KPI Deck (with guardrails)
# -----------------------------
st.subheader("📈 Executive KPIs")

def safe_sum(s):   return float(s.sum()) if not s.empty else 0.0
def safe_mean(s):  return float(s.mean()) if not s.empty else 0.0
def safe_int(n):   return int(n) if not pd.isna(n) else 0

total_revenue = safe_sum(sales_f["Sales_Revenue"])
total_units   = safe_sum(sales_f["Units_Sold"])
avg_basket    = safe_mean(sales_f["Basket_Size"])
avg_price     = safe_mean(sales_f["Unit_Price"])
avg_footfall  = safe_mean(sales_f["Footfall"])
conv_proxy    = 0.0
denom = sales_f["Footfall"].sum()
if denom and denom > 0:
    conv_proxy = ((sales_f["Web_Orders"].sum() + sales_f["Mobile_Orders"].sum()) / denom) * 100.0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Revenue (AED)", f"{total_revenue:,.0f}")
c2.metric("Total Units Sold", f"{safe_int(total_units):,}")
c3.metric("Avg Basket Size", f"{avg_basket:,.2f}")
c4.metric("Avg Unit Price (AED)", f"{avg_price:,.2f}")
c5.metric("Avg Footfall / Day", f"{avg_footfall:,.0f}")
c6.metric("Digital Conversion Proxy (%)", f"{conv_proxy:,.2f}")

# ----------------------------------------
# Tabs: Overview | Sales Ops | Personas | Alerts
# ----------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Sales Ops", "Personas", "Alerts & Actions"])

# ------------- Overview -------------
with tab1:
    st.markdown("### Revenue Trend & Category Mix")
    col_l, col_r = st.columns([2, 1])

    with col_l:
        if sales_f.empty:
            st.info("No data for the selected filters.")
        else:
            rev_trend = sales_f.groupby("Date", as_index=False)["Sales_Revenue"].sum()
            st.plotly_chart(
                px.line(rev_trend, x="Date", y="Sales_Revenue", title="Revenue Over Time"),
                use_container_width=True
            )

    with col_r:
        if sales_f.empty:
            st.empty()
        else:
            cat_mix = (
                sales_f.groupby("SKU_Category", as_index=False)["Sales_Revenue"]
                .sum()
                .sort_values("Sales_Revenue", ascending=False)
            )
            st.plotly_chart(
                px.bar(cat_mix, x="SKU_Category", y="Sales_Revenue", title="Category Revenue Mix"),
                use_container_width=True
            )

    st.markdown("### Region → Store Performance")
    if sales_f.empty:
        st.info("No data for the selected filters.")
    else:
        perf = (
            sales_f.groupby(["Region","Store_ID"], as_index=False)
            .agg(Revenue=("Sales_Revenue","sum"),
                 Units=("Units_Sold","sum"),
                 Footfall=("Footfall","sum"))
            .sort_values("Revenue", ascending=False)
        )
        st.dataframe(perf, use_container_width=True)

# ------------- Sales Ops -------------
with tab2:
    st.markdown("### Pricing vs Demand & Promotions Impact")
    cA, cB = st.columns(2)

    with cA:
        if sales_f.empty:
            st.info("No data to visualize.")
        else:
            # Sample to keep plotting responsive
            sample_df = sales_f.sample(min(2000, len(sales_f))) if len(sales_f) > 0 else sales_f
            # Try with trendline; if statsmodels is missing, fallback without trendline
            try:
                fig = px.scatter(
                    sample_df,
                    x="Unit_Price", y="Units_Sold",
                    color="SKU_Category",
                    trendline="ols",
                    title="Price vs Units Sold (Sample)"
                )
            except Exception:
                fig = px.scatter(
                    sample_df,
                    x="Unit_Price", y="Units_Sold",
                    color="SKU_Category",
                    title="Price vs Units Sold (Sample)"
                )
            st.plotly_chart(fig, use_container_width=True)

    with cB:
        if sales_f.empty:
            st.empty()
        else:
            promo = sales_f.groupby("Promo_Flag", as_index=False)["Sales_Revenue"].mean()
            promo["Promo_Flag"] = promo["Promo_Flag"].map({0:"No Promo", 1:"Promo"}).fillna("Unknown")
            st.plotly_chart(
                px.bar(promo, x="Promo_Flag", y="Sales_Revenue", title="Average Revenue: Promo vs No Promo"),
                use_container_width=True
            )

    st.markdown("### Operational Drivers by Category")
    if sales_f.empty:
        st.info("No data for the selected filters.")
    else:
        drivers = sales_f.groupby("SKU_Category", as_index=False).agg(
            Avg_Footfall=("Footfall","mean"),
            Avg_Staff=("Staff_Count","mean"),
            Avg_Discount=("Discount","mean"),
            Avg_CompetitorPrice=("Competitor_Price","mean")
        ).round(2)
        st.dataframe(drivers, use_container_width=True)

# ------------- Personas -------------
with tab3:
    st.markdown("### Persona Overview")
    if persona_f.empty:
        st.info("No persona data for the current filters.")
    else:
        st.dataframe(persona_f.head(100), use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(
                px.histogram(persona_f, x="App_Engagement", color="Loyalty_Segment",
                             barmode="group", title="Engagement by Loyalty"),
                use_container_width=True
            )
        with c2:
            st.plotly_chart(
                px.histogram(persona_f, x="Preferred_Visit_Day", color="City",
                             barmode="group", title="Preferred Visit Days"),
                use_container_width=True
            )

        st.markdown("### High-Value Personas (Gold/Platinum)")
        hv = persona_f[persona_f["Loyalty_Segment"].isin(["Gold","Platinum"])].copy()
        if hv.empty:
            st.info("No Gold/Platinum personas in current filters.")
        else:
            # Simple value index for quick prioritization
            hv["Value_Index"] = (
                pd.to_numeric(hv["Avg_Spend_AED"], errors="coerce").fillna(0.0) *
                (pd.to_numeric(hv["Visit_Frequency"], errors="coerce").fillna(0.0) +
                 0.5 * pd.to_numeric(hv["Typical_Basket_Size"], errors="coerce").fillna(0.0))
            )
            cols_show = ["Customer_ID","Name","City","Avg_Spend_AED",
                         "Visit_Frequency","Typical_Basket_Size",
                         "Category_Preference","App_Engagement","Value_Index"]
            st.dataframe(hv.sort_values("Value_Index", ascending=False)[cols_show].head(20), use_container_width=True)

# ------------- Alerts & Actions -------------
with tab4:
    st.markdown("### Algorithmic Alerts & Actionables")
    if sales_f.empty:
        st.info("No data to generate alerts.")
    else:
        # Restock: inventory below 60% of current demand
        try:
            restock = sales_f[sales_f["Stock_On_Hand"] < sales_f["Units_Sold"] * 0.6]
        except Exception:
            restock = pd.DataFrame()

        if restock.empty:
            st.success("No restock alerts. Inventory appears adequate for demand.")
        else:
            st.warning(f"Restock Alerts: {len(restock)} rows flagged")
            st.dataframe(
                restock[["Date","Store_ID","SKU","SKU_Category","Units_Sold","Stock_On_Hand","Sales_Revenue"]]
                .head(50),
                use_container_width=True
            )

        # Promo: underperformers without promos
        try:
            q25 = sales_f["Sales_Revenue"].quantile(0.25)
            under_rev = sales_f["Sales_Revenue"] < q25
            promo_suggest = sales_f[(sales_f["Promo_Flag"] == 0) & under_rev]
        except Exception:
            promo_suggest = pd.DataFrame()

        if promo_suggest.empty:
            st.success("No immediate promo suggestions.")
        else:
            st.info(f"Promo Suggestions: {len(promo_suggest)} underperforming rows without promos")
            st.dataframe(
                promo_suggest[["Date","Store_ID","SKU","SKU_Category","Sales_Revenue","Unit_Price","Discount"]]
                .head(50),
                use_container_width=True
            )

        # Staffing: high footfall per staff threshold
        try:
            staffing = sales_f[sales_f["Footfall"] / sales_f["Staff_Count"] > 50]
        except Exception:
            staffing = pd.DataFrame()

        if staffing.empty:
            st.success("Staffing levels appear adequate for current footfall.")
        else:
            st.error(f"Staffing Alerts: {len(staffing)} rows where footfall per staff is high")
            st.dataframe(
                staffing[["Date","Store_ID","Region","Footfall","Staff_Count","SKU_Category"]]
                .head(50),
                use_container_width=True
            )

# -----------------------------
# Downloads
# -----------------------------
st.markdown("---")
st.subheader("⬇️ Downloads")
st.download_button("Download Filtered Sales CSV", sales_f.to_csv(index=False), file_name="filtered_sales.csv")
st.download_button("Download Filtered Persona CSV", persona_f.to_csv(index=False), file_name="filtered_persona.csv")

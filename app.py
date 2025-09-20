
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import date

st.set_page_config(page_title="Lulu Executive Command Center", layout="wide")

@st.cache_data
def load_data():
    sales = pd.read_csv("lulu_sales_ops.csv", parse_dates=["Date"])
    persona = pd.read_csv("lulu_persona.csv", parse_dates=["Last_Visit_Date"])
    return sales, persona

sales, persona = load_data()

st.title("🛒 Lulu Executive Command Center – Data-Driven Decisions")

if sales.empty:
    st.error("Sales dataset is empty. Please upload a valid lulu_sales_ops.csv.")
    st.stop()

with st.sidebar:
    st.header("🔎 Global Filters")
    min_d = sales["Date"].min().date()
    max_d = sales["Date"].max().date()
    date_range = st.date_input(
        "Date Range",
        (min_d, max_d),
        min_value=min_d,
        max_value=max_d,
        key="date_range_picker"
    )
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_d, end_d = date_range
    else:
        start_d = end_d = date_range

    region = st.multiselect("Region", sorted(sales["Region"].unique()), default=list(sales["Region"].unique()))
    stores = st.multiselect("Store", sorted(sales["Store_ID"].unique()), default=list(sales["Store_ID"].unique()))
    categories = st.multiselect("Category", sorted(sales["SKU_Category"].unique()), default=list(sales["SKU_Category"].unique()))
    loyalty_filter = st.multiselect("Loyalty (Persona)", sorted(persona["Loyalty_Segment"].unique()), default=list(persona["Loyalty_Segment"].unique()))

sales_f = sales[
    (sales["Date"] >= pd.to_datetime(start_d)) &
    (sales["Date"] <= pd.to_datetime(end_d)) &
    (sales["Region"].isin(region)) &
    (sales["Store_ID"].isin(stores)) &
    (sales["SKU_Category"].isin(categories))
].copy()

persona_f = persona[persona["Loyalty_Segment"].isin(loyalty_filter)].copy()

st.subheader("📈 Executive KPIs")

total_revenue = float(sales_f["Sales_Revenue"].sum()) if not sales_f.empty else 0.0
avg_basket = float(sales_f["Basket_Size"].mean()) if not sales_f.empty else 0.0
avg_price = float(sales_f["Unit_Price"].mean()) if not sales_f.empty else 0.0
total_units = int(sales_f["Units_Sold"].sum()) if not sales_f.empty else 0
avg_footfall = float(sales_f["Footfall"].mean()) if not sales_f.empty else 0.0
conv_proxy = ((sales_f["Web_Orders"] + sales_f["Mobile_Orders"]).sum() / (sales_f["Footfall"].sum() + 1)) * 100 if not sales_f.empty else 0.0

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Total Revenue (AED)", f"{total_revenue:,.0f}")
col2.metric("Total Units Sold", f"{total_units:,.0f}")
col3.metric("Avg Basket Size", f"{avg_basket:,.2f}")
col4.metric("Avg Unit Price (AED)", f"{avg_price:,.2f}")
col5.metric("Avg Footfall / Day", f"{avg_footfall:,.0f}")
col6.metric("Digital Conversion Proxy (%)", f"{conv_proxy:,.2f}")

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Sales Ops", "Personas", "Alerts & Actions"])

with tab1:
    st.markdown("### Revenue Trend & Category Mix")
    t1c1, t1c2 = st.columns([2,1])
    with t1c1:
        if sales_f.empty:
            st.info("No data for the selected filters.")
        else:
            rev_trend = sales_f.groupby("Date")["Sales_Revenue"].sum().reset_index()
            st.plotly_chart(px.line(rev_trend, x="Date", y="Sales_Revenue", title="Revenue Over Time"), use_container_width=True)
    with t1c2:
        if sales_f.empty:
            st.empty()
        else:
            cat_mix = sales_f.groupby("SKU_Category")["Sales_Revenue"].sum().reset_index().sort_values("Sales_Revenue", ascending=False)
            st.plotly_chart(px.bar(cat_mix, x="SKU_Category", y="Sales_Revenue", title="Category Revenue Mix"), use_container_width=True)

    st.markdown("### Region-Store Performance")
    if sales_f.empty:
        st.info("No data for the selected filters.")
    else:
        perf = sales_f.groupby(["Region","Store_ID"], as_index=False).agg(
            Revenue=("Sales_Revenue","sum"),
            Units=("Units_Sold","sum"),
            Footfall=("Footfall","sum")
        ).sort_values("Revenue", ascending=False)
        st.dataframe(perf, use_container_width=True)

with tab2:
    st.markdown("### Pricing vs Demand & Promotions Impact")
    t2c1, t2c2 = st.columns(2)
    with t2c1:
        if sales_f.empty:
            st.info("No data to visualize.")
        else:
            st.plotly_chart(px.scatter(
                sales_f.sample(min(1000, len(sales_f))), x="Unit_Price", y="Units_Sold",
                color="SKU_Category", trendline="ols", title="Price vs Units Sold (Sample)"
            ), use_container_width=True)
    with t2c2:
        if sales_f.empty:
            st.empty()
        else:
            promo = sales_f.groupby("Promo_Flag")["Sales_Revenue"].mean().reset_index()
            promo["Promo_Flag"] = promo["Promo_Flag"].map({0:"No Promo",1:"Promo"})
            st.plotly_chart(px.bar(promo, x="Promo_Flag", y="Sales_Revenue", title="Average Revenue: Promo vs No Promo"), use_container_width=True)

    st.markdown("### Operational Drivers")
    if sales_f.empty:
        st.info("No data for the selected filters.")
    else:
        drivers = sales_f.groupby("SKU_Category", as_index=False).agg(
            Avg_Footfall=("Footfall","mean"),
            Avg_Staff=("Staff_Count","mean"),
            Avg_Discount=("Discount","mean"),
            Avg_CompetitorPrice=("Competitor_Price","mean")
        )
        st.dataframe(drivers.round(2), use_container_width=True)

with tab3:
    st.markdown("### Persona Overview")
    if persona_f.empty:
        st.info("No persona data for the selected filters.")
    else:
        st.dataframe(persona_f.head(100), use_container_width=True)
        t3c1, t3c2 = st.columns(2)
        with t3c1:
            st.plotly_chart(px.histogram(persona_f, x="App_Engagement", color="Loyalty_Segment", barmode="group", title="Engagement by Loyalty"), use_container_width=True)
        with t3c2:
            st.plotly_chart(px.histogram(persona_f, x="Preferred_Visit_Day", color="City", barmode="group", title="Preferred Visit Days"), use_container_width=True)

        st.markdown("### High-Value Personas (Gold/Platinum)")
        hv = persona_f[persona_f["Loyalty_Segment"].isin(["Gold","Platinum"])].copy()
        if hv.empty:
            st.info("No Gold/Platinum personas in current filters.")
        else:
            hv["Value_Index"] = hv["Avg_Spend_AED"] * (hv["Visit_Frequency"] + 0.5*hv["Typical_Basket_Size"])
            hv_top = hv.sort_values("Value_Index", ascending=False).head(20)[["Customer_ID","Name","City","Avg_Spend_AED","Visit_Frequency","Typical_Basket_Size","Category_Preference","App_Engagement","Value_Index"]]
            st.dataframe(hv_top, use_container_width=True)

with tab4:
    st.markdown("### Algorithmic Alerts & Actionables")
    if sales_f.empty:
        st.info("No data to generate alerts.")
    else:
        restock = sales_f[sales_f["Stock_On_Hand"] < sales_f["Units_Sold"] * 0.6]
        if restock.empty:
            st.success("No restock alerts. Inventory levels appear healthy against demand.")
        else:
            st.warning(f"Restock Alerts: {len(restock)} rows flagged")
            st.dataframe(restock[["Date","Store_ID","SKU","SKU_Category","Units_Sold","Stock_On_Hand","Sales_Revenue"]].head(50), use_container_width=True)

        under_rev = sales_f["Sales_Revenue"] < sales_f["Sales_Revenue"].quantile(0.25)
        promo_suggest = sales_f[(sales_f["Promo_Flag"]==0) & under_rev]
        if len(promo_suggest) > 0:
            st.info(f"Promo Suggestions: {len(promo_suggest)} underperforming rows without promos")
            st.dataframe(promo_suggest[["Date","Store_ID","SKU","SKU_Category","Sales_Revenue","Unit_Price","Discount"]].head(50), use_container_width=True)
        else:
            st.success("No immediate promo suggestions.")

        staffing = sales_f[sales_f["Footfall"]/sales_f["Staff_Count"] > 50]
        if len(staffing) > 0:
            st.error(f"Staffing Alerts: {len(staffing)} rows where footfall per staff is high")
            st.dataframe(staffing[["Date","Store_ID","Region","Footfall","Staff_Count","SKU_Category"]].head(50), use_container_width=True)
        else:
            st.success("Staffing levels appear adequate for current footfall.")

st.markdown("---")
st.subheader("⬇️ Downloads")
st.download_button("Download Filtered Sales CSV", sales_f.to_csv(index=False), file_name="filtered_sales.csv")
st.download_button("Download Filtered Persona CSV", persona_f.to_csv(index=False), file_name="filtered_persona.csv")

from pathlib import Path
import sys, io
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from analytics import load_data, clean_data, analysis_rows, product_summary, division_summary, pareto_summary, kpis

st.set_page_config(page_title="Nassau Candy | Profitability Intelligence", page_icon="🍬", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.3rem; padding-bottom: 2rem;}
.hero {padding: 1.3rem 1.5rem; border-radius: 16px; background: linear-gradient(120deg,#172554,#1d4ed8); color: white; margin-bottom: 1rem;}
.hero h1 {color:white; margin:0 0 .3rem 0;}
.hero p {color:#e0e7ff; margin:0;}
div[data-testid="stMetric"] {border:1px solid rgba(128,128,128,.25); padding:12px 14px; border-radius:12px;}
.small-note {font-size:.88rem; color: #64748b;}
</style>
<div class="hero"><h1>🍬 Nassau Candy Distributor</h1><p>Product Line Profitability & Margin Performance Intelligence</p></div>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def read_default(path, mtime):
    return load_data(path)

default_path = ROOT / "data" / "Nassau Candy Distributor.csv"
uploaded = st.sidebar.file_uploader("Upload a replacement CSV (optional)", type=["csv"])
try:
    if uploaded is not None:
        raw = pd.read_csv(uploaded)
        df = clean_data(raw)
        source_name = uploaded.name
    else:
        df = read_default(str(default_path), default_path.stat().st_mtime)
        source_name = "Bundled Nassau Candy Distributor.csv"
except Exception as e:
    st.error(f"Could not load dataset: {e}")
    st.stop()

base_valid = analysis_rows(df)
if base_valid.empty:
    st.error("No valid rows remain for profitability analysis. Check that Sales, Units, Cost, Gross Profit, and Order Date contain usable values.")
    st.stop()

st.sidebar.header("Filters")
date_min = base_valid["Order Date"].min().date()
date_max = base_valid["Order Date"].max().date()
date_range = st.sidebar.date_input("Order date range", value=(date_min, date_max), min_value=date_min, max_value=date_max)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = date_min, date_max
divisions = sorted(base_valid["Division"].dropna().astype(str).unique().tolist())
chosen_divisions = st.sidebar.multiselect("Division", divisions, default=divisions)
threshold = st.sidebar.slider("Margin threshold (%)", min_value=-100, max_value=100, value=35, step=5)
product_search = st.sidebar.text_input("Search product", placeholder="e.g. Wonka Bar")
risk_only = st.sidebar.checkbox("Show only margin-risk products", value=False)

filtered = base_valid[
    base_valid["Order Date"].dt.date.between(start_date, end_date) &
    base_valid["Division"].astype(str).isin(chosen_divisions)
].copy()
if product_search.strip():
    filtered = filtered[filtered["Product Name"].astype(str).str.contains(product_search.strip(), case=False, na=False)]
if filtered.empty:
    st.warning("No rows match the current filters. Widen the date range, clear the product search, or select more divisions.")
    st.stop()

ps = product_summary(filtered)
ds = division_summary(filtered)
k = kpis(filtered)
if risk_only:
    ps = ps[ps["Gross Margin (%)"] < threshold]

st.caption(f"Data source: {source_name} · {len(filtered):,} valid transaction rows in current filter · Order dates {start_date} to {end_date}")
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Revenue", f"${k['Revenue']:,.2f}")
c2.metric("Gross profit", f"${k['Gross Profit']:,.2f}")
c3.metric("Weighted gross margin", f"{k['Gross Margin (%)']:.2f}%")
c4.metric("Profit / unit", f"${k['Profit per Unit']:,.2f}")
c5.metric("Products", f"{k['Products']:,}")

tabs = st.tabs(["Overview", "Product Profitability", "Division Performance", "Cost & Margin Diagnostics", "Profit Concentration", "Geography & Factories", "Data Quality & Export"])

with tabs[0]:
    st.subheader("Profitability overview")
    a,b = st.columns([1.35,1])
    with a:
        monthly = filtered.assign(Month=filtered["Order Date"].dt.to_period("M").dt.to_timestamp()).groupby("Month", as_index=False).agg(Sales=("Sales","sum"), Profit=("Gross Profit","sum"), Cost=("Cost","sum"))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=monthly["Month"], y=monthly["Sales"], name="Revenue", mode="lines+markers"))
        fig.add_trace(go.Scatter(x=monthly["Month"], y=monthly["Profit"], name="Gross profit", mode="lines+markers"))
        fig.update_layout(title="Monthly revenue and gross profit", xaxis_title="", yaxis_title="USD", legend_title="")
        st.plotly_chart(fig, use_container_width=True)
    with b:
        fig = px.bar(ds, x="Division", y=["Sales","Gross_Profit"], barmode="group", title="Revenue vs gross profit by division")
        fig.update_layout(yaxis_title="USD", legend_title="")
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("#### Highest gross-profit products")
    show = ps.sort_values("Gross_Profit", ascending=False).head(10)
    st.dataframe(show[["Division","Product Name","Sales","Gross_Profit","Gross Margin (%)","Profit per Unit","Profit Contribution (%)","Margin Risk"]].rename(columns={"Gross_Profit":"Gross Profit"}).style.format({"Sales":"${:,.2f}","Gross Profit":"${:,.2f}","Gross Margin (%)":"{:.2f}%","Profit per Unit":"${:,.2f}","Profit Contribution (%)":"{:.2f}%"}), use_container_width=True, hide_index=True)

with tabs[1]:
    st.subheader("Product-level profitability leaderboard")
    metric = st.selectbox("Rank products by", ["Gross profit","Gross margin","Revenue","Profit per unit","Profit contribution"])
    colmap = {"Gross profit":"Gross_Profit","Gross margin":"Gross Margin (%)","Revenue":"Sales","Profit per unit":"Profit per Unit","Profit contribution":"Profit Contribution (%)"}
    pshow = ps.sort_values(colmap[metric], ascending=False)
    pshow = pshow[pshow["Gross Margin (%)"] >= threshold] if not risk_only else pshow
    st.dataframe(pshow[["Division","Product Name","Sales","Cost","Gross_Profit","Gross Margin (%)","Units","Profit per Unit","Revenue Contribution (%)","Profit Contribution (%)","Margin Volatility (pp)","Margin Risk"]].rename(columns={"Gross_Profit":"Gross Profit"}).style.format({"Sales":"${:,.2f}","Cost":"${:,.2f}","Gross Profit":"${:,.2f}","Gross Margin (%)":"{:.2f}%","Profit per Unit":"${:,.2f}","Revenue Contribution (%)":"{:.2f}%","Profit Contribution (%)":"{:.2f}%","Margin Volatility (pp)":"{:.2f}"}), use_container_width=True, hide_index=True)
    fig = px.bar(pshow.head(20).sort_values("Gross_Profit"), x="Gross_Profit", y="Product Name", color="Division", orientation="h", title="Top products by gross profit")
    fig.update_layout(xaxis_title="Gross profit (USD)", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)
    st.download_button("Download product leaderboard CSV", pshow.to_csv(index=False).encode("utf-8"), "product_profitability.csv", "text/csv")

with tabs[2]:
    st.subheader("Division performance")
    fig = px.bar(ds, x="Division", y="Gross Margin (%)", color="Division", title="Weighted gross margin by division", text_auto=".1f")
    fig.update_layout(yaxis_title="Gross margin (%)", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    fig = px.scatter(ds, x="Sales", y="Gross_Profit", size="Products", color="Division", hover_name="Division", title="Revenue vs profit (bubble size = product count)")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(ds.rename(columns={"Gross_Profit":"Gross Profit"}).style.format({"Sales":"${:,.2f}","Cost":"${:,.2f}","Gross Profit":"${:,.2f}","Gross Margin (%)":"{:.2f}%","Profit per Unit":"${:,.2f}","Revenue Contribution (%)":"{:.2f}%","Profit Contribution (%)":"{:.2f}%"}), use_container_width=True, hide_index=True)
    st.info("Division margins are weighted margins: total gross profit divided by total sales for each division. This is more meaningful than averaging transaction-level margin percentages.")

with tabs[3]:
    st.subheader("Cost versus margin diagnostics")
    scatter = px.scatter(filtered, x="Sales", y="Cost", color="Division", size="Units", hover_data=["Product Name","Gross Profit","Gross Margin (%)","Order ID"], title="Transaction cost vs sales")
    st.plotly_chart(scatter, use_container_width=True)
    pdiag = product_summary(filtered)
    low_margin = pdiag[pdiag["Gross Margin (%)"] < threshold].sort_values("Sales", ascending=False)
    st.markdown(f"#### Products below {threshold}% gross margin")
    if low_margin.empty:
        st.success("No products fall below the selected threshold in this filtered dataset.")
    else:
        st.dataframe(low_margin[["Division","Product Name","Sales","Cost","Gross_Profit","Gross Margin (%)","Profit per Unit","Margin Risk"]].rename(columns={"Gross_Profit":"Gross Profit"}).style.format({"Sales":"${:,.2f}","Cost":"${:,.2f}","Gross Profit":"${:,.2f}","Gross Margin (%)":"{:.2f}%","Profit per Unit":"${:,.2f}"}), use_container_width=True, hide_index=True)
    st.caption("Risk flags are screening indicators, not automatic discontinuation decisions. Validate price, costs, strategic value, and customer commitments before action.")

with tabs[4]:
    st.subheader("Profit concentration / Pareto")
    basis = st.radio("Concentration basis", ["Revenue","Gross profit"], horizontal=True)
    value_col = "Sales" if basis == "Revenue" else "Gross_Profit"
    pareto = pareto_summary(product_summary(filtered), value_col)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=pareto["Product Name"], y=pareto[value_col], name=basis))
    fig.add_trace(go.Scatter(x=pareto["Product Name"], y=pareto["Cumulative Contribution (%)"], name="Cumulative contribution (%)", yaxis="y2", mode="lines+markers"))
    fig.update_layout(title=f"{basis} Pareto by product", xaxis_title="Products (sorted high to low)", yaxis=dict(title=basis+" (USD)"), yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0,105]), showlegend=True)
    st.plotly_chart(fig, use_container_width=True)
    count80 = int((pareto["Cumulative Contribution (%)"] < 80).sum() + 1) if not pareto.empty else 0
    share80 = count80 / len(pareto) * 100 if len(pareto) else 0
    st.metric("Products needed to reach at least 80% of "+basis.lower(), f"{count80} ({share80:.1f}% of products)")
    st.dataframe(pareto[["Product Name",value_col,"Cumulative Contribution (%)","Cumulative Products (%)"]].style.format({value_col:"${:,.2f}","Cumulative Contribution (%)":"{:.2f}%","Cumulative Products (%)":"{:.2f}%"}), use_container_width=True, hide_index=True)
    st.caption("Pareto is calculated from the current filtered product summary. Negative profits, if present, can complicate cumulative concentration interpretation.")

with tabs[5]:
    st.subheader("Geography and factory reference")
    geo = filtered.groupby(["State/Province","Region"], dropna=False, as_index=False).agg(Sales=("Sales","sum"), Gross_Profit=("Gross Profit","sum"), Orders=("Order ID","nunique"))
    geo = geo.sort_values("Sales", ascending=False)
    fig = px.bar(geo.head(15), x="State/Province", y="Sales", color="Region", title="Top 15 states/provinces by revenue")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("#### Factory coordinates")
    fac_path = ROOT / "data" / "factories.csv"
    mapping_path = ROOT / "data" / "product_factory_mapping.csv"
    if fac_path.exists():
        factories = pd.read_csv(fac_path)
        st.dataframe(factories, use_container_width=True, hide_index=True)
    if mapping_path.exists():
        fmap = pd.read_csv(mapping_path)
        st.dataframe(fmap, use_container_width=True, hide_index=True)
        joined = ps.merge(fmap, on=["Division","Product Name"], how="left")
        st.markdown("#### Product profitability by mapped factory")
        by_factory = joined.groupby("Factory", dropna=False, as_index=False).agg(Sales=("Sales","sum"), Gross_Profit=("Gross_Profit","sum"), Cost=("Cost","sum"), Products=("Product ID","nunique"))
        by_factory["Gross Margin (%)"] = by_factory["Gross_Profit"] / by_factory["Sales"] * 100
        st.dataframe(by_factory.rename(columns={"Gross_Profit":"Gross Profit"}).style.format({"Sales":"${:,.2f}","Gross Profit":"${:,.2f}","Cost":"${:,.2f}","Gross Margin (%)":"{:.2f}%"}), use_container_width=True, hide_index=True)
        st.caption("Factory-level figures include only products with an explicit mapping. Unmapped products are not assigned to a factory. This mapping is a reference relationship, not proof that cost is factory-specific.")
    st.markdown("#### State-level revenue and profit")
    st.dataframe(geo.rename(columns={"Gross_Profit":"Gross Profit"}).style.format({"Sales":"${:,.2f}","Gross Profit":"${:,.2f}"}), use_container_width=True, hide_index=True)

with tabs[6]:
    st.subheader("Data quality, assumptions and export")
    quality = df.copy()
    q1,q2,q3,q4 = st.columns(4)
    q1.metric("Source rows", f"{len(df):,}")
    q2.metric("Rows with quality flags", f"{int(df['Has Quality Issue'].sum()):,}")
    q3.metric("Rows in analysis", f"{len(base_valid):,}")
    q4.metric("Excluded from analysis", f"{len(df)-len(base_valid):,}")
    flagged = quality[quality["Has Quality Issue"]]
    if flagged.empty:
        st.success("No rows have been flagged by the configured validation rules.")
    else:
        st.warning("Some rows have data-quality flags. They are retained in the quality view; only rows passing core analysis criteria contribute to main profitability calculations.")
        st.dataframe(flagged[["Row ID","Order ID","Order Date","Ship Date","Division","Product Name","Sales","Units","Gross Profit","Cost","Quality Issue"]], use_container_width=True, hide_index=True)
    st.markdown("#### Validation rules")
    st.markdown("- Sales must be positive; units must be positive; cost cannot be negative.\n- Dates must parse; ship date earlier than order date is flagged.\n- Gross profit is expected to reconcile to Sales − Cost within $0.02.\n- Rows failing core criteria are excluded from analytical summaries, but remain available in the quality view.")
    st.markdown("#### Download filtered data and summaries")
    st.download_button("Download filtered transactions CSV", filtered.to_csv(index=False).encode("utf-8"), "filtered_transactions.csv", "text/csv")
    st.download_button("Download division summary CSV", ds.to_csv(index=False).encode("utf-8"), "division_summary.csv", "text/csv")
    st.download_button("Download all source rows with quality flags CSV", df.to_csv(index=False).encode("utf-8"), "data_quality_audit.csv", "text/csv")
    st.markdown("#### Important source-data caveat")
    st.info("The supplied file contains order dates from 2024–2025 and ship dates extending from 2026 to 2030. The app flags ship dates before order dates, but dates that are unusually far in the future should be reviewed with the data owner. The app does not silently rewrite source dates.")

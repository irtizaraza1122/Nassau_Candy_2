from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

REQUIRED_COLUMNS = [
    "Row ID", "Order ID", "Order Date", "Ship Date", "Ship Mode", "Customer ID",
    "Country/Region", "City", "State/Province", "Postal Code", "Division", "Region",
    "Product ID", "Product Name", "Sales", "Units", "Gross Profit", "Cost"
]
NUMERIC_COLUMNS = ["Sales", "Units", "Gross Profit", "Cost"]

def load_data(file_or_path) -> pd.DataFrame:
    """Read CSV or uploaded file, validate schema, and standardize types."""
    df = pd.read_csv(file_or_path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("Dataset is missing required columns: " + ", ".join(missing))
    return clean_data(df)

def clean_data(raw: pd.DataFrame) -> pd.DataFrame:
    """Conservative cleaning: standardize text, parse dates, coerce numeric fields.
    Invalid rows are retained with quality flags rather than silently dropped.
    """
    df = raw.copy()
    for c in ["Division", "Region", "Product Name", "Product ID", "Order ID",
              "Ship Mode", "Country/Region", "City", "State/Province"]:
        if c in df.columns:
            df[c] = df[c].astype("string").str.strip()
            df[c] = df[c].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce", dayfirst=True)
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], errors="coerce", dayfirst=True)
    for c in NUMERIC_COLUMNS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Gross Margin (%)"] = np.where(df["Sales"] > 0, df["Gross Profit"] / df["Sales"] * 100, np.nan)
    df["Profit per Unit"] = np.where(df["Units"] > 0, df["Gross Profit"] / df["Units"], np.nan)
    df["Revenue Contribution (%)"] = np.nan
    total_sales = df.loc[df["Sales"] > 0, "Sales"].sum()
    if total_sales:
        df["Revenue Contribution (%)"] = df["Sales"] / total_sales * 100
    total_profit = df.loc[df["Gross Profit"] > 0, "Gross Profit"].sum()
    df["Profit Contribution (%)"] = np.where(total_profit > 0, df["Gross Profit"] / total_profit * 100, np.nan)
    df["Quality Issue"] = ""
    conditions = [
        (df["Sales"].isna() | (df["Sales"] <= 0), "Invalid/non-positive sales"),
        (df["Units"].isna() | (df["Units"] <= 0), "Missing/non-positive units"),
        (df["Cost"].isna() | (df["Cost"] < 0), "Missing/negative cost"),
        (df["Gross Profit"].isna(), "Missing gross profit"),
        (df["Order Date"].isna(), "Invalid order date"),
        (df["Ship Date"].isna(), "Invalid ship date"),
        (df["Ship Date"].notna() & df["Order Date"].notna() & (df["Ship Date"] < df["Order Date"]), "Ship date before order date"),
        (df["Gross Profit"].notna() & df["Sales"].notna() & df["Cost"].notna() &
         ((df["Sales"] - df["Cost"] - df["Gross Profit"]).abs() > 0.02), "Profit does not reconcile to sales minus cost"),
    ]
    for mask, label in conditions:
        df.loc[mask, "Quality Issue"] = df.loc[mask, "Quality Issue"].apply(
            lambda s: (s + "; " if s else "") + label
        )
    df["Has Quality Issue"] = df["Quality Issue"].ne("")
    df["Margin Risk"] = np.select(
        [df["Gross Margin (%)"].isna(), df["Gross Margin (%)"] < 0, df["Gross Margin (%)"] < 20, df["Gross Margin (%)"] < 35],
        ["Unscorable", "Loss-making", "Critical (<20%)", "Watch (<35%)"],
        default="Healthy (>=35%)"
    )
    return df

def analysis_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Rows suitable for core profitability analysis; keeps source unchanged elsewhere."""
    return df.loc[
        df["Sales"].gt(0) & df["Units"].gt(0) & df["Cost"].ge(0) &
        df["Gross Profit"].notna() & df["Order Date"].notna()
    ].copy()

def product_summary(df: pd.DataFrame) -> pd.DataFrame:
    d = analysis_rows(df)
    g = d.groupby(["Division", "Product ID", "Product Name"], dropna=False, as_index=False).agg(
        Sales=("Sales","sum"), Cost=("Cost","sum"), Gross_Profit=("Gross Profit","sum"),
        Units=("Units","sum"), Order_Count=("Order ID","nunique"),
        Margin_Std=("Gross Margin (%)","std"), Row_Count=("Row ID","count")
    )
    g["Gross Margin (%)"] = np.where(g["Sales"] > 0, g["Gross_Profit"] / g["Sales"] * 100, np.nan)
    g["Profit per Unit"] = np.where(g["Units"] > 0, g["Gross_Profit"] / g["Units"], np.nan)
    total_sales = g["Sales"].sum()
    total_profit = g["Gross_Profit"].sum()
    g["Revenue Contribution (%)"] = np.where(total_sales != 0, g["Sales"] / total_sales * 100, np.nan)
    g["Profit Contribution (%)"] = np.where(total_profit != 0, g["Gross_Profit"] / total_profit * 100, np.nan)
    g["Margin Volatility (pp)"] = g["Margin_Std"] * 100
    g["Margin Risk"] = np.select(
        [g["Gross Margin (%)"] < 0, g["Gross Margin (%)"] < 20, g["Gross Margin (%)"] < 35],
        ["Loss-making", "Critical (<20%)", "Watch (<35%)"], default="Healthy (>=35%)"
    )
    g["Sales Rank"] = g["Sales"].rank(method="min", ascending=False).astype(int)
    g["Profit Rank"] = g["Gross_Profit"].rank(method="min", ascending=False).astype(int)
    g["Margin Rank"] = g["Gross Margin (%)"].rank(method="min", ascending=False).astype(int)
    return g.sort_values("Gross_Profit", ascending=False)

def division_summary(df: pd.DataFrame) -> pd.DataFrame:
    d = analysis_rows(df)
    g = d.groupby("Division", dropna=False, as_index=False).agg(
        Sales=("Sales","sum"), Cost=("Cost","sum"), Gross_Profit=("Gross Profit","sum"),
        Units=("Units","sum"), Orders=("Order ID","nunique"), Products=("Product ID","nunique")
    )
    g["Gross Margin (%)"] = np.where(g["Sales"] > 0, g["Gross_Profit"] / g["Sales"] * 100, np.nan)
    g["Profit per Unit"] = np.where(g["Units"] > 0, g["Gross_Profit"] / g["Units"], np.nan)
    g["Revenue Contribution (%)"] = g["Sales"] / g["Sales"].sum() * 100
    g["Profit Contribution (%)"] = g["Gross_Profit"] / g["Gross_Profit"].sum() * 100 if g["Gross_Profit"].sum() else np.nan
    return g.sort_values("Sales", ascending=False)

def pareto_summary(summary: pd.DataFrame, value_col: str) -> pd.DataFrame:
    g = summary.sort_values(value_col, ascending=False).copy()
    total = g[value_col].sum()
    g["Cumulative Value"] = g[value_col].cumsum()
    g["Cumulative Contribution (%)"] = g["Cumulative Value"] / total * 100 if total else np.nan
    g["Cumulative Products (%)"] = np.arange(1, len(g)+1) / len(g) * 100 if len(g) else np.nan
    return g

def kpis(df: pd.DataFrame) -> dict:
    d = analysis_rows(df)
    sales = float(d["Sales"].sum())
    cost = float(d["Cost"].sum())
    profit = float(d["Gross Profit"].sum())
    units = float(d["Units"].sum())
    return {
        "Revenue": sales, "Cost": cost, "Gross Profit": profit,
        "Gross Margin (%)": profit / sales * 100 if sales else np.nan,
        "Profit per Unit": profit / units if units else np.nan,
        "Products": int(d["Product ID"].nunique()),
        "Orders": int(d["Order ID"].nunique()),
        "Rows Analyzed": int(len(d)),
        "Rows Excluded From Core Analysis": int(len(df)-len(d)),
    }

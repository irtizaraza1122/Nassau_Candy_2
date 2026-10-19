import sys
from pathlib import Path
import pandas as pd
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analytics import clean_data, analysis_rows, product_summary, division_summary, pareto_summary, kpis

def sample():
    return pd.DataFrame({
        "Row ID":[1,2,3], "Order ID":["A","B","C"], "Order Date":["01-01-2025"]*3,
        "Ship Date":["02-01-2025"]*3, "Ship Mode":["Standard"]*3, "Customer ID":[1,2,3],
        "Country/Region":["United States"]*3, "City":["X"]*3, "State/Province":["CA"]*3,
        "Postal Code":["1"]*3, "Division":["Chocolate","Chocolate","Sugar"], "Region":["West"]*3,
        "Product ID":["P1","P1","P2"], "Product Name":["Bar","Bar","Candy"],
        "Sales":[100,50,80], "Units":[10,5,8], "Gross Profit":[40,20,24], "Cost":[60,30,56]
    })

def test_margin_calculation_and_reconciliation():
    d=clean_data(sample())
    assert np.isclose(d.loc[0,"Gross Margin (%)"],40)
    assert not d["Has Quality Issue"].any()

def test_product_and_division_summary():
    d=analysis_rows(clean_data(sample()))
    p=product_summary(d)
    assert set(p["Product Name"]) == {"Bar","Candy"}
    bar=p[p["Product Name"]=="Bar"].iloc[0]
    assert np.isclose(bar["Sales"],150)
    assert np.isclose(bar["Gross_Profit"],60)
    assert np.isclose(bar["Gross Margin (%)"],40)
    ds=division_summary(d)
    ch=ds[ds["Division"]=="Chocolate"].iloc[0]
    assert np.isclose(ch["Gross Margin (%)"],40)

def test_invalid_rows_flagged_and_excluded_from_core():
    x=sample()
    x.loc[0,"Sales"]=0
    d=clean_data(x)
    assert "Invalid/non-positive sales" in d.loc[0,"Quality Issue"]
    assert len(analysis_rows(d)) == 2

def test_pareto_cumulative_and_kpis():
    d=analysis_rows(clean_data(sample()))
    p=product_summary(d)
    pareto=pareto_summary(p,"Sales")
    assert pareto["Cumulative Contribution (%)"].is_monotonic_increasing
    assert np.isclose(kpis(d)["Revenue"],230)

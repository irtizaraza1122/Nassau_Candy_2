# Nassau Candy Distributor — Product Line Profitability & Margin Performance Analysis

A local Streamlit analytics application using the provided Nassau Candy Distributor CSV. It includes data validation, product and division profitability, margin diagnostics, Pareto concentration, geography, factory/product mapping, and CSV exports.

## Quick start (Windows)

1. Install Python 3.11 or 3.12 from https://www.python.org/downloads/ and enable **Add Python to PATH**.
2. Extract this project ZIP to a folder.
3. Open PowerShell in that folder.
4. Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

5. Launch the dashboard:

```powershell
streamlit run app.py
```

Streamlit should open a local browser tab. If it does not, open the local URL shown in the terminal (normally http://localhost:8501).

## Project structure

- `app.py` — seven-tab Streamlit dashboard
- `src/analytics.py` — cleaning, validation, KPI and summary logic
- `data/Nassau Candy Distributor.csv` — supplied dataset
- `data/factories.csv` — supplied factory coordinates
- `data/product_factory_mapping.csv` — supplied product-to-factory mapping
- `reports/` — research paper, executive summary, and data profile
- `tests/` — automated analytics tests

## Definitions

- Gross margin (%) = total gross profit ÷ total sales × 100 (weighted margin).
- Profit per unit = total gross profit ÷ total units.
- Revenue contribution = product revenue ÷ total revenue × 100.
- Profit contribution = product gross profit ÷ total gross profit × 100.
- Margin volatility = standard deviation of transaction-level margin percentages for the product, reported in percentage points. This is a descriptive measure; it may be unstable for products with few observations.

## Data-handling choices

- Source rows are preserved in the data-quality view.
- Invalid rows are not silently deleted from the source. Core summaries use rows with positive sales and units, nonnegative cost, a valid order date, and nonmissing gross profit.
- Profit reconciliation is checked against Sales − Cost with a $0.02 tolerance.
- The dataset contains order dates in 2024–2025 and ship dates in 2026–2030. These dates are not automatically corrected; verify them with the data owner.
- The supplied product-to-factory mapping is used as provided. A factory-level summary only includes mapped products and does not assert that reported costs are factory-specific.

## Troubleshooting

- If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that same terminal, then activate again.
- If `streamlit` is not recognized, activate `.venv` and run `python -m streamlit run app.py`.
- If package installation fails, use Python 3.11/3.12 and rerun `pip install -r requirements.txt`.

## Testing

```powershell
pytest -q
```

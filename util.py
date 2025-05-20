import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# --- Chargement des fichiers Excel ---
def load_real_data(files):
    dfs = []
    for f in files:
        df = pd.read_excel(f, sheet_name="Sheet1", engine="openpyxl")
        dfs.append(df)
    df_all = pd.concat(dfs, ignore_index=True)
    df_all["Posting Date"] = pd.to_datetime(df_all["Posting Date"], errors="coerce")
    df_all["Year"] = df_all["Posting Date"].dt.year
    df_all["Month"] = df_all["Posting Date"].dt.month
    df_all["Cost"] = df_all["In profit center local currency"].fillna(0)
    return df_all

# --- Calcul automatique Budget & Forecast ---
def compute_budget_forecast(df):
    ts = (
        df
        .groupby(df["Posting Date"].dt.to_period("M"))["Cost"]
        .sum()
        .sort_index()
        .to_timestamp()
    )
    if len(ts) < 2:
        return pd.DataFrame(columns=["Period", "Budget", "Year", "Month"]), pd.DataFrame(columns=["Period", "Forecast", "Year", "Month"])

    growth12 = ts.pct_change(12).dropna().mean() if len(ts) >= 13 else 0.05
    last = ts.iloc[-1]
    next_period = ts.index[-1] + pd.offsets.MonthBegin()
    budget_next = last * (1 + growth12)
    budget = pd.Series(budget_next, index=[next_period])

    try:
        model = ExponentialSmoothing(ts, trend="add", seasonal=None, initialization_method="estimated")
        fit = model.fit()
        forecast = fit.forecast(1)
    except Exception:
        forecast = pd.Series([last], index=[next_period])

    dfB = pd.DataFrame({
        "Period": pd.to_datetime(list(ts.index.to_timestamp()) + list(budget.index.to_timestamp())),
        "Budget": list(ts.values) + [budget_next]
    })
    dfF = pd.DataFrame({
        "Period": pd.to_datetime(list(ts.index.to_timestamp()) + list(forecast.index.to_timestamp())),
        "Forecast": list(ts.values) + list(forecast.values)
    })
    for dfx in (dfB, dfF):
        dfx["Year"] = dfx["Period"].dt.year
        dfx["Month"] = dfx["Period"].dt.month
    return dfB, dfF

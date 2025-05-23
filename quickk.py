{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": None,
   "id": "d9d7e145-5204-4b5d-83bd-37fdf01606a7",
   "metadata": {},
   "outputs": [],
   "source": [
    "# ---\n",
    "# jupyter:\n",
    "#   jupytext:\n",
    "#     text_representation:\n",
    "#       extension: .py\n",
    "#       format_name: percent\n",
    "#       format_version: '1.3'\n",
    "#       jupytext_version: 1.17.1\n",
    "#   kernelspec:\n",
    "#     display_name: Python 3 (ipykernel)\n",
    "#     language: python\n",
    "#     name: python3\n",
    "# ---\n",
    "\n",
    "# %%\n",
    "import streamlit as st\n",
    "import pandas as pd\n",
    "import plotly.express as px\n",
    "from statsmodels.tsa.holtwinters import ExponentialSmoothing\n",
    "\n",
    "# %% [markdown]\n",
    "# # Dashboard Coûts de Maintenance\n",
    "\n",
    "# %% \n",
    "# --- Page Config ---\n",
    "st.set_page_config(page_title=\"Maintenance Cost Dashboard\", layout=\"wide\")\n",
    "\n",
    "# %% [markdown]\n",
    "# ## 1. Upload des fichiers réels\n",
    "\n",
    "# %%\n",
    "st.sidebar.title(\"Chargement des fichiers\")\n",
    "uploaded_data = st.sidebar.file_uploader(\n",
    "    \"Fichiers Réels (TPS, TPSM, MM MOIS 4, WEAR PART)\",\n",
    "    type=[\"xlsx\"],\n",
    "    accept_multiple_files=True\n",
    ")\n",
    "if not uploaded_data:\n",
    "    st.sidebar.error(\"⚠️ Charge au moins un fichier de données réelles.\")\n",
    "    st.stop()\n",
    "\n",
    "# %%\n",
    "@st.cache_data(ttl=3600)\n",
    "def load_real_data(files):\n",
    "    dfs = []\n",
    "    for f in files:\n",
    "        df = pd.read_excel(f, sheet_name=\"Sheet1\", engine=\"openpyxl\")\n",
    "        dfs.append(df)\n",
    "    df_all = pd.concat(dfs, ignore_index=True)\n",
    "    df_all[\"Posting Date\"] = pd.to_datetime(df_all[\"Posting Date\"])\n",
    "    df_all[\"Year\"]  = df_all[\"Posting Date\"].dt.year\n",
    "    df_all[\"Month\"] = df_all[\"Posting Date\"].dt.month\n",
    "    df_all[\"Cost\"]  = df_all[\"In profit center local currency\"].fillna(0)\n",
    "    return df_all\n",
    "\n",
    "df = load_real_data(uploaded_data)\n",
    "\n",
    "# %% [markdown]\n",
    "# ## 2. Calcul automatique Budget & Forecast\n",
    "\n",
    "# %%\n",
    "@st.cache_data(ttl=3600)\n",
    "def compute_budget_forecast(df):\n",
    "    ts = (\n",
    "        df\n",
    "        .groupby(df[\"Posting Date\"].dt.to_period(\"M\"))[\"Cost\"]\n",
    "        .sum()\n",
    "        .sort_index()\n",
    "        .to_timestamp()\n",
    "    )\n",
    "    # Budget = dernier réel * (1 + croissance moyenne 12 mois)\n",
    "    growth12 = ts.pct_change(12).dropna().mean()\n",
    "    last = ts.iloc[-1]\n",
    "    next_period = ts.index[-1] + pd.offsets.MonthBegin()\n",
    "    budget_next = last * (1 + growth12)\n",
    "    budget = pd.Series(budget_next, index=[next_period])\n",
    "    # Forecast = Holt-Winters (trend additif, sans saison)\n",
    "    model = ExponentialSmoothing(ts, trend=\"add\", seasonal=None, initialization_method=\"estimated\")\n",
    "    fit   = model.fit()\n",
    "    forecast = fit.forecast(1)\n",
    "    # DataFrames\n",
    "    dfB = pd.DataFrame({\n",
    "        \"Period\": list(ts.index) + list(budget.index),\n",
    "        \"Budget\": list(ts.values) + [budget_next]\n",
    "    })\n",
    "    dfF = pd.DataFrame({\n",
    "        \"Period\": list(ts.index) + list(forecast.index),\n",
    "        \"Forecast\": list(ts.values) + list(forecast.values)\n",
    "    })\n",
    "    for dfx in (dfB, dfF):\n",
    "        dfx[\"Year\"]  = dfx[\"Period\"].dt.year\n",
    "        dfx[\"Month\"] = dfx[\"Period\"].dt.month\n",
    "    return dfB, dfF\n",
    "\n",
    "dfB, dfF = compute_budget_forecast(df)\n",
    "\n",
    "# %% [markdown]\n",
    "# ## 3. Filtres\n",
    "\n",
    "# %%\n",
    "st.sidebar.title(\"Filtres\")\n",
    "years  = sorted(df[\"Year\"].unique())\n",
    "year   = st.sidebar.selectbox(\"Année\", years, index=len(years)-1)\n",
    "plants = [\"Toutes\"] + sorted(df[\"Plant\"].dropna().unique().tolist())\n",
    "plant  = st.sidebar.selectbox(\"Usine\", plants)\n",
    "\n",
    "mask = (df[\"Year\"] == year)\n",
    "if plant != \"Toutes\":\n",
    "    mask &= (df[\"Plant\"] == plant)\n",
    "df_filt = df[mask]\n",
    "\n",
    "# %% [markdown]\n",
    "# ## 4. Onglets\n",
    "\n",
    "# %%\n",
    "tabs = st.tabs([\n",
    "    \"Overview\", \"Total & Benchmark\", \"Cost w/o PM\",\n",
    "    \"By Location\", \"By Equipment\", \"By Vendor\",\n",
    "    \"By Material\", \"By Order\", \"By Stoppages\"\n",
    "])\n",
    "\n",
    "# %% [markdown]\n",
    "# ### 4.1 Overview – Actual vs Budget vs Forecast\n",
    "\n",
    "# %%\n",
    "with tabs[0]:\n",
    "    st.header(\"Overview – Actual vs Budget vs Forecast\")\n",
    "    real = (\n",
    "        df_filt\n",
    "        .groupby(df_filt[\"Posting Date\"].dt.to_period(\"M\"))[\"Cost\"]\n",
    "        .sum()\n",
    "        .to_timestamp()\n",
    "        .reset_index()\n",
    "        .rename(columns={\"Posting Date\":\"Period\", \"Cost\":\"Actual\"})\n",
    "    )\n",
    "    comp = real.merge(dfB, on=[\"Period\"], how=\"left\").merge(dfF, on=[\"Period\"], how=\"left\")\n",
    "    fig = px.line(\n",
    "        comp,\n",
    "        x=\"Period\",\n",
    "        y=[\"Actual\",\"Budget\",\"Forecast\"],\n",
    "        labels={\"value\":\"Coût\", \"Period\":\"Mois\"},\n",
    "        markers=True\n",
    "    )\n",
    "    st.plotly_chart(fig, use_container_width=True)\n",
    "\n",
    "# %% [markdown]\n",
    "# ### 4.2 Total Cost & Benchmark\n",
    "\n",
    "# %%\n",
    "with tabs[1]:\n",
    "    st.header(\"Total Cost & Benchmark\")\n",
    "    agg = df_filt.groupby(\"Plant\")[\"Cost\"].sum().reset_index().sort_values(\"Cost\", ascending=False)\n",
    "    st.plotly_chart(px.bar(agg, x=\"Plant\", y=\"Cost\", labels={\"Cost\":\"Coût total\"}), use_container_width=True)\n",
    "\n",
    "# %% [markdown]\n",
    "# ### 4.3 Cost without PM order\n",
    "\n",
    "# %%\n",
    "with tabs[2]:\n",
    "    st.header(\"Cost without PM order\")\n",
    "    wo_pm = df_filt[df_filt[\"Order\"].isna()]\n",
    "    agg = (\n",
    "        wo_pm\n",
    "        .groupby(wo_pm[\"Posting Date\"].dt.to_period(\"M\"))[\"Cost\"]\n",
    "        .sum()\n",
    "        .to_timestamp()\n",
    "        .reset_index()\n",
    "    )\n",
    "    agg.columns = [\"Period\",\"Cost\"]\n",
    "    st.plotly_chart(px.bar(agg, x=\"Period\", y=\"Cost\", labels={\"Cost\":\"Coût sans PM\"}), use_container_width=True)\n",
    "\n",
    "# %% [markdown]\n",
    "# ### 4.4 Cost at Functional Location\n",
    "\n",
    "# %%\n",
    "with tabs[3]:\n",
    "    st.header(\"Cost at Functional Location\")\n",
    "    agg = df_filt.groupby(\"Functional Area\")[\"Cost\"].sum().reset_index().sort_values(\"Cost\", ascending=False)\n",
    "    st.plotly_chart(px.bar(agg, x=\"Functional Area\", y=\"Cost\"), use_container_width=True)\n",
    "\n",
    "# %% [markdown]\n",
    "# ### 4.5 Cost at Equipment\n",
    "\n",
    "# %%\n",
    "with tabs[4]:\n",
    "    st.header(\"Cost at Equipment\")\n",
    "    agg = df_filt.groupby(\"Equipment\")[\"Cost\"].sum().reset_index().sort_values(\"Cost\", ascending=False)\n",
    "    st.plotly_chart(px.bar(agg, x=\"Equipment\", y=\"Cost\"), use_container_width=True)\n",
    "\n",
    "# %% [markdown]\n",
    "# ### 4.6 Cost at Vendor\n",
    "\n",
    "# %%\n",
    "with tabs[5]:\n",
    "    st.header(\"Cost at Vendor\")\n",
    "    agg = df_filt.groupby(\"Vendor\")[\"Cost\"].sum().reset_index().sort_values(\"Cost\", ascending=False)\n",
    "    st.plotly_chart(px.bar(agg, x=\"Vendor\", y=\"Cost\"), use_container_width=True)\n",
    "\n",
    "# %% [markdown]\n",
    "# ### 4.7 Cost at Material\n",
    "\n",
    "# %%\n",
    "with tabs[6]:\n",
    "    st.header(\"Cost at Material\")\n",
    "    agg = df_filt.groupby(\"Material\")[\"Cost\"].sum().reset_index().sort_values(\"Cost\", ascending=False)\n",
    "    st.plotly_chart(px.bar(agg, x=\"Material\", y=\"Cost\"), use_container_width=True)\n",
    "\n",
    "# %% [markdown]\n",
    "# ### 4.8 Cost at Order\n",
    "\n",
    "# %%\n",
    "with tabs[7]:\n",
    "    st.header(\"Cost at Order\")\n",
    "    agg = df_filt.groupby(\"Order\")[\"Cost\"].sum().reset_index().sort_values(\"Cost\", ascending=False)\n",
    "    st.plotly_chart(px.bar(agg, x=\"Order\", y=\"Cost\"), use_container_width=True)\n",
    "\n",
    "# %% [markdown]\n",
    "# ### 4.9 Cost at Stoppages\n",
    "\n",
    "# %%\n",
    "with tabs[8]:\n",
    "    st.header(\"Cost at Stoppages\")\n",
    "    agg = (\n",
    "        df_filt\n",
    "        .groupby([\"Stop ID\",\"Stop Cause\"])[\"Cost\"]\n",
    "        .sum()\n",
    "        .reset_index()\n",
    "        .sort_values(\"Cost\", ascending=False)\n",
    "    )\n",
    "    st.plotly_chart(\n",
    "        px.bar(agg, x=\"Stop ID\", y=\"Cost\", hover_data=[\"Stop Cause\"]),\n",
    "        use_container_width=True\n",
    "    )\n"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3 (ipykernel)",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.12.4"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}

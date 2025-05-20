import streamlit as st
import pandas as pd
import plotly.express as px
from utils import load_real_data, compute_budget_forecast

# --- Page Config ---
st.set_page_config(page_title="Maintenance Cost Dashboard", layout="wide")

# --- Display visual example ---
st.image("17426b14-ca6b-4020-b777-92a17e0db9f1.png", caption="Exemple du rapport de coûts de maintenance (onglet 'Functional Location')", use_column_width=True)

# --- Upload des fichiers réels ---
st.sidebar.title("Chargement des fichiers")
uploaded_data = st.sidebar.file_uploader(
    "Fichiers Réels (TPS, TPSM, MM MOIS 4, WEAR PART)",
    type=["xlsx"],
    accept_multiple_files=True
)
if not uploaded_data:
    st.sidebar.error("⚠️ Charge au moins un fichier de données réelles.")
    st.stop()

df = load_real_data(uploaded_data)
dfB, dfF = compute_budget_forecast(df)

# --- Filtres ---
st.sidebar.title("Filtres")

# Top Filters
region = st.sidebar.selectbox("Region", sorted(df["Business Area"].dropna().unique()))
country_options = df[df["Business Area"] == region]["Controlling Area"].dropna().unique()
country = st.sidebar.selectbox("Country", sorted(country_options))

years = sorted(df["Year"].unique())
year = st.sidebar.selectbox("Année", years, index=len(years) - 1)
months = df[df["Year"] == year]["Month"].dropna().unique()
month = st.sidebar.selectbox("Mois", sorted(months))

settlement = st.sidebar.selectbox("Settlement Type", sorted(df["Document Type"].dropna().unique()))
currency = st.sidebar.selectbox("Currency", sorted(df["Curr. Key of CoCd Curr."].dropna().unique()))

# Left Filters
subsegment = st.sidebar.selectbox("Sub-segment", sorted(df["Profit Center"].dropna().unique()))
plant_options = df[df["Controlling Area"] == country]["Plant"].dropna().unique()
plant = st.sidebar.selectbox("Usine", ["Toutes"] + sorted(plant_options))
functional_area = st.sidebar.selectbox("Functional Area", sorted(df["Functional Area"].dropna().unique()))
plant_section = st.sidebar.selectbox("Plant Section", sorted(df["Cost Center"].dropna().unique()))
revision = st.sidebar.selectbox("Revision", sorted(df["Ref. Document"].dropna().unique()))
order_type = st.sidebar.selectbox("Order Type", sorted(df["Order"].dropna().unique()))
work_center = st.sidebar.selectbox("Work Center", sorted(df["WBS Element"].dropna().unique()))
planner_group = st.sidebar.selectbox("Planner Group", sorted(df["User Name"].dropna().unique()))

# Filtrage combiné
mask = (
    (df["Year"] == year) &
    (df["Month"] == month) &
    (df["Business Area"] == region) &
    (df["Controlling Area"] == country)
)
if plant != "Toutes":
    mask &= (df["Plant"] == plant)
df_filt = df[mask]

# --- Onglets ---
tabs = st.tabs([
    "Overview", "Total & Benchmark", "Cost w/o PM",
    "By Location", "By Equipment", "By Vendor",
    "By Material", "By Order", "By Stoppages"
])

with tabs[0]:
    st.header("Overview – Actual vs Budget vs Forecast")
    real = (
        df_filt
        .groupby(df_filt["Posting Date"].dt.to_period("M"))["Cost"]
        .sum()
        .to_timestamp()
        .reset_index()
        .rename(columns={"Posting Date": "Period", "Cost": "Actual"})
    )
    real["Period"] = pd.to_datetime(real["Period"], errors="coerce")
    dfB["Period"] = pd.to_datetime(dfB["Period"], errors="coerce")
    dfF["Period"] = pd.to_datetime(dfF["Period"], errors="coerce")
    comp = pd.merge(real, dfB, on="Period", how="left")
    comp = pd.merge(comp, dfF, on="Period", how="left")
    try:
        comp[["Actual", "Budget", "Forecast"]] = comp[["Actual", "Budget", "Forecast"]].apply(pd.to_numeric, errors="coerce")
        fig = px.line(
            comp,
            x="Period",
            y=["Actual", "Budget", "Forecast"],
            labels={"value": "Coût", "Period": "Mois"},
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Erreur dans l'affichage du graphique : {e}")
        st.dataframe(comp)

# [Remaining tabs unchanged]

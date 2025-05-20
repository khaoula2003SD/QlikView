# app.py

import streamlit as st
import pandas as pd
import plotly.express as px
from utils import load_real_data, compute_budget_forecast

# --- Page Config ---
st.set_page_config(page_title="Maintenance Cost Dashboard", layout="wide")

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
years = sorted(df["Year"].unique())
year = st.sidebar.selectbox("Année", years, index=len(years) - 1)
plants = ["Toutes"] + sorted(df["Plant"].dropna().unique().tolist())
plant = st.sidebar.selectbox("Usine", plants)

mask = (df["Year"] == year)
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
    real["Period"] = pd.to_datetime(real["Period"])
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

with tabs[1]:
    st.header("Total Cost & Benchmark")
    agg = df_filt.groupby("Plant")["Cost"].sum().reset_index().sort_values("Cost", ascending=False)
    st.plotly_chart(px.bar(agg, x="Plant", y="Cost", labels={"Cost": "Coût total"}), use_container_width=True)

with tabs[2]:
    st.header("Cost without PM order")
    wo_pm = df_filt[df_filt["Order"].isna()]
    agg = (
        wo_pm
        .groupby(wo_pm["Posting Date"].dt.to_period("M"))["Cost"]
        .sum()
        .to_timestamp()
        .reset_index()
    )
    agg.columns = ["Period", "Cost"]
    st.plotly_chart(px.bar(agg, x="Period", y="Cost", labels={"Cost": "Coût sans PM"}), use_container_width=True)

with tabs[3]:
    st.header("Cost at Functional Location")
    agg = df_filt.groupby("Functional Area")["Cost"].sum().reset_index().sort_values("Cost", ascending=False)
    st.plotly_chart(px.bar(agg, x="Functional Area", y="Cost"), use_container_width=True)

with tabs[4]:
    st.header("Cost at Equipment")
    if "Equipment" in df_filt.columns:
        agg = df_filt.groupby("Equipment")["Cost"].sum().reset_index().sort_values("Cost", ascending=False)
        st.plotly_chart(px.bar(agg, x="Equipment", y="Cost"), use_container_width=True)
    else:
        st.warning("La colonne 'Equipment' est absente des fichiers chargés.")

with tabs[5]:
    st.header("Cost at Vendor")
    agg = df_filt.groupby("Vendor")["Cost"].sum().reset_index().sort_values("Cost", ascending=False)
    st.plotly_chart(px.bar(agg, x="Vendor", y="Cost"), use_container_width=True)

with tabs[6]:
    st.header("Cost at Material")
    agg = df_filt.groupby("Material")["Cost"].sum().reset_index().sort_values("Cost", ascending=False)
    st.plotly_chart(px.bar(agg, x="Material", y="Cost"), use_container_width=True)

with tabs[7]:
    st.header("Cost at Order")
    agg = df_filt.groupby("Order")["Cost"].sum().reset_index().sort_values("Cost", ascending=False)
    st.plotly_chart(px.bar(agg, x="Order", y="Cost"), use_container_width=True)

with tabs[8]:
    st.header("Cost at Stoppages")
    if "Stop ID" in df_filt.columns and "Stop Cause" in df_filt.columns:
        agg = (
            df_filt
            .groupby(["Stop ID", "Stop Cause"])["Cost"]
            .sum()
            .reset_index()
            .sort_values("Cost", ascending=False)
        )
        st.plotly_chart(px.bar(agg, x="Stop ID", y="Cost", hover_data=["Stop Cause"]), use_container_width=True)
    else:
        st.warning("Colonnes 'Stop ID' et 'Stop Cause' absentes des données.")

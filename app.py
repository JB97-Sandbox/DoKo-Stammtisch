import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

st.set_page_config(page_title="Stammtisch Punkte", page_icon="🃏", layout="wide")

# --- Verbindung zu Supabase ---
@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_client()

# --- Hilfsfunktionen ---
def load_spieler():
    res = supabase.table("spieler").select("*").order("name").execute()
    return pd.DataFrame(res.data)

def load_spielabende():
    res = supabase.table("spielabend").select("*").order("datum", desc=True).execute()
    return pd.DataFrame(res.data)

def load_ergebnisse():
    res = supabase.table("ergebnis").select(
        "*, spiel(*, spielabend(*)), spieler(*)"
    ).execute()
    return res.data

def add_spieler(name: str):
    supabase.table("spieler").insert({"name": name}).execute()

def add_spielabend(datum: str, ort: str):
    res = supabase.table("spielabend").insert({"datum": datum, "ort": ort}).execute()
    return res.data[0]["id"]

def add_spiel(spielabend_id: int, spielart: str, runde: int):
    res = supabase.table("spiel").insert({
        "spielabend_id": spielabend_id,
        "spielart": spielart,
        "runde": runde
    }).execute()
    return res.data[0]["id"]

def add_ergebnis(spiel_id: int, spieler_id: int, punkte: int):
    supabase.table("ergebnis").insert({
        "spiel_id": spiel_id,
        "spieler_id": spieler_id,
        "punkte": punkte
    }).execute()

# --- Passwortschutz (einfach, optional) ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        pw = st.text_input("Passwort", type="password")
        if pw == st.secrets.get("APP_PASSWORD", ""):
            st.session_state.authenticated = True
            st.rerun()
        else:
            if pw:
                st.error("Falsches Passwort")
            st.stop()

check_password()

st.title("🃏 Stammtisch Punkte-Tracker")

tab1, tab2, tab3, tab4 = st.tabs(["Neue Runde erfassen", "Spieler verwalten", "Rangliste", "Verlauf"])

# --- Tab 1: Neue Runde erfassen ---
with tab1:
    st.header("Neuen Spielabend / neue Runde erfassen")

    spieler_df = load_spieler()
    if spieler_df.empty:
        st.warning("Bitte zuerst Spieler im Tab 'Spieler verwalten' anlegen.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            datum = st.date_input("Datum", value=date.today())
        with col2:
            ort = st.text_input("Ort (optional)", "")
        with col3:
            spielart = st.selectbox("Spielart", ["Doppelkopf", "Skat"])

        st.subheader("Teilnehmer & Punkte dieser Runde")
        teilnehmer = st.multiselect(
            "Wer spielt mit?",
            options=spieler_df["name"].tolist(),
            default=spieler_df["name"].tolist()
        )

        punkte_eingabe = {}
        if teilnehmer:
            cols = st.columns(len(teilnehmer))
            for i, name in enumerate(teilnehmer):
                with cols[i]:
                    punkte_eingabe[name] = st.number_input(
                        f"{name}", value=0, step=1, key=f"pkt_{name}"
                    )

        runde_nr = st.number_input("Rundennummer (bei mehreren Runden am Abend)", min_value=1, value=1, step=1)

        if st.button("💾 Runde speichern", type="primary"):
            # Spielabend nur einmal pro Datum+Ort anlegen, sonst wiederverwenden
            abende = load_spielabende()
            existing = abende[(abende["datum"] == str(datum)) & (abende["ort"] == ort)] if not abende.empty else pd.DataFrame()
            if not existing.empty:
                abend_id = int(existing.iloc[0]["id"])
            else:
                abend_id = add_spielabend(str(datum), ort)

            spiel_id = add_spiel(abend_id, spielart, int(runde_nr))

            id_map = dict(zip(spieler_df["name"], spieler_df["id"]))
            for name, punkte in punkte_eingabe.items():
                add_ergebnis(spiel_id, int(id_map[name]), int(punkte))

            st.success(f"Runde gespeichert! ({len(punkte_eingabe)} Spieler, {spielart})")
            st.cache_resource.clear()

# --- Tab 2: Spieler verwalten ---
with tab2:
    st.header("Spieler verwalten")
    neuer_name = st.text_input("Neuen Spieler hinzufügen")
    if st.button("➕ Spieler hinzufügen"):
        if neuer_name.strip():
            add_spieler(neuer_name.strip())
            st.success(f"{neuer_name} hinzugefügt!")
            st.rerun()

    spieler_df = load_spieler()
    if not spieler_df.empty:
        st.dataframe(spieler_df[["name"]], use_container_width=True, hide_index=True)

# --- Tab 3: Rangliste ---
with tab3:
    st.header("Gesamtrangliste")
    data = load_ergebnisse()
    if data:
        rows = []
        for row in data:
            rows.append({
                "Spieler": row["spieler"]["name"],
                "Punkte": row["punkte"],
                "Spielart": row["spiel"]["spielart"],
                "Datum": row["spiel"]["spielabend"]["datum"],
            })
        df = pd.DataFrame(rows)

        filter_art = st.radio("Filter Spielart", ["Alle", "Doppelkopf", "Skat"], horizontal=True)
        if filter_art != "Alle":
            df = df[df["Spielart"] == filter_art]

        rangliste = df.groupby("Spieler")["Punkte"].agg(["sum", "count", "mean"]).reset_index()
        rangliste.columns = ["Spieler", "Gesamtpunkte", "Anzahl Runden", "Ø Punkte/Runde"]
        rangliste = rangliste.sort_values("Gesamtpunkte", ascending=False)
        rangliste["Ø Punkte/Runde"] = rangliste["Ø Punkte/Runde"].round(1)

        st.dataframe(rangliste, use_container_width=True, hide_index=True)
    else:
        st.info("Noch keine Ergebnisse erfasst.")

# --- Tab 4: Verlauf ---
with tab4:
    st.header("Punkteverlauf über Zeit")
    data = load_ergebnisse()
    if data:
        rows = []
        for row in data:
            rows.append({
                "Spieler": row["spieler"]["name"],
                "Punkte": row["punkte"],
                "Spielart": row["spiel"]["spielart"],
                "Datum": row["spiel"]["spielabend"]["datum"],
            })
        df = pd.DataFrame(rows)
        df["Datum"] = pd.to_datetime(df["Datum"])
        verlauf = df.groupby(["Datum", "Spieler"])["Punkte"].sum().reset_index()
        verlauf = verlauf.sort_values("Datum")
        verlauf["Kumuliert"] = verlauf.groupby("Spieler")["Punkte"].cumsum()

        pivot = verlauf.pivot(index="Datum", columns="Spieler", values="Kumuliert").ffill()
        st.line_chart(pivot)
    else:
        st.info("Noch keine Daten für Verlauf vorhanden.")

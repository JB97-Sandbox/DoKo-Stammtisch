import streamlit as st
import pandas as pd
import base64
from datetime import date
from supabase import create_client, Client

st.set_page_config(page_title="Stammtisch Punkte", page_icon="🃏", layout="wide")

@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_client()

def load_spieler():
    res = supabase.table("spieler").select("*").order("name").execute()
    return pd.DataFrame(res.data)

def load_spielabende():
    res = supabase.table("spielabend").select("*").order("datum", desc=True).execute()
    return pd.DataFrame(res.data)

def load_ergebnisse():
    res = supabase.table("ergebnis").select("*, spiel(*, spielabend(*)), spieler(*)").execute()
    return res.data

def add_spieler(name: str):
    supabase.table("spieler").insert({"name": name}).execute()

def add_spielabend(datum: str, ort: str, spielart: str):
    res = supabase.table("spielabend").insert({"datum": datum, "ort": ort, "spielart": spielart}).execute()
    return res.data[0]["id"]

def add_spiel(spielabend_id: int, runde: int, geber: str, punktwert: int):
    res = supabase.table("spiel").insert({
        "spielabend_id": spielabend_id, "runde": runde, "geber": geber, "punktwert": punktwert
    }).execute()
    return res.data[0]["id"]

def add_ergebnis(spiel_id: int, spieler_id: int, punkte: int):
    supabase.table("ergebnis").insert({"spiel_id": spiel_id, "spieler_id": spieler_id, "punkte": punkte}).execute()

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("🃏 Stammtisch Punkte-Tracker")
        pw = st.text_input("Passwort", type="password")
        if pw == st.secrets.get("APP_PASSWORD", ""):
            st.session_state.authenticated = True
            st.rerun()
        else:
            if pw:
                st.error("Falsches Passwort")
            st.stop()

check_password()

if "page" not in st.session_state:
    st.session_state.page = "home"
if "abend_id" not in st.session_state:
    st.session_state.abend_id = None
if "spielart" not in st.session_state:
    st.session_state.spielart = None
if "teilnehmer" not in st.session_state:
    st.session_state.teilnehmer = []
if "geber_index" not in st.session_state:
    st.session_state.geber_index = None
if "runde_nr" not in st.session_state:
    st.session_state.runde_nr = 1
if "phase" not in st.session_state:
    st.session_state.phase = "setup"

def go_to(page_name: str, reset_game: bool = False):
    st.session_state.page = page_name
    if reset_game:
        st.session_state.abend_id = None
        st.session_state.spielart = None
        st.session_state.teilnehmer = []
        st.session_state.geber_index = None
        st.session_state.runde_nr = 1
        st.session_state.phase = "setup"

@st.cache_data
def get_base64_image(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

bg_image = get_base64_image("background.png")

if bg_image:
    st.markdown(f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(255,255,255,0.55), rgba(255,255,255,0.55)),
                           url("data:image/png;base64,{bg_image}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
<style>
div.stButton > button {
    height: 130px; width: 100%; font-size: 22px; font-weight: 700;
    border-radius: 18px; border: 3px solid #3A2E1F;
    background-color: rgba(255,255,255,0.9);
    transition: all 0.15s ease-in-out;
}
div.stButton > button:hover {
    border-color: #E23636; background-color: rgba(255,240,240,0.95); transform: scale(1.03);
}
.big-box { background-color: rgba(255,255,255,0.92); border-radius: 18px; padding: 25px; border: 2px solid #3A2E1F; }
</style>
""", unsafe_allow_html=True)

def show_back_button(label="⬅️ Zurück zur Übersicht", reset_game=False):
    if st.button(label):
        go_to("home", reset_game=reset_game)
        st.rerun()

if st.session_state.page == "home":
    st.title("🃏 Stammtisch Punkte-Tracker")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🎮\n\nNeues Spiel", key="btn_neues_spiel"):
            go_to("neues_spiel", reset_game=True)
            st.rerun()
    with col2:
        if st.button("📊\n\nStatistik", key="btn_statistik"):
            go_to("statistik")
            st.rerun()
    with col3:
        if st.button("👥\n\nSpieler verwalten", key="btn_spieler"):
            go_to("spieler")
            st.rerun()

elif st.session_state.page == "neues_spiel":
    if st.session_state.phase == "setup":
        show_back_button(reset_game=True)
        st.header("🎮 Neuer Spielabend")
        st.markdown('<div class="big-box">', unsafe_allow_html=True)
        st.subheader("Was wird heute gespielt?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🃏 Doppelkopf", key="btn_doko"):
                st.session_state.spielart = "Doppelkopf"
                st.session_state.phase = "teilnehmer"
                st.rerun()
        with col2:
            if st.button("🂠 Skat", key="btn_skat"):
                st.session_state.spielart = "Skat"
                st.session_state.phase = "teilnehmer"
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.phase == "teilnehmer":
        show_back_button(reset_game=True)
        st.header(f"🎮 {st.session_state.spielart} - Teilnehmer festlegen")
        st.markdown('<div class="big-box">', unsafe_allow_html=True)
        spieler_df = load_spieler()
        if spieler_df.empty:
            st.warning("Bitte zuerst Spieler unter 'Spieler verwalten' anlegen.")
        else:
            st.write("Wer spielt heute mit? (Reihenfolge = Sitzreihenfolge im Uhrzeigersinn)")
            teilnehmer = st.multiselect("Teilnehmer auswählen", options=spieler_df["name"].tolist(), default=st.session_state.teilnehmer)
            st.session_state.teilnehmer = teilnehmer
            ort = st.text_input("Ort (optional)", "")
            if len(teilnehmer) >= 3:
                if st.button("▶️ Los geht's!", type="primary"):
                    import random
                    abend_id = add_spielabend(str(date.today()), ort, st.session_state.spielart)
                    st.session_state.abend_id = abend_id
                    st.session_state.geber_index = random.randint(0, len(teilnehmer) - 1)
                    st.session_state.runde_nr = 1
                    st.session_state.phase = "spiel_laeuft"
                    st.rerun()
            else:
                st.info("Bitte mindestens 3 Spieler auswählen.")
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.phase == "spiel_laeuft":
        teilnehmer = st.session_state.teilnehmer
        geber = teilnehmer[st.session_state.geber_index]
        st.header(f"🎮 {st.session_state.spielart} - Runde {st.session_state.runde_nr}")
        st.markdown('<div class="big-box">', unsafe_allow_html=True)
        st.markdown(f"### 🎴 Geber: **{geber}**")
        st.write("Teilnehmer: " + ", ".join(teilnehmer))
        st.markdown('</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Spiel vorbei", type="primary", key="btn_spiel_vorbei"):
                st.session_state.phase = "spiel_auswertung"
                st.rerun()
        with col2:
            if st.button("🏁 Abend vorbei", key="btn_abend_vorbei"):
                go_to("home", reset_game=True)
                st.rerun()

    elif st.session_state.phase == "spiel_auswertung":
        teilnehmer = st.session_state.teilnehmer
        geber = teilnehmer[st.session_state.geber_index]
        st.header(f"🎮 Auswertung Runde {st.session_state.runde_nr}")
        st.markdown('<div class="big-box">', unsafe_allow_html=True)
        punktwert = st.number_input("Wieviele Punkte war das Spiel wert?", min_value=0, value=0, step=1)
        col1, col2 = st.columns(2)
        with col1:
            gewinner = st.multiselect("Wer hat gewonnen?", options=teilnehmer, key="gewinner_sel")
        with col2:
            verlierer = st.multiselect("Wer hat verloren?", options=[t for t in teilnehmer if t not in gewinner], key="verlierer_sel")
        if st.button("💾 Ergebnis speichern", type="primary"):
            if not gewinner or not verlierer:
                st.error("Bitte mindestens einen Gewinner und einen Verlierer auswählen.")
            else:
                spieler_df = load_spieler()
                id_map = dict(zip(spieler_df["name"], spieler_df["id"]))
                spiel_id = add_spiel(st.session_state.abend_id, st.session_state.runde_nr, geber, int(punktwert))
                for name in gewinner:
                    add_ergebnis(spiel_id, int(id_map[name]), int(punktwert))
                for name in verlierer:
                    add_ergebnis(spiel_id, int(id_map[name]), -int(punktwert))
                for name in teilnehmer:
                    if name not in gewinner and name not in verlierer:
                        add_ergebnis(spiel_id, int(id_map[name]), 0)
                st.success("Ergebnis gespeichert!")
        st.markdown('</div>', unsafe_allow_html=True)
        st.subheader("Nächstes Spiel?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Ja, weiter", type="primary", key="btn_naechstes_ja"):
                st.session_state.geber_index = (st.session_state.geber_index + 1) % len(teilnehmer)
                st.session_state.runde_nr += 1
                st.session_state.phase = "spiel_laeuft"
                st.rerun()
        with col2:
            if st.button("❌ Nein, Abend beenden", key="btn_naechstes_nein"):
                go_to("home", reset_game=True)
                st.rerun()

elif st.session_state.page == "statistik":
    show_back_button()
    st.header("📊 Statistik")
    tab_rang, tab_verlauf = st.tabs(["Rangliste", "Verlauf"])
    data = load_ergebnisse()
    with tab_rang:
        if data:
            rows = [{"Spieler": r["spieler"]["name"], "Punkte": r["punkte"],
                     "Spielart": r["spiel"]["spielabend"]["spielart"], "Datum": r["spiel"]["spielabend"]["datum"]} for r in data]
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
    with tab_verlauf:
        if data:
            rows = [{"Spieler": r["spieler"]["name"], "Punkte": r["punkte"],
                     "Spielart": r["spiel"]["spielabend"]["spielart"], "Datum": r["spiel"]["spielabend"]["datum"]} for r in data]
            df = pd.DataFrame(rows)
            df["Datum"] = pd.to_datetime(df["Datum"])
            verlauf = df.groupby(["Datum", "Spieler"])["Punkte"].sum().reset_index()
            verlauf = verlauf.sort_values("Datum")
            verlauf["Kumuliert"] = verlauf.groupby("Spieler")["Punkte"].cumsum()
            pivot = verlauf.pivot(index="Datum", columns="Spieler", values="Kumuliert").ffill()
            st.line_chart(pivot)
        else:
            st.info("Noch keine Daten für Verlauf vorhanden.")

elif st.session_state.page == "spieler":
    show_back_button()
    st.header("👥 Spieler verwalten")
    neuer_name = st.text_input("Neuen Spieler hinzufügen")
    if st.button("➕ Spieler hinzufügen"):
        if neuer_name.strip():
            add_spieler(neuer_name.strip())
            st.success(f"{neuer_name} hinzugefügt!")
            st.rerun()
    spieler_df = load_spieler()
    if not spieler_df.empty:
        st.dataframe(spieler_df[["name"]], use_container_width=True, hide_index=True)

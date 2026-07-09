import streamlit as st
import pandas as pd
import base64
from datetime import date
from supabase import create_client, Client

st.set_page_config(page_title="Stammtisch Punkte", page_icon="🃏", layout="centered")

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
        st.markdown("<h1 style='text-align:center;'>🃏 Stammtisch</h1>", unsafe_allow_html=True)
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

bg_css = ""
if bg_image:
    bg_css = f"""
    .stApp {{
        background-image: linear-gradient(rgba(255,255,255,0.72), rgba(255,255,255,0.82)),
                           url("data:image/png;base64,{bg_image}");
        background-size: cover;
        background-position: center top;
        background-attachment: fixed;
    }}
    """

st.markdown(f"""
<style>
{bg_css}

.block-container {{
    padding-top: 1.2rem !important;
    padding-bottom: 3rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 600px;
}}

div.stButton > button {{
    width: 100%;
    min-height: 64px;
    font-size: 19px;
    font-weight: 700;
    border-radius: 16px;
    border: none;
    color: white;
    background: linear-gradient(135deg, #FF6B4A 0%, #E23636 100%);
    box-shadow: 0 4px 10px rgba(0,0,0,0.18);
    transition: all 0.15s ease-in-out;
    margin-bottom: 0.6rem;
}}
div.stButton > button:hover {{
    transform: scale(1.02);
    box-shadow: 0 6px 14px rgba(0,0,0,0.25);
}}
div.stButton > button:active {{
    transform: scale(0.98);
}}

button[kind="secondary"] {{
    background: linear-gradient(135deg, #6c757d 0%, #495057 100%) !important;
}}

.card-box {{
    background-color: rgba(255,255,255,0.94);
    border-radius: 20px;
    padding: 22px 18px;
    margin-bottom: 1rem;
    box-shadow: 0 3px 12px rgba(0,0,0,0.12);
}}

.geber-badge {{
    display: inline-block;
    background: linear-gradient(135deg, #FFD166 0%, #F4A24A 100%);
    color: #3A2E1F;
    font-weight: 800;
    font-size: 20px;
    padding: 10px 20px;
    border-radius: 30px;
    margin: 8px 0 14px 0;
    box-shadow: 0 3px 8px rgba(0,0,0,0.15);
}}

h1, h2, h3 {{
    text-align: center;
}}

span[data-baseweb="tag"] {{
    background-color: #E23636 !important;
}}
</style>
""", unsafe_allow_html=True)

def show_back_button(label="⬅️ Zurück", reset_game=False):
    if st.button(label, key=f"back_{st.session_state.page}"):
        go_to("home", reset_game=reset_game)
        st.rerun()

if st.session_state.page == "home":
    st.markdown("<h1>🃏 Stammtisch</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#555; margin-bottom:1.5rem;'>Punkte-Tracker für Doppelkopf & Skat</p>", unsafe_allow_html=True)

    if st.button("🎮  Neues Spiel", key="btn_neues_spiel"):
        go_to("neues_spiel", reset_game=True)
        st.rerun()
    if st.button("📊  Statistik", key="btn_statistik"):
        go_to("statistik")
        st.rerun()
    if st.button("👥  Spieler verwalten", key="btn_spieler"):
        go_to("spieler")
        st.rerun()

elif st.session_state.page == "neues_spiel":

    if st.session_state.phase == "setup":
        show_back_button(reset_game=True)
        st.markdown("<h2>🎮 Neuer Spielabend</h2>", unsafe_allow_html=True)
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; font-weight:600;'>Was wird heute gespielt?</p>", unsafe_allow_html=True)
        if st.button("🃏  Doppelkopf", key="btn_doko"):
            st.session_state.spielart = "Doppelkopf"
            st.session_state.phase = "teilnehmer"
            st.rerun()
        if st.button("🂠  Skat", key="btn_skat"):
            st.session_state.spielart = "Skat"
            st.session_state.phase = "teilnehmer"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.phase == "teilnehmer":
        show_back_button(reset_game=True)
        st.markdown(f"<h2>{st.session_state.spielart}</h2>", unsafe_allow_html=True)
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        spieler_df = load_spieler()
        if spieler_df.empty:
            st.warning("Bitte zuerst Spieler unter 'Spieler verwalten' anlegen.")
        else:
            st.markdown("<p style='font-weight:600;'>Wer spielt mit?</p>", unsafe_allow_html=True)
            st.caption("Reihenfolge = Sitzreihenfolge im Uhrzeigersinn")
            teilnehmer = st.multiselect("Teilnehmer", options=spieler_df["name"].tolist(),
                                          default=st.session_state.teilnehmer, label_visibility="collapsed")
            st.session_state.teilnehmer = teilnehmer
            ort = st.text_input("Ort (optional)", "")

            if len(teilnehmer) >= 3:
                if st.button("▶️  Los geht's!", key="btn_los"):
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

        st.markdown(f"<h2>Runde {st.session_state.runde_nr}</h2>", unsafe_allow_html=True)
        st.markdown('<div class="card-box" style="text-align:center;">', unsafe_allow_html=True)
        st.markdown(f'<span class="geber-badge">🎴 Geber: {geber}</span>', unsafe_allow_html=True)
        st.markdown(f"<p style='color:#555;'>Teilnehmer: {', '.join(teilnehmer)}</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("✅  Spiel vorbei", key="btn_spiel_vorbei"):
            st.session_state.phase = "spiel_auswertung"
            st.rerun()
        if st.button("🏁  Abend vorbei", key="btn_abend_vorbei"):
            go_to("home", reset_game=True)
            st.rerun()

    elif st.session_state.phase == "spiel_auswertung":
        teilnehmer = st.session_state.teilnehmer
        geber = teilnehmer[st.session_state.geber_index]

        st.markdown(f"<h2>Auswertung Runde {st.session_state.runde_nr}</h2>", unsafe_allow_html=True)
        st.markdown('<div class="card-box">', unsafe_allow_html=True)

        punktwert = st.number_input("Punktwert des Spiels", min_value=0, value=0, step=1)
        gewinner = st.multiselect("Gewinner", options=teilnehmer, key="gewinner_sel")
        verlierer = st.multiselect("Verlierer", options=[t for t in teilnehmer if t not in gewinner], key="verlierer_sel")

        if st.button("💾  Ergebnis speichern", key="btn_speichern"):
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
                st.session_state.ergebnis_gespeichert = True

        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get("ergebnis_gespeichert"):
            st.markdown("<p style='text-align:center; font-weight:600;'>Nächstes Spiel?</p>", unsafe_allow_html=True)
            if st.button("✅  Ja, weiter", key="btn_naechstes_ja"):
                st.session_state.geber_index = (st.session_state.geber_index + 1) % len(teilnehmer)
                st.session_state.runde_nr += 1
                st.session_state.phase = "spiel_laeuft"
                st.session_state.ergebnis_gespeichert = False
                st.rerun()
            if st.button("❌  Nein, Abend beenden", key="btn_naechstes_nein"):
                st.session_state.ergebnis_gespeichert = False
                go_to("home", reset_game=True)
                st.rerun()

elif st.session_state.page == "statistik":
    show_back_button()
    st.markdown("<h2>📊 Statistik</h2>", unsafe_allow_html=True)

    tab_rang, tab_verlauf = st.tabs(["🏆 Rangliste", "📈 Verlauf"])
    data = load_ergebnisse()

    with tab_rang:
        if data:
            rows = [{"Spieler": r["spieler"]["name"], "Punkte": r["punkte"],
                     "Spielart": r["spiel"]["spielabend"]["spielart"], "Datum": r["spiel"]["spielabend"]["datum"]} for r in data]
            df = pd.DataFrame(rows)
            filter_art = st.radio("Filter", ["Alle", "Doppelkopf", "Skat"], horizontal=True, label_visibility="collapsed")
            if filter_art != "Alle":
                df = df[df["Spielart"] == filter_art]
            rangliste = df.groupby("Spieler")["Punkte"].agg(["sum", "count", "mean"]).reset_index()
            rangliste.columns = ["Spieler", "Punkte", "Runden", "Ø/Runde"]
            rangliste = rangliste.sort_values("Punkte", ascending=False)
            rangliste["Ø/Runde"] = rangliste["Ø/Runde"].round(1)
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            st.dataframe(rangliste, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
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
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            st.line_chart(pivot)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Noch keine Daten für Verlauf vorhanden.")

elif st.session_state.page == "spieler":
    show_back_button()
    st.markdown("<h2>👥 Spieler verwalten</h2>", unsafe_allow_html=True)

    st.markdown('<div class="card-box">', unsafe_allow_html=True)
    neuer_name = st.text_input("Neuen Spieler hinzufügen", label_visibility="collapsed", placeholder="Name eingeben...")
    if st.button("➕  Spieler hinzufügen", key="btn_add_spieler"):
        if neuer_name.strip():
            add_spieler(neuer_name.strip())
            st.success(f"{neuer_name} hinzugefügt!")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    spieler_df = load_spieler()
    if not spieler_df.empty:
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        st.dataframe(spieler_df[["name"]], use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

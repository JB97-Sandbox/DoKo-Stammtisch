import streamlit as st
import pandas as pd
import base64
from datetime import date
from supabase import create_client, Client

st.set_page_config(page_title="Stammtisch Punkte", page_icon="\U0001F0CF", layout="centered")

ICON_OPTIONS = ["\U0001F464","\U0001F600","\U0001F60E","\U0001F913","\U0001F975",
                "\U0001F921","\U0001F47B","\U0001F916","\U0001F42F","\U0001F43A",
                "\U0001F984","\U0001F989","\U0001F995","\U0001F47D","\U0001F480",
                "\U0001F3B2","\U0001F0CF","\u2694\uFE0F","\U0001F37A","\U0001F355",
                "\U0001F525","\u26A1","\U0001F480","\U0001F3AF"]

@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_client()

def load_spieler():
    res = supabase.table("spieler").select("*").order("name").execute()
    df = pd.DataFrame(res.data)
    if not df.empty and "icon" not in df.columns:
        df["icon"] = "\U0001F464"
    if not df.empty:
        df["icon"] = df["icon"].fillna("\U0001F464")
    return df

def load_spielabende():
    res = supabase.table("spielabend").select("*").order("datum", desc=True).execute()
    return pd.DataFrame(res.data)

def load_ergebnisse():
    res = supabase.table("ergebnis").select("*, spiel(*, spielabend(*)), spieler(*)").execute()
    return res.data

def add_spieler(name: str, icon: str = "\U0001F464"):
    supabase.table("spieler").insert({"name": name, "icon": icon}).execute()

def update_spieler_icon(spieler_id: int, icon: str):
    supabase.table("spieler").update({"icon": icon}).eq("id", spieler_id).execute()

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
        st.markdown("<h1 style='text-align:center;'>\U0001F0CF Stammtisch</h1>", unsafe_allow_html=True)
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
if "icon_edit_id" not in st.session_state:
    st.session_state.icon_edit_id = None

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

/* Spieler-Icon Buttons */
.player-tile button {{
    width: 100% !important;
    min-height: 72px !important;
    font-size: 34px !important;
    padding: 4px !important;
    border-radius: 18px !important;
    background: rgba(255,255,255,0.85) !important;
    color: #333 !important;
    border: 3px solid transparent !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15) !important;
    margin-bottom: 0.2rem !important;
}}
.player-tile.selected button {{
    border: 3px solid #E23636 !important;
    background: rgba(255,235,235,0.95) !important;
}}
.player-name {{
    text-align: center;
    font-size: 13px;
    font-weight: 600;
    color: #3A2E1F;
    margin-top: -4px;
    margin-bottom: 10px;
}}
</style>
""", unsafe_allow_html=True)

def show_back_button(label="\u2b05\ufe0f Zur\u00fcck", reset_game=False):
    if st.button(label, key=f"back_{st.session_state.page}"):
        go_to("home", reset_game=reset_game)
        st.rerun()

def player_grid_selector(spieler_df, session_key, cols_per_row=4):
    """Zeigt Spieler als Icon-Kacheln in Reihen zu 'cols_per_row' an. Klick toggelt Auswahl."""
    if session_key not in st.session_state:
        st.session_state[session_key] = []

    names = spieler_df["name"].tolist()
    icons = dict(zip(spieler_df["name"], spieler_df["icon"]))

    for row_start in range(0, len(names), cols_per_row):
        row_names = names[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for i, name in enumerate(row_names):
            with cols[i]:
                selected = name in st.session_state[session_key]
                css_class = "player-tile selected" if selected else "player-tile"
                st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                if st.button(icons.get(name, "\U0001F464"), key=f"{session_key}_{name}"):
                    if selected:
                        st.session_state[session_key].remove(name)
                    else:
                        st.session_state[session_key].append(name)
                    st.rerun()
                st.markdown(f'</div><p class="player-name">{"\u2705 " if selected else ""}{name}</p>', unsafe_allow_html=True)

    return st.session_state[session_key]

# =========================================================
# STARTSEITE
# =========================================================
if st.session_state.page == "home":
    st.markdown("<h1>\U0001F0CF Stammtisch</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#555; margin-bottom:1.5rem;'>Punkte-Tracker f\u00fcr Doppelkopf & Skat</p>", unsafe_allow_html=True)

    if st.button("\U0001F3AE  Neues Spiel", key="btn_neues_spiel"):
        go_to("neues_spiel", reset_game=True)
        st.rerun()
    if st.button("\U0001F4CA  Statistik", key="btn_statistik"):
        go_to("statistik")
        st.rerun()
    if st.button("\U0001F465  Spieler verwalten", key="btn_spieler"):
        go_to("spieler")
        st.rerun()

# =========================================================
# SEITE: Neues Spiel (mehrstufiger Ablauf)
# =========================================================
elif st.session_state.page == "neues_spiel":

    if st.session_state.phase == "setup":
        show_back_button(reset_game=True)
        st.markdown("<h2>\U0001F3AE Neuer Spielabend</h2>", unsafe_allow_html=True)
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; font-weight:600;'>Was wird heute gespielt?</p>", unsafe_allow_html=True)
        if st.button("\U0001F0CF  Doppelkopf", key="btn_doko"):
            st.session_state.spielart = "Doppelkopf"
            st.session_state.phase = "teilnehmer"
            st.session_state.teilnehmer_auswahl = []
            st.rerun()
        if st.button("\U0001F0A0  Skat", key="btn_skat"):
            st.session_state.spielart = "Skat"
            st.session_state.phase = "teilnehmer"
            st.session_state.teilnehmer_auswahl = []
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
            st.markdown("<p style='font-weight:600; text-align:center;'>Wer spielt mit?</p>", unsafe_allow_html=True)
            st.caption("Tippe auf die Spieler in der Reihenfolge, wie ihr sitzt (im Uhrzeigersinn).")

            teilnehmer = player_grid_selector(spieler_df, "teilnehmer_auswahl", cols_per_row=4)
            st.session_state.teilnehmer = teilnehmer

            ort = st.text_input("Ort (optional)", "")

            if len(teilnehmer) >= 3:
                if st.button("\u25b6\ufe0f  Los geht's!", key="btn_los"):
                    import random
                    abend_id = add_spielabend(str(date.today()), ort, st.session_state.spielart)
                    st.session_state.abend_id = abend_id
                    st.session_state.geber_index = random.randint(0, len(teilnehmer) - 1)
                    st.session_state.runde_nr = 1
                    st.session_state.phase = "spiel_laeuft"
                    st.rerun()
            else:
                st.info("Bitte mindestens 3 Spieler ausw\u00e4hlen.")
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.phase == "spiel_laeuft":
        teilnehmer = st.session_state.teilnehmer
        geber = teilnehmer[st.session_state.geber_index]

        st.markdown(f"<h2>Runde {st.session_state.runde_nr}</h2>", unsafe_allow_html=True)
        st.markdown('<div class="card-box" style="text-align:center;">', unsafe_allow_html=True)
        st.markdown(f'<span class="geber-badge">\U0001F3B4 Geber: {geber}</span>', unsafe_allow_html=True)
        st.markdown(f"<p style='color:#555;'>Teilnehmer: {', '.join(teilnehmer)}</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("\u2705  Spiel vorbei", key="btn_spiel_vorbei"):
            st.session_state.phase = "spiel_auswertung"
            st.rerun()
        if st.button("\U0001F3C1  Abend vorbei", key="btn_abend_vorbei"):
            go_to("home", reset_game=True)
            st.rerun()

    elif st.session_state.phase == "spiel_auswertung":
        teilnehmer = st.session_state.teilnehmer
        geber = teilnehmer[st.session_state.geber_index]

        st.markdown(f"<h2>Auswertung Runde {st.session_state.runde_nr}</h2>", unsafe_allow_html=True)
        st.markdown('<div class="card-box">', unsafe_allow_html=True)

        punktwert = st.number_input("Punktwert des Spiels", min_value=0, value=0, step=1)

        spieler_df_aw = load_spieler()
        icons_aw = dict(zip(spieler_df_aw["name"], spieler_df_aw["icon"]))

        if "gewinner_auswahl" not in st.session_state:
            st.session_state.gewinner_auswahl = []
        if "verlierer_auswahl" not in st.session_state:
            st.session_state.verlierer_auswahl = []

        st.markdown("<p style='font-weight:600; text-align:center; margin-top:0.5rem;'>🏆 Wer hat gewonnen?</p>", unsafe_allow_html=True)
        cols_per_row = 4
        for row_start in range(0, len(teilnehmer), cols_per_row):
            row_names = teilnehmer[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for i, name in enumerate(row_names):
                with cols[i]:
                    selected = name in st.session_state.gewinner_auswahl
                    css_class = "player-tile selected" if selected else "player-tile"
                    st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                    if st.button(icons_aw.get(name, "👤"), key=f"gew_{name}"):
                        if selected:
                            st.session_state.gewinner_auswahl.remove(name)
                        else:
                            st.session_state.gewinner_auswahl.append(name)
                            if name in st.session_state.verlierer_auswahl:
                                st.session_state.verlierer_auswahl.remove(name)
                        st.rerun()
                    st.markdown(f'</div><p class="player-name">{"✅ " if selected else ""}{name}</p>', unsafe_allow_html=True)
        gewinner = st.session_state.gewinner_auswahl

        st.markdown("<p style='font-weight:600; text-align:center; margin-top:1rem;'>😔 Wer hat verloren?</p>", unsafe_allow_html=True)
        verlierer_optionen = [t for t in teilnehmer if t not in gewinner]
        for row_start in range(0, len(verlierer_optionen), cols_per_row):
            row_names = verlierer_optionen[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for i, name in enumerate(row_names):
                with cols[i]:
                    selected = name in st.session_state.verlierer_auswahl
                    css_class = "player-tile selected" if selected else "player-tile"
                    st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                    if st.button(icons_aw.get(name, "👤"), key=f"verl_{name}"):
                        if selected:
                            st.session_state.verlierer_auswahl.remove(name)
                        else:
                            st.session_state.verlierer_auswahl.append(name)
                        st.rerun()
                    st.markdown(f'</div><p class="player-name">{"✅ " if selected else ""}{name}</p>', unsafe_allow_html=True)
        verlierer = [t for t in st.session_state.verlierer_auswahl if t in verlierer_optionen]

        if st.button("\U0001F4BE  Ergebnis speichern", key="btn_speichern"):
            if not gewinner or not verlierer:
                st.error("Bitte mindestens einen Gewinner und einen Verlierer ausw\u00e4hlen.")
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
                st.session_state.gewinner_auswahl = []
                st.session_state.verlierer_auswahl = []

        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get("ergebnis_gespeichert"):
            st.markdown("<p style='text-align:center; font-weight:600;'>N\u00e4chstes Spiel?</p>", unsafe_allow_html=True)
            if st.button("\u2705  Ja, weiter", key="btn_naechstes_ja"):
                st.session_state.geber_index = (st.session_state.geber_index + 1) % len(teilnehmer)
                st.session_state.runde_nr += 1
                st.session_state.phase = "spiel_laeuft"
                st.session_state.ergebnis_gespeichert = False
                st.session_state.gewinner_auswahl = []
                st.session_state.verlierer_auswahl = []
                st.rerun()
            if st.button("\u274c  Nein, Abend beenden", key="btn_naechstes_nein"):
                st.session_state.ergebnis_gespeichert = False
                st.session_state.gewinner_auswahl = []
                st.session_state.verlierer_auswahl = []
                go_to("home", reset_game=True)
                st.rerun()

# =========================================================
# SEITE: Statistik
# =========================================================
elif st.session_state.page == "statistik":
    show_back_button()
    st.markdown("<h2>\U0001F4CA Statistik</h2>", unsafe_allow_html=True)

    tab_rang, tab_verlauf = st.tabs(["\U0001F3C6 Rangliste", "\U0001F4C8 Verlauf"])
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
            rangliste.columns = ["Spieler", "Punkte", "Runden", "\u00d8/Runde"]
            rangliste = rangliste.sort_values("Punkte", ascending=False)
            rangliste["\u00d8/Runde"] = rangliste["\u00d8/Runde"].round(1)
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
            st.info("Noch keine Daten f\u00fcr Verlauf vorhanden.")

# =========================================================
# SEITE: Spieler verwalten
# =========================================================
elif st.session_state.page == "spieler":
    show_back_button()
    st.markdown("<h2>\U0001F465 Spieler verwalten</h2>", unsafe_allow_html=True)

    st.markdown('<div class="card-box">', unsafe_allow_html=True)
    neuer_name = st.text_input("Neuen Spieler hinzuf\u00fcgen", label_visibility="collapsed", placeholder="Name eingeben...")
    if st.button("\u2795  Spieler hinzuf\u00fcgen", key="btn_add_spieler"):
        if neuer_name.strip():
            add_spieler(neuer_name.strip())
            st.success(f"{neuer_name} hinzugef\u00fcgt!")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    spieler_df = load_spieler()
    if not spieler_df.empty:
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        st.markdown("<p style='font-weight:600; text-align:center;'>Icon antippen, um es zu \u00e4ndern</p>", unsafe_allow_html=True)

        names = spieler_df["name"].tolist()
        ids = dict(zip(spieler_df["name"], spieler_df["id"]))
        icons = dict(zip(spieler_df["name"], spieler_df["icon"]))
        cols_per_row = 4

        for row_start in range(0, len(names), cols_per_row):
            row_names = names[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for i, name in enumerate(row_names):
                with cols[i]:
                    if st.button(icons.get(name, "\U0001F464"), key=f"iconbtn_{name}"):
                        st.session_state.icon_edit_id = ids[name]
                        st.rerun()
                    st.markdown(f"<p class='player-name'>{name}</p>", unsafe_allow_html=True)

        if st.session_state.icon_edit_id is not None:
            edit_name = [n for n, i in ids.items() if i == st.session_state.icon_edit_id][0]
            st.markdown(f"<p style='text-align:center; font-weight:600; margin-top:1rem;'>Neues Icon f\u00fcr {edit_name} w\u00e4hlen:</p>", unsafe_allow_html=True)
            icon_cols = st.columns(6)
            for idx, opt in enumerate(ICON_OPTIONS):
                with icon_cols[idx % 6]:
                    if st.button(opt, key=f"iconopt_{idx}"):
                        update_spieler_icon(st.session_state.icon_edit_id, opt)
                        st.session_state.icon_edit_id = None
                        st.rerun()
            if st.button("Abbrechen", key="cancel_icon_edit"):
                st.session_state.icon_edit_id = None
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

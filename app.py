import streamlit as st
import pandas as pd
import base64
from datetime import date
from supabase import create_client, Client

st.set_page_config(page_title="Stammtisch Punkte", page_icon="\U0001F0CF", layout="centered")

QUICK_PUNKTWERTE = [1, 2, 3, 4, 5, 10]

@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_client()

def load_spieler():
    res = supabase.table("spieler").select("*").execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df = df.sort_values(by="name", key=lambda col: col.str.casefold()).reset_index(drop=True)
    return df

def load_ergebnisse():
    res = supabase.table("ergebnis").select("*, spiel(*, spielabend(*)), spieler(*)").execute()
    return res.data

def load_ergebnisse_fuer_abend(abend_id: int):
    res = supabase.table("ergebnis").select("*, spiel!inner(*), spieler(*)").eq("spiel.spielabend_id", abend_id).execute()
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

def delete_spiel(spiel_id: int):
    supabase.table("ergebnis").delete().eq("spiel_id", spiel_id).execute()
    supabase.table("spiel").delete().eq("id", spiel_id).execute()

def save_live_state():
    if st.session_state.page != "neues_spiel" or st.session_state.phase == "setup":
        payload = None
    else:
        payload = {
            "page": st.session_state.page,
            "phase": st.session_state.phase,
            "abend_id": st.session_state.abend_id,
            "spielart": st.session_state.spielart,
            "teilnehmer": st.session_state.teilnehmer,
            "geber_index": st.session_state.geber_index,
            "runde_nr": st.session_state.runde_nr,
            "letztes_spiel_id": st.session_state.letztes_spiel_id,
            "letzte_zusammenfassung": st.session_state.letzte_zusammenfassung,
            "gespeicherte_runden": list(st.session_state.gespeicherte_runden),
        }
    try:
        supabase.table("live_state").update({"data": payload}).eq("id", 1).execute()
    except Exception:
        pass

def load_live_state():
    try:
        res = supabase.table("live_state").select("*").eq("id", 1).execute()
        if res.data:
            return res.data[0].get("data")
    except Exception:
        pass
    return None

def clear_live_state():
    try:
        supabase.table("live_state").update({"data": None}).eq("id", 1).execute()
    except Exception:
        pass

def reset_alle_spieldaten():
    supabase.table("ergebnis").delete().neq("id", -1).execute()
    supabase.table("spiel").delete().neq("id", -1).execute()
    supabase.table("spielabend").delete().neq("id", -1).execute()
    clear_live_state()

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

defaults = {
    "page": "home", "abend_id": None, "spielart": None, "teilnehmer": [],
    "geber_index": None, "runde_nr": 1, "phase": "setup",
    "letztes_spiel_id": None, "letzte_zusammenfassung": None,
    "live_state_restored": False, "live_state_dismissed": False,
    "gespeicherte_runden": set(), "abend_beendet_ansicht": False,
    "gewinner_auswahl": [], "verlierer_auswahl": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if not st.session_state.live_state_restored and not st.session_state.live_state_dismissed:
    _restored = load_live_state()
    if _restored and st.session_state.page == "home":
        st.session_state.pending_restore = _restored
    st.session_state.live_state_restored = True

def go_to(page_name: str, reset_game: bool = False):
    st.session_state.page = page_name
    if reset_game:
        st.session_state.abend_id = None
        st.session_state.spielart = None
        st.session_state.teilnehmer = []
        st.session_state.geber_index = None
        st.session_state.runde_nr = 1
        st.session_state.phase = "setup"
        st.session_state.letztes_spiel_id = None
        st.session_state.letzte_zusammenfassung = None
        st.session_state.gespeicherte_runden = set()
        st.session_state.abend_beendet_ansicht = False
        clear_live_state()

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
div.stButton > button:disabled {{
    opacity: 0.5;
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
h1 {{
    font-size: 34px !important;
    margin-bottom: 0.1rem !important;
}}
h2 {{
    font-size: 24px !important;
    margin-top: 0.4rem !important;
    margin-bottom: 0.8rem !important;
}}

hr {{
    margin: 1.2rem 0 !important;
    border-color: rgba(0,0,0,0.08) !important;
}}

[data-testid="stCaptionContainer"] {{
    text-align: center !important;
}}

.stTextInput input, .stNumberInput input {{
    border-radius: 12px !important;
    min-height: 48px !important;
    font-size: 16px !important;
}}

.stRadio label, .stSelectbox label {{
    font-weight: 600 !important;
}}

div[data-testid="stAlert"] {{
    border-radius: 14px !important;
}}

.stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 12px 12px 0 0 !important;
    font-weight: 700 !important;
}}

[data-testid="stDataFrame"] {{
    border-radius: 12px !important;
    overflow: hidden !important;
}}

::-webkit-scrollbar {{
    width: 6px;
}}

div[data-testid="stHorizontalBlock"] {{
    gap: 0.4rem !important;
}}

/* Spieler-Namen-Buttons (Auswahl statt Emoji-Icons) */
div[class*="st-key-namebtn_"] button {{
    width: 100% !important;
    min-height: 50px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    color: #222 !important;
    background: #ffffff !important;
    border: 2px solid rgba(0,0,0,0.12) !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08) !important;
    margin: 0 !important;
}}
div[class*="st-key-namebtnsel_"] button {{
    width: 100% !important;
    min-height: 50px !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    background: linear-gradient(135deg, #FF6B4A 0%, #E23636 100%) !important;
    border: 2px solid #E23636 !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 6px rgba(226,54,54,0.35) !important;
    margin: 0 !important;
}}

.summary-box {{
    background: rgba(255,255,255,0.95);
    border-radius: 16px;
    padding: 16px;
    margin: 0.8rem 0;
    border: 2px dashed #F4A24A;
}}

.abend-stand-row {{
    display: flex;
    justify-content: space-between;
    padding: 4px 2px;
    font-size: 15px;
    border-bottom: 1px solid rgba(0,0,0,0.08);
}}
</style>
""", unsafe_allow_html=True)

def show_back_button(label="\u2b05\ufe0f Zur\u00fcck", reset_game=False):
    if st.button(label, key=f"back_{st.session_state.page}"):
        go_to("home", reset_game=reset_game)
        st.rerun()

def player_name_selector(names, session_key, cols_per_row=3):
    """Zeigt Spielernamen als einfache Auswahl-Buttons (schwarz auf weiss) in Reihen.
    Klick toggelt Auswahl. Zeigt Auswahlreihenfolge als Nummer im Button-Text."""
    if session_key not in st.session_state:
        st.session_state[session_key] = []

    order = {name: idx + 1 for idx, name in enumerate(st.session_state[session_key])}

    for row_start in range(0, len(names), cols_per_row):
        row_names = names[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for i, name in enumerate(row_names):
            with cols[i]:
                selected = name in st.session_state[session_key]
                key_prefix = "namebtnsel" if selected else "namebtn"
                label = f"{order[name]}. {name}" if selected else name
                with st.container(key=f"{key_prefix}_{session_key}_{name}"):
                    if st.button(label, key=f"btn_{session_key}_{name}"):
                        if selected:
                            st.session_state[session_key].remove(name)
                        else:
                            st.session_state[session_key].append(name)
                        st.rerun()

    if st.session_state[session_key]:
        reihenfolge_text = " \u2192 ".join(
            f"{idx+1}. {n}" for idx, n in enumerate(st.session_state[session_key])
        )
        st.caption(f"\U0001F501 Sitzreihenfolge: {reihenfolge_text}")

    return st.session_state[session_key]

def zeige_abend_zwischenstand(abend_id, teilnehmer):
    if not abend_id:
        return
    daten = load_ergebnisse_fuer_abend(abend_id)
    if not daten:
        st.caption("Noch keine Ergebnisse in diesem Abend.")
        return
    rows = [{"Spieler": r["spieler"]["name"], "Punkte": r["punkte"]} for r in daten]
    df = pd.DataFrame(rows)
    stand = df.groupby("Spieler")["Punkte"].sum().reindex(teilnehmer).fillna(0).astype(int)
    stand = stand.sort_values(ascending=False)
    st.markdown('<div class="summary-box">', unsafe_allow_html=True)
    st.markdown("<p style='font-weight:700; text-align:center; margin-bottom:6px;'>\U0001F4CB Aktueller Punktestand</p>", unsafe_allow_html=True)
    for name, punkte in stand.items():
        vorzeichen = "+" if punkte > 0 else ""
        farbe = "#2E7D32" if punkte > 0 else ("#C62828" if punkte < 0 else "#555")
        st.markdown(
            f'<div class="abend-stand-row"><span>{name}</span><span style="color:{farbe}; font-weight:700;">{vorzeichen}{punkte}</span></div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)
    return stand

# =========================================================
# STARTSEITE
# =========================================================
if st.session_state.page == "home":
    st.markdown("<h1>\U0001F0CF Stammtisch</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#777; margin-bottom:1.8rem; font-size:15px;'>Punkte-Tracker f\u00fcr Doppelkopf & Skat</p>", unsafe_allow_html=True)

    if st.session_state.get("pending_restore"):
        rs = st.session_state.pending_restore
        st.markdown('<div class="summary-box">', unsafe_allow_html=True)
        st.markdown(f"\u26A0\uFE0F **Es gibt einen unterbrochenen Spielabend** ({rs.get('spielart','')}, Runde {rs.get('runde_nr','?')}).")
        st.caption("Teilnehmer: " + ", ".join(rs.get("teilnehmer", [])))
        col_r, col_d = st.columns(2)
        with col_r:
            if st.button("\u25b6\ufe0f  Fortsetzen", key="btn_restore_game"):
                st.session_state.page = rs.get("page", "neues_spiel")
                st.session_state.phase = rs.get("phase", "spiel_laeuft")
                st.session_state.abend_id = rs.get("abend_id")
                st.session_state.spielart = rs.get("spielart")
                st.session_state.teilnehmer = rs.get("teilnehmer", [])
                st.session_state.geber_index = rs.get("geber_index")
                st.session_state.runde_nr = rs.get("runde_nr", 1)
                st.session_state.letztes_spiel_id = rs.get("letztes_spiel_id")
                st.session_state.letzte_zusammenfassung = rs.get("letzte_zusammenfassung")
                st.session_state.gespeicherte_runden = set(rs.get("gespeicherte_runden", []))
                st.session_state.pending_restore = None
                st.session_state.live_state_dismissed = True
                st.rerun()
        with col_d:
            if st.button("\U0001F5D1\uFE0F  Verwerfen", key="btn_discard_game"):
                clear_live_state()
                st.session_state.pending_restore = None
                st.session_state.live_state_dismissed = True
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

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

            teilnehmer = player_name_selector(spieler_df["name"].tolist(), "teilnehmer_auswahl", cols_per_row=3)
            st.session_state.teilnehmer = teilnehmer

            ort = st.text_input("Ort (optional)", "")

            if len(teilnehmer) >= 3:
                if st.button("\u25b6\ufe0f  Los geht's!", key="btn_los"):
                    import random
                    with st.spinner("Spielabend wird angelegt..."):
                        abend_id = add_spielabend(str(date.today()), ort, st.session_state.spielart)
                    st.session_state.abend_id = abend_id
                    st.session_state.geber_index = random.randint(0, len(teilnehmer) - 1)
                    st.session_state.runde_nr = 1
                    st.session_state.phase = "spiel_laeuft"
                    save_live_state()
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
            if "punktwert_manual" in st.session_state:
                del st.session_state["punktwert_manual"]
            save_live_state()
            st.rerun()

        if st.session_state.letztes_spiel_id is not None and st.session_state.letzte_zusammenfassung:
            st.markdown('<div class="summary-box">', unsafe_allow_html=True)
            st.caption(f"\u2139\ufe0f Zuletzt gespeichert: {st.session_state.letzte_zusammenfassung}")
            if st.button("\U0001F5D1\uFE0F  Letzte Runde l\u00f6schen", key="delete_last_round"):
                with st.spinner("L\u00f6sche letzte Runde..."):
                    delete_spiel(st.session_state.letztes_spiel_id)
                st.session_state.gespeicherte_runden.discard(st.session_state.runde_nr - 1)
                st.session_state.letztes_spiel_id = None
                st.session_state.letzte_zusammenfassung = None
                st.session_state.runde_nr = max(1, st.session_state.runde_nr - 1)
                st.session_state.geber_index = (st.session_state.geber_index - 1) % len(teilnehmer)
                save_live_state()
                st.success("Letzte Runde gel\u00f6scht.")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        zeige_abend_zwischenstand(st.session_state.abend_id, teilnehmer)

        if st.button("\U0001F3C1  Abend vorbei", key="btn_abend_vorbei"):
            st.session_state.abend_beendet_ansicht = True
            st.rerun()

    elif st.session_state.phase == "spiel_auswertung":
        teilnehmer = st.session_state.teilnehmer
        geber = teilnehmer[st.session_state.geber_index]

        bereits_gespeichert = st.session_state.runde_nr in st.session_state.gespeicherte_runden

        st.markdown(f"<h2>Auswertung Runde {st.session_state.runde_nr}</h2>", unsafe_allow_html=True)
        st.markdown('<div class="card-box">', unsafe_allow_html=True)

        if "punktwert_manual" not in st.session_state:
            st.session_state.punktwert_manual = 0

        st.markdown("<p style='font-weight:600; text-align:center;'>Punktwert des Spiels</p>", unsafe_allow_html=True)
        quick_cols = st.columns(len(QUICK_PUNKTWERTE))
        for i, val in enumerate(QUICK_PUNKTWERTE):
            with quick_cols[i]:
                active = st.session_state.punktwert_manual == val
                key_prefix = "quickptactive" if active else "quickpt"
                with st.container(key=f"{key_prefix}_{val}"):
                    if st.button(str(val), key=f"quickbtn_{val}", disabled=bereits_gespeichert):
                        st.session_state.punktwert_manual = val
                        st.rerun()

        punktwert = st.number_input("Oder eigenen Wert eingeben", min_value=0, step=1,
                                     key="punktwert_manual", disabled=bereits_gespeichert)

        st.markdown("<p style='font-weight:600; text-align:center; margin-top:0.5rem;'>\U0001F3C6 Wer hat gewonnen?</p>", unsafe_allow_html=True)
        gewinner = player_name_selector(teilnehmer, "gewinner_auswahl", cols_per_row=3) if not bereits_gespeichert else st.session_state.gewinner_auswahl
        if bereits_gespeichert:
            st.write(", ".join(gewinner) if gewinner else "-")

        for name in list(st.session_state.verlierer_auswahl):
            if name in st.session_state.gewinner_auswahl:
                st.session_state.verlierer_auswahl.remove(name)

        st.markdown("<p style='font-weight:600; text-align:center; margin-top:1rem;'>\U0001F614 Wer hat verloren?</p>", unsafe_allow_html=True)
        verlierer_optionen = [t for t in teilnehmer if t not in gewinner]
        if not bereits_gespeichert:
            verlierer = player_name_selector(verlierer_optionen, "verlierer_auswahl", cols_per_row=3)
            verlierer = [t for t in verlierer if t in verlierer_optionen]
        else:
            verlierer = st.session_state.verlierer_auswahl
            st.write(", ".join(verlierer) if verlierer else "-")

        if not bereits_gespeichert and (gewinner or verlierer):
            gew_text = ", ".join(f"{n} +{int(punktwert)}" for n in gewinner) if gewinner else "-"
            verl_text = ", ".join(f"{n} -{int(punktwert)}" for n in verlierer) if verlierer else "-"
            st.markdown('<div class="summary-box">', unsafe_allow_html=True)
            st.markdown(f"**Vorschau:** \U0001F3C6 {gew_text} &nbsp;|&nbsp; \U0001F614 {verl_text}")
            st.markdown('</div>', unsafe_allow_html=True)

        col_save, col_back = st.columns(2)
        with col_save:
            if st.button("\U0001F4BE  Speichern", key="btn_speichern", disabled=bereits_gespeichert):
                if not gewinner or not verlierer:
                    st.error("Bitte mindestens einen Gewinner und einen Verlierer ausw\u00e4hlen.")
                else:
                    gew_text = ", ".join(f"{n} +{int(punktwert)}" for n in gewinner)
                    verl_text = ", ".join(f"{n} -{int(punktwert)}" for n in verlierer)
                    with st.spinner("Speichere Ergebnis..."):
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
                    st.session_state.letztes_spiel_id = spiel_id
                    st.session_state.letzte_zusammenfassung = f"Runde {st.session_state.runde_nr}: \U0001F3C6 {gew_text} | \U0001F614 {verl_text}"
                    st.session_state.gespeicherte_runden.add(st.session_state.runde_nr)
                    save_live_state()
                    st.success("Ergebnis gespeichert!")
                    st.rerun()
        with col_back:
            if st.button("\u21a9\ufe0f  Zur\u00fcck", key="btn_zurueck_zu_spiel", disabled=bereits_gespeichert):
                st.session_state.phase = "spiel_laeuft"
                st.session_state.gewinner_auswahl = []
                st.session_state.verlierer_auswahl = []
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        zeige_abend_zwischenstand(st.session_state.abend_id, teilnehmer)

        if bereits_gespeichert:
            st.markdown("<p style='text-align:center; font-weight:600;'>N\u00e4chstes Spiel?</p>", unsafe_allow_html=True)
            col_ja, col_nein = st.columns(2)
            with col_ja:
                if st.button("\u2705  Ja, weiter", key="btn_naechstes_ja"):
                    st.session_state.geber_index = (st.session_state.geber_index + 1) % len(teilnehmer)
                    st.session_state.runde_nr += 1
                    st.session_state.phase = "spiel_laeuft"
                    st.session_state.gewinner_auswahl = []
                    st.session_state.verlierer_auswahl = []
                    if "punktwert_manual" in st.session_state:
                        del st.session_state["punktwert_manual"]
                    save_live_state()
                    st.rerun()
            with col_nein:
                if st.button("\U0001F3C1  Abend beenden", key="btn_naechstes_nein"):
                    st.session_state.gewinner_auswahl = []
                    st.session_state.verlierer_auswahl = []
                    st.session_state.abend_beendet_ansicht = True
                    st.rerun()

    if st.session_state.abend_beendet_ansicht:
        st.markdown("<h2>\U0001F3C1 Abend beendet!</h2>", unsafe_allow_html=True)
        stand = zeige_abend_zwischenstand(st.session_state.abend_id, st.session_state.teilnehmer)
        if stand is not None and len(stand) > 0 and stand.max() > 0:
            sieger = stand.idxmax()
            st.markdown(f"<p style='text-align:center; font-size:20px; font-weight:800; color:#3A2E1F;'>\U0001F3C6 Gewinner des Abends: {sieger}!</p>", unsafe_allow_html=True)
            st.balloons()
        if st.button("\u2b05\ufe0f  Zur\u00fcck zur Startseite", key="btn_abend_beendet_home"):
            go_to("home", reset_game=True)
            st.rerun()

# =========================================================
# SEITE: Statistik
# =========================================================
elif st.session_state.page == "statistik":
    show_back_button()
    st.markdown("<h2>\U0001F4CA Statistik</h2>", unsafe_allow_html=True)

    tab_rang, tab_verlauf = st.tabs(["\U0001F3C6 Rangliste", "\U0001F4C8 Verlauf"])
    with st.spinner("Lade Daten..."):
        data = load_ergebnisse()

    with tab_rang:
        if data:
            rows = [{"Spieler": r["spieler"]["name"], "Punkte": r["punkte"],
                     "Spielart": r["spiel"]["spielabend"]["spielart"],
                     "Datum": r["spiel"]["spielabend"]["datum"]} for r in data]
            df = pd.DataFrame(rows)
            df["Datum"] = pd.to_datetime(df["Datum"])

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filter_art = st.radio("Spielart", ["Alle", "Doppelkopf", "Skat"], horizontal=True)
            with col_f2:
                zeitraum = st.selectbox("Zeitraum", ["Gesamt", "Dieses Jahr", "Dieser Monat"])

            gefiltert = df.copy()
            if filter_art != "Alle":
                gefiltert = gefiltert[gefiltert["Spielart"] == filter_art]

            heute = pd.Timestamp(date.today())
            if zeitraum == "Dieses Jahr":
                gefiltert = gefiltert[gefiltert["Datum"].dt.year == heute.year]
            elif zeitraum == "Dieser Monat":
                gefiltert = gefiltert[(gefiltert["Datum"].dt.year == heute.year) & (gefiltert["Datum"].dt.month == heute.month)]

            if gefiltert.empty:
                st.info("Keine Ergebnisse f\u00fcr diesen Zeitraum.")
            else:
                rangliste = gefiltert.groupby("Spieler")["Punkte"].agg(["sum", "count", "mean"]).reset_index()
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
            with st.spinner("F\u00fcge Spieler hinzu..."):
                add_spieler(neuer_name.strip())
            st.success(f"{neuer_name} hinzugef\u00fcgt!")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    spieler_df = load_spieler()
    if not spieler_df.empty:
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        st.markdown("<p style='font-weight:600; text-align:center;'>Aktuelle Spielerliste</p>", unsafe_allow_html=True)
        names = spieler_df["name"].tolist()
        cols_per_row = 3
        for row_start in range(0, len(names), cols_per_row):
            row_names = names[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for i, name in enumerate(row_names):
                with cols[i]:
                    with st.container(key=f"namebtn_liste_{name}"):
                        st.button(name, key=f"nameonly_{name}", disabled=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("\u26A0\uFE0F Testdaten zur\u00fccksetzen"):
        st.caption("L\u00f6scht alle bisher gespeicherten Spielabende, Spiele und Ergebnisse unwiderruflich. Spieler bleiben erhalten.")
        reset_pw = st.text_input("Passwort zum Best\u00e4tigen", type="password", key="reset_pw_input")
        bestaetigung = st.checkbox("Ich bin sicher, dass ich alle Spieldaten l\u00f6schen m\u00f6chte", key="confirm_reset")
        pw_korrekt = reset_pw == "Stammtisch"
        if reset_pw and not pw_korrekt:
            st.error("Falsches Passwort.")
        if st.button("\U0001F5D1\uFE0F  Alle Spieldaten l\u00f6schen", key="btn_reset_data", disabled=not (bestaetigung and pw_korrekt)):
            with st.spinner("L\u00f6sche alle Spieldaten..."):
                reset_alle_spieldaten()
            if "confirm_reset" in st.session_state:
                del st.session_state["confirm_reset"]
            if "reset_pw_input" in st.session_state:
                del st.session_state["reset_pw_input"]
            st.success("Alle Spieldaten wurden gel\u00f6scht.")
            st.rerun()

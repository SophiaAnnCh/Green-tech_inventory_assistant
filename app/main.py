import sys
import os
from pathlib import Path

APP_DIR = Path(__file__).parent
ROOT_DIR = APP_DIR.parent
sys.path.insert(0, str(APP_DIR))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

import streamlit as st
import streamlit.components.v1
from datetime import datetime, timedelta

from inventory import (
    load_inventory, save_inventory,
    load_history, save_history,
    add_item, update_quantity, delete_item,
    search_and_filter, get_item,
    VALID_ORGS, VALID_TYPES,
)
from forecasting import forecast_item, forecast_all, simulate_days_forward, set_sim_date
from alerts import check_alerts, check_all_alerts, alert_badge_color, alert_emoji, AlertType, Severity
from insights import generate_insight, generate_daily_brief, fallback_insight, ORG_CONTEXT, suggest_suppliers, generate_cross_org_tip, get_cross_org_scenario

st.set_page_config(
    page_title="EcoTrack AI",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@400;600;700;800&display=swap');

/* ── Root tokens ── */
:root {
    --bg:        #0f1110;
    --surface:   #171c1a;
    --surface2:  #1e2422;
    --border:    #2a3330;
    --accent:    #4ade80;
    --accent2:   #86efac;
    --warn:      #fb923c;
    --danger:    #f87171;
    --muted:     #6b7c76;
    --text:      #e8ede9;
    --text2:     #a8b8b0;
    --mono:      'DM Mono', monospace;
    --display:   'Syne', sans-serif;
}

/* ── Global resets ── */
html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
}

[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] * { color: var(--text) !important; }

/* ── Typography ── */
h1, h2, h3 { font-family: var(--display) !important; letter-spacing: -0.02em; }
h1 { font-size: 2rem !important; font-weight: 800 !important; }
h2 { font-size: 1.25rem !important; font-weight: 700 !important; color: var(--text2) !important; }
h3 { font-size: 1rem !important; font-weight: 600 !important; }

/* ── Buttons ── */
.stButton > button {
    background: var(--surface2) !important;
    color: var(--accent) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.05em !important;
    padding: 0.4rem 1rem !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    border-color: var(--accent) !important;
    background: #1a2e22 !important;
}
.stButton > button[kind="primary"] {
    background: var(--accent) !important;
    color: #0f1110 !important;
    font-weight: 700 !important;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div,
.stDateInput > div > div > input {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 4px !important;
    font-family: var(--mono) !important;
}

.stSelectbox > div > div > div { color: var(--text) !important; }

/* ── Slider ── */
.stSlider > div > div > div > div { background: var(--accent) !important; }

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    padding: 1rem !important;
}
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 0.7rem !important; letter-spacing: 0.1em !important; text-transform: uppercase !important; }
[data-testid="stMetricValue"] { color: var(--text) !important; font-family: var(--display) !important; font-size: 1.6rem !important; }
[data-testid="stMetricDelta"] svg { display: none; }

/* ── Expander ── */
.streamlit-expanderHeader {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
}
.streamlit-expanderContent {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-top: none !important;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

/* ── Success / warning / error messages ── */
.stSuccess { background: #14291e !important; border: 1px solid var(--accent) !important; color: var(--accent) !important; }
.stWarning { background: #2a1a0a !important; border: 1px solid var(--warn) !important; color: var(--warn) !important; }
.stError   { background: #2a0f0f !important; border: 1px solid var(--danger) !important; color: var(--danger) !important; }
.stInfo    { background: var(--surface2) !important; border: 1px solid var(--border) !important; }

/* ── Custom cards (via markdown HTML) ── */
.et-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
    transition: border-color 0.15s ease;
}
.et-card:hover { border-color: var(--muted); }
.et-card.alert-high  { border-left: 3px solid #f87171; }
.et-card.alert-med   { border-left: 3px solid #fb923c; }
.et-card.alert-low   { border-left: 3px solid #60a5fa; }
.et-card.ok          { border-left: 3px solid #4ade80; }

.et-tag {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.15rem 0.5rem;
    border-radius: 2px;
    margin-right: 0.3rem;
}
.tag-perishable  { background: #1f2d1a; color: #86efac; border: 1px solid #2d4a24; }
.tag-consumable  { background: #1e2030; color: #93c5fd; border: 1px solid #2a3050; }
.tag-non_expiry  { background: #2a2010; color: #fcd34d; border: 1px solid #4a3510; }
.tag-cafe        { background: #2a1a10; color: #fdba74; border: 1px solid #4a2a15; }
.tag-nonprofit   { background: #1a1f2a; color: #a5b4fc; border: 1px solid #252d40; }
.tag-university_lab { background: #1f2a2a; color: #5eead4; border: 1px solid #253535; }

.et-mono { font-family: var(--mono); font-size: 0.82rem; color: var(--text2); }
.et-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); }
.et-value { font-family: var(--display); font-size: 1.1rem; font-weight: 700; color: var(--text); }

.ai-badge {
    display: inline-block;
    font-size: 0.6rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 0.1rem 0.4rem;
    border-radius: 2px;
    font-weight: 600;
    margin-left: 0.4rem;
    vertical-align: middle;
}
.ai-badge.llm      { background: #1a2e22; color: #4ade80; border: 1px solid #2a4a32; }
.ai-badge.fallback { background: #2a2010; color: #fcd34d; border: 1px solid #4a3510; }

.dev-mode-banner {
    background: #1a1500;
    border: 1px solid #4a3510;
    border-radius: 4px;
    padding: 0.5rem 1rem;
    color: #fcd34d;
    font-size: 0.78rem;
    margin-bottom: 1rem;
    letter-spacing: 0.03em;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer { display: none !important; }
/* Keep sidebar toggle and toolbar visible */
[data-testid="stToolbar"] { display: flex !important; }
[data-testid="collapsedControl"] { display: flex !important; }
</style>
""", unsafe_allow_html=True)


def init_state():
    if "inventory" not in st.session_state:
        st.session_state.inventory = load_inventory()
    if "history" not in st.session_state:
        st.session_state.history = load_history()
    if "sim_days" not in st.session_state:
        st.session_state.sim_days = 0
    if "sim_active" not in st.session_state:
        st.session_state.sim_active = False
    if "selected_item_id" not in st.session_state:
        st.session_state.selected_item_id = None
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"
    if "insight_cache" not in st.session_state:
        st.session_state.insight_cache = {}
    if "waste_events" not in st.session_state:
        st.session_state.waste_events = []
    if "sim_current_date" not in st.session_state:
        st.session_state.sim_current_date = None
    if "dev_mode" not in st.session_state:
        st.session_state.dev_mode = False
    if "org_filter" not in st.session_state:
        st.session_state.org_filter = "all"

init_state()

inv   = st.session_state.inventory
hist  = st.session_state.history

set_sim_date(st.session_state.get("sim_current_date"))


@st.cache_data(ttl=30, show_spinner=False)
def get_forecasts(inv_json: str, hist_json: str) -> dict:
    import json
    inventory = json.loads(inv_json)
    history   = json.loads(hist_json)
    return forecast_all(inventory, history)

import json as _json
forecasts  = get_forecasts(_json.dumps(inv), _json.dumps(hist))
all_alerts = check_all_alerts(inv, forecasts)



ORG_LABELS  = {"all": "All Orgs", "cafe": "☕ Café", "nonprofit": "🤝 Non-Profit", "university_lab": "🔬 University Lab"}
TYPE_LABELS = {"all": "All Types", "perishable": "Perishable", "consumable": "Consumable", "non_expiry": "Non-Expiry"}
ORG_ICONS   = {"cafe": "☕", "nonprofit": "🤝", "university_lab": "🔬"}

def sev_class(severity) -> str:
    return {"high": "alert-high", "medium": "alert-med", "low": "alert-low"}.get(str(severity), "ok")

def confidence_color(conf: str) -> str:
    return {"high": "#4ade80", "medium": "#fcd34d", "low": "#fb923c", "none": "#6b7280"}.get(conf, "#6b7280")

def fmt_qty(qty, unit) -> str:
    if qty == int(qty):
        return f"{int(qty)} {unit}"
    return f"{qty:.1f} {unit}"

def tag_html(label: str, css_class: str) -> str:
    return f'<span class="et-tag {css_class}">{label}</span>'

def reload_data():
    """Force a full reload from disk (after saves)."""
    st.session_state.inventory = load_inventory()
    st.session_state.history   = load_history()
    get_forecasts.clear()


with st.sidebar:
    st.markdown('<h1 style="font-family:\'Syne\',sans-serif;font-size:1.4rem;font-weight:800;color:#4ade80;margin-bottom:0">🌿 EcoTrack</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:#6b7c76;font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;margin-top:0">AI Inventory Assistant</p>', unsafe_allow_html=True)

    st.divider()

    # Navigation
    pages = {
        "dashboard":  "⬛  Dashboard",
        "inventory":  "📋  Inventory",
        "analytics":  "📊  Analytics",
        "add_item":   "＋  Add Item",
        "alerts":     f"🔔  Alerts ({sum(1 for a in all_alerts if a.severity in (Severity.HIGH, Severity.MEDIUM))})",
    }
    for key, label in pages.items():
        active = st.session_state.page == key
        if st.button(label, key=f"nav_{key}", use_container_width=True,
                     type="primary" if active else "secondary"):
            st.session_state.page = key
            st.rerun()

    st.divider()

    # ── Org filter ─────────────────────────────────────────────────────────────
    st.markdown('<p class="et-label">Organisation</p>', unsafe_allow_html=True)
    _org_options = {"all": "🌐 All Orgs", "cafe": "☕ Café",
                    "nonprofit": "🤝 Non-Profit", "university_lab": "🔬 University Lab"}
    selected_org = st.selectbox("org", options=list(_org_options.keys()),
        format_func=lambda x: _org_options[x], label_visibility="collapsed",
        key="org_selector",
        index=list(_org_options.keys()).index(st.session_state.org_filter))
    if selected_org != st.session_state.org_filter:
        st.session_state.org_filter = selected_org
        st.rerun()

    st.divider()

    # ── Mode toggle ────────────────────────────────────────────────────────────
    from datetime import datetime as _dt_sb
    _real_today = _dt_sb.today().strftime("%Y-%m-%d")
    _display_date = st.session_state.get("sim_current_date") or _real_today

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if st.button("📋 Live Mode",
                     type="primary" if not st.session_state.dev_mode else "secondary",
                     use_container_width=True):
            st.session_state.dev_mode = False
            st.rerun()
    with col_m2:
        if st.button("🧪 Dev Mode",
                     type="primary" if st.session_state.dev_mode else "secondary",
                     use_container_width=True):
            st.session_state.dev_mode = True
            st.rerun()

    _date_color = "#fcd34d" if st.session_state.sim_active else "#4ade80"
    _date_prefix = "⏩ Simulated" if st.session_state.sim_active else "📅 Date"
    st.markdown(
        f'<div style="background:var(--surface2);border:1px solid var(--border);border-radius:4px;'
        f'text-align:center;font-family:DM Mono,monospace;font-size:0.82rem;'
        f'color:{_date_color};padding:0.4rem 0.6rem;margin:0.3rem 0">'
        f'<span style="color:var(--muted);font-size:0.68rem;letter-spacing:0.1em;text-transform:uppercase">{_date_prefix}</span>'
        f'<br><strong>{_display_date}</strong></div>',
        unsafe_allow_html=True,
    )

    st.divider()

    if st.session_state.dev_mode:
        # ── Developer Mode controls ───────────────────────────────────────────
        st.markdown('<p class="et-label">Simulate Time Forward</p>', unsafe_allow_html=True)

        sim_days = st.slider(
            "Days to add", 1, 30, 5,
            key="sim_slider", label_visibility="collapsed",
        )

        trackable = [i for i in inv if i["type"] != "non_expiry"]
        with st.expander(f"Set usage overrides ({len(trackable)} items)", expanded=False):
            st.caption(
                f"Total units consumed over {sim_days} day(s). "
                "Leave at 0 to use historical average."
            )
            overrides = {}
            for item in trackable:
                fc_item  = forecasts.get(item["id"], {})
                avg      = fc_item.get("avg_daily_usage", 0)
                expected = round(avg * sim_days, 1)
                val = st.number_input(
                    f"{item['name']} ({item['unit']})",
                    min_value=0.0,
                    max_value=float(item["current_qty"]),
                    value=0.0,
                    step=0.5,
                    key=f"sim_override_{item['id']}",
                    help=f"Expected at avg usage: {expected} {item['unit']}",
                )
                if val > 0:
                    overrides[item["id"]] = val

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("▶ Apply", use_container_width=True):
                if sim_days > 0:
                    with st.spinner("Simulating..."):
                        from datetime import datetime as _dt, timedelta as _td
                        sim_start = st.session_state.sim_current_date or _dt.today().strftime("%Y-%m-%d")
                        new_inv, new_hist, waste_evts = simulate_days_forward(
                            inv, hist, sim_days,
                            overrides=overrides,
                            current_date=sim_start,
                        )
                        new_sim_date = (_dt.strptime(sim_start, "%Y-%m-%d") + _td(days=sim_days)).strftime("%Y-%m-%d")
                        st.session_state.inventory        = new_inv
                        st.session_state.history          = new_hist
                        st.session_state.sim_days        += sim_days
                        st.session_state.sim_active       = True
                        st.session_state.sim_current_date = new_sim_date
                        st.session_state.waste_events     = st.session_state.waste_events + waste_evts
                        set_sim_date(new_sim_date)
                        save_inventory(new_inv)
                        save_history(new_hist)
                        get_forecasts.clear()
                        st.rerun()
        with col_b:
            if st.button("↺ Reset", use_container_width=True):
                reload_data()
                st.session_state.sim_days         = 0
                st.session_state.sim_active       = False
                st.session_state.waste_events     = []
                st.session_state.sim_current_date = None
                set_sim_date(None)
                st.rerun()

        if st.session_state.sim_active:
            st.markdown(
                f'<div style="color:#fcd34d;font-size:0.72rem;margin-top:0.3rem">'
                f'⏩ {st.session_state.sim_days}d total simulated</div>',
                unsafe_allow_html=True,
            )

    else:
        # ── Live Mode: daily inventory update ────────────────────────────────
        from datetime import datetime as _dt_live, date as _date_live
        st.markdown('<p class="et-label">Record Inventory Count</p>', unsafe_allow_html=True)

        record_date = st.date_input(
            "Count date",
            value=_date_live.today(),
            key="live_record_date",
            label_visibility="collapsed",
            help="The date these counts are recorded for (typically end of business day)",
        )
        record_date_str = record_date.strftime("%Y-%m-%d")
        st.caption(f"Recording counts for {record_date_str}")

        trackable_live = [i for i in inv if i["type"] != "non_expiry"]
        with st.expander(f"Update quantities ({len(trackable_live)} items)", expanded=False):
            st.caption("Set actual on-hand quantity for each item.")
            live_updates = {}
            for item in trackable_live:
                cur = item["current_qty"]
                fc_live = forecasts.get(item["id"], {})
                avg_live = fc_live.get("avg_daily_usage", 0)
                new_val = st.number_input(
                    f"{item['name']} ({item['unit']})",
                    min_value=0.0,
                    value=float(cur),
                    step=0.5,
                    key=f"live_qty_{item['id']}",
                    help=f"Current: {cur:.1f} {item['unit']}  |  Avg daily: {avg_live:.2f} {item['unit']}/day",
                )
                if abs(new_val - cur) > 0.01:
                    live_updates[item["id"]] = new_val

        changed_count = len(live_updates)
        btn_label = f"Save {changed_count} change(s) for {record_date_str}" if changed_count else "No changes"
        if st.button(btn_label, type="primary", use_container_width=True,
                     disabled=(changed_count == 0), key="live_save_btn"):
            cur_inv, cur_hist = inv, hist
            errors_all = []
            for item_id, new_qty in live_updates.items():
                item_obj = next((i for i in cur_inv if i["id"] == item_id), None)
                note = "restock" if item_obj and new_qty > item_obj["current_qty"] else "usage"
                cur_inv, cur_hist, errs = update_quantity(
                    cur_inv, cur_hist, item_id, new_qty, note,
                    current_date=record_date_str,
                )
                errors_all.extend(errs)
            if errors_all:
                for e in errors_all:
                    st.error(e)
            else:
                st.session_state.inventory  = cur_inv
                st.session_state.history    = cur_hist
                st.session_state.sim_current_date = record_date_str
                set_sim_date(record_date_str)
                get_forecasts.clear()
                st.session_state.insight_cache = {}
                save_inventory(cur_inv)
                save_history(cur_hist)
                st.success(f"✓ {changed_count} item(s) recorded for {record_date_str}")
                st.rerun()

    if st.session_state.sim_active:
        _trackable_all = [i for i in inv if i["type"] != "non_expiry"]
        n_overridden = len([i for i in _trackable_all
                            if st.session_state.get(f"sim_override_{i['id']}", 0) > 0])
        label = f"{st.session_state.sim_days}d total simulated"
        if n_overridden:
            label += f" · {n_overridden} override(s)"
        st.markdown(f'<div style="color:#fcd34d;font-size:0.72rem;margin-top:0.3rem">{label}</div>',
                    unsafe_allow_html=True)


    st.divider()

    api_key = os.getenv("GROQ_API_KEY", "")
    if api_key:
        st.markdown('<p style="color:#4ade80;font-size:0.72rem">● AI insights active</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p style="color:#fb923c;font-size:0.72rem">● Rule-based fallback mode</p>', unsafe_allow_html=True)
        st.caption("Set ANTHROPIC_API_KEY in .env to enable LLM insights")


def page_dashboard():
    if st.session_state.sim_active:
        from datetime import datetime as _dt_dash
        sim_cur = st.session_state.get("sim_current_date", _dt_dash.today().strftime("%Y-%m-%d"))
        st.markdown(f'<div class="dev-mode-banner">⏩ Developer Mode — {st.session_state.sim_days} days simulated · Date: {sim_cur}</div>', unsafe_allow_html=True)

    waste_evts = st.session_state.get("waste_events", [])
    if waste_evts:
        total_wasted_items = len(waste_evts)
        st.markdown(
            f'<div class="et-card alert-high" style="margin-bottom:1rem">'
            f'<div style="font-family:Syne,sans-serif;font-size:0.95rem;font-weight:700;margin-bottom:0.5rem">'
            f'🚫 {total_wasted_items} item(s) expired during simulation</div>',
            unsafe_allow_html=True,
        )
        for we in waste_evts:
            st.markdown(
                f'<div style="font-size:0.82rem;color:#f87171;margin-bottom:0.2rem">'
                f'● {we["item_name"]} — '
                f'<strong>{we["wasted_qty"]} {we["unit"]}</strong> expired on {we["date"]}</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    _of = st.session_state.get("org_filter", "all")
    disp_inv = inv if _of == "all" else [i for i in inv if i["org"] == _of]
    disp_forecasts = {i["id"]: forecasts.get(i["id"], {}) for i in disp_inv}
    disp_alerts = check_all_alerts(disp_inv, disp_forecasts)

    _of2 = st.session_state.get("org_filter", "all")
    _org_labels = {"all": "All Orgs", "cafe": "☕ Café", "nonprofit": "🤝 Non-Profit", "university_lab": "🔬 University Lab"}
    org_label = _org_labels.get(_of2, "All Orgs")
    st.markdown(f"<h1>Inventory Overview <span style='color:#6b7c76;font-size:1rem;font-weight:400'>{org_label}</span></h1>", unsafe_allow_html=True)

    high_count    = sum(1 for a in disp_alerts if a.severity == Severity.HIGH)
    waste_count   = sum(1 for a in disp_alerts if a.type == AlertType.WASTE_RISK)
    stock_count   = sum(1 for a in disp_alerts if a.type == AlertType.STOCKOUT_RISK)
    expired_count = sum(1 for a in disp_alerts if a.type == AlertType.EXPIRED)
    sim_waste_qty = sum(w["wasted_qty"] for w in waste_evts)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Items",     len(disp_inv))
    c2.metric("🚨 Critical",      high_count,   delta=f"{high_count} need action" if high_count else "All clear", delta_color="inverse")
    c3.metric("♻️ Waste Risk",    waste_count,  delta="items may expire" if waste_count else "None detected", delta_color="inverse")
    c4.metric("⚠️ Stockout Risk", stock_count,  delta="reorder soon" if stock_count else "Levels OK", delta_color="inverse")
    c5.metric("🗑 Food Waste",
              f"{sim_waste_qty:.1f} units" if sim_waste_qty else "None",
              delta=f"{len(waste_evts)} item(s) expired" if waste_evts else "No expiry events",
              delta_color="inverse")

    st.divider()

    brief_org = st.session_state.get("org_filter", "cafe")
    if brief_org == "all":
        brief_org = "cafe" 
    brief_key = f"brief_{brief_org}_{st.session_state.sim_days}"

    with st.expander("🧠 Daily Intelligence Brief", expanded=True):
        if brief_key not in st.session_state.insight_cache:
            with st.spinner("Generating brief..."):
                brief_result = generate_daily_brief(
                    org=brief_org,
                    inventory=disp_inv,
                    forecasts=disp_forecasts,
                    all_alerts=disp_alerts,
                )
                st.session_state.insight_cache[brief_key] = brief_result
        else:
            brief_result = st.session_state.insight_cache[brief_key]

        source = brief_result.get("source", "fallback")
        badge_class = "llm" if source == "llm" else "fallback"
        badge_label = "AI Generated" if source == "llm" else "Rule-based Fallback"

        st.markdown(
            f'<span class="ai-badge {badge_class}">{badge_label}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(brief_result["brief"])

        if brief_result.get("error"):
            st.caption(f"ℹ️ {brief_result['error']}")

    st.divider()

    high_med = [a for a in disp_alerts if a.severity in (Severity.HIGH, Severity.MEDIUM)]
    if high_med:
        st.markdown("<h2>Active Alerts</h2>", unsafe_allow_html=True)
        for alert in high_med[:8]: 
            emoji = alert_emoji(alert.type)
            css   = sev_class(alert.severity)
            st.markdown(
                f'<div class="et-card {css}">'
                f'<span style="font-size:1rem">{emoji}</span> '
                f'<strong style="font-family:\'Syne\',sans-serif;font-size:0.9rem">{alert.title}</strong> '
                f'<span style="color:#6b7c76;font-size:0.75rem">— {alert.item_name}</span>'
                f'<div style="color:#a8b8b0;font-size:0.8rem;margin-top:0.3rem">{alert.message}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.success("No critical alerts. Inventory looking healthy.")

    st.divider()

    # ── Sustainability Panel ─────────────────────────────────────────────────
    st.markdown("<h2>🌱 Sustainability Snapshot</h2>", unsafe_allow_html=True)

    # Compute waste cost + items at risk
    _waste_cost   = 0.0
    _waste_items  = []
    _saved_cost   = 0.0 
    for _item in disp_inv:
        _fc = disp_forecasts.get(_item["id"], {})
        _wu = _fc.get("estimated_waste_units") or 0
        _cpu = _item.get("cost_per_unit", 0)
        if _wu > 0 and _cpu > 0:
            _wc = round(_wu * _cpu, 2)
            _waste_cost += _wc
            _waste_items.append((_item["name"], _wu, _item["unit"], _wc))
            
        if not _fc.get("waste_risk") and not _fc.get("stockout_risk") and _item["type"] != "non_expiry":
            _saved_cost += _item.get("cost_per_unit", 0) * max(0, _item["current_qty"] * 0.05)

    _sus_c1, _sus_c2, _sus_c3 = st.columns(3)
    _sus_c1.metric("Potential Waste Value",
                   f"₹{_waste_cost:.0f}" if _waste_cost else "₹0",
                   delta=f"{len(_waste_items)} item(s) at risk" if _waste_items else "No waste risk",
                   delta_color="inverse")
    _sus_c2.metric("Items On Track",
                   f"{sum(1 for i in disp_inv if not disp_forecasts.get(i['id'],{}).get('waste_risk') and not disp_forecasts.get(i['id'],{}).get('stockout_risk') and i['type']!='non_expiry')}",
                   delta="healthy stock levels")
    _sus_c3.metric("Tracked Items",
                   len([i for i in disp_inv if i['type'] != 'non_expiry']),
                   delta=f"{len([i for i in disp_inv if i['type']=='perishable'])} perishables monitored")

    if _waste_items:
        _waste_rows = "".join(
            f'<tr><td>{n}</td><td style="color:#f97316">{w:.1f} {u}</td>'
            f'<td style="color:#f87171">₹{c:.0f}</td></tr>'
            for n, w, u, c in _waste_items
        )
        st.markdown(
            f'<div style="margin-top:0.5rem">'
            f'<table style="width:100%;border-collapse:collapse;font-family:DM Mono,monospace;font-size:0.78rem">'
            f'<thead><tr>'
            f'<th style="color:#6b7c76;text-align:left;padding:0.3rem 0.5rem;border-bottom:1px solid #2a3330">Item</th>'
            f'<th style="color:#6b7c76;text-align:left;padding:0.3rem 0.5rem;border-bottom:1px solid #2a3330">Potential Waste</th>'
            f'<th style="color:#6b7c76;text-align:left;padding:0.3rem 0.5rem;border-bottom:1px solid #2a3330">Est. Loss</th>'
            f'</tr></thead><tbody>'
            f'{_waste_rows}'
            f'</tbody></table></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Quick inventory grid 
    st.markdown("<h2>Inventory at a Glance</h2>", unsafe_allow_html=True)

    def sort_key(item):
        fc  = forecasts.get(item["id"], {})
        als = check_alerts(item, fc)
        sev = min(({"high": 0, "medium": 1, "low": 2}.get(str(a.severity), 3) for a in als), default=99)
        return sev

    sorted_inv = sorted(disp_inv, key=sort_key)

    for item in sorted_inv[:15]:
        fc   = forecasts.get(item["id"], {})
        als  = check_alerts(item, fc)
        high = [a for a in als if a.severity == Severity.HIGH]
        med  = [a for a in als if a.severity == Severity.MEDIUM]

        if high:   css = "alert-high"
        elif med:  css = "alert-med"
        else:      css = "ok"

        days_out  = fc.get("days_until_runout")
        exp_days  = fc.get("expiry_days_remaining")
        conf      = fc.get("confidence", "none")
        conf_col  = confidence_color(conf)

        days_str  = f"{days_out:.0f}d left" if days_out is not None else "N/A"
        exp_str   = item.get('expiry_date', 'no expiry') if item.get('expiry_date') else 'no expiry'

        type_tag  = tag_html(item["type"].replace("_", " "), f"tag-{item['type']}")
        org_tag   = tag_html(item["org"].replace("_", " "), f"tag-{item['org']}")

        icons = "".join(alert_emoji(a.type) for a in als if a.severity in (Severity.HIGH, Severity.MEDIUM))

        col1, col2, col3, col4 = st.columns([3, 1.5, 1.5, 1])
        with col1:
            st.markdown(
                f'<div class="et-card {css}" style="margin-bottom:0.3rem">'
                f'{type_tag}{org_tag}'
                f'<div style="font-family:\'Syne\',sans-serif;font-size:0.95rem;font-weight:600;margin-top:0.4rem">'
                f'{icons} {item["name"]}</div>'
                f'<div class="et-mono" style="margin-top:0.2rem">{item["category"]} · {item["unit"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f'<div class="et-card" style="margin-bottom:0.3rem;text-align:center">'
                f'<div class="et-label">Current Stock</div>'
                f'<div class="et-value">{fmt_qty(item["current_qty"], item["unit"])}</div>'
                f'<div class="et-mono">reorder: {int(item["reorder_qty"])} {item["unit"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                f'<div class="et-card" style="margin-bottom:0.3rem;text-align:center">'
                f'<div class="et-label">Forecast</div>'
                f'<div class="et-value">{days_str}</div>'
                f'<div class="et-mono">{exp_str}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col4:
            if item['type'] == 'non_expiry':
                conf_display = '<div class="et-label">Forecast</div><div style="font-size:0.8rem;color:#6b7c76;margin-top:0.3rem">Equipment —<br>no forecast</div>'
            else:
                conf_display = f'<div class="et-label">Confidence</div><div style="font-family:\'Syne\',sans-serif;font-size:1rem;font-weight:700;color:{conf_col}">{conf.upper()}</div><div class="et-mono">{fc.get("data_points_used",0)} data pts</div>'
            st.markdown(
                f'<div class="et-card" style="margin-bottom:0.3rem;text-align:center">{conf_display}</div>',
                unsafe_allow_html=True,
            )

    if len(sorted_inv) > 15:
        st.caption(f"Showing 15 of {len(sorted_inv)} items. View all in Inventory tab.")



def page_inventory():
    st.markdown("<h1>Inventory</h1>", unsafe_allow_html=True)

    fc1, fc2, fc3, fc4 = st.columns([3, 1.5, 1.5, 1.5])
    with fc1:
        query = st.text_input("🔍 Search items...", placeholder="name or category", label_visibility="collapsed")
    with fc2:
        type_filter = st.selectbox("type", options=list(TYPE_LABELS.keys()),
                                   format_func=lambda x: TYPE_LABELS[x], label_visibility="collapsed")
    with fc3:
        alert_filter = st.selectbox("alerts", options=["all", "waste_risk", "stockout_risk", "below_threshold"],
                                    format_func=lambda x: {"all": "All Items", "waste_risk": "♻️ Waste Risk",
                                                            "stockout_risk": "⚠️ Stockout Risk",
                                                            "below_threshold": "📉 Below Threshold"}[x],
                                    label_visibility="collapsed")
    with fc4:
        sort_by = st.selectbox("sort", options=["alert", "name", "expiry", "qty"],
                               format_func=lambda x: {"alert": "Sort: Alerts", "name": "Sort: Name",
                                                       "expiry": "Sort: Expiry", "qty": "Sort: Qty"}[x],
                               label_visibility="collapsed")

    filtered = search_and_filter(
        inv, query=query, org=st.session_state.get("org_filter","all"), item_type=type_filter,
        alert_filter=alert_filter, forecasts=forecasts,
    )

    if sort_by == "alert":
        def _sort(item):
            als = check_alerts(item, forecasts.get(item["id"], {}))
            return min(({"high":0,"medium":1,"low":2}.get(str(a.severity),3) for a in als), default=99)
        filtered = sorted(filtered, key=_sort)
    elif sort_by == "name":
        filtered = sorted(filtered, key=lambda i: i["name"])
    elif sort_by == "expiry":
        filtered = sorted(filtered, key=lambda i: i.get("expiry_date") or "9999-99-99")
    elif sort_by == "qty":
        filtered = sorted(filtered, key=lambda i: i["current_qty"])

    st.caption(f"{len(filtered)} item(s) shown")
    st.divider()

    for item in filtered:
        fc   = forecasts.get(item["id"], {})
        als  = check_alerts(item, fc)
        high = [a for a in als if a.severity == Severity.HIGH]
        med  = [a for a in als if a.severity == Severity.MEDIUM]

        if high:   css = "alert-high"
        elif med:  css = "alert-med"
        else:      css = "ok"

        days_out = fc.get("days_until_runout")
        exp_days = fc.get("expiry_days_remaining")
        conf     = fc.get("confidence", "none")
        icons    = "".join(alert_emoji(a.type) for a in als if a.severity in (Severity.HIGH, Severity.MEDIUM))

        type_tag = tag_html(item["type"].replace("_", " "), f"tag-{item['type']}")
        org_tag  = tag_html(ORG_ICONS.get(item["org"], "") + " " + item["org"].replace("_", " "), f"tag-{item['org']}")

        with st.expander(
            f"{icons}  {item['name']}   —   {fmt_qty(item['current_qty'], item['unit'])}",
            expanded=(st.session_state.selected_item_id == item["id"]),
        ):
            col_left, col_right = st.columns([2, 1])

            with col_left:
                st.markdown(
                    f'{type_tag}{org_tag}'
                    f'<div style="margin-top:0.6rem" class="et-mono">'
                    f'ID: {item["id"]} &nbsp;·&nbsp; Category: {item["category"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                st.markdown("---")
                if item['type'] == 'non_expiry':
                    m1, m2 = st.columns(2)
                    m1.metric("Current Stock", fmt_qty(item["current_qty"], item["unit"]))
                    m2.metric("Type", "Equipment — no forecast applicable")
                else:
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Current Stock", fmt_qty(item["current_qty"], item["unit"]))
                    m2.metric("Runs Out In",
                              f"{days_out:.1f} days" if days_out is not None else "N/A")
                    m3.metric("Expires In",
                              f"{exp_days} days" if exp_days is not None else "No expiry")
                    m4.metric("Forecast Conf.",
                              conf.upper(),
                              delta=f"{fc.get('data_points_used',0)} data pts")

                if fc.get("waste_risk"):
                    wu = fc.get("estimated_waste_units", 0)
                    st.warning(f"♻️ Waste risk — ~{wu} {item['unit']} may expire unused")
                if fc.get("stockout_risk"):
                    st.error(f"⚠️ Stockout risk — reorder {item.get('reorder_qty','')} {item['unit']} recommended")

                if als:
                    st.markdown("**Alerts:**")
                    for alert in als:
                        emoji = alert_emoji(alert.type)
                        col = {"high": "#f87171", "medium": "#fb923c", "low": "#60a5fa"}.get(str(alert.severity), "#a8b8b0")
                        st.markdown(f'<div style="color:{col};font-size:0.82rem;margin-bottom:0.2rem">{emoji} {alert.message}</div>', unsafe_allow_html=True)

                if item['type'] != 'non_expiry':
                    if fc.get("model_used") == "fallback":
                        st.markdown('<span class="ai-badge fallback">Rule-based fallback</span>', unsafe_allow_html=True)
                        if fc.get("note"):
                            st.caption(fc["note"])
                    else:
                        st.markdown('<span class="ai-badge llm">WMA Forecast</span>', unsafe_allow_html=True)

                st.markdown("---")

                # AI Insight
                if item['type'] != 'non_expiry':
                    insight_key = f"insight_{item['id']}_{st.session_state.sim_days}"
                    if st.button(f"Generate AI Insight", key=f"gen_{item['id']}"):
                        with st.spinner("Thinking..."):
                            result = generate_insight(item, fc, als)
                            st.session_state.insight_cache[insight_key] = result

                    if insight_key in st.session_state.insight_cache:
                        result = st.session_state.insight_cache[insight_key]
                        source = result.get("source", "fallback")
                        badge_class = "llm" if source == "llm" else "fallback"
                        badge_label = "AI Generated" if source == "llm" else "Rule-based Fallback"
                        st.markdown(
                            f'<div class="et-card" style="background:#0f1a14;border-color:#2a4a32">'
                            f'<span class="ai-badge {badge_class}">{badge_label}</span>'
                            f'<div style="margin-top:0.5rem;font-size:0.85rem;line-height:1.6">{result["insight"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        if result.get("error"):
                            st.caption(f"ℹ️ {result['error']}")

            with col_right:
                st.markdown('<div class="et-label">Update Quantity</div>', unsafe_allow_html=True)
                new_qty = st.number_input(
                    "new qty", value=float(item["current_qty"]),
                    min_value=0.0, step=1.0, label_visibility="collapsed",
                    key=f"qty_{item['id']}",
                )
                update_note = st.selectbox(
                    "reason", options=["usage", "manual_update", "waste", "correction"],
                    label_visibility="collapsed", key=f"note_{item['id']}",
                )
                if st.button("Update", key=f"upd_{item['id']}", type="primary"):
                    _sim_date = st.session_state.get("sim_current_date")
                    updated_inv, updated_hist, errors = update_quantity(
                        inv, hist, item["id"], new_qty, update_note,
                        current_date=_sim_date,
                    )
                    if errors:
                        for e in errors:
                            st.error(e)
                    else:
                        st.session_state.inventory = updated_inv
                        st.session_state.history   = updated_hist
                        get_forecasts.clear()
                        st.session_state.insight_cache = {}
                        st.success("✓ Updated")
                        st.rerun()

                st.markdown("---")
                st.markdown('<div class="et-label">Item Details</div>', unsafe_allow_html=True)
                next_exp = item.get("next_batch_expiry")
                exp_display = item.get("expiry_date") or "None"
                if next_exp and next_exp != item.get("expiry_date"):
                    exp_display += f" (new batch: {next_exp})"
                details = {
                    "ID": item["id"],
                    "Cost / unit": f"₹{item.get('cost_per_unit', 0)}",
                    "Reorder qty": f"{item.get('reorder_qty','')} {item['unit']}",
                    "Last updated": item.get("last_updated", "—"),
                    "Expiry date": exp_display,
                }
                for k, v in details.items():
                    st.markdown(f'<div class="et-mono"><span style="color:#6b7c76">{k}:</span> {v}</div>', unsafe_allow_html=True)

                st.markdown("---")

                exp_days_inv = fc.get("expiry_days_remaining")
                if exp_days_inv is not None and exp_days_inv <= 1 and item["current_qty"] > 0:
                    avg_inv        = fc.get("avg_daily_usage", 0)
                    shelf_life_inv = item.get("shelf_life_days")
                    target         = min(14, shelf_life_inv - 1) if shelf_life_inv else 14
                    target_qty     = round(avg_inv * target, 1) if avg_inv > 0 else float(item.get("reorder_qty", 0))
                    sug            = target_qty
                    sug_note       = (
                        f"Target: {target_qty} {item['unit']} (~{target}d stock). "
                        f"You have {item['current_qty']:.1f} {item['unit']} — "
                        f"discard first, then order {sug} {item['unit']}."
                    )
                    st.markdown(
                        f'<div class="et-card alert-high" style="margin-bottom:0.5rem">' +
                        f'<div style="font-size:0.78rem;color:#f87171">Expires in {exp_days_inv} day(s). Discard and restock?</div>' +
                        f'<div style="color:#4ade80;font-size:0.82rem;margin-top:0.3rem">{sug_note}</div>' +
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(f"🗑 Discard {item['current_qty']:.0f} {item['unit']}",
                                 key=f"discard_inv_{item['id']}", type="primary"):
                        _sim_date = st.session_state.get("sim_current_date")
                        updated_inv, updated_hist, errors = update_quantity(
                            inv, hist, item["id"], 0.0, "waste",
                            current_date=_sim_date,
                        )
                        if errors:
                            for e in errors: st.error(e)
                        else:
                            st.session_state.inventory = updated_inv
                            st.session_state.history   = updated_hist
                            get_forecasts.clear()
                            st.session_state.insight_cache = {}
                            st.success(f"Discarded. Order {sug} {item['unit']} to restock (~{target}d supply).")
                            st.rerun()

                if st.button("🗑 Delete item", key=f"del_{item['id']}"):
                    updated_inv, errors = delete_item(inv, item["id"])
                    if errors:
                        for e in errors: st.error(e)
                    else:
                        st.session_state.inventory = updated_inv
                        get_forecasts.clear()
                        st.success("Deleted")
                        st.rerun()


# PAGE: ADD ITEM

def page_add_item():
    st.markdown("<h1>Add New Item</h1>", unsafe_allow_html=True)
    st.caption("All fields marked * are required.")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        name     = st.text_input("Item Name *", placeholder="e.g. Whole Milk")
        org      = st.selectbox("Organisation *", options=list(VALID_ORGS),
                                format_func=lambda x: ORG_LABELS.get(x, x))
        item_type = st.selectbox("Item Type *", options=list(VALID_TYPES),
                                 format_func=lambda x: TYPE_LABELS.get(x, x))
        category = st.text_input("Category", placeholder="e.g. dairy, reagent, office_supply")
        unit     = st.text_input("Unit *", placeholder="e.g. liters, kg, units, boxes")

    with col2:
        current_qty     = st.number_input("Current Quantity *", min_value=0.0, step=1.0, value=10.0)
        reorder_threshold = st.number_input("Reorder Threshold *", min_value=0.0, step=1.0, value=3.0,
                                             help="Alert triggers below this quantity")
        reorder_qty     = st.number_input("Reorder Quantity", min_value=0.0, step=1.0, value=0.0,
                                          help="How much to order. Defaults to 3× threshold.")
        cost_per_unit   = st.number_input("Cost per Unit (₹)", min_value=0.0, step=1.0, value=0.0)

        has_expiry = st.checkbox("Has expiry date?", value=(item_type == "perishable"))
        expiry_date = None
        if has_expiry:
            expiry_date = st.date_input("Expiry Date",
                                        value=datetime.today() + timedelta(days=30),
                                        min_value=datetime.today())
            expiry_date = expiry_date.strftime("%Y-%m-%d")

    st.divider()

    if st.button("＋ Add Item", type="primary"):
        data = {
            "name": name,
            "org": org,
            "type": item_type,
            "category": category or "general",
            "unit": unit,
            "current_qty": current_qty,
            "reorder_threshold": reorder_threshold,
            "reorder_qty": reorder_qty if reorder_qty > 0 else reorder_threshold * 3,
            "cost_per_unit": cost_per_unit,
            "expiry_date": expiry_date,
        }
        updated_inv, errors = add_item(inv, data)
        if errors:
            for e in errors:
                st.error(f"✗ {e}")
        else:
            st.session_state.inventory = updated_inv
            get_forecasts.clear()
            st.success(f"✓ '{name}' added to inventory.")
            st.balloons()
            st.session_state.page = "inventory"
            st.rerun()


# PAGE: ALERTS

def page_alerts():
    st.markdown("<h1>Alerts</h1>", unsafe_allow_html=True)

    _of3 = st.session_state.get("org_filter", "all")
    disp_inv = inv if _of3 == "all" else [i for i in inv if i["org"] == _of3]
    disp_fc  = {i["id"]: forecasts.get(i["id"], {}) for i in disp_inv}
    disp_als = check_all_alerts(disp_inv, disp_fc)

    by_sev = {s: [a for a in disp_als if a.severity == s] for s in Severity}
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 High",   len(by_sev[Severity.HIGH]))
    c2.metric("⚠️ Medium", len(by_sev[Severity.MEDIUM]))
    c3.metric("🔍 Low",    len(by_sev[Severity.LOW]))

    st.divider()

    if not disp_als:
        st.success("No alerts for the selected filter. Inventory looks healthy.")
        return

    type_groups = {}
    for alert in disp_als:
        type_groups.setdefault(alert.type, []).append(alert)

    type_order = [AlertType.EXPIRED, AlertType.WASTE_RISK, AlertType.STOCKOUT_RISK,
                  AlertType.CRITICAL_LOW]

    for atype in type_order:
        group = type_groups.get(atype, [])
        if not group:
            continue

        emoji = alert_emoji(atype)
        label = atype.value.replace("_", " ").title()
        st.markdown(f"<h2>{emoji} {label} ({len(group)})</h2>", unsafe_allow_html=True)

        for alert in group:
            css = sev_class(alert.severity)
            item = get_item(inv, alert.item_id)
            fc   = forecasts.get(alert.item_id, {})

            with st.expander(f"{alert.item_name} — {alert.title}"):
                st.markdown(
                    f'<div class="et-card {css}">'
                    f'<div style="font-size:0.85rem;line-height:1.6">{alert.message}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                if item:
                    avg_usage  = fc.get("avg_daily_usage", 0)
                    days_out   = fc.get("days_until_runout")
                    exp_days   = fc.get("expiry_days_remaining")
                    unit       = item["unit"]

                    shelf_life = item.get("shelf_life_days")
                    if item["type"] == "perishable" and shelf_life:
                        TARGET_DAYS_STOCK = min(14, shelf_life - 1)
                        target_label = f"~{TARGET_DAYS_STOCK}d (shelf life)"
                    else:
                        TARGET_DAYS_STOCK = 14
                        target_label = "~14d"
                    if avg_usage and avg_usage > 0:
                        target_qty    = round(avg_usage * TARGET_DAYS_STOCK, 1)
                        on_hand       = item["current_qty"]
                        suggested_order = round(max(0, target_qty - on_hand), 1)
                        restock_note = (
                            f"Target stock: {target_qty} {unit} ({target_label}). "
                            f"You have {on_hand:.1f} {unit} — order {suggested_order} {unit}."
                        )
                    else:
                        suggested_order = float(item.get("reorder_qty", 0))
                        restock_note = None

                    already_out   = item["current_qty"] <= 0
                    is_expired    = (exp_days is not None and exp_days <= 0)
                    is_waste_risk = atype == AlertType.WASTE_RISK
                    show_discard  = (is_expired or is_waste_risk) and not already_out

                    if show_discard:
                        # WASTE / EXPIRED with remaining stock 
                        waste_qty = item["current_qty"]
                        st.markdown(
                            f'<div class="et-card alert-high" style="margin-top:0.5rem">'
                            f'<div style="font-size:0.82rem;color:#f87171;margin-bottom:0.5rem">'
                            f'🚫 {waste_qty:.1f} {unit} will be discarded. This cannot be undone.</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        col_d, col_r = st.columns(2)
                        with col_d:
                            if st.button(f"🗑 Discard all ({waste_qty:.0f} {unit})",
                                         key=f"discard_{alert.item_id}_{atype}", type="primary"):
                                _sim_date = st.session_state.get("sim_current_date")
                                updated_inv, updated_hist, errors = update_quantity(
                                    inv, hist, alert.item_id, 0.0, "waste",
                                    current_date=_sim_date,
                                )
                                if errors:
                                    for e in errors: st.error(e)
                                else:
                                    st.session_state.inventory = updated_inv
                                    st.session_state.history   = updated_hist
                                    get_forecasts.clear()
                                    st.session_state.insight_cache = {}
                                    st.success(f"✓ Discarded {waste_qty:.0f} {unit} of {item['name']}")
                                    st.rerun()
                        with col_r:
                            st.markdown(
                                f'<div class="et-card" style="padding:0.6rem 0.8rem">'
                                f'<div class="et-label">Suggested Restock (after discarding)</div>'
                                f'<div style="color:#4ade80;font-size:1rem;font-weight:700;font-family:Syne,sans-serif">{suggested_order} {unit}</div>'
                                + (f'<div class="et-mono" style="font-size:0.72rem;margin-top:0.2rem">{restock_note}</div>' if restock_note else "")
                                + f'</div>',
                                unsafe_allow_html=True,
                            )

                    else:
                        # OUT OF STOCK / STOCKOUT / CRITICAL_LOW → restock
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown(f'<div class="et-mono">Current: {fmt_qty(item["current_qty"], unit)}</div>', unsafe_allow_html=True)
                            if days_out is not None and days_out > 0:
                                st.markdown(f'<div class="et-mono">Runs out in: {days_out:.1f} days</div>', unsafe_allow_html=True)
                            if exp_days is not None and exp_days > 0:
                                st.markdown(f'<div class="et-mono">Expires in: {exp_days} days</div>', unsafe_allow_html=True)
                        with c2:
                            st.markdown(
                                f'<div class="et-card" style="padding:0.6rem 0.8rem">'
                                f'<div class="et-label">Suggested Restock</div>'
                                f'<div style="color:#4ade80;font-size:1rem;font-weight:700;font-family:Syne,sans-serif">{suggested_order} {unit}</div>'
                                + (f'<div class="et-mono" style="font-size:0.72rem;margin-top:0.2rem">{restock_note}</div>' if restock_note else "")
                                + f'</div>',
                                unsafe_allow_html=True,
                            )
                        restock_qty = st.number_input(
                            "Restock amount", value=float(suggested_order),
                            min_value=0.0, step=1.0, key=f"alt_qty_{alert.item_id}_{atype}"
                        )
                        new_total = item["current_qty"] + restock_qty
                        if st.button(f"+ Restock {restock_qty:.0f} {unit}",
                                     key=f"alt_upd_{alert.item_id}_{atype}", type="primary"):
                            _sim_date = st.session_state.get("sim_current_date")
                            updated_inv, updated_hist, errors = update_quantity(
                                inv, hist, alert.item_id, new_total, "restock",
                                current_date=_sim_date,
                            )
                            if errors:
                                for e in errors: st.error(e)
                            else:
                                st.session_state.inventory = updated_inv
                                st.session_state.history   = updated_hist
                                get_forecasts.clear()
                                st.session_state.insight_cache = {}
                                st.success(f"✓ Restocked — new qty: {new_total:.1f} {unit}")
                                st.rerun()

                        # Sustainable supplier suggestion
                        sugg_key = f"sugg_{alert.item_id}"
                        if st.button("🌱 Sustainable sourcing tips",
                                     key=f"sugg_btn_{alert.item_id}_{atype}"):
                            with st.spinner("Finding sustainable options..."):
                                sugg = suggest_suppliers(item)
                                st.session_state.insight_cache[sugg_key] = sugg
                        if sugg_key in st.session_state.insight_cache:
                            _sugg = st.session_state.insight_cache[sugg_key]
                            _badge = "llm" if _sugg["source"] == "llm" else "fallback"
                            st.markdown(
                                f'<div class="et-card" style="background:#0f1a14;border-color:#2a4a32;margin-top:0.4rem">'
                                f'<span class="ai-badge {_badge}">{"AI Suggestion" if _badge=="llm" else "Fallback Tip"}</span>'
                                f'<div style="margin-top:0.4rem;font-size:0.82rem;line-height:1.6;color:#a8b8b0">{_sugg["suggestion"]}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

        st.divider()



# PAGE: ANALYTICS

def page_analytics():
    st.markdown("<h1>Analytics</h1>", unsafe_allow_html=True)
    st.markdown(
        '<p class="et-mono" style="color:#6b7c76;margin-top:-0.5rem">'
        'Usage trends and restock history. Simulate time forward in the sidebar to see depletion.'
        '</p>',
        unsafe_allow_html=True,
    )

    # Item selector
    _of4 = st.session_state.get("org_filter", "all")
    _base = inv if _of4 == "all" else [i for i in inv if i["org"] == _of4]
    trackable = [i for i in _base if i["type"] != "non_expiry"]
    sel_name  = st.selectbox("Select item", [i["name"] for i in trackable],
                              label_visibility="collapsed")
    sel_item  = next(i for i in trackable if i["name"] == sel_name)
    item_id   = sel_item["id"]
    unit      = sel_item["unit"]

    item_hist = sorted(
        [r for r in hist if r["item_id"] == item_id],
        key=lambda r: r["date"],
    )

    st.divider()

    if not item_hist:
        st.info("No usage history for this item yet.")
        return

    fc           = forecasts.get(item_id, {})
    dates        = [r["date"] for r in item_hist]
    usage_vals   = [r["quantity_used"] for r in item_hist]
    restock_vals = [r.get("restock_qty", 0) for r in item_hist]
    events       = [r.get("event", "normal") for r in item_hist]

    qty     = sel_item["current_qty"]
    running = []
    for usage, restock in zip(reversed(usage_vals), reversed(restock_vals)):
        qty = qty + usage - restock
        running.append(round(qty, 2))
    running = list(reversed(running))

    # Summary metrics
    total_used     = sum(usage_vals)
    restock_events = sum(1 for e in events if e == "restock")
    bulk_events    = sum(1 for e in events if e == "bulk_order")
    avg_daily      = fc.get("avg_daily_usage", 0)
    active_days    = sum(1 for v in usage_vals if v > 0)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(f"Total Used ({len(item_hist)}d)", f"{total_used:.1f} {unit}")
    c2.metric("Avg / Day",       f"{avg_daily:.2f} {unit}")
    c3.metric("Active Days",     f"{active_days} / {len(item_hist)}")
    c4.metric("Restock Events",  restock_events)
    c5.metric("Bulk Spikes",     bulk_events)

    st.divider()

    # Chart: Stock level + daily usage
    st.markdown("<h2>Stock Level Over Time</h2>", unsafe_allow_html=True)

    restock_indices = [i for i, e in enumerate(events) if e == "restock"]
    bulk_indices    = [i for i, e in enumerate(events) if e == "bulk_order"]

    chart_html = f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  body {{ margin:0; background:#0f1110; }}
  .wrap {{ padding:16px; }}
  canvas {{ max-height:280px; }}
  .legend {{ display:flex; gap:20px; padding:8px 0 0; font-size:11px; color:#6b7c76;
             font-family:'DM Mono',monospace; }}
  .dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:4px; }}
</style>
</head><body>
<div class="wrap">
  <canvas id="c"></canvas>
  <div class="legend">
    <span><span class="dot" style="background:#4ade80"></span>Stock ({unit})</span>
    <span><span class="dot" style="background:#60a5fa"></span>Daily usage ({unit})</span>
    <span><span class="dot" style="background:#f97316"></span>Restock</span>
    <span><span class="dot" style="background:#fcd34d"></span>Bulk spike</span>
  </div>
</div>
<script>
const labels  = {dates};
const stock   = {running};
const usage   = {usage_vals};
const restock = {restock_vals};

const ptColor = labels.map((_,i) => {{
  if ({restock_indices}.includes(i)) return '#f97316';
  if ({bulk_indices}.includes(i))    return '#fcd34d';
  return 'rgba(0,0,0,0)';
}});
const ptSize = labels.map((_,i) =>
  ({restock_indices}.includes(i) || {bulk_indices}.includes(i)) ? 5 : 0
);

new Chart(document.getElementById('c'), {{
  type: 'line',
  data: {{
    labels,
    datasets: [
      {{
        label: 'Stock ({unit})',
        data: stock,
        borderColor: '#4ade80',
        backgroundColor: 'rgba(74,222,128,0.07)',
        borderWidth: 2, fill: true, tension: 0.3,
        pointBackgroundColor: ptColor,
        pointRadius: ptSize, pointHoverRadius: 5,
      }},
      {{
        label: 'Daily Usage ({unit})',
        data: usage,
        borderColor: '#60a5fa',
        borderWidth: 1.5, fill: false, tension: 0.3,
        pointRadius: 0, pointHoverRadius: 4,
        yAxisID: 'y2',
      }},
    ]
  }},
  options: {{
    responsive: true,
    interaction: {{ mode:'index', intersect:false }},
    plugins: {{
      legend: {{ display:false }},
      tooltip: {{
        backgroundColor:'#1e2422', borderColor:'#2a3330', borderWidth:1,
        titleColor:'#e8ede9', bodyColor:'#a8b8b0',
        callbacks: {{
          afterBody: (items) => {{
            const i = items[0].dataIndex;
            const out = [];
            if ({restock_indices}.includes(i)) out.push(`↑ Restock: +${{restock[i]}} {unit}`);
            if ({bulk_indices}.includes(i))    out.push('⚡ Bulk spike');
            return out;
          }}
        }}
      }}
    }},
    scales: {{
      x:  {{ ticks:{{ color:'#6b7c76', maxTicksLimit:10, font:{{size:10}} }}, grid:{{color:'#1e2422'}} }},
      y:  {{ position:'left',  ticks:{{color:'#4ade80',font:{{size:10}}}}, grid:{{color:'#1e2422'}},
             title:{{display:true,text:'Stock ({unit})',color:'#6b7c76',font:{{size:10}}}} }},
      y2: {{ position:'right', ticks:{{color:'#60a5fa',font:{{size:10}}}}, grid:{{drawOnChartArea:false}},
             title:{{display:true,text:'Usage ({unit})',color:'#6b7c76',font:{{size:10}}}} }},
    }}
  }}
}});
</script></body></html>"""

    st.components.v1.html(chart_html, height=340)
    st.divider()

    # Usage bar chart + restock log
    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown("<h2>Daily Usage — Last 21 Days</h2>", unsafe_allow_html=True)
        recent_dates  = dates[-21:]
        recent_usage  = usage_vals[-21:]
        recent_events = events[-21:]
        bar_colors    = ['#f97316' if e=='restock' else '#fcd34d' if e=='bulk_order'
                         else '#4ade80' for e in recent_events]

        bar_html = f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>body{{margin:0;background:#0f1110;}} canvas{{max-height:220px;}}</style>
</head><body>
<div style="padding:12px">
  <canvas id="b"></canvas>
</div>
<script>
new Chart(document.getElementById('b'), {{
  type: 'bar',
  data: {{
    labels: {recent_dates},
    datasets: [{{ label:'Usage ({unit})', data:{recent_usage},
                 backgroundColor:{bar_colors}, borderRadius:2 }}]
  }},
  options: {{
    responsive:true,
    plugins:{{ legend:{{display:false}},
      tooltip:{{backgroundColor:'#1e2422',borderColor:'#2a3330',borderWidth:1,
                titleColor:'#e8ede9',bodyColor:'#a8b8b0'}} }},
    scales:{{
      x:{{ ticks:{{color:'#6b7c76',maxTicksLimit:7,font:{{size:9}}}}, grid:{{color:'#1e2422'}} }},
      y:{{ ticks:{{color:'#a8b8b0',font:{{size:10}}}}, grid:{{color:'#1e2422'}} }}
    }}
  }}
}});
</script></body></html>"""
        st.components.v1.html(bar_html, height=260)

    with col_r:
        st.markdown("<h2>Restock Log</h2>", unsafe_allow_html=True)
        restock_records = [
            (r["date"], r["restock_qty"])
            for r in item_hist if r.get("restock_qty", 0) > 0
        ]
        if restock_records:
            for date, qty_r in reversed(restock_records[-10:]):
                st.markdown(
                    f'<div class="et-card" style="padding:0.5rem 0.8rem;margin-bottom:0.3rem;'
                    f'display:flex;justify-content:space-between;align-items:center">'
                    f'<span class="et-mono" style="font-size:0.75rem;color:#6b7c76">{date}</span>'
                    f'<span style="color:#f97316;font-family:Syne,sans-serif;font-size:0.85rem;'
                    f'font-weight:600">+{qty_r:.0f} {unit}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No restock events recorded yet.")

    st.divider()

    # Weekly breakdown table
    st.markdown("<h2>Weekly Breakdown</h2>", unsafe_allow_html=True)
    from datetime import datetime as _dt
    weekly = {}
    for r in item_hist:
        w = _dt.strptime(r["date"], "%Y-%m-%d").isocalendar()[1]
        d = weekly.setdefault(w, {"used": 0, "restocked": 0, "active": 0})
        d["used"]      += r["quantity_used"]
        d["restocked"] += r.get("restock_qty", 0)
        if r["quantity_used"] > 0:
            d["active"] += 1

    rows = ""
    for n, (w, d) in enumerate(sorted(weekly.items()), 1):
        avg = d["used"] / max(d["active"], 1)
        rows += (
            f'<tr><td>Week {n}</td>'
            f'<td style="color:#4ade80">{d["used"]:.1f} {unit}</td>'
            f'<td style="color:#60a5fa">{avg:.2f} {unit}/day</td>'
            f'<td style="color:#f97316">{d["restocked"]:.0f} {unit}</td>'
            f'<td style="color:#a8b8b0">{d["active"]} days</td></tr>'
        )

    st.markdown(
        f'<style>table{{width:100%;border-collapse:collapse;font-family:DM Mono,monospace;font-size:0.8rem}}'
        f'th{{color:#6b7c76;text-transform:uppercase;letter-spacing:.08em;font-size:.68rem;'
        f'padding:.4rem .8rem;border-bottom:1px solid #2a3330;text-align:left}}'
        f'td{{color:#e8ede9;padding:.4rem .8rem;border-bottom:1px solid #1e2422}}'
        f'tr:last-child td{{border-bottom:none}}</style>'
        f'<table><thead><tr><th>Period</th><th>Total Used</th><th>Daily Avg</th>'
        f'<th>Restocked</th><th>Active Days</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )


# PAGE: ADD ITEM

def page_add_item():
    st.markdown("<h1>Add New Item</h1>", unsafe_allow_html=True)
    st.caption("All fields marked * are required.")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        name     = st.text_input("Item Name *", placeholder="e.g. Whole Milk")
        org      = st.selectbox("Organisation *", options=list(VALID_ORGS),
                                format_func=lambda x: ORG_LABELS.get(x, x))
        item_type = st.selectbox("Item Type *", options=list(VALID_TYPES),
                                 format_func=lambda x: TYPE_LABELS.get(x, x))
        category = st.text_input("Category", placeholder="e.g. dairy, reagent, office_supply")
        unit     = st.text_input("Unit *", placeholder="e.g. liters, kg, units, boxes")

    with col2:
        current_qty     = st.number_input("Current Quantity *", min_value=0.0, step=1.0, value=10.0)
        reorder_threshold = st.number_input("Reorder Threshold *", min_value=0.0, step=1.0, value=3.0,
                                             help="Alert triggers below this quantity")
        reorder_qty     = st.number_input("Reorder Quantity", min_value=0.0, step=1.0, value=0.0,
                                          help="How much to order. Defaults to 3× threshold.")
        cost_per_unit   = st.number_input("Cost per Unit (₹)", min_value=0.0, step=1.0, value=0.0)

        has_expiry = st.checkbox("Has expiry date?", value=(item_type == "perishable"))
        expiry_date = None
        if has_expiry:
            expiry_date = st.date_input("Expiry Date",
                                        value=datetime.today() + timedelta(days=30),
                                        min_value=datetime.today())
            expiry_date = expiry_date.strftime("%Y-%m-%d")

    st.divider()

    if st.button("＋ Add Item", type="primary"):
        data = {
            "name": name,
            "org": org,
            "type": item_type,
            "category": category or "general",
            "unit": unit,
            "current_qty": current_qty,
            "reorder_threshold": reorder_threshold,
            "reorder_qty": reorder_qty if reorder_qty > 0 else reorder_threshold * 3,
            "cost_per_unit": cost_per_unit,
            "expiry_date": expiry_date,
        }
        updated_inv, errors = add_item(inv, data)
        if errors:
            for e in errors:
                st.error(f"✗ {e}")
        else:
            st.session_state.inventory = updated_inv
            get_forecasts.clear()
            st.success(f"✓ '{name}' added to inventory.")
            st.balloons()
            st.session_state.page = "inventory"
            st.rerun()


# PAGE: ALERTS

def page_alerts():
    st.markdown("<h1>Alerts</h1>", unsafe_allow_html=True)

    _of3 = st.session_state.get("org_filter", "all")
    disp_inv = inv if _of3 == "all" else [i for i in inv if i["org"] == _of3]
    disp_fc  = {i["id"]: forecasts.get(i["id"], {}) for i in disp_inv}
    disp_als = check_all_alerts(disp_inv, disp_fc)

    # Summary row
    by_sev = {s: [a for a in disp_als if a.severity == s] for s in Severity}
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 High",   len(by_sev[Severity.HIGH]))
    c2.metric("⚠️ Medium", len(by_sev[Severity.MEDIUM]))
    c3.metric("🔍 Low",    len(by_sev[Severity.LOW]))

    st.divider()

    if not disp_als:
        st.success("No alerts for the selected filter. Inventory looks healthy.")
        return

    type_groups = {}
    for alert in disp_als:
        type_groups.setdefault(alert.type, []).append(alert)

    type_order = [AlertType.EXPIRED, AlertType.WASTE_RISK, AlertType.STOCKOUT_RISK,
                  AlertType.CRITICAL_LOW]

    for atype in type_order:
        group = type_groups.get(atype, [])
        if not group:
            continue

        emoji = alert_emoji(atype)
        label = atype.value.replace("_", " ").title()
        st.markdown(f"<h2>{emoji} {label} ({len(group)})</h2>", unsafe_allow_html=True)

        for alert in group:
            css = sev_class(alert.severity)
            item = get_item(inv, alert.item_id)
            fc   = forecasts.get(alert.item_id, {})

            with st.expander(f"{alert.item_name} — {alert.title}"):
                st.markdown(
                    f'<div class="et-card {css}">'
                    f'<div style="font-size:0.85rem;line-height:1.6">{alert.message}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                if item:
                    avg_usage  = fc.get("avg_daily_usage", 0)
                    days_out   = fc.get("days_until_runout")
                    exp_days   = fc.get("expiry_days_remaining")
                    unit       = item["unit"]

                    # Restock suggestion (usage-based)
                    shelf_life = item.get("shelf_life_days")
                    if item["type"] == "perishable" and shelf_life:
                        TARGET_DAYS_STOCK = min(14, shelf_life - 1)
                        target_label = f"~{TARGET_DAYS_STOCK}d (shelf life)"
                    else:
                        TARGET_DAYS_STOCK = 14
                        target_label = "~14d"
                    if avg_usage and avg_usage > 0:
                        target_qty    = round(avg_usage * TARGET_DAYS_STOCK, 1)
                        on_hand       = item["current_qty"]
                        suggested_order = round(max(0, target_qty - on_hand), 1)
                        restock_note = (
                            f"Target stock: {target_qty} {unit} ({target_label}). "
                            f"You have {on_hand:.1f} {unit} — order {suggested_order} {unit}."
                        )
                    else:
                        suggested_order = float(item.get("reorder_qty", 0))
                        restock_note = None

                    # Routing: discard only if stock remains AND expired/waste
                    already_out   = item["current_qty"] <= 0
                    is_expired    = (exp_days is not None and exp_days <= 0)
                    is_waste_risk = atype == AlertType.WASTE_RISK
                    show_discard  = (is_expired or is_waste_risk) and not already_out

                    if show_discard:
                        waste_qty = item["current_qty"]
                        st.markdown(
                            f'<div class="et-card alert-high" style="margin-top:0.5rem">'
                            f'<div style="font-size:0.82rem;color:#f87171;margin-bottom:0.5rem">'
                            f'🚫 {waste_qty:.1f} {unit} will be discarded. This cannot be undone.</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        col_d, col_r = st.columns(2)
                        with col_d:
                            if st.button(f"🗑 Discard all ({waste_qty:.0f} {unit})",
                                         key=f"discard_{alert.item_id}_{atype}", type="primary"):
                                _sim_date = st.session_state.get("sim_current_date")
                                updated_inv, updated_hist, errors = update_quantity(
                                    inv, hist, alert.item_id, 0.0, "waste",
                                    current_date=_sim_date,
                                )
                                if errors:
                                    for e in errors: st.error(e)
                                else:
                                    st.session_state.inventory = updated_inv
                                    st.session_state.history   = updated_hist
                                    get_forecasts.clear()
                                    st.session_state.insight_cache = {}
                                    st.success(f"✓ Discarded {waste_qty:.0f} {unit} of {item['name']}")
                                    st.rerun()
                        with col_r:
                            st.markdown(
                                f'<div class="et-card" style="padding:0.6rem 0.8rem">'
                                f'<div class="et-label">Suggested Restock (after discarding)</div>'
                                f'<div style="color:#4ade80;font-size:1rem;font-weight:700;font-family:Syne,sans-serif">{suggested_order} {unit}</div>'
                                + (f'<div class="et-mono" style="font-size:0.72rem;margin-top:0.2rem">{restock_note}</div>' if restock_note else "")
                                + f'</div>',
                                unsafe_allow_html=True,
                            )

                        # Cross-org tip (café waste → donate to nonprofit)
                        _cross_scenario = get_cross_org_scenario(item, fc)
                        if _cross_scenario:
                            _cross_key = f"cross_{alert.item_id}"
                            _cross_icon = "🤝" if _cross_scenario == "cafe_donate" else "🥡"
                            _cross_label = {
                                "cafe_donate": "Donate surplus to non-profit?",
                                "nonprofit_expiry": "Redistribute before expiry?",
                            }.get(_cross_scenario, "Community action")
                            if st.button(f"{_cross_icon} {_cross_label}",
                                         key=f"cross_btn_{alert.item_id}_{atype}"):
                                with st.spinner("Thinking cross-org..."):
                                    _cross_result = generate_cross_org_tip(item, fc, inv)
                                    st.session_state.insight_cache[_cross_key] = _cross_result
                            if _cross_key in st.session_state.insight_cache:
                                _cr = st.session_state.insight_cache[_cross_key]
                                if _cr.get("tip"):
                                    _badge = "llm" if _cr["source"] == "llm" else "fallback"
                                    st.markdown(
                                        f'<div class="et-card" style="background:#0f1520;border-color:#2a3a50;margin-top:0.4rem">'
                                        f'<span class="ai-badge {_badge}">{"AI — Community Tip" if _badge=="llm" else "Community Tip"}</span>'
                                        f'<div style="margin-top:0.4rem;font-size:0.82rem;line-height:1.6;color:#a8b8b0">{_cr["tip"]}</div>'
                                        f'</div>',
                                        unsafe_allow_html=True,
                                    )

                    else:
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown(f'<div class="et-mono">Current: {fmt_qty(item["current_qty"], unit)}</div>', unsafe_allow_html=True)
                            if days_out is not None and days_out > 0:
                                st.markdown(f'<div class="et-mono">Runs out in: {days_out:.1f} days</div>', unsafe_allow_html=True)
                            if exp_days is not None and exp_days > 0:
                                st.markdown(f'<div class="et-mono">Expires in: {exp_days} days</div>', unsafe_allow_html=True)
                        with c2:
                            st.markdown(
                                f'<div class="et-card" style="padding:0.6rem 0.8rem">'
                                f'<div class="et-label">Suggested Restock</div>'
                                f'<div style="color:#4ade80;font-size:1rem;font-weight:700;font-family:Syne,sans-serif">{suggested_order} {unit}</div>'
                                + (f'<div class="et-mono" style="font-size:0.72rem;margin-top:0.2rem">{restock_note}</div>' if restock_note else "")
                                + f'</div>',
                                unsafe_allow_html=True,
                            )
                        restock_qty = st.number_input(
                            "Restock amount", value=float(suggested_order),
                            min_value=0.0, step=1.0, key=f"alt_qty_{alert.item_id}_{atype}"
                        )
                        new_total = item["current_qty"] + restock_qty
                        if st.button(f"+ Restock {restock_qty:.0f} {unit}",
                                     key=f"alt_upd_{alert.item_id}_{atype}", type="primary"):
                            _sim_date = st.session_state.get("sim_current_date")
                            updated_inv, updated_hist, errors = update_quantity(
                                inv, hist, alert.item_id, new_total, "restock",
                                current_date=_sim_date,
                            )
                            if errors:
                                for e in errors: st.error(e)
                            else:
                                st.session_state.inventory = updated_inv
                                st.session_state.history   = updated_hist
                                get_forecasts.clear()
                                st.session_state.insight_cache = {}
                                st.success(f"Restocked — new qty: {new_total:.1f} {unit}")
                                st.rerun()

                        # Sustainable supplier suggestion
                        sugg_key = f"sugg_{alert.item_id}"
                        if st.button("🌱 Sustainable sourcing tips",
                                     key=f"sugg_btn_{alert.item_id}_{atype}"):
                            with st.spinner("Finding sustainable options..."):
                                sugg = suggest_suppliers(item)
                                st.session_state.insight_cache[sugg_key] = sugg
                        if sugg_key in st.session_state.insight_cache:
                            _sugg = st.session_state.insight_cache[sugg_key]
                            _badge = "llm" if _sugg["source"] == "llm" else "fallback"
                            st.markdown(
                                f'<div class="et-card" style="background:#0f1a14;border-color:#2a4a32;margin-top:0.4rem">'
                                f'<span class="ai-badge {_badge}">{"AI Suggestion" if _badge=="llm" else "Fallback Tip"}</span>'
                                f'<div style="margin-top:0.4rem;font-size:0.82rem;line-height:1.6;color:#a8b8b0">{_sugg["suggestion"]}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                        # Cross-org tip (nonprofit stockout → solicit donations)
                        _cross_scenario = get_cross_org_scenario(item, fc)
                        if _cross_scenario == "nonprofit_solicit":
                            _cross_key = f"cross_{alert.item_id}"
                            if st.button("📢 Donation drive ideas",
                                         key=f"cross_btn_{alert.item_id}_{atype}"):
                                with st.spinner("Generating community appeal ideas..."):
                                    _cross_result = generate_cross_org_tip(item, fc, inv)
                                    st.session_state.insight_cache[_cross_key] = _cross_result
                            if _cross_key in st.session_state.insight_cache:
                                _cr = st.session_state.insight_cache[_cross_key]
                                if _cr.get("tip"):
                                    _badge = "llm" if _cr["source"] == "llm" else "fallback"
                                    st.markdown(
                                        f'<div class="et-card" style="background:#0f1520;border-color:#2a3a50;margin-top:0.4rem">'
                                        f'<span class="ai-badge {_badge}">{"AI — Community Tip" if _badge=="llm" else "Community Tip"}</span>'
                                        f'<div style="margin-top:0.4rem;font-size:0.82rem;line-height:1.6;color:#a8b8b0">{_cr["tip"]}</div>'
                                        f'</div>',
                                        unsafe_allow_html=True,
                                    )

        st.divider()



# PAGE: ANALYTICS

def page_analytics():
    from datetime import datetime as _dt
    TODAY_STR = _dt.today().strftime("%Y-%m-%d")

    sim_active = st.session_state.sim_active
    sim_d      = st.session_state.sim_days

    subtitle = (
        f"Showing historical data + {sim_d}-day simulation window"
        if sim_active else
        "Historical usage trends over the last 45 days — use Developer Mode to simulate forward"
    )
    st.markdown("<h1>Analytics</h1>", unsafe_allow_html=True)
    st.markdown(f'<p class="et-mono" style="color:#6b7c76;margin-top:-0.5rem">{subtitle}</p>', unsafe_allow_html=True)

    if sim_active:
        st.markdown(
            f'<div class="dev-mode-banner">⏩ Simulation active — +{sim_d} days. Simulated entries shown in a different colour on the chart.</div>',
            unsafe_allow_html=True,
        )

    #Item selector (filtered by selected org)
    _org_filter = st.session_state.get("org_filter", "all")
    if _org_filter == "all":
        trackable = [i for i in inv if i["type"] != "non_expiry"]
    else:
        trackable = [i for i in inv if i["type"] != "non_expiry" and i["org"] == _org_filter]

    if not trackable:
        st.info("No trackable items for the selected organisation.")
        return

    item_names = [i["name"] for i in trackable]
    sel_name = st.selectbox("Select item", item_names, label_visibility="collapsed")
    sel_item = next(i for i in trackable if i["name"] == sel_name)
    item_id  = sel_item["id"]

    item_hist = sorted(
        [r for r in hist if r["item_id"] == item_id],
        key=lambda r: r["date"]
    )

    st.divider()

    if not item_hist:
        st.info("No usage history for this item yet.")
        return

    # Split historical vs simulated
    fc = forecasts.get(item_id, {})
    hist_records = [r for r in item_hist if r.get("event") != "simulated"]
    sim_records  = [r for r in item_hist if r.get("event") == "simulated"]

    dates         = [r["date"] for r in item_hist]
    usage_vals    = [r["quantity_used"] for r in item_hist]
    restock_vals  = [r.get("restock_qty", 0) for r in item_hist]
    events        = [r.get("event", "normal") for r in item_hist]

    sim_start_index = len(hist_records) if sim_records else None

    current = sel_item["current_qty"]
    running = []
    qty = current
    for usage, restock in zip(reversed(usage_vals), reversed(restock_vals)):
        qty = qty + usage - restock
        running.append(round(qty, 2))
    running = list(reversed(running))

    # Summary metrics row
    total_used    = sum(usage_vals)
    total_restock = sum(restock_vals)
    restock_events = sum(1 for e in events if e == "restock")
    bulk_events    = sum(1 for e in events if e == "bulk_order")
    avg_daily      = fc.get("avg_daily_usage", 0)
    active_days    = sum(1 for v in usage_vals if v > 0)

    c1, c2, c3, c4, c5 = st.columns(5)
    period_label = f"Total Used ({len(item_hist)}d)"
    c1.metric(period_label, f"{total_used:.1f} {sel_item['unit']}")
    c2.metric("Avg Daily Usage",    f"{avg_daily:.2f} {sel_item['unit']}")
    c3.metric("Active Days",        f"{active_days} / {len(item_hist)}")
    c4.metric("Restock Events",     restock_events)
    c5.metric("Bulk Spikes",        bulk_events)

    st.divider()

    # Chart 1: Stock level over time (area)
    chart_title = "Stock Level Over Time"
    if sim_active and sim_start_index:
        chart_title += f" (grey = simulated {sim_d}d)"
    st.markdown(f"<h2>{chart_title}</h2>", unsafe_allow_html=True)

    labels_js    = str(dates)
    running_js   = str(running)
    usage_js     = str(usage_vals)
    restock_js   = str(restock_vals)
    threshold_js = str(sel_item["reorder_threshold"])
    unit         = sel_item["unit"]

    restock_indices = [i for i, e in enumerate(events) if e == "restock"]
    bulk_indices    = [i for i, e in enumerate(events) if e == "bulk_order"]
    sim_start_js    = sim_start_index if sim_start_index is not None else len(dates)

    chart_html = f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  body {{ margin: 0; background: #0f1110; font-family: 'DM Mono', monospace; }}
  .chart-wrap {{ padding: 16px; }}
  canvas {{ max-height: 280px; }}
  .legend {{ display: flex; gap: 20px; padding: 8px 0 0 0; font-size: 11px; color: #6b7c76; }}
  .legend-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; }}
</style>
</head>
<body>
<div class="chart-wrap">
  <canvas id="stockChart"></canvas>
  <div class="legend">
    <span><span class="legend-dot" style="background:#4ade80"></span>Stock level</span>
    <span><span class="legend-dot" style="background:#60a5fa"></span>Daily usage</span>
    <span><span class="legend-dot" style="background:#f97316"></span>Restock event</span>
  </div>
</div>
<script>
const labels = {labels_js};
const stockData = {running_js};
const usageData = {usage_js};
const restockData = {restock_js};
const threshold = {threshold_js};

// Point colors: orange for restock, yellow for bulk, default for normal
const pointColors = labels.map((_, i) => {{
  if ({restock_indices}.includes(i)) return '#f97316';
  if ({bulk_indices}.includes(i)) return '#fcd34d';
  return 'rgba(74,222,128,0)';
}});
const pointRadius = labels.map((_, i) => {{
  if ({restock_indices}.includes(i) || {bulk_indices}.includes(i)) return 5;
  return 0;
}});

const ctx = document.getElementById('stockChart').getContext('2d');
new Chart(ctx, {{
  type: 'line',
  data: {{
    labels,
    datasets: [
      {{
        label: 'Stock Level ({unit})',
        data: stockData,
        borderColor: labels.map((_, i) => i >= {sim_start_js} ? '#4b5563' : '#4ade80'),
        segment: {{ borderColor: (ctx) => ctx.p0DataIndex >= {sim_start_js} ? '#4b5563' : '#4ade80' }},
        backgroundColor: 'rgba(74,222,128,0.06)',
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointBackgroundColor: pointColors,
        pointRadius: pointRadius,
        pointHoverRadius: 5,
      }},
      {{
        label: 'Daily Usage ({unit})',
        data: usageData,
        borderColor: '#60a5fa',
        backgroundColor: 'rgba(96,165,250,0.06)',
        borderWidth: 1.5,
        fill: false,
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 4,
        yAxisID: 'y2',
      }},
    ]
  }},
  options: {{
    responsive: true,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        backgroundColor: '#1e2422',
        borderColor: '#2a3330',
        borderWidth: 1,
        titleColor: '#e8ede9',
        bodyColor: '#a8b8b0',
        callbacks: {{
          afterBody: (items) => {{
            const i = items[0].dataIndex;
            const r = restockData[i];
            const lines = [];
            if ({restock_indices}.includes(i)) lines.push(`↑ Restock: +${{r}} {unit}`);
            if ({bulk_indices}.includes(i)) lines.push('⚡ Bulk spike event');
            return lines;
          }}
        }}
      }}
    }},
    scales: {{
      x: {{
        ticks: {{ color: '#6b7c76', maxTicksLimit: 10, font: {{ size: 10 }} }},
        grid: {{ color: '#1e2422' }},
      }},
      y: {{
        position: 'left',
        ticks: {{ color: '#4ade80', font: {{ size: 10 }} }},
        grid: {{ color: '#1e2422' }},
        title: {{ display: true, text: 'Stock ({unit})', color: '#6b7c76', font: {{ size: 10 }} }},
      }},
      y2: {{
        position: 'right',
        ticks: {{ color: '#60a5fa', font: {{ size: 10 }} }},
        grid: {{ drawOnChartArea: false }},
        title: {{ display: true, text: 'Daily Usage ({unit})', color: '#6b7c76', font: {{ size: 10 }} }},
      }}
    }}
  }}
}});
</script>
</body>
</html>
"""
    st.components.v1.html(chart_html, height=340)

    st.divider()

    # Chart 2: Usage distribution (bar) + restock timeline
    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown("<h2>Daily Usage Distribution</h2>", unsafe_allow_html=True)

        recent_dates  = dates[-21:]
        recent_usage  = usage_vals[-21:]
        recent_events = events[-21:]

        bar_colors = []
        for e in recent_events:
            if e == "restock":    bar_colors.append("#f97316")
            elif e == "bulk_order": bar_colors.append("#fcd34d")
            else:                 bar_colors.append("#4ade80")

        bar_html = f"""
<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>body{{margin:0;background:#0f1110;}} canvas{{max-height:220px;}}</style>
</head><body>
<div style="padding:12px">
<canvas id="barChart"></canvas>
</div>
<script>
new Chart(document.getElementById('barChart'), {{
  type: 'bar',
  data: {{
    labels: {str(recent_dates)},
    datasets: [{{
      label: 'Usage ({unit})',
      data: {str(recent_usage)},
      backgroundColor: {str(bar_colors)},
      borderRadius: 2,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: false }},
      tooltip: {{ backgroundColor:'#1e2422', borderColor:'#2a3330', borderWidth:1,
                  titleColor:'#e8ede9', bodyColor:'#a8b8b0' }} }},
    scales: {{
      x: {{ ticks: {{ color:'#6b7c76', maxTicksLimit:7, font:{{size:9}} }}, grid:{{color:'#1e2422'}} }},
      y: {{ ticks: {{ color:'#a8b8b0', font:{{size:10}} }}, grid:{{color:'#1e2422'}} }}
    }}
  }}
}});
</script></body></html>
"""
        st.components.v1.html(bar_html, height=260)

    with col_r:
        st.markdown("<h2>Restock Log</h2>", unsafe_allow_html=True)
        restock_records = [
            (r["date"], r.get("restock_qty", 0), r.get("event",""))
            for r in item_hist if r.get("restock_qty", 0) > 0
        ]
        if restock_records:
            for date, qty_r, ev in reversed(restock_records[-10:]):
                label = "restock" if ev == "restock" else ev
                card = (
                    f'<div class="et-card" style="padding:0.5rem 0.8rem;margin-bottom:0.3rem;display:flex;justify-content:space-between;align-items:center">'
                    f'<span class="et-mono" style="font-size:0.75rem;color:#6b7c76">{date}</span>'
                    f'<span style="color:#f97316;font-family:Syne,sans-serif;font-size:0.85rem;font-weight:600">+{qty_r:.0f} {unit}</span>'
                    f'</div>'
                )
                st.markdown(card, unsafe_allow_html=True)
        else:
            st.caption("No restock events in the last 45 days.")

    st.divider()

    # Consumption stats table
    st.markdown("<h2>Consumption Breakdown</h2>", unsafe_allow_html=True)

    # Weekly buckets
    from datetime import datetime as dt
    weekly = {}
    for r in item_hist:
        week = dt.strptime(r["date"], "%Y-%m-%d").isocalendar()[1]
        weekly.setdefault(week, {"used": 0, "restocked": 0, "days": 0})
        weekly[week]["used"]      += r["quantity_used"]
        weekly[week]["restocked"] += r.get("restock_qty", 0)
        if r["quantity_used"] > 0:
            weekly[week]["days"] += 1

    weeks = sorted(weekly.keys())
    rows_html = ""
    for i, w in enumerate(weeks):
        d = weekly[w]
        avg = d["used"] / max(d["days"], 1)
        label = f"Week {i+1}"
        rows_html += (
            f'<tr>'
            f'<td>{label}</td>'
            f'<td style="color:#4ade80">{d["used"]:.1f} {unit}</td>'
            f'<td style="color:#60a5fa">{avg:.2f} {unit}/day</td>'
            f'<td style="color:#f97316">{d["restocked"]:.0f} {unit}</td>'
            f'<td style="color:#a8b8b0">{d["days"]} days</td>'
            f'</tr>'
        )

    table_html = f"""
<style>
table {{ width:100%; border-collapse:collapse; font-family:'DM Mono',monospace; font-size:0.8rem; }}
th {{ color:#6b7c76; text-transform:uppercase; letter-spacing:0.08em; font-size:0.68rem;
     padding:0.4rem 0.8rem; border-bottom:1px solid #2a3330; text-align:left; }}
td {{ color:#e8ede9; padding:0.4rem 0.8rem; border-bottom:1px solid #1e2422; }}
tr:last-child td {{ border-bottom: none; }}
</style>
<table>
<thead><tr>
  <th>Period</th><th>Total Used</th><th>Daily Avg</th><th>Restocked</th><th>Active Days</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>
"""
    st.markdown(table_html, unsafe_allow_html=True)


# ROUTER

page = st.session_state.page

if page == "dashboard":
    page_dashboard()
elif page == "inventory":
    page_inventory()
elif page == "analytics":
    page_analytics()
elif page == "add_item":
    page_add_item()
elif page == "alerts":
    page_alerts()
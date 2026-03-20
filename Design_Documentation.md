# 🌿 EcoTrack AI — Green-Tech Inventory Assistant


A lightweight, AI-powered inventory assistant built for sustainability-minded organisations. EcoTrack helps small cafés, community non-profits, and university labs track perishable stock, predict waste before it happens, and make smarter procurement decisions without the complexity or cost of enterprise software.


---

## Problem Statement

Small organisations managing physical inventory face a common failure pattern: manual spreadsheet tracking leads to over-purchasing, items expire unnoticed, and there is no early warning system for waste until money is already lost. Existing enterprise solutions are too expensive and too complex for a café manager or a non-profit coordinator to operate day-to-day.

EcoTrack solves this with three things: a usage-based forecast that tells you when stock will run out *before* it does, an alert system that flags waste risk and stockout risk in plain language, and an AI layer that synthesises all of it into a one-sentence action with a rule-based fallback that is used in case the AI is unavailable.

---

## Target Audiences

| Organisation | Key items tracked | Usage pattern |
|---|---|---|
| ☕ **Café** | Milk, Sourdough, Cold Brew, Oat Milk, Cream | Weekend spikes (+20-55%), high turnover |
| 🤝 **Non-Profit** | Donated Canned Food, Sanitiser, Paper, First Aid Kits | Weekend zero-usage days (50% probability) |
| 🔬 **University Lab** | Ethanol, PBS, Trypsin-EDTA, Gloves, Petri Dishes | Mostly closed weekends (80% probability) |

---

## Features

### Core Inventory Flow
- Add, view, update, and delete items with full input validation and clear error messages
- Search by name or category; filter by organisation, item type, and alert state; sort by severity, name, expiry, or quantity
- Quantity update with reason logging (usage, restock, waste, correction)
- Restock correctly refreshes expiry date using `shelf_life_days` — no stale expiry dates after restocking

### Forecasting Engine
- **Weighted Moving Average (WMA)** over the last 45 days of usage history — more recent data is weighted higher
- Zero-usage days (closed days, weekends) are excluded from the average to avoid downward bias
- Restock spike cleaning — large one-off quantities in history do not inflate the daily average
- **FIFO-aware waste calculation** — when you restock with old stock still on the shelf, waste risk is calculated per batch, not against the blended total
- Confidence levels: `none` / `low` / `medium` / `high` based on data points available
- Rule-based fallback when fewer than 3 non-zero data points exist

### Alert System
Four alert types, fully deterministic, no AI required:
- **WASTE_RISK** — stock will expire before it can be used at current rate
- **STOCKOUT_RISK** — stock will run out within 7 days, or already below reorder threshold
- **EXPIRED** — item has passed expiry date with stock remaining (suppressed if qty = 0)
- **CRITICAL_LOW** — below reorder threshold, not yet at stockout risk

### AI Capability: Summarise
Three distinct LLM calls, all with explicit fallbacks:

| Function | What it does |
|---|---|
| `generate_insight()` | Per-item insight: waste cost in ₹, procurement tip, exact numbers |
| `generate_daily_brief()` | Org-level daily brief: most urgent action, ₹ at risk, stock health summary |
| `suggest_suppliers()` | Sustainable sourcing tips on stockout alerts, category-aware |

Every AI output displays a visible badge: **AI Generated** or **Rule-based Fallback** so the user always knows which mode is active.

### Cross-Org Intelligence
EcoTrack understands that its three audiences exist in the same community:
- **Café waste risk** → "🤝 Donate surplus to non-profit?" button with donation logistics tip
- **Non-profit stockout** → "📢 Donation drive ideas" button with social media and local business appeal suggestions
- **Non-profit perishable expiry** → "🥡 Redistribute before expiry?" button with food drive and package deal ideas

### Developer Mode (Time Simulation)
- Simulate 1–30 days forward with a slider
- Per-item usage overrides: set exact total consumption for the period
- Mid-simulation expiry enforcement: items zero out on the correct day, waste events logged with date and quantity
- Chained simulations work correctly — each run starts from where the last ended
- Full reset restores original JSON state

### Live Mode (Real Inventory Counts)
- Date-picker defaults to today, can record for any date
- Enter actual on-hand quantities for all items; only changed items are saved
- Save button shows count before committing: "Save 3 change(s) for 2026-03-21"
- Restock detection automatically refreshes expiry date using shelf life

### Analytics
- Stock level over time (area chart, Chart.js) with simulated vs historical shading
- Daily usage bar chart with restock and bulk-spike event markers
- Restock log with dates and quantities
- Weekly consumption breakdown table
- All charts filtered by selected organisation

### Sustainability Panel
- Potential waste value in ₹ across all at-risk perishables
- Items on track vs items at risk counts
- Waste-at-risk table: item, units at risk, estimated ₹ loss

---

## AI Design Decisions

**Why LLM for summarisation, not pure ML?**
The forecasting is entirely statistical (WMA). The AI layer's job is not to predict but to synthesise structured forecast data, alert states, and org context into a natural-language action that a non-technical user can act on immediately. This is a summarisation task, which LLMs handle well. A rule-based template can approximate it for the fallback case.

**Why Groq / llama-3.3-70b-versatile?**
Fast inference, generous free tier suitable for a demo, and the model handles structured JSON context reliably. The provider and model are swappable the `generate_insight()` interface is the only coupling point.

**Responsible AI practices:**
- Every AI output is labelled with its source (LLM vs fallback) — the user is never misled about what generated the text
- Confidence labels on every forecast (`none` / `low` / `medium` / `high`) so users know how much to trust the numbers
- The fallback produces genuinely useful output, not just an error message so the app is fully functional without an API key
- LLM prompts include org context so advice is appropriate to a lab, a café, or a non-profit rather than a generic statement

---

## Architecture

```
ecotrack/
├── app/
│   ├── main.py          ← Streamlit UI — all pages, sidebar, session state
│   ├── forecasting.py   ← WMA engine, simulate_days_forward, FIFO waste calc
│   ├── alerts.py        ← Rule-based alert engine (no AI dependency)
│   ├── insights.py      ← Groq LLM: generate_insight, generate_daily_brief,
│   │                       suggest_suppliers, generate_cross_org_tip
│   └── inventory.py     ← CRUD, validation, search_and_filter, update_quantity
├── data/
│   ├── generate_synthetic_data.py  ← Generates 25 items, 1035 history records
│   ├── inventory.json              ← Sample data (checked into repo)
│   └── usage_history.json          ← Sample data (checked into repo)
├── tests/
│   └── test_ecotrack.py  ← 31 tests, plain Python, no pytest required
├── .env.example
├── requirements.txt
└── README.md
```

**Data flow:**
`inventory.json` + `usage_history.json` → `forecasting.py` (WMA) → `alerts.py` (rule engine) → `insights.py` (LLM summarise) → `main.py` (Streamlit UI)

**Persistence:** JSON flat files. `load_inventory()` and `save_inventory()` in `inventory.py` are the only I/O layer — swapping to SQLite or PostgreSQL requires changing only those two functions, with zero changes elsewhere.

---

**Test coverage:**
- WMA forecast accuracy and recent-data bias
- Waste risk and stockout risk detection
- Zero-usage day exclusion from average
- Spike outlier cleaning
- FIFO waste suppression on empty stock and zero-qty items
- Alert routing (all 4 alert types)
- Multi-org filtering
- Input validation (5 cases: name, org, type, quantity, date format)
- Fallback insight generation without API key

---

## Synthetic Data

All data is generated by `data/generate_synthetic_data.py`. The generator:
- Creates 25 items across 3 organisations with realistic categories, units, costs, and shelf lives
- Generates 45 days of usage history per item with org-aware patterns (lab weekend closure, café weekend spikes, non-profit irregular usage)
- Inserts realistic restock events and occasional bulk-order spikes
- Runs a day-0 health check after generation to confirm no false alerts exist before any simulation

The `inventory.json` and `usage_history.json` in the repo are the output of running this script with `random.seed(42)` and today's date as the baseline.

---

## Security

- API key stored in `.env`, never committed
- `.env` is in `.gitignore`
- `.env.example` provided with placeholder: `GROQ_API_KEY=your_key_here`
- No external API calls except to Groq's completions endpoint, and only when the key is present

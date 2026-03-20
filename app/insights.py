import os
import json
from alerts import AlertType, Severity

try:
    import groq
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False

ORG_CONTEXT = {
    "cafe": "a small sustainability-focused café trying to reduce food waste and costs",
    "nonprofit": "a community non-profit managing donated goods and limited office supplies",
    "university_lab": "a university research laboratory managing chemicals, reagents, and lab consumables",
}

ITEM_TYPE_GUIDANCE = {
    "perishable": "Focus on waste prevention and timely usage. Expiry is a hard deadline.",
    "consumable": "Focus on avoiding stockouts. Reorder lead time matters.",
    "non_expiry": "Flag if quantity is critically low. No urgency otherwise.",
}


def fallback_insight(item: dict, forecast: dict, alerts: list) -> str:
    name = item["name"]
    qty = item["current_qty"]
    unit = item["unit"]
    days_out = forecast.get("days_until_runout")
    expiry_days = forecast.get("expiry_days_remaining")
    waste_risk = forecast.get("waste_risk", False)
    stockout_risk = forecast.get("stockout_risk", False)
    confidence = forecast.get("confidence", "none")
    avg_usage = forecast.get("avg_daily_usage", 0)
    waste_units = forecast.get("estimated_waste_units")

    parts = []

    # Stock status
    if days_out is not None:
        parts.append(f"At current usage ({avg_usage:.1f} {unit}/day), **{name}** will last approximately **{days_out:.1f} days**.")
    else:
        parts.append(f"**{name}** has {qty} {unit} remaining.")

    # Expiry
    if expiry_days is not None:
        if expiry_days <= 0:
            parts.append(f"This item has **expired**.")
        else:
            parts.append(f"It expires in **{expiry_days} days**.")

    # Waste risk
    if waste_risk and waste_units:
        parts.append(f"**Waste risk**: ~{waste_units} {unit} may go unused before expiry. Consider reducing next order quantity.")

    # Stockout
    if stockout_risk:
        reorder = item.get("reorder_qty", "N/A")
        parts.append(f"**Stockout risk**: Consider reordering {reorder} {unit} soon.")

    # Confidence caveat
    if confidence in ("none", "low"):
        n = forecast.get("data_points_used", 0)
        model = forecast.get("model_used", "fallback")
        note = "Rule-based fallback used." if model == "fallback" else "Log more usage to improve accuracy."
        parts.append(f"_Note: Forecast confidence is {confidence} ({n} data point(s)). {note}_")

    return " ".join(parts) if parts else f"No significant issues detected for {name}."


def generate_insight(item: dict, forecast: dict, alerts: list) -> dict:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key or not _GROQ_AVAILABLE:
        return {
            "insight": fallback_insight(item, forecast, alerts),
            "source": "fallback",
            "error": "No API key found or groq package not installed. Using rule-based fallback.",
        }

    alert_summaries = [
        {"type": a.type, "severity": a.severity, "message": a.message}
        for a in alerts
    ]

    context = {
        "item": {
            "name": item["name"],
            "type": item["type"],
            "category": item["category"],
            "current_qty": item["current_qty"],
            "unit": item["unit"],
            "reorder_threshold": item.get("reorder_threshold"),
            "reorder_qty": item.get("reorder_qty"),
            "cost_per_unit": item.get("cost_per_unit"),
        },
        "forecast": {
            "days_until_runout": forecast.get("days_until_runout"),
            "avg_daily_usage": forecast.get("avg_daily_usage"),
            "expiry_days_remaining": forecast.get("expiry_days_remaining"),
            "waste_risk": forecast.get("waste_risk"),
            "stockout_risk": forecast.get("stockout_risk"),
            "estimated_waste_units": forecast.get("estimated_waste_units"),
            "confidence": forecast.get("confidence"),
            "model_used": forecast.get("model_used"),
        },
        "active_alerts": alert_summaries,
        "org_type": item.get("org"),
        "org_context": ORG_CONTEXT.get(item.get("org", ""), "an organization"),
        "item_type_guidance": ITEM_TYPE_GUIDANCE.get(item.get("type", ""), ""),
    }

    prompt = f"""You are a sustainability-focused inventory assistant for {context['org_context']}.
Your primary goal is helping this organisation reduce waste, save money, and make smarter procurement decisions.

Item data:
{json.dumps(context, indent=2)}

Write a 2-4 sentence insight for the manager of this organisation. Think like an experienced operator in their domain, not a data analyst.

Rules:
- Lead with the single most important action to take RIGHT NOW
- If waste_risk is true: tell them exactly how much will be wasted in monetary terms if they do nothing (estimated_waste_units × cost_per_unit), and suggest a specific way to use it up (e.g. daily special, staff consumption, reduce next order)
- If stockout_risk is true: tell them when they'll run out and the minimum they should order to avoid running dry
- If both risks exist: waste takes priority for perishables — running out of milk is recoverable, throwing it away is not
- If everything is fine: say so in one sentence, no padding
- Never say "based on the data" or "according to the forecast" — just state the facts directly
- Use actual numbers. Never round aggressively — say "3.2 liters" not "about 3 liters"
- End with one concrete procurement tip if relevant (e.g. "Consider ordering every 5 days instead of weekly")"""

    try:
        client = groq.Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        insight_text = response.choices[0].message.content.strip()

        return {
            "insight": insight_text,
            "source": "llm",
            "error": None,
        }

    except Exception as e:
        return {
            "insight": fallback_insight(item, forecast, alerts),
            "source": "fallback",
            "error": f"LLM unavailable: {str(e)}",
        }


def generate_daily_brief(
    org: str,
    inventory: list[dict],
    forecasts: dict,
    all_alerts: list,
) -> dict:
    api_key = os.getenv("GROQ_API_KEY")

    high_alerts = [a for a in all_alerts if a.severity == Severity.HIGH]
    waste_items = [a.item_name for a in all_alerts if a.type == AlertType.WASTE_RISK]
    stockout_items = [a.item_name for a in all_alerts if a.type == AlertType.STOCKOUT_RISK]
    expired_items = [a.item_name for a in all_alerts if a.type == AlertType.EXPIRED]

    # Fallback brief
    def _fallback_brief():
        lines = [f"**Daily Inventory Brief — {ORG_CONTEXT.get(org, org)}**\n"]
        lines.append(f"Tracking **{len(inventory)}** items across your inventory.\n")
        if expired_items:
            lines.append(f"**Expired items** requiring immediate removal: {', '.join(expired_items)}.\n")
        if waste_items:
            lines.append(f"**Waste risk** on: {', '.join(waste_items)}. Consider reducing order quantities.\n")
        if stockout_items:
            lines.append(f"**Stockout risk** on: {', '.join(stockout_items)}. Reorder recommended.\n")
        if not high_alerts:
            lines.append("No critical issues detected this week.")
        return "".join(lines)

    if not api_key or not _GROQ_AVAILABLE:
        return {"brief": _fallback_brief(), "source": "fallback", "error": "No API key or groq package not installed."}

    waste_cost_total = 0.0
    waste_details = []
    for item in inventory:
        fc = forecasts.get(item["id"], {})
        if fc.get("waste_risk") and fc.get("estimated_waste_units", 0) > 0:
            cost = item.get("cost_per_unit", 0) * fc["estimated_waste_units"]
            waste_cost_total += cost
            waste_details.append({
                "item": item["name"],
                "waste_units": fc["estimated_waste_units"],
                "unit": item["unit"],
                "estimated_cost": round(cost, 2),
            })

    summary_data = {
        "org_context": ORG_CONTEXT.get(org, org),
        "total_items": len(inventory),
        "high_severity_alerts": len(high_alerts),
        "expired_items": expired_items,
        "waste_risk_items": waste_items,
        "stockout_risk_items": stockout_items,
        "potential_waste_cost_total": round(waste_cost_total, 2),
        "waste_details": waste_details,
        "items_below_threshold": [
            i["name"] for i in inventory
            if i["current_qty"] <= i.get("reorder_threshold", 0)
        ],
    }

    prompt = f"""You are a sustainability advisor for {ORG_CONTEXT.get(org, org)}.
Your job is to give the manager a sharp, practical daily briefing — what needs attention RIGHT NOW today.

Today's inventory snapshot:
{json.dumps(summary_data, indent=2)}

Write a 3-5 sentence daily brief. Structure it like this:
1. Open with the single most urgent thing to act on today (expired > waste risk > stockout)
2. If waste_details is non-empty, state the ₹ value at risk (potential_waste_cost_total) and name the specific items
3. Give 1-2 concrete actions for today: what to use up, what to order now, what to skip ordering
4. Close with one sentence on overall stock health

Rules:
- This is a daily brief, not a weekly report — use today-focused language ("Order milk today", "Use up the sourdough by tonight")
- Talk like a trusted advisor, not a system notification
- Use exact numbers from the data — never round or say "about"
- Never say "based on the data" or "according to the forecast"
- If everything is healthy, say so in 2 warm sentences and give one tip to stay ahead of waste"""

    try:
        client = groq.Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=250,
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "brief": response.choices[0].message.content.strip(),
            "source": "llm",
            "error": None,
        }
    except Exception as e:
        return {"brief": _fallback_brief(), "source": "fallback", "error": str(e)}


def suggest_suppliers(item: dict) -> dict:
    api_key = os.getenv("GROQ_API_KEY")

    org_ctx = ORG_CONTEXT.get(item.get("org", ""), "a small organization")

    def _fallback_suggestion():
        name = item["name"]
        cat  = item["category"]
        tips = {
            "dairy":             f"Source {name} from local dairy cooperatives. Buy smaller batches more frequently to reduce waste.",
            "dairy_alternative": f"Consider bulk purchasing {name} with longer shelf life. Compare Tetra Pak vs fresh options.",
            "beverage":          f"For {name}, look for Fair Trade certified suppliers. Buying slightly less more often reduces waste.",
            "bakery":            f"Partner with a local bakery for {name} on a daily order basis to eliminate over-purchasing.",
            "chemical":          f"Order {name} in smaller quantities to reduce expiry waste. Check supplier minimum order quantities.",
            "reagent":           f"Pool orders with other labs for {name} to get bulk pricing without over-stocking.",
            "ppe":               f"Source {name} from certified sustainable manufacturers. Consider reusable alternatives where safe.",
            "packaging":         f"Switch to compostable or recycled alternatives for {name}. Many suppliers offer eco-certified options.",
        }
        return tips.get(cat, f"Source {name} from verified local suppliers. Request smaller, more frequent deliveries to reduce waste and storage costs.")

    if not api_key or not _GROQ_AVAILABLE:
        return {"suggestion": _fallback_suggestion(), "source": "fallback", "error": None}

    prompt = f"""You are a sustainable procurement advisor for {org_ctx}.

Item that needs restocking: {item['name']}
Category: {item['category']}
Type: {item['type']}
Unit: {item['unit']}

Give 2-3 short, practical procurement tips focused on:
1. Where to source sustainably (local, Fair Trade, certified, cooperative)
2. How to order smarter to reduce waste (frequency, quantity, batch size)
3. Any eco-friendly alternatives worth considering

Keep it to 3 sentences max. Be specific and actionable. No bullet points."""

    try:
        client = groq.Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "suggestion": response.choices[0].message.content.strip(),
            "source": "llm",
            "error": None,
        }
    except Exception as e:
        return {"suggestion": _fallback_suggestion(), "source": "fallback", "error": str(e)}


# Categories the nonprofit can meaningfully receive as donations
DONATABLE_CATEGORIES = {"dairy", "bakery", "beverage", "dairy_alternative", "food_donation", "flavouring"}

def get_cross_org_scenario(item: dict, forecast: dict) -> str | None:
    org  = item.get("org")
    itype = item.get("type")
    cat  = item.get("category", "")

    if org == "cafe" and forecast.get("waste_risk") and cat in DONATABLE_CATEGORIES:
        return "cafe_donate"

    if org == "nonprofit":
        if forecast.get("stockout_risk"):
            return "nonprofit_solicit"
        if itype == "perishable" and (forecast.get("expiry_days_remaining") or 99) <= 14 and item.get("current_qty", 0) > 0:
            return "nonprofit_expiry"

    return None


def _fallback_cross_org(item: dict, forecast: dict, scenario: str) -> str:
    name      = item["name"]
    qty       = item["current_qty"]
    unit      = item["unit"]
    exp_days  = forecast.get("expiry_days_remaining")
    waste_qty = forecast.get("estimated_waste_units", 0)

    if scenario == "cafe_donate":
        return (
            f"**Donation opportunity:** ~{waste_qty} {unit} of {name} is at risk of going to waste. "
            f"Consider donating the surplus to a local food bank or community nonprofit before it expires — "
            f"this reduces waste costs and counts as a charitable contribution."
        )
    elif scenario == "nonprofit_solicit":
        return (
            f"**Low stock alert:** {name} is running low. Consider posting a donation request on your "
            f"social channels or sending a targeted appeal to regular donors and local businesses who may have surplus stock."
        )
    elif scenario == "nonprofit_expiry":
        return (
            f"**Expiry action needed:** {qty} {unit} of {name} expires in {exp_days} day(s). "
            f"Organise a food drive, community package deal, or partner with a local café to redistribute "
            f"before the deadline. This avoids waste and builds community goodwill."
        )
    return ""


def generate_cross_org_tip(item: dict, forecast: dict, full_inventory: list[dict]) -> dict:
    scenario = get_cross_org_scenario(item, forecast)
    if not scenario:
        return {"tip": "", "scenario": None, "source": "none", "error": None}

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key or not _GROQ_AVAILABLE:
        return {
            "tip": _fallback_cross_org(item, forecast, scenario),
            "scenario": scenario,
            "source": "fallback",
            "error": None,
        }

    # Build scenario-specific prompt
    name      = item["name"]
    qty       = item["current_qty"]
    unit      = item["unit"]
    exp_days  = forecast.get("expiry_days_remaining")
    waste_qty = forecast.get("estimated_waste_units", 0)
    waste_val = round(waste_qty * item.get("cost_per_unit", 0), 2)

    # Find nonprofit items for context (used in cafe_donate scenario)
    np_items = [i["name"] for i in full_inventory if i.get("org") == "nonprofit" and i.get("type") == "perishable"]

    if scenario == "cafe_donate":
        prompt = f"""You are a sustainability advisor for a small café that is part of a local community network which includes a non-profit food bank.

The café has a waste risk on: {name} ({qty} {unit} remaining, expires in {exp_days} days, ~{waste_qty} {unit} estimated waste, ₹{waste_val} at risk).
The local non-profit currently tracks these perishable items: {', '.join(np_items) if np_items else 'food staples'}.

Write 2-3 sentences suggesting the café donate the at-risk surplus to the non-profit.
Include: what to donate, roughly how much, why it helps both orgs, and one practical step to make the handoff easy.
Be warm and community-minded. No bullet points. No preamble."""

    elif scenario == "nonprofit_solicit":
        prompt = f"""You are a community engagement advisor for a non-profit food bank.

The non-profit is running low on: {name} ({qty} {unit} remaining, stockout risk flagged).

Write 2-3 sentences suggesting specific actions to solicit donations or replenish stock.
Include: a social media appeal idea, reaching out to local businesses (specifically cafés or restaurants who may have surplus), and one other concrete channel.
Tone: warm, community-focused, practical. No bullet points. No preamble."""

    elif scenario == "nonprofit_expiry":
        prompt = f"""You are a community outreach advisor for a non-profit food bank.

The non-profit has {qty} {unit} of {name} expiring in {exp_days} day(s).

Write 2-3 sentences suggesting ways to redistribute or use this stock before it expires.
Ideas to consider: organising a same-week food drive, creating a community package deal, partnering with local cafés or schools, or offering it at reduced cost to beneficiaries.
Tone: warm, urgent but positive, community-focused. No bullet points. No preamble."""

    else:
        return {"tip": "", "scenario": None, "source": "none", "error": None}

    try:
        client = groq.Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "tip": response.choices[0].message.content.strip(),
            "scenario": scenario,
            "source": "llm",
            "error": None,
        }
    except Exception as e:
        return {
            "tip": _fallback_cross_org(item, forecast, scenario),
            "scenario": scenario,
            "source": "fallback",
            "error": str(e),
        }
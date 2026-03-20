# pyright: reportArgumentType=false
from datetime import datetime, timedelta

_SIM_CURRENT_DATE: str | None = None

def set_sim_date(date_str: str | None) -> None:
    global _SIM_CURRENT_DATE
    _SIM_CURRENT_DATE = date_str

def get_effective_today() -> datetime:
    if _SIM_CURRENT_DATE:
        return datetime.strptime(_SIM_CURRENT_DATE, "%Y-%m-%d")
    return datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

MIN_DATA_POINTS = 3     
RESTOCK_SPIKE_MULTIPLIER = 2 


def _parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")


def _days_until(date_str: str) -> int | None:
    if not date_str:
        return None
    delta = _parse_date(date_str) - get_effective_today()
    return delta.days


def _clean_usage(usages: list[float]) -> list[float]:
    if not usages:
        return []
    valid = [u for u in usages if u >= 0]
    if not valid:
        return []
    mean = sum(valid) / len(valid)
    cleaned = [u for u in valid if u <= mean * RESTOCK_SPIKE_MULTIPLIER + 1]
    return cleaned if cleaned else valid


def _weighted_moving_average(values: list[float]) -> float:
    n = len(values)
    weights = list(range(1, n + 1))
    total_weight = sum(weights)
    wma = sum(v * w for v, w in zip(values, weights)) / total_weight
    return wma


def _confidence_level(n_points: int) -> str:
    if n_points < MIN_DATA_POINTS:
        return "none"
    elif n_points < 7:
        return "low"
    elif n_points < 20:
        return "medium"
    else:
        return "high"

def _fallback_forecast(item: dict) -> dict:
    qty = item.get("current_qty", 0)

    if item.get("type") == "non_expiry" and qty > 0:
        return {
            "days_until_runout": None,
            "avg_daily_usage": 0.0,
            "confidence": "none",
            "model_used": "fallback",
            "data_points_used": 0,
            "note": "Non-consumable item. No usage forecast applicable.",
        }
    
    fallback_rate = item.get("_avg_daily_usage_hint", None)

    if fallback_rate and fallback_rate > 0:
        days = round(qty / fallback_rate, 1)
    elif qty == 0:
        days = 0
    else:
        days = None

    return {
        "days_until_runout": days,
        "avg_daily_usage": fallback_rate or 0.0,
        "confidence": "none",
        "model_used": "fallback",
        "data_points_used": 0,
        "note": "Insufficient usage history. Rule-based estimate used.",
    }


def _primary_forecast(item: dict, usage_records: list[dict]) -> dict:
    """
    Weighted moving average over cleaned usage data.
    Skips zero-usage days (closed/holiday) to avoid downward bias.
    """
    # Sort by date ascending
    sorted_records = sorted(usage_records, key=lambda r: r["date"])

    # Extract non-zero usage values
    raw_usages = [r["quantity_used"] for r in sorted_records if r["quantity_used"] > 0]

    cleaned = _clean_usage(raw_usages)

    if len(cleaned) < MIN_DATA_POINTS:
        return _fallback_forecast(item)

    avg_daily = _weighted_moving_average(cleaned)

    qty = item.get("current_qty", 0)
    if avg_daily > 0:
        days_until_runout = round(qty / avg_daily, 1)
    else:
        days_until_runout = None

    return {
        "days_until_runout": days_until_runout,
        "avg_daily_usage": round(avg_daily, 3),
        "confidence": _confidence_level(len(cleaned)),
        "model_used": "weighted_moving_average",
        "data_points_used": len(cleaned),
        "note": None,
    }


def forecast_item(item: dict, all_history: list[dict]) -> dict:

    item_history = [r for r in all_history if r["item_id"] == item["id"]]

    if not item_history:
        result = _fallback_forecast(item)
    else:
        result = _primary_forecast(item, item_history)

    expiry_days     = _days_until(item.get("expiry_date"))
    next_batch_days = _days_until(item.get("next_batch_expiry"))
    result["expiry_days_remaining"] = expiry_days

    days_out = result.get("days_until_runout")
    avg      = result.get("avg_daily_usage", 0)
    qty      = item["current_qty"]

    if qty <= 0 or expiry_days is None or days_out is None or avg <= 0:
        result["waste_risk"]            = False
        result["estimated_waste_units"] = None

    elif (next_batch_days is not None
          and next_batch_days != expiry_days
          and item.get("old_batch_qty", 0) > 0):
        old_qty_remaining = item["old_batch_qty"]
        new_qty           = max(0, qty - old_qty_remaining)
        
        old_can_use  = avg * expiry_days
        old_waste    = round(max(0, old_qty_remaining - old_can_use), 2)

        time_for_new = next_batch_days - expiry_days
        new_qty           = max(0, qty - old_qty_remaining)
        used_in_old_window = min(old_qty_remaining, old_can_use)
        overflow_usage    = max(0, old_can_use - old_qty_remaining)
        remaining_for_new = max(0, new_qty - overflow_usage)
        new_waste    = round(max(0, remaining_for_new - avg * time_for_new), 2)

        total_waste = round(old_waste + new_waste, 2)
        result["waste_risk"]            = total_waste > 0
        result["estimated_waste_units"] = total_waste if total_waste > 0 else 0.0

    else:
        result["waste_risk"] = expiry_days < days_out
        if result["waste_risk"]:
            leftover = qty - (expiry_days * avg)
            result["estimated_waste_units"] = round(max(0, leftover), 2)
        else:
            result["estimated_waste_units"] = 0.0

    threshold = item.get("reorder_threshold", 0)
    result["stockout_risk"] = (
        item.get("type") != "non_expiry" and (
            (days_out is not None and days_out <= 7) or
            (item["current_qty"] <= threshold)
        )
    )

    return result


def forecast_all(inventory: list[dict], all_history: list[dict]) -> dict[str, dict]:
    """Returns {item_id: forecast_dict} for the full inventory."""
    return {item["id"]: forecast_item(item, all_history) for item in inventory}


def simulate_days_forward(
    inventory: list[dict],
    all_history: list[dict],
    days: int,
    overrides: dict[str, float] | None = None,
    current_date: str | None = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    import copy, random
    from datetime import datetime

    overrides  = overrides or {}

    if current_date:
        today = datetime.strptime(current_date, "%Y-%m-%d")
    else:
        today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    updated_inv  = copy.deepcopy(inventory)
    updated_hist = copy.deepcopy(all_history)
    waste_events = []

    for item in updated_inv:
        item_hist = [r for r in all_history if r["item_id"] == item["id"]]
        forecast  = forecast_item(item, item_hist)
        avg       = forecast["avg_daily_usage"]

        if avg == 0 and item["id"] not in overrides:
            continue

        if item["id"] in overrides:
            per_day = overrides[item["id"]] / days if days > 0 else 0
        else:
            per_day = avg

        expiry_dt      = None
        next_expiry_dt = None
        old_batch_qty  = item.get("old_batch_qty", 0)

        if item.get("expiry_date"):
            expiry_dt = datetime.strptime(item["expiry_date"], "%Y-%m-%d")
        if item.get("next_batch_expiry") and item.get("next_batch_expiry") != item.get("expiry_date"):
            next_expiry_dt = datetime.strptime(item["next_batch_expiry"], "%Y-%m-%d")

        remaining_old = old_batch_qty if (expiry_dt and next_expiry_dt and old_batch_qty > 0) else 0

        expired_on_day = None

        for d in range(1, days + 1):
            sim_date = today + timedelta(days=d)
            date_str = sim_date.strftime("%Y-%m-%d")

            if expired_on_day is not None:
                continue

            if item["id"] in overrides:
                day_usage = round(per_day, 2)
            else:
                day_usage = round(max(0, random.gauss(per_day, per_day * 0.2)), 2)

            day_usage = min(day_usage, item["current_qty"])

            updated_hist.append({
                "item_id":       item["id"],
                "date":          date_str,
                "quantity_used": day_usage,
                "restock_qty":   0,
                "event":         "simulated",
            })

            item["current_qty"] = round(max(0, item["current_qty"] - day_usage), 2)

            if remaining_old > 0:
                remaining_old = round(max(0, remaining_old - day_usage), 2)

            if expiry_dt and sim_date > expiry_dt:
                if next_expiry_dt and item.get("old_batch_qty", 0) > 0:
                    old_waste = min(remaining_old, item["current_qty"])
                    if old_waste > 0:
                        waste_events.append({
                            "item_id":    item["id"],
                            "item_name":  item["name"],
                            "date":       date_str,
                            "wasted_qty": round(old_waste, 2),
                            "unit":       item["unit"],
                        })
                        updated_hist.append({
                            "item_id":       item["id"],
                            "date":          date_str,
                            "quantity_used": 0,
                            "restock_qty":   0,
                            "wasted_qty":    round(old_waste, 2),
                            "event":         "expired_waste",
                        })
                        item["current_qty"] = round(max(0, item["current_qty"] - old_waste), 2)
                    expiry_dt = next_expiry_dt
                    next_expiry_dt = None
                    remaining_old  = 0
                    item.pop("old_batch_qty", None)
                    item.pop("next_batch_expiry", None)
                    item["expiry_date"] = expiry_dt.strftime("%Y-%m-%d")
                else:
                    expired_on_day = d
                    wasted = item["current_qty"]
                    if wasted > 0:
                        waste_events.append({
                            "item_id":    item["id"],
                            "item_name":  item["name"],
                            "date":       date_str,
                            "wasted_qty": round(wasted, 2),
                            "unit":       item["unit"],
                        })
                        updated_hist.append({
                            "item_id":       item["id"],
                            "date":          date_str,
                            "quantity_used": 0,
                            "restock_qty":   0,
                            "wasted_qty":    round(wasted, 2),
                            "event":         "expired_waste",
                        })
                        item["current_qty"] = 0.0

        item["last_updated"] = (today + timedelta(days=days)).strftime("%Y-%m-%d")

    return updated_inv, updated_hist, waste_events
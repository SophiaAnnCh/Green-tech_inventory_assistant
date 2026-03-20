"""
Tests for EcoTrack AI
Run with: python tests/test_ecotrack.py

Covers:
- Forecasting: happy path + edge cases
- Alerts: correct triggers
- Inventory: validation + CRUD
- Fallback: insight fallback when no API key
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../app"))

from datetime import datetime, timedelta

from forecasting import forecast_item, _weighted_moving_average, _clean_usage
from alerts import check_alerts, AlertType, Severity
from inventory import validate_item, search_and_filter
from insights import fallback_insight


# ─────────────────────────────────────────────
# TEST RUNNER
# ─────────────────────────────────────────────

_passed = 0
_failed = 0
_errors = []

def run_test(name, fn):
    global _passed, _failed
    try:
        fn()
        print(f"  ✓ {name}")
        _passed += 1
    except AssertionError as e:
        print(f"  ✗ {name}")
        _errors.append(f"FAIL: {name}\n       {e}")
        _failed += 1
    except Exception as e:
        print(f"  ✗ {name}")
        _errors.append(f"ERROR: {name}\n       {type(e).__name__}: {e}")
        _failed += 1

def approx(value, expected, rel=0.15):
    """Returns True if value is within rel% of expected."""
    if expected == 0:
        return abs(value) < 1e-6
    return abs(value - expected) / abs(expected) <= rel


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

TODAY     = datetime.today().strftime("%Y-%m-%d")
FUTURE_5  = (datetime.today() + timedelta(days=5)).strftime("%Y-%m-%d")
FUTURE_30 = (datetime.today() + timedelta(days=30)).strftime("%Y-%m-%d")
PAST_1    = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")


def make_item(**kwargs) -> dict:
    base = {
        "id": "test_001",
        "name": "Test Milk",
        "org": "cafe",
        "type": "perishable",
        "category": "dairy",
        "unit": "liters",
        "current_qty": 10.0,
        "reorder_threshold": 3.0,
        "reorder_qty": 12.0,
        "cost_per_unit": 65,
        "expiry_date": FUTURE_30,
    }
    base.update(kwargs)
    return base


def make_history(item_id: str, usages: list, start_days_ago: int = 30) -> list:
    records = []
    for i, usage in enumerate(usages):
        date = (datetime.today() - timedelta(days=start_days_ago - i)).strftime("%Y-%m-%d")
        records.append({
            "item_id": item_id,
            "date": date,
            "quantity_used": usage,
            "restock_qty": 0,
            "event": "normal",
        })
    return records


# ─────────────────────────────────────────────
# FORECASTING — HAPPY PATH
# ─────────────────────────────────────────────

def test_basic_runout_prediction():
    """Standard item with 20 days of regular usage data."""
    item = make_item(current_qty=10.0)
    history = make_history("test_001", [2.0] * 20)
    result = forecast_item(item, history)

    assert approx(result["days_until_runout"], 5.0), \
        f"Expected ~5.0 days, got {result['days_until_runout']}"
    assert approx(result["avg_daily_usage"], 2.0), \
        f"Expected ~2.0 avg, got {result['avg_daily_usage']}"
    assert result["model_used"] == "weighted_moving_average"
    assert result["confidence"] in ("medium", "high")


def test_weighted_average_favors_recent_data():
    """WMA should weight recent higher usage more heavily than older low usage."""
    usages = [1.0] * 10 + [3.0] * 10
    result = _weighted_moving_average(usages)
    assert result > 2.0, f"WMA should be > 2.0, got {result}"


def test_waste_risk_detected():
    """Item expires before it will be used up → waste_risk=True."""
    item = make_item(current_qty=20.0, expiry_date=FUTURE_5)
    history = make_history("test_001", [1.0] * 20)
    result = forecast_item(item, history)

    assert result["waste_risk"] is True, "Expected waste_risk=True"
    assert result["estimated_waste_units"] > 0, "Expected waste units > 0"


def test_stockout_risk_detected():
    """Item running out within 7 days below threshold → stockout_risk=True."""
    item = make_item(current_qty=5.0, reorder_threshold=4.0)
    history = make_history("test_001", [2.0] * 15)
    result = forecast_item(item, history)

    assert result["stockout_risk"] is True, "Expected stockout_risk=True"


def test_no_expiry_item():
    """Consumable with no expiry date → no waste risk."""
    item = make_item(type="consumable", expiry_date=None)
    history = make_history("test_001", [2.0] * 15)
    result = forecast_item(item, history)

    assert result["waste_risk"] is False
    assert result["expiry_days_remaining"] is None


def test_non_expiry_equipment():
    """Equipment item with zero usage → returns fallback with None runout."""
    item = make_item(type="non_expiry", expiry_date=None, current_qty=2.0)
    result = forecast_item(item, [])

    assert result["days_until_runout"] is None
    assert result["model_used"] == "fallback"


# ─────────────────────────────────────────────
# FORECASTING — EDGE CASES
# ─────────────────────────────────────────────

def test_zero_history_triggers_fallback():
    """No usage records at all → fallback model."""
    item = make_item()
    result = forecast_item(item, [])

    assert result["model_used"] == "fallback"
    assert result["confidence"] == "none"
    assert result["data_points_used"] == 0


def test_sparse_history_triggers_fallback():
    """Only 2 records (below MIN_DATA_POINTS=3) → fallback."""
    item = make_item()
    history = make_history("test_001", [2.0, 3.0])
    result = forecast_item(item, history)

    assert result["model_used"] == "fallback"


def test_zero_quantity_item():
    """Item already at zero → days_until_runout should be 0."""
    item = make_item(current_qty=0.0)
    history = make_history("test_001", [2.0] * 15)
    result = forecast_item(item, history)

    assert result["days_until_runout"] == 0.0, \
        f"Expected 0.0, got {result['days_until_runout']}"


def test_zero_usage_days_excluded():
    """Zero-usage days (closed) should not drag down avg."""
    item = make_item(current_qty=10.0)
    usages = [2.0, 0.0, 0.0, 2.0, 0.0, 2.0, 0.0, 0.0, 2.0, 2.0,
              0.0, 2.0, 0.0, 0.0, 2.0, 0.0, 2.0, 0.0, 2.0, 2.0]
    history = make_history("test_001", usages)
    result = forecast_item(item, history)

    assert approx(result["avg_daily_usage"], 2.0, rel=0.15), \
        f"Expected ~2.0/day (zeros excluded), got {result['avg_daily_usage']}"


def test_spike_outlier_cleaning():
    """Restock spikes should not inflate avg daily usage."""
    base = [1.0] * 15
    base[7] = 50.0
    cleaned = _clean_usage(base)

    assert 50.0 not in cleaned, "Spike 50.0 should have been removed"
    assert all(v <= 5.0 for v in cleaned), "All cleaned values should be <= 5.0"


def test_already_expired_item():
    """Expired item: expiry_days_remaining should be negative."""
    item = make_item(expiry_date=PAST_1)
    history = make_history("test_001", [1.0] * 15)
    result = forecast_item(item, history)

    assert result["expiry_days_remaining"] is not None
    assert result["expiry_days_remaining"] < 0, \
        f"Expected negative expiry days, got {result['expiry_days_remaining']}"


def test_history_for_different_item_ignored():
    """History from other items should not affect this item's forecast."""
    item = make_item(id="test_001")
    wrong_history = make_history("other_item", [999.0] * 20)
    result = forecast_item(item, wrong_history)

    assert result["model_used"] == "fallback"


# ─────────────────────────────────────────────
# ALERTS
# ─────────────────────────────────────────────

def test_waste_alert_triggered():
    item = make_item(expiry_date=FUTURE_5)
    forecast = {
        "waste_risk": True, "stockout_risk": False,
        "expiry_days_remaining": 5, "days_until_runout": 15,
        "estimated_waste_units": 8.0, "confidence": "high", "data_points_used": 20,
    }
    alerts = check_alerts(item, forecast)
    assert AlertType.WASTE_RISK in [a.type for a in alerts]


def test_stockout_alert_triggered():
    item = make_item(current_qty=2.0, reorder_threshold=3.0)
    forecast = {
        "waste_risk": False, "stockout_risk": True,
        "expiry_days_remaining": None, "days_until_runout": 2.0,
        "estimated_waste_units": None, "confidence": "medium", "data_points_used": 10,
    }
    alerts = check_alerts(item, forecast)
    assert AlertType.STOCKOUT_RISK in [a.type for a in alerts]


def test_no_alerts_for_healthy_item():
    item = make_item(current_qty=20.0, reorder_threshold=3.0, expiry_date=FUTURE_30)
    forecast = {
        "waste_risk": False, "stockout_risk": False,
        "expiry_days_remaining": 30, "days_until_runout": 10.0,
        "estimated_waste_units": 0.0, "confidence": "high", "data_points_used": 25,
    }
    alerts = check_alerts(item, forecast)
    critical = [a for a in alerts if a.severity in (Severity.HIGH, Severity.MEDIUM)]
    assert len(critical) == 0, f"Expected no critical alerts, got {critical}"


def test_expired_item_alert():
    item = make_item(expiry_date=PAST_1)
    forecast = {
        "waste_risk": False, "stockout_risk": False,
        "expiry_days_remaining": -1, "days_until_runout": 5.0,
        "estimated_waste_units": None, "confidence": "medium", "data_points_used": 10,
    }
    alerts = check_alerts(item, forecast)
    assert AlertType.EXPIRED in [a.type for a in alerts]


def test_expired_suppressed_when_zero_qty():
    """EXPIRED alert should NOT fire when qty=0 — nothing left to discard."""
    item = make_item(current_qty=0.0, expiry_date=PAST_1)
    forecast = {
        "waste_risk": False, "stockout_risk": False,
        "expiry_days_remaining": -1, "days_until_runout": 0.0,
        "estimated_waste_units": None, "confidence": "medium", "data_points_used": 10,
    }
    alerts = check_alerts(item, forecast)
    assert AlertType.EXPIRED not in [a.type for a in alerts], \
        "EXPIRED should be suppressed when qty=0"


def test_waste_risk_suppressed_when_zero_qty():
    """WASTE_RISK should NOT fire when qty=0."""
    item = make_item(current_qty=0.0, expiry_date=FUTURE_5)
    forecast = {
        "waste_risk": False, "stockout_risk": False,
        "expiry_days_remaining": 5, "days_until_runout": 0.0,
        "estimated_waste_units": None, "confidence": "medium", "data_points_used": 10,
    }
    alerts = check_alerts(item, forecast)
    assert AlertType.WASTE_RISK not in [a.type for a in alerts]


# ─────────────────────────────────────────────
# INVENTORY VALIDATION
# ─────────────────────────────────────────────

def test_valid_item_passes():
    data = {
        "name": "Test Coffee", "org": "cafe", "type": "perishable",
        "category": "beverage", "unit": "kg",
        "current_qty": 5.0, "reorder_threshold": 2.0, "expiry_date": FUTURE_30,
    }
    assert validate_item(data) == []


def test_missing_name_fails():
    data = {
        "name": "", "org": "cafe", "type": "perishable",
        "unit": "kg", "current_qty": 5.0, "reorder_threshold": 2.0,
    }
    errors = validate_item(data)
    assert any("name" in e.lower() for e in errors)


def test_invalid_org_fails():
    data = {
        "name": "Test", "org": "hospital",
        "type": "perishable", "unit": "kg",
        "current_qty": 5.0, "reorder_threshold": 2.0,
    }
    errors = validate_item(data)
    assert any("organisation" in e.lower() for e in errors)


def test_negative_quantity_fails():
    data = {
        "name": "Test", "org": "cafe", "type": "consumable",
        "unit": "units", "current_qty": -1.0, "reorder_threshold": 2.0,
    }
    errors = validate_item(data)
    assert any("quantity" in e.lower() for e in errors)


def test_invalid_date_format_fails():
    data = {
        "name": "Test", "org": "cafe", "type": "perishable",
        "unit": "kg", "current_qty": 5.0, "reorder_threshold": 2.0,
        "expiry_date": "20-03-2026",
    }
    errors = validate_item(data)
    assert any("date" in e.lower() for e in errors)


# ─────────────────────────────────────────────
# SEARCH & FILTER
# ─────────────────────────────────────────────

_inv = [
    make_item(id="cafe_001", name="Whole Milk",   org="cafe",          type="perishable"),
    make_item(id="cafe_002", name="Coffee Beans", org="cafe",          type="perishable"),
    make_item(id="np_001",   name="A4 Paper",     org="nonprofit",     type="consumable"),
    make_item(id="lab_001",  name="Ethanol",      org="university_lab",type="perishable"),
]

def test_search_by_name():
    results = search_and_filter(_inv, query="milk")
    assert len(results) == 1 and results[0]["name"] == "Whole Milk"

def test_filter_by_org():
    results = search_and_filter(_inv, org="cafe")
    assert len(results) == 2 and all(r["org"] == "cafe" for r in results)

def test_filter_by_type():
    results = search_and_filter(_inv, item_type="consumable")
    assert len(results) == 1 and results[0]["id"] == "np_001"

def test_empty_query_returns_all():
    results = search_and_filter(_inv)
    assert len(results) == len(_inv)

def test_no_match_returns_empty():
    results = search_and_filter(_inv, query="xyznotfound")
    assert results == []


# ─────────────────────────────────────────────
# FALLBACK INSIGHT
# ─────────────────────────────────────────────

def test_fallback_runs_without_api_key():
    """Fallback should always return a non-empty string."""
    item = make_item()
    forecast = {
        "days_until_runout": 5.0, "avg_daily_usage": 2.0,
        "expiry_days_remaining": 10, "waste_risk": False, "stockout_risk": True,
        "estimated_waste_units": 0, "confidence": "medium",
        "model_used": "weighted_moving_average", "data_points_used": 15,
    }
    result = fallback_insight(item, forecast, [])
    assert isinstance(result, str) and len(result) > 20


def test_fallback_flags_waste_risk():
    """Fallback insight mentions waste when waste_risk=True."""
    item = make_item(expiry_date=FUTURE_5)
    forecast = {
        "days_until_runout": 15.0, "avg_daily_usage": 1.0,
        "expiry_days_remaining": 5, "waste_risk": True, "stockout_risk": False,
        "estimated_waste_units": 10.0, "confidence": "high",
        "model_used": "weighted_moving_average", "data_points_used": 20,
    }
    result = fallback_insight(item, forecast, [])
    assert "waste" in result.lower(), f"Expected 'waste' in fallback output, got: {result}"



# ─────────────────────────────────────────────
# LIVE MODE DATE VALIDATION & GAP FILL
# ─────────────────────────────────────────────

def _simulate_live_mode_save(ref_date_str, record_date_str, item, existing_hist):
    """
    Replicates the Live Mode save logic from main.py in a pure-Python context
    so it can be tested without Streamlit.

    Returns (gap_entries, final_hist, days_delta, date_blocked).
    """
    from datetime import datetime as dt, timedelta as td

    ref_date    = dt.strptime(ref_date_str, "%Y-%m-%d").date()
    record_date = dt.strptime(record_date_str, "%Y-%m-%d").date()
    days_delta  = (record_date - ref_date).days

    if days_delta < 0:
        return [], existing_hist, days_delta, True  # blocked

    gap_entries = []
    cur_hist    = list(existing_hist)

    if days_delta > 0:
        for gap_day in range(1, days_delta):
            gap_date = (ref_date + td(days=gap_day)).strftime("%Y-%m-%d")
            entry = {
                "item_id":       item["id"],
                "date":          gap_date,
                "quantity_used": 0.0,
                "restock_qty":   0,
                "event":         "no_use",
            }
            gap_entries.append(entry)
            cur_hist.append(entry)

    return gap_entries, cur_hist, days_delta, False


def test_past_date_is_blocked():
    """Saving for a date before the reference date must be blocked."""
    item = make_item()
    _, _, days_delta, blocked = _simulate_live_mode_save(
        ref_date_str="2026-03-20",
        record_date_str="2026-03-18",   # 2 days in the past
        item=item,
        existing_hist=[],
    )
    assert blocked is True, "Expected save to be blocked for a past date"
    assert days_delta < 0


def test_today_is_not_blocked():
    """Saving for the reference date itself (today) must not be blocked."""
    item = make_item()
    _, _, days_delta, blocked = _simulate_live_mode_save(
        ref_date_str="2026-03-20",
        record_date_str="2026-03-20",   # same day
        item=item,
        existing_hist=[],
    )
    assert blocked is False
    assert days_delta == 0


def test_future_date_not_blocked():
    """Saving for a future date must not be blocked."""
    item = make_item()
    _, _, days_delta, blocked = _simulate_live_mode_save(
        ref_date_str="2026-03-20",
        record_date_str="2026-03-25",   # 5 days ahead
        item=item,
        existing_hist=[],
    )
    assert blocked is False
    assert days_delta == 5


def test_future_date_gap_fill_count():
    """Gap between ref date and future record date should produce (delta - 1) no-use entries."""
    item = make_item()
    gap_entries, _, days_delta, _ = _simulate_live_mode_save(
        ref_date_str="2026-03-20",
        record_date_str="2026-03-25",   # 5 days ahead → 4 gap days (21, 22, 23, 24)
        item=item,
        existing_hist=[],
    )
    assert days_delta == 5
    assert len(gap_entries) == 4, f"Expected 4 gap entries, got {len(gap_entries)}"


def test_future_date_gap_fill_events():
    """All gap-fill entries must have event='no_use' and quantity_used=0."""
    item = make_item()
    gap_entries, _, _, _ = _simulate_live_mode_save(
        ref_date_str="2026-03-20",
        record_date_str="2026-03-23",   # 3 days ahead → 2 gap days
        item=item,
        existing_hist=[],
    )
    for entry in gap_entries:
        assert entry["event"] == "no_use", f"Expected no_use, got {entry['event']}"
        assert entry["quantity_used"] == 0.0, f"Expected 0.0 usage, got {entry['quantity_used']}"
        assert entry["item_id"] == item["id"]


def test_future_date_gap_fill_dates_are_correct():
    """Gap entries must cover exactly the days between ref and record date (exclusive of both)."""
    item = make_item()
    gap_entries, _, _, _ = _simulate_live_mode_save(
        ref_date_str="2026-03-20",
        record_date_str="2026-03-23",   # gap days should be 21 and 22
        item=item,
        existing_hist=[],
    )
    gap_dates = [e["date"] for e in gap_entries]
    assert gap_dates == ["2026-03-21", "2026-03-22"],         f"Expected ['2026-03-21', '2026-03-22'], got {gap_dates}"


def test_gap_fill_zero_use_excluded_from_forecast():
    """No-use gap entries (quantity_used=0) must not affect the WMA average."""
    item = make_item(current_qty=10.0)

    # Base history: 2.0/day for 15 days
    base_hist = make_history("test_001", [2.0] * 15)
    result_before = forecast_item(item, base_hist)

    # Add 5 no-use gap entries on top
    gap_hist = base_hist + [
        {"item_id": "test_001", "date": f"2026-03-2{i}", "quantity_used": 0.0,
         "restock_qty": 0, "event": "no_use"}
        for i in range(1, 6)
    ]
    result_after = forecast_item(item, gap_hist)

    assert approx(result_after["avg_daily_usage"], result_before["avg_daily_usage"], rel=0.05),         f"Gap-fill entries should not change avg: before={result_before['avg_daily_usage']:.3f}, after={result_after['avg_daily_usage']:.3f}"


def test_same_day_produces_no_gap_entries():
    """Recording for today (delta=0) must produce zero gap entries."""
    item = make_item()
    gap_entries, _, days_delta, _ = _simulate_live_mode_save(
        ref_date_str="2026-03-20",
        record_date_str="2026-03-20",
        item=item,
        existing_hist=[],
    )
    assert days_delta == 0
    assert len(gap_entries) == 0


# ─────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────

ALL_TESTS = [
    # Forecasting — happy path
    ("Basic runout prediction",             test_basic_runout_prediction),
    ("WMA favors recent data",              test_weighted_average_favors_recent_data),
    ("Waste risk detected",                 test_waste_risk_detected),
    ("Stockout risk detected",              test_stockout_risk_detected),
    ("No expiry item — no waste risk",      test_no_expiry_item),
    ("Equipment — fallback no runout",      test_non_expiry_equipment),
    # Forecasting — edge cases
    ("Zero history → fallback",            test_zero_history_triggers_fallback),
    ("Sparse history → fallback",          test_sparse_history_triggers_fallback),
    ("Zero qty → runout = 0",              test_zero_quantity_item),
    ("Zero-usage days excluded from avg",  test_zero_usage_days_excluded),
    ("Spike outlier cleaning",             test_spike_outlier_cleaning),
    ("Already expired item",               test_already_expired_item),
    ("Wrong item history ignored",         test_history_for_different_item_ignored),
    # Alerts
    ("Waste alert triggered",              test_waste_alert_triggered),
    ("Stockout alert triggered",           test_stockout_alert_triggered),
    ("No alerts for healthy item",         test_no_alerts_for_healthy_item),
    ("Expired item alert",                 test_expired_item_alert),
    ("Expired suppressed at zero qty",     test_expired_suppressed_when_zero_qty),
    ("Waste risk suppressed at zero qty",  test_waste_risk_suppressed_when_zero_qty),
    # Validation
    ("Valid item passes",                  test_valid_item_passes),
    ("Missing name fails",                 test_missing_name_fails),
    ("Invalid org fails",                  test_invalid_org_fails),
    ("Negative quantity fails",            test_negative_quantity_fails),
    ("Invalid date format fails",          test_invalid_date_format_fails),
    # Search & filter
    ("Search by name",                     test_search_by_name),
    ("Filter by org",                      test_filter_by_org),
    ("Filter by type",                     test_filter_by_type),
    ("Empty query returns all",            test_empty_query_returns_all),
    ("No match returns empty",             test_no_match_returns_empty),
    # Fallback insight
    ("Fallback runs without API key",      test_fallback_runs_without_api_key),
    ("Fallback flags waste risk",          test_fallback_flags_waste_risk),
    # Live Mode date validation & gap fill
    ("Past date is blocked",               test_past_date_is_blocked),
    ("Today is not blocked",               test_today_is_not_blocked),
    ("Future date not blocked",            test_future_date_not_blocked),
    ("Future date gap fill count",         test_future_date_gap_fill_count),
    ("Future date gap fill events",        test_future_date_gap_fill_events),
    ("Future date gap fill dates correct", test_future_date_gap_fill_dates_are_correct),
    ("Gap fill excluded from forecast",    test_gap_fill_zero_use_excluded_from_forecast),
    ("Same day — no gap entries",          test_same_day_produces_no_gap_entries),
]

if __name__ == "__main__":
    print(f"\nEcoTrack AI — Test Suite ({len(ALL_TESTS)} tests)\n")
    for name, fn in ALL_TESTS:
        run_test(name, fn)

    print(f"\nResults: {_passed} passed, {_failed} failed")
    if _errors:
        print("\nFailures:")
        for e in _errors:
            print(f"  {e}")
    sys.exit(0 if _failed == 0 else 1)
# pyright: reportCallIssue=false, reportArgumentType=false
"""
inventory.py — CRUD operations for inventory items
Loads from / saves to JSON files in the data/ directory.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
INVENTORY_FILE = DATA_DIR / "inventory.json"
HISTORY_FILE = DATA_DIR / "usage_history.json"

VALID_TYPES = {"perishable", "consumable", "non_expiry"}
VALID_ORGS = {"cafe", "nonprofit", "university_lab"}


# ─────────────────────────────────────────────
# LOAD / SAVE
# ─────────────────────────────────────────────

def load_inventory() -> list[dict]:
    with open(INVENTORY_FILE, "r") as f:
        return json.load(f)


def save_inventory(inventory: list[dict]) -> None:
    with open(INVENTORY_FILE, "w") as f:
        json.dump(inventory, f, indent=2)


def load_history() -> list[dict]:
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)


def save_history(history: list[dict]) -> None:
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


# ─────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────

def validate_item(data: dict) -> list[str]:
    """Returns list of validation error strings. Empty = valid."""
    errors = []

    if not data.get("name", "").strip():
        errors.append("Item name is required.")
    if data.get("type") not in VALID_TYPES:
        errors.append(f"Type must be one of: {', '.join(VALID_TYPES)}.")
    if data.get("org") not in VALID_ORGS:
        errors.append(f"Organisation must be one of: {', '.join(VALID_ORGS)}.")
    if not isinstance(data.get("current_qty"), (int, float)) or data["current_qty"] < 0:
        errors.append("Quantity must be a non-negative number.")
    if not data.get("unit", "").strip():
        errors.append("Unit is required (e.g. kg, units, liters).")
    if not isinstance(data.get("reorder_threshold"), (int, float)) or data["reorder_threshold"] < 0:
        errors.append("Reorder threshold must be a non-negative number.")

    # Expiry date — optional, but if provided must be a valid date
    expiry = data.get("expiry_date")
    if expiry:
        try:
            datetime.strptime(expiry, "%Y-%m-%d")
        except ValueError:
            errors.append("Expiry date must be in YYYY-MM-DD format.")

    return errors


# ─────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────

def get_item(inventory: list[dict], item_id: str) -> dict | None:
    return next((i for i in inventory if i["id"] == item_id), None)


def add_item(inventory: list[dict], data: dict) -> tuple[list[dict], list[str]]:
    """Returns (updated_inventory, errors)."""
    errors = validate_item(data)
    if errors:
        return inventory, errors

    # Generate ID
    prefix = data["org"][:3]
    existing_ids = [i["id"] for i in inventory if i["id"].startswith(prefix)]
    suffix = str(len(existing_ids) + 1).zfill(3)
    new_id = f"{prefix}_{suffix}"

    new_item = {
        "id": new_id,
        "name": data["name"].strip(),
        "org": data["org"],
        "type": data["type"],
        "category": data.get("category", "general").strip(),
        "unit": data["unit"].strip(),
        "current_qty": float(data["current_qty"]),
        "reorder_threshold": float(data["reorder_threshold"]),
        "reorder_qty": float(data.get("reorder_qty", data["reorder_threshold"] * 3)),
        "cost_per_unit": float(data.get("cost_per_unit", 0)),
        "expiry_date": data.get("expiry_date") or None,
        "shelf_life_days": int(data["shelf_life_days"]) if data.get("shelf_life_days") else None,
        "created_at": datetime.today().strftime("%Y-%m-%d"),
        "last_updated": datetime.today().strftime("%Y-%m-%d"),
    }

    updated = inventory + [new_item]
    save_inventory(updated)
    return updated, []


def update_quantity(
    inventory: list[dict],
    history: list[dict],
    item_id: str,
    new_qty: float,
    note: str = "manual_update",
    current_date: str | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """
    Updates item quantity and logs the delta to usage history.
    If this is a restock (new_qty > old_qty) on a perishable item,
    refreshes expiry_date based on shelf_life_days from the item record.
    Returns (updated_inventory, updated_history, errors).
    """
    if new_qty < 0:
        return inventory, history, ["Quantity cannot be negative."]

    item = get_item(inventory, item_id)
    if not item:
        return inventory, history, [f"Item '{item_id}' not found."]

    today_str = current_date or datetime.today().strftime("%Y-%m-%d")
    today_dt  = datetime.strptime(today_str, "%Y-%m-%d")

    old_qty = item["current_qty"]
    delta   = old_qty - new_qty  # positive = usage, negative = restock
    is_restock = delta < 0

    # Build the updated item fields
    update_fields = {
        "current_qty": new_qty,
        "last_updated": today_str,
    }

    # On restock of a perishable: handle mixed-batch expiry correctly.
    # If old stock remains, the effective expiry is the EARLIER of the two
    # dates (old batch expires first — FIFO principle).
    # Only replace with new batch date when restocking from zero.
    if is_restock and item.get("type") == "perishable":
        shelf_life = item.get("shelf_life_days")
        if shelf_life:
            new_batch_expiry = (today_dt + timedelta(days=shelf_life)).strftime("%Y-%m-%d")
            old_expiry = item.get("expiry_date")
            if old_qty <= 0 or old_expiry is None:
                # Empty shelf — new batch sets the expiry
                update_fields["expiry_date"] = new_batch_expiry
                update_fields.pop("next_batch_expiry", None)
                update_fields["old_batch_qty"] = 0.0
            else:
                # Mixed stock — old batch expires first (FIFO)
                update_fields["expiry_date"]      = min(old_expiry, new_batch_expiry)
                update_fields["next_batch_expiry"] = new_batch_expiry
                update_fields["old_batch_qty"]     = round(old_qty, 2)

    updated_inv = [
        {**i, **update_fields} if i["id"] == item_id else i
        for i in inventory
    ]

    history_entry = {
        "item_id":       item_id,
        "date":          today_str,
        "quantity_used": round(max(0, delta), 2),
        "restock_qty":   round(max(0, -delta), 2),
        "event":         note if delta >= 0 else "restock",
    }
    updated_hist = history + [history_entry]

    save_inventory(updated_inv)
    save_history(updated_hist)

    return updated_inv, updated_hist, []


def delete_item(inventory: list[dict], item_id: str) -> tuple[list[dict], list[str]]:
    """Removes an item from inventory."""
    if not get_item(inventory, item_id):
        return inventory, [f"Item '{item_id}' not found."]
    updated = [i for i in inventory if i["id"] != item_id]
    save_inventory(updated)
    return updated, []


# ─────────────────────────────────────────────
# SEARCH / FILTER
# ─────────────────────────────────────────────

def search_and_filter(
    inventory: list[dict],
    query: str = "",
    org: str = "all",
    item_type: str = "all",
    alert_filter: str = "all",
    forecasts: dict = None,
) -> list[dict]:
    results = inventory

    if query.strip():
        q = query.strip().lower()
        results = [
            i for i in results
            if q in i["name"].lower() or q in i["category"].lower()
        ]

    if org != "all":
        results = [i for i in results if i["org"] == org]

    if item_type != "all":
        results = [i for i in results if i["type"] == item_type]

    if alert_filter != "all" and forecasts:
        if alert_filter == "waste_risk":
            results = [i for i in results if forecasts.get(i["id"], {}).get("waste_risk")]
        elif alert_filter == "stockout_risk":
            results = [i for i in results if forecasts.get(i["id"], {}).get("stockout_risk")]
        elif alert_filter == "below_threshold":
            results = [i for i in results if i["current_qty"] <= i.get("reorder_threshold", 0)]

    return results
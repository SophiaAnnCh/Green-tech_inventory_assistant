import json, random, os
from datetime import datetime, timedelta

random.seed(42)
TODAY = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

def days_from_today(n):
    return (TODAY + timedelta(days=n)).strftime("%Y-%m-%d")

RAW_ITEMS = [
    # CAFÉ
    {
        "id": "cafe_001", "name": "Whole Milk", "org": "cafe",
        "type": "perishable", "category": "dairy", "unit": "liters",
        "current_qty": 33, "reorder_threshold": 6, "reorder_qty": 18, "cost_per_unit": 65,
        "expiry_days_from_today": 10, "avg_daily_usage": 3.5, "usage_variance": 1.0,
    },
    {
        "id": "cafe_002", "name": "Bread Loaves", "org": "cafe",
        "type": "perishable", "category": "bakery", "unit": "loaves",
        "current_qty": 36, "reorder_threshold": 4, "reorder_qty": 12, "cost_per_unit": 120,
        "expiry_days_from_today": 10, "avg_daily_usage": 4.0, "usage_variance": 1.5,
    },
    {
        "id": "cafe_003", "name": "Coffee Beans", "org": "cafe",
        "type": "perishable", "category": "beverage", "unit": "kg",
        "current_qty": 12, "reorder_threshold": 3, "reorder_qty": 12, "cost_per_unit": 850,
        "expiry_days_from_today": 60, "avg_daily_usage": 0.85, "usage_variance": 0.25,
    },
    {
        "id": "cafe_004", "name": "Oat Milk", "org": "cafe",
        "type": "perishable", "category": "dairy_alternative", "unit": "liters",
        "current_qty": 17, "reorder_threshold": 4, "reorder_qty": 12, "cost_per_unit": 180,
        "expiry_days_from_today": 18, "avg_daily_usage": 1.4, "usage_variance": 0.4,
    },
    {
        "id": "cafe_005", "name": "Disposable Coffee Cups", "org": "cafe",
        "type": "consumable", "category": "packaging", "unit": "units",
        "current_qty": 800, "reorder_threshold": 150, "reorder_qty": 500, "cost_per_unit": 3,
        "expiry_days_from_today": None, "avg_daily_usage": 48, "usage_variance": 14,
    },
    {
        "id": "cafe_006", "name": "Vanilla Syrup", "org": "cafe",
        "type": "perishable", "category": "flavouring", "unit": "bottles",
        "current_qty": 8, "reorder_threshold": 2, "reorder_qty": 6, "cost_per_unit": 320,
        "expiry_days_from_today": 90, "avg_daily_usage": 0.25, "usage_variance": 0.1,
    },
    {
        "id": "cafe_007", "name": "Fresh Cream", "org": "cafe",
        "type": "perishable", "category": "dairy", "unit": "liters",
        "current_qty": 9, "reorder_threshold": 3, "reorder_qty": 8, "cost_per_unit": 210,
        "expiry_days_from_today": 14, "avg_daily_usage": 0.9, "usage_variance": 0.3,
    },
    {
        "id": "cafe_008", "name": "Cold Brew Concentrate", "org": "cafe",
        "type": "perishable", "category": "beverage", "unit": "liters",
        "current_qty": 12, "reorder_threshold": 3, "reorder_qty": 8, "cost_per_unit": 480,
        "expiry_days_from_today": 12, "avg_daily_usage": 1.3, "usage_variance": 0.4,
    },
    {
        "id": "cafe_009", "name": "Paper Napkins", "org": "cafe",
        "type": "consumable", "category": "packaging", "unit": "packs",
        "current_qty": 22, "reorder_threshold": 5, "reorder_qty": 20, "cost_per_unit": 85,
        "expiry_days_from_today": None, "avg_daily_usage": 0.9, "usage_variance": 0.3,
    },

    # NON-PROFIT
    {
        "id": "np_001", "name": "Canned Food", "org": "nonprofit",
        "type": "perishable", "category": "food_donation", "unit": "units",
        "current_qty": 120, "reorder_threshold": 25, "reorder_qty": 80, "cost_per_unit": 0,
        "expiry_days_from_today": 90, "avg_daily_usage": 10, "usage_variance": 4,
    },
    {
        "id": "np_002", "name": "Hand Sanitizer", "org": "nonprofit",
        "type": "consumable", "category": "hygiene", "unit": "bottles",
        "current_qty": 28, "reorder_threshold": 8, "reorder_qty": 24, "cost_per_unit": 95,
        "expiry_days_from_today": 180, "avg_daily_usage": 1.2, "usage_variance": 0.4,
    },
    {
        "id": "np_003", "name": "A4 Printing Paper", "org": "nonprofit",
        "type": "consumable", "category": "office_supply", "unit": "reams",
        "current_qty": 18, "reorder_threshold": 5, "reorder_qty": 20, "cost_per_unit": 280,
        "expiry_days_from_today": None, "avg_daily_usage": 0.8, "usage_variance": 0.3,
    },
    {
        "id": "np_004", "name": "First Aid Kits", "org": "nonprofit",
        "type": "consumable", "category": "medical", "unit": "kits",
        "current_qty": 8, "reorder_threshold": 3, "reorder_qty": 6, "cost_per_unit": 750,
        "expiry_days_from_today": 365, "avg_daily_usage": 0.12, "usage_variance": 0.1,
    },
    {
        "id": "np_005", "name": "Whiteboard Markers", "org": "nonprofit",
        "type": "consumable", "category": "office_supply", "unit": "units",
        "current_qty": 20, "reorder_threshold": 5, "reorder_qty": 24, "cost_per_unit": 35,
        "expiry_days_from_today": None, "avg_daily_usage": 0.4, "usage_variance": 0.2,
    },
    {
        "id": "np_006", "name": "Printed Brochures", "org": "nonprofit",
        "type": "consumable", "category": "marketing", "unit": "units",
        "current_qty": 350, "reorder_threshold": 50, "reorder_qty": 300, "cost_per_unit": 12,
        "expiry_days_from_today": None, "avg_daily_usage": 18, "usage_variance": 8,
    },
    {
        "id": "np_007", "name": "Volunteer T-Shirts", "org": "nonprofit",
        "type": "non_expiry", "category": "apparel", "unit": "units",
        "current_qty": 40, "reorder_threshold": 10, "reorder_qty": 30, "cost_per_unit": 220,
        "expiry_days_from_today": None, "avg_daily_usage": 0.3, "usage_variance": 0.3,
    },

    # UNIVERSITY LAB
    {
        "id": "lab_001", "name": "Ethanol 70%", "org": "university_lab",
        "type": "perishable", "category": "chemical", "unit": "liters",
        "current_qty": 15, "reorder_threshold": 4, "reorder_qty": 20, "cost_per_unit": 420,
        "expiry_days_from_today": 30, "avg_daily_usage": 0.8, "usage_variance": 0.3,
    },
    {
        "id": "lab_002", "name": "Nitrile Gloves", "org": "university_lab",
        "type": "consumable", "category": "ppe", "unit": "boxes",
        "current_qty": 12, "reorder_threshold": 3, "reorder_qty": 12, "cost_per_unit": 380,
        "expiry_days_from_today": None, "avg_daily_usage": 0.5, "usage_variance": 0.2,
    },
    {
        "id": "lab_003", "name": "Phosphate Buffer Saline", "org": "university_lab",
        "type": "perishable", "category": "reagent", "unit": "liters",
        "current_qty": 8, "reorder_threshold": 2, "reorder_qty": 10, "cost_per_unit": 1200,
        "expiry_days_from_today": 25, "avg_daily_usage": 0.35, "usage_variance": 0.15,
    },
    {
        "id": "lab_004", "name": "Petri Dishes", "org": "university_lab",
        "type": "consumable", "category": "labware", "unit": "packs",
        "current_qty": 14, "reorder_threshold": 4, "reorder_qty": 20, "cost_per_unit": 260,
        "expiry_days_from_today": None, "avg_daily_usage": 0.6, "usage_variance": 0.3,
    },
    {
        "id": "lab_005", "name": "Micropipette Tips", "org": "university_lab",
        "type": "consumable", "category": "labware", "unit": "racks",
        "current_qty": 20, "reorder_threshold": 5, "reorder_qty": 24, "cost_per_unit": 180,
        "expiry_days_from_today": None, "avg_daily_usage": 0.9, "usage_variance": 0.4,
    },
    {
        "id": "lab_006", "name": "Trypsin-EDTA Solution", "org": "university_lab",
        "type": "perishable", "category": "reagent", "unit": "bottles",
        "current_qty": 4, "reorder_threshold": 2, "reorder_qty": 6, "cost_per_unit": 2800,
        "expiry_days_from_today": 45, "avg_daily_usage": 0.18, "usage_variance": 0.1,
    },
    {
        "id": "lab_007", "name": "Autoclave Bags", "org": "university_lab",
        "type": "consumable", "category": "waste_management", "unit": "units",
        "current_qty": 250, "reorder_threshold": 50, "reorder_qty": 200, "cost_per_unit": 8,
        "expiry_days_from_today": None, "avg_daily_usage": 6, "usage_variance": 2,
    },
]


def generate_usage_history(item, days=45):
    if item["avg_daily_usage"] == 0:
        return []

    history = []
    qty  = item["current_qty"] * 2.5
    avg  = item["avg_daily_usage"]
    var  = item["usage_variance"]
    shelf_life = item["expiry_days_from_today"]
    expiry_date = None
    if shelf_life is not None:
        expiry_date = (TODAY + timedelta(days=-days + shelf_life)).strftime("%Y-%m-%d")

    for i in range(-days, 0):
        date_obj = TODAY + timedelta(days=i)
        date     = date_obj.strftime("%Y-%m-%d")
        weekday  = date_obj.weekday()

        # Org-aware usage patterns
        if item["org"] == "university_lab" and weekday >= 5:
            zero_prob = 0.80 
        elif item["org"] == "nonprofit" and weekday >= 5:
            zero_prob = 0.50
        else:
            zero_prob = 0.0

        if random.random() < zero_prob:
            history.append({"item_id": item["id"], "date": date,
                            "quantity_used": 0.0, "restock_qty": 0, "event": "closed",
                            "expiry_date": expiry_date})
            continue

        weekend_mult = random.uniform(1.2, 1.55) if (item["org"] == "cafe" and weekday >= 5) else 1.0
        usage = max(0, random.gauss(avg * weekend_mult, var))

        event = "normal"
        if random.random() < 0.06:
            usage *= random.uniform(2.2, 3.5)
            event = "bulk_order"

        usage   = round(min(usage, qty), 2)
        restock = 0
        if qty - usage < item["reorder_threshold"]:
            if random.random() < 0.70:
                restock = item["reorder_qty"]
                event   = "restock"
                if shelf_life is not None:
                    expiry_date = (date_obj + timedelta(days=shelf_life)).strftime("%Y-%m-%d")

        history.append({"item_id": item["id"], "date": date,
                        "quantity_used": round(usage, 2), "restock_qty": restock,
                        "event": event,
                        "expiry_date": expiry_date if shelf_life is not None else None})
        qty = max(0, qty - usage + restock)

    return history


def main():
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))

    inventory = [
        {
            "id": item["id"], "name": item["name"], "org": item["org"],
            "type": item["type"], "category": item["category"], "unit": item["unit"],
            "current_qty": float(item["current_qty"]),
            "reorder_threshold": float(item["reorder_threshold"]),
            "reorder_qty": float(item["reorder_qty"]),
            "cost_per_unit": item["cost_per_unit"],
            "expiry_date": days_from_today(item["expiry_days_from_today"])
                           if item["expiry_days_from_today"] is not None else None,
            "shelf_life_days": item["expiry_days_from_today"],
            "created_at": days_from_today(-60),
            "last_updated": TODAY.strftime("%Y-%m-%d"),
        }
        for item in RAW_ITEMS
    ]

    all_history = []
    for item in RAW_ITEMS:
        all_history.extend(generate_usage_history(item, days=45))

    with open(os.path.join(out_dir, "inventory.json"), "w") as f:
        json.dump(inventory, f, indent=2)
    with open(os.path.join(out_dir, "usage_history.json"), "w") as f:
        json.dump(all_history, f, indent=2)

    print(f"{len(inventory)} items across 3 orgs, {len(all_history)} history records")

    # Summary by org
    by_org = {}
    for i in inventory:
        by_org.setdefault(i["org"], 0)
        by_org[i["org"]] += 1
    for org, count in sorted(by_org.items()):
        print(f"  {org:<20} {count} items")

    # Day-0 check
    import sys
    sys.path.insert(0, os.path.join(out_dir, "../app"))
    from forecasting import forecast_item
    from alerts import check_alerts, Severity

    print("\nDay 0 — all should be healthy:")
    any_crit = False
    for item in inventory:
        fc  = forecast_item(item, all_history)
        als = check_alerts(item, fc)
        crit = [a for a in als if a.severity in (Severity.HIGH, Severity.MEDIUM)]
        if crit:
            any_crit = True
            print(f"  ✗ {item['name']}: {[a.type.value for a in crit]}")
    if not any_crit:
        print("Data Generation Successful: No critical alerts on Day 0.")


if __name__ == "__main__":
    main()
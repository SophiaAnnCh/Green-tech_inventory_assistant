from dataclasses import dataclass
from enum import Enum


class AlertType(str, Enum):
    WASTE_RISK = "waste_risk"
    STOCKOUT_RISK = "stockout_risk"
    CRITICAL_LOW = "critical_low"
    EXPIRED = "expired"
    LOW_CONFIDENCE = "low_confidence"


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Alert:
    type: AlertType
    severity: Severity
    title: str
    message: str
    item_id: str
    item_name: str


def check_alerts(item: dict, forecast: dict) -> list[Alert]:
    alerts = []
    name = item["name"]
    iid = item["id"]
    qty = item["current_qty"]
    threshold = item.get("reorder_threshold", 0)
    days_out = forecast.get("days_until_runout")
    expiry_days = forecast.get("expiry_days_remaining")
    item_type = item.get("type")

    #  EXPIRED 
    if expiry_days is not None and expiry_days <= 0 and qty > 0:
        alerts.append(Alert(
            type=AlertType.EXPIRED,
            severity=Severity.HIGH,
            title="Item Expired",
            message=f"{name} has expired. Remove from inventory immediately.",
            item_id=iid,
            item_name=name,
        ))
        return alerts 

    # WASTE RISK 
    if forecast.get("waste_risk"):
        waste_units = forecast.get("estimated_waste_units", 0)
        alerts.append(Alert(
            type=AlertType.WASTE_RISK,
            severity=Severity.HIGH if (expiry_days or 99) <= 3 else Severity.MEDIUM,
            title="Waste Risk Detected",
            message=(
                f"{name} expires in {expiry_days} day(s) but will last "
                f"{days_out} days at current usage. "
                f"~{waste_units} {item['unit']} may go to waste."
            ),
            item_id=iid,
            item_name=name,
        ))

    # STOCKOUT RISK 
    if forecast.get("stockout_risk"):
        already_out = qty <= 0
        if already_out:
            sev = Severity.HIGH
            title = "Out of Stock — Critical"
            msg = (
                f"{name} is completely out of stock. "
                f"Immediate reorder required."
            )
        elif (days_out or 99) <= 3:
            sev = Severity.HIGH
            title = "Stockout Risk"
            msg = (
                f"{name} will run out in ~{days_out:.1f} day(s). "
                f"Reorder immediately."
            )
        else:
            sev = Severity.MEDIUM
            title = "Stockout Risk"
            msg = (
                f"{name} will run out in ~{days_out:.1f} day(s). "
                f"Reorder point is {threshold} {item['unit']}."
            )
        alerts.append(Alert(
            type=AlertType.STOCKOUT_RISK,
            severity=sev,
            title=title,
            message=msg,
            item_id=iid,
            item_name=name,
        ))

    # CRITICAL LOW 
    if (
        item_type != "non_expiry"
        and qty <= threshold
        and not forecast.get("stockout_risk")
    ):
        alerts.append(Alert(
            type=AlertType.CRITICAL_LOW,
            severity=Severity.MEDIUM,
            title="Below Reorder Threshold",
            message=(
                f"{name} is at {qty} {item['unit']}, "
                f"below reorder threshold of {threshold}."
            ),
            item_id=iid,
            item_name=name,
        ))

    return alerts


def check_all_alerts(inventory: list[dict], forecasts: dict[str, dict]) -> list[Alert]:
    """Returns all alerts across the full inventory, sorted by severity."""
    all_alerts = []
    severity_order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}

    for item in inventory:
        forecast = forecasts.get(item["id"], {})
        alerts = check_alerts(item, forecast)
        all_alerts.extend(alerts)

    all_alerts.sort(key=lambda a: severity_order.get(a.severity, 99))
    return all_alerts


def alert_badge_color(severity: Severity) -> str:
    """Returns a Streamlit-friendly color string."""
    return {
        Severity.HIGH: "#ef4444",
        Severity.MEDIUM: "#f97316",
        Severity.LOW: "#3b82f6",
    }.get(severity, "#6b7280")


def alert_emoji(alert_type: AlertType) -> str:
    return {
        AlertType.WASTE_RISK: "♻️",
        AlertType.STOCKOUT_RISK: "⚠️",
        AlertType.CRITICAL_LOW: "📉",
        AlertType.EXPIRED: "🚫",
        AlertType.LOW_CONFIDENCE: "🔍",
    }.get(alert_type, "ℹ️")
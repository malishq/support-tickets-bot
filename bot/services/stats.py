from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from bot.services import statuses

DAY = 86400
WEEK = 7 * DAY

Row = Dict[str, Any]


def tz(offset_hours: int) -> timezone:
    return timezone(timedelta(hours=offset_hours))


def day_start(now_ts: int, offset_hours: int) -> int:
    local = datetime.fromtimestamp(now_ts, tz=tz(offset_hours))
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(midnight.timestamp())


def average(values: Iterable[float]) -> Optional[float]:
    items = list(values)
    if not items:
        return None
    return sum(items) / len(items)


def compute_stats(tickets: List[Row], ratings: List[Row], now_ts: int, offset_hours: int) -> Dict[str, Any]:
    today = day_start(now_ts, offset_hours)
    week = now_ts - WEEK

    created_today = [t for t in tickets if t["created_at"] >= today]
    created_week = [t for t in tickets if t["created_at"] >= week]
    closed_today = [t for t in tickets if t.get("closed_at") and t["closed_at"] >= today]
    closed_week = [t for t in tickets if t.get("closed_at") and t["closed_at"] >= week]
    active = [t for t in tickets if t["status"] != statuses.CLOSED]

    by_status = {status: 0 for status in statuses.ALL}
    for ticket in tickets:
        by_status[ticket["status"]] = by_status.get(ticket["status"], 0) + 1

    first_reply_times = [
        t["first_reply_at"] - t["created_at"]
        for t in tickets
        if t.get("first_reply_at") and t["first_reply_at"] >= week
    ]
    close_times = [t["closed_at"] - t["created_at"] for t in closed_week]
    week_ratings = [r["score"] for r in ratings if r["created_at"] >= week]

    operators: Dict[int, Dict[str, Any]] = {}
    for ticket in tickets:
        operator_id = ticket.get("operator_id")
        if operator_id is None:
            continue
        entry = operators.setdefault(operator_id, {"active": 0, "closed_week": 0, "first_reply_times": []})
        if ticket["status"] != statuses.CLOSED:
            entry["active"] += 1
        if ticket.get("closed_at") and ticket["closed_at"] >= week:
            entry["closed_week"] += 1
        if ticket.get("first_reply_at") and ticket["first_reply_at"] >= week:
            entry["first_reply_times"].append(ticket["first_reply_at"] - ticket["created_at"])

    operator_stats = {
        operator_id: {
            "active": entry["active"],
            "closed_week": entry["closed_week"],
            "avg_first_reply": average(entry["first_reply_times"]),
        }
        for operator_id, entry in operators.items()
    }

    return {
        "created_today": len(created_today),
        "created_week": len(created_week),
        "closed_today": len(closed_today),
        "closed_week": len(closed_week),
        "active": len(active),
        "by_status": by_status,
        "avg_first_reply": average(first_reply_times),
        "avg_close": average(close_times),
        "avg_rating": average(week_ratings),
        "rating_count": len(week_ratings),
        "operators": operator_stats,
    }

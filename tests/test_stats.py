from bot.services import statuses as s
from bot.services.formatting import format_duration
from bot.services.stats import DAY, average, compute_stats, day_start

TZ = 3
NOW = day_start(1_800_000_000, TZ) + 12 * 3600


def ticket(ticket_id, created, status, first_reply=None, closed=None, operator_id=None):
    return {
        "id": ticket_id,
        "created_at": created,
        "status": status,
        "first_reply_at": first_reply,
        "closed_at": closed,
        "operator_id": operator_id,
    }


TICKETS = [
    ticket(1001, NOW - 600, s.WAITING_CLIENT, first_reply=NOW - 300, operator_id=1),
    ticket(1002, NOW - 7200, s.CLOSED, first_reply=NOW - 6300, closed=NOW - 3600, operator_id=1),
    ticket(1003, NOW - 10 * DAY, s.CLOSED, first_reply=NOW - 10 * DAY + 60, closed=NOW - 9 * DAY, operator_id=2),
    ticket(1004, NOW - 2 * DAY, s.OPEN),
]

RATINGS = [
    {"ticket_id": 1002, "score": 5, "created_at": NOW - 3500},
    {"ticket_id": 1003, "score": 3, "created_at": NOW - 9 * DAY},
]


def test_counts():
    stats = compute_stats(TICKETS, RATINGS, NOW, TZ)
    assert stats["created_today"] == 2
    assert stats["created_week"] == 3
    assert stats["closed_today"] == 1
    assert stats["closed_week"] == 1
    assert stats["active"] == 2
    assert stats["by_status"][s.OPEN] == 1
    assert stats["by_status"][s.WAITING_CLIENT] == 1
    assert stats["by_status"][s.CLOSED] == 2


def test_average_times_and_rating():
    stats = compute_stats(TICKETS, RATINGS, NOW, TZ)
    assert stats["avg_first_reply"] == 600
    assert stats["avg_close"] == 3600
    assert stats["avg_rating"] == 5.0
    assert stats["rating_count"] == 1


def test_operator_breakdown():
    stats = compute_stats(TICKETS, RATINGS, NOW, TZ)
    assert stats["operators"][1] == {"active": 1, "closed_week": 1, "avg_first_reply": 600}
    assert stats["operators"][2] == {"active": 0, "closed_week": 0, "avg_first_reply": None}


def test_empty_data():
    stats = compute_stats([], [], NOW, TZ)
    assert stats["created_today"] == 0
    assert stats["avg_first_reply"] is None
    assert stats["avg_rating"] is None
    assert stats["operators"] == {}


def test_average_and_day_start():
    assert average([]) is None
    assert average([1, 2, 3]) == 2
    start = day_start(NOW, TZ)
    assert (start + TZ * 3600) % DAY == 0
    assert start <= NOW < start + DAY


def test_format_duration():
    assert format_duration(None) == "—"
    assert format_duration(30) == "меньше минуты"
    assert format_duration(90) == "1 мин"
    assert format_duration(3600 + 300) == "1 ч 05 мин"
    assert format_duration(2 * DAY + 3 * 3600) == "2 дн 3 ч"

import pytest

from bot.db import Database
from bot.services import statuses as s


@pytest.fixture
async def db():
    database = Database(":memory:", first_ticket_number=1001)
    await database.connect()
    yield database
    await database.close()


async def test_ticket_numbers_start_at_1001(db):
    first = await db.create_ticket(1, "payment", "Первое")
    second = await db.create_ticket(2, "delivery", "Второе")
    assert first["id"] == 1001
    assert second["id"] == 1002
    assert first["status"] == s.OPEN
    assert first["awaiting_since"] == first["created_at"]


async def test_user_queries_and_filters(db):
    await db.upsert_user(1, "Иван Петров", "ivan")
    open_ticket = await db.create_ticket(1, "payment", "Открыт")
    closed_ticket = await db.create_ticket(1, "tech", "Закрыт")
    await db.update_ticket(closed_ticket["id"], status=s.CLOSED, closed_at=100, awaiting_since=None)

    active = await db.active_ticket_for_user(1)
    assert active["id"] == open_ticket["id"]
    latest = await db.latest_ticket_for_user(1)
    assert latest["id"] == closed_ticket["id"]
    assert await db.count_tickets() == 2
    assert await db.count_tickets(status=s.CLOSED) == 1
    assert await db.count_tickets(category="payment") == 1
    assert [t["id"] for t in await db.list_tickets(status=s.OPEN)] == [open_ticket["id"]]
    assert await db.active_ticket_for_user(2) is None

    user = await db.get_user(1)
    assert user["full_name"] == "Иван Петров"
    await db.upsert_user(1, "Иван Сидоров", None)
    assert (await db.get_user(1))["full_name"] == "Иван Сидоров"


async def test_ban_creates_missing_user(db):
    await db.set_banned(555, True)
    assert (await db.get_user(555))["is_banned"] == 1
    await db.set_banned(555, False)
    assert (await db.get_user(555))["is_banned"] == 0


async def test_messages_ratings_relays(db):
    ticket = await db.create_ticket(1, "other", "Текст")
    await db.add_message(ticket["id"], "client", 1, "Текст")
    await db.add_message(ticket["id"], "client", 1, None, "photo", "file", None)
    await db.add_message(ticket["id"], "operator", 7, "Ответ")
    messages = await db.ticket_messages(ticket["id"])
    assert [m["sender"] for m in messages] == ["client", "client", "operator"]
    assert [m["sender"] for m in await db.ticket_messages(ticket["id"], limit=2)] == ["client", "operator"]
    assert await db.count_attachments(ticket["id"]) == 1

    await db.add_rating(ticket["id"], 1, 4)
    await db.add_rating(ticket["id"], 1, 5)
    rating = await db.get_rating(ticket["id"])
    assert rating["score"] == 5
    await db.set_rating_comment(ticket["id"], "Спасибо")
    assert (await db.get_rating(ticket["id"]))["comment"] == "Спасибо"

    await db.add_relay(10, 1, ticket["id"], "card")
    await db.add_relay(10, 5, ticket["id"], "card")
    await db.add_relay(20, 3, ticket["id"], "client_message")
    relay = await db.find_relay(20, 3)
    assert relay["ticket_id"] == ticket["id"]
    cards = await db.latest_cards(ticket["id"])
    assert [(c["chat_id"], c["message_id"]) for c in cards] == [(10, 5)]


async def test_awaiting_and_reminders(db):
    old = await db.create_ticket(1, "payment", "Старое", ts=1000)
    fresh = await db.create_ticket(2, "payment", "Новое", ts=5000)
    waiting = await db.tickets_awaiting(older_than_ts=2000, reminded_before_ts=2000)
    assert [t["id"] for t in waiting] == [old["id"]]
    await db.mark_reminded([old["id"]], 2500)
    assert await db.tickets_awaiting(2000, 2000) == []
    assert [t["id"] for t in await db.tickets_awaiting(6000, 6000)] == [old["id"], fresh["id"]]
    await db.update_ticket(old["id"], status=s.CLOSED, awaiting_since=None)
    assert [t["id"] for t in await db.tickets_awaiting(6000, 6000)] == [fresh["id"]]


async def test_operators_map(db):
    await db.upsert_operator(7, "Мария", "maria")
    await db.upsert_operator(8, "", None)
    names = await db.operators_map()
    assert names == {7: "Мария", 8: "8"}

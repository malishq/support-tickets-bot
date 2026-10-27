from bot.services import statuses as s
from bot.services.formatting import (
    format_client_ticket,
    format_history,
    format_reminder,
    format_stats,
    format_ticket_card,
    format_ticket_row,
    format_tickets_list,
    plural,
    short_name,
)
from bot.services.stats import compute_stats

TZ = 3
NOW = 1_800_000_000

TICKET = {
    "id": 1001,
    "user_id": 42,
    "category": "payment",
    "status": s.OPEN,
    "description": "<b>Не прошла</b> оплата & заказ 55",
    "created_at": NOW - 900,
    "operator_id": None,
    "closed_at": None,
    "awaiting_since": NOW - 900,
}
USER = {"id": 42, "full_name": "Иван Петров", "username": "ivan"}


def test_card_contains_key_fields_and_escapes_html():
    card = format_ticket_card(TICKET, USER, None, 2, TZ)
    assert "#1001" in card
    assert "открыт" in card
    assert "Оплата" in card
    assert "@ivan" in card
    assert "id 42" in card
    assert "Оператор: —" in card
    assert "Вложений: 2" in card
    assert "&lt;b&gt;Не прошла&lt;/b&gt;" in card
    assert "<b>Не прошла</b>" not in card
    assert "&amp;" in card


def test_card_closed_with_operator():
    ticket = dict(TICKET, status=s.CLOSED, operator_id=7, closed_at=NOW)
    card = format_ticket_card(ticket, USER, "Мария <Оп>", 0, TZ)
    assert "закрыт" in card
    assert "Закрыто:" in card
    assert "Мария &lt;Оп&gt;" in card
    assert "Вложений" not in card


def test_card_without_user_record():
    card = format_ticket_card(TICKET, None, None, 0, TZ)
    assert "id 42" in card


def test_client_ticket_view():
    text = format_client_ticket(dict(TICKET, status=s.WAITING_CLIENT), "Мария", TZ)
    assert "ждём вашего ответа" in text
    assert "Оператор: Мария" in text
    assert "@ivan" not in text


def test_history_for_operator_and_client():
    messages = [
        {"sender": "client", "sender_id": 42, "text": "Не могу <войти>", "media_type": None, "file_name": None, "created_at": NOW - 600},
        {"sender": "operator", "sender_id": 7, "text": "Проверяю", "media_type": None, "file_name": None, "created_at": NOW - 300},
        {"sender": "client", "sender_id": 42, "text": None, "media_type": "document", "file_name": "invoice.pdf", "created_at": NOW - 200},
        {"sender": "system", "sender_id": 7, "text": "Обращение закрыто", "media_type": None, "file_name": None, "created_at": NOW},
    ]
    names = {7: "Мария"}
    operator_view = format_history(messages, TZ, names, viewer="operator", now_ts=NOW)
    assert "Клиент:" in operator_view
    assert "Оператор Мария:" in operator_view
    assert "invoice.pdf" in operator_view
    assert "&lt;войти&gt;" in operator_view
    assert "Система:" in operator_view
    client_view = format_history(messages, TZ, names, viewer="client", now_ts=NOW)
    assert "Вы:" in client_view
    assert "Клиент:" not in client_view
    assert format_history([], TZ, names) == "История пуста."


def test_history_is_trimmed_to_latest_messages():
    messages = [
        {"sender": "client", "sender_id": 1, "text": "x" * 300, "media_type": None, "file_name": None, "created_at": NOW + i}
        for i in range(40)
    ]
    text = format_history(messages, TZ, {}, now_ts=NOW)
    assert len(text) < 4096
    assert text.count("Клиент:") < 40
    assert "…" in text


def test_ticket_row_and_list():
    row = format_ticket_row(TICKET, USER, "Мария Иванова", NOW)
    assert "#1001" in row
    assert "Иван П." in row
    assert "оп. Мария И." in row
    assert "15 мин назад" in row
    listing = format_tickets_list([TICKET], {42: USER}, {}, s.OPEN, None, 0, 1, 1, NOW)
    assert "статус: открыт" in listing
    assert "категория: все" in listing
    assert "#1001" in listing
    assert "нет" in format_tickets_list([], {}, {}, None, None, 0, 1, 0, NOW)


def test_stats_and_reminder_text():
    tickets = [dict(TICKET, operator_id=7, first_reply_at=NOW - 600, status=s.IN_PROGRESS)]
    stats = compute_stats(tickets, [], NOW, TZ)
    text = format_stats(stats, {7: "Мария"})
    assert "Статистика" in text
    assert "Мария" in text
    assert "5 мин" in text
    reminder = format_reminder([TICKET], {42: USER}, NOW, 10)
    assert "#1001" in reminder
    assert "15 мин" in reminder
    assert "дольше 10 мин" in reminder


def test_plural_and_short_name():
    assert plural(1, "оценка", "оценки", "оценок") == "оценка"
    assert plural(3, "оценка", "оценки", "оценок") == "оценки"
    assert plural(11, "оценка", "оценки", "оценок") == "оценок"
    assert plural(21, "оценка", "оценки", "оценок") == "оценка"
    assert short_name("Иван Петров") == "Иван П."
    assert short_name("Иван") == "Иван"
    assert short_name("") == "без имени"

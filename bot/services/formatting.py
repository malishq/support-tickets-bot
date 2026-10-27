from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any, Dict, List, Optional

from bot.services import categories, statuses
from bot.services.stats import tz

Row = Dict[str, Any]

HISTORY_LIMIT = 3500


def fmt_dt(ts: Optional[int], offset_hours: int) -> str:
    if ts is None:
        return "—"
    return datetime.fromtimestamp(ts, tz=tz(offset_hours)).strftime("%d.%m.%Y %H:%M")


def fmt_short(ts: Optional[int], now_ts: int, offset_hours: int) -> str:
    if ts is None:
        return "—"
    moment = datetime.fromtimestamp(ts, tz=tz(offset_hours))
    today = datetime.fromtimestamp(now_ts, tz=tz(offset_hours))
    if moment.date() == today.date():
        return moment.strftime("%H:%M")
    return moment.strftime("%d.%m %H:%M")


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "—"
    total = max(int(seconds), 0)
    if total < 60:
        return "меньше минуты"
    minutes = total // 60
    if minutes < 60:
        return f"{minutes} мин"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours} ч {minutes:02d} мин"
    days, hours = divmod(hours, 24)
    return f"{days} дн {hours} ч"


def shorten(text: Optional[str], limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def short_name(full_name: Optional[str]) -> str:
    parts = (full_name or "").split()
    if not parts:
        return "без имени"
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[1][0]}."


def first_name(full_name: Optional[str]) -> str:
    parts = (full_name or "").split()
    return parts[0] if parts else ""


def client_line(user: Optional[Row], user_id: int) -> str:
    if not user:
        return f"id {user_id}"
    name = escape(user.get("full_name") or "без имени")
    username = user.get("username")
    extra = f"@{escape(username)}, id {user_id}" if username else f"id {user_id}"
    return f"{name} ({extra})"


def status_line(status: str) -> str:
    return f"{statuses.icon(status)} {statuses.label(status)}"


def format_ticket_card(
    ticket: Row,
    user: Optional[Row],
    operator_name: Optional[str],
    attachments: int,
    offset_hours: int,
) -> str:
    lines = [
        f"🎫 <b>Обращение #{ticket['id']}</b> · {status_line(ticket['status'])}",
        f"Категория: {categories.icon(ticket['category'])} {categories.label(ticket['category'])}",
        f"Клиент: {client_line(user, ticket['user_id'])}",
        f"Создано: {fmt_dt(ticket['created_at'], offset_hours)}",
        f"Оператор: {escape(operator_name) if operator_name else '—'}",
    ]
    if ticket.get("closed_at"):
        lines.append(f"Закрыто: {fmt_dt(ticket['closed_at'], offset_hours)}")
    lines.append("")
    lines.append(f"<blockquote>{escape(shorten(ticket['description'], 1500))}</blockquote>")
    if attachments:
        lines.append(f"📎 Вложений: {attachments}")
    return "\n".join(lines)


def format_client_ticket(ticket: Row, operator_name: Optional[str], offset_hours: int) -> str:
    lines = [
        f"🎫 <b>Обращение #{ticket['id']}</b>",
        f"Статус: {statuses.icon(ticket['status'])} {statuses.client_label(ticket['status'])}",
        f"Категория: {categories.label(ticket['category'])}",
        f"Создано: {fmt_dt(ticket['created_at'], offset_hours)}",
    ]
    if operator_name:
        lines.append(f"Оператор: {escape(operator_name)}")
    if ticket.get("closed_at"):
        lines.append(f"Закрыто: {fmt_dt(ticket['closed_at'], offset_hours)}")
    return "\n".join(lines)


def describe_media(message: Row) -> str:
    text = shorten(message.get("text"), 300)
    media_type = message.get("media_type")
    if media_type == "photo":
        return ("📷 фото " + text).strip()
    if media_type == "document":
        name = message.get("file_name") or "файл"
        return (f"📎 {name} " + text).strip()
    return text


def format_history(
    messages: List[Row],
    offset_hours: int,
    operator_names: Dict[int, str],
    viewer: str = "operator",
    now_ts: Optional[int] = None,
) -> str:
    if not messages:
        return "История пуста."
    if now_ts is None:
        now_ts = messages[-1]["created_at"]
    lines: List[str] = []
    for message in messages:
        sender = message.get("sender")
        if sender == "client":
            who = "Вы" if viewer == "client" else "Клиент"
        elif sender == "operator":
            name = operator_names.get(message.get("sender_id"), "")
            who = f"Оператор {name}".strip()
        else:
            who = "Система"
        body = escape(describe_media(message))
        lines.append(f"{fmt_short(message['created_at'], now_ts, offset_hours)} · <b>{escape(who)}:</b> {body}")
    kept: List[str] = []
    total = 0
    for line in reversed(lines):
        total += len(line) + 1
        if total > HISTORY_LIMIT:
            kept.append("…")
            break
        kept.append(line)
    return "<b>История:</b>\n" + "\n".join(reversed(kept))


def format_ticket_row(ticket: Row, user: Optional[Row], operator_name: Optional[str], now_ts: int) -> str:
    name = short_name(user.get("full_name") if user else None)
    parts = [
        f"{statuses.icon(ticket['status'])} <b>#{ticket['id']}</b>",
        categories.short_label(ticket["category"]),
        escape(name),
        f"{format_duration(now_ts - ticket['created_at'])} назад",
    ]
    if operator_name:
        parts.append(f"оп. {escape(short_name(operator_name))}")
    return " · ".join(parts)


def format_tickets_list(
    tickets: List[Row],
    users: Dict[int, Row],
    operator_names: Dict[int, str],
    status: Optional[str],
    category: Optional[str],
    page: int,
    pages: int,
    total: int,
    now_ts: int,
) -> str:
    status_text = statuses.label(status) if status else "все"
    category_text = categories.label(category) if category else "все"
    lines = [
        f"<b>Обращения</b> · статус: {status_text} · категория: {category_text}",
        f"Всего: {total} · страница {page + 1}/{max(pages, 1)}",
        "",
    ]
    if not tickets:
        lines.append("Обращений с такими фильтрами нет.")
    for ticket in tickets:
        operator_name = operator_names.get(ticket.get("operator_id")) if ticket.get("operator_id") else None
        lines.append(format_ticket_row(ticket, users.get(ticket["user_id"]), operator_name, now_ts))
    return "\n".join(lines)


def format_rating(value: Optional[float], count: int) -> str:
    if value is None:
        return "пока нет оценок"
    return f"{value:.1f} из 5 ({count} {plural(count, 'оценка', 'оценки', 'оценок')})"


def plural(number: int, one: str, few: str, many: str) -> str:
    tail = number % 100
    if 11 <= tail <= 19:
        return many
    tail = number % 10
    if tail == 1:
        return one
    if 2 <= tail <= 4:
        return few
    return many


def format_stats(stats: Dict[str, Any], operator_names: Dict[int, str]) -> str:
    by_status = stats["by_status"]
    lines = [
        "📊 <b>Статистика</b>",
        "",
        f"Сегодня: новых {stats['created_today']} · закрыто {stats['closed_today']}",
        f"За 7 дней: новых {stats['created_week']} · закрыто {stats['closed_week']}",
        "",
        f"Сейчас активных: {stats['active']} "
        f"(открыт {by_status.get(statuses.OPEN, 0)} · в работе {by_status.get(statuses.IN_PROGRESS, 0)} · "
        f"ждём клиента {by_status.get(statuses.WAITING_CLIENT, 0)})",
        "",
        f"Первый ответ (7 дн): {format_duration(stats['avg_first_reply'])}",
        f"Время закрытия (7 дн): {format_duration(stats['avg_close'])}",
        f"Оценка (7 дн): {format_rating(stats['avg_rating'], stats['rating_count'])}",
    ]
    operators = stats.get("operators") or {}
    if operators:
        lines.append("")
        lines.append("<b>Операторы</b>")
        ordered = sorted(operators.items(), key=lambda item: (-item[1]["active"], -item[1]["closed_week"]))
        for operator_id, entry in ordered:
            name = escape(operator_names.get(operator_id, str(operator_id)))
            lines.append(
                f"• {name} — в работе {entry['active']} · закрыто {entry['closed_week']} · "
                f"первый ответ {format_duration(entry['avg_first_reply'])}"
            )
    return "\n".join(lines)


def format_reminder(tickets: List[Row], users: Dict[int, Row], now_ts: int, minutes: int) -> str:
    lines = [f"⏰ <b>Без ответа дольше {minutes} мин:</b>"]
    for ticket in tickets:
        user = users.get(ticket["user_id"])
        name = escape(short_name(user.get("full_name") if user else None))
        waiting = format_duration(now_ts - ticket["awaiting_since"])
        lines.append(f"• #{ticket['id']} · {categories.short_label(ticket['category'])} · {name} — {waiting}")
    return "\n".join(lines)

from __future__ import annotations

import math
from typing import Any, Optional, Tuple

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, Filter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot import keyboards, texts
from bot.db import now_ts
from bot.services import categories, statuses
from bot.services.formatting import format_stats, format_tickets_list
from bot.services.stats import DAY, compute_stats
from bot.support import Support
from bot.utils import parse_ticket_number, safe_edit

router = Router(name="operator_commands")


class IsOperator(Filter):
    async def __call__(self, event: Any, **kwargs: Any) -> bool:
        support: Support = kwargs["support"]
        user = event.from_user
        if user is None:
            return False
        if isinstance(event, Message):
            chat_id: Optional[int] = event.chat.id
        else:
            chat_id = event.message.chat.id if isinstance(event.message, Message) else None
        return support.is_operator(user.id, chat_id)


router.message.filter(IsOperator())
router.callback_query.filter(IsOperator())


def parse_filters(args: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    status: Optional[str] = None
    category: Optional[str] = None
    for word in (args or "").split():
        status = status or statuses.parse_status(word)
        category = category or categories.parse_category(word)
    return status, category


async def tickets_page(
    support: Support, status: Optional[str], category: Optional[str], page: int
) -> Tuple[str, InlineKeyboardMarkup]:
    per_page = keyboards.TICKETS_PER_PAGE
    total = await support.db.count_tickets(status, category)
    pages = max(1, math.ceil(total / per_page))
    page = min(max(page, 0), pages - 1)
    tickets = await support.db.list_tickets(status, category, limit=per_page, offset=page * per_page)
    users = await support.db.users_map(ticket["user_id"] for ticket in tickets)
    names = await support.db.operators_map()
    text = format_tickets_list(tickets, users, names, status, category, page, pages, total, now_ts())
    return text, keyboards.tickets_list(status, category, page, pages, tickets)


@router.message(Command("tickets"))
async def cmd_tickets(message: Message, command: CommandObject, support: Support) -> None:
    await support.remember_operator(message.from_user)
    status, category = parse_filters(command.args)
    text, markup = await tickets_page(support, status, category, 0)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("tl:"))
async def cb_tickets(callback: CallbackQuery, support: Support) -> None:
    _, status, category, page = callback.data.split(":")
    text, markup = await tickets_page(
        support, None if status == "all" else status, None if category == "all" else category, int(page)
    )
    await safe_edit(callback.message, text, markup)
    await callback.answer()


@router.message(Command("ticket"))
async def cmd_ticket(message: Message, command: CommandObject, support: Support) -> None:
    await support.remember_operator(message.from_user)
    ticket_id = parse_ticket_number(command.args)
    if ticket_id is None:
        await message.answer(texts.USAGE_TICKET)
        return
    ticket = await support.db.get_ticket(ticket_id)
    if ticket is None:
        await message.answer(texts.TICKET_NOT_FOUND)
        return
    card = await message.answer(await support.card_text(ticket), reply_markup=keyboards.ticket_card(ticket))
    await support.db.add_relay(card.chat.id, card.message_id, ticket["id"], "card")
    history = await message.answer(await support.history_text(ticket))
    await support.db.add_relay(history.chat.id, history.message_id, ticket["id"], "note")


@router.message(Command("stats"))
async def cmd_stats(message: Message, support: Support) -> None:
    await support.remember_operator(message.from_user)
    now = now_ts()
    since = now - 8 * DAY
    tickets = await support.db.tickets_for_stats(since)
    ratings = await support.db.ratings_since(since)
    stats = compute_stats(tickets, ratings, now, support.config.tz_offset_hours)
    await message.answer(format_stats(stats, await support.db.operators_map()))


async def resolve_user_id(message: Message, command: CommandObject, support: Support) -> Optional[int]:
    if message.reply_to_message is not None:
        relay = await support.db.find_relay(message.chat.id, message.reply_to_message.message_id)
        if relay is not None:
            ticket = await support.db.get_ticket(relay["ticket_id"])
            if ticket is not None:
                return ticket["user_id"]
    number = parse_ticket_number(command.args)
    if number is None:
        return None
    ticket = await support.db.get_ticket(number)
    if ticket is not None:
        return ticket["user_id"]
    return number


async def toggle_ban(message: Message, command: CommandObject, support: Support, banned: bool) -> None:
    if not support.is_admin(message.from_user.id):
        await message.answer(texts.ADMIN_ONLY)
        return
    user_id = await resolve_user_id(message, command, support)
    if user_id is None:
        await message.answer(texts.USAGE_BAN)
        return
    if banned and (support.is_operator(user_id) or support.is_admin(user_id)):
        await message.answer(texts.CANNOT_BAN_OPERATOR)
        return
    await support.db.set_banned(user_id, banned)
    await message.answer(texts.banned_ok(user_id) if banned else texts.unbanned_ok(user_id))


@router.message(Command("ban"))
async def cmd_ban(message: Message, command: CommandObject, support: Support) -> None:
    await toggle_ban(message, command, support, True)


@router.message(Command("unban"))
async def cmd_unban(message: Message, command: CommandObject, support: Support) -> None:
    await toggle_ban(message, command, support, False)


@router.message(Command("chatid"))
async def cmd_chatid(message: Message) -> None:
    await message.answer(texts.chat_id_text(message.chat.id, message.chat.type))

from __future__ import annotations

from typing import Any, Dict, Optional, Union

from aiogram import F, Router
from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message

from bot import keyboards, texts
from bot.services import statuses
from bot.services.statuses import InvalidTransition
from bot.services.templates import find_template
from bot.support import Support
from bot.utils import extract_content, safe_edit_markup

router = Router(name="operator")


class TicketReply(Filter):
    async def __call__(self, message: Message, **kwargs: Any) -> Union[bool, Dict[str, Any]]:
        support: Support = kwargs["support"]
        if message.from_user is None or message.from_user.is_bot:
            return False
        ticket = None
        if message.chat.type == "private":
            if message.from_user.id not in support.config.operator_ids or message.reply_to_message is None:
                return False
            relay = await support.db.find_relay(message.chat.id, message.reply_to_message.message_id)
            if relay is None:
                return False
            ticket = await support.db.get_ticket(relay["ticket_id"])
        elif support.config.support_chat_id is not None and message.chat.id == support.config.support_chat_id:
            if message.message_thread_id is None:
                return False
            ticket = await support.db.ticket_by_thread(message.message_thread_id)
        if ticket is None:
            return False
        return {"ticket": ticket}


@router.message(TicketReply(), F.text | F.photo | F.document)
async def operator_reply(message: Message, ticket: Dict[str, Any], support: Support) -> None:
    if message.text and message.text.startswith("/"):
        return
    if ticket["status"] == statuses.CLOSED:
        await message.reply(texts.REPLY_CLOSED)
        return
    text, media_type, file_id, file_name = extract_content(message)
    updated, delivered = await support.operator_reply(ticket, message.from_user, text, media_type, file_id, file_name)
    note = await message.reply(texts.reply_sent(updated) if delivered else texts.reply_not_delivered(updated))
    await support.db.add_relay(note.chat.id, note.message_id, updated["id"], "note")


@router.message(TicketReply())
async def operator_reply_unsupported(message: Message) -> None:
    await message.reply(texts.OPERATOR_UNSUPPORTED)


async def card_context(callback: CallbackQuery, support: Support) -> Optional[Dict[str, Any]]:
    chat_id = callback.message.chat.id if isinstance(callback.message, Message) else None
    if not support.is_operator(callback.from_user.id, chat_id):
        await callback.answer(texts.NOT_OPERATOR, show_alert=True)
        return None
    ticket = await support.db.get_ticket(int(callback.data.split(":")[2]))
    if ticket is None:
        await callback.answer(texts.TICKET_NOT_FOUND, show_alert=True)
        return None
    await support.remember_operator(callback.from_user)
    return ticket


@router.callback_query(F.data.startswith("t:take:"))
async def cb_take(callback: CallbackQuery, support: Support) -> None:
    ticket = await card_context(callback, support)
    if ticket is None:
        return
    try:
        await support.take(ticket, callback.from_user)
    except InvalidTransition:
        if ticket["status"] == statuses.CLOSED:
            await callback.answer(texts.ALREADY_CLOSED, show_alert=True)
        else:
            name = await support.operator_name(ticket.get("operator_id")) or "—"
            await callback.answer(texts.already_taken(name), show_alert=True)
        return
    await callback.answer(texts.TAKEN_OK)


@router.callback_query(F.data.startswith("t:close:"))
async def cb_close(callback: CallbackQuery, support: Support) -> None:
    ticket = await card_context(callback, support)
    if ticket is None:
        return
    try:
        await support.close(ticket, callback.from_user)
    except InvalidTransition:
        await callback.answer(texts.ALREADY_CLOSED, show_alert=True)
        return
    await callback.answer(texts.CLOSED_OK)


@router.callback_query(F.data.startswith("t:tpl:"))
async def cb_templates(callback: CallbackQuery, support: Support) -> None:
    ticket = await card_context(callback, support)
    if ticket is None:
        return
    if not support.templates:
        await callback.answer(texts.TEMPLATES_EMPTY, show_alert=True)
        return
    if ticket["status"] == statuses.CLOSED:
        await callback.answer(texts.ALREADY_CLOSED, show_alert=True)
        return
    await safe_edit_markup(callback.message, keyboards.templates(ticket["id"], support.templates))
    await callback.answer()


@router.callback_query(F.data.startswith("t:tpls:"))
async def cb_template_send(callback: CallbackQuery, support: Support) -> None:
    ticket = await card_context(callback, support)
    if ticket is None:
        return
    template = find_template(support.templates, callback.data.split(":")[3])
    if template is None:
        await callback.answer(texts.TEMPLATES_EMPTY, show_alert=True)
        return
    if ticket["status"] == statuses.CLOSED:
        await callback.answer(texts.ALREADY_CLOSED, show_alert=True)
        return
    updated, delivered = await support.send_template(ticket, callback.from_user, template)
    await safe_edit_markup(callback.message, keyboards.ticket_card(updated))
    if delivered:
        await callback.answer(texts.template_sent(template["title"], updated))
    else:
        await callback.answer(texts.reply_not_delivered(updated), show_alert=True)


@router.callback_query(F.data.startswith("t:back:"))
async def cb_back(callback: CallbackQuery, support: Support) -> None:
    ticket = await card_context(callback, support)
    if ticket is None:
        return
    await safe_edit_markup(callback.message, keyboards.ticket_card(ticket))
    await callback.answer()


@router.callback_query(F.data.startswith("t:hist:"))
async def cb_history(callback: CallbackQuery, support: Support) -> None:
    ticket = await card_context(callback, support)
    if ticket is None:
        return
    if isinstance(callback.message, Message):
        sent = await callback.message.reply(await support.history_text(ticket))
        await support.db.add_relay(sent.chat.id, sent.message_id, ticket["id"], "note")
    await callback.answer()


@router.callback_query(F.data.startswith("t:open:"))
async def cb_open(callback: CallbackQuery, support: Support) -> None:
    ticket = await card_context(callback, support)
    if ticket is None:
        return
    if isinstance(callback.message, Message):
        sent = await callback.message.answer(await support.card_text(ticket), reply_markup=keyboards.ticket_card(ticket))
        await support.db.add_relay(sent.chat.id, sent.message_id, ticket["id"], "card")
    await callback.answer()

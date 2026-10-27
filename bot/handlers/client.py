from __future__ import annotations

from typing import Any, Dict, Optional

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot import keyboards, texts
from bot.db import now_ts
from bot.services import categories, statuses
from bot.services.faq import find_faq, match_faq
from bot.services.formatting import format_client_ticket
from bot.support import Support
from bot.utils import extract_content, safe_edit

router = Router(name="client")
router.message.filter(F.chat.type == "private")

MIN_DESCRIPTION = 5


class NewTicket(StatesGroup):
    category = State()
    description = State()
    faq = State()
    attachment = State()
    confirm = State()


class RatingFlow(StatesGroup):
    comment = State()


async def begin_new_ticket(
    target: Any, state: FSMContext, description: Optional[str] = None, edit: bool = False
) -> None:
    await state.set_state(NewTicket.category)
    await state.update_data(description=description, attachment=None, category=None)
    if edit:
        await safe_edit(target, texts.NEW_CATEGORY, keyboards.category_choice())
    else:
        await target.answer(texts.NEW_CATEGORY, reply_markup=keyboards.category_choice())


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.welcome(message.from_user.first_name), reply_markup=keyboards.main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP, reply_markup=keyboards.main_menu())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.CANCELLED, reply_markup=keyboards.main_menu())


@router.message(Command("new"))
@router.message(F.text == texts.MENU_NEW)
async def menu_new(message: Message, state: FSMContext, support: Support) -> None:
    await state.clear()
    active = await support.db.active_ticket_for_user(message.from_user.id)
    if active is not None:
        await message.answer(texts.has_active_ticket(active), reply_markup=keyboards.active_ticket_choice(active["id"]))
        return
    await begin_new_ticket(message, state)


@router.message(Command("my"))
@router.message(F.text == texts.MENU_MY)
async def menu_my(message: Message, state: FSMContext, support: Support) -> None:
    await state.clear()
    tickets = await support.db.user_tickets(message.from_user.id)
    if not tickets:
        await message.answer(texts.MY_EMPTY, reply_markup=keyboards.main_menu())
        return
    await message.answer(texts.MY_LIST, reply_markup=keyboards.my_tickets(tickets))


@router.message(Command("faq"))
@router.message(F.text == texts.MENU_FAQ)
async def menu_faq(message: Message, state: FSMContext, support: Support) -> None:
    await state.clear()
    await message.answer(texts.FAQ_LIST, reply_markup=keyboards.faq_list(support.faq))


@router.callback_query(F.data == "nt:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(callback.message, texts.CANCELLED)
    await callback.answer()


@router.callback_query(F.data == "nt:new")
async def cb_new(callback: CallbackQuery, state: FSMContext) -> None:
    await begin_new_ticket(callback.message, state, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("nt:write:"))
async def cb_write(callback: CallbackQuery, state: FSMContext, support: Support) -> None:
    await state.clear()
    ticket = await support.db.get_ticket(int(callback.data.split(":")[2]))
    await safe_edit(callback.message, texts.write_to_ticket(ticket) if ticket else texts.TICKET_NOT_FOUND)
    await callback.answer()


@router.callback_query(F.data.in_({"nt:from_text", "faq:need"}))
async def cb_create_from_text(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await begin_new_ticket(callback.message, state, description=data.get("pending_text"), edit=True)
    await callback.answer()


@router.callback_query(F.data == "faq:ok")
async def cb_faq_ok(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(pending_text=None)
    await safe_edit(callback.message, texts.FAQ_HELPED)
    await callback.answer()


@router.callback_query(NewTicket.category, F.data.startswith("nt:cat:"))
async def cb_category(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":")[2]
    if not categories.is_valid(code):
        await callback.answer()
        return
    data = await state.update_data(category=code)
    if data.get("description"):
        await state.set_state(NewTicket.attachment)
        await safe_edit(callback.message, f"{texts.category_chosen(code)}\n\n{texts.NEW_ATTACHMENT}", keyboards.attachment())
    else:
        await state.set_state(NewTicket.description)
        await safe_edit(callback.message, f"{texts.category_chosen(code)}\n\n{texts.NEW_DESCRIPTION}", keyboards.cancel())
    await callback.answer()


@router.message(NewTicket.category)
async def st_category_other(message: Message) -> None:
    await message.answer(texts.NEW_CATEGORY, reply_markup=keyboards.category_choice())


@router.message(NewTicket.description, F.text)
async def st_description(message: Message, state: FSMContext, support: Support) -> None:
    text = message.text.strip()
    if len(text) < MIN_DESCRIPTION:
        await message.answer(texts.DESCRIPTION_TOO_SHORT)
        return
    await state.update_data(description=text)
    entry = match_faq(text, support.faq)
    if entry is not None:
        await state.set_state(NewTicket.faq)
        await message.answer(texts.faq_offer(entry), reply_markup=keyboards.faq_offer(in_flow=True))
        return
    await state.set_state(NewTicket.attachment)
    await message.answer(texts.NEW_ATTACHMENT, reply_markup=keyboards.attachment())


@router.message(NewTicket.description)
async def st_description_other(message: Message) -> None:
    await message.answer(texts.DESCRIPTION_TEXT_ONLY, reply_markup=keyboards.cancel())


@router.callback_query(NewTicket.faq, F.data == "nt:faq_ok")
async def cb_flow_faq_ok(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(callback.message, texts.FAQ_HELPED)
    await callback.answer()


@router.callback_query(NewTicket.faq, F.data == "nt:faq_op")
async def cb_flow_faq_operator(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(NewTicket.attachment)
    await safe_edit(callback.message, texts.NEW_ATTACHMENT, keyboards.attachment())
    await callback.answer()


@router.message(NewTicket.faq)
async def st_faq_other(message: Message) -> None:
    await message.answer(texts.FAQ_CHOOSE)


async def show_confirm(target: Any, state: FSMContext, edit: bool) -> None:
    data = await state.get_data()
    await state.set_state(NewTicket.confirm)
    text = texts.new_confirm(data["category"], data["description"], data.get("attachment"))
    if edit:
        await safe_edit(target, text, keyboards.confirm())
    else:
        await target.answer(text, reply_markup=keyboards.confirm())


@router.message(NewTicket.attachment, F.photo | F.document)
async def st_attachment(message: Message, state: FSMContext) -> None:
    caption, media_type, file_id, file_name = extract_content(message)
    await state.update_data(
        attachment={"media_type": media_type, "file_id": file_id, "file_name": file_name, "caption": caption}
    )
    await show_confirm(message, state, edit=False)


@router.callback_query(NewTicket.attachment, F.data == "nt:skip")
async def cb_skip_attachment(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(attachment=None)
    await show_confirm(callback.message, state, edit=True)
    await callback.answer()


@router.message(NewTicket.attachment)
async def st_attachment_other(message: Message) -> None:
    await message.answer(texts.ATTACHMENT_WRONG, reply_markup=keyboards.attachment())


@router.callback_query(NewTicket.confirm, F.data == "nt:send")
async def cb_send(callback: CallbackQuery, state: FSMContext, support: Support) -> None:
    data = await state.get_data()
    await state.clear()
    ticket = await support.create_ticket(
        callback.from_user, data["category"], data["description"], data.get("attachment")
    )
    await safe_edit(callback.message, texts.ticket_created(ticket))
    await callback.answer("Обращение создано")


@router.callback_query(NewTicket.confirm, F.data == "nt:edit")
async def cb_edit_description(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(NewTicket.description)
    await safe_edit(callback.message, texts.NEW_DESCRIPTION, keyboards.cancel())
    await callback.answer()


@router.message(NewTicket.confirm)
async def st_confirm_other(message: Message) -> None:
    await message.answer(texts.CONFIRM_CHOOSE)


@router.callback_query(F.data == "faq:list")
async def cb_faq_list(callback: CallbackQuery, support: Support) -> None:
    await safe_edit(callback.message, texts.FAQ_LIST, keyboards.faq_list(support.faq))
    await callback.answer()


@router.callback_query(F.data.startswith("faq:show:"))
async def cb_faq_show(callback: CallbackQuery, support: Support) -> None:
    entry = find_faq(support.faq, callback.data.split(":", 2)[2])
    if entry is None:
        await callback.answer(texts.FAQ_NOT_FOUND, show_alert=True)
        return
    await safe_edit(callback.message, texts.faq_answer(entry), keyboards.faq_answer(entry["id"]))
    await callback.answer()


@router.callback_query(F.data.startswith("faq:op:"))
async def cb_faq_operator(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(pending_text=None)
    await begin_new_ticket(callback.message, state, edit=True)
    await callback.answer()


async def owned_ticket(callback: CallbackQuery, support: Support) -> Optional[Dict[str, Any]]:
    ticket = await support.db.get_ticket(int(callback.data.rsplit(":", 1)[1]))
    if ticket is None or ticket["user_id"] != callback.from_user.id:
        await callback.answer(texts.TICKET_NOT_FOUND, show_alert=True)
        return None
    return ticket


@router.callback_query(F.data == "my:list")
async def cb_my_list(callback: CallbackQuery, support: Support) -> None:
    tickets = await support.db.user_tickets(callback.from_user.id)
    if not tickets:
        await safe_edit(callback.message, texts.MY_EMPTY)
    else:
        await safe_edit(callback.message, texts.MY_LIST, keyboards.my_tickets(tickets))
    await callback.answer()


@router.callback_query(F.data.startswith("my:show:"))
async def cb_my_show(callback: CallbackQuery, support: Support) -> None:
    ticket = await owned_ticket(callback, support)
    if ticket is None:
        return
    operator_name = await support.operator_name(ticket.get("operator_id"))
    text = format_client_ticket(ticket, operator_name, support.config.tz_offset_hours)
    text += "\n\n" + await support.history_text(ticket, viewer="client", limit=20)
    can_reopen = ticket["status"] == statuses.CLOSED and statuses.can_reopen(
        ticket.get("closed_at"), now_ts(), support.config.reopen_hours
    )
    await safe_edit(callback.message, text, keyboards.my_ticket(ticket["id"], can_reopen))
    await callback.answer()


async def reopen_ticket(
    callback: CallbackQuery, state: FSMContext, support: Support, ticket: Dict[str, Any], attach_pending: bool
) -> None:
    if ticket["status"] != statuses.CLOSED:
        await callback.answer(texts.ALREADY_OPEN, show_alert=True)
        return
    if not statuses.can_reopen(ticket.get("closed_at"), now_ts(), support.config.reopen_hours):
        await callback.answer(texts.REOPEN_EXPIRED, show_alert=True)
        return
    updated = await support.reopen(ticket, callback.from_user)
    if attach_pending:
        data = await state.get_data()
        pending = data.get("pending_text")
        if pending:
            updated = await support.client_message(updated, callback.from_user, pending, None, None, None)
            await state.update_data(pending_text=None)
    await safe_edit(callback.message, texts.reopen_done(updated))
    await callback.answer()


@router.callback_query(F.data.startswith("my:reopen:"))
async def cb_my_reopen(callback: CallbackQuery, state: FSMContext, support: Support) -> None:
    ticket = await owned_ticket(callback, support)
    if ticket is not None:
        await reopen_ticket(callback, state, support, ticket, attach_pending=False)


@router.callback_query(F.data.startswith("re:reopen:"))
async def cb_reopen_with_text(callback: CallbackQuery, state: FSMContext, support: Support) -> None:
    ticket = await owned_ticket(callback, support)
    if ticket is not None:
        await reopen_ticket(callback, state, support, ticket, attach_pending=True)


@router.callback_query(F.data.startswith("rate:skip:"))
async def cb_rate_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(callback.message, texts.RATING_DONE)
    await callback.answer()


@router.callback_query(F.data.startswith("rate:"))
async def cb_rate(callback: CallbackQuery, state: FSMContext, support: Support) -> None:
    parts = callback.data.split(":")
    ticket = await support.db.get_ticket(int(parts[1]))
    score = int(parts[2])
    if ticket is None or ticket["user_id"] != callback.from_user.id or not 1 <= score <= 5:
        await callback.answer(texts.TICKET_NOT_FOUND, show_alert=True)
        return
    if ticket["status"] != statuses.CLOSED:
        await callback.answer(texts.RATING_NOT_CLOSED, show_alert=True)
        return
    if await support.db.get_rating(ticket["id"]) is not None:
        await callback.answer(texts.RATING_TWICE, show_alert=True)
        return
    await support.rate(ticket, callback.from_user, score)
    await state.set_state(RatingFlow.comment)
    await state.update_data(rating_ticket=ticket["id"])
    await safe_edit(callback.message, texts.rating_thanks(score), keyboards.skip_comment(ticket["id"]))
    await callback.answer()


@router.message(RatingFlow.comment, F.text)
async def st_rating_comment(message: Message, state: FSMContext, support: Support) -> None:
    data = await state.get_data()
    await state.clear()
    ticket = await support.db.get_ticket(int(data.get("rating_ticket") or 0))
    if ticket is not None:
        await support.rating_comment(ticket, message.from_user, message.text.strip())
    await message.answer(texts.RATING_COMMENT_SAVED, reply_markup=keyboards.main_menu())


@router.message(RatingFlow.comment)
async def st_rating_other(message: Message) -> None:
    await message.answer(texts.RATING_COMMENT_TEXT)


@router.message(StateFilter(None), F.text | F.photo | F.document)
async def free_message(message: Message, state: FSMContext, support: Support) -> None:
    if message.text and message.text.startswith("/"):
        await message.answer(texts.UNKNOWN_COMMAND, reply_markup=keyboards.main_menu())
        return
    text, media_type, file_id, file_name = extract_content(message)
    user = message.from_user
    active = await support.db.active_ticket_for_user(user.id)
    if active is not None:
        updated = await support.client_message(active, user, text, media_type, file_id, file_name)
        await support.acknowledge(message, updated)
        return
    if media_type:
        await message.answer(texts.MEDIA_WITHOUT_TICKET, reply_markup=keyboards.new_ticket_button())
        return
    await state.update_data(pending_text=text)
    entry = match_faq(text, support.faq)
    if entry is not None:
        await message.answer(texts.faq_offer(entry), reply_markup=keyboards.faq_offer(in_flow=False))
        return
    last = await support.db.latest_ticket_for_user(user.id)
    if (
        last is not None
        and last["status"] == statuses.CLOSED
        and statuses.can_reopen(last.get("closed_at"), now_ts(), support.config.reopen_hours)
    ):
        await message.answer(texts.closed_recently(last), reply_markup=keyboards.reopen_or_new(last["id"]))
        return
    await message.answer(texts.NO_FAQ_MATCH, reply_markup=keyboards.create_from_text())


@router.message(StateFilter(None))
async def unsupported(message: Message) -> None:
    await message.answer(texts.UNSUPPORTED_CONTENT)


@router.callback_query()
async def stale_callback(callback: CallbackQuery) -> None:
    await callback.answer(texts.STALE_BUTTON)

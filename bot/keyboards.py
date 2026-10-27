from __future__ import annotations

from typing import Any, Dict, List, Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import texts
from bot.services import categories, statuses

Row = Dict[str, Any]

TICKETS_PER_PAGE = 10


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.MENU_NEW), KeyboardButton(text=texts.MENU_MY)],
            [KeyboardButton(text=texts.MENU_FAQ)],
        ],
        resize_keyboard=True,
        input_field_placeholder=texts.MENU_PLACEHOLDER,
    )


def category_choice() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code in categories.ORDER:
        builder.button(text=f"{categories.icon(code)} {categories.label(code)}", callback_data=f"nt:cat:{code}")
    builder.adjust(2)
    builder.row(_cancel_button())
    return builder.as_markup()


def _cancel_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="nt:cancel")


def cancel() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.BTN_CANCEL, callback_data="nt:cancel")
    return builder.as_markup()


def attachment() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.BTN_SKIP, callback_data="nt:skip")
    builder.button(text=texts.BTN_CANCEL, callback_data="nt:cancel")
    builder.adjust(2)
    return builder.as_markup()


def confirm() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.BTN_SEND, callback_data="nt:send")
    builder.button(text=texts.BTN_EDIT, callback_data="nt:edit")
    builder.button(text=texts.BTN_CANCEL, callback_data="nt:cancel")
    builder.adjust(1, 2)
    return builder.as_markup()


def faq_offer(in_flow: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.BTN_HELPED, callback_data="nt:faq_ok" if in_flow else "faq:ok")
    builder.button(text=texts.BTN_NEED_OPERATOR, callback_data="nt:faq_op" if in_flow else "faq:need")
    builder.adjust(2)
    return builder.as_markup()


def faq_list(faq: List[Row]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for entry in faq:
        builder.button(text=entry["question"], callback_data=f"faq:show:{entry['id']}")
    builder.adjust(1)
    return builder.as_markup()


def faq_answer(entry_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.BTN_BACK, callback_data="faq:list")
    builder.button(text=texts.BTN_NEED_OPERATOR, callback_data=f"faq:op:{entry_id}")
    builder.adjust(2)
    return builder.as_markup()


def create_from_text() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.BTN_CREATE, callback_data="nt:from_text")
    builder.button(text=texts.BTN_CANCEL, callback_data="nt:cancel")
    builder.adjust(2)
    return builder.as_markup()


def new_ticket_button() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.MENU_NEW, callback_data="nt:new")
    return builder.as_markup()


def active_ticket_choice(ticket_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Написать в #{ticket_id}", callback_data=f"nt:write:{ticket_id}")
    builder.button(text=texts.BTN_CREATE_NEW, callback_data="nt:new")
    builder.adjust(2)
    return builder.as_markup()


def reopen_or_new(ticket_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{texts.BTN_REOPEN} #{ticket_id}", callback_data=f"re:reopen:{ticket_id}")
    builder.button(text=texts.BTN_CREATE_NEW, callback_data="nt:from_text")
    builder.adjust(2)
    return builder.as_markup()


def my_tickets(tickets: List[Row]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ticket in tickets:
        label = f"{statuses.icon(ticket['status'])} #{ticket['id']} · {categories.short_label(ticket['category'])} · {statuses.label(ticket['status'])}"
        builder.button(text=label, callback_data=f"my:show:{ticket['id']}")
    builder.adjust(1)
    return builder.as_markup()


def my_ticket(ticket_id: int, can_reopen: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_reopen:
        builder.button(text=texts.BTN_REOPEN, callback_data=f"my:reopen:{ticket_id}")
    builder.button(text=texts.BTN_TO_LIST, callback_data="my:list")
    builder.adjust(2)
    return builder.as_markup()


def rating(ticket_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for score in range(1, 6):
        builder.button(text=str(score), callback_data=f"rate:{ticket_id}:{score}")
    builder.adjust(5)
    builder.button(text=texts.BTN_REOPEN, callback_data=f"my:reopen:{ticket_id}")
    builder.adjust(5, 1)
    return builder.as_markup()


def skip_comment(ticket_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.BTN_SKIP, callback_data=f"rate:skip:{ticket_id}")
    return builder.as_markup()


def ticket_card(ticket: Row) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    ticket_id = ticket["id"]
    status = ticket["status"]
    if status == statuses.OPEN:
        builder.button(text=texts.BTN_TAKE, callback_data=f"t:take:{ticket_id}")
    if status != statuses.CLOSED:
        builder.button(text=texts.BTN_CLOSE, callback_data=f"t:close:{ticket_id}")
        builder.button(text=texts.BTN_TEMPLATES, callback_data=f"t:tpl:{ticket_id}")
    builder.button(text=texts.BTN_HISTORY, callback_data=f"t:hist:{ticket_id}")
    builder.adjust(2)
    return builder.as_markup()


def templates(ticket_id: int, items: List[Row]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for template in items:
        builder.button(text=template["title"], callback_data=f"t:tpls:{ticket_id}:{template['id']}")
    builder.adjust(2)
    builder.row(_back_button(ticket_id))
    return builder.as_markup()


def _back_button(ticket_id: int) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=texts.BTN_BACK, callback_data=f"t:back:{ticket_id}")


def _mark(text: str, selected: bool) -> str:
    return f"• {text}" if selected else text


def tickets_list(
    status: Optional[str],
    category: Optional[str],
    page: int,
    pages: int,
    tickets: List[Row],
) -> InlineKeyboardMarkup:
    status_key = status or "all"
    category_key = category or "all"
    rows: List[List[InlineKeyboardButton]] = []

    status_options = [(None, "Все"), (statuses.OPEN, "Открытые"), (statuses.IN_PROGRESS, "В работе")]
    rows.append(
        [
            InlineKeyboardButton(text=_mark(title, status == code), callback_data=f"tl:{code or 'all'}:{category_key}:0")
            for code, title in status_options
        ]
    )
    status_options = [(statuses.WAITING_CLIENT, "Ждём клиента"), (statuses.CLOSED, "Закрытые")]
    rows.append(
        [
            InlineKeyboardButton(text=_mark(title, status == code), callback_data=f"tl:{code}:{category_key}:0")
            for code, title in status_options
        ]
    )
    rows.append(
        [InlineKeyboardButton(text=_mark("Все категории", category is None), callback_data=f"tl:{status_key}:all:0")]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=_mark(categories.short_label(code), category == code),
                callback_data=f"tl:{status_key}:{code}:0",
            )
            for code in categories.ORDER
        ]
    )
    ticket_buttons = [
        InlineKeyboardButton(text=f"#{ticket['id']}", callback_data=f"t:open:{ticket['id']}") for ticket in tickets
    ]
    for index in range(0, len(ticket_buttons), 5):
        rows.append(ticket_buttons[index : index + 5])
    nav: List[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=texts.BTN_PREV, callback_data=f"tl:{status_key}:{category_key}:{page - 1}"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton(text=texts.BTN_NEXT, callback_data=f"tl:{status_key}:{category_key}:{page + 1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)

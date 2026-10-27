from __future__ import annotations

import logging
from html import escape
from typing import Any, Dict, List, Optional, Tuple

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message, ReactionTypeEmoji, User

from bot import keyboards, texts
from bot.config import Config
from bot.db import Database, now_ts
from bot.services import categories, statuses
from bot.services.faq import load_faq
from bot.services.formatting import first_name, format_history, format_ticket_card, shorten
from bot.services.templates import load_templates, render_template

logger = logging.getLogger(__name__)

Row = Dict[str, Any]
Target = Tuple[int, Optional[int]]


class Support:
    def __init__(self, bot: Bot, db: Database, config: Config) -> None:
        self.bot = bot
        self.db = db
        self.config = config
        self.faq = load_faq(config.faq_path)
        self.templates = load_templates(config.templates_path)

    def is_operator(self, user_id: int, chat_id: Optional[int] = None) -> bool:
        if user_id in self.config.operator_ids:
            return True
        return self.config.support_chat_id is not None and chat_id == self.config.support_chat_id

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.config.admin_ids

    async def remember_operator(self, user: User) -> None:
        await self.db.upsert_operator(user.id, user.full_name, user.username)

    async def operator_name(self, operator_id: Optional[int]) -> Optional[str]:
        if operator_id is None:
            return None
        row = await self.db.get_operator(operator_id)
        if row and row.get("full_name"):
            return row["full_name"]
        return str(operator_id)

    async def card_text(self, ticket: Row) -> str:
        user = await self.db.get_user(ticket["user_id"])
        operator_name = await self.operator_name(ticket.get("operator_id"))
        attachments = await self.db.count_attachments(ticket["id"])
        return format_ticket_card(ticket, user, operator_name, attachments, self.config.tz_offset_hours)

    async def history_text(self, ticket: Row, viewer: str = "operator", limit: int = 30) -> str:
        messages = await self.db.ticket_messages(ticket["id"], limit=limit)
        names = await self.db.operators_map()
        return format_history(messages, self.config.tz_offset_hours, names, viewer=viewer, now_ts=now_ts())

    async def targets(self, ticket: Row) -> List[Target]:
        result: List[Target] = [(operator_id, None) for operator_id in self.config.operator_ids]
        if self.config.support_chat_id is not None:
            thread_id = await self.ensure_topic(ticket)
            result.append((self.config.support_chat_id, thread_id))
        return result

    async def ensure_topic(self, ticket: Row) -> Optional[int]:
        if ticket.get("thread_id") is not None:
            return ticket["thread_id"]
        chat_id = self.config.support_chat_id
        if chat_id is None:
            return None
        user = await self.db.get_user(ticket["user_id"])
        name = (user or {}).get("full_name") or str(ticket["user_id"])
        title = f"#{ticket['id']} · {categories.label(ticket['category'])} · {name}"[:128]
        try:
            topic = await self.bot.create_forum_topic(chat_id=chat_id, name=title)
        except TelegramAPIError as error:
            logger.warning("Не удалось создать топик для #%s: %s", ticket["id"], error)
            return None
        await self.db.update_ticket(ticket["id"], thread_id=topic.message_thread_id)
        ticket["thread_id"] = topic.message_thread_id
        return topic.message_thread_id

    async def _send(
        self,
        chat_id: int,
        thread_id: Optional[int],
        header: str,
        text: Optional[str],
        media_type: Optional[str] = None,
        file_id: Optional[str] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> Message:
        body = escape(shorten(text, 900 if media_type else 3800))
        content = "\n".join(part for part in (header, body) if part)
        if media_type == "photo":
            return await self.bot.send_photo(
                chat_id, photo=file_id, caption=content, message_thread_id=thread_id, reply_markup=reply_markup
            )
        if media_type == "document":
            return await self.bot.send_document(
                chat_id, document=file_id, caption=content, message_thread_id=thread_id, reply_markup=reply_markup
            )
        return await self.bot.send_message(
            chat_id, content or "…", message_thread_id=thread_id, reply_markup=reply_markup
        )

    async def announce_ticket(self, ticket: Row, reopened: bool = False) -> None:
        text = await self.card_text(ticket)
        if reopened:
            text = texts.CARD_REOPENED_PREFIX + text
        markup = keyboards.ticket_card(ticket)
        for chat_id, thread_id in await self.targets(ticket):
            try:
                sent = await self.bot.send_message(chat_id, text, reply_markup=markup, message_thread_id=thread_id)
            except TelegramAPIError as error:
                logger.warning("Карточка #%s не отправлена в чат %s: %s", ticket["id"], chat_id, error)
                continue
            await self.db.add_relay(chat_id, sent.message_id, ticket["id"], "card")

    async def refresh_cards(self, ticket: Row) -> None:
        text = await self.card_text(ticket)
        markup = keyboards.ticket_card(ticket)
        for relay in await self.db.latest_cards(ticket["id"]):
            try:
                await self.bot.edit_message_text(
                    text, chat_id=relay["chat_id"], message_id=relay["message_id"], reply_markup=markup
                )
            except TelegramBadRequest as error:
                if "message is not modified" not in str(error):
                    logger.debug("Карточка #%s в чате %s не обновлена: %s", ticket["id"], relay["chat_id"], error)
            except TelegramAPIError as error:
                logger.warning("Карточка #%s в чате %s не обновлена: %s", ticket["id"], relay["chat_id"], error)

    async def relay_client_content(
        self,
        ticket: Row,
        user_name: str,
        text: Optional[str],
        media_type: Optional[str],
        file_id: Optional[str],
        file_name: Optional[str],
    ) -> None:
        header = texts.relay_header(ticket, user_name)
        if media_type == "document" and file_name:
            header += f"\n📎 {escape(file_name)}"
        for chat_id, thread_id in await self.targets(ticket):
            try:
                sent = await self._send(chat_id, thread_id, header, text, media_type, file_id)
            except TelegramAPIError as error:
                logger.warning("Сообщение клиента по #%s не доставлено в чат %s: %s", ticket["id"], chat_id, error)
                continue
            await self.db.add_relay(chat_id, sent.message_id, ticket["id"], "client_message")

    async def send_to_client(
        self,
        ticket: Row,
        header: str,
        text: Optional[str],
        media_type: Optional[str] = None,
        file_id: Optional[str] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> bool:
        try:
            await self._send(ticket["user_id"], None, header, text, media_type, file_id, reply_markup)
        except TelegramAPIError as error:
            logger.warning("Клиент %s недоступен: %s", ticket["user_id"], error)
            return False
        return True

    async def notify_client(self, ticket: Row, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None) -> bool:
        try:
            await self.bot.send_message(ticket["user_id"], text, reply_markup=reply_markup)
        except TelegramAPIError as error:
            logger.warning("Уведомление клиенту %s не доставлено: %s", ticket["user_id"], error)
            return False
        return True

    async def broadcast(self, text: str) -> None:
        chats: List[int] = list(self.config.operator_ids)
        if self.config.support_chat_id is not None:
            chats.append(self.config.support_chat_id)
        for chat_id in chats:
            try:
                await self.bot.send_message(chat_id, text)
            except TelegramAPIError as error:
                logger.warning("Сообщение в чат %s не отправлено: %s", chat_id, error)

    async def note_to_operators(self, ticket: Row, text: str) -> None:
        for chat_id, thread_id in await self.targets(ticket):
            try:
                sent = await self.bot.send_message(chat_id, text, message_thread_id=thread_id)
            except TelegramAPIError as error:
                logger.warning("Заметка по #%s не отправлена в чат %s: %s", ticket["id"], chat_id, error)
                continue
            await self.db.add_relay(chat_id, sent.message_id, ticket["id"], "note")

    async def create_ticket(
        self, user: User, category: str, description: str, attachment: Optional[Dict[str, Any]]
    ) -> Row:
        ts = now_ts()
        ticket = await self.db.create_ticket(user.id, category, description, ts)
        await self.db.add_message(ticket["id"], "client", user.id, description, ts=ts)
        if attachment:
            await self.db.add_message(
                ticket["id"],
                "client",
                user.id,
                attachment.get("caption"),
                attachment.get("media_type"),
                attachment.get("file_id"),
                attachment.get("file_name"),
                ts,
            )
        await self.announce_ticket(ticket)
        if attachment:
            await self.relay_client_content(
                ticket,
                user.full_name,
                attachment.get("caption"),
                attachment.get("media_type"),
                attachment.get("file_id"),
                attachment.get("file_name"),
            )
        logger.info("Создано обращение #%s (%s) от %s", ticket["id"], category, user.id)
        return ticket

    async def client_message(
        self,
        ticket: Row,
        user: User,
        text: Optional[str],
        media_type: Optional[str],
        file_id: Optional[str],
        file_name: Optional[str],
    ) -> Row:
        new_status = statuses.on_client_message(ticket["status"])
        ts = now_ts()
        fields: Dict[str, Any] = {"last_client_at": ts}
        if ticket.get("awaiting_since") is None:
            fields["awaiting_since"] = ts
            fields["reminded_at"] = None
        if new_status != ticket["status"]:
            fields["status"] = new_status
        await self.db.add_message(ticket["id"], "client", user.id, text, media_type, file_id, file_name, ts)
        updated = await self.db.update_ticket(ticket["id"], **fields)
        await self.relay_client_content(updated, user.full_name, text, media_type, file_id, file_name)
        if new_status != ticket["status"] or media_type:
            await self.refresh_cards(updated)
        return updated

    async def take(self, ticket: Row, operator: User) -> Row:
        new_status = statuses.on_take(ticket["status"])
        ts = now_ts()
        await self.remember_operator(operator)
        updated = await self.db.update_ticket(ticket["id"], status=new_status, operator_id=operator.id, taken_at=ts)
        await self.db.add_message(ticket["id"], "system", operator.id, texts.history_taken(operator.full_name), ts=ts)
        await self.notify_client(updated, texts.client_taken(updated, operator.full_name))
        await self.refresh_cards(updated)
        return updated

    async def close(self, ticket: Row, operator: User) -> Row:
        new_status = statuses.on_close(ticket["status"])
        ts = now_ts()
        await self.remember_operator(operator)
        fields: Dict[str, Any] = {"status": new_status, "closed_at": ts, "awaiting_since": None, "reminded_at": None}
        if ticket.get("operator_id") is None:
            fields["operator_id"] = operator.id
            fields["taken_at"] = ticket.get("taken_at") or ts
        updated = await self.db.update_ticket(ticket["id"], **fields)
        await self.db.add_message(ticket["id"], "system", operator.id, texts.history_closed(operator.full_name), ts=ts)
        await self.notify_client(updated, texts.client_closed(updated), reply_markup=keyboards.rating(updated["id"]))
        await self.refresh_cards(updated)
        return updated

    async def reopen(self, ticket: Row, user: User) -> Row:
        new_status = statuses.on_reopen(ticket["status"], ticket.get("operator_id") is not None)
        ts = now_ts()
        updated = await self.db.update_ticket(
            ticket["id"], status=new_status, closed_at=None, reopened_at=ts, awaiting_since=ts, reminded_at=None
        )
        await self.db.add_message(ticket["id"], "system", user.id, texts.HISTORY_REOPENED, ts=ts)
        await self.refresh_cards(updated)
        await self.announce_ticket(updated, reopened=True)
        return updated

    async def operator_reply(
        self,
        ticket: Row,
        operator: User,
        text: Optional[str],
        media_type: Optional[str],
        file_id: Optional[str],
        file_name: Optional[str],
    ) -> Tuple[Row, bool]:
        new_status = statuses.on_operator_reply(ticket["status"])
        ts = now_ts()
        await self.remember_operator(operator)
        header = texts.client_reply_header(ticket, operator.full_name)
        delivered = await self.send_to_client(ticket, header, text, media_type, file_id)
        await self.db.add_message(ticket["id"], "operator", operator.id, text, media_type, file_id, file_name, ts)
        fields: Dict[str, Any] = {
            "status": new_status,
            "last_operator_at": ts,
            "awaiting_since": None,
            "reminded_at": None,
        }
        if ticket.get("first_reply_at") is None:
            fields["first_reply_at"] = ts
        if ticket.get("operator_id") is None:
            fields["operator_id"] = operator.id
            fields["taken_at"] = ts
        updated = await self.db.update_ticket(ticket["id"], **fields)
        await self.refresh_cards(updated)
        return updated, delivered

    async def send_template(self, ticket: Row, operator: User, template: Dict[str, Any]) -> Tuple[Row, bool]:
        user = await self.db.get_user(ticket["user_id"])
        text = render_template(
            template["text"],
            name=first_name((user or {}).get("full_name")),
            operator=operator.full_name,
        )
        return await self.operator_reply(ticket, operator, text, None, None, None)

    async def rate(self, ticket: Row, user: User, score: int) -> None:
        await self.db.add_rating(ticket["id"], user.id, score)
        await self.note_to_operators(ticket, texts.operator_rating_note(ticket, user.full_name, score))

    async def rating_comment(self, ticket: Row, user: User, comment: str) -> None:
        await self.db.set_rating_comment(ticket["id"], comment)
        await self.note_to_operators(ticket, texts.operator_comment_note(ticket, user.full_name, comment))

    async def acknowledge(self, message: Message, ticket: Row) -> None:
        try:
            await message.react([ReactionTypeEmoji(emoji="👌")])
        except TelegramAPIError:
            await message.answer(texts.client_message_added(ticket))

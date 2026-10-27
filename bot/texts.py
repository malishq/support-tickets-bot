from __future__ import annotations

from html import escape
from typing import Any, Dict, Optional

from bot.services import categories, statuses

Row = Dict[str, Any]

BOT_DESCRIPTION = (
    "Служба поддержки. Создайте обращение, приложите фото или файл — оператор ответит прямо здесь. "
    "Статусы, история переписки и ответы на частые вопросы всегда под рукой."
)
BOT_SHORT_DESCRIPTION = "Обращения в поддержку: вопрос, фото, ответ оператора — в одном чате."

MENU_NEW = "Новое обращение"
MENU_MY = "Мои обращения"
MENU_FAQ = "Частые вопросы"
MENU_PLACEHOLDER = "Опишите проблему или выберите действие"

BTN_CANCEL = "Отмена"
BTN_SKIP = "Пропустить"
BTN_SEND = "Отправить"
BTN_EDIT = "Изменить описание"
BTN_HELPED = "Помогло"
BTN_NEED_OPERATOR = "Нужен оператор"
BTN_BACK = "Назад"
BTN_TO_LIST = "К списку"
BTN_REOPEN = "Переоткрыть"
BTN_CREATE = "Создать обращение"
BTN_CREATE_NEW = "Создать новое"
BTN_TAKE = "Взять в работу"
BTN_CLOSE = "Закрыть"
BTN_TEMPLATES = "Шаблоны ответов"
BTN_HISTORY = "История"
BTN_PREV = "◀️"
BTN_NEXT = "▶️"


def welcome(name: str) -> str:
    return (
        f"Здравствуйте, {escape(name)}! Это служба поддержки.\n\n"
        "Здесь можно создать обращение, приложить фото или файл и получить ответ оператора прямо в этом чате.\n\n"
        "Выберите действие в меню или просто опишите, что случилось."
    )


HELP = (
    "<b>Как это работает</b>\n"
    "• «Новое обращение» — выберите тему, опишите проблему, при желании приложите фото или файл.\n"
    "• Пока обращение открыто, любое ваше сообщение здесь уходит оператору.\n"
    "• «Мои обращения» — статусы и история переписки.\n"
    "• «Частые вопросы» — ответы, которые помогают сразу.\n\n"
    "Команды: /new — новое обращение, /my — мои обращения, /faq — частые вопросы, /cancel — отменить действие."
)

BANNED = "Доступ к поддержке ограничен. Если это ошибка, свяжитесь с нами другим способом."
CANCELLED = "Отменили. Чем ещё помочь?"
UNKNOWN_COMMAND = "Такой команды нет. Нажмите /help, чтобы посмотреть, что я умею."
UNSUPPORTED_CONTENT = "Поддерживаем текст, фото и файлы. Пришлите, пожалуйста, в одном из этих форматов."

NEW_CATEGORY = "О чём обращение? Выберите категорию:"
NEW_DESCRIPTION = "Опишите проблему одним сообщением: что случилось, номер заказа, когда это произошло."
DESCRIPTION_TOO_SHORT = "Слишком коротко. Опишите, пожалуйста, чуть подробнее — хотя бы пару слов."
DESCRIPTION_TEXT_ONLY = "Сначала опишите проблему текстом. Фото или файл можно будет приложить на следующем шаге."
NEW_ATTACHMENT = "Если есть скриншот, фото или файл — пришлите его сейчас. Если нет, нажмите «Пропустить»."
ATTACHMENT_WRONG = "Это не фото и не файл. Пришлите фото или документ либо нажмите «Пропустить»."
FAQ_HELPED = "Отлично, рады помочь! Если появится вопрос — напишите."
FAQ_LIST = "Частые вопросы — выберите тему:"
FAQ_NOT_FOUND = "Этот вопрос уже убрали из базы."
NO_FAQ_MATCH = "Готового ответа не нашли. Создать обращение, чтобы вам ответил оператор?"
MEDIA_WITHOUT_TICKET = (
    "Чтобы отправить фото или файл оператору, сначала создайте обращение — вложение можно будет добавить на втором шаге."
)
MY_EMPTY = "У вас пока нет обращений. Нажмите «Новое обращение», чтобы создать первое."
MY_LIST = "Ваши обращения:"
REOPEN_EXPIRED = "Переоткрыть можно в течение 24 часов после закрытия. Создайте, пожалуйста, новое обращение."
ALREADY_OPEN = "Это обращение уже открыто."
RATING_DONE = "Спасибо за оценку! Хорошего дня."
RATING_COMMENT_SAVED = "Спасибо за отзыв! Он поможет нам стать лучше."
RATING_TWICE = "Вы уже оценили это обращение."
RATING_NOT_CLOSED = "Оценить можно после закрытия обращения."
TICKET_NOT_FOUND = "Обращение не найдено."
NOT_OPERATOR = "Эта кнопка только для операторов."
ADMIN_ONLY = "Команда доступна только администраторам."
TAKEN_OK = "Обращение у вас в работе"
CLOSED_OK = "Обращение закрыто"
ALREADY_CLOSED = "Обращение уже закрыто"
REPLY_CLOSED = "Обращение закрыто, ответ не отправлен. Клиент может переоткрыть его в течение 24 часов."
REPLY_HINT = "Чтобы ответить клиенту, ответьте (reply) на карточку обращения или на его сообщение."
OPERATOR_UNSUPPORTED = "Клиенту можно отправить текст, фото или файл."
TEMPLATES_EMPTY = "Шаблоны не настроены: добавьте их в data/templates.json."
USAGE_TICKET = "Укажите номер обращения: /ticket 1001"
USAGE_BAN = "Укажите id пользователя или номер обращения: /ban 123456789 или /ban 1001"
HISTORY_REOPENED = "Обращение переоткрыто клиентом"


def category_chosen(code: str) -> str:
    return f"Категория: {categories.icon(code)} {categories.label(code)}"


def new_confirm(category: str, description: str, attachment: Optional[Dict[str, Any]]) -> str:
    attachment_text = "нет"
    if attachment:
        attachment_text = "фото" if attachment.get("media_type") == "photo" else f"файл {escape(attachment.get('file_name') or '')}".strip()
    return (
        "<b>Проверьте обращение</b>\n\n"
        f"Категория: {categories.icon(category)} {categories.label(category)}\n"
        f"Описание: {escape(description)}\n"
        f"Вложение: {attachment_text}\n\n"
        "Отправить оператору?"
    )


def ticket_created(ticket: Row) -> str:
    return (
        f"Обращение <b>#{ticket['id']}</b> создано ✅\n"
        f"Статус: {statuses.icon(ticket['status'])} {statuses.client_label(ticket['status'])}\n\n"
        "Оператор ответит здесь, в этом чате. Если хотите что-то добавить — просто напишите."
    )


def faq_offer(entry: Dict[str, Any]) -> str:
    return (
        "Похоже, у нас уже есть ответ:\n\n"
        f"<b>{escape(entry['question'])}</b>\n{escape(entry['answer'])}\n\n"
        "Это помогло?"
    )


def faq_answer(entry: Dict[str, Any]) -> str:
    return f"<b>{escape(entry['question'])}</b>\n\n{escape(entry['answer'])}"


def has_active_ticket(ticket: Row) -> str:
    return (
        f"У вас уже есть обращение <b>#{ticket['id']}</b> ({statuses.client_label(ticket['status'])}).\n"
        "Напишите сообщение — оно попадёт в него. Или создать новое?"
    )


def write_to_ticket(ticket: Row) -> str:
    return f"Напишите сообщение — оно попадёт в обращение #{ticket['id']}."


def closed_recently(ticket: Row) -> str:
    return f"Ваше последнее обращение <b>#{ticket['id']}</b> закрыто. Переоткрыть его или создать новое?"


def client_message_added(ticket: Row) -> str:
    return f"Передали оператору · #{ticket['id']}"


def client_taken(ticket: Row, operator_name: str) -> str:
    return f"Ваше обращение <b>#{ticket['id']}</b> в работе — его ведёт оператор {escape(operator_name)}."


def client_closed(ticket: Row) -> str:
    return (
        f"Обращение <b>#{ticket['id']}</b> закрыто. Спасибо, что написали!\n\n"
        "Оцените, пожалуйста, как вам помогли — от 1 до 5. "
        "Если вопрос не решён, обращение можно переоткрыть в течение 24 часов."
    )


def rating_thanks(score: int) -> str:
    return (
        f"Спасибо за оценку {score}! Хотите добавить комментарий? "
        "Напишите его одним сообщением или нажмите «Пропустить»."
    )


def reopen_done(ticket: Row) -> str:
    return (
        f"Обращение <b>#{ticket['id']}</b> переоткрыто, статус: {statuses.client_label(ticket['status'])}. "
        "Напишите, что ещё не так — оператор увидит."
    )


def client_reply_header(ticket: Row, operator_name: str) -> str:
    return f"💬 <b>Оператор {escape(operator_name)}</b> · обращение #{ticket['id']}"


def relay_header(ticket: Row, user_name: str) -> str:
    return f"✉️ <b>#{ticket['id']}</b> · {escape(user_name)}"


CARD_REOPENED_PREFIX = "🔁 <b>Обращение переоткрыто клиентом</b>\n\n"


def already_taken(operator_name: str) -> str:
    return f"Уже в работе: {operator_name}"


def reply_sent(ticket: Row) -> str:
    return f"✅ Отправлено клиенту · #{ticket['id']}"


def reply_not_delivered(ticket: Row) -> str:
    return f"⚠️ Не удалось доставить клиенту (#{ticket['id']}): возможно, он заблокировал бота."


def template_sent(template_title: str, ticket: Row) -> str:
    return f"Шаблон «{template_title}» отправлен · #{ticket['id']}"


def history_taken(operator_name: str) -> str:
    return f"В работе у оператора {operator_name}"


def history_closed(operator_name: str) -> str:
    return f"Обращение закрыто оператором {operator_name}"


def operator_rating_note(ticket: Row, user_name: str, score: int) -> str:
    return f"⭐ Оценка по обращению #{ticket['id']}: <b>{score} из 5</b> — {escape(user_name)}"


def operator_comment_note(ticket: Row, user_name: str, comment: str) -> str:
    return f"💬 Комментарий к оценке по #{ticket['id']} от {escape(user_name)}:\n<blockquote>{escape(comment)}</blockquote>"


def banned_ok(user_id: int) -> str:
    return f"Пользователь {user_id} заблокирован: его сообщения больше не принимаются."


def unbanned_ok(user_id: int) -> str:
    return f"Пользователь {user_id} разблокирован."


def chat_id_text(chat_id: int, chat_type: str) -> str:
    return f"Id этого чата: <code>{chat_id}</code> (тип: {chat_type})"

ERROR = "Что-то пошло не так. Попробуйте ещё раз чуть позже."
STALE_BUTTON = "Эта кнопка уже неактуальна. Откройте меню заново."
FAQ_CHOOSE = "Нажмите «Помогло» или «Нужен оператор» под ответом выше."
CONFIRM_CHOOSE = "Нажмите «Отправить», чтобы передать обращение оператору, или «Отмена»."
RATING_COMMENT_TEXT = "Комментарий — текстом, пожалуйста. Или нажмите «Пропустить»."
CANNOT_BAN_OPERATOR = "Операторов и администраторов заблокировать нельзя."

from __future__ import annotations

from typing import Dict, Optional

PAYMENT = "payment"
DELIVERY = "delivery"
TECH = "tech"
OTHER = "other"

ORDER = (PAYMENT, DELIVERY, TECH, OTHER)

CATEGORIES: Dict[str, str] = {
    PAYMENT: "Оплата",
    DELIVERY: "Доставка",
    TECH: "Техническая проблема",
    OTHER: "Другое",
}

SHORT: Dict[str, str] = {
    PAYMENT: "Оплата",
    DELIVERY: "Доставка",
    TECH: "Тех. проблема",
    OTHER: "Другое",
}

ICONS: Dict[str, str] = {
    PAYMENT: "💳",
    DELIVERY: "🚚",
    TECH: "🛠",
    OTHER: "💬",
}

ALIASES: Dict[str, str] = {
    "payment": PAYMENT,
    "pay": PAYMENT,
    "оплата": PAYMENT,
    "оплат": PAYMENT,
    "delivery": DELIVERY,
    "доставка": DELIVERY,
    "доставк": DELIVERY,
    "tech": TECH,
    "technical": TECH,
    "тех": TECH,
    "техническая": TECH,
    "техника": TECH,
    "other": OTHER,
    "другое": OTHER,
    "прочее": OTHER,
}


def label(code: str) -> str:
    return CATEGORIES.get(code, code)


def short_label(code: str) -> str:
    return SHORT.get(code, label(code))


def icon(code: str) -> str:
    return ICONS.get(code, "💬")


def is_valid(code: str) -> bool:
    return code in CATEGORIES


def parse_category(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    return ALIASES.get(text.strip().lower().replace("ё", "е"))

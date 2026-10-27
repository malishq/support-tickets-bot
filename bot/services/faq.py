from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional, Pattern, Tuple

WORD_RE = re.compile(r"[a-zа-я0-9]+")

Entry = Dict[str, Any]


def load_faq(path: str) -> List[Entry]:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    entries: List[Entry] = []
    for item in data:
        keywords = [normalize(keyword) for keyword in item.get("keywords", [])]
        entries.append(
            {
                "id": str(item["id"]),
                "question": item["question"],
                "answer": item["answer"],
                "keywords": [keyword for keyword in keywords if keyword],
            }
        )
    return entries


def normalize(text: Optional[str]) -> str:
    if not text:
        return ""
    return " ".join(WORD_RE.findall(text.lower().replace("ё", "е")))


def tokenize(text: Optional[str]) -> List[str]:
    normalized = normalize(text)
    return normalized.split() if normalized else []


@lru_cache(maxsize=512)
def keyword_pattern(keyword: str) -> Pattern[str]:
    stems = [re.escape(word) for word in normalize(keyword).split()]
    return re.compile(r"(?<!\S)" + r"\S*\s+".join(stems))


def keyword_matches(keyword: str, normalized_text: str) -> bool:
    if not keyword or not normalized_text:
        return False
    return keyword_pattern(keyword).search(normalized_text) is not None


def score_entry(text: Optional[str], entry: Entry) -> Tuple[int, int]:
    normalized = normalize(text)
    if not normalized:
        return 0, 0
    matched = [keyword for keyword in entry.get("keywords", []) if keyword_matches(keyword, normalized)]
    return len(matched), sum(len(keyword) for keyword in matched)


def match_faq(text: Optional[str], faq: List[Entry], min_score: int = 1) -> Optional[Entry]:
    best: Optional[Entry] = None
    best_score: Tuple[int, int] = (0, 0)
    for entry in faq:
        score = score_entry(text, entry)
        if score > best_score:
            best, best_score = entry, score
    if best is None or best_score[0] < min_score:
        return None
    return best


def find_faq(faq: List[Entry], entry_id: str) -> Optional[Entry]:
    for entry in faq:
        if entry["id"] == entry_id:
            return entry
    return None

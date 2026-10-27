from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

Template = Dict[str, Any]


class SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return ""


def load_templates(path: str) -> List[Template]:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return [{"id": str(item["id"]), "title": item["title"], "text": item["text"]} for item in data]


def find_template(templates: List[Template], template_id: str) -> Optional[Template]:
    for template in templates:
        if template["id"] == template_id:
            return template
    return None


def render_template(text: str, **values: Any) -> str:
    rendered = text.format_map(SafeDict({key: value for key, value in values.items() if value}))
    rendered = re.sub(r"\s*,\s*([!.?])", r"\1", rendered)
    rendered = re.sub(r"^[\s,]+", "", rendered)
    rendered = re.sub(r"\s+([,.!?])", r"\1", rendered)
    rendered = re.sub(r"[ \t]{2,}", " ", rendered).strip()
    if rendered and rendered[0].islower():
        rendered = rendered[0].upper() + rendered[1:]
    return rendered

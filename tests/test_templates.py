import os

from bot.services.templates import find_template, load_templates, render_template

TEMPLATES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "templates.json")


def test_render_with_values():
    text = "Здравствуйте, {name}! Меня зовут {operator}."
    assert render_template(text, name="Иван", operator="Мария") == "Здравствуйте, Иван! Меня зовут Мария."


def test_render_without_name_cleans_punctuation():
    assert render_template("Здравствуйте, {name}! Уже смотрю.", name="") == "Здравствуйте! Уже смотрю."
    assert render_template("{name}, уточните номер заказа.") == "Уточните номер заказа."


def test_load_and_find():
    templates = load_templates(TEMPLATES_PATH)
    assert templates
    assert find_template(templates, templates[0]["id"]) == templates[0]
    assert find_template(templates, "nope") is None
    for template in templates:
        assert render_template(template["text"], name="Иван", operator="Мария")

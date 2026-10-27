import os

import pytest

from bot.services.faq import find_faq, load_faq, match_faq, normalize, score_entry, tokenize

FAQ_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "faq.json")


@pytest.fixture
def faq():
    return load_faq(FAQ_PATH)


def test_normalize_lowercases_and_replaces_yo():
    assert normalize("Ещё, не пришёл КОД!") == "еще не пришел код"
    assert normalize("") == ""
    assert normalize(None) == ""


def test_tokenize():
    assert tokenize("Где мой заказ?") == ["где", "мой", "заказ"]


def test_keyword_is_a_word_stem():
    entry = {"id": "x", "keywords": ["оплат"]}
    assert score_entry("Как оплатить заказ картой?", entry) == (1, 5)
    assert score_entry("переоплата", entry) == (0, 0)


def test_phrase_keyword_allows_inflection():
    entry = {"id": "x", "keywords": ["способ оплат"]}
    assert score_entry("Какие способы оплаты есть?", entry)[0] == 1
    assert score_entry("способ есть, оплаты нет", entry)[0] == 0


def test_best_match_wins(faq):
    assert match_faq("Оплата не прошла, деньги списались дважды", faq)["id"] == "payment_failed"
    assert match_faq("Какие способы оплаты есть?", faq)["id"] == "payment_methods"
    assert match_faq("Где мой заказ?", faq)["id"] == "tracking"
    assert match_faq("Хочу вернуть деньги за заказ", faq)["id"] == "refund"
    assert match_faq("Не приходит смс с кодом", faq)["id"] == "login_code"


def test_no_match_returns_none(faq):
    assert match_faq("Привет, как дела", faq) is None
    assert match_faq("", faq) is None
    assert match_faq(None, faq) is None
    assert match_faq("оплата", faq, min_score=2) is None


def test_every_question_matches_itself(faq):
    assert len(faq) >= 5
    for entry in faq:
        matched = match_faq(entry["question"], faq)
        assert matched is not None, entry["id"]
        assert matched["id"] == entry["id"]


def test_find_faq(faq):
    assert find_faq(faq, "refund")["question"]
    assert find_faq(faq, "missing") is None

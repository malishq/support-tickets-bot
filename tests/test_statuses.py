import pytest

from bot.services import statuses as s


def test_full_lifecycle():
    status = s.OPEN
    status = s.on_take(status)
    assert status == s.IN_PROGRESS
    status = s.on_operator_reply(status)
    assert status == s.WAITING_CLIENT
    status = s.on_client_message(status)
    assert status == s.IN_PROGRESS
    status = s.on_close(status)
    assert status == s.CLOSED


@pytest.mark.parametrize("status", [s.IN_PROGRESS, s.WAITING_CLIENT, s.CLOSED])
def test_take_only_from_open(status):
    with pytest.raises(s.InvalidTransition):
        s.on_take(status)


def test_closed_ticket_rejects_messages_and_replies():
    with pytest.raises(s.InvalidTransition):
        s.on_client_message(s.CLOSED)
    with pytest.raises(s.InvalidTransition):
        s.on_operator_reply(s.CLOSED)
    with pytest.raises(s.InvalidTransition):
        s.on_close(s.CLOSED)


def test_client_message_keeps_status_unless_waiting():
    assert s.on_client_message(s.OPEN) == s.OPEN
    assert s.on_client_message(s.IN_PROGRESS) == s.IN_PROGRESS
    assert s.on_client_message(s.WAITING_CLIENT) == s.IN_PROGRESS


def test_operator_reply_moves_to_waiting_client():
    assert s.on_operator_reply(s.OPEN) == s.WAITING_CLIENT
    assert s.on_operator_reply(s.IN_PROGRESS) == s.WAITING_CLIENT
    assert s.on_operator_reply(s.WAITING_CLIENT) == s.WAITING_CLIENT


def test_close_from_any_active_status():
    for status in s.ACTIVE:
        assert s.on_close(status) == s.CLOSED


def test_reopen():
    assert s.on_reopen(s.CLOSED, has_operator=True) == s.IN_PROGRESS
    assert s.on_reopen(s.CLOSED, has_operator=False) == s.OPEN
    with pytest.raises(s.InvalidTransition):
        s.on_reopen(s.OPEN, has_operator=False)


def test_reopen_window():
    closed_at = 1_000_000
    assert s.can_reopen(closed_at, closed_at + 24 * 3600, 24)
    assert not s.can_reopen(closed_at, closed_at + 24 * 3600 + 1, 24)
    assert s.can_reopen(closed_at, closed_at + 3600, 1)
    assert not s.can_reopen(None, closed_at, 24)
    assert not s.can_reopen(closed_at, closed_at - 10, 24)


@pytest.mark.parametrize(
    "current,target,allowed",
    [
        (s.OPEN, s.IN_PROGRESS, True),
        (s.OPEN, s.CLOSED, True),
        (s.IN_PROGRESS, s.OPEN, False),
        (s.WAITING_CLIENT, s.IN_PROGRESS, True),
        (s.CLOSED, s.WAITING_CLIENT, False),
        (s.CLOSED, s.OPEN, True),
        ("unknown", s.OPEN, False),
    ],
)
def test_transition_matrix(current, target, allowed):
    assert s.can_transition(current, target) is allowed
    if allowed:
        assert s.transition(current, target) == target
    else:
        with pytest.raises(s.InvalidTransition):
            s.transition(current, target)


def test_labels_and_parse():
    assert s.label(s.WAITING_CLIENT) == "ждём ответа клиента"
    assert s.client_label(s.WAITING_CLIENT) == "ждём вашего ответа"
    assert s.parse_status("Открытые") == s.OPEN
    assert s.parse_status("closed") == s.CLOSED
    assert s.parse_status("ждём") == s.WAITING_CLIENT
    assert s.parse_status("что-то") is None
    assert s.parse_status(None) is None

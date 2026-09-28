import itertools
from unittest.mock import patch

import pytest

from core.connection import ConnectionService
from core.states import ConnectionState as CS

ALL_STATES = list(CS)
ALL_PAIRS = list(itertools.product(ALL_STATES, ALL_STATES))
NON_CONNECTED_STATES = [s for s in ALL_STATES if s is not CS.CONNECTED]


@pytest.fixture
def service(qtbot):
    return ConnectionService()


# --- _transition() / _TRANSITIONS table ---


@pytest.mark.parametrize(
    "from_state,to_state",
    ALL_PAIRS,
    ids=[f"{a.name}->{b.name}" for a, b in ALL_PAIRS],
)
def test_transition_full_grid(service, qtbot, from_state, to_state):
    service._state = from_state
    legal = to_state in ConnectionService._TRANSITIONS[from_state]

    if legal:
        with qtbot.waitSignal(service.state_changed, timeout=1000) as blocker:
            result = service._transition(to_state)
        assert blocker.args == [to_state]
    else:
        with qtbot.assertNotEmitted(service.state_changed):
            result = service._transition(to_state)

    assert result is legal
    assert service._state == (to_state if legal else from_state)


# --- start() / stop() ---


def test_start_from_disconnected_calls_buildup(service):
    service._state = CS.DISCONNECTED
    with patch.object(service, "_buildup") as buildup:
        service.start()
    assert service._state == CS.CONNECTING
    buildup.assert_called_once()


def test_start_from_connected_is_noop(service):
    service._state = CS.CONNECTED
    with patch.object(service, "_buildup") as buildup:
        service.start()
    assert service._state == CS.CONNECTED
    buildup.assert_not_called()


def test_stop_from_connecting_emits_close(service, qtbot):
    service._state = CS.CONNECTING
    with qtbot.waitSignal(service.wrkr_close_connection, timeout=1000):
        service.stop()
    assert service._state == CS.STOPPING


def test_stop_from_connected_emits_close(service, qtbot):
    service._state = CS.CONNECTED
    with qtbot.waitSignal(service.wrkr_close_connection, timeout=1000):
        service.stop()
    assert service._state == CS.STOPPING


def test_stop_from_disconnected_is_silent_noop(service, qtbot):
    service._state = CS.DISCONNECTED
    with qtbot.assertNotEmitted(service.wrkr_close_connection):
        service.stop()
    assert service._state == CS.DISCONNECTED


# --- _on_connection_result() ---


def test_on_connection_result_success_transitions_to_connected(service):
    service._state = CS.CONNECTING
    service._on_connection_result(True)
    assert service._state == CS.CONNECTED


def test_on_connection_result_success_but_illegal_closes_port(service, qtbot):
    service._state = CS.STOPPING
    with qtbot.waitSignal(service.wrkr_close_connection, timeout=1000):
        service._on_connection_result(True)
    assert service._state == CS.STOPPING


def test_on_connection_result_failure_transitions_to_failed_and_tears_down(service):
    service._state = CS.CONNECTING
    with patch.object(service, "_teardown") as teardown:
        service._on_connection_result(False)
    assert service._state == CS.FAILED
    teardown.assert_called_once()


# --- _on_connection_closed() ---


def test_on_connection_closed_prefers_disconnected(service):
    service._state = CS.CONNECTED
    with patch.object(service, "_teardown") as teardown:
        service._on_connection_closed()
    assert service._state == CS.DISCONNECTED
    teardown.assert_called_once()


def test_on_connection_closed_falls_back_to_failed(service):
    service._state = CS.CONNECTING
    with patch.object(service, "_teardown") as teardown:
        service._on_connection_closed()
    assert service._state == CS.FAILED
    teardown.assert_called_once()


def test_on_connection_closed_neither_legal_still_tears_down(service):
    service._state = CS.DISCONNECTED
    with patch.object(service, "_teardown") as teardown:
        service._on_connection_closed()
    assert service._state == CS.DISCONNECTED
    teardown.assert_called_once()


# --- send_line() / send_realtime() guards ---


def test_send_line_emits_when_connected(service, qtbot):
    service._state = CS.CONNECTED
    with qtbot.waitSignal(service.wrkr_send_line, timeout=1000) as blocker:
        service.send_line("G0 X1")
    assert blocker.args == ["G0 X1"]


@pytest.mark.parametrize("state", NON_CONNECTED_STATES, ids=lambda s: s.name)
def test_send_line_noop_when_not_connected(service, qtbot, state):
    service._state = state
    with qtbot.assertNotEmitted(service.wrkr_send_line):
        service.send_line("G0 X1")


def test_send_realtime_emits_when_connected(service, qtbot):
    service._state = CS.CONNECTED
    with qtbot.waitSignal(service.wrkr_send_realtime, timeout=1000) as blocker:
        service.send_realtime(b"?")
    assert blocker.args == [b"?"]


@pytest.mark.parametrize("state", NON_CONNECTED_STATES, ids=lambda s: s.name)
def test_send_realtime_noop_when_not_connected(service, qtbot, state):
    service._state = state
    with qtbot.assertNotEmitted(service.wrkr_send_realtime):
        service.send_realtime(b"?")

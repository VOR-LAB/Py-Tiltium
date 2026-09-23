import itertools
from unittest.mock import patch

import pytest

from controller.queue_controller import CommandKind, QueueCommand, QueueController
from core.states import ConnectionState as CState
from core.states import QueueState as QS

ALL_STATES = list(QS)
ALL_PAIRS = list(itertools.product(ALL_STATES, ALL_STATES))


@pytest.fixture
def controller(qtbot):
    return QueueController()


def test_init_starts_finished(controller):
    assert controller._state == QS.FINISHED


# --- _transition() / _TRANSITIONS table ---


@pytest.mark.parametrize(
    "from_state,to_state",
    ALL_PAIRS,
    ids=[f"{a.name}->{b.name}" for a, b in ALL_PAIRS],
)
def test_transition_full_grid(controller, qtbot, from_state, to_state):
    controller._state = from_state
    legal = to_state in QueueController._TRANSITIONS[from_state]
    self_transition = legal and to_state == from_state

    if legal and not self_transition:
        with qtbot.waitSignal(controller.queue_state_changed, timeout=1000) as blocker:
            result = controller._transition(to_state)
        assert blocker.args == [to_state]
    else:
        with qtbot.assertNotEmitted(controller.queue_state_changed):
            result = controller._transition(to_state)

    assert result is legal
    assert controller._state == (to_state if legal else from_state)


# --- req_jog_line() / req_pause(): only queue while IDLE ---


def test_req_jog_line_appends_when_idle(controller, qtbot):
    controller._state = QS.IDLE
    with qtbot.waitSignal(controller.current_queue, timeout=1000):
        controller.req_jog_line("A", 10.0, 2.0)
    assert len(controller._queue) == 1
    cmd = controller._queue[0]
    assert cmd.kind == CommandKind.GCODE
    assert cmd.angle == 10.0
    assert cmd.angle_rate == 2.0


def test_req_jog_line_noop_when_not_idle(controller, qtbot):
    controller._state = QS.RUNNING
    with qtbot.assertNotEmitted(controller.current_queue):
        controller.req_jog_line("A", 10.0, 50.0)
    assert controller._queue == []


def test_req_pause_appends_when_idle(controller):
    controller._state = QS.IDLE
    controller.req_pause(2.5)
    assert controller._queue == [QueueCommand(CommandKind.PAUSE, 2.5)]


def test_req_pause_noop_when_not_idle(controller):
    controller._state = QS.RUNNING
    controller.req_pause(2.5)
    assert controller._queue == []


# --- clear() ---


def test_clear_from_finished_resets_to_idle(controller):
    controller._state = QS.FINISHED
    controller._queue = [QueueCommand(CommandKind.PAUSE, 1.0)]
    controller.clear()
    assert controller._state == QS.IDLE
    assert controller._queue == []


def test_clear_from_running_is_noop(controller):
    controller._state = QS.RUNNING
    controller._queue = [QueueCommand(CommandKind.PAUSE, 1.0)]
    controller.clear()
    assert controller._state == QS.RUNNING
    assert len(controller._queue) == 1


# --- start() ---


def test_start_not_connected_is_noop(controller):
    controller._conn_state = CState.DISCONNECTED
    controller._state = QS.IDLE
    with patch.object(controller, "_advance") as advance:
        controller.start()
    assert controller._state == QS.IDLE
    advance.assert_not_called()


def test_start_from_idle_when_connected_transitions_and_advances(controller):
    controller._conn_state = CState.CONNECTED
    controller._state = QS.IDLE
    with patch.object(controller, "_advance") as advance:
        controller.start()
    assert controller._state == QS.RUNNING
    advance.assert_called_once()


@pytest.mark.parametrize("state", [QS.RUNNING, QS.FINISHED, QS.CANCELLED, QS.UNKNOWN_ERROR])
def test_start_from_non_idle_when_connected_is_noop(controller, state):
    controller._conn_state = CState.CONNECTED
    controller._state = state
    with patch.object(controller, "_advance") as advance:
        controller.start()
    assert controller._state == state
    advance.assert_not_called()


# --- _advance() ---


def test_advance_queue_empty_transitions_to_finished(controller, qtbot):
    controller._state = QS.RUNNING
    controller._queue = []
    controller._current_command = QueueCommand(CommandKind.PAUSE, 1.0)
    with qtbot.waitSignal(controller.current_command_changed, timeout=1000) as blocker:
        controller._advance()
    assert blocker.args == [None]
    assert controller._state == QS.FINISHED
    assert controller._current_command is None


def test_advance_pops_gcode_command_sends_line_and_starts_timer(controller):
    controller._state = QS.RUNNING
    controller._queue = [
        QueueCommand(CommandKind.GCODE, ("$J=G91 A1.000 F10.000", 0.5), angle=1.0, angle_rate=10.0)
    ]
    with patch.object(controller._connection, "send_line") as send_line:
        controller._advance()
    send_line.assert_called_once_with("$J=G91 A1.000 F10.000")
    assert controller._queue == []
    assert controller._queue_timer.isActive()


def test_advance_pops_pause_command_starts_timer_without_sending(controller):
    controller._state = QS.RUNNING
    controller._queue = [QueueCommand(CommandKind.PAUSE, 2.0)]
    with patch.object(controller._connection, "send_line") as send_line:
        controller._advance()
    send_line.assert_not_called()
    assert controller._queue_timer.isActive()


# --- _insure_idle() ---


def test_insure_idle_advances_when_idle_and_timer_inactive(controller):
    controller._state = QS.RUNNING
    assert not controller._queue_timer.isActive()
    with patch.object(controller, "_advance") as advance:
        controller._insure_idle({"state": "Idle"})
    advance.assert_called_once()


def test_insure_idle_ignored_when_timer_active(controller):
    controller._state = QS.RUNNING
    controller._queue_timer.start(5000)
    with patch.object(controller, "_advance") as advance:
        controller._insure_idle({"state": "Idle"})
    advance.assert_not_called()
    controller._queue_timer.stop()


def test_insure_idle_ignored_when_not_running(controller):
    controller._state = QS.IDLE
    with patch.object(controller, "_advance") as advance:
        controller._insure_idle({"state": "Idle"})
    advance.assert_not_called()


def test_insure_idle_jog_state_cancels_instead_of_advancing(controller):
    controller._state = QS.RUNNING
    with (
        patch.object(controller, "_advance") as advance,
        patch.object(controller, "req_jog_cancel") as cancel,
    ):
        controller._insure_idle({"state": "Jog"})
    advance.assert_not_called()
    cancel.assert_called_once()


# --- _on_conn_state_changed() ---


def test_on_conn_state_changed_cancels_when_running_and_disconnected(controller):
    controller._state = QS.RUNNING
    with patch.object(controller, "req_jog_cancel") as cancel:
        controller._on_conn_state_changed(CState.DISCONNECTED)
    cancel.assert_called_once()


def test_on_conn_state_changed_noop_when_not_running(controller):
    controller._state = QS.IDLE
    with patch.object(controller, "req_jog_cancel") as cancel:
        controller._on_conn_state_changed(CState.DISCONNECTED)
    cancel.assert_not_called()


# --- req_jog_cancel() ---


def test_req_jog_cancel_from_running_transitions_and_clears(controller, qtbot):
    controller._state = QS.RUNNING
    controller._queue = [QueueCommand(CommandKind.PAUSE, 1.0)]
    controller._current_command = QueueCommand(CommandKind.PAUSE, 1.0)
    with patch.object(controller._connection, "send_realtime") as send_realtime:
        with qtbot.waitSignal(controller.current_command_changed, timeout=1000) as blocker:
            controller.req_jog_cancel()
    assert blocker.args == [None]
    assert controller._state == QS.CANCELLED
    assert controller._queue == []
    assert controller._current_command is None
    send_realtime.assert_called_once()


@pytest.mark.parametrize("state", [QS.IDLE, QS.FINISHED, QS.CANCELLED, QS.UNKNOWN_ERROR])
def test_req_jog_cancel_from_non_running_is_noop(controller, state):
    controller._state = state
    with patch.object(controller._connection, "send_realtime") as send_realtime:
        controller.req_jog_cancel()
    assert controller._state == state
    send_realtime.assert_not_called()

import itertools
import json
from unittest.mock import patch

import pytest

from controller import queue_controller
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


# --- req_save_preset() / req_load_preset() / list_presets() ---
#
# Spec: presets are the current `_queue` serialized as JSON to
# `PRESETS_DIR / f"{name}.json"`. `PRESETS_DIR` is a module-level `pathlib.Path`
# constant in `controller.queue_controller` (tests monkeypatch it to a tmp_path,
# so the implementation must read that constant rather than recomputing the path
# inline). Both saving and loading only run while IDLE (same rule as
# req_jog_line/req_pause) - the queue shrinks as it runs, so saving mid-run would
# capture leftovers instead of the full recipe. Loading replaces `_queue`
# wholesale and emits `current_queue` on success. A missing preset file is
# allowed to raise FileNotFoundError - no special-casing needed.
#
# On-disk shape: a JSON list of objects, one per QueueCommand, in queue order:
#   {"kind": "GCODE" | "PAUSE", "payload": [str, float] | float,
#    "angle": float | None, "angle_rate": float | None}
#
# Name safety: `name` comes from a free-text "save" box in the UI (the "load"
# side will be a dropdown built from list_presets(), so it never sees a raw
# typed name) but both req_save_preset and req_load_preset must reject a name
# that isn't safe to use as a bare filename - anything containing a path
# separator, `..`, or another character a filesystem/shell would choke on
# (`:`, `$`, etc.) - by raising ValueError, before touching the filesystem.
#
# list_presets() returns the sorted stems of every "*.json" file directly
# under PRESETS_DIR (empty list if the directory doesn't exist yet), for the
# UI to populate that load dropdown.

UNSAFE_PRESET_NAMES = ["foo:bar", "foo$bar", "foo/bar", "foo\\bar", ".."]


@pytest.fixture
def preset_dir(monkeypatch, tmp_path):
    """Point controller.queue_controller.PRESETS_DIR at a throwaway directory
    so preset tests never touch the real project .presets/ folder."""
    monkeypatch.setattr(queue_controller, "PRESETS_DIR", tmp_path, raising=False)
    return tmp_path


def test_req_save_preset_writes_expected_json(controller, preset_dir):
    controller._state = QS.IDLE
    controller._queue = [
        QueueCommand(CommandKind.GCODE, ("$J=G91 A1.000 F10.000", 0.5), angle=1.0, angle_rate=10.0),
        QueueCommand(CommandKind.PAUSE, 2.0),
    ]

    controller.req_save_preset("my_preset")

    data = json.loads((preset_dir / "my_preset.json").read_text())
    assert data == [
        {
            "kind": "GCODE",
            "payload": ["$J=G91 A1.000 F10.000", 0.5],
            "angle": 1.0,
            "angle_rate": 10.0,
        },
        {"kind": "PAUSE", "payload": 2.0, "angle": None, "angle_rate": None},
    ]


def test_req_save_preset_creates_presets_dir_if_missing(monkeypatch, tmp_path, controller):
    monkeypatch.setattr(queue_controller, "PRESETS_DIR", tmp_path / ".presets", raising=False)
    controller._state = QS.IDLE
    controller._queue = [QueueCommand(CommandKind.PAUSE, 1.0)]

    controller.req_save_preset("preset")

    assert (tmp_path / ".presets" / "preset.json").exists()


def test_req_save_preset_overwrites_existing_file(controller, preset_dir):
    controller._state = QS.IDLE
    controller._queue = [QueueCommand(CommandKind.PAUSE, 1.0)]
    controller.req_save_preset("preset")

    controller._queue = [QueueCommand(CommandKind.PAUSE, 9.0)]
    controller.req_save_preset("preset")

    data = json.loads((preset_dir / "preset.json").read_text())
    assert data == [{"kind": "PAUSE", "payload": 9.0, "angle": None, "angle_rate": None}]


@pytest.mark.parametrize("state", [QS.RUNNING, QS.FINISHED, QS.CANCELLED, QS.UNKNOWN_ERROR])
def test_req_save_preset_noop_when_not_idle(controller, preset_dir, state):
    controller._state = state
    controller._queue = [QueueCommand(CommandKind.PAUSE, 1.0)]

    controller.req_save_preset("preset")

    assert not (preset_dir / "preset.json").exists()


def test_req_load_preset_replaces_queue_when_idle(controller, qtbot, preset_dir):
    controller._state = QS.IDLE
    controller._queue = [QueueCommand(CommandKind.PAUSE, 1.0)]
    controller.req_save_preset("preset")
    controller._queue = []

    with qtbot.waitSignal(controller.current_queue, timeout=1000):
        controller.req_load_preset("preset")

    assert controller._queue == [QueueCommand(CommandKind.PAUSE, 1.0)]


def test_req_load_preset_restores_gcode_tuple_payload(controller, preset_dir):
    controller._state = QS.IDLE
    controller._queue = [
        QueueCommand(CommandKind.GCODE, ("$J=G91 A1.000 F10.000", 0.5), angle=1.0, angle_rate=10.0)
    ]
    controller.req_save_preset("preset")
    controller._queue = []

    controller.req_load_preset("preset")

    cmd = controller._queue[0]
    assert cmd == QueueCommand(
        CommandKind.GCODE, ("$J=G91 A1.000 F10.000", 0.5), angle=1.0, angle_rate=10.0
    )
    assert isinstance(cmd.payload, tuple)


def test_req_load_preset_noop_when_not_idle(controller, preset_dir):
    controller._state = QS.IDLE
    controller._queue = [QueueCommand(CommandKind.PAUSE, 1.0)]
    controller.req_save_preset("preset")

    controller._state = QS.RUNNING
    controller._queue = [QueueCommand(CommandKind.PAUSE, 9.0)]
    controller.req_load_preset("preset")

    assert controller._queue == [QueueCommand(CommandKind.PAUSE, 9.0)]


def test_req_load_preset_missing_file_raises(controller, preset_dir):
    controller._state = QS.IDLE
    with pytest.raises(FileNotFoundError):
        controller.req_load_preset("does_not_exist")


@pytest.mark.parametrize("bad_name", UNSAFE_PRESET_NAMES)
def test_req_save_preset_rejects_unsafe_name(controller, preset_dir, bad_name):
    controller._queue = [QueueCommand(CommandKind.PAUSE, 1.0)]
    with pytest.raises(ValueError):
        controller.req_save_preset(bad_name)
    assert list(preset_dir.iterdir()) == []


@pytest.mark.parametrize("bad_name", UNSAFE_PRESET_NAMES)
def test_req_load_preset_rejects_unsafe_name(controller, preset_dir, bad_name):
    controller._state = QS.IDLE
    controller._queue = [QueueCommand(CommandKind.PAUSE, 9.0)]
    with pytest.raises(ValueError):
        controller.req_load_preset(bad_name)
    assert controller._queue == [QueueCommand(CommandKind.PAUSE, 9.0)]


def test_req_save_preset_allows_spaces_hyphen_and_underscore(controller, preset_dir):
    controller._state = QS.IDLE
    controller._queue = [QueueCommand(CommandKind.PAUSE, 1.0)]
    controller.req_save_preset("my preset_1-final")
    assert (preset_dir / "my preset_1-final.json").exists()


# --- list_presets() ---


def test_list_presets_empty_when_dir_missing(controller, monkeypatch, tmp_path):
    monkeypatch.setattr(queue_controller, "PRESETS_DIR", tmp_path / ".presets", raising=False)
    assert controller.list_presets() == []


def test_list_presets_returns_saved_names_sorted(controller, preset_dir):
    (preset_dir / "b_preset.json").write_text("[]")
    (preset_dir / "a_preset.json").write_text("[]")
    assert controller.list_presets() == ["a_preset", "b_preset"]


def test_list_presets_ignores_non_json_files(controller, preset_dir):
    (preset_dir / "preset.json").write_text("[]")
    (preset_dir / "notes.txt").write_text("hello")
    assert controller.list_presets() == ["preset"]

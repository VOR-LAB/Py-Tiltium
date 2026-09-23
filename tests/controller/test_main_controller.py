from unittest.mock import patch

import pytest

from controller.main_controller import UIController
from core.protocol import JOG_CANCEL, STATUS_QUERY, jog_command
from core.states import ConnectionState as CState
from params import DEG_PER_DIST


@pytest.fixture
def controller(qtbot):
    return UIController()


def test_req_jog_line_converts_units_and_sends(controller):
    with patch.object(controller._connection, "send_line") as send_line:
        controller.req_jog_line("A", 5.81, 2.0)
    expected_dist = 5.81 / DEG_PER_DIST
    expected_rate = 2.0 / DEG_PER_DIST * 60.0
    send_line.assert_called_once_with(jog_command("A", expected_dist, expected_rate))


def test_req_jog_cancel_sends_jog_cancel_byte(controller):
    with patch.object(controller._connection, "send_realtime") as send_realtime:
        controller.req_jog_cancel()
    send_realtime.assert_called_once_with(JOG_CANCEL)


def test_req_status_sends_status_query_byte(controller):
    with patch.object(controller._connection, "send_realtime") as send_realtime:
        controller.req_status()
    send_realtime.assert_called_once_with(STATUS_QUERY)


def test_toggle_connect_disconnect_connects_when_disconnected(controller):
    controller._conn_state = CState.DISCONNECTED
    with (
        patch.object(controller, "req_connect") as req_connect,
        patch.object(controller, "req_disconnect") as req_disconnect,
    ):
        controller.toggle_connect_disconnect()
    req_connect.assert_called_once()
    req_disconnect.assert_not_called()


def test_toggle_connect_disconnect_disconnects_when_connected(controller):
    controller._conn_state = CState.CONNECTED
    with (
        patch.object(controller, "req_connect") as req_connect,
        patch.object(controller, "req_disconnect") as req_disconnect,
    ):
        controller.toggle_connect_disconnect()
    req_disconnect.assert_called_once()
    req_connect.assert_not_called()


def test_on_conn_state_change_updates_state_and_emits(controller, qtbot):
    with qtbot.waitSignal(controller.conn_state_changed, timeout=1000) as blocker:
        controller._on_conn_state_change(CState.CONNECTED)
    assert blocker.args == [CState.CONNECTED]
    assert controller._conn_state == CState.CONNECTED


def test_info_received_updates_activity_log_and_emits(controller, qtbot):
    with qtbot.waitSignal(controller.log_updated, timeout=1000) as blocker:
        controller._connection.ok_received.emit()
    assert blocker.args[0].endswith("] ok")

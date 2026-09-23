from unittest.mock import MagicMock

import pytest

from core import status
from core.connection import Connection


@pytest.fixture
def connection(qtbot):
    return Connection()


# --- send_line() / send_realtime() ---


def test_send_line_writes_utf8_with_newline(connection):
    connection._port = MagicMock()
    connection.send_line("G0 X1 F100")
    connection._port.write.assert_called_once_with(b"G0 X1 F100\n")


def test_send_line_noop_when_port_none(connection):
    connection.send_line("G0 X1 F100")  # must not raise


def test_send_realtime_writes_raw_bytes_no_newline(connection):
    connection._port = MagicMock()
    connection.send_realtime(b"?")
    connection._port.write.assert_called_once_with(b"?")


def test_send_realtime_noop_when_port_none(connection):
    connection.send_realtime(b"?")  # must not raise


# --- _handle_line() dispatch ---


def test_handle_line_status_dispatches_status_received(connection, qtbot):
    line = "<Idle|MPos:0.0,0.0>"
    with qtbot.waitSignal(connection.status_received, timeout=1000) as blocker:
        connection._handle_line(line)
    assert blocker.args == [status.parse_status(line)]


def test_handle_line_ok_dispatches_ok_received(connection, qtbot):
    with qtbot.waitSignal(connection.ok_received, timeout=1000):
        connection._handle_line("ok")


def test_handle_line_error_dispatches_error_received_with_full_line(connection, qtbot):
    with qtbot.waitSignal(connection.error_received, timeout=1000) as blocker:
        connection._handle_line("error:9")
    assert blocker.args == ["error:9"]


def test_handle_line_arbitrary_dispatches_line_received(connection, qtbot):
    with qtbot.waitSignal(connection.line_received, timeout=1000) as blocker:
        connection._handle_line("Grbl 1.1f ['$' for help]")
    assert blocker.args == ["Grbl 1.1f ['$' for help]"]


@pytest.mark.parametrize("line", ["", "   "])
def test_handle_line_empty_dispatches_nothing(connection, qtbot, line):
    with (
        qtbot.assertNotEmitted(connection.status_received),
        qtbot.assertNotEmitted(connection.ok_received),
        qtbot.assertNotEmitted(connection.error_received),
        qtbot.assertNotEmitted(connection.line_received),
    ):
        connection._handle_line(line)


def test_handle_line_strips_whitespace(connection, qtbot):
    with qtbot.waitSignal(connection.ok_received, timeout=1000):
        connection._handle_line("  ok  \r")


# --- _on_ready_read() buffering ---


def _fake_port(data: bytes) -> MagicMock:
    port = MagicMock()
    port.readAll.return_value.data.return_value = data
    return port


def test_on_ready_read_dispatches_single_complete_line(connection, qtbot):
    connection._port = _fake_port(b"ok\n")
    with qtbot.waitSignal(connection.ok_received, timeout=1000):
        connection._on_ready_read()
    assert connection._buffer == ""


def test_on_ready_read_buffers_partial_line(connection, qtbot):
    connection._port = _fake_port(b"ok")
    with qtbot.assertNotEmitted(connection.ok_received):
        connection._on_ready_read()
    assert connection._buffer == "ok"


def test_on_ready_read_dispatches_multiple_lines_in_one_read(connection):
    connection._port = _fake_port(b"ok\nok\n")
    received = MagicMock()
    connection.ok_received.connect(received)
    connection._on_ready_read()
    assert received.call_count == 2
    assert connection._buffer == ""


def test_on_ready_read_completes_buffered_partial_line_on_next_read(connection, qtbot):
    connection._port = _fake_port(b"o")
    connection._on_ready_read()
    assert connection._buffer == "o"

    connection._port = _fake_port(b"k\n")
    with qtbot.waitSignal(connection.ok_received, timeout=1000):
        connection._on_ready_read()
    assert connection._buffer == ""

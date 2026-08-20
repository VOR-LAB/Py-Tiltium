import logging
from typing import ClassVar

from PySide6.QtCore import QEventLoop, QObject, QThread, Signal, Slot
from PySide6.QtSerialPort import QSerialPort

from core import status
from core.states import ConnectionState as CS
from hardware import device

logger = logging.getLogger(__name__)


# Connection handles QSerialPort object for sending and receiving
# information over the serial connection.
class Connection(QObject):
    result = Signal(bool)
    closed = Signal()

    status_received = Signal(dict)
    ok_received = Signal()
    error_received = Signal(str)
    line_received = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._port: QSerialPort | None = None
        self._buffer = ""

    def _on_ready_read(self):
        if self._port is not None:
            self._buffer += bytes(self._port.readAll().data()).decode("utf-8", errors="ignore")

        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._handle_line(line)

    def _on_error(self, err):
        match err:
            case QSerialPort.SerialPortError.NoError:
                pass
            case _:
                logger.error("serial port error: %s", err)
                self.close()

    def _handle_line(self, line: str):
        line = line.strip()
        if not line:
            return
        if line.startswith("<"):
            self.status_received.emit(status.parse_status(line))
        elif line == "ok":
            self.ok_received.emit()
        elif line.startswith("error:"):
            self.error_received.emit(line)
        else:
            self.line_received.emit(line)

    @Slot(str)
    def send_line(self, text: str):
        if self._port is not None:
            self._port.write((text + "\n").encode("utf-8"))

    @Slot(bytes)
    def send_realtime(self, byte: bytes):
        if self._port is not None:
            self._port.write(byte)

    @Slot()
    def connect_to_device(self):
        port = device.connect()
        if port is None:
            self.result.emit(False)
            return
        self._port = port
        self._port.readyRead.connect(self._on_ready_read)
        self._port.errorOccurred.connect(self._on_error)
        self.result.emit(True)

    @Slot()
    def close(self):
        if self._port is not None:
            self._port.close()

        self._port = None
        self._buffer = ""
        self.closed.emit()


class ConnectionService(QObject):
    """Owns connection state and the worker thread's lifecycle.

    ConnectionService is the only object the rest of the app should talk to. It
    never touches the serial port itself -- Connection (running on
                                                        _connection_thread)
    does that. ConnectionService's job is to:
      1. hold the single source of truth for ConnectionState (self._state)
      2. enforce which state transitions are legal (_TRANSITIONS)
      3. create/destroy the worker thread + Connection object in step with
      those transitions (_buildup / _teardown)

    All state changes MUST go through _transition() -- never assign self._state
    directly anywhere else in this class.
    """

    _TRANSITIONS: ClassVar[dict[CS, set[CS]]] = {
        CS.DISCONNECTED: {CS.CONNECTING},
        CS.CONNECTING: {CS.CONNECTED, CS.FAILED, CS.STOPPING},
        CS.CONNECTED: {CS.STOPPING, CS.DISCONNECTED},
        CS.FAILED: {CS.CONNECTING},
        CS.STOPPING: {CS.DISCONNECTED, CS.FAILED},
    }

    state_changed = Signal(CS)
    """Emitted every time _transition() succeeds. Parent/UI should connect to
    this to react to state changes -- it's the only outward-facing notification
    this class makes about its own state."""

    wrkr_close_connection = Signal()
    """Emitted to ask the worker (Connection, on _connection_thread) to close
    its port. It does NOT mean the port is closed yet. The actual confirmation
    comes back later via Connection.closed, handled in
    _on_connection_closed."""

    wrkr_send_line = Signal(str)
    wrkr_send_realtime = Signal(bytes)
    """Emitted to ask the worker (Connection) to send a line/realtime-byte
    through the usb port."""

    def __init__(self, parent=None):
        """Starts in DISCONNECTED with no worker thread or connection yet."""
        super().__init__(parent)
        self._connection_thread: QThread | None = None
        self._connection: Connection | None = None
        self._state = CS.DISCONNECTED

    def _transition(self, new_state: CS) -> bool:
        """Attempt to move to new_state.

        Returns:
            True if the transition was applied, False if it was illegal.
        """
        if new_state not in self._TRANSITIONS[self._state]:
            return False
        self._state = new_state
        self.state_changed.emit(new_state)
        logger.info("`ConnectionService`: State changed to %s", self._state)
        return True

    def _teardown(self):
        """Releases the worker thread and Connection object."""
        if self._connection_thread is not None:
            self._connection_thread.quit()
            self._connection_thread.wait()
        if self._connection is not None:
            self._connection.deleteLater()

        self._connection_thread = None
        self._connection = None

    def _buildup(self):
        """Creates the worker thread + Connection and wires up all signals."""
        self._connection_thread = QThread()
        self._connection = Connection()
        self._connection.moveToThread(self._connection_thread)

        self._connection_thread.started.connect(self._connection.connect_to_device)

        # Worker signal towards self which trigger a function
        self._connection.result.connect(self._on_connection_result)
        self._connection.closed.connect(self._on_connection_closed)
        self._connection.status_received.connect(self._on_connection_status)
        self._connection.ok_received.connect(self._on_connection_ok)
        self._connection.error_received.connect(self._on_connection_error)
        self._connection.line_received.connect(self._on_connection_line)

        # Self signals towards worker which trigger a function
        self.wrkr_close_connection.connect(self._connection.close)
        self.wrkr_send_line.connect(self._connection.send_line)
        self.wrkr_send_realtime.connect(self._connection.send_realtime)

        self._connection_thread.finished.connect(self._connection_thread.deleteLater)

        self._connection_thread.start()

    @Slot(bool)
    def _on_connection_result(self, success: bool):
        """Handles Connection.result -- the outcome of connect_to_device().

        Runs on whichever thread emits the signal originally, but since this is
        a queued cross-thread connection, this method body itself executes back
        on ConnectionService's own thread.
        """
        if success:
            if not self._transition(CS.CONNECTED):
                self.wrkr_close_connection.emit()
        else:
            if self._transition(CS.FAILED):
                self._teardown()

    @Slot()
    def _on_connection_closed(self):
        """Handles Connection.closed -- confirmation the port is shut."""
        if self._transition(CS.DISCONNECTED):
            ...
        elif self._transition(CS.FAILED):
            ...
        else:
            logger.warning(
                "`ConnectionService`: closed received in unexpected state: %s", self._state
            )

        self._teardown()

    def _on_connection_ok(self): ...
    def _on_connection_status(self): ...
    def _on_connection_error(self): ...
    def _on_connection_line(self): ...

    def start(self):
        """Begins connecting, if currently DISCONNECTED or FAILED."""
        if self._transition(CS.CONNECTING):
            self._buildup()
        else:
            logger.warning(
                "`ConnectionService`: start() called from invalid state: %s", self._state
            )

    def stop(self):
        """Requests a stop, if currently CONNECTING or CONNECTED. No-ops
        otherwise."""
        if self._transition(CS.STOPPING):
            self.wrkr_close_connection.emit()

    def shutdown(self, on_ready):
        self.stop()

        if self._state in (CS.DISCONNECTED, CS.FAILED):
            on_ready()
            return

        loop = QEventLoop()

        def _on_state_changed(s):
            if s in (CS.DISCONNECTED, CS.FAILED):
                self.state_changed.disconnect(_on_state_changed)
                loop.quit()

        self.state_changed.connect(_on_state_changed)
        loop.exec_()
        on_ready()

    def send_line(self, text):
        """Request `text` to be sent over the serial connection."""
        if self._state is CS.CONNECTED:
            self.wrkr_send_line.emit(text)

    def send_realtime(self, data):
        """Request `data` to be sent over the serial connection. as a realtime
        byte"""
        if self._state is CS.CONNECTED:
            self.wrkr_send_realtime.emit(data)

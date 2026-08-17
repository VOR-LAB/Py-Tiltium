from PySide6.QtCore import QObject, Signal, Slot

from core.connection import ConnectionService
from core.protocol import JOG_CANCEL, jog_command
from core.states import ConnectionState as CState


class UIController(QObject):
    # UI State Signal
    state_changed = Signal(CState)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._conn_state: CState = CState.DISCONNECTED
        self._connection = ConnectionService()
        self._connection.state_changed.connect(self._on_conn_state_change)

    def shutdown(self, on_ready):
        self._connection.shutdown(on_ready)

    @Slot()
    def connect_request(self):
        self._connection.start()

    @Slot()
    def disconnect_request(self):
        self._connection.stop()

    @Slot()
    def connection_button_callback(self):
        if self._conn_state in (CState.DISCONNECTED, CState.FAILED):
            self.connect_request()
        else:
            self.disconnect_request()

    @Slot(CState)
    def _on_conn_state_change(self, state):
        self._conn_state = state
        self.state_changed.emit(state)

    def send_jog_line(self, dir, mag):
        match dir:
            case "Z+":
                self._connection.send_line(jog_command("Z", +mag, 180.0))
            case "Z-":
                self._connection.send_line(jog_command("Z", -mag, 180.0))
            case "A+":
                self._connection.send_line(jog_command("A", +mag, 180.0))
            case "A-":
                self._connection.send_line(jog_command("A", -mag, 180.0))

    def send_jog_cancel(self):
        self._connection.send_realtime(JOG_CANCEL)

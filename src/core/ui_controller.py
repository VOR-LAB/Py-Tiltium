from PySide6.QtCore import QObject, Signal, Slot
from core.connection import ConnectionService
from core.states import ConnectionState
from core.protocol import jog_command, JOG_CANCEL

class UIController(QObject):

    #Connection Signals
    close_connection = Signal()
    arrow_pressed = Signal(str)
    arrow_released = Signal(bytes)

    #UI State Signal
    state_changed = Signal(ConnectionState)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._conn_state: ConnectionState = ConnectionState.DISCONNECTED;
        self._connection = ConnectionService()
        self.close_connection.connect(self._connection.stop)
        self.arrow_pressed.connect(self._connection.send_line)
        self.arrow_released.connect(self._connection.send_realtime)
        self._connection.state_changed.connect(self._on_conn_state_change)

    def shutdown(self, on_ready):
        if self._conn_state == ConnectionState.DISCONNECTED:
            on_ready()
            return
        self.state_changed.connect(lambda s: on_ready() if s == ConnectionState.DISCONNECTED else None)
        self.close_connection.emit()

    @Slot()
    def connect_request(self):
        self._connection.start()

    @Slot()
    def disconnect_request(self):
        self._connection.stop()

    @Slot()
    def connection_button_callback(self):
        if self._conn_state in (ConnectionState.DISCONNECTED, ConnectionState.FAILED):
            self.connect_request()
        else:
            self.disconnect_request()

    @Slot(ConnectionState)
    def _on_conn_state_change(self, state):
        self._conn_state = state;
        self.state_changed.emit(state)

    def arrow_button_pressed(self, dir):
        match dir:
            case 'Z+':
                self.arrow_pressed.emit(jog_command('Z', 20.0, 180.0))
            case 'Z-':
                self.arrow_pressed.emit(jog_command('Z', -20.0, 180.0))
            case 'A+':
                self.arrow_pressed.emit(jog_command('A', +20.0, 180.0))
            case 'A-':
                self.arrow_pressed.emit(jog_command('A', -20.0, 180.0))

    def arrow_button_released(self):
        self.arrow_released.emit(JOG_CANCEL)

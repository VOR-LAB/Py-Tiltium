import logging
logger = logging.getLogger(__name__)

from PySide6.QtCore import QObject, Signal, Slot

from core.connection import ConnectionService
from core.activity_log import ActivityLog
from core.states import ConnectionState as CState
from core.protocol import jog_command, JOG_CANCEL, STATUS_QUERY, jog_time

class UIController(QObject):

    state_changed = Signal(CState)

    log_updated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._conn_state: CState = CState.DISCONNECTED;

        self._connection = ConnectionService()
        self._connection.state_changed.connect(self._on_conn_state_change)

        self._activity_log = ActivityLog()
        self._connection.status_received.connect(lambda d: self._on_info_received('status', d))
        self._connection.ok_received.connect(lambda: self._on_info_received('ok', None))
        self._connection.error_received.connect(lambda msg: self._on_info_received('error', msg))
        self._connection.line_received.connect(lambda line: self._on_info_received('line', line))

    @Slot(CState)
    def _on_conn_state_change(self, state):
        self._conn_state = state;
        self.state_changed.emit(state)

    def _on_info_received(self, kind: str, payload):
        self.log_updated.emit(self._activity_log.add(kind, payload))

    def shutdown(self, on_ready):
        self._connection.shutdown(on_ready);

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

    def req_jog_line(self, axis, dist, rate):
        self._connection.send_line(jog_command(axis, dist, rate))
        logger.info(f"`req_jog_line`: time taken is {jog_time(axis, dist, rate):.3f}s")

    def req_jog_cancel(self):
        self._connection.send_realtime(JOG_CANCEL)

    def req_realtime_status(self):
        self._connection.send_realtime(STATUS_QUERY)

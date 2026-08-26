import logging

from PySide6.QtCore import QObject, Signal, Slot

from core.activity_log import ActivityLog
from core.connection import ConnectionService
from core.protocol import JOG_CANCEL, STATUS_QUERY, jog_command, jog_time
from core.states import ConnectionState as CState
from params import DEG_PER_DIST

logger = logging.getLogger(__name__)


class UIController(QObject):
    conn_state_changed = Signal(CState)
    log_updated = Signal(str)

    def __init__(self, parent=None, deg_per_dist: float = DEG_PER_DIST):
        super().__init__(parent)
        self._deg_per_dist = deg_per_dist

        self._conn_state: CState = CState.DISCONNECTED
        self._connection = ConnectionService()
        self._connection.state_changed.connect(self._on_conn_state_change)

        self._activity_log = ActivityLog()
        self._connection.status_received.connect(lambda d: self._on_info_received("status", d))
        self._connection.ok_received.connect(lambda: self._on_info_received("ok", None))
        self._connection.error_received.connect(lambda msg: self._on_info_received("error", msg))
        self._connection.line_received.connect(lambda line: self._on_info_received("line", line))

    @Slot(CState)
    def _on_conn_state_change(self, state):
        self._conn_state = state
        self.conn_state_changed.emit(state)

    def _on_info_received(self, kind: str, payload):
        self.log_updated.emit(self._activity_log.add(kind, payload))

    def shutdown(self, on_ready):
        self._connection.shutdown(on_ready)

    @Slot()
    def req_connect(self):
        self._connection.start()

    @Slot()
    def req_disconnect(self):
        self._connection.stop()

    @Slot()
    def toggle_connect_disconnect(self):
        if self._conn_state in (CState.DISCONNECTED, CState.FAILED):
            self.req_connect()
        else:
            self.req_disconnect()

    def req_jog_line(self, axis, dist, rate):
        dist /= self._deg_per_dist
        rate /= self._deg_per_dist
        rate *= 60.0
        self._connection.send_line(jog_command(axis, dist, rate))
        logger.info(f"`req_jog_line`: time taken is {jog_time(axis, dist, rate):.3f}s")

    def req_jog_cancel(self):
        self._connection.send_realtime(JOG_CANCEL)

    def req_status(self):
        self._connection.send_realtime(STATUS_QUERY)

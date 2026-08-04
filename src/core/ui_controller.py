from PySide6.QtCore import QObject, QThread, Signal
from core.connection import Connection
from core.protocol import jog_command, JOG_CANCEL

class UIController(QObject):
    #Connection Signals
    close_connection = Signal()
    arrow_pressed = Signal(str)
    arrow_released = Signal(bytes)

    #UI Signals
    status_text_changed = Signal(str)
    button_text_changed = Signal(str)
    button_enable_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.connection: Connection | None = None
        self.connection_thread: QThread | None = None

    def connection_button_callback(self):
        if self.connection is None:
            self.status_text_changed.emit('Connecting...')
            self.button_enable_changed.emit(False)
            self.connection_thread = QThread()
            self.connection = Connection()
            self.connection.moveToThread(self.connection_thread)

            self.connection_thread.started.connect(self.connection.connect_to_device)
            self.connection.result.connect(self.connected_callback)

            self.close_connection.connect(self.connection.close)
            self.arrow_pressed.connect(self.connection.send_line)
            self.arrow_released.connect(self.connection.send_realtime)

            self.connection.closed.connect(self.connection_thread.quit)
            self.connection_thread.finished.connect(self.connection_thread.deleteLater)

            self.connection_thread.start()
        else:
            self.status_text_changed.emit('Disconnecting...')
            self.button_enable_changed.emit(False)
            self.close_connection.emit()

    def connected_callback(self, success):
        if success:
            self.status_text_changed.emit('Connection Failed.')
            self.button_enable_changed.emit(True)
            return
        self.connection_thread.finished.connect(self.disconnected_callback)
        self.status_text_changed.emit(f"Connected to HAPPY")
        self.button_text_changed.emit('Disconnect')
        self.button_enable_changed.emit(True)

    def disconnected_callback(self):
        self.connection = None
        self.connection_thread = None
        self.status_text_changed.emit('Disconnected.')
        self.button_text_changed.emit('Connect')
        self.button_enable_changed.emit(True)

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


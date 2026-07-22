from PySide6.QtCore import QObject, Signal
from core.connection import Connection
from core.workers import start_worker, DeviceWorker

class UIController(QObject):
    status_text_changed = Signal(str)
    button_text_changed = Signal(str)
    button_enable_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.connection = None

        self.thread = None
        self.worker = None

    def connection_button_callback(self):
        if self.connection is None:
            self.status_text_changed.emit("Connecting...")
            self.button_enabled_changed.emit(False)
            self.thread, self.worker = start_worker(DeviceWorker(), self.connection_result_callback)
        else:
            self.status_text_changed.emit("Disconnecting...")
            self.button_enabled_changed.emit(False)
            self.connection.close()
            self.connection = None
            self.status_text_changed.emit("Disconnected.")
            self.button_text_changed.emit("Connect")
            self.button_enabled_changed.emit(True)

    def connection_result_callback(self, port):
        if port is None:
            self.status_text_changed.emit("Connection Failed.")
            self.button_enabled_changed.emit(True)
            return
        self.connection = Connection(port, parent=self)
        self.status_text_changed.emit(f"Connected to {port.portName()}")
        self.button_text_changed.emit("Disconnect")
        self.button_enabled_changed.emit(True)

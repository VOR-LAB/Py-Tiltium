from PySide6.QtCore import QObject, Signal
from PySide6.QtSerialPort import QSerialPort
from core import status

# Connection handles QSerialPort object for sending and receiving 
# information over the serial connection.
class Connection(QObject):
    status_received = Signal(dict)
    ok_received = Signal()
    error_received = Signal(str)
    line_received = Signal(str)

    def __init__(self, port: QSerialPort, parent=None):
        super().__init__(parent)
        self._port = port
        self._buffer = ''
        self._port.readyRead.connect(self._on_ready_read)

    def _on_ready_read(self):
        self._buffer += bytes(self._port.readAll().data()).decode('utf-8', errors='ignore')
        while '\n' in self._buffer:
            line, self._buffer = self._buffer.split('\n', 1)
            self._handle_line(line)

    def _handle_line(self, line: str):
        line = line.strip()
        if not line:
            return
        if line.startswith('<'):
            self.status_received.emit(status.parse_status(line))
        elif line == 'ok':
            self.ok_received.emit()
        elif line.startswith('error:'):
            self.error_received.emit(line)
        else:
            self.line_received.emit(line)

    def send_line(self, text: str):
        self._port.write((text + '\n').encode('utf-8'))

    def send_realtime(self, byte: bytes):
        self._port.write(byte)

    def close(self):
        self._port.close()

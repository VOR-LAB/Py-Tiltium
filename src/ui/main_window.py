import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QWidget

from core.workers import start_worker, DeviceWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.device_connection = None

        self.connection_status = QLabel("Device not connected.")

        self.connection_button = QPushButton("Connect")
        self.connection_button.clicked.connect(self.connection_button_callback)

        # Layout starts here.
        layout = QVBoxLayout()

        tool_bar = QHBoxLayout()
        tool_bar.addWidget(self.connection_status)
        tool_bar.addWidget(self.connection_button)

        layout.addLayout(tool_bar)
        # Layout ends here.

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.thread = None
        self.worker = None

    def connection_button_callback(self):
        self.connection_status.setText("Connecting...")
        self.connection_button.setEnabled(False)
        
        self.thread, self.work = start_worker(DeviceWorker(), self.connection_result_callback)

    def connection_result_callback(self, result):
        if result is None:
            self.connection_status.setText("Connection Failed.")
            self.connection_button.setEnabled(True)
        else:
            self.device_connection = result
            self.connection_status.setText(f"Connected to {result.name}")

    def closeEvent(self, event):
        if self.device_connection:
            self.device_connection.close()

        event.accept()
        

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

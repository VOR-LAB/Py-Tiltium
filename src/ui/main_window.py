import sys
from core.states import ConnectionState as CState
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QWidget, QStyle

class MainWindow(QMainWindow):
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        self._connection_status = QLabel('Device not connected.')
        self._connection_button = QPushButton('Connect')
        self._connection_button.clicked.connect(self.controller.connection_button_callback)

        controller.state_changed.connect(self._state_changed)

        self._z_plus_button = QPushButton('Up')
        self._z_minus_button = QPushButton('Down')
        self._a_plus_button = QPushButton('Right')
        self._a_minus_button = QPushButton('Left')

        self._z_plus_button.pressed.connect(lambda: self.controller.arrow_button_pressed('Z+'))
        self._z_minus_button.pressed.connect(lambda: self.controller.arrow_button_pressed('Z-'))
        self._a_plus_button.pressed.connect(lambda: self.controller.arrow_button_pressed('A+'))
        self._a_minus_button.pressed.connect(lambda: self.controller.arrow_button_pressed('A-'))

        self._z_plus_button.released.connect(lambda: self.controller.arrow_button_released())
        self._z_minus_button.released.connect(lambda: self.controller.arrow_button_released())
        self._a_plus_button.released.connect(lambda: self.controller.arrow_button_released())
        self._a_minus_button.released.connect(lambda: self.controller.arrow_button_released())

        self._z_plus_button.setIcon(self._z_plus_button.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self._z_minus_button.setIcon(self._z_minus_button.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self._a_plus_button.setIcon(self._a_plus_button.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self._a_minus_button.setIcon(self._a_minus_button.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))

        # Layout starts here.
        layout = QVBoxLayout()

        tool_bar = QHBoxLayout()
        tool_bar.addWidget(self._connection_status)
        tool_bar.addWidget(self._connection_button)

        button_box = QGridLayout()
        button_box.addWidget(self._z_plus_button, 0, 1)
        button_box.addWidget(self._z_minus_button, 2, 1)
        
        button_box.addWidget(self._a_minus_button, 1, 0)
        button_box.addWidget(self._a_plus_button, 1, 2)

        layout.addLayout(tool_bar)
        layout.addLayout(button_box)
        # Layout ends here.

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        
    def _state_changed(self, states):
        match states:
            case CState.DISCONNECTED:
                self._connection_button.setText("Connect")
                self._connection_status.setText("Disconnected.")
                self._connection_button.setEnabled(True)
            case CState.CONNECTING:
                self._connection_status.setText("Connecting...")
                self._connection_button.setEnabled(False)
            case CState.FAILED:
                self._connection_button.setText("Connect")
                self._connection_button.setEnabled(True)
                self._connection_status.setText("Connection Failed, check physical connection.")
            case CState.CONNECTED:
                self._connection_button.setText("Disconnect")
                self._connection_button.setEnabled(True)
                self._connection_status.setText("Connected!")
            case CState.STOPPING:
                self._connection_button.setEnabled(False)
                self._connection_status.setText("Disconnecting...")
            case _:
                self._connection_button.setText("Unknown State")
                self._connection_button.setEnabled(False)
                self._connection_status.setText("Unknown State")

    def closeEvent(self, event):
        self.controller.shutdown(self.close)
        event.ignore()
        

if __name__ == '__main__':
    from core.ui_controller import UIController

    app = QApplication(sys.argv)
    window = MainWindow(UIController())
    window.show()
    sys.exit(app.exec())

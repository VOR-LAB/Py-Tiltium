import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QWidget, QStyle

class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        self._connection_status = QLabel("Device not connected.")
        self._connection_button = QPushButton("Connect")
        self._connection_button.clicked.connect(self.controller.connection_button_callback)

        self.controller.status_text_changed.connect(self._connection_status.setText);
        self.controller.button_text_changed.connect(self._connection_button.setText);
        self.controller.button_enabled_changed.connect(self._connection_button.setEnabled);

        self._z_plus_button = QPushButton("Up")
        self._z_minus_button = QPushButton("Down")
        self._a_plus_button = QPushButton("Right")
        self._a_minus_button = QPushButton("Left")

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

    def closeEvent(self, event):
        event.accept()
        

if __name__ == '__main__':
    from core.ui_controller import UIController

    app = QApplication(sys.argv)
    window = MainWindow(UIController())
    window.show()
    sys.exit(app.exec())

import sys
from typing import ClassVar, NamedTuple

from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from core.protocol import MAX_DIST, MAX_RATE
from core.states import ConnectionState as CState
from params import DEG_PER_DIST


class ConnStateDisplay(NamedTuple):
    button_text: str
    button_enabled: bool
    status_text: str


class MainWindow(QMainWindow):
    _CONN_STATE_DISPLAY: ClassVar[dict] = {
        CState.DISCONNECTED: ConnStateDisplay("Connect", True,
                                              "Disconnected."),
        CState.CONNECTING: ConnStateDisplay("Connect", False, "Connecting..."),
        CState.FAILED: ConnStateDisplay("Connect", True, "Connection Failed, " + 
                                        "check physical connection."),
        CState.CONNECTED: ConnStateDisplay("Disconnect", True, "Connected!"),
        CState.STOPPING: ConnStateDisplay("Disconnect", False,
                                          "Disconnecting..."),
    }
    _UNKNOWN_CONN_STATE_DISPLAY = ConnStateDisplay("Unknown State", False, "Unknown State")

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        self._connection_status_label = QLabel("Device not connected.")
        self._connection_button = QPushButton("Connect")

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)

        self._distance_spinbox = QDoubleSpinBox()
        self._distance_spinbox.setDecimals(1)
        self._distance_spinbox.setRange(0.0, MAX_DIST * DEG_PER_DIST)
        self._distance_spinbox.setSingleStep(10)

        self._rate_spinbox = QDoubleSpinBox()
        self._rate_spinbox.setDecimals(1)
        self._rate_spinbox.setRange(0.0, (MAX_RATE * DEG_PER_DIST) / 60.0)
        self._rate_spinbox.setSingleStep(5)

        self._z_plus_button = QPushButton("Up")
        self._z_minus_button = QPushButton("Down")
        self._a_plus_button = QPushButton("Right")
        self._a_minus_button = QPushButton("Left")

        self._jog_cancel_button = QPushButton("Cancel")
        self._req_status_button = QPushButton("Status")

        layout = QVBoxLayout()

        top_bar_layout = QHBoxLayout()
        top_bar_layout.addWidget(self._connection_status_label)
        top_bar_layout.addWidget(self._connection_button)
        layout.addLayout(top_bar_layout)

        center_layout = QHBoxLayout()

        log_panel_layout = QVBoxLayout()
        log_panel_layout.addWidget(self._log_view)
        center_layout.addLayout(log_panel_layout)

        controls_panel_layout = QVBoxLayout()

        trajectory_settings_layout = QFormLayout()
        trajectory_settings_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        trajectory_settings_layout.addRow("Angle (deg):", self._distance_spinbox)
        trajectory_settings_layout.addRow("Rate (deg/s):", self._rate_spinbox)
        controls_panel_layout.addLayout(trajectory_settings_layout)

        jog_pad_grid = QGridLayout()
        jog_pad_grid.addWidget(self._z_plus_button, 0, 1)
        jog_pad_grid.addWidget(self._z_minus_button, 2, 1)
        jog_pad_grid.addWidget(self._a_minus_button, 1, 0)
        jog_pad_grid.addWidget(self._a_plus_button, 1, 2)
        controls_panel_layout.addLayout(jog_pad_grid)

        center_layout.addLayout(controls_panel_layout)
        layout.addLayout(center_layout)

        bottom_bar_layout = QHBoxLayout()
        bottom_bar_layout.addWidget(self._req_status_button)
        bottom_bar_layout.addWidget(self._jog_cancel_button)
        layout.addLayout(bottom_bar_layout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._z_plus_button.setIcon(self._z_plus_button.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self._z_minus_button.setIcon(self._z_minus_button.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self._a_plus_button.setIcon(self._a_plus_button.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self._a_minus_button.setIcon(self._a_minus_button.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))

        self._connect_widgets_to_controller()
        self._connect_controller_to_widgets()

    def _connect_widgets_to_controller(self):
        self._connection_button.clicked.connect(self.controller.toggle_connect_disconnect)
        self._jog_cancel_button.clicked.connect(self.controller.req_jog_cancel)
        self._req_status_button.clicked.connect(self.controller.req_status)

        self._z_plus_button.clicked.connect(
            lambda: self.controller.req_jog_line("Z", 
                                                 self._distance_spinbox.value(), 
                                                 self._rate_spinbox.value())
        )
        self._z_minus_button.clicked.connect(
            lambda: self.controller.req_jog_line("Z", 
                                                 -self._distance_spinbox.value(), 
                                                 self._rate_spinbox.value())
        )
        self._a_plus_button.clicked.connect(
            lambda: self.controller.req_jog_line("A", 
                                                 self._distance_spinbox.value(), 
                                                 self._rate_spinbox.value())
        )
        self._a_minus_button.clicked.connect(
            lambda: self.controller.req_jog_line("A", 
                                                 -self._distance_spinbox.value(), 
                                                 self._rate_spinbox.value())
        )

    def _connect_controller_to_widgets(self):
        self.controller.conn_state_changed.connect(self._on_conn_state_changed)
        self.controller.log_updated.connect(self._log_view.setPlainText)

    def _on_conn_state_changed(self, state):
        display = self._CONN_STATE_DISPLAY.get(state, self._UNKNOWN_CONN_STATE_DISPLAY)
        self._connection_button.setText(display.button_text)
        self._connection_button.setEnabled(display.button_enabled)
        self._connection_status_label.setText(display.status_text)

    def closeEvent(self, event):
        self.controller.shutdown(self.close)
        event.ignore()


if __name__ == "__main__":
    import argparse
    import logging

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="count", default=0)
    args = parser.parse_args()

    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(args.verbose, len(levels) - 1)]
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    from controller.main_controller import UIController

    app = QApplication(sys.argv)
    window = MainWindow(UIController())
    window.show()
    sys.exit(app.exec())

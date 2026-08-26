import argparse
import logging
import sys
from typing import ClassVar, NamedTuple

from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
        CState.DISCONNECTED: ConnStateDisplay("Connect", True, "Disconnected."),
        CState.CONNECTING: ConnStateDisplay("Connect", False, "Connecting..."),
        CState.FAILED: ConnStateDisplay("Connect", True, "Connection Failed, " +
                                        "check physical connection."),
        CState.CONNECTED: ConnStateDisplay("Disconnect", True, "Connected!"),
        CState.STOPPING: ConnStateDisplay("Disconnect", False, "Disconnecting..."),
    }
    _UNKNOWN_CONN_STATE_DISPLAY = ConnStateDisplay("Unknown State", False, "Unknown State")

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        self._connection_status_label = QLabel("Device not connected.")
        self._connection_button = QPushButton("Connect")

        self._conn_state_readout = QLineEdit()
        self._conn_state_readout.setReadOnly(True)
        self._conn_state_readout.setText("CS.DISCONNECTED")

        self._queue_state_readout = QLineEdit()
        self._queue_state_readout.setReadOnly(True)
        self._queue_state_readout.setText("QS.IDLE")

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)

        self._queue_view = QPlainTextEdit()
        self._queue_view.setReadOnly(True)

        self._req_status_button = QPushButton("Status")
        self._clear_queue_button = QPushButton("Clear")

        self._distance_spinbox = QDoubleSpinBox()
        self._distance_spinbox.setDecimals(1)
        self._distance_spinbox.setRange(0.0, MAX_DIST * DEG_PER_DIST)
        self._distance_spinbox.setValue(30.0)
        self._distance_spinbox.setSingleStep(10)

        self._rate_spinbox = QDoubleSpinBox()
        self._rate_spinbox.setDecimals(1)
        self._rate_spinbox.setRange(0.0, (MAX_RATE * DEG_PER_DIST) / 60.0)
        self._rate_spinbox.setValue(2.0)
        self._rate_spinbox.setSingleStep(5)

        self._duration_spinbox = QDoubleSpinBox()
        self._duration_spinbox.setDecimals(2)
        self._duration_spinbox.setRange(0.0, 60.0)
        self._duration_spinbox.setValue(10.0)
        self._duration_spinbox.setSingleStep(0.1)

        self._z_plus_button = QPushButton("Up")
        self._z_minus_button = QPushButton("Down")
        self._pause_button = QPushButton("Pause")
        self._a_plus_button = QPushButton("Right")
        self._a_minus_button = QPushButton("Left")

        self._start_queue_button = QPushButton("Start")
        self._jog_cancel_button = QPushButton("Cancel")

        layout = QVBoxLayout()

        top_bar_layout = QHBoxLayout()
        top_bar_layout.addWidget(self._connection_status_label)
        top_bar_layout.addWidget(self._connection_button)
        layout.addLayout(top_bar_layout)

        center_layout = QHBoxLayout()

        activity_panel_layout = QVBoxLayout()

        state_readout_layout = QHBoxLayout()
        state_readout_layout.addWidget(self._conn_state_readout)
        state_readout_layout.addWidget(self._queue_state_readout)
        activity_panel_layout.addLayout(state_readout_layout)

        activity_panel_layout.addWidget(self._log_view)
        activity_panel_layout.addWidget(self._queue_view)

        activity_buttons_layout = QHBoxLayout()
        activity_buttons_layout.addWidget(self._req_status_button)
        activity_buttons_layout.addWidget(self._clear_queue_button)
        activity_panel_layout.addLayout(activity_buttons_layout)

        center_layout.addLayout(activity_panel_layout)

        controls_panel_layout = QVBoxLayout()

        trajectory_settings_layout = QFormLayout()
        trajectory_settings_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        trajectory_settings_layout.addRow("Angle (deg):", self._distance_spinbox)
        trajectory_settings_layout.addRow("Rate (deg/s):", self._rate_spinbox)
        trajectory_settings_layout.addRow("Pause Duration (t):", self._duration_spinbox)
        controls_panel_layout.addLayout(trajectory_settings_layout)

        jog_pad_grid = QGridLayout()
        jog_pad_grid.addWidget(self._z_plus_button, 0, 1)
        jog_pad_grid.addWidget(self._a_minus_button, 1, 0)
        jog_pad_grid.addWidget(self._pause_button, 1, 1)
        jog_pad_grid.addWidget(self._a_plus_button, 1, 2)
        jog_pad_grid.addWidget(self._z_minus_button, 2, 1)
        controls_panel_layout.addLayout(jog_pad_grid)

        controls_panel_layout.addWidget(self._start_queue_button)
        controls_panel_layout.addWidget(self._jog_cancel_button)

        center_layout.addLayout(controls_panel_layout)
        layout.addLayout(center_layout)

        bottom_bar_layout = QHBoxLayout()
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
        self._clear_queue_button.clicked.connect(self.controller.clear)
        self._start_queue_button.clicked.connect(self.controller.start)

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
        self._pause_button.clicked.connect(
            lambda: self.controller.req_pause(self._duration_spinbox.value())
        )

    def _connect_controller_to_widgets(self):
        self.controller.conn_state_changed.connect(self._on_conn_state_changed)
        self.controller.conn_state_changed.connect(
            lambda s: self._conn_state_readout.setText(f"CS.{s.name}")
        )
        self.controller.queue_state_changed.connect(
            lambda s: self._queue_state_readout.setText(f"QS.{s.name}")
        )
        self.controller.current_queue.connect(self._queue_view.setPlainText)
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
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="count", default=0)
    args = parser.parse_args()

    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(args.verbose, len(levels) - 1)]

    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    from controller.queue_controller import QueueController

    app = QApplication(sys.argv)
    window = MainWindow(QueueController())
    window.show()
    sys.exit(app.exec())

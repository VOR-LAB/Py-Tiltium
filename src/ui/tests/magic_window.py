import argparse
import logging
import sys

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

parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", action="count", default=0)
args = parser.parse_args()

levels = [logging.WARNING, logging.INFO, logging.DEBUG]
level = levels[min(args.verbose, len(levels) - 1)]

logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

class MainWindow(QMainWindow):
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        # Layout starts here.
        layout = QVBoxLayout()

        top_bar_layout = QHBoxLayout()
        layout.addLayout(top_bar_layout)

        center_layout = QHBoxLayout()
        layout.addLayout(center_layout)

        bottom_bar_layout = QHBoxLayout()
        layout.addLayout(bottom_bar_layout)

        # --- top bar (layout_box[0]) ---
        self._connection_status = QLabel('Device not connected.')
        top_bar_layout.addWidget(self._connection_status)

        self._connection_button = QPushButton('Connect')
        top_bar_layout.addWidget(self._connection_button)

        # --- center layout (layout_box[1]) ---
        activity_panel_layout = QVBoxLayout()
        center_layout.addLayout(activity_panel_layout)

        button_panel_layout = QVBoxLayout()
        center_layout.addLayout(button_panel_layout)

        # --- activity panel (center_box[0]) ---
        state_info_layout = QHBoxLayout()
        activity_panel_layout.addLayout(state_info_layout)

        self._conn_state_box = QLineEdit()
        state_info_layout.addWidget(self._conn_state_box)

        self._queue_state_box = QLineEdit()
        state_info_layout.addWidget(self._queue_state_box)

        self._log_box = QPlainTextEdit()
        activity_panel_layout.addWidget(self._log_box)

        self._command_queue_box = QPlainTextEdit()
        activity_panel_layout.addWidget(self._command_queue_box)

        activity_buttons_layout = QHBoxLayout()
        activity_panel_layout.addLayout(activity_buttons_layout)

        self._req_status_button = QPushButton('Status')
        self._queue_clear_button = QPushButton('Clear')
        activity_buttons_layout.addWidget(self._req_status_button)
        activity_buttons_layout.addWidget(self._queue_clear_button)

        # --- button panel (center_box[1]) ---
        trajectory_setting = QFormLayout()
        button_panel_layout.addLayout(trajectory_setting)
        trajectory_setting.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        arrow_grid = QGridLayout()
        button_panel_layout.addLayout(arrow_grid)

        self._distance_spin_field = QDoubleSpinBox()
        trajectory_setting.addRow('Distance:', self._distance_spin_field)

        self._rate_spin_field = QDoubleSpinBox()
        trajectory_setting.addRow('Rate:', self._rate_spin_field)

        self._duration_spin_field = QDoubleSpinBox()
        trajectory_setting.addRow('Pause Duration:', self._duration_spin_field)

        self._z_plus_button  = QPushButton('Up')
        arrow_grid.addWidget(self._z_plus_button, 0, 1)

        self._z_minus_button = QPushButton('Down')
        arrow_grid.addWidget(self._z_minus_button, 2, 1)

        self._pause_button = QPushButton("Pause")
        arrow_grid.addWidget(self._pause_button, 1, 1)

        self._a_plus_button  = QPushButton('Right')
        arrow_grid.addWidget(self._a_plus_button, 1, 2)

        self._a_minus_button = QPushButton('Left')
        arrow_grid.addWidget(self._a_minus_button, 1, 0)

        self._start_button = QPushButton('Start')
        self._req_cancel_button = QPushButton('Cancel')
        button_panel_layout.addWidget(self._start_button)
        button_panel_layout.addWidget(self._req_cancel_button)

        # --- bottom_bar (layout_box[2]) ---
        # Layout ends here.

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.controller.conn_state_changed.connect(self.conn_state_changed)
        self.controller.current_queue.connect(self._command_queue_box.setPlainText)
        self.controller.log_updated.connect(self._log_box.setPlainText)

        self._conn_state_box.setReadOnly(True)
        self._conn_state_box.setText('CS.DISCONNECTED')
        self._queue_state_box.setReadOnly(True)
        self._queue_state_box.setText('QS.IDLE')

        self.controller.conn_state_changed.connect(lambda s: self._conn_state_box.setText(f"CS.{s.name}"))
        self.controller.queue_state_changed.connect(lambda s: self._queue_state_box.setText(f"QS.{s.name}"))

        self._log_box.setReadOnly(True)
        self._command_queue_box.setReadOnly(True)

        self._connection_button.clicked.connect(self.controller.toggle_connect_disconnect)

        self._rate_spin_field.setDecimals(1)
        self._rate_spin_field.setRange(0.0, MAX_RATE)
        self._rate_spin_field.setValue(180.0)
        self._rate_spin_field.setSingleStep(5)

        self._distance_spin_field.setDecimals(1)
        self._distance_spin_field.setRange(0.0, MAX_DIST)
        self._distance_spin_field.setValue(30.0)
        self._distance_spin_field.setSingleStep(10)

        self._duration_spin_field.setDecimals(2)
        self._duration_spin_field.setRange(0.0, 60.0)
        self._duration_spin_field.setValue(10.0)
        self._duration_spin_field.setSingleStep(0.1)

        self._req_cancel_button.clicked.connect(self.controller.req_jog_cancel)
        self._req_status_button.clicked.connect(self.controller.req_status)
        self._queue_clear_button.clicked.connect(self.controller.clear)
        self._start_button.clicked.connect(self.controller.start)

        self._z_plus_button.clicked.connect(lambda:
                                            self.controller.req_jog_line('Z',
                                                                         self._distance_spin_field.value(),
                                                                         self._rate_spin_field.value()))
        self._z_minus_button.clicked.connect(lambda:
                                             self.controller.req_jog_line('Z',
                                                                          -self._distance_spin_field.value(),
                                                                          self._rate_spin_field.value()))
        self._a_plus_button.clicked.connect(lambda:
                                            self.controller.req_jog_line('A',
                                                                         self._distance_spin_field.value(),
                                                                         self._rate_spin_field.value()))
        self._a_minus_button.clicked.connect(lambda:
                                             self.controller.req_jog_line('A',
                                                                          -self._distance_spin_field.value(),
                                                                          self._rate_spin_field.value()))

        self._pause_button.clicked.connect(lambda: self.controller.req_pause(self._duration_spin_field.value()))

        self._z_plus_button.setIcon(self._z_plus_button
                                    .style()
                                    .standardIcon(QStyle.StandardPixmap.
                                                  SP_ArrowUp))
        self._z_minus_button.setIcon(self._z_minus_button
                                     .style()
                                     .standardIcon(QStyle.StandardPixmap.
                                                   SP_ArrowDown))
        self._a_plus_button.setIcon(self._a_plus_button
                                    .style()
                                    .standardIcon(QStyle.StandardPixmap.
                                                  SP_ArrowRight))
        self._a_minus_button.setIcon(self._a_minus_button
                                     .style()
                                     .standardIcon(QStyle.StandardPixmap.
                                                   SP_ArrowLeft))

    def _on_controller_status(self, status: dict):
        self._log_box.appendPlainText(status['state'])
        
    def conn_state_changed(self, states):
        match states:
            case CState.DISCONNECTED:
                self._connection_button.setText('Connect')
                self._connection_button.setEnabled(True)
                self._connection_status.setText('Disconnected.')
            case CState.CONNECTING:
                self._connection_button.setText('Connect')
                self._connection_button.setEnabled(False)
                self._connection_status.setText('Connecting...')
            case CState.FAILED:
                self._connection_button.setText('Connect')
                self._connection_button.setEnabled(True)
                self._connection_status.setText('Connection Failed, check'
                                                'physical connection.')
            case CState.CONNECTED:
                self._connection_button.setText('Disconnect')
                self._connection_button.setEnabled(True)
                self._connection_status.setText('Connected!')
            case CState.STOPPING:
                self._connection_button.setText('Disconnect')
                self._connection_button.setEnabled(False)
                self._connection_status.setText('Disconnecting...')
            case _:
                self._connection_button.setText('Unknown State')
                self._connection_button.setEnabled(False)
                self._connection_status.setText('Unknown State')

    def closeEvent(self, event):
        self.controller.shutdown(self.close)
        event.ignore()
        
if __name__ == '__main__':
    from controller.queue_controller import QueueController

    app = QApplication(sys.argv)
    window = MainWindow(QueueController())
    window.show()
    sys.exit(app.exec())

import sys
import argparse
import logging
from typing import assert_never

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QFormLayout, QMainWindow, QPlainTextEdit, QPushButton, QLabel, QGridLayout, QDoubleSpinBox, QVBoxLayout, QHBoxLayout, QWidget, QStyle
from core.states import ConnectionState as CState
from core.protocol import MAX_DIST, MAX_RATE

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
        self.controller.state_changed.connect(self.conn_state_changed)

        self._connection_status = QLabel('Device not connected.')

        self._log_box = QPlainTextEdit();
        self._log_box.setEnabled(False);

        self.controller.log_updated.connect(self._log_box.setPlainText)
        
        self._command_queue_box = QPlainTextEdit();
        self._command_queue_box.setEnabled(False);

        self._connection_button = QPushButton('Connect')
        self._connection_button.clicked.connect(self.controller.connection_button_callback)

        self._rate_spin_field = QDoubleSpinBox()
        self._rate_spin_field.setDecimals(1)
        self._rate_spin_field.setRange(0.0, MAX_RATE)
        self._rate_spin_field.setSingleStep(10)

        self._distance_spin_field = QDoubleSpinBox()
        self._distance_spin_field.setDecimals(1)
        self._distance_spin_field.setRange(0.0, MAX_DIST)
        self._distance_spin_field.setSingleStep(0.1)

        self._z_plus_button  = QPushButton('Up')
        self._z_minus_button = QPushButton('Down')
        self._a_plus_button  = QPushButton('Right')
        self._a_minus_button = QPushButton('Left')

        self._jog_cancel_button = QPushButton('Cancel')
        self._jog_cancel_button.clicked.connect(self.controller.send_jog_cancel)

        self._req_status_button = QPushButton('Status')
        self._req_status_button.clicked.connect(self.controller.send_realtime_status)

        self._z_plus_button.clicked.connect(lambda:
                                            self.controller.send_jog_line('Z',
                                                                          self._distance_spin_field.value(),
                                                                          self._rate_spin_field.value()))
        self._z_minus_button.clicked.connect(lambda:
                                             self.controller.send_jog_line('Z',
                                                                           -self._distance_spin_field.value(),
                                                                           self._rate_spin_field.value()))
        self._a_plus_button.clicked.connect(lambda:
                                            self.controller.send_jog_line('A',
                                                                          self._distance_spin_field.value(),
                                                                          self._rate_spin_field.value()))
        self._a_minus_button.clicked.connect(lambda:
                                             self.controller.send_jog_line('A',
                                                                           -self._distance_spin_field.value(),
                                                                           self._rate_spin_field.value()))

        self._z_plus_button.setIcon(self._z_plus_button.style()
                                    .standardIcon(QStyle.StandardPixmap.
                                                  SP_ArrowUp))
        self._z_minus_button.setIcon(self._z_minus_button .style()
                                     .standardIcon(QStyle.StandardPixmap.
                                                   SP_ArrowDown))
        self._a_plus_button.setIcon(self._a_plus_button .style()
                                    .standardIcon(QStyle.StandardPixmap.
                                                  SP_ArrowRight))
        self._a_minus_button.setIcon(self._a_minus_button.style()
                                     .standardIcon(QStyle.StandardPixmap.
                                                   SP_ArrowLeft))

        # Layout starts here.
        layout = QVBoxLayout()

        tool_bar = QHBoxLayout()

        tool_bar.addWidget(self._connection_status)
        tool_bar.addWidget(self._connection_button)
        layout.addLayout(tool_bar)

        center_layout = QHBoxLayout()

        command_space_layout = QVBoxLayout()
        command_space_layout.addWidget(self._log_box);
        command_space_layout.addWidget(self._command_queue_box);
        center_layout.addLayout(command_space_layout)

        button_panel = QVBoxLayout()

        trajectory_setting = QFormLayout()
        trajectory_setting.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        trajectory_setting.addRow('Distance:', self._distance_spin_field)
        trajectory_setting.addRow('Rate:', self._rate_spin_field)
        button_panel.addLayout(trajectory_setting)

        arrow_grid = QGridLayout()
        arrow_grid.addWidget(self._z_plus_button, 0, 1)
        arrow_grid.addWidget(self._z_minus_button, 2, 1)
        arrow_grid.addWidget(self._a_minus_button, 1, 0)
        arrow_grid.addWidget(self._a_plus_button, 1, 2)
        button_panel.addLayout(arrow_grid)

        additional_commands = QFormLayout()

        center_layout.addLayout(button_panel)

        bottom_bar = QHBoxLayout()
        bottom_bar.addWidget(self._req_status_button)
        bottom_bar.addWidget(self._jog_cancel_button)

        layout.addLayout(center_layout)

        layout.addLayout(bottom_bar)
        # Layout ends here.

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)


    def _on_controller_status(self, status: dict):
        self._log_box.appendPlainText(status['state']);
        
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

import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Union

from PySide6.QtCore import QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication

from controller.main_controller import UIController

from core.protocol import jog_command, jog_time
from core.states import QueueState as QS

class CommandKind(Enum):
    GCODE = auto()
    PAUSE = auto()

@dataclass
class QueueCommand:
    kind: CommandKind
    payload: Union[tuple[str, float], float]  # [str, float] for GCODE, float seconds for PAUSE

class QueueController(UIController):
    """An extension of `UIController` which handles queuing multiple commands
    before executing them on the grbrHAL controller. Includes non-GCode
    commands which get handled by the python code instead."""

    _TRANSITIONS: dict[QS, set[QS]] = {
        QS.IDLE:          {QS.RUNNING, QS.UNKNOWN_ERROR},
        QS.RUNNING:       {QS.CANCELLED, QS.FINISHED, QS.UNKNOWN_ERROR},
        QS.FINISHED:      {QS.IDLE, QS.UNKNOWN_ERROR},
        QS.CANCELLED:     {QS.IDLE, QS.UNKNOWN_ERROR},
        QS.UNKNOWN_ERROR: set(),
    }

    state_changed = Signal(QS)
    """emitted when a state transition has occurred."""

    current_command_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = QS.IDLE
        self._current_command: Optional[QueueCommand] = None

        self._queue: list[QueueCommand] = []

        self._queue_timer = QTimer(self)
        self._queue_timer.setSingleShot(True)
        self._queue_timer.timeout.connect(self.req_realtime_status)

        self._connection.status_received.connect(self._insure_idle)

    def _transition(self, new_state: QS) -> bool:
        """Attempt to move to new_state.

        Returns:
            True if the transition was applied, False if it was illegal.
        """
        if new_state not in self._TRANSITIONS[self._state]:
            return False
        self._state = new_state
        self.state_changed.emit(new_state)
        logger.info('`QueueController`: State changed to %s', self._state)
        return True

    def queue_jog_line(self, axis, dist, rate):
        if self._state is QS.IDLE:
            self._queue.append(QueueCommand(CommandKind.GCODE, 
                                            (jog_command(axis, 
                                                         dist, 
                                                         rate), 
                                             jog_time(axis, 
                                                      dist, 
                                                      rate))))
        else:
            logger.warning("`QueueController`: Tried queuing while not idle.")

    def queue_pause(self, dur: float):
        if self._state is QS.IDLE:
            self._queue.append(QueueCommand(CommandKind.PAUSE, dur))
        else:
            logger.warning("`QueueController`: Tried queuing while not idle.")

    def clear(self):
        """Discard the queue without running it."""
        if self._state is QS.IDLE:
            self._queue.clear()
            self._queue_timer.stop()
        else:
            logger.warning("`QueueController`: Tried clearing the queue while not idle.")

    def start(self):
        """Begin executing the queue in order."""
        if self._transition(QS.RUNNING):
            self._advance()
        else:
            match self._state:
                case QS.RUNNING:
                    logger.warning("`QueueController`: Queue is already running.")
                case QS.FINISHED:
                    logger.warning("`QueueController`: Finished queue must be acknowledged.")
                case QS.CANCELLED:
                    logger.warning("`QueueController`: Cancelled queue must be acknowledged.")
                case QS.UNKNOWN_ERROR:
                    logger.error("`QueueController`: Currently in an Unknown state.")

    def _advance(self):
        """Called when the current step has finished execution."""
        if self._state is QS.RUNNING:
            if not self._queue:
                if self._transition(QS.FINISHED):
                    self._current_command = None
                    self.current_command_changed.emit(None)
                    return
                elif self._transition(QS.UNKNOWN_ERROR):
                    logger.error("`QueueController`: I have no clue what may have caused this...")
                    self._current_command = None
                    self.current_command_changed.emit(None)
                    return

            self._current_command = self._queue.pop(0)
            self.current_command_changed.emit(self._current_command)

            payload = self._current_command.payload

            match self._current_command.kind:
                case CommandKind.GCODE:
                    assert isinstance(payload, tuple)
                    line, t = payload
                    self._connection.send_line(line)
                    self._queue_timer.start(int((t + 0.1) * 1000))
                case CommandKind.PAUSE:
                    assert isinstance(payload, float)
                    self._queue_timer.start(int(payload * 1000))

    @Slot(dict)
    def _insure_idle(self, status):
        if self._state == QS.RUNNING:
            state = status['state']
            if state == 'Idle':
                self._advance()
            elif state == 'Jog':
                logger.error(f"`QueueController`: My disappointment is immeasurable and my day is "
                             f"ruined: still jogging past deadline, state: {state}")
                self.req_jog_cancel()
            else:
                logger.error(f"`QueueController`: unexpected state during jog wait, panicking: {state}")
                self.req_jog_cancel()
                app = QApplication.instance()
                assert app is not None
                app.exit(1)

    def req_jog_cancel(self):
        if self._transition(QS.CANCELLED):
            super().req_jog_cancel()
            self._queue.clear()
            self._queue_timer.stop()
            if self._current_command is not None:
                self._current_command = None
                self.current_command_changed.emit(None)
        else:
            match self._state:
                case QS.FINISHED:
                    logger.warning("`QueueController`: Already finished, reset instead.")
                case QS.CANCELLED:
                    logger.warning("`QueueController`: Already cancelled, reset instead.")
                case QS.IDLE:
                    logger.warning("`QueueController`: Already idle, use clear instead.")
                case QS.UNKNOWN_ERROR:
                    logger.warning("`QueueController`: An unknown error has occured...")
                    

    def reset(self):
        if not self._transition(QS.IDLE):
            logger.warning(f"`QueueController`: Cannot go idle, state: {self._state}")

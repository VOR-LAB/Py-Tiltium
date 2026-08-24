from enum import Enum, auto


class QueueState(Enum):
    RUNNING = auto()
    CANCELLED = auto()
    FINISHED = auto()
    IDLE = auto()
    UNKNOWN_ERROR = auto()


class ConnectionState(Enum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    FAILED = auto()
    STOPPING = auto()


class ControlMode(Enum):
    QUEUE = auto()
    NORMAL = auto()

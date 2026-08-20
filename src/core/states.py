from enum import Enum, auto


class ConnectionState(Enum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    FAILED = auto()
    STOPPING = auto()


class UICState(Enum):
    ALLOW_INPUT = auto()
    DISALLOW_INPUT = auto()

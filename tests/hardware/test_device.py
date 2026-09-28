from dataclasses import dataclass

from hardware import device


@dataclass
class FakePortInfo:
    device: str
    vid: int | None
    pid: int | None
    serial_number: str | None


def test_find_device_port_matches_vid_pid_serial(monkeypatch):
    target = FakePortInfo(
        "/dev/tty.target", device.TARGET_VID, device.TARGET_PID, device.TARGET_SERIAL
    )
    other = FakePortInfo("/dev/tty.other", 0x1234, 0x5678, "OTHERSERIAL")
    monkeypatch.setattr(device.serial.tools.list_ports, "comports", lambda: [other, target])
    assert device.find_device_port() == "/dev/tty.target"


def test_find_device_port_no_match_returns_none(monkeypatch):
    other = FakePortInfo("/dev/tty.other", 0x1234, 0x5678, "OTHERSERIAL")
    monkeypatch.setattr(device.serial.tools.list_ports, "comports", lambda: [other])
    assert device.find_device_port() is None


def test_find_device_port_requires_all_three_fields(monkeypatch):
    # right vid/pid but wrong serial must not match
    wrong_serial = FakePortInfo("/dev/tty.x", device.TARGET_VID, device.TARGET_PID, "WRONG")
    monkeypatch.setattr(device.serial.tools.list_ports, "comports", lambda: [wrong_serial])
    assert device.find_device_port() is None

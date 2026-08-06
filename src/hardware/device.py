import logging
logger = logging.getLogger(__name__)

from PySide6.QtCore import QIODeviceBase
from PySide6.QtSerialPort import QSerialPort
import serial.tools.list_ports

# grblHAL BOB controller VID and PID. 
TARGET_VID    = int('0483', 16)
TARGET_PID    = int('5740', 16)
TARGET_SERIAL = '4E814D985200'
TARGET_BAUD   = 115200

# Fine the device port currently used by the BOB.
def find_device_port():
    for port in serial.tools.list_ports.comports():
        if (
                port.vid == TARGET_VID and
                port.pid == TARGET_PID and
                port.serial_number == TARGET_SERIAL
        ):
            return port.device

    return None

# Connect to the device port found by the above function.
def connect():
    target = find_device_port()

    if target is None:
        logger.info("Device not found. Check connection.")
        return None

    port = QSerialPort()
    port.setPortName(target)
    port.setBaudRate(TARGET_BAUD)
    port.setDataBits(QSerialPort.DataBits.Data8)
    port.setParity(QSerialPort.Parity.NoParity)
    port.setStopBits(QSerialPort.StopBits.OneStop)
    port.setFlowControl(QSerialPort.FlowControl.NoFlowControl)

    if not port.open(QIODeviceBase.OpenModeFlag.ReadWrite):
        print(f"Failed to open {target}: {port.errorString()}")
        return None

    return port

# Unit test for insuring the code within this file is running correctly.
if __name__ == "__main__":
    ser = connect()
    try:
        print("Port open:", ser.isOpen() if ser else False)
        if ser:
            print("Device:", ser.portName())
    finally:
        if ser:
            ser.close()

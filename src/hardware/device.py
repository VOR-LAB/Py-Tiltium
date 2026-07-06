import serial
import serial.tools.list_ports

# grblHAL BOB controller VID and PID. 
TARGET_VID = int('0483', 16)
TARGET_PID = int('5740', 16)
TARGET_SERIAL = '4E814D985200'

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
        print("Device not found. Check connection.")
        return None

    try:
        ser = serial.Serial(port=target, baudrate=115200, timeout=2, rtscts=False)

    except serial.SerialException as e:
        print(f"Failed to open {target}: {e}")
        return None

    return ser

# Unit test for insuring the code within this file is running correctly.
if __name__ == "__main__":
    ser = connect()
    try:
        print("Port open:", ser.is_open if ser else False)
        if ser:
            print("Device:", ser.name)
    finally:
        if ser:
            ser.close()

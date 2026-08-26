import math

# Real-time bytes. Sent raw, no newline, processed immediately by grblHAL.
STATUS_QUERY = b"?"
FEED_HOLD = b"!"
CYCLE_RESUME = b"~"
JOG_CANCEL = b"\x85"
SOFT_RESET = b"\x18"

# Checks and bounds. Must raise exceptions in case functions are used incorrectly.
AXES = ("A", "Z")
MAX_DIST = 200.0
MIN_DIST = -200.0
MAX_RATE = 300.0

ACCEL_SETTING = {"A": 10.0, "Z": 10.0}  # revs/s^2 ($122, $123)
MAX_RATE_SETTING = {"A": 500.0, "Z": 500.0}  # revs/min ($112, $113)


# Line-based command builder.
def jog_command(axis: str, distance: float, feedrate: float) -> str:
    if axis not in AXES:
        raise ValueError(f"jog_command: incorrect `axis`: {axis!r}, expected one of {AXES}")
    if not (MIN_DIST < distance < MAX_DIST):
        raise ValueError(
            f"jog_command: `distance` out of range: {distance}, "
            f"expected `{MIN_DIST} < distance < {MAX_DIST}`"
        )
    if feedrate < 0:
        raise ValueError(
            f"jog_command: `feedrate` is negative: {feedrate}, expected a positive value"
        )
    if feedrate > MAX_RATE:
        raise ValueError(
            f"jog_command: `feedrate` too large: {feedrate}, expected `feedrate < {MAX_RATE}`"
        )

    return f"$J=G91 {axis}{distance:.3f} F{feedrate:.3f}"

# Calculates the amount of time a jog takes.
def jog_time(axis: str, distance: float, feedrate: float) -> float:
    if axis not in AXES:
        raise ValueError(f"jog_command: incorrect `axis`: {axis!r}, expected one of {AXES}")
    if not (MIN_DIST < distance < MAX_DIST):
        raise ValueError(
            f"jog_command: `distance` out of range: {distance}, "
            f"expected `{MIN_DIST} < distance < {MAX_DIST}`"
        )
    if feedrate < 0:
        raise ValueError(
            f"jog_command: `feedrate` is negative: {feedrate}, expected a positive value"
        )
    if feedrate > MAX_RATE:
        raise ValueError(
            f"jog_command: `feedrate` too large: {feedrate}, expected `feedrate < {MAX_RATE}`"
        )

    accel = ACCEL_SETTING[axis]
    v_max = min(feedrate, MAX_RATE_SETTING[axis]) / 60.0
    d = abs(distance)
    d_accel = v_max**2 / (2 * accel)

    if 2 * d_accel < d:
        d_cruise = d - 2 * d_accel
        t = 2 * (v_max / accel) + d_cruise / v_max
    else:
        v_peak = math.sqrt(accel * d)
        t = 2 * v_peak / accel

    return t

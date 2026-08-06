# Real-time bytes. Sent raw, no newline, processed immediately by grblHAL.
STATUS_QUERY = b'?'
FEED_HOLD    = b'!'
CYCLE_RESUME = b'~'
JOG_CANCEL   = b'\x85'
SOFT_RESET   = b'\x18'

# Checks and bounds. Must raise exceptions in case functions are used incorrectly.
AXES         = ('A', 'Z')
MAX_DIST     = 30.0
MIN_DIST     = -30.0
MAX_RATE     = 300.0

# Line-based command builder.
def jog_command(axis: str, distance: float, feedrate: float) -> str:
    if axis not in AXES:
        raise ValueError(
                f"jog_command: incorrect `axis`: {axis!r}, "
                f"expected one of {AXES}"
        )
    if not (MIN_DIST < distance < MAX_DIST):
        raise ValueError(
                f"jog_command: `distance` out of range: {distance}, " 
                f"expected `{MIN_DIST} < distance < {MAX_DIST}`"
        )
    if feedrate < 0:
        raise ValueError(
                f"jog_command: `feedrate` is negative: {feedrate}, "
                f"expected a positive value"
        )
    if feedrate > MAX_RATE:
        raise ValueError(
                f"jog_command: `feedrate` too large: {feedrate}, "
                f"expected `feedrate < {MAX_RATE}`"
        )

    return f"$J=G91 {axis}{distance} F{feedrate}"

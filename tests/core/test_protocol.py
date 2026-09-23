import math

import pytest

from core import protocol


def test_realtime_byte_constants():
    assert protocol.STATUS_QUERY == b"?"
    assert protocol.FEED_HOLD == b"!"
    assert protocol.CYCLE_RESUME == b"~"
    assert protocol.JOG_CANCEL == b"\x85"
    assert protocol.SOFT_RESET == b"\x18"


# --- jog_command: valid inputs ---


def test_jog_command_formats_axis_a_positive():
    assert protocol.jog_command("A", 12.5, 100.0) == "$J=G91 A12.500 F100.000"


def test_jog_command_formats_axis_z_negative():
    assert protocol.jog_command("Z", -50.0, 25.0) == "$J=G91 Z-50.000 F25.000"


def test_jog_command_rounds_to_three_decimals():
    assert protocol.jog_command("A", 1.23456, 10.0) == "$J=G91 A1.235 F10.000"


def test_jog_command_distance_zero():
    assert protocol.jog_command("A", 0.0, 10.0) == "$J=G91 A0.000 F10.000"


def test_jog_command_feedrate_at_max_rate_allowed():
    result = protocol.jog_command("A", 10.0, protocol.MAX_RATE)
    assert result == "$J=G91 A10.000 F300.000"


# --- jog_command: validation errors ---


def test_jog_command_invalid_axis():
    with pytest.raises(ValueError, match="incorrect `axis`"):
        protocol.jog_command("X", 10.0, 10.0)


def test_jog_command_distance_at_min_bound_rejected():
    with pytest.raises(ValueError, match="out of range"):
        protocol.jog_command("A", protocol.MIN_DIST, 10.0)


def test_jog_command_distance_at_max_bound_rejected():
    with pytest.raises(ValueError, match="out of range"):
        protocol.jog_command("A", protocol.MAX_DIST, 10.0)


def test_jog_command_distance_below_min():
    with pytest.raises(ValueError, match="out of range"):
        protocol.jog_command("A", -201.0, 10.0)


def test_jog_command_distance_above_max():
    with pytest.raises(ValueError, match="out of range"):
        protocol.jog_command("A", 201.0, 10.0)


def test_jog_command_feedrate_negative():
    with pytest.raises(ValueError, match="is negative"):
        protocol.jog_command("A", 10.0, -1.0)


def test_jog_command_feedrate_above_max():
    with pytest.raises(ValueError, match="too large"):
        protocol.jog_command("A", 10.0, 300.001)


# --- jog_time ---


def test_jog_time_shares_validation_with_jog_command():
    with pytest.raises(ValueError, match="incorrect `axis`"):
        protocol.jog_time("X", 10.0, 10.0)


def test_jog_time_distance_zero_returns_zero():
    assert protocol.jog_time("A", 0.0, 100.0) == 0.0


def test_jog_time_triangular_branch():
    # accel=10, feedrate=60 -> v_max=1.0. distance=0.05 keeps 2*d_accel (0.1) >= d,
    # so this never reaches v_max (triangular profile).
    t = protocol.jog_time("A", 0.05, 60.0)
    accel = protocol.ACCEL_SETTING["A"]
    v_peak = math.sqrt(accel * 0.05)
    expected = 2 * v_peak / accel
    assert t == pytest.approx(expected)


def test_jog_time_trapezoidal_branch():
    # Same accel/feedrate as above but distance=10.0 is large enough to cruise
    # at v_max (2*d_accel=0.1 < d=10.0).
    t = protocol.jog_time("A", 10.0, 60.0)
    assert t == pytest.approx(10.1)


def test_jog_time_feedrate_zero_with_nonzero_distance_raises():
    with pytest.raises(ValueError, match=r"feedrate.*zero"):
        protocol.jog_time("A", 50.0, 0.0)


def test_jog_time_feedrate_zero_with_zero_distance_returns_zero():
    assert protocol.jog_time("A", 0.0, 0.0) == 0.0

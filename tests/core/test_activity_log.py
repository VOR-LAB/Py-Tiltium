import re

from core.activity_log import ActivityLog

TS = re.compile(r"^\[\d{2}:\d{2}:\d{2}\] ")


def test_add_returns_full_text():
    log = ActivityLog()
    assert log.add("ok", None) == log.text


def test_text_lists_newest_first():
    log = ActivityLog()
    log.add("line", "first")
    log.add("line", "second")
    lines = log.text.split("\n")
    assert lines[0].endswith("second")
    assert lines[1].endswith("first")


def test_max_lines_truncates_oldest():
    log = ActivityLog(max_lines=2)
    log.add("line", "a")
    log.add("line", "b")
    log.add("line", "c")
    lines = log.text.split("\n")
    assert len(lines) == 2
    assert lines[-1].endswith("b")


def test_format_status_joins_dict_as_key_equals_value():
    log = ActivityLog()
    log.add("status", {"state": "Idle", "MPos": ["0", "0"]})
    assert TS.match(log.text)
    assert log.text.endswith("state=Idle, MPos=['0', '0']")


def test_format_ok_ignores_payload():
    log = ActivityLog()
    log.add("ok", "anything")
    assert log.text.endswith("] ok")


def test_format_error_and_line_use_payload_verbatim():
    log = ActivityLog()
    log.add("error", "error:9")
    assert log.text.endswith("error:9")


def test_format_unknown_kind_uses_str_of_payload():
    log = ActivityLog()
    log.add("mystery", 42)
    assert log.text.endswith("42")

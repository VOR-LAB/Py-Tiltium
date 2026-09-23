from core.status import parse_status


def test_parse_status_basic():
    result = parse_status("<Idle|MPos:0.000,1.000,2.000|FS:500,0>")
    assert result == {"state": "Idle", "MPos": ["0.000", "1.000", "2.000"], "FS": ["500", "0"]}


def test_parse_status_no_fields():
    assert parse_status("<Idle>") == {"state": "Idle"}


def test_parse_status_skips_field_without_colon():
    result = parse_status("<Idle|garbage|Pn:X>")
    assert result == {"state": "Idle", "Pn": ["X"]}


def test_parse_status_single_value_field_is_a_list():
    result = parse_status("<Idle|WCO:0.0>")
    assert result["WCO"] == ["0.0"]


def test_parse_status_strips_whitespace_and_missing_brackets():
    result = parse_status("  Idle|MPos:1,2\n")
    assert result == {"state": "Idle", "MPos": ["1", "2"]}

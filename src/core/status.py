def parse_status(line: str) -> dict:
    body = line.strip().lstrip("<").rstrip(">")
    parts = body.split("|")
    state = parts[0]
    fields = {}
    for p in parts[1:]:
        if ":" in p:
            key, val = p.split(":", 1)
            fields[key] = val.split(",")
    return {"state": state, **fields}

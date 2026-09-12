"""Summarize temporal and spatial anomalies without altering raw."""
from collections import Counter
from analytics.io import data_dir, read_events, write_json
from analytics.pipeline import normalize


def audit_anomalies() -> dict:
    anomalies = []
    for path in sorted((data_dir() / "raw" / "events").glob("*.jsonl.gz")):
        raw = read_events(path)
        by_id = {e['id']: e for e in raw}
        events = sorted([normalize(e) for e in raw], key=lambda e: (e.period, e.index))
        for a, b in zip(events, events[1:]):
            if a.period == b.period and a.seconds > b.seconds:
                anomalies.append({"match_id": path.name.split('.')[0], "kind": "time", "minute": by_id[b.event_id]['minute'], "second": by_id[b.event_id]['second'], "previous": a.model_dump(), "event": b.model_dump()})
        for e in events:
            if any(not (0 <= p[0] <= 120 and 0 <= p[1] <= 80) for p in (e.location, e.end_location) if p):
                anomalies.append({"match_id": path.name.split('.')[0], "kind": "coordinates", "event": e.model_dump()})
    write_json(data_dir() / "interim" / "anomalies.json", anomalies)
    return dict(Counter(f"{r['kind']}:{r['event']['type']}" for r in anomalies))


if __name__ == "__main__":
    print(audit_anomalies())

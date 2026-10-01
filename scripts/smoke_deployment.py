"""Check the deployed API against verified artifacts and a real historical run.

Usage: python scripts/smoke_deployment.py --base-url http://127.0.0.1:8000
POST creates or replaces only the deterministic run file under processed/runs.
"""
from __future__ import annotations

import argparse
import http.client
import json
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def request(base: str, path: str, payload: dict[str, object] | None = None) -> object:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    with urlopen(Request(base + path, data=data, headers=headers), timeout=120) as response:
        if response.status not in (200, 201):
            raise RuntimeError(f"Unexpected HTTP status: {response.status}")
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--origin", help="Optional frontend origin to check CORS preflight")
    parser.add_argument("--assistant-mode", choices=("skip", "deterministic", "openai"), default="skip",
                        help="Explicitly call report and agent, asserting the expected provider mode")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    for attempt in range(30):
        try:
            assert request(base, "/api/v1/ready") == {"status": "ready", "product": "CornerScout"}
            break
        except (URLError, http.client.RemoteDisconnected):
            if attempt == 29:
                raise
            time.sleep(2)
    query = urlencode({"rival": "Barcelona", "before": "2016-03-01", "limit": 8})
    matches = request(base, "/api/v1/matches?" + query)
    assert isinstance(matches, list) and len(matches) == 8
    assert all(match["match_date"] < "2016-03-01" for match in matches)
    run = request(base, "/api/v1/scouting-runs", {
        "rival": "Barcelona", "cutoff_date": "2016-03-01",
        "expected_match_ids": [match["match_id"] for match in matches],
    })
    assert isinstance(run, dict) and len(run["run_id"]) == 64
    path = "/api/v1/scouting-runs/" + run["run_id"]
    assert len(request(base, path)["matches"]) == 8
    assert len(request(base, path + "/matches-profile")) == 8
    summary = request(base, path + "/summary")
    assert summary["matches"] == 8 and summary["corners"] > 0
    assert request(base, path + "/habits")["corners"] == summary["corners"]
    assert isinstance(request(base, path + "/corners"), list)
    assert isinstance(request(base, path + "/destination-heatmap")["cells"], list)
    assert isinstance(request(base, path + "/patterns"), list)
    assert request(base, path + "/quality")["coverage_matches"] == 380
    assert request(base, path + "/model")["evaluations"]["objective_winners"]
    if args.assistant_mode != "skip":
        report = request(base, path + "/report", {})
        agent = request(base, path + "/agent", {"question": "¿Qué partidos se analizaron?"})
        print("Report mode:", report["mode"], "fallback:", report.get("fallback_reason"))
        print("Agent mode:", agent["mode"], "fallback:", agent.get("fallback_reason"))
        print("Agent tokens (input/output/total):", agent["input_tokens"], agent["output_tokens"], agent["total_tokens"])
        assert report["mode"] == args.assistant_mode
        assert agent["mode"] == args.assistant_mode and agent["status"] == "answered"
    if args.origin:
        preflight = Request(base + "/api/v1/scouting-runs", method="OPTIONS", headers={
            "Origin": args.origin, "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        with urlopen(preflight, timeout=30) as response:
            assert response.headers.get("Access-Control-Allow-Origin") == args.origin
    print("OK: readiness, historical run, six sections, optional fallback and CORS preflight")


if __name__ == "__main__":
    main()

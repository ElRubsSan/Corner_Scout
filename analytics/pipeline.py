"""Audit raw before publishing compact, traceable Parquet datasets."""
import json
from collections import Counter
from datetime import date

import pandas as pd
from pydantic import BaseModel, Field

from analytics.io import data_dir, manifest, now, read_events, write_json

RULE = "scr15-v0.2-team-inclusive"
RESTARTS = {"Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off", "Penalty"}


class Event(BaseModel):
    event_id: str
    index: int
    period: int
    seconds: float = Field(ge=0)
    type: str
    team: str | None = None
    possession_team: str | None = None
    possession: int | None = None
    player: str | None = None
    pass_type: str | None = None
    location: list[float] | None = None
    end_location: list[float] | None = None
    height: str | None = None
    xg: float | None = Field(default=None, ge=0, le=1)


def name(value):
    return value.get("name") if isinstance(value, dict) else value


def normalize(raw: dict) -> Event:
    h, m, s = raw["timestamp"].split(":")
    passed = raw.get("pass") or {}
    shot = raw.get("shot") or {}
    return Event(event_id=raw["id"], index=raw["index"], period=raw["period"],
                 seconds=int(h)*3600 + int(m)*60 + float(s), type=name(raw["type"]),
                 team=name(raw.get("team")), possession_team=name(raw.get("possession_team")),
                 possession=raw.get("possession"), player=name(raw.get("player")),
                 pass_type=raw.get("pass_type") or name(passed.get("type")),
                 location=raw.get("location"), end_location=raw.get("pass_end_location") or passed.get("end_location"),
                 height=raw.get("pass_height") or name(passed.get("height")),
                 xg=raw.get("shot_statsbomb_xg") if raw.get("shot_statsbomb_xg") is not None else shot.get("statsbomb_xg"))


def sequences(events: list[Event], match_id: int) -> list[dict]:
    rows = []
    events = sorted(events, key=lambda e: (e.period, e.index))
    for i, corner in enumerate(events):
        if corner.type != "Pass" or corner.pass_type != "Corner":
            continue
        if corner.team is None or corner.possession_team != corner.team:
            raise ValueError(f"Invalid corner possession: {match_id}/{corner.event_id}")
        shots, restarts, changes = [], [], []
        valid_sequence = True
        reason, end_time = "period_end", corner.seconds
        last_possession = corner.possession
        for event in events[i+1:]:
            elapsed = event.seconds - corner.seconds
            if event.period != corner.period:
                reason = "period_end"
                break
            if elapsed > 15:
                reason, end_time = "15_seconds", corner.seconds + 15
                break
            if elapsed < 0:
                reason, valid_sequence = "invalid_timestamp", False
                break
            end_time = event.seconds
            if event.type == "Half End":
                reason = "period_end"
                break
            if event.possession_team is None:
                raise ValueError(f"Missing possession_team in sequence {match_id}/{event.event_id}")
            if event.possession_team != corner.team:
                reason = "possession_team_change"
                break
            if event.possession != last_possession:
                changes.append(event.event_id)
                last_possession = event.possession
            if event.pass_type in RESTARTS:
                restarts.append(event.event_id)
            if event.type == "Shot" and event.team == corner.team:
                if event.xg is None:
                    raise ValueError("Missing xG for attributed shot")
                shots.append(event)
        origin, dest = corner.location, corner.end_location
        if origin is None or dest is None:
            raise ValueError(f"Missing corner coordinates {match_id}/{corner.event_id}")
        length = ((dest[0]-origin[0])**2 + (dest[1]-origin[1])**2)**0.5
        spatial_valid = all(0 <= p[0] <= 120 and 0 <= p[1] <= 80 for p in (origin, dest))
        near_y = dest[1] if origin[1] < 40 else 80-dest[1]
        zone = "fuera_area" if dest[0] < 102 or not 18 <= dest[1] <= 62 else ("primer_poste" if near_y < 36 else "segundo_poste" if near_y > 44 else "centro")
        rows.append({"match_id": match_id, "event_id": corner.event_id, "index": corner.index,
                     "team": corner.team, "player": corner.player or "Desconocido", "period": corner.period,
                     "seconds": corner.seconds, "end_seconds": end_time, "end_reason": reason,
                     "x": origin[0], "y": origin[1], "end_x": dest[0], "end_y": dest[1],
                     "side": "y_bajo" if origin[1] < 40 else "y_alto", "height": corner.height or "Desconocida",
                     "delivery": "corto" if length <= 15 else "envio", "zone": zone,
                     "valid_sequence": valid_sequence, "spatial_valid": spatial_valid,
                     "shot_within_15s": bool(shots) if valid_sequence else None, "xg": sum(s.xg for s in shots) if valid_sequence else None,
                     "shot_ids": json.dumps([s.event_id for s in shots]), "restart_ids": json.dumps(restarts),
                     "possession_change_ids": json.dumps(changes), "rule_version": RULE})
    return rows


def load_matches() -> pd.DataFrame:
    df = pd.read_csv(data_dir() / "raw" / "matches_laliga_2015_16.csv")
    # statsbombpy exports names; provider-normalized export includes explicit IDs.
    for side in ("home", "away"):
        if f"{side}_team_{side}_team_name" in df:
            df[f"{side}_team"] = df[f"{side}_team_{side}_team_name"]
    columns = ["match_id", "match_date", "kick_off", "home_team", "away_team"]
    df = df[columns].copy()
    df["match_date"] = df.match_date.map(lambda d: date.fromisoformat(str(d)).isoformat())
    return df.sort_values(["match_date", "kick_off", "match_id"]).reset_index(drop=True)


def build() -> dict:
    root = data_dir()
    fingerprint = manifest()
    matches = load_matches()
    teams = sorted(set(matches.home_team) | set(matches.away_team))
    errors, audit, corners = [], [], []
    if len(matches) != 380 or matches.match_id.nunique() != 380 or len(teams) != 20:
        errors.append("Expected 380 unique matches and 20 teams")
    expected = set(matches.match_id.astype(str))
    actual = {p.name.split(".")[0] for p in (root / "raw" / "events").glob("*.jsonl.gz")}
    if actual != expected:
        errors.append("Event file coverage differs from match metadata")
    seen = set()
    for match in matches.itertuples():
        path = root / "raw" / "events" / f"{match.match_id}.jsonl.gz"
        if not path.exists():
            continue
        try:
            events = [normalize(row) for row in read_events(path)]
            ids = [e.event_id for e in events]
            if not events or len(set(ids)) != len(ids) or seen.intersection(ids):
                raise ValueError("Empty events or duplicate event IDs")
            seen.update(ids)
            if len({e.index for e in events}) != len(events):
                raise ValueError("Duplicate event indices")
            ordered = sorted(events, key=lambda e: (e.period, e.index))
            regressions = sum(a.period == b.period and a.seconds > b.seconds for a, b in zip(ordered, ordered[1:]))
            # Provider index remains authoritative. Regressions outside a corner
            # sequence are audited, not repaired or used to reject entire matches.
            invalid_coords = sum(any(not (0 <= p[0] <= 120 and 0 <= p[1] <= 80) for p in (e.location, e.end_location) if p is not None) for e in events)
            # Out-of-pitch events can describe balls out of play. Raw coordinates
            # remain intact; only invalid corner geometry blocks spatial metrics.
            extracted = sequences(ordered, match.match_id)
            corners.extend(extracted)
            audit.append({"match_id": match.match_id, "events": len(events), "corners": len(extracted),
                          "source_reordered": events != ordered, "regressions": regressions, "invalid_coords": invalid_coords})
        except (ValueError, KeyError, OSError) as exc:
            errors.append(f"match {match.match_id}: {exc}")
    quality = {"passed": not errors, "matches": len(matches), "teams": len(teams), "events": len(seen),
               "corners": len(corners), "errors": errors, "source_manifest_sha256": fingerprint,
               "processed_at": now(), "rule_version": RULE, "pipeline_version": "0.2.0", "audits": audit}
    write_json(root / "processed" / "quality.json", quality)
    if errors:
        raise ValueError(f"Data gate failed: {len(errors)} errors; see data/processed/quality.json")
    frame = pd.DataFrame(corners).merge(matches[["match_id", "match_date"]], on="match_id", validate="many_to_one")
    quality["excluded_sequences"] = int((~frame.valid_sequence).sum())
    quality["excluded_spatial"] = int((~frame.spatial_valid).sum())
    quality["timestamp_regressions"] = sum(a["regressions"] for a in audit)
    quality["out_of_bounds_events"] = sum(a["invalid_coords"] for a in audit)
    write_json(root / "processed" / "quality.json", quality)
    for df in (frame, matches):
        df["provider"] = "statsbomb_open_data"
        df["competition_id"], df["season_id"] = 11, 27
        df["processed_at"] = quality["processed_at"]
        df["source_manifest_sha256"] = fingerprint
    (root / "interim").mkdir(exist_ok=True)
    frame.to_parquet(root / "interim" / "corner_sequences.parquet", index=False)
    frame.to_parquet(root / "processed" / "corners.parquet", index=False)
    matches.to_parquet(root / "processed" / "matches.parquet", index=False)
    write_json(root / "manifests" / "quality-summary.json", {k: v for k, v in quality.items() if k != "audits"})
    return {k: v for k, v in quality.items() if k != "audits"}

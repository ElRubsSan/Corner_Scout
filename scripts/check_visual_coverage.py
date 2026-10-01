"""Report the real local image coverage of the canonical historical season."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict

from analytics.io import ROOT
from backend.repository import repository


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true",
                        help="Require the 20 badges and exactly 202 corner-taker portraits")
    parser.add_argument("--top-takers", action="store_true")
    options = parser.parse_args()
    inventory = json.loads((ROOT / "docs/visual-inventory.json").read_text(encoding="utf-8"))
    badges = ROOT / "frontend/public/media/clubs"
    portraits = ROOT / "frontend/public/media/players"
    found_clubs = [club for club in inventory["clubs"] if (badges / f"{club['id']}.png").is_file()]
    found_players = [player for player in inventory["players"] if (portraits / f"{player['id']}.webp").is_file()]
    corners = repository().rows("corners_engineered")
    takers = {int(row["player_id"]) for row in corners
              if row.get("player_id") is not None}
    found_takers = {int(player["id"]) for player in found_players if player["id"] in takers}
    files = {int(path.stem) for path in portraits.glob("*.webp") if path.stem.isdecimal()}
    print(f"Club badges: {len(found_clubs)}/{len(inventory['clubs'])}")
    print(f"Corner taker portraits: {len(found_takers)}/{len(takers)}")
    print(f"Other player portraits: {len(files - takers)} (not needed by the current interface)")
    print(f"Player identities in season: {len(inventory['players'])} (not all need photos)")
    if options.top_takers:
        club_takers: dict[str, Counter[tuple[int, str]]] = defaultdict(Counter)
        for row in corners:
            if row.get("player_id") is not None:
                club_takers[str(row["team"])][int(row["player_id"]), str(row["player"])] += 1
        for club, players in sorted(club_takers.items()):
            for (player_id, name), count in players.most_common(2):
                print(f"{club}: {player_id} {name} ({count}) - "
                      f"{'photo' if (portraits / f'{player_id}.webp').is_file() else 'missing'}")
    if options.require_complete and (len(found_clubs) != 20 or found_takers != takers or files != takers):
        raise SystemExit("Corner-taker visual catalog remains incomplete")


if __name__ == "__main__":
    main()

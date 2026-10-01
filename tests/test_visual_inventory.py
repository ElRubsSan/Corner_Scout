"""Presentation identities must reconcile with the canonical event source."""

import json
from pathlib import Path

from PIL import Image

from backend.repository import repository
from scripts.build_visual_inventory import build_inventory


ROOT = Path(__file__).resolve().parents[1]


def test_visual_identity_catalog_matches_verified_2015_16_artifacts():
    generated = build_inventory()
    published = json.loads((ROOT / "docs/visual-inventory.json").read_text(encoding="utf-8"))
    assert generated == published
    assert len(published["clubs"]) == 20
    assert len(published["players"]) == 539
    assert len({club["id"] for club in published["clubs"]}) == 20
    assert len({player["id"] for player in published["players"]}) == 539
    assert all(player["team_ids"] for player in published["players"])


def test_distributed_images_cover_only_real_corner_takers():
    takers = {int(row["player_id"]) for row in repository().rows("corners_engineered")
              if row.get("player_id") is not None}
    assert len(takers) == 202
    portraits = ROOT / "frontend/public/media/players"
    files = list(portraits.glob("*.webp"))
    assert len(files) == 202 and {int(path.stem) for path in files} == takers
    for path in files:
        with Image.open(path) as image:
            assert image.format == "WEBP" and image.size == (256, 256)
            image.verify()
    assert len(list((ROOT / "frontend/public/media/clubs").glob("*.png"))) == 20

    contributed = json.loads((ROOT / "docs/user-taker-photo-sources.json").read_text(encoding="utf-8"))
    assert len(contributed) == 75
    names = {int(player["id"]): player["name"] for player in json.loads(
        (ROOT / "docs/visual-inventory.json").read_text(encoding="utf-8"
    ))["players"]}
    assert all(int(key) in takers and names[int(key)] == item["name"]
               for key, item in contributed.items())

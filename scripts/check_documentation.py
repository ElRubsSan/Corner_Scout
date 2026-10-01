"""Check repository Markdown links without network access or changing files."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ("docs", "analytics", "backend", "contracts", "data/manifests")


def main() -> None:
    documents = list(ROOT.glob("*.md"))
    documents += [ROOT / name / "README.md" for name in ("data", "frontend", "artifacts")]
    for directory in DIRECTORIES:
        documents += list((ROOT / directory).rglob("*.md"))
    problems: list[str] = []
    checked = 0
    for document in sorted(set(documents)):
        if not document.is_file():
            continue
        # Examples inside fenced code are not Markdown links.
        text = re.sub(r"```.*?```", "", document.read_text(encoding="utf-8"), flags=re.S)
        for match in re.finditer(r"!?\[[^\]]*\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)", text):
            url = urlsplit(match.group(1))
            if url.scheme or url.netloc or not url.path:
                continue
            destination = (document.parent / unquote(url.path)).resolve()
            checked += 1
            if not destination.is_relative_to(ROOT) or not destination.exists():
                line = text.count("\n", 0, match.start()) + 1
                problems.append(f"{document.relative_to(ROOT)}:{line}: {match.group(1)}")
    if problems:
        raise SystemExit("Broken local Markdown links:\n" + "\n".join(problems))
    print(f"OK: {checked} local Markdown links in {len(set(documents))} documents")


if __name__ == "__main__":
    main()

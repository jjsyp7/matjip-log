#!/usr/bin/env python3
"""Preview option 1 scores; --apply backs up and updates places.json."""
import argparse
from collections import Counter
import copy
import datetime as dt
import json
import os
from pathlib import Path
import tempfile

from scoring import apply_scoring

ROOT = Path(__file__).resolve().parent


def rescore_places(places, as_of):
    if not isinstance(places, list) or not places:
        raise ValueError("places must be a nonempty list")
    if len({p["id"] for p in places}) != len(places):
        raise ValueError("duplicate place IDs")
    updated = copy.deepcopy(places)
    rows = [apply_scoring(p, as_of) for p in updated]
    for before, after in zip(places, updated):
        if "price" not in before or after["price"] != before["price"]:
            raise ValueError(f"price missing or changed: {before['id']}")
    return updated, rows


def apply_file(source, original, updated):
    """Validate before writing; keep the original backup on repeated runs."""
    content = (json.dumps(updated, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    if json.loads(original) == updated:
        return False
    backup = source.with_name("places.bak_rescore.json")
    if source.is_symlink() or (backup.exists() and backup.samefile(source)):
        raise ValueError("input and backup must be separate regular files")
    if source.read_bytes() != original:
        raise RuntimeError("input changed during calculation")
    if backup.exists():
        if backup.read_bytes() != original:
            raise ValueError("backup already exists with different data; preserve it before another update")
    else:
        with backup.open("xb") as f:
            f.write(original)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=source.parent, prefix=".rescore-", delete=False) as f:
            temporary = Path(f.name)
            f.write(content)
        if json.loads(temporary.read_bytes()) != updated:
            raise RuntimeError("written JSON validation failed")
        if source.read_bytes() != original:
            raise RuntimeError("input changed before replacement")
        temporary.chmod(source.stat().st_mode & 0o777)
        os.replace(temporary, source)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--input", type=Path, default=ROOT / "places.json")
    parser.add_argument("--as-of", type=dt.date.fromisoformat, default=dt.date.today())
    args = parser.parse_args()
    source = args.input.absolute()
    original = source.read_bytes()
    places = json.loads(original)
    if source == ROOT / "places.json" and len(places) != 685:
        parser.error("expected 685 places")
    updated, rows = rescore_places(places, args.as_of)
    changed = sum(r["delta"] != 0 for r in rows)
    print(f"{'반영' if args.apply else '미리보기'} {len(rows)}곳 | 종합 점수 변경 {changed}곳")
    print("점수 변동:", dict(sorted(Counter(r["delta"] for r in rows).items())))
    print("기본 표시:", sum(r["old_visible"] for r in rows), "→", sum(r["new_visible"] for r in rows))
    print("신뢰도:", dict(Counter(r["confidence"] or "없음" for r in rows)))
    if args.apply:
        print("저장 완료" if apply_file(source, original, updated) else "변경 없음")


if __name__ == "__main__":
    main()

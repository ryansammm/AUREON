"""Genre-config completeness: every genre file declares its groove intent.

Each file in ``config/genres/`` must be auditable on its own, without
running the merge logic:

- A genre with a groove must author ``groove_profile`` (a profile id from
  ``config/grooves/``) *and* ``bass_drum_interlock``.
- A genre that intentionally has no groove (e.g. ambient textures) must
  say so via ``groove_intentionally_default`` with a non-empty reason,
  and must not keep a ``groove_profile``.

Sub-genres inherit keys from their parent via ``_merge_overrides``, so a
child of a grooved parent would get a groove for free — but the file
still has to declare its own intent explicitly.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENRES_DIR = ROOT / "config" / "genres"

INTERLOCK_MODES = {"lock", "syncopate", "independent"}


def _all_genre_files() -> list:
    return sorted(GENRES_DIR.glob("*.json"))


def _load(name: str) -> dict:
    return json.loads((GENRES_DIR / name).read_text(encoding="utf-8"))


def test_every_genre_file_is_valid_json():
    for path in _all_genre_files():
        json.loads(path.read_text(encoding="utf-8"))


def test_every_genre_authors_a_groove_or_declares_it_default():
    missing = []
    for path in _all_genre_files():
        config = _load(path.name)
        profile = config.get("groove_profile")
        reason = config.get("groove_intentionally_default")
        if profile or reason:
            continue
        missing.append(path.name)
    assert not missing, (
        "genres neither author a groove_profile nor declare "
        f"groove_intentionally_default: {', '.join(missing)}"
    )


def test_groove_profile_must_be_a_non_empty_string():
    for path in _all_genre_files():
        profile = _load(path.name).get("groove_profile")
        if profile is None:
            continue
        assert isinstance(profile, str) and profile.strip(), (
            f"{path.name}: groove_profile must be a non-empty string"
        )
        groove_file = ROOT / "config" / "grooves" / f"{profile}.json"
        assert groove_file.is_file(), (
            f"{path.name}: groove_profile '{profile}' has no matching "
            f"groove file at {groove_file.relative_to(ROOT)}"
        )


def test_grooved_genres_author_bass_drum_interlock():
    bad = []
    for path in _all_genre_files():
        config = _load(path.name)
        if not config.get("groove_profile"):
            continue
        interlock = config.get("bass_drum_interlock")
        if not (
            isinstance(interlock, dict)
            and interlock.get("mode") in INTERLOCK_MODES
        ):
            bad.append(path.name)
    assert not bad, (
        "grooved genres without a valid bass_drum_interlock: "
        f"{', '.join(bad)}"
    )


def test_reason_genres_must_not_keep_a_groove_profile():
    bad = []
    for path in _all_genre_files():
        config = _load(path.name)
        reason = config.get("groove_intentionally_default")
        if not reason:
            continue
        if config.get("groove_profile") is not None:
            bad.append(path.name)
    assert not bad, (
        "genres that declare groove_intentionally_default must not also "
        f"set groove_profile: {', '.join(bad)}"
    )


def test_reason_must_be_a_non_empty_string():
    for path in _all_genre_files():
        reason = _load(path.name).get("groove_intentionally_default")
        if reason is None:
            continue
        assert isinstance(reason, str) and reason.strip(), (
            f"{path.name}: groove_intentionally_default must be a "
            "non-empty string"
        )

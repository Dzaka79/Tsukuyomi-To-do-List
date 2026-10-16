"""Unit tests for logic.py — the non-UI acceptance criteria from SPEC.md §4."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

import logic
from logic import (
    ASSETS_DIR,
    CHARACTERS,
    MAX_TITLE_LENGTH,
    MISSION_TYPES,
    MSG_ADDED,
    MSG_DONE,
    MSG_START,
    Character,
    Task,
)


@pytest.fixture
def data_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "tasks.json"


# ---------------------------------------------------------------------------
# Message constants (SPEC §2.4)
# ---------------------------------------------------------------------------


def test_message_constants_match_spec_exactly():
    assert MSG_START == "Let's finish the tasks one by one~"
    assert MSG_ADDED == "One more task, huh? Don't lose hope, let's do it together!"
    assert MSG_DONE == "Yaay~! A task is done, a celebration must begun!"


# ---------------------------------------------------------------------------
# Task model (SPEC §3.1)
# ---------------------------------------------------------------------------


def test_task_json_round_trip():
    task = Task(
        id="abc123", title="Read chapter 5", done=True, created_at="2026-10-16T21:08:03"
    )
    assert Task.from_json(task.to_json()) == task


@pytest.mark.parametrize(
    "bad",
    [
        "not a dict",
        {"title": "x", "done": False, "created_at": "t"},
        {"id": "x", "done": False, "created_at": "t"},
        {"id": "x", "title": "   ", "done": False, "created_at": "t"},
        {"id": "x", "title": "t", "done": "yes", "created_at": "t"},
        {"id": "x", "title": "t", "done": False, "created_at": 5},
        {"id": "", "title": "t", "done": False, "created_at": "t"},
    ],
)
def test_task_from_json_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        Task.from_json(bad)


def test_from_json_strips_title():
    task = Task.from_json(
        {"id": "x", "title": "  padded  ", "done": False, "created_at": "t"}
    )
    assert task.title == "padded"


# ---------------------------------------------------------------------------
# Store load/save (SPEC §2.8, §3.3)
# ---------------------------------------------------------------------------


def test_default_store_shape():
    store = logic.default_store()
    assert store == {"version": 1, "missions": {"main": [], "side": []}}


def test_missing_file_returns_default(data_path):
    assert logic.load_store(data_path) == logic.default_store()
    assert not data_path.exists()


def test_corrupt_json_returns_default(data_path):
    data_path.parent.mkdir(parents=True)
    data_path.write_text("{not json", encoding="utf-8")
    assert logic.load_store(data_path) == logic.default_store()


@pytest.mark.parametrize(
    "payload",
    [
        {"version": 1},  # no missions key
        {"missions": {"main": []}},  # missing side
        {"missions": {"main": [], "side": "nope"}},  # wrong type
        {"missions": {"main": [{"id": 1}], "side": []}},  # invalid task entry
    ],
)
def test_bad_schema_returns_default(data_path, payload):
    data_path.parent.mkdir(parents=True)
    data_path.write_text(json.dumps(payload), encoding="utf-8")
    assert logic.load_store(data_path) == logic.default_store()


def test_save_load_round_trip(data_path):
    store = logic.default_store()
    now = datetime(2026, 10, 16, 21, 8, 3)
    task = logic.add_task(store, "main", "Task 1", now=now)
    logic.add_task(store, "side", "Task 2")
    logic.save_store(store, data_path)

    loaded = logic.load_store(data_path)
    assert loaded["missions"]["main"] == [task]
    assert [t.title for t in loaded["missions"]["side"]] == ["Task 2"]
    assert loaded["missions"]["main"][0].created_at == "2026-10-16T21:08:03"


def test_save_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "dir" / "tasks.json"
    logic.save_store(logic.default_store(), path)
    assert path.is_file()


# ---------------------------------------------------------------------------
# add_task (SPEC §2.1)
# ---------------------------------------------------------------------------


def test_add_task_appends_last():
    store = logic.default_store()
    first = logic.add_task(store, "main", "Task 1")
    second = logic.add_task(store, "main", "Task 2")
    assert [t.title for t in logic.get_tasks(store, "main")] == ["Task 1", "Task 2"]
    assert first.id != second.id


def test_add_task_fields():
    store = logic.default_store()
    task = logic.add_task(
        store, "main", "Read chapter 5", now=datetime(2026, 10, 16, 21, 8, 3)
    )
    assert task is not None
    assert len(task.id) == 32 and int(task.id, 16) >= 0  # uuid4().hex
    assert task.done is False
    assert task.created_at == "2026-10-16T21:08:03"


def test_add_task_strips_title():
    store = logic.default_store()
    task = logic.add_task(store, "main", "  padded  ")
    assert task.title == "padded"


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_blank_title_rejected_no_state_change(blank):
    store = logic.default_store()
    assert logic.add_task(store, "main", blank) is None
    assert logic.get_tasks(store, "main") == []


def test_non_string_title_rejected():
    store = logic.default_store()
    assert logic.add_task(store, "main", None) is None
    assert logic.add_task(store, "main", 42) is None
    assert logic.get_tasks(store, "main") == []


def test_too_long_title_rejected():
    store = logic.default_store()
    assert logic.add_task(store, "main", "x" * (MAX_TITLE_LENGTH + 1)) is None
    assert logic.get_tasks(store, "main") == []


def test_max_length_title_accepted():
    store = logic.default_store()
    assert logic.add_task(store, "main", "x" * MAX_TITLE_LENGTH) is not None


def test_unknown_mission_raises():
    store = logic.default_store()
    with pytest.raises(KeyError):
        logic.add_task(store, "boss", "Task")
    with pytest.raises(KeyError):
        logic.get_tasks(store, "boss")


def test_duplicate_titles_allowed():
    store = logic.default_store()
    logic.add_task(store, "main", "Same")
    logic.add_task(store, "main", "Same")
    assert len(logic.get_tasks(store, "main")) == 2


def test_sections_are_independent():
    store = logic.default_store()
    logic.add_task(store, "main", "Main only")
    assert logic.get_tasks(store, "side") == []


# ---------------------------------------------------------------------------
# toggle / remove (SPEC §2.2, §2.3)
# ---------------------------------------------------------------------------


def test_toggle_flips_done():
    store = logic.default_store()
    task = logic.add_task(store, "main", "Task 1")
    assert logic.toggle_task(store, "main", task.id).done is True
    assert logic.toggle_task(store, "main", task.id).done is False


def test_toggle_unknown_mission_raises():
    store = logic.default_store()
    with pytest.raises(KeyError):
        logic.toggle_task(store, "nope", "some-id")


def test_toggle_unknown_task_raises():
    store = logic.default_store()
    with pytest.raises(KeyError):
        logic.toggle_task(store, "main", "missing-id")


def test_remove_task_returns_and_removes():
    store = logic.default_store()
    task = logic.add_task(store, "main", "Task 1")
    logic.add_task(store, "main", "Task 2")
    removed = logic.remove_task(store, "main", task.id)
    assert removed == task
    assert [t.title for t in logic.get_tasks(store, "main")] == ["Task 2"]


def test_remove_unknown_task_raises():
    store = logic.default_store()
    with pytest.raises(KeyError):
        logic.remove_task(store, "side", "missing-id")


def test_remove_unknown_mission_raises_before_lookup():
    store = logic.default_store()
    with pytest.raises(KeyError):
        logic.remove_task(store, "nope", "any-id")


def test_toggle_and_remove_work_in_side_section():
    store = logic.default_store()
    task = logic.add_task(store, "side", "Side task")
    assert logic.toggle_task(store, "side", task.id).done is True
    logic.remove_task(store, "side", task.id)
    assert logic.get_tasks(store, "side") == []


# ---------------------------------------------------------------------------
# Daily character rotation (SPEC §2.9, §3.2)
# ---------------------------------------------------------------------------


def test_roster_size_keys_and_quotes():
    assert [c.key for c in CHARACTERS] == ["yachiyo", "iroha", "kaguya"]
    quotes = {c.key: c.quote for c in CHARACTERS}
    assert quotes["yachiyo"] == (
        "Yaoyoro~! Let's keep working hard today, and rest harder afterwards!"
    )
    assert quotes["iroha"] == "Ugh, so much to do.. Let's just get this over with"
    assert quotes["kaguya"] == (
        "Kaguyaho-! Let's have fun together and defeat these annoying homeworks!!"
    )


def test_each_character_has_three_photos_in_assets_dir():
    for character in CHARACTERS:
        assert len(character.photos) == 3
        for photo in character.photos:
            path = Path(photo)
            assert path.parent == ASSETS_DIR
            assert path.name.startswith(character.key)


def test_daily_pick_deterministic_within_a_day():
    day = date(2026, 10, 16)
    assert logic.daily_pick(day) == logic.daily_pick(day)


def test_daily_pick_covers_all_characters():
    picks = {
        logic.daily_pick(date(2026, 1, 1) + timedelta(days=i))[0].key
        for i in range(120)
    }
    assert picks == {"yachiyo", "iroha", "kaguya"}


def test_daily_pick_photo_belongs_to_character():
    for i in range(60):
        char, photo = logic.daily_pick(date(2026, 2, 1) + timedelta(days=i))
        assert photo in char.photos


def test_daily_pick_returns_character_from_roster():
    for i in range(30):
        char, _ = logic.daily_pick(date(2027, 5, 1) + timedelta(days=i))
        assert char in CHARACTERS


def test_today_returns_current_date():
    assert abs((date.today() - logic.today()).days) <= 1


# ---------------------------------------------------------------------------
# Character assets (SPEC §2.10, §3.2)
# ---------------------------------------------------------------------------

FAKE_CHARACTERS = (
    Character(
        key="ghost",
        name="Ghost",
        quote="boo",
        photos=("does/not/exist_1.jpg", "does/not/exist_2.jpg"),
    ),
)


def test_missing_photos_lists_all_absent_paths():
    assert logic.missing_photos(FAKE_CHARACTERS) == [
        "does/not/exist_1.jpg",
        "does/not/exist_2.jpg",
    ]


def test_ensure_assets_raises_listing_paths():
    with pytest.raises(FileNotFoundError) as exc:
        logic.ensure_assets(FAKE_CHARACTERS)
    message = str(exc.value)
    assert "does/not/exist_1.jpg" in message
    assert "does/not/exist_2.jpg" in message


@pytest.mark.skipif(
    not ASSETS_DIR.is_dir(),
    reason="character photos not saved yet (see SPEC.md §3.2 asset inventory)",
)
@pytest.mark.parametrize("photo", logic.roster_photos())
def test_roster_photo_exists(photo):
    assert Path(photo).is_file(), f"missing roster photo: {photo}"


# ---------------------------------------------------------------------------
# Formatting helpers (SPEC §2.5, §2.7)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "seconds,expected",
    [(0, "00:00:00"), (968, "00:16:08"), (3661, "01:01:01"), (359999, "99:59:59")],
)
def test_format_elapsed(seconds, expected):
    assert logic.format_elapsed(seconds) == expected


def test_format_calendar():
    assert logic.format_calendar(date(2026, 10, 16)) == ("16", "October, 2026")


def test_format_clock():
    assert logic.format_clock(datetime(2026, 10, 16, 21, 8)) == "21:08"


def test_mission_types_contract():
    assert MISSION_TYPES == ("main", "side")

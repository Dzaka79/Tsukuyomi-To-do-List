"""Pure business logic for Tsukuyomi To-do-List.

No Streamlit imports here — everything is unit-testable with plain pytest.
See SPEC.md for the contract this module implements.
"""

from __future__ import annotations

import json
import random
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

MISSION_TYPES = ("main", "side")
MAX_TITLE_LENGTH = 200
STORE_VERSION = 1
DEFAULT_DATA_PATH = Path("data/tasks.json")
ASSETS_DIR = Path("assets/characters")

MSG_START = "Let's finish the tasks one by one~"
MSG_ADDED = "One more task, huh? Don't lose hope, let's do it together!"
MSG_DONE = "Yaay~! A task is done, a celebration must begun!"


@dataclass
class Task:
    id: str
    title: str
    done: bool = False
    created_at: str = ""

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "done": self.done,
            "created_at": self.created_at,
        }

    @classmethod
    def from_json(cls, data: dict) -> "Task":
        if not isinstance(data, dict):
            raise ValueError("task must be a JSON object")
        id_ = data.get("id")
        title = data.get("title")
        done = data.get("done")
        created_at = data.get("created_at")
        if not isinstance(id_, str) or not id_:
            raise ValueError("task id must be a non-empty string")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("task title must be a non-empty string")
        if not isinstance(done, bool):
            raise ValueError("task done must be a boolean")
        if not isinstance(created_at, str):
            raise ValueError("task created_at must be a string")
        return cls(id=id_, title=title.strip(), done=done, created_at=created_at)


@dataclass(frozen=True)
class Character:
    key: str
    name: str
    quote: str
    photos: tuple[str, ...]


CHARACTERS: tuple[Character, ...] = (
    Character(
        key="yachiyo",
        name="Yachiyo",
        quote="Yaoyoro~! Let's keep working hard today, and rest harder afterwards!",
        photos=(
            str(ASSETS_DIR / "yachiyo_1.jpg"),
            str(ASSETS_DIR / "yachiyo_2.jpg"),
            str(ASSETS_DIR / "yachiyo_3.jpg"),
        ),
    ),
    Character(
        key="iroha",
        name="Iroha",
        quote="Ugh, so much to do.. Let's just get this over with",
        photos=(
            str(ASSETS_DIR / "iroha_1.jpg"),
            str(ASSETS_DIR / "iroha_2.jpg"),
            str(ASSETS_DIR / "iroha_3.jpg"),
        ),
    ),
    Character(
        key="kaguya",
        name="Kaguya",
        quote="Kaguyaho-! Let's have fun together and defeat these annoying homeworks!!",
        photos=(
            str(ASSETS_DIR / "kaguya_1.jpg"),
            str(ASSETS_DIR / "kaguya_2.jpg"),
            str(ASSETS_DIR / "kaguya_3.jpg"),
        ),
    ),
)


def today() -> date:
    """Today's date; thin wrapper so tests can monkeypatch it."""
    return date.today()


def daily_pick(day: date) -> tuple[Character, str]:
    """Deterministically pick the character and photo shown on ``day``.

    Same date always yields the same pick; the pick rolls over when the
    date changes (SPEC §2.9).
    """
    rng = random.Random(f"tsukuyomi|{day.isoformat()}")
    character = rng.choice(CHARACTERS)
    photo = rng.choice(character.photos)
    return character, photo


def default_store() -> dict:
    return {
        "version": STORE_VERSION,
        "missions": {mission: [] for mission in MISSION_TYPES},
    }


def _check_mission(mission: str) -> None:
    if mission not in MISSION_TYPES:
        raise KeyError(f"unknown mission type: {mission!r}")


def load_store(path: Path = DEFAULT_DATA_PATH) -> dict:
    """Load the task store; missing or malformed files yield the default shape."""
    path = Path(path)
    if not path.is_file():
        return default_store()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        missions = raw["missions"]
        store = default_store()
        for mission in MISSION_TYPES:
            store["missions"][mission] = [
                Task.from_json(entry) for entry in missions[mission]
            ]
        return store
    except (OSError, ValueError, KeyError, TypeError):
        return default_store()


def save_store(store: dict, path: Path = DEFAULT_DATA_PATH) -> None:
    """Persist the store as JSON, creating parent directories as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": STORE_VERSION,
        "missions": {
            mission: [task.to_json() for task in store["missions"][mission]]
            for mission in MISSION_TYPES
        },
    }
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def get_tasks(store: dict, mission: str) -> list[Task]:
    _check_mission(mission)
    return store["missions"][mission]


def add_task(
    store: dict,
    mission: str,
    title: str,
    *,
    now: datetime | None = None,
) -> Task | None:
    """Append a task; returns None (no state change) if the title is rejected.

    A title is rejected when it is not a string, blank after stripping, or
    longer than MAX_TITLE_LENGTH. Unknown mission raises KeyError.
    """
    _check_mission(mission)
    if not isinstance(title, str):
        return None
    title = title.strip()
    if not title or len(title) > MAX_TITLE_LENGTH:
        return None
    stamp = (now if now is not None else datetime.now()).isoformat(
        timespec="seconds"
    )
    task = Task(id=uuid.uuid4().hex, title=title, done=False, created_at=stamp)
    store["missions"][mission].append(task)
    return task


def _find_task(store: dict, mission: str, task_id: str) -> Task:
    _check_mission(mission)
    for task in store["missions"][mission]:
        if task.id == task_id:
            return task
    raise KeyError(f"no task {task_id!r} in mission {mission!r}")


def toggle_task(store: dict, mission: str, task_id: str) -> Task:
    task = _find_task(store, mission, task_id)
    task.done = not task.done
    return task


def remove_task(store: dict, mission: str, task_id: str) -> Task:
    task = _find_task(store, mission, task_id)
    store["missions"][mission].remove(task)
    return task


def roster_photos(characters: tuple[Character, ...] = CHARACTERS) -> list[str]:
    return [photo for character in characters for photo in character.photos]


def missing_photos(characters: tuple[Character, ...] = CHARACTERS) -> list[str]:
    return [photo for photo in roster_photos(characters) if not Path(photo).is_file()]


def ensure_assets(characters: tuple[Character, ...] = CHARACTERS) -> None:
    """Fail fast (SPEC §2.10) listing every missing character photo."""
    missing = missing_photos(characters)
    if missing:
        raise FileNotFoundError(
            "Missing character photos: " + ", ".join(missing)
        )


def format_clock(moment: datetime) -> str:
    return moment.strftime("%H:%M")


def format_calendar(day: date) -> tuple[str, str]:
    """(day number, 'Month, YYYY') for the sidebar calendar."""
    return str(day.day), day.strftime("%B, %Y")


def format_elapsed(seconds: int) -> str:
    """Working-time counter as zero-padded 'HH:MM:SS'."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

# SPEC.md — Tsukuyomi To-do-List

Single-user to-do app: Python + Streamlit (UI) + pytest (tests).
Run: `streamlit run ui-app.py` · Test: `python -m pytest` · Build exe: see AGENTS.md.

## 1. UI layout (template: first screenshot)

**Sidebar** (dark navy, collapsible via native arrow "<"):
- live clock, `HH:MM`
- static calendar: big day number + `Month, YYYY` (today's date, NOT interactive)
- label `Shortcut:` + two buttons `Main Missions`, `Side Missions` (no prefix)

**Main area**, top → bottom:
0. banner image spanning the content width (`assets/banner.jpg` or `.png`; skipped silently when absent)
1. `# Welcome to Tsukuyomi To-do-List!` + subtitle `Let's do our best again today!`
2. Character card: square photo with rounded corners (daily pick, §2.9), beside it:
   `Today, you meet` / **`<name> !`** (e.g. `Yachiyo !`) / `“<quote>”`
3. **Message box**: one rounded container; shows the text of the last triggered event (§2.4)
4. `Working time:` + `HH:MM:SS` elapsed since session start, ticks every 1 s
5. `Main Missions` section: heading + `⊕` add toggle; each row = `[checkbox] [title] [×]`
6. `Side Missions` section: identical

Dark navy theme approximating the template via `.streamlit/config.toml` + minimal CSS (rounded cards, message box).

## 2. Features

**2.1 Two mission types** — `main` and `side` are independent lists. `⊕` per section reveals a text input; submitting appends the task to the END of that section's list. Titles are trimmed; empty/whitespace-only titles are rejected (no state change, no message change). Duplicate titles allowed.

**2.2 Complete / uncheck** — checkbox toggles `done`; state persists to disk. Unchecking is allowed.

**2.3 Delete** — `×` removes the task regardless of `done` state.

**2.4 Message box** — single box, text replaced by the last triggered event:

| Event | Exact text |
|---|---|
| First render of a session (app start) | `Let's finish the tasks one by one~` |
| A task is added | `One more task, huh? Don't lose hope, let's do it together!` |
| A task is checked as done | `Yaay~! A task is done, a celebration must begun!` |

Only these three events change it. Unchecking or deleting leaves the message unchanged. A new session always resets to the start message.

**2.5 Sidebar clock & calendar** — clock is today's time `HH:MM`; calendar shows today's day number and `Month, YYYY` (static, not a date picker).

**2.6 Shortcuts** — clicking a shortcut scrolls the main view to that section (implemented via a `<div id="main-missions">` anchor plus a same-origin `st.iframe` JS `scrollIntoView`; consumed from the `jump_target` session key in the same rerun).

**2.7 Working-time timer** — counts up from first render of the session, format `HH:MM:SS`, refreshed every second with `st.fragment(run_every=1)` (AppTest does not tick it — tests assert format only).

**2.8 Persistence** — tasks live in `data/tasks.json` (created on first save). On startup: missing file → empty lists; malformed file → start empty, do NOT crash. Message text and working-time start are session-only, never persisted. The daily character pick is NOT persisted (§2.9 is stateless).

**2.9 Daily character rotation** — the app shows one of three characters each day: **Yachiyo, Iroha, Kaguya**.
- Character (name + quote) AND photo are chosen **once per day** and stay fixed for the whole day; both re-roll when the date changes.
- Selection is **stateless and deterministic**: `daily_pick(today)` seeds `random.Random(f"tsukuyomi|{date.isoformat()}")`, then `choice(CHARACTERS)` and `choice(character.photos)`. Same date ⇒ same character + same photo (any session, any rerun); evaluated fresh on every full rerun, so it rolls over at midnight automatically.
- The date comes through a thin `characters.today()` wrapper so tests can monkeypatch a fixed date.

**2.10 Character assets** — all 9 photos are required under `assets/characters/` (§3.2); a missing file fails fast at startup with an error listing the missing path(s).

## 3. Data structure

### 3.1 Task model (`logic.py`, Streamlit-free)

```python
MISSION_TYPES = ("main", "side")          # the only valid section keys

@dataclass
class Task:
    id: str          # uuid4().hex, assigned on creation
    title: str       # stripped, 1..200 chars
    done: bool = False
    created_at: str  # datetime.now().isoformat(timespec="seconds")

    def to_json(self) -> dict: ...
    @classmethod
    def from_json(cls, d: dict) -> "Task": ...
```

`logic.py` owns all mutations (`load / save / add / toggle / delete`) with **zero Streamlit imports** so it is unit-testable without the UI.

### 3.2 Character roster (`logic.py`, also Streamlit-free)

```python
@dataclass(frozen=True)
class Character:
    key: str                    # "yachiyo" | "iroha" | "kaguya"
    name: str
    quote: str
    photos: tuple[str, ...]     # exactly 3 asset paths

CHARACTERS: tuple[Character, ...] = (
    Character("yachiyo", "Yachiyo",
              "Yaoyoro~! Let's keep working hard today, and rest harder afterwards!",
              ("assets/characters/yachiyo_1.jpg", "yachiyo_2.jpg", "yachiyo_3.jpg")),
    Character("iroha", "Iroha",
              "Ugh, so much to do.. Let's just get this over with",
              ("assets/characters/iroha_1.jpg", "iroha_2.jpg", "iroha_3.jpg")),
    Character("kaguya", "Kaguya",
              "Kaguyaho-! Let's have fun together and defeat these annoying homeworks!!",
              ("assets/characters/kaguya_1.jpg", "kaguya_2.jpg", "kaguya_3.jpg")),
)

def today() -> date: ...                    # thin wrapper, monkeypatchable in tests
def daily_pick(day: date) -> tuple[Character, str]: ...
    # rng = random.Random(f"tsukuyomi|{day.isoformat()}")
```

(The Yachiyo quote here supersedes the older template screenshot's wording.)

**Asset inventory** — user must save the provided images to these paths (extensions must match the actual files, `.jpg` or `.png`; roster lists exact paths). The optional banner goes to `assets/banner.jpg` (or `.png`).

| key | photos (in given order) |
|---|---|
| yachiyo | `yachiyo_1` = earlier-provided portrait, `yachiyo_2` = bun-hair night-city, `yachiyo_3` = laughing |
| iroha | `iroha_1` = blue-eyed close-up, `iroha_2` = blue jacket, `iroha_3` = green-eyed night |
| kaguya | `kaguya_1` = hugging cat, `kaguya_2` = hands framing face, `kaguya_3` = cat headphones |

### 3.3 On-disk file `data/tasks.json` (tasks only — no character state)

```json
{
  "version": 1,
  "missions": {
    "main": [
      {"id": "9f2c1a7e...", "title": "Task 1",
       "done": false, "created_at": "2026-10-16T21:08:03"}
    ],
    "side": []
  }
}
```

### 3.4 Session state (transient)

| key | type | purpose |
|---|---|---|
| `message` | `str` | current message-box text |
| `working_start` | `datetime` | start of the working-time counter |
| `jump_target` | `str \| None` | set by shortcut buttons (`"main"` / `"side"`) |
| `show_input_main`, `show_input_side` | `bool` | `⊕` toggle per section |

## 4. Acceptance criteria (example test cases)

UI tests use `streamlit.testing.v1.AppTest`; JSON paths are redirected to `tmp_path` via monkeypatch. Selector details (element keys/labels) are finalized at implementation — the assertions are the contract.

```python
# helpers
def page_text(at) -> str:
    return "\n".join([m.value for m in at.markdown] + [i.value for i in at.info])


def test_startup_message(app):                      # AC1: start text on first render
    at = app.run()
    assert "Let's finish the tasks one by one~" in page_text(at)


def test_character_card_shows_todays_pick(app, monkeypatch, fixed_date):
    """AC2: card shows name+quote+photo of daily_pick(today)."""
    monkeypatch.setattr("tsukuyomi.characters.today", lambda: fixed_date)
    at = app.run()
    char, photo = daily_pick(fixed_date)
    assert char.name in page_text(at)
    assert char.quote in page_text(at)
    assert at.image[0].path == photo               # selector illustrative


def test_daily_pick_stable_within_a_day():          # AC3: same date → identical pick
    day = date(2026, 10, 16)
    assert daily_pick(day) == daily_pick(day)


def test_daily_pick_covers_all_characters():        # AC4: roster rotates (deterministic seed)
    picks = {daily_pick(date(2026, 1, 1) + timedelta(days=i))[0].key
             for i in range(120)}
    assert picks == {"yachiyo", "iroha", "kaguya"}


def test_daily_pick_photo_belongs_to_character():   # AC5: photo is one of the 3
    for i in range(60):
        char, photo = daily_pick(date(2026, 2, 1) + timedelta(days=i))
        assert photo in char.photos


@pytest.mark.parametrize("path", all_roster_photos())
def test_photo_asset_exists(path):                  # AC6: all 9 files present
    assert Path(path).is_file()


def test_add_main_mission(app):                     # AC7: add → list + add-message + JSON
    at = app.run()
    at.text_input(key="input_main").set_value("Read chapter 5").run()
    assert "Read chapter 5" in page_text(at)
    assert "One more task, huh? Don't lose hope, let's do it together!" in page_text(at)
    assert len(load_json(app.data_path)["missions"]["main"]) == 1


def test_add_side_mission_goes_to_side_list(app):   # AC8: sections are independent
    ...
    assert data["missions"]["side"] and not data["missions"]["main"]


def test_blank_title_rejected(app):                 # AC9: whitespace-only input is a no-op
    at = app.run()
    at.text_input(key="input_main").set_value("   ").run()
    assert data["missions"]["main"] == []
    assert "Let's finish the tasks one by one~" in page_text(at)   # message unchanged


def test_check_done_shows_celebration(app):         # AC10: checking → celebration + JSON done
    at = add_task_and_check(app, "Task 1")
    assert "Yaay~! A task is done, a celebration must begun!" in page_text(at)
    assert load_json(app.data_path)["missions"]["main"][0]["done"] is True


def test_uncheck_keeps_message(app):                # AC11: uncheck flips done, message stays
    at = ...  # check then uncheck
    assert task["done"] is False
    assert "Yaay~!" in page_text(at)                # unchanged


def test_delete_removes_task(app):                  # AC12: × removes row and JSON entry
    ...
    assert "Task 1" not in page_text(at)
    assert load_json(app.data_path)["missions"]["main"] == []


def test_tasks_survive_restart(app_factory):        # AC13: JSON persistence across sessions
    app_factory().run().text_input(key="input_main").set_value("Persist me").run()
    at2 = app_factory().run()                       # fresh AppTest, same data file
    assert "Persist me" in page_text(at2)
    assert "Let's finish the tasks one by one~" in page_text(at2)   # AC14: message resets


def test_working_time_format(app):                  # AC15: timer matches HH:MM:SS
    import re
    assert re.search(r"\b\d{2}:\d{2}:\d{2}\b", page_text(app.run()))


def test_sidebar_date_and_clock(app, frozen_now):   # AC16: day number + "Month, YYYY" + "HH:MM"
    at = app.run()
    assert str(frozen_now.day) in page_text(at)
    assert frozen_now.strftime("%B, %Y") in page_text(at)


def test_shortcut_buttons(app):                     # AC17: both shortcuts exist and set target
    at = app.run()
    at.button(key="shortcut_main").run()
    assert at.session_state["jump_target"] == "main"


def test_corrupt_json_does_not_crash(app):          # AC18: malformed file → empty lists, app runs
    app.data_path.write_text("{not json", encoding="utf-8")
    at = app.run()                                  # no exception
    assert load_json(app.data_path)["missions"]["main"] == []
```

The non-UI parts are implemented in `test_logic.py`: message constants, JSON round-trip, add-appends-last, toggle/delete by id, unknown section → `KeyError`, missing/corrupt file → default shape, daily-pick determinism/coverage/photo membership, asset checks, and formatting helpers.

## 5. Project layout

```
logic.py                 # ALL pure logic (Task, store, characters, messages, formatting) — no Streamlit
test_logic.py            # pytest unit tests for logic.py
ui-app.py                # Streamlit UI entrypoint (implements §1–§2; imports logic)
launcher.py              # starts the server + opens a browser; PyInstaller entry point
.streamlit/config.toml   # dark navy theme for `streamlit run ui-app.py`
assets/characters/       # 9 photos: {yachiyo,iroha,kaguya}_1..3 (user-provided)
data/tasks.json          # generated at runtime, relative to the working directory
dist/Tsukuyomi TDL - Login.exe   # frozen single-file build of launcher.py (console hidden,
                                 # bundles assets/ and mirrors them beside the exe on first
                                 # run; logs to tsukuyomi_tdl.log beside the exe)
```

## 6. Non-goals

Editing a task's title after creation, due dates, priorities, multi-user/cloud sync, auth, notifications, offline PWA, mobile-specific layout, manual re-roll of today's character, customizing the character roster.

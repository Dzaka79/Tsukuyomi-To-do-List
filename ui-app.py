from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

import streamlit as st
import logic

st.set_page_config(
    page_title="Tsukuyomi To-do-List",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded",
)

_CSS = """
.stApp { background-color: #111d33; color: #e7ecf5; }
section[data-testid="stSidebar"] { background-color: #0c1526; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { background: transparent; }
[data-testid="stFooter"] { display: none; }
[data-testid="stDeployButton"] { display: none; }
[data-testid="stMainBlockContainer"], .block-container {
    max-width: 1120px;
    padding-top: 3rem;
    padding-bottom: 4rem;
}
h1 { font-size: 46px !important; font-weight: 800 !important; color: #ffffff; }
.subtitle { color: #c6d1e4; font-size: 17px; margin: 4px 0 30px 0; }
.clock { font-size: 28px; font-weight: 600; color: #eef2f9; margin-bottom: 30px; }
.cal-day { font-size: 96px; font-weight: 700; line-height: 1.0; color: #ffffff; }
.cal-month { font-size: 26px; color: #dfe6f2; margin: 14px 0 44px 0; }
.shortcut-label { font-weight: 700; font-size: 15px; color: #eef2f9; margin-bottom: 6px; }
section[data-testid="stSidebar"] div[data-testid="stButton"] button {
    background-color: #172744;
    border: 1px solid #22345a;
    color: #dfe6f2;
    border-radius: 8px;
    font-size: 15px;
    height: 2.6rem;
    justify-content: flex-start;
    padding-left: 14px;
}
.stImage img { border-radius: 18px; }
.meet-label { color: #c6d1e4; font-size: 17px; }
.char-name { font-size: 44px; font-weight: 800; color: #ffffff; line-height: 1.15; margin: 6px 0 14px 0; }
.char-quote { color: #dbe3f0; font-size: 18px; line-height: 1.5; max-width: 620px; }
.msg-box {
    background-color: #17253f;
    border-radius: 14px;
    padding: 24px 30px;
    color: #e7ecf5;
    font-size: 17px;
    margin: 26px 0 6px 0;
}
.working-label { font-weight: 700; font-size: 21px; color: #eef2f9; margin-top: 34px; }
.working-value { font-size: 44px; font-weight: 700; color: #ffffff; margin-top: 4px; }
.section-title { font-size: 34px; font-weight: 800; color: #ffffff; }
.task-title { color: #e7ecf5; font-size: 17px; margin: 0; }
.task-title.done { text-decoration: line-through; color: #8ba0c2; }
.empty-note { color: #7f8dab; font-size: 15px; }
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stMarkdownContainer"] {
    margin: 0;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #17253f;
    border-color: #22345a;
    border-radius: 14px;
}
[data-testid="stForm"] {
    background-color: #17253f;
    border: 1px solid #22345a;
    border-radius: 12px;
    padding: 14px 16px;
}
div[data-testid="stButton"] button { border-radius: 10px; }
[data-testid="stIFrame"] { margin: 0; padding: 0; border: none; overflow: hidden; }
section[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
"""

st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)

try:
    logic.ensure_assets()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.info(
        "Save the character photos listed in SPEC.md §3.2 into assets/characters/, then reload."
    )
    st.stop()

# Session-only state (SPEC §2.4, §2.7, §3.4).
if "message" not in st.session_state:
    st.session_state["message"] = logic.MSG_START
if "working_start" not in st.session_state:
    st.session_state["working_start"] = datetime.now()

def _toggle_input(mission: str) -> None:
    key = f"show_input_{mission}"
    st.session_state[key] = not st.session_state.get(key, False)


def _handle_add(mission: str) -> None:
    text_key = f"text_{mission}"
    title = st.session_state.get(text_key, "")
    store = logic.load_store()
    task = logic.add_task(store, mission, title)
    if task is not None:
        logic.save_store(store)
        st.session_state["message"] = logic.MSG_ADDED
    st.session_state[text_key] = ""


def _handle_toggle(mission: str, task_id: str) -> None:
    store = logic.load_store()
    task = logic.toggle_task(store, mission, task_id)
    logic.save_store(store)
    if task.done:
        st.session_state["message"] = logic.MSG_DONE


def _handle_delete(mission: str, task_id: str) -> None:
    store = logic.load_store()
    logic.remove_task(store, mission, task_id)
    logic.save_store(store)
    # Message intentionally unchanged (SPEC §2.4).


@st.fragment(run_every=1)
def _live_clock() -> None:
    st.markdown(
        f'<div class="clock">{logic.format_clock(datetime.now())}</div>',
        unsafe_allow_html=True,
    )


@st.fragment(run_every=1)
def _working_time() -> None:
    elapsed = int((datetime.now() - st.session_state["working_start"]).total_seconds())
    st.markdown('<div class="working-label">Working time:</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="working-value">{logic.format_elapsed(max(elapsed, 0))}</div>',
        unsafe_allow_html=True,
    )


with st.sidebar:
    _live_clock()
    day_number, month_year = logic.format_calendar(logic.today())
    st.markdown(f'<div class="cal-day">{day_number}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cal-month">{month_year}</div>', unsafe_allow_html=True)
    st.markdown('<div class="shortcut-label">Shortcut:</div>', unsafe_allow_html=True)
    if st.button("Main Missions", key="shortcut_main", width="stretch"):
        st.session_state["jump_target"] = "main"
    if st.button("Side Missions", key="shortcut_side", width="stretch"):
        st.session_state["jump_target"] = "side"


def _render_section(store: dict, mission: str, label: str) -> None:
    st.markdown(f'<div id="{mission}-missions"></div>', unsafe_allow_html=True)
    heading_col, add_col = st.columns([6, 1])
    with heading_col:
        st.markdown(f'<div class="section-title">{label}</div>', unsafe_allow_html=True)
    with add_col:
        st.button(
            "⊕",
            key=f"add_toggle_{mission}",
            on_click=_toggle_input,
            args=(mission,),
            width="stretch",
            help="Add a task",
        )

    if st.session_state.get(f"show_input_{mission}", False):
        with st.form(key=f"form_{mission}"):
            st.text_input(
                "Task title",
                key=f"text_{mission}",
                label_visibility="collapsed",
                placeholder="What needs to be done?",
            )
            st.form_submit_button(
                "Add task",
                key=f"submit_{mission}",
                on_click=_handle_add,
                args=(mission,),
                width="stretch",
            )

    tasks = logic.get_tasks(store, mission)
    if not tasks:
        st.markdown(
            '<div class="empty-note">No missions yet — press ⊕ to add one.</div>',
            unsafe_allow_html=True,
        )
        return

    for task in tasks:
        with st.container(border=True):
            done_col, title_col, delete_col = st.columns(
                [1, 10, 1], vertical_alignment="center"
            )
            with done_col:
                st.checkbox(
                    "Done",
                    value=task.done,
                    key=f"done::{mission}::{task.id}",
                    on_change=_handle_toggle,
                    args=(mission, task.id),
                    label_visibility="collapsed",
                    help="Toggle mission complete",
                )
            with title_col:
                css = "task-title done" if task.done else "task-title"
                st.markdown(
                    f'<div class="{css}">{html.escape(task.title, quote=False)}</div>',
                    unsafe_allow_html=True,
                )
            with delete_col:
                st.button(
                    "×",
                    key=f"del::{mission}::{task.id}",
                    on_click=_handle_delete,
                    args=(mission, task.id),
                    width="stretch",
                    help="Delete task",
                )


# Banner
for _banner in (Path("assets/banner.jpg"), Path("assets/banner.png")):
    if _banner.is_file():
        st.image(str(_banner), width="stretch")
        break

st.title("Welcome to Tsukuyomi To-do-List!")
st.markdown(
    '<div class="subtitle">Let\'s do our best again today!</div>',
    unsafe_allow_html=True,
)

character, photo = logic.daily_pick(logic.today())
photo_col, info_col = st.columns([2.1, 9], gap="small")
with photo_col:
    st.image(photo, width=210)
with info_col:
    st.markdown('<div class="meet-label">Today, you meet</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="char-name">{character.name} !</div>', unsafe_allow_html=True
    )
    st.markdown(
        f'<div class="char-quote">&ldquo;{html.escape(character.quote, quote=False)}&rdquo;</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    f'<div class="msg-box">{html.escape(st.session_state["message"], quote=False)}</div>',
    unsafe_allow_html=True,
)

_working_time()

store = logic.load_store()
_render_section(store, "main", "Main Missions")
_render_section(store, "side", "Side Missions")

# Sidebar shortcut
jump = st.session_state.get("jump_target")
if jump in ("main", "side"):
    st.session_state["jump_target"] = None
    st.iframe(
        "<script>try{var el=window.parent.document.getElementById('%s-missions');"
        "if(el){el.scrollIntoView({behavior:'smooth',block:'start'});}}"
        "catch(e){}</script>" % jump,
        height=1,
        width="content",
    )

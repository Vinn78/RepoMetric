"""
RepoMetric - GitHub Repository Activity & Collaboration Analyzer
==============================================================

Streamlit front end. This file only presents data: every number shown comes
from the dictionaries and DataFrames returned by ``analyze_repository`` in
``github_api.py`` (which in turn uses ``data_processor.py``). Nothing in the
API, pagination, authentication or metric logic lives here.

Layout of this file
-------------------
1. Design tokens (colours, fonts, chart palette)
2. Icons and small formatting helpers
3. Global CSS (kept in one place, driven by the tokens above)
4. Reusable UI components (cards, KPI grids, insights, notices, tables)
5. Chart helpers (a single Plotly theme applied to every figure)
6. One render function per analysis section
7. Input panel, analysis flow and page assembly
"""

import html
import re
from contextlib import contextmanager
from datetime import datetime
from urllib.parse import quote

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from github_api import PERIOD_OPTIONS, analyze_repository

st.set_page_config(
    page_title="RepoMetric",
    page_icon="🔎",
    layout="wide"
)

THEME = {
    "bg": "#0d0f13",
    "surface": "#14171d",
    "surface_2": "#191d25",
    "surface_3": "#212631",
    "border": "rgba(255,255,255,0.075)",
    "border_strong": "rgba(255,255,255,0.14)",
    "text": "#eceff5",
    "text_2": "#a6aebd",
    "text_3": "#737c8e",
    "accent": "#6e7bff",
    "accent_2": "#8f7bff",
    "accent_3": "#4f9dff",
    "success": "#3fbf95",
    "warning": "#e3a94f",
    "danger": "#e5717d",
}
CHART_COLORS = [
    "#7583ff", "#a08bff", "#56a5f7", "#45c2b0", "#d78fe0",
    "#8ea2c8", "#e3a94f", "#6cc4e8", "#b6a2ff", "#7f8cf0",
]

FONT_STACK = (
    '"Geist", "Inter", ui-sans-serif, system-ui, -apple-system, '
    '"Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
)
MONO_STACK = (
    '"Geist Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, '
    '"Liberation Mono", monospace'
)
PLOT_FONT = (
    "Geist, Inter, ui-sans-serif, system-ui, -apple-system, "
    "Segoe UI, Roboto, Arial, sans-serif"
)
FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2"
    "?family=Geist:wght@400;500;600;700"
    "&family=Geist+Mono:wght@400;500&display=swap');"
)

ANALYSIS_OPTIONS = [
    "Commits",
    "Contributors",
    "Issues",
    "Pull Requests",
    "Languages",
    "Releases"
]

HEALTH_ICONS = {
    "activity": "activity",
    "collaboration": "users",
    "issues": "issue",
    "pull_requests": "pull_request",
    "releases": "tag",
}

ANALYSIS_META = {
    "Commits": {
        "slug": "commits",
        "icon": "commit",
        "description": "Volume, cadence and busiest days",
    },
    "Contributors": {
        "slug": "contributors",
        "icon": "users",
        "description": "Who contributes and how concentrated it is",
    },
    "Issues": {
        "slug": "issues",
        "icon": "issue",
        "description": "Open versus closed, and how it trends",
    },
    "Pull Requests": {
        "slug": "pull_requests",
        "icon": "pull_request",
        "description": "Open, merged and closed pull requests",
    },
    "Languages": {
        "slug": "languages",
        "icon": "code",
        "description": "Language mix by bytes of code",
    },
    "Releases": {
        "slug": "releases",
        "icon": "tag",
        "description": "Release history and latest version",
    },
}

_ICON_PATHS = {
    "github": (
        '<path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5'
        '.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15'
        '-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65'
        '-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/>'
    ),
    "star": (
        '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 '
        '5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>'
    ),
    "fork": (
        '<circle cx="12" cy="18" r="3"/><circle cx="6" cy="6" r="3"/>'
        '<circle cx="18" cy="6" r="3"/><path d="M18 9v2c0 .6-.4 1-1 1H7c-.6 0-1-.4-1-1V9"/>'
        '<path d="M12 12v3"/>'
    ),
    "issue": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="1"/>',
    "code": '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
    "commit": (
        '<circle cx="12" cy="12" r="3"/><line x1="3" x2="9" y1="12" y2="12"/>'
        '<line x1="15" x2="21" y1="12" y2="12"/>'
    ),
    "users": (
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
        '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
    ),
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "pull_request": (
        '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/>'
        '<path d="M13 6h3a2 2 0 0 1 2 2v7"/><line x1="6" x2="6" y1="9" y2="21"/>'
    ),
    "merge": (
        '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/>'
        '<path d="M6 21V9a9 9 0 0 0 9 9"/>'
    ),
    "tag": (
        '<path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 '
        '1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"/>'
        '<circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/>'
    ),
    "branch": (
        '<line x1="6" x2="6" y1="3" y2="15"/><circle cx="18" cy="6" r="3"/>'
        '<circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>'
    ),
    "calendar": (
        '<rect width="18" height="18" x="3" y="4" rx="2"/>'
        '<path d="M16 2v4M8 2v4M3 10h18"/>'
    ),
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "activity": (
        '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 '
        '2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>'
    ),
    "bulb": (
        '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 '
        '2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>'
    ),
    "alert": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>'
        '<path d="M12 9v4"/><path d="M12 17h.01"/>'
    ),
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "inbox": (
        '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/>'
        '<path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 '
        '16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>'
    ),
    "scale": (
        '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/>'
        '<path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/>'
        '<path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>'
    ),
    "package": (
        '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 '
        '1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/>'
        '<path d="M12 22V12"/>'
    ),
    "percent": (
        '<line x1="19" x2="5" y1="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/>'
        '<circle cx="17.5" cy="17.5" r="2.5"/>'
    ),
    "trending": (
        '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>'
        '<polyline points="16 7 22 7 22 13"/>'
    ),
    "upload": '<path d="M12 3v12"/><path d="m17 8-5-5-5 5"/><path d="M5 21h14"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "lock": (
        '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>'
        '<path d="M7 11V7a5 5 0 0 1 10 0v4"/>'
    ),
}


def icon(name, size=18, stroke=1.9):
    """Inline SVG icon (Lucide-style outline glyphs) that inherits currentColor."""

    return (
        f'<svg class="gs-i" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="{stroke}" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f'{_ICON_PATHS[name]}</svg>'
    )


def esc(value):
    """HTML-escape any value (GitHub data is untrusted) and neutralise '$'."""

    text = "" if value is None else str(value)

    return html.escape(text, quote=True).replace("$", "&#36;")


def compact(markup):
    """Collapse a multi-line HTML string so Markdown never sees blank lines.

    Lines are joined with a single space (not concatenated directly) so that
    prose wrapped across source lines doesn't get glued into one word; HTML
    collapses whitespace between tags anyway, so this is always safe.
    """

    return " ".join(line.strip() for line in markup.strip().splitlines() if line.strip())



def render_html(markup):

    st.markdown(compact(markup), unsafe_allow_html=True)


def is_missing(value):

    if value is None:
        return True

    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def to_timestamp(value):

    if is_missing(value):
        return None

    try:
        stamp = pd.to_datetime(value, utc=True)
    except (TypeError, ValueError):
        return None

    return None if pd.isna(stamp) else stamp


def fmt_int(value):

    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "N/A"


def fmt_bytes(value):

    try:
        size = float(value)
    except (TypeError, ValueError):
        return "N/A"

    for unit in ("B", "KB", "MB", "GB"):

        if size < 1024 or unit == "GB":

            if unit == "B":
                return f"{int(size):,} B"

            return f"{size:,.1f} {unit}"

        size /= 1024

    return f"{size:,.1f} GB"


def fmt_date(value, with_time=False):

    stamp = to_timestamp(value)

    if stamp is None:
        return "N/A"

    text = f"{stamp.day} {stamp.strftime('%b %Y')}"

    if with_time:
        text += f", {stamp.strftime('%H:%M')}"

    return text


def format_percentage(value):

    return f"{value:.2f}%"


def parse_github_url(url):

    pattern = (
        r"https?://github\.com/"
        r"([^/\s]+)/([^/\s]+)"
        r"/?$"
    )

    match = re.match(
        pattern,
        url.strip()
    )

    if not match:
        return None, None

    owner = match.group(1)
    repo = match.group(2)

    return owner, repo


def github_url(owner, repo, path=""):
    """Link to a page on github.com (owner/repo are URL-quoted)."""

    base = f"https://github.com/{quote(str(owner))}/{quote(str(repo))}"

    return f"{base}/{path}" if path else base

def _root_variables():
    """Design tokens exposed as CSS custom properties (single source of truth)."""

    t = THEME

    return (
        ":root{"
        f"--gs-bg:{t['bg']};"
        f"--gs-surface:{t['surface']};"
        f"--gs-surface-2:{t['surface_2']};"
        f"--gs-surface-3:{t['surface_3']};"
        f"--gs-border:{t['border']};"
        f"--gs-border-strong:{t['border_strong']};"
        f"--gs-text:{t['text']};"
        f"--gs-text-2:{t['text_2']};"
        f"--gs-text-3:{t['text_3']};"
        f"--gs-accent:{t['accent']};"
        f"--gs-accent-2:{t['accent_2']};"
        f"--gs-accent-3:{t['accent_3']};"
        f"--gs-success:{t['success']};"
        f"--gs-warning:{t['warning']};"
        f"--gs-danger:{t['danger']};"
        "--gs-accent-soft:rgba(110,123,255,0.14);"
        "--gs-accent-line:rgba(129,140,255,0.55);"
        f"--gs-font:{FONT_STACK};"
        f"--gs-mono:{MONO_STACK};"
        "--gs-ease:cubic-bezier(.2,.7,.2,1);"
        "--gs-shadow:0 1px 0 rgba(255,255,255,0.03) inset,"
        "0 10px 30px -14px rgba(0,0,0,0.6);"
        "}"
    )


BASE_CSS = """

html, body { background: var(--gs-bg); }

.stApp {
    background: var(--gs-bg) !important;
    color: var(--gs-text) !important;
    font-family: var(--gs-font);
    color-scheme: dark;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

.stApp :is(p, h1, h2, h3, h4, h5, h6, label, li, input, textarea, button, a) {
    font-family: var(--gs-font);
}

[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main {
    background: transparent !important;
}

[data-testid="stAppViewContainer"] { position: relative; z-index: 1; }

[data-testid="stHeader"] { background: transparent !important; }

[data-testid="stDecoration"],
[data-testid="stAppDeployButton"],
footer { display: none !important; }

[data-testid="stToolbar"] button,
[data-testid="stToolbar"] svg,
[data-testid="stStatusWidget"] { color: var(--gs-text-2) !important; }


[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] style) {
    display: none;
}

[data-testid="stMainBlockContainer"],
.block-container {
    max-width: 1200px;
    padding: 2.25rem 1.75rem 5rem;
}

* { scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.16) transparent; }
::selection { background: rgba(117,131,255,0.35); }

.gs-i { display: block; flex: none; }


.stApp::before {
    content: "";
    position: fixed;
    inset: -25%;
    z-index: 0;
    pointer-events: none;
    background:
        radial-gradient(38% 34% at 22% 24%, rgba(96,110,255,0.17), transparent 70%),
        radial-gradient(34% 30% at 78% 16%, rgba(143,123,255,0.13), transparent 70%),
        radial-gradient(40% 36% at 62% 84%, rgba(79,157,255,0.10), transparent 70%);
    animation: gs-drift 52s ease-in-out infinite alternate;
    will-change: transform;
}

.stApp::after {
    content: "";
    position: fixed;
    top: -56px; right: 0; bottom: 0; left: 0;
    z-index: 0;
    pointer-events: none;
    background-image:
        linear-gradient(rgba(255,255,255,0.032) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.032) 1px, transparent 1px);
    background-size: 56px 56px;
    -webkit-mask-image: radial-gradient(ellipse 75% 60% at 50% 0%, #000 0%, transparent 78%);
    mask-image: radial-gradient(ellipse 75% 60% at 50% 0%, #000 0%, transparent 78%);
    animation: gs-grid 110s linear infinite;
    will-change: transform;
}

@keyframes gs-drift {
    from { transform: translate3d(0, 0, 0) rotate(0deg) scale(1); }
    to   { transform: translate3d(3%, -2%, 0) rotate(8deg) scale(1.08); }
}

@keyframes gs-grid {
    from { transform: translate3d(0, 0, 0); }
    to   { transform: translate3d(0, 56px, 0); }
}


.gs-hero {
    position: relative;
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 4px 2px 26px;
    margin-bottom: 4px;
}

.gs-hero::after {
    content: "";
    position: absolute;
    left: 0; right: 0; bottom: 0;
    height: 1px;
    background: linear-gradient(90deg, var(--gs-accent-line), rgba(255,255,255,0.06) 45%, transparent);
}

.gs-mark {
    position: relative;
    flex: none;
    width: 54px; height: 54px;
    display: grid;
    place-items: center;
    border-radius: 16px;
    background: linear-gradient(140deg, #4f8cff 0%, #7a6cf6 55%, #a07af8 100%);
    box-shadow:
        0 12px 32px -8px rgba(110,123,255,0.6),
        inset 0 1px 0 rgba(255,255,255,0.28);
}

.gs-title {
    margin: 0;
    font-size: 2.55rem;
    line-height: 1.05;
    font-weight: 700;
    letter-spacing: -0.035em;
    background: linear-gradient(180deg, #ffffff 10%, #bfc8ff 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    filter: drop-shadow(0 0 22px rgba(110,123,255,0.35));
}

.gs-subtitle {
    margin-top: 8px;
    font-size: 1.04rem;
    color: var(--gs-text-2);
    letter-spacing: -0.005em;
}

.gs-lede {
    margin-top: 6px;
    font-size: 0.92rem;
    color: var(--gs-text-3);
    max-width: 68ch;
    line-height: 1.55;
}


div.st-key-control_panel {
    background:
        linear-gradient(180deg, rgba(255,255,255,0.022), rgba(255,255,255,0) 40%),
        var(--gs-surface);
    border: 1px solid var(--gs-border);
    border-radius: 20px;
    padding: 26px 26px 24px;
    box-shadow: var(--gs-shadow);
    gap: 1.6rem !important;
}

.gs-field-label {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
}

.gs-field-label b { font-size: 0.98rem; font-weight: 600; color: var(--gs-text); }
.gs-field-label span { font-size: 0.86rem; color: var(--gs-text-3); }


div.st-key-repo_field [data-testid="stTextInput"] [data-baseweb="input"] {
    background: var(--gs-surface-2) !important;
    border: 1px solid var(--gs-border-strong) !important;
    border-radius: 13px !important;
    min-height: 54px;
    transition: border-color .18s var(--gs-ease), box-shadow .18s var(--gs-ease), background .18s var(--gs-ease);
}

div.st-key-repo_field [data-testid="stTextInput"] [data-baseweb="base-input"] {
    background: transparent !important;
    border-radius: 13px !important;
}

div.st-key-repo_field [data-testid="stTextInput"] [data-baseweb="input"]:hover {
    border-color: rgba(129,140,255,0.42) !important;
}

div.st-key-repo_field [data-testid="stTextInput"] [data-baseweb="input"]:focus-within {
    border-color: var(--gs-accent) !important;
    background: var(--gs-surface-3) !important;
    box-shadow: 0 0 0 4px rgba(110,123,255,0.17), 0 0 30px -8px rgba(110,123,255,0.5) !important;
}

div.st-key-repo_field [data-testid="stTextInput"] input {
    height: 54px;
    padding-left: 48px !important;
    font-size: 1rem;
    color: var(--gs-text) !important;
    -webkit-text-fill-color: var(--gs-text);
    caret-color: var(--gs-accent-3);
    background-color: transparent !important;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='22' height='22' viewBox='0 0 24 24' fill='none' stroke='%23879099' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4'/%3E%3Cpath d='M9 18c-4.51 2-5-2-7-2'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: 16px center;
    background-size: 22px 22px;
}

div.st-key-repo_field [data-testid="stTextInput"] input::placeholder {
    color: var(--gs-text-3) !important;
    -webkit-text-fill-color: var(--gs-text-3);
    opacity: 1;
}


div.st-key-module_grid {
    display: grid !important;
    grid-template-columns: repeat(auto-fill, minmax(236px, 1fr));
    gap: 12px !important;
}

div[class*="st-key-apick_"] { position: relative; gap: 0 !important; }

div[class*="st-key-apick_"] [data-testid="stElementContainer"] { position: static; margin: 0; }


div[class*="st-key-apick_"] [data-testid="stMarkdown"] > div { display: block !important; }

div[class*="st-key-apick_"] [data-testid="stButton"] {
    
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 112px;
    z-index: 3;
}

div[class*="st-key-apick_"] [data-testid="stButton"] button {
    width: 100%;
    height: 100%;
    min-height: 0;
    padding: 0;
    opacity: 0;
    cursor: pointer;
}

.gs-pick {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 14px;
    min-height: 96px;
    padding: 16px 44px 16px 16px;
    border: 1px solid var(--gs-border);
    border-radius: 14px;
    background: var(--gs-surface-2);
    transition: border-color .18s var(--gs-ease), background .18s var(--gs-ease),
                transform .18s var(--gs-ease), box-shadow .18s var(--gs-ease);
}

div[class*="st-key-apick_"]:hover .gs-pick {
    border-color: rgba(129,140,255,0.4);
    background: var(--gs-surface-3);
    transform: translateY(-1px);
}

div[class*="st-key-apick_"]:has(button:focus-visible) .gs-pick {
    outline: 2px solid var(--gs-accent-3);
    outline-offset: 2px;
}

.gs-pick--on,
div[class*="st-key-apick_"]:hover .gs-pick--on {
    border-color: rgba(129,140,255,0.7);
    background: linear-gradient(180deg, rgba(110,123,255,0.20), rgba(110,123,255,0.07));
    box-shadow: 0 0 0 1px rgba(129,140,255,0.25) inset, 0 14px 34px -16px rgba(110,123,255,0.65);
}

.gs-pick__icon {
    flex: none;
    width: 40px; height: 40px;
    display: grid;
    place-items: center;
    border-radius: 11px;
    color: var(--gs-text-2);
    background: rgba(255,255,255,0.045);
    transition: background .18s var(--gs-ease), color .18s var(--gs-ease);
}

.gs-pick--on .gs-pick__icon {
    color: #fff;
    background: linear-gradient(140deg, #4f8cff, #8f7bff);
    box-shadow: 0 6px 16px -6px rgba(110,123,255,0.8);
}

.gs-pick__title { font-size: 0.98rem; font-weight: 600; color: var(--gs-text); }
.gs-pick__desc { margin-top: 3px; font-size: 0.84rem; line-height: 1.4; color: var(--gs-text-2); }

.gs-pick__check {
    position: absolute;
    top: 14px; right: 14px;
    width: 20px; height: 20px;
    display: grid;
    place-items: center;
    border-radius: 50%;
    border: 1.5px solid var(--gs-border-strong);
    color: transparent;
    transition: background .18s var(--gs-ease), border-color .18s var(--gs-ease), color .18s var(--gs-ease);
}

.gs-pick--on .gs-pick__check {
    background: var(--gs-accent);
    border-color: var(--gs-accent);
    color: #fff;
}


div[class*="st-key-atool_"] button,
div[class*="st-key-dl_"] button {
    min-height: 34px;
    width: auto !important;
    padding: 0 14px;
    border-radius: 9px;
    border: 1px solid var(--gs-border) !important;
    background: transparent !important;
    color: var(--gs-text-2) !important;
    font-size: 0.84rem;
    font-weight: 500;
    white-space: nowrap;
    transition: border-color .18s var(--gs-ease), color .18s var(--gs-ease), background .18s var(--gs-ease);
}

div[class*="st-key-atool_"] button:hover,
div[class*="st-key-dl_"] button:hover {
    border-color: rgba(129,140,255,0.5) !important;
    color: var(--gs-text) !important;
    background: var(--gs-accent-soft) !important;
}

div[class*="st-key-atool_"] button p,
div[class*="st-key-dl_"] button p { color: inherit !important; }

div[class*="st-key-dl_"] { display: flex; justify-content: flex-end; }

.gs-foot-note { font-size: 0.88rem; color: var(--gs-text-2); line-height: 1.5; }
.gs-foot-note b { color: var(--gs-text); font-weight: 600; }

.gs-period-note {
    display:flex; align-items:center; flex-wrap:wrap; gap:9px;
    margin-top:8px; padding:10px 12px; border:1px solid rgba(129,140,255,0.18);
    border-radius:11px; background:rgba(110,123,255,0.055); color:var(--gs-text-2);
    font-size:0.84rem; line-height:1.4;
}
.gs-period-note__icon { color:#aab4ff; display:inline-flex; }
.gs-period-note b { color:var(--gs-text); font-weight:600; }
.gs-period-note__muted { color:var(--gs-text-3); }


div.st-key-analyze_cta button {
    min-height: 52px;
    padding: 0 26px;
    border-radius: 13px;
    border: 1px solid rgba(255,255,255,0.16) !important;
    background: linear-gradient(135deg, #4f7cff 0%, #7568f5 55%, #9377f6 100%) !important;
    color: #fff !important;
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: -0.005em;
    box-shadow: 0 12px 30px -10px rgba(110,123,255,0.75), inset 0 1px 0 rgba(255,255,255,0.24);
    transition: transform .18s var(--gs-ease), box-shadow .18s var(--gs-ease), filter .18s var(--gs-ease);
}

div.st-key-analyze_cta button:hover {
    transform: translateY(-1px);
    filter: brightness(1.07);
    box-shadow: 0 18px 38px -10px rgba(110,123,255,0.85), inset 0 1px 0 rgba(255,255,255,0.28);
}

div.st-key-analyze_cta button:active { transform: translateY(0); filter: brightness(0.98); }
div.st-key-analyze_cta button:focus-visible { outline: 2px solid #fff; outline-offset: 3px; }
div.st-key-analyze_cta button p { color: #fff !important; font-weight: 600; }


div.st-key-results { animation: gs-enter .55s var(--gs-ease) both; gap: 1rem; }

@keyframes gs-enter {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: none; }
}

.gs-section {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    margin: 2.2rem 0 0.5rem;
}

.gs-section:first-child { margin-top: 0.9rem; }

.gs-section__icon {
    flex: none;
    width: 44px; height: 44px;
    display: grid;
    place-items: center;
    border-radius: 13px;
    color: #b4bcff;
    background: linear-gradient(180deg, rgba(110,123,255,0.22), rgba(110,123,255,0.08));
    border: 1px solid rgba(129,140,255,0.32);
}

.gs-section__title {
    font-size: 1.55rem;
    line-height: 1.2;
    font-weight: 650;
    letter-spacing: -0.025em;
    color: var(--gs-text);
}

.gs-section__desc { margin-top: 4px; font-size: 0.95rem; color: var(--gs-text-2); max-width: 70ch; line-height: 1.5; }

.gs-section__note {
    margin-left: auto;
    align-self: center;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 11px;
    border-radius: 999px;
    font-size: 0.8rem;
    color: var(--gs-text-2);
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--gs-border);
    white-space: nowrap;
}


.gs-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(208px, 1fr)); gap: 14px; }

.gs-kpi {
    position: relative;
    min-width: 0;
    padding: 18px 18px 16px;
    border: 1px solid var(--gs-border);
    border-radius: 15px;
    background: var(--gs-surface);
    box-shadow: var(--gs-shadow);
    transition: border-color .2s var(--gs-ease), background .2s var(--gs-ease);
}

.gs-kpi:hover { border-color: var(--gs-border-strong); background: var(--gs-surface-2); }

.gs-kpi__top { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.gs-kpi__label { font-size: 0.88rem; font-weight: 500; color: var(--gs-text-2); }

.gs-kpi__icon {
    width: 32px; height: 32px;
    display: grid;
    place-items: center;
    border-radius: 10px;
    color: #a4afff;
    background: var(--gs-accent-soft);
}

.gs-kpi__icon--success { color: #6fd8b3; background: rgba(63,191,149,0.14); }
.gs-kpi__icon--violet  { color: #b7a6ff; background: rgba(143,123,255,0.16); }
.gs-kpi__icon--blue    { color: #8ec3ff; background: rgba(79,157,255,0.15); }
.gs-kpi__icon--warning { color: #efc27e; background: rgba(227,169,79,0.14); }

.gs-kpi__value {
    margin-top: 16px;
    font-size: 2rem;
    line-height: 1.1;
    font-weight: 650;
    letter-spacing: -0.03em;
    color: var(--gs-text);
    font-variant-numeric: tabular-nums;
}

.gs-kpi__value--text {
    font-size: 1.45rem;
    letter-spacing: -0.02em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.gs-kpi__hint { margin-top: 7px; font-size: 0.82rem; color: var(--gs-text-3); }


div[class*="st-key-card_"] {
    background: var(--gs-surface);
    border: 1px solid var(--gs-border);
    border-radius: 18px;
    padding: 20px 22px 16px;
    box-shadow: var(--gs-shadow);
    gap: 0.8rem !important;
    min-width: 0;
}

.gs-card__title { font-size: 1rem; font-weight: 600; color: var(--gs-text); letter-spacing: -0.01em; }
.gs-card__sub { margin-top: 3px; font-size: 0.86rem; color: var(--gs-text-2); line-height: 1.45; }

[data-testid="stPlotlyChart"] { background: transparent; }

.gs-empty-chart { padding: 26px 8px; text-align: center; color: var(--gs-text-3); font-size: 0.9rem; }

.gs-table-toggle {
    display: flex;
    justify-content: flex-end;
    margin: 0;
}

.gs-expand-btn {
    display: flex;
    justify-content: flex-end;
    margin: 0;
}

.gs-table-toggle button {
    min-height: 34px !important;
    width: 34px !important;
    padding: 0 !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 9px !important;
    background: rgba(255,255,255,0.035) !important;
    color: var(--gs-text-2) !important;
    font-size: 15px !important;
}

.gs-table-toggle button:hover {
    border-color: rgba(117,131,255,0.42) !important;
    background: rgba(117,131,255,0.10) !important;
    color: var(--gs-text) !important;
}

div[class*="st-key-table-collapsed-"] {
    background: var(--gs-surface);
    border: 1px solid var(--gs-border);
    border-radius: 12px;
    padding: 7px 10px;
    box-shadow: var(--gs-shadow);
    min-width: 0;
    margin-top: 0;
    margin-bottom: 0;
}

div[class*="st-key-table-collapsed-"] [data-testid="stHorizontalBlock"] {
    align-items: center;
    gap: 8px;
}

div[class*="st-key-table-collapsed-"] [data-testid="stMarkdownContainer"] {
    padding: 0;
}

.gs-collapsed-table-title {
    color: var(--gs-text);
    font-size: 0.92rem;
    font-weight: 600;
    line-height: 32px;
}

div[class*="st-key-table-collapsed-"] button {
    min-height: 32px !important;
    height: 32px !important;
    width: 32px !important;
    padding: 0 !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 8px !important;
    background: rgba(255,255,255,0.035) !important;
    color: var(--gs-text-2) !important;
    font-size: 15px !important;
}

div[class*="st-key-table-collapsed-"] button:hover {
    border-color: rgba(117,131,255,0.42) !important;
    background: rgba(117,131,255,0.10) !important;
    color: var(--gs-text) !important;
}

.gs-expand-btn button {
    min-height: 34px;
    padding: 0 12px;
    border-radius: 9px;
    border: 1px solid rgba(255,255,255,0.09);
    background: rgba(255,255,255,0.035);
    color: var(--gs-text-2);
    font-size: 0.8rem;
    font-weight: 600;
}

.gs-expand-btn button:hover {
    border-color: rgba(117,131,255,0.42);
    color: var(--gs-text);
    background: rgba(117,131,255,0.10);
}



.gs-insights { display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 14px; }
.gs-insights--stack { grid-template-columns: 1fr; }

.gs-insight {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 16px 18px 16px 22px;
    border-radius: 15px;
    border: 1px solid rgba(129,140,255,0.2);
    background:
        linear-gradient(135deg, rgba(110,123,255,0.10), rgba(143,123,255,0.03) 65%),
        var(--gs-surface);
    box-shadow: var(--gs-shadow);
}

.gs-insight::before {
    content: "";
    position: absolute;
    left: 0; top: 14px; bottom: 14px;
    width: 3px;
    border-radius: 0 3px 3px 0;
    background: linear-gradient(180deg, #4f8cff, #8f7bff);
}

.gs-insight__icon { flex: none; margin-top: 2px; color: #a4afff; }
.gs-insight__title { font-size: 0.86rem; font-weight: 500; color: var(--gs-text-2); }
.gs-insight__body { margin-top: 4px; font-size: 0.97rem; line-height: 1.55; color: var(--gs-text); }
.gs-insight__body strong { font-weight: 600; color: #fff; }

.gs-insights-title { margin: 0.3rem 0 0.1rem; font-size: 1rem; font-weight: 600; color: var(--gs-text); }


.gs-repo {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 18px;
    padding: 24px 26px;
    border-radius: 20px;
    border: 1px solid var(--gs-border);
    background:
        radial-gradient(110% 150% at 0% 0%, rgba(110,123,255,0.16), transparent 58%),
        var(--gs-surface);
    box-shadow: var(--gs-shadow);
    overflow: hidden;
}

.gs-repo::before {
    content: "";
    position: absolute;
    left: 0; right: 0; top: 0;
    height: 1px;
    background: linear-gradient(90deg, var(--gs-accent-line), rgba(255,255,255,0.05) 60%, transparent);
}

.gs-avatar {
    position: relative;
    flex: none;
    width: 60px; height: 60px;
    display: grid;
    place-items: center;
    border-radius: 16px;
    color: var(--gs-text-2);
    background: var(--gs-surface-3);
    border: 1px solid var(--gs-border-strong);
    overflow: hidden;
}

.gs-avatar img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }

.gs-repo__body { min-width: 0; }
.gs-repo__label { font-size: 0.84rem; color: var(--gs-text-3); margin-bottom: 4px; }

.gs-repo__name {
    font-size: 1.5rem;
    line-height: 1.2;
    font-weight: 650;
    letter-spacing: -0.025em;
    overflow-wrap: anywhere;
}

.gs-repo__name a { color: var(--gs-text); text-decoration: none; transition: color .18s var(--gs-ease); }
.gs-repo__name a:hover { color: #b9c1ff; }
.gs-repo__name .owner { color: var(--gs-text-2); font-weight: 500; }
.gs-repo__name .sep { color: var(--gs-text-3); font-weight: 400; padding: 0 2px; }

.gs-repo__desc { margin-top: 8px; max-width: 78ch; font-size: 0.98rem; line-height: 1.6; color: var(--gs-text-2); }
.gs-repo__chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }

.gs-chip {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 5px 11px;
    border-radius: 999px;
    font-size: 0.82rem;
    color: var(--gs-text-2);
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--gs-border);
}

.gs-chip--topic { color: #b4bcff; background: rgba(110,123,255,0.10); border-color: rgba(129,140,255,0.22); }
.gs-chip--warn { color: #efc27e; background: rgba(227,169,79,0.10); border-color: rgba(227,169,79,0.25); }


.gs-notice {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 16px 18px;
    border-radius: 15px;
    border: 1px solid var(--gs-border);
    background: var(--gs-surface);
    box-shadow: var(--gs-shadow);
}

.gs-notice__icon {
    flex: none;
    width: 34px; height: 34px;
    display: grid;
    place-items: center;
    border-radius: 10px;
}

.gs-notice__title { font-size: 1rem; font-weight: 600; color: var(--gs-text); }
.gs-notice__msg { margin-top: 3px; font-size: 0.92rem; line-height: 1.55; color: var(--gs-text-2); }
.gs-notice__msg code, .gs-empty code {
    font-family: var(--gs-mono);
    font-size: 0.85em;
    padding: 1px 6px;
    border-radius: 6px;
    color: var(--gs-text);
    background: rgba(255,255,255,0.07);
}

.gs-notice details { margin-top: 10px; }
.gs-notice summary { cursor: pointer; font-size: 0.84rem; color: var(--gs-text-3); width: fit-content; }
.gs-notice summary:hover { color: var(--gs-text-2); }

.gs-notice pre {
    margin: 8px 0 0;
    padding: 10px 12px;
    max-height: 160px;
    overflow: auto;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: var(--gs-mono);
    font-size: 0.78rem;
    line-height: 1.5;
    color: var(--gs-text-2);
    background: rgba(0,0,0,0.28);
    border: 1px solid var(--gs-border);
    border-radius: 10px;
}

.gs-notice--error   { border-color: rgba(229,113,125,0.32); background: linear-gradient(135deg, rgba(229,113,125,0.09), transparent 60%), var(--gs-surface); }
.gs-notice--error   .gs-notice__icon { color: #f0949d; background: rgba(229,113,125,0.14); }
.gs-notice--warning { border-color: rgba(227,169,79,0.32); background: linear-gradient(135deg, rgba(227,169,79,0.08), transparent 60%), var(--gs-surface); }
.gs-notice--warning .gs-notice__icon { color: #efc27e; background: rgba(227,169,79,0.14); }
.gs-notice--success { border-color: rgba(63,191,149,0.3); background: linear-gradient(135deg, rgba(63,191,149,0.08), transparent 60%), var(--gs-surface); }
.gs-notice--success .gs-notice__icon { color: #6fd8b3; background: rgba(63,191,149,0.14); }
.gs-notice--info    .gs-notice__icon { color: #8ec3ff; background: rgba(79,157,255,0.14); }


.gs-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    padding: 34px 24px;
    text-align: center;
    border: 1px dashed var(--gs-border-strong);
    border-radius: 18px;
    background: rgba(255,255,255,0.015);
}

.gs-empty__icon {
    width: 46px; height: 46px;
    display: grid;
    place-items: center;
    margin-bottom: 6px;
    border-radius: 14px;
    color: #a4afff;
    background: var(--gs-accent-soft);
}

.gs-empty__title { font-size: 1.05rem; font-weight: 600; color: var(--gs-text); }
.gs-empty__msg { max-width: 56ch; font-size: 0.92rem; line-height: 1.55; color: var(--gs-text-2); }


.gs-loader {
    padding: 22px 24px 24px;
    border-radius: 20px;
    border: 1px solid var(--gs-border);
    background: var(--gs-surface);
    box-shadow: var(--gs-shadow);
}

.gs-loader__head { display: flex; align-items: center; gap: 14px; }

.gs-spinner {
    flex: none;
    width: 24px; height: 24px;
    border-radius: 50%;
    border: 2.5px solid rgba(129,140,255,0.22);
    border-top-color: var(--gs-accent);
    animation: gs-spin .85s linear infinite;
}

.gs-loader__title { font-size: 1.02rem; font-weight: 600; color: var(--gs-text); }
.gs-loader__sub { margin-top: 2px; font-size: 0.88rem; color: var(--gs-text-2); overflow-wrap: anywhere; }

.gs-loader__bar { margin: 18px 0 14px; height: 3px; overflow: hidden; border-radius: 3px; background: rgba(255,255,255,0.06); }

.gs-loader__bar::after {
    content: "";
    display: block;
    height: 100%;
    width: 34%;
    border-radius: 3px;
    background: linear-gradient(90deg, transparent, var(--gs-accent), var(--gs-accent-2), transparent);
    animation: gs-slide 1.5s ease-in-out infinite;
}

.gs-loader__chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }

.gs-skel-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 12px; }

.gs-skel {
    border-radius: 12px;
    background: linear-gradient(100deg, rgba(255,255,255,0.035) 30%, rgba(255,255,255,0.075) 50%, rgba(255,255,255,0.035) 70%);
    background-size: 220% 100%;
    animation: gs-shimmer 1.7s linear infinite;
}

.gs-skel--kpi { height: 92px; }
.gs-skel--chart { height: 170px; }

@keyframes gs-spin { to { transform: rotate(360deg); } }
@keyframes gs-slide { from { transform: translateX(-110%); } to { transform: translateX(310%); } }
@keyframes gs-shimmer { from { background-position: 120% 0; } to { background-position: -120% 0; } }


.gs-tl { position: relative; display: flex; flex-direction: column; gap: 18px; padding: 4px 0 4px 4px; }
.gs-tl::before { content: ""; position: absolute; left: 10px; top: 12px; bottom: 12px; width: 1px; background: var(--gs-border-strong); }
.gs-tl__item { position: relative; display: flex; gap: 14px; padding-left: 4px; min-width: 0; }

.gs-tl__dot {
    position: relative;
    flex: none;
    width: 13px; height: 13px;
    margin-top: 5px;
    border-radius: 50%;
    background: var(--gs-surface);
    border: 2px solid var(--gs-accent);
    box-shadow: 0 0 0 4px var(--gs-surface);
}

.gs-tl__item--pre .gs-tl__dot { border-color: var(--gs-warning); }
.gs-tl__top { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }

.gs-tl__tag {
    font-family: var(--gs-mono);
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--gs-text);
    text-decoration: none;
    overflow-wrap: anywhere;
}

a.gs-tl__tag:hover { color: #b9c1ff; }
.gs-tl__name { margin-top: 2px; font-size: 0.86rem; color: var(--gs-text-2); overflow-wrap: anywhere; }
.gs-tl__meta { margin-top: 2px; font-size: 0.8rem; color: var(--gs-text-3); }

.gs-pill { padding: 2px 8px; border-radius: 999px; font-size: 0.72rem; font-weight: 500; }
.gs-pill--warn { color: #efc27e; background: rgba(227,169,79,0.12); border: 1px solid rgba(227,169,79,0.25); }
.gs-pill--muted { color: var(--gs-text-2); background: rgba(255,255,255,0.05); border: 1px solid var(--gs-border); }

.gs-method { display: flex; flex-direction: column; }
.gs-method__row { display: flex; gap: 18px; padding: 14px 0; border-top: 1px solid var(--gs-border); }
.gs-method__row:first-child { border-top: 0; padding-top: 2px; }
.gs-method__name { flex: 0 0 150px; font-size: 0.92rem; font-weight: 600; color: var(--gs-text); }
.gs-method__weight { display: block; margin-top: 2px; font-size: 0.78rem; font-weight: 400; color: var(--gs-text-3); }
.gs-method__body { min-width: 0; flex: 1; font-size: 0.86rem; line-height: 1.5; color: var(--gs-text-2); }
.gs-method__rule { margin-top: 4px; color: var(--gs-text-3); overflow-wrap: anywhere; }
.gs-method__rule b { font-weight: 500; color: var(--gs-text-2); }
.gs-method__foot { margin-top: 6px; padding-top: 12px; border-top: 1px solid var(--gs-border); font-size: 0.84rem; color: var(--gs-text-3); }


.stApp iframe { border: 0; border-radius: 12px; color-scheme: dark; }



div[data-testid="stSelectboxVirtualDropdown"] {
    background: var(--gs-surface-3) !important;
    border: 1px solid var(--gs-border-strong) !important;
    border-radius: 12px !important;
    box-shadow: var(--gs-shadow) !important;
}

div[data-testid="stSelectboxVirtualDropdown"] [role="option"] {
    background: transparent !important;
    color: var(--gs-text) !important;
}

div[data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover,
div[data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"] {
    background: var(--gs-accent-soft) !important;
    color: var(--gs-text) !important;
}

div[data-testid="stSelectboxVirtualDropdown"] [role="option"] * {
    color: inherit !important;
}


@media (max-width: 900px) {
    [data-testid="stMainBlockContainer"], .block-container { padding: 1.5rem 1rem 4rem; }
    .gs-title { font-size: 2.05rem; }
    .gs-mark { width: 46px; height: 46px; border-radius: 14px; }
    div.st-key-control_panel { padding: 18px 16px; border-radius: 16px; }
    div[class*="st-key-card_"] { padding: 16px 14px 12px; border-radius: 16px; }
    .gs-repo { flex-direction: column; padding: 20px 18px; }
    .gs-section { flex-wrap: wrap; margin-top: 1.8rem; }
    .gs-section__note { margin-left: 0; }
    .gs-kpi__value { font-size: 1.7rem; }
}

@media (max-width: 520px) {
    .gs-hero { align-items: flex-start; }
    .gs-method__row { flex-direction: column; gap: 6px; }
    .gs-method__name { flex: none; }
    .gs-lede { display: none; }
    div.st-key-module_grid { grid-template-columns: 1fr; }
}

@media (prefers-reduced-motion: reduce) {
    .stApp::before, .stApp::after, div.st-key-results,
    .gs-spinner, .gs-loader__bar::after, .gs-skel { animation: none !important; }
    .gs-pick, .gs-kpi, div.st-key-analyze_cta button { transition: none !important; }
}
"""


def inject_styles():
    """Inject the global stylesheet once per run."""

    st.markdown(
        "<style>" + FONT_IMPORT + _root_variables() + BASE_CSS + "</style>",
        unsafe_allow_html=True
    )

def hero():

    render_html(f"""
    <div class="gs-hero">
        <div class="gs-mark">{icon('search', 26, 2.1)}</div>
        <div>
            <h1 class="gs-title">RepoMetric</h1>
            <div class="gs-subtitle">GitHub Repository Activity &amp; Collaboration Analyzer</div>
            <div class="gs-lede">
                Point it at any public repository to pull commit activity, contributor
                concentration, issue and pull request health, language mix and release
                history straight from the GitHub API.
            </div>
        </div>
    </div>
    """)


def section_header(title, description, icon_name, note=None):

    note_html = f'<div class="gs-section__note">{icon("info", 14)}{esc(note)}</div>' if note else ""

    render_html(f"""
    <div class="gs-section">
        <div class="gs-section__icon">{icon(icon_name, 22, 1.8)}</div>
        <div style="min-width:0;">
            <div class="gs-section__title">{esc(title)}</div>
            <div class="gs-section__desc">{esc(description)}</div>
        </div>
        {note_html}
    </div>
    """)


def kpi_grid(cards):
    """cards: list of dicts with label, value, icon, hint (optional), tone (optional)."""

    items = []

    for card in cards:

        tone = card.get("tone", "")
        tone_class = f" gs-kpi__icon--{tone}" if tone else ""
        value = esc(card["value"])
        value_class = "gs-kpi__value" + (" gs-kpi__value--text" if card.get("wrap_text") else "")
        hint = f'<div class="gs-kpi__hint">{esc(card["hint"])}</div>' if card.get("hint") else ""

        items.append(f"""
        <div class="gs-kpi">
            <div class="gs-kpi__top">
                <div class="gs-kpi__label">{esc(card['label'])}</div>
                <div class="gs-kpi__icon{tone_class}">{icon(card['icon'], 16, 2)}</div>
            </div>
            <div class="{value_class}" title="{value}">{value}</div>
            {hint}
        </div>
        """)

    render_html(f'<div class="gs-kpis">{"".join(items)}</div>')


def insight_cards(items, stack=False):
    """items: list of dicts with icon, title, body_html (pre-escaped inline HTML allowed for <strong>)."""

    if not items:
        return

    grid_class = "gs-insights gs-insights--stack" if stack else "gs-insights"

    cards = "".join(f"""
    <div class="gs-insight">
        <div class="gs-insight__icon">{icon(item['icon'], 18, 1.9)}</div>
        <div>
            <div class="gs-insight__title">{esc(item['title'])}</div>
            <div class="gs-insight__body">{item['body_html']}</div>
        </div>
    </div>
    """ for item in items)

    render_html(f"""
    <div class="gs-insights-title">Key insights</div>
    <div class="{grid_class}">{cards}</div>
    """)


def notice(kind, title, message, detail=None):
    """kind: 'error' | 'warning' | 'success' | 'info'."""

    icon_by_kind = {
        "error": "alert",
        "warning": "alert",
        "success": "check",
        "info": "info",
    }

    detail_html = ""

    if detail:
        detail_html = f"<details><summary>Show details</summary><pre>{esc(detail)}</pre></details>"

    render_html(f"""
    <div class="gs-notice gs-notice--{kind}">
        <div class="gs-notice__icon">{icon(icon_by_kind[kind], 18, 2)}</div>
        <div style="min-width:0;">
            <div class="gs-notice__title">{esc(title)}</div>
            <div class="gs-notice__msg">{esc(message)}{detail_html}</div>
        </div>
    </div>
    """)


def empty_state(title, message, icon_name="inbox"):

    render_html(f"""
    <div class="gs-empty">
        <div class="gs-empty__icon">{icon(icon_name, 22, 1.8)}</div>
        <div class="gs-empty__title">{esc(title)}</div>
        <div class="gs-empty__msg">{esc(message)}</div>
    </div>
    """)


@contextmanager
def card_open(key, title=None, subtitle=None):
    """Bordered chart/table card, used as ``with card_open("key", "Title"): ...``.

    A single ``@contextmanager`` wrapping ``st.container()`` is important here:
    entering the container's context manager a second time at the call site
    (e.g. via ``with`` on an already-entered container) would leave Streamlit's
    internal layout stack unbalanced by one level for the rest of the script
    run, silently corrupting the width/nesting of every section rendered
    afterward. Using ``yield`` inside a single ``with st.container(...)``
    guarantees exactly one enter and one exit.
    """

    with st.container(key=f"card_{key}"):

        if title:

            sub_html = f'<div class="gs-card__sub">{esc(subtitle)}</div>' if subtitle else ""

            render_html(f"""
            <div class="gs-card__title">{esc(title)}</div>
            {sub_html}
            """)

        yield


def loading_panel(owner, repo, selected, period=None):

    chips = "".join(
        f'<span class="gs-chip">{icon(ANALYSIS_META[name]["icon"], 13)}{esc(name)}</span>'
        for name in selected
    )

    skel_kpis = "".join('<div class="gs-skel gs-skel--kpi"></div>' for _ in range(4))

    render_html(f"""
    <div class="gs-loader">
        <div class="gs-loader__head">
            <div class="gs-spinner"></div>
            <div style="min-width:0;">
                <div class="gs-loader__title">Fetching data from the GitHub API</div>
                <div class="gs-loader__sub">{esc(owner)}/{esc(repo)} &middot; {len(selected)} module{'s' if len(selected) != 1 else ''} selected &middot; {esc(period or "All Time")}</div>
            </div>
        </div>
        <div class="gs-loader__bar"></div>
        <div class="gs-loader__chips">{chips}</div>
        <div class="gs-skel-grid">{skel_kpis}</div>
    </div>
    """)


def styled_dataframe(df, column_config=None, height=None, column_order=None):

    st.dataframe(
        df,
        width="stretch",
        height=height if height is not None else "content",
        hide_index=True,
        column_config=column_config or {},
        column_order=column_order,
    )


@st.dialog("Expanded View", width="large")
def expanded_view(title, fig=None, df=None, column_config=None, height=520, column_order=None):

    st.markdown(f"### {esc(title)}")

    if fig is not None:
        fig.update_layout(autosize=True, height=height)
        st.plotly_chart(
            fig,
            width="stretch",
            height=height,
            config={**PLOTLY_CONFIG, "responsive": True},
        )

    if df is not None:
        st.dataframe(
            df,
            width="stretch",
            height=height,
            hide_index=True,
            column_config=column_config or {},
            column_order=column_order,
        )


def visual_card(key, title, subtitle, fig=None, df=None, column_config=None, height=360, column_order=None, default_view="Chart"):

    if fig is not None:
        with card_open(f"{key}_chart", title, subtitle):
            chart_action_cols = st.columns([1, 0.12], gap="small")
            with chart_action_cols[1]:
                st.markdown('<div class="gs-expand-btn">', unsafe_allow_html=True)
                if st.button("Expand", key=f"{key}_chart_expand", width="stretch"):
                    expanded_view(
                        title,
                        fig=fig,
                        height=max(height, 520),
                    )
                st.markdown('</div>', unsafe_allow_html=True)
            render_chart(fig)

    if df is not None:
        table_state_key = f"table_visible_{key}"
        if table_state_key not in st.session_state:
            st.session_state[table_state_key] = False

        table_visible = st.session_state[table_state_key]

        if not table_visible:
            with st.container(key=f"table-collapsed-{key}"):
                collapsed_cols = st.columns([1, 0.05], gap="small", vertical_alignment="center")
                with collapsed_cols[0]:
                    st.markdown(
                        f'<div class="gs-collapsed-table-title">{esc(title)} table</div>',
                        unsafe_allow_html=True,
                    )
                with collapsed_cols[1]:
                    if st.button("⌄", key=f"{key}_table_toggle", width="stretch"):
                        st.session_state[table_state_key] = True
                        st.rerun()
        else:
            with card_open(f"{key}_table", f"{title} table", "Detailed data for this analysis."):
                table_action_cols = st.columns([1, 0.08, 0.08], gap="small")

                with table_action_cols[1]:
                    st.markdown('<div class="gs-expand-btn">', unsafe_allow_html=True)
                    if st.button("Expand", key=f"{key}_table_expand", width="stretch"):
                        expanded_view(
                            f"{title} table",
                            df=df,
                            column_config=column_config,
                            height=max(height, 520),
                            column_order=column_order,
                        )
                    st.markdown('</div>', unsafe_allow_html=True)

                with table_action_cols[2]:
                    st.markdown('<div class="gs-table-toggle">', unsafe_allow_html=True)
                    if st.button(
                        "⌃",
                        key=f"{key}_table_toggle",
                        width="stretch",
                    ):
                        st.session_state[table_state_key] = False
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                styled_dataframe(
                    df,
                    column_config=column_config,
                    height=height,
                    column_order=column_order,
                )

def _style_figure(fig, height=340, legend=True):
    """Apply the shared dark theme to any Plotly figure in place."""

    fig.update_layout(
        template=None,
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=PLOT_FONT, size=13, color=THEME["text_2"]),
        hoverlabel=dict(
            bgcolor=THEME["surface_3"],
            bordercolor=THEME["border_strong"],
            font=dict(family=PLOT_FONT, size=12.5, color=THEME["text"]),
        ),
        legend=dict(
            visible=legend,
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
            font=dict(size=12, color=THEME["text_2"]),
            bgcolor="rgba(0,0,0,0)",
        ) if legend else dict(visible=False),
        colorway=CHART_COLORS,
        hovermode="x unified",
    )

    fig.update_xaxes(
        gridcolor="rgba(255,255,255,0.06)",
        zerolinecolor="rgba(255,255,255,0.09)",
        linecolor="rgba(255,255,255,0.09)",
        tickfont=dict(color=THEME["text_3"], size=11.5),
        title_font=dict(color=THEME["text_2"], size=12),
    )

    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.06)",
        zerolinecolor="rgba(255,255,255,0.09)",
        linecolor="rgba(255,255,255,0.09)",
        tickfont=dict(color=THEME["text_3"], size=11.5),
        title_font=dict(color=THEME["text_2"], size=12),
    )

    return fig


PLOTLY_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    "scrollZoom": False,
}


def render_chart(fig):

    fig.update_layout(autosize=True)
    st.plotly_chart(
        fig,
        width="stretch",
        config={**PLOTLY_CONFIG, "responsive": True},
    )


def commit_trend_figure(commits_df):

    daily = (
        commits_df.groupby("day").size().reset_index(name="commits").sort_values("day")
    )

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=daily["day"], y=daily["commits"],
        mode="lines", name="Commits",
        line=dict(color=CHART_COLORS[0], width=2.4, shape="spline", smoothing=0.35),
        fill="tozeroy", fillcolor="rgba(117,131,255,0.14)",
        hovertemplate="%{x|%d %b %Y}<br><b>%{y} commit(s)</b><extra></extra>",
    ))

    fig.update_yaxes(rangemode="tozero", title_text="Commits")
    fig.update_xaxes(title_text=None)

    return _style_figure(fig, legend=False)


def commit_monthly_figure(monthly_df):

    ordered = monthly_df.sort_values("month")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=ordered["month"], y=ordered["commits"],
        name="Commits",
        marker=dict(color=CHART_COLORS[0], line=dict(width=0)),
        customdata=ordered[["active_days", "contributors"]],
        hovertemplate=(
            "<b>%{x}</b><br>"
            "%{y} commit(s)<br>"
            "%{customdata[0]} active day(s)<br>"
            "%{customdata[1]} contributor(s)"
            "<extra></extra>"
        ),
    ))

    fig.update_yaxes(rangemode="tozero", title_text="Commits")
    fig.update_xaxes(title_text=None, type="category")

    return _style_figure(fig, legend=False)


def contributors_figure(contributors_df, top_n=15):

    top = contributors_df.head(top_n).iloc[::-1]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=top["contributions"], y=top["username"],
        orientation="h",
        marker=dict(
            color=top["contributions"],
            colorscale=[[0, "#4a53c9"], [1, "#8f7bff"]],
            line=dict(width=0),
        ),
        hovertemplate="<b>%{y}</b><br>%{x} contribution(s)<extra></extra>",
    ))

    fig.update_yaxes(title_text=None)
    fig.update_xaxes(title_text="Contributions", rangemode="tozero")

    height = max(260, 34 * len(top) + 40)

    return _style_figure(fig, height=height, legend=False)


def status_donut_figure(counts, labels_colors):
    """counts: dict of state -> count. labels_colors: dict of state -> hex color."""

    states = list(counts.keys())
    values = [counts[s] for s in states]
    colors = [labels_colors.get(s, CHART_COLORS[i % len(CHART_COLORS)]) for i, s in enumerate(states)]

    fig = go.Figure(go.Pie(
        labels=[s.capitalize() for s in states],
        values=values,
        hole=0.62,
        marker=dict(colors=colors, line=dict(color=THEME["surface"], width=3)),
        textinfo="percent",
        textfont=dict(size=12.5, color=THEME["text"]),
        hovertemplate="<b>%{label}</b><br>%{value} (%{percent})<extra></extra>",
        sort=False,
    ))

    total = sum(values)

    fig.add_annotation(
        text=f"<b>{total:,}</b>", showarrow=False,
        font=dict(size=22, color=THEME["text"], family=PLOT_FONT),
        x=0.5, y=0.56,
    )

    fig.add_annotation(
        text="total", showarrow=False,
        font=dict(size=11.5, color=THEME["text_3"], family=PLOT_FONT),
        x=0.5, y=0.42,
    )

    return _style_figure(fig, height=300)


def languages_figure(languages_df, top_n=8):

    ordered = languages_df.sort_values("bytes", ascending=False).reset_index(drop=True)

    if len(ordered) > top_n:

        head = ordered.iloc[:top_n]
        other_bytes = ordered.iloc[top_n:]["bytes"].sum()
        other_pct = ordered.iloc[top_n:]["percentage"].sum()

        head = pd.concat([
            head,
            pd.DataFrame([{"language": "Other", "bytes": other_bytes, "percentage": other_pct}])
        ], ignore_index=True)

    else:

        head = ordered

    fig = go.Figure(go.Pie(
        labels=head["language"],
        values=head["bytes"],
        hole=0.5,
        marker=dict(colors=CHART_COLORS, line=dict(color=THEME["surface"], width=3)),
        textinfo="label+percent",
        textfont=dict(size=12, color=THEME["text"]),
        hovertemplate="<b>%{label}</b><br>%{percent} of code<extra></extra>",
    ))

    return _style_figure(fig, height=340)


def releases_timeline_figure(releases_df):

    ordered = releases_df.dropna(subset=["published_at"]).sort_values("published_at")

    if ordered.empty:
        return None

    colors = ["#e3a94f" if pre else "#7583ff" for pre in ordered["prerelease"]]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=ordered["published_at"], y=[1] * len(ordered),
        mode="markers",
        marker=dict(size=13, color=colors, line=dict(color=THEME["surface"], width=2)),
        customdata=ordered[["tag", "name"]],
        hovertemplate="<b>%{customdata[0]}</b><br>%{x|%d %b %Y}<extra></extra>",
    ))

    fig.update_yaxes(visible=False, range=[0.5, 1.5])
    fig.update_xaxes(title_text=None)

    return _style_figure(fig, height=170, legend=False)

def health_color(score):

    if score >= 75:
        return THEME["success"]

    if score >= 50:
        return THEME["warning"]

    return THEME["danger"]


def health_tone(score):

    if score is None:
        return ""

    if score >= 75:
        return "success"

    if score >= 50:
        return "blue"

    return "warning"


def health_components_figure(components):

    scored = [item for item in components if item["available"]][::-1]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=[item["score"] for item in scored],
        y=[item["name"] for item in scored],
        orientation="h",
        marker=dict(
            color=[health_color(item["score"]) for item in scored],
            line=dict(width=0),
        ),
        text=[f"{item['score']:.0f}" for item in scored],
        textposition="outside",
        cliponaxis=False,
        textfont=dict(color=THEME["text"], size=13),
        hovertemplate="<b>%{y}</b><br>Score %{x:.0f} / 100<extra></extra>",
    ))

    fig.update_yaxes(title_text=None)
    fig.update_xaxes(
        title_text="Score (0-100)",
        range=[0, 112],
        tickvals=[0, 25, 50, 75, 100],
    )

    height = max(240, 54 * len(scored) + 70)

    return _style_figure(fig, height=height, legend=False)


def health_breakdown_table(components):

    rows = []

    for item in components:

        applied = (
            f"{item['effective_weight']:.0f}%"
            if item["available"] and item["effective_weight"] is not None
            else "0%"
        )
        base = f"{item['weight']}%"
        component_score = item["score"] if item["available"] else None

        if not item["inputs"]:

            rows.append({
                "component": item["name"],
                "component_score": component_score,
                "metric": "Window result" if item["available"] else "Not scored",
                "value": item["reason"] or "Not available",
                "metric_score": component_score,
                "rule": "",
                "base_weight": base,
                "applied_weight": applied,
            })

            continue

        for entry in item["inputs"]:

            rows.append({
                "component": item["name"],
                "component_score": component_score,
                "metric": entry["label"],
                "value": entry["value"],
                "metric_score": entry["score"],
                "rule": entry["rule"],
                "base_weight": base,
                "applied_weight": applied,
            })

    return pd.DataFrame(rows)


def render_health_methodology(components):

    rows = []

    for item in components:

        rules = "".join(
            f'<div class="gs-method__rule"><b>{esc(label)}:</b> {esc(rule)}</div>'
            for label, rule in item["rules"]
        )

        status = ""

        if not item["available"]:
            status = (
                f'<div class="gs-method__rule">'
                f'<span class="gs-pill gs-pill--warn">Not scored</span> {esc(item["reason"])}'
                f'</div>'
            )

        rows.append(f"""
        <div class="gs-method__row">
            <div class="gs-method__name">{esc(item['name'])}
                <span class="gs-method__weight">Base weight {item['weight']}%</span>
            </div>
            <div class="gs-method__body">{esc(item['summary'])}{rules}{status}</div>
        </div>
        """)

    with card_open(
        "health_method",
        "How the score is calculated",
        "Each component is scored 0-100 from the rules below. The overall score is the weighted average of the components that could be scored.",
    ):
        render_html(f"""
        <div class="gs-method">
            {''.join(rows)}
            <div class="gs-method__foot">
                Overall bands: Healthy is 75 or above, Moderate is 50 to 74, Needs attention is below 50.
                Components without data are left out and the remaining weights are rescaled to 100%.
                All inputs come from the selected analysis window.
            </div>
        </div>
        """)


def render_health_score(analysis):

    health = analysis.get("health_score")

    if not health:
        return

    section_header(
        "Repository Health Score",
        "A 0-100 score built from activity, collaboration, issue, pull request and release signals, with every input shown.",
        "activity",
    )

    components = health["components"]

    if health["overall"] is None:

        empty_state(
            "Health score unavailable",
            "Select at least one of Commits, Contributors, Issues, Pull Requests or Releases so there is data to score.",
            "activity",
        )

        return

    def component_card(item):

        if item["available"]:
            value = f"{item['score']:.0f}"
            hint = f"Applied weight {item['effective_weight']:.0f}%"
        else:
            value = "N/A"
            hint = "Not scored"

        return {
            "label": item["name"],
            "value": value,
            "icon": HEALTH_ICONS[item["key"]],
            "tone": health_tone(item["score"]) if item["available"] else "",
            "hint": hint,
        }

    overall_card = {
        "label": "Overall Health",
        "value": f"{health['overall']} / 100",
        "icon": "trending",
        "tone": health_tone(health["overall"]),
        "hint": f"{health['label']} · {health['available_count']} of {health['total_count']} components scored",
    }

    cards = [component_card(item) for item in components]

    kpi_grid([overall_card] + cards[:2])
    kpi_grid(cards[2:])

    unscored = [item for item in components if not item["available"]]

    if unscored:

        details = " ".join(f"{item['name']}: {item['reason']}" for item in unscored)

        notice(
            "info",
            "Some components were not scored",
            f"The overall score uses {health['available_count']} of {health['total_count']} components, "
            f"with the remaining weights rescaled to 100%. {details}",
        )

    scored = [item for item in components if item["available"]]

    visual_card(
        "health_components",
        "Component scores",
        "Score of each component behind the overall health score, and the full breakdown table.",
        fig=health_components_figure(components) if scored else None,
        df=health_breakdown_table(components),
        column_config={
            "component": st.column_config.TextColumn("Component"),
            "component_score": st.column_config.NumberColumn("Component score", format="%.0f"),
            "metric": st.column_config.TextColumn("Metric"),
            "value": st.column_config.TextColumn("Value", width="medium"),
            "metric_score": st.column_config.NumberColumn("Metric score", format="%.0f"),
            "rule": st.column_config.TextColumn("How it is scored", width="large"),
            "base_weight": st.column_config.TextColumn("Base weight"),
            "applied_weight": st.column_config.TextColumn("Applied weight"),
        },
        height=360,
    )

    render_health_methodology(components)


def render_repository_overview(repository, owner, repo):

    section_header(
        "Repository Overview",
        "Headline numbers for the repository, pulled directly from the GitHub API.",
        "package",
    )

    full_name = repository.get("full_name") or f"{owner}/{repo}"
    name_parts = full_name.split("/", 1)
    owner_part, repo_part = (name_parts + [repo])[:2] if len(name_parts) == 2 else (owner, repo)
    avatar_url = ((repository.get("owner") or {}).get("avatar_url"))
    homepage = repository.get("homepage")
    topics = repository.get("topics") or []
    archived = repository.get("archived")

    avatar_html = (
        f'<img src="{esc(avatar_url)}" alt="" />' if avatar_url else icon("github", 26, 1.7)
    )

    chips = [f'<span class="gs-chip">{icon("branch", 13)}{esc(repository.get("default_branch", "N/A"))}</span>']

    if repository.get("license"):

        license_name = (repository.get("license") or {}).get("name")

        if license_name:
            chips.append(f'<span class="gs-chip">{icon("scale", 13)}{esc(license_name)}</span>')

    if homepage:
        chips.append(
            f'<a class="gs-chip" href="{esc(homepage)}" target="_blank" rel="noopener">'
            f'{icon("upload", 13)}{esc(homepage)}</a>'
        )

    if archived:
        chips.append(f'<span class="gs-chip gs-chip--warn">{icon("lock", 13)}Archived</span>')

    for topic in topics[:6]:
        chips.append(f'<span class="gs-chip gs-chip--topic">{esc(topic)}</span>')

    render_html(f"""
    <div class="gs-repo">
        <div class="gs-avatar">{avatar_html}</div>
        <div class="gs-repo__body">
            <div class="gs-repo__label">Repository</div>
            <div class="gs-repo__name">
                <a href="{esc(github_url(owner, repo))}" target="_blank" rel="noopener">
                    <span class="owner">{esc(owner_part)}</span><span class="sep">/</span>{esc(repo_part)}
                </a>
            </div>
            <div class="gs-repo__desc">{esc(repository.get('description') or 'No description available.')}</div>
            <div class="gs-repo__chips">{''.join(chips)}</div>
        </div>
    </div>
    """)

    st.write("")

    kpi_grid([
        {"label": "Stars", "value": fmt_int(repository.get("stargazers_count", 0)), "icon": "star", "tone": "warning"},
        {"label": "Forks", "value": fmt_int(repository.get("forks_count", 0)), "icon": "fork", "tone": "blue"},
        {"label": "Open Issues", "value": fmt_int(repository.get("open_issues_count", 0)), "icon": "issue", "tone": ""},
        {"label": "Primary Language", "value": repository.get("language") or "N/A", "icon": "code", "tone": "violet", "wrap_text": True},
    ])


def render_commits_section(analysis):

    section_header(
        "Commit Analysis",
        "Volume and cadence of commits fetched from the repository's commit history.",
        "commit",
    )

    metrics = analysis["commit_metrics"]
    trend = analysis["commit_activity_trend"]
    monthly_metrics = analysis["commit_monthly_metrics"]
    monthly_trend = analysis["commit_monthly_trend"]
    commits_df = analysis["commits"]

    kpi_grid([
        {"label": "Total Commits", "value": fmt_int(metrics["total_commits"]), "icon": "commit"},
        {"label": "Unique Contributors", "value": fmt_int(metrics["unique_contributors"]), "icon": "users", "tone": "violet"},
        {"label": "Avg Commits / Day", "value": f"{metrics['average_commits_per_day']:.2f}", "icon": "activity", "tone": "blue"},
        {"label": "Active Days", "value": fmt_int(trend["active_days"]), "icon": "calendar", "tone": "success"},
    ])

    if commits_df.empty:
        empty_state("No commit data", "GitHub returned no commits for this repository.", "commit")
        return

    table = commits_df[["date", "author", "message", "sha"]].copy()
    table["sha"] = table["sha"].astype(str).str.slice(0, 7)
    table = table.sort_values("date", ascending=False)

    commit_fig = commit_trend_figure(commits_df)
    commit_config = {
        "date": st.column_config.DatetimeColumn("Date", format="D MMM YYYY, HH:mm"),
        "author": st.column_config.TextColumn("Author"),
        "message": st.column_config.TextColumn("Message", width="large"),
        "sha": st.column_config.TextColumn("SHA"),
    }

    visual_card(
        "commits_activity",
        "Commits over time",
        "Commit activity over time and the detailed commit log.",
        fig=commit_fig,
        df=table,
        column_config=commit_config,
        height=360,
    )

    if not monthly_trend.empty:
        monthly_fig = commit_monthly_figure(monthly_trend)
        with card_open("commits_monthly", "Monthly commit activity", "Commits, active days and contributors per month."):
            monthly_action_cols = st.columns([1, 0.12], gap="small")
            with monthly_action_cols[1]:
                st.markdown('<div class="gs-expand-btn">', unsafe_allow_html=True)
                if st.button("Expand", key="commits_monthly_expand", width="stretch"):
                    expanded_view(
                        "Monthly commit activity",
                        fig=monthly_fig,
                        height=560,
                    )
                st.markdown('</div>', unsafe_allow_html=True)
            render_chart(monthly_fig)

    insight_items = [
        {
            "icon": "calendar",
            "title": "Activity window",
            "body_html": f"First commit on <strong>{esc(trend['first_commit_date'])}</strong>, "
                         f"most recent on <strong>{esc(trend['latest_commit_date'])}</strong>.",
        },
        {
            "icon": "trending",
            "title": "Busiest day",
            "body_html": f"<strong>{esc(trend['most_active_day'])}</strong> had "
                         f"<strong>{fmt_int(trend['most_active_day_commits'])} commit(s)</strong>, the most of any day.",
        },
    ]

    if monthly_metrics:
        insight_items.append({
            "icon": "calendar",
            "title": "Busiest month",
            "body_html": f"<strong>{esc(monthly_metrics['most_active_month'])}</strong> had "
                         f"<strong>{fmt_int(monthly_metrics['most_active_month_commits'])} commit(s)</strong>, "
                         f"averaging <strong>{monthly_metrics['average_commits_per_active_month']:.1f}</strong> "
                         f"per active month across {fmt_int(monthly_metrics['active_months'])} month(s).",
        })

    insight_cards(insight_items)


def render_contributors_section(analysis):

    section_header(
        "Contributor Analysis",
        "Who contributes to the repository and how concentrated that contribution is.",
        "users",
    )

    metrics = analysis["contributor_metrics"]
    concentration = analysis["contributor_concentration"]
    contributors_df = analysis["contributors"]

    kpi_grid([
        {"label": "Contributors Analyzed", "value": fmt_int(metrics["total_contributors"]), "icon": "users"},
        {"label": "Top Contributor", "value": metrics["top_contributor"], "icon": "user", "tone": "violet", "wrap_text": True},
        {"label": "Top Contributor Share", "value": format_percentage(concentration["top_contributor_concentration"]), "icon": "percent", "tone": "blue"},
        {"label": "Top 3 Share", "value": format_percentage(concentration["top_3_contributor_concentration"]), "icon": "trending", "tone": "success"},
    ])

    if contributors_df.empty:
        empty_state("No contributor data", "GitHub returned no contributors for this repository.", "users")
        return

    contributor_config = {
        "username": st.column_config.TextColumn("Username"),
        "contributions": st.column_config.NumberColumn("Contributions", format="%d"),
        "contribution_percentage": st.column_config.ProgressColumn(
            "Share",
            format="%.2f%%",
            min_value=0,
            max_value=max(float(contributors_df["contribution_percentage"].max()), 1.0),
        ),
    }

    visual_card(
        "contributors_activity",
        "Top contributors",
        "Contribution distribution and the detailed contributor table.",
        fig=contributors_figure(contributors_df),
        df=contributors_df,
        column_config=contributor_config,
        height=360,
    )

    insight_cards([
        {
            "icon": "user",
            "title": "Contribution concentration",
            "body_html": f"<strong>{esc(metrics['top_contributor'])}</strong> accounts for "
                         f"<strong>{format_percentage(concentration['top_contributor_concentration'])}</strong> of analyzed contributions.",
        },
        {
            "icon": "users",
            "title": "Top 3 combined",
            "body_html": f"The top 3 contributors together make up "
                         f"<strong>{format_percentage(concentration['top_3_contributor_concentration'])}</strong> of all contributions.",
        },
    ])


def render_issues_section(analysis):

    section_header(
        "Issue Analysis",
        "Open versus closed issues, and how quickly they're resolved.",
        "issue",
    )

    metrics = analysis["issue_metrics"]
    issues_df = analysis["issues"]

    kpi_grid([
        {"label": "Total Issues", "value": fmt_int(metrics["total_issues"]), "icon": "issue"},
        {"label": "Open", "value": fmt_int(metrics["open_issues"]), "icon": "alert", "tone": "warning"},
        {"label": "Closed", "value": fmt_int(metrics["closed_issues"]), "icon": "check", "tone": "success"},
        {"label": "Closure Rate", "value": format_percentage(metrics["closure_rate"]), "icon": "percent", "tone": "blue"},
    ])

    if issues_df.empty:
        empty_state("No issue data", "GitHub returned no issues for this repository.", "issue")
        return

    state_counts = issues_df["state"].value_counts().to_dict()
    table = issues_df.sort_values("created_at", ascending=False)
    issue_config = {
        "number": st.column_config.NumberColumn("#", format="%d"),
        "title": st.column_config.TextColumn("Title", width="large"),
        "state": st.column_config.TextColumn("State"),
        "author": st.column_config.TextColumn("Author"),
        "created_at": st.column_config.DatetimeColumn("Opened", format="D MMM YYYY"),
        "closed_at": st.column_config.DatetimeColumn("Closed", format="D MMM YYYY"),
        "comments": st.column_config.NumberColumn("Comments", format="%d"),
    }

    visual_card(
        "issues_activity",
        "Issue activity",
        "Issue status distribution and the detailed issue table.",
        fig=status_donut_figure(state_counts, {"open": THEME["warning"], "closed": THEME["success"]}),
        df=table,
        column_config=issue_config,
        height=360,
    )

    insight_cards([
        {
            "icon": "percent",
            "title": "Closure rate",
            "body_html": f"<strong>{format_percentage(metrics['closure_rate'])}</strong> of fetched issues have been closed.",
        },
        {
            "icon": "alert",
            "title": "Currently open",
            "body_html": f"<strong>{fmt_int(metrics['open_issues'])}</strong> issue(s) remain open out of "
                         f"<strong>{fmt_int(metrics['total_issues'])}</strong> fetched.",
        },
    ], stack=True)


def render_pull_requests_section(analysis):

    section_header(
        "Pull Request Analysis",
        "Open, merged and closed pull requests, and how often changes get merged.",
        "pull_request",
    )

    metrics = analysis["pull_request_metrics"]
    pr_df = analysis["pull_requests"]

    kpi_grid([
        {"label": "Total PRs", "value": fmt_int(metrics["total_pull_requests"]), "icon": "pull_request"},
        {"label": "Open PRs", "value": fmt_int(metrics["open_pull_requests"]), "icon": "alert", "tone": "warning"},
        {"label": "Merged PRs", "value": fmt_int(metrics["merged_pull_requests"]), "icon": "merge", "tone": "violet"},
        {"label": "Merge Rate", "value": format_percentage(metrics["merge_rate"]), "icon": "percent", "tone": "success"},
    ])

    if pr_df.empty:
        empty_state("No pull request data", "GitHub returned no pull requests for this repository.", "pull_request")
        return

    state_counts = pr_df["state"].value_counts().to_dict()
    table = pr_df.sort_values("created_at", ascending=False)
    pr_config = {
        "number": st.column_config.NumberColumn("#", format="%d"),
        "title": st.column_config.TextColumn("Title", width="large"),
        "state": st.column_config.TextColumn("State"),
        "author": st.column_config.TextColumn("Author"),
        "created_at": st.column_config.DatetimeColumn("Opened", format="D MMM YYYY"),
        "merged_at": st.column_config.DatetimeColumn("Merged", format="D MMM YYYY"),
        "closed_at": st.column_config.DatetimeColumn("Closed", format="D MMM YYYY"),
        "comments": st.column_config.NumberColumn("Comments", format="%d"),
    }

    visual_card(
        "pr_activity",
        "Pull request activity",
        "Pull request status distribution and the detailed pull request table.",
        fig=status_donut_figure(state_counts, {"open": THEME["warning"], "closed": THEME["accent"]}),
        df=table,
        column_config=pr_config,
        height=360,
    )

    insight_cards([
        {
            "icon": "merge",
            "title": "Merge rate",
            "body_html": f"<strong>{format_percentage(metrics['merge_rate'])}</strong> of fetched pull requests have been merged.",
        },
        {
            "icon": "alert",
            "title": "Currently open",
            "body_html": f"<strong>{fmt_int(metrics['open_pull_requests'])}</strong> pull request(s) are still open.",
        },
    ], stack=True)


def render_languages_section(analysis):

    section_header(
        "Programming Language Analysis",
        "Language mix by bytes of code, as reported by the GitHub Languages API.",
        "code",
    )

    languages_df = analysis["languages"]

    if languages_df.empty:
        empty_state("No language data", "GitHub returned no language breakdown for this repository.", "code")
        return

    total_bytes = languages_df["bytes"].sum()
    top_row = languages_df.iloc[0]
    polyglot_count = int((languages_df["percentage"] >= 1.0).sum())

    kpi_grid([
        {"label": "Languages Detected", "value": fmt_int(len(languages_df)), "icon": "code"},
        {"label": "Primary Language", "value": top_row["language"], "icon": "star", "tone": "warning", "wrap_text": True},
        {"label": "Primary Share", "value": format_percentage(top_row["percentage"]), "icon": "percent", "tone": "blue"},
        {"label": "Total Code Size", "value": fmt_bytes(total_bytes), "icon": "package", "tone": "success"},
    ])

    language_config = {
        "language": st.column_config.TextColumn("Language"),
        "bytes": st.column_config.NumberColumn("Bytes", format="%d"),
        "percentage": st.column_config.ProgressColumn("Share", format="%.2f%%", min_value=0, max_value=100),
    }

    visual_card(
        "languages_activity",
        "Language distribution",
        "Language distribution and the detailed language table.",
        fig=languages_figure(languages_df),
        df=languages_df,
        column_config=language_config,
        height=360,
    )

    insight_cards([
        {
            "icon": "star",
            "title": "Dominant language",
            "body_html": f"<strong>{esc(top_row['language'])}</strong> makes up "
                         f"<strong>{format_percentage(top_row['percentage'])}</strong> of the codebase by size.",
        },
        {
            "icon": "code",
            "title": "Language diversity",
            "body_html": f"<strong>{polyglot_count}</strong> language(s) each account for at least 1% of the codebase.",
        },
    ], stack=True)


def render_releases_section(analysis, owner, repo):

    section_header(
        "Release Analysis",
        "Release history and cadence, newest first.",
        "tag",
    )

    metrics = analysis["release_metrics"]
    releases_df = analysis["releases"]

    has_cadence = metrics.get("total_releases", 0) >= 2
    avg_days_value = f"{metrics['average_days_between_releases']:.1f} days" if has_cadence else "N/A"
    per_month_value = f"{metrics['releases_per_month']:.2f}/mo" if has_cadence else "N/A"

    kpi_grid([
        {"label": "Total Releases", "value": fmt_int(metrics["total_releases"]), "icon": "tag"},
        {"label": "Latest Release", "value": metrics["latest_release"], "icon": "package", "tone": "violet", "wrap_text": True},
        {"label": "Avg Days Between Releases", "value": avg_days_value, "icon": "clock", "tone": "blue"},
        {"label": "Release Frequency", "value": per_month_value, "icon": "trending", "tone": "success"},
    ])

    if releases_df.empty:
        empty_state("No release data", "This repository has no published releases.", "tag")
        return

    ordered = releases_df.sort_values("published_at", ascending=False, na_position="last")
    release_fig = releases_timeline_figure(releases_df)
    release_config = {
        "tag": st.column_config.TextColumn("Tag"),
        "name": st.column_config.TextColumn("Name", width="medium"),
        "author": st.column_config.TextColumn("Author"),
        "published_at": st.column_config.DatetimeColumn("Published", format="D MMM YYYY"),
        "draft": st.column_config.CheckboxColumn("Draft"),
        "prerelease": st.column_config.CheckboxColumn("Pre-release"),
    }

    visual_card(
        "releases_activity",
        "Release timeline",
        "Release timeline and the complete release table.",
        fig=release_fig,
        df=ordered,
        column_config=release_config,
        column_order=["tag", "name", "author", "published_at", "draft", "prerelease"],
        height=360,
    )

    if has_cadence:
        insight_cards([
            {
                "icon": "clock",
                "title": "Release cadence",
                "body_html": f"New releases ship roughly every <strong>{metrics['average_days_between_releases']:.1f} days</strong>, "
                             f"about <strong>{metrics['releases_per_month']:.2f} per month</strong>.",
            },
        ], stack=True)

    items = []

    for _, row in ordered.head(12).iterrows():

        pre_class = " gs-tl__item--pre" if row.get("prerelease") else ""
        pills = ""

        if row.get("draft"):
            pills += '<span class="gs-pill gs-pill--muted">Draft</span> '

        if row.get("prerelease"):
            pills += '<span class="gs-pill gs-pill--warn">Pre-release</span>'

        published = fmt_date(row.get("published_at")) if not is_missing(row.get("published_at")) else "Unpublished"
        link = github_url(owner, repo, f"releases/tag/{quote(str(row['tag']))}")

        items.append(f"""
        <div class="gs-tl__item{pre_class}">
            <div class="gs-tl__dot"></div>
            <div style="min-width:0;">
                <div class="gs-tl__top">
                    <a class="gs-tl__tag" href="{esc(link)}" target="_blank" rel="noopener">{esc(row['tag'])}</a>
                    {pills}
                </div>
                <div class="gs-tl__name">{esc(row['name'])}</div>
                <div class="gs-tl__meta">{esc(published)} &middot; {esc(row.get('author', 'Unknown'))}</div>
            </div>
        </div>
        """)

    with card_open("releases_list", "Recent releases", None):
        render_html(f'<div class="gs-tl">{"".join(items)}</div>')


def init_state():

    defaults = {
        "repo_url": "",
        "selected": set(ANALYSIS_OPTIONS),
        "selected_period": "All Time",
        "analysis": None,
        "analyzed_owner": None,
        "analyzed_repo": None,
        "error": None,
        "is_analyzing": False,
    }

    for key, value in defaults.items():

        if key not in st.session_state:
            st.session_state[key] = value


def toggle_analysis(name):

    if name in st.session_state.selected:
        st.session_state.selected.discard(name)
    else:
        st.session_state.selected.add(name)


def render_control_panel():

    with st.container(key="control_panel"):

        render_html(f"""
        <div class="gs-field-label">
            <b>{icon('github', 16)} Repository URL</b>
            <span>Public repositories only, e.g. https://github.com/pandas-dev/pandas</span>
        </div>
        """)

        with st.container(key="repo_field"):

            st.text_input(
                "Repository URL",
                key="repo_url",
                placeholder="https://github.com/owner/repository",
                label_visibility="collapsed",
            )

        top = st.columns([1, 1], gap="small")

        with top[0]:
            render_html('<div class="gs-field-label"><b>Analyses to run</b></div>')

        with top[1]:

            tool_cols = st.columns([1, 1, 6], gap="small")

            with tool_cols[0]:
                with st.container(key="atool_all"):
                    if st.button("Select all", key="select_all_btn"):
                        st.session_state.selected = set(ANALYSIS_OPTIONS)

            with tool_cols[1]:
                with st.container(key="atool_clear"):
                    if st.button("Clear", key="clear_all_btn"):
                        st.session_state.selected = set()

        with st.container(key="module_grid"):

            for name in ANALYSIS_OPTIONS:

                meta = ANALYSIS_META[name]
                is_on = name in st.session_state.selected

                with st.container(key=f"apick_{meta['slug']}"):

                    pick_class = "gs-pick gs-pick--on" if is_on else "gs-pick"
                    check_icon = icon("check", 12, 2.4) if is_on else ""

                    render_html(f"""
                    <div class="{pick_class}">
                        <div class="gs-pick__icon">{icon(meta['icon'], 19, 1.9)}</div>
                        <div>
                            <div class="gs-pick__title">{esc(name)}</div>
                            <div class="gs-pick__desc">{esc(meta['description'])}</div>
                        </div>
                        <div class="gs-pick__check">{check_icon}</div>
                    </div>
                    """)

                    st.button(
                        name,
                        key=f"apick_btn_{meta['slug']}",
                        on_click=toggle_analysis,
                        args=(name,),
                    )

        render_html(f"""
        <div class="gs-field-label">
            <b>{icon('calendar', 16)} Analysis period</b>
            <span>Choose the time window for time-based analysis modules</span>
        </div>
        """)

        st.selectbox(
            "Analysis period",
            PERIOD_OPTIONS,
            index=PERIOD_OPTIONS.index("All Time") if "All Time" in PERIOD_OPTIONS else 0,
            key="selected_period",
            label_visibility="collapsed",
        )

        render_html(
            f'<div class="gs-period-note">'
            f'<span class="gs-period-note__icon">{icon("calendar", 15, 1.9)}</span>'
            f'<span><b>Active analysis window:</b> {esc(st.session_state.selected_period)}</span>'
            f'<span class="gs-period-note__muted">Repository overview and language composition remain repository-level.</span>'
            f'</div>'
        )

        count = len(st.session_state.selected)
        summary = "No analyses selected — Repository Overview will still run." if count == 0 else (
            f"<b>{count}</b> of {len(ANALYSIS_OPTIONS)} analyses selected."
        )

        bottom = st.columns([3, 1.3], gap="medium", vertical_alignment="center")

        with bottom[0]:
            render_html(f'<div class="gs-foot-note">{summary}</div>')

        with bottom[1]:
            with st.container(key="analyze_cta"):
                analyze_clicked = st.button(
                    "Analyze repository",
                    key="analyze_btn",
                    icon=":material/search:",
                    width="stretch",
                )

    return analyze_clicked


def run_analysis():

    owner, repo = parse_github_url(st.session_state.repo_url)

    if not owner or not repo:

        st.session_state.error = (
            "invalid_url",
            "That doesn't look like a GitHub repository URL. "
            "Use the form https://github.com/owner/repository."
        )
        st.session_state.analysis = None

        return

    st.session_state.error = None

    placeholder = st.empty()

    with placeholder.container():
        loading_panel(owner, repo, sorted(st.session_state.selected), st.session_state.selected_period)

    try:

        analysis = analyze_repository(
            owner,
            repo,
            selected_analyses=list(st.session_state.selected) or None,
            period=st.session_state.selected_period,
        )

    except Exception as exc:

        placeholder.empty()

        st.session_state.analysis = None
        st.session_state.error = ("api_error", str(exc))

        return

    placeholder.empty()

    st.session_state.analysis = analysis
    st.session_state.analyzed_owner = owner
    st.session_state.analyzed_repo = repo
    st.session_state.ran_selected = list(st.session_state.selected)


def render_error(kind, message):

    if kind == "invalid_url":

        notice("warning", "Check the repository URL", message)
        return

    lowered = message.lower()

    if "rate limit" in lowered:

        notice(
            "error",
            "GitHub API rate limit reached",
            "RepoMetric has hit GitHub's API rate limit for this token. "
            "Add a GITHUB_TOKEN to raise the limit, or try again shortly.",
            detail=message,
        )

    elif "404" in message:

        notice(
            "error",
            "Repository not found",
            "GitHub returned a 404 for that repository. Check that it exists, is public, "
            "and that the owner/name are spelled correctly.",
            detail=message,
        )

    elif "403" in lowered:

        notice(
            "error",
            "Access denied by GitHub",
            "GitHub refused this request. The repository may be private, or the API token "
            "may lack the required permissions.",
            detail=message,
        )

    else:

        notice(
            "error",
            "Couldn't complete the analysis",
            "Something went wrong while talking to the GitHub API.",
            detail=message,
        )


def render_results():

    analysis = st.session_state.analysis
    owner = st.session_state.analyzed_owner
    repo = st.session_state.analyzed_repo
    selected = set(st.session_state.get("ran_selected", []))

    with st.container(key="results"):

        period_label = analysis.get("period", st.session_state.get("selected_period", "All Time"))
        period_start = analysis.get("period_start")
        period_end = analysis.get("period_end")
        date_detail = ""
        if period_start and period_end:
            date_detail = f' · {fmt_date(period_start)} – {fmt_date(period_end)}'
        elif str(period_label) == "All Time":
            date_detail = " · full available repository history"

        render_html(
            f'<div class="gs-period-note" style="margin-bottom:.6rem;">'
            f'<span class="gs-period-note__icon">{icon("calendar", 15, 1.9)}</span>'
            f'<span><b>Analysis window:</b> {esc(period_label)}{esc(date_detail)}</span>'
            f'</div>'
        )

        render_repository_overview(analysis["repository"], owner, repo)

        if selected:
            render_health_score(analysis)

        if "Commits" in selected:
            render_commits_section(analysis)

        if "Contributors" in selected:
            render_contributors_section(analysis)

        if "Issues" in selected:
            render_issues_section(analysis)

        if "Pull Requests" in selected:
            render_pull_requests_section(analysis)

        if "Languages" in selected:
            render_languages_section(analysis)

        if "Releases" in selected:
            render_releases_section(analysis, owner, repo)


def main():

    inject_styles()
    init_state()
    hero()

    analyze_clicked = render_control_panel()

    if analyze_clicked:
        run_analysis()

    st.write("")

    if st.session_state.error:

        kind, message = st.session_state.error
        render_error(kind, message)

    elif st.session_state.analysis is not None:

        render_results()

    else:

        empty_state(
            "Ready when you are",
            "Enter a public GitHub repository URL above, choose the analyses you want, "
            "and select Analyze repository to pull live data from the GitHub API.",
            "search",
        )


if __name__ == "__main__":
    main()
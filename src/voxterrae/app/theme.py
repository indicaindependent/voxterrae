"""VoxTerrae themes. Two variants: 'darkops' (WarHeatMap phosphor, default) and 'plain' (accessibility: same layout, no glow).
Colour carries meaning: theatre red/blue, phosphor = live/unread, cyan = links/system, muted = metadata."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Palette:
    bg: str; panel: str; panel2: str; grid: str
    phosphor: str; cyan: str; red: str; blue: str; amber: str
    text: str; muted: str; dim: str
    mono: str; body: str
    glow: bool

DARKOPS = Palette(
    bg="#05070a", panel="#0b1016", panel2="#0f161e", grid="#12202b",
    phosphor="#39ff88", cyan="#2fd6ff", red="#ff3b4e", blue="#3b8bff", amber="#ffb020",
    text="#d7e3ea", muted="#6b7f8c", dim="#3b4a55",
    mono='"Cascadia Code","JetBrains Mono","Consolas","DejaVu Sans Mono",monospace',
    body='"Inter","Segoe UI Variable","Segoe UI","DejaVu Sans",sans-serif',
    glow=True,
)
PLAIN = Palette(
    bg="#0e1116", panel="#151a21", panel2="#1a212a", grid="#242d38",
    phosphor="#7ee2a8", cyan="#6cc9e8", red="#ff6b78", blue="#6ea6ff", amber="#ffc45a",
    text="#e6edf3", muted="#8b9bab", dim="#4a5866",
    mono=DARKOPS.mono, body=DARKOPS.body, glow=False,
)
THEMES = {"darkops": DARKOPS, "plain": PLAIN}
BODY_PX = 14   # Pete's floor: never smaller than 14 px body text


def qss(p: Palette) -> str:
    return f"""
QWidget {{ background: {p.bg}; color: {p.text}; font-family: {p.body}; font-size: {BODY_PX}px; }}
QMainWindow, QDialog {{ background: {p.bg}; }}
QFrame#rail, QFrame#rooms, QFrame#mapRail {{ background: {p.panel}; border: 1px solid {p.grid}; border-radius: 8px; }}
QFrame#timeline {{ background: {p.bg}; border: 1px solid {p.grid}; border-radius: 8px; }}
QLabel#wordmark {{ font-family: {p.mono}; font-size: 18px; font-weight: 700; color: {p.phosphor}; letter-spacing: 3px; }}
QLabel#sectionHead {{ font-family: {p.mono}; font-size: 11px; color: {p.muted}; letter-spacing: 2px; }}
QLabel#roomTitle {{ font-family: {p.mono}; font-size: 15px; font-weight: 700; color: {p.text}; }}
QLabel#roomMeta {{ color: {p.muted}; font-size: 12px; }}
QLabel#divider {{ font-family: {p.mono}; font-size: 11px; color: {p.muted}; letter-spacing: 2px; }}
QLabel#typing {{ color: {p.muted}; font-style: italic; font-size: 12px; }}
QListWidget {{ background: transparent; border: none; outline: 0; }}
QListWidget#roomList::item {{ padding: 6px 10px; border-radius: 6px; color: {p.text}; }}
QListWidget#roomList::item:selected {{ background: {p.panel2}; color: {p.phosphor}; border-left: 2px solid {p.phosphor}; }}
QListWidget#roomList::item:hover {{ background: {p.panel2}; }}
QListView#timelineView {{ background: transparent; border: none; }}
QLineEdit#composer {{ background: {p.panel}; border: 1px solid {p.grid}; border-radius: 10px; padding: 10px 14px; color: {p.text}; font-size: {BODY_PX}px; selection-background-color: {p.cyan}; }}
QLineEdit#composer:focus {{ border: 1px solid {p.phosphor}; }}
QPushButton {{ background: {p.panel2}; border: 1px solid {p.grid}; border-radius: 8px; padding: 8px 14px; color: {p.text}; }}
QPushButton:hover {{ border-color: {p.cyan}; color: {p.cyan}; }}
QPushButton#primary {{ background: {p.phosphor}; color: {p.bg}; font-weight: 700; border: none; font-family: {p.mono}; letter-spacing: 1px; padding: 12px 22px; font-size: 15px; }}
QPushButton#primary:hover {{ background: {p.cyan}; }}
QLabel#eventRed {{ color: {p.red}; }} QLabel#eventBlue {{ color: {p.blue}; }}
QLabel#cardTitle {{ font-family: {p.mono}; font-size: 11px; color: {p.muted}; letter-spacing: 2px; }}
QFrame#card {{ background: {p.panel2}; border: 1px solid {p.grid}; border-radius: 8px; }}
QLabel#status {{ color: {p.muted}; font-size: 12px; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {p.grid}; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QToolTip {{ background: {p.panel2}; color: {p.text}; border: 1px solid {p.grid}; }}
"""

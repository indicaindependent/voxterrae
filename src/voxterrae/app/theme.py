"""VoxTerrae themes (0.1.2). Two variants: 'darkops' (WarHeatMap phosphor, default) and 'plain' (accessibility: same
layout, calmer colour). Colour carries meaning: theatre red/blue, phosphor = live/unread/me, cyan = links/system,
muted = metadata. Windows 11 surface language: 8 px radius, 1 px hairline borders, layered panels, no glow effects."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class Palette:
    bg: str; panel: str; panel2: str; panel3: str; grid: str; border: str
    phosphor: str; cyan: str; red: str; blue: str; amber: str
    text: str; muted: str; dim: str
    mono: str; body: str
    nicks: Tuple[str, ...]        # deterministic per-nick colours (all pass 4.5:1 on panel)
    glow: bool

DARKOPS = Palette(
    bg="#07090d", panel="#0c1219", panel2="#111a23", panel3="#16212c", grid="#15222d", border="#1c2b38",
    phosphor="#39ff88", cyan="#2fd6ff", red="#ff3b4e", blue="#4d8fff", amber="#ffb020",
    text="#dbe6ee", muted="#7d90a0", dim="#42525f",
    mono='"Cascadia Mono","Cascadia Code","JetBrains Mono","Consolas","DejaVu Sans Mono",monospace',
    body='"Segoe UI Variable Text","Segoe UI Variable","Segoe UI","Inter","DejaVu Sans",sans-serif',
    nicks=("#7fd1ff", "#ffb86b", "#c8a4ff", "#7be0b3", "#ff9db0", "#e0d36b", "#8ab4ff", "#f0a6ff"),
    glow=True,
)
PLAIN = Palette(
    bg="#0f1318", panel="#161c24", panel2="#1c242e", panel3="#222c38", grid="#26313d", border="#2f3c4a",
    phosphor="#7ee2a8", cyan="#6cc9e8", red="#ff6b78", blue="#7fb0ff", amber="#ffc45a",
    text="#e8eef4", muted="#96a6b6", dim="#56667a",
    mono=DARKOPS.mono, body=DARKOPS.body,
    nicks=("#9ad8ff", "#ffc38a", "#d4b8ff", "#9ae8c6", "#ffb3c2", "#e8dd8a", "#a6c6ff", "#f4bcff"),
    glow=False,
)
THEMES = {"darkops": DARKOPS, "plain": PLAIN}
BODY_PX = 14   # Pete's floor: never smaller than 14 px body text (Settings lets it go UP, never down)

def nick_color(p: Palette, nick: str) -> str:
    """Stable colour per nick: same person, same hue, every session, every room."""
    h = 0
    for ch in nick.lower().rstrip("_"): h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return p.nicks[h % len(p.nicks)]


def qss(p: Palette, body_px: int = BODY_PX) -> str:
    body_px = max(BODY_PX, int(body_px))
    return f"""
QWidget {{ background: {p.bg}; color: {p.text}; font-family: {p.body}; font-size: {body_px}px; }}
QMainWindow, QDialog {{ background: {p.bg}; }}
QLabel {{ background: transparent; }}
QFrame#rooms, QFrame#mapRail {{ background: {p.panel}; border: 1px solid {p.border}; border-radius: 8px; }}
QFrame#timeline {{ background: {p.bg}; border: 1px solid {p.border}; border-radius: 8px; }}
QWidget#roomHead {{ background: {p.panel}; border-bottom: 1px solid {p.border}; border-top-left-radius: 8px; border-top-right-radius: 8px; }}
QLabel#wordmark {{ font-family: {p.mono}; font-size: 17px; font-weight: 700; color: {p.phosphor}; letter-spacing: 3px; }}
QLabel#sectionHead {{ font-family: {p.mono}; font-size: 11px; color: {p.muted}; letter-spacing: 2px; }}
QLabel#roomTitle {{ font-family: {p.mono}; font-size: 15px; font-weight: 700; color: {p.text}; }}
QLabel#roomMeta {{ color: {p.muted}; font-size: 12px; }}
QLabel#typing {{ color: {p.muted}; font-style: italic; font-size: 12px; }}
QLabel#status {{ color: {p.muted}; font-size: 12px; }}
QLabel#hint {{ color: {p.dim}; font-size: 12px; }}
QLabel#eventRed {{ color: {p.red}; }} QLabel#eventBlue {{ color: {p.blue}; }}
QLabel#cardTitle {{ font-family: {p.mono}; font-size: 11px; color: {p.muted}; letter-spacing: 2px; }}
QFrame#card {{ background: {p.panel2}; border: 1px solid {p.border}; border-radius: 8px; }}
QFrame#banner {{ background: {p.panel2}; border: 1px solid {p.amber}; border-radius: 8px; }}
QLabel#bannerText {{ color: {p.amber}; font-size: 13px; }}
QFrame#emptyState {{ background: transparent; }}
QLabel#emptyTitle {{ color: {p.muted}; font-size: 15px; }}
QLabel#emptyBody {{ color: {p.dim}; font-size: 13px; }}
QListWidget, QListView {{ background: transparent; border: none; outline: 0; }}
QListView#timelineView {{ background: transparent; border: none; }}
QListWidget#members::item {{ padding: 5px 8px; border-radius: 6px; }}
QListWidget#members::item:hover {{ background: {p.panel2}; }}
QListWidget#members::item:selected {{ background: {p.panel3}; }}
QPlainTextEdit#composer {{ background: {p.panel}; border: 1px solid {p.border}; border-radius: 10px; padding: 8px 12px; color: {p.text}; font-size: {body_px}px; selection-background-color: {p.cyan}; selection-color: {p.bg}; }}
QPlainTextEdit#composer:focus {{ border: 1px solid {p.phosphor}; }}
QPlainTextEdit#composer[warn="true"] {{ border: 1px solid {p.amber}; }}
QPlainTextEdit#composer:disabled {{ color: {p.dim}; border-color: {p.grid}; }}
QLineEdit {{ background: {p.panel}; border: 1px solid {p.border}; border-radius: 8px; padding: 8px 12px; color: {p.text}; selection-background-color: {p.cyan}; selection-color: {p.bg}; }}
QLineEdit:focus {{ border: 1px solid {p.phosphor}; }}
QLineEdit#composer {{ border-radius: 10px; padding: 10px 14px; }}
QLineEdit#filter {{ padding: 5px 10px; font-size: 12px; background: {p.panel2}; }}
QPushButton {{ background: {p.panel2}; border: 1px solid {p.border}; border-radius: 8px; padding: 7px 14px; color: {p.text}; }}
QPushButton:hover {{ background: {p.panel3}; border-color: {p.dim}; }}
QPushButton:pressed {{ background: {p.panel}; }}
QPushButton:disabled {{ color: {p.dim}; border-color: {p.grid}; }}
QPushButton#primary {{ background: {p.phosphor}; color: {p.bg}; font-weight: 700; border: none; font-family: {p.mono}; letter-spacing: 1px; padding: 12px 22px; font-size: 15px; }}
QPushButton#primary:hover {{ background: {p.cyan}; }}
QPushButton#iconBtn {{ background: transparent; border: none; border-radius: 6px; padding: 4px; }}
QPushButton#iconBtn:hover {{ background: {p.panel3}; }}
QPushButton#sendBtn {{ background: {p.panel2}; border: 1px solid {p.border}; border-radius: 8px; padding: 6px; }}
QPushButton#sendBtn:hover {{ border-color: {p.phosphor}; }}
QPushButton#sendBtn:disabled {{ background: transparent; border-color: {p.grid}; }}
QPushButton#jumpBtn {{ background: {p.panel3}; border: 1px solid {p.border}; border-radius: 14px; padding: 5px 12px 5px 8px; color: {p.text}; font-size: 12px; }}
QPushButton#jumpBtn:hover {{ border-color: {p.phosphor}; color: {p.phosphor}; }}
QPushButton#pill {{ background: {p.panel3}; border: 1px solid {p.border}; border-radius: 10px; padding: 2px 10px; font-size: 12px; color: {p.muted}; }}
QPushButton#pill:hover {{ color: {p.text}; }}
QPushButton#pillAccent {{ background: {p.panel3}; border: 1px solid {p.phosphor}; border-radius: 10px; padding: 2px 10px; font-size: 12px; color: {p.phosphor}; }}
QMenu {{ background: {p.panel2}; border: 1px solid {p.border}; border-radius: 8px; padding: 6px; }}
QMenu::item {{ padding: 7px 26px 7px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: {p.panel3}; color: {p.text}; }}
QMenu::separator {{ height: 1px; background: {p.border}; margin: 6px 4px; }}
QMenu::item:disabled {{ color: {p.dim}; }}
QComboBox {{ background: {p.panel2}; border: 1px solid {p.border}; border-radius: 8px; padding: 6px 10px; }}
QComboBox QAbstractItemView {{ background: {p.panel2}; border: 1px solid {p.border}; selection-background-color: {p.panel3}; }}
QSpinBox {{ background: {p.panel2}; border: 1px solid {p.border}; border-radius: 8px; padding: 5px 8px; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {p.dim}; border-radius: 4px; background: {p.panel2}; }}
QCheckBox::indicator:checked {{ background: {p.phosphor}; border-color: {p.phosphor}; }}
QTabWidget::pane {{ border: 1px solid {p.border}; border-radius: 8px; top: -1px; }}
QTabBar::tab {{ background: transparent; color: {p.muted}; padding: 8px 14px; border: none; }}
QTabBar::tab:selected {{ color: {p.text}; border-bottom: 2px solid {p.phosphor}; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 8px; }}
QSplitter::handle:hover {{ background: {p.grid}; border-radius: 4px; }}
QStatusBar {{ background: {p.bg}; color: {p.muted}; font-size: 12px; border-top: 1px solid {p.grid}; }}
QStatusBar::item {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p.grid}; border-radius: 4px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {p.dim}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ height: 0; }}
QToolTip {{ background: {p.panel3}; color: {p.text}; border: 1px solid {p.border}; padding: 6px 8px; border-radius: 6px; font-size: 12px; }}
QListWidget#palette::item {{ padding: 8px 10px; border-radius: 6px; }}
QListWidget#palette::item:selected {{ background: {p.panel3}; color: {p.phosphor}; }}
QFrame#paletteFrame {{ background: {p.panel2}; border: 1px solid {p.border}; border-radius: 10px; }}
QLabel#kbd {{ font-family: {p.mono}; font-size: 11px; color: {p.muted}; border: 1px solid {p.border}; border-radius: 4px; padding: 1px 5px; background: {p.panel3}; }}
"""

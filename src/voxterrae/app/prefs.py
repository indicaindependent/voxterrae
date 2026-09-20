"""Preferences (0.1.2): one dataclass backed by QSettings, plus the Settings dialog. Every value has a safe default,
so a missing or corrupt settings store never blocks launch. Body text can be made larger, never smaller than 14 px."""
from __future__ import annotations
from dataclasses import dataclass, asdict, fields
from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QSpinBox, QTabWidget, QVBoxLayout, QWidget, QHBoxLayout, QPushButton)
from .theme import BODY_PX, THEMES

@dataclass
class Prefs:
    handle: str = ""
    theme: str = "darkops"
    font_px: int = BODY_PX
    compact: bool = False           # single-line IRC layout instead of header + body
    show_time_always: bool = False  # timestamps on grouped lines too (default: on hover)
    notify_mentions: bool = True
    notify_dms: bool = True
    notify_sound: bool = False
    close_to_tray: bool = True      # Windows 11 pattern: X hides to the tray, Quit lives in the tray menu
    start_minimized: bool = False
    show_rail: bool = True
    fold_presence: bool = True      # fold join/part/quit lines
    confirm_links: bool = False     # ask before opening a link in the browser
    update_check: bool = True

    @classmethod
    def load(cls, s: QSettings) -> "Prefs":
        p = cls()
        for f in fields(cls):
            v = s.value("prefs/" + f.name, None)
            if v is None: continue
            try:
                if f.type == "bool" or isinstance(getattr(p, f.name), bool): v = str(v).lower() in ("1", "true", "yes")
                elif isinstance(getattr(p, f.name), int): v = int(v)
                else: v = str(v)
                setattr(p, f.name, v)
            except Exception: pass
        p.font_px = max(BODY_PX, min(22, int(p.font_px)))
        if p.theme not in THEMES: p.theme = "darkops"
        return p
    def save(self, s: QSettings):
        for k, v in asdict(self).items(): s.setValue("prefs/" + k, v)
        s.sync()

class SettingsDialog(QDialog):
    applied = Signal(object)
    def __init__(self, prefs: Prefs, parent=None):
        super().__init__(parent); self.setWindowTitle("Settings · VoxTerrae"); self.setMinimumWidth(460); self.prefs = prefs
        tabs = QTabWidget(); lay = QVBoxLayout(self); lay.addWidget(tabs)
        # General
        g = QWidget(); gf = QFormLayout(g); gf.setLabelAlignment(Qt.AlignRight)
        self.handle = QLineEdit(prefs.handle); self.handle.setPlaceholderText("your nick on both networks"); gf.addRow("Handle", self.handle)
        self.theme = QComboBox(); self.theme.addItems(list(THEMES)); self.theme.setCurrentText(prefs.theme); gf.addRow("Theme", self.theme)
        self.font_px = QSpinBox(); self.font_px.setRange(BODY_PX, 22); self.font_px.setValue(prefs.font_px); self.font_px.setSuffix(" px"); gf.addRow("Message text", self.font_px)
        self.compact = QCheckBox("Compact lines (time · nick · text on one line)"); self.compact.setChecked(prefs.compact); gf.addRow("", self.compact)
        self.times = QCheckBox("Always show timestamps"); self.times.setChecked(prefs.show_time_always); gf.addRow("", self.times)
        self.fold = QCheckBox("Fold join / leave lines"); self.fold.setChecked(prefs.fold_presence); gf.addRow("", self.fold)
        self.rail = QCheckBox("Show the right-hand rail (map, members)"); self.rail.setChecked(prefs.show_rail); gf.addRow("", self.rail)
        note = QLabel("Handle and theme changes apply at the next connect."); note.setObjectName("hint"); gf.addRow("", note)
        tabs.addTab(g, "General")
        # Notifications
        n = QWidget(); nf = QFormLayout(n)
        self.n_m = QCheckBox("When someone mentions my handle"); self.n_m.setChecked(prefs.notify_mentions); nf.addRow("", self.n_m)
        self.n_d = QCheckBox("Direct messages"); self.n_d.setChecked(prefs.notify_dms); nf.addRow("", self.n_d)
        self.n_s = QCheckBox("Play the system alert sound"); self.n_s.setChecked(prefs.notify_sound); nf.addRow("", self.n_s)
        tabs.addTab(n, "Notifications")
        # Window & privacy
        w = QWidget(); wf = QFormLayout(w)
        self.tray = QCheckBox("Closing the window keeps VoxTerrae running in the tray"); self.tray.setChecked(prefs.close_to_tray); wf.addRow("", self.tray)
        self.startmin = QCheckBox("Start minimised to the tray"); self.startmin.setChecked(prefs.start_minimized); wf.addRow("", self.startmin)
        self.links = QCheckBox("Ask before opening links in the browser"); self.links.setChecked(prefs.confirm_links); wf.addRow("", self.links)
        self.upd = QCheckBox("Check voxterrae.app for a newer version at launch (one GET, no identifiers)"); self.upd.setChecked(prefs.update_check); wf.addRow("", self.upd)
        tabs.addTab(w, "Window and privacy")
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply); lay.addWidget(bb)
        bb.accepted.connect(lambda: (self._apply(), self.accept())); bb.rejected.connect(self.reject); bb.button(QDialogButtonBox.Apply).clicked.connect(self._apply)
    def _apply(self):
        p = self.prefs
        p.handle = self.handle.text().strip(); p.theme = self.theme.currentText(); p.font_px = self.font_px.value(); p.compact = self.compact.isChecked(); p.show_time_always = self.times.isChecked()
        p.fold_presence = self.fold.isChecked(); p.show_rail = self.rail.isChecked(); p.notify_mentions = self.n_m.isChecked(); p.notify_dms = self.n_d.isChecked(); p.notify_sound = self.n_s.isChecked()
        p.close_to_tray = self.tray.isChecked(); p.start_minimized = self.startmin.isChecked(); p.confirm_links = self.links.isChecked(); p.update_check = self.upd.isChecked()
        self.applied.emit(p)

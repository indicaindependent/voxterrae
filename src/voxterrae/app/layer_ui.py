"""Dialogs for the VoxTerrae Layer: the one-screen consent and the profile editor."""
from __future__ import annotations
import asyncio, json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QPlainTextEdit, QDialogButtonBox, QCheckBox, QWidget)

CONSENT_TEXT = (
    "VoxTerrae can add a thin layer over plain IRC: a profile card, reactions, threaded replies and a list of who else is "
    "here with VoxTerrae. Other IRC users see ordinary text (a reply also posts a short quote line so they can follow).\n\n"
    "What leaves this computer: your nick, a small hash of each message you send (never the text), your reactions, and "
    "the profile you choose to write. What never leaves: message text, direct messages, your key.\n\n"
    "Your nick is verified once per session by a one-time code that cablepair sends you over IRC. No account, no email, "
    "no password. /layer wipe erases everything the layer holds about you; Settings → Layer turns it off."
)

class ConsentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("The VoxTerrae Layer"); self.setMinimumWidth(520)
        lay = QVBoxLayout(self); t = QLabel(CONSENT_TEXT); t.setWordWrap(True); t.setTextInteractionFlags(Qt.TextSelectableByMouse); lay.addWidget(t)
        self.on = QCheckBox("Use the layer (recommended)"); self.on.setChecked(True); lay.addWidget(self.on)
        bb = QDialogButtonBox(QDialogButtonBox.Ok); bb.accepted.connect(self.accept); lay.addWidget(bb)
    def enabled(self) -> bool: return self.on.isChecked()

class ProfileEditor(QDialog):
    def __init__(self, layer, parent=None):
        super().__init__(parent); self.layer = layer; self.setWindowTitle("Your VoxTerrae profile"); self.setMinimumWidth(480)
        lay = QVBoxLayout(self); f = QFormLayout(); lay.addLayout(f)
        self.display = QLineEdit(); self.display.setMaxLength(32); f.addRow("Display name", self.display)
        self.pronouns = QLineEdit(); self.pronouns.setMaxLength(24); f.addRow("Pronouns", self.pronouns)
        self.tz = QLineEdit(); self.tz.setMaxLength(48); self.tz.setPlaceholderText("e.g. America/New_York"); f.addRow("Time zone", self.tz)
        self.accent = QLineEdit(); self.accent.setMaxLength(7); self.accent.setPlaceholderText("#ff5500"); f.addRow("Accent colour", self.accent)
        self.bio = QPlainTextEdit(); self.bio.setPlaceholderText("300 characters"); self.bio.setFixedHeight(80); f.addRow("Bio", self.bio)
        self.links = QPlainTextEdit(); self.links.setPlaceholderText("one per line: label https://…  (max 5)"); self.links.setFixedHeight(70); f.addRow("Links", self.links)
        self.avatar_key = ""; self.banner_key = ""
        self.status = QLabel(""); self.status.setObjectName("hint"); lay.addWidget(self.status)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self._save); bb.rejected.connect(self.reject); lay.addWidget(bb)
        asyncio.get_event_loop().create_task(self._load())
    async def _load(self):
        if not self.layer.ready: self.status.setText("Layer not verified yet: /layer verify first."); return
        p = await self.layer.get_profile(self.layer.nick) or {}
        self.display.setText(p.get("display_name") or ""); self.pronouns.setText(p.get("pronouns") or ""); self.tz.setText(p.get("tz") or "")
        self.accent.setText(p.get("accent") or ""); self.bio.setPlainText(p.get("bio") or "")
        self.links.setPlainText("\n".join(f"{l.get('label', 'link')} {l.get('url', '')}" for l in p.get("links") or []))
        self.avatar_key = (p.get("avatar") or "").rsplit("/", 1)[-1]; self.banner_key = (p.get("banner") or "").rsplit("/", 1)[-1]
    def payload(self) -> dict:
        links = []
        for line in self.links.toPlainText().splitlines()[:5]:
            parts = line.strip().split()
            if not parts: continue
            url = next((x for x in parts if x.startswith("https://")), None)
            if url: links.append({"label": " ".join(x for x in parts if x != url)[:24] or "link", "url": url})
        return {"display_name": self.display.text().strip(), "pronouns": self.pronouns.text().strip(), "tz": self.tz.text().strip(),
                "accent": self.accent.text().strip() or None, "bio": self.bio.toPlainText().strip()[:300], "links": links,
                "avatar_key": self.avatar_key or None, "banner_key": self.banner_key or None}
    def _save(self):
        async def go():
            ok = await self.layer.put_profile(self.payload())
            if ok: self.accept()
            else: self.status.setText("Save failed (layer not verified, or the server refused a field).")
        asyncio.get_event_loop().create_task(go())

"""Composer (0.1.2): a growing multi-line box. Enter sends, Shift+Enter breaks a line, Tab completes nicks and
commands, Up/Down walks your sent history, a command popup opens on "/", and a byte counter warns before the
IRC line limit. Public surface kept from the old QLineEdit composer: text(), setText(), clear(),
setPlaceholderText(), signals textEdited(str) and submitted(str)."""
from __future__ import annotations
from typing import Callable, List, Optional, Tuple
from PySide6.QtCore import QEvent, QSize, Qt, Signal, QTimer
from PySide6.QtGui import QFontMetrics, QKeyEvent, QTextCursor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPlainTextEdit, QVBoxLayout, QWidget

# IRC lines are 512 bytes including ":nick!user@host PRIVMSG #room :" and CRLF; 400 leaves room for a long hostmask.
SAFE_BYTES = 400
COMMANDS: List[Tuple[str, str]] = [
    ("/join #room", "enter a room (EFnet joins nothing for you)"), ("/part", "leave this room"), ("/me does something", "action line"),
    ("/msg nick text", "private message"), ("/search words", "local full-text search on this network"), ("/ask question", "ask Axiom (HOME rooms)"),
    ("/reply <msgid> text", "reply with context (HOME)"), ("/react <msgid> 🔥", "react to a message (HOME)"), ("/topic", "show the room topic"),
    ("/whois nick", "who is that"), ("/nick newname", "change your handle"), ("/clear", "clear this view"), ("/help", "this list"),
]

class CommandPopup(QFrame):
    picked = Signal(str)
    def __init__(self, parent: QWidget):
        super().__init__(parent); self.setObjectName("paletteFrame"); self.list = QListWidget(self); self.list.setObjectName("palette"); self.list.setFrameShape(QFrame.NoFrame)
        lay = QVBoxLayout(self); lay.setContentsMargins(6, 6, 6, 6); lay.addWidget(self.list); self.hide()
        self.list.itemClicked.connect(lambda it: self.picked.emit(it.data(Qt.UserRole)))
    def refill(self, prefix: str) -> int:
        self.list.clear()
        for cmd, desc in COMMANDS:
            if cmd.split(" ")[0].startswith(prefix.lower()):
                it = QListWidgetItem(f"{cmd}    {desc}"); it.setData(Qt.UserRole, cmd.split(" ")[0] + " "); self.list.addItem(it)
        if self.list.count(): self.list.setCurrentRow(0)
        return self.list.count()
    def current(self) -> Optional[str]:
        it = self.list.currentItem(); return it.data(Qt.UserRole) if it else None
    def move_sel(self, step: int):
        n = self.list.count()
        if n: self.list.setCurrentRow((self.list.currentRow() + step) % n)

class Composer(QPlainTextEdit):
    submitted = Signal(str); textEdited = Signal(str); escape = Signal(); typing = Signal()
    MAX_LINES = 6
    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("composer"); self.setTabChangesFocus(False); self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded); self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history: List[str] = []; self._hist_i = -1; self._draft = ""; self.completions: Callable[[], List[str]] = lambda: []
        self._tab_state: Optional[Tuple[str, int, List[str]]] = None
        self.popup: Optional[CommandPopup] = None
        self.document().contentsChanged.connect(self._grow); self.textChanged.connect(self._on_change); self._grow()
    # ---- old QLineEdit surface ----
    def text(self) -> str: return self.toPlainText()
    def setText(self, t: str):
        self.setPlainText(t); c = self.textCursor(); c.movePosition(QTextCursor.End); self.setTextCursor(c)
    def set_popup(self, popup: CommandPopup):
        self.popup = popup; popup.picked.connect(lambda cmd: (self.setText(cmd), popup.hide(), self.setFocus()))
    # ---- sizing ----
    def _grow(self):
        fm = QFontMetrics(self.font())
        rows = self.document().size().height()
        h = int(fm.lineSpacing() * max(1, min(self.MAX_LINES, rows)) + 22)
        self.setFixedHeight(max(fm.lineSpacing() + 22, min(h, fm.lineSpacing() * self.MAX_LINES + 22)))
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded if rows > self.MAX_LINES else Qt.ScrollBarAlwaysOff)
    def sizeHint(self) -> QSize: return QSize(400, self.height())
    def bytes_used(self) -> int:
        longest = max((len(l.encode("utf-8")) for l in self.toPlainText().split("\n")), default=0); return longest
    def _on_change(self):
        t = self.toPlainText(); self.textEdited.emit(t); self._tab_state = None
        warn = self.bytes_used() > SAFE_BYTES
        if self.property("warn") != warn: self.setProperty("warn", warn); self.style().unpolish(self); self.style().polish(self)
        if self.popup is not None:
            if t.startswith("/") and " " not in t and "\n" not in t and self.popup.refill(t):
                self.popup.adjustSize(); self.popup.setFixedWidth(max(320, self.width() - 40)); self.popup.setFixedHeight(min(280, 12 + 36 * self.popup.list.count()))
                pos = self.mapTo(self.popup.parentWidget(), self.rect().topLeft()); self.popup.move(pos.x(), pos.y() - self.popup.height() - 6); self.popup.show(); self.popup.raise_()
            else: self.popup.hide()
    # ---- keys ----
    def keyPressEvent(self, e: QKeyEvent):
        k = e.key(); mods = e.modifiers(); pop = self.popup is not None and self.popup.isVisible()
        if k == Qt.Key_Escape:
            if pop: self.popup.hide(); return
            self.escape.emit(); return
        if pop and k in (Qt.Key_Up, Qt.Key_Down): self.popup.move_sel(-1 if k == Qt.Key_Up else 1); return
        if pop and k in (Qt.Key_Tab, Qt.Key_Return, Qt.Key_Enter) and self.popup.current():
            self.setText(self.popup.current()); self.popup.hide(); return
        if k in (Qt.Key_Return, Qt.Key_Enter):
            if mods & Qt.ShiftModifier: super().keyPressEvent(e); return
            self._submit(); return
        if k == Qt.Key_Tab: self._complete(); return
        if k == Qt.Key_Up and self._at_first_line() and self.history and (not self.toPlainText() or self._hist_i != -1):
            if self._hist_i == -1: self._draft = self.toPlainText(); self._hist_i = len(self.history)
            if self._hist_i > 0: self._hist_i -= 1; self.setText(self.history[self._hist_i])
            return
        if k == Qt.Key_Down and self._hist_i != -1 and self._at_last_line():
            self._hist_i += 1
            if self._hist_i >= len(self.history): self._hist_i = -1; self.setText(self._draft)
            else: self.setText(self.history[self._hist_i])
            return
        super().keyPressEvent(e); self.typing.emit()
    def _at_first_line(self) -> bool: return self.textCursor().blockNumber() == 0
    def _at_last_line(self) -> bool: return self.textCursor().blockNumber() == self.document().blockCount() - 1
    def _submit(self):
        t = self.toPlainText().strip()
        if not t: return
        if not self.history or self.history[-1] != t: self.history.append(t); self.history = self.history[-100:]
        self._hist_i = -1; self._draft = ""; self.submitted.emit(t); self.clear(); self._grow()
    def _complete(self):
        c = self.textCursor(); text = self.toPlainText(); pos = c.position()
        if self._tab_state and self._tab_state[0] == text:
            _, start, cands = self._tab_state; cands = cands[1:] + cands[:1]
        else:
            start = pos
            while start > 0 and not text[start - 1].isspace(): start -= 1
            frag = text[start:pos]
            if not frag: return
            if frag.startswith("/"): cands = [cmd.split(" ")[0] for cmd, _ in COMMANDS if cmd.startswith(frag.lower())]
            else: cands = [n for n in self.completions() if n.lower().startswith(frag.lower())]
            if not cands: return
        word = cands[0] + (": " if start == 0 and not cands[0].startswith("/") else " ")
        new = text[:start] + word; self.blockSignals(True); self.setPlainText(new + text[pos:]); self.blockSignals(False)
        cur = self.textCursor(); cur.setPosition(len(new)); self.setTextCursor(cur); self._grow()
        self._tab_state = (self.toPlainText(), start, cands); self.textEdited.emit(self.toPlainText())
    def insertFromMimeData(self, source):
        if source.hasText(): self.insertPlainText(source.text().replace("\r\n", "\n").replace("\r", "\n"))
        else: super().insertFromMimeData(source)

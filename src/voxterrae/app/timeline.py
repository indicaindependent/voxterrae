"""Timeline model + delegate: grouped messages, day dividers, reply strips, reaction chips, read line."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from PySide6.QtCore import QAbstractListModel, QModelIndex, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen, QTextDocument, QTextOption
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem
from .theme import Palette, BODY_PX

@dataclass
class Item:
    kind: str                 # "msg" | "day" | "read" | "system"
    nick: str = ""
    text: str = ""
    ts: Optional[datetime] = None
    msgid: str = ""
    reply_to_nick: str = ""
    reply_to_text: str = ""
    reactions: Dict[str, int] = field(default_factory=dict)
    is_me: bool = False
    is_bot: bool = False
    highlight: bool = False
    grouped: bool = False     # same nick as previous within 5 min -> no header

class TimelineModel(QAbstractListModel):
    def __init__(self):
        super().__init__(); self.items: List[Item] = []; self._by_id: Dict[str, int] = {}
    def rowCount(self, parent=QModelIndex()): return len(self.items)
    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.UserRole: return self.items[index.row()]
        if role == Qt.DisplayRole: return self.items[index.row()].text
        return None
    def append(self, it: Item):
        if it.kind == "msg":
            if it.msgid and it.msgid in self._by_id: return  # dedupe (store-level rule mirrored in the view)
            last_day = next((x.ts.date() for x in reversed(self.items) if x.kind == "msg" and x.ts), None)
            if it.ts and last_day != it.ts.date():
                self._push(Item("day", ts=it.ts))
            prev = next((x for x in reversed(self.items) if x.kind in ("msg", "day", "read")), None)
            it.grouped = bool(prev and prev.kind == "msg" and prev.nick == it.nick and it.ts and prev.ts
                              and (it.ts - prev.ts).total_seconds() < 300 and not it.reply_to_nick)
        self._push(it)
        if it.msgid: self._by_id[it.msgid] = len(self.items) - 1
    def _push(self, it: Item):
        self.beginInsertRows(QModelIndex(), len(self.items), len(self.items)); self.items.append(it); self.endInsertRows()
    def react(self, msgid: str, emoji: str):
        i = self._by_id.get(msgid)
        if i is None: return
        it = self.items[i]; it.reactions[emoji] = it.reactions.get(emoji, 0) + 1
        self.dataChanged.emit(self.index(i), self.index(i))

class TimelineDelegate(QStyledItemDelegate):
    PAD = 10; GUTTER = 14; CHIP_H = 22
    def __init__(self, p: Palette, parent=None):
        super().__init__(parent); self.p = p
        self.f_body = QFont(); self.f_body.setPixelSize(BODY_PX)
        self.f_nick = QFont(); self.f_nick.setPixelSize(BODY_PX); self.f_nick.setBold(True)
        self.f_mono = QFont("DejaVu Sans Mono"); self.f_mono.setPixelSize(11); self.f_mono.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        self.f_small = QFont(); self.f_small.setPixelSize(12)
    def _doc(self, text: str, width: int) -> QTextDocument:
        d = QTextDocument(); d.setDefaultFont(self.f_body); d.setDocumentMargin(0)
        opt = QTextOption(); opt.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere); d.setDefaultTextOption(opt)
        d.setPlainText(text); d.setTextWidth(max(80, width)); return d
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        it: Item = index.data(Qt.UserRole); w = option.rect.width() or 600
        if it.kind in ("day", "read"): return QSize(w, 30)
        if it.kind == "system": return QSize(w, 26)
        h = self.PAD
        if not it.grouped: h += 20
        if it.reply_to_nick: h += 22
        h += int(self._doc(it.text, w - 2 * self.GUTTER).size().height()) + 4
        if it.reactions: h += self.CHIP_H + 6
        return QSize(w, h + self.PAD // 2)
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        it: Item = index.data(Qt.UserRole); p = self.p; r = option.rect
        painter.save(); painter.setRenderHint(QPainter.Antialiasing); painter.setRenderHint(QPainter.TextAntialiasing)
        if it.kind in ("day", "read"):
            label = it.ts.strftime("%a %d %b · %H:%M").upper() if (it.kind == "day" and it.ts) else "READ UP TO HERE"
            painter.setFont(self.f_mono); fm = QFontMetrics(self.f_mono); tw = fm.horizontalAdvance(label)
            cy = r.center().y(); pen = QPen(QColor(p.grid if it.kind == "day" else p.phosphor)); pen.setStyle(Qt.DashLine if it.kind == "read" else Qt.SolidLine)
            painter.setPen(pen); painter.drawLine(r.left() + self.GUTTER, cy, r.center().x() - tw // 2 - 10, cy); painter.drawLine(r.center().x() + tw // 2 + 10, cy, r.right() - self.GUTTER, cy)
            painter.setPen(QColor(p.muted if it.kind == "day" else p.phosphor)); painter.drawText(r, Qt.AlignCenter, label); painter.restore(); return
        if it.kind == "system":
            painter.setFont(self.f_small); painter.setPen(QColor(p.cyan)); painter.drawText(r.adjusted(self.GUTTER, 0, -self.GUTTER, 0), Qt.AlignVCenter | Qt.AlignLeft, "▸ " + it.text); painter.restore(); return
        if it.highlight:
            painter.fillRect(r, QColor(p.phosphor + "14")); painter.fillRect(QRect(r.left(), r.top(), 2, r.height()), QColor(p.phosphor))
        x = r.left() + self.GUTTER; y = r.top() + self.PAD // 2; wmax = r.width() - 2 * self.GUTTER
        if not it.grouped:
            painter.setFont(self.f_nick); col = p.phosphor if it.is_me else (p.cyan if it.is_bot else p.text)
            painter.setPen(QColor(col)); fm = QFontMetrics(self.f_nick); painter.drawText(x, y + fm.ascent(), it.nick)
            nx = x + fm.horizontalAdvance(it.nick) + 8
            if it.is_bot:
                painter.setFont(self.f_mono); painter.setPen(QColor(p.muted)); painter.drawText(nx, y + fm.ascent() - 1, "BOT"); nx += 34
            if it.ts:
                painter.setFont(self.f_small); painter.setPen(QColor(p.muted)); painter.drawText(nx, y + fm.ascent(), it.ts.strftime("%H:%M"))
            y += 20
        if it.reply_to_nick:
            painter.setPen(QPen(QColor(p.grid), 2)); painter.drawLine(x + 2, y + 4, x + 2, y + 16)
            painter.setFont(self.f_small); painter.setPen(QColor(p.muted))
            snippet = QFontMetrics(self.f_small).elidedText(f"↳ replying to {it.reply_to_nick}: {it.reply_to_text}", Qt.ElideRight, wmax - 12)
            painter.drawText(x + 10, y + 14, snippet); y += 22
        doc = self._doc(it.text, wmax); painter.translate(x, y)
        ctx_color = QColor(p.text); doc.setDefaultStyleSheet(""); painter.setPen(ctx_color)
        from PySide6.QtGui import QAbstractTextDocumentLayout
        ctx = QAbstractTextDocumentLayout.PaintContext(); ctx.palette.setColor(ctx.palette.ColorRole.Text, ctx_color)
        doc.documentLayout().draw(painter, ctx); painter.translate(-x, -y); y += int(doc.size().height()) + 6
        if it.reactions:
            cx = x
            for emoji, n in it.reactions.items():
                label = f"{emoji} {n}"; painter.setFont(self.f_small); tw = QFontMetrics(self.f_small).horizontalAdvance(label) + 16
                chip = QRectF(cx, y, tw, self.CHIP_H); painter.setPen(QPen(QColor(p.grid))); painter.setBrush(QColor(p.panel2)); painter.drawRoundedRect(chip, 11, 11)
                painter.setPen(QColor(p.text)); painter.drawText(chip, Qt.AlignCenter, label); cx += tw + 6
        painter.restore()

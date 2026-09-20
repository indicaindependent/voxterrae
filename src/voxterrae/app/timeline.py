"""Timeline model + delegate (0.1.2): grouped messages, day dividers, unread line, reply strips, reaction chips,
clickable links, per-nick colours, /me actions, folded join/part lines, hover actions (Reply / React / Copy) and a
compact single-line mode. Everything is painted by one delegate over a QListView, so 10k lines stay cheap."""
from __future__ import annotations
import html, re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from PySide6.QtCore import QAbstractListModel, QEvent, QModelIndex, QObject, QPoint, QRect, QRectF, QSize, Qt, Signal, QUrl
from PySide6.QtGui import QAbstractTextDocumentLayout, QColor, QDesktopServices, QFont, QFontMetrics, QPainter, QPen, QTextDocument, QTextOption, QCursor
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QToolTip
from .icons import pixmap
from .theme import Palette, BODY_PX, nick_color

URL_RE = re.compile(r"(?<![\w@])((?:https?://|www\.)[^\s<>\"'()\[\]{}]+)", re.I)
_TRAIL = ".,;:!?'\""

def linkify(text: str, me: str = "", p: Optional[Palette] = None) -> str:
    """Escape, then wrap URLs in anchors and the user's own nick in a mention span. Pure function, unit-tested."""
    out: List[str] = []; last = 0
    for m in URL_RE.finditer(text):
        url = m.group(1); end = m.end()
        while url and url[-1] in _TRAIL: url = url[:-1]; end -= 1
        out.append(_mention(html.escape(text[last:m.start()]), me, p))
        href = url if url.lower().startswith("http") else "https://" + url
        out.append(f'<a href="{html.escape(href, quote=True)}">{html.escape(url)}</a>')
        last = end
    out.append(_mention(html.escape(text[last:]), me, p))
    return "".join(out).replace("\n", "<br/>")

def _mention(escaped: str, me: str, p: Optional[Palette]) -> str:
    if not me or not p: return escaped
    return re.sub(rf"(?<![\w-])({re.escape(html.escape(me))})(?![\w-])",
                  rf'<span style="color:{p.phosphor};font-weight:600">\1</span>', escaped, flags=re.I)

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
    sub: str = ""             # system sub-kind: "presence" (join/part/quit, folded) | "topic" | "error" | "" (info)
    meta: Dict[str, list] = field(default_factory=dict)   # presence fold: {"joined": [...], "left": [...]}

    @property
    def is_action(self) -> bool: return self.kind == "msg" and self.text.startswith("* ")

class TimelineModel(QAbstractListModel):
    def __init__(self):
        super().__init__(); self.items: List[Item] = []; self._by_id: Dict[str, int] = {}
    def rowCount(self, parent=QModelIndex()): return len(self.items)
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.items): return None
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
                              and (it.ts - prev.ts).total_seconds() < 300 and not it.reply_to_nick and not it.is_action and not prev.is_action)
        elif it.kind == "system" and it.sub == "presence" and self.items and self.items[-1].kind == "system" and self.items[-1].sub == "presence":
            last = self.items[-1]   # fold: "maya_k joined · 2 left" instead of a wall of one-liners
            for k in ("joined", "left", "renamed"): last.meta.setdefault(k, []).extend(it.meta.get(k, []))
            last.text = presence_text(last.meta); i = len(self.items) - 1
            self.dataChanged.emit(self.index(i), self.index(i)); return
        self._push(it)
        if it.msgid: self._by_id[it.msgid] = len(self.items) - 1
    def _push(self, it: Item):
        self.beginInsertRows(QModelIndex(), len(self.items), len(self.items)); self.items.append(it); self.endInsertRows()
    def react(self, msgid: str, emoji: str):
        i = self._by_id.get(msgid)
        if i is None: return
        it = self.items[i]; it.reactions[emoji] = it.reactions.get(emoji, 0) + 1
        self.dataChanged.emit(self.index(i), self.index(i))
    def last_msg(self) -> Optional[Item]:
        return next((x for x in reversed(self.items) if x.kind == "msg"), None)
    def count_msgs(self) -> int: return sum(1 for x in self.items if x.kind == "msg")

def presence_text(meta: Dict[str, list]) -> str:
    def part(names: List[str], verb: str) -> str:
        if not names: return ""
        if len(names) <= 3: return ", ".join(names) + f" {verb}"
        return f"{names[0]}, {names[1]} and {len(names) - 2} others {verb}"
    renamed = ", ".join(meta.get("renamed", [])[-3:])
    return " · ".join(x for x in (part(meta.get("joined", []), "joined"), part(meta.get("left", []), "left"), renamed) if x)

def presence_item(nick: str, joined: bool) -> Item:
    return Item("system", sub="presence", text=f"{nick} {'joined' if joined else 'left'}", meta={"joined": [nick] if joined else [], "left": [] if joined else [nick]})


class TimelineDelegate(QStyledItemDelegate):
    """Paints rows; also owns hover state, link hit-testing and the hover action pills."""
    action = Signal(str, object)          # "reply" | "react" | "copy", Item
    link_opened = Signal(str)
    PAD = 8; GUTTER = 14; CHIP_H = 22; TIME_W = 44; ACTION_W = 26
    def __init__(self, p: Palette, parent=None, body_px: int = BODY_PX):
        super().__init__(parent); self.p = p; self.me = ""; self.compact = False; self.show_time_always = False; self.home = True
        self.hover_row = -1; self.hover_pos = QPoint(); self.set_font_px(body_px)
    def set_font_px(self, px: int):
        px = max(BODY_PX, int(px)); self.body_px = px
        self.f_body = QFont(); self.f_body.setPixelSize(px)
        self.f_nick = QFont(); self.f_nick.setPixelSize(px); self.f_nick.setBold(True)
        self.f_mono = QFont("Cascadia Mono"); self.f_mono.setStyleHint(QFont.Monospace); self.f_mono.setPixelSize(11); self.f_mono.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        self.f_time = QFont("Cascadia Mono"); self.f_time.setStyleHint(QFont.Monospace); self.f_time.setPixelSize(max(11, px - 3))
        self.f_small = QFont(); self.f_small.setPixelSize(max(12, px - 2))
        self.f_action = QFont(); self.f_action.setPixelSize(px); self.f_action.setItalic(True)
        self.HEAD_H = px + 8; self._docs: Dict[Tuple[str, int, int], QTextDocument] = {}
    # ---- documents -------------------------------------------------------------------------------------------
    def _doc(self, it: Item, width: int) -> QTextDocument:
        key = (id(it), width, self.body_px)
        d = self._docs.get(key)
        if d is not None: return d
        if len(self._docs) > 600: self._docs.clear()
        d = QTextDocument(); d.setDefaultFont(self.f_action if it.is_action else self.f_body); d.setDocumentMargin(0)
        opt = QTextOption(); opt.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere); d.setDefaultTextOption(opt)
        d.setDefaultStyleSheet(f"a {{ color: {self.p.cyan}; text-decoration: underline; }}")
        body = it.text[2:] if it.is_action else it.text
        col = self.p.muted if it.is_action else self.p.text
        prefix = f'<span style="color:{nick_color(self.p, it.nick) if not it.is_me else self.p.phosphor};font-weight:600">{html.escape(it.nick)}</span> ' if it.is_action else ""
        d.setHtml(f'<span style="color:{col}">{prefix}{linkify(body, self.me, self.p)}</span>'); d.setTextWidth(max(80, width)); self._docs[key] = d; return d
    def _geom(self, it: Item, r: QRect) -> Tuple[int, int, int]:
        """(text_x, text_y, text_w) for a msg row, matching paint()."""
        if self.compact:
            x = r.left() + self.GUTTER + self.TIME_W + 8; y = r.top() + self.PAD // 2
            if not it.grouped and not it.is_action: x += QFontMetrics(self.f_nick).horizontalAdvance(it.nick) + 10
            return x, y, r.right() - self.GUTTER - x
        x = r.left() + self.GUTTER + self.TIME_W + 10; y = r.top() + self.PAD // 2
        if not it.grouped and not it.is_action: y += self.HEAD_H
        if it.reply_to_nick: y += 22
        return x, y, r.right() - self.GUTTER - x
    # ---- sizing -----------------------------------------------------------------------------------------------
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        it: Item = index.data(Qt.UserRole); w = option.rect.width() or 600
        if it is None: return QSize(w, 0)
        if it.kind in ("day", "read"): return QSize(w, 32)
        if it.kind == "system": return QSize(w, max(24, int(self._sys_doc(it, w).size().height()) + 10))
        x, y, tw = self._geom(it, QRect(0, 0, w, 10))
        h = y + int(self._doc(it, tw).size().height()) + 4
        if it.reactions: h += self.CHIP_H + 6
        return QSize(w, h + self.PAD // 2)
    def _sys_doc(self, it: Item, w: int) -> QTextDocument:
        key = (id(it), w, -1); d = self._docs.get(key)
        if d is not None: return d
        d = QTextDocument(); d.setDefaultFont(self.f_small); d.setDocumentMargin(0)
        opt = QTextOption(); opt.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere); d.setDefaultTextOption(opt)
        col = {"error": self.p.red, "topic": self.p.text, "presence": self.p.dim}.get(it.sub, self.p.muted)
        d.setDefaultStyleSheet(f"a {{ color: {self.p.cyan}; text-decoration: underline; }}")
        d.setHtml(f'<span style="color:{col}">{linkify(it.text)}</span>'); d.setTextWidth(max(80, w - 2 * self.GUTTER - 20)); self._docs[key] = d; return d
    # ---- painting ---------------------------------------------------------------------------------------------
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        it: Item = index.data(Qt.UserRole); p = self.p; r = option.rect
        if it is None: return
        painter.save(); painter.setRenderHint(QPainter.Antialiasing); painter.setRenderHint(QPainter.TextAntialiasing)
        hovered = index.row() == self.hover_row
        if it.kind in ("day", "read"):
            label = it.ts.strftime("%a %d %b").upper() if (it.kind == "day" and it.ts) else "NEW MESSAGES"
            painter.setFont(self.f_mono); fm = QFontMetrics(self.f_mono); tw = fm.horizontalAdvance(label)
            cy = r.center().y(); col = QColor(p.grid if it.kind == "day" else p.phosphor)
            painter.setPen(QPen(col, 1)); painter.drawLine(r.left() + self.GUTTER, cy, r.center().x() - tw // 2 - 12, cy); painter.drawLine(r.center().x() + tw // 2 + 12, cy, r.right() - self.GUTTER, cy)
            painter.setPen(QColor(p.muted if it.kind == "day" else p.phosphor)); painter.drawText(r, Qt.AlignCenter, label); painter.restore(); return
        if it.kind == "system":
            ic = {"error": ("warning", p.red), "topic": ("info", p.muted), "presence": ("dot", p.dim)}.get(it.sub, ("chevron", p.dim))
            painter.drawPixmap(r.left() + self.GUTTER, r.top() + 6, pixmap(ic[0], ic[1], 12))
            d = self._sys_doc(it, r.width()); painter.translate(r.left() + self.GUTTER + 20, r.top() + 5); d.documentLayout().draw(painter, QAbstractTextDocumentLayout.PaintContext()); painter.restore(); return
        if hovered: painter.fillRect(r, QColor(p.panel))
        if it.highlight:
            tint = QColor(p.phosphor); tint.setAlpha(18); painter.fillRect(r, tint); painter.fillRect(QRect(r.left(), r.top(), 2, r.height()), QColor(p.phosphor))
        x, y, wmax = self._geom(it, r); tx = r.left() + self.GUTTER
        ncol = p.phosphor if it.is_me else (p.cyan if it.is_bot else nick_color(p, it.nick))
        if self.compact:
            if it.ts and (not it.grouped or hovered or self.show_time_always):
                painter.setFont(self.f_time); painter.setPen(QColor(p.dim if it.grouped else p.muted)); painter.drawText(QRect(tx, y, self.TIME_W, self.body_px + 6), Qt.AlignLeft | Qt.AlignVCenter, it.ts.strftime("%H:%M"))
            if not it.grouped and not it.is_action:
                painter.setFont(self.f_nick); painter.setPen(QColor(ncol)); painter.drawText(QRect(tx + self.TIME_W + 8, y, x - tx - self.TIME_W - 8, self.body_px + 6), Qt.AlignLeft | Qt.AlignVCenter, it.nick)
        else:
            if it.is_action:
                if it.ts: painter.setFont(self.f_time); painter.setPen(QColor(p.muted)); painter.drawText(QRect(tx, y, self.TIME_W, self.body_px + 6), Qt.AlignLeft | Qt.AlignVCenter, it.ts.strftime("%H:%M"))
            elif not it.grouped:
                hy = r.top() + self.PAD // 2
                painter.setFont(self.f_nick); painter.setPen(QColor(ncol)); fm = QFontMetrics(self.f_nick)
                painter.drawText(QRect(x, hy, wmax, self.HEAD_H), Qt.AlignLeft | Qt.AlignVCenter, it.nick); nx = x + fm.horizontalAdvance(it.nick) + 8
                if it.is_bot:
                    painter.setFont(self.f_mono); painter.setPen(QPen(QColor(p.border))); painter.setBrush(QColor(p.panel2)); painter.drawRoundedRect(QRectF(nx, hy + 3, 30, self.HEAD_H - 6), 4, 4)
                    painter.setPen(QColor(p.muted)); painter.drawText(QRect(nx, hy, 30, self.HEAD_H), Qt.AlignCenter, "BOT"); nx += 36
                if it.ts:
                    painter.setFont(self.f_time); painter.setPen(QColor(p.muted)); painter.drawText(QRect(tx, hy, self.TIME_W, self.HEAD_H), Qt.AlignLeft | Qt.AlignVCenter, it.ts.strftime("%H:%M"))
            elif it.ts and (hovered or self.show_time_always):
                painter.setFont(self.f_time); painter.setPen(QColor(p.dim)); painter.drawText(QRect(tx, y, self.TIME_W, self.body_px + 6), Qt.AlignLeft | Qt.AlignVCenter, it.ts.strftime("%H:%M"))
            if it.reply_to_nick:
                ry = y - 22; painter.setPen(QPen(QColor(p.border), 2)); painter.drawLine(x + 2, ry + 5, x + 2, ry + 17)
                painter.setFont(self.f_small); painter.setPen(QColor(p.muted))
                snippet = QFontMetrics(self.f_small).elidedText(f"{it.reply_to_nick}: {it.reply_to_text}", Qt.ElideRight, wmax - 30)
                painter.drawPixmap(x + 9, ry + 4, pixmap("reply", p.muted, 12)); painter.drawText(QRect(x + 26, ry, wmax - 26, 22), Qt.AlignLeft | Qt.AlignVCenter, snippet)
        doc = self._doc(it, wmax); painter.translate(x, y); doc.documentLayout().draw(painter, QAbstractTextDocumentLayout.PaintContext()); painter.translate(-x, -y)
        y += int(doc.size().height()) + 6
        if it.reactions:
            cx = x
            for emoji, n in it.reactions.items():
                label = f"{emoji} {n}"; painter.setFont(self.f_small); tw = QFontMetrics(self.f_small).horizontalAdvance(label) + 16
                chip = QRectF(cx, y, tw, self.CHIP_H); painter.setPen(QPen(QColor(p.border))); painter.setBrush(QColor(p.panel2)); painter.drawRoundedRect(chip, 11, 11)
                painter.setPen(QColor(p.text)); painter.drawText(chip, Qt.AlignCenter, label); cx += tw + 6
        if hovered and it.msgid:
            for name, rect in self._action_rects(it, r):
                painter.setPen(QPen(QColor(p.border))); painter.setBrush(QColor(p.panel3)); painter.drawRoundedRect(QRectF(rect), 6, 6)
                painter.drawPixmap(rect.left() + 5, rect.top() + 5, pixmap(name, p.muted if not (self.hover_pos and rect.contains(self.hover_pos)) else p.text, 14))
        painter.restore()
    def _action_rects(self, it: Item, r: QRect) -> List[Tuple[str, QRect]]:
        names = (["reply", "react"] if self.home else []) + ["copy"]
        right = r.right() - self.GUTTER; out = []
        for n in reversed(names):
            out.append((n, QRect(right - self.ACTION_W, r.top() + 2, 24, 24))); right -= self.ACTION_W + 2
        return list(reversed(out))
    # ---- interaction -------------------------------------------------------------------------------------------
    def editorEvent(self, event, model, option, index) -> bool:
        it: Item = index.data(Qt.UserRole)
        if it is None: return False
        view = self.parent(); et = event.type()
        if et == QEvent.MouseMove:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            old = self.hover_row; self.hover_row = index.row(); self.hover_pos = pos
            over_link = self._link_at(it, option.rect, pos) if it.kind in ("msg", "system") else None
            over_action = it.kind == "msg" and it.msgid and any(rc.contains(pos) for _, rc in self._action_rects(it, option.rect))
            if view: view.viewport().setCursor(Qt.PointingHandCursor if (over_link or over_action) else Qt.ArrowCursor)
            if view and (old != self.hover_row): view.viewport().update()
            elif view: view.viewport().update(option.rect)
            return False
        if et == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            if it.kind == "msg" and it.msgid:
                for name, rc in self._action_rects(it, option.rect):
                    if rc.contains(pos): self.action.emit(name, it); return True
            href = self._link_at(it, option.rect, pos) if it.kind in ("msg", "system") else None
            if href: self.link_opened.emit(href); QDesktopServices.openUrl(QUrl(href)); return True
        return False
    def _link_at(self, it: Item, r: QRect, pos: QPoint) -> Optional[str]:
        if it.kind == "system":
            d = self._sys_doc(it, r.width()); lp = pos - QPoint(r.left() + self.GUTTER + 20, r.top() + 5)
        else:
            x, y, w = self._geom(it, r); d = self._doc(it, w); lp = pos - QPoint(x, y)
        href = d.documentLayout().anchorAt(lp)
        return href or None
    def helpEvent(self, event, view, option, index) -> bool:
        it: Item = index.data(Qt.UserRole)
        if it and it.kind == "msg" and it.ts:
            pos = event.pos(); href = self._link_at(it, option.rect, pos)
            QToolTip.showText(event.globalPos(), href or it.ts.strftime("%A %d %B %Y · %H:%M:%S"), view); return True
        return super().helpEvent(event, view, option, index)
    def leave(self):
        if self.hover_row != -1:
            self.hover_row = -1; v = self.parent()
            if v: v.viewport().update()

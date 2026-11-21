# -*- coding: utf-8 -*-
"""게이지·차트 SVG 생성 (자바스크립트 없이 서버에서 그림 → 검색엔진도 숫자를 읽을 수 있음)"""
import math
import os
import sys
from html import escape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

ZONES = config.ZONES


def zone_of(v):
    for mx, name, color in ZONES:
        if v <= mx:
            return name, color
    return ZONES[-1][1], ZONES[-1][2]


def _pt(cx, cy, r, v):
    a = math.pi * (1 - v / 100.0)          # 0 → 왼쪽, 100 → 오른쪽
    return cx + r * math.cos(a), cy - r * math.sin(a)


def gauge(score, size=260, title=""):
    """반원 게이지. score=None 이면 '準備中'"""
    w, h = 240, 140
    cx, cy, r = 120, 122, 96
    parts = ['<svg class="gauge" viewBox="0 0 %d %d" width="%d" role="img" aria-label="%s">' % (w, h, size, escape(title))]
    lo = 0
    for mx, name, color in ZONES:
        x1, y1 = _pt(cx, cy, r, lo + 0.6)
        x2, y2 = _pt(cx, cy, r, mx - 0.6 if mx < 100 else 100)
        parts.append('<path d="M%.1f %.1f A%d %d 0 0 1 %.1f %.1f" stroke="%s" stroke-width="20" fill="none" stroke-linecap="butt"/>' % (x1, y1, r, r, x2, y2, color))
        lo = mx + 1 if mx < 100 else mx
    for t in (0, 25, 50, 75, 100):
        x, y = _pt(cx, cy, r - 22, t)
        parts.append('<text x="%.1f" y="%.1f" class="g-tick">%d</text>' % (x, y + 4, t))
    if score is not None:
        nx, ny = _pt(cx, cy, r - 6, score)
        parts.append('<line x1="%d" y1="%d" x2="%.1f" y2="%.1f" class="g-needle"/>' % (cx, cy, nx, ny))
        parts.append('<circle cx="%d" cy="%d" r="7" class="g-hub"/>' % (cx, cy))
    parts.append("</svg>")
    return "".join(parts)


def history_chart(hist, width=760, height=280):
    """대만(실선) + 미국(점선) 추이. 배경에 5단계 구간 색"""
    pts = [h for h in hist if h.get("tw") is not None]
    if len(pts) < 2:
        return '<p class="muted">資料累積中，圖表將於近期顯示。</p>'
    L, R, T, B = 34, 12, 12, 30
    iw, ih = width - L - R, height - T - B
    n = len(pts)

    def X(i):
        return L + iw * i / (n - 1)

    def Y(v):
        return T + ih * (1 - v / 100.0)

    s = ['<svg class="chart" viewBox="0 0 %d %d" role="img" aria-label="台股恐懼貪婪指數走勢圖">' % (width, height)]
    lo = 0
    for mx, name, color in ZONES:
        s.append('<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="%s" opacity=".10"/>' % (L, Y(mx), iw, Y(lo) - Y(mx), color))
        lo = mx
    for v in (0, 25, 50, 75, 100):
        s.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="c-grid"/><text x="%d" y="%.1f" class="c-ylab">%d</text>' % (L, L + iw, Y(v), Y(v), L - 6, Y(v) + 4, v))
    step = max(1, n // 6)
    for i in range(0, n, step):
        d = pts[i]["date"]
        s.append('<text x="%.1f" y="%d" class="c-xlab">%s/%s</text>' % (X(i), height - 8, int(d[5:7]), int(d[8:10])))
    us = [(i, p["us"]) for i, p in enumerate(pts) if p.get("us") is not None]
    if len(us) > 1:
        s.append('<polyline class="c-us" points="%s"/>' % " ".join("%.1f,%.1f" % (X(i), Y(v)) for i, v in us))
    s.append('<polyline class="c-tw" points="%s"/>' % " ".join("%.1f,%.1f" % (X(i), Y(p["tw"])) for i, p in enumerate(pts)))
    # 점마다 툴팁(마우스를 올리면 날짜·값 표시)
    for i, p in enumerate(pts):
        tip = "%s 台股 %d" % (p["date"], p["tw"]) + (" / 美股 %d" % p["us"] if p.get("us") is not None else "")
        s.append('<circle cx="%.1f" cy="%.1f" r="5" class="c-hit"><title>%s</title></circle>' % (X(i), Y(p["tw"]), tip))
    last = pts[-1]
    s.append('<circle cx="%.1f" cy="%.1f" r="4.5" class="c-last"/>' % (X(n - 1), Y(last["tw"])))
    s.append("</svg>")
    return "".join(s)


def bar(value):
    name, color = zone_of(value)
    return ('<div class="bar" role="img" aria-label="%d分 %s"><span style="width:%d%%;background:%s"></span></div>'
            % (value, name, max(2, value), color))

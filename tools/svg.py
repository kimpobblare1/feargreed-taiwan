# -*- coding: utf-8 -*-
"""
그림(SVG) 생성 — 자바스크립트 없이 서버에서 그려서 검색엔진도 숫자를 읽을 수 있어요.
  dial()          메인 레이더 다이얼 (240도)
  radar()         7개 지표 레이더 차트  ← 恐貪雷達만의 시그니처
  scale_row()     4개 시장 비교 막대
  history_chart() 6개월 추이
  line_chart() / bar_chart()  인사이트 글용 범용 차트
"""
import math
import os
import sys
from html import escape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

ZONES = config.ZONES
INK = "#0F1E33"
GRID = "#DDE3EC"
MUTED = "#7A8899"


def zone_of(v):
    for mx, name, color in ZONES:
        if v <= mx:
            return name, color
    return ZONES[-1][1], ZONES[-1][2]


# ── 메인 다이얼 ────────────────────────────────────────────
def _polar(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def _arc(cx, cy, r, d0, d1):
    x0, y0 = _polar(cx, cy, r, d0)
    x1, y1 = _polar(cx, cy, r, d1)
    large = 1 if (d1 - d0) > 180 else 0
    return "M%.1f %.1fA%d %d 0 %d 1 %.1f %.1f" % (x0, y0, r, r, large, x1, y1)


def dial(score, size=300, dark=False, title=""):
    """240도 다이얼. 시작 150도 → 끝 390도(=30도)"""
    W = 260
    cx, cy, r = 130, 132, 104
    start, span = 150, 240

    def deg(v):
        return start + span * v / 100.0

    tick = "#9FB1C7" if dark else MUTED
    track = "rgba(255,255,255,.10)" if dark else "#EEF2F7"
    s = ['<svg class="dial" font-family="Noto Sans TC,Noto Sans CJK TC,sans-serif" viewBox="0 0 %d 236" width="%d" role="img" aria-label="%s">' % (W, size, escape(title))]
    # 레이더 동심원(점선)
    for rr in (40, 64, 88):
        s.append('<circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-dasharray="2 5"/>' % (cx, cy, rr, track))
    s.append('<path d="%s" stroke="%s" stroke-width="16" fill="none" stroke-linecap="round"/>' % (_arc(cx, cy, r, deg(0), deg(100)), track))
    lo = 0
    for mx, _n, color in ZONES:
        s.append('<path d="%s" stroke="%s" stroke-width="8" fill="none"/>' % (_arc(cx, cy, r, deg(lo) + 0.8, deg(mx) - 0.8), color))
        lo = mx
    for t in (0, 25, 50, 75, 100):
        x, y = _polar(cx, cy, r + 15, deg(t))
        s.append('<text x="%.1f" y="%.1f" fill="%s" font-size="10" text-anchor="middle" dominant-baseline="middle">%d</text>' % (x, y, tick, t))
    if score is not None:
        _n, color = zone_of(score)
        # 레이더 스윕(부채꼴)
        a0, a1 = deg(max(0, score - 7)), deg(score)
        x0, y0 = _polar(cx, cy, r - 12, a0)
        x1, y1 = _polar(cx, cy, r - 12, a1)
        s.append('<path d="M%d %d L%.1f %.1f A%d %d 0 0 1 %.1f %.1f Z" fill="%s" opacity=".16"/>' % (cx, cy, x0, y0, r - 12, r - 12, x1, y1, color))
        x, y = _polar(cx, cy, r - 12, a1)
        xi, yi = _polar(cx, cy, 58, a1)
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="3" stroke-linecap="round"/>' % (xi, yi, x, y, color))
        px, py = _polar(cx, cy, r, a1)
        s.append('<circle cx="%.1f" cy="%.1f" r="9" fill="%s" stroke="%s" stroke-width="3"/>' % (px, py, color, "#fff" if not dark else INK))
    s.append("</svg>")
    return "".join(s)


# ── 레이더 차트 (7개 지표) ─────────────────────────────────
def radar(items, size=540):
    """items: [(이름, 점수0~100), ...]"""
    n = len(items)
    if n < 3:
        return ""
    W, H = 540, 380
    cx, cy, R = 270, 192, 128

    def pt(i, v):
        a = -math.pi / 2 + 2 * math.pi * i / n
        return cx + R * v / 100.0 * math.cos(a), cy + R * v / 100.0 * math.sin(a)

    s = ['<svg class="radar" viewBox="0 0 %d %d" width="%d" role="img" aria-label="七項指標雷達圖">' % (W, H, size)]
    for lv in (25, 50, 75, 100):
        pts = " ".join("%.1f,%.1f" % pt(i, lv) for i in range(n))
        s.append('<polygon points="%s" fill="%s" stroke="%s"/>' % (pts, "#F7F9FC" if lv == 100 else "none", GRID))
    for i in range(n):
        x, y = pt(i, 100)
        s.append('<line x1="%d" y1="%d" x2="%.1f" y2="%.1f" stroke="%s"/>' % (cx, cy, x, y, GRID))
    avg = sum(v for _n, v in items) / n
    _z, color = zone_of(avg)
    poly = " ".join("%.1f,%.1f" % pt(i, max(3, v)) for i, (_n, v) in enumerate(items))
    s.append('<polygon points="%s" fill="%s" fill-opacity=".18" stroke="%s" stroke-width="2.5" stroke-linejoin="round"/>' % (poly, color, color))
    for i, (name, v) in enumerate(items):
        x, y = pt(i, max(3, v))
        c = zone_of(v)[1]
        s.append('<circle cx="%.1f" cy="%.1f" r="4.5" fill="%s" stroke="#fff" stroke-width="1.5"><title>%s %d</title></circle>' % (x, y, c, escape(name), v))
        lx, ly = pt(i, 122)
        anchor = "middle" if abs(lx - cx) < 20 else ("start" if lx > cx else "end")
        s.append('<text x="%.1f" y="%.1f" font-size="16" fill="%s" text-anchor="%s" dominant-baseline="middle">%s '
                 '<tspan font-weight="700" fill="%s">%d</tspan></text>' % (lx, ly, INK, anchor, escape(name), c, v))
    for lv in (50, 100):
        x, y = pt(0, lv)
        s.append('<text x="%.1f" y="%.1f" font-size="9" fill="%s" dx="4">%d</text>' % (x, y + 10, MUTED, lv))
    s.append("</svg>")
    return "".join(s)


# ── 4개 시장 비교 막대 ─────────────────────────────────────
def scale_row(score):
    """0~100 막대 위에 현재 위치 표시"""
    stops, lo = [], 0
    for mx, _n, c in ZONES:
        stops.append('<span style="flex:%d;background:%s"></span>' % (mx - lo, c))
        lo = mx
    mark = "" if score is None else '<i style="left:%.1f%%"></i>' % max(0, min(100, score))
    return '<div class="scale">%s%s</div>' % ("".join(stops), mark)


def bar(value):
    _n, color = zone_of(value)
    return '<div class="bar"><span style="width:%d%%;background:%s"></span></div>' % (max(2, value), color)


# ── 6개월 추이 ─────────────────────────────────────────────
def history_chart(hist, width=760, height=280):
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
    for mx, _n, color in ZONES:
        s.append('<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="%s" opacity=".08"/>' % (L, Y(mx), iw, Y(lo) - Y(mx), color))
        lo = mx
    for v in (0, 25, 50, 75, 100):
        s.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s"/><text x="%d" y="%.1f" class="c-ylab">%d</text>' % (L, L + iw, Y(v), Y(v), GRID, L - 6, Y(v) + 4, v))
    step = max(1, n // 6)
    for i in range(0, n, step):
        d = pts[i]["date"]
        s.append('<text x="%.1f" y="%d" class="c-xlab">%s/%s</text>' % (X(i), height - 8, int(d[5:7]), int(d[8:10])))
    us = [(i, p["us"]) for i, p in enumerate(pts) if p.get("us") is not None]
    if len(us) > 1:
        s.append('<polyline class="c-us" points="%s"/>' % " ".join("%.1f,%.1f" % (X(i), Y(v)) for i, v in us))
    area = "%.1f,%.1f " % (X(0), Y(0)) + " ".join("%.1f,%.1f" % (X(i), Y(p["tw"])) for i, p in enumerate(pts)) + " %.1f,%.1f" % (X(n - 1), Y(0))
    s.append('<defs><linearGradient id="twg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#12B5CB" stop-opacity=".28"/>'
             '<stop offset="1" stop-color="#12B5CB" stop-opacity="0"/></linearGradient></defs>')
    s.append('<polygon points="%s" fill="url(#twg)"/>' % area)
    s.append('<polyline class="c-tw" points="%s"/>' % " ".join("%.1f,%.1f" % (X(i), Y(p["tw"])) for i, p in enumerate(pts)))
    for i, p in enumerate(pts):
        tip = "%s 台股 %d" % (p["date"], p["tw"]) + (" / 美股 %d" % p["us"] if p.get("us") is not None else "")
        s.append('<circle cx="%.1f" cy="%.1f" r="5" class="c-hit"><title>%s</title></circle>' % (X(i), Y(p["tw"]), tip))
    last = pts[-1]
    s.append('<circle cx="%.1f" cy="%.1f" r="5" fill="%s" stroke="#fff" stroke-width="2"/>' % (X(n - 1), Y(last["tw"]), zone_of(last["tw"])[1]))
    s.append("</svg>")
    return "".join(s)


# ── 인사이트 글용 범용 차트 ────────────────────────────────
PALETTE = ["#163A6B", "#12B5CB", "#E8304F", "#F2A33A", "#7A8899"]


def _nice(lo, hi):
    if lo == hi:
        lo, hi = lo - 1, hi + 1
    span = hi - lo
    step = 10 ** math.floor(math.log10(span / 4))
    for m in (1, 2, 2.5, 5, 10):
        if span / (step * m) <= 5:
            step *= m
            break
    return math.floor(lo / step) * step, math.ceil(hi / step) * step, step


def line_chart(labels, series, title="", unit="", source="", width=760, height=300, zones=False):
    """labels: x축 이름 목록 / series: {"이름": [값...]} (None 허용)"""
    vals = [v for ys in series.values() for v in ys if v is not None]
    if not vals or len(labels) < 2:
        return ""
    lo, hi, step = (0, 100, 25) if zones else _nice(min(vals), max(vals))
    L, R, T, B = 56, 16, 16, 34
    iw, ih = width - L - R, height - T - B
    n = len(labels)

    def X(i):
        return L + iw * i / (n - 1)

    def Y(v):
        return T + ih * (1 - (v - lo) / (hi - lo))

    s = ['<svg viewBox="0 0 %d %d" class="chart" role="img" aria-label="%s">' % (width, height, escape(title))]
    if zones:
        z0 = 0
        for mx, _n, c in ZONES:
            s.append('<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="%s" opacity=".08"/>' % (L, Y(mx), iw, Y(z0) - Y(mx), c))
            z0 = mx
    v = lo
    while v <= hi + 1e-9:
        s.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s"/><text x="%d" y="%.1f" class="c-ylab">%s</text>'
                 % (L, L + iw, Y(v), Y(v), GRID, L - 6, Y(v) + 4, _fmt(v)))
        v += step
    if lo < 0 < hi:
        s.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="1.5"/>' % (L, L + iw, Y(0), Y(0), MUTED))
    k = max(1, n // 7)
    for i in range(0, n, k):
        s.append('<text x="%.1f" y="%d" class="c-xlab">%s</text>' % (X(i), height - 10, escape(str(labels[i]))))
    leg = []
    for j, (name, ys) in enumerate(series.items()):
        c = PALETTE[j % len(PALETTE)]
        segs, cur = [], []
        for i, y in enumerate(ys):
            if y is None:
                if cur:
                    segs.append(cur)
                cur = []
            else:
                cur.append("%.1f,%.1f" % (X(i), Y(y)))
        if cur:
            segs.append(cur)
        for sg in segs:
            s.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round"%s/>'
                     % (" ".join(sg), c, "2.6" if j == 0 else "2", "" if j == 0 else ' stroke-dasharray="6 4"' if j > 1 else ""))
        for i, y in enumerate(ys):
            if y is not None:
                s.append('<circle cx="%.1f" cy="%.1f" r="5" fill="transparent"><title>%s %s：%s%s</title></circle>' % (X(i), Y(y), escape(str(labels[i])), escape(name), _fmt(y), escape(unit)))
        leg.append('<span><i style="background:%s"></i>%s</span>' % (c, escape(name)))
    s.append("</svg>")
    return _figure("".join(s), title, unit, source, "".join(leg))


def bar_chart(labels, values, title="", unit="", source="", width=760, signed=True):
    """가로 막대. signed=True면 양수 빨강·음수 초록(대만식 상승/하락 색)"""
    if not values:
        return ""
    n = len(values)
    rowh = 34
    height = 20 + rowh * n
    L, R = 110, 120
    iw = width - L - R
    mn, mx = min(0, min(values)), max(0, max(values))
    if mn == mx:
        mx = mn + 1

    def X(v):
        return L + iw * (v - mn) / (mx - mn)

    s = ['<svg viewBox="0 0 %d %d" class="chart" role="img" aria-label="%s">' % (width, height, escape(title))]
    s.append('<line x1="%.1f" x2="%.1f" y1="6" y2="%d" stroke="%s"/>' % (X(0), X(0), height - 6, MUTED))
    for i, (lab, v) in enumerate(zip(labels, values)):
        y = 12 + i * rowh
        c = ("#D9363E" if v >= 0 else "#13A06F") if signed else PALETTE[0]
        x0, x1 = sorted((X(0), X(v)))
        s.append('<text x="%d" y="%d" font-size="13" fill="%s" text-anchor="end">%s</text>' % (L - 10, y + 16, INK, escape(str(lab))))
        s.append('<rect x="%.1f" y="%d" width="%.1f" height="20" rx="4" fill="%s"><title>%s %s%s</title></rect>' % (x0, y + 2, max(1.5, x1 - x0), c, escape(str(lab)), _fmt(v), escape(unit)))
        s.append('<text x="%d" y="%d" font-size="12" fill="%s" text-anchor="end" font-weight="700">%s%s</text>' % (width - 4, y + 16, c, _fmt(v, sign=signed), escape(unit)))
    s.append("</svg>")
    return _figure("".join(s), title, unit, source, "")


def _fmt(v, sign=False):
    if abs(v) >= 1000:
        t = "{:,.0f}".format(v)
    elif abs(v - round(v)) < 1e-9:
        t = "%d" % round(v)
    else:
        t = "%.2f" % v
    return ("+" + t) if sign and v > 0 else t


def _figure(svgtxt, title, unit, source, legend):
    cap = ""
    if title:
        cap = '<figcaption><b>%s</b>%s</figcaption>' % (escape(title), ('<span class="small muted">（單位：%s）</span>' % escape(unit)) if unit else "")
    foot = ""
    if legend or source:
        foot = '<div class="fig-foot"><div class="legend">%s</div>%s</div>' % (legend, ('<span class="small muted">資料來源：%s</span>' % escape(source)) if source else "")
    return '<figure class="fig">%s%s%s</figure>' % (cap, svgtxt, foot)

# -*- coding: utf-8 -*-
"""
글 파일(build 함수)에서 쓰는 도우미
  from blogkit import *  로 불러와서 표·강조 박스를 쉽게 만들어요.
"""
import json
import os
import sys
from html import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg import bar_chart, line_chart  # noqa: E402,F401

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

__all__ = ["table", "callout", "warn", "zone_name", "zone_color", "score_chip", "esc", "toc",
           "line_chart", "bar_chart", "keypoints", "latest", "cache", "series"]


def esc(s):
    return escape(str(s))


def table(headers, rows, caption=None):
    """table(["항목","값"], [["台股",45],["美股",38]])  ※ 셀에 HTML을 쓰려면 문자열 앞에 '!'"""
    def cell(v):
        v = str(v)
        return v[1:] if v.startswith("!") else escape(v)
    h = "".join("<th>%s</th>" % cell(x) for x in headers)
    b = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % cell(c) for c in r) for r in rows)
    cap = "<caption class='small muted'>%s</caption>" % escape(caption) if caption else ""
    return '<div class="tbl"><table>%s<thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (cap, h, b)


def callout(html):
    return '<div class="callout">%s</div>' % html


def warn(html):
    return '<div class="callout warn">%s</div>' % html


def _z():
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config
    return config.ZONES


def zone_name(v):
    for mx, n, _c in _z():
        if v <= mx:
            return n
    return _z()[-1][1]


def zone_color(v):
    for mx, _n, c in _z():
        if v <= mx:
            return c
    return _z()[-1][2]


def score_chip(v):
    return '<b style="color:%s">%d（%s）</b>' % (zone_color(v), v, zone_name(v))


def toc(items):
    """toc([("s1","第一段"),("s2","第二段")]) → 목차"""
    li = "".join('<li><a href="#%s">%s</a></li>' % (a, escape(t)) for a, t in items)
    return '<nav class="toc" aria-label="目錄"><b>本文目錄</b><ol>%s</ol></nav>' % li


def keypoints(items):
    """글 맨 위 '3줄 요약' 박스"""
    li = "".join("<li>%s</li>" % x for x in items)
    return '<div class="keypoints"><b>重點整理</b><ul>%s</ul></div>' % li


# ── 사이트에 쌓인 실제 데이터 (글 안의 그래프를 실데이터로 그릴 때) ──
def latest():
    """data/latest.json → dict (대만·미국·일본·한국 점수와 6개월 기록)"""
    with open(os.path.join(_ROOT, "data", "latest.json"), encoding="utf-8") as f:
        return json.load(f)


def cache():
    """data/tw_cache.json → dict (가권지수·외국인·융자·풋콜 등 원재료)"""
    with open(os.path.join(_ROOT, "data", "tw_cache.json"), encoding="utf-8") as f:
        return json.load(f)


def series(name, start=None, end=None):
    """원재료 하나를 [(날짜, 값)] 으로. name: taiex / fx / margin / foreign / pcr / breadth"""
    d = cache()[name]
    out = [(k, d[k]) for k in sorted(d) if (start is None or k >= start) and (end is None or k <= end)]
    if name == "breadth":
        out = [(k, v[0] - v[1]) for k, v in out]
    return out

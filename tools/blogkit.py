# -*- coding: utf-8 -*-
"""
글 파일(build 함수)에서 쓰는 도우미
  from blogkit import *  로 불러와서 표·강조 박스를 쉽게 만들어요.
"""
from html import escape

__all__ = ["table", "callout", "warn", "zone_name", "zone_color", "score_chip", "esc", "toc"]


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

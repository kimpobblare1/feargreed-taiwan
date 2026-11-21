# -*- coding: utf-8 -*-
"""
공유 썸네일(1200×630) 자동 생성 — 그날 점수를 레이더 바늘이 가리켜요.
  LINE·Facebook·X에 링크를 올리면 이 이미지가 뜹니다.
  글꼴은 tools/fonts/ 의 Noto Sans CJK TC 부분 글꼴(썸네일에 쓰는 글자만 담음, SIL OFL)을 씁니다.
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import config as C  # noqa: E402

S = 2                     # 2배로 그린 뒤 줄여서 테두리를 매끄럽게
W, H = 1200, 630
BG = (15, 30, 51)
CYAN = (18, 181, 203)
CYAN_L = (143, 243, 255)
MUTED = (159, 177, 199)
WD = "一二三四五六日"


def _font(weight, size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", "og-%s.otf" % weight), size * S)


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def zone_of(v):
    for mx, name, color in C.ZONES:
        if v <= mx:
            return name, _hex(color)
    return C.ZONES[-1][1], _hex(C.ZONES[-1][2])


def make(path, score, as_of=None, others=None):
    """score: 0~100 / as_of: 'YYYY-MM-DD' / others: [("美股", 10), ("日股", 16), ("韓股", 6)]"""
    im = Image.new("RGB", (W * S, H * S), BG)
    # 배경 은은한 빛
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gx, gy = 900 * S, 330 * S
    for r in range(430, 0, -10):
        a = int(46 * (1 - r / 430) ** 1.5)
        gd.ellipse([gx - r * S, gy - r * S, gx + r * S, gy + r * S], fill=CYAN + (a,))
    im.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(im, "RGBA")

    # ── 왼쪽 글자 ──
    zname, zcol = zone_of(score)
    d.text((80 * S, 70 * S), C.SITE_NAME, font=_font("black", 50), fill=(255, 255, 255))
    d.text((84 * S, 140 * S), "台股恐懼貪婪指數", font=_font("medium", 30), fill=(169, 194, 217))
    num = str(int(score))
    fnum = _font("black", 190)
    d.text((70 * S, 170 * S), num, font=fnum, fill=zcol)
    nw = d.textlength(num, font=fnum) / S
    # 구간 이름 알약
    fz = _font("black", 40)
    tw = d.textlength(zname, font=fz) / S
    px, py = 70 + nw + 26, 300
    d.rounded_rectangle([px * S, py * S, (px + tw + 44) * S, (py + 66) * S], radius=33 * S, fill=zcol)
    d.text(((px + 22) * S, (py + 8) * S), zname, font=fz, fill=(15, 30, 51) if zname == "中性" else (255, 255, 255))
    if as_of:
        import datetime as _dt
        dt = _dt.date.fromisoformat(as_of)
        d.text((80 * S, 438 * S), "資料日 %d/%d/%d（%s）" % (dt.year, dt.month, dt.day, WD[dt.weekday()]),
               font=_font("medium", 26), fill=MUTED)
    if others:
        x = 80
        for name, v in others:
            if v is None:
                continue
            _zn, c = zone_of(v)
            f1, f2 = _font("medium", 24), _font("black", 34)
            d.text((x * S, 500 * S), name, font=f1, fill=MUTED)
            lw = d.textlength(name, font=f1) / S
            d.text(((x + lw + 10) * S, 491 * S), str(int(v)), font=f2, fill=c)
            x += lw + 10 + d.textlength(str(int(v)), font=f2) / S + 34

    # ── 오른쪽 게이지 + 레이더 바늘 ──
    cx, cy, R = 858, 430, 205

    def P(r, deg):           # deg 0 = 0점(왼쪽), 180 = 100점(오른쪽)
        a = math.radians(180 - deg)
        return (cx + r * math.cos(a)) * S, (cy - r * math.sin(a)) * S

    def box(r):
        return [(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S]

    for r in (60, 112, 164):  # 레이더 동심원(점선)
        for k in range(0, 180, 4):
            d.arc(box(r), 180 + k, 180 + k + 2, fill=(143, 217, 228, 55), width=2 * S)
    for deg in (30, 60, 90, 120, 150):
        d.line([P(0, deg), P(190, deg)], fill=(143, 217, 228, 28), width=1 * S)
    d.line([P(R, 0), P(R, 180)], fill=(143, 217, 228, 50), width=1 * S)
    lo = 0
    flab = _font("black", 19)
    for mx, name, color in C.ZONES:
        a0, a1 = 180 + 180 * lo / 100 + (0.8 if lo else 0), 180 + 180 * (mx + (1 if mx < 100 else 0)) / 100 - (0.8 if mx < 100 else 0)
        d.arc(box(R), a0, a1, fill=_hex(color), width=24 * S)
        mid = (a0 + a1) / 2 - 180
        tx, ty = P(R + 28, mid)
        tw = d.textlength(name, font=flab)
        if abs(tx / S - cx) < 60:
            tx -= tw / 2
        elif tx / S < cx:
            tx -= tw
        d.text((tx, ty - 13 * S), name, font=flab, fill=_hex(color))
        lo = mx + 1 if mx < 100 else mx
    # 스윕 잔상
    deg = 180 * score / 100.0
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    span, n = 50, 50
    for i in range(n):
        t0 = deg - span + i * span / n
        if t0 + span / n < 0:
            continue
        op = int(255 * (0.01 + 0.42 * (i / (n - 1)) ** 2.2))
        ld.pieslice(box(R - 14), 180 + max(0, t0), 180 + t0 + span / n + 0.5, fill=CYAN + (op,))
    im.paste(layer, (0, 0), layer)
    d = ImageDraw.Draw(im, "RGBA")
    # 빔(바늘)
    tip = P(R - 14, deg)
    beam = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(beam).line([(cx * S, cy * S), tip], fill=CYAN + (170,), width=16 * S)
    beam = beam.filter(ImageFilter.GaussianBlur(6 * S))
    im.paste(beam, (0, 0), beam)
    d = ImageDraw.Draw(im, "RGBA")
    d.line([(cx * S, cy * S), tip], fill=CYAN_L, width=5 * S)
    # 포착 지점
    bx, by = P(R, deg)
    halo = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([bx - 28 * S, by - 28 * S, bx + 28 * S, by + 28 * S], fill=zcol + (150,))
    halo = halo.filter(ImageFilter.GaussianBlur(8 * S))
    im.paste(halo, (0, 0), halo)
    d = ImageDraw.Draw(im, "RGBA")
    d.ellipse([bx - 13 * S, by - 13 * S, bx + 13 * S, by + 13 * S], fill=zcol, outline=(255, 255, 255), width=4 * S)
    d.ellipse([(cx - 14) * S, (cy - 14) * S, (cx + 14) * S, (cy + 14) * S], fill=BG, outline=CYAN_L, width=4 * S)
    d.ellipse([(cx - 5) * S, (cy - 5) * S, (cx + 5) * S, (cy + 5) * S], fill=CYAN_L)
    ft = _font("medium", 16)
    for t in (0, 50, 100):
        x, y = P(R - 44, 180 * t / 100)
        tw = d.textlength(str(t), font=ft)
        d.text((x - tw / 2, y - (0 if t == 50 else -4 * S) - 10 * S), str(t), font=ft, fill=MUTED)
    # 아래 5색 띠
    for i, (_mx, _n, color) in enumerate(C.ZONES):
        d.rectangle([i * W / 5 * S, (H - 12) * S, (i + 1) * W / 5 * S, H * S], fill=_hex(color))
    out = im.resize((W, H), Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out.save(path, optimize=True)
    return path


if __name__ == "__main__":
    make("/tmp/og_test.png", int(sys.argv[1]) if len(sys.argv) > 1 else 5, "2026-11-20", [("美股", 10), ("日股", 16), ("韓股", 6)])
    print("saved /tmp/og_test.png")

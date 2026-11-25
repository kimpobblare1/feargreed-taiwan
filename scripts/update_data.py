#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
대만 공포탐욕지수 업데이트 스크립트
  1) 원재료 데이터를 모아 data/tw_cache.json 에 쌓고 (TWSE는 하루치씩만 줘서 누적 저장)
  2) 7개 지표 점수(0~100)를 계산해서
  3) data/latest.json (사이트가 읽는 파일)을 만듭니다.

실행:  python scripts/update_data.py              # 평소 (부족한 날짜 최대 12일만 채움)
       python scripts/update_data.py --backfill 320   # 처음 한 번: 1년치 이상 채우기 (약 40분)

안전장치
  - 어떤 데이터가 실패해도 나머지로 계산합니다 (빠진 지표는 가중치를 나눠 가짐)
  - 전부 실패하면 직전 값을 stale(이전 값) 표시로 유지합니다
  - 새로 받은 날짜가 기존보다 과거면 덮어쓰지 않습니다
"""
import argparse
import hashlib
import json
import math
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
import sources as S  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(ROOT, "data", "tw_cache.json")
OUT_PATH = os.path.join(ROOT, "data", "latest.json")

TARGET_DAYS = 330          # TWSE 일별 데이터를 최근 몇 거래일까지 보관할지
WINDOW = 252               # 점수 = 최근 1년(252거래일) 안에서의 위치(백분위)
MIN_WINDOW = 60            # 데이터가 60일 이상 쌓이면 점수 계산 시작
HISTORY_DAYS = 130         # 사이트 차트에 보여줄 기간(약 6개월)

# (키, 이름, 가중치, 반대방향 여부, 단위, 설명)
INDICATORS = [
    ("momentum", "市場動能", 0.20, False, "%", "加權指數與125日均線的乖離率。高於均線越多越貪婪。"),
    ("volatility", "市場波動", 0.15, True, "%", "加權指數近20日的年化波動率。波動越大越恐懼。"),
    ("breadth", "漲跌家數", 0.15, False, "%", "上市股票近10日上漲與下跌家數的淨比率。上漲家數越多越貪婪。"),
    ("margin", "融資餘額", 0.15, False, "%", "上市融資餘額的20日變化率。散戶加碼槓桿代表貪婪。"),
    ("foreign", "外資動向", 0.15, False, "億元", "外資近20個交易日累計買賣超。持續買超代表貪婪。"),
    ("pcr", "選擇權多空比", 0.10, False, "%", "台指選擇權賣權/買權成交量比（5日平均）。台股行情強勢時賣權成交量常隨之增加，比值越高越偏多。"),
    ("fx", "新台幣匯率", 0.10, True, "%", "美元兌新台幣的20日變化。新台幣走弱（資金外流）代表恐懼。"),
]
KEYS = [k for k, *_ in INDICATORS]
WEIGHTS = {k: w for k, _n, w, *_ in INDICATORS}


def log(*a):
    print(*a, flush=True)


def tw_now():
    return datetime.now(S.TW_TZ)


def load_json(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return default


def save_json(p, obj, indent=None):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent, separators=(",", ":") if indent is None else None)
    os.replace(tmp, p)


def zone(v):
    for mx, name, _c in config.ZONES:
        if v <= mx:
            return name
    return config.ZONES[-1][1]


# ─────────────────────────────────────────────────────────────
# 1) 원재료 모으기
# ─────────────────────────────────────────────────────────────
def collect(cache, backfill):
    now = tw_now()
    today = now.date().isoformat()
    status = {}

    # 가권지수
    try:
        rows = S.yahoo_daily("^TWII", "3y")
        cache["taiex"].update({d: round(c, 2) for d, c in rows})
        status["taiex"] = "Yahoo ^TWII %d일" % len(rows)
    except Exception as e:  # noqa: BLE001
        log("  ⚠ Yahoo 가권지수 실패 → TWSE 월별로 대체:", e)
        months = 2 if len(cache["taiex"]) > 200 else 18
        d = now.date().replace(day=1)
        got = 0
        for _ in range(months):
            try:
                for day, close, _val in S.twse_taiex_month(d.strftime("%Y%m01")):
                    if close:
                        cache["taiex"][day] = close
                        got += 1
            except Exception as e2:  # noqa: BLE001
                log("    FMTQIK", d, e2)
            d = (d - timedelta(days=1)).replace(day=1)
        status["taiex"] = "TWSE FMTQIK %d일" % got
    # 최근 거래일은 TWSE 공식 종가로 덮어쓰기 (Yahoo가 마지막 날을 비워 두는 경우가 있어서)
    if "Yahoo" in status.get("taiex", ""):
        d = now.date().replace(day=1)
        for mm in (d, (d - timedelta(days=1)).replace(day=1)):
            try:
                for day, close, _val in S.twse_taiex_month(mm.strftime("%Y%m01")):
                    if close:
                        cache["taiex"][day] = close
            except Exception as e:  # noqa: BLE001
                log("    FMTQIK 보강 실패", mm, e)
    # 장중(14:00 전)에 돌면 오늘 값은 아직 확정이 아니라서 빼요
    if now.hour < 14 and today in cache["taiex"]:
        cache["taiex"].pop(today)

    # 환율
    try:
        rows = S.yahoo_daily("TWD=X", "3y")
        cache["fx"].update({d: round(c, 4) for d, c in rows if d <= today})
        status["fx"] = "Yahoo TWD=X %d일" % len(rows)
    except Exception as e:  # noqa: BLE001
        status["fx"] = "실패: %s" % e

    dates = sorted(d for d in cache["taiex"] if d <= today)[-TARGET_DAYS:]

    # TWSE 일별 3종: 최신 날짜부터, 최대 backfill 일
    jobs = [("breadth", S.twse_breadth), ("margin", S.twse_margin), ("foreign", S.twse_foreign)]
    fails = cache.setdefault("fails", {})
    todo = []
    for d in reversed(dates):
        need = [k for k, _f in jobs if d not in cache[k] and fails.get(k, {}).get(d, 0) < 3]
        if need:
            todo.append((d, need))
    todo = todo[:backfill]
    log("  TWSE 일별 데이터: %d일 처리 예정" % len(todo))
    ok = {k: 0 for k, _ in jobs}
    for i, (d, need) in enumerate(todo, 1):
        ymd = d.replace("-", "")
        for k, fn in jobs:
            if k not in need:
                continue
            try:
                v = fn(ymd)
                cache[k][d] = list(v) if isinstance(v, tuple) else v
                ok[k] += 1
                fails.get(k, {}).pop(d, None)
            except Exception as e:  # noqa: BLE001
                # 최근 2일은 아직 발표 전일 수 있어서 실패 횟수를 세지 않아요
                if d < (now.date() - timedelta(days=2)).isoformat():
                    fails.setdefault(k, {})[d] = fails.get(k, {}).get(d, 0) + 1
                if i <= 3:
                    log("    %s %s: %s" % (k, d, e))
        if i % 20 == 0:
            log("    ... %d/%d일 완료" % (i, len(todo)))
            save_json(CACHE_PATH, cache)       # 중간 저장 (오래 걸리는 백필 대비)
    for k, _ in jobs:
        status[k] = "새로 %d일 (보유 %d일)" % (ok[k], len(cache[k]))

    # 풋/콜 비율: 비어 있는 구간만 한 달씩
    missing = [d for d in dates if d not in cache["pcr"]]
    if missing:
        start = date.fromisoformat(missing[0])
        if backfill < 30:      # 평소엔 최근 40일만
            start = max(start, now.date() - timedelta(days=40))
        got, chunks = 0, 0
        end = now.date()                       # 최신 구간부터 거꾸로 한 달씩
        while end >= start and chunks < 18:
            cur = max(start, end - timedelta(days=30))
            try:
                part = S.taifex_pcr(cur, end)
                cache["pcr"].update(part)
                got += len(part)
            except Exception as e:  # noqa: BLE001
                log("    PCR %s~%s: %s" % (cur, end, e))
            end = cur - timedelta(days=1)
            chunks += 1
        status["pcr"] = "새로 %d일 (보유 %d일)" % (got, len(cache["pcr"]))

    # 오래된 데이터 정리
    keep_from = dates[0] if dates else "0000"
    for k in ("breadth", "margin", "foreign", "pcr"):
        cache[k] = {d: v for d, v in cache[k].items() if d >= keep_from}
    return dates, status


# ─────────────────────────────────────────────────────────────
# 2) 지표 계산
# ─────────────────────────────────────────────────────────────
def raw_series(cache, dates):
    px = [cache["taiex"][d] for d in dates]
    fx_dates = sorted(cache["fx"])
    raw = {k: [None] * len(dates) for k in KEYS}

    def fx_on(d):
        # d 당일 또는 그 이전 가장 가까운 환율
        lo, hi = 0, len(fx_dates) - 1
        best = None
        while lo <= hi:
            mid = (lo + hi) // 2
            if fx_dates[mid] <= d:
                best = fx_dates[mid]
                lo = mid + 1
            else:
                hi = mid - 1
        return cache["fx"][best] if best and (date.fromisoformat(d) - date.fromisoformat(best)).days <= 5 else None

    for i, d in enumerate(dates):
        if i >= 124:
            ma = sum(px[i - 124:i + 1]) / 125
            raw["momentum"][i] = (px[i] / ma - 1) * 100
        if i >= 20:
            rets = [math.log(px[j] / px[j - 1]) for j in range(i - 19, i + 1)]
            m = sum(rets) / 20
            raw["volatility"][i] = math.sqrt(sum((r - m) ** 2 for r in rets) / 19) * math.sqrt(252) * 100
        if i >= 9:
            vals = []
            for j in range(i - 9, i + 1):
                b = cache["breadth"].get(dates[j])
                if b and (b[0] + b[1]) > 0:
                    vals.append((b[0] - b[1]) / (b[0] + b[1]) * 100)
            if len(vals) >= 7 and dates[i] in cache["breadth"]:
                raw["breadth"][i] = sum(vals) / len(vals)
        if i >= 20:
            a, b = cache["margin"].get(dates[i - 20]), cache["margin"].get(d)
            if a and b:
                raw["margin"][i] = (b / a - 1) * 100
        if i >= 19:
            vals = [cache["foreign"][dates[j]] for j in range(i - 19, i + 1) if dates[j] in cache["foreign"]]
            if len(vals) >= 15 and d in cache["foreign"]:
                raw["foreign"][i] = sum(vals) * 20 / len(vals)
        if i >= 4:
            vals = [cache["pcr"][dates[j]] for j in range(i - 4, i + 1) if dates[j] in cache["pcr"]]
            if len(vals) >= 3 and d in cache["pcr"]:
                raw["pcr"][i] = sum(vals) / len(vals)
        if i >= 20:
            a, b = fx_on(dates[i - 20]), fx_on(d)
            if a and b:
                raw["fx"][i] = (b / a - 1) * 100
    return raw


def pct_rank(window, x):
    lt = sum(1 for v in window if v < x)
    eq = sum(1 for v in window if v == x)
    return (lt + 0.5 * eq) / len(window) * 100


def score_series(raw, dates):
    parts = [dict() for _ in dates]
    meta = {}
    for k, _n, _w, invert, *_ in INDICATORS:
        series = raw[k]
        for i in range(len(dates)):
            x = series[i]
            if x is None:
                continue
            win = [v for v in series[max(0, i - WINDOW + 1):i + 1] if v is not None]
            if len(win) < MIN_WINDOW:
                continue
            p = pct_rank(win, x)
            parts[i][k] = round(100 - p if invert else p, 1)
        # 진단 정보: 최근 1년 분포
        last = [v for v in series[-WINDOW:] if v is not None]
        if last:
            s = sorted(last)
            meta[k] = {"low": round(s[0], 2), "high": round(s[-1], 2), "median": round(s[len(s) // 2], 2), "n": len(s)}
    comp = [None] * len(dates)
    for i, p in enumerate(parts):
        if "momentum" not in p or len(p) < 3:
            continue
        ws = sum(WEIGHTS[k] for k in p)
        if ws < 0.5:
            continue
        comp[i] = sum(WEIGHTS[k] * v for k, v in p.items()) / ws
    return parts, comp, meta


def smooth3(comp, i):
    vals = [comp[j] for j in range(max(0, i - 2), i + 1) if comp[j] is not None]
    return round(sum(vals) / len(vals)) if vals else None


def build_tw(cache, dates):
    raw = raw_series(cache, dates)
    parts, comp, meta = score_series(raw, dates)
    idx = [i for i, c in enumerate(comp) if c is not None]
    if not idx:
        return None, []
    last = idx[-1]
    disp = {i: smooth3(comp, i) for i in idx}

    def back(n):
        j = last - n
        return disp.get(j) if j >= 0 else None

    inds, missing = [], []
    for k, name, w, invert, unit, desc in INDICATORS:
        vals = [parts[j][k] for j in range(max(0, last - 2), last + 1) if k in parts[j]]
        if k not in parts[last]:
            missing.append(name)
            continue
        inds.append({
            "key": k, "name": name, "weight": w, "value": round(sum(vals) / len(vals)),
            "raw": round(raw[k][last], 2), "unit": unit, "desc": desc, **meta.get(k, {}),
        })
    px = cache["taiex"]
    d0, d1 = dates[last], dates[last - 1] if last > 0 else None
    taiex = {"close": px[d0]}
    if d1:
        taiex["change"] = round(px[d0] - px[d1], 2)
        taiex["change_pct"] = round((px[d0] / px[d1] - 1) * 100, 2)
    tw = {
        "score": disp[last], "label": zone(disp[last]),
        "previous_close": back(1), "previous_1_week": back(5), "previous_1_month": back(21),
        "as_of": d0, "indicators": inds, "missing": missing, "stale": False, "taiex": taiex,
    }
    hist = []
    for i in idx[-HISTORY_DAYS:]:
        hist.append({"date": dates[i], "tw": disp[i], "taiex": px[dates[i]],
                     "parts": {k: round(v) for k, v in parts[i].items()}})
    return tw, hist


# ─────────────────────────────────────────────────────────────
# 3) 메인
# ─────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", type=int, default=int(os.environ.get("BACKFILL_DAYS") or 12),
                    help="TWSE 일별 데이터를 이번에 최대 며칠까지 채울지")
    args = ap.parse_args(argv)

    prev = load_json(OUT_PATH, {})
    cache = load_json(CACHE_PATH, {})
    for k in ("taiex", "fx", "breadth", "margin", "foreign", "pcr"):
        cache.setdefault(k, {})

    log("=== 대만 원재료 수집 (backfill=%d) ===" % args.backfill)
    dates, status = collect(cache, args.backfill)
    for k, v in status.items():
        log("  %-9s %s" % (k, v))
    save_json(CACHE_PATH, cache)

    log("=== 대만 지수 계산 ===")
    tw, hist = (None, [])
    if len(dates) >= 150:
        tw, hist = build_tw(cache, dates)
    if tw:
        log("  → 대만 %d (%s) 기준일 %s / 빠진 지표: %s" % (tw["score"], tw["label"], tw["as_of"], ", ".join(tw["missing"]) or "없음"))
    prev_tw = prev.get("tw")
    if tw and prev_tw and tw["as_of"] < prev_tw.get("as_of", ""):
        log("  ⚠ 새 값의 날짜가 이전보다 과거라서 이전 값을 유지해요")
        tw, hist = None, []
    if tw is None and prev_tw:
        tw = dict(prev_tw, stale=True)
        hist = [h for h in prev.get("history", [])]
        log("  ⚠ 대만은 이전 값을 유지 (stale)")

    log("=== 미국·일본·한국 ===")
    us, us_hist = None, {}
    try:
        us, us_hist = S.cnn_fear_greed()
        log("  ✅ 미국(CNN) %d (과거 기록 %d일)" % (us["score"], len(us_hist)))
    except Exception as e:  # noqa: BLE001
        log("  ⚠ CNN 실패:", e)
    sis = {}
    # 한국은 '마감 지수'만 써요: 한국 시간 평일 15:40 이후 실행에서만 가져오고, 그 외에는 이전 마감 값을 유지
    kst = datetime.now(S.TW_TZ) + timedelta(hours=1)
    kr_closed = kst.weekday() < 5 and (kst.hour, kst.minute) >= (15, 40)
    prev_kr = prev.get("kr") if isinstance(prev.get("kr"), dict) else None
    for key, cfg in (("jp", config.JP_SITE), ("kr", config.KR_SITE)):
        if key == "kr" and not kr_closed:
            if prev_kr:
                sis[key] = dict(prev_kr, _raw={})
                log("  ⏸ kr 장중/장전이라 이전 마감 값 유지 (%s, %s)" % (prev_kr.get("score"), prev_kr.get("as_of") or "날짜 없음"))
            continue
        try:
            sis[key] = S.sister_site(cfg)
            log("  ✅ %s %d" % (key, sis[key]["score"]))
        except Exception as e:  # noqa: BLE001
            log("  ⚠ %s 실패: %s" % (key, e))
            continue
        if key == "kr":
            today = kst.date().isoformat()
            sis[key]["as_of"] = sis[key].get("as_of") or today
            if prev_kr and prev_kr.get("as_of") and prev_kr["as_of"] < sis[key]["as_of"]:
                sis[key]["previous_close"] = prev_kr.get("score")
            elif prev_kr and prev_kr.get("as_of") == sis[key]["as_of"]:
                sis[key]["previous_close"] = prev_kr.get("previous_close")
    # CNN이 막히면 일본 사이트 JSON의 us 값을 빌려 와요
    if us is None and sis.get("jp") and isinstance(sis["jp"]["_raw"].get("us"), dict):
        u = sis["jp"]["_raw"]["us"]
        us = {k: u.get(k) for k in ("score", "previous_close", "previous_1_week", "previous_1_month", "as_of")}
        us["url"] = "https://edition.cnn.com/markets/fear-and-greed"
        log("  ↪ 미국 값은 일본 사이트 데이터로 대체")
    # CNN 과거 기록이 비었으면 일본 사이트의 기록(날짜별 미국 값)으로 채워요
    if not us_hist and sis.get("jp"):
        for hrow in sis["jp"]["_raw"].get("history", []) or []:
            if isinstance(hrow, dict) and hrow.get("us") is not None and hrow.get("date"):
                us_hist[hrow["date"]] = int(hrow["us"])
        if us_hist:
            log("  ↪ 미국 과거 기록 %d일을 일본 사이트 데이터로 채움" % len(us_hist))
    for v in sis.values():
        v.pop("_raw", None)
    out_other = {}
    for key, val in (("us", us), ("jp", sis.get("jp")), ("kr", sis.get("kr"))):
        if val is None and isinstance(prev.get(key), dict):
            val = dict(prev[key], stale=True)
        if val is not None:
            val.setdefault("stale", False)
            val["label"] = zone(val["score"]) if val.get("score") is not None else None
        out_other[key] = val

    if tw is None:
        log("❌ 대만 지수를 만들 수 없고 이전 값도 없어요. (처음이라면 --backfill 320 으로 실행)")
        if not any(out_other.values()):
            return 1

    # 차트용: 대만 거래일에 미국 값을 붙임 (5일 이내 가장 가까운 과거 값)
    us_dates = sorted(us_hist)
    for h in hist:
        cand = [d for d in us_dates if d <= h["date"]]
        if cand and (date.fromisoformat(h["date"]) - date.fromisoformat(cand[-1])).days <= 5:
            h["us"] = us_hist[cand[-1]]

    payload = {"success": True, "tw": tw, **out_other, "history": hist}
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    if prev.get("hash") == digest:
        log("변경 없음: latest.json 그대로 둡니다.")
        return 0
    now = tw_now()
    payload["hash"] = digest
    payload["updated_at"] = now.isoformat(timespec="seconds")
    payload["updated_at_tw"] = now.strftime("%Y/%m/%d %H:%M")
    save_json(OUT_PATH, payload, indent=1)
    log("✅ data/latest.json 저장 (%s)" % payload["updated_at_tw"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

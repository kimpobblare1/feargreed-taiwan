# -*- coding: utf-8 -*-
"""
데이터 가져오기 모음 (모두 무료 공개 데이터)
  - 가권지수(TAIEX) 종가 ........ Yahoo Finance(^TWII) → 실패 시 TWSE FMTQIK(월별)
  - 상승/하락 종목 수 ........... TWSE MI_INDEX (일별)
  - 융자 잔액(融資餘額) ......... TWSE MI_MARGN (일별)
  - 외국인 순매수(外資買賣超) ... TWSE BFI82U (일별)
  - 풋/콜 비율 ................. TAIFEX pcRatio (기간 조회)
  - 달러/대만달러 ............... Yahoo Finance(TWD=X)
  - 미국 CNN 공포탐욕지수 ....... CNN dataviz
  - 일본·한국 ................... 형제 사이트의 JSON
모든 함수는 실패하면 예외를 던집니다. (update_data.py가 잡아서 '빠진 지표'로 처리)
"""
import csv
import io
import re
import time
from datetime import date, datetime, timedelta, timezone

import requests

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}
TWSE = "https://www.twse.com.tw/rwd/zh"
TW_TZ = timezone(timedelta(hours=8))
_last_twse_call = [0.0]
TWSE_GAP = 2.2   # TWSE는 너무 자주 부르면 막아요 → 호출 사이 최소 간격(초)


def _num(s):
    """'1,234.5' / '+12.3' / '-' / '' → float 또는 None"""
    if s is None:
        return None
    s = str(s).strip().replace(",", "").replace("+", "")
    s = re.sub(r"<[^>]+>", "", s)
    s = s.split("(")[0].strip()
    if s in ("", "-", "--", "X"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _get(url, params=None, timeout=25, **kw):
    r = requests.get(url, params=params, headers=UA, timeout=timeout, **kw)
    r.raise_for_status()
    return r


def _twse_json(path, params):
    wait = TWSE_GAP - (time.time() - _last_twse_call[0])
    if wait > 0:
        time.sleep(wait)
    params = dict(params, response="json")
    try:
        r = _get(TWSE + path, params)
    finally:
        _last_twse_call[0] = time.time()
    j = r.json()
    stat = str(j.get("stat", "OK"))
    if stat not in ("OK", "ok"):
        # 휴장일·데이터 없음: '很抱歉，沒有符合條件的資料!' 등
        raise LookupError("TWSE %s: %s" % (path, stat))
    return j


def _tables(j):
    """TWSE 응답은 {'fields','data'} 또는 {'tables':[{'title','fields','data'}]} 두 형태라서 통일"""
    out = []
    if isinstance(j.get("tables"), list):
        for t in j["tables"]:
            if isinstance(t, dict) and t.get("data"):
                out.append((t.get("title", ""), t.get("fields", []), t["data"]))
    if j.get("data"):
        out.append((j.get("title", ""), j.get("fields", []), j["data"]))
    for k, v in j.items():          # 예전 형식: data1, data2 ... / fields1, fields2 ...
        m = re.match(r"data(\d+)$", k)
        if m and isinstance(v, list) and v:
            out.append((j.get("subtitle" + m.group(1), ""), j.get("fields" + m.group(1), []), v))
    return out


# ── 가권지수 ────────────────────────────────────────────────
def yahoo_daily(symbol, rng="3y"):
    """Yahoo 차트 API → [(YYYY-MM-DD, close), ...] (대만/현지 날짜 기준)"""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%s" % requests.utils.quote(symbol)
    j = _get(url, {"range": rng, "interval": "1d", "includePrePost": "false"}).json()
    res = j["chart"]["result"][0]
    off = int(res["meta"].get("gmtoffset", 28800))
    ts = res["timestamp"]
    closes = res["indicators"]["quote"][0]["close"]
    out = {}
    for t, c in zip(ts, closes):
        if c is None:
            continue
        d = datetime.fromtimestamp(t + off, tz=timezone.utc).date().isoformat()
        out[d] = float(c)
    if len(out) < 30:
        raise ValueError("Yahoo %s: 데이터가 너무 적어요 (%d)" % (symbol, len(out)))
    return sorted(out.items())


def _roc_to_iso(s):
    """'115/11/19' → '2026-11-19'"""
    y, m, d = [int(x) for x in re.findall(r"\d+", s)[:3]]
    return date(y + 1911, m, d).isoformat()


def twse_taiex_month(yyyymm01):
    """TWSE FMTQIK: 한 달치 [(날짜, 가권지수 종가, 거래대금)]"""
    j = _twse_json("/afterTrading/FMTQIK", {"date": yyyymm01})
    out = []
    for _t, fields, rows in _tables(j):
        for r in rows:
            try:
                out.append((_roc_to_iso(r[0]), _num(r[4]), _num(r[2])))
            except Exception:  # noqa: BLE001
                continue
    if not out:
        raise LookupError("FMTQIK 비어 있음")
    return out


# ── TWSE 일별 3종 ───────────────────────────────────────────
def twse_breadth(ymd):
    """MI_INDEX(type=MS): 상승·하락 종목 수 (주식 기준) → (adv, dec)"""
    j = _twse_json("/afterTrading/MI_INDEX", {"date": ymd, "type": "MS"})
    adv = dec = None
    for title, fields, rows in _tables(j):
        for r in rows:
            if not r:
                continue
            head = re.sub(r"<[^>]+>", "", str(r[0]))
            vals = [_num(x) for x in r[1:]]
            vals = [v for v in vals if v is not None]
            if not vals:
                continue
            v = vals[-1]                     # 마지막 칸 = '股票' 열
            if head.startswith("上漲") and adv is None:
                adv = v
            elif head.startswith("下跌") and dec is None:
                dec = v
    if adv is None or dec is None:
        raise LookupError("MI_INDEX에서 상승/하락 수를 찾지 못했어요")
    return adv, dec


def twse_margin(ymd):
    """MI_MARGN(selectType=MS): 융자 잔액(仟元) 오늘 값"""
    j = _twse_json("/marginTrading/MI_MARGN", {"date": ymd, "selectType": "MS"})
    for title, fields, rows in _tables(j):
        for r in rows:
            if r and "融資金額" in str(r[0]):
                v = _num(r[-1])
                if v:
                    return v
    raise LookupError("MI_MARGN에서 融資金額을 찾지 못했어요")


def twse_foreign(ymd):
    """BFI82U: 외국인(외자+외자자영상) 순매수 금액(원) → 억 대만달러"""
    j = _twse_json("/fund/BFI82U", {"type": "day", "dayDate": ymd})
    tot, hit = 0.0, False
    for title, fields, rows in _tables(j):
        for r in rows:
            name = str(r[0])
            if name.startswith("外資") or name.startswith("Foreign"):
                v = _num(r[-1])
                if v is not None:
                    tot += v
                    hit = True
    if not hit:
        raise LookupError("BFI82U에서 外資 행을 찾지 못했어요")
    return round(tot / 1e8, 2)


# ── TAIFEX 풋/콜 비율 ───────────────────────────────────────
def taifex_pcr(start, end):
    """기간 [start, end] (date) → {날짜: 풋/콜 거래량 비율(%)}"""
    form = {"queryStartDate": start.strftime("%Y/%m/%d"), "queryEndDate": end.strftime("%Y/%m/%d")}
    r = requests.post("https://www.taifex.com.tw/cht/3/pcRatioDown", data=form, headers=UA, timeout=30)
    r.raise_for_status()
    raw = r.content
    for enc in ("cp950", "big5", "utf-8-sig"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    out = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 4 or not re.match(r"\d{4}/\d{1,2}/\d{1,2}", row[0].strip()):
            continue
        y, m, d = [int(x) for x in row[0].strip().split("/")]
        v = _num(row[3])                      # 買賣權成交量比率%
        if v is not None:
            out[date(y, m, d).isoformat()] = v
    if not out:
        # CSV가 안 오면 HTML 표로 한 번 더 시도
        h = requests.post("https://www.taifex.com.tw/cht/3/pcRatio", data=form, headers=UA, timeout=30).text
        for m in re.finditer(r"(\d{4}/\d{1,2}/\d{1,2})</td>(.*?)</tr>", h, re.S):
            cells = re.findall(r"<td[^>]*>(.*?)</td>", m.group(2), re.S)
            if len(cells) >= 3:
                v = _num(cells[2])
                if v is not None:
                    y, mo, d = [int(x) for x in m.group(1).split("/")]
                    out[date(y, mo, d).isoformat()] = v
    if not out:
        raise LookupError("TAIFEX 풋/콜 비율을 읽지 못했어요")
    return out


# ── 미국 CNN ────────────────────────────────────────────────
def cnn_fear_greed():
    base = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/"
    h = dict(UA, Referer="https://edition.cnn.com/", Origin="https://edition.cnn.com")
    start = (datetime.now(TW_TZ).date() - timedelta(days=220)).isoformat()
    try:
        j = _get(base + start, headers=h).json()       # 시작일을 주면 과거 기록(차트용)이 함께 와요
    except Exception:  # noqa: BLE001
        j = _get(base, headers=h).json()
    fg = j["fear_and_greed"]
    ts = fg.get("timestamp", "")
    as_of = str(ts)[:10]
    hist = {}
    for p in j.get("fear_and_greed_historical", {}).get("data", []):
        d = datetime.fromtimestamp(p["x"] / 1000, tz=timezone.utc).date().isoformat()
        hist[d] = int(round(p["y"]))
    return {
        "score": int(round(fg["score"])),
        "previous_close": _r(fg.get("previous_close")),
        "previous_1_week": _r(fg.get("previous_1_week")),
        "previous_1_month": _r(fg.get("previous_1_month")),
        "as_of": as_of,
        "url": "https://edition.cnn.com/markets/fear-and-greed",
    }, hist


def _r(v):
    return None if v is None else int(round(float(v)))


# ── 형제 사이트 (일본·한국) ─────────────────────────────────
def _dig(obj, path):
    for k in path.split("."):
        if isinstance(obj, dict) and k in obj:
            obj = obj[k]
        else:
            return None
    return obj


def _kr_comments(html):
    """한국 사이트 index.html 의 COMMENTS 배열에서 (날짜, 한국 점수)를 최신순으로 뽑기"""
    i = html.find("COMMENTS = [")
    if i < 0:
        raise LookupError("COMMENTS 목록을 찾지 못했어요")
    out = []
    for m in re.finditer(r"date:\s*'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일[^']*'.*?kr:\s*\{\s*score:\s*(\d+)", html[i:i + 200000], re.S):
        y, mo, d, sc = (int(x) for x in m.groups())
        out.append((date(y, mo, d).isoformat(), sc))
        if len(out) >= 2:
            break
    if not out:
        raise LookupError("COMMENTS 안에서 한국 점수를 찾지 못했어요")
    return out


def sister_site(cfg):
    """API(JSON)를 먼저 쓰고, 실패하면 시황 코멘트 점수로 대체"""
    try:
        return _sister_site(cfg)
    except Exception:
        if cfg.get("json") and cfg.get("html_comments"):
            return _sister_site({k: v for k, v in cfg.items() if k != "json"})
        raise


def _sister_site(cfg):
    if cfg.get("html_comments") and not cfg.get("json"):
        # 한국 사이트 정적 페이지의 시황 코멘트 점수 (API가 없을 때만 사용)
        rows = _kr_comments(_get(cfg["html_comments"]).text)
        return {"score": rows[0][1], "previous_close": rows[1][1] if len(rows) > 1 else None,
                "as_of": rows[0][0], "url": cfg.get("url", ""), "_raw": {}}
    if not cfg.get("json"):
        raise LookupError("JSON 주소가 설정되지 않았어요")
    j = _get(cfg["json"]).json()
    score = _dig(j, cfg["score_path"])
    if score is None:
        raise LookupError("점수 위치(%s)를 찾지 못했어요" % cfg["score_path"])
    return {
        "score": int(round(float(score))),
        "previous_close": _r(_dig(j, cfg.get("prev_path", ""))) if cfg.get("prev_path") else None,
        "as_of": str(_dig(j, cfg.get("asof_path", "")) or "")[:10],
        "url": cfg.get("url", ""),
        "_raw": j,
    }

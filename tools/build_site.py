#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사이트 빌드: data/latest.json + content/posts/*.py + content/insights/*.py → public/ (배포 폴더)
  python tools/build_site.py
"""
import json
import os
import shutil
import sys
from datetime import datetime
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import config as C  # noqa: E402
import checks  # noqa: E402
import layout as L  # noqa: E402
import pages  # noqa: E402
import posts as P  # noqa: E402
import svg  # noqa: E402

try:
    import og_image  # 썸네일 자동 생성 (Pillow 필요)
except Exception as _e:  # noqa: BLE001
    og_image = None
    print("  ⚠ 썸네일 자동 생성 끔 (Pillow 없음): %s" % _e)


def make_og(rel, score, as_of, others):
    """public/<rel> 에 썸네일을 만들고 '/<rel>' 주소를 돌려줘요. 실패하면 기본 썸네일."""
    if og_image is None or score is None:
        return "/assets/og.png"
    try:
        og_image.make(os.path.join(OUT, rel), score, as_of, others)
        return "/" + rel
    except Exception as e:  # noqa: BLE001
        print("  ⚠ 썸네일 생성 실패(%s): %s" % (rel, e))
        return "/assets/og.png"

OUT = os.path.join(ROOT, "public")
DATA = os.path.join(ROOT, "data", "latest.json")
MIN_CHARS = {"daily": 1200, "insight": 2500}   # 공백 제외 최소 글자 수


def write(rel, html):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)


def fmt_num(v, d=2):
    return "{:,.{}f}".format(v, d)


def head(eyebrow, title, link=None, link_text=""):
    a = '<a href="%s">%s →</a>' % (link, link_text) if link else ""
    return '<div class="sec-head"><div><span class="eyebrow">%s</span><h2>%s</h2></div>%s</div>' % (eyebrow, title, a)


def kv(label, v):
    if v is None:
        return "<div><span>%s</span><b>–</b></div>" % label
    zn, zc = svg.zone_of(v)
    return '<div><span>%s</span><b>%d</b><em style="color:%s">%s</em></div>' % (label, v, zc, zn)


# ── 메인 페이지 설명 섹션 (공탐지수란? / 구간별 가이드 / 실전 활용 / 주의사항 / FAQ) ──
ZONE_GUIDE = [
    ("極度恐懼", "0–24", "恐慌性賣壓、融資斷頭、外資大量賣超，新聞標題普遍悲觀。",
     ["是否因恐慌而想全部賣出？先回頭檢查原本的投資理由是否改變", "現金部位是否足夠應付持續下跌", "若有分批計畫，確認每一批的條件與金額"]),
    ("恐懼", "25–44", "量縮觀望、反彈無力，多數人選擇等待。",
     ["觀察外資賣超是否收斂、融資是否止跌", "比較台股與美日韓是否同步改善", "避免因短線反彈而臨時改變計畫"]),
    ("中性", "45–54", "多空拉鋸、區間整理，方向尚未明確。",
     ["回到基本面與自己的資產配置比例", "檢查持股是否過度集中在單一產業", "定期定額或既定計畫照常執行"]),
    ("貪婪", "55–74", "追價意願提高，融資回升，題材股輪動加快。",
     ["新增買進前，確認是否只是因為「大家都在買」", "檢視槓桿與融資使用是否過高", "預先設定停利或再平衡的規則"]),
    ("極度貪婪", "75–100", "市場普遍樂觀，熱門股成交爆量，追高風險升高。",
     ["檢查持股比重是否已偏離原本的配置", "留意融資快速增加、漲跌家數背離等過熱訊號", "思考若回檔 10–20%，自己是否承受得住"]),
]
FAQ_ITEMS = [
    ("台股恐懼貪婪指數是什麼？", "把台股的市場情緒換算成 0（極度恐懼）到 100（極度貪婪）的分數。恐貪雷達參考 CNN 指數的概念，改用加權指數、融資餘額、外資買賣超、台指選擇權等台灣在地資料計算。"),
    ("台股恐懼貪婪指數和恐慌指數（VIX）有什麼不同？", "恐慌指數只看選擇權反映的波動預期；恐懼貪婪指數綜合動能、波動、漲跌家數、融資、外資、選擇權與匯率七個面向，更完整反映市場情緒。"),
    ("多久更新一次？", "每個交易日收盤後約 15:40 更新，晚間約 21:40 再補上融資等較晚公布的資料。國定假日與颱風休市不更新。"),
    ("分數低就代表該買進嗎？", "不一定。指數描述的是目前的情緒，不是買賣訊號。極度恐懼可能持續數週，請搭配基本面與自身資金規劃判斷。"),
    ("指數多少算「低」？", "0–24 為極度恐懼、25–44 為恐懼。但比起單一數字，更值得注意的是變化速度，例如三天內從 70 掉到 30。"),
    ("可以用來做短線交易嗎？", "不建議。指數以收盤資料計算並取三日平均，適合觀察中期情緒變化，不適合當作盤中或隔日的進出依據。"),
    ("為什麼和 CNN 的數字不一樣？", "CNN 指數只看美股，恐貪雷達的台股指數使用台灣市場資料，兩者計算方式不同，比較方向與變化會更有意義。"),
]


def build_learn_sections():
    out = {}
    out["what"] = (
        '<section>%s<div class="card learn-what"><div>'
        "<p>恐懼貪婪指數（Fear &amp; Greed Index）是把市場情緒變成 <b>0 到 100 的一個數字</b>。數字越低，代表投資人越恐懼、急著賣出；"
        "數字越高，代表投資人越貪婪、搶著買進。美國 CNN 的版本只看美股，恐貪雷達則改用<b>台股在地資料</b>計算，"
        "包括外資買賣超、融資餘額、台指選擇權與新台幣匯率等台灣投資人最關心的數據。</p>"
        "<p>「別人貪婪時我恐懼，別人恐懼時我貪婪。」市場常被情緒推著走，這個指數的用途，是在你追高或殺低之前，"
        "先提醒你現在的市場溫度。</p></div>"
        '<ul class="facts"><li><b>0–100</b><span>極度恐懼 ↔ 極度貪婪</span></li>'
        '<li><b>7 項</b><span>台股在地指標</span></li><li><b>每日</b><span>收盤後自動更新</span></li></ul>'
        '</div></section>' % head("WHAT IS IT", "恐懼貪婪指數是什麼？", "/guide", "新手指南"))
    cards = []
    for (mx, _n, color), (name, rng, scene, checks_) in zip(C.ZONES, ZONE_GUIDE):
        cards.append('<div class="zone-card" style="--zc:%s"><div class="zc-head"><b>%s</b><span>%s</span></div>'
                     '<p class="scene">%s</p><p class="small muted" style="margin:8px 0 2px">可以檢查的事</p><ul>%s</ul></div>'
                     % (color, name, rng, scene, "".join("<li>%s</li>" % c for c in checks_)))
    out["zones"] = ('<section>%s<div class="zone-grid">%s</div>'
                    '<p class="note">※ 以上為一般性的觀察重點，並非買賣建議。每個人的資金、目標與風險承受度不同，請依自身情況判斷。</p></section>'
                    % (head("ZONE GUIDE", "各區間的觀察與應對指南"), "".join(cards)))
    steps = [
        ("看方向，不只看數字", "同樣是 30 分，從 60 掉下來和從 10 爬上來，代表的意義完全不同。先看最近一週的變化方向。"),
        ("拆開七項指標", "用雷達圖找出是哪一項拖累分數：外資撤出、融資斷頭還是波動放大，原因不同，持續時間也不同。"),
        ("對照美日韓", "四個市場同時恐懼，多半是全球事件；只有台股特別恐懼，則可能是權值股或資金面的在地因素。"),
        ("寫下自己的規則", "事先決定「指數低於多少時檢查一次持股」「高於多少時重新平衡」，讓情緒指標幫你守紀律，而不是被情緒帶著走。"),
    ]
    out["howto"] = ('<section>%s<ol class="steps">%s</ol></section>'
                    % (head("HOW TO USE", "恐懼貪婪指數實戰運用"),
                       "".join('<li><b>%s</b><p>%s</p></li>' % (t, d) for t, d in steps)))
    cautions = [
        ("不是買賣訊號", "指數描述的是現在的情緒，不能預測明天的漲跌。"),
        ("極端狀態可能持續", "極度恐懼或極度貪婪可能維持數週，過早反向操作同樣有風險。"),
        ("各市場算法不同", "台股、美股、日股、韓股的指數不宜直接比大小，請比較各自的變化。"),
        ("資料可能修正", "官方資料偶有更正，過去的分數可能出現 1–2 分的調整。"),
        ("請自行承擔風險", "本站不推薦個股、不提供投資顧問服務，投資決定請依自身狀況判斷。"),
    ]
    out["caution"] = ('<section>%s<div class="caution-grid">%s</div></section>'
                      % (head("BEFORE YOU INVEST", "投資前一定要知道的注意事項"),
                         "".join('<div class="caution"><b>%s</b><p>%s</p></div>' % (t, d) for t, d in cautions)))
    return out


# ─────────────────────────────────────────────
def build_index(d, daily, insights):
    d = d or {}
    tw = d.get("tw")
    if tw:
        zn, zc = svg.zone_of(tw["score"])
        tx = tw.get("taiex", {})
        chg = ""
        if tx.get("change") is not None:
            cls, arrow = ("up", "▲") if tx["change"] >= 0 else ("down", "▼")
            chg = '<span class="%s num">%s %s（%+.2f%%）</span>' % (cls, arrow, fmt_num(abs(tx["change"])), tx["change_pct"])
        hero = """
<section class="hero">
  <div class="hero-dial">
    <div class="eyebrow">TAIWAN FEAR &amp; GREED RADAR</div>
    <div class="dial-wrap">{dial}
      <div class="dial-center"><b>{score}</b><span class="zone-pill" style="background:{zc};color:{ztxt}">{zn}</span></div>
    </div>
    <div class="stamp">資料日 {asof}・更新 {upd}（台灣時間）{stale}</div>
  </div>
  <div class="hero-info">
    <h1>今日台股恐懼貪婪指數：{score}（{zn}）</h1>
    <p class="lead">恐貪雷達每個交易日收盤後，用 7 項台灣在地指標掃描市場情緒。0 代表極度恐懼，100 代表極度貪婪。</p>
    <div class="kv">{k1}{k2}{k3}</div>
    <div class="taiex"><span class="t">加權指數收盤</span><b>{close}</b>{chg}</div>
    <div class="trust"><span>證交所・期交所官方資料</span><span>計算方法公開</span><span>每日收盤後更新</span></div>
  </div>
</section>""".format(
            dial=svg.dial(tw["score"], 330, dark=True, title="台股恐懼貪婪指數 %d" % tw["score"]), score=tw["score"],
            zc=zc, zn=zn, ztxt="#0F1E33" if zn == "中性" else "#fff", asof=tw["as_of"].replace("-", "/"),
            upd=escape(d.get("updated_at_tw", "")[5:]), stale='<span class="stale">資料延遲</span>' if tw.get("stale") else "",
            k1=kv("前一交易日", tw.get("previous_close")), k2=kv("一週前", tw.get("previous_1_week")),
            k3=kv("一個月前", tw.get("previous_1_month")), close=fmt_num(tx.get("close", 0)), chg=chg)
    else:
        hero = '<section class="card"><h1>台股恐懼貪婪指數</h1><p class="muted">資料準備中，請稍後再來。</p></section>'

    # 4개 시장
    rows = []
    for code, name, sub, dd, link, main in (
            ("TW", "台股", "恐貪雷達計算", tw, "/methodology", True),
            ("US", "美股", "CNN 官方數值", d.get("us"), "https://edition.cnn.com/markets/fear-and-greed", False),
            ("JP", "日股", "日經225・姊妹站", d.get("jp"), C.JP_SITE.get("url"), False),
            ("KR", "韓股", "KOSPI・姊妹站", d.get("kr"), C.KR_SITE.get("url"), False)):
        sc = dd.get("score") if dd else None
        zn, zc = svg.zone_of(sc) if sc is not None else ("準備中", "#7A8899")
        prev = dd.get("previous_close") if dd else None
        delta = ""
        if sc is not None and prev is not None:
            delta = "<small>前日 %d（%+d）</small>" % (prev, sc - prev)
        inner = ('<div class="name"><span class="code">%s</span>%s<small>%s</small></div>'
                 '<div class="sc" style="color:%s">%s</div>%s<div class="zl" style="color:%s">%s%s</div>'
                 % (code, name, sub, zc, sc if sc is not None else "–", svg.scale_row(sc), zc, zn, delta))
        cls = "mkt-row" + (" main" if main else "")
        if link:
            ext = "" if link.startswith("/") else ' target="_blank" rel="noopener"'
            rows.append('<a class="%s" href="%s"%s>%s</a>' % (cls, escape(link), ext, inner))
        else:
            rows.append('<div class="%s">%s</div>' % (cls, inner))
    markets = ('<section>%s<div class="card" style="padding:6px 20px">%s</div>'
               '<p class="note">※ 各市場的計算方式不同（美股為 CNN 官方數值），數字高低不宜直接比較，建議觀察各自的方向與變化。</p></section>'
               % (head("MARKET RADAR", "四大市場情緒一覽"), "".join(rows)))

    # 레이더 + 지표
    radar_sec = ""
    if tw and tw.get("indicators"):
        li = []
        for i in tw["indicators"]:
            zn, zc = svg.zone_of(i["value"])
            raw = ("%+.2f" % i["raw"]) if i["unit"] in ("%", "億元") else "%.2f" % i["raw"]
            li.append('<li><div class="nm">%s<small>%s%s・權重 %d%%</small></div>%s<div class="v" style="color:%s">%d</div></li>'
                      % (escape(i["name"]), raw, i["unit"], round(i["weight"] * 100), svg.bar(i["value"]), zc, i["value"]))
        desc = "".join("<tr><td><b>%s</b></td><td>%s</td></tr>" % (escape(i["name"]), escape(i["desc"])) for i in tw["indicators"])
        miss = ('<p class="note">今日暫缺：%s（其餘指標依比例計算）</p>' % "、".join(tw["missing"])) if tw.get("missing") else ""
        radar_sec = ('<section>%s<div class="card"><div class="radar-grid"><div>%s</div><div><ul class="ind-list">%s</ul>'
                     '<details class="ind-more"><summary>各指標代表什麼？</summary><div class="tbl"><table><tbody>%s</tbody></table></div></details>'
                     '</div></div></div>%s</section>'
                     % (head("7 SIGNALS", "七項指標雷達圖", "/methodology", "計算方法"),
                        svg.radar([(i["name"], i["value"]) for i in tw["indicators"]]), "".join(li), desc, miss))

    chart = ""
    if d.get("history"):
        chart = ('<section>%s<div class="card">%s<div class="legend"><span><i></i>台股恐懼貪婪指數</span>'
                 '<span><i class="us"></i>美股（CNN）</span></div></div></section>' % (head("6 MONTHS", "近六個月走勢"), svg.history_chart(d["history"])))

    ins = list(reversed(insights))[:3]
    ins_sec = ('<section>%s%s</section>' % (head("RADAR INSIGHTS", "雷達洞察｜恐貪雷達獨家分析", "/insights/", "全部洞察"),
               ('<div class="posts">%s</div>' % "".join(post_card(p) for p in ins)) if ins else
               '<div class="empty">獨家市場分析即將推出。</div>'))
    blog = ""
    if daily:
        blog = '<section>%s<div class="posts">%s</div></section>' % (
            head("DAILY REPORT", "每日指數日報", "/blog/", "全部日報"), "".join(post_card(p) for p in list(reversed(daily))[:3]))

    learn = build_learn_sections()
    faq_items = FAQ_ITEMS
    faq = '<section>%s%s</section>' % (head("FAQ", "常見問題（FAQ）"), "".join(
        '<details class="faq"%s><summary>%s</summary><p>%s</p></details>' % (" open" if i == 0 else "", escape(q), escape(a))
        for i, (q, a) in enumerate(faq_items)))

    body = (hero + markets + L.ad_slot() + radar_sec + chart + learn["what"] + learn["zones"] + ins_sec + L.ad_slot()
            + blog + learn["howto"] + learn["caution"] + faq)
    jsonld = [
        {"@context": "https://schema.org", "@type": "WebSite", "name": C.SITE_NAME, "alternateName": [C.SITE_SUBTITLE, C.SITE_NAME_EN, "Fear & Greed Taiwan", "feargreedtaiwan.com"],
         "url": C.SITE_URL + "/", "inLanguage": "zh-TW"},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq_items]},
    ]
    desc = C.HOME_DESCRIPTION
    if tw:
        desc = "今日台股恐懼貪婪指數 %d（%s）。" % (tw["score"], svg.zone_of(tw["score"])[0]) + desc
    og = "/assets/og.png"
    if tw:
        og = make_og("og/tw-%s.png" % tw["as_of"].replace("-", ""), tw["score"], tw["as_of"],
                     [(n, (d.get(k) or {}).get("score")) for n, k in (("美股", "us"), ("日股", "jp"), ("韓股", "kr"))])
    return L.page("/", C.HOME_TITLE, desc, body, jsonld=jsonld, active="/", og_image=og)


def post_card(p):
    tags = "".join('<span class="chip">%s</span>' % escape(t) for t in list(p.TAGS)[:2])
    ex = getattr(p, "CARD_EXCERPT", p.EXCERPT)
    sc = ""
    if p.TW_SCORE is not None:
        zn, zc = svg.zone_of(p.TW_SCORE)
        sc = '<span class="sc" style="color:%s">台股 %d・%s</span>' % (zc, p.TW_SCORE, zn)
    cls = "post-card insight" if p.KIND == "insight" else "post-card"
    cat = '<span class="chip ins">雷達洞察</span>' if p.KIND == "insight" else ""
    return ('<a class="%s" href="%s"><div class="meta"><span>%s</span>%s</div><h3>%s</h3><p>%s</p><div style="margin-top:10px">%s%s</div></a>'
            % (cls, p.PATH, P.date_label(p.DATE_ISO), sc, escape(p.TITLE), escape(ex), cat, tags))


def score_b(v):
    if v is None:
        return "<b>–</b>"
    zn, zc = svg.zone_of(v)
    return '<b style="color:%s">%d</b> <span class="small" style="color:%s;font-weight:700">%s</span>' % (zc, v, zc, zn)


def build_post(p, prev, nxt):
    body_html = p.build()
    simp, terms = checks.check_text(body_html + p.TITLE + p.DESCRIPTION)
    if simp:
        raise SystemExit("【간체자 발견】%s : %s  → 번체로 고쳐 주세요" % (p.FILE, "".join(simp)))
    for k, v in terms:
        print("  ⚠ %s : 대륙식 표현 「%s」 → 대만식 「%s」 권장" % (p.FILE, k, v))
    n = checks.char_count(body_html)
    need = MIN_CHARS[p.KIND]
    if n < need and not getattr(p, "ALLOW_SHORT", False):
        raise SystemExit("【글이 너무 짧아요】%s : %d자 (최소 %d자, 공백 제외)" % (p.FILE, n, need))
    if p.KIND == "insight":
        if "<svg" not in body_html:
            raise SystemExit("【그래프 없음】%s : 雷達洞察 글에는 그래프(line_chart/bar_chart)가 꼭 1개 이상 필요해요" % p.FILE)
        if "<table" not in body_html:
            raise SystemExit("【표 없음】%s : 雷達洞察 글에는 표(table)가 꼭 1개 이상 필요해요" % p.FILE)
    cells = []
    for lab, v in (("台股", p.TW_SCORE), ("美股（CNN）", p.US_SCORE), ("日股", p.JP_SCORE), ("韓股", p.KR_SCORE)):
        if v is not None:
            cells.append('<div><span class="small muted">%s</span><br>%s</div>' % (lab, score_b(v)))
    board = '<div class="scoreboard">%s</div>' % "".join(cells) if cells else ""
    if p.KIND == "insight":
        sec_path, sec_name = "/insights/", "雷達洞察"
    elif p.CATEGORY != "每日指數日報":           # 가이드 글은 新手指南 아래로
        sec_path, sec_name = "/guide", "新手指南"
    else:
        sec_path, sec_name = "/blog/", "每日日報"
    crumb_label = getattr(p, "CRUMB_LABEL", P.date_label(p.DATE_ISO))
    pn = '<div class="pn">%s%s</div>' % (
        ('<a href="%s"><small>← 上一篇</small>%s</a>' % (prev.PATH, escape(prev.TITLE))) if prev else "<span></span>",
        ('<a href="%s" style="text-align:right"><small>下一篇 →</small>%s</a>' % (nxt.PATH, escape(nxt.TITLE))) if nxt else "<span></span>")
    tags = "".join('<span class="chip">#%s</span>' % escape(t) for t in p.TAGS)
    html = """
<article class="article">
<p class="crumb"><a href="/">首頁</a> › <a href="{sp}">{sn}</a> › {crumb}</p>
<span class="chip{ci}">{cat}</span>
<h1>{title}</h1>
<div class="byline"><span>發布 {pub}</span>{upd}<span>作者 {op}</span><span>約 {mins} 分鐘讀完</span></div>
{board}
{ad}
{body}
<div style="margin-top:22px">{tags}</div>
{share}
<p class="disclaimer">本文內容僅供資訊參考，不構成任何投資建議或買賣邀約。台股指數為恐貪雷達依公開資料自行計算，計算方式請見<a href="/methodology">計算方法</a>。如發現錯誤，歡迎<a href="/contact">來信指正</a>。</p>
{pn}
</article>""".format(sp=sec_path, sn=sec_name, crumb=escape(crumb_label), ci=" ins" if p.KIND == "insight" else "",
                     cat=escape(p.CATEGORY), title=escape(p.TITLE), pub=p.PUBLISHED_ISO[:16].replace("T", " "),
                     upd=("<span>更新 %s</span>" % p.UPDATED_ISO[:16].replace("T", " ")) if getattr(p, "UPDATED_ISO", None) else "",
                     op=escape(C.OPERATOR_NAME), mins=max(1, round(n / 500)), board=board, ad=L.ad_slot(), body=body_html,
                     tags=tags, share=L.share_buttons(p.PATH, p.TITLE), pn=pn)
    jsonld = [
        {"@context": "https://schema.org", "@type": "Article", "headline": p.TITLE, "description": p.DESCRIPTION,
         "datePublished": p.PUBLISHED_ISO, "dateModified": getattr(p, "UPDATED_ISO", p.PUBLISHED_ISO),
         "inLanguage": "zh-TW", "keywords": ",".join(p.TAGS), "mainEntityOfPage": L.url(p.PATH),
         "image": C.SITE_URL + "/assets/og.png",
         "author": {"@type": "Organization", "name": C.OPERATOR_NAME, "url": C.SITE_URL + "/about"},
         "publisher": {"@type": "Organization", "name": C.SITE_NAME, "logo": {"@type": "ImageObject", "url": C.SITE_URL + "/assets/apple-touch-icon.png"}}},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首頁", "item": C.SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": sec_name, "item": C.SITE_URL + sec_path},
            {"@type": "ListItem", "position": 3, "name": p.TITLE, "item": L.url(p.PATH)}]},
    ]
    og = "/assets/og.png"
    if p.KIND == "daily" and p.TW_SCORE is not None:
        og = make_og("og/post-%s.png" % p.SLUG, p.TW_SCORE, p.DATE_ISO, [("美股", p.US_SCORE), ("日股", p.JP_SCORE), ("韓股", p.KR_SCORE)])
    jsonld[0]["image"] = C.SITE_URL + og
    write(p.PATH.lstrip("/") + ".html", L.page(p.PATH, p.META_TITLE, p.DESCRIPTION, html, og_type="article", jsonld=jsonld, active=sec_path, og_image=og))
    return n


def build_list(path, eyebrow, title, lead, items, meta_title, meta_desc, empty):
    cards = "".join(post_card(p) for p in reversed(items)) or '<div class="empty" style="grid-column:1/-1">%s</div>' % empty
    body = ('<p class="crumb"><a href="/">首頁</a> › %s</p><div class="page-head"><span class="small" style="color:var(--cyan-d);font-weight:700;letter-spacing:.18em">%s</span>'
            '<h1>%s</h1><p>%s</p></div><div class="posts">%s</div>' % (title, eyebrow, title, lead, cards))
    write(path.lstrip("/") + "index.html", L.page(path, meta_title, meta_desc, body, active=path))


def build_feeds(all_posts):
    today = datetime.now().strftime("%Y-%m-%d")
    urls = [("/", today, "daily", "1.0"), ("/blog/", today, "daily", "0.8"), ("/insights/", today, "weekly", "0.8"),
            ("/methodology", C.LAUNCH_DATE, "monthly", "0.6"), ("/guide", C.LAUNCH_DATE, "monthly", "0.6"),
            ("/about", C.LAUNCH_DATE, "yearly", "0.3"), ("/privacy", C.LAUNCH_DATE, "yearly", "0.2"),
            ("/terms", C.LAUNCH_DATE, "yearly", "0.2"), ("/contact", C.LAUNCH_DATE, "yearly", "0.2")]
    for p in all_posts:
        urls.append((p.PATH, getattr(p, "UPDATED_ISO", p.PUBLISHED_ISO)[:10], "monthly", "0.7"))
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, lm, cf, pr in urls:
        sm.append("<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq><priority>%s</priority></url>" % (escape(L.url(u)), lm, cf, pr))
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm))
    items = []
    for p in sorted(all_posts, key=lambda x: x.PUBLISHED_ISO, reverse=True)[:30]:
        dt = datetime.fromisoformat(p.PUBLISHED_ISO)
        items.append("<item><title>%s</title><link>%s</link><guid>%s</guid><pubDate>%s</pubDate><category>%s</category><description>%s</description></item>"
                     % (escape(p.TITLE), L.url(p.PATH), L.url(p.PATH), dt.strftime("%a, %d %b %Y %H:%M:%S %z"), escape(p.CATEGORY), escape(p.DESCRIPTION)))
    write("feed.xml", '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>%s｜%s</title><link>%s/</link>'
          '<description>%s</description><language>zh-TW</language>%s</channel></rss>'
          % (escape(C.SITE_NAME), escape(C.SITE_SUBTITLE), C.SITE_URL, escape(C.SITE_TAGLINE), "".join(items)))
    write("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % C.SITE_URL)
    if C.ADSENSE_CLIENT:
        write("ads.txt", "google.com, %s, DIRECT, f08c47fec0942fa0\n" % C.ADSENSE_CLIENT.replace("ca-", ""))
    write("CNAME", C.SITE_URL.split("://", 1)[-1].strip("/") + "\n")


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(os.path.join(ROOT, "static"), OUT)
    if os.path.exists(os.path.join(OUT, "assets", "favicon.ico")):
        shutil.copy(os.path.join(OUT, "assets", "favicon.ico"), os.path.join(OUT, "favicon.ico"))
    d = None
    if os.path.exists(DATA):
        with open(DATA, encoding="utf-8") as f:
            d = json.load(f)
        os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
        shutil.copy(DATA, os.path.join(OUT, "data", "latest.json"))
    all_daily, insights = P.load("daily"), P.load("insight")
    # 每日日報 목록에는 시황 글만, 가이드 글(CATEGORY가 다른 글)은 新手指南 페이지의 延伸閱讀로
    daily = [p for p in all_daily if p.CATEGORY == "每日指數日報"]
    guides = [p for p in all_daily if p.CATEGORY != "每日指數日報"]
    write("index.html", build_index(d, daily, insights))
    for path, title, desc, fn in [
        ("methodology", "台股恐懼貪婪指數計算方法", "恐貪雷達台股恐懼貪婪指數的七項指標、權重、資料來源與計算方式完整公開。", pages.methodology),
        ("guide", "恐懼貪婪指數是什麼？新手指南", "恐懼貪婪指數是什麼？台股版與 CNN 美股版、恐慌指數有何不同？一次看懂分數區間與正確使用方式。", pages.guide),
        ("about", "關於我們", "恐貪雷達的營運理念、原則與聯絡資訊。", pages.about),
        ("privacy", "隱私權政策", "恐貪雷達隱私權政策與 Cookie、Google AdSense 使用說明。", pages.privacy),
        ("terms", "使用條款與免責聲明", "恐貪雷達使用條款與投資免責聲明。", pages.terms),
        ("contact", "聯絡我們", "與恐貪雷達聯絡的方式。", pages.contact),
    ]:
        html = fn()
        if path == "guide" and guides:
            html = html.replace("</article>", '<h2>延伸閱讀</h2><div class="posts">%s</div></article>'
                                % "".join(post_card(g) for g in reversed(guides)))
        simp, _ = checks.check_text(html)
        if simp:
            raise SystemExit("【간체자】%s: %s" % (path, "".join(simp)))
        write(path + ".html", L.page("/" + path, title, desc, html, active="/" + path))
    write("404.html", L.page("/404", "找不到頁面", "找不到頁面", pages.not_found(), noindex=True))
    for group in (daily, guides, insights):
        for i, p in enumerate(group):
            build_post(p, group[i - 1] if i > 0 else None, group[i + 1] if i + 1 < len(group) else None)
    build_list("/blog/", "DAILY REPORT", "每日指數日報", "每個交易日用恐懼貪婪指數解讀台股、美股與亞洲市場的情緒變化。", daily,
               "台股恐懼貪婪指數每日日報", "恐貪雷達每日日報：台股恐懼貪婪指數、加權指數、外資、融資與美股情緒的每日變化。", "日報準備中。")
    build_list("/insights/", "RADAR INSIGHTS", "雷達洞察", "恐貪雷達獨家市場分析：用數據、圖表與表格，深入解讀台股與總體經濟。", insights,
               "雷達洞察｜台股與經濟獨家分析", "恐貪雷達獨家分析：以恐懼貪婪指數、外資、融資等數據與圖表，深入解讀台股與總體經濟。", "獨家市場分析即將推出。")
    build_feeds(all_daily + insights)
    print("✅ 빌드 완료: 일일 글 %d개, 인사이트 %d개, 대만 점수 %s" % (len(daily), len(insights), (d or {}).get("tw", {}).get("score", "없음")))


if __name__ == "__main__":
    main()

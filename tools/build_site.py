#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사이트 빌드: data/latest.json + content/posts/*.py → public/ (배포 폴더)
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

OUT = os.path.join(ROOT, "public")
DATA = os.path.join(ROOT, "data", "latest.json")
MIN_CHARS = 1200      # 글 본문 최소 글자 수(공백 제외). 짧으면 애드센스 '가치 없는 콘텐츠' 위험


def write(rel, html):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)


def fmt_num(v, d=2):
    return "{:,.{}f}".format(v, d)


def diff_html(cur, old, label):
    if cur is None or old is None:
        return '<div><b>–</b><span>%s</span></div>' % label
    return '<div><b>%d</b><span>%s（%s）</span></div>' % (old, label, svg.zone_of(old)[0])


# ─────────────────────────────────────────────
def market_card(code, name, d, link, main=False, note=""):
    if not d or d.get("score") is None:
        inner = svg.gauge(None, 180, name) + '<div class="num">–</div><div class="lab muted">準備中</div>'
    else:
        zn, zc = svg.zone_of(d["score"])
        inner = (svg.gauge(d["score"], 180, "%s %d" % (name, d["score"])) +
                 '<div class="num">%d</div><div class="lab" style="color:%s">%s</div>' % (d["score"], zc, zn) +
                 '<div class="small muted">%s%s</div>' % (("資料日 " + d["as_of"].replace("-", "/")) if d.get("as_of") else "",
                                                          '<span class="stale">延遲</span>' if d.get("stale") else ""))
    head = '<span class="chip">%s</span><h3>%s</h3>' % (code, name)
    cls = "card mkt" + (" main" if main else "")
    if link:
        ext = "" if link.startswith("/") else ' target="_blank" rel="noopener"'
        return '<a class="%s" href="%s"%s>%s%s<div class="small muted">%s</div></a>' % (cls, escape(link), ext, head, inner, note)
    return '<div class="%s">%s%s<div class="small muted">%s</div></div>' % (cls, head, inner, note)


def build_index(d, posts):
    tw = (d or {}).get("tw")
    if tw:
        zn, zc = svg.zone_of(tw["score"])
        tx = tw.get("taiex", {})
        chg = ""
        if tx.get("change") is not None:
            cls, arrow = ("up", "▲") if tx["change"] >= 0 else ("down", "▼")
            chg = ' <span class="%s">%s%s（%+.2f%%）</span>' % (cls, arrow, fmt_num(abs(tx["change"])), tx["change_pct"])
        hero = """
<section class="card hero">
  <div>
    <h1>台股恐懼貪婪指數</h1>
    <p class="lead">用台股在地資料計算的市場情緒指標，每個交易日更新。目前市場情緒為<b style="color:{zc}">「{zn}」</b>。</p>
    <p class="taiex">加權指數 <b>{close}</b>{chg}</p>
    <div class="cmp">{c1}{c2}{c3}</div>
    <p class="asof">資料日：{asof}　更新時間：{upd}（台灣時間）{stale}</p>
  </div>
  <div class="score-wrap">
    {gauge}
    <div class="score-num">{score}</div>
    <span class="score-label" style="background:{zc};color:{ztxt}">{zn}</span>
  </div>
</section>""".format(zc=zc, zn=zn, ztxt="#1B2A3A" if zn == "中性" else "#fff", close=fmt_num(tx.get("close", 0)), chg=chg,
                     c1=diff_html(tw["score"], tw.get("previous_close"), "前一交易日"),
                     c2=diff_html(tw["score"], tw.get("previous_1_week"), "一週前"),
                     c3=diff_html(tw["score"], tw.get("previous_1_month"), "一個月前"),
                     asof=P.date_label(tw["as_of"]), upd=escape(d.get("updated_at_tw", "")),
                     stale='<span class="stale">資料延遲，顯示前次數值</span>' if tw.get("stale") else "",
                     gauge=svg.gauge(tw["score"], 300, "台股恐懼貪婪指數 %d" % tw["score"]), score=tw["score"])
    else:
        hero = '<section class="card hero"><div><h1>台股恐懼貪婪指數</h1><p class="lead">資料準備中，請稍後再來。</p></div></section>'

    markets = """
<section>
  <h2 class="sec">四大市場情緒一覽</h2>
  <div class="markets">{tw}{us}{jp}{kr}</div>
  <p class="note">※ 各市場指數的計算方式不同（美股為 CNN 官方數值），數字高低不宜直接比較，建議觀察各自的方向與變化。</p>
</section>""".format(
        tw=market_card("TW", "台股", tw, "/methodology", main=True, note="本站計算"),
        us=market_card("US", "美股（CNN）", (d or {}).get("us"), "https://edition.cnn.com/markets/fear-and-greed", note="CNN Business"),
        jp=market_card("JP", "日股", (d or {}).get("jp"), C.JP_SITE.get("url"), note="姊妹站"),
        kr=market_card("KR", "韓股", (d or {}).get("kr"), C.KR_SITE.get("url"), note="姊妹站"))

    inds = ""
    if tw and tw.get("indicators"):
        cards = []
        for i in tw["indicators"]:
            zn, zc = svg.zone_of(i["value"])
            raw = ("%+.2f" % i["raw"]) if i["unit"] in ("%", "億元") else "%.2f" % i["raw"]
            cards.append('<div class="card ind"><div class="ind-top"><b>%s</b><span class="v" style="color:%s">%d</span></div>%s'
                         '<p>%s</p><p class="small muted">目前數值 %s%s　｜　權重 %d%%　｜　%s</p></div>'
                         % (escape(i["name"]), zc, i["value"], svg.bar(i["value"]), escape(i["desc"]), raw, i["unit"],
                            round(i["weight"] * 100), zn))
        miss = ""
        if tw.get("missing"):
            miss = '<p class="note">今日暫缺：%s（其餘指標依比例計算）</p>' % "、".join(tw["missing"])
        inds = '<section><h2 class="sec">七項指標拆解</h2><div class="inds">%s</div>%s<p class="small"><a href="/methodology">→ 查看完整計算方法</a></p></section>' % ("".join(cards), miss)

    chart = ""
    if d and d.get("history"):
        chart = ('<section class="card"><h2 class="sec">近六個月走勢</h2>%s'
                 '<div class="legend"><span><i></i>台股恐懼貪婪指數</span><span><i class="us"></i>美股（CNN）</span></div></section>'
                 % svg.history_chart(d["history"]))

    latest = [p for p in reversed(posts)][:3]
    pc = "".join(post_card(p) for p in latest)
    blog = '<section><h2 class="sec">最新市場日報</h2><div class="posts">%s</div><p class="small"><a href="/blog/">→ 看全部文章</a></p></section>' % pc if pc else ""

    faq_items = [
        ("台股恐懼貪婪指數是什麼？", "把台股的市場情緒換算成 0（極度恐懼）到 100（極度貪婪）的分數。本站參考 CNN 指數的概念，改用加權指數、融資餘額、外資買賣超、台指選擇權等台灣在地資料計算。"),
        ("多久更新一次？", "每個交易日收盤後約 15:40 更新，晚間約 21:40 再補上融資等較晚公布的資料。"),
        ("分數低就代表該買進嗎？", "不一定。指數描述的是目前的情緒，不是買賣訊號。極度恐懼可能持續一段時間，請搭配基本面與自身資金規劃判斷。"),
        ("為什麼和 CNN 的數字不一樣？", "CNN 指數只看美股，本站台股指數使用台灣市場資料，兩者計算方式不同，比較方向與變化會更有意義。"),
    ]
    faq = '<section><h2 class="sec">常見問題</h2>%s</section>' % "".join(
        "<details><summary>%s</summary><p>%s</p></details>" % (escape(q), escape(a)) for q, a in faq_items)
    zones = '<section class="card"><h2 class="sec">分數怎麼看？</h2>%s</section>' % pages.zone_table()

    body = hero + markets + L.ad_slot() + inds + chart + zones + L.ad_slot() + blog + faq
    jsonld = [
        {"@context": "https://schema.org", "@type": "WebSite", "name": C.SITE_NAME, "alternateName": C.SITE_NAME_EN,
         "url": C.SITE_URL + "/", "inLanguage": "zh-TW"},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq_items]},
    ]
    desc = "台股恐懼貪婪指數每日更新：以加權指數、融資餘額、外資買賣超、台指選擇權等七項指標計算市場情緒，並同步比較美股 CNN、日股、韓股恐懼貪婪指數。"
    if tw:
        desc = "今日台股恐懼貪婪指數 %d（%s）。" % (tw["score"], svg.zone_of(tw["score"])[0]) + desc
    title = "台股恐懼貪婪指數｜今日台股市場情緒（Fear & Greed Index）"
    return L.page("/", title, desc, body, jsonld=jsonld, active="/")


def post_card(p):
    tags = "".join('<span class="chip">%s</span>' % escape(t) for t in list(p.TAGS)[:2])
    ex = getattr(p, "CARD_EXCERPT", p.EXCERPT)
    return ('<a class="card post-card" href="%s"><span class="small muted">%s</span><h3>%s</h3><p>%s</p><div style="margin-top:8px">%s</div></a>'
            % (p.PATH, P.date_label(p.DATE_ISO), escape(p.TITLE), escape(ex), tags))


def build_post(p, prev, nxt):
    body_html = p.build()
    simp, terms = checks.check_text(body_html + p.TITLE + p.DESCRIPTION)
    if simp:
        raise SystemExit("【간체자 발견】%s : %s  → 번체로 고쳐 주세요" % (p.FILE, "".join(simp)))
    for k, v in terms:
        print("  ⚠ %s : 대륙식 표현 「%s」 → 대만식 「%s」 권장" % (p.FILE, k, v))
    n = checks.char_count(body_html)
    if n < MIN_CHARS and not getattr(p, "ALLOW_SHORT", False):
        raise SystemExit("【글이 너무 짧아요】%s : %d자 (최소 %d자, 공백 제외)" % (p.FILE, n, MIN_CHARS))
    board = '<div class="scoreboard"><div><span class="small muted">台股</span><br>%s</div><div><span class="small muted">美股（CNN）</span><br>%s</div>%s%s</div>' % (
        score_b(p.TW_SCORE), score_b(p.US_SCORE),
        ('<div><span class="small muted">日股</span><br>%s</div>' % score_b(p.JP_SCORE)) if getattr(p, "JP_SCORE", None) is not None else "",
        ('<div><span class="small muted">韓股</span><br>%s</div>' % score_b(p.KR_SCORE)) if getattr(p, "KR_SCORE", None) is not None else "")
    if p.TW_SCORE is None and p.US_SCORE is None:
        board = ""
    crumb_label = getattr(p, "CRUMB_LABEL", P.date_label(p.DATE_ISO) + " " + p.CATEGORY)
    pn = '<div class="pn">%s%s</div>' % (
        ('<a href="%s">← %s</a>' % (prev.PATH, escape(prev.TITLE))) if prev else "<span></span>",
        ('<a href="%s" style="text-align:right">%s →</a>' % (nxt.PATH, escape(nxt.TITLE))) if nxt else "<span></span>")
    tags = "".join('<span class="chip">#%s</span>' % escape(t) for t in p.TAGS)
    html = """
<article class="article">
<p class="crumb"><a href="/">首頁</a> › <a href="/blog/">市場日報</a> › {crumb}</p>
<span class="chip">{cat}</span>
<h1>{title}</h1>
<p class="small muted">發布：{pub}{upd}　｜　作者：{op}</p>
{board}
{ad}
{body}
<div style="margin-top:20px">{tags}</div>
{share}
<p class="disclaimer">本文內容僅供資訊參考，不構成任何投資建議或買賣邀約。指數為本站依公開資料自行計算，計算方式請見<a href="/methodology">計算方法</a>。</p>
{pn}
</article>""".format(crumb=escape(crumb_label), cat=escape(p.CATEGORY), title=escape(p.TITLE),
                     pub=p.PUBLISHED_ISO[:16].replace("T", " "),
                     upd=("　更新：" + p.UPDATED_ISO[:16].replace("T", " ")) if getattr(p, "UPDATED_ISO", None) else "",
                     op=escape(C.OPERATOR_NAME), board=board, ad=L.ad_slot(), body=body_html, tags=tags,
                     share=L.share_buttons(p.PATH, p.TITLE), pn=pn)
    jsonld = [
        {"@context": "https://schema.org", "@type": "Article", "headline": p.TITLE, "description": p.DESCRIPTION,
         "datePublished": p.PUBLISHED_ISO, "dateModified": getattr(p, "UPDATED_ISO", p.PUBLISHED_ISO),
         "inLanguage": "zh-TW", "keywords": ",".join(p.TAGS), "mainEntityOfPage": L.url(p.PATH),
         "author": {"@type": "Organization", "name": C.OPERATOR_NAME, "url": C.SITE_URL + "/about"},
         "publisher": {"@type": "Organization", "name": C.SITE_NAME, "logo": {"@type": "ImageObject", "url": C.SITE_URL + "/assets/favicon.svg"}}},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首頁", "item": C.SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "市場日報", "item": C.SITE_URL + "/blog/"},
            {"@type": "ListItem", "position": 3, "name": p.TITLE, "item": L.url(p.PATH)}]},
    ]
    write("blog/%s.html" % p.SLUG, L.page(p.PATH, p.META_TITLE, p.DESCRIPTION, html, og_type="article", jsonld=jsonld, active="/blog/"))
    return n


def score_b(v):
    if v is None:
        return "<b>–</b>"
    zn, zc = svg.zone_of(v)
    return '<b>%d</b> <span class="small" style="color:%s;font-weight:700">%s</span>' % (v, zc, zn)


def build_blog_index(posts):
    cards = "".join(post_card(p) for p in reversed(posts)) or '<p class="muted">文章準備中。</p>'
    body = ('<p class="crumb"><a href="/">首頁</a> › 市場日報</p><h1>市場日報</h1>'
            '<p class="muted">每天用恐懼貪婪指數解讀台股、美股與亞洲市場的情緒變化。</p><div class="posts">%s</div>' % cards)
    write("blog/index.html", L.page("/blog/", "市場日報｜台股恐懼貪婪指數每日解讀",
                                    "台股恐懼貪婪指數每日市場日報：整理加權指數、外資、融資與美股情緒的變化與重點。", body, active="/blog/"))


def build_feeds(posts):
    today = datetime.now().strftime("%Y-%m-%d")
    urls = [("/", today, "daily", "1.0"), ("/blog/", today, "daily", "0.8"), ("/methodology", C.LAUNCH_DATE, "monthly", "0.6"),
            ("/guide", C.LAUNCH_DATE, "monthly", "0.6"), ("/about", C.LAUNCH_DATE, "yearly", "0.3"),
            ("/privacy", C.LAUNCH_DATE, "yearly", "0.2"), ("/terms", C.LAUNCH_DATE, "yearly", "0.2"), ("/contact", C.LAUNCH_DATE, "yearly", "0.2")]
    for p in posts:
        urls.append((p.PATH, getattr(p, "UPDATED_ISO", p.PUBLISHED_ISO)[:10], "monthly", "0.7"))
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, lm, cf, pr in urls:
        sm.append("<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq><priority>%s</priority></url>" % (escape(L.url(u)), lm, cf, pr))
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm))
    items = []
    for p in list(reversed(posts))[:30]:
        dt = datetime.fromisoformat(p.PUBLISHED_ISO)
        items.append("<item><title>%s</title><link>%s</link><guid>%s</guid><pubDate>%s</pubDate><description>%s</description></item>"
                     % (escape(p.TITLE), L.url(p.PATH), L.url(p.PATH), dt.strftime("%a, %d %b %Y %H:%M:%S %z"), escape(p.DESCRIPTION)))
    write("feed.xml", '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>%s</title><link>%s/</link>'
          '<description>%s</description><language>zh-TW</language>%s</channel></rss>' % (escape(C.SITE_NAME), C.SITE_URL, escape(C.SITE_TAGLINE), "".join(items)))
    write("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % C.SITE_URL)
    if C.ADSENSE_CLIENT:
        write("ads.txt", "google.com, %s, DIRECT, f08c47fec0942fa0\n" % C.ADSENSE_CLIENT.replace("ca-", ""))
    host = C.SITE_URL.split("://", 1)[-1].strip("/")
    write("CNAME", host + "\n")


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(os.path.join(ROOT, "static"), OUT)
    d = None
    if os.path.exists(DATA):
        with open(DATA, encoding="utf-8") as f:
            d = json.load(f)
        os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
        shutil.copy(DATA, os.path.join(OUT, "data", "latest.json"))
    posts = P.load()
    write("index.html", build_index(d, posts))
    for path, title, desc, fn in [
        ("methodology", "計算方法", "台股恐懼貪婪指數的七項指標、權重、資料來源與計算方式完整公開。", pages.methodology),
        ("guide", "新手指南：恐懼貪婪指數怎麼看", "恐懼貪婪指數是什麼？台股版與 CNN 美股版有何不同？一次看懂分數區間與正確使用方式。", pages.guide),
        ("about", "關於我們", "台股恐懼貪婪指數的營運理念、原則與聯絡資訊。", pages.about),
        ("privacy", "隱私權政策", "本站隱私權政策與 Cookie、Google AdSense 使用說明。", pages.privacy),
        ("terms", "使用條款與免責聲明", "本站使用條款與投資免責聲明。", pages.terms),
        ("contact", "聯絡我們", "與台股恐懼貪婪指數聯絡的方式。", pages.contact),
    ]:
        html = fn()
        simp, _ = checks.check_text(html)
        if simp:
            raise SystemExit("【간체자】%s: %s" % (path, "".join(simp)))
        write(path + ".html", L.page("/" + path, title, desc, html, active="/" + path))
    write("404.html", L.page("/404", "找不到頁面", "找不到頁面", pages.not_found(), noindex=True))
    total = 0
    for i, p in enumerate(posts):
        total += build_post(p, posts[i - 1] if i > 0 else None, posts[i + 1] if i + 1 < len(posts) else None)
    build_blog_index(posts)
    build_feeds(posts)
    print("✅ 빌드 완료: 글 %d개, 대만 점수 %s, 출력 폴더 public/" % (len(posts), (d or {}).get("tw", {}).get("score", "없음")))


if __name__ == "__main__":
    main()

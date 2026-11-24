# -*- coding: utf-8 -*-
"""모든 페이지 공통 틀 (head, 상단 메뉴, 하단 정보)"""
import json
import os
import sys
from html import escape
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C  # noqa: E402

ASSET_VER = "3"
NAV = [("/", "今日指數"), ("/blog/", "每日日報"), ("/insights/", "雷達洞察"), ("/methodology", "計算方法"), ("/guide", "新手指南"), ("/about", "關於我們")]


def url(path):
    return C.SITE_URL + path


def adsense_head():
    if not C.ADSENSE_CLIENT:
        return ""
    return ('<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=%s" '
            'crossorigin="anonymous"></script>' % C.ADSENSE_CLIENT)


def ad_slot(name="top"):
    """광고 자리. 애드센스 ID/슬롯이 없으면 아무것도 출력하지 않아요 (빈 박스 방지)"""
    if not (C.ADSENSE_CLIENT and C.ADSENSE_SLOT_TOP):
        return ""
    return ('<div class="ad" aria-label="廣告"><span class="ad-label">廣告</span>'
            '<ins class="adsbygoogle" style="display:block" data-ad-client="%s" data-ad-slot="%s" '
            'data-ad-format="auto" data-full-width-responsive="true"></ins>'
            '<script>(adsbygoogle=window.adsbygoogle||[]).push({});</script></div>' % (C.ADSENSE_CLIENT, C.ADSENSE_SLOT_TOP))


def ga_head():
    if not C.GA_ID:
        return ""
    if C.GA_ID.startswith("GTM-"):
        # 구글 태그(GTM 컨테이너) 방식: 받은 코드 그대로
        return ('<script async src="https://www.googletagmanager.com/gtm.js?id={0}"></script>'
                '<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}'
                'gtag("js",new Date());</script>').format(C.GA_ID)
    return ('<script async src="https://www.googletagmanager.com/gtag/js?id={0}"></script>'
            '<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}'
            'gtag("js",new Date());gtag("config","{0}");</script>').format(C.GA_ID)


def page(path, title, description, body, og_type="website", jsonld=None, noindex=False, active="/", og_image="/assets/og.png"):
    brand = "%s %s" % (C.SITE_NAME, C.SITE_NAME_EN)          # 예: 恐貪雷達 FearGreedTaiwan
    if title == C.HOME_TITLE or C.SITE_NAME_EN in title:   # 메인 제목은 config 그대로
        full_title = title
    elif C.SITE_NAME in title:
        full_title = "%s｜%s" % (title, C.SITE_NAME_EN)
    else:
        full_title = "%s｜%s" % (title, brand)
    meta = []
    if C.GOOGLE_SITE_VERIFICATION:
        meta.append('<meta name="google-site-verification" content="%s">' % C.GOOGLE_SITE_VERIFICATION)
    if C.BING_SITE_VERIFICATION:
        meta.append('<meta name="msvalidate.01" content="%s">' % C.BING_SITE_VERIFICATION)
    if noindex:
        meta.append('<meta name="robots" content="noindex">')
    ld = ""
    for obj in (jsonld or []):
        ld += '<script type="application/ld+json">%s</script>' % json.dumps(obj, ensure_ascii=False)
    nav = "".join('<a href="%s"%s>%s</a>' % (h, ' aria-current="page"' if h == active else "", t) for h, t in NAV)
    return """<!DOCTYPE html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{site}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{ogimg}">
<meta property="og:locale" content="zh_TW">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0F1E33">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="{site}" href="/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css?v={ver}">
{meta}{ga}{ads}{ld}
</head>
<body>
<a class="skip" href="#main">跳至主要內容</a>
<header class="site-header">
  <div class="wrap hdr">
    <a class="brand" href="/" aria-label="{site} 首頁">
      <img src="/assets/favicon.svg" width="38" height="38" alt="">
      <span><b>{site}</b><small>{sub}</small></span>
    </a>
    <button class="menu-btn" aria-label="選單" aria-expanded="false" onclick="var n=document.querySelector('.nav');var o=n.classList.toggle('open');this.setAttribute('aria-expanded',o)">選單</button>
    <nav class="nav">{nav}</nav>
  </div>
</header>
<main id="main" class="wrap">
{body}
</main>
<footer class="site-footer">
  <div class="wrap foot">
    <div>
      <p class="foot-brand"><img src="/assets/favicon.svg" width="26" height="26" alt=""> {site}<span>{sub}</span></p>
      <p>本站內容僅供資訊參考，不構成任何投資建議或買賣邀約。投資有風險，請自行判斷並承擔責任。</p>
      <p class="small">資料來源：臺灣證券交易所、臺灣期貨交易所、Yahoo Finance、CNN Business。台股指數由本站依公開資料自行計算，<a href="/methodology">計算方法完整公開</a>。</p>
    </div>
    <div class="foot-links">
      <b>內容</b><a href="/">今日指數</a><a href="/blog/">每日日報</a><a href="/insights/">雷達洞察</a><a href="/guide">新手指南</a><a href="/feed.xml">RSS 訂閱</a>
    </div>
    <div class="foot-links">
      <b>關於</b><a href="/about">關於我們</a><a href="/methodology">計算方法</a><a href="/privacy">隱私權政策</a><a href="/terms">使用條款與免責聲明</a><a href="/contact">聯絡我們</a>
    </div>
    <div class="foot-links">
      <b>其他市場</b>{sister}<a href="https://edition.cnn.com/markets/fear-and-greed" rel="noopener" target="_blank">CNN 美股恐懼貪婪指數</a>
    </div>
  </div>
  <p class="wrap copy small">© {year} {operator}</p>
</footer>
</body>
</html>""".format(
        title=escape(full_title), desc=escape(description), canon=escape(url(path)), og_type=og_type,
        site=escape(C.SITE_NAME), site_en=escape(C.SITE_NAME_EN), sub=escape(C.SITE_SUBTITLE), ogimg=escape(url(og_image)), ver=ASSET_VER,
        meta="\n".join(meta), ga=ga_head(), ads=adsense_head(), ld=ld, nav=nav, body=body,
        sister=sister_links(), year=C.LAUNCH_DATE[:4], operator=escape(C.OPERATOR_NAME))


def sister_links():
    out = []
    if C.JP_SITE.get("url"):
        out.append('<a href="%s" rel="noopener" target="_blank">日股恐懼貪婪指數</a>' % escape(C.JP_SITE["url"]))
    if C.KR_SITE.get("url"):
        out.append('<a href="%s" rel="noopener" target="_blank">韓股恐懼貪婪指數</a>' % escape(C.KR_SITE["url"]))
    return "".join(out)


def share_buttons(path, title):
    u = quote(url(path), safe="")
    t = quote(title, safe="")
    return ('<div class="share"><span class="small muted">分享：</span>'
            '<a class="sh line" href="https://social-plugins.line.me/lineit/share?url={u}" target="_blank" rel="noopener">LINE</a>'
            '<a class="sh fb" href="https://www.facebook.com/sharer/sharer.php?u={u}" target="_blank" rel="noopener">Facebook</a>'
            '<a class="sh x" href="https://twitter.com/intent/tweet?url={u}&amp;text={t}" target="_blank" rel="noopener">X</a>'
            '<a class="sh th" href="https://www.threads.net/intent/post?text={t}%20{u}" target="_blank" rel="noopener">Threads</a>'
            '</div>').format(u=u, t=t)

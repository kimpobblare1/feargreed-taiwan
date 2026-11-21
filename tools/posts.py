# -*- coding: utf-8 -*-
"""
글 등록부 (자동 읽기) — 파일을 올리기만 하면 목록·이전/다음 글·사이트맵·RSS가 자동으로 바뀌어요.

  ① 每日指數日報 (매일 쓰는 공탐지수 글)
     content/posts/blog_post_YYYYMMDD.py        → /blog/YYYYMMDD
     같은 날 두 번째 글: blog_post_YYYYMMDD-guide.py
     필수: DATE_ISO, DATE_ID, PUBLISHED_ISO, TITLE, META_TITLE, DESCRIPTION, EXCERPT, TAGS, TW_SCORE, US_SCORE, build()

  ② 雷達洞察 (요청할 때 쓰는 고유 분석 글, 2,500자 이상 + 표 + 그래프 필수)
     content/insights/insight_YYYYMMDD-영어.py  → /insights/YYYYMMDD-영어
     필수: DATE_ISO, DATE_ID, PUBLISHED_ISO, TITLE, META_TITLE, DESCRIPTION, EXCERPT, TAGS, build()

  (선택) CATEGORY / JP_SCORE / KR_SCORE / UPDATED_ISO / CARD_EXCERPT / CRUMB_LABEL / ALLOW_SHORT
"""
import glob
import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = ["DATE_ISO", "DATE_ID", "PUBLISHED_ISO", "TITLE", "META_TITLE", "DESCRIPTION", "EXCERPT", "TAGS", "build"]
KINDS = {
    "daily": {"dir": os.path.join(ROOT, "content", "posts"), "prefix": "blog_post_", "base": "/blog",
              "required": BASE + ["TW_SCORE", "US_SCORE"], "category": "每日指數日報", "slug_re": r"\d{8}(?:-[a-z0-9]+)?"},
    "insight": {"dir": os.path.join(ROOT, "content", "insights"), "prefix": "insight_", "base": "/insights",
                "required": BASE, "category": "雷達洞察", "slug_re": r"\d{8}-[a-z0-9-]+"},
}
WEEKDAY = ["一", "二", "三", "四", "五", "六", "日"]


def _fail(msg):
    raise SystemExit("【글 파일 오류】" + msg)


def load(kind="daily"):
    k = KINDS[kind]
    for p in (k["dir"], os.path.dirname(os.path.abspath(__file__))):
        if p not in sys.path:
            sys.path.insert(0, p)
    posts = []
    for path in sorted(glob.glob(os.path.join(k["dir"], k["prefix"] + "*.py"))):
        fn = os.path.basename(path)
        m = re.match(re.escape(k["prefix"]) + "(" + k["slug_re"] + r")\.py$", fn)
        if not m:
            ex = "blog_post_20261120.py" if kind == "daily" else "insight_20261125-ai-supply-chain.py"
            _fail("%s : 파일 이름 형식이 달라요 (예: %s)" % (fn, ex))
        try:
            spec = importlib.util.spec_from_file_location("%s_%s" % (kind, m.group(1).replace("-", "_")), path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except SyntaxError as e:
            _fail("%s 의 %d번째 줄에 문법 오류가 있어요: %s" % (fn, e.lineno or 0, e.msg))
        except Exception as e:  # noqa: BLE001
            _fail("%s 를 읽지 못했어요: %s: %s" % (fn, type(e).__name__, e))
        lack = [x for x in k["required"] if not hasattr(mod, x)]
        if lack:
            _fail("%s 에 빠진 항목: %s" % (fn, ", ".join(lack)))
        if mod.DATE_ID != m.group(1):
            _fail("%s : DATE_ID(%s)가 파일 이름(%s)과 달라요" % (fn, mod.DATE_ID, m.group(1)))
        if mod.DATE_ID[:8] != mod.DATE_ISO.replace("-", ""):
            _fail("%s : DATE_ISO(%s)와 DATE_ID(%s)의 날짜가 달라요" % (fn, mod.DATE_ISO, mod.DATE_ID))
        mod.KIND = kind
        mod.FILE = fn
        mod.SLUG = mod.DATE_ID
        mod.PATH = "%s/%s" % (k["base"], mod.SLUG)
        mod.CATEGORY = getattr(mod, "CATEGORY", k["category"])
        for opt in ("TW_SCORE", "US_SCORE", "JP_SCORE", "KR_SCORE"):
            if not hasattr(mod, opt):
                setattr(mod, opt, None)
        posts.append(mod)
    posts.sort(key=lambda p: (p.DATE_ISO, 0 if "-" in p.DATE_ID else 1, p.DATE_ID))
    return posts


def date_label(iso):
    import datetime as _dt
    y, m, d = [int(x) for x in iso.split("-")]
    return "%d年%d月%d日（%s）" % (y, m, d, WEEKDAY[_dt.date(y, m, d).weekday()])

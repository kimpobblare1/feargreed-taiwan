# -*- coding: utf-8 -*-
"""
블로그 글 등록부 (자동 읽기) — 일본 사이트와 같은 방식
  content/posts/ 에 blog_post_YYYYMMDD.py 를 올리기만 하면 끝!
  같은 날 두 번째 글은 blog_post_YYYYMMDD-guide.py 처럼 '-영어소문자'를 붙여요.
  → 글 목록, 이전/다음 글, 사이트맵, RSS, 메인의 최신 글이 전부 자동으로 바뀝니다.

  글 파일에 꼭 있어야 하는 항목:
    DATE_ISO, DATE_ID, PUBLISHED_ISO, TITLE, META_TITLE, DESCRIPTION, EXCERPT, TAGS, TW_SCORE, US_SCORE, build()
  (선택) CATEGORY = "市場日報" 또는 "投資指南" / JP_SCORE / KR_SCORE / UPDATED_ISO
         ALLOW_SHORT = True  (글자 수 하한 검사 면제)
"""
import glob
import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.environ.get("POSTS_DIR") or os.path.join(ROOT, "content", "posts")
REQUIRED = ["DATE_ISO", "DATE_ID", "PUBLISHED_ISO", "TITLE", "META_TITLE", "DESCRIPTION", "EXCERPT", "TAGS",
            "TW_SCORE", "US_SCORE", "build"]
WEEKDAY = ["一", "二", "三", "四", "五", "六", "日"]


def _fail(msg):
    raise SystemExit("【글 파일 오류】" + msg)


def load():
    for p in (POSTS_DIR, os.path.dirname(os.path.abspath(__file__))):
        if p not in sys.path:
            sys.path.insert(0, p)
    posts = []
    for path in sorted(glob.glob(os.path.join(POSTS_DIR, "blog_post_*.py"))):
        fn = os.path.basename(path)
        m = re.match(r"blog_post_(\d{8}(?:-[a-z0-9]+)?)\.py$", fn)
        if not m:
            _fail("%s : 파일 이름은 blog_post_20261120.py 또는 blog_post_20261120-guide.py 형식이어야 해요" % fn)
        try:
            spec = importlib.util.spec_from_file_location("post_" + m.group(1).replace("-", "_"), path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except SyntaxError as e:
            _fail("%s 의 %d번째 줄에 문법 오류가 있어요: %s" % (fn, e.lineno or 0, e.msg))
        except Exception as e:  # noqa: BLE001
            _fail("%s 를 읽지 못했어요: %s: %s" % (fn, type(e).__name__, e))
        lack = [k for k in REQUIRED if not hasattr(mod, k)]
        if lack:
            _fail("%s 에 빠진 항목: %s" % (fn, ", ".join(lack)))
        if mod.DATE_ID != m.group(1):
            _fail("%s : DATE_ID(%s)가 파일 이름(%s)과 달라요" % (fn, mod.DATE_ID, m.group(1)))
        if mod.DATE_ID[:8] != mod.DATE_ISO.replace("-", ""):
            _fail("%s : DATE_ISO(%s)와 DATE_ID(%s)의 날짜가 달라요" % (fn, mod.DATE_ISO, mod.DATE_ID))
        mod.FILE = fn
        mod.SLUG = mod.DATE_ID
        mod.PATH = "/blog/%s" % mod.SLUG
        mod.CATEGORY = getattr(mod, "CATEGORY", "市場日報")
        posts.append(mod)
    # 날짜순. 같은 날이면 가이드(-slug)가 앞, 시황이 뒤 → 최신 글은 시황
    posts.sort(key=lambda p: (p.DATE_ISO, 0 if "-" in p.DATE_ID else 1, p.DATE_ID))
    return posts


def date_label(iso):
    y, m, d = [int(x) for x in iso.split("-")]
    import datetime as _dt
    wd = WEEKDAY[_dt.date(y, m, d).weekday()]
    return "%d年%d月%d日（%s）" % (y, m, d, wd)

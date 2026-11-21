# -*- coding: utf-8 -*-
"""
사이트 전체 설정 (여기만 바꾸면 모든 페이지에 반영돼요)
  ※ 주석은 한국어, 화면에 나오는 글은 대만 번체 중국어(zh-Hant-TW)입니다.
"""

# ── 기본 정보 ─────────────────────────────────────────────
SITE_URL = "https://feargreedtaiwan.com"        # ← 실제 도메인으로 바꾸세요 (끝에 / 없이)
SITE_NAME = "台股恐懼貪婪指數"                    # 화면에 크게 나오는 이름
SITE_NAME_EN = "Fear & Greed Taiwan"
SITE_TAGLINE = "每天一眼看懂台股市場情緒"          # 부제 (매일 한눈에 보는 대만 증시 심리)
OPERATOR_NAME = "Fear & Greed Taiwan 編輯部"     # 운영자 표기 (본인 닉네임/회사명으로 바꿔도 됨)
CONTACT_EMAIL = "contact@feargreedtaiwan.com"   # ← 실제로 받을 수 있는 메일로 바꾸세요
LAUNCH_DATE = "2026-11-20"                       # 사이트 개설일 (약관 제정일 등에 사용)

# ── 광고·분석 (애드센스 승인 전에는 비워 두세요) ────────────
ADSENSE_CLIENT = ""      # 예: "ca-pub-9496300145102373"  → 넣으면 모든 페이지에 광고 코드 + ads.txt 자동 생성
ADSENSE_SLOT_TOP = ""    # 광고 단위 ID (선택). 비워 두면 '자동 광고'만 사용
GA_ID = ""               # 예: "G-XXXXXXXXXX"  (대만 사이트용 새 속성을 만드는 것을 권장)

# ── 검색엔진 소유 확인 메타태그 (HTML 태그 방식일 때만) ─────
GOOGLE_SITE_VERIFICATION = ""   # 서치콘솔 'HTML 태그'의 content 값
BING_SITE_VERIFICATION = ""     # Bing 웹마스터 'msvalidate.01'의 content 값

# ── 형제 사이트 (메인 페이지의 일본·한국 카드) ─────────────
#   json: 그 사이트가 공개하는 최신 데이터 JSON 주소
#   path: JSON 안에서 점수가 들어 있는 위치 (점으로 구분)
JP_SITE = {
    "url": "https://feargreedjapan.com",
    "json": "https://feargreedjapan.com/data/latest.json",
    "score_path": "jp.score",
    "prev_path": "jp.previous_close",
    "asof_path": "jp.as_of",
}
KR_SITE = {
    "url": "https://feargreed.co.kr",
    # 한국 사이트 게이지와 같은 실시간 점수 (하루 4번만 호출 → 부하 거의 없음)
    "json": "https://feargree-api.vercel.app/api",
    "score_path": "kr.score",
    "prev_path": "",
    "asof_path": "",
    # API가 실패할 때만: 메인 페이지 시황 코멘트의 점수로 대체
    "html_comments": "https://feargreed.co.kr/",
}

# ── 색상: 한국 사이트와 같은 계열 (극단적 공포 = 위험 신호 빨강) ─
#   흰 배경에서도 글자가 잘 보이도록 한국 사이트 색보다 한 톤 진하게 맞췄어요.
#   구간 경계도 한국·일본 사이트와 같게: 0–24 / 25–44 / 45–54 / 55–74 / 75–100
ZONES = [  # (상한, 라벨, 색)
    (24, "極度恐懼", "#E8304F"),
    (44, "恐懼", "#F26A2E"),
    (54, "中性", "#E0A800"),
    (74, "貪婪", "#22B04B"),
    (100, "極度貪婪", "#0AA5C2"),
]

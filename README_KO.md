# 대만 공포탐욕지수 사이트 — 처음 설정 가이드 (비개발자용)

## 폴더 구조
| 폴더/파일 | 하는 일 | 내가 손댈 일 |
|---|---|---|
| `config.py` | 사이트 이름·도메인·이메일·애드센스·형제사이트 | **처음 한 번 수정** |
| `content/posts/` | 每日日報 = 매일 공탐지수 글 (`blog_post_YYYYMMDD.py`) | **매일 1개 업로드** |
| `content/insights/` | 雷達洞察 = 요청 시 쓰는 고유 분석 글 (`insight_YYYYMMDD-주제.py`) | 필요할 때 업로드 |
| `scripts/` | 데이터 수집·지수 계산 (`update_data.py`) | 없음 |
| `tools/` | 페이지 생성 (`build_site.py`) | 없음 |
| `static/` | 디자인(CSS)·아이콘 | 없음 |
| `data/` | 자동 저장되는 원재료·결과 | 없음 (자동) |
| `public/` | 완성된 사이트 (자동 생성) | 없음 (자동) |

## 1단계. config.py 고치기
- `SITE_URL` : 산 도메인 (예: https://feargreedtaiwan.com)
- `CONTACT_EMAIL` : 실제로 받을 수 있는 메일 (애드센스 심사에서 봐요)
- `KR_SITE` : 한국 사이트 주소와 점수 JSON 주소
- `ADSENSE_CLIENT`, `GA_ID` : 승인 후에 넣기 (비워 두면 광고 코드가 안 들어가요)

## 2단계. GitHub에 올리기
1. GitHub → New repository → 이름 `feargreed-taiwan` → Create
2. **uploading an existing file** 클릭 → zip을 푼 폴더 안의 파일·폴더를 전부 끌어다 놓기 → Commit
   - `.github` 폴더가 숨김이라 안 보이면: Add file → Create new file → 이름 칸에 `.github/workflows/site.yml` 입력 → 내용 붙여넣기
3. Settings → Actions → General → Workflow permissions → **Read and write** 선택 → Save

## 3단계. 처음 한 번: 1년치 데이터 채우기 (약 40분)
Actions 탭 → update-and-build → Run workflow → backfill 칸에 **320** → Run
- 끝나면 `data/latest.json`이 생기고 대만 점수가 나와요
- 이후엔 하루 4번 자동 실행 (대만 15:40 / 21:40 / 06:37 / 09:13)

## 4단계. 배포 (둘 중 하나)
**A. Cloudflare Pages (추천 — 일본 사이트와 같은 방식, 비공개 저장소 가능)**
Cloudflare → Workers & Pages → Create → Pages → Connect to Git → 저장소 선택
→ Build command: 비움 / Build output directory: `public` → Save and Deploy → Custom domains에 도메인 연결

**B. GitHub Pages**
Settings → Pages → Source: **GitHub Actions** / Settings → Secrets and variables → Actions → Variables → `DEPLOY_GH_PAGES` = `true`

## 매일 블로그 올리기
1. `content/TEMPLATE_daily_post.py.txt`를 참고해 만든 `blog_post_20261123.py`를 `content/posts/`에 업로드 → Commit
2. 1~2분 뒤 자동으로 글 목록·사이트맵·RSS·메인 최신 글까지 반영
3. 같은 날 가이드 글을 하나 더 올릴 땐 `blog_post_20261123-guide.py`처럼 이름 뒤에 `-영어`

### 빌드가 실패하면 (Actions에 빨간 X)
| 메시지 | 뜻 |
|---|---|
| 【간체자 발견】 | 중국 대륙 글자가 섞임 → 대만 독자 신뢰도 문제라 일부러 막아요 |
| 【글이 너무 짧아요】 | 공백 빼고 日報 1,200자 / 洞察 2,500자 미만 |
| 【그래프 없음】【표 없음】 | 雷達洞察 글에 그래프·표가 빠짐 |
| 【글 파일 오류】 | 날짜 3곳 불일치, 항목 누락, 문법 오류 |
경고(⚠ 대륙식 표현)는 실패는 아니지만 고치는 게 좋아요.

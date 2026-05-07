# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행 (hot-reload)
uvicorn main:app --reload --port 8000

# 프로덕션 실행 (Procfile 기준)
uvicorn main:app --host 0.0.0.0 --port $PORT
```

환경 변수: 루트의 `.env` 파일에 `ANTHROPIC_API_KEY=...` 필요.

## Architecture

단일 파일 FastAPI 앱 (`main.py`) + 순수 HTML/CSS/JS 정적 프론트엔드.

```
main.py          ← 모든 백엔드 로직 (API + 정적 파일 서빙)
static/
  landing.html   ← 랜딩페이지 (/, Font Awesome, pricing/features 섹션 포함)
  index.html     ← 앱 UI (/app, 업로드·인터뷰·생성 플로우)
  docs.html      ← 서비스 문서 (/docs)
  qna.html       ← FAQ + 게시판 (/qna)
  logo.png       ← nav 로고 (크롭된 버전)
image/           ← 원본 이미지 에셋 (/image/* 로 서빙)
```

**FastAPI Swagger UI 비활성화됨**: `docs_url=None, redoc_url=None` — `/docs`는 우리 커스텀 문서 페이지로 사용.

## Session Flow

세션은 서버 메모리(`sessions: Dict[str, Any]`)에 UUID 키로 저장 — 서버 재시작 시 소멸, DB 없음.

```
POST /upload/file|notion|text  → session_id 발급, materials 파싱
POST /retro/save               → KPT/STAR 회고 저장 (optional)
POST /interview/start          → Claude가 꼬리 질문 3개 생성
POST /interview/answer (×3)    → 답변 누적
POST /generate                 → 포트폴리오 HTML 반환
```

## 2-Pass Portfolio Generation

`POST /generate`는 Claude를 **두 번** 호출한다:

1. **1차 호출** (`build_prompt_track_a/b`): 핵심 섹션 생성
   - Track A (JD 없음): S1 자기소개, S2 프로젝트, S3 역량 (3섹션)
   - Track B (JD 있음): S1~S5 — S4 역량매핑, S5 문제해결 추가 (5섹션)

2. **2차 호출** (`build_prompt_second_call`): 회고/지표 섹션 생성
   - Track A: S4 회고 & 성장 스토리
   - Track B: S6 회고, S7 핵심 성과 지표 테이블, S8 미보유 역량 & 학습 계획

두 결과를 문자열 concat으로 합쳐 반환. `call_claude()`는 `stop_reason == "max_tokens"`이면 자동으로 이어쓰기(최대 4회).

## Portfolio HTML 구조 규칙

생성되는 HTML의 CSS 클래스는 고정 — `index.html`의 포트폴리오 스타일시트와 맞춰야 함:

- 섹션 래퍼: `<section class="section s1">` (s1~s8)
- 항목 카드: `<div class="item">`
- 기술 태그: `<span class="tech-tag">`
- JD 키워드 강조 (Track B 전용): `<strong class="kw">`
- 전체 래퍼: `<div class="portfolio-content">`

## Job Role Templates

`TEMPLATES` dict가 4개 직군(developer/planner/designer/marketer)별로 섹션 제목과 강조 지표를 정의. `POST /generate`의 `portfolio_type` 파라미터로 선택.

## Frontend Design Tokens

`landing.html`, `docs.html`, `qna.html` 공통 CSS 변수:

```css
--p: #6366F1   /* primary indigo */
--pd: #4338CA  /* dark indigo */
--pl: #EEF2FF  /* light indigo bg */
--ok: #10B981  /* green */
--g50~g900     /* gray scale */
```

새 페이지 추가 시 이 토큰과 Font Awesome 6.5.2 CDN을 동일하게 사용할 것.

## GitHub 작업 지침

### 커밋 메시지 규칙
형식: `{type}({scope}): {summary}`

- `type`: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `style`
- `scope`: 변경 대상 (페이지, 컴포넌트, 모듈, API 등)
- `summary`: 한글, 50자 이내, 명령형 어미 사용

예시
- `feat(signup): 이메일 중복 확인 API 연동`
- `fix(auth): 토큰 만료 시 자동 로그아웃 처리`
- `refactor(api): axios 인스턴스 공통화`
- `chore(deps): React 19로 업그레이드`

---

## Claude 행동 지침

1. **현재 브랜치 확인**: 작업 시작 전 `git status`로 현재 브랜치를 확인한다. `main`이면 사용자에게 알리고 다른 브랜치로 전환할지 묻는다.
2. **커밋 단위**: 한 커밋에는 하나의 논리적 변경만 담는다.
3. **금지 동작**: `main`에 직접 commit/push, force push(`--force`), 히스토리 재작성(`rebase -i`, `reset --hard`)은 사용자의 명시적 요청 없이 수행하지 않는다.
5. **feat 브랜치 판단**: 사용자가 큰 기능을 요청하면 feat 브랜치를 팔지 먼저 묻는다. 작은 작업은 main을 제외한 현재 브랜치에서 진행.
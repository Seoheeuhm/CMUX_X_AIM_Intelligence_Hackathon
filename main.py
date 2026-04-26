import io
import json
import os
import re
import uuid
from typing import Any, Dict, List

import anthropic
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
print("KEY LOADED:", bool(os.getenv("ANTHROPIC_API_KEY")))

try:
    from pptx import Presentation
    PPTX_OK = True
except ImportError:
    PPTX_OK = False

try:
    import PyPDF2
    PDF_OK = True
except ImportError:
    PDF_OK = False

app = FastAPI(title="AI Portfolio Generator")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

sessions: Dict[str, Any] = {}


def client() -> anthropic.Anthropic:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(500, "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
    return anthropic.Anthropic(api_key=key)


def extract_pptx(data: bytes) -> str:
    if not PPTX_OK:
        raise HTTPException(400, "python-pptx가 설치되지 않았습니다.")
    prs = Presentation(io.BytesIO(data))
    parts = []
    for i, slide in enumerate(prs.slides, 1):
        texts = [s.text.strip() for s in slide.shapes if hasattr(s, "text") and s.text.strip()]
        if texts:
            parts.append(f"[슬라이드 {i}]\n" + "\n".join(texts))
    return "\n\n".join(parts)


def extract_pdf(data: bytes) -> str:
    if not PDF_OK:
        raise HTTPException(400, "PyPDF2가 설치되지 않았습니다.")
    reader = PyPDF2.PdfReader(io.BytesIO(data))
    parts = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if text.strip():
            parts.append(f"[페이지 {i}]\n{text.strip()}")
    return "\n\n".join(parts)


def scrape(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PortfolioBot/1.0)"}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "meta", "link"]):
            tag.decompose()
        lines = [ln.strip() for ln in soup.get_text("\n").splitlines() if ln.strip()]
        return "\n".join(lines[:700])
    except Exception:
        return ""


def parse_materials(text: str, source: str) -> dict:
    c = client()
    msg = c.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": (
                f"다음 포트폴리오 텍스트를 분석해서 JSON만 반환하세요 (코드블록·설명 없이).\n"
                f"출처: {source}\n\n텍스트:\n{text[:8000]}\n\n"
                '반환 형식:\n{"projects":[{"name":"","role":"","tech_stack":[],"achievements":[],"description":""}],'
                '"skills":[],"summary":""}'
            ),
        }],
    )
    raw = msg.content[0].text.strip()
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return {"projects": [], "skills": [], "summary": text[:300]}


# ── Pydantic models ──────────────────────────────────────────────────────────

class UrlReq(BaseModel):
    url: str

class InterviewStartReq(BaseModel):
    session_id: str

class InterviewAnswerReq(BaseModel):
    session_id: str
    answer: str

class RetroReq(BaseModel):
    session_id: str
    retro_type: str
    retro_data: list  # 프로젝트별 회고 리스트 [{"project":"...", "Keep":"...", ...}, ...]

class GenerateReq(BaseModel):
    session_id: str
    job_title: str
    job_posting: str
    portfolio_type: str  # developer | planner | designer | marketer


# ── Static files ─────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")


# ── Upload ────────────────────────────────────────────────────────────────────

@app.post("/upload/file")
async def upload_file(files: List[UploadFile] = File(...)):
    sid = str(uuid.uuid4())
    materials = []
    for f in files:
        name = f.filename or ""
        data = await f.read()
        ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
        if ext in ("pptx", "ppt"):
            raw = extract_pptx(data)
        elif ext == "pdf":
            raw = extract_pdf(data)
        else:
            raise HTTPException(400, f"지원하지 않는 형식: {name}")
        if not raw.strip():
            raise HTTPException(400, f"텍스트를 추출할 수 없습니다: {name}")
        parsed = parse_materials(raw, name)
        materials.append({"source": name, "raw": raw[:5000], "parsed": parsed})

    sessions[sid] = {
        "materials": materials,
        "retro": {},
        "questions": [],
        "answers": [],
        "q_index": 0,
    }
    return {"session_id": sid, "parsed": [m["parsed"] for m in materials]}


@app.post("/upload/notion")
def upload_notion(req: UrlReq):
    raw = scrape(req.url)
    if not raw:
        raise HTTPException(400, "노션 페이지를 가져올 수 없습니다. 공개 링크인지 확인해주세요.")
    sid = str(uuid.uuid4())
    parsed = parse_materials(raw, "Notion")
    sessions[sid] = {
        "materials": [{"source": "Notion", "raw": raw[:5000], "parsed": parsed}],
        "retro": {},
        "questions": [],
        "answers": [],
        "q_index": 0,
    }
    return {"session_id": sid, "parsed": [parsed]}


# ── Retrospective ─────────────────────────────────────────────────────────────

@app.post("/retro/save")
def retro_save(req: RetroReq):
    if req.session_id not in sessions:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    sessions[req.session_id]["retro"] = {
        "type": req.retro_type,
        "data": req.retro_data  # list of per-project retro dicts
    }
    return {"ok": True}


# ── Interview ─────────────────────────────────────────────────────────────────

@app.post("/interview/start")
def interview_start(req: InterviewStartReq):
    if req.session_id not in sessions:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    sess = sessions[req.session_id]
    summary = json.dumps([m["parsed"] for m in sess["materials"]], ensure_ascii=False)
    c = client()
    msg = c.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": (
                f"포트폴리오 내용:\n{summary}\n\n"
                "이 경험을 더 깊이 파악하는 꼬리 질문 3개를 JSON만 반환하세요 (설명 없이):\n"
                '{"questions":["질문1","질문2","질문3"]}\n\n'
                "질문 주제: 1) 가장 어려운 기술적/업무적 문제와 해결법 "
                "2) 구체적 성과 수치 또는 임팩트 3) 팀 내 핵심 기여와 역할"
            ),
        }],
    )
    raw = msg.content[0].text.strip()
    m = re.search(r"\{[\s\S]*\}", raw)
    qs = None
    if m:
        try:
            qs = json.loads(m.group()).get("questions")
        except Exception:
            pass
    if not qs or len(qs) < 3:
        qs = [
            "가장 큰 기술적 챌린지는 무엇이었고 어떻게 해결하셨나요?",
            "가장 자랑스러운 성과의 구체적인 수치나 임팩트가 있다면 알려주세요.",
            "팀 프로젝트에서 본인의 핵심 기여와 역할은 무엇이었나요?",
        ]
    sess["questions"] = qs
    sess["q_index"] = 0
    return {"question": qs[0], "number": 1, "total": len(qs)}


@app.post("/interview/answer")
def interview_answer(req: InterviewAnswerReq):
    if req.session_id not in sessions:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    sess = sessions[req.session_id]
    sess["answers"].append(req.answer)
    sess["q_index"] += 1
    if sess["q_index"] >= len(sess["questions"]):
        return {"done": True}
    q = sess["questions"][sess["q_index"]]
    return {"done": False, "question": q, "number": sess["q_index"] + 1, "total": len(sess["questions"])}


# ── Scrape job posting ────────────────────────────────────────────────────────

@app.post("/scrape")
def scrape_url(req: UrlReq):
    text = scrape(req.url)
    if not text:
        raise HTTPException(400, "URL을 파싱할 수 없습니다.")
    return {"text": text}


# ── Generate portfolio ────────────────────────────────────────────────────────

TEMPLATES = {
    "developer": {
        "s1_tag": "기술스택 중심 (언어·프레임워크·인프라)",
        "s3_title": "기술 역량 요약",
        "s4_metric": "성능 개선율·코드 품질·배포 횟수 등 기술 지표",
        "s5_title": "기술적 문제해결 역량",
    },
    "planner": {
        "s1_tag": "기획 방법론 중심 (리서치·UX·지표 설계)",
        "s3_title": "기획 역량 요약",
        "s4_metric": "MAU·전환율·NPS·기획 범위 등 서비스 지표",
        "s5_title": "서비스 기획 역량",
    },
    "designer": {
        "s1_tag": "툴·결과물 중심 (Figma·브랜딩·UX 개선)",
        "s3_title": "디자인 역량 요약",
        "s4_metric": "사용성 개선·브랜드 임팩트·결과물 수 등 시각 지표",
        "s5_title": "디자인 프로세스 역량",
    },
    "marketer": {
        "s1_tag": "채널·지표 중심 (캠페인·ROAS·CTR·세그먼트)",
        "s3_title": "채널 경험 요약",
        "s4_metric": "CTR·ROAS·CAC·세그먼트 수 등 퍼포먼스 지표",
        "s5_title": "데이터 기반 전략 역량",
    },
}


@app.post("/generate")
def generate(req: GenerateReq):
    if req.session_id not in sessions:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    sess = sessions[req.session_id]

    mat_json = json.dumps([m["parsed"] for m in sess["materials"]], ensure_ascii=False)

    interview_txt = ""
    for i, (q, a) in enumerate(zip(sess.get("questions", []), sess.get("answers", [])), 1):
        interview_txt += f"Q{i}. {q}\nA. {a}\n\n"

    # 프로젝트별 회고 포맷
    retro_txt = ""
    if sess.get("retro"):
        r = sess["retro"]
        rtype = r.get("type", "")
        rdata = r.get("data", [])
        if rtype and rtype != "skip" and rdata:
            retro_txt = f"회고 유형: {rtype}\n"
            if isinstance(rdata, list):
                for pr in rdata:
                    pname = pr.get("project", "프로젝트")
                    retro_txt += f"\n[프로젝트: {pname}]\n"
                    for k, val in pr.items():
                        if k != "project" and val:
                            retro_txt += f"  {k}: {val}\n"
            elif isinstance(rdata, dict):
                for k, val in rdata.items():
                    if val:
                        retro_txt += f"  {k}: {val}\n"

    tmpl = TEMPLATES.get(req.portfolio_type, TEMPLATES["developer"])

    prompt = f"""당신은 채용 전문가 겸 포트폴리오 작성 전문가입니다.
아래 지원자 정보와 채용공고를 바탕으로, 지정된 8개 섹션 구조에 맞춰 포트폴리오 HTML을 생성하세요.

[지원자 정보]
파싱된 포트폴리오: {mat_json}
인터뷰 답변: {interview_txt or "(없음)"}
회고: {retro_txt or "(없음)"}

[채용 정보]
지원 직무: {req.job_title}
채용공고: {req.job_posting[:3500]}

[직무 유형별 설정]
스킬 태그 방향: {tmpl["s1_tag"]}
경험 요약 섹션명: {tmpl["s3_title"]}
성과 지표 방향: {tmpl["s4_metric"]}
역량 섹션명: {tmpl["s5_title"]}

[출력 섹션 구조 — 반드시 아래 8개 섹션을 순서대로 모두 포함]

SECTION 1 — 지원자 핵심 요약 카드
- <section class="section s1">
- 포지셔닝 한 줄 문장 (지원자의 강점을 직무에 맞게 재해석)
- 지원 직무명
- 핵심 스킬 태그: {tmpl["s1_tag"]} 기준으로 <span class="tech-tag">태그</span> 나열

SECTION 2 — 채용공고 Fit 분석
- <section class="section s2">
- 채용공고에서 요구역량 5~8개 추출
- 각 요구역량 vs 지원자 경험 1:1 매핑 테이블
- 직접 경험: ✅ 직접 경험 / 간접 경험: 🔶 간접 경험 / 미경험: ⚠️ 학습 중
- 테이블 하단에 Fit 종합 코멘트 한 줄

SECTION 3 — {tmpl["s3_title"]}
- <section class="section s3">
- 서술형 요약 2~3줄 (지원자 전체 경험을 직무 관점으로 재해석)
- 핵심 역량 불릿 4~5개 (역량명: 경험 설명)
- 도구·툴 나열

SECTION 4 — 주요 프로젝트 카드 (프로젝트 수만큼 반복)
- <section class="section s4">
- 각 프로젝트마다 <div class="item"> 카드 1개
- 카드 내 필수 구성:
  1) 프로젝트명 + 부제목
  2) 📌 프로젝트 배경 & 목적 (문제의식과 목표, 3~4줄)
  3) 📌 담당 범위 & 기여도 (역할 / 기여도 % / 팀 구성 / 기간)
  4) 📌 핵심 과정 & 의사결정 (전체 흐름 단계 → 단계 / 왜 이 방법을 선택했는가)
  5) 📌 어려웠던 점 & 해결 (문제 상황 → 극복 방법)
  6) 📌 핵심 성과 ({tmpl["s4_metric"]} 포함, 수치 중심 3개 이상)
  7) 📌 사용 기술 (<span class="tech-tag">태그</span> 나열)

SECTION 5 — {tmpl["s5_title"]}
- <section class="section s5">
- 직무 연계 총평 2~3줄
- 역량별 불릿 (역량명: 경험 설명 — 직무 연계 의미)

SECTION 6 — 회고 & 성장 스토리
- <section class="section s6">
- 회고 데이터가 있으면 프로젝트별로 자연스러운 문장으로 재구성, 없으면 인터뷰 답변 기반으로 작성
- 3개 파트로 구성:
  1) 이 경험에서 얻은 인사이트 (2~3줄)
  2) 나의 업무 스타일 (1~2줄)
  3) 다음 프로젝트에서의 적용 계획 (1~2줄)

SECTION 7 — 핵심 성과 지표 요약
- <section class="section s7">
- 전체 프로젝트 성과를 하나의 테이블로 정리
- 컬럼: 항목 | 수치/성과 | 직무 연계 의미
- 5~8개 행

SECTION 8 — 미보유 역량 & 학습 계획
- <section class="section s8">
- 채용공고 대비 미보유/부족 역량 2~3개 솔직하게 명시
- 각 항목에 현재 보완 방법 또는 학습 계획 함께 작성

[작성 지침]
1. 채용공고의 핵심 키워드는 반드시 <strong class="kw">키워드</strong>로 강조하세요.
2. 모든 수치와 경험은 지원자 정보에 실제로 있는 내용만 사용하세요. 없으면 생략하세요.
3. 마크다운·코드블록 없이 순수 HTML 콘텐츠만 반환하세요 (html/head/body 태그 없이).
4. 전체를 <div class="portfolio-content"></div>로 감싸세요.
5. 섹션 제목은 <h2 class="section-title">으로, 항목 카드는 <div class="item">으로 작성하세요.
6. 기술 태그는 <span class="tech-tag">태그명</span>을 사용하세요.
7. 8개 섹션을 순서대로 빠짐없이 모두 생성하세요.
"""

    c = client()
    msg = c.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}],
    )
    html = msg.content[0].text.strip()

    if "```" in html:
        m = re.search(r"```(?:html)?\s*([\s\S]*?)```", html)
        if m:
            html = m.group(1).strip()

    if '<div class="portfolio-content">' not in html:
        html = f'<div class="portfolio-content">{html}</div>'

    return {
        "portfolio_html": html,
        "job_title": req.job_title,
        "portfolio_type": req.portfolio_type,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

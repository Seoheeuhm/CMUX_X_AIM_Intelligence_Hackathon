import io
import json
import os
import re
import uuid
from typing import Any, Dict, List

import anthropic
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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

app = FastAPI(title="AI Portfolio Generator", docs_url=None, redoc_url=None)
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


def clean_html(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:html)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def call_claude(c: anthropic.Anthropic, prompt: str, max_tokens: int = 8192, max_rounds: int = 4) -> str:
    """Claude 호출. max_tokens에 도달해 잘리면 자동으로 이어쓰기(최대 max_rounds회)."""
    messages = [{"role": "user", "content": prompt}]
    accumulated = ""

    for _ in range(max_rounds):
        msg = c.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            messages=messages,
        )
        chunk = msg.content[0].text
        accumulated += chunk

        if msg.stop_reason != "max_tokens":
            break

        # 잘린 경우: 지금까지 쓴 내용을 assistant 턴으로 이어붙이고 계속 요청
        messages.append({"role": "assistant", "content": chunk})
        messages.append({
            "role": "user",
            "content": (
                "HTML이 중간에 잘렸습니다. "
                "이미 작성한 내용은 반복하지 말고, "
                "잘린 부분부터 이어서 나머지 HTML을 완성해주세요. "
                "모든 열린 태그를 올바르게 닫아주세요."
            ),
        })

    return clean_html(accumulated)


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


# ── Prompt builders ───────────────────────────────────────────────────────────

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

COMMON_RULES = """
공통 HTML 규칙:
- 섹션: <section class="section">
- 섹션 제목: <h2 class="section-title">제목</h2>
- 항목 카드: <div class="item">
- 기술 태그: <span class="tech-tag">태그</span>
- 채용공고 키워드 강조(Track B만): <strong class="kw">키워드</strong>
- 마크다운·코드블록 금지, 순수 HTML만 반환
- <div class="portfolio-content"> 래퍼 없이 섹션만 반환
"""


def build_prompt_track_a(mat_json: str, interview_txt: str, tmpl: dict) -> str:
    return f"""당신은 포트폴리오 작성 전문가입니다.
아래 지원자 정보를 바탕으로 포트폴리오 HTML을 생성하세요.

[지원자 정보]
파싱된 포트폴리오: {mat_json}
인터뷰 답변: {interview_txt or "(없음)"}

[양식]
{tmpl['s1_tag']}

{COMMON_RULES}

아래 3개 섹션만 생성하세요 (순서 유지):

SECTION 1 — 자기소개 & 핵심 역량
  <section class="section s1">: 강점 3가지를 자연스러운 소개 문장으로.

SECTION 2 — 주요 프로젝트
  <section class="section s2">: 프로젝트별 카드. 각 카드에 역할·기술스택·성과 포함.

SECTION 3 — {tmpl['s3_title']}
  <section class="section s3">: 보유 기술/역량을 카테고리별로. tech-tag 적극 활용.
"""


def build_prompt_track_b(mat_json: str, interview_txt: str,
                          tmpl: dict, job_title: str, job_posting: str) -> str:
    return f"""당신은 채용 전문가 겸 포트폴리오 작성 전문가입니다.
아래 지원자 정보와 채용공고를 바탕으로 맞춤형 포트폴리오 HTML을 생성하세요.

[지원자 정보]
파싱된 포트폴리오: {mat_json}
인터뷰 답변: {interview_txt or "(없음)"}

[채용 정보]
지원 직무: {job_title}
채용공고: {job_posting[:2500]}

[양식]
{tmpl['s1_tag']}

{COMMON_RULES}

아래 5개 섹션만 생성하세요 (순서 유지):

SECTION 1 — 지원자 프로필 & 직무 적합성
  <section class="section s1">: 채용공고 요구사항에 맞춘 자기소개 + 핵심 강점 3가지.
  채용공고 키워드를 <strong class="kw">로 강조.

SECTION 2 — 주요 프로젝트
  <section class="section s2">: 프로젝트별 카드. 채용공고 관련 내용 우선 배치.
  채용공고 키워드를 <strong class="kw">로 강조.

SECTION 3 — {tmpl['s3_title']}
  <section class="section s3">: 보유 기술/역량 카테고리별 정리. tech-tag 활용.

SECTION 4 — 채용공고 요구 역량 매핑
  <section class="section s4">: 채용공고 요구 역량과 내 경험을 1:1 매핑 카드로.
  형식: [요구역량] → [나의 경험 근거]

SECTION 5 — {tmpl['s5_title']}
  <section class="section s5">: 대표적인 문제→해결→결과 사례 2~3개.
  {tmpl['s4_metric']} 포함.
"""


def build_prompt_second_call(mat_json: str, interview_txt: str, retro_txt: str,
                              has_jd: bool, job_title: str = "", job_posting: str = "") -> str:
    jd_block = ""
    if has_jd:
        jd_block = f"[채용공고] 지원직무: {job_title}\n{job_posting[:1500]}"

    if has_jd:
        sections = f"""
SECTION 6 — 회고 & 성장 스토리
  <section class="section s6">: 프로젝트별 회고를 자연스러운 문장으로.
  1) 핵심 인사이트  2) 파악된 업무 스타일  3) 다음 프로젝트 적용 계획.

SECTION 7 — 핵심 성과 지표 요약
  <section class="section s7">: <table> 태그로 5~8행 구성.
  컬럼: 항목 | 수치 | 직무 연계 포인트.

SECTION 8 — 미보유 역량 & 학습 계획
  <section class="section s8">: 채용공고 기준 미보유 역량 2~3개와 구체적 보완 방법.
"""
    else:
        sections = """
SECTION 4 — 회고 & 성장 스토리
  <section class="section s4">: 프로젝트별 회고를 자연스러운 문장으로.
  1) 핵심 인사이트  2) 파악된 업무 스타일  3) 다음 프로젝트 적용 계획.
"""

    return f"""아래 내용을 바탕으로 추가 섹션만 HTML로 생성하세요.
순수 HTML만 반환, 코드블록 금지.

[지원자 정보]
{mat_json}
인터뷰 답변: {interview_txt or "(없음)"}
회고: {retro_txt or "(없음)"}
{jd_block}

{COMMON_RULES}

아래 섹션만 생성하세요 (다른 내용 절대 추가 금지):
{sections}
"""


# ── Pydantic models ───────────────────────────────────────────────────────────

class UrlReq(BaseModel):
    url: str

class TextReq(BaseModel):
    text: str

class InterviewStartReq(BaseModel):
    session_id: str

class InterviewAnswerReq(BaseModel):
    session_id: str
    answer: str

class RetroReq(BaseModel):
    session_id: str
    retro_type: str
    retro_data: list

class GenerateReq(BaseModel):
    session_id: str
    portfolio_type: str       # developer | planner | designer | marketer
    job_title: str = ""
    job_posting: str = ""


# ── Static files ──────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/image", StaticFiles(directory="image"), name="image")

@app.get("/")
def root():
    return FileResponse("static/landing.html")

@app.get("/app")
def app_page():
    return FileResponse("static/index.html")

@app.get("/docs")
def docs_page():
    return FileResponse("static/docs.html")

@app.get("/qna")
def qna_page():
    return FileResponse("static/qna.html")


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


@app.post("/upload/text")
def upload_text(req: TextReq):
    if not req.text.strip():
        raise HTTPException(400, "텍스트를 입력해주세요.")
    sid = str(uuid.uuid4())
    parsed = parse_materials(req.text, "직접 입력")
    sessions[sid] = {
        "materials": [{"source": "직접 입력", "raw": req.text[:5000], "parsed": parsed}],
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
        "data": req.retro_data,
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

@app.post("/generate")
def generate(req: GenerateReq):
    if req.session_id not in sessions:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    sess = sessions[req.session_id]

    mat_json = json.dumps([m["parsed"] for m in sess["materials"]], ensure_ascii=False)

    interview_txt = ""
    for i, (q, a) in enumerate(zip(sess.get("questions", []), sess.get("answers", [])), 1):
        interview_txt += f"Q{i}. {q}\nA. {a}\n\n"

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
    has_jd = bool(req.job_title and req.job_posting and req.job_posting.strip())

    # ── 1차 호출: 핵심 섹션 ──────────────────────────────────────────────────
    if has_jd:
        prompt1 = build_prompt_track_b(
            mat_json, interview_txt, tmpl, req.job_title, req.job_posting
        )
    else:
        prompt1 = build_prompt_track_a(mat_json, interview_txt, tmpl)

    c = client()

    # 1차 호출: 핵심 섹션 (최대 8192토큰, 잘리면 자동 이어쓰기)
    html1 = call_claude(c, prompt1)

    # 2차 호출: 회고·지표·학습계획 섹션 (최대 8192토큰, 잘리면 자동 이어쓰기)
    prompt2 = build_prompt_second_call(
        mat_json, interview_txt, retro_txt,
        has_jd, req.job_title, req.job_posting,
    )
    html2 = call_claude(c, prompt2)

    # ── 결합 ────────────────────────────────────────────────────────────────
    combined = html1 + "\n" + html2
    if '<div class="portfolio-content">' not in combined:
        combined = f'<div class="portfolio-content">{combined}</div>'

    return {
        "portfolio_html": combined,
        "job_title": req.job_title,
        "portfolio_type": req.portfolio_type,
        "track": "B" if has_jd else "A",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

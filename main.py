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
    except Exception as e:
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
    retro_data: dict

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
    sessions[req.session_id]["retro"] = {"type": req.retro_type, "data": req.retro_data}
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
                "질문 주제: 1) 가장 어려운 기술적/업무적 문제와 해결법  "
                "2) 구체적 성과 수치 또는 임팩트  3) 팀 내 핵심 기여와 역할"
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
    "developer": "개발자 포트폴리오: 기술스택 요약 / 주요 프로젝트(역할·기술·성과) / 기술적 문제해결 경험 / 정량적 성과(성능개선·코드품질)",
    "planner": "기획자 포트폴리오: 서비스기획 경험 / 주요 프로젝트(기획범위·리서치방법·지표) / UX 개선 사례 / 비즈니스 임팩트(MAU·전환율·매출)",
    "designer": "디자이너 포트폴리오: 디자인 철학·역량 / 주요 프로젝트(범위·사용툴·결과물) / UX 개선 사례 / 시각적 성과·브랜드 임팩트",
    "marketer": "마케터 포트폴리오: 채널 경험 요약 / 주요 캠페인(채널·타겟·성과지표) / 데이터 기반 전략 / ROI·ROAS·CAC 핵심 지표 성과",
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

    retro_txt = ""
    if sess.get("retro"):
        r = sess["retro"]
        retro_txt = f"회고 유형: {r.get('type', '')}\n"
        for k, v in (r.get("data") or {}).items():
            if v:
                retro_txt += f"  {k}: {v}\n"

    tmpl = TEMPLATES.get(req.portfolio_type, TEMPLATES["developer"])

    prompt = f"""당신은 채용 전문가 겸 포트폴리오 작성 전문가입니다.

[지원자 정보]
파싱된 포트폴리오:
{mat_json}

인터뷰 답변:
{interview_txt or "(없음)"}

회고:
{retro_txt or "(없음)"}

[채용 정보]
지원 직무: {req.job_title}
채용공고:
{req.job_posting[:3500]}

[출력 형식]
{tmpl}

[작성 지침]
1. 채용공고의 요구사항과 핵심 키워드에 맞게 경험을 재해석하세요.
2. 채용공고에서 언급된 키워드는 반드시 <strong class="kw">키워드</strong>로 강조하세요.
3. 구체적인 수치와 성과를 포함하세요.
4. {req.job_title} 직무에 적합한 강점을 부각하세요.
5. 각 섹션은 <section class="section">으로, 섹션 제목은 <h2 class="section-title">으로,
   항목 카드는 <div class="item">으로 작성하세요.
6. 기술 태그는 <span class="tech-tag">태그명</span>을 사용하세요.
7. 마크다운·코드블록 없이 순수 HTML 콘텐츠만 반환하세요 (html/head/body 태그 없이).
8. 전체를 <div class="portfolio-content"> ... </div>로 감싸세요."""

    c = client()
    msg = c.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    html = msg.content[0].text.strip()

    # Strip code fences if any
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

import os
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import init_database, get_db, SessionLocal
from .schemas import AIUseCreate
from .service import create_ai_use, run_rules_check, get_ai_card
from .seed import seed_reference_data
from .models import GuidedQuestion, AIUseCase

app = FastAPI(title="AI Governance Center API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:8080"), "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_database()
    db = SessionLocal()
    try:
        seed_reference_data(db)
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/questions")
def questions(db: Session = Depends(get_db)):
    rows = db.query(GuidedQuestion).order_by(GuidedQuestion.sequence).all()
    return [{"code": q.question_code, "section": q.section_code, "text": q.plain_language_text,
             "why_we_ask": q.why_we_ask, "answer_type": q.answer_type, "fact_path": q.canonical_fact_path} for q in rows]

@app.get("/api/ai-uses")
def list_ai_uses(db: Session = Depends(get_db)):
    rows = db.query(AIUseCase).all()
    return [{"id": x.id, "name": x.name, "purpose": x.business_purpose, "status": x.lifecycle_status} for x in rows]

@app.post("/api/ai-uses")
def add_ai_use(payload: AIUseCreate, db: Session = Depends(get_db)):
    try:
        return create_ai_use(db, payload)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/api/governance-cases/{case_id}/rules-check")
def rules_check(case_id: str, db: Session = Depends(get_db)):
    try:
        return run_rules_check(db, case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@app.get("/api/ai-uses/{ai_use_id}/card")
def ai_card(ai_use_id: str, db: Session = Depends(get_db)):
    try:
        return get_ai_card(db, ai_use_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

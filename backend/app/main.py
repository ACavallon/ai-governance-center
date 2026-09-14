import os
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import init_database, get_db, SessionLocal
from .schemas import (
    AIUseCreate, GroupCreate, PersonCreate, QualificationCreate,
    RiskReviewInitialize, RiskUpdate, ControlImplementationUpdate, EvidenceCreate,
    ApprovalDecisionCreate, ObservationCreate, ChangeEventCreate, IncidentCreate,
)
from .service import (
    create_ai_use, run_rules_check, get_ai_card, ensure_demo_org,
    initialize_risk_review, get_phase_c_summary, update_risk_evaluation,
    update_control_implementation, add_control_evidence, get_approval_summary,
    create_approval_decision, get_monitoring_summary, add_monitoring_observation,
    create_change_event, create_incident,
)
from .seed import seed_reference_data
from .models import (
    GuidedQuestion, AIUseCase, Country, Person, Group, PersonQualification, BusinessUnit
)

app = FastAPI(title="AI Governance Center API", version="0.0.5")
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
    return {"status": "ok", "version": "0.0.5"}


@app.get("/api/reference/countries")
def countries(eu_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Country).filter(Country.status == "ACTIVE")
    if eu_only:
        query = query.filter(Country.eu_member.is_(True))
    rows = query.order_by(Country.name).all()
    return [{"code": c.code, "name": c.name, "eu_member": c.eu_member, "eea_member": c.eea_member} for c in rows]


@app.get("/api/business-units")
def business_units(db: Session = Depends(get_db)):
    _, _, default_bu = ensure_demo_org(db)
    rows = db.query(BusinessUnit).filter(BusinessUnit.organisation_id == default_bu.organisation_id, BusinessUnit.status == "ACTIVE").order_by(BusinessUnit.name).all()
    return [{"id": b.id, "name": b.name, "description": b.description, "owner_person_id": b.owner_person_id} for b in rows]


@app.get("/api/people")
def people(active_only: bool = True, db: Session = Depends(get_db)):
    org_entity, _, _ = ensure_demo_org(db)
    query = db.query(Person).filter(Person.organisation_id == org_entity.id)
    if active_only:
        query = query.filter(Person.status == "ACTIVE")
    rows = query.order_by(Person.display_name).all()
    return [{
        "id": p.id,
        "display_name": p.display_name,
        "first_name": p.first_name,
        "last_name": p.last_name,
        "email": p.email,
        "employee_id": p.employee_id,
        "job_title": p.job_title,
        "employment_type": p.employment_type,
        "business_unit_id": p.business_unit_id,
        "manager_person_id": p.manager_person_id,
        "country_code": p.country_code,
        "authority_level": p.authority_level,
        "status": p.status,
        "qualifications": [
            {"type": q.qualification_type, "status": q.status, "issued_at": q.issued_at, "valid_until": q.valid_until}
            for q in db.query(PersonQualification).filter(PersonQualification.person_id == p.id).all()
        ],
    } for p in rows]


@app.post("/api/people")
def add_person(payload: PersonCreate, db: Session = Depends(get_db)):
    try:
        org_entity, _, default_bu = ensure_demo_org(db)
        if payload.country_code and not db.get(Country, payload.country_code):
            raise ValueError("Country must be selected from the country directory")
        if payload.business_unit_id and not db.get(BusinessUnit, payload.business_unit_id):
            raise ValueError("Unknown business unit")
        if payload.manager_person_id and not db.get(Person, payload.manager_person_id):
            raise ValueError("Unknown manager")
        if payload.email and db.query(Person).filter_by(organisation_id=org_entity.id, email=payload.email).first():
            raise ValueError("A person with this email already exists")
        person = Person(
            organisation_id=org_entity.id,
            business_unit_id=payload.business_unit_id or default_bu.id,
            manager_person_id=payload.manager_person_id,
            employee_id=payload.employee_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            display_name=f"{payload.first_name} {payload.last_name}".strip(),
            email=payload.email,
            job_title=payload.job_title,
            employment_type=payload.employment_type,
            country_code=payload.country_code,
            authority_level=payload.authority_level,
        )
        db.add(person); db.commit(); db.refresh(person)
        return {"id": person.id, "display_name": person.display_name, "email": person.email, "job_title": person.job_title, "country_code": person.country_code, "status": person.status}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/people/{person_id}/qualifications")
def add_qualification(person_id: str, payload: QualificationCreate, db: Session = Depends(get_db)):
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    qualification = PersonQualification(person_id=person_id, qualification_type=payload.qualification_type, status=payload.status,
                                        issued_at=payload.issued_at, valid_until=payload.valid_until,
                                        evidence_reference=payload.evidence_reference)
    db.add(qualification); db.commit(); db.refresh(qualification)
    return {"id": qualification.id, "type": qualification.qualification_type, "status": qualification.status, "valid_until": qualification.valid_until}


@app.get("/api/groups")
def groups(db: Session = Depends(get_db)):
    org_entity, _, _ = ensure_demo_org(db)
    rows = db.query(Group).filter(Group.organisation_id == org_entity.id, Group.status == "ACTIVE").order_by(Group.name).all()
    return [{"id": g.id, "name": g.name, "group_type": g.group_type, "owner_person_id": g.owner_person_id, "description": g.description} for g in rows]


@app.post("/api/groups")
def add_group(payload: GroupCreate, db: Session = Depends(get_db)):
    try:
        org_entity, _, _ = ensure_demo_org(db)
        if payload.owner_person_id and not db.get(Person, payload.owner_person_id):
            raise ValueError("Unknown group owner")
        group = Group(organisation_id=org_entity.id, group_type=payload.group_type, name=payload.name,
                      owner_person_id=payload.owner_person_id, description=payload.description)
        db.add(group); db.commit(); db.refresh(group)
        return {"id": group.id, "name": group.name, "group_type": group.group_type}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


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


@app.get("/api/governance-cases/{case_id}/phase-c")
def phase_c_summary(case_id: str, db: Session = Depends(get_db)):
    try:
        return get_phase_c_summary(db, case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/governance-cases/{case_id}/risk-review/initialize")
def start_risk_review(case_id: str, payload: RiskReviewInitialize, db: Session = Depends(get_db)):
    try:
        return initialize_risk_review(db, case_id, payload.owner_person_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/risks/{risk_id}/evaluation")
def review_risk(risk_id: str, payload: RiskUpdate, db: Session = Depends(get_db)):
    try:
        return update_risk_evaluation(db, risk_id, payload.result, payload.uncertainty, payload.rationale)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.patch("/api/control-implementations/{implementation_id}")
def update_safeguard(implementation_id: str, payload: ControlImplementationUpdate, db: Session = Depends(get_db)):
    try:
        return update_control_implementation(db, implementation_id, payload.status, payload.owner_person_id, payload.implementation_description)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/control-implementations/{implementation_id}/evidence")
def add_evidence(implementation_id: str, payload: EvidenceCreate, db: Session = Depends(get_db)):
    try:
        return add_control_evidence(db, implementation_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@app.get("/api/governance-cases/{case_id}/approval")
def approval_summary(case_id: str, db: Session = Depends(get_db)):
    try:
        return get_approval_summary(db, case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/governance-cases/{case_id}/approval")
def decide_approval(case_id: str, payload: ApprovalDecisionCreate, db: Session = Depends(get_db)):
    try:
        return create_approval_decision(db, case_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/governance-cases/{case_id}/monitoring")
def monitoring_summary(case_id: str, db: Session = Depends(get_db)):
    try:
        return get_monitoring_summary(db, case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/monitoring-definitions/{definition_id}/observations")
def record_observation(definition_id: str, payload: ObservationCreate, db: Session = Depends(get_db)):
    try:
        return add_monitoring_observation(db, definition_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/governance-cases/{case_id}/changes")
def report_change(case_id: str, payload: ChangeEventCreate, db: Session = Depends(get_db)):
    try:
        return create_change_event(db, case_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/governance-cases/{case_id}/incidents")
def report_incident(case_id: str, payload: IncidentCreate, db: Session = Depends(get_db)):
    try:
        return create_incident(db, case_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

# --- v0.0.5 guide, organisation governance, RACI and learning ---
from datetime import date as _date
from .models import (
    GuideContent, GovernanceResponsibility, GovernanceRole, RoleResponsibility,
    GovernanceRoleAssignment, Course, RoleTrainingRequirement, CourseCompletion,
    LearningAssignment,
)


def _person_training_readiness(db: Session, person_id: str) -> dict:
    assignments = db.query(GovernanceRoleAssignment).filter_by(person_id=person_id, status="ACTIVE").all()
    role_ids = [a.role_id for a in assignments]
    reqs = db.query(RoleTrainingRequirement).filter(RoleTrainingRequirement.role_id.in_(role_ids)).all() if role_ids else []
    mandatory = {(r.role_id, r.course_id): r for r in reqs if r.requirement_level == "MANDATORY"}
    course_ids = list({r.course_id for r in reqs})
    completions = db.query(CourseCompletion).filter(CourseCompletion.person_id == person_id, CourseCompletion.course_id.in_(course_ids)).all() if course_ids else []
    current = set()
    today = _date.today()
    for c in completions:
        if c.status == "CURRENT" and (c.valid_until is None or c.valid_until >= today):
            current.add(c.course_id)
    missing = []
    for (_, course_id), req in mandatory.items():
        if course_id not in current:
            course = db.get(Course, course_id)
            role = db.get(GovernanceRole, req.role_id)
            missing.append({"course_id": course_id, "course": course.title if course else course_id, "role": role.name if role else req.role_id})
    return {"ready": len(missing) == 0, "mandatory_required": len(mandatory), "missing_mandatory": missing}


@app.get("/api/guide")
def guide(section: str | None = None, db: Session = Depends(get_db)):
    query = db.query(GuideContent).filter(GuideContent.status == "ACTIVE")
    if section:
        query = query.filter(GuideContent.section == section.upper())
    rows = query.order_by(GuideContent.sequence).all()
    return [{
        "code": x.code, "section": x.section, "journey_stage": x.journey_stage, "title": x.title,
        "summary": x.summary, "why_it_matters": x.why_it_matters, "expected_input": x.expected_input,
        "responsible_role": x.responsible_role, "next_step": x.next_step, "source_reference": x.source_reference,
        "version": x.version,
    } for x in rows]


@app.get("/api/governance/responsibilities")
def governance_responsibilities(db: Session = Depends(get_db)):
    rows = db.query(GovernanceResponsibility).filter_by(status="ACTIVE").order_by(GovernanceResponsibility.lifecycle_stage, GovernanceResponsibility.name).all()
    return [{"id": x.id, "code": x.code, "name": x.name, "description": x.description, "lifecycle_stage": x.lifecycle_stage, "source_reference": x.source_reference} for x in rows]


@app.get("/api/governance/roles")
def governance_roles(db: Session = Depends(get_db)):
    roles = db.query(GovernanceRole).filter_by(status="ACTIVE").order_by(GovernanceRole.name).all()
    result = []
    for role in roles:
        mappings = db.query(RoleResponsibility).filter_by(role_id=role.id).all()
        training = db.query(RoleTrainingRequirement).filter_by(role_id=role.id).all()
        result.append({
            "id": role.id, "code": role.code, "name": role.name, "description": role.description, "scope_type": role.scope_type,
            "responsibilities": [{
                "responsibility_id": m.responsibility_id,
                "responsibility": db.get(GovernanceResponsibility, m.responsibility_id).name,
                "raci": m.raci_type,
                "stage": db.get(GovernanceResponsibility, m.responsibility_id).lifecycle_stage,
            } for m in mappings],
            "training_requirements": [{
                "course_id": t.course_id, "course": db.get(Course, t.course_id).title,
                "requirement_level": t.requirement_level, "rationale": t.rationale,
            } for t in training],
        })
    return result


@app.get("/api/learning/courses")
def learning_courses(db: Session = Depends(get_db)):
    rows = db.query(Course).filter_by(status="ACTIVE").order_by(Course.title).all()
    return [{"id": c.id, "code": c.code, "title": c.title, "description": c.description, "provider": c.provider, "validity_months": c.validity_months} for c in rows]


@app.get("/api/learning/dashboard")
def learning_dashboard(db: Session = Depends(get_db)):
    people = db.query(Person).filter_by(status="ACTIVE").all()
    roles = db.query(GovernanceRole).filter_by(status="ACTIVE").all()
    person_rows = []
    for p in people:
        assignments = db.query(GovernanceRoleAssignment).filter_by(person_id=p.id, status="ACTIVE").all()
        role_names = [db.get(GovernanceRole, a.role_id).name for a in assignments if db.get(GovernanceRole, a.role_id)]
        readiness = _person_training_readiness(db, p.id)
        person_rows.append({"person_id": p.id, "name": p.display_name, "roles": role_names, "training": readiness})
    course_rows=[]
    for c in db.query(Course).filter_by(status="ACTIVE").all():
        required_people=set()
        for rr in db.query(RoleTrainingRequirement).filter_by(course_id=c.id).all():
            for a in db.query(GovernanceRoleAssignment).filter_by(role_id=rr.role_id, status="ACTIVE").all():
                if a.person_id: required_people.add(a.person_id)
        current=0
        for pid in required_people:
            comp=db.query(CourseCompletion).filter_by(person_id=pid, course_id=c.id, status="CURRENT").order_by(CourseCompletion.completed_at.desc()).first()
            if comp and (comp.valid_until is None or comp.valid_until >= _date.today()): current+=1
        course_rows.append({"course_id":c.id,"course":c.title,"assigned":len(required_people),"current":current,"coverage":round((current/len(required_people))*100) if required_people else None})
    return {"people": person_rows, "courses": course_rows, "roles": len(roles), "people_ready": sum(1 for p in person_rows if p["training"]["ready"]), "people_with_gaps": sum(1 for p in person_rows if not p["training"]["ready"])}

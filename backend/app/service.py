from __future__ import annotations
from datetime import datetime
import hashlib
import json
from sqlalchemy.orm import Session

from . import models
from .schemas import AIUseCreate
from .rule_engine import evaluate_expression

EU_COUNTRIES = {"AT","BE","BG","HR","CY","CZ","DK","EE","FI","FR","DE","GR","HU","IE","IT","LV","LT","LU","MT","NL","PL","PT","RO","SK","SI","ES","SE"}


def new_governed(db: Session, object_type: str) -> str:
    obj = models.GovernedObject(object_type=object_type)
    db.add(obj); db.flush(); return obj.id


def ensure_demo_org(db: Session):
    entity = db.query(models.LegalEntity).filter_by(legal_name="Demo Company EU").first()
    if entity:
        org = db.get(models.Organisation, entity.id)
        bu = db.query(models.BusinessUnit).filter_by(organisation_id=entity.id, name="Human Resources").first()
        return entity, org, bu
    entity = models.LegalEntity(legal_name="Demo Company EU", display_name="Demo Company", entity_type="OUR_ORGANISATION", country_code="FR")
    db.add(entity); db.flush()
    org = models.Organisation(legal_entity_id=entity.id)
    db.add(org); db.flush()
    bu = models.BusinessUnit(organisation_id=entity.id, name="Human Resources")
    db.add(bu); db.flush()
    db.commit()
    return entity, org, bu


def create_ai_use(db: Session, payload: AIUseCreate) -> dict:
    org_entity, _, bu = ensure_demo_org(db)
    owner = db.get(models.Person, payload.owner_person_id)
    if not owner or owner.status != "ACTIVE" or owner.organisation_id != org_entity.id:
        raise ValueError("Business owner must be an active person in the organisation directory")

    valid_country_codes = {c.code for c in db.query(models.Country).filter(models.Country.code.in_(payload.countries)).all()}
    invalid_countries = sorted(set(payload.countries) - valid_country_codes)
    if invalid_countries:
        raise ValueError(f"Unknown country code(s): {', '.join(invalid_countries)}")

    supplier_id = None
    if payload.supply_model == "third_party" and payload.supplier_name:
        supplier = db.query(models.LegalEntity).filter_by(legal_name=payload.supplier_name).first()
        if not supplier:
            supplier = models.LegalEntity(legal_name=payload.supplier_name, display_name=payload.supplier_name, entity_type="VENDOR")
            db.add(supplier); db.flush()
        supplier_id = supplier.id

    uc_id = new_governed(db, "AI_USE_CASE")
    use_case = models.AIUseCase(id=uc_id, business_unit_id=bu.id, name=payload.name, business_purpose=payload.business_purpose,
                               business_process=payload.business_process, business_owner_id=owner.id)
    db.add(use_case)

    sys_id = new_governed(db, "AI_SYSTEM")
    system = models.AISystem(id=sys_id, name=payload.system_name, intended_purpose=payload.system_purpose,
                             development_type=payload.supply_model.upper(), supplier_entity_id=supplier_id)
    db.add(system); db.flush()
    db.add(models.UseCaseSystem(use_case_id=uc_id, system_id=sys_id))

    dep_id = new_governed(db, "DEPLOYMENT_CONTEXT")
    deployment = models.DeploymentContext(id=dep_id, system_id=sys_id, use_case_id=uc_id, name=f"{payload.name} deployment",
                                           intended_purpose=payload.business_purpose,
                                           degree_of_automation="HUMAN_FINAL_DECISION" if payload.human_final_decision else "AUTOMATED")
    db.add(deployment); db.flush()
    for c in payload.countries:
        db.add(models.DeploymentGeography(deployment_context_id=dep_id, country_code=c.upper()))
    db.add(models.AffectedPopulation(deployment_context_id=dep_id, population_type=payload.affected_population.upper()))
    db.add(models.DecisionInvolvement(deployment_context_id=dep_id, decision_domain=payload.decision_domain.upper(),
                                      ai_role=payload.function.upper(), human_role="Final decision" if payload.human_final_decision else "Limited/no final review"))

    case = models.GovernanceCase(deployment_context_id=dep_id)
    db.add(case); db.flush()

    facts = {
        "system": {"supply_model": payload.supply_model},
        "deployment": {
            "countries": [c.upper() for c in payload.countries],
            "decision_domain": payload.decision_domain.upper(),
            "function": payload.function.lower(),
            "affected_population": payload.affected_population.upper(),
            "human_final_decision": payload.human_final_decision,
        },
    }
    for field, value in [
        ("business_purpose", payload.business_purpose), ("business_owner_id", payload.owner_person_id),
        ("system_name", payload.system_name), ("decision_domain", payload.decision_domain),
        ("function", payload.function), ("countries", payload.countries)
    ]:
        db.add(models.FactProvenance(entity_type="DEPLOYMENT_CONTEXT", entity_id=dep_id, field_name=field,
                                     source_type="USER_INPUT", source_reference="guided_onboarding"))
    db.commit()
    return {"ai_use_id": uc_id, "deployment_id": dep_id, "case_id": case.id, "facts": facts}


def build_facts(db: Session, case: models.GovernanceCase) -> dict:
    dep = db.get(models.DeploymentContext, case.deployment_context_id)
    sys = db.get(models.AISystem, dep.system_id)
    di = db.get(models.DecisionInvolvement, dep.id)
    countries = [r.country_code for r in db.query(models.DeploymentGeography).filter_by(deployment_context_id=dep.id).all()]
    pop = db.query(models.AffectedPopulation).filter_by(deployment_context_id=dep.id).first()
    supply_model = sys.development_type.lower()
    if supply_model == "third_party": supply_model = "third_party"
    return {
        "system": {"supply_model": supply_model},
        "deployment": {
            "countries": countries,
            "decision_domain": di.decision_domain if di else None,
            "function": (di.ai_role.lower() if di else None),
            "affected_population": pop.population_type if pop else None,
            "human_final_decision": bool(di and di.human_role == "Final decision"),
        },
    }


def run_rules_check(db: Session, case_id: str) -> dict:
    case = db.get(models.GovernanceCase, case_id)
    if not case:
        raise KeyError("Governance case not found")
    facts = build_facts(db, case)
    profile = []
    high_risk_triggered = False
    likely_deployer = False

    versions = db.query(models.RuleVersion).join(models.Rule).filter(models.RuleVersion.status == "ACTIVE", models.Rule.status == "ACTIVE").all()
    for rv in versions:
        result = evaluate_expression(rv.expression, facts)
        output_key = "when_unknown" if result is None else ("when_true" if result else "when_false")
        outcome = rv.output[output_key]
        evaluation = models.RuleEvaluation(rule_version_id=rv.id, governance_case_id=case.id, subject_id=case.deployment_context_id,
                                           input_snapshot=facts, result={"matched": result, "outcome": outcome, "dimension": rv.output["dimension"]},
                                           explanation=rv.explanation_template)
        db.add(evaluation); db.flush()
        confidence = "LOW" if result is None else rv.output.get("confidence", "MEDIUM")
        db.add(models.ClassificationAssessment(governance_case_id=case.id, subject_id=case.deployment_context_id,
                                               dimension=rv.output["dimension"], outcome=outcome,
                                               source_rule_evaluation_id=evaluation.id,
                                               reasoning=rv.explanation_template, confidence=confidence))
        profile.append({
            "dimension": rv.output["dimension"], "outcome": outcome, "confidence": confidence,
            "explanation": rv.explanation_template, "source": rv.source_reference,
            "rule_version": rv.version,
        })
        if rv.output["dimension"] == "HIGH_RISK" and result is True:
            high_risk_triggered = True
        if rv.output["dimension"] == "ACTOR_ROLE" and outcome == "DEPLOYER":
            likely_deployer = True

    actions = []
    reqs = {r.requirement_code: r for r in db.query(models.Requirement).all()}
    if high_risk_triggered:
        for code in ("AIA-RISK-001", "AIA-HO-001"):
            req = reqs[code]
            obl = models.Obligation(governance_case_id=case.id, requirement_id=req.id, subject_id=case.deployment_context_id)
            db.add(obl); db.flush()
            if code == "AIA-RISK-001":
                title, desc, priority = "Complete AI risk & impact review", "Identify material risks, affected people and required treatments before approval.", "HIGH"
            else:
                title, desc, priority = "Set up human oversight", "Assign people with sufficient competence and authority to review and intervene in the AI-supported process.", "HIGH"
            action = models.GovernanceAction(governance_case_id=case.id, action_type="REQUIRED_GOVERNANCE", title=title, description=desc, priority=priority)
            db.add(action); db.flush(); db.add(models.ActionObligation(action_id=action.id, obligation_id=obl.id))
            actions.append({"id": action.id, "title": title, "description": desc, "priority": priority, "source": f"EU AI Act — {req.source_reference}"})

    if likely_deployer:
        actions.append({"id":"generated-supplier", "title":"Collect supplier information", "description":"Confirm provider instructions, system limitations and information needed for safe and compliant deployment.", "priority":"MEDIUM", "source":"EU AI Act deployer governance"})
    actions.append({"id":"generated-monitor", "title":"Prepare monitoring approach", "description":"Define what needs to be watched once the AI is approved and active.", "priority":"MEDIUM", "source":"Lifecycle governance / ISO 42001-aligned management"})

    case.governance_state = "CLASSIFIED"
    db.commit()
    return {"case_id": case.id, "ai_use_id": db.get(models.DeploymentContext, case.deployment_context_id).use_case_id,
            "regulatory_profile": profile, "actions": actions}


def get_ai_card(db: Session, ai_use_id: str) -> dict:
    use_case = db.get(models.AIUseCase, ai_use_id)
    if not use_case:
        raise KeyError("AI use not found")
    link = db.query(models.UseCaseSystem).filter_by(use_case_id=ai_use_id).first()
    system = db.get(models.AISystem, link.system_id)
    dep = db.query(models.DeploymentContext).filter_by(use_case_id=ai_use_id, system_id=system.id).first()
    case = db.query(models.GovernanceCase).filter_by(deployment_context_id=dep.id).order_by(models.GovernanceCase.opened_at.desc()).first()
    owner = db.get(models.Person, use_case.business_owner_id)
    geos = [r.country_code for r in db.query(models.DeploymentGeography).filter_by(deployment_context_id=dep.id).all()]
    pop = db.query(models.AffectedPopulation).filter_by(deployment_context_id=dep.id).first()
    di = db.get(models.DecisionInvolvement, dep.id)
    classifications = db.query(models.ClassificationAssessment).filter_by(governance_case_id=case.id).all()
    actions = db.query(models.GovernanceAction).filter_by(governance_case_id=case.id).all()
    return {
        "id": ai_use_id,
        "name": use_case.name,
        "purpose": use_case.business_purpose,
        "owner": owner.display_name,
        "system": {"name": system.name, "development_type": system.development_type},
        "context": {"countries": geos, "affected_population": pop.population_type if pop else None,
                    "decision_domain": di.decision_domain if di else None, "ai_role": di.ai_role if di else None,
                    "human_final_decision": bool(di and di.human_role == "Final decision")},
        "governance": {"case_id": case.id, "stage": case.governance_state,
                       "needs_attention": len([a for a in actions if a.status == "OPEN"])},
        "classifications": [{"dimension": c.dimension, "outcome": c.outcome, "confidence": c.confidence} for c in classifications],
        "actions": [{"id": a.id, "title": a.title, "description": a.description, "priority": a.priority, "status": a.status} for a in actions],
    }


def initialize_risk_review(db: Session, case_id: str, owner_person_id: str | None = None) -> dict:
    case = db.get(models.GovernanceCase, case_id)
    if not case:
        raise KeyError("Governance case not found")
    dep = db.get(models.DeploymentContext, case.deployment_context_id)
    owner = db.get(models.Person, owner_person_id) if owner_person_id else None
    if owner_person_id and not owner:
        raise ValueError("Unknown risk-review owner")

    template = db.query(models.AssessmentTemplate).filter_by(template_code="AI_RISK_GENERAL", status="ACTIVE").first()
    if not template:
        raise ValueError("Risk assessment template is not configured")
    assessment = db.query(models.Assessment).filter_by(governance_case_id=case.id, template_id=template.id, subject_id=dep.id).first()
    if not assessment:
        assessment = models.Assessment(governance_case_id=case.id, template_id=template.id, subject_id=dep.id,
                                       owner_person_id=owner_person_id, status="IN_PROGRESS")
        db.add(assessment); db.flush()

    existing = db.query(models.Risk).filter_by(governed_object_id=dep.id, assessment_id=assessment.id).all()
    if not existing:
        pop = db.query(models.AffectedPopulation).filter_by(deployment_context_id=dep.id).first()
        di = db.get(models.DecisionInvolvement, dep.id)
        domain = (di.decision_domain or "").upper() if di else ""
        patterns = [
            ("INCORRECT_OUTCOME", "Suitable people may receive an incorrect outcome",
             "The AI may make an inaccurate ranking or recommendation.",
             "AI output is materially incorrect", "A person may lose an opportunity or receive an adverse outcome", "HIGH", "DECISION_QUALITY", "MAJOR"),
            ("OVER_RELIANCE", "People may rely too heavily on the AI recommendation",
             "Users may treat the AI output as authoritative rather than critically reviewing it.",
             "Human reviewer rubber-stamps the recommendation", "Human oversight may become ineffective", "MEDIUM", "HUMAN_OVERSIGHT", "MAJOR"),
        ]
        if domain == "EMPLOYMENT":
            patterns.insert(1, ("GROUP_DISPARITY", "Performance may differ across applicant groups",
                "Data or model behaviour may produce systematically different outcomes for groups of applicants.",
                "Ranking quality differs materially across groups", "Applicants may be treated unfairly or lose employment opportunities", "HIGH", "FAIRNESS", "MAJOR"))
        for idx, (suffix, title, cause, event, consequence, rating, impact_type, magnitude) in enumerate(patterns, start=1):
            risk = models.Risk(governed_object_id=dep.id, assessment_id=assessment.id,
                               risk_code=f"{case.id[:8]}-{suffix}", title=title, description=f"Suggested risk pattern for {dep.name}.",
                               cause=cause, risk_event=event, potential_consequence=consequence,
                               risk_owner_id=owner_person_id, status="OPEN")
            db.add(risk); db.flush()
            db.add(models.RiskEvaluation(risk_id=risk.id, assessment_id=assessment.id, evaluation_stage="INHERENT",
                                         methodology_code="QUALITATIVE_V1",
                                         criteria_snapshot={"likelihood":"POSSIBLE", "severity":magnitude}, result=rating,
                                         uncertainty="MEDIUM", rationale="Initial contextual assessment; requires owner review."))
            db.add(models.Impact(risk_id=risk.id, affected_population_id=pop.id if pop else None,
                                 impact_type=impact_type, description=consequence, polarity="NEGATIVE",
                                 magnitude=magnitude, reversibility="PARTIALLY_REVERSIBLE"))
    db.flush()

    controls = db.query(models.Control).filter(models.Control.status == "ACTIVE").all()
    risks = db.query(models.Risk).filter_by(governed_object_id=dep.id, assessment_id=assessment.id).all()
    risk_by_suffix = {r.risk_code.split("-", 1)[-1]: r for r in risks}
    mappings = {
        "CTRL-HO-001": ["OVER_RELIANCE", "INCORRECT_OUTCOME"],
        "CTRL-FAIR-001": ["GROUP_DISPARITY"],
        "CTRL-TRN-001": ["OVER_RELIANCE"],
        "CTRL-MON-001": ["INCORRECT_OUTCOME", "GROUP_DISPARITY"],
    }
    for control in controls:
        impl = db.query(models.ControlImplementation).filter_by(control_id=control.id, governed_object_id=dep.id).first()
        if not impl:
            impl = models.ControlImplementation(control_id=control.id, governed_object_id=dep.id,
                                                owner_person_id=owner_person_id,
                                                implementation_description=control.description,
                                                execution_mode=control.execution_mode,
                                                frequency=control.frequency_type, status="PLANNED")
            db.add(impl); db.flush()
        for suffix in mappings.get(control.control_code, []):
            risk = risk_by_suffix.get(suffix)
            if risk and not db.query(models.RiskControlMapping).filter_by(risk_id=risk.id, control_id=control.id).first():
                db.add(models.RiskControlMapping(risk_id=risk.id, control_id=control.id, coverage="SUPPORTING",
                                                 rationale="Suggested safeguard mapping based on the risk pattern."))

    case.governance_state = "ASSESSED"
    db.commit()
    return get_phase_c_summary(db, case_id)


def get_phase_c_summary(db: Session, case_id: str) -> dict:
    case = db.get(models.GovernanceCase, case_id)
    if not case:
        raise KeyError("Governance case not found")
    dep = db.get(models.DeploymentContext, case.deployment_context_id)
    assessments = db.query(models.Assessment).filter_by(governance_case_id=case.id).all()
    assessment_ids = [a.id for a in assessments]
    risks = db.query(models.Risk).filter(models.Risk.governed_object_id == dep.id).all()
    risk_items = []
    for r in risks:
        evaluations = db.query(models.RiskEvaluation).filter_by(risk_id=r.id).order_by(models.RiskEvaluation.evaluated_at.desc()).all()
        current_eval = evaluations[0] if evaluations else None
        impact = db.query(models.Impact).filter_by(risk_id=r.id).first()
        owner = db.get(models.Person, r.risk_owner_id) if r.risk_owner_id else None
        risk_items.append({
            "id": r.id, "code": r.risk_code, "title": r.title, "cause": r.cause,
            "event": r.risk_event, "consequence": r.potential_consequence, "status": r.status,
            "owner": owner.display_name if owner else None,
            "evaluation": {"result": current_eval.result, "uncertainty": current_eval.uncertainty, "stage": current_eval.evaluation_stage,
                           "rationale": current_eval.rationale} if current_eval else None,
            "impact": {"type": impact.impact_type, "description": impact.description, "magnitude": impact.magnitude} if impact else None,
        })
    implementations = db.query(models.ControlImplementation).filter_by(governed_object_id=dep.id).all()
    safeguards = []
    for impl in implementations:
        ctl = db.get(models.Control, impl.control_id)
        owner = db.get(models.Person, impl.owner_person_id) if impl.owner_person_id else None
        evidence_links = db.query(models.ControlEvidence).filter_by(control_implementation_id=impl.id).all()
        evidence = [db.get(models.Evidence, x.evidence_id) for x in evidence_links]
        linked_risks = db.query(models.RiskControlMapping).filter_by(control_id=ctl.id).all()
        linked_risk_ids = [x.risk_id for x in linked_risks if db.get(models.Risk, x.risk_id) and db.get(models.Risk, x.risk_id).governed_object_id == dep.id]
        safeguards.append({
            "id": impl.id, "control_code": ctl.control_code, "name": ctl.name, "description": ctl.description,
            "status": impl.status, "owner": owner.display_name if owner else None, "frequency": impl.frequency,
            "risk_ids": linked_risk_ids,
            "evidence": [{"id": e.id, "title": e.title, "type": e.evidence_type, "reference": e.artifact_reference,
                          "valid_until": e.valid_until, "status": e.status} for e in evidence if e],
        })
    implemented = len([x for x in safeguards if x["status"] in {"IMPLEMENTED", "EFFECTIVE"}])
    return {
        "case_id": case.id,
        "state": case.governance_state,
        "assessment_started": bool(assessments),
        "assessment_status": assessments[0].status if assessments else "NOT_STARTED",
        "risks": risk_items,
        "safeguards": safeguards,
        "summary": {"risk_count": len(risk_items), "high_risks": len([r for r in risk_items if (r.get("evaluation") or {}).get("result") in {"HIGH","CRITICAL"}]),
                    "safeguard_count": len(safeguards), "safeguards_ready": implemented,
                    "evidence_count": sum(len(s["evidence"]) for s in safeguards)},
    }


def update_risk_evaluation(db: Session, risk_id: str, result: str, uncertainty: str, rationale: str | None) -> dict:
    risk = db.get(models.Risk, risk_id)
    if not risk:
        raise KeyError("Risk not found")
    db.add(models.RiskEvaluation(risk_id=risk.id, assessment_id=risk.assessment_id, evaluation_stage="INHERENT",
                                 methodology_code="QUALITATIVE_V1", criteria_snapshot={"reviewed": True}, result=result,
                                 uncertainty=uncertainty, rationale=rationale or "Reviewed by governance user."))
    db.commit()
    return {"id": risk.id, "result": result, "uncertainty": uncertainty}


def update_control_implementation(db: Session, implementation_id: str, status: str, owner_person_id: str | None,
                                  description: str | None) -> dict:
    impl = db.get(models.ControlImplementation, implementation_id)
    if not impl:
        raise KeyError("Safeguard implementation not found")
    if owner_person_id and not db.get(models.Person, owner_person_id):
        raise ValueError("Unknown safeguard owner")
    impl.status = status
    if owner_person_id is not None:
        impl.owner_person_id = owner_person_id
    if description is not None:
        impl.implementation_description = description
    db.commit()
    return {"id": impl.id, "status": impl.status}


def add_control_evidence(db: Session, implementation_id: str, payload) -> dict:
    impl = db.get(models.ControlImplementation, implementation_id)
    if not impl:
        raise KeyError("Safeguard implementation not found")
    evidence = models.Evidence(title=payload.title, evidence_type=payload.evidence_type, description=payload.description,
                               artifact_reference=payload.artifact_reference, valid_until=payload.valid_until)
    db.add(evidence); db.flush()
    db.add(models.ControlEvidence(control_implementation_id=impl.id, evidence_id=evidence.id, evidence_role="SUPPORTING"))
    db.commit(); db.refresh(evidence)
    return {"id": evidence.id, "title": evidence.title, "type": evidence.evidence_type, "reference": evidence.artifact_reference,
            "valid_until": evidence.valid_until, "status": evidence.status}


def _phase_d_readiness(db: Session, case_id: str) -> dict:
    case = db.get(models.GovernanceCase, case_id)
    if not case:
        raise KeyError("Governance case not found")
    phase_c = get_phase_c_summary(db, case_id)
    blockers = []
    if not phase_c["assessment_started"]:
        blockers.append("Risk & impact review has not been started")
    if phase_c["summary"]["high_risks"] > 0:
        blockers.append("High or critical risks remain and require review")
    not_ready = [s for s in phase_c["safeguards"] if s["status"] not in {"IMPLEMENTED", "EFFECTIVE"}]
    if not_ready:
        blockers.append(f"{len(not_ready)} safeguard(s) are not implemented")
    missing_evidence = [s for s in phase_c["safeguards"] if not s["evidence"]]
    if missing_evidence:
        blockers.append(f"{len(missing_evidence)} safeguard(s) have no supporting evidence")
    return {
        "ready": not blockers,
        "blockers": blockers,
        "risk_count": phase_c["summary"]["risk_count"],
        "safeguard_count": phase_c["summary"]["safeguard_count"],
        "evidence_count": phase_c["summary"]["evidence_count"],
    }


def get_approval_summary(db: Session, case_id: str) -> dict:
    case = db.get(models.GovernanceCase, case_id)
    if not case:
        raise KeyError("Governance case not found")
    readiness = _phase_d_readiness(db, case_id)
    decision = db.query(models.Decision).filter_by(governance_case_id=case_id, decision_type="DEPLOYMENT_APPROVAL", status="CURRENT").order_by(models.Decision.decided_at.desc()).first()
    authority = db.get(models.Person, decision.decision_authority_id) if decision else None
    baseline = db.query(models.ApprovalBaseline).filter_by(decision_id=decision.id).first() if decision else None
    return {
        "case_id": case_id,
        "state": case.governance_state,
        "readiness": readiness,
        "decision": ({
            "id": decision.id,
            "outcome": decision.outcome,
            "authority": authority.display_name if authority else None,
            "decided_at": decision.decided_at,
            "rationale": decision.rationale,
            "conditions": decision.conditions or [],
            "valid_until": decision.valid_until,
        } if decision else None),
        "baseline": ({"id": baseline.id, "created_at": baseline.created_at, "content_hash": baseline.content_hash} if baseline else None),
    }


def _build_approval_snapshot(db: Session, case: models.GovernanceCase) -> dict:
    dep = db.get(models.DeploymentContext, case.deployment_context_id)
    system = db.get(models.AISystem, dep.system_id)
    phase_c = get_phase_c_summary(db, case.id)
    classifications = db.query(models.ClassificationAssessment).filter_by(governance_case_id=case.id, status="CURRENT").all()
    return {
        "system": {"id": system.id, "name": system.name, "development_type": system.development_type, "intended_purpose": system.intended_purpose},
        "deployment": {"id": dep.id, "name": dep.name, "intended_purpose": dep.intended_purpose, "lifecycle_status": dep.lifecycle_status},
        "classifications": [{"dimension": c.dimension, "outcome": c.outcome, "confidence": c.confidence} for c in classifications],
        "risks": phase_c["risks"],
        "safeguards": phase_c["safeguards"],
    }


def _ensure_monitoring_plan(db: Session, case: models.GovernanceCase, owner_person_id: str) -> models.MonitoringPlan:
    dep = db.get(models.DeploymentContext, case.deployment_context_id)
    plan = db.query(models.MonitoringPlan).filter_by(deployment_context_id=dep.id, status="ACTIVE").first()
    if plan:
        return plan
    plan = models.MonitoringPlan(
        deployment_context_id=dep.id,
        owner_person_id=owner_person_id,
        purpose="Monitor AI performance, fairness, human oversight and governance health after approval.",
        review_frequency="QUARTERLY",
    )
    db.add(plan); db.flush()
    defs = [
        ("Performance remains acceptable", "PERFORMANCE", "Review model/system outcomes against approved operating expectations.", "MONTHLY"),
        ("Fairness remains acceptable", "FAIRNESS", "Review material differences in outcomes across relevant affected groups.", "MONTHLY"),
        ("Human oversight remains effective", "HUMAN_OVERSIGHT", "Review whether humans are actively reviewing and able to intervene.", "MONTHLY"),
        ("Governance controls remain current", "CONTROL_EFFECTIVENESS", "Review safeguard status, evidence currency and open governance issues.", "MONTHLY"),
    ]
    for name, mtype, desc, freq in defs:
        d = models.MonitoringDefinition(monitoring_plan_id=plan.id, name=name, monitoring_type=mtype, description=desc, frequency=freq)
        db.add(d); db.flush()
        # Simple prototype rule: explicit numeric values below 0 are a breach; qualitative FAIL is handled separately.
        db.add(models.ThresholdRule(monitoring_definition_id=d.id, operator="gte", threshold_value="0", severity="HIGH", breach_action="REASSESS"))
    return plan


def create_approval_decision(db: Session, case_id: str, payload) -> dict:
    case = db.get(models.GovernanceCase, case_id)
    if not case:
        raise KeyError("Governance case not found")
    authority = db.get(models.Person, payload.decision_authority_id)
    if not authority:
        raise ValueError("Unknown decision authority")
    readiness = _phase_d_readiness(db, case_id)
    if payload.outcome in {"APPROVED", "APPROVED_WITH_CONDITIONS"} and not readiness["ready"]:
        raise ValueError("Approval gate is not ready: " + "; ".join(readiness["blockers"]))
    current = db.query(models.Decision).filter_by(governance_case_id=case_id, decision_type="DEPLOYMENT_APPROVAL", status="CURRENT").all()
    for old in current:
        old.status = "SUPERSEDED"
    decision = models.Decision(
        governance_case_id=case.id,
        subject_id=case.deployment_context_id,
        decision_type="DEPLOYMENT_APPROVAL",
        outcome=payload.outcome,
        decision_authority_id=authority.id,
        rationale=payload.rationale,
        conditions=payload.conditions,
        valid_until=payload.valid_until,
    )
    db.add(decision); db.flush()
    if payload.outcome in {"APPROVED", "APPROVED_WITH_CONDITIONS"}:
        snapshot = _build_approval_snapshot(db, case)
        raw = json.dumps(snapshot, sort_keys=True, default=str).encode("utf-8")
        baseline = models.ApprovalBaseline(
            decision_id=decision.id,
            deployment_context_id=case.deployment_context_id,
            system_snapshot=snapshot["system"],
            classification_snapshot=snapshot["classifications"],
            risk_snapshot={"risks": snapshot["risks"]},
            control_snapshot={"safeguards": snapshot["safeguards"]},
            evidence_snapshot={"count": readiness["evidence_count"]},
            content_hash=hashlib.sha256(raw).hexdigest(),
        )
        db.add(baseline)
        dep = db.get(models.DeploymentContext, case.deployment_context_id)
        dep.lifecycle_status = "ACTIVE"
        case.governance_state = "ACTIVE"
        _ensure_monitoring_plan(db, case, authority.id)
    elif payload.outcome == "REJECTED":
        case.governance_state = "REJECTED"
    else:
        case.governance_state = "ASSURED"
    db.add(models.GovernanceGateResult(
        governance_case_id=case.id,
        gate_code="G07",
        result="PASS" if payload.outcome in {"APPROVED", "APPROVED_WITH_CONDITIONS"} else "FAIL" if payload.outcome == "REJECTED" else "PENDING",
        rationale=payload.rationale,
        blocking_reasons={"items": readiness["blockers"]},
    ))
    db.commit()
    return get_approval_summary(db, case_id)


def get_monitoring_summary(db: Session, case_id: str) -> dict:
    case = db.get(models.GovernanceCase, case_id)
    if not case:
        raise KeyError("Governance case not found")
    plan = db.query(models.MonitoringPlan).filter_by(deployment_context_id=case.deployment_context_id, status="ACTIVE").first()
    if not plan:
        return {"case_id": case_id, "state": case.governance_state, "active": False, "definitions": [], "events": [], "reassessments": []}
    defs = db.query(models.MonitoringDefinition).filter_by(monitoring_plan_id=plan.id, status="ACTIVE").all()
    items = []
    for d in defs:
        obs = db.query(models.Observation).filter_by(monitoring_definition_id=d.id).order_by(models.Observation.observed_at.desc()).first()
        items.append({
            "id": d.id, "name": d.name, "type": d.monitoring_type, "description": d.description, "frequency": d.frequency,
            "latest": ({"observed_at": obs.observed_at, "value": obs.value, "qualitative_result": obs.qualitative_result, "threshold_status": obs.threshold_status} if obs else None),
        })
    events = db.query(models.GovernanceEvent).filter_by(subject_id=case.deployment_context_id).order_by(models.GovernanceEvent.detected_at.desc()).all()
    reassessments = db.query(models.Reassessment).filter_by(governance_case_id=case.id).order_by(models.Reassessment.opened_at.desc()).all()
    return {
        "case_id": case.id, "state": case.governance_state, "active": True,
        "plan": {"id": plan.id, "purpose": plan.purpose, "review_frequency": plan.review_frequency},
        "definitions": items,
        "events": [{"id": e.id, "type": e.event_type, "severity": e.severity, "description": e.description, "status": e.status, "detected_at": e.detected_at} for e in events],
        "reassessments": [{"id": r.id, "starting_domain": r.starting_domain, "reason": r.reason, "status": r.status, "outcome": r.outcome, "opened_at": r.opened_at} for r in reassessments],
    }


def add_monitoring_observation(db: Session, definition_id: str, payload) -> dict:
    definition = db.get(models.MonitoringDefinition, definition_id)
    if not definition:
        raise KeyError("Monitoring definition not found")
    threshold_status = "OK"
    numeric = payload.value if isinstance(payload.value, (int, float)) else None
    if numeric is not None and numeric < 0:
        threshold_status = "BREACH"
    if payload.qualitative_result and payload.qualitative_result.strip().upper() in {"FAIL", "BREACH", "UNACCEPTABLE"}:
        threshold_status = "BREACH"
    obs = models.Observation(
        monitoring_definition_id=definition.id,
        value={"value": payload.value} if payload.value is not None else None,
        qualitative_result=payload.qualitative_result,
        threshold_status=threshold_status,
    )
    db.add(obs); db.flush()
    if threshold_status == "BREACH":
        plan = db.get(models.MonitoringPlan, definition.monitoring_plan_id)
        event = models.GovernanceEvent(subject_id=plan.deployment_context_id, event_type="MONITORING_BREACH", source=definition.name,
                                       severity="HIGH", description=f"Monitoring breach: {definition.name}")
        db.add(event); db.flush()
        case = db.query(models.GovernanceCase).filter_by(deployment_context_id=plan.deployment_context_id, status="OPEN").order_by(models.GovernanceCase.opened_at.desc()).first()
        if case:
            db.add(models.Reassessment(governance_case_id=case.id, trigger_event_id=event.id, starting_domain="RISK_IMPACT",
                                       reason=f"Monitoring breach detected for {definition.name}", owner_person_id=plan.owner_person_id))
            case.governance_state = "REASSESSMENT"
    db.commit()
    return {"id": obs.id, "threshold_status": obs.threshold_status, "observed_at": obs.observed_at}


def create_change_event(db: Session, case_id: str, payload) -> dict:
    case = db.get(models.GovernanceCase, case_id)
    if not case:
        raise KeyError("Governance case not found")
    severity = "HIGH" if payload.materiality in {"MATERIAL", "POTENTIALLY_SUBSTANTIAL", "SUBSTANTIAL"} else "LOW"
    event = models.GovernanceEvent(subject_id=case.deployment_context_id, event_type="CHANGE", source="USER_REPORTED", severity=severity,
                                   description=payload.description)
    db.add(event); db.flush()
    db.add(models.ChangeEvent(governance_event_id=event.id, change_type=payload.change_type, old_state_reference=payload.old_state,
                              new_state_reference=payload.new_state, materiality=payload.materiality))
    starting = "CLASSIFICATION" if payload.change_type in {"INTENDED_PURPOSE", "GEOGRAPHY", "AFFECTED_POPULATION", "AUTOMATION_LEVEL"} else "RISK_IMPACT"
    reassessment = None
    if payload.materiality != "NON_MATERIAL":
        reassessment = models.Reassessment(governance_case_id=case.id, trigger_event_id=event.id, starting_domain=starting,
                                           reason=payload.description)
        db.add(reassessment)
        case.governance_state = "REASSESSMENT"
    db.commit()
    return {"event_id": event.id, "materiality": payload.materiality, "reassessment_id": reassessment.id if reassessment else None, "state": case.governance_state}


def create_incident(db: Session, case_id: str, payload) -> dict:
    case = db.get(models.GovernanceCase, case_id)
    if not case:
        raise KeyError("Governance case not found")
    event = models.GovernanceEvent(subject_id=case.deployment_context_id, event_type="INCIDENT", source="USER_REPORTED", severity=payload.severity,
                                   description=payload.description)
    db.add(event); db.flush()
    db.add(models.Incident(governance_event_id=event.id, incident_category=payload.incident_category,
                           actual_harm=payload.actual_harm, potential_harm=payload.potential_harm,
                           containment_status="OPEN", reportability_status="REVIEW_REQUIRED"))
    reassessment = models.Reassessment(governance_case_id=case.id, trigger_event_id=event.id, starting_domain="RISK_IMPACT",
                                       reason=f"Incident: {payload.description}")
    db.add(reassessment)
    case.governance_state = "REASSESSMENT"
    db.commit()
    return {"event_id": event.id, "reassessment_id": reassessment.id, "state": case.governance_state, "reportability_status": "REVIEW_REQUIRED"}

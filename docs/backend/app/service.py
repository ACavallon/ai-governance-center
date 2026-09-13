from __future__ import annotations
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
    owner = models.ResponsibleParty(organisation_id=org_entity.id, party_type="PERSON", display_name=payload.owner_name)
    db.add(owner); db.flush()

    supplier_id = None
    if payload.supply_model == "third_party" and payload.supplier_name:
        supplier = models.LegalEntity(legal_name=payload.supplier_name, display_name=payload.supplier_name, entity_type="VENDOR")
        db.add(supplier); db.flush(); supplier_id = supplier.id

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
        ("business_purpose", payload.business_purpose), ("system_name", payload.system_name),
        ("decision_domain", payload.decision_domain), ("function", payload.function), ("countries", payload.countries)
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
    owner = db.get(models.ResponsibleParty, use_case.business_owner_id)
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

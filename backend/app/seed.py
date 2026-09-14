from sqlalchemy.orm import Session
from .models import (
    NormativeSource, SourceVersion, Requirement, Rule, RuleVersion, GuidedQuestion,
    Country, LegalEntity, Organisation, BusinessUnit, Person, Group, PersonQualification,
    AssessmentTemplate, ControlObjective, Control, RequirementControlMapping
)
from .countries import COUNTRIES

AI_ACT_URL = "https://eur-lex.europa.eu/eli/reg/2024/1689/2026-07-27/eng"


def _seed_phase_c(db: Session) -> None:
    template = db.query(AssessmentTemplate).filter_by(template_code="AI_RISK_GENERAL").first()
    if not template:
        db.add(AssessmentTemplate(
            template_code="AI_RISK_GENERAL",
            name="AI risk & impact review",
            assessment_type="AI_RISK",
            description="Plain-language review of material AI risks, impacts and safeguards before approval.",
            source_type="INTEGRATED_GOVERNANCE",
            version=1,
        ))
        db.flush()

    objectives = {
        "OBJ-HO-001": ("Maintain effective human oversight", "Ensure people can critically review and intervene in AI-supported decisions.", "HUMAN_OVERSIGHT"),
        "OBJ-FAIR-001": ("Detect material group disparities", "Evaluate whether performance differs materially across affected groups.", "FAIRNESS"),
        "OBJ-TRN-001": ("Prepare people for AI oversight", "Ensure people responsible for AI oversight understand the system, limitations and intervention process.", "TRAINING"),
        "OBJ-MON-001": ("Monitor operational AI risk", "Track performance and risk indicators after deployment.", "MONITORING"),
    }
    obj_rows = {}
    for code, (name, desc, domain) in objectives.items():
        row = db.query(ControlObjective).filter_by(objective_code=code).first()
        if not row:
            row = ControlObjective(objective_code=code, name=name, description=desc, governance_domain=domain)
            db.add(row); db.flush()
        obj_rows[code] = row

    controls = {
        "CTRL-HO-001": ("OBJ-HO-001", "Human review before adverse decision", "A qualified person reviews material AI recommendations and can override or stop the outcome.", "PREVENTIVE", "MANUAL", "PER_DECISION"),
        "CTRL-FAIR-001": ("OBJ-FAIR-001", "Fairness testing by affected group", "Evaluate relevant performance measures across affected groups before approval and after material change.", "DETECTIVE", "HYBRID", "ON_CHANGE"),
        "CTRL-TRN-001": ("OBJ-TRN-001", "Human overseer training", "People assigned to oversight receive role-appropriate training and understand when and how to intervene.", "PREVENTIVE", "MANUAL", "ANNUAL"),
        "CTRL-MON-001": ("OBJ-MON-001", "Performance and fairness monitoring", "Monitor approved performance and fairness indicators during operation and escalate material deviations.", "DETECTIVE", "HYBRID", "PERIODIC"),
    }
    ctl_rows = {}
    for code, (obj_code, name, desc, ctype, mode, freq) in controls.items():
        row = db.query(Control).filter_by(control_code=code).first()
        if not row:
            row = Control(control_code=code, objective_id=obj_rows[obj_code].id, name=name, description=desc,
                          control_type=ctype, execution_mode=mode, frequency_type=freq)
            db.add(row); db.flush()
        ctl_rows[code] = row

    req_human = db.query(Requirement).filter_by(requirement_code="AIA-HO-001").first()
    req_risk = db.query(Requirement).filter_by(requirement_code="AIA-RISK-001").first()
    mapping_specs = []
    if req_human:
        mapping_specs += [(req_human, ctl_rows["CTRL-HO-001"], "FULL"), (req_human, ctl_rows["CTRL-TRN-001"], "SUPPORTING")]
    if req_risk:
        mapping_specs += [(req_risk, ctl_rows["CTRL-FAIR-001"], "SUPPORTING"), (req_risk, ctl_rows["CTRL-MON-001"], "SUPPORTING")]
    for req, ctl, coverage in mapping_specs:
        if not db.query(RequirementControlMapping).filter_by(requirement_id=req.id, control_id=ctl.id).first():
            db.add(RequirementControlMapping(requirement_id=req.id, control_id=ctl.id, coverage=coverage,
                                             rationale="Prototype integrated mapping; requires governance validation before production use."))
    db.commit()


def seed_reference_data(db: Session) -> None:
    # Reference data is seeded independently so later versions can add directory/reference
    # records without being blocked by an already-seeded normative source.
    if db.query(Country).count() == 0:
        db.add_all([Country(code=code, name=name, eu_member=eu, eea_member=eea) for code, name, eu, eea in COUNTRIES])
        db.flush()

    entity = db.query(LegalEntity).filter_by(legal_name="Demo Company EU").first()
    if not entity:
        entity = LegalEntity(legal_name="Demo Company EU", display_name="Demo Company", entity_type="OUR_ORGANISATION", country_code="FR")
        db.add(entity); db.flush()
        db.add(Organisation(legal_entity_id=entity.id)); db.flush()
    org = db.get(Organisation, entity.id)
    bu = db.query(BusinessUnit).filter_by(organisation_id=entity.id, name="Human Resources").first()
    if not bu:
        bu = BusinessUnit(organisation_id=entity.id, name="Human Resources")
        db.add(bu); db.flush()

    demo_people = [
        ("Anna", "Rossi", "anna.rossi@example.com", "Head of Human Resources", "FR", "EXECUTIVE"),
        ("Marco", "Bianchi", "marco.bianchi@example.com", "HR Technology Lead", "IT", "MANAGER"),
        ("Sophie", "Martin", "sophie.martin@example.com", "AI Governance Lead", "FR", "GOVERNANCE_APPROVER"),
    ]
    people = {}
    for first, last, email, title, country, authority in demo_people:
        person = db.query(Person).filter_by(organisation_id=entity.id, email=email).first()
        if not person:
            person = Person(organisation_id=entity.id, business_unit_id=bu.id, first_name=first, last_name=last, display_name=f"{first} {last}", email=email, job_title=title, employment_type="EMPLOYEE", country_code=country, authority_level=authority)
            db.add(person); db.flush()
        people[email] = person
    if not bu.owner_person_id:
        bu.owner_person_id = people["anna.rossi@example.com"].id
    committee = db.query(Group).filter_by(organisation_id=entity.id, name="AI Governance Committee", group_type="COMMITTEE").first()
    if not committee:
        db.add(Group(organisation_id=entity.id, group_type="COMMITTEE", name="AI Governance Committee", owner_person_id=people["sophie.martin@example.com"].id, description="Cross-functional AI governance approval body."))
    if not db.query(PersonQualification).filter_by(person_id=people["sophie.martin@example.com"].id, qualification_type="AI_GOVERNANCE_REVIEWER").first():
        db.add(PersonQualification(person_id=people["sophie.martin@example.com"].id, qualification_type="AI_GOVERNANCE_REVIEWER", status="CURRENT"))
    db.commit()

    if db.query(NormativeSource).filter_by(source_code="EU_AI_ACT").first():
        _seed_phase_c(db)
        return

    source = NormativeSource(
        source_code="EU_AI_ACT",
        title="Regulation (EU) 2024/1689 — Artificial Intelligence Act",
        short_name="EU AI Act",
        source_type="LAW",
        issuer="European Union",
        jurisdiction="EU",
        authority_level="BINDING_LAW",
        binding_status="BINDING",
        official_uri=AI_ACT_URL,
    )
    db.add(source); db.flush()
    version = SourceVersion(source_id=source.id, version_label="Consolidated 2026-07-27", official_uri=AI_ACT_URL)
    db.add(version); db.flush()

    req_human = Requirement(
        source_version_id=version.id,
        requirement_code="AIA-HO-001",
        title="Human oversight for high-risk AI",
        normative_statement="Relevant high-risk AI governance requires effective human oversight and deployer oversight responsibilities where applicable.",
        source_reference="Articles 14 and 26",
    )
    req_risk = Requirement(
        source_version_id=version.id,
        requirement_code="AIA-RISK-001",
        title="Risk management for high-risk AI",
        normative_statement="High-risk AI systems are subject to lifecycle risk-management requirements where the actor and context make those provisions applicable.",
        source_reference="Article 9",
    )
    req_transparency = Requirement(
        source_version_id=version.id,
        requirement_code="AIA-TRANS-001",
        title="Transparency screening",
        normative_statement="Certain AI systems and uses are subject to specific transparency duties.",
        source_reference="Article 50",
    )
    db.add_all([req_human, req_risk, req_transparency]); db.flush()

    rules = [
        (
            "EU_SCOPE_INDICATOR", "EU scope indicator", "SCOPE", "CLASSIFICATION_RESULT",
            {"any": [
                {"fact": "deployment.countries", "operator": "contains_any", "value": ["AT","BE","BG","HR","CY","CZ","DK","EE","FI","FR","DE","GR","HU","IE","IT","LV","LT","LU","MT","NL","PL","PT","RO","SK","SI","ES","SE"]}
            ]},
            {"dimension":"REGULATORY_SCOPE","when_true":"APPLICABLE_INDICATOR","when_false":"REVIEW_OTHER_SCOPE","when_unknown":"UNDETERMINED","confidence":"MEDIUM"},
            "At least one declared deployment/affected-person country is in the EU, so EU AI Act scope is indicated. Full Article 2 scope review remains part of governance confirmation.",
            "EU AI Act Article 2"
        ),
        (
            "LIKELY_DEPLOYER", "Likely deployer role", "ACTOR_ROLE", "ACTOR_ROLE",
            {"fact":"system.supply_model","operator":"eq","value":"third_party"},
            {"dimension":"ACTOR_ROLE","when_true":"DEPLOYER","when_false":"ROLE_REVIEW_REQUIRED","when_unknown":"UNDETERMINED","confidence":"MEDIUM"},
            "The organisation is using a third-party AI system, indicating a likely deployer role. Provider status must still be reviewed if the system is marketed under the organisation's name or materially modified.",
            "EU AI Act Article 3 actor definitions"
        ),
        (
            "EMPLOYMENT_HIGH_RISK_SCREEN", "Employment high-risk screening", "CLASSIFICATION", "CLASSIFICATION_RESULT",
            {"all": [
                {"fact":"deployment.decision_domain","operator":"eq","value":"EMPLOYMENT"},
                {"fact":"deployment.function","operator":"in","value":["ranking","scoring","selection","evaluation"]}
            ]},
            {"dimension":"HIGH_RISK","when_true":"ANNEX_III_REVIEW_REQUIRED","when_false":"NO_EMPLOYMENT_TRIGGER_IDENTIFIED","when_unknown":"UNDETERMINED","confidence":"MEDIUM"},
            "The declared use involves employment-related ranking/evaluation. This is a strong Annex III screening trigger, but the full Article 6 and Annex III conditions and exceptions must be reviewed before a final legal conclusion.",
            "EU AI Act Article 6 and Annex III"
        ),
        (
            "TRANSPARENCY_SCREEN", "Transparency screening", "CLASSIFICATION", "CLASSIFICATION_RESULT",
            {"fact":"deployment.function","operator":"in","value":["generation","chatbot","deepfake","synthetic_content"]},
            {"dimension":"TRANSPARENCY","when_true":"ARTICLE_50_REVIEW_REQUIRED","when_false":"NO_TRIGGER_IDENTIFIED","when_unknown":"UNDETERMINED","confidence":"MEDIUM"},
            "The declared function may fall within an Article 50 transparency category. A detailed review is required before confirming the specific duty.",
            "EU AI Act Article 50"
        ),
    ]
    for code, name, rtype, target, expr, output, explanation, source_ref in rules:
        rule = Rule(rule_code=code, name=name, rule_type=rtype, target_type=target)
        db.add(rule); db.flush()
        db.add(RuleVersion(rule_id=rule.id, version=1, expression=expr, output=output, explanation_template=explanation, source_reference=source_ref))

    questions = [
        ("PURPOSE-01", "purpose", "What are you using AI for?", "We use this to understand the business purpose and intended outcome.", "text", "use_case.business_purpose", 1),
        ("TECH-01", "technology", "Is the AI built internally or supplied by another company?", "This helps us determine which organisations and actor roles need review.", "choice", "system.supply_model", 2),
        ("FUNCTION-01", "use", "What does the AI actually do?", "Function is important for regulatory classification and risk analysis.", "choice", "deployment.function", 3),
        ("PEOPLE-01", "people", "Who could be affected by the AI?", "Affected people drive impact, risk and some regulatory checks.", "choice", "deployment.affected_population", 4),
        ("DECISION-01", "decisions", "Can the AI influence an important decision about a person?", "This helps identify higher-impact use cases and required safeguards.", "choice", "deployment.decision_domain", 5),
        ("WHERE-01", "location", "Where will the AI be used or affect people?", "Location is relevant to territorial scope and governance obligations.", "countries", "deployment.countries", 6),
    ]
    for code, section, text, why, atype, path, seq in questions:
        db.add(GuidedQuestion(question_code=code, section_code=section, plain_language_text=text, why_we_ask=why, answer_type=atype, canonical_fact_path=path, sequence=seq))
    db.commit()
    _seed_phase_c(db)

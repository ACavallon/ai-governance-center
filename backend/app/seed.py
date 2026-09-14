from sqlalchemy.orm import Session
from .models import (
    NormativeSource, SourceVersion, Requirement, Rule, RuleVersion, GuidedQuestion,
    Country, LegalEntity, Organisation, BusinessUnit, Person, Group, PersonQualification,
    AssessmentTemplate, ControlObjective, Control, RequirementControlMapping,
    GovernanceResponsibility, GovernanceRole, RoleResponsibility, GovernanceRoleAssignment,
    Course, TrainingProgram, TrainingProgramCourse, RoleTrainingRequirement, LearningAssignment, CourseCompletion, GuideContent
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



def _seed_v005(db: Session) -> None:
    responsibilities = [
        ("RESP-DESCRIBE", "Describe intended purpose", "Define and maintain the business purpose, intended users and decision context.", "DESCRIBE", "NIST AI RMF GOVERN 1.6; EU AI Act role/context obligations"),
        ("RESP-CLASSIFY", "Review regulatory classification", "Review scope, actor role and relevant AI Act classification dimensions.", "RULES", "EU AI Act Articles 2, 3, 5, 6, 50"),
        ("RESP-RISK", "Perform AI risk and impact review", "Identify material risk scenarios, affected people and impacts.", "RISKS", "EU AI Act Article 9 where applicable; ISO/IEC 42001 AIMS; NIST MAP/MEASURE/MANAGE"),
        ("RESP-CONTROL", "Define and implement safeguards", "Select, implement and maintain safeguards addressing requirements and material risks.", "SAFEGUARDS", "ISO/IEC 42001; NIST GOVERN/MANAGE"),
        ("RESP-APPROVE", "Approve AI deployment", "Make an accountable decision on readiness and residual risk before operation.", "APPROVAL", "NIST AI RMF GOVERN 2.3"),
        ("RESP-OVERSIGHT", "Perform human oversight", "Exercise meaningful human oversight and escalation for the AI-supported process.", "OPERATE", "EU AI Act Articles 14 and 26 where applicable"),
        ("RESP-MONITOR", "Monitor operational AI", "Review performance, fairness, control effectiveness and changes during operation.", "OPERATE", "EU AI Act Article 72 where applicable; NIST GOVERN 1.5"),
        ("RESP-INCIDENT", "Review AI incidents and changes", "Assess incidents and material changes and trigger targeted reassessment.", "OPERATE", "EU AI Act incident/change obligations where applicable; NIST MANAGE"),
    ]
    resp_rows={}
    for code,name,desc,stage,source in responsibilities:
        row=db.query(GovernanceResponsibility).filter_by(code=code).first()
        if not row:
            row=GovernanceResponsibility(code=code,name=name,description=desc,lifecycle_stage=stage,source_reference=source)
            db.add(row); db.flush()
        resp_rows[code]=row

    role_specs = [
        ("ROLE-BUSINESS-OWNER","AI Business Owner","Accountable business owner for intended purpose and operational use."),
        ("ROLE-TECH-OWNER","AI Technical Owner","Responsible for technical implementation, configuration and technical monitoring."),
        ("ROLE-RISK-REVIEWER","AI Risk Reviewer","Independent or second-line reviewer of AI risk and control adequacy."),
        ("ROLE-GOV-LEAD","AI Governance Lead","Coordinates governance, classification, assurance and escalation."),
        ("ROLE-APPROVER","AI Approver","Accountable authority for deployment approval and residual-risk decision."),
        ("ROLE-HUMAN-OVERSEER","Human Oversight Officer","Performs role-specific human oversight during operation."),
    ]
    roles={}
    for code,name,desc in role_specs:
        row=db.query(GovernanceRole).filter_by(code=code).first()
        if not row:
            row=GovernanceRole(code=code,name=name,description=desc)
            db.add(row); db.flush()
        roles[code]=row

    raci = {
        "ROLE-BUSINESS-OWNER":{"RESP-DESCRIBE":"A","RESP-RISK":"C","RESP-CONTROL":"A","RESP-MONITOR":"A","RESP-INCIDENT":"A"},
        "ROLE-TECH-OWNER":{"RESP-DESCRIBE":"C","RESP-RISK":"C","RESP-CONTROL":"R","RESP-MONITOR":"R","RESP-INCIDENT":"R"},
        "ROLE-RISK-REVIEWER":{"RESP-RISK":"R","RESP-CONTROL":"C","RESP-APPROVE":"C","RESP-INCIDENT":"C"},
        "ROLE-GOV-LEAD":{"RESP-CLASSIFY":"A","RESP-RISK":"A","RESP-CONTROL":"C","RESP-APPROVE":"R","RESP-MONITOR":"C","RESP-INCIDENT":"R"},
        "ROLE-APPROVER":{"RESP-APPROVE":"A"},
        "ROLE-HUMAN-OVERSEER":{"RESP-OVERSIGHT":"R","RESP-MONITOR":"C","RESP-INCIDENT":"R"},
    }
    raci_map={"R":"RESPONSIBLE","A":"ACCOUNTABLE","C":"CONSULTED","I":"INFORMED"}
    for role_code,mapping in raci.items():
        for resp_code,r in mapping.items():
            if not db.query(RoleResponsibility).filter_by(role_id=roles[role_code].id,responsibility_id=resp_rows[resp_code].id).first():
                db.add(RoleResponsibility(role_id=roles[role_code].id,responsibility_id=resp_rows[resp_code].id,raci_type=raci_map[r]))

    courses = [
        ("CRS-AI-LIT","AI Governance Fundamentals","Baseline AI literacy, governance roles, limitations and escalation.",24),
        ("CRS-EU-ACT","EU AI Act for Governance Roles","Role-relevant EU AI Act responsibilities and evidence expectations.",12),
        ("CRS-RISK","AI Risk & Impact Assessment","Scenario-based AI risk, impact and residual-risk assessment.",12),
        ("CRS-HO","Human Oversight for AI Systems","System limitations, intervention, override and escalation for human overseers.",12),
        ("CRS-APPROVAL","AI Approval & Accountability","Approval gates, residual-risk decisions and segregation of duties.",12),
    ]
    course_rows={}
    for code,title,desc,validity in courses:
        row=db.query(Course).filter_by(code=code).first()
        if not row:
            row=Course(code=code,title=title,description=desc,provider="Organisation / connected LMS",validity_months=validity)
            db.add(row); db.flush()
        course_rows[code]=row
    program=db.query(TrainingProgram).filter_by(code="PRG-AI-GOV").first()
    if not program:
        program=TrainingProgram(code="PRG-AI-GOV",name="AI Governance Core",description="Core role-based learning pathway for AI governance responsibilities.")
        db.add(program); db.flush()
    for i,code in enumerate(["CRS-AI-LIT","CRS-EU-ACT","CRS-RISK","CRS-HO","CRS-APPROVAL"],1):
        if not db.query(TrainingProgramCourse).filter_by(training_program_id=program.id,course_id=course_rows[code].id).first():
            db.add(TrainingProgramCourse(training_program_id=program.id,course_id=course_rows[code].id,sequence=i,requirement_level="MANDATORY" if code=="CRS-AI-LIT" else "RECOMMENDED"))
    reqs={
        "ROLE-BUSINESS-OWNER":[("CRS-AI-LIT","MANDATORY"),("CRS-EU-ACT","RECOMMENDED")],
        "ROLE-TECH-OWNER":[("CRS-AI-LIT","MANDATORY")],
        "ROLE-RISK-REVIEWER":[("CRS-AI-LIT","MANDATORY"),("CRS-RISK","MANDATORY"),("CRS-EU-ACT","RECOMMENDED")],
        "ROLE-GOV-LEAD":[("CRS-AI-LIT","MANDATORY"),("CRS-EU-ACT","MANDATORY"),("CRS-RISK","MANDATORY")],
        "ROLE-APPROVER":[("CRS-AI-LIT","MANDATORY"),("CRS-EU-ACT","MANDATORY"),("CRS-APPROVAL","MANDATORY")],
        "ROLE-HUMAN-OVERSEER":[("CRS-AI-LIT","MANDATORY"),("CRS-HO","MANDATORY")],
    }
    for role_code,items in reqs.items():
        for course_code,level in items:
            if not db.query(RoleTrainingRequirement).filter_by(role_id=roles[role_code].id,course_id=course_rows[course_code].id).first():
                db.add(RoleTrainingRequirement(role_id=roles[role_code].id,course_id=course_rows[course_code].id,requirement_level=level,rationale="Role-based competence and AI literacy requirement."))

    people={p.email:p for p in db.query(Person).filter(Person.email.is_not(None)).all()}
    assignments=[
        ("anna.rossi@example.com","ROLE-BUSINESS-OWNER"),
        ("marco.bianchi@example.com","ROLE-TECH-OWNER"),
        ("sophie.martin@example.com","ROLE-GOV-LEAD"),
        ("sophie.martin@example.com","ROLE-APPROVER"),
    ]
    for email,role_code in assignments:
        person=people.get(email)
        if person and not db.query(GovernanceRoleAssignment).filter_by(person_id=person.id,role_id=roles[role_code].id,assignment_scope="ORGANISATION").first():
            db.add(GovernanceRoleAssignment(person_id=person.id,role_id=roles[role_code].id,assignment_scope="ORGANISATION"))
    # Seed illustrative completion records; these are demo data, not legal conclusions.
    from datetime import date, timedelta
    today=date.today()
    completion_specs=[
        ("anna.rossi@example.com","CRS-AI-LIT",today-timedelta(days=100),today+timedelta(days=630)),
        ("marco.bianchi@example.com","CRS-AI-LIT",today-timedelta(days=80),today+timedelta(days=650)),
        ("sophie.martin@example.com","CRS-AI-LIT",today-timedelta(days=40),today+timedelta(days=690)),
        ("sophie.martin@example.com","CRS-EU-ACT",today-timedelta(days=30),today+timedelta(days=335)),
        ("sophie.martin@example.com","CRS-RISK",today-timedelta(days=25),today+timedelta(days=340)),
        ("sophie.martin@example.com","CRS-APPROVAL",today-timedelta(days=20),today+timedelta(days=345)),
    ]
    for email,course_code,completed,valid_until in completion_specs:
        person=people.get(email)
        if person and not db.query(CourseCompletion).filter_by(person_id=person.id,course_id=course_rows[course_code].id).first():
            db.add(CourseCompletion(person_id=person.id,course_id=course_rows[course_code].id,completed_at=completed,valid_until=valid_until,status="CURRENT",evidence_reference="Demo learning record"))

    guide = [
        ("GUIDE-OVERVIEW","UNDERSTAND",None,"What AI governance is","AI governance is the organisation-wide system of accountability, policies, risk management, controls, assurance and continual improvement used to develop and use AI responsibly.","It connects organisational governance with decisions made for each individual AI use.",None,None,"Start with the difference between organisation governance and AI-use governance.","ISO/IEC 42001; NIST AI RMF GOVERN"),
        ("GUIDE-LAYERS","UNDERSTAND",None,"Organisation governance vs. AI-use governance","Organisation governance defines the framework, roles, policies, competence and oversight. AI-use governance applies that framework to one concrete deployment context.","Keeping the layers separate prevents a per-system checklist from being mistaken for the whole governance system.",None,None,"Use Governance for the management system and My AI for individual AI uses.","ISO/IEC 42001; NIST AI RMF GOVERN"),
        ("GUIDE-DESCRIBE","JOURNEY","DESCRIBE","1. Describe your AI","Capture the intended purpose, system, people affected, countries and decision involvement in business language.","Reliable governance depends on reliable facts about the actual use.","Business purpose, owner, system, geography, affected population and decision context.","AI Business Owner","Run the Rules Check.","EU AI Act scope/actor context; NIST MAP"),
        ("GUIDE-RULES","JOURNEY","RULES","2. Understand applicable rules","Use facts about the AI use to determine scope, actor roles and relevant regulatory classification dimensions.","Users should provide facts; the system should not ask non-lawyers to classify Annex III themselves.","Factual answers and expert review for uncertain legal conclusions.","AI Governance Lead / Legal","Translate applicable requirements into governance actions.","EU AI Act Articles 2, 3, 5, 6 and 50"),
        ("GUIDE-RISKS","JOURNEY","RISKS","3. Assess risks & impacts","Identify cause-event-consequence scenarios, affected people, impacts and uncertainty.","Regulatory classification and risk are related but not the same thing.","Risk scenarios, affected populations, impacts and evaluations.","AI Risk Reviewer with business/technical contributors","Select treatments and safeguards.","EU AI Act Article 9 where applicable; ISO/IEC 23894; NIST AI RMF"),
        ("GUIDE-SAFEGUARDS","JOURNEY","SAFEGUARDS","4. Define safeguards & proof","Implement safeguards, assign owners, collect evidence and test whether controls operate effectively.","A control is not evidence, and evidence existence does not prove effectiveness.","Control implementation, evidence and assurance results.","Business/Technical owners and control owners","Resolve findings and prepare approval.","ISO/IEC 42001; NIST MANAGE"),
        ("GUIDE-APPROVAL","JOURNEY","APPROVAL","5. Obtain accountable approval","An eligible authority reviews readiness, residual risk and conditions and freezes the approved baseline.","The organisation needs a traceable accountable decision rather than an implicit go-live.","Gate results, residual risk, evidence and approver rationale.","AI Approver","Operate only against the approved baseline.","NIST AI RMF GOVERN 2.3"),
        ("GUIDE-OPERATE","JOURNEY","OPERATE","6. Operate, monitor & reassess","Monitor the approved AI use and trigger targeted reassessment when monitoring, incidents or changes invalidate earlier conclusions.","AI governance is continuous, not a one-time checklist.","Observations, incidents, changes, complaints and review outcomes.","Operational owners / AI Governance","Reassess only the affected downstream domains.","EU AI Act Article 72 where applicable; ISO/IEC 42001 continual improvement; NIST GOVERN 1.5"),
        ("GUIDE-PEOPLE","UNDERSTAND",None,"Roles, RACI and competence","Governance roles are configurable bundles of responsibilities. RACI states how each role participates; training and qualifications determine whether a person is eligible for an assignment.","This separates organisational design from physical people and makes accountability auditable.",None,None,"Review the People & Roles area and training readiness.","EU AI Act Article 4; NIST GOVERN 2.1-2.2; ISO/IEC 42001"),
    ]
    for i,(code,section,stage,title,summary,why,expected,role,next_step,source) in enumerate(guide,1):
        if not db.query(GuideContent).filter_by(code=code).first():
            db.add(GuideContent(code=code,section=section,journey_stage=stage,title=title,summary=summary,why_it_matters=why,expected_input=expected,responsible_role=role,next_step=next_step,source_reference=source,sequence=i))
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
        _seed_v005(db)
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
    _seed_v005(db)

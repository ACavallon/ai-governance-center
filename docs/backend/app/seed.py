from sqlalchemy.orm import Session
from .models import NormativeSource, SourceVersion, Requirement, Rule, RuleVersion, GuidedQuestion

AI_ACT_URL = "https://eur-lex.europa.eu/eli/reg/2024/1689/2026-07-27/eng"


def seed_reference_data(db: Session) -> None:
    if db.query(NormativeSource).filter_by(source_code="EU_AI_ACT").first():
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

from __future__ import annotations
from datetime import date, datetime
import uuid

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def uid() -> str:
    return str(uuid.uuid4())

class Country(Base):
    __tablename__ = "country"
    __table_args__ = {"schema": "core"}
    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    eu_member: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    eea_member: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)

class LegalEntity(Base):
    __tablename__ = "legal_entity"
    __table_args__ = {"schema": "core"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    legal_name: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    entity_type: Mapped[str] = mapped_column(String(50))
    country_code: Mapped[str | None] = mapped_column(ForeignKey("core.country.code"))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class GovernedObject(Base):
    __tablename__ = "governed_object"
    __table_args__ = {"schema": "core"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    object_type: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Organisation(Base):
    __tablename__ = "organisation"
    __table_args__ = {"schema": "org"}
    legal_entity_id: Mapped[str] = mapped_column(ForeignKey("core.legal_entity.id"), primary_key=True)
    governance_scope: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

class BusinessUnit(Base):
    __tablename__ = "business_unit"
    __table_args__ = {"schema": "org"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organisation_id: Mapped[str] = mapped_column(ForeignKey("org.organisation.legal_entity_id"))
    parent_unit_id: Mapped[str | None] = mapped_column(ForeignKey("org.business_unit.id"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    owner_person_id: Mapped[str | None] = mapped_column(ForeignKey("org.person.id"))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

class Person(Base):
    __tablename__ = "person"
    __table_args__ = (
        UniqueConstraint("organisation_id", "email", name="uq_person_org_email"),
        {"schema": "org"},
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organisation_id: Mapped[str] = mapped_column(ForeignKey("org.organisation.legal_entity_id"))
    business_unit_id: Mapped[str | None] = mapped_column(ForeignKey("org.business_unit.id"))
    manager_person_id: Mapped[str | None] = mapped_column(ForeignKey("org.person.id"))
    employee_id: Mapped[str | None] = mapped_column(String(120))
    first_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[str] = mapped_column(String(120))
    display_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    job_title: Mapped[str | None] = mapped_column(String(255))
    employment_type: Mapped[str | None] = mapped_column(String(60))
    country_code: Mapped[str | None] = mapped_column(ForeignKey("core.country.code"))
    authority_level: Mapped[str | None] = mapped_column(String(60))
    active_from: Mapped[date | None] = mapped_column(Date)
    active_to: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

class Group(Base):
    __tablename__ = "group"
    __table_args__ = (
        UniqueConstraint("organisation_id", "name", "group_type", name="uq_group_org_name_type"),
        {"schema": "org"},
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organisation_id: Mapped[str] = mapped_column(ForeignKey("org.organisation.legal_entity_id"))
    group_type: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(255))
    owner_person_id: Mapped[str | None] = mapped_column(ForeignKey("org.person.id"))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

class RoleAssignment(Base):
    __tablename__ = "role_assignment"
    __table_args__ = {"schema": "org"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    person_id: Mapped[str | None] = mapped_column(ForeignKey("org.person.id"))
    group_id: Mapped[str | None] = mapped_column(ForeignKey("org.group.id"))
    role_type: Mapped[str] = mapped_column(String(80))
    governed_object_id: Mapped[str | None] = mapped_column(ForeignKey("core.governed_object.id"))
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

class PersonQualification(Base):
    __tablename__ = "person_qualification"
    __table_args__ = {"schema": "org"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    person_id: Mapped[str] = mapped_column(ForeignKey("org.person.id"))
    qualification_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="CURRENT")
    issued_at: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    evidence_reference: Mapped[str | None] = mapped_column(Text)

class AIUseCase(Base):
    __tablename__ = "ai_use_case"
    __table_args__ = {"schema": "ai"}
    id: Mapped[str] = mapped_column(ForeignKey("core.governed_object.id"), primary_key=True)
    business_unit_id: Mapped[str] = mapped_column(ForeignKey("org.business_unit.id"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    business_purpose: Mapped[str] = mapped_column(Text)
    intended_outcome: Mapped[str | None] = mapped_column(Text)
    business_process: Mapped[str | None] = mapped_column(String(120))
    business_owner_id: Mapped[str] = mapped_column(ForeignKey("org.person.id"))
    lifecycle_status: Mapped[str] = mapped_column(String(30), default="ASSESSMENT")

class AISystem(Base):
    __tablename__ = "ai_system"
    __table_args__ = {"schema": "ai"}
    id: Mapped[str] = mapped_column(ForeignKey("core.governed_object.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    intended_purpose: Mapped[str] = mapped_column(Text)
    development_type: Mapped[str] = mapped_column(String(30))
    supplier_entity_id: Mapped[str | None] = mapped_column(ForeignKey("core.legal_entity.id"))
    lifecycle_status: Mapped[str] = mapped_column(String(30), default="ASSESSMENT")

class UseCaseSystem(Base):
    __tablename__ = "use_case_system"
    __table_args__ = (
        UniqueConstraint("use_case_id", "system_id", name="uq_use_case_system"),
        {"schema": "ai"},
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    use_case_id: Mapped[str] = mapped_column(ForeignKey("ai.ai_use_case.id"))
    system_id: Mapped[str] = mapped_column(ForeignKey("ai.ai_system.id"))

class DeploymentContext(Base):
    __tablename__ = "deployment_context"
    __table_args__ = {"schema": "ai"}
    id: Mapped[str] = mapped_column(ForeignKey("core.governed_object.id"), primary_key=True)
    system_id: Mapped[str] = mapped_column(ForeignKey("ai.ai_system.id"))
    use_case_id: Mapped[str] = mapped_column(ForeignKey("ai.ai_use_case.id"))
    name: Mapped[str] = mapped_column(String(255))
    intended_purpose: Mapped[str] = mapped_column(Text)
    deployment_environment: Mapped[str | None] = mapped_column(String(80))
    degree_of_automation: Mapped[str | None] = mapped_column(String(50))
    human_oversight_model: Mapped[str | None] = mapped_column(Text)
    lifecycle_status: Mapped[str] = mapped_column(String(30), default="ASSESSMENT")

class DeploymentGeography(Base):
    __tablename__ = "deployment_geography"
    __table_args__ = {"schema": "ai"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    deployment_context_id: Mapped[str] = mapped_column(ForeignKey("ai.deployment_context.id"))
    country_code: Mapped[str] = mapped_column(ForeignKey("core.country.code"))
    usage_type: Mapped[str] = mapped_column(String(40), default="AFFECTED_PERSON_LOCATION")

class AffectedPopulation(Base):
    __tablename__ = "affected_population"
    __table_args__ = {"schema": "ai"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    deployment_context_id: Mapped[str] = mapped_column(ForeignKey("ai.deployment_context.id"))
    population_type: Mapped[str] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(Text)
    estimated_scale: Mapped[int | None] = mapped_column(Integer)
    is_vulnerable_group: Mapped[bool] = mapped_column(Boolean, default=False)

class DecisionInvolvement(Base):
    __tablename__ = "decision_involvement"
    __table_args__ = {"schema": "ai"}
    deployment_context_id: Mapped[str] = mapped_column(ForeignKey("ai.deployment_context.id"), primary_key=True)
    decision_domain: Mapped[str | None] = mapped_column(String(80))
    ai_role: Mapped[str] = mapped_column(String(50))
    human_role: Mapped[str | None] = mapped_column(Text)
    decision_consequence: Mapped[str | None] = mapped_column(Text)

class ActorRoleAssignment(Base):
    __tablename__ = "actor_role_assignment"
    __table_args__ = {"schema": "governance"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    legal_entity_id: Mapped[str] = mapped_column(ForeignKey("core.legal_entity.id"))
    governed_object_id: Mapped[str] = mapped_column(ForeignKey("core.governed_object.id"))
    role_type: Mapped[str] = mapped_column(String(60))
    jurisdiction: Mapped[str | None] = mapped_column(String(30))
    confidence: Mapped[str] = mapped_column(String(30), default="INFERRED")
    assessment_basis: Mapped[str | None] = mapped_column(Text)

class GovernanceCase(Base):
    __tablename__ = "governance_case"
    __table_args__ = {"schema": "governance"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    deployment_context_id: Mapped[str] = mapped_column(ForeignKey("ai.deployment_context.id"))
    case_type: Mapped[str] = mapped_column(String(50), default="NEW_DEPLOYMENT")
    governance_state: Mapped[str] = mapped_column(String(40), default="REGISTERED")
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class NormativeSource(Base):
    __tablename__ = "normative_source"
    __table_args__ = {"schema": "normative"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    source_code: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(500))
    short_name: Mapped[str | None] = mapped_column(String(100))
    source_type: Mapped[str] = mapped_column(String(60))
    issuer: Mapped[str | None] = mapped_column(String(255))
    jurisdiction: Mapped[str | None] = mapped_column(String(50))
    authority_level: Mapped[str] = mapped_column(String(60))
    binding_status: Mapped[str] = mapped_column(String(30))
    official_uri: Mapped[str | None] = mapped_column(Text)

class SourceVersion(Base):
    __tablename__ = "source_version"
    __table_args__ = {"schema": "normative"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    source_id: Mapped[str] = mapped_column(ForeignKey("normative.normative_source.id"))
    version_label: Mapped[str] = mapped_column(String(120))
    official_uri: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

class Requirement(Base):
    __tablename__ = "requirement"
    __table_args__ = {"schema": "normative"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    source_version_id: Mapped[str] = mapped_column(ForeignKey("normative.source_version.id"))
    requirement_code: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(500))
    normative_statement: Mapped[str] = mapped_column(Text)
    source_reference: Mapped[str] = mapped_column(String(120))
    mandatory_level: Mapped[str] = mapped_column(String(30), default="MANDATORY")

class Rule(Base):
    __tablename__ = "rule"
    __table_args__ = {"schema": "rules"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    rule_code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    rule_type: Mapped[str] = mapped_column(String(60))
    target_type: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

class RuleVersion(Base):
    __tablename__ = "rule_version"
    __table_args__ = (
        UniqueConstraint("rule_id", "version", name="uq_rule_version"),
        {"schema": "rules"},
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    rule_id: Mapped[str] = mapped_column(ForeignKey("rules.rule.id"))
    version: Mapped[int] = mapped_column(Integer)
    expression: Mapped[dict] = mapped_column(JSON)
    output: Mapped[dict] = mapped_column(JSON)
    explanation_template: Mapped[str] = mapped_column(Text)
    source_reference: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

class RuleEvaluation(Base):
    __tablename__ = "rule_evaluation"
    __table_args__ = {"schema": "rules"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    rule_version_id: Mapped[str] = mapped_column(ForeignKey("rules.rule_version.id"))
    governance_case_id: Mapped[str] = mapped_column(ForeignKey("governance.governance_case.id"))
    subject_id: Mapped[str] = mapped_column(ForeignKey("core.governed_object.id"))
    input_snapshot: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    explanation: Mapped[str] = mapped_column(Text)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ClassificationAssessment(Base):
    __tablename__ = "classification_assessment"
    __table_args__ = {"schema": "governance"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    governance_case_id: Mapped[str] = mapped_column(ForeignKey("governance.governance_case.id"))
    subject_id: Mapped[str] = mapped_column(ForeignKey("core.governed_object.id"))
    dimension: Mapped[str] = mapped_column(String(80))
    outcome: Mapped[str] = mapped_column(String(120))
    source_rule_evaluation_id: Mapped[str] = mapped_column(ForeignKey("rules.rule_evaluation.id"))
    reasoning: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(30), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(30), default="CURRENT")

class Obligation(Base):
    __tablename__ = "obligation"
    __table_args__ = {"schema": "governance"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    governance_case_id: Mapped[str] = mapped_column(ForeignKey("governance.governance_case.id"))
    requirement_id: Mapped[str] = mapped_column(ForeignKey("normative.requirement.id"))
    subject_id: Mapped[str] = mapped_column(ForeignKey("core.governed_object.id"))
    workflow_status: Mapped[str] = mapped_column(String(30), default="PENDING")
    compliance_status: Mapped[str] = mapped_column(String(30), default="NOT_ASSESSED")

class GovernanceAction(Base):
    __tablename__ = "action"
    __table_args__ = {"schema": "governance"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    governance_case_id: Mapped[str] = mapped_column(ForeignKey("governance.governance_case.id"))
    action_type: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(30), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(30), default="OPEN")

class ActionObligation(Base):
    __tablename__ = "action_obligation"
    __table_args__ = {"schema": "governance"}
    action_id: Mapped[str] = mapped_column(ForeignKey("governance.action.id"), primary_key=True)
    obligation_id: Mapped[str] = mapped_column(ForeignKey("governance.obligation.id"), primary_key=True)

class GuidedQuestion(Base):
    __tablename__ = "guided_question"
    __table_args__ = {"schema": "ux"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    question_code: Mapped[str] = mapped_column(String(100), unique=True)
    section_code: Mapped[str] = mapped_column(String(80))
    plain_language_text: Mapped[str] = mapped_column(Text)
    why_we_ask: Mapped[str | None] = mapped_column(Text)
    answer_type: Mapped[str] = mapped_column(String(40))
    canonical_fact_path: Mapped[str] = mapped_column(String(200))
    sequence: Mapped[int] = mapped_column(Integer)

class QuestionResponse(Base):
    __tablename__ = "question_response"
    __table_args__ = {"schema": "ux"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    governance_case_id: Mapped[str] = mapped_column(ForeignKey("governance.governance_case.id"))
    question_id: Mapped[str] = mapped_column(ForeignKey("ux.guided_question.id"))
    answer: Mapped[dict] = mapped_column(JSON)
    answered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class FactProvenance(Base):
    __tablename__ = "fact_provenance"
    __table_args__ = {"schema": "audit"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(36))
    field_name: Mapped[str] = mapped_column(String(160))
    source_type: Mapped[str] = mapped_column(String(60))
    source_reference: Mapped[str | None] = mapped_column(String(255))
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    confidence: Mapped[str] = mapped_column(String(30), default="USER_DECLARED")

class AssessmentTemplate(Base):
    __tablename__ = "template"
    __table_args__ = {"schema": "assessment"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    template_code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    assessment_type: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str | None] = mapped_column(String(60))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

class Assessment(Base):
    __tablename__ = "assessment"
    __table_args__ = {"schema": "assessment"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    governance_case_id: Mapped[str] = mapped_column(ForeignKey("governance.governance_case.id"))
    template_id: Mapped[str] = mapped_column(ForeignKey("assessment.template.id"))
    subject_id: Mapped[str] = mapped_column(ForeignKey("core.governed_object.id"))
    owner_person_id: Mapped[str | None] = mapped_column(ForeignKey("org.person.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="IN_PROGRESS")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

class Risk(Base):
    __tablename__ = "risk"
    __table_args__ = {"schema": "risk"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    governed_object_id: Mapped[str] = mapped_column(ForeignKey("core.governed_object.id"))
    assessment_id: Mapped[str | None] = mapped_column(ForeignKey("assessment.assessment.id"))
    risk_code: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    cause: Mapped[str | None] = mapped_column(Text)
    risk_event: Mapped[str | None] = mapped_column(Text)
    potential_consequence: Mapped[str | None] = mapped_column(Text)
    risk_owner_id: Mapped[str | None] = mapped_column(ForeignKey("org.person.id"))
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    identified_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Impact(Base):
    __tablename__ = "impact"
    __table_args__ = {"schema": "risk"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    risk_id: Mapped[str] = mapped_column(ForeignKey("risk.risk.id"))
    affected_population_id: Mapped[str | None] = mapped_column(ForeignKey("ai.affected_population.id"))
    impact_type: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    polarity: Mapped[str] = mapped_column(String(20), default="NEGATIVE")
    magnitude: Mapped[str | None] = mapped_column(String(30))
    reversibility: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="CURRENT")

class RiskEvaluation(Base):
    __tablename__ = "risk_evaluation"
    __table_args__ = {"schema": "risk"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    risk_id: Mapped[str] = mapped_column(ForeignKey("risk.risk.id"))
    assessment_id: Mapped[str | None] = mapped_column(ForeignKey("assessment.assessment.id"))
    evaluation_stage: Mapped[str] = mapped_column(String(30))
    methodology_code: Mapped[str] = mapped_column(String(80), default="QUALITATIVE_V1")
    criteria_snapshot: Mapped[dict] = mapped_column(JSON)
    result: Mapped[str] = mapped_column(String(30))
    uncertainty: Mapped[str | None] = mapped_column(String(30))
    rationale: Mapped[str | None] = mapped_column(Text)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ControlObjective(Base):
    __tablename__ = "control_objective"
    __table_args__ = {"schema": "control"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    objective_code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    governance_domain: Mapped[str] = mapped_column(String(80))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

class Control(Base):
    __tablename__ = "control"
    __table_args__ = {"schema": "control"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    control_code: Mapped[str] = mapped_column(String(100), unique=True)
    objective_id: Mapped[str] = mapped_column(ForeignKey("control.control_objective.id"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    control_type: Mapped[str] = mapped_column(String(40), default="PREVENTIVE")
    execution_mode: Mapped[str] = mapped_column(String(30), default="MANUAL")
    frequency_type: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

class RequirementControlMapping(Base):
    __tablename__ = "requirement_mapping"
    __table_args__ = {"schema": "control"}
    requirement_id: Mapped[str] = mapped_column(ForeignKey("normative.requirement.id"), primary_key=True)
    control_id: Mapped[str] = mapped_column(ForeignKey("control.control.id"), primary_key=True)
    coverage: Mapped[str] = mapped_column(String(30), default="SUPPORTING")
    rationale: Mapped[str | None] = mapped_column(Text)

class RiskControlMapping(Base):
    __tablename__ = "risk_mapping"
    __table_args__ = {"schema": "control"}
    risk_id: Mapped[str] = mapped_column(ForeignKey("risk.risk.id"), primary_key=True)
    control_id: Mapped[str] = mapped_column(ForeignKey("control.control.id"), primary_key=True)
    coverage: Mapped[str] = mapped_column(String(30), default="SUPPORTING")
    rationale: Mapped[str | None] = mapped_column(Text)

class ControlImplementation(Base):
    __tablename__ = "control_implementation"
    __table_args__ = {"schema": "control"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    control_id: Mapped[str] = mapped_column(ForeignKey("control.control.id"))
    governed_object_id: Mapped[str] = mapped_column(ForeignKey("core.governed_object.id"))
    implementation_description: Mapped[str | None] = mapped_column(Text)
    owner_person_id: Mapped[str | None] = mapped_column(ForeignKey("org.person.id"))
    status: Mapped[str] = mapped_column(String(30), default="PLANNED")
    execution_mode: Mapped[str | None] = mapped_column(String(30))
    frequency: Mapped[str | None] = mapped_column(String(40))

class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = {"schema": "control"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(255))
    evidence_type: Mapped[str] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(Text)
    artifact_reference: Mapped[str | None] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    valid_until: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="CURRENT")

class ControlEvidence(Base):
    __tablename__ = "control_evidence"
    __table_args__ = {"schema": "control"}
    control_implementation_id: Mapped[str] = mapped_column(ForeignKey("control.control_implementation.id"), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("control.evidence.id"), primary_key=True)
    evidence_role: Mapped[str] = mapped_column(String(40), default="SUPPORTING")

class GovernanceGateResult(Base):
    __tablename__ = "gate_result"
    __table_args__ = {"schema": "governance"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    governance_case_id: Mapped[str] = mapped_column(ForeignKey("governance.governance_case.id"))
    gate_code: Mapped[str] = mapped_column(String(30))
    result: Mapped[str] = mapped_column(String(30))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    rationale: Mapped[str | None] = mapped_column(Text)
    blocking_reasons: Mapped[dict | None] = mapped_column(JSON)

class Decision(Base):
    __tablename__ = "decision"
    __table_args__ = {"schema": "governance"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    governance_case_id: Mapped[str] = mapped_column(ForeignKey("governance.governance_case.id"))
    subject_id: Mapped[str] = mapped_column(ForeignKey("core.governed_object.id"))
    decision_type: Mapped[str] = mapped_column(String(60))
    outcome: Mapped[str] = mapped_column(String(60))
    decision_authority_id: Mapped[str] = mapped_column(ForeignKey("org.person.id"))
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    rationale: Mapped[str | None] = mapped_column(Text)
    conditions: Mapped[dict | None] = mapped_column(JSON)
    valid_until: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="CURRENT")

class ApprovalBaseline(Base):
    __tablename__ = "approval_baseline"
    __table_args__ = {"schema": "governance"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    decision_id: Mapped[str] = mapped_column(ForeignKey("governance.decision.id"), unique=True)
    deployment_context_id: Mapped[str] = mapped_column(ForeignKey("ai.deployment_context.id"))
    system_snapshot: Mapped[dict] = mapped_column(JSON)
    classification_snapshot: Mapped[dict] = mapped_column(JSON)
    risk_snapshot: Mapped[dict] = mapped_column(JSON)
    control_snapshot: Mapped[dict] = mapped_column(JSON)
    evidence_snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    content_hash: Mapped[str | None] = mapped_column(String(128))

class MonitoringPlan(Base):
    __tablename__ = "monitoring_plan"
    __table_args__ = {"schema": "monitoring"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    deployment_context_id: Mapped[str] = mapped_column(ForeignKey("ai.deployment_context.id"))
    owner_person_id: Mapped[str] = mapped_column(ForeignKey("org.person.id"))
    purpose: Mapped[str] = mapped_column(Text)
    review_frequency: Mapped[str] = mapped_column(String(40), default="QUARTERLY")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MonitoringDefinition(Base):
    __tablename__ = "monitoring_definition"
    __table_args__ = {"schema": "monitoring"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    monitoring_plan_id: Mapped[str] = mapped_column(ForeignKey("monitoring.monitoring_plan.id"))
    name: Mapped[str] = mapped_column(String(255))
    monitoring_type: Mapped[str] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(Text)
    method: Mapped[str | None] = mapped_column(Text)
    frequency: Mapped[str] = mapped_column(String(40), default="MONTHLY")
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

class ThresholdRule(Base):
    __tablename__ = "threshold_rule"
    __table_args__ = {"schema": "monitoring"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    monitoring_definition_id: Mapped[str] = mapped_column(ForeignKey("monitoring.monitoring_definition.id"))
    operator: Mapped[str] = mapped_column(String(20))
    threshold_value: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(30), default="MEDIUM")
    breach_action: Mapped[str] = mapped_column(String(60), default="REASSESS")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

class Observation(Base):
    __tablename__ = "observation"
    __table_args__ = {"schema": "monitoring"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    monitoring_definition_id: Mapped[str] = mapped_column(ForeignKey("monitoring.monitoring_definition.id"))
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    value: Mapped[dict | None] = mapped_column(JSON)
    qualitative_result: Mapped[str | None] = mapped_column(Text)
    quality_status: Mapped[str] = mapped_column(String(30), default="VALID")
    threshold_status: Mapped[str] = mapped_column(String(30), default="NOT_EVALUATED")

class GovernanceEvent(Base):
    __tablename__ = "governance_event"
    __table_args__ = {"schema": "event"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    subject_id: Mapped[str] = mapped_column(ForeignKey("core.governed_object.id"))
    event_type: Mapped[str] = mapped_column(String(60))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source: Mapped[str | None] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(30), default="MEDIUM")
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="OPEN")

class ChangeEvent(Base):
    __tablename__ = "change_event"
    __table_args__ = {"schema": "event"}
    governance_event_id: Mapped[str] = mapped_column(ForeignKey("event.governance_event.id"), primary_key=True)
    change_type: Mapped[str] = mapped_column(String(80))
    old_state_reference: Mapped[dict | None] = mapped_column(JSON)
    new_state_reference: Mapped[dict | None] = mapped_column(JSON)
    materiality: Mapped[str] = mapped_column(String(40), default="UNDETERMINED")

class Incident(Base):
    __tablename__ = "incident"
    __table_args__ = {"schema": "event"}
    governance_event_id: Mapped[str] = mapped_column(ForeignKey("event.governance_event.id"), primary_key=True)
    incident_category: Mapped[str] = mapped_column(String(80))
    actual_harm: Mapped[str | None] = mapped_column(Text)
    potential_harm: Mapped[str | None] = mapped_column(Text)
    containment_status: Mapped[str] = mapped_column(String(40), default="OPEN")
    reportability_status: Mapped[str] = mapped_column(String(40), default="NOT_ASSESSED")

class Reassessment(Base):
    __tablename__ = "reassessment"
    __table_args__ = {"schema": "event"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    governance_case_id: Mapped[str] = mapped_column(ForeignKey("governance.governance_case.id"))
    trigger_event_id: Mapped[str] = mapped_column(ForeignKey("event.governance_event.id"))
    starting_domain: Mapped[str] = mapped_column(String(60))
    reason: Mapped[str] = mapped_column(Text)
    owner_person_id: Mapped[str | None] = mapped_column(ForeignKey("org.person.id"))
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    outcome: Mapped[str | None] = mapped_column(String(60))

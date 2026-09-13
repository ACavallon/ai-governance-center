from __future__ import annotations
from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def uid() -> str:
    return str(uuid.uuid4())

class LegalEntity(Base):
    __tablename__ = "legal_entity"
    __table_args__ = {"schema": "core"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    legal_name: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    entity_type: Mapped[str] = mapped_column(String(50))
    country_code: Mapped[str | None] = mapped_column(String(2))
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
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

class ResponsibleParty(Base):
    __tablename__ = "responsible_party"
    __table_args__ = {"schema": "org"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organisation_id: Mapped[str] = mapped_column(ForeignKey("org.organisation.legal_entity_id"))
    party_type: Mapped[str] = mapped_column(String(30))
    display_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

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
    business_owner_id: Mapped[str] = mapped_column(ForeignKey("org.responsible_party.id"))
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
    country_code: Mapped[str] = mapped_column(String(2))
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

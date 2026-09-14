from datetime import date
from pydantic import BaseModel, Field, field_validator


class AIUseCreate(BaseModel):
    name: str
    business_purpose: str
    business_process: str = "Other"
    owner_person_id: str
    system_name: str
    system_purpose: str
    supply_model: str = Field(pattern="^(third_party|internal|hybrid|unknown)$")
    supplier_name: str | None = None
    function: str
    decision_domain: str
    human_final_decision: bool
    affected_population: str
    countries: list[str]

    @field_validator("countries")
    @classmethod
    def normalize_countries(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(code.strip().upper() for code in value if code.strip()))


class PersonCreate(BaseModel):
    first_name: str
    last_name: str
    email: str | None = None
    employee_id: str | None = None
    job_title: str | None = None
    employment_type: str | None = None
    business_unit_id: str | None = None
    manager_person_id: str | None = None
    country_code: str | None = None
    authority_level: str | None = None

    @field_validator("country_code")
    @classmethod
    def normalize_country(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


class GroupCreate(BaseModel):
    name: str
    group_type: str = Field(pattern="^(TEAM|FUNCTION|COMMITTEE)$")
    owner_person_id: str | None = None
    description: str | None = None


class QualificationCreate(BaseModel):
    qualification_type: str
    status: str = "CURRENT"
    issued_at: date | None = None
    valid_until: date | None = None
    evidence_reference: str | None = None


class RulesCheckResult(BaseModel):
    case_id: str
    ai_use_id: str
    regulatory_profile: list[dict]
    actions: list[dict]

class RiskReviewInitialize(BaseModel):
    owner_person_id: str | None = None

class RiskUpdate(BaseModel):
    result: str = Field(pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    uncertainty: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH)$")
    rationale: str | None = None

class ControlImplementationUpdate(BaseModel):
    status: str = Field(pattern="^(PLANNED|IMPLEMENTED|EFFECTIVE|NOT_APPLICABLE)$")
    owner_person_id: str | None = None
    implementation_description: str | None = None

class EvidenceCreate(BaseModel):
    title: str
    evidence_type: str = Field(pattern="^(POLICY|PROCEDURE|TRAINING_RECORD|TEST_REPORT|SYSTEM_CONFIGURATION|LOG|CONTRACT|ATTESTATION|OTHER)$")
    description: str | None = None
    artifact_reference: str | None = None
    valid_until: date | None = None

class ApprovalDecisionCreate(BaseModel):
    decision_authority_id: str
    outcome: str = Field(pattern="^(APPROVED|APPROVED_WITH_CONDITIONS|REJECTED|DEFERRED)$")
    rationale: str | None = None
    conditions: list[str] = []
    valid_until: date | None = None

class ObservationCreate(BaseModel):
    value: float | int | str | None = None
    qualitative_result: str | None = None

class ChangeEventCreate(BaseModel):
    change_type: str
    description: str
    materiality: str = Field(default="UNDETERMINED", pattern="^(NON_MATERIAL|MATERIAL|POTENTIALLY_SUBSTANTIAL|SUBSTANTIAL|UNDETERMINED)$")
    old_state: dict | None = None
    new_state: dict | None = None

class IncidentCreate(BaseModel):
    incident_category: str
    description: str
    severity: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    actual_harm: str | None = None
    potential_harm: str | None = None

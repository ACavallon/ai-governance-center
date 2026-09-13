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

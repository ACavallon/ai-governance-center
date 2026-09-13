from pydantic import BaseModel, Field

class AIUseCreate(BaseModel):
    name: str
    business_purpose: str
    business_process: str = "Other"
    owner_name: str
    system_name: str
    system_purpose: str
    supply_model: str = Field(pattern="^(third_party|internal|hybrid|unknown)$")
    supplier_name: str | None = None
    function: str
    decision_domain: str
    human_final_decision: bool
    affected_population: str
    countries: list[str]

class RulesCheckResult(BaseModel):
    case_id: str
    ai_use_id: str
    regulatory_profile: list[dict]
    actions: list[dict]

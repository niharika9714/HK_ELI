"""Versioned public contracts. Identity never originates in an execution plan."""
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


def now():
    return datetime.now(timezone.utc).isoformat()


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Identity(Strict):
    id: str = Field(min_length=1,max_length=200)
    country: str = Field(pattern=r'^[A-Z]{2}$')
    line_of_business: str = Field(min_length=1,max_length=100)
    tableau_username: str = ''
    groups: list[str] = []
    permissions: list[str] = []
    resources: list[str] = []


class SkillMetadata(Strict):
    id: str
    version: str = '1.0.0'
    domain: str
    description: str
    use_when: list[str] = []
    do_not_use_when: list[str] = []
    examples: list[dict] = []
    limitations: list[str] = []
    permissions: list[str] = ['analytics.read']
    capabilities: list[str] = []
    source_modes: list[Literal['LIVE', 'MOCK']] = ['MOCK']
    timeout_seconds: float = 30
    retries: int = Field(default=0, ge=0, le=2)
    idempotent: bool = True
    cache_policy: str = 'none'
    service: str = 'analytics'
    input_schema: dict = {}
    output_schema: dict = {}


class TaskSpec(Strict):
    id: str = Field(pattern=r'^[a-zA-Z][a-zA-Z0-9_-]{0,49}$')
    skill_id: str
    skill_version: str = '1.0.0'
    parameters: dict[str, Any] = {}
    dependencies: list[str] = Field(default_factory=list, max_length=24)
    expected_output: str = 'SkillOutput'
    source_mode: Literal['LIVE','MOCK'] | None = None


class UserIntent(Strict):
    question: str
    analytical: bool = True
    domain: str = 'hk_eli'
    measures: list[str] = Field(default_factory=list,max_length=12)
    dimensions: list[str] = Field(default_factory=list,max_length=12)
    conditions: list[str] = Field(default_factory=list,max_length=12)


class SourceRequirement(Strict):
    resource_id: str
    grain: str
    source_mode: Literal['LIVE', 'MOCK']


class OutputSpecification(Strict):
    layout: Literal['side_by_side', 'stacked'] = 'stacked'
    formats: list[Literal['docx', 'pptx', 'pdf', 'xlsx']] = Field(default_factory=list, max_length=4)


class SourceAssessment(Strict):
    match: Literal['complete_match','partial_match','no_match']
    view_id: str | None = None
    reason: str = Field(max_length=1000)
    remaining_gaps: list[str] = Field(default_factory=list,max_length=12)
    task_ids: list[str] = Field(default_factory=list,max_length=24)


class RequestRequirement(Strict):
    id: str = Field(pattern=r'^[a-zA-Z][a-zA-Z0-9_-]{0,49}$')
    quote: str = Field(min_length=1,max_length=2000)
    kind: Literal['measure','dimension','condition','period','output','source','pricing_input','other']
    interpretation: str = Field(min_length=1,max_length=500)
    expected_value: Any = None


class ParameterBinding(Strict):
    task_id: str
    parameter_path: str = Field(pattern=r'^/',max_length=300)
    target: Literal['parameters','task'] = 'parameters'


class RequirementCoverage(Strict):
    requirement_id: str
    status: Literal['satisfied','unresolved']
    task_ids: list[str] = Field(default_factory=list,max_length=24)
    bindings: list[ParameterBinding] = Field(default_factory=list,max_length=24)
    reason: str = Field(min_length=1,max_length=500)


class ExecutionPlan(Strict):
    version: str = '1.0'
    intent: UserIntent
    tasks: list[TaskSpec] = Field(default_factory=list,max_length=24)
    output: OutputSpecification = Field(default_factory=OutputSpecification)
    source_assessments: list[SourceAssessment] = Field(default_factory=list,max_length=12)
    requirements: list[RequestRequirement] = Field(default_factory=list,max_length=24)
    coverage: list[RequirementCoverage] = Field(default_factory=list,max_length=24)


class PlanValidationResult(Strict):
    valid: bool
    errors: list[str] = []


class EvidenceRecord(Strict):
    id: str
    source_type: str
    source_mode: Literal['LIVE', 'MOCK']
    source_id: str
    source_version: str
    retrieved_at: str = Field(default_factory=now)
    as_of: str
    filters: dict = {}
    authorization_scope: list[str]
    grain: str
    metric_version: str = '1.0'
    value: str | None = None
    unit: str = 'number'
    input_evidence_ids: list[str] = []
    calculation_id: str
    classification: str = 'restricted'
    warnings: list[str] = []
    metric: str = ''
    statistic: str = 'observed'
    dimensions: dict[str,str] = {}


class Claim(Strict):
    text: str = Field(max_length=1200)
    evidence_ids: list[str] = Field(min_length=1, max_length=12)


class Narrative(Strict):
    summary: list[Claim] = Field(default_factory=list, max_length=5)
    insights: list[Claim] = Field(default_factory=list, max_length=6)
    recommended_actions: list[Claim] = Field(default_factory=list, max_length=4)


class SkillOutput(Strict):
    status: Literal['complete', 'partial', 'unavailable'] = 'complete'
    data: dict = {}
    evidence: list[EvidenceRecord] = []
    visualizations: list[dict] = []
    warnings: list[str] = []


class Request(Strict):
    question: str = Field(min_length=1, max_length=2000)
    dashboards: list[str] = Field(default_factory=list, max_length=10)
    # Explicit typed plans are useful for integration/benchmarks; execution reauthorizes every task.
    plan: ExecutionPlan | None = None
    formats: list[Literal['docx', 'pptx', 'pdf', 'xlsx']] = []
    conversation_id: str | None = Field(default=None,pattern=r'^[a-f0-9]{32}$')
    context_turn_ids: list[str] = Field(default_factory=list,max_length=20)
    template_id: str | None = Field(default=None,pattern=r'^[a-z][a-z0-9-]{0,79}$')


class QuoteInput(Strict):
    entity: str = Field(default='SYNTHETIC', max_length=80)
    product: str = Field(default='ELI', max_length=80)
    issue_date_lag: int = Field(default=2, ge=0, le=30)
    currency: Literal['HKD', 'USD'] = 'HKD'
    basket: list[str] = Field(min_length=1, max_length=5)
    tenor_months: int = Field(ge=1, le=36)
    strike: float = Field(default=90, gt=0, le=150)
    coupon: float = Field(default=8, ge=0, le=100)
    ki_type: str = 'European'
    ki_level: float = Field(default=60, gt=0, le=100)
    ko_type: str = 'Daily'
    ko_level: float = Field(default=100, gt=0, le=150)
    coupon_frequency: Literal['monthly', 'quarterly'] = 'monthly'
    price: float = Field(default=100, gt=0, le=200)
    solve_target: Literal['coupon', 'strike'] = 'coupon'

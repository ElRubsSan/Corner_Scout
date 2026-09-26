from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ErrorResponse(Contract):
    detail: str | list[dict[str, object]]


class Team(Contract):
    name: str


class Match(Contract):
    match_id: int
    match_date: str
    kick_off: str
    home_team: str
    away_team: str


class RunRequest(Contract):
    rival: str = Field(min_length=1, max_length=100)
    cutoff_date: date | None = None
    target_match_id: int | None = Field(default=None, gt=0)
    analyst: str | None = Field(default=None, max_length=100)
    expected_match_ids: list[int] | None = Field(default=None, min_length=8, max_length=8)

    @model_validator(mode="after")
    def one_cutoff(self):
        if (self.cutoff_date is None) == (self.target_match_id is None):
            raise ValueError("Indique fecha o partido objetivo, exclusivamente uno")
        return self


class Run(Contract):
    run_id: str
    rival: str
    analyst: str | None
    cutoff_date: str
    matches: list[Match]
    dataset_version: str
    canonical_runs: dict[str, str] = Field(default_factory=dict)


class Corner(Contract):
    match_id: int
    event_id: str
    player: str
    x: float
    y: float
    end_x: float
    end_y: float
    side: str
    delivery: str
    zone: str
    height: str
    shot_within_15s: bool | None
    xg: float | None
    valid_sequence: bool
    spatial_valid: bool
    end_reason: str
    shot_ids: list[str]
    restart_ids: list[str]
    possession_change_ids: list[str]
    cluster: int | None = None


class Group(Contract):
    label: str
    count: int


class Summary(Contract):
    rival: str
    cutoff_date: str
    matches: int
    corners: int
    evaluable_corners: int
    excluded_corners: int
    shots: int
    scr15: float | None = Field(ge=0, le=1)
    xg_per_corner: float | None = Field(ge=0)
    probability: float | None = Field(ge=0, le=1)
    probability_method: str
    players: list[Group]
    sides: list[Group]
    deliveries: list[Group]
    zones: list[Group]


class Pattern(Contract):
    cluster: int
    count: int
    evaluable: int
    scr15: float | None
    xg_per_corner: float | None
    dominant_zone: str
    main_taker: str
    example_event_ids: list[str]
    snapshot: str


class Quality(Contract):
    provider: str = "StatsBomb Open Data"
    season: str = "LaLiga 2015/16"
    competition_id: int = 11
    season_id: int = 27
    processed_at: str
    source_manifest_sha256: str
    rule_version: str
    coverage_matches: int
    coverage_events: int
    excluded_sequences: int
    excluded_spatial: int
    limitations: list[str]


class ObjectiveWinner(Contract):
    objective: str
    winner: str
    modeled: bool
    justification: str


class TemporalMetric(Contract):
    objective: str
    window: str
    role: str
    model: str
    n: int
    positive: float | None = None
    prevalence: float | None = None
    average_precision: float | None = None
    brier: float | None = None
    log_loss: float | None = None
    calibration_gap: float | None = None
    roc_auc: float | None = None
    mae: float | None = None
    poisson_deviance: float | None = None


class ModelEvaluation(Contract):
    objective_winners: list[ObjectiveWinner]
    temporal_metrics: list[TemporalMetric]


class ModelResult(Contract):
    served: str
    probability: float | None
    evaluation_scope: str
    evaluations: ModelEvaluation


class Evidence(Contract):
    id: str
    description: str
    value: str
    event_ids: list[str] = Field(default_factory=list)


class ReportInput(Contract):
    rival: str
    cutoff_date: str
    matches: list[Match]
    summary: Summary
    patterns: list[Pattern]
    evidence: list[Evidence]
    limitations: list[str]


class Claim(Contract):
    text: str = Field(min_length=1, max_length=1500)
    evidence_ids: list[str] = Field(min_length=1)


class Narrative(Contract):
    observations: list[Claim] = Field(min_length=1, max_length=8)
    recommendations: list[Claim] = Field(max_length=5)


class Report(Contract):
    mode: Literal["deterministic", "openai"]
    fallback_reason: str | None
    plan: list[str]
    input: ReportInput
    narrative: Narrative
    sources: list[str]


class AgentRequest(Contract):
    question: str = Field(min_length=1, max_length=1000)


class AgentTrace(Contract):
    kind: Literal["tool"] = "tool"
    tool: str
    arguments: dict[str, object]
    arguments_validated: bool
    status: Literal["ok", "error"]
    result_summary: dict[str, object] | None = None
    error_type: str | None = None
    error_code: str | None = None
    latency_ms: float = Field(ge=0)


class AgentResponse(Contract):
    mode: Literal["deterministic", "openai"]
    fallback_reason: str | None = None
    status: Literal["answered", "out_of_scope", "error"]
    answer: str
    evidence_ids: list[str]
    tool_calls: int = Field(ge=0, le=4)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    traces: list[AgentTrace] = Field(default_factory=list)

"""
LangGraph Shared State schema and all Pydantic output models.
This Denifes the contract between every agent node in the system.
"""
from __future__ import annotations
import operator
from datetime import datetime, timezone 
from enum import Enum
from typing import Annotated, List, Literal, Optional, TypedDict, Dict, Any, Union
from pydantic import BaseModel, Field, RootModel

# Enums
class ClaimType(str, Enum):
    EMPIRICAL = "empirical"
    THEORETICAL = "theoretical"
    EXPERIMENTAL= "experimental"
    COMPUTATIONAL = "computational"
    METHODOLOGICAL = "methodological"

class EvidenceStrength(str, Enum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    INFERRED = "inferred"

class ReproVerdict(str, Enum):
    REPRODUCIBLE = "reproducible"
    PARTIALLY_REPRODUCIBLE = "partially_reproducible"
    NOT_REPRODUCIBLE = "not_reproducible"
    INSUFFICIENT_INFO = "insufficient_information"

class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

# Core data models
class PaperMetadata(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    publication_date: Optional[str] = None
    journal: Optional[str] = None 
    keywords: list[str] = Field(default_factory=list)

class Claim(BaseModel):
    """A testable scientific claim extracted from the paper."""
    claim_id: str
    claim_text: str
    claim_type: ClaimType
    section_source: str  # which section this came from
    evidence_strength: EvidenceStrength
    supporting_text: str = ""  # original text from paper  
    numerical_values: list[str] = Field(default_factory=list)
    controls_present: Optional[bool] = None
    blinding_reported: Optional[bool] = None
    biological_replicates_stated: Optional[bool] = None
    qrp_flags: list[str] = Field(default_factory=list)
    confidence: str = ""

#Agent Result Models
class ExtractionResult(BaseModel):
    paper_section:str
    research_paradigm: str
    subdiscipline: str 
    total_claims_extracted: int 
    claims: list[Claim] 
    
class DimensionScore(BaseModel):
    """Score for a single reproducibility dimension."""
    dimension: str
    score: float = Field(ge=0, le=100)
    reasoning: str
    evidence: str = ""

class MethodologyVerdict(BaseModel):
    """Result from the Repro Checker agent (Gemini 2.5 Pro)."""
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    overall_score: float = Field(ge=0, le=100, default=0)
    summary: str = ""
    missing_details: list[str] = Field(default_factory=list)

class StatisticalClaim(BaseModel):
    """A statistical claim extracted from the paper.

    Fields are aligned with the JSON schema requested by the statistical
    extraction prompt. Both raw and parsed p-value fields are kept to
    preserve formatting from the paper while enabling numeric checks.

    For papers that report only descriptive statistics (review articles,
    population studies, meta-analyses), the descriptive_* and proportion
    fields capture percentages, medians, IQR, and similar metrics.
    """
    claim_id: str = ""
    # test name (legacy) and explicit test type expected by the prompt
    test_name: Optional[str] = None
    test_type: Optional[str] = None

    # Variance reporting (SD / SEM / Not Reported)
    variance_metric: Optional[str] = None

    # Test statistic details
    test_statistic_type: Optional[str] = None
    test_statistic_value: Optional[float] = None

    # p-value: numeric parsed value (if available) and raw reported string
    p_value: Optional[float] = None
    reported_p_value: Optional[str] = None

    # Degrees of freedom may be reported as a string or as an array (e.g., [2, 27])
    degrees_of_freedom: Optional[Union[str, List[int]]] = None

    confidence_interval: Optional[str] = None
    effect_size: Optional[float] = None
    stated_sample_size_n: Optional[int] = None
    section: str = ""

    # --- Descriptive / review-paper statistics ---
    # Free-text value exactly as reported (e.g., "82.6%", "median 2")
    descriptive_value: Optional[str] = None
    # Metric type: proportion, percentage, count, median, IQR, mean, range, score
    descriptive_metric: Optional[str] = None
    # Central-tendency measure if applicable (mean / median)
    central_tendency: Optional[str] = None
    # Spread measure and value (e.g., "IQR", "P25-P75")
    spread_metric: Optional[str] = None
    spread_value: Optional[str] = None
    # Proportion as a string, e.g., "38/46"
    proportion: Optional[str] = None
    # Brief context explaining what the number refers to
    context: Optional[str] = None

class StatisticalExtractionResult(RootModel[List[StatisticalClaim]]):
    """
    Structured output from the Nemotron LLM for statistical claim extraction.
    The statistical prompt produces a top-level JSON array of claim objects.
    """

class StatsVerdict(BaseModel):
    """Result from the Stats Agent (Gemini Flash + scipy)."""
    statistical_claims: list[StatisticalClaim] = Field(default_factory=list)
    p_hacking_risk: float = Field(ge=0, le=1, default=0)
    power_adequate: Optional[bool] = None
    test_selection_appropriate: Optional[bool] = None
    overall_score: float = Field(ge=0, le=100, default=0)
    summary: str = ""
    flags: list[str] = Field(default_factory=list)



#Tool Calling Agent Models
class ToolCall(BaseModel):
    """A single tool invocation planned by the tool calling agent."""
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""

class ToolCallResult(BaseModel):
    """Result of a single tool execution."""
    tool_name: str
    success: bool = True
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0

class ToolCallingPlan(BaseModel):
    """The LLM's plan for which tools to call."""
    data_understanding: str = ""  # what the LLM thinks the data is
    source_agent: str = ""        # which agent produced this data
    tool_calls: List[ToolCall] = Field(default_factory=list)

class ToolAgentResponse(BaseModel):
    """Final response from the Tool Calling Agent after tool execution."""
    plan: ToolCallingPlan = Field(default_factory=ToolCallingPlan)
    tool_results: List[ToolCallResult] = Field(default_factory=list)
    synthesis: str = ""  # LLM's summary after seeing tool results
    flags: List[str] = Field(default_factory=list)


class LiteratureEvidence(BaseModel):
    """Evidence from related papers via Agent Builder RAG."""
    source_paper: str
    relevant_text: str
    stance: Literal["supporting", "contradicting", "neutral"]
    confidence: float = Field(ge=0, le=1)
    claim_id: str = ""


class CodeVerdict(BaseModel):
    """Result from the GitLab Sandbox agent."""
    repo_url: str = ""
    runtime_detected: str = ""
    has_dockerfile: bool = False
    has_pinned_deps: bool = False
    has_tests: bool = False
    ci_pipeline_status: PipelineStatus = PipelineStatus.SKIPPED
    pipeline_url: str = ""
    reproduction_delta: Optional[float] = None  # diff between paper & CI outputs
    overall_score: float = Field(ge=0, le=100, default=0)
    summary: str = ""
    logs_excerpt: str = ""


class WetlabVerdict(BaseModel):
    """Result from the Wet Lab agent."""
    reagents_verified: int = 0
    reagents_total: int = 0
    compounds_found: list[str] = Field(default_factory=list)
    compounds_missing: list[str] = Field(default_factory=list)
    overall_score: float = Field(ge=0, le=100, default=0)
    summary: str = ""


class Contradiction(BaseModel):
    """A contradiction detected in the knowledge graph."""
    subject: str
    predicate_a: str
    object_a: str
    predicate_b: str
    object_b: str
    source_a: str = ""
    source_b: str = ""
    severity: Literal["low", "medium", "high"] = "medium"


class AgentResult(BaseModel):
    """Generic wrapper for any agent's output — used for fan-in aggregation."""
    agent_name: str
    score: float = Field(ge=0, le=100, default=0)
    confidence: float = Field(ge=0, le=1, default=0)
    summary: str = ""
    details: dict = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AuditEntry(BaseModel):
    """An entry in the audit trail (logged to Cloud Logging)."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent: str
    action: str
    details: str = ""
    latency_ms: Optional[float] = None

#Final Report Model
class ClaimVerdict(BaseModel):
    """Per-claim reproducibility verdict."""
    claim: Claim
    verdict: ReproVerdict
    score: float = Field(ge=0, le=100)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    reasoning: str = ""


class MethodologyAssessment(BaseModel):
    """Section of the final report covering methodology."""
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    overall_score: float = Field(ge=0, le=100, default=0)
    narrative: str = ""


class StatisticalAssessment(BaseModel):
    """Section of the final report covering statistics."""
    claims_analyzed: int = 0
    p_hacking_risk: float = 0
    power_adequate: Optional[bool] = None
    overall_score: float = Field(ge=0, le=100, default=0)
    narrative: str = ""


class DataAvailability(BaseModel):
    """Section of the final report covering data/code availability."""
    data_accessible: Optional[bool] = None
    code_accessible: Optional[bool] = None
    repo_url: str = ""
    overall_score: float = Field(ge=0, le=100, default=0)
    narrative: str = ""


class LiteratureConsistency(BaseModel):
    """Section of the final report covering literature cross-referencing."""
    papers_analyzed: int = 0
    supporting_count: int = 0
    contradicting_count: int = 0
    overall_score: float = Field(ge=0, le=100, default=0)
    narrative: str = ""


class ReproducibilityReport(BaseModel):
    """The final structured reproducibility report — the system's primary output."""
    paper_id: str
    paper_title: str
    overall_verdict: ReproVerdict
    overall_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)

    methodology_assessment: MethodologyAssessment = Field(
        default_factory=MethodologyAssessment
    )
    statistical_assessment: StatisticalAssessment = Field(
        default_factory=StatisticalAssessment
    )
    data_availability: DataAvailability = Field(default_factory=DataAvailability)
    code_assessment: Optional[CodeVerdict] = None
    literature_consistency: LiteratureConsistency = Field(
        default_factory=LiteratureConsistency
    )

    claims: list[ClaimVerdict] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    audit_trail: list[AuditEntry] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

# LangGraph Shared State
class ReprCheckState(TypedDict):
    """
    The shared state for the LangGraph orchestrator.
    Every node reads from and writes to this state.
    `agent_results` uses Annotated[list, operator.add] for parallel fan-in.
    """
    # Input
    file_path:str 
    paper_id: str
    raw_text: str
    sections: dict  # {section_name: text}
    metadata: dict  # PaperMetadata as dict

    #  Extraction
    claims: list[Claim] # list of Claim objects
    paper_meta: dict #LLM output : research paradigm, subsdiscipline, paper section.
    github_url: str

    # Statistics Agent Output
    statistical_claims: list[StatisticalClaim]
    extracted_statistical_values: Dict[str, List[Any]]

    # Routing
    active_agents: list  # which agents to activate
    paper_type: str  # "computational", "experimental", "theoretical", etc.

    #  Agent Results (fan-in via operator.add)
    agent_results: Annotated[list, operator.add]
    methodology_verdict: dict
    stats_verdict: dict
    code_verdict: dict
    literature_evidence: list
    kg_contradictions: list
    wetlab_verdict: dict

    # Tool Calling Agent Output
    tool_call_plan: list          # the LLM's tool selection plan
    tool_execution_results: list  # raw results from each tool execution
    tool_agent_summary: str       # final synthesized summary from the agent

    # Aggregation 
    retry_count: int
    confidence_score: float

    # Output 
    final_report: dict  # ReproducibilityReport as dict
    audit_trail: Annotated[list, operator.add]
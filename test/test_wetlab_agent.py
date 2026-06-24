"""
Tests for the Wet Lab Agent and Reproducibility Evaluator.
Covers:
 - state.py              (new Pydantic models: PaperType, ReagentInfo, ProtocolDetail, etc.)
 - wet_lab_prompt.py      (prompt templates)
 - wetlab_agent.py        (node function with mocked LLM)
 - reproducibility_evaluator.py (node function with mocked LLM)
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))



#  State Models — New Pydantic models


class TestPaperType:
    """Tests for the PaperType enum."""

    def test_all_values_exist(self):
        from Agent.state import PaperType
        expected = [
            "quantitative_experimental", "omics", "methodological",
            "clinical_translational", "computational_bioinformatics",
            "review_meta_analysis", "hybrid",
        ]
        actual = [e.value for e in PaperType]
        assert set(expected) == set(actual)

    def test_enum_string_comparison(self):
        from Agent.state import PaperType
        assert PaperType.OMICS == "omics"
        assert PaperType.HYBRID.value == "hybrid"


class TestReagentInfo:
    """Tests for the ReagentInfo model."""

    def test_creation_with_all_fields(self):
        from Agent.state import ReagentInfo
        r = ReagentInfo(
            name="Anti-β-actin antibody",
            category="antibody",
            identifier="RRID:AB_476743",
            vendor="Sigma-Aldrich",
            concentration="1:5000",
        )
        assert r.name == "Anti-β-actin antibody"
        assert r.category == "antibody"
        assert r.identifier == "RRID:AB_476743"
        assert r.verified is None

    def test_creation_minimal(self):
        from Agent.state import ReagentInfo
        r = ReagentInfo(name="DMSO", category="chemical")
        assert r.name == "DMSO"
        assert r.identifier is None
        assert r.vendor is None
        assert r.concentration is None

    def test_serialization(self):
        from Agent.state import ReagentInfo
        r = ReagentInfo(name="HeLa cells", category="cell_line", identifier="RRID:CVCL_0030")
        d = r.model_dump()
        assert isinstance(d, dict)
        assert d["name"] == "HeLa cells"
        serialized = json.dumps(d)
        assert "RRID:CVCL_0030" in serialized


class TestProtocolDetail:
    """Tests for the ProtocolDetail model."""

    def test_creation(self):
        from Agent.state import ProtocolDetail
        p = ProtocolDetail(
            technique="Western blot",
            description="Proteins separated on 10% SDS-PAGE",
            parameters_reported=["gel percentage: 10%", "blocking: 5% BSA"],
            parameters_missing=["transfer voltage", "exposure time"],
            reference_protocol="Smith et al. 2020",
            assessment="Core steps described but transfer conditions missing.",
        )
        assert p.technique == "Western blot"
        assert len(p.parameters_reported) == 2
        assert len(p.parameters_missing) == 2
        assert p.reference_protocol == "Smith et al. 2020"

    def test_defaults(self):
        from Agent.state import ProtocolDetail
        p = ProtocolDetail(technique="PCR", description="Standard PCR")
        assert p.parameters_reported == []
        assert p.parameters_missing == []
        assert p.reference_protocol is None
        assert p.assessment == ""


class TestPaperClassification:
    """Tests for the PaperClassification model."""

    def test_creation(self):
        from Agent.state import PaperClassification
        pc = PaperClassification(
            primary_type="quantitative_experimental",
            secondary_type=None,
            reasoning="Controlled drug treatment experiments",
            key_indicators=["ANOVA", "Western blot", "dose-response"],
            experimental_techniques=["Western blot", "MTT assay"],
        )
        assert pc.primary_type == "quantitative_experimental"
        assert pc.secondary_type is None
        assert len(pc.key_indicators) == 3

    def test_hybrid_paper(self):
        from Agent.state import PaperClassification
        pc = PaperClassification(
            primary_type="omics",
            secondary_type="quantitative_experimental",
            reasoning="RNA-seq with qPCR validation",
        )
        assert pc.secondary_type == "quantitative_experimental"

    def test_serialization(self):
        from Agent.state import PaperClassification
        pc = PaperClassification(
            primary_type="methodological",
            reasoning="New protocol paper",
        )
        d = pc.model_dump()
        assert d["primary_type"] == "methodological"
        json.dumps(d)  # should not raise


class TestWetlabVerdict:
    """Tests for the expanded WetlabVerdict model."""

    def test_creation_with_all_fields(self):
        from Agent.state import (
            WetlabVerdict, PaperClassification, ReagentInfo, ProtocolDetail,
        )
        v = WetlabVerdict(
            classification=PaperClassification(
                primary_type="quantitative_experimental",
                reasoning="Experimental paper",
            ),
            reagents=[
                ReagentInfo(name="DMSO", category="chemical"),
                ReagentInfo(name="Anti-CD20", category="antibody", identifier="RRID:AB_123"),
            ],
            reagents_with_identifiers=1,
            reagents_total=2,
            protocols=[
                ProtocolDetail(technique="ELISA", description="Standard ELISA"),
            ],
            positive_controls_present=True,
            negative_controls_present=True,
            biological_replicates=3,
            blinding_reported=False,
            methodology_assessment="Solid methodology with minor gaps.",
            strengths=["Good controls"],
            weaknesses=["No blinding"],
            flags=["Missing power analysis"],
            summary="Moderately reproducible.",
        )
        assert v.reagents_total == 2
        assert v.reagents_with_identifiers == 1
        assert len(v.protocols) == 1
        assert v.positive_controls_present is True
        assert len(v.flags) == 1

    def test_defaults(self):
        from Agent.state import WetlabVerdict
        v = WetlabVerdict()
        assert v.classification is None
        assert v.reagents == []
        assert v.reagents_total == 0
        assert v.protocols == []
        assert v.positive_controls_present is None
        assert v.summary == ""

    def test_serialization(self):
        from Agent.state import WetlabVerdict, ReagentInfo
        v = WetlabVerdict(
            reagents=[ReagentInfo(name="test", category="chemical")],
            reagents_total=1,
            summary="test summary",
        )
        d = v.model_dump()
        serialized = json.dumps(d)
        assert "test summary" in serialized


class TestWetlabExtractionResult:
    """Tests for the WetlabExtractionResult structured output model."""

    def test_creation(self):
        from Agent.state import WetlabExtractionResult, PaperClassification
        result = WetlabExtractionResult(
            classification=PaperClassification(
                primary_type="omics",
                reasoning="RNA-seq study",
            ),
            data_deposited_geo_sra=True,
            accession_numbers=["GSE12345"],
            summary="Omics data deposited.",
        )
        assert result.classification.primary_type == "omics"
        assert result.data_deposited_geo_sra is True
        assert "GSE12345" in result.accession_numbers

    def test_serialization_roundtrip(self):
        from Agent.state import WetlabExtractionResult, PaperClassification, ReagentInfo
        result = WetlabExtractionResult(
            classification=PaperClassification(primary_type="methodological", reasoning="test"),
            reagents=[ReagentInfo(name="Taq", category="enzyme")],
            summary="test",
        )
        d = result.model_dump()
        roundtrip = WetlabExtractionResult(**d)
        assert roundtrip.classification.primary_type == "methodological"
        assert roundtrip.reagents[0].name == "Taq"


class TestReproducibilityEvaluation:
    """Tests for the ReproducibilityEvaluation model."""

    def test_creation(self):
        from Agent.state import ReproducibilityEvaluation
        e = ReproducibilityEvaluation(
            verdict="partially_reproducible",
            confidence="medium",
            methodology_rigor="Methods are adequately described with some gaps.",
            statistical_validity="Appropriate statistical tests used.",
            reagent_transparency="Most reagents identified with catalog numbers.",
            protocol_completeness="Key steps described but some parameters missing.",
            data_availability="Raw data not deposited.",
            controls_and_design="Controls present, no blinding reported.",
            strengths=["Good controls", "Appropriate statistics"],
            weaknesses=["No raw data", "Missing protocol details"],
            critical_gaps=["No code availability"],
            recommendations=["Deposit raw data", "Add protocol to protocols.io"],
            overall_narrative="The paper is partially reproducible.",
        )
        assert e.verdict == "partially_reproducible"
        assert e.confidence == "medium"
        assert len(e.strengths) == 2
        assert len(e.critical_gaps) == 1

    def test_defaults(self):
        from Agent.state import ReproducibilityEvaluation
        e = ReproducibilityEvaluation(verdict="insufficient_information", confidence="low")
        assert e.methodology_rigor == ""
        assert e.strengths == []
        assert e.overall_narrative == ""

    def test_serialization(self):
        from Agent.state import ReproducibilityEvaluation
        e = ReproducibilityEvaluation(
            verdict="reproducible",
            confidence="high",
            overall_narrative="Fully reproducible.",
        )
        d = e.model_dump()
        serialized = json.dumps(d)
        assert "reproducible" in serialized


#  Prompt Templates

class TestWetlabPromptTemplates:
    """Tests for the wet lab prompt templates."""

    def test_wetlab_system_prompt_exists(self):
        from Agent.prompts.wet_lab_prompt import WETLAB_AGENT_SYSTEM
        assert len(WETLAB_AGENT_SYSTEM) > 200
        assert "quantitative_experimental" in WETLAB_AGENT_SYSTEM
        assert "omics" in WETLAB_AGENT_SYSTEM
        assert "methodological" in WETLAB_AGENT_SYSTEM

    def test_wetlab_human_prompt_exists(self):
        from Agent.prompts.wet_lab_prompt import WETLAB_AGENT_HUMAN
        assert len(WETLAB_AGENT_HUMAN) > 200
        assert "{extracted_claims}" in WETLAB_AGENT_HUMAN
        assert "{raw_text}" in WETLAB_AGENT_HUMAN

    def test_wetlab_human_prompt_format_works(self):
        """The .format() call should not raise."""
        from Agent.prompts.wet_lab_prompt import WETLAB_AGENT_HUMAN
        formatted = WETLAB_AGENT_HUMAN.format(
            extracted_claims="[test claims]",
            raw_text="test raw text",
        )
        assert "[test claims]" in formatted
        assert "test raw text" in formatted

    def test_eval_system_prompt_exists(self):
        from Agent.prompts.wet_lab_prompt import REPRODUCIBILITY_EVAL_SYSTEM
        assert len(REPRODUCIBILITY_EVAL_SYSTEM) > 200
        assert "reproducible" in REPRODUCIBILITY_EVAL_SYSTEM
        assert "partially_reproducible" in REPRODUCIBILITY_EVAL_SYSTEM
        assert "not_reproducible" in REPRODUCIBILITY_EVAL_SYSTEM

    def test_eval_human_prompt_exists(self):
        from Agent.prompts.wet_lab_prompt import REPRODUCIBILITY_EVAL_HUMAN
        assert "{evidence_json}" in REPRODUCIBILITY_EVAL_HUMAN

    def test_eval_human_prompt_format_works(self):
        from Agent.prompts.wet_lab_prompt import REPRODUCIBILITY_EVAL_HUMAN
        formatted = REPRODUCIBILITY_EVAL_HUMAN.format(
            evidence_json="{{test evidence}}",
        )
        assert "test evidence" in formatted



#  Wetlab Agent Node (mocked LLM)

class TestWetlabAgentNode:
    """Tests for the wetlab_agent_node with mocked LLM calls."""

    def _mock_state(self):
        """Build a realistic state dict."""
        from Agent.state import Claim, ClaimType, EvidenceStrength
        return {
            "raw_text": "Treatment with 10µM Compound X reduced HeLa cell viability by 40%...",
            "claims": [
                Claim(
                    claim_id="claim_1",
                    claim_text="Compound X reduced cell viability by 40%",
                    claim_type=ClaimType.EXPERIMENTAL,
                    section_source="results",
                    evidence_strength=EvidenceStrength.DIRECT,
                    numerical_values=["40%", "10µM"],
                    controls_present=True,
                ),
            ],
            "paper_meta": {"research_paradigm": "wet_lab", "subdiscipline": "oncology"},
        }

    def test_empty_state_returns_early(self):
        """Node should return gracefully when raw_text and claims are empty."""
        from Agent.nodes.wetlab_agent import wetlab_agent_node
        state = {}
        result = wetlab_agent_node(state)
        assert result["paper_classification"] == {}
        assert result["paper_type"] == "unknown"
        assert result["wetlab_verdict"] == {}

    @patch("Agent.nodes.wetlab_agent.get_nemotron3super")
    def test_node_with_mocked_llm(self, mock_get_nemotron):
        """Full node test with mocked LLM."""
        from Agent.nodes.wetlab_agent import wetlab_agent_node
        from Agent.state import (
            WetlabExtractionResult, PaperClassification,
            ReagentInfo, ProtocolDetail,
        )

        mock_response = WetlabExtractionResult(
            classification=PaperClassification(
                primary_type="quantitative_experimental",
                reasoning="Controlled cell viability experiments",
                key_indicators=["dose-response", "cell viability assay"],
                experimental_techniques=["MTT assay", "cell culture"],
            ),
            reagents=[
                ReagentInfo(name="Compound X", category="chemical", concentration="10µM"),
                ReagentInfo(name="HeLa cells", category="cell_line", identifier="RRID:CVCL_0030"),
            ],
            protocols=[
                ProtocolDetail(
                    technique="MTT assay",
                    description="Cell viability measured after 48h treatment",
                    parameters_reported=["concentration: 10µM", "duration: 48h"],
                    parameters_missing=["cell passage number", "seeding density"],
                    assessment="Key parameters reported but missing seeding details.",
                ),
            ],
            positive_controls_present=True,
            negative_controls_present=True,
            biological_replicates=3,
            blinding_reported=False,
            methodology_assessment="Standard cell viability assay with adequate controls.",
            strengths=["Biological triplicates", "Both controls present"],
            weaknesses=["No blinding", "Missing seeding density"],
            flags=["Sample size not justified"],
            summary="Moderately reproducible experimental setup.",
        )

        # Wire up the mock
        mock_llm_structured = MagicMock()
        mock_llm_structured.invoke.return_value = mock_response

        mock_nemotron_instance = MagicMock()
        mock_nemotron_instance.with_structured_output.return_value = mock_llm_structured

        mock_get_nemotron.return_value = mock_nemotron_instance

        state = self._mock_state()
        result = wetlab_agent_node(state)

        # Verify structure
        assert "paper_classification" in result
        assert "paper_type" in result
        assert "wetlab_verdict" in result

        # Verify classification
        assert result["paper_type"] == "quantitative_experimental"
        assert result["paper_classification"]["primary_type"] == "quantitative_experimental"

        # Verify verdict
        verdict = result["wetlab_verdict"]
        assert verdict["reagents_total"] == 2
        assert verdict["reagents_with_identifiers"] == 1
        assert len(verdict["protocols"]) == 1
        assert verdict["positive_controls_present"] is True
        assert len(verdict["flags"]) == 1
        assert "Moderately reproducible" in verdict["summary"]

    @patch("Agent.nodes.wetlab_agent.get_nemotron3super")
    def test_node_review_paper(self, mock_get_nemotron):
        """Test that review papers are handled gracefully (no reagents/protocols)."""
        from Agent.nodes.wetlab_agent import wetlab_agent_node
        from Agent.state import WetlabExtractionResult, PaperClassification

        mock_response = WetlabExtractionResult(
            classification=PaperClassification(
                primary_type="review_meta_analysis",
                reasoning="Systematic review of 46 studies",
                key_indicators=["PRISMA", "systematic search"],
            ),
            reagents=[],
            protocols=[],
            methodology_assessment="Review methodology — wet-lab criteria not applicable.",
            summary="Review paper — wet-lab assessment N/A.",
        )

        mock_llm_structured = MagicMock()
        mock_llm_structured.invoke.return_value = mock_response

        mock_nemotron_instance = MagicMock()
        mock_nemotron_instance.with_structured_output.return_value = mock_llm_structured

        mock_get_nemotron.return_value = mock_nemotron_instance

        state = self._mock_state()
        result = wetlab_agent_node(state)

        assert result["paper_type"] == "review_meta_analysis"
        assert result["wetlab_verdict"]["reagents_total"] == 0
        assert result["wetlab_verdict"]["protocols"] == []



#  Reproducibility Evaluator Node (mocked LLM)

class TestReproducibilityEvaluatorNode:
    """Tests for the reproducibility_evaluator_node with mocked LLM calls."""

    def _mock_state_full(self):
        """Build a state with all upstream data populated."""
        from Agent.state import Claim, StatisticalClaim, ClaimType, EvidenceStrength
        return {
            "raw_text": "Some paper text...",
            "claims": [
                Claim(
                    claim_id="claim_1",
                    claim_text="Drug reduced tumor by 40%",
                    claim_type=ClaimType.EXPERIMENTAL,
                    section_source="results",
                    evidence_strength=EvidenceStrength.DIRECT,
                ),
            ],
            "statistical_claims": [
                StatisticalClaim(
                    claim_id="claim_1",
                    test_type="t-test",
                    p_value=0.028,
                ),
            ],
            "paper_meta": {"research_paradigm": "wet_lab"},
            "paper_classification": {"primary_type": "quantitative_experimental"},
            "wetlab_verdict": {
                "reagents_total": 5,
                "reagents_with_identifiers": 3,
                "positive_controls_present": True,
                "summary": "Moderately reproducible.",
            },
            "tool_agent_summary": "P-value verified, no p-hacking detected.",
        }

    def test_empty_state_returns_insufficient_info(self):
        """Node should return insufficient_information when no evidence."""
        from Agent.nodes.reproducibility_evaluator import reproducibility_evaluator_node
        state = {}
        result = reproducibility_evaluator_node(state)
        eval_result = result["reproducibility_evaluation"]
        assert eval_result["verdict"] == "insufficient_information"
        assert eval_result["confidence"] == "low"

    def test_collect_evidence(self):
        """Internal evidence collector should produce valid dict."""
        from Agent.nodes.reproducibility_evaluator import _collect_evidence
        state = self._mock_state_full()
        evidence = _collect_evidence(state)
        assert "extracted_claims" in evidence
        assert "statistical_claims" in evidence
        assert "wetlab_verdict" in evidence
        assert "paper_classification" in evidence
        assert "tool_verification_summary" in evidence

    def test_collect_evidence_empty_state(self):
        """Empty state should produce empty evidence dict."""
        from Agent.nodes.reproducibility_evaluator import _collect_evidence
        evidence = _collect_evidence({})
        assert evidence == {}

    @patch("Agent.nodes.reproducibility_evaluator.get_nemotron3super")
    def test_node_with_mocked_llm(self, mock_get_nemotron):
        """Full node test with mocked LLM."""
        from Agent.nodes.reproducibility_evaluator import reproducibility_evaluator_node
        from Agent.state import ReproducibilityEvaluation

        mock_response = ReproducibilityEvaluation(
            verdict="partially_reproducible",
            confidence="medium",
            methodology_rigor="Methods are adequately described.",
            statistical_validity="Appropriate tests used.",
            reagent_transparency="3 of 5 reagents have identifiers.",
            protocol_completeness="Some parameters missing.",
            data_availability="No raw data deposited.",
            controls_and_design="Controls present, no blinding.",
            strengths=["Good controls", "Appropriate statistics"],
            weaknesses=["No raw data", "Missing protocol details"],
            critical_gaps=["No code availability"],
            recommendations=["Deposit raw data"],
            overall_narrative="The paper is partially reproducible due to missing data.",
        )

        mock_llm_structured = MagicMock()
        mock_llm_structured.invoke.return_value = mock_response

        mock_nemotron_instance = MagicMock()
        mock_nemotron_instance.with_structured_output.return_value = mock_llm_structured

        mock_get_nemotron.return_value = mock_nemotron_instance

        state = self._mock_state_full()
        result = reproducibility_evaluator_node(state)

        # Verify structure
        assert "reproducibility_evaluation" in result
        assert "audit_trail" in result

        eval_result = result["reproducibility_evaluation"]
        assert eval_result["verdict"] == "partially_reproducible"
        assert eval_result["confidence"] == "medium"
        assert len(eval_result["strengths"]) == 2
        assert len(eval_result["weaknesses"]) == 2
        assert len(eval_result["critical_gaps"]) == 1
        assert "partially reproducible" in eval_result["overall_narrative"]

        # Verify audit trail
        assert len(result["audit_trail"]) == 1
        assert result["audit_trail"][0]["agent"] == "reproducibility_evaluator"

    @patch("Agent.nodes.reproducibility_evaluator.get_nemotron3super")
    def test_node_reproducible_verdict(self, mock_get_nemotron):
        """Test a fully reproducible verdict."""
        from Agent.nodes.reproducibility_evaluator import reproducibility_evaluator_node
        from Agent.state import ReproducibilityEvaluation

        mock_response = ReproducibilityEvaluation(
            verdict="reproducible",
            confidence="high",
            overall_narrative="Fully reproducible study.",
        )

        mock_llm_structured = MagicMock()
        mock_llm_structured.invoke.return_value = mock_response

        mock_nemotron_instance = MagicMock()
        mock_nemotron_instance.with_structured_output.return_value = mock_llm_structured

        mock_get_nemotron.return_value = mock_nemotron_instance

        state = self._mock_state_full()
        result = reproducibility_evaluator_node(state)

        assert result["reproducibility_evaluation"]["verdict"] == "reproducible"
        assert result["reproducibility_evaluation"]["confidence"] == "high"

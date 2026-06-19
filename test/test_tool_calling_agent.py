"""
Tests for the Tool Calling Agent and all supporting modules.
Covers:
 - statistical_tools.py  (verify_p_value, check_sample_size_power, detect_p_hacking_pattern)
 - verification_tools.py (cross_reference_claims, flag_missing_details)
 - tool_registry.py      (catalog, lookup, execution)
 - state.py              (new Pydantic models)
 - tool_calling_prompt.py (prompt templates)
 - tool_calling_agent.py  (node function with mocked LLM)
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


#  Statistical Tools

class TestVerifyPValue:
    """Tests for the verify_p_value tool."""

    def test_f_statistic_match(self):
        """Known ANOVA: F(2, 27) = 4.12 should give p ≈ 0.027"""
        from Agent.Tools.statistical_tools import verify_p_value
        result = verify_p_value.invoke({
            "test_statistic_value": 4.12,
            "degrees_of_freedom": [2, 27],
            "test_statistic_type": "F",
            "reported_p_value": 0.027,
        })
        assert result["match"] == True
        assert result["calculated_p_value"] is not None
        assert result["flag"] is None

    def test_f_statistic_mismatch(self):
        """F(2, 27) = 4.12 should NOT match p=0.5"""
        from Agent.Tools.statistical_tools import verify_p_value
        result = verify_p_value.invoke({
            "test_statistic_value": 4.12,
            "degrees_of_freedom": [2, 27],
            "test_statistic_type": "F",
            "reported_p_value": 0.5,
        })
        assert result["match"] == False
        assert result["flag"] == "P-VALUE MISMATCH"

    def test_t_statistic(self):
        """t(14) = 2.45 → two-tailed p ≈ 0.028"""
        from Agent.Tools.statistical_tools import verify_p_value
        result = verify_p_value.invoke({
            "test_statistic_value": 2.45,
            "degrees_of_freedom": [14],
            "test_statistic_type": "t",
            "reported_p_value": 0.028,
        })
        assert result["match"] == True
        assert result["discrepancy"] < 0.01

    def test_chi_square(self):
        """chi2(1) = 3.84 → p ≈ 0.05"""
        from Agent.Tools.statistical_tools import verify_p_value
        result = verify_p_value.invoke({
            "test_statistic_value": 3.84,
            "degrees_of_freedom": [1],
            "test_statistic_type": "chi2",
            "reported_p_value": 0.05,
        })
        assert result["match"] == True

    def test_unsupported_test_type(self):
        """Unknown test type should return error, not crash."""
        from Agent.Tools.statistical_tools import verify_p_value
        result = verify_p_value.invoke({
            "test_statistic_value": 1.0,
            "degrees_of_freedom": [10],
            "test_statistic_type": "z",
            "reported_p_value": 0.05,
        })
        assert result["match"] is None
        assert "error" in result


class TestCheckSampleSizePower:
    """Tests for the check_sample_size_power tool."""

    def test_adequate_power(self):
        """Large sample + large effect = adequate power."""
        from Agent.Tools.statistical_tools import check_sample_size_power
        result = check_sample_size_power.invoke({
            "sample_size": 100,
            "effect_size": 0.8,
        })
        assert result["power_adequate"] == True
        assert result["flag"] is None
        assert result["estimated_power"] > 0.80

    def test_underpowered(self):
        """Tiny sample + small effect = underpowered."""
        from Agent.Tools.statistical_tools import check_sample_size_power
        result = check_sample_size_power.invoke({
            "sample_size": 5,
            "effect_size": 0.2,
        })
        assert result["power_adequate"] == False
        assert result["flag"] == "UNDERPOWERED STUDY"
        assert result["estimated_power"] < 0.80

    def test_custom_alpha(self):
        """Custom alpha should be accepted."""
        from Agent.Tools.statistical_tools import check_sample_size_power
        result = check_sample_size_power.invoke({
            "sample_size": 50,
            "effect_size": 0.5,
            "alpha": 0.01,
        })
        assert "estimated_power" in result
        assert result["alpha"] == 0.01


class TestDetectPHackingPattern:
    """Tests for the detect_p_hacking_pattern tool."""

    def test_no_suspicious_pattern(self):
        """Spread of p-values should not be flagged."""
        from Agent.Tools.statistical_tools import detect_p_hacking_pattern
        result = detect_p_hacking_pattern.invoke({
            "p_values": [0.001, 0.003, 0.15, 0.22, 0.8],
        })
        assert result["suspicious"] is False
        assert result["flag"] is None

    def test_suspicious_clustering(self):
        """All p-values just below 0.05 → suspicious."""
        from Agent.Tools.statistical_tools import detect_p_hacking_pattern
        result = detect_p_hacking_pattern.invoke({
            "p_values": [0.041, 0.043, 0.048, 0.039, 0.045],
        })
        assert result["suspicious"] is True
        assert result["flag"] == "POSSIBLE P-HACKING PATTERN"

    def test_empty_list(self):
        """Empty list should not crash."""
        from Agent.Tools.statistical_tools import detect_p_hacking_pattern
        result = detect_p_hacking_pattern.invoke({
            "p_values": [],
        })
        assert result["suspicious"] is False

    def test_single_p_value(self):
        """Single value should work without error."""
        from Agent.Tools.statistical_tools import detect_p_hacking_pattern
        result = detect_p_hacking_pattern.invoke({
            "p_values": [0.03],
        })
        assert "total_p_values" in result
        assert result["total_p_values"] == 1



#  Verification Tools


class TestCrossReferenceClaims:
    """Tests for the cross_reference_claims tool."""

    def test_all_claims_have_stats(self):
        """All claims matched → no issues."""
        from Agent.Tools.verification_tools import cross_reference_claims
        claims = [
            {"claim_id": "claim_1", "claim_text": "Drug reduced tumor", "claim_type": "experimental"},
        ]
        stats = [
            {"claim_id": "claim_1", "test_type": "t-test", "stated_sample_size_n": 10},
        ]
        result = cross_reference_claims.invoke({
            "claims_data": claims,
            "statistical_claims_data": stats,
        })
        assert result["claims_with_statistical_backing"] == 1
        assert result["claims_without_statistical_backing"] == 0

    def test_missing_stats_for_experimental_claim(self):
        """Experimental claim without stats → flagged as high severity."""
        from Agent.Tools.verification_tools import cross_reference_claims
        claims = [
            {"claim_id": "claim_1", "claim_text": "Drug reduced tumor", "claim_type": "experimental"},
            {"claim_id": "claim_2", "claim_text": "Model predicts binding", "claim_type": "theoretical"},
        ]
        stats = []
        result = cross_reference_claims.invoke({
            "claims_data": claims,
            "statistical_claims_data": stats,
        })
        assert result["claims_without_statistical_backing"] == 2
        # Only the experimental claim should be flagged as high
        high_issues = [i for i in result["issues"] if i["severity"] == "high"]
        assert len(high_issues) == 1
        assert high_issues[0]["claim_id"] == "claim_1"

    def test_controls_without_test(self):
        """Claim says controls present but no test_type → medium flag."""
        from Agent.Tools.verification_tools import cross_reference_claims
        claims = [
            {"claim_id": "c1", "claim_text": "Compared to control", "claim_type": "experimental", "controls_present": True},
        ]
        stats = [
            {"claim_id": "c1", "test_type": None, "stated_sample_size_n": 10},
        ]
        result = cross_reference_claims.invoke({
            "claims_data": claims,
            "statistical_claims_data": stats,
        })
        medium_issues = [i for i in result["issues"] if i["severity"] == "medium"]
        assert len(medium_issues) == 1

    def test_empty_inputs(self):
        """Empty inputs should not crash."""
        from Agent.Tools.verification_tools import cross_reference_claims
        result = cross_reference_claims.invoke({
            "claims_data": [],
            "statistical_claims_data": [],
        })
        assert result["total_claims"] == 0
        assert result["issues_found"] == 0


class TestFlagMissingDetails:
    """Tests for the flag_missing_details tool."""

    def test_all_complete(self):
        """All fields present → all_complete is True."""
        from Agent.Tools.verification_tools import flag_missing_details
        data = [
            {"claim_id": "c1", "test_type": "t-test", "p_value": 0.03},
        ]
        result = flag_missing_details.invoke({
            "data": data,
            "required_fields": ["claim_id", "test_type", "p_value"],
            "data_source": "statistics_agent",
        })
        assert result["all_complete"] is True
        assert result["incomplete_records"] == 0

    def test_missing_fields(self):
        """Missing p_value → flagged."""
        from Agent.Tools.verification_tools import flag_missing_details
        data = [
            {"claim_id": "c1", "test_type": "t-test", "p_value": None},
            {"claim_id": "c2", "test_type": "ANOVA", "p_value": 0.01},
        ]
        result = flag_missing_details.invoke({
            "data": data,
            "required_fields": ["claim_id", "test_type", "p_value"],
            "data_source": "stats",
        })
        assert result["all_complete"] is False
        assert result["incomplete_records"] == 1
        assert result["missing_details"][0]["record_id"] == "c1"
        assert "p_value" in result["missing_details"][0]["missing_fields"]

    def test_empty_data(self):
        """Empty data should return complete=True."""
        from Agent.Tools.verification_tools import flag_missing_details
        result = flag_missing_details.invoke({
            "data": [],
            "required_fields": ["x"],
            "data_source": "test",
        })
        assert result["complete"] is True

    def test_empty_string_counts_as_missing(self):
        """Empty string should count as missing."""
        from Agent.Tools.verification_tools import flag_missing_details
        data = [{"claim_id": "", "test_type": "t-test"}]
        result = flag_missing_details.invoke({
            "data": data,
            "required_fields": ["claim_id"],
            "data_source": "test",
        })
        assert result["incomplete_records"] == 1



#  Tool Registry

class TestToolRegistry:
    """Tests for the tool registry module."""

    def test_catalog_has_all_tools(self):
        """Catalog should contain all 5 registered tools."""
        from Agent.Tools.tool_registry import get_tool_catalog
        catalog = get_tool_catalog()
        names = [t["tool_name"] for t in catalog]
        assert "verify_p_value" in names
        assert "check_sample_size_power" in names
        assert "detect_p_hacking_pattern" in names
        assert "cross_reference_claims" in names
        assert "flag_missing_details" in names
        assert len(catalog) == 5

    def test_catalog_entries_have_description(self):
        """Each tool in the catalog should have a non-empty description."""
        from Agent.Tools.tool_registry import get_tool_catalog
        catalog = get_tool_catalog()
        for tool in catalog:
            assert tool["description"], f"{tool['tool_name']} has no description"
            assert tool["tool_name"], "tool_name is empty"

    def test_catalog_entries_have_parameters(self):
        """Each tool should expose its parameter schema."""
        from Agent.Tools.tool_registry import get_tool_catalog
        catalog = get_tool_catalog()
        for tool in catalog:
            assert isinstance(tool["parameters"], dict), f"{tool['tool_name']} has no parameter schema"

    def test_get_tool_by_name_found(self):
        """Known tool name should return a callable."""
        from Agent.Tools.tool_registry import get_tool_by_name
        tool = get_tool_by_name("verify_p_value")
        assert tool is not None
        assert callable(tool.invoke)

    def test_get_tool_by_name_not_found(self):
        """Unknown tool name should return None."""
        from Agent.Tools.tool_registry import get_tool_by_name
        tool = get_tool_by_name("nonexistent_tool")
        assert tool is None

    def test_execute_tool_success(self):
        """Execute a real tool and check the result structure."""
        from Agent.Tools.tool_registry import execute_tool
        result = execute_tool("detect_p_hacking_pattern", {"p_values": [0.03, 0.5]})
        assert result["success"] is True
        assert result["tool_name"] == "detect_p_hacking_pattern"
        assert result["error"] is None
        assert result["execution_time_ms"] >= 0

    def test_execute_tool_not_found(self):
        """Executing a nonexistent tool should return success=False."""
        from Agent.Tools.tool_registry import execute_tool
        result = execute_tool("ghost_tool", {})
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_catalog_is_json_serializable(self):
        """The catalog must be JSON-serializable (it goes into the prompt)."""
        from Agent.Tools.tool_registry import get_tool_catalog
        catalog = get_tool_catalog()
        serialized = json.dumps(catalog)
        assert isinstance(serialized, str)
        assert len(serialized) > 10



#  State Models (Pydantic)

class TestStateModels:
    """Tests for the new Pydantic models in state.py."""

    def test_tool_call_creation(self):
        from Agent.state import ToolCall
        tc = ToolCall(tool_name="verify_p_value", arguments={"x": 1}, reasoning="test")
        assert tc.tool_name == "verify_p_value"
        assert tc.arguments == {"x": 1}
        assert tc.reasoning == "test"

    def test_tool_call_defaults(self):
        from Agent.state import ToolCall
        tc = ToolCall(tool_name="test")
        assert tc.arguments == {}
        assert tc.reasoning == ""

    def test_tool_call_result_creation(self):
        from Agent.state import ToolCallResult
        tr = ToolCallResult(tool_name="test", success=True, result={"match": True})
        assert tr.success is True
        assert tr.result == {"match": True}
        assert tr.error is None

    def test_tool_call_result_failure(self):
        from Agent.state import ToolCallResult
        tr = ToolCallResult(tool_name="test", success=False, error="boom")
        assert tr.success is False
        assert tr.error == "boom"

    def test_tool_calling_plan_creation(self):
        from Agent.state import ToolCallingPlan, ToolCall
        plan = ToolCallingPlan(
            data_understanding="Statistical data from stats agent",
            source_agent="statistics_agent",
            tool_calls=[
                ToolCall(tool_name="verify_p_value", arguments={"x": 1}),
            ],
        )
        assert plan.source_agent == "statistics_agent"
        assert len(plan.tool_calls) == 1

    def test_tool_calling_plan_defaults(self):
        from Agent.state import ToolCallingPlan
        plan = ToolCallingPlan()
        assert plan.data_understanding == ""
        assert plan.source_agent == ""
        assert plan.tool_calls == []

    def test_tool_agent_response_creation(self):
        from Agent.state import ToolAgentResponse, ToolCallingPlan, ToolCallResult
        response = ToolAgentResponse(
            plan=ToolCallingPlan(data_understanding="test"),
            tool_results=[ToolCallResult(tool_name="t", success=True)],
            synthesis="All good",
            flags=["FLAG_1"],
        )
        assert response.synthesis == "All good"
        assert len(response.flags) == 1

    def test_tool_agent_response_serialization(self):
        """Model should be JSON-serializable via model_dump."""
        from Agent.state import ToolAgentResponse, ToolCallingPlan, ToolCall, ToolCallResult
        response = ToolAgentResponse(
            plan=ToolCallingPlan(
                data_understanding="test",
                tool_calls=[ToolCall(tool_name="x")],
            ),
            tool_results=[ToolCallResult(tool_name="x", success=True, result={"a": 1})],
            synthesis="summary",
        )
        d = response.model_dump()
        assert isinstance(d, dict)
        serialized = json.dumps(d)
        assert "summary" in serialized



#  Prompt Templates

class TestPromptTemplates:
    """Tests for the tool calling prompt templates."""

    def test_system_prompt_exists(self):
        from Agent.prompts.tool_calling_prompt import TOOL_CALLING_SYSTEM
        assert len(TOOL_CALLING_SYSTEM) > 100
        assert "{tool_catalog}" in TOOL_CALLING_SYSTEM

    def test_human_prompt_exists(self):
        from Agent.prompts.tool_calling_prompt import TOOL_CALLING_HUMAN
        assert len(TOOL_CALLING_HUMAN) > 50
        assert "{agent_data}" in TOOL_CALLING_HUMAN

    def test_synthesis_system_prompt_exists(self):
        from Agent.prompts.tool_calling_prompt import TOOL_SYNTHESIS_SYSTEM
        assert len(TOOL_SYNTHESIS_SYSTEM) > 50

    def test_synthesis_human_prompt_exists(self):
        from Agent.prompts.tool_calling_prompt import TOOL_SYNTHESIS_HUMAN
        assert "{original_data}" in TOOL_SYNTHESIS_HUMAN
        assert "{tool_results}" in TOOL_SYNTHESIS_HUMAN

    def test_system_prompt_has_reasoning_steps(self):
        """The prompt should include the 4 reasoning steps."""
        from Agent.prompts.tool_calling_prompt import TOOL_CALLING_SYSTEM
        assert "IDENTIFY" in TOOL_CALLING_SYSTEM
        assert "ASSESS" in TOOL_CALLING_SYSTEM
        assert "SELECT" in TOOL_CALLING_SYSTEM
        assert "PLAN" in TOOL_CALLING_SYSTEM

    def test_system_prompt_format_works(self):
        """The .format() call with tool_catalog should not raise."""
        from Agent.prompts.tool_calling_prompt import TOOL_CALLING_SYSTEM
        formatted = TOOL_CALLING_SYSTEM.format(tool_catalog="[test catalog]")
        assert "[test catalog]" in formatted

    def test_human_prompt_format_works(self):
        from Agent.prompts.tool_calling_prompt import TOOL_CALLING_HUMAN
        formatted = TOOL_CALLING_HUMAN.format(agent_data="{\"test\": 1}")
        assert '{"test": 1}' in formatted



#  Tool Calling Agent Node (mocked LLM)


class TestToolCallingAgentNode:
    """Tests for the tool_calling_agent_node with mocked LLM calls."""

    def _mock_state_with_data(self):
        """Build a realistic state dict with claims and statistical claims."""
        from Agent.state import Claim, StatisticalClaim, ClaimType, EvidenceStrength
        return {
            "claims": [
                Claim(
                    claim_id="claim_1",
                    claim_text="Drug reduced tumor by 40%",
                    claim_type=ClaimType.EXPERIMENTAL,
                    section_source="results",
                    evidence_strength=EvidenceStrength.DIRECT,
                    numerical_values=["40%"],
                    controls_present=True,
                ),
            ],
            "statistical_claims": [
                StatisticalClaim(
                    claim_id="claim_1",
                    test_type="t-test",
                    test_statistic_type="t",
                    test_statistic_value=2.45,
                    degrees_of_freedom=[14],
                    reported_p_value="=0.028",
                    p_value=0.028,
                    stated_sample_size_n=10,
                    section="results",
                ),
            ],
            "paper_meta": {"research_paradigm": "wet_lab", "subdiscipline": "oncology"},
            "raw_text": "Some paper text...",
        }

    def test_empty_state_returns_early(self):
        """Node should return gracefully when there's no upstream data."""
        from Agent.nodes.tool_calling_agent import tool_calling_agent_node
        state = {}
        result = tool_calling_agent_node(state)
        assert result["tool_call_plan"] == []
        assert result["tool_execution_results"] == []
        assert "No upstream data" in result["tool_agent_summary"]

    def test_serialize_agent_data(self):
        """The internal serializer should produce valid JSON from state."""
        from Agent.nodes.tool_calling_agent import _serialize_agent_data
        state = self._mock_state_with_data()
        json_str = _serialize_agent_data(state)
        parsed = json.loads(json_str)
        assert "extracted_claims" in parsed
        assert "statistical_claims" in parsed
        assert len(parsed["extracted_claims"]) == 1
        assert parsed["extracted_claims"][0]["claim_id"] == "claim_1"

    def test_serialize_empty_state(self):
        """Empty state should produce '{}'."""
        from Agent.nodes.tool_calling_agent import _serialize_agent_data
        result = _serialize_agent_data({})
        assert result == "{}"

    @patch("Agent.nodes.tool_calling_agent.get_gemini_flash")
    def test_node_with_mocked_llm(self, mock_get_flash):
        """Full node test with mocked LLM — verifies the two-pass pattern."""
        from Agent.nodes.tool_calling_agent import tool_calling_agent_node
        from Agent.state import ToolCallingPlan, ToolCall

        # Mock Pass 1: LLM returns a plan to call detect_p_hacking_pattern
        mock_plan = ToolCallingPlan(
            data_understanding="Statistical data with p-values",
            source_agent="statistics_agent",
            tool_calls=[
                ToolCall(
                    tool_name="detect_p_hacking_pattern",
                    arguments={"p_values": [0.03, 0.04, 0.5]},
                    reasoning="Multiple p-values found, checking for clustering",
                ),
            ],
        )

        # Mock Pass 2: LLM returns synthesis text
        mock_synthesis = MagicMock()
        mock_synthesis.content = "All tools executed. No p-hacking detected."

        # Setup the mock chain
        mock_llm_structured = MagicMock()
        mock_llm_structured.invoke.return_value = mock_plan

        mock_llm_plain = MagicMock()
        mock_llm_plain.invoke.return_value = mock_synthesis

        # First call returns structured LLM, second returns plain
        mock_flash_instance = MagicMock()
        mock_flash_instance.with_structured_output.return_value = mock_llm_structured
        mock_flash_instance.invoke.return_value = mock_synthesis

        mock_get_flash.return_value = mock_flash_instance

        state = self._mock_state_with_data()
        result = tool_calling_agent_node(state)

        # Verify structure
        assert "tool_call_plan" in result
        assert "tool_execution_results" in result
        assert "tool_agent_summary" in result
        assert "audit_trail" in result

        # Verify the plan was used
        assert len(result["tool_call_plan"]) == 1

        # Verify tool was actually executed (not just planned)
        assert len(result["tool_execution_results"]) == 1
        assert result["tool_execution_results"][0]["tool_name"] == "detect_p_hacking_pattern"
        assert result["tool_execution_results"][0]["success"] is True

    @patch("Agent.nodes.tool_calling_agent.get_gemini_flash")
    def test_node_handles_tool_failure_gracefully(self, mock_get_flash):
        """If LLM picks a nonexistent tool, node should not crash."""
        from Agent.nodes.tool_calling_agent import tool_calling_agent_node
        from Agent.state import ToolCallingPlan, ToolCall

        mock_plan = ToolCallingPlan(
            data_understanding="test",
            source_agent="test",
            tool_calls=[
                ToolCall(tool_name="nonexistent_tool", arguments={}, reasoning="bad pick"),
            ],
        )

        mock_synthesis = MagicMock()
        mock_synthesis.content = "Tool failed."

        mock_flash_instance = MagicMock()
        mock_flash_instance.with_structured_output.return_value = MagicMock(invoke=MagicMock(return_value=mock_plan))
        mock_flash_instance.invoke.return_value = mock_synthesis

        mock_get_flash.return_value = mock_flash_instance

        state = self._mock_state_with_data()
        result = tool_calling_agent_node(state)

        # Should still return a result, not crash
        assert len(result["tool_execution_results"]) == 1
        assert result["tool_execution_results"][0]["success"] is False
        assert "not found" in result["tool_execution_results"][0]["error"]

    @patch("Agent.nodes.tool_calling_agent.get_gemini_flash")
    def test_node_no_tools_needed(self, mock_get_flash):
        """If LLM decides no tools are needed, node should handle gracefully."""
        from Agent.nodes.tool_calling_agent import tool_calling_agent_node
        from Agent.state import ToolCallingPlan

        mock_plan = ToolCallingPlan(
            data_understanding="Theoretical claims, no stats to verify",
            source_agent="claim_extractor",
            tool_calls=[],
        )

        mock_synthesis = MagicMock()
        mock_synthesis.content = "No tools needed."

        mock_flash_instance = MagicMock()
        mock_flash_instance.with_structured_output.return_value = MagicMock(invoke=MagicMock(return_value=mock_plan))
        mock_flash_instance.invoke.return_value = mock_synthesis

        mock_get_flash.return_value = mock_flash_instance

        state = self._mock_state_with_data()
        result = tool_calling_agent_node(state)

        assert result["tool_execution_results"] == []
        assert len(result["tool_call_plan"]) == 1

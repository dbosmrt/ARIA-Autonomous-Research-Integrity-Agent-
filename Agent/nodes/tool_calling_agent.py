"""
Tool Calling Agent node — the LLM-powered tool dispatcher.
Receives structured output from upstream agents, reasons about the data,
selects and executes appropriate verification tools, then synthesizes results.

Uses a two-pass LLM pattern:
  Pass 1: LLM analyzes data → outputs ToolCallingPlan (which tools to call)
  Pass 2: After tool execution → LLM synthesizes results into a summary
"""

import json
from typing import Dict, Any, List
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from Agent.model import get_gemini_flash
from Agent.state import (
    ReprCheckState, Claim, StatisticalClaim,
    ToolCallingPlan, ToolCallResult, ToolAgentResponse,
)
from Agent.prompts.tool_calling_prompt import (
    TOOL_CALLING_SYSTEM,
    TOOL_CALLING_HUMAN,
    TOOL_SYNTHESIS_SYSTEM,
    TOOL_SYNTHESIS_HUMAN,
)
from Agent.Tools.tool_registry import get_tool_catalog, execute_tool
from Agent.logging_config import setup_logging, get_agent_logger

setup_logging()
logger = get_agent_logger("tool_calling_agent")


def _serialize_agent_data(state: ReprCheckState) -> str:
    """Collect all available upstream agent data from state and serialize to JSON.
    This is what gets fed to the LLM so it can understand what data it has.
    """
    data = {}

    # Claims from claim extractor
    claims = state.get("claims", [])
    if claims:
        data["extracted_claims"] = [
            c.model_dump() if hasattr(c, "model_dump") else c
            for c in claims
        ]

    # Statistical claims from statistics agent
    stat_claims = state.get("statistical_claims", [])
    if stat_claims:
        data["statistical_claims"] = [
            sc.model_dump() if hasattr(sc, "model_dump") else sc
            for sc in stat_claims
        ]

    # Paper metadata
    paper_meta = state.get("paper_meta", {})
    if paper_meta:
        data["paper_metadata"] = paper_meta

    # Agent results (fan-in list)
    agent_results = state.get("agent_results", [])
    if agent_results:
        data["agent_results"] = [
            ar.model_dump() if hasattr(ar, "model_dump") else ar
            for ar in agent_results
        ]

    # Methodology verdict
    meth_verdict = state.get("methodology_verdict", {})
    if meth_verdict:
        data["methodology_verdict"] = meth_verdict

    # Stats verdict
    stats_verdict = state.get("stats_verdict", {})
    if stats_verdict:
        data["stats_verdict"] = stats_verdict

    # Wetlab verdict
    wetlab_verdict = state.get("wetlab_verdict", {})
    if wetlab_verdict:
        data["wetlab_verdict"] = wetlab_verdict

    if not data:
        return "{}"

    return json.dumps(data, indent=2, default=str)


# LangGraph Node Function
def tool_calling_agent_node(state: ReprCheckState) -> dict:
    """
    LangGraph node that acts as a universal tool dispatcher.
    Reads upstream agent outputs, asks LLM which tools to call,
    executes them, then synthesizes the results.
    """
    start = datetime.now(timezone.utc)
    logger.info("Tool Calling Agent started...")

    # Collect all upstream data
    agent_data_json = _serialize_agent_data(state)
    if agent_data_json == "{}":
        logger.warning("No upstream agent data found in state. Skipping tool calling.")
        return {
            "tool_call_plan": [],
            "tool_execution_results": [],
            "tool_agent_summary": "No upstream data available for tool execution.",
        }

    # Build the tool catalog for the prompt
    catalog = get_tool_catalog()
    catalog_json = json.dumps(catalog, indent=2)

    # === PASS 1: Ask LLM which tools to call ===
    logger.info("Pass 1: Asking LLM to select tools...")

    llm = get_gemini_flash().with_structured_output(ToolCallingPlan)

    system_prompt = TOOL_CALLING_SYSTEM.format(tool_catalog=catalog_json)
    human_prompt = TOOL_CALLING_HUMAN.format(agent_data=agent_data_json)

    plan: ToolCallingPlan = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ])

    logger.info(f"LLM identified data as: {plan.data_understanding}")
    logger.info(f"LLM selected {len(plan.tool_calls)} tools to call")

    # === EXECUTE TOOLS ===
    tool_results: List[dict] = []

    for tc in plan.tool_calls:
        logger.info(f"Executing tool: {tc.tool_name} (reason: {tc.reasoning})")
        result = execute_tool(tc.tool_name, tc.arguments)
        tool_results.append(result)

    logger.info(f"Executed {len(tool_results)} tools, {sum(1 for r in tool_results if r['success'])} succeeded")

    # === PASS 2: Synthesize results ===
    logger.info("Pass 2: Synthesizing tool results...")

    synthesis_llm = get_gemini_flash()  # plain text output, no structured

    tool_results_json = json.dumps(tool_results, indent=2, default=str)

    synthesis_response = synthesis_llm.invoke([
        SystemMessage(content=TOOL_SYNTHESIS_SYSTEM),
        HumanMessage(content=TOOL_SYNTHESIS_HUMAN.format(
            original_data=agent_data_json,
            tool_results=tool_results_json,
        )),
    ])

    synthesis_text = synthesis_response.content if hasattr(synthesis_response, "content") else str(synthesis_response)

    # Collect flags from tool results
    flags = []
    for r in tool_results:
        if r.get("success") and isinstance(r.get("result"), dict):
            flag = r["result"].get("flag")
            if flag:
                flags.append(flag)

    elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
    logger.info(f"Tool Calling Agent completed in {elapsed_ms:.1f}ms — {len(flags)} flags raised")

    # Build the full response
    response = ToolAgentResponse(
        plan=plan,
        tool_results=[
            ToolCallResult(
                tool_name=r["tool_name"],
                success=r["success"],
                result=r.get("result"),
                error=r.get("error"),
                execution_time_ms=r.get("execution_time_ms", 0),
            )
            for r in tool_results
        ],
        synthesis=synthesis_text,
        flags=flags,
    )

    return {
        "tool_call_plan": [plan.model_dump()],
        "tool_execution_results": [r for r in tool_results],
        "tool_agent_summary": synthesis_text,
        "audit_trail": [{
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "tool_calling_agent",
            "action": f"Executed {len(tool_results)} tools, raised {len(flags)} flags",
            "details": json.dumps({"flags": flags, "tools_called": [r["tool_name"] for r in tool_results]}),
            "latency_ms": elapsed_ms,
        }],
    }

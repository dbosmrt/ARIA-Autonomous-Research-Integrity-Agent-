"""
Central tool registry for the Tool Calling Agent.
Collects all @tool-decorated functions and provides:
 - get_tool_catalog() → JSON-serializable list of tool descriptions for the prompt
 - get_tool_by_name(name) → returns the callable
 - execute_tool(name, args) → runs with error handling, returns result dict
"""

import time
from typing import Any, Dict, Optional
from Agent.logging_config import setup_logging, get_agent_logger

setup_logging()
logger = get_agent_logger("tool_registry")

# Import all tool modules so their @tool decorators register
from Agent.Tools.statistical_tools import (
    verify_p_value,
    check_sample_size_power,
    detect_p_hacking_pattern,
)
from Agent.Tools.verification_tools import (
    cross_reference_claims,
    flag_missing_details,
)


# Master registry — maps tool name to (callable, description, args_schema)
_TOOL_REGISTRY: Dict[str, dict] = {}

def _register(tool_fn):
    """Register a LangChain @tool function into the registry."""
    name = tool_fn.name
    description = tool_fn.description or ""
    # Extract argument schema from the tool's args_schema (Pydantic model)
    args_schema = {}
    if hasattr(tool_fn, "args_schema") and tool_fn.args_schema:
        schema = tool_fn.args_schema.model_json_schema()
        args_schema = schema.get("properties", {})

    _TOOL_REGISTRY[name] = {
        "callable": tool_fn,
        "description": description,
        "args_schema": args_schema,
    }
    logger.debug(f"Registered tool: {name}")


# Register all tools on import
for _tool_fn in [
    verify_p_value,
    check_sample_size_power,
    detect_p_hacking_pattern,
    cross_reference_claims,
    flag_missing_details,
]:
    _register(_tool_fn)

logger.info(f"Tool registry loaded: {len(_TOOL_REGISTRY)} tools available")


def get_tool_catalog() -> list[dict]:
    """Returns a JSON-serializable catalog of all available tools.
    This gets injected into the tool calling agent's prompt so the LLM
    knows what tools exist and how to call them.
    """
    catalog = []
    for name, info in _TOOL_REGISTRY.items():
        catalog.append({
            "tool_name": name,
            "description": info["description"],
            "parameters": info["args_schema"],
        })
    return catalog


def get_tool_by_name(name: str) -> Optional[Any]:
    """Lookup a tool by name. Returns the callable or None."""
    entry = _TOOL_REGISTRY.get(name)
    if entry:
        return entry["callable"]
    logger.warning(f"Tool not found: {name}")
    return None


def execute_tool(name: str, arguments: Dict[str, Any]) -> dict:
    """Execute a tool by name with given arguments.
    Returns a result dict with success/error/timing info.
    """
    tool_fn = get_tool_by_name(name)
    if not tool_fn:
        return {
            "tool_name": name,
            "success": False,
            "result": None,
            "error": f"Tool '{name}' not found in registry",
            "execution_time_ms": 0,
        }

    start = time.time()
    try:
        result = tool_fn.invoke(arguments)
        elapsed_ms = (time.time() - start) * 1000
        logger.info(f"Tool '{name}' executed in {elapsed_ms:.1f}ms")
        return {
            "tool_name": name,
            "success": True,
            "result": result,
            "error": None,
            "execution_time_ms": round(elapsed_ms, 2),
        }
    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000
        logger.error(f"Tool '{name}' failed: {e}")
        return {
            "tool_name": name,
            "success": False,
            "result": None,
            "error": str(e),
            "execution_time_ms": round(elapsed_ms, 2),
        }

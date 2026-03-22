"""
evaluator.py
-----------
Agent LangGraph responsable de la décision stop / regenerate.
"""

import json

from langchain_core.output_parsers import JsonOutputParser

from src.utils.prompts import EVALUATOR_PROMPT
from src.utils.llm import get_llm, invoke_with_retry


def evaluator_node(state: dict) -> dict:
    """
    Nœud LangGraph : EVALUATOR.
    Entrées : execution_summary, analyzer_report
    Sorties  : evaluation_decision, evaluation_reason
    """
    print("--- EVALUATOR ---")

    llm    = get_llm()
    chain  = EVALUATOR_PROMPT | llm
    parser = JsonOutputParser()

    try:
        message = invoke_with_retry(chain, {
            "execution_summary": json.dumps(state.get("execution_summary", {})),
            "analyzer_json":     json.dumps(state.get("analyzer_report", {})),
        })
        result: dict = parser.invoke(message)
    except Exception as exc:
        print(f"[Evaluator] ❌ Fallback LLM : {exc}")
        result = {"decision": "stop", "reason": f"Evaluateur indisponible : {exc}"}

    return {
        "evaluation_decision": result.get("decision", "stop"),
        "evaluation_reason":   result.get("reason", ""),
    }
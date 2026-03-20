# analyzer.py
import json
from langchain_core.output_parsers import JsonOutputParser
from src.utils.prompts import ANALYZER_PROMPT
from src.utils.llm import get_llm, invoke_with_retry

def analyzer_node(state):
    print("--- ANALYZER ---")
    llm = get_llm()
    chain = ANALYZER_PROMPT | llm | JsonOutputParser()

    try:
        result = invoke_with_retry(chain, {
            "contract_code": state.get("contract_code", ""),
            "test_code": state.get("test_code", ""),
            "mochawesome_json": json.dumps(state.get("test_report", {})),
            "coverage_json": json.dumps(state.get("coverage_report", {}))
        })
    except Exception as e:
        # Keep the graph alive on transient Ollama errors.
        result = {
            "failures": [],
            "missing_coverage": {"functions": [], "branches": [], "edge_cases": []},
            "suggestions": ["Analyzer unavailable"],
            "error": str(e),
        }
        print(f"Analyzer fallback due to LLM error: {e}")

    return {"analyzer_report": result}

# evaluator.py
import json
from langchain_core.output_parsers import JsonOutputParser
from src.utils.prompts import EVALUATOR_PROMPT
from src.utils.llm import get_llm, invoke_with_retry

def evaluator_node(state):
    print("--- EVALUATOR ---")
    llm = get_llm()
    chain = EVALUATOR_PROMPT | llm
    parser = JsonOutputParser()

    try:
        message = invoke_with_retry(chain, {
            "execution_summary": json.dumps(state.get("execution_summary", {})),
            "analyzer_json": json.dumps(state.get("analyzer_report", {}))
        })
        result = parser.invoke(message)
    except Exception as e:
        print(f"Evaluator fallback due to LLM error: {e}")
        result = {"decision": "stop", "reason": f"Evaluator unavailable: {e}"}

    decision = result.get("decision", "stop")
    return {"evaluation_decision": decision, "evaluation_reason": result.get("reason", "")}

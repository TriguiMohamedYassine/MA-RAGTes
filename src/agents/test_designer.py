# test_designer.py
import json
import os
from langchain_core.output_parsers import JsonOutputParser
from src.utils.prompts import TEST_DESIGNER_PROMPT
from src.utils.llm import get_llm, invoke_with_retry

def test_designer_node(state):
    print("--- TEST DESIGNER ---")
    llm = get_llm()
    chain = TEST_DESIGNER_PROMPT | llm
    parser = JsonOutputParser()
    
    message = invoke_with_retry(chain, {
        "contract_code": state.get("contract_code", ""),
        "user_story": state.get("user_story", "")
    })
    result = parser.invoke(message)

    os.makedirs("outputs", exist_ok=True)
    try:
        with open("outputs/test_design.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    except Exception as e:
        print(f"Warning: could not save test design artifact: {e}")

    return {"test_design": result}

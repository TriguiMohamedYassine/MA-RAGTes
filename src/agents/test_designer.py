"""
test_designer.py
----------------
Agent LangGraph responsable de la conception de la stratégie de tests.

Construit un contexte local avant d'appeler le LLM,
puis persiste le résultat dans OUTPUT_DIR/test_design.json.
"""

import json
import re

from langchain_core.output_parsers import JsonOutputParser

from src.utils.prompts import TEST_DESIGNER_PROMPT
from src.utils.llm import get_llm, invoke_with_retry
from src.config import OUTPUT_DIR


def _build_local_contract_context(contract_code: str) -> str:
    """Construit un contexte utile a partir du contrat, sans retrieval externe."""
    if not contract_code.strip():
        return "Contexte local indisponible: contrat vide."

    contract_match = re.search(r"\bcontract\s+(\w+)", contract_code)
    contract_name = contract_match.group(1) if contract_match else "UnknownContract"

    functions = re.findall(r"function\s+(\w+)\s*\(", contract_code)
    functions_preview = ", ".join(functions[:12]) if functions else "Aucune fonction detectee"

    return (
        "Contexte local. "
        f"Contrat: {contract_name}. "
        f"Fonctions detectees: {functions_preview}."
    )


def test_designer_node(state: dict) -> dict:
    """
    Nœud LangGraph : TEST DESIGNER.

    Entrées du state :
      - contract_code (str)
      - user_story    (str, optionnel)

    Sorties ajoutées au state :
      - test_design  (dict)
      - erc_context  (str)
    """
    print("--- TEST DESIGNER ---")

    contract_code: str = state.get("contract_code", "")

    # Contexte construit localement.
    erc_context = _build_local_contract_context(contract_code)

    # --- Appel LLM ---
    llm    = get_llm()
    chain  = TEST_DESIGNER_PROMPT | llm
    parser = JsonOutputParser()

    # FIX : try/except avec fallback minimal pour ne pas tuer le pipeline
    try:
        message = invoke_with_retry(chain, {
            "contract_code": contract_code,
            "user_story":    state.get("user_story", ""),
            "erc_context":   erc_context,
        })
        result: dict = parser.invoke(message)
    except Exception as exc:
        print(f"[Test Designer] ❌ Fallback LLM : {exc}")
        result = {
            "contract_name": "Unknown",
            "test_suites":   [],
            "error":         str(exc),
        }

    # --- Persistance de l'artefact ---
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(OUTPUT_DIR / "test_design.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        print(f"[Test Designer] Impossible de sauvegarder test_design.json : {exc}")

    return {
        "test_design": result,
        "erc_context": erc_context,
    }
"""
test_designer.py
----------------
Agent LangGraph responsable de la conception de la stratégie de tests.

Utilise le RAG ERC pour enrichir le contexte avant d'appeler le LLM,
puis persiste le résultat dans OUTPUT_DIR/test_design.json.
"""

import json

from langchain_core.output_parsers import JsonOutputParser

from src.utils.prompts import TEST_DESIGNER_PROMPT
from src.utils.llm import get_llm, invoke_with_retry
from src.utils.advanced_rag import AdvancedRAG
from src.config import OUTPUT_DIR


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

    # --- Récupération du contexte ERC via RAG ---
    try:
        rag = AdvancedRAG(collection_name="erc_standards")
        rag_result = rag.retrieve(contract_code)
        erc_context: str = rag_result.get("context", "Aucun standard détecté.")
    except Exception as exc:
        print(f"[Test Designer] RAG ERC échoué : {exc}")
        erc_context = "Contexte ERC indisponible."

    # --- Appel LLM ---
    llm = get_llm()
    chain = TEST_DESIGNER_PROMPT | llm
    parser = JsonOutputParser()

    message = invoke_with_retry(chain, {
        "contract_code": contract_code,
        "user_story":    state.get("user_story", ""),
        "erc_context":   erc_context,
    })
    result: dict = parser.invoke(message)

    # --- Persistance de l'artefact ---
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(OUTPUT_DIR / "test_design.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        print(f"[Test Designer] Impossible de sauvegarder test_design.json : {exc}")

    return {"test_design": result, "erc_context": erc_context}
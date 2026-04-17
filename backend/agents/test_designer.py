"""Agent LangGraph responsable de la conception de la stratégie de tests."""

import json

from langchain_core.output_parsers import JsonOutputParser

from backend.config.prompts import TEST_DESIGNER_PROMPT
from backend.utils.llm import get_llm, invoke_with_retry
from backend.rag.advanced_rag import AdvancedRAG
from backend.config.settings import OUTPUT_DIR


def test_designer_node(state: dict) -> dict:
    """
    Nœud LangGraph : TEST DESIGNER.

    Entrées du state :
      - contract_code (str)
      - user_story    (str, optionnel)

    Sorties ajoutées au state :
      - test_design  (dict)
      - erc_context  (str)
    - rag_cache    (dict)
    """
    print("--- TEST DESIGNER ---")

    contract_code: str = state.get("contract_code", "")

    # --- Récupération du contexte ERC via RAG ---
    rag_cache: dict = {}
    try:
        rag = AdvancedRAG(collection_name="erc_standards")
        rag_result   = rag.retrieve(contract_code)
        erc_context  = rag_result.get("context", "Aucun standard détecté.")
        rag_cache    = {
            "context":       erc_context,
            "detected_ercs": rag_result.get("detected_ercs", []),
            "collection_name": "erc_standards",
        }
    except Exception as exc:
        print(f"[Test Designer] RAG ERC échoué : {exc}")
        erc_context = "Contexte ERC indisponible."
        rag_cache   = {
            "context": erc_context,
            "detected_ercs": [],
            "collection_name": "erc_standards",
        }

    # --- Appel LLM ---
    llm    = get_llm()
    chain  = TEST_DESIGNER_PROMPT | llm
    parser = JsonOutputParser()

    # Fallback minimal pour ne pas interrompre le pipeline.
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

    # Retourne rag_cache pour éviter un 2ème appel RAG dans generator_normal_node.
    return {
        "test_design": result,
        "erc_context": erc_context,
        "rag_cache":   rag_cache,
    }


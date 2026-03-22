"""
analyzer.py
-----------
Agent LangGraph responsable de l'analyse des résultats de tests.
"""

import json

from langchain_core.output_parsers import JsonOutputParser

from src.utils.prompts import ANALYZER_PROMPT
from src.utils.llm import get_llm, invoke_with_retry


def analyzer_node(state: dict) -> dict:
    """
    Nœud LangGraph : ANALYZER.
    Entrées : contract_code, test_code, test_report, coverage_report
    Sorties  : analyzer_report
    """
    print("--- ANALYZER ---")

    test_report = state.get("test_report", {})

    # Diagnostics
    if not state.get("test_code", "").strip():
        print("[Analyzer] ⚠️  test_code vide dans le state.")
    if not test_report:
        print("[Analyzer] ⚠️  test_report vide — Hardhat n'a pas produit de rapport.")
    else:
        s = test_report.get("stats", {})
        print(f"[Analyzer] Rapport reçu : {s.get('passes',0)} ✅  {s.get('failures',0)} ❌  (total {s.get('tests',0)})")

    llm   = get_llm()
    chain = ANALYZER_PROMPT | llm | JsonOutputParser()

    try:
        result: dict = invoke_with_retry(chain, {
            "contract_code":    state.get("contract_code", ""),
            "test_code":        state.get("test_code", ""),
            "mochawesome_json": json.dumps(test_report),
            "coverage_json":    json.dumps(state.get("coverage_report", {})),
        })
        print(f"[Analyzer] ✅ {len(result.get('failures', []))} échec(s) identifié(s).")
    except Exception as exc:
        print(f"[Analyzer] ❌ Fallback LLM : {exc}")
        result = {
            "failures":         [],
            "missing_coverage": {"functions": [], "branches": [], "edge_cases": []},
            "suggestions":      ["Analyzer indisponible — relancez manuellement."],
            "error":            str(exc),
        }

    return {"analyzer_report": result}
"""
analyzer.py
-----------
Agent LangGraph responsable de l'analyse des résultats de tests.

Implémentation déterministe (sans appel LLM) pour éviter les suggestions
hallucinées qui demandent de modifier le contrat Solidity.
"""

from __future__ import annotations

from typing import Any
from src.utils.analyzer_utils import _extract_failures, _extract_missing_coverage





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

    failures = _extract_failures(test_report)
    missing_coverage = _extract_missing_coverage(state.get("coverage_report", {}))

    suggestions: list[str] = []
    if failures:
        suggestions.append("Corriger les tests en échec listés dans failures.")
    if missing_coverage["branches"]:
        suggestions.append("Ajouter des tests pour couvrir les branches existantes du contrat.")

    result = {
        "failures": failures,
        "missing_coverage": missing_coverage,
        "suggestions": suggestions,
    }
    print(f"[Analyzer] ✅ {len(failures)} échec(s) identifié(s).")

    return {"analyzer_report": result}
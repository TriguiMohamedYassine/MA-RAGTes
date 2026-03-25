"""
evaluator.py
-----------
Agent LangGraph responsable de la décision stop / regenerate.
"""

from __future__ import annotations


def _coverage_totals_from_report(coverage_report: dict) -> tuple[int, int, int]:
    """
    Retourne (statements_total, branches_total, functions_total).
    Supporte coverage-summary.json et coverage-final.json.
    """
    total = coverage_report.get("total") if isinstance(coverage_report, dict) else None
    if isinstance(total, dict):
        statements_total = int((total.get("statements") or {}).get("total", 0) or 0)
        branches_total = int((total.get("branches") or {}).get("total", 0) or 0)
        functions_total = int((total.get("functions") or {}).get("total", 0) or 0)
        return statements_total, branches_total, functions_total

    # coverage-final.json fallback
    statements_total = branches_total = functions_total = 0
    if isinstance(coverage_report, dict):
        for file_data in coverage_report.values():
            if not isinstance(file_data, dict):
                continue
            statements_total += len(file_data.get("s", {}) or {})
            functions_total += len(file_data.get("f", {}) or {})
            for hits in (file_data.get("b", {}) or {}).values():
                if isinstance(hits, list):
                    branches_total += len(hits)
    return statements_total, branches_total, functions_total


def evaluator_node(state: dict) -> dict:
    """
    Nœud LangGraph : EVALUATOR.
    Entrées : execution_summary, analyzer_report
    Sorties  : evaluation_decision, evaluation_reason
    """
    print("--- EVALUATOR ---")

    summary = state.get("execution_summary", {}) or {}
    coverage = summary.get("coverage", {}) or {}
    failed = int(summary.get("failed", 0) or 0)
    stmts_pct = float(coverage.get("statements", 0) or 0)
    branches_pct = float(coverage.get("branches", 0) or 0)

    coverage_report = state.get("coverage_report", {}) or {}
    _stmts_total, branches_total, _funcs_total = _coverage_totals_from_report(coverage_report)

    # Règles déterministes :
    # - Si des tests échouent, on continue.
    # - La contrainte branches>=80 n'est appliquée que si le contrat a réellement des branches.
    # - Si aucun test échoue et les seuils applicables sont satisfaits, on stop.
    if failed > 0:
        decision = "regenerate"
        reason = f"{failed} test(s) en échec — correction des tests nécessaire."
    else:
        statements_ok = stmts_pct >= 85
        branches_required = branches_total > 0
        branches_ok = (branches_pct >= 80) if branches_required else True

        if statements_ok and branches_ok:
            decision = "stop"
            if branches_required:
                reason = "Tous les tests passent et les seuils coverage applicables sont atteints."
            else:
                reason = "Tous les tests passent; aucune branche instrumentée à couvrir."
        else:
            decision = "regenerate"
            if not statements_ok:
                reason = f"Couverture statements insuffisante ({stmts_pct:.1f}% < 85%)."
            else:
                reason = f"Couverture branches insuffisante ({branches_pct:.1f}% < 80%)."

    return {
        "evaluation_decision": decision,
        "evaluation_reason": reason,
    }
"""
evaluator.py
-----------
Agent LangGraph responsable de la décision stop / regenerate.
"""

from __future__ import annotations

from backend.utils.evaluator_utils import _coverage_totals_from_report, _has_rate_limit_signal





def evaluator_node(state: dict) -> dict:
    """
    Nœud LangGraph : EVALUATOR.
    Entrées : execution_summary, analyzer_report
    Sorties  : evaluation_decision, evaluation_reason
    """
    print("--- EVALUATOR ---")

    summary = state.get("execution_summary", {}) or {}
    coverage = summary.get("coverage", {}) or {}
    total = int(summary.get("total", 0) or 0)
    failed = int(summary.get("failed", 0) or 0)
    stmts_pct = float(coverage.get("statements", 0) or 0)
    branches_pct = float(coverage.get("branches", 0) or 0)
    rate_limited = _has_rate_limit_signal(state)

    coverage_report = state.get("coverage_report", {}) or {}
    _stmts_total, branches_total, _funcs_total = _coverage_totals_from_report(coverage_report)

    # Règles déterministes :
    # - Si des tests échouent, on continue.
    # - La contrainte branches>=80 n'est appliquée que si le contrat a réellement des branches.
    # - Si aucun test échoue et les seuils applicables sont satisfaits, on stop.
    if total == 0:
        decision = "stop"
        reason = "Aucun test exécuté — arrêt préventif pour éviter une boucle de régénération vide."
    elif rate_limited:
        decision = "stop"
        reason = "API rate-limited (429) détectée — arrêt préventif, relancer après refroidissement quota."
    elif failed > 0:
        decision = "regenerate"
        reason = f"{failed} test(s) en échec — correction des tests nécessaire."
    else:
        # Arrêt générique robuste : si tous les tests passent et la couverture
        # des instructions est déjà élevée, éviter des itérations coûteuses.
        if stmts_pct >= 90:
            decision = "stop"
            reason = (
                "Tous les tests passent et la couverture statements est élevée "
                f"({stmts_pct:.1f}%). Arrêt pour éviter une régénération inutile."
            )
            return {
                "evaluation_decision": decision,
                "evaluation_reason": reason,
            }

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

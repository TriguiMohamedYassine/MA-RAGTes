"""Construit le graphe LangGraph du pipeline en passe unique (sans boucle)."""

from typing import TypedDict

from langgraph.graph import StateGraph, END

from src.agents.test_designer  import test_designer_node
from src.agents.generator      import generator_normal_node
from src.agents.executor       import executor_node
from src.agents.analyzer       import analyzer_node
from src.agents.evaluator      import evaluator_node


# ---------------------------------------------------------------------------
# Définition du state partagé
# ---------------------------------------------------------------------------

class PipelineState(TypedDict, total=False):
    contract_code:       str
    user_story:          str
    erc_context:         str
    test_design:         dict
    test_code:           str
    rag_cache:           dict
    test_report:         dict
    coverage_report:     dict
    execution_summary:   dict
    analyzer_report:     dict
    evaluation_decision: str
    evaluation_reason:   str
    iterations:          int


# ---------------------------------------------------------------------------
# Condition de routage après l'Évaluateur
# ---------------------------------------------------------------------------

def _route_after_evaluation(state: PipelineState) -> str:
    """
    Pipeline en passe unique : toujours arrêter après l'évaluation.
    """
    _print_execution_summary(state)

    print("[Orchestrator] ✅ Exécution terminée en passe unique.")
    return END


# ---------------------------------------------------------------------------
# Affichage du résumé d'exécution
# ---------------------------------------------------------------------------

def _print_execution_summary(state: PipelineState) -> None:
    """Affiche dans le terminal un résumé lisible des résultats Hardhat."""
    summary  = state.get("execution_summary", {})
    reason   = state.get("evaluation_reason", "")
    coverage = summary.get("coverage", {})

    total     = summary.get("total",  0)
    passed    = summary.get("passed", 0)
    failed    = summary.get("failed", 0)
    stmts     = coverage.get("statements", 0)
    branches  = coverage.get("branches",   0)
    functions = coverage.get("functions",  0)

    bar_ok  = "█" * passed
    bar_err = "░" * failed

    print("\n" + "─" * 50)
    print("  📊  RÉSULTATS D'EXÉCUTION")
    print("─" * 50)
    print(f"  Tests     : {bar_ok}{bar_err}  {passed} ✅  {failed} ❌  (total : {total})")
    print(f"  Coverage statements : {stmts:.1f} %")
    print(f"  Coverage branches   : {branches:.1f} %")
    print(f"  Coverage functions  : {functions:.1f} %")
    if reason:
        print(f"  Raison              : {reason}")
    print("─" * 50 + "\n")


# ---------------------------------------------------------------------------
# Construction du graphe
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """
    Construit et compile le graphe LangGraph du pipeline.

    Flux principal :
        test_designer → generator_normal → executor → analyzer → evaluator → END
    """
    graph = StateGraph(PipelineState)

    # --- Nœuds ---
    graph.add_node("test_designer",    test_designer_node)
    graph.add_node("generator_normal", generator_normal_node)
    graph.add_node("executor",         executor_node)
    graph.add_node("analyzer",         analyzer_node)
    graph.add_node("evaluator",        evaluator_node)

    # --- Arêtes du flux principal ---
    graph.set_entry_point("test_designer")
    graph.add_edge("test_designer",    "generator_normal")
    graph.add_edge("generator_normal", "executor")
    graph.add_edge("executor",         "analyzer")
    graph.add_edge("analyzer",         "evaluator")

    # --- Routage conditionnel depuis l'Évaluateur ---
    graph.add_conditional_edges(
        "evaluator",
        _route_after_evaluation,
        {END: END},
    )

    return graph.compile()
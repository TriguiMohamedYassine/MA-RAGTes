"""
orchestrator.py
---------------
Construit et retourne le graphe LangGraph du pipeline de génération de tests.

Ce module est le chef d'orchestre : il relie tous les nœuds agents et définit
les conditions de routage (stop / regenerate).
"""

from typing import TypedDict

from langgraph.graph import StateGraph, END

from src.agents.test_designer  import test_designer_node
from src.agents.generator      import generator_normal_node, generator_corrector_node
from src.agents.executor       import executor_node
from src.agents.analyzer       import analyzer_node
from src.agents.evaluator      import evaluator_node
from src.config                import MAX_RETRIES


# ---------------------------------------------------------------------------
# Définition du state partagé
# ---------------------------------------------------------------------------
# LangGraph fusionne les dicts retournés par chaque nœud dans le state global.
# Il faut utiliser TypedDict (et non dict) pour que la fusion fonctionne
# correctement, notamment pour les champs scalaires comme `iterations`.
# ---------------------------------------------------------------------------

class PipelineState(TypedDict, total=False):
    contract_code:       str
    user_story:          str
    erc_context:         str
    test_design:         dict
    test_code:           str
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
    Retourne ``"increment"`` (→ corrector) si le pipeline doit régénérer, ``END`` sinon.

    Le nœud ``increment`` s'exécute en premier pour mettre à jour le compteur,
    puis enchaîne sur ``corrector``. Ainsi la valeur affichée dans les logs
    reflète toujours l'itération en cours.
    """
    decision   = state.get("evaluation_decision", "stop")
    iterations = state.get("iterations", 0)

    _print_execution_summary(state)

    if iterations >= MAX_RETRIES:
        print(f"[Orchestrator] ⛔ Limite de {MAX_RETRIES} itérations atteinte. Arrêt forcé.")
        return END

    if decision == "regenerate":
        return "increment"   # increment → corrector → executor → …

    print(f"[Orchestrator] ✅ Critères satisfaits après {iterations} itération(s). Arrêt.")
    return END


def _increment_iterations(state: PipelineState) -> dict:
    """
    Incrémente le compteur d'itérations.
    Retourne UNIQUEMENT la clé modifiée — LangGraph fusionne le reste automatiquement.
    """
    new_count = state.get("iterations", 0) + 1
    print(f"[Orchestrator] 🔁 Itération {new_count}/{MAX_RETRIES} — lancement de la correction…")
    return {"iterations": new_count}


# ---------------------------------------------------------------------------
# Affichage du résumé d'exécution
# ---------------------------------------------------------------------------

def _print_execution_summary(state: PipelineState) -> None:
    """Affiche dans le terminal un résumé lisible des résultats Hardhat."""
    summary  = state.get("execution_summary", {})
    decision = state.get("evaluation_decision", "?")
    reason   = state.get("evaluation_reason", "")
    coverage = summary.get("coverage", {})

    total    = summary.get("total",  0)
    passed   = summary.get("passed", 0)
    failed   = summary.get("failed", 0)
    stmts    = coverage.get("statements", 0)
    branches = coverage.get("branches",   0)

    bar_ok  = "█" * passed
    bar_err = "░" * failed

    print("\n" + "─" * 50)
    print("  📊  RÉSULTATS D'EXÉCUTION")
    print("─" * 50)
    print(f"  Tests   : {bar_ok}{bar_err}  {passed} ✅  {failed} ❌  (total : {total})")
    print(f"  Coverage statements : {stmts:.1f} %")
    print(f"  Coverage branches   : {branches:.1f} %")
    print(f"  Décision évaluateur : {'🔁 REGENERATE' if decision == 'regenerate' else '🛑 STOP'}")
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
        test_designer → generator_normal → executor → analyzer → evaluator
                                ↑                                      |
                                └──────── corrector ←──── (regenerate) ┘
    """
    graph = StateGraph(PipelineState)  # TypedDict → fusion automatique par LangGraph

    # --- Nœuds ---
    graph.add_node("test_designer",    test_designer_node)
    graph.add_node("generator_normal", generator_normal_node)
    graph.add_node("executor",         executor_node)
    graph.add_node("analyzer",         analyzer_node)
    graph.add_node("evaluator",        evaluator_node)
    graph.add_node("increment",        _increment_iterations)
    graph.add_node("corrector",        generator_corrector_node)

    # --- Arêtes du flux principal ---
    graph.set_entry_point("test_designer")
    graph.add_edge("test_designer",    "generator_normal")
    graph.add_edge("generator_normal", "executor")
    graph.add_edge("executor",         "analyzer")
    graph.add_edge("analyzer",         "evaluator")

    # --- Routage conditionnel depuis l'Évaluateur ---
    # La fonction retourne "increment" ou END.
    # "increment" incrémente le compteur puis enchaîne sur "corrector".
    graph.add_conditional_edges(
        "evaluator",
        _route_after_evaluation,
        {"increment": "increment", END: END},
    )

    # --- Boucle de correction ---
    graph.add_edge("increment", "corrector")
    graph.add_edge("corrector", "executor")

    return graph.compile()
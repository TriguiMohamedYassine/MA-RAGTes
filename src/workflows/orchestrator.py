"""
orchestrator.py
---------------
Construit le graphe LangGraph du baseline single-agent.

Flux baseline :
    single_agent_baseline -> executor -> END
"""

from typing import TypedDict

from langgraph.graph import StateGraph, END

from src.agents.single_agent_baseline import single_agent_baseline_node
from src.agents.executor import executor_node


# ---------------------------------------------------------------------------
# Définition du state partagé
# ---------------------------------------------------------------------------

class PipelineState(TypedDict, total=False):
    contract_code: str
    user_story: str
    test_code: str
    test_report: dict
    coverage_report: dict
    execution_summary: dict


# ---------------------------------------------------------------------------
# Construction du graphe
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """
    Construit et compile le graphe LangGraph baseline.

    Une génération LLM, puis exécution Hardhat et affichage des résultats.
    """
    graph = StateGraph(PipelineState)

    graph.add_node("single_agent_baseline", single_agent_baseline_node)
    graph.add_node("executor", executor_node)
    graph.set_entry_point("single_agent_baseline")
    graph.add_edge("single_agent_baseline", "executor")
    graph.add_edge("executor", END)

    return graph.compile()
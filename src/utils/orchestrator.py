from typing import TypedDict, Any, Dict
from langgraph.graph import StateGraph, END

from src.agents.test_designer import test_designer_node
from src.agents.generator import generator_normal_node, generator_corrector_node
from src.agents.executor import executor_node
from src.agents.analyzer import analyzer_node
from src.agents.evaluator import evaluator_node

class GraphState(TypedDict):
    contract_code: str
    user_story: str
    test_design: Dict[str, Any]
    test_code: str
    test_report: Dict[str, Any]
    coverage_report: Dict[str, Any]
    execution_summary: Dict[str, Any]
    analyzer_report: Dict[str, Any]
    evaluation_decision: str
    evaluation_reason: str
    iterations: int

def evaluator_condition(state: GraphState):
    decision = state.get("evaluation_decision", "stop")

    if decision in ["fix", "improve"]:
        return "generator_corrector"
    else:
        return END

def build_graph():
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("test_designer", test_designer_node)
    workflow.add_node("generator_normal", generator_normal_node)
    workflow.add_node("generator_corrector", generator_corrector_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("analyzer", analyzer_node)
    workflow.add_node("evaluator", evaluator_node)

    # Establish entry point
    workflow.set_entry_point("test_designer")

    # Build edges
    workflow.add_edge("test_designer", "generator_normal")
    workflow.add_edge("generator_normal", "executor")
    workflow.add_edge("generator_corrector", "executor")
    workflow.add_edge("executor", "analyzer")
    workflow.add_edge("analyzer", "evaluator")

    # Conditional edge from evaluator
    workflow.add_conditional_edges(
        "evaluator",
        evaluator_condition,
        {
            "generator_corrector": "generator_corrector",
            END: END
        }
    )

    # Compile graph
    app = workflow.compile()
    return app

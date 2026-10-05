"""LangGraph topology for the UMC upstream validation pipeline."""

from langgraph.graph import END, START, StateGraph

from v0_code.graph.state import UMCState
from v0_code.nodes.load_inputs import load_inputs_node
from v0_code.nodes.plausibility_filter import (
    plausibility_filter_node,
    route_after_filter,
)
from v0_code.nodes.baseline_engine import baseline_engine_node
from v0_code.nodes.personal_data_store import personal_data_store_node
from v0_code.nodes.short_range_linker import short_range_linker_node
from v0_code.nodes.threshold_evaluator import threshold_evaluator_node


def build_graph():
    builder = StateGraph(UMCState)

    builder.add_node("load_inputs", load_inputs_node)
    builder.add_node("plausibility_filter", plausibility_filter_node)
    builder.add_node("threshold_evaluator", threshold_evaluator_node)
    builder.add_node("short_range_linker", short_range_linker_node)
    builder.add_node("personal_data_store", personal_data_store_node)
    builder.add_node("baseline_engine", baseline_engine_node)

    builder.add_edge(START, "load_inputs")
    builder.add_edge("load_inputs", "plausibility_filter")
    builder.add_conditional_edges(
        "plausibility_filter",
        route_after_filter,
        {"threshold_evaluator": "threshold_evaluator", "__end__": END},
    )
    builder.add_edge("threshold_evaluator", "short_range_linker")
    builder.add_edge("short_range_linker", "personal_data_store")
    builder.add_edge("personal_data_store", "baseline_engine")
    builder.add_edge("baseline_engine", END)

    return builder.compile()

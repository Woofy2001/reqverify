from typing import TypedDict, Literal
import pytest
from langgraph.graph import StateGraph, START, END

MAX_CRITIC_ITERS = 3

class CondState(TypedDict, total=False):
    condition: dict
    selectors: list[dict]
    script: str
    probe: dict
    critic: dict
    iteration: int
    final: str

def create_agent3_subgraph(critic_behavior="approve_at_1"):
    """Factory creating an Agent 3 subgraph with configurable mock critic behavior."""
    def generate(state: CondState) -> dict:
        it = state.get("iteration", 0) + 1
        return {"script": f"# Test script iteration {it}", "iteration": it}

    def probe(state: CondState) -> dict:
        return {"probe": {"outcome": "passed", "duration": 0.5}}

    def critic(state: CondState) -> dict:
        it = state["iteration"]
        if critic_behavior == "approve_at_1":
            verdict = "APPROVE"
        elif critic_behavior == "approve_at_2":
            verdict = "APPROVE" if it >= 2 else "REJECT"
        elif critic_behavior == "never_converge":
            verdict = "REJECT"
        else:
            verdict = "REJECT"
        return {"critic": {"verdict": verdict, "iteration": it}}

    def route(state: CondState) -> Literal["generate", "approved", "not_converged"]:
        if state["critic"]["verdict"] == "APPROVE":
            return "approved"
        if state["iteration"] >= MAX_CRITIC_ITERS:
            return "not_converged"
        return "generate"

    g = StateGraph(CondState)
    g.add_node("generate", generate)
    g.add_node("probe", probe)
    g.add_node("critic", critic)
    g.add_node("approved", lambda s: {"final": "approved"})
    g.add_node("not_converged", lambda s: {"final": "not_converged"})

    g.add_edge(START, "generate")
    g.add_edge("generate", "probe")
    g.add_edge("probe", "critic")
    g.add_conditional_edges("critic", route, {
        "generate": "generate",
        "approved": "approved",
        "not_converged": "not_converged"
    })
    g.add_edge("approved", END)
    g.add_edge("not_converged", END)

    return g.compile()

def test_spike_s3_approves_on_first_pass():
    graph = create_agent3_subgraph(critic_behavior="approve_at_1")
    result = graph.invoke({"condition": {"id": "C-01"}}, {"recursion_limit": 25})
    assert result["final"] == "approved"
    assert result["iteration"] == 1

def test_spike_s3_repairs_and_approves_at_iteration_2():
    graph = create_agent3_subgraph(critic_behavior="approve_at_2")
    result = graph.invoke({"condition": {"id": "C-02"}}, {"recursion_limit": 25})
    assert result["final"] == "approved"
    assert result["iteration"] == 2

def test_spike_s3_forced_reject_terminates_at_3():
    graph = create_agent3_subgraph(critic_behavior="never_converge")
    result = graph.invoke({"condition": {"id": "C-03"}}, {"recursion_limit": 25})
    assert result["final"] == "not_converged"
    assert result["iteration"] == 3

"""Agent 3 subgraph: generate -> probe -> critic -> route, capped at 3 iterations (Decision D8, NFR-03, Guide §10).

One subgraph invocation handles ONE condition, so a pipeline of N conditions never approaches LangGraph's
``recursion_limit`` (each iteration is ~3 super-steps; 3 iterations + terminal node fit well under 25).
The state is plain JSON-serialisable data so it can later be checkpointed (``thread_id = run_id:condition_id``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional, TypedDict, Union

from langgraph.graph import END, START, StateGraph

from reqverify.agents.critic import TestCritic
from reqverify.agents.generator import GenerationContractError, TestGenerator
from reqverify.safety.ast_validator import ScriptSafetyViolation
from reqverify.schemas.contracts import ExtractedCondition, ProbeResult
from reqverify.schemas.probes import CriticDecision
from reqverify.schemas.selectors import SelectorMap

MAX_CRITIC_ITERS = 3
_PER_PAGE_SNAPSHOT_CHARS = 2500


class CondState(TypedDict, total=False):
    condition: dict            # ExtractedCondition.model_dump()
    selectors: list            # list[UIElementSelector.model_dump()]
    snapshot_excerpt: str      # trimmed ARIA snapshot text shown to the critic
    script: str
    probe: dict                # ProbeResult.model_dump()
    critic: dict               # CriticDecision.model_dump()
    iteration: int
    final: str                 # "approved" | "not_converged"
    canonical_signature: list  # D7: locked assertion signature from the first valid generation
    canonical_assertion_code: list
    assertion_reverted: bool
    generation_error: str


def route(state: CondState) -> Literal["generate", "approved", "not_converged"]:
    if state["critic"]["verdict"] == "APPROVE":
        return "approved"
    if state["iteration"] >= MAX_CRITIC_ITERS:
        return "not_converged"
    return "generate"


def build_agent3(generator: TestGenerator, prober: Any, critic: TestCritic):
    """Compile the Agent 3 subgraph around injected generator, prober and critic."""

    def generate(state: CondState) -> dict:
        it = state.get("iteration", 0) + 1
        try:
            res = generator.generate(
                state["condition"],
                state.get("selectors", []),
                iteration=it,
                previous_script=state.get("script") or None,
                canonical_signature=state.get("canonical_signature"),
                canonical_assertion_code=state.get("canonical_assertion_code"),
                probe=state.get("probe"),
                critic=state.get("critic"),
            )
        except GenerationContractError as exc:
            return {"iteration": it, "generation_error": str(exc)}
        update: dict = {
            "script": res.script,
            "iteration": it,
            "generation_error": "",
            "assertion_reverted": bool(state.get("assertion_reverted")) or res.reverted,
        }
        if state.get("canonical_signature") is None:
            update["canonical_signature"] = list(res.signature)
            update["canonical_assertion_code"] = list(res.assertion_code)
        return update

    def probe(state: CondState) -> dict:
        if state.get("generation_error"):
            return {"probe": _runtime_error("GenerationContractError", state["generation_error"]).model_dump()}
        cond_id = state["condition"]["condition_id"]
        try:
            result = prober.probe(state["script"], cond_id, state["iteration"])
        except ScriptSafetyViolation as exc:
            result = _runtime_error("ScriptSafetyViolation", "; ".join(exc.violations))
        return {"probe": result.model_dump()}

    def critique(state: CondState) -> dict:
        probe_d = state["probe"]
        if probe_d.get("exception_type") in ("GenerationContractError", "ScriptSafetyViolation"):
            decision = critic.reject_without_review(probe_d.get("stdout_tail", "") or "script rejected")
        else:
            decision = critic.review(
                state["condition"], state["script"], probe_d, state.get("snapshot_excerpt", "")
            )
        return {"critic": decision.model_dump()}

    g = StateGraph(CondState)
    g.add_node("generate", generate)
    g.add_node("probe", probe)
    g.add_node("critic", critique)
    g.add_node("approved", lambda s: {"final": "approved"})
    g.add_node("not_converged", lambda s: {"final": "not_converged"})
    g.add_edge(START, "generate")
    g.add_edge("generate", "probe")
    g.add_edge("probe", "critic")
    g.add_conditional_edges(
        "critic", route, {"generate": "generate", "approved": "approved", "not_converged": "not_converged"}
    )
    g.add_edge("approved", END)
    g.add_edge("not_converged", END)
    return g.compile()


def _runtime_error(exc_type: str, message: str) -> ProbeResult:
    return ProbeResult(
        exit_code=-2, outcome="runtime_error", exception_type=exc_type, stdout_tail=message[-2000:], duration_s=0.0
    )


# --------------------------------------------------------------------------- convenience API ------
@dataclass
class Agent3Result:
    final: str                       # "approved" | "not_converged"
    iterations: int
    script: str
    probe: ProbeResult
    critic: CriticDecision
    assertion_reverted: bool
    untested_reason: Optional[str]   # "critic_not_converged" when the loop gave up
    needs_human_review: bool


def snapshot_excerpt(selector_map: SelectorMap, total_chars: int = 6000) -> str:
    parts = []
    for route_, snap in selector_map.pages.items():
        parts.append(f"# {route_}\n{snap.raw_aria_tree[:_PER_PAGE_SNAPSHOT_CHARS]}")
    return "\n\n".join(parts)[:total_chars]


def run_agent3(
    condition: Union[ExtractedCondition, dict],
    selector_map: SelectorMap,
    *,
    generator: TestGenerator,
    prober: Any,
    critic: TestCritic,
) -> Agent3Result:
    """Run the generator-critic loop for ONE testable condition and summarise the outcome."""
    cond = condition if isinstance(condition, ExtractedCondition) else ExtractedCondition.model_validate(condition)
    graph = build_agent3(generator, prober, critic)
    out = graph.invoke(
        {
            "condition": cond.model_dump(),
            "selectors": [e.model_dump() for e in selector_map.get_all_elements()],
            "snapshot_excerpt": snapshot_excerpt(selector_map),
        },
        {"recursion_limit": 25},
    )
    not_converged = out["final"] == "not_converged"
    return Agent3Result(
        final=out["final"],
        iterations=out["iteration"],
        script=out.get("script", ""),
        probe=ProbeResult.model_validate(out["probe"]),
        critic=CriticDecision.model_validate(out["critic"]),
        assertion_reverted=bool(out.get("assertion_reverted")),
        untested_reason="critic_not_converged" if not_converged else None,
        needs_human_review=not_converged,
    )

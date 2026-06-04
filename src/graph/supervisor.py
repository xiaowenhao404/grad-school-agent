"""顶层 supervisor 图组装。"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, StateGraph

from src.graph.state import GraphState


def _reject_node(state: GraphState) -> GraphState:
    reply = "抱歉，我是申研选校助手，仅能协助选校咨询、预约老师和相关问题解答。"
    state["agent_response"] = reply
    trace = state.setdefault("trace", [])
    trace.append({"agent": "reject", "label": "归类机器人", "text": "本轮请求与本系统业务无关，已拒绝。"})
    msgs = state.setdefault("messages", [])
    from datetime import datetime
    msgs.append({"role": "assistant", "agent_name": "reject",
                 "content": reply, "created_at": datetime.utcnow().isoformat()})
    return state


def _route(state: GraphState) -> str:
    return state.get("task_type", "reject")


@lru_cache(maxsize=1)
def build_supervisor_graph():
    from src.agents.appointment_agent import AppointmentAgent
    from src.agents.consultant_agent import ConsultantAgent
    from src.agents.school_selection_agent import SchoolSelectionAgent
    from src.agents.task_classifier import TaskClassifier
    from src.agents.user_behavior_agent import UserBehaviorAgent
    from src.graph.hooks import post_hook, pre_hook

    g = StateGraph(GraphState)
    g.add_node("pre_hook", pre_hook)
    g.add_node("classifier", TaskClassifier().run)
    g.add_node("consultant", ConsultantAgent().run)
    g.add_node("school", SchoolSelectionAgent().run)
    g.add_node("appointment", AppointmentAgent().run)
    g.add_node("behavior", UserBehaviorAgent().run)
    g.add_node("reject", _reject_node)
    g.add_node("post_hook", post_hook)

    g.set_entry_point("pre_hook")
    g.add_edge("pre_hook", "classifier")
    g.add_conditional_edges("classifier", _route, {
        "consultant": "consultant",
        "school": "school",
        "appointment": "appointment",
        "behavior": "behavior",
        "reject": "reject",
    })
    for expert in ("consultant", "school", "appointment", "behavior"):
        g.add_edge(expert, "post_hook")
    g.add_edge("post_hook", END)
    g.add_edge("reject", END)

    return g.compile()

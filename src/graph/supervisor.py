"""顶层 supervisor 图组装。

详见 DEV_SPEC.md 4.1 节整体架构图。

流程：
    user_input
        -> pre_hook
        -> task_classifier
        -> conditional edge by task_type:
            - reject: -> reject_node -> END
            - consultant: -> consultant_agent -> post_hook -> END
            - school: -> school_selection_agent -> post_hook -> END
            - appointment: -> appointment_subgraph -> post_hook -> END
            - behavior: -> user_behavior_agent (display) -> END
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def build_supervisor_graph():
    """构建并编译 LangGraph StateGraph。

    Returns:
        编译后的 graph 实例，调用 .invoke(state) 即可运行。
    """
    # TODO:
    # from langgraph.graph import StateGraph, END
    # from src.graph.state import GraphState
    # from src.graph.hooks import pre_hook, post_hook
    # from src.agents.task_classifier import TaskClassifier
    # ...
    #
    # graph = StateGraph(GraphState)
    # graph.add_node("pre_hook", pre_hook)
    # graph.add_node("classifier", TaskClassifier().run)
    # graph.add_node("consultant", ConsultantAgent().run)
    # ...
    # graph.add_edge("pre_hook", "classifier")
    # graph.add_conditional_edges("classifier", route_by_task_type, {...})
    # graph.set_entry_point("pre_hook")
    # return graph.compile()
    raise NotImplementedError


def route_by_task_type(state: dict) -> str:
    """conditional edge 路由函数。"""
    # TODO: return state['task_type']
    raise NotImplementedError

"""预约状态机 subgraph。

详见 DEV_SPEC.md 4.4.3 节预约状态机图、6.4 节。

状态：collect_preferences -> show_candidates -> show_slots -> confirm -> done
"""
from __future__ import annotations


def build_appointment_subgraph():
    """构建预约状态机子图。

    与 supervisor 不同，本子图状态机需要"等待用户输入"才能推进，
    实现上通常每次对话只走一步（一个 stage），然后退出等下次调用。
    """
    # TODO:
    # 1. 定义状态机各 node（collect_preferences / show_candidates / ...）
    # 2. 每个 node 内部判断"信息是否齐全/用户是否已选择"
    # 3. 推进 stage 并写回 state['appointment_slots']['current_stage']
    raise NotImplementedError

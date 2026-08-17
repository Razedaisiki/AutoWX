"""群列表与 process_groups 参数。"""
from __future__ import annotations


def build_group_nicknames(groups: list[str], nickname: str) -> dict[str, str]:
    """把机器人群昵称套用到所有群。"""
    return {group: nickname for group in groups}

"""文章生命周期状态枚举与迁移规则。"""

from __future__ import annotations

from enum import Enum


class ArticleStatus(str, Enum):
    """文章生命周期状态枚举。

    六态模型：
        draft → review → ready → drafted → published → archived
    """

    DRAFT = "draft"
    REVIEW = "review"
    READY = "ready"
    DRAFTED = "drafted"
    PUBLISHED = "published"
    ARCHIVED = "archived"

    @classmethod
    def is_valid(cls, status: str) -> bool:
        """判断是否为合法状态值。"""
        return status in {s.value for s in cls}

    @classmethod
    def valid_transitions(cls) -> dict[str, list[str]]:
        """返回合法状态迁移表。"""
        return {
            cls.DRAFT.value: [cls.REVIEW.value, cls.ARCHIVED.value],
            cls.REVIEW.value: [cls.READY.value, cls.DRAFT.value, cls.ARCHIVED.value],
            cls.READY.value: [cls.DRAFTED.value, cls.PUBLISHED.value, cls.ARCHIVED.value],
            cls.DRAFTED.value: [cls.PUBLISHED.value, cls.READY.value, cls.ARCHIVED.value],
            cls.PUBLISHED.value: [cls.ARCHIVED.value],
            cls.ARCHIVED.value: [cls.DRAFT.value],
        }

    @classmethod
    def is_publishable(cls, status: str) -> bool:
        """判断是否可执行 ink publish。仅 ready 状态可发布。"""
        return status == cls.READY.value

    @classmethod
    def is_syndicatable(cls, status: str) -> bool:
        """判断是否可执行 ink syndicate（Phase 2）。仅 drafted 状态可推送。"""
        return status == cls.DRAFTED.value

    @classmethod
    def is_visible_in_search(cls, status: str) -> bool:
        """判断是否在默认搜索结果中可见。仅 archived 不可见。"""
        return status != cls.ARCHIVED.value

"""
通用分页工具
"""
from pydantic import BaseModel, ConfigDict
from typing import List, Any


class PaginatedResult(BaseModel):
    """分页响应的通用结构"""
    model_config = ConfigDict(from_attributes=True)

    items: List[Any] = []
    total: int = 0
    page: int = 1
    page_size: int = 0
    total_pages: int = 1
    has_more: bool = False



def paginate(query, page: int = 1, page_size: int = 0) -> dict:
    """
    通用分页函数。

    - page_size=0（默认）: 不分页，返回全部
    - page_size>0: 分页返回

    返回 dict，可直接作为 PaginatedResult。
    """
    total = query.count()

    if page_size <= 0:
        # 全量模式
        items = query.all()
        return {
            "items": items,
            "total": total,
            "page": 1,
            "page_size": 0,
            "total_pages": 1,
            "has_more": False,
        }

    # 分页模式
    page = max(1, page)
    page_size = min(page_size, 100)
    total_pages = max(1, (total + page_size - 1) // page_size)
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_more": page < total_pages,
    }

"""管理端仪表盘查询公共 API。"""

from ._dashboard_highlights import get_dashboard_highlights
from ._dashboard_overview import get_dashboard_overview
from ._dashboard_trends import get_dashboard_trends

__all__ = [
    "get_dashboard_highlights",
    "get_dashboard_overview",
    "get_dashboard_trends",
]

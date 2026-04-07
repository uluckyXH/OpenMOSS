"""task_cli 终端输出封装。"""

import json


def print_json(data) -> None:
    """格式化输出 JSON。"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def extract_items(data):
    """从分页响应中提取 items 列表，并打印分页信息。"""
    if isinstance(data, dict) and "items" in data:
        total = data.get("total", 0)
        page = data.get("page", 1)
        page_size = data.get("page_size", 0)
        if page_size > 0:
            print(f"  [第 {page} 页，共 {data.get('total_pages', 1)} 页，{total} 条记录]")
        else:
            print(f"  [共 {total} 条记录]")
        return data["items"]
    return data if isinstance(data, list) else []


def print_http_error(status_code: int, detail: str) -> None:
    """统一输出 HTTP 错误。"""
    print(f"❌ 错误 ({status_code}): {detail}")


def print_connection_error(base_url: str) -> None:
    """统一输出连接错误。"""
    print(f"❌ 无法连接到服务: {base_url}")

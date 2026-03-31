#!/usr/bin/env bash

# ============================================================
# OpenMOSS 停止脚本
# ============================================================

OPENMOSS_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$OPENMOSS_DIR/.openmoss.pid"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo -e "${GREEN}[OpenMOSS]${NC} 服务已停止 (PID: $PID)"
    else
        echo -e "${YELLOW}[OpenMOSS]${NC} 服务未运行 (PID $PID 已不存在)"
    fi
    rm -f "$PID_FILE"
else
    PID=$(pgrep -f "uvicorn app.main:app" 2>/dev/null | head -1)
    if [ -n "$PID" ]; then
        kill "$PID"
        echo -e "${GREEN}[OpenMOSS]${NC} 服务已停止 (PID: $PID)"
    else
        echo -e "${YELLOW}[OpenMOSS]${NC} 服务未运行"
    fi
fi

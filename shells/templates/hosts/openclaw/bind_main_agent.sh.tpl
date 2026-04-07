REQUIRE_OPENCLAW=1

section "Bind OpenClaw main agent"

AGENT_ID="${AGENT_ID:-main}"
AGENT_WORKSPACE="${AGENT_WORKSPACE:-$HOME/.openclaw/workspace}"

log "binding OpenClaw main agent: ${AGENT_ID}"
log "workspace: ${AGENT_WORKSPACE}"

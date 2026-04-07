REQUIRE_OPENCLAW=1

section "Bind existing OpenClaw agent"

[[ -n "${AGENT_ID:-}" ]] || die "AGENT_ID is required"
[[ -n "${AGENT_WORKSPACE:-}" ]] || die "AGENT_WORKSPACE is required"

if openclaw agents list 2>/dev/null | grep -qF "${AGENT_ID}"; then
  log "found existing OpenClaw agent: ${AGENT_ID}"
else
  die "OpenClaw agent not found: ${AGENT_ID}"
fi

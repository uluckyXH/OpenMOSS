REQUIRE_OPENCLAW=1

section "Create OpenClaw sub agent"

[[ -n "${AGENT_ID:-}" ]] || die "AGENT_ID is required"
[[ -n "${AGENT_WORKSPACE:-}" ]] || die "AGENT_WORKSPACE is required"

if openclaw agents list 2>/dev/null | grep -qF "${AGENT_ID}"; then
  log "agent already exists: ${AGENT_ID}"
else
  cmd=(openclaw agents add "${AGENT_ID}" --workspace "${AGENT_WORKSPACE}" --non-interactive)
  if [[ -n "${OPENCLAW_MODEL:-}" ]]; then
    cmd+=(--model "${OPENCLAW_MODEL}")
  fi
  "${cmd[@]}"
  log "created agent ${AGENT_ID}"
fi

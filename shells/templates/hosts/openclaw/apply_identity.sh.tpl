if [[ "${WRITE_IDENTITY_MD:-0}" == "1" ]]; then
  section "Apply OpenClaw identity"
  openclaw agents set-identity \
    --agent "${AGENT_ID}" \
    --workspace "${AGENT_WORKSPACE}" \
    --from-identity >/dev/null
  log "applied identity from ${IDENTITY_FILE}"
fi

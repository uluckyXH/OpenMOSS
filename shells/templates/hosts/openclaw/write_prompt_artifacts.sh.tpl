section "Write OpenClaw prompt artifacts"

if [[ "${WRITE_AGENTS_MD:-0}" == "1" ]]; then
  cat > "${AGENTS_FILE}" <<'EOF_AGENTS_MD'
${AGENTS_MD_CONTENT}
EOF_AGENTS_MD
  log "wrote ${AGENTS_FILE}"
fi

if [[ "${WRITE_SOUL_MD:-0}" == "1" ]]; then
  cat > "${SOUL_FILE}" <<'EOF_SOUL_MD'
${SOUL_MD_CONTENT}
EOF_SOUL_MD
  log "wrote ${SOUL_FILE}"
fi

if [[ "${WRITE_IDENTITY_MD:-0}" == "1" ]]; then
  cat > "${IDENTITY_FILE}" <<'EOF_IDENTITY_MD'
${IDENTITY_MD_CONTENT}
EOF_IDENTITY_MD
  log "wrote ${IDENTITY_FILE}"
fi

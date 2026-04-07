section "Download task CLI bundle"

[[ -n "${API_KEY:-}" ]] || die "API_KEY is required before downloading skill bundle"

curl -fsS -H "Authorization: Bearer ${API_KEY}" \
  "${OPENMOSS_URL}${OPENMOSS_CLI_PATH:-/api/tools/cli}" \
  -o "${TASK_CLI_PATH}"
chmod +x "${TASK_CLI_PATH}"
log "downloaded task-cli.py to ${TASK_CLI_PATH}"

curl -fsS -H "Authorization: Bearer ${API_KEY}" \
  "${OPENMOSS_URL}${OPENMOSS_SKILL_PATH:-/api/agents/me/skill}" \
  -o "${SKILL_MD_PATH}"
log "downloaded SKILL.md to ${SKILL_MD_PATH}"

# Credential placement is intentionally not handled here.
# Later bootstrap assembly will decide whether API key goes into
# task-cli.py, a credential file, or another target.

echo "╔══════════════════════════════════════════════════════╗"
echo "║           OpenMOSS deployment summary               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo
echo "  Agent ID:    ${AGENT_ID}"
echo "  Name:        ${AGENT_NAME}"
echo "  Role:        ${AGENT_ROLE}"
echo "  Workspace:   ${AGENT_WORKSPACE}"
echo "  OpenMOSS:    ${OPENMOSS_URL}"

if [[ -n "${SCHEDULE_EXPR:-}" ]]; then
  echo "  Schedule:    ${SCHEDULE_EXPR} (timeout ${SCHEDULE_TIMEOUT_SECONDS:-1800}s)"
fi

echo

echo "╔══════════════════════════════════════════════════════╗"
echo "║           Deployment fragment complete              ║"
echo "╚══════════════════════════════════════════════════════╝"
echo
echo "  Agent:       ${AGENT_NAME} (${AGENT_ID})"
echo "  Workspace:   ${AGENT_WORKSPACE}"
echo "  Skill dir:   ${SKILL_DIR}"

if [[ -n "${AGENTS_FILE:-}" ]]; then
  echo "  AGENTS.md:   ${AGENTS_FILE}"
fi
if [[ -n "${SOUL_FILE:-}" ]]; then
  echo "  SOUL.md:     ${SOUL_FILE}"
fi
if [[ -n "${IDENTITY_FILE:-}" ]]; then
  echo "  IDENTITY.md: ${IDENTITY_FILE}"
fi

echo
